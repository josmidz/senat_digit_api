
from typing import Optional
import uuid
from app.modules.core.enums.type_enum import EAppGroupFlag, EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field, field_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey

class RefApplicationGroupModel(BaseDocument):
    """
    This collection defines application groups, which categorize different applications.
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
        description="Unique identifier for the application group",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the application group (e.g., Administration, Reporting)",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    flag: EAppGroupFlag = Field(
        ...,
        description="Integer flag used for referencing the application group",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.REJECT_IF_EXIST.value}": True,
            }
        )
    )

    icon: Optional[str] = Field(
        default=None,
        description="Icon for the application group",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    order_by: int = Field(
        default=0,
        description="Number of the application group display order",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True},
        )
    )

    description_str: Optional[str] = Field(
        default=None,
        description="Plain-text description of the application group",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    @field_validator("name")
    def validate_and_lowercase_blood_type(cls, value: str) -> str:
        """
        Validate and convert the application group name to lowercase.
        """
        return value.lower()

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "icon": "Icône",
            "order_by": "Ordre d'affichage",
            "description_str": "Description",
        },
        en={
            "name": "Name",
            "icon": "Icon",
            "order_by": "Display Order",
            "description_str": "Description",
        },
        ln={
            "name": "Nkombo",
            "icon": "Elilingi",
            "order_by": "Molongo ya kolakisa",
            "description_str": "Ndimbola",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_APPLICATION_GROUP.model_name}"
        validate_on_save = True
