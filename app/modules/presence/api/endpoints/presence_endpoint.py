"""Presence endpoints — `/verb/resource` per CLAUDE.md.

Mounted at `/api/v1` (no prefix).

| Method | Path                                  | Permission                   | Status |
|--------|---------------------------------------|------------------------------|--------|
| POST   | /create/presence_signature            | presence.sign_self           | MVP    |
| POST   | /create/presence_signature_biometric  | presence.sign_self_biometric | 501 (v1.1) |
| POST   | /create/presence_signature_nfc        | presence.sign_self_nfc       | 501 (v1.1) |
| POST   | /mark/presence_manual                 | presence.mark_manual         | 501 (v1.1) |
| GET    | /list/presence_self                   | presence.read_self           | MVP    |
| GET    | /list/presence                        | presence.read                | MVP    |
"""

from fastapi import APIRouter, Query, Request

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.presence.api.controller.presence_controller import PresenceController
from app.modules.presence.schemas.presence_schema import (
    PresenceMarkManualRequest,
    PresenceSignBiometricRequest,
    PresenceSignNfcRequest,
    PresenceSignRequest,
)


router = APIRouter()


def _accept_language(request: Request) -> str:
    return request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()


@router.post("/create/presence_signature")
async def sign_presence(request: Request, payload: PresenceSignRequest):
    return await PresenceController(_accept_language(request)).sign_self(request, payload)


@router.post("/create/presence_signature_biometric")
async def sign_presence_biometric(request: Request, payload: PresenceSignBiometricRequest):
    return await PresenceController(_accept_language(request)).sign_self_biometric(request, payload)


@router.post("/create/presence_signature_nfc")
async def sign_presence_nfc(request: Request, payload: PresenceSignNfcRequest):
    return await PresenceController(_accept_language(request)).sign_self_nfc(request, payload)


@router.post("/mark/presence_manual")
async def mark_presence_manual(request: Request, payload: PresenceMarkManualRequest):
    return await PresenceController(_accept_language(request)).mark_manual(request, payload)


@router.get("/list/presence_self")
async def list_presence_self(request: Request):
    return await PresenceController(_accept_language(request)).list_self(request)


@router.get("/list/presence")
async def list_presence(request: Request, session_id: str = Query(..., min_length=12)):
    return await PresenceController(_accept_language(request)).list_for_session(request, session_id)
