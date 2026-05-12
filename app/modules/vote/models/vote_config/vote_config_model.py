"""VoteConfigModel — configuration for a single scrutin.

A scrutin (vote) is configured against a `DocumentMetaModel` of typology
RESOLUTION (or AMENDEMENT). The greffier sets the ballot type, secrecy,
majority rule, and duration before opening the vote.

Secret-vote crypto invariant: when `is_secret=True`, the resolution DEK
sealed by the org KMS is stored in `sealed_dek_b64` (set by VoteCryptoService
at create-time). Endpoints MUST scrub this field before returning the
config to any caller — see `VoteCryptoService.redacted_config_payload`.
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
from app.modules.vote.enums.vote_enum import EVoteBallotType, EVoteMajorityType, EVoteStatus


class VoteConfigModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(default_factory=PydanticObjectId, alias="_id")

    identifier: str = Field(default_factory=lambda: f"{uuid.uuid4().hex[:8]}")

    sys_organization_id: Annotated[
        PydanticObjectId,
        Indexed(name="vote_config_org_index"),
        Field(...),
    ]

    session_meeting_id: Annotated[
        PydanticObjectId,
        Indexed(name="vote_config_session_index"),
        Field(..., description="Session this scrutin belongs to."),
    ]

    resolution_id: Annotated[
        PydanticObjectId,
        Indexed(name="vote_config_resolution_index"),
        Field(..., description="DocumentMeta of typology RESOLUTION (or AMENDEMENT) being voted on."),
    ]

    title: str = Field(..., min_length=3, max_length=300)
    description_str: Optional[str] = Field(None, max_length=4000)

    ballot_type: EVoteBallotType = Field(default=EVoteBallotType.OUI_NON)
    is_secret: bool = Field(
        default=False,
        description="When True, voter_user_id is encrypted-at-rest in VoteBallotModel.",
        json_schema_extra=translation_meta(
            may_have_translation=False, to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
        ),
    )
    majority_type: EVoteMajorityType = Field(default=EVoteMajorityType.RELATIVE)
    majority_custom_threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="0.0–1.0 ratio. Required when majority_type=CUSTOM, ignored otherwise.",
    )
    duration_seconds: int = Field(default=60, ge=10, le=3600)
    allow_proxies: bool = Field(default=True)

    status: EVoteStatus = Field(default=EVoteStatus.PROJET)
    opened_at: Optional[datetime] = Field(default=None)
    suspended_at: Optional[datetime] = Field(default=None)
    closed_at: Optional[datetime] = Field(default=None)
    validated_at: Optional[datetime] = Field(default=None)

    # Secret-vote crypto — populated by VoteCryptoService at create-time when is_secret=True.
    # NEVER returned in HTTP responses; redacted by `redacted_config_payload`.
    sealed_dek_b64: Optional[str] = Field(default=None)

    # Cached counter set by BallotService — used by VoteService to enforce
    # the "no change_type after first ballot" invariant on secret votes.
    ballots_cast_count: int = Field(default=0, ge=0)

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
            "resolution_id": str(self.resolution_id),
            "title": self.title,
            "description_str": self.description_str,
            "ballot_type": self.ballot_type.value,
            "is_secret": self.is_secret,
            "majority_type": self.majority_type.value,
            "majority_custom_threshold": self.majority_custom_threshold,
            "duration_seconds": self.duration_seconds,
            "allow_proxies": self.allow_proxies,
            "status": self.status.value,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "suspended_at": self.suspended_at.isoformat() if self.suspended_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "ballots_cast_count": self.ballots_cast_count,
            # `sealed_dek_b64` intentionally NOT included — defence in depth.
        }

    class Settings:
        name = CollectionKey.VOTE_CONFIG.model_name
        validate_on_save = True
