from typing import Optional
import uuid
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

class CfgSudoActionSetupModel(BaseDocument):
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
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    is_enabled: bool = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
    
    sys_organization_id: PydanticObjectId = Field(
        ...,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    ) 

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "is_enabled": "Est activé",
            "sys_organization_id": "ID organisation",
        },
        en={
            "is_enabled": "Is Enabled",
            "sys_organization_id": "Organization ID",
        },
        ln={
            "is_enabled": "Esili ko activer",
            "sys_organization_id": "ID ya organisation",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_SUDO_ACTION_SETUP.model_name}"
        validate_on_save = True


    async def get_formated_data(self,lang:str="fr",output: FormatedOutPut = FormatedOutPut.MINIMAL) -> dict:
        return {
            "id":str(self.id),
            "identifier":self.identifier,
            "is_enabled":self.is_enabled,
        }





