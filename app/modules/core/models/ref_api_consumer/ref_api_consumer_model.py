
from typing import Optional
import uuid
from pydantic import Field, model_validator

from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId

from app.modules.core.services.hash.hash_service import HashService
from app.modules.core.enums.type_enum import AppGeneratorType, EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
import re

class RefApiConsumerModel(BaseDocument):
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
        description="The name of the API consumer.",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    consumer_key: Optional[str] = Field(
        default=None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        )
    )
    consumer_hash: Optional[str] = Field(
        default=None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        )
    )

    # ── HMAC request signing ─────────────────────────────────────────────
    # 256-bit symmetric secret, hex-encoded (64 chars). Used by the
    # ConsumerValidationMiddleware to verify the X-Api-Signature header
    # on each request. Provisioned per consumer; rotated per app release.
    #
    # Mobile clients embed this at build time via --dart-define so it
    # never crosses the wire. Server-side clients (admin web, fs api)
    # hold it in their own env config.
    #
    # Treat as a credential — never returned in /list/ref_api_consumer
    # endpoints (filter at the controller level), never logged.
    consumer_secret: Optional[str] = Field(
        default=None,
        repr=False,
        description="HMAC-SHA256 shared secret (hex). Never expose via API.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        )
    )

    restricted: Optional[bool] = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    can_receive_totp_validation_push: Optional[bool] = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    meta: Optional[str] = Field(
        default=None,
        description="The metadata to validate the API consumer.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    is_default: bool = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    flag: Optional[str] = Field(
        default=None,
        description="Api consumer flag for hard coding purpose",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.REJECT_IF_EXIST.value}": True,
            },
        )
    )

    # @model_validator(mode='before')
    # def generate_consumer_keys(cls, values):
    #     """
    #     Custom validator to generate the 'flag' field if not provided.
    #     """
    #     if "name" not in values:
    #         name = values.get("name")
    #         if name:
    #             sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
    #             values["consumer_key"] =  f"{sanitized_name}_{len(sanitized_name)}"
    #     return values
     
    
    # @staticmethod
    # def generate_consumer_key(name: str) -> str:
    #     """
    #     Custom generator for consumer_key based on the name field.
    #     """
    #     # name = values.get("name")
    #     if not name:
    #         raise ValueError("Name is required to generate consumer_key.")
    #     sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
    #     return f"{sanitized_name}_{len(sanitized_name)}"

    # @staticmethod
    # def generate_consumer_hash(name: str) -> str:
    #     """
    #     Generates a hashed value based on the provided name.
    #     """
    #     if not name:
    #         raise ValueError("Name is required for hash generation.")
    #     sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
    #     hashed = HashService.generate_base64_hash(f"{sanitized_name}_{len(sanitized_name)}")
    #     return hashed
    
    @staticmethod
    def generate_flag_key(name: str,flag:Optional[str]) -> str:
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
        
    @model_validator(mode='before')
    def generate_consumer_hashes(cls, values):
        """
        """
        if "flag" not in values:
            flag_value = values.get("name")
            if flag_value:
                sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", flag_value).lower()
                hashed = HashService.generate_base64_hash(f"{sanitized_name}_{len(sanitized_name)}")
                values["consumer_hash"] =  hashed

                # 
                sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", flag_value).lower()
                values["consumer_key"] =  f"{sanitized_name}_{len(sanitized_name)}"
        else:
            flag_value = values.get("flag")
            sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", flag_value).lower()
            hashed = HashService.generate_base64_hash(f"{sanitized_name}_{len(sanitized_name)}")
            values["consumer_hash"] =  hashed

            # 
            sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", flag_value).lower()
            values["consumer_key"] =  f"{sanitized_name}_{len(sanitized_name)}"
        return values

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "consumer_key": "Clé du consommateur",
            "consumer_hash": "Hash du consommateur",
            "restricted": "Restreint",
            "can_receive_totp_validation_push": "Peut recevoir une validation TOTP",
            "meta": "Métadonnées",
            "is_default": "Par défaut",
        },
        en={
            "name": "Name",
            "consumer_key": "Consumer Key",
            "consumer_hash": "Consumer Hash",
            "restricted": "Restricted",
            "can_receive_totp_validation_push": "Can Receive TOTP Validation Push",
            "meta": "Metadata",
            "is_default": "Default",
        },
        ln={
            "name": "Nkombo",
            "consumer_key": "Fungola ya mosaleli",
            "consumer_hash": "Hash ya mosaleli",
            "restricted": "Epekisami",
            "can_receive_totp_validation_push": "Akoki kozwa validation TOTP",
            "meta": "Métadonnées",
            "is_default": "Ya liboso",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_API_CONSUMER.model_name}"
        validate_on_save = True
