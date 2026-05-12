
from typing import Annotated, Dict, Optional
import uuid
from beanie import PydanticObjectId
from pydantic import Field, model_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

from app.modules.core.enums.type_enum import ECollectionCrudInfoFlag, EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
import re

class RefCollectionCrudInfoModel(BaseDocument):
    """
    This collection defines collections CRUD info.
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
                f"{EGLOBAL_EXTRA_METAS.FIELD_ORDERING.value}": "id,identifier,label,flag,description_str,created_at",
                # f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN.value}": f"{CollectionKey.SYS_ORGANIZATION_AGENT.value}",
                f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN_WITH_CUSTOM_FIELD_NAME.value}": f"<{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.value},targeted_id>,<{CollectionKey.RBAC_RESTRICTED_PROFIL.value},targeted_id>",
                f"{EGLOBAL_EXTRA_METAS.EXCLUDED_FIELDS.value}": "created_by_id,id,ref_collection_id",
                f"{EGLOBAL_EXTRA_METAS.UPPERCASED_FIELD_VALUES.value}": "identifier,name",
                f"{EGLOBAL_EXTRA_METAS.DELETE_CASCADE_ON_DELETE_WITH_CUSTOM_FIELD_NAME.value}": f"<{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.value},targeted_id>,<{CollectionKey.RBAC_RESTRICTED_PROFIL.value},targeted_id>"
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the collection",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    label: str = Field(
        ...,
        description="Short name of the collection",
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
    parent_field_name: Optional[str] = Field(
        default=None,
        description="Parent field name",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}": True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}": False,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}": 3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}": 100,
            },
        )
    )

    targeted_id: PydanticObjectId = Field(
        ...,
        description="ID of targeted collection (menu or application, view,...)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    rbac_endpoint_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Reference to another related own",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": f"{CollectionKey.RBAC_ENDPOINT.value}",
            }
        )
    )

    flag: ECollectionCrudInfoFlag = Field(
        default=ECollectionCrudInfoFlag.NONE,
        description="Flag for the collection",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}": "ECollectionCrudInfoFlag",
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True,
                f"{EGLOBAL_EXTRA_METAS.UPSERT_IF_EXIST_WITH_PROPS.value}": "rbac_endpoint_id,flag,targeted_id",
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": "<none,000000,F5F5F5>,<fetch_url,2196F3,D1E8FB>,<update_processing_url,4CAF50,E8F5E9>,<update_head_process_url,8BC34A,EEF7E4>,<parent_field_name,9C27B0,F3E5F5>,<delete_processing_url,F44336,FDEAEA>,<create_processing_url,FF9800,FFF3E0>,<create_head_process_url,FFC107,FFF8E1>,<create_child_processing_url,03A9F4,E1F5FE>,<download_process_url,00BCD4,E0F7FA>,<create_child_head_process_url,009688,E0F2F1>,<fetch_one_info_url,673AB7,EDE7F6>,<fetch_one_info_for_viewing_url,3F51B5,E8EAF6>,<put_processing_url,795548,EFEBE9>,<patch_processing_url,607D8B,ECEFF1>"
            }
        )
    )

    hard_code_flag: Optional[str] = Field(
        default="main",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
            }
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "label": "Libellé",
            "parent_field_name": "Nom du champ parent",
            "targeted_id": "ID cible",
            "rbac_endpoint_id": "Endpoint RBAC",
            "hard_code_flag": "Indicateur codé en dur",
        },
        en={
            "label": "Label",
            "parent_field_name": "Parent Field Name",
            "targeted_id": "Target ID",
            "rbac_endpoint_id": "RBAC Endpoint",
            "hard_code_flag": "Hard Code Flag",
        },
        ln={
            "label": "Etiketi",
            "parent_field_name": "Nkombo ya esika ya mobotami",
            "targeted_id": "ID ya cible",
            "rbac_endpoint_id": "Endpoint RBAC",
            "hard_code_flag": "Elembo ya code",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_COLLECTION_CRUD_INFO.model_name}"
        validate_on_save = True