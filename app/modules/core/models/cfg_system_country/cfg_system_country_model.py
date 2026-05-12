
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, EAppGroupFlag
from app.modules.core.utils.model.status_color_helper import StatusColorHelper
from pydantic import Field
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from typing import Annotated, List, Optional

class CfgSystemCountryModel(BaseDocument):
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

    transfert_recever_email_is_required: Optional[bool] = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
    transfert_recever_phone_number_is_required: Optional[bool] = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
    can_appear_to_transfert: Optional[bool] = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
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
            }
        )
    )

    ref_application_group_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Application group",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_APPLICATION_GROUP.value}",
            }
        )
    )

    application_group_flag: Optional[EAppGroupFlag] = Field(
        default=EAppGroupFlag.COMMON.value,
        description="Application group flag",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":"EAppGroupFlag",
                f"{EGLOBAL_EXTRA_METAS.UPSERT_IF_EXIST_WITH_PROPS.value}":"ref_entity_id,application_group_flag",
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    EAppGroupFlag,
                    StatusColorHelper.create_mapping(
                        gray=[EAppGroupFlag.COMMON.value],
                    )
                ),
            }
        )
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "transfert_recever_email_is_required": "E-mail du destinataire requis",
            "transfert_recever_phone_number_is_required": "Téléphone du destinataire requis",
            "can_appear_to_transfert": "Peut apparaître au transfert",
            "ref_entity_id": "Entité de référence",
            "ref_application_group_id": "Groupe d'application",
            "application_group_flag": "Indicateur de groupe d'application",
        },
        en={
            "transfert_recever_email_is_required": "Receiver Email Required",
            "transfert_recever_phone_number_is_required": "Receiver Phone Number Required",
            "can_appear_to_transfert": "Can Appear in Transfer",
            "ref_entity_id": "Reference Entity",
            "ref_application_group_id": "Application Group",
            "application_group_flag": "Application Group Flag",
        },
        ln={
            "transfert_recever_email_is_required": "E-mail ya mozwi esengeli",
            "transfert_recever_phone_number_is_required": "Nimero ya telefone ya mozwi esengeli",
            "can_appear_to_transfert": "Ekoki komonana na transfert",
            "ref_entity_id": "Entité ya référence",
            "ref_application_group_id": "Lisanga ya application",
            "application_group_flag": "Elembo ya lisanga ya application",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_SYSTEM_COUNTRY.model_name}"
        indexes = [
            "ref_entity_id",
            "application_group_flag",
        ]
        validate_on_save = True
 
