from fastapi import APIRouter, Query, Request

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.security.api.controller.rls_users_accesses_controller import RlsUsersAccessesController


router = APIRouter()


# ─── FETCH RLS USERS ACCESSES OVERVIEW ────────────────────────────────────────

@router.get("/fetch/user-accesses")
async def fetch_rls_users_accesses(request: Request, user_id: str = Query(None)):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = RlsUsersAccessesController(accept_language)
    if user_id:
        return await controller.fetch_user_rls_detail(request=request, user_id=user_id)
    return await controller.fetch_rls_users_accesses(request=request)
