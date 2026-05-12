from typing import Optional

from fastapi import APIRouter, Query, Request

from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.security.api.controller.delegated_validators_controller import DelegatedValidatorsController

router = APIRouter()


# ─── FETCH DELEGATED VALIDATORS (RBAC TITLE TREE) ────────────────────────────

@router.get("/fetch/delegated-validators")
async def fetch_delegated_validators(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Output format"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
):
    """Fetch all org sudo action configurations formatted as RBAC title tree with linked validators."""
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = DelegatedValidatorsController(accept_language)
    return await controller.fetch_delegated_validators(
        request=request,
        output_data_type=output_data_type,
        all_data=all_data,
        page=page,
        limit=limit,
    )
