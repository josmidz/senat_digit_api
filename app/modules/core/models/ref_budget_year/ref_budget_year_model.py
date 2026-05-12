
from typing import Optional
import uuid
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class RefBudgetYearModel(BaseDocument):
    """
    This collection defines the budget year.
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
        description="Unique identifier for the budget year",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    year: int = Field(
        ...,
        description="Name of the budget year",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_NUMBER.value}": True}
        )
    )

    order_by: Optional[int] = Field(
        default=0,
        description="Number of the menu display order",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True},
        )
    )

    description_str: Optional[str] = Field(
        default="Aucune description fournie.",
        description="Plain-text description of the period type",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True}
        )
    )

    is_current_year: Optional[bool] = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    last_year_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the associated last year",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            exclude_from_data_table=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_BUDGET_YEAR.value}",
            }
        )
    )

    sys_organization_id: PydanticObjectId = Field(
        default=None,
        description="System organization ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True}
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "year": "Année",
            "order_by": "Ordre d'affichage",
            "description_str": "Description",
            "is_current_year": "Année en cours",
            "last_year_id": "Année précédente",
        },
        en={
            "year": "Year",
            "order_by": "Display Order",
            "description_str": "Description",
            "is_current_year": "Current Year",
            "last_year_id": "Previous Year",
        },
        ln={
            "year": "Mbula",
            "order_by": "Molongo ya kolakisa",
            "description_str": "Ndimbola",
            "is_current_year": "Mbula ya lelo",
            "last_year_id": "Mbula eleki",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_BUDGET_YEAR.model_name}"
        validate_on_save = True
