
from datetime import datetime, timezone
from typing import Optional
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
 
class CfgUserMfaModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    secret: Optional[str] = Field(
        default=None,
        description="The secret TOTP of the MFA method.",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    
    is_configured: bool = Field(
        default=False,
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )

    is_disabled: bool = Field(
        default=False,
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )
 
    mfa_configuration_next_setup_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True})
    )
    
    sys_user_id:PydanticObjectId = Field(
        ...,
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    ref_mfa_id:PydanticObjectId = Field(
        ...,
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
      

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "secret": "Clé secrète TOTP",
            "is_configured": "Est configuré",
            "is_disabled": "Est désactivé",
            "mfa_configuration_next_setup_at": "Prochaine configuration MFA",
            "sys_user_id": "Utilisateur système",
            "ref_mfa_id": "Méthode MFA",
        },
        en={
            "secret": "TOTP Secret Key",
            "is_configured": "Is Configured",
            "is_disabled": "Is Disabled",
            "mfa_configuration_next_setup_at": "Next MFA Setup Date",
            "sys_user_id": "System User",
            "ref_mfa_id": "MFA Method",
        },
        ln={
            "secret": "Fungola ya nkuku TOTP",
            "is_configured": "Ebongisami",
            "is_disabled": "Elongwá",
            "mfa_configuration_next_setup_at": "Mokolo ya kobongisa MFA ya nsima",
            "sys_user_id": "Mosaleli ya système",
            "ref_mfa_id": "Lolenge ya MFA",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_USER_MFA.model_name}"
        validate_on_save = True 
