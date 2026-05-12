import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, EUserThemeMode
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from typing import   Optional
 
class CfgUserConfigModel(BaseDocument):
    """
    This collection defines user-specific configurations, including language, theme, and mode preferences.
    """
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
        description="Unique identifier for the user configuration",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    sys_user_id: PydanticObjectId = Field(
        ...,
        description="ID of the system user associated with the configuration",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    ref_language_id: PydanticObjectId = Field(
        ...,
        description="ID of the language preference for the user",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    sys_app_theme_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the application theme selected by the user (if any)",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    dark_mode: bool = Field(
        default=False,
        description="Boolean indicating if dark mode is enabled",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    theme_mode: Optional[EUserThemeMode] = Field(
        default=EUserThemeMode.LIGHT,
        description="User theme mode",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True}
        )
    )

    # DEVICE ALLOWED COUNT
    allowed_device_count: Optional[int] = Field(
        default=1,
        description="Number of devices allowed for the user",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True
            }
        )
    ) 

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "sys_user_id": "Utilisateur système",
            "ref_language_id": "Langue préférée",
            "sys_app_theme_id": "Thème de l'application",
            "dark_mode": "Mode sombre",
            "theme_mode": "Mode du thème",
            "allowed_device_count": "Nombre d'appareils autorisés",
        },
        en={
            "sys_user_id": "System User",
            "ref_language_id": "Preferred Language",
            "sys_app_theme_id": "Application Theme",
            "dark_mode": "Dark Mode",
            "theme_mode": "Theme Mode",
            "allowed_device_count": "Allowed Device Count",
        },
        ln={
            "sys_user_id": "Mosaleli ya système",
            "ref_language_id": "Monoko olingá",
            "sys_app_theme_id": "Thème ya application",
            "dark_mode": "Mode ya molili",
            "theme_mode": "Mode ya thème",
            "allowed_device_count": "Motángo ya ba-appareils endimamá",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_USER_CONFIG.model_name}"
        validate_on_save = True 
