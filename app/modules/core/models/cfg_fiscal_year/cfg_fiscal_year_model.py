
from datetime import datetime
from typing import Optional
import uuid
from pydantic import Field
from beanie import PydanticObjectId

from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class CfgFiscalYearModel(BaseDocument):
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
        description="Unique identifier",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    label: str = Field(
        ...,
        description="Fiscal Year Label",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    start_date: datetime = Field(
        ...,
        description="Start Date",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    end_date: datetime = Field(
        ...,
        description="End Date",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    number_of_months: int = Field(
        default=0,
        description="Number of months",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True})
    )

    sys_organization_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="System organization ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True
            }
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "label": "Libellé",
            "start_date": "Date de début",
            "end_date": "Date de fin",
            "number_of_months": "Nombre de mois",
            "sys_organization_id": "Organisation système",
        },
        en={
            "label": "Label",
            "start_date": "Start Date",
            "end_date": "End Date",
            "number_of_months": "Number of Months",
            "sys_organization_id": "System Organization",
        },
        ln={
            "label": "Nkombo",
            "start_date": "Mokolo ya kobanda",
            "end_date": "Mokolo ya kosuka",
            "number_of_months": "Motango ya sanza",
            "sys_organization_id": "Organisation ya système",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_FISCAL_YEAR.model_name}"
        validate_on_save = True
