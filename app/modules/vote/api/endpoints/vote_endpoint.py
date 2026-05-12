"""Vote endpoints — `/verb/resource` per CLAUDE.md.

Mounted at `/api/v1` (no prefix).

| Method | Path                          | Permission                |
|--------|-------------------------------|---------------------------|
| POST   | /create/vote_config           | vote.configure            |
| PATCH  | /patch/vote_config            | vote.configure            |
| GET    | /detail/vote_config           | vote.supervise            |
| GET    | /list/vote_by_session         | vote.list_by_session      |
| GET    | /list/vote_by_text            | vote.list_by_text         |
| GET    | /detail/resolution_active     | vote.cast (read-only side)|
| POST   | /open/vote                    | vote.open       (custom)  |
| POST   | /suspend/vote                 | vote.suspend    (custom)  |
| POST   | /close/vote                   | vote.close      (custom)  |
| POST   | /validate/vote_result         | vote.validate   (custom)  |
| POST   | /change_type/vote             | vote.change_type_live (c) |
| POST   | /create/vote_ballot           | vote.cast       (custom)  |
| GET    | /detail/vote_result           | vote.read_results         |
| POST   | /export/pv                    | vote.export_pv  (custom)  |
| POST   | /assign/vote_proxy            | proxy.assign    (custom)  |
| POST   | /revoke/vote_proxy            | proxy.revoke    (custom)  |
| GET    | /list/vote_proxy              | proxy.list                |
| GET    | /list/proxy_self              | proxy.read_self           |
"""

from fastapi import APIRouter, Body, Query, Request

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.vote.api.controller.vote_controller import VoteController
from app.modules.vote.schemas.vote_schema import (
    BallotCastRequest,
    ProxyAssignRequest,
    ProxyRevokeRequest,
    VoteChangeTypeLiveRequest,
    VoteConfigCreateRequest,
    VoteConfigPatchRequest,
    VoteExportPvRequest,
    VoteStateTransitionRequest,
)


router = APIRouter()


def _accept_language(request: Request) -> str:
    return request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()


# ---- config ----
@router.post("/create/vote_config")
async def create_vote_config(request: Request, payload: VoteConfigCreateRequest):
    return await VoteController(_accept_language(request)).create_config(request, payload)


@router.patch("/patch/vote_config")
async def patch_vote_config(
    request: Request, payload: VoteConfigPatchRequest, id: str = Query(..., min_length=12)
):
    return await VoteController(_accept_language(request)).patch_config(request, id, payload)


@router.get("/detail/vote_config")
async def detail_vote_config(request: Request, id: str = Query(..., min_length=12)):
    return await VoteController(_accept_language(request)).detail_config(request, id)


@router.get("/list/vote_by_session")
async def list_vote_by_session(request: Request, session_id: str = Query(..., min_length=12)):
    return await VoteController(_accept_language(request)).list_by_session(request, session_id)


@router.get("/list/vote_by_text")
async def list_vote_by_text(request: Request, resolution_id: str = Query(..., min_length=12)):
    return await VoteController(_accept_language(request)).list_by_text(request, resolution_id)


@router.get("/list/vote_ballot_self")
async def list_vote_ballot_self(
    request: Request,
    limit: int = Query(200, ge=1, le=500),
):
    """Caller's own vote history (PUBLIC ballots only). Powers the
    sénateur "Mes votes" tile."""
    return await VoteController(_accept_language(request)).list_ballot_self(
        request, limit=limit,
    )


@router.post("/create/vote_manual_tally")
async def create_vote_manual_tally(
    request: Request, body: dict = Body(...),
):
    """Greffier records a manual ballot count when the electronic count
    is unavailable (PPTX slide 18 fallback path).

    MVP scope: persist the input as an audit-tagged note attached to
    the VoteResult so the PV can reference it. Does NOT bypass the
    chain-of-evidence — the electronic count remains canonical when
    available, and a discrepancy between manual + electronic surfaces
    in the audit log for human review.

    Request body (validated minimally — full Pydantic schema in a
    follow-up slice):
      - vote_config_id : str (24-char hex)
      - counts         : {"POUR": int, "CONTRE": int, "ABSTENTION": int, "NPV": int}
      - justification  : str (why a manual count was needed)
    """
    return await VoteController(_accept_language(request)).create_manual_tally(
        request, body,
    )


@router.get("/detail/resolution_active")
async def detail_resolution_active(request: Request, session_id: str = Query(..., min_length=12)):
    return await VoteController(_accept_language(request)).detail_resolution_active(request, session_id)


# ---- FSM ----
@router.post("/open/vote")
async def open_vote(request: Request, payload: VoteStateTransitionRequest):
    return await VoteController(_accept_language(request)).open(request, payload)


@router.post("/suspend/vote")
async def suspend_vote(request: Request, payload: VoteStateTransitionRequest):
    return await VoteController(_accept_language(request)).suspend(request, payload)


@router.post("/close/vote")
async def close_vote(request: Request, payload: VoteStateTransitionRequest):
    return await VoteController(_accept_language(request)).close(request, payload)


@router.post("/validate/vote_result")
async def validate_vote_result(request: Request, payload: VoteStateTransitionRequest):
    return await VoteController(_accept_language(request)).validate(request, payload)


@router.post("/change_type/vote")
async def change_type_vote(request: Request, payload: VoteChangeTypeLiveRequest):
    return await VoteController(_accept_language(request)).change_type_live(request, payload)


# ---- ballot ----
@router.post("/create/vote_ballot")
async def cast_vote_ballot(request: Request, payload: BallotCastRequest):
    return await VoteController(_accept_language(request)).cast_ballot(request, payload)


# ---- result ----
@router.get("/detail/vote_result")
async def detail_vote_result(request: Request, vote_config_id: str = Query(..., min_length=12)):
    return await VoteController(_accept_language(request)).detail_result(request, vote_config_id)


# ---- PV export (procès-verbal) ----
@router.post("/export/pv")
async def export_pv(request: Request, payload: VoteExportPvRequest):
    return await VoteController(_accept_language(request)).export_pv(request, payload)


# ---- proxy ----
@router.post("/assign/vote_proxy")
async def assign_vote_proxy(request: Request, payload: ProxyAssignRequest):
    return await VoteController(_accept_language(request)).assign_proxy(request, payload)


@router.post("/revoke/vote_proxy")
async def revoke_vote_proxy(request: Request, payload: ProxyRevokeRequest):
    return await VoteController(_accept_language(request)).revoke_proxy(request, payload)


@router.get("/list/vote_proxy")
async def list_vote_proxy(request: Request, session_id: str = Query(..., min_length=12)):
    return await VoteController(_accept_language(request)).list_proxies(request, session_id)


@router.get("/list/proxy_self")
async def list_proxy_self(request: Request, session_id: str = Query(..., min_length=12)):
    return await VoteController(_accept_language(request)).list_proxy_self(request, session_id)


@router.get("/list/proxy_granted_by_me")
async def list_proxy_granted_by_me(
    request: Request,
    session_id: str = Query(..., min_length=12),
):
    """Proxies the caller has GRANTED — powers the "Donner pouvoir"
    tile (lets the sénateur see + revoke active grants they've made)."""
    return await VoteController(_accept_language(request)).list_proxy_granted_by_me(
        request, session_id,
    )
