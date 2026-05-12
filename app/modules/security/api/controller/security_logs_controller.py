import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, Request, status
from starlette.responses import StreamingResponse

from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.enums.type_enum import FormatedOutPut, OutputDataType
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.ops_log.ops_log_service import OpsLogService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.types.response import CustomJSONResponse
from app.modules.security.models.cfg_ops_log_setup.cfg_ops_log_setup_model import CfgOpsLogSetupModel


class SecurityLogsController(DebugService, ResponseService, ConverterService, AuthenticatedService):
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        super().__init__(accept_language)

    # ─── FETCH LOG SETUP ─────────────────────────────────────────────────────

    async def fetch_log_setup(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
    ):
        """Fetch the organization's log setup configuration."""
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_OPS_LOG_SETUP,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={"filter__sys_organization_id": str(user_details['sys_organization_id'])},
                user=user_details,
            )

            if not data:
                # Auto-create setup with is_enabled=False for this organization
                data_instance = CfgOpsLogSetupModel(
                    sys_organization_id=user_details['sys_organization_id'],
                    is_enabled=False,
                    is_create_log_enabled=False,
                    is_read_log_enabled=False,
                    is_update_log_enabled=False,
                    is_delete_log_enabled=False,
                    expiration_days=30,
                    max_expiration_days=150,
                )
                await data_instance.save()
            else:
                data_instance = CfgOpsLogSetupModel(**data)
            formatted = await data_instance.get_formated_data(self.accept_language, output=FormatedOutPut.MINIMAL)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Log setup fetched successfully",
                    "data": formatted,
                },
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"[SecurityLogsController] fetch_log_setup error: {e}", False)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── PATCH LOG SETUP (is_enabled) ────────────────────────────────────────

    async def patch_log_setup_enabled(self, request: Request, body: dict):
        """Update is_enabled on the log setup."""
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            org_id = str(user_details['sys_organization_id'])

            is_enabled = body.get("is_enabled")
            if is_enabled is None:
                raise HTTPException(status_code=400, detail="is_enabled field is required.")

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_OPS_LOG_SETUP,
                output_data_type="default",
                accept_language=self.accept_language,
                query={"filter__sys_organization_id": org_id},
                user=user_details,
            )

            if not data:
                raise HTTPException(status_code=404, detail="Log setup not found for this organization.")

            data_instance = CfgOpsLogSetupModel(**data)
            data_instance.is_enabled = bool(is_enabled)

            # When main flag is disabled, disable all CRUD flags
            if not data_instance.is_enabled:
                data_instance.is_create_log_enabled = False
                data_instance.is_read_log_enabled = False
                data_instance.is_update_log_enabled = False
                data_instance.is_delete_log_enabled = False

            await data_instance.save()

            OpsLogService.invalidate_cache(org_id)

            formatted = await data_instance.get_formated_data(self.accept_language, output=FormatedOutPut.MINIMAL)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Log setup updated successfully",
                    "data": formatted,
                },
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"[SecurityLogsController] patch_log_setup_enabled error: {e}", False)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── PATCH LOG SETUP (CRUD flags) ────────────────────────────────────────

    async def patch_log_setup_crud_flags(self, request: Request, body: dict):
        """Update individual CRUD log flags. Only allowed when main is_enabled is True."""
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            org_id = str(user_details['sys_organization_id'])

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_OPS_LOG_SETUP,
                output_data_type="default",
                accept_language=self.accept_language,
                query={"filter__sys_organization_id": org_id},
                user=user_details,
            )

            if not data:
                raise HTTPException(status_code=404, detail="Log setup not found for this organization.")

            data_instance = CfgOpsLogSetupModel(**data)

            if not data_instance.is_enabled:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot update CRUD flags while main logging is disabled."
                )

            crud_flag_keys = [
                "is_create_log_enabled",
                "is_read_log_enabled",
                "is_update_log_enabled",
                "is_delete_log_enabled",
            ]

            updated = False
            for key in crud_flag_keys:
                if key in body:
                    setattr(data_instance, key, bool(body[key]))
                    updated = True

            if not updated:
                raise HTTPException(
                    status_code=400,
                    detail="At least one CRUD flag must be provided (is_create_log_enabled, is_read_log_enabled, is_update_log_enabled, is_delete_log_enabled)."
                )

            await data_instance.save()

            OpsLogService.invalidate_cache(org_id)

            formatted = await data_instance.get_formated_data(self.accept_language, output=FormatedOutPut.MINIMAL)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "CRUD log flags updated successfully",
                    "data": formatted,
                },
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"[SecurityLogsController] patch_log_setup_crud_flags error: {e}", False)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── PATCH LOG SETUP (expiration_days) ───────────────────────────────────

    async def patch_log_setup_expiration(self, request: Request, body: dict):
        """Update expiration_days on the log setup. Min 5, Max 150."""
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            org_id = str(user_details['sys_organization_id'])

            expiration_days = body.get("expiration_days")
            if expiration_days is None:
                raise HTTPException(status_code=400, detail="expiration_days field is required.")

            expiration_days = int(expiration_days)
            if expiration_days < 5:
                expiration_days = 5
                # expiration_days = 10
            if expiration_days > 150:
                expiration_days = 150

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_OPS_LOG_SETUP,
                output_data_type="default",
                accept_language=self.accept_language,
                query={"filter__sys_organization_id": org_id},
                user=user_details,
            )

            if not data:
                raise HTTPException(status_code=404, detail="Log setup not found for this organization.")

            data_instance = CfgOpsLogSetupModel(**data)
            data_instance.expiration_days = expiration_days
            await data_instance.save()

            OpsLogService.invalidate_cache(org_id)

            formatted = await data_instance.get_formated_data(self.accept_language, output=FormatedOutPut.MINIMAL)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Log expiration updated successfully",
                    "data": formatted,
                },
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"[SecurityLogsController] patch_log_setup_expiration error: {e}", False)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── FETCH LOGS (PAGINATED) ──────────────────────────────────────────────

    async def fetch_logs(
        self,
        request: Request,
        crud_type: Optional[str] = None,
        collection_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ):
        """Fetch paginated organization CRUD logs."""
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            org_id = str(user_details['sys_organization_id'])

            result = await OpsLogService.get_logs_paginated(
                sys_organization_id=org_id,
                crud_type=crud_type,
                collection_name=collection_name,
                skip=skip,
                limit=limit,
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Logs fetched successfully",
                    "data": result,
                },
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"[SecurityLogsController] fetch_logs error: {e}", False)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── SSE STREAM (REAL-TIME LOGS) ─────────────────────────────────────────

    async def stream_logs_sse(self, request: Request, token: Optional[str] = None):
        """
        Server-Sent Events endpoint for real-time log streaming.
        Polls the database every 3 seconds for new log entries.
        Accepts token as query param since EventSource cannot send headers.
        """
        try:
            # SSE via EventSource cannot set Authorization header,
            # so we accept a token query param and inject it into the request headers.
            if token and not request.headers.get("authorization"):
                # Build a mutable scope so downstream auth reads the token
                request._headers = request.headers.mutablecopy()
                request._headers["authorization"] = f"Bearer {token}"
            user_details = await self.get_user_info(request, self.accept_language)
            org_id = str(user_details['sys_organization_id'])
        except Exception:
            raise HTTPException(status_code=401, detail="Unauthorized")

        async def event_generator():
            last_check = datetime.now(timezone.utc)
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    new_logs = await OpsLogService.get_recent_logs(
                        sys_organization_id=org_id,
                        since_utc=last_check,
                        limit=20,
                    )

                    if new_logs:
                        last_check = datetime.now(timezone.utc)
                        for log_entry in reversed(new_logs):
                            data = json.dumps(log_entry, default=str)
                            yield f"data: {data}\n\n"
                    else:
                        # Send a keep-alive comment
                        yield ": heartbeat\n\n"

                except Exception as exc:
                    logging.warning(f"[SSE] Error fetching logs: {exc}")
                    yield ": error\n\n"

                await asyncio.sleep(3)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
