
from typing import List, Optional
import uuid
from pydantic import Field, model_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

from app.modules.core.schemas.rbac_schema import EndpointRestrictedPlatformInfo, EndpointRestrictedProfilInfo
from beanie import PydanticObjectId
from app.modules.core.enums.type_enum import AppGeneratorType, EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
import re

from app.modules.auth.enums.common import ERbacComponentFlag

class RbacComponentModel(BaseDocument):
    """
    This collection defines RBAC Component.
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
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the view component",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    label: str = Field(
        ...,
        description="Label of the component",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True
            }
        )
    )

    rbac_component_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Recursive id",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    targeted_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of application or menu",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
    rbac_permission_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the RBAC permission",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    is_standalone: bool = Field(
        default=False,
        description="Indicates if the menu is standalone (not tied to an application) e.g., admin, notification, profile, config",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    description_str: Optional[str] = Field(
        default="aucune description fournie",
        description="Plain-text description of the endpoint",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True
            }
        )
    )

    description_html: Optional[str] = Field(
        default="<p>aucune description fournie</p>",
        description="HTML-formatted description of the endpoint",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            exclude_from_head=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True}
        )
    )

    hard_code_flag: Optional[str] = Field(
        default='main',
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        )
    )

    flag: Optional[ERbacComponentFlag] = Field(
        default=ERbacComponentFlag.STANDARD_COMPONENT,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        )
    )

    @model_validator(mode='before')
    def generate_flag_if_not_provided(cls, values):
        """
        Custom validator to generate the 'flag' field if not provided.
        """
        if "hard_code_flag" not in values or not values["hard_code_flag"]:
            name = values.get("label")
            if name:
                sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
                values["hard_code_flag"] = f"{sanitized_name}_{len(name)}"
        return values

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "label": "Libellé",
            "rbac_component_id": "ID composant RBAC",
            "targeted_id": "ID cible",
            "rbac_permission_id": "ID permission RBAC",
            "is_standalone": "Est autonome",
            "description_str": "Description",
            "description_html": "Description HTML",
            "hard_code_flag": "Indicateur codé en dur",
        },
        en={
            "label": "Label",
            "rbac_component_id": "RBAC Component ID",
            "targeted_id": "Target ID",
            "rbac_permission_id": "RBAC Permission ID",
            "is_standalone": "Is Standalone",
            "description_str": "Description",
            "description_html": "HTML Description",
            "hard_code_flag": "Hard Code Flag",
        },
        ln={
            "label": "Nkombo",
            "rbac_component_id": "ID ya composant RBAC",
            "targeted_id": "ID ya cible",
            "rbac_permission_id": "ID ya ndingisa RBAC",
            "is_standalone": "Ezali kaka yango moko",
            "description_str": "Ndimbola",
            "description_html": "Ndimbola HTML",
            "hard_code_flag": "Elembo ya code",
        },
    )

    class Settings:
        name = f"{CollectionKey.RBAC_COMPONENT.model_name}"
        validate_on_save = True
