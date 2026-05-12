"""CfgStorageModel — per-organization storage + KMS configuration.

One row per `sys_organization_id`. Currently used by:

  - `VoteCryptoService` (F10): `kms_master_key_id` resolves the master key
    used to seal per-resolution DEKs for secret votes. When the row is
    absent or the field is null, the service falls back to the global
    `settings.ENCRYPTION_KEY` env var — single-tenant deployments stay
    zero-config.

Future fields (post-MVP, see `_planning/_followup_batch.md`):

  - `storage_adapter_kind` (LOCAL | MINIO | S3) for F6
  - `signed_url_ttl_seconds` per-tenant override for F5
  - `audit_chain_emit_lock_ttl_seconds` for F9 tuning

Per CLAUDE.md: per-tenant config lives in `Cfg*` models keyed by
`sys_organization_id`. No env vars, no global flags for tenant-scoped
behavior. F10 honours that contract.
"""

import uuid
from typing import Annotated, Any, Dict, Optional

from beanie import Indexed, PydanticObjectId
from pydantic import Field

from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper


class CfgStorageModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    sys_organization_id: Annotated[
        PydanticObjectId,
        Indexed(name="cfg_storage_org_index", unique=True),
        Field(
            ...,
            description="One CfgStorage row per organisation. Unique-indexed.",
        ),
    ]

    kms_master_key_id: Optional[str] = Field(
        default=None,
        max_length=200,
        description=(
            "Identifier the `KmsResolverService` uses to look up the master "
            "key for this org. Concrete resolution is adapter-dependent: "
            "MVP env-var adapter expects `KMS_MASTER_KEY_<id>` in the env. "
            "When null, secret-vote crypto falls back to the global "
            "`settings.ENCRYPTION_KEY`."
        ),
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    notes_str: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Free-form admin notes (e.g. 'Rotated 2026-04-29').",
    )

    async def get_formated_data(
        self,
        accept_language: str = "fr",
        output: FormatedOutPut = FormatedOutPut.MINIMAL,
    ) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "identifier": self.identifier,
            "sys_organization_id": str(self.sys_organization_id),
            "kms_master_key_id": self.kms_master_key_id,
            "notes_str": self.notes_str,
        }

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "sys_organization_id": "Organisation",
            "kms_master_key_id": "ID clé maître KMS",
            "notes_str": "Notes",
        },
        en={
            "sys_organization_id": "Organization",
            "kms_master_key_id": "KMS master key ID",
            "notes_str": "Notes",
        },
        ln={
            "sys_organization_id": "Organisasyo",
            "kms_master_key_id": "ID ya fungola KMS",
            "notes_str": "Banoti",
        },
    )

    class Settings:
        name = CollectionKey.CFG_STORAGE.model_name
        validate_on_save = True
