"""BlobProxyService — produces a short-lived signed URL pointing at senat_digit_fs_api.

Per `_planning/_followup_batch.md` F13, the signed URL is now a JWS Compact
Serialization token (RFC 7515) carried in `?token=<jws>` on the URL. The
JWS payload is `{"file_str_id": <str>, "exp": <unix_seconds>, "iat": ...,
"iss": "senat_digit_api"}` signed HS256 with `JWT_SECRET_KEY`.

Why JWS over the previous HMAC-SHA256-in-`?sig=`:
  - Standardised wire format the fs side can validate with any
    `python-jose` / `jose-jwt` / Node `jose` library — no custom HMAC code.
  - Algorithm + key id live IN the token header, so future rotation
    (HS256 → RS256, key1 → key2) is just a header change and a JWK
    publish — callers don't need to know.
  - `exp` is a structurally-validated claim (jose lib raises on expired)
    rather than an integer query param the verifier has to remember to
    enforce.

When F5 lands on fs:
  - this service keeps emitting `?token=<jws>` URLs unchanged
  - fs's `signed_url_service` decodes the JWS, validates `exp` and `iss`,
    rejects expired/tampered tokens with 401
  - the existing /view-file endpoint stays the canonical reader

The previous HMAC `?exp=&sig=` shape is **not** kept for back-compat —
no production deployment has run yet, and Flutter's `SignedBlobUrl.fromJson`
treats the URL as opaque (passes it through to syncfusion or Dio), so
the shape change is invisible to the only live consumer.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from jose import jwt

from app.modules.core.configs.config import settings
from app.modules.document.models.document_meta.document_meta_model import DocumentMetaModel


# Default short TTL for blob URLs. Configurable per-tenant in v1.1 via CfgStorageModel.
_DEFAULT_TTL_SECONDS = 300

# JWS algorithm. Symmetric for MVP (single deployment, single shared
# secret). v1.1 may upgrade to RS256 + JWK publish for proper public-key
# verification on fs without sharing the signing key.
_JWS_ALG = "HS256"

# Issuer claim — fs uses this to filter out tokens that wandered in from
# unrelated services sharing the same JWT secret.
_JWS_ISS = "senat_digit_api"


def _mint_jws_token(file_str_id: str, expires_at: int, secret: str) -> str:
    """Encode the signed-URL claims as a JWS Compact Serialization token.

    Claims:
      sub: the fs-side `file_str_id_composed` capability
      exp: unix seconds (RFC 7519 §4.1.4)
      iat: unix seconds (RFC 7519 §4.1.6) — issued-at
      iss: "senat_digit_api" (RFC 7519 §4.1.1)
    """
    now = int(time.time())
    payload: Dict[str, Any] = {
        "sub": file_str_id,
        "exp": int(expires_at),
        "iat": now,
        "iss": _JWS_ISS,
    }
    return jwt.encode(payload, secret, algorithm=_JWS_ALG)


class BlobProxyService:
    def __init__(self, accept_language: str = "fr"):
        self.accept_language = accept_language

    async def signed_url_for_document(
        self,
        document_id: str,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> Dict[str, Any]:
        """Return a signed URL the Flutter client can use to read the blob.

        Raises ValueError if the document has no `arch_file_id` (PV not yet
        generated, attachment not uploaded, etc.).
        """
        oid = document_id if isinstance(document_id, PydanticObjectId) else PydanticObjectId(document_id)
        meta = await DocumentMetaModel.get(oid)
        if meta is None:
            raise ValueError(f"Document introuvable: {document_id}")
        if meta.arch_file_id is None:
            raise ValueError(
                f"Document sans fichier rattaché: {document_id} (téléverser le PDF d'abord)."
            )

        # Resolve the underlying ArchFileModel to get its `file_str_id_composed`.
        # ArchFileModel lives in the edocs module — late import to avoid a
        # cycle at startup if edocs ever depends on document.
        from app.modules.edocs.models.arch_file.arch_file_model import ArchFileModel

        arch_file = await ArchFileModel.get(meta.arch_file_id)
        if arch_file is None:
            raise ValueError(
                f"Métadonnée de fichier introuvable: {meta.arch_file_id}"
            )
        file_str = getattr(arch_file, "file_str_id_composed", None) or str(arch_file.id)

        # `SENAT_DIGIT_APPS_FILE_SYSTEM_URL` convention (verified across every
        # other api consumer of it — `organization_controller.py`,
        # `pv_export_service.py`, `sys_organization_model.py`,
        # `email_template.py`, `static_controller.py`): the env var holds
        # the **fs base including `/api/v1`** (e.g. `http://host:7537/api/v1`).
        # Callers append routes like `/files/upload` or `/static/...` to it.
        fs_base = (
            getattr(settings, "SENAT_DIGIT_APPS_FILE_SYSTEM_URL", None)
            or "http://localhost:7537/api/v1"
        )
        fs_base = fs_base.rstrip("/")

        ttl = max(60, int(ttl_seconds))
        expires_at = int(time.time()) + ttl
        secret: Optional[str] = getattr(settings, "JWT_SECRET_KEY", None) or "dev-only-blob-secret"
        token = _mint_jws_token(
            file_str_id=file_str,
            expires_at=expires_at,
            secret=secret,
        )

        # fs `file_router` is mounted at `/api/v1/files` (see
        # `senat_digit_fs_api/app/main.py`), and the view route inside it
        # is `@router.get("/view-file/{file_str_id_composed}")`. So the
        # full URL is `<fs_base>/files/view-file/<id>` — NOT
        # `<fs_base>/api/v1/view-file/<id>` as the pre-F13 HMAC code had it
        # (that path was a 404; the bug had never been exercised end-to-end).
        signed_url = f"{fs_base}/files/view-file/{file_str}?token={token}"
        return {
            "document_id": str(meta.id),
            "arch_file_id": str(meta.arch_file_id),
            "signed_url": signed_url,
            # `expires_at` kept in the JSON response for clients that want to
            # display "expires in X seconds" without decoding the JWS — the
            # token itself remains the cryptographic source of truth.
            "expires_at": str(expires_at),
        }
