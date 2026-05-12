
from typing import Optional
import uuid
from pydantic import Field, model_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
import re

class RbacTitleModel(BaseDocument):
    """
    This collection defines RBAC endpoints or permissions titles.
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
        description="Unique identifier for the endpoint",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    label: str = Field(
        ...,
        description="Label for grouping endpoints and permissions [eg: notifications, users]",
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

    description_str: Optional[str] = Field(
        default="aucune description fournie",
        description="Plain-text description of the endpoint",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True
            }
        )
    )

    rbac_title_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Reference to another related rbac title (optional)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.RBAC_TITLE.value}",
            },
        )
    )

    description_html: Optional[str] = Field(
        default="<p>aucune description fournie</p>",
        description="HTML-formatted description of the endpoint",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    is_default: Optional[bool] = Field(
        default=False,
        description="if default == true, its means it cannot be fetch when creating a custom role, it has to be added automatically Ex=notification,profil,",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    flag: Optional[str] = Field(
        default_factory=None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
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
                exist = RbacTitleModel.find_one({'flag': sanitized_name})
                if exist:
                    values["flag"] = f"{sanitized_name}_{len(name)}_{uuid.uuid4().hex[:8]}"
                else:
                    values["flag"] = f"{sanitized_name}_{len(name)}"
        return values

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "label": "Libellé",
            "description_str": "Description",
            "rbac_title_id": "ID titre RBAC",
            "description_html": "Description HTML",
            "is_default": "Est par défaut",
        },
        en={
            "label": "Label",
            "description_str": "Description",
            "rbac_title_id": "RBAC Title ID",
            "description_html": "HTML Description",
            "is_default": "Is Default",
        },
        ln={
            "label": "Nkombo",
            "description_str": "Ndimbola",
            "rbac_title_id": "ID ya titre RBAC",
            "description_html": "Ndimbola HTML",
            "is_default": "Ezali ya liboso",
        },
    )

    class Settings:
        name = f"{CollectionKey.RBAC_TITLE.model_name}"
        validate_on_save = True
