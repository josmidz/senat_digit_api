
import uuid
from app.modules.core.schemas.user_schema import OthersInfo
from pydantic import Field
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

from app.modules.core.utils.model.base_document import BaseDocument
from typing import Annotated, List, Optional
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

class CfgSystemOrganizationModel(BaseDocument):
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
                f"{EGLOBAL_EXTRA_METAS.FIELD_ORDERING.value}":"id,identifier,created_at",
                f"{EGLOBAL_EXTRA_METAS.EXCLUDED_FIELDS.value}":"created_by_id,id,is_activated,created_at,updated_at,sys_organization_id",
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the document",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )  
    
    sys_organization_id: PydanticObjectId = Field(
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
            "sys_organization_id": "Organisation système",
        },
        en={
            "sys_organization_id": "System Organization",
        },
        ln={
            "sys_organization_id": "Organisation ya système",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_SYSTEM_ORGANIZATION.model_name}"
        validate_on_save = True
 
