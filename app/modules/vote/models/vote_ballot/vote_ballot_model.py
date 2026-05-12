"""VoteBallotModel — one row per ballot cast.

For PUBLIC scrutins: `voter_user_id` holds the plaintext sénateur id.
                      `voter_user_id_enc` is None.
For SECRET scrutins: `voter_user_id` is None.
                      `voter_user_id_enc` holds the Fernet-encrypted id (DEK
                      from VoteConfigModel.sealed_dek_b64). Plaintext is
                      reconstructed in memory only during tally.

`weight` accommodates pouvoirs/proxies — slide 15 *"gestion du nombre de
voix et des pouvoirs"*. A holder casting on behalf of N grantors uses
weight = 1 + N. The weight is computed by `BallotService.cast` from
active VoteProxyModel rows at cast-time and frozen on the ballot row.
"""

import uuid
from datetime import datetime
from typing import Annotated, Optional

from beanie import Indexed, PydanticObjectId
from pydantic import Field

from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.vote.enums.vote_enum import EVoteChoice


class VoteBallotModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(default_factory=PydanticObjectId, alias="_id")

    identifier: str = Field(default_factory=lambda: f"{uuid.uuid4().hex[:8]}")

    sys_organization_id: Annotated[
        PydanticObjectId,
        Indexed(name="vote_ballot_org_index"),
        Field(...),
    ]

    vote_config_id: Annotated[
        PydanticObjectId,
        Indexed(name="vote_ballot_config_index"),
        Field(...),
    ]

    # Public votes only. None for secret votes.
    voter_user_id: Optional[PydanticObjectId] = Field(default=None)

    # Secret votes only. Fernet ciphertext of the voter id, base64. Only
    # decryptable with the resolution's unsealed DEK.
    voter_user_id_enc: Optional[str] = Field(default=None)

    choice: EVoteChoice = Field(...)

    weight: int = Field(
        default=1, ge=1, le=100,
        description="1 = own vote; >1 = own + proxy(ies). Frozen at cast-time.",
    )

    proxy_grantor_user_ids: list[PydanticObjectId] = Field(
        default_factory=list,
        description="Audit-only: list of granter ids whose proxy was used. "
        "For secret votes, these are NOT encrypted — pouvoirs are administrative records, "
        "not the secret choice. Verifying compliance with règlement intérieur is a public concern.",
    )

    cast_at: datetime = Field(default_factory=datetime.utcnow)

    # Audit / device-binding hooks
    device_id_str: Optional[str] = Field(default=None, max_length=200)
    signature_hash: Optional[str] = Field(default=None, max_length=200)

    class Settings:
        name = CollectionKey.VOTE_BALLOT.model_name
        validate_on_save = True
        indexes = [
            # No (vote_config_id, voter_user_id) unique index — secret votes
            # have null voter_user_id. Uniqueness is enforced at the service
            # layer via the encrypted-voter check on secret votes.
        ]
