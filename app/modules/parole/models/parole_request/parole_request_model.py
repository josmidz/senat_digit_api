"""ParoleRequestModel — sénateur's request to speak during a séance.

FIFO queue ordered by `requested_at` (greffier may override priority by
dispatching out of order — the `requested_at` field is preserved as audit).
"""

import uuid
from datetime import datetime
from typing import Annotated, Any, Dict, Optional

from beanie import Indexed, PydanticObjectId
from pydantic import Field

from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.parole.enums.parole_enum import EParoleStatus


class ParoleRequestModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(default_factory=PydanticObjectId, alias="_id")

    identifier: str = Field(default_factory=lambda: f"{uuid.uuid4().hex[:8]}")

    sys_organization_id: Annotated[
        PydanticObjectId,
        Indexed(name="parole_request_org_index"),
        Field(...),
    ]

    session_meeting_id: Annotated[
        PydanticObjectId,
        Indexed(name="parole_request_session_index"),
        Field(..., description="Session this request belongs to."),
    ]

    agenda_item_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Optional context: the agenda point the sénateur wants to address.",
    )

    requester_user_id: Annotated[
        PydanticObjectId,
        Indexed(name="parole_request_requester_index"),
        Field(..., description="The sénateur asking to speak."),
    ]

    requested_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Original request timestamp. FIFO ordering. Never mutated after insert.",
    )

    motive: Optional[str] = Field(
        None, max_length=500,
        description="Short reason / topic the sénateur wishes to address (FR).",
        json_schema_extra=translation_meta(
            may_have_translation=True, to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True},
        ),
    )

    status: EParoleStatus = Field(
        default=EParoleStatus.EN_ATTENTE,
        description="EN_ATTENTE | ACCORDEE | REFUSEE | EXPIREE | TERMINEE",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    # Greffier dispatch fields
    dispatched_by_user_id: Optional[PydanticObjectId] = Field(default=None)
    dispatched_at: Optional[datetime] = Field(default=None)
    dispatch_reason: Optional[str] = Field(None, max_length=500)
    granted_duration_seconds: Optional[int] = Field(
        None, ge=10, le=1800,
        description="Allotted speaking time in seconds (10s..30min). Set when ACCORDEE.",
    )

    # Set when status moves to TERMINEE
    terminated_at: Optional[datetime] = Field(default=None)

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
            "agenda_item_id": str(self.agenda_item_id) if self.agenda_item_id else None,
            "requester_user_id": str(self.requester_user_id),
            "requested_at": self.requested_at.isoformat(),
            "motive": self.motive,
            "status": self.status.value,
            "dispatched_by_user_id": str(self.dispatched_by_user_id) if self.dispatched_by_user_id else None,
            "dispatched_at": self.dispatched_at.isoformat() if self.dispatched_at else None,
            "dispatch_reason": self.dispatch_reason,
            "granted_duration_seconds": self.granted_duration_seconds,
            "terminated_at": self.terminated_at.isoformat() if self.terminated_at else None,
        }

    class Settings:
        name = CollectionKey.PAROLE_REQUEST.model_name
        validate_on_save = True
