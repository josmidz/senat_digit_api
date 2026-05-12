
from typing import List, Optional
import uuid
from pydantic import Field, model_validator
import re

from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.schemas.rbac_schema import EndpointRestrictedPlatformInfo, EndpointRestrictedProfilInfo
from beanie import PydanticObjectId
from app.modules.core.enums.type_enum import AppGeneratorType, EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey

class RbacPermissionModel(BaseDocument):
    """
    This collection defines RBAC permissions, grouping permissions within profiles.
    Generic permissions are grouped under the "FULL" or "*" profile.
    """
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN.value}": f"{CollectionKey.RBAC_PERMISSION_TARGET.value},{CollectionKey.RBAC_PERMISSION_ROLE.value}"
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the permission",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    label: str = Field(
        ...,
        description="Label of the permission, if targeted_id is given, name can correspond to module,or app name [eg: cores, users]",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}": True,
            }
        )
    )

    rbac_title_id: PydanticObjectId = Field(
        default=None,
        description="ID of the rbac title",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.RBAC_TITLE.value}",
            }
        )
    )

    is_sudo_delegated_action: Optional[bool] = Field(
        default=False,
        description="if true Indicates the accessing this endpoint  OTP validation (true: requires OTP)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    )

    is_available_for_rls: Optional[bool] = Field(
        default=False,
        description="if true Indicates the accessing this endpoint  OTP validation (true: requires OTP)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    )

    is_sudo_cross_organization_validation_action: Optional[bool] = Field(
        default=False,
        description="if true Indicates the accessing this endpoint  OTP validation (true: requires OTP)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    )
    
    is_sudo_inter_connected_organization_validation_action: Optional[bool] = Field(
        default=False,
        description="if true Indicates the accessing this endpoint  OTP validation (true: requires OTP)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    )

    description_str: Optional[str] = Field(
        default="Aucune description fournie.",
        description="Plain-text description of the permission",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True,
                f"{EGLOBAL_EXTRA_METAS.SECONDARY_DISPLAY_VALUE_ON_INPUT_SELECT.value}": True,
            }
        )
    )

    description_html: Optional[str] = Field(
        default="<p>Aucune description fournie.</p>",
        description="HTML-formatted description of the permission",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            exclude_from_head=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True}
        )
    )

    flag: str = Field(
        ...,
        description="Unique key for hard-coded references",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    is_default: Optional[bool] = Field(
        default=False,
        description="if default == true, its means it cannot be fetch when creating a custom role, it has to be added automatically Ex= loading own notification, reset password,",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    is_sudo_action: Optional[bool] = Field(
        default=False,
        description="if is_sudo_action == true, its required totp validation",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
    is_sudo_group_action: Optional[bool] = Field(
        default=False,
        description="if is_sudo_action == true, its required totp validation of many validators",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
    is_system_sudo_group_action: Optional[bool] = Field(
        default=False,
        description="if is_system_sudo_group_action == true, its required totp validation or many validators from system org even data is submitted by other organizations",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    is_accessible_to_all_profil: Optional[bool] = Field(
        default=False,
        description="Indicates if the permission is accessible to all profil",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )

    menu_accessible_to_all_profil_flag: Optional[str] = Field(
        default=None,
        description="Unique key for hard-coded references",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
    app_accessible_to_all_profil_flag: Optional[str] = Field(
        default=None,
        description="Unique key for hard-coded references",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    action_accessible_to_all_profil_flag: Optional[str] = Field(
        default=None,
        description="Unique key for hard-coded references",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    component_accessible_to_all_profil_flag: Optional[str] = Field(
        default=None,
        description="Unique key for hard-coded references",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    @model_validator(mode='before')
    def generate_flag_if_not_provided(cls, values):
        """
        Custom validator to generate the 'flag' field if not provided.
        """
        if "flag" not in values or not values["flag"]:
            name = values.get("label")
            if name:
                sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
                values["flag"] = f"{sanitized_name}_{len(name)}"
        return values

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "label": "Libellé",
            "rbac_title_id": "ID titre RBAC",
            "is_sudo_delegated_action": "Action sudo déléguée",
            "is_available_for_rls": "Disponible pour RLS",
            "is_sudo_cross_organization_validation_action": "Action sudo validation inter-organisation",
            "is_sudo_inter_connected_organization_validation_action": "Action sudo validation organisation interconnectée",
            "description_str": "Description",
            "description_html": "Description HTML",
            "is_default": "Est par défaut",
            "is_sudo_action": "Action sudo",
            "is_sudo_group_action": "Action sudo de groupe",
            "is_system_sudo_group_action": "Action sudo de groupe système",
            "is_accessible_to_all_profil": "Accessible à tous les profils",
            "menu_accessible_to_all_profil_flag": "Indicateur menu accessible à tous les profils",
            "app_accessible_to_all_profil_flag": "Indicateur application accessible à tous les profils",
            "action_accessible_to_all_profil_flag": "Indicateur action accessible à tous les profils",
            "component_accessible_to_all_profil_flag": "Indicateur composant accessible à tous les profils",
        },
        en={
            "label": "Label",
            "rbac_title_id": "RBAC Title ID",
            "is_sudo_delegated_action": "Sudo Delegated Action",
            "is_available_for_rls": "Available for RLS",
            "is_sudo_cross_organization_validation_action": "Sudo Cross-Organization Validation Action",
            "is_sudo_inter_connected_organization_validation_action": "Sudo Inter-Connected Organization Validation Action",
            "description_str": "Description",
            "description_html": "HTML Description",
            "is_default": "Is Default",
            "is_sudo_action": "Sudo Action",
            "is_sudo_group_action": "Sudo Group Action",
            "is_system_sudo_group_action": "System Sudo Group Action",
            "is_accessible_to_all_profil": "Accessible to All Profiles",
            "menu_accessible_to_all_profil_flag": "Menu Accessible to All Profiles Flag",
            "app_accessible_to_all_profil_flag": "App Accessible to All Profiles Flag",
            "action_accessible_to_all_profil_flag": "Action Accessible to All Profiles Flag",
            "component_accessible_to_all_profil_flag": "Component Accessible to All Profiles Flag",
        },
        ln={
            "label": "Nkombo",
            "rbac_title_id": "ID ya titre RBAC",
            "is_sudo_delegated_action": "Action sudo ya kopesa",
            "is_available_for_rls": "Ezali mpo na RLS",
            "is_sudo_cross_organization_validation_action": "Action sudo ya vérification entre ba organisations",
            "is_sudo_inter_connected_organization_validation_action": "Action sudo ya vérification ya ba organisations oyo ekangami",
            "description_str": "Ndimbola",
            "description_html": "Ndimbola HTML",
            "is_default": "Ezali ya liboso",
            "is_sudo_action": "Action sudo",
            "is_sudo_group_action": "Action sudo ya lisanga",
            "is_system_sudo_group_action": "Action sudo ya lisanga ya système",
            "is_accessible_to_all_profil": "Ekoki kokoma na ba profils nyonso",
            "menu_accessible_to_all_profil_flag": "Elembo ya menu mpo na ba profils nyonso",
            "app_accessible_to_all_profil_flag": "Elembo ya application mpo na ba profils nyonso",
            "action_accessible_to_all_profil_flag": "Elembo ya action mpo na ba profils nyonso",
            "component_accessible_to_all_profil_flag": "Elembo ya composant mpo na ba profils nyonso",
        },
    )

    class Settings:
        name = f"{CollectionKey.RBAC_PERMISSION.model_name}"
        validate_on_save = True
        
        
        