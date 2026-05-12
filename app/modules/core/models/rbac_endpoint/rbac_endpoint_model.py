
from typing import List, Optional
import uuid
from pydantic import Field, model_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.schemas.rbac_schema import EndpointRestrictedPlatformInfo, EndpointRestrictedProfilInfo

from app.modules.core.enums.type_enum import AppGeneratorType, EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from beanie import PydanticObjectId
import re

class RbacEndpointModel(BaseDocument):
    """
    This collection defines RBAC endpoints for managing permissions at the endpoint level.
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
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN.value}": "permissionTargets,refCollectionCrudInfos"
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the endpoint",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    )

    url: Optional[str] = Field(
        ...,
        description="URL of the endpoint (e.g., /api/users)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True,
                f"{EGLOBAL_EXTRA_METAS.UPSERT_IF_EXIST_WITH_PROPS.value}": "url"
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
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.RBAC_TITLE.value}",
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    )

    label: str = Field(
        ...,
        description="Label of the endpoint, if targeted_id is given, name can correspond to module,or app name [eg: cores, users]",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    )

    is_leaf: Optional[bool] = Field(
        default=False,
        description="Indicates if the endpoint is not just a title or has url",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True
            }
        )
    )

    is_primary: Optional[bool] = Field(
        default=False,
        description="Indicates if the endpoint is the one where can be applied sudo, or sudo group validation",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    )
    is_sudo_action: Optional[bool] = Field(
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

    is_sudo_group_action: Optional[bool] = Field(
        default=False,
        description="if true Indicates  that this endpoints requires OTP validation by multiple accounts (true: requires multiple OTP validations)",
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

    is_sudo_group_cross_validation_action: Optional[bool] = Field(
        default=False,
        description="if true Indicates  that this endpoints requires OTP validation by multiple accounts (true: requires multiple OTP validations)",
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
    
    is_sudo_group_inter_organization_validation_action: Optional[bool] = Field(
        default=False,
        description="if true Indicates  that this endpoints requires OTP validation by multiple accounts (true: requires multiple OTP validations)",
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
        default="aucune description fournie",
        description="Plain-text description of the endpoint",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    )

    description_html: Optional[str] = Field(
        default="<p>aucune description fournie</p>",
        description="HTML-formatted description of the endpoint",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True}
        )
    )

    flag: str = Field(
        default_factory=None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    )

    @staticmethod
    def generate_flag(name: str):
        """
        Generate the 'flag' field if not provided.
        """
        sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
        gen_flag = f"{sanitized_name}_{len(name)}"
        return gen_flag

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
            "url": "URL",
            "rbac_title_id": "ID titre RBAC",
            "label": "Libellé",
            "is_leaf": "Est une feuille",
            "is_primary": "Est primaire",
            "is_sudo_action": "Action sudo",
            "is_sudo_delegated_action": "Action sudo déléguée",
            "is_available_for_rls": "Disponible pour RLS",
            "is_sudo_group_action": "Action sudo de groupe",
            "is_sudo_group_cross_validation_action": "Action sudo validation croisée de groupe",
            "is_sudo_group_inter_organization_validation_action": "Action sudo validation inter-organisation",
            "description_str": "Description",
            "description_html": "Description HTML",
        },
        en={
            "url": "URL",
            "rbac_title_id": "RBAC Title ID",
            "label": "Label",
            "is_leaf": "Is Leaf",
            "is_primary": "Is Primary",
            "is_sudo_action": "Sudo Action",
            "is_sudo_delegated_action": "Sudo Delegated Action",
            "is_available_for_rls": "Available for RLS",
            "is_sudo_group_action": "Sudo Group Action",
            "is_sudo_group_cross_validation_action": "Sudo Group Cross Validation Action",
            "is_sudo_group_inter_organization_validation_action": "Sudo Group Inter-Organization Validation Action",
            "description_str": "Description",
            "description_html": "HTML Description",
        },
        ln={
            "url": "URL",
            "rbac_title_id": "ID ya titre RBAC",
            "label": "Nkombo",
            "is_leaf": "Ezali nkasa",
            "is_primary": "Ezali ya liboso",
            "is_sudo_action": "Action sudo",
            "is_sudo_delegated_action": "Action sudo ya kopesa",
            "is_available_for_rls": "Ezali mpo na RLS",
            "is_sudo_group_action": "Action sudo ya lisanga",
            "is_sudo_group_cross_validation_action": "Action sudo ya vérification croisée ya lisanga",
            "is_sudo_group_inter_organization_validation_action": "Action sudo ya vérification entre ba organisations",
            "description_str": "Ndimbola",
            "description_html": "Ndimbola HTML",
        },
    )

    class Settings:
        name = f"{CollectionKey.RBAC_ENDPOINT.model_name}"
        validate_on_save = True
