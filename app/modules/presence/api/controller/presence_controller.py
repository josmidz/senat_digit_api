"""PresenceController — handler layer for the presence slice."""

from __future__ import annotations

from typing import Any, Dict

from beanie import PydanticObjectId
from fastapi import HTTPException, Request, status

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.presence.enums.presence_enum import EPresenceMethod
from app.modules.presence.schemas.presence_schema import (
    PresenceMarkManualRequest,
    PresenceSignBiometricRequest,
    PresenceSignNfcRequest,
    PresenceSignRequest,
)
from app.modules.presence.services.presence_service import PresenceService


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


class PresenceController:
    def __init__(self, accept_language: str = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self._service = PresenceService(accept_language)

    async def _org_id(self, request: Request) -> PydanticObjectId:
        # Reads from `request.state.user["sys_organization_id"]` — the
        # auth middleware never sets a flat `user_organization_id`.
        from app.modules.core.utils.request_state import current_user_org_id
        return current_user_org_id(request)

    async def _user_id(self, request: Request) -> PydanticObjectId:
        from app.modules.core.utils.request_state import current_user_id
        return current_user_id(request)

    # ---- ESIGN — MVP ----
    async def sign_self(self, request: Request, payload: PresenceSignRequest) -> Dict[str, Any]:
        org_id = await self._org_id(request)
        user_id = await self._user_id(request)
        try:
            sig = await self._service.sign(
                sys_organization_id=org_id,
                session_id=payload.session_id,
                sys_user_id=user_id,
                method=EPresenceMethod.ESIGN,
                device_id_str=payload.device_id_str,
                signature_hash=payload.signature_hash,
                geolocation_lat=payload.geolocation_lat,
                geolocation_lon=payload.geolocation_lon,
            )
        except ValueError as exc:
            msg = str(exc)
            code = status.HTTP_404_NOT_FOUND if "introuvable" in msg else status.HTTP_409_CONFLICT
            raise _http(code, msg) from exc
        return {"status_code": 201, "data": await sig.get_formated_data(self.accept_language)}

    # ---- v1.1 stubs (return 501) ----
    async def sign_self_biometric(self, request: Request, payload: PresenceSignBiometricRequest):
        raise _http(
            status.HTTP_501_NOT_IMPLEMENTED,
            "Signature par empreinte digitale disponible en v1.1.",
        )

    async def sign_self_nfc(self, request: Request, payload: PresenceSignNfcRequest):
        raise _http(
            status.HTTP_501_NOT_IMPLEMENTED,
            "Signature par badge NFC disponible en v1.1.",
        )

    async def mark_manual(self, request: Request, payload: PresenceMarkManualRequest):
        raise _http(
            status.HTTP_501_NOT_IMPLEMENTED,
            "Pointage manuel par le greffier disponible en v1.1.",
        )

    # ---- read ----
    async def list_self(self, request: Request) -> Dict[str, Any]:
        user_id = await self._user_id(request)
        rows = await self._service.list_for_self(user_id)
        return {
            "status_code": 200,
            "data": [await r.get_formated_data(self.accept_language) for r in rows],
        }

    async def list_for_session(self, request: Request, session_id: str) -> Dict[str, Any]:
        try:
            PydanticObjectId(session_id)
        except Exception as exc:
            raise _http(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        rows = await self._service.list_for_session(session_id)
        return {
            "status_code": 200,
            "data": [await r.get_formated_data(self.accept_language) for r in rows],
        }
