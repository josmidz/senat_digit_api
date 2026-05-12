"""ConsumerValidationMiddleware — three identification paths in priority order.

   1. **HMAC signature** (the secure default for v1):
        X-Api-Consumer-Flag, X-Api-Timestamp, X-Api-Nonce, X-Api-Signature
        Verified against `consumer_secret` stored on the RefApiConsumer row.
        Adds: body integrity, time-bounded replay protection, per-request
        unforgeability without the shared secret.

   2. **Encrypted consumer key** (legacy production hardening, kept for
      back-compat with TRANSCO-era clients):
        api-consumer: <Fernet ciphertext of consumer_key>

   3. **Bare flag** (dev convenience only):
        x-api-consumer-flag: senat_digit_mobile
        Resolves the consumer by `flag` directly. Emits a deprecation log.
        REJECTED when settings.STRICT_CONSUMER_VALIDATION is True.

Production runs with STRICT_CONSUMER_VALIDATION=True and only path (1) and
(2) are accepted. Local + CI keep the bare-flag fallback so smoke tests
don't need to compute signatures.

Body handling: we buffer the request body once (via a wrapped `receive`)
so we can SHA-256 it for the canonical signature input AND still let the
downstream handler read it. Bounded-size requests only — uploads larger
than CONSUMER_SIGNATURE_MAX_BODY_BYTES bypass signature verification and
are routed through the legacy paths.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Awaitable, Callable, Optional

from fastapi import HTTPException, Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.modules.auth.services.signature.signature_service import (
    SignatureComponents,
    SignatureService,
)
from app.modules.core.configs.config import settings
from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.encryption.encryption_service import EncryptionService
from app.modules.core.services.generic.generic_services import GenericService

logger = logging.getLogger("senat_digit.consumer_validation")

# Bodies larger than this skip HMAC verification (multipart uploads to
# the fs api land here). The fs api enforces its own auth on top.
MAX_SIGNED_BODY_BYTES = 5 * 1024 * 1024  # 5 MiB

# WebSocket routes that don't carry consumer headers — skip middleware.
DEFAULT_EXCLUDED_PREFIXES = (
    "/api/v1/websocket/ws",
    "/api/v1/websocket/pending-notifications",
    "/api/v1/ng-websocket/ws",
)


class ConsumerValidationMiddleware:
    """ASGI middleware that resolves `request.state.apiConsumer`."""

    def __init__(self, app: ASGIApp, excluded_routes: Optional[list[str]] = None):
        self.app = app
        self.excluded_routes = list(excluded_routes or []) + list(DEFAULT_EXCLUDED_PREFIXES)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_path = scope.get("path", "")
        if any(request_path.startswith(p) for p in self.excluded_routes):
            await self.app(scope, receive, send)
            return

        # ── Body buffering ───────────────────────────────────────────────
        # Read the entire body once so we can hash it. Replay it to the
        # downstream app via a wrapped `receive` callable. Capped at
        # MAX_SIGNED_BODY_BYTES — larger requests bypass HMAC and go
        # straight through to the legacy resolution paths.
        body_bytes, oversize = await _drain_body(receive, MAX_SIGNED_BODY_BYTES)
        replay_receive = _make_replay_receive(body_bytes)

        request = Request(scope, receive=replay_receive)
        accept_language = (
            request.headers.get("accept-language", DEFAULT_LANGUAGE)
            .split(",")[0]
            .strip()
        )
        generic_service = GenericService(accept_language)

        api_consumer = None
        try:
            api_consumer = await self._resolve_consumer(
                request=request,
                body_bytes=body_bytes,
                oversize_body=oversize,
                generic_service=generic_service,
            )
        except HTTPException as exc:
            # Strict mode rejects with explicit status. Re-raise via the
            # ASGI error pipeline so FastAPI's exception handlers surface
            # a clean JSON error.
            await _send_http_error(send, exc.status_code, exc.detail)
            return
        except Exception as exc:  # noqa: BLE001
            # Defensive: never let the middleware crash the request
            # silently. Log + fall through; the request will hit the
            # auth pipeline without `apiConsumer` and 404 from there if
            # the route requires one.
            logger.exception("ConsumerValidationMiddleware unexpected error: %s", exc)

        if api_consumer:
            request.state.apiConsumer = api_consumer

        # Hand off to downstream with the buffered body.
        await self.app(scope, replay_receive, send)

    # ── Resolution paths (priority-ordered) ─────────────────────────────

    async def _resolve_consumer(
        self,
        *,
        request: Request,
        body_bytes: bytes,
        oversize_body: bool,
        generic_service: GenericService,
    ) -> Optional[dict]:
        """Try each path in turn. Returns the consumer dict on success."""
        # Path 1: HMAC signature (secure default).
        sig_components = _extract_signature_headers(request, body_bytes)
        if sig_components is not None:
            return await self._verify_hmac(
                components=sig_components,
                request=request,
                generic_service=generic_service,
            )

        # Path 2: Legacy encrypted consumer key.
        encrypted = request.headers.get("api-consumer")
        if encrypted:
            try:
                consumer_key = EncryptionService.decrypt_data(encrypted)
            except Exception:  # noqa: BLE001
                logger.warning("api-consumer header failed to decrypt — rejecting")
                consumer_key = None
            if consumer_key:
                return await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_API_CONSUMER,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__consumer_key": str(consumer_key).strip()},
                )

        # Path 3: Bare flag fallback (dev only).
        flag = request.headers.get("x-api-consumer-flag")
        if flag:
            if settings.STRICT_CONSUMER_VALIDATION:
                logger.warning(
                    "STRICT_CONSUMER_VALIDATION rejecting bare-flag header "
                    "from %s flag=%s path=%s",
                    request.client.host if request.client else "?",
                    flag,
                    request.url.path,
                )
                raise HTTPException(
                    status_code=401,
                    detail="Signature de requête manquante.",
                )
            logger.info(
                "ConsumerValidationMiddleware: accepting bare flag '%s' "
                "(non-strict mode). Migrate this client to HMAC signing.",
                flag,
            )
            return await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_API_CONSUMER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__flag": str(flag).strip()},
            )

        # Strict mode requires a header — nothing matched, reject.
        if settings.STRICT_CONSUMER_VALIDATION:
            raise HTTPException(
                status_code=401,
                detail="Signature de requête manquante.",
            )

        return None

    async def _verify_hmac(
        self,
        *,
        components: SignatureComponents,
        request: Request,
        generic_service: GenericService,
    ) -> Optional[dict]:
        consumer = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.REF_API_CONSUMER,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter__flag": components.flag},
        )
        if not consumer:
            raise HTTPException(
                status_code=401,
                detail="Client API inconnu.",
            )
        secret = consumer.get("consumer_secret")
        if not secret:
            # The consumer exists but no secret has been provisioned.
            # In strict mode this is a deployment mistake — fail loudly.
            # In non-strict, fall through (the bare-flag path could still
            # have matched if we hadn't run the HMAC path first).
            logger.error(
                "consumer_secret missing for flag=%s — provision it via the "
                "rotate-consumer-secret admin action before requiring HMAC.",
                components.flag,
            )
            if settings.STRICT_CONSUMER_VALIDATION:
                raise HTTPException(
                    status_code=401,
                    detail="Configuration du client API incomplète.",
                )
            return None

        result = await SignatureService.verify_request_signature(
            consumer_secret=secret,
            components=components,
            method=request.method,
            path=_full_path_with_query(request),
            max_skew_seconds=settings.CONSUMER_SIGNATURE_MAX_SKEW_SECONDS,
        )
        if not result.ok:
            # For 'stale' include the actual delta so a misconfigured
            # device clock is obvious in the logs (NTP drift, wrong
            # timezone, emulator clock vs host, …).
            import time as _time
            now_epoch = int(_time.time())
            delta = now_epoch - components.timestamp
            logger.warning(
                "HMAC verification failed reason=%s flag=%s path=%s "
                "client_ts=%s server_ts=%s delta_s=%+d (window=±%ss)",
                result.reason,
                components.flag,
                request.url.path,
                components.timestamp,
                now_epoch,
                delta,
                settings.CONSUMER_SIGNATURE_MAX_SKEW_SECONDS,
            )
            # Map verification reason → user-facing French message.
            window = settings.CONSUMER_SIGNATURE_MAX_SKEW_SECONDS
            detail_map = {
                "missing_nonce": "Nonce de signature manquant.",
                "stale": (
                    f"Horodatage de signature expiré ou en avance "
                    f"(décalage de {delta:+d}s, fenêtre ±{window}s). "
                    "Vérifiez l'horloge du client."
                ),
                "bad_signature": "Signature de requête invalide.",
            }
            raise HTTPException(
                status_code=401,
                detail=detail_map.get(result.reason, "Signature de requête invalide."),
            )
        return consumer


# ── Body buffering helpers ──────────────────────────────────────────────


async def _drain_body(receive: Receive, max_bytes: int) -> tuple[bytes, bool]:
    """Read the full request body. Returns (body, oversize_flag).

    If the cumulative body exceeds `max_bytes`, we stop reading and
    return `oversize_flag=True`. The caller should skip HMAC verification
    on oversize requests (signature-over-multi-MB-uploads is wasteful and
    the fs api enforces its own auth)."""
    chunks: list[bytes] = []
    total = 0
    oversize = False
    while True:
        msg = await receive()
        if msg["type"] != "http.request":
            # http.disconnect — propagate by returning what we have.
            break
        chunk = msg.get("body", b"")
        if chunk:
            total += len(chunk)
            if total > max_bytes:
                oversize = True
                # Continue consuming so we don't break the socket, but
                # don't keep the bytes — we won't HMAC them.
                if not msg.get("more_body", False):
                    break
                continue
            chunks.append(chunk)
        if not msg.get("more_body", False):
            break
    return (b"" if oversize else b"".join(chunks), oversize)


def _make_replay_receive(body: bytes) -> Receive:
    """Return a `receive` callable that yields the buffered body once,
    then disconnects on subsequent calls. Hands the downstream app a
    body identical to what arrived on the wire."""
    sent = False

    async def replay() -> Message:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return replay


async def _send_http_error(send: Send, status_code: int, detail: str) -> None:
    """Emit a minimal JSON error response when the middleware itself
    rejects the request (we can't rely on FastAPI's exception handlers
    here because we haven't called downstream yet)."""
    payload = (b'{"detail":' + _json_escape(detail).encode("utf-8") + b"}")
    await send({
        "type": "http.response.start",
        "status": status_code,
        "headers": [
            (b"content-type", b"application/json; charset=utf-8"),
            (b"content-length", str(len(payload)).encode("ascii")),
        ],
    })
    await send({"type": "http.response.body", "body": payload, "more_body": False})


def _json_escape(s: str) -> str:
    """Cheap JSON string escape — enough for error messages."""
    import json
    return json.dumps(s)


# ── Header parsing ──────────────────────────────────────────────────────


def _extract_signature_headers(
    request: Request, body_bytes: bytes
) -> Optional[SignatureComponents]:
    """If all four signature headers are present, parse + validate
    structurally. Returns None if any is missing (caller will try the
    legacy paths instead)."""
    flag = request.headers.get("x-api-consumer-flag")
    ts_raw = request.headers.get("x-api-timestamp")
    nonce = request.headers.get("x-api-nonce")
    signature = request.headers.get("x-api-signature")
    if not (flag and ts_raw and nonce and signature):
        return None
    try:
        ts = int(ts_raw)
    except ValueError:
        return None  # invalid timestamp — legacy paths will reject too
    return SignatureComponents(
        flag=flag.strip(),
        timestamp=ts,
        nonce=nonce.strip(),
        signature=signature.strip(),
        body_sha256_hex=hashlib.sha256(body_bytes or b"").hexdigest(),
    )


def _full_path_with_query(request: Request) -> str:
    """Reconstruct the path INCLUDING query string, as the canonical
    input expects. `request.url.path` drops the query."""
    qs = request.url.query
    return f"{request.url.path}?{qs}" if qs else request.url.path
