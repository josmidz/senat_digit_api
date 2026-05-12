"""
Validation-request endpoints centralised in the security module.

Full URL paths (prefix /api/v1/securities/validations/requests):
  GET  /pending           → fetch all pending requests for the current user
  GET  /single            → fetch a single request by item_id query param
  POST /validate-or-reject → submit approve / reject decision
  POST /validate-all      → bulk-approve all pending where user is next validator
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Query, Request

from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE

router = APIRouter()


# ─── GET pending list ─────────────────────────────────────────────────────────

@router.get("/pending")
async def fetch_pending_validation_requests(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(
        OutputDataType.DEFAULT, description="Output format"
    ),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number"),
    limit: Optional[int] = Query(10, description="Items per page"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call flag"),
):
    """Fetch all pending / in-progress validation requests where the current
    user is a listed validator for their organisation."""
    from app.modules.core.api.controller.static_controller import StaticController

    accept_language = (
        request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    )
    return await StaticController(accept_language).fetch_pending_validation_requests(
        request=request,
        all_data=all_data,
        page=page,
        limit=limit,
        output_data_type=output_data_type,
        endpoint_call=endpoint_call,
    )


# ─── GET single request ───────────────────────────────────────────────────────

@router.get("/single")
async def fetch_single_validation_request(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(
        OutputDataType.DEFAULT, description="Output format"
    ),
):
    """Fetch a single validation request by item_id query parameter.
    The backend enforces that the current user must be among the validators
    (guard via MongoDB $match on validator_users)."""
    from app.modules.core.api.controller.static_controller import StaticController

    accept_language = (
        request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    )
    return await StaticController(accept_language).fetch_single_validation_request(
        request=request,
        output_data_type=output_data_type,
    )


# ─── POST validate / reject ───────────────────────────────────────────────────

@router.post("/validate-or-reject")
async def validate_or_reject_pending_validation_request(
    request: Request,
    body: Dict[str, Any],
):
    """Submit an APPROVED or REJECTED decision on a pending validation request.
    Only the designated next_validator_id who has has_validation_access may act."""
    from app.modules.core.api.controller.static_controller import StaticController

    accept_language = (
        request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    )
    return await StaticController(
        accept_language
    ).validate_or_reject_pending_validation_request(
        request=request,
        body=body,
    )


# ─── POST validate all ────────────────────────────────────────────────────────

@router.post("/validate-all")
async def validate_all_pending_validation_requests(
    request: Request,
    body: Dict[str, Any],
):
    """Bulk-approve all pending validation requests where the current user is
    the designated next validator.  Only APPROVED decisions are accepted
    (bulk rejection is intentionally disallowed for safety)."""
    from app.modules.core.api.controller.static_controller import StaticController

    accept_language = (
        request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    )
    return await StaticController(
        accept_language
    ).validate_all_pending_validation_requests(
        request=request,
        body=body,
    )
