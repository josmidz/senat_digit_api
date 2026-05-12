"""HMAC-SHA256 request signing for the API consumer surface.

Threat model + design rationale: see `_planning/_consumer_signing.md`
(short version inline here).

Why we sign at all:
    Distinguishing client identity from `consumer_flag` alone is a stable
    public ID — useful for RBAC scoping but offers no integrity. With a
    shared secret + HMAC over the request, we add:
      • Body integrity (catches tampering past TLS termination at any
        upstream proxy / CDN / sidecar).
      • Time-bounded replay protection (timestamp window).
      • Per-request unforgeability without the shared secret.

What this is NOT:
    The shared secret IS recoverable from a reverse-engineered mobile
    binary. That's a fundamental limit of any client-side credential.
    Phase 2 layers Play Integrity / App Attest on top to attest the app
    instance itself, but this module remains the single point of HMAC
    validation regardless.

Signature input string (canonical, verbatim newlines):

    {flag}\\n{ts}\\n{nonce}\\n{method}\\n{path}\\n{body_sha256_hex}

Each component:
    flag             — consumer flag (e.g. "senat_digit_mobile")
    ts               — Unix epoch seconds, decimal string
    nonce            — base64url(16 random bytes), no padding
    method           — uppercase HTTP verb ("POST", "GET", ...)
    path             — request URL path INCLUDING query string
                       (e.g. "/api/v1/list/document?typology=RESOLUTION")
    body_sha256_hex  — sha256 of the raw request body, hex.
                       Empty body → sha256(b"") still hashed (so GET also
                       commits to a hash; client + server agree).

Then:
    signature = HMAC-SHA256(consumer_secret_bytes, input_string).hex()

Headers expected:
    X-Api-Consumer-Flag : senat_digit_mobile
    X-Api-Timestamp     : 1735680000
    X-Api-Nonce         : a1b2c3...
    X-Api-Signature     : 5fed8d0e...

The middleware validates in this order:
    1. All four headers present                 → else: missing-header 401
    2. Timestamp parses + within ±MAX_SKEW      → else: stale 401
    3. Flag resolves to a consumer with a
       non-empty consumer_secret                → else: unknown-consumer 401
    4. Recomputed signature matches             → else: bad-signature 401
       (constant-time compare)
    5. (Phase 2) Nonce not seen in Redis        → else: replay 401
       (SETNX with TTL = MAX_SKEW * 2)

The verification is `await`-able for symmetry with future Redis nonce
checks, even though Phase 1 logic is purely CPU-bound.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SignatureComponents:
    """Decoded signature headers + computed body hash."""
    flag: str
    timestamp: int
    nonce: str
    signature: str
    body_sha256_hex: str


@dataclass(frozen=True)
class SignatureVerificationResult:
    """Outcome of `verify_request_signature`. `ok=True` is the only
    success state; otherwise `reason` carries a short machine-readable
    code suitable for telemetry (`stale`, `bad_signature`, …)."""
    ok: bool
    reason: Optional[str] = None


class SignatureService:
    """Stateless helpers — `verify_request_signature` is the entry point
    used by the middleware; `compute_signature` is provided for tests +
    potential server-to-server signing (e.g. fs api callbacks).
    """

    SIG_INPUT_SEPARATOR = "\n"

    # ── public API ───────────────────────────────────────────────────────

    @classmethod
    def compute_signature(
        cls,
        *,
        consumer_secret: str,
        flag: str,
        timestamp: int,
        nonce: str,
        method: str,
        path: str,
        body: bytes,
    ) -> str:
        """Pure HMAC computation. Returns lowercase hex digest."""
        body_sha256_hex = hashlib.sha256(body or b"").hexdigest()
        canonical = cls._canonical_input(
            flag=flag,
            timestamp=timestamp,
            nonce=nonce,
            method=method,
            path=path,
            body_sha256_hex=body_sha256_hex,
        )
        digest = hmac.new(
            key=consumer_secret.encode("utf-8"),
            msg=canonical.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return digest

    @classmethod
    async def verify_request_signature(
        cls,
        *,
        consumer_secret: str,
        components: SignatureComponents,
        method: str,
        path: str,
        max_skew_seconds: int,
        now_epoch: Optional[int] = None,
    ) -> SignatureVerificationResult:
        """Validate timestamp window + recomputed signature.

        Phase 1 only: nonce uniqueness against Redis is a Phase 2 add
        (`Redis SETNX` with TTL = `max_skew_seconds * 2`). Phase 1 just
        ensures the nonce is non-empty so clients are forward-compatible.
        """
        # 1. Nonce non-empty (forward-compat with Phase 2 dedup).
        if not components.nonce:
            return SignatureVerificationResult(ok=False, reason="missing_nonce")

        # 2. Timestamp window.
        now = now_epoch if now_epoch is not None else int(time.time())
        skew = abs(now - components.timestamp)
        if skew > max_skew_seconds:
            return SignatureVerificationResult(ok=False, reason="stale")

        # 3. Signature.
        canonical = cls._canonical_input(
            flag=components.flag,
            timestamp=components.timestamp,
            nonce=components.nonce,
            method=method,
            path=path,
            body_sha256_hex=components.body_sha256_hex,
        )
        expected = hmac.new(
            key=consumer_secret.encode("utf-8"),
            msg=canonical.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, components.signature.lower()):
            return SignatureVerificationResult(ok=False, reason="bad_signature")

        return SignatureVerificationResult(ok=True)

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def generate_consumer_secret() -> str:
        """Return a cryptographically-random 256-bit secret as 64 hex chars."""
        return secrets.token_hex(32)

    @classmethod
    def _canonical_input(
        cls,
        *,
        flag: str,
        timestamp: int,
        nonce: str,
        method: str,
        path: str,
        body_sha256_hex: str,
    ) -> str:
        """Build the canonical signing string. Stable: do NOT change
        ordering, separators, or casing without bumping a version header
        — every signed client must agree byte-for-byte."""
        return cls.SIG_INPUT_SEPARATOR.join([
            flag,
            str(timestamp),
            nonce,
            method.upper(),
            path,
            body_sha256_hex,
        ])
