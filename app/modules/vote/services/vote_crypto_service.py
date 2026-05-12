"""VoteCryptoService — secret-vote envelope encryption.

Implements the hard PPTX requirement (slide 15):
  *"Votes secrets : il est impossible de remonter jusqu'au votant et de l'enregistrer."*

Per-resolution model (memory: senat_pptx_requirements §4):

  - When a `VoteConfigModel` is created with `is_secret=True`, the service
    generates a fresh **Data Encryption Key** (DEK, 32 bytes Fernet key) and
    seals it with the org-level master key. Per `_planning/_followup_batch.md`
    F10, the master key is resolved via `KmsResolverService.resolve_for_org`
    — per-org `CfgStorageModel.kms_master_key_id` when configured, falling
    back to the global `settings.ENCRYPTION_KEY` for single-tenant deploys.
    The sealed DEK is stored on `VoteConfigModel.sealed_dek_b64`.
  - When a sénateur casts a ballot on a secret scrutin, `voter_user_id` is
    encrypted with the DEK and stored in `VoteBallotModel.voter_user_id_enc`.
    The plaintext `voter_user_id` field is left null.
  - For tally, the DEK is unsealed once and used to decrypt every ballot's
    voter_user_id IN MEMORY ONLY — the count is aggregated into
    `VoteResultModel`. Per-voter mappings never surface in any HTTP response.

Public votes (`is_secret=False`) skip all of this — `voter_user_id` is
stored in clear and surfaces normally in detail/result endpoints.

The DEK never leaves this service. Even greffier-side endpoints that read
`VoteConfigModel` MUST go through `redacted_config_payload()` to strip
`sealed_dek_b64` from any response.

Construction:
  - `VoteCryptoService(accept_language)` — no crypto (`redacted_config_payload`
    only). Constructing eagerly with no master key is intentional so endpoints
    that only need redaction don't pay the per-org KMS lookup cost.
  - `await VoteCryptoService.for_org(sys_organization_id, accept_language)` —
    full crypto. Use this from `VoteService.create / change_type_live` and
    every `BallotService` path that touches `seal_dek` / `unseal_dek`.

Sealed DEKs are organisation-scoped: a key sealed with org A's master key
cannot be unsealed by org B's. Cross-org tally attempts therefore fail
with `ValueError("Sceau de DEK invalide ou altéré")` — by construction.
"""

from __future__ import annotations

import base64
from typing import Any, Optional

from beanie import PydanticObjectId
from cryptography.fernet import Fernet, InvalidToken

from app.modules.core.configs.config import settings


def _global_master_key() -> bytes:
    """Synchronous fallback for callers that don't have an org context yet
    (unit tests, eager redact-only constructors). Always reads the global
    `settings.ENCRYPTION_KEY` — never the per-org cfg row.

    `for_org()` is the supported path for production code.
    """
    raw: Optional[str] = getattr(settings, "ENCRYPTION_KEY", None)
    if not raw:
        raise RuntimeError(
            "ENCRYPTION_KEY non configurée — secret-vote crypto inopérant."
        )
    return raw.encode("utf-8") if isinstance(raw, str) else raw


class VoteCryptoService:
    REDACTED_FIELDS = ("sealed_dek_b64",)

    def __init__(
        self,
        accept_language: str = "fr",
        master_key_bytes: Optional[bytes] = None,
    ):
        """Build a service instance.

        Pass `master_key_bytes` to bind to a specific resolved master key
        (for callers that already resolved per-org via `for_org`). Leave
        as None to fall back to the global `settings.ENCRYPTION_KEY` —
        appropriate for `redacted_config_payload`-only call sites.
        """
        self.accept_language = accept_language
        self._master = Fernet(master_key_bytes if master_key_bytes is not None else _global_master_key())

    @classmethod
    async def for_org(
        cls,
        sys_organization_id: str | PydanticObjectId,
        accept_language: str = "fr",
    ) -> "VoteCryptoService":
        """Resolve the per-org master key (with global fallback) and bind a
        fresh service instance to it.

        Use this from every code path that calls `seal_dek`, `unseal_dek`,
        `encrypt_voter_id`, or `decrypt_voter_id`. Idempotent — safe to call
        repeatedly per request.
        """
        # Late import to avoid a circular dependency at startup
        # (security.services depends on security.models depends on core
        # which itself loads vote crypto for the seed-time class registry).
        from app.modules.security.services.kms.kms_resolver_service import (
            KmsResolverService,
        )

        master_key = await KmsResolverService.resolve_for_org(sys_organization_id)
        return cls(accept_language=accept_language, master_key_bytes=master_key)

    # ---- DEK lifecycle ----
    def generate_dek(self) -> bytes:
        """Fresh per-resolution DEK (32 bytes, Fernet-formatted)."""
        return Fernet.generate_key()

    def seal_dek(self, dek: bytes) -> str:
        """Wrap the DEK with the master key. Output is base64 — store in MongoDB."""
        sealed = self._master.encrypt(dek)
        return base64.urlsafe_b64encode(sealed).decode("ascii")

    def unseal_dek(self, sealed_b64: str) -> bytes:
        """Reverse of `seal_dek`. Raises ValueError if the seal is tampered."""
        try:
            sealed = base64.urlsafe_b64decode(sealed_b64.encode("ascii"))
            return self._master.decrypt(sealed)
        except (InvalidToken, ValueError) as exc:
            raise ValueError("Sceau de DEK invalide ou altéré.") from exc

    # ---- voter_user_id encryption ----
    def encrypt_voter_id(self, dek: bytes, voter_user_id: str) -> str:
        """Encrypt a voter id with the resolution DEK. Output base64."""
        f = Fernet(dek)
        return f.encrypt(voter_user_id.encode("utf-8")).decode("ascii")

    def decrypt_voter_id(self, dek: bytes, ciphertext: str) -> str:
        """Decrypt a voter id. Used IN MEMORY for tally only — never in API responses."""
        f = Fernet(dek)
        try:
            return f.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Bulletin chiffré altéré ou DEK incorrect.") from exc

    # ---- payload redaction ----
    def redacted_config_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Strip every secret-vote internal from a config payload before returning to a caller.

        Use this on EVERY VoteConfig response. Defence in depth: even if a
        future endpoint accidentally returns the raw model dict, the wrapper
        scrubs the sealed key.
        """
        redacted = dict(payload)
        for field in self.REDACTED_FIELDS:
            if field in redacted:
                redacted[field] = "<REDACTED:sealed_dek>"
        return redacted

    # ---- self-check ----
    def self_test(self) -> bool:
        """Round-trip a DEK + a voter id. Used by health-check endpoints in v1.1."""
        try:
            dek = self.generate_dek()
            sealed = self.seal_dek(dek)
            unsealed = self.unseal_dek(sealed)
            assert unsealed == dek
            ciphertext = self.encrypt_voter_id(dek, "00000000-0000-0000-0000-000000000001")
            plaintext = self.decrypt_voter_id(dek, ciphertext)
            return plaintext == "00000000-0000-0000-0000-000000000001"
        except Exception:
            return False
