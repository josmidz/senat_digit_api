from fastapi import APIRouter, Request

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.security.api.controller.rls_overview_controller import RlsOverviewController

router = APIRouter()


# ─── FETCH RLS OVERVIEW ──────────────────────────────────────────────────────

@router.get("/fetch/overview")
async def fetch_rls_overview(request: Request):
    """
    Returns a dashboard overview of RLS security:
    - Security group count
    - Access type breakdown (global / revoked / custom)
    - Permission stats (total, enabled, strict mode)
    - Calculated security score %
    """
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = RlsOverviewController(accept_language)
    return await controller.fetch_rls_overview(request=request)
