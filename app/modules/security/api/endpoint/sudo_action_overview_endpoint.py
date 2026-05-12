from fastapi import APIRouter, Query, Request

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.security.api.controller.sudo_action_overview_controller import SudoActionOverviewController
from app.modules.security.api.controller.users_sudo_action_overview_controller import UsersSudoActionOverviewController

router = APIRouter()


# ─── FETCH SUDO ACTIONS OVERVIEW ─────────────────────────────────────────────

@router.get("/fetch/sudo-actions-overview")
async def fetch_sudo_actions_overview(request: Request):
    """
    Returns a dashboard overview of sudo action security:
    - Security group count
    - Access type breakdown (global / grouped / delegated)
    - Per sudo-action-type permission stats (total vs enabled)
    - Calculated security score %
    """
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SudoActionOverviewController(accept_language)
    return await controller.fetch_sudo_actions_overview(request=request)


# ─── FETCH USERS SUDO ACTIONS OVERVIEW ───────────────────────────────────────

@router.get("/fetch/users-sudo-actions-overview")
async def fetch_users_sudo_actions_overview(request: Request, user_id: str = Query(None)):
    """
    Returns a per-user dashboard overview of sudo action assignments:
    - Summary: total users, assigned count, unassigned count, coverage %
    - Per access type: how many users have that type
    - User list with per-user access breakdown (direct vs group, per-type counts)

    When ?user_id= is provided, returns detailed sudo action access for that single user.
    """
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = UsersSudoActionOverviewController(accept_language)
    if user_id:
        return await controller.fetch_user_sudo_action_detail(request=request, user_id=user_id)
    return await controller.fetch_users_sudo_actions_overview(request=request)
