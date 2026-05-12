"""AuditEventModel — append-only chained audit log.

Tamper-evidence is enforced by the (`prev_event_hash`, `event_hash`) pair:

  event_hash = SHA256(  prev_event_hash || canonical_json(payload_for_hash)  )

where:
  - `prev_event_hash` is the `event_hash` of the immediate predecessor row in
    the chain (filtered by sys_organization_id), or `"GENESIS"` for the first.
  - `payload_for_hash` is a deterministic dict including event_type, actor,
    session/resolution/document refs, sequence_number, occurred_at (ISO-Z),
    and the event-specific `details` dict — all SHA-stable thanks to
    `json.dumps(..., sort_keys=True, separators=(",", ":"))`.

Verification (`AuditChainService.verify_chain`) walks the sequence in order
and recomputes each row's hash. The first row whose recomputed hash differs
from the stored one is the break point — older rows are trusted, newer rows
are not.

Note: this model is INTENTIONALLY separate from `OpsOrganizationLogModel`
(which handles general CRUD logs without integrity guarantees) so the
chained surface stays small + auditable.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any, Dict, Optional

from beanie import Indexed, PydanticObjectId
from pymongo import IndexModel
from pydantic import Field

from app.modules.audit_security.enums.audit_enum import EAuditEventType
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta


class AuditEventModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(default_factory=PydanticObjectId, alias="_id")

    identifier: str = Field(default_factory=lambda: f"{uuid.uuid4().hex[:8]}")

    sys_organization_id: Annotated[
        PydanticObjectId,
        Indexed(name="audit_event_org_index"),
        Field(...),
    ]

    # Monotonic int per org. Set by AuditChainService at emit-time. Does NOT
    # use Mongo's _id ordering (ObjectId timestamps are 1-second granular).
    sequence_number: int = Field(
        ..., ge=0,
        description="Monotonic per (sys_organization_id). Used for chain walk ordering.",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True},
        ),
    )

    occurred_at: datetime = Field(default_factory=datetime.utcnow)

    event_type: EAuditEventType = Field(
        ...,
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    # Who did it
    actor_user_id: Optional[PydanticObjectId] = Field(default=None)
    actor_api_consumer_flag: Optional[str] = Field(default=None, max_length=100)
    actor_device_id_str: Optional[str] = Field(default=None, max_length=200)

    # What it relates to (any/all may be null depending on event_type)
    session_meeting_id: Optional[PydanticObjectId] = Field(default=None)
    vote_config_id: Optional[PydanticObjectId] = Field(default=None)
    document_meta_id: Optional[PydanticObjectId] = Field(default=None)
    parole_request_id: Optional[PydanticObjectId] = Field(default=None)

    # Free-form event-specific data (keys are stable per event_type — see
    # AuditChainService docstring for the schema each event uses).
    details: Dict[str, Any] = Field(default_factory=dict)

    # ---- chain ----
    prev_event_hash: str = Field(
        ..., min_length=1,
        description="event_hash of the immediate predecessor row in the chain, "
                    "or the literal string 'GENESIS' for the very first row.",
    )

    event_hash: str = Field(
        ..., min_length=64, max_length=64,
        description="SHA-256 (hex) of (prev_event_hash || canonical_json(payload_for_hash)).",
    )

    async def get_formated_data(
        self,
        accept_language: str = "fr",
        output: FormatedOutPut = FormatedOutPut.MINIMAL,
    ) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "identifier": self.identifier,
            "sys_organization_id": str(self.sys_organization_id),
            "sequence_number": self.sequence_number,
            "occurred_at": self.occurred_at.isoformat(),
            "event_type": self.event_type.value,
            "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
            "actor_api_consumer_flag": self.actor_api_consumer_flag,
            "actor_device_id_str": self.actor_device_id_str,
            "session_meeting_id": str(self.session_meeting_id) if self.session_meeting_id else None,
            "vote_config_id": str(self.vote_config_id) if self.vote_config_id else None,
            "document_meta_id": str(self.document_meta_id) if self.document_meta_id else None,
            "parole_request_id": str(self.parole_request_id) if self.parole_request_id else None,
            "details": self.details,
            "prev_event_hash": self.prev_event_hash,
            "event_hash": self.event_hash,
        }

    class Settings:
        name = CollectionKey.AUDIT_EVENT.model_name
        validate_on_save = True
        indexes = [
            IndexModel(
                [("sys_organization_id", 1), ("sequence_number", 1)],
                name="audit_event_seq_per_org",
                unique=True,
            ),
        ]
