import uuid
from datetime import datetime

from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

from pydantic import Field, EmailStr
from typing import Optional

class OpsContactUsModel(BaseDocument):
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
        description="Unique identifier for the contact request",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    full_name: str = Field(
        ...,
        description="Full name of the person contacting",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    email: EmailStr = Field(
        ...,
        description="Email address of the person contacting",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    phone_number: Optional[str] = Field(
        default=None,
        pattern=r"^\+?[0-9\s\-]{7,15}$",
        description="Phone number of the contact in international format (optional)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    subject: str = Field(
        ...,
        description="Subject of the contact message",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    message: str = Field(
        ...,
        description="Content of the message from the contact form",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    contact_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp indicating when the contact message was sent",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True})
    )

    resolved: bool = Field(
        default=False,
        description="Indicates whether the contact message has been resolved",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )

    resolution_note: Optional[str] = Field(
        default=None,
        description="Notes or details about how the message was resolved",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "full_name": "Nom complet",
            "email": "Adresse e-mail",
            "phone_number": "Numéro de téléphone",
            "subject": "Objet",
            "message": "Message",
            "contact_date": "Date de contact",
            "resolved": "Résolu",
            "resolution_note": "Note de résolution",
        },
        en={
            "full_name": "Full Name",
            "email": "Email Address",
            "phone_number": "Phone Number",
            "subject": "Subject",
            "message": "Message",
            "contact_date": "Contact Date",
            "resolved": "Resolved",
            "resolution_note": "Resolution Note",
        },
        ln={
            "full_name": "Nkombo mobimba",
            "email": "Adresse ya e-mail",
            "phone_number": "Nimero ya telefone",
            "subject": "Likambo",
            "message": "Nsango",
            "contact_date": "Mokolo ya koyanola",
            "resolved": "Esilá kokatama",
            "resolution_note": "Liloba ya résolution",
        },
    )

    class Settings:
        name = f"{CollectionKey.OPS_CONTACT_US.model_name}"
        validate_on_save = True


