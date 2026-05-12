
from typing import Annotated, Dict, Optional
import uuid
from beanie import PydanticObjectId
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

from app.modules.core.utils.model.base_document import BaseDocument
import re
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class CfgOrganismChartModel(BaseDocument):
    """
    This collection defines data.
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
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the organism chart",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}":True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}":True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}":3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}":255,
            },
        )
    )

    description_str: Optional[str] = Field(
        default="aucune description fournie",
        description="Descriptive note in plain text",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}":True,
            },
        )
    )

    cfg_organism_chart_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Reference to another related own",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_CASCADE.value}": True
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.CFG_ORGANISM_CHART.value}",
            },
        )
    )
    sys_organization_id: Annotated[
        Optional[PydanticObjectId],
        Field(
            default=None,
            description="System organization ID",
            json_schema_extra=translation_meta(
                may_have_translation=False,
                to_be_translated_in_front=False,
                data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True}
            )
        )
    ]

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "description_str": "Description",
            "cfg_organism_chart_id": "Organigramme parent",
            "sys_organization_id": "Organisation système",
        },
        en={
            "name": "Name",
            "description_str": "Description",
            "cfg_organism_chart_id": "Parent Organism Chart",
            "sys_organization_id": "System Organization",
        },
        ln={
            "name": "Nkombo",
            "description_str": "Ndimbola",
            "cfg_organism_chart_id": "Organigramme ya likolo",
            "sys_organization_id": "Organisation ya système",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_ORGANISM_CHART.model_name}"
        validate_on_save = True
 
