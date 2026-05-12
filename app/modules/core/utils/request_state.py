"""Helpers for reading the per-request user context that
`verify_logged_in_user` middleware writes to `request.state.user`.

Every senat-digit feature controller needs to extract the caller's
`sys_user_id` and `sys_organization_id` from the request. Doing this
inline in every controller produces 6+ near-identical helpers and lets
them drift from each other (which they did — all 6 feature controllers
were reading `request.state.user_organization_id`, a flat attribute
that the middleware NEVER sets, leading to silent 401s).

Use these helpers instead:

    from app.modules.core.utils.request_state import (
        current_user_id, current_user_org_id,
    )

    async def list(self, request: Request) -> Dict[str, Any]:
        org_id = current_user_org_id(request)
        ...

Both helpers raise an `HTTPException(401, …)` when the relevant context
is missing — this should never happen for a request that's already
passed `verify_logged_in_user`, but the defensive raise keeps callers
from silently de-referencing None.
"""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId
from fastapi import HTTPException, Request, status


def _user_dict(request: Request) -> dict[str, Any]:
    """Return the user dict the auth middleware attached, or raise 401."""
    user = getattr(request.state, "user", None)
    if not isinstance(user, dict) or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contexte utilisateur absent du jeton.",
        )
    return user


def current_user_id(request: Request) -> PydanticObjectId:
    """Return the caller's `sys_user._id` as a PydanticObjectId."""
    user = _user_dict(request)
    raw = user.get("id") or user.get("_id")
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant utilisateur absent du contexte.",
        )
    return raw if isinstance(raw, PydanticObjectId) else PydanticObjectId(str(raw))


def current_user_org_id(request: Request) -> PydanticObjectId:
    """Return the caller's `sys_organization_id` as a PydanticObjectId."""
    user = _user_dict(request)
    raw = user.get("sys_organization_id")
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contexte d'organisation absent du jeton.",
        )
    return raw if isinstance(raw, PydanticObjectId) else PydanticObjectId(str(raw))
