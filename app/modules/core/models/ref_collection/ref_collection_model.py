
from typing import Annotated, Dict, Optional
import uuid
from beanie import PydanticObjectId
from pydantic import Field, model_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
import re

class RefCollectionModel(BaseDocument):
    """
    This collection defines collections.
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
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}": True,
                f"{EGLOBAL_EXTRA_METAS.FIELD_ORDERING.value}": "id,identifier,name,verbose,description_str,created_at",
                f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN.value}": f"{CollectionKey.REF_COLLECTION_CRUD_INFO.value}",
                f"{EGLOBAL_EXTRA_METAS.EXCLUDED_FIELDS.value}": "created_by_id,id,ref_collection_id,flag",
                f"{EGLOBAL_EXTRA_METAS.UPPERCASED_FIELD_VALUES.value}": "identifier,name"
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the collection",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    collection_key: str = Field(
        ...,
        description="Collection key of the collection",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}": 3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}": 100,
            },
        )
    )
    collection_name: str = Field(
        ...,
        description="Collection name of the collection",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}": 3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}": 100,
            },
        )
    )
    verbose: str = Field(
        ...,
        description="Verbose name of the collection",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}": 3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}": 100,
            },
        )
    )

    is_exposed: bool = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
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
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}": 3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}": 255,
            },
        )
    )

    ref_collection_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Reference to another related own",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_CASCADE.value}": True
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.REF_COLLECTION.value}",
            },
        )
    )

    flag: Optional[str] = Field(
        default_factory=None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        )
    )

    has_row_level_security: Optional[bool] = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    @model_validator(mode='before')
    def generate_flag_if_not_provided(cls, values):
        """
        Custom validator to generate the 'flag' field if not provided.
        """
        if "flag" not in values or not values["flag"]:
            name = values.get("verbose")
            if name:
                sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
                values["flag"] = f"{sanitized_name}_{len(name)}"
        return values

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "collection_key": "Clé de la collection",
            "collection_name": "Nom de la collection",
            "verbose": "Nom verbose",
            "is_exposed": "Exposée",
            "description_str": "Description",
            "ref_collection_id": "Collection parente",
            "has_row_level_security": "Sécurité au niveau des lignes",
        },
        en={
            "collection_key": "Collection Key",
            "collection_name": "Collection Name",
            "verbose": "Verbose Name",
            "is_exposed": "Exposed",
            "description_str": "Description",
            "ref_collection_id": "Parent Collection",
            "has_row_level_security": "Row Level Security",
        },
        ln={
            "collection_key": "Fungola ya collection",
            "collection_name": "Nkombo ya collection",
            "verbose": "Nkombo ya mobimba",
            "is_exposed": "Emonisami",
            "description_str": "Ndimbola",
            "ref_collection_id": "Collection ya mobotami",
            "has_row_level_security": "Sécurité ya molongo",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_COLLECTION.model_name}"
        validate_on_save = True
