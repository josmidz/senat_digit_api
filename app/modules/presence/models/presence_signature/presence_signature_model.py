"""PresenceSignatureModel — one row per sénateur per séance.

Created when the sénateur signs présence on their tablette. The presence
of a row IS the presence — there's no separate "is_signed" flag, just the
existence of the row + its `signed_at` timestamp + `method` audit field.

Uniqueness: at most one signature per (session_meeting_id, sys_user_id).
Enforced by a unique compound index + the service layer.

Geolocation is OPTIONAL and OFF by default — RGPD: location is sensitive,
only collected when the deployment explicitly opts in via CfgPrivacyModel
(future, v1.1).
"""

import uuid
from datetime import datetime
from typing import Annotated, Any, Dict, Optional

from beanie import Indexed, PydanticObjectId
from pymongo import IndexModel
from pydantic import Field

from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.presence.enums.presence_enum import EPresenceMethod


class PresenceSignatureModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(default_factory=PydanticObjectId, alias="_id")

    identifier: str = Field(default_factory=lambda: f"{uuid.uuid4().hex[:8]}")

    sys_organization_id: Annotated[
        PydanticObjectId,
        Indexed(name="presence_signature_org_index"),
        Field(...),
    ]

    session_meeting_id: Annotated[
        PydanticObjectId,
        Indexed(name="presence_signature_session_index"),
        Field(...),
    ]

    sys_user_id: Annotated[
        PydanticObjectId,
        Indexed(name="presence_signature_user_index"),
        Field(...),
    ]

    method: EPresenceMethod = Field(
        default=EPresenceMethod.ESIGN,
        description="How presence was captured. MVP: ESIGN only. Others reserved for v1.1.",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    signed_at: datetime = Field(default_factory=datetime.utcnow)

    # Audit / device-binding
    device_id_str: Optional[str] = Field(default=None, max_length=200)
    signature_hash: Optional[str] = Field(
        default=None, max_length=200,
        description="HMAC of (user_id|session_id|device_id|signed_at) — used by audit chain.",
    )

    # Optional, opt-in (RGPD)
    geolocation_lat: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    geolocation_lon: Optional[float] = Field(default=None, ge=-180.0, le=180.0)

    async def get_formated_data(
        self,
        accept_language: str = "fr",
        output: FormatedOutPut = FormatedOutPut.MINIMAL,
    ) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "identifier": self.identifier,
            "sys_organization_id": str(self.sys_organization_id),
            "session_meeting_id": str(self.session_meeting_id),
            "sys_user_id": str(self.sys_user_id),
            "method": self.method.value,
            "signed_at": self.signed_at.isoformat(),
            "device_id_str": self.device_id_str,
            "signature_hash": self.signature_hash,
            "geolocation_lat": self.geolocation_lat,
            "geolocation_lon": self.geolocation_lon,
        }

    class Settings:
        name = CollectionKey.PRESENCE_SIGNATURE.model_name
        validate_on_save = True
        indexes = [
            IndexModel(
                [("session_meeting_id", 1), ("sys_user_id", 1)],
                name="presence_signature_unique_per_user_per_session",
                unique=True,
            ),
        ]
