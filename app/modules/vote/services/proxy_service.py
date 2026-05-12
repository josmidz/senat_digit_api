"""ProxyService — pouvoirs management.

Greffier-only assign/revoke. The active-weight resolver
(`active_weight_for_holder`) is used by `BallotService.cast` to compute
the ballot weight at cast-time.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from beanie import PydanticObjectId

from app.modules.vote.models.vote_proxy.vote_proxy_model import VoteProxyModel


class ProxyService:
    def __init__(self, accept_language: str = "fr"):
        self.accept_language = accept_language

    async def assign(
        self,
        sys_organization_id: PydanticObjectId,
        session_meeting_id: str,
        granter_user_id: str,
        holder_user_id: str,
    ) -> VoteProxyModel:
        if granter_user_id == holder_user_id:
            raise ValueError("Le mandant et le mandataire ne peuvent être identiques.")
        # Reject if granter already has an active proxy for this séance — one
        # voter, one delegation. Holder may receive multiple.
        existing = await VoteProxyModel.find_one(
            VoteProxyModel.session_meeting_id == PydanticObjectId(session_meeting_id),
            VoteProxyModel.granter_user_id == PydanticObjectId(granter_user_id),
            VoteProxyModel.revoked_at == None,  # noqa: E711
        )
        if existing is not None:
            raise ValueError(
                "Un pouvoir actif existe déjà pour ce sénateur sur cette séance."
            )
        proxy = VoteProxyModel(
            sys_organization_id=sys_organization_id,
            session_meeting_id=PydanticObjectId(session_meeting_id),
            granter_user_id=PydanticObjectId(granter_user_id),
            holder_user_id=PydanticObjectId(holder_user_id),
        )
        await proxy.insert()
        return proxy

    async def revoke(self, proxy_id: str, reason: Optional[str]) -> VoteProxyModel:
        oid = PydanticObjectId(proxy_id)
        proxy = await VoteProxyModel.get(oid)
        if proxy is None:
            raise ValueError(f"Pouvoir introuvable: {proxy_id}")
        if proxy.revoked_at is not None:
            return proxy  # idempotent
        proxy.revoked_at = datetime.now(timezone.utc)
        proxy.revocation_reason = reason
        await proxy.save()
        return proxy

    async def active_for_holder(
        self,
        session_meeting_id: PydanticObjectId,
        holder_user_id: PydanticObjectId,
    ) -> list[VoteProxyModel]:
        return await VoteProxyModel.find(
            VoteProxyModel.session_meeting_id == session_meeting_id,
            VoteProxyModel.holder_user_id == holder_user_id,
            VoteProxyModel.revoked_at == None,  # noqa: E711
        ).to_list()

    async def list_session_proxies(
        self,
        session_meeting_id: str,
    ) -> list[VoteProxyModel]:
        return await VoteProxyModel.find(
            VoteProxyModel.session_meeting_id == PydanticObjectId(session_meeting_id),
        ).to_list()

    async def list_self_received(
        self,
        session_meeting_id: str,
        holder_user_id: PydanticObjectId,
    ) -> list[VoteProxyModel]:
        return await VoteProxyModel.find(
            VoteProxyModel.session_meeting_id == PydanticObjectId(session_meeting_id),
            VoteProxyModel.holder_user_id == holder_user_id,
        ).to_list()

    async def list_self_granted(
        self,
        session_meeting_id: str,
        granter_user_id: PydanticObjectId,
    ) -> list[VoteProxyModel]:
        """Mirror of [list_self_received] for the OPPOSITE direction —
        proxies the caller has GRANTED to other sénateurs in this
        session. Powers the "Donner pouvoir" tile so the granter can
        see + revoke their active grants."""
        return await VoteProxyModel.find(
            VoteProxyModel.session_meeting_id == PydanticObjectId(session_meeting_id),
            VoteProxyModel.granter_user_id == granter_user_id,
        ).to_list()
