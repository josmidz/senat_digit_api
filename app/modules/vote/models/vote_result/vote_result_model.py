"""VoteResultModel — aggregated tally per scrutin.

One row per `vote_config_id`. Created by `TallyService` at `close_vote()`,
then validated by greffier (`status` on parent VoteConfig moves to VALIDE).

For secret votes, this is the ONLY surface that exposes anything about
the cast ballots — and it exposes only counts. The per-voter mapping
remains encrypted-at-rest in `VoteBallotModel.voter_user_id_enc`.
"""

import uuid
from datetime import datetime
from typing import Annotated, Optional

from beanie import Indexed, PydanticObjectId
from pydantic import Field

from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument


class VoteResultModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(default_factory=PydanticObjectId, alias="_id")

    identifier: str = Field(default_factory=lambda: f"{uuid.uuid4().hex[:8]}")

    sys_organization_id: Annotated[
        PydanticObjectId,
        Indexed(name="vote_result_org_index"),
        Field(...),
    ]

    vote_config_id: Annotated[
        PydanticObjectId,
        Indexed(name="vote_result_config_index", unique=True),
        Field(...),
    ]

    # Weighted counts (i.e. sum of VoteBallotModel.weight grouped by choice).
    count_pour: int = Field(default=0, ge=0)
    count_contre: int = Field(default=0, ge=0)
    count_abstention: int = Field(default=0, ge=0)
    count_npv: int = Field(default=0, ge=0)

    # Headcount (number of ballots, not weighted) — useful for quorum cross-check.
    ballot_headcount: int = Field(default=0, ge=0)

    total_weighted: int = Field(default=0, ge=0)

    # Decision
    majority_required_count: int = Field(default=0, ge=0)
    majority_met: bool = Field(default=False)
    decision: Optional[str] = Field(
        None,
        description="ADOPTE | REJETE | NULL (NULL = inconclusive, e.g. quorum miss)",
    )

    computed_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = CollectionKey.VOTE_RESULT.model_name
        validate_on_save = True
