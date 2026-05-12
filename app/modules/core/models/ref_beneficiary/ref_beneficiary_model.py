
import uuid
from app.modules.core.schemas.user_schema import OthersInfo
from pydantic import Field
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from typing import Annotated, List, Optional
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class RefBeneficiaryModel(BaseDocument):
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
        description="Unique identifier for the document",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the department",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    description_str: Optional[str] = Field(
        default="aucune description fournie",
        description="Descriptive note in plain text",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True})
    )

    description_html: Optional[str] = Field(
        default="<p>aucune description fournie</p>",
        description="Descriptive note in HTML format",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    sys_organization_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="System organization ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}": True
            }
        )
    )

    others: Optional[List["OthersInfo"]] = Field(
        default=[],
        description="List of dynamic beneficiary others informations",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ARRAY_OF_OBJECT.value}": True}
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "description_str": "Description",
            "description_html": "Description HTML",
            "others": "Autres informations",
        },
        en={
            "name": "Name",
            "description_str": "Description",
            "description_html": "HTML Description",
            "others": "Other Information",
        },
        ln={
            "name": "Nkombo",
            "description_str": "Ndimbola",
            "description_html": "Ndimbola HTML",
            "others": "Bansango mosusu",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_BENEFICIARY.model_name}"
        validate_on_save = True
