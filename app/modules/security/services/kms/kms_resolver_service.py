"""KmsResolverService — resolves per-organization master keys for envelope crypto.

Per `_planning/_followup_batch.md` F10. Two-tier resolution:

  1. Look up `CfgStorageModel` for the org. If a row exists with
     `kms_master_key_id`, ask the active adapter to materialise the key.
  2. If no row, no `kms_master_key_id`, or adapter resolution fails →
     fall back to the global `settings.ENCRYPTION_KEY`. Single-tenant
     deployments stay zero-config.

Adapter pluggability:
  - `EnvVarAdapter` (MVP, default): looks up `KMS_MASTER_KEY_<id>` in os.environ.
    Forward-shaped — production sysadmins inject the actual KMS key bytes
    via env var, then rotate by issuing a new env var + a new
    `kms_master_key_id` value on the cfg row.
  - Future adapters (`AwsKmsAdapter`, `VaultAdapter`, `HsmAdapter`) plug
    in by implementing `resolve(kms_master_key_id) -> bytes`. Selection
    is env-var-controlled (`KMS_ADAPTER=env|aws|vault|hsm`).

The resolved master key is what `VoteCryptoService` wraps with `Fernet()`
to seal/unseal per-resolution DEKs. Format must be a Fernet key (32-byte
url-safe base64) — the legacy `ENCRYPTION_KEY` env var follows that
shape, and adapters are expected to produce the same shape.
"""

from __future__ import annotations

import os
from typing import Optional

from beanie import PydanticObjectId

from app.modules.core.configs.config import settings
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.security.models.cfg_storage.cfg_storage_model import CfgStorageModel


class KmsResolverService:
    """Stateless per-call resolver. Use `KmsResolverService.resolve_for_org(org_id)`."""

    @staticmethod
    async def resolve_for_org(
        sys_organization_id: Optional[str | PydanticObjectId] = None,
    ) -> bytes:
        """Return the master key bytes for the given org, falling back to
        `settings.ENCRYPTION_KEY` when no per-org config exists.

        Pure resolver — never raises on a missing per-org row; only raises
        if BOTH the per-org lookup AND the global fallback are
        unavailable, since that's an unrecoverable misconfiguration.
        """
        # 1. Try per-org cfg row.
        if sys_organization_id is not None:
            try:
                org_oid = (
                    sys_organization_id
                    if isinstance(sys_organization_id, PydanticObjectId)
                    else PydanticObjectId(sys_organization_id)
                )
                cfg = await CfgStorageModel.find_one(
                    CfgStorageModel.sys_organization_id == org_oid
                )
                if cfg is not None and cfg.kms_master_key_id:
                    key = _resolve_via_adapter(cfg.kms_master_key_id)
                    if key:
                        return key
                    DebugService.app_debug_print(
                        f"[KmsResolverService] kms_master_key_id={cfg.kms_master_key_id!r} "
                        f"set on org {org_oid} but adapter returned no key — falling back "
                        f"to settings.ENCRYPTION_KEY",
                        True,
                    )
            except Exception as exc:
                # Lookup failed (DB outage, malformed id, etc.) → fall through
                # to the global key. Logged so an operator can investigate.
                DebugService.app_debug_print(
                    f"[KmsResolverService] per-org KMS lookup failed: {exc} — "
                    f"falling back to settings.ENCRYPTION_KEY",
                    True,
                )

        # 2. Global fallback.
        raw = getattr(settings, "ENCRYPTION_KEY", None)
        if not raw:
            raise RuntimeError(
                "Aucune clé maître KMS disponible: ni CfgStorageModel pour "
                "l'organisation, ni settings.ENCRYPTION_KEY. Crypto secret-vote "
                "inopérant."
            )
        return raw.encode("utf-8") if isinstance(raw, str) else raw


def _resolve_via_adapter(kms_master_key_id: str) -> Optional[bytes]:
    """Invoke the configured adapter. Returns None when the adapter
    cannot produce a key (so the caller falls back to the global env var)."""
    adapter_kind = (getattr(settings, "KMS_ADAPTER", None) or "env").strip().lower()
    if adapter_kind in ("env", "envvar", "env-var"):
        return _env_var_adapter(kms_master_key_id)
    # Future adapters land here as elif branches:
    #   if adapter_kind == "aws": return _aws_kms_adapter(kms_master_key_id)
    #   if adapter_kind == "vault": return _vault_adapter(kms_master_key_id)
    DebugService.app_debug_print(
        f"[KmsResolverService] Unknown KMS_ADAPTER={adapter_kind!r} — "
        f"only 'env' is implemented at MVP.",
        True,
    )
    return None


def _env_var_adapter(kms_master_key_id: str) -> Optional[bytes]:
    """Look up `KMS_MASTER_KEY_<id>` in process env. Lowercased + stripped
    for hyphens to keep env-var names POSIX-friendly."""
    safe_id = "".join(c if c.isalnum() else "_" for c in kms_master_key_id).upper()
    env_name = f"KMS_MASTER_KEY_{safe_id}"
    raw = os.environ.get(env_name)
    if not raw:
        DebugService.app_debug_print(
            f"[KmsResolverService] env var {env_name!r} not set — "
            f"falling back",
            False,
        )
        return None
    return raw.encode("utf-8")
