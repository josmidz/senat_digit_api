
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_EXTRA_METAS, FormatedOutPut

from pydantic import Field
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from typing import Annotated, List, Optional

from app.modules.core.utils.helpers.line_helper import format_exception

class CfgSystemTownEntityModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True,
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the document",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
 

    ref_entity_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Entity",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_ENTITY.value}",
                f"{EGLOBAL_EXTRA_METAS.UPSERT_IF_EXIST_WITH_PROPS.value}":"ref_entity_id",
            }
        )
    )
  

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "ref_entity_id": "Entité de référence",
        },
        en={
            "ref_entity_id": "Reference Entity",
        },
        ln={
            "ref_entity_id": "Entité ya référence",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_SYSTEM_TOWN_ENTITY.model_name}"
        indexes = [
            "ref_entity_id",
        ]
        validate_on_save = True

    async def get_formated_data(self,accept_language:str = 'fr',output:FormatedOutPut = FormatedOutPut.FULL) -> dict:
        from app.modules.core.models.ref_entity.ref_entity_model import RefEntityModel
        try:
            ref_entity = await RefEntityModel.get(self.ref_entity_id)
            ref_country_entity = None
            ref_province_entity = None
            if ref_entity:
                ref_entity = await ref_entity.get_formated_data(accept_language,FormatedOutPut.MINIMAL)
                if ref_entity:
                    ref_province_entity = await RefEntityModel.get(ref_entity['ref_entity_id'])
                    if ref_province_entity:
                        ref_province_entity = await ref_province_entity.get_formated_data(accept_language,FormatedOutPut.MINIMAL)
                        if ref_province_entity:
                            ref_country_entity = await RefEntityModel.get(ref_province_entity['ref_entity_id'])
                            if ref_country_entity:
                                ref_country_entity = await ref_country_entity.get_formated_data(accept_language,FormatedOutPut.MINIMAL)
            return {
                "id":str(self.id),
                "identifier":self.identifier,
                "ref_entity_id":str(self.ref_entity_id),
                "ref_entity":ref_entity,
                "ref_province_entity":ref_province_entity,
                "ref_country_entity":ref_country_entity,
            }
        except Exception as e:
            format_error = format_exception("Error in get_formated_data", e)
            print(f"Error in get_formated_data > cfg_system_town_entity_model: {format_error}")
            return {
                "id":str(self.id),
                "identifier":self.identifier,
                "ref_entity_id":str(self.ref_entity_id),
            }
    
 
