import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field, field_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from typing import   Optional
 
class CfgUserQuestionResponseModel(BaseDocument):
    """
    This collection defines user-specific authentication setup, including pin and biometric. This is used to store the user's responses to the security questions.
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
        description="Unique identifier for the user authentication setup",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    sys_user_id: PydanticObjectId = Field(
        ...,
        description="ID of the system user associated with the authentication setup",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )  

    cfg_user_question_id: PydanticObjectId = Field(
        ...,
        description="ID of the security question associated with the response",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    response: Optional[str] = Field(
        default=None,
        description="DEPRECATED — plaintext response (bloonio legacy). "
                    "New code writes to response_hash and never reads "
                    "this column. Kept for backward compatibility with "
                    "any existing rows.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    # Argon2 hash of the normalised answer (trim + lowercase). Verify
    # path runs the same normalisation on the user's input before
    # hashing for comparison. NEVER returned to the client.
    response_hash: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=200,
        description="Argon2 hash of the normalised (trim+lower) answer.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True,
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}": True,
            },
        ),
    )

    #validator on response to trim and lower case (legacy plaintext field only)
    @field_validator("response", mode='before')
    def trim_response(cls, v):
        if v:
            return v.strip().lower()
        return v
 

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "sys_user_id": "Utilisateur système",
            "cfg_user_question_id": "Question de sécurité",
            "response": "Réponse",
        },
        en={
            "sys_user_id": "System User",
            "cfg_user_question_id": "Security Question",
            "response": "Response",
        },
        ln={
            "sys_user_id": "Mosaleli ya système",
            "cfg_user_question_id": "Motuna ya sécurité",
            "response": "Eyano",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_USER_QUESTION_RESPONSE.model_name}"
        validate_on_save = True 
