
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field,model_validator
import re
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.enums.type_enum import AppGeneratorType
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from typing import Optional
from app.modules.auth.enums.common import EIconFlag
 
class RefIconModel(BaseDocument):
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
    name: str = Field(
        ...,
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    
    icon: str = Field(
        ...,
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    
    description_str: Optional[str] = Field(
        default=None,
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,"is_nullable":True})
    )
    
    is_default: bool = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=True,
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
    
    flag: EIconFlag = Field(
        default=EIconFlag.STANDARD_SVG,
        description="A flag used for internal coding purposes.",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            data_list=[]
        )
    )  
    
    hard_code_flag: Optional[str] = Field(
        default=None,
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            # auto_generate=True,
            # generator_type=AppGeneratorType.CUSTOM,
            # custom_generator=lambda values: RefIconModel.generate_flag(values.get("name"),values.get("flag")),
        )
    )  
    @model_validator(mode='before')
    def generate_flag_if_not_provided(cls, values):
        """
        Custom validator to generate the 'flag' field if not provided.
        """
        if "flag" not in values or not values["flag"]:
            name = values.get("name")
            if name:
                sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
                values["hard_code_flag"] = f"{sanitized_name}_{len(name)}"
        return values
    @staticmethod
    def generate_flag(name: str,flag:Optional[str]) -> str:
        """
        Custom generator for flag based on the name field.
        """
        if not flag:
            if not name:
                raise ValueError("Label is required to generate flag.")
            sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
            return f"{sanitized_name}_{len(sanitized_name)}"
        else :
            return flag
      
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom de l'icône",
            "icon": "Icône",
            "description_str": "Description",
            "is_default": "Par défaut",
            "hard_code_flag": "Code interne",
        },
        en={
            "name": "Icon Name",
            "icon": "Icon",
            "description_str": "Description",
            "is_default": "Default",
            "hard_code_flag": "Hard Code Flag",
        },
        ln={
            "name": "Nkombo ya icône",
            "icon": "Icône",
            "description_str": "Ndimbola",
            "is_default": "Ya liboso",
            "hard_code_flag": "Elembo ya code",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_ICON.model_name}"
        validate_on_save = True 
