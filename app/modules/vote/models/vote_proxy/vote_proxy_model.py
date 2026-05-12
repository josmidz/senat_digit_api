"""VoteProxyModel — pouvoir / procuration.

Slide 15 *"gestion du nombre de voix et des pouvoirs"*. Granter delegates
their voting right to the holder for a single séance. A proxy is active
between `granted_at` and `revoked_at` (None = still active).

Cap on number of proxies a holder can hold per séance is configurable
(open question in 00_gap_analysis.md #6 — règlement intérieur). MVP
default: no cap. The greffier is the only one who can assign/revoke.
"""

import uuid
from datetime import datetime
from typing import Annotated, Optional

from beanie import Indexed, PydanticObjectId
from pydantic import Field

from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument


class VoteProxyModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(default_factory=PydanticObjectId, alias="_id")

    identifier: str = Field(default_factory=lambda: f"{uuid.uuid4().hex[:8]}")

    sys_organization_id: Annotated[
        PydanticObjectId,
        Indexed(name="vote_proxy_org_index"),
        Field(...),
    ]

    session_meeting_id: Annotated[
        PydanticObjectId,
        Indexed(name="vote_proxy_session_index"),
        Field(..., description="Proxies are séance-scoped (not perpetual)."),
    ]

    granter_user_id: Annotated[
        PydanticObjectId,
        Indexed(name="vote_proxy_granter_index"),
        Field(..., description="The sénateur giving up their vote."),
    ]

    holder_user_id: Annotated[
        PydanticObjectId,
        Indexed(name="vote_proxy_holder_index"),
        Field(..., description="The sénateur receiving the additional voting weight."),
    ]

    granted_at: datetime = Field(default_factory=datetime.utcnow)
    revoked_at: Optional[datetime] = Field(default=None)
    revocation_reason: Optional[str] = Field(None, max_length=500)

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    class Settings:
        name = CollectionKey.VOTE_PROXY.model_name
        validate_on_save = True
