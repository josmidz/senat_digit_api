"""SessionMeetingModel — séance parlementaire.

Tracks a single parliamentary session: planning, opening, suspending,
closing, archival. Status transitions are enforced by `SessionService`
(see `services/session_service.py`); this model only carries the state.

ID-only storage rule: no denormalized name fields. Resolve names at runtime
in `get_formated_data` via `_resolve_*` helpers (CLAUDE.md).
"""

import uuid
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional

from beanie import Indexed, PydanticObjectId
from pydantic import Field

from app.modules.core.enums.type_enum import (
    EGLOBAL_DATA_TYPE,
    FormatedOutPut,
    OutputDataType,
)
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.session_meeting.enums.session_enum import ESessionMode, ESessionStatus


class SessionMeetingModel(BaseDocument):
    """A parliamentary session ("séance"). MVP: présentiel mode only."""

    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Short unique identifier",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    sys_organization_id: Annotated[
        PydanticObjectId,
        Indexed(name="session_meeting_org_index"),
        Field(
            ...,
            description="Owner organization (tenant scope for RLS)",
            json_schema_extra=translation_meta(
                may_have_translation=False,
                to_be_translated_in_front=False,
                data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            ),
        ),
    ]

    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Title of the séance (FR)",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    description_str: Optional[str] = Field(
        None,
        max_length=2000,
        description="Long-form description (FR)",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True},
        ),
    )

    scheduled_at: datetime = Field(
        ...,
        description="Planned start (UTC)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True},
        ),
    )

    mode: ESessionMode = Field(
        default=ESessionMode.PRESENTIEL,
        description="Mode: PRESENTIEL (MVP) | DISTANCE | HYBRIDE",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    status: ESessionStatus = Field(
        default=ESessionStatus.PLANIFIEE,
        description="FSM state — transitions enforced by SessionService",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    opened_at: Optional[datetime] = Field(default=None)
    suspended_at: Optional[datetime] = Field(default=None)
    closed_at: Optional[datetime] = Field(default=None)

    # Quorum reference values — frozen at session creation, used by QuorumService.
    total_seats: int = Field(
        ...,
        ge=1,
        description="Total nominal seats for this séance (denominator for quorum)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True},
        ),
    )

    required_quorum_count: int = Field(
        ...,
        ge=1,
        description="Minimum present-vote count to declare quorum (e.g. ceil(total_seats/2)+1)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True},
        ),
    )

    async def get_formated_data(
        self,
        accept_language: str = "fr",
        output: FormatedOutPut = FormatedOutPut.MINIMAL,
    ) -> Dict[str, Any]:
        """Format for API responses. Resolves status/mode labels lazily."""
        return {
            "id": str(self.id),
            "identifier": self.identifier,
            "title": self.title,
            "description_str": self.description_str,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "mode": self.mode.value,
            "status": self.status.value,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "suspended_at": self.suspended_at.isoformat() if self.suspended_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "total_seats": self.total_seats,
            "required_quorum_count": self.required_quorum_count,
            "sys_organization_id": str(self.sys_organization_id),
            "created_at": self.created_at.isoformat() if getattr(self, "created_at", None) else None,
        }

    class Settings:
        name = CollectionKey.SESSION_MEETING.model_name
        validate_on_save = True
