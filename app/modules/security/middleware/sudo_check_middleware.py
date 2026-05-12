import json
from typing import Any, Optional
from fastapi import Request, status
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.modules.auth.enums.mfa import MFaFlag
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.keys import RedisKeys
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.generator.generator_service import GeneratorService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.redis.redis_service import AppRedisService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.auth.enums.common import MessageCategory
from app.modules.core.enums.type_enum import OutputDataType
from app.modules.security.enums.security_enum import (
    EConfigSudoActionTypeFlag,
    ESudoActionAccessTargetedTypeFlag,
    ESudoActionAccessTypeFlag,
)
from app.modules.core.utils.asgi_utils import (
    build_receive_with_cached_body,
    get_cached_body,
    has_cached_body,
)


class SudoActionCheckMiddleware:
    """
    Middleware that enforces sudo validation for RBAC endpoints flagged as
    `is_sudo_action` or `is_sudo_group_action`.
    """

    # Routes that should be excluded from sudo checking
    EXCLUDED_ROUTES = [
        "/api/v1/sudo-actions/",
        "/api/v1/websocket/",
        "/api/v1/ng-websocket/",
        "/api/v1/websocket-service/",
    ]

    # Methods that should bypass sudo checking
    BYPASS_METHODS = {"OPTIONS", "HEAD"}

    def __init__(self, app: ASGIApp):
        self.app = app

    async def _resolve_rbac_endpoint(self, current_path: str, accept_language: str):
        """Fetch RBAC endpoint metadata for the given URL path."""
        generic_service = GenericService(accept_language)

        candidate_paths = []
        if current_path:
            candidate_paths.append(current_path)
            trimmed_path = current_path.rstrip("/")
            if trimmed_path and trimmed_path != current_path:
                candidate_paths.append(trimmed_path)

        for path in candidate_paths:
            endpoint = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ENDPOINT,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=accept_language,
                query={"filter__url": path},
            )
            if endpoint:
                return endpoint

        return None

    def _resolve_sudo_action_types(self, rbac_endpoint: dict) -> list[str]:
        """Return all sudo action types enabled on this endpoint."""
        if not rbac_endpoint:
            return []

        sudo_types = []
        if bool(rbac_endpoint.get("is_sudo_action", False)):
            sudo_types.append(EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value)
        if bool(rbac_endpoint.get("is_sudo_group_action", False)):
            sudo_types.append(EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value)
        if bool(rbac_endpoint.get("is_sudo_delegated_action", False)):
            sudo_types.append(EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION.value)
        if bool(rbac_endpoint.get("is_sudo_group_cross_validation_action", False)):
            sudo_types.append(
                EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION.value
            )
        if bool(rbac_endpoint.get("is_sudo_group_inter_organization_validation_action", False)):
            sudo_types.append(
                EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION.value
            )

        return sudo_types

    async def _is_sudo_enabled_for_organization(self, accept_language: str, organization_id: str) -> bool:
        """Check if CFG_SUDO_ACTION_SETUP is enabled for the organization."""
        generic_service = GenericService(accept_language)
        sudo_setup = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SUDO_ACTION_SETUP,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=accept_language,
            query={
                "filter__sys_organization_id": organization_id,
                "filter__is_enabled": True,
            },
        )
        return bool(sudo_setup)

    async def _is_endpoint_sudo_enabled_for_organization(
        self,
        accept_language: str,
        organization_id: str,
        endpoint_id: str,
        sudo_action_types: list[str],
    ) -> dict[str, Any]:
        """
        Resolve endpoint sudo enablement for organization and return:
        - is_enabled
        - selected_sudo_action_type (priority based)
        - cfg_organization_sudo_action (selected CFG_ORGANIZATION_SUDO_ACTION row)
        """
        result: dict[str, Any] = {
            "is_enabled": False,
            "selected_sudo_action_type": None,
            "cfg_organization_sudo_action": None,
            "available_sudo_action_types": [],
        }

        if not endpoint_id or not sudo_action_types:
            return result

        ordered_sudo_action_types = self._get_sudo_action_type_priority(
            sudo_action_types
        )
        result["available_sudo_action_types"] = ordered_sudo_action_types

        generic_service = GenericService(accept_language)
        for sudo_action_type in ordered_sudo_action_types:
            org_endpoint_sudo = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=accept_language,
                query={
                    "filter__sys_organization_id": organization_id,
                    "filter__rbac_endpoint_id": endpoint_id,
                    "filter__sudo_action_type": sudo_action_type,
                    "filter__is_enabled": True,
                },
            )
            if org_endpoint_sudo:
                result["is_enabled"] = True
                result["selected_sudo_action_type"] = sudo_action_type
                result["cfg_organization_sudo_action"] = org_endpoint_sudo
                return result

        return result

    @staticmethod
    def _get_sudo_action_type_priority(sudo_action_types: list[str]) -> list[str]:
        """
        Priority order:
        - inter_connected > cross > grouped > delegated > simple sudo
        """
        priority_order = [
            EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION.value,
            EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION.value,
            EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value,
            EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION.value,
            EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value,
        ]
        ordered = [item for item in priority_order if item in sudo_action_types]
        remaining = [item for item in sudo_action_types if item not in ordered]
        return ordered + remaining

    async def _fetch_user_group_ids(
        self,
        accept_language: str,
        organization_id: str,
        user_id: str,
    ) -> set[str]:
        """Fetch all sudo/rls security groups containing the user."""
        generic_service = GenericService(accept_language)
        group_memberships = await generic_service.fetch_data_from_collection(
            collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
            all_data=True,
            page=0,
            limit=100000,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=accept_language,
            query={
                "filter__sys_organization_id": organization_id,
                "filter__sys_user_id": user_id,
                "filter__is_activated": True,
            },
        )
        group_ids: set[str] = set()
        for membership in group_memberships or []:
            group_id = membership.get("ref_sudo_rls_security_group_id", None)
            if group_id:
                group_ids.add(str(group_id))
        return group_ids

    @staticmethod
    def _is_access_entry_matching_user(
        access_entry: dict[str, Any],
        user_id: str,
        user_group_ids: set[str],
    ) -> bool:
        """Check whether a CFG_SUDO_ACTION_ACCESS entry applies to the user."""
        targeted_type = access_entry.get("targeted_type", "")
        targeted_id = str(access_entry.get("targeted_id", ""))
        if not targeted_id:
            return False

        if (
            targeted_type == ESudoActionAccessTargetedTypeFlag.USER.value
            and targeted_id == str(user_id)
        ):
            return True

        if (
            targeted_type
            == ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value
            and targeted_id in user_group_ids
        ):
            return True

        return False

    @staticmethod
    def _is_user_or_group_target(access_entry: dict[str, Any]) -> bool:
        """Only USER and SUDO_RLS_SECURITY_GROUP targets are eligible validators."""
        targeted_type = access_entry.get("targeted_type", "")
        targeted_id = str(access_entry.get("targeted_id", "")).strip()
        return bool(targeted_id) and targeted_type in {
            ESudoActionAccessTargetedTypeFlag.USER.value,
            ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value,
        }

    async def _fetch_sudo_action_access_records(
        self,
        accept_language: str,
        organization_id: str,
        sudo_action_access_type: str,
        cfg_organization_sudo_action_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Fetch CFG_SUDO_ACTION_ACCESS rows by type and optional action binding."""
        generic_service = GenericService(accept_language)
        query: dict[str, Any] = {
            "filter__sys_organization_id": organization_id,
            "filter__sudo_action_access_type": sudo_action_access_type,
            "filter__is_activated": True,
        }
        if cfg_organization_sudo_action_id is not None:
            query["filter__cfg_organization_sudo_action_id"] = cfg_organization_sudo_action_id

        data = await generic_service.fetch_data_from_collection(
            collection_key=CollectionKey.CFG_SUDO_ACTION_ACCESS,
            all_data=True,
            page=0,
            limit=100000,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=accept_language,
            query=query,
        )
        return data or []

    async def _is_user_allowed_for_delegated_validation(
        self,
        accept_language: str,
        organization_id: str,
        user_id: str,
        cfg_organization_sudo_action_id: str,
    ) -> bool:
        """
        Delegated validation permissions:
        - GLOBAL_ACCESS (direct user or group membership)
        - DELEGATED_ACCESS linked to cfg_organization_sudo_action_id
        """
        user_group_ids = await self._fetch_user_group_ids(
            accept_language=accept_language,
            organization_id=organization_id,
            user_id=user_id,
        )

        global_access_records = await self._fetch_sudo_action_access_records(
            accept_language=accept_language,
            organization_id=organization_id,
            sudo_action_access_type=ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value,
        )
        delegated_access_records = await self._fetch_sudo_action_access_records(
            accept_language=accept_language,
            organization_id=organization_id,
            sudo_action_access_type=ESudoActionAccessTypeFlag.DELEGATED_ACCESS.value,
            cfg_organization_sudo_action_id=cfg_organization_sudo_action_id,
        )

        allowed_records = (global_access_records or []) + (delegated_access_records or [])
        return any(
            self._is_access_entry_matching_user(record, user_id, user_group_ids)
            for record in allowed_records
        )

    async def _has_group_action_validator_configuration(
        self,
        accept_language: str,
        organization_id: str,
        cfg_organization_sudo_action_id: str,
    ) -> bool:
        """
        Grouped action can be initiated only when at least one eligible validator exists:
        - GLOBAL_ACCESS (user or security group)
        - GROUPED_ACCESS linked to cfg_organization_sudo_action_id
        """
        global_access_records = await self._fetch_sudo_action_access_records(
            accept_language=accept_language,
            organization_id=organization_id,
            sudo_action_access_type=ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value,
        )
        grouped_access_records = await self._fetch_sudo_action_access_records(
            accept_language=accept_language,
            organization_id=organization_id,
            sudo_action_access_type=ESudoActionAccessTypeFlag.GROUPED_ACCESS.value,
            cfg_organization_sudo_action_id=cfg_organization_sudo_action_id,
        )

        return any(
            self._is_user_or_group_target(record)
            for record in (global_access_records or []) + (grouped_access_records or [])
        )

    async def _extract_totp_and_instruction_id(
        self,
        request: Request,
        scope: Scope,
        receive: Receive,
    ):
        """Extract totp and instruction_id from headers/query/body."""
        totp = (
            request.headers.get("X-Sudo-Totp-Key", "").strip()
            or request.query_params.get("totp", "").strip()
        )
        instruction_id = request.query_params.get("instruction_id", "").strip()

        # Try JSON body only when needed
        if not totp or not instruction_id:
            try:
                raw = await get_cached_body(scope, receive)
                if raw:
                    payload = json.loads(raw.decode("utf-8"))
                    if isinstance(payload, dict):
                        if not totp:
                            totp = str(payload.get("totp", "")).strip()
                        if not instruction_id:
                            instruction_id = str(payload.get("instruction_id", "")).strip()
            except Exception:
                # Ignore parsing issues; fallback to current values
                pass

        return totp, instruction_id

    async def _verify_user_totp(self, user_id: str, totp: str, accept_language: str) -> bool:
        """Validate provided totp against user's SYCAMORE_2FA_APP secret."""
        if not totp:
            return False

        generic_service = GenericService(accept_language)

        mfa = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.REF_MFAS,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=accept_language,
            query={
                "filter__is_activated": True,
                "filter__flag": MFaFlag.SYCAMORE_2FA_APP.value,
            },
            sort={"created_at": -1},
        )
        if not mfa or not mfa.get("id"):
            return False

        user_mfa = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_USER_MFA,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=accept_language,
            query={
                "filter__is_activated": True,
                "filter__sys_user_id": user_id,
                "filter__ref_mfa_id": mfa.get("id"),
            },
            sort={"created_at": -1},
        )
        if not user_mfa or not user_mfa.get("secret"):
            return False

        return GeneratorService.verify_totp_code(user_mfa.get("secret"), totp)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        try:
            accept_language = request.headers.get(
                "accept-language", DEFAULT_LANGUAGE
            ).split(",")[0].strip()

            current_path = request.url.path

            # Skip excluded routes
            if any(current_path.startswith(route) for route in self.EXCLUDED_ROUTES):
                await self.app(scope, receive, send)
                return

            # Skip non-action methods
            if request.method in self.BYPASS_METHODS:
                await self.app(scope, receive, send)
                return

            # Check whether this endpoint requires sudo/sudo-group validation
            rbac_endpoint = await self._resolve_rbac_endpoint(current_path, accept_language)
            is_sudo_action = bool((rbac_endpoint or {}).get("is_sudo_action", False))
            is_sudo_group_action = bool((rbac_endpoint or {}).get("is_sudo_group_action", False))
            is_sudo_delegated_action = bool((rbac_endpoint or {}).get("is_sudo_delegated_action", False))
            is_sudo_group_cross_validation_action = bool((rbac_endpoint or {}).get("is_sudo_group_cross_validation_action", False))
            is_sudo_group_inter_organization_validation_action = bool((rbac_endpoint or {}).get("is_sudo_group_inter_organization_validation_action", False))
            is_sudo_protected = (
                is_sudo_action
                or is_sudo_group_action
                or is_sudo_delegated_action
                or is_sudo_group_cross_validation_action
                or is_sudo_group_inter_organization_validation_action
            )

            DebugService.app_debug_print(
                f"\n[SUDO CHECK] URL={current_path} "
                f"RBAC_FOUND={bool(rbac_endpoint)} "
                f"is_sudo_action={is_sudo_action} "
                f"is_sudo_group_action={is_sudo_group_action} "
                f"is_sudo_delegated_action={is_sudo_delegated_action} "
                f"is_sudo_group_cross_validation_action={is_sudo_group_cross_validation_action} "
                f"is_sudo_group_inter_organization_validation_action={is_sudo_group_inter_organization_validation_action}\n",
                True,
            )

            # Not a sudo-protected endpoint, continue.
            if not is_sudo_protected:
                await self.app(scope, receive, send)
                return

            # Get user info from request state (set by AuthByPassMiddleware)
            user_details = getattr(request.state, "user", None)
            if not user_details:
                DebugService.app_debug_print(
                    "\n[SUDO CHECK] No user in request.state\n", True
                )
                message = ResponseService.get_response_message(
                    MessageCategory.COMMON, "AUTHENTICATION_REQUIRED", accept_language
                )
                response = JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "detail": message or "Authentication required for sudo action",
                        "error": "AUTHENTICATION_REQUIRED",
                        "status_code": 401,
                    },
                )
                await response(scope, receive, send)
                return

            user_id = user_details.get("id", None)
            if not user_id:
                message = ResponseService.get_response_message(
                    MessageCategory.COMMON, "INVALID_USER_ACCOUNT", accept_language
                )
                response = JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "detail": message or "Invalid user account",
                        "error": "INVALID_USER_ACCOUNT",
                        "status_code": 401,
                    },
                )
                await response(scope, receive, send)
                return

            organization_id = user_details.get("sys_organization_id", None)
            if isinstance(organization_id, dict):
                organization_id = organization_id.get("id", None) or organization_id.get(
                    "_id", None
                )
            if not organization_id:
                message = ResponseService.get_response_message(
                    MessageCategory.COMMON, "INVALID_USER_ACCOUNT", accept_language
                )
                response = JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "detail": message or "Invalid user organization",
                        "error": "INVALID_USER_ORGANIZATION",
                        "status_code": 401,
                    },
                )
                await response(scope, receive, send)
                return

            # 1) Organization-level sudo setup switch
            org_sudo_enabled = await self._is_sudo_enabled_for_organization(
                accept_language=accept_language,
                organization_id=str(organization_id),
            )
            if not org_sudo_enabled:
                DebugService.app_debug_print(
                    f"\n[SUDO CHECK] Skipped: CFG_SUDO_ACTION_SETUP disabled for org={organization_id}\n",
                    True,
                )
                await self.app(scope, receive, send)
                return

            # 2) Organization endpoint-level sudo switch by sudo_action_type
            endpoint_sudo_types = self._resolve_sudo_action_types(rbac_endpoint or {})
            endpoint_id = (rbac_endpoint or {}).get("id", "")
            endpoint_sudo_resolution = await self._is_endpoint_sudo_enabled_for_organization(
                accept_language=accept_language,
                organization_id=str(organization_id),
                endpoint_id=str(endpoint_id),
                sudo_action_types=endpoint_sudo_types,
            )
            if not endpoint_sudo_resolution.get("is_enabled", False):
                DebugService.app_debug_print(
                    f"\n[SUDO CHECK] Skipped: endpoint={endpoint_id} not enabled in CFG_ORGANIZATION_SUDO_ACTION for org={organization_id} (types={endpoint_sudo_types})\n",
                    True,
                )
                await self.app(scope, receive, send)
                return

            selected_sudo_action_type = endpoint_sudo_resolution.get(
                "selected_sudo_action_type", ""
            )
            selected_org_sudo_action = endpoint_sudo_resolution.get(
                "cfg_organization_sudo_action", {}
            ) or {}
            selected_org_sudo_action_id_raw = selected_org_sudo_action.get(
                "id", None
            ) or selected_org_sudo_action.get("_id", None)
            selected_org_sudo_action_id = (
                str(selected_org_sudo_action_id_raw).strip()
                if selected_org_sudo_action_id_raw is not None
                else ""
            )
            DebugService.app_debug_print(
                f"\n[SUDO CHECK] Resolved org sudo action type={selected_sudo_action_type} cfg_organization_sudo_action_id={selected_org_sudo_action_id}\n",
                True,
            )

            selected_is_sudo_action = (
                selected_sudo_action_type
                == EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value
            )
            selected_is_sudo_group_action = (
                selected_sudo_action_type
                == EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value
            )
            selected_is_sudo_delegated_action = (
                selected_sudo_action_type
                == EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION.value
            )
            selected_is_sudo_group_cross_validation_action = (
                selected_sudo_action_type
                == EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION.value
            )
            selected_is_sudo_group_inter_organization_validation_action = (
                selected_sudo_action_type
                == EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION.value
            )

            # Group-action precondition: at least one eligible validator exists.
            if selected_is_sudo_group_action:
                if not selected_org_sudo_action_id:
                    response = JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "detail": "Grouped sudo action is misconfigured for this endpoint.",
                            "error": "SUDO_GROUP_ACTION_MISCONFIGURED",
                            "status_code": 403,
                            "is_sudo_required": False,
                            "resolved_sudo_action_type": selected_sudo_action_type,
                        },
                    )
                    await response(scope, receive, send)
                    return

                has_group_validator_configuration = (
                    await self._has_group_action_validator_configuration(
                        accept_language=accept_language,
                        organization_id=str(organization_id),
                        cfg_organization_sudo_action_id=selected_org_sudo_action_id,
                    )
                )
                if not has_group_validator_configuration:
                    response = JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "detail": (
                                "Missing global/grouped validators configuration for grouped sudo action."
                            ),
                            "error": "SUDO_GROUP_VALIDATORS_MISSING",
                            "status_code": 403,
                            "is_sudo_required": False,
                            "resolved_sudo_action_type": selected_sudo_action_type,
                        },
                    )
                    await response(scope, receive, send)
                    return

            # Require instruction key header for sudo-protected endpoints
            sudo_instruction_key = request.headers.get("X-Sudo-Instruction-Key", None)
            if not sudo_instruction_key:
                message = ResponseService.get_response_message(
                    MessageCategory.COMMON,
                    "NO_SUDO_ACTION_INSTRUCTION",
                    accept_language,
                )
                response = JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": message or "Missing X-Sudo-Instruction-Key header",
                        "error": "SUDO_INSTRUCTION_KEY_REQUIRED",
                        "status_code": 403,
                        # Include sudo flags so the frontend can trigger the
                        # correct sudo verification flow even when its local
                        # RBAC cache is stale (endpoint was updated after login).
                        "is_sudo_required": True,
                        "is_sudo_action": selected_is_sudo_action,
                        "is_sudo_group_action": selected_is_sudo_group_action,
                        "is_sudo_delegated_action": selected_is_sudo_delegated_action,
                        "is_sudo_group_cross_validation_action": selected_is_sudo_group_cross_validation_action,
                        "is_sudo_group_inter_organization_validation_action": selected_is_sudo_group_inter_organization_validation_action,
                        "resolved_sudo_action_type": selected_sudo_action_type,
                        "cfg_organization_sudo_action_id": selected_org_sudo_action_id,
                    },
                )
                await response(scope, receive, send)
                return

            DebugService.app_debug_print(
                f"\n[SUDO CHECK] Method={request.method} URL={current_path} "
                f"Instruction-Key={sudo_instruction_key}\n",
                True,
            )

            # Build Redis key matching initiate_sudo_action format
            sudo_redis_key = RedisKeys.format_key(
                RedisKeys.SUDO_ACTION,
                instruction_id=f"{user_id}_{sudo_instruction_key}",
            )

            DebugService.app_debug_print(
                f"\n[SUDO CHECK] Looking up Redis key: {sudo_redis_key}\n", True
            )

            saved_data = await AppRedisService.get_str_redis_value(sudo_redis_key)
            if not saved_data:
                DebugService.app_debug_print(
                    "\n[SUDO CHECK] Key NOT FOUND in Redis (expired or invalid)\n",
                    True,
                )
                message = ResponseService.get_response_message(
                    MessageCategory.COMMON,
                    "SUDO_ACTION_NOT_FOUND",
                    accept_language,
                )
                response = JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": message or "Sudo action not found or expired. Please re-initiate.",
                        "error": "SUDO_ACTION_EXPIRED",
                        "status_code": 403,
                    },
                )
                await response(scope, receive, send)
                return

            data = json.loads(saved_data)
            stored_status = data.get("status", "unknown")

            DebugService.app_debug_print(
                f"\n[SUDO CHECK] Found in Redis. Status={stored_status}\n", True
            )

            if stored_status != "validated":
                totp, instruction_id = await self._extract_totp_and_instruction_id(
                    request,
                    scope,
                    receive,
                )

                if instruction_id and instruction_id != sudo_instruction_key:
                    response = JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "detail": "Provided instruction_id does not match X-Sudo-Instruction-Key.",
                            "error": "SUDO_INSTRUCTION_MISMATCH",
                            "status_code": 403,
                        },
                    )
                    await response(scope, receive, send)
                    return

                if stored_status in ("pending_verification", "pending") and totp:
                    if selected_is_sudo_delegated_action and not selected_org_sudo_action_id:
                        response = JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            content={
                                "detail": "Delegated sudo action is misconfigured for this endpoint.",
                                "error": "SUDO_DELEGATED_ACTION_MISCONFIGURED",
                                "status_code": 403,
                            },
                        )
                        await response(scope, receive, send)
                        return

                    if selected_is_sudo_delegated_action and selected_org_sudo_action_id:
                        can_validate_delegated = (
                            await self._is_user_allowed_for_delegated_validation(
                                accept_language=accept_language,
                                organization_id=str(organization_id),
                                user_id=str(user_id),
                                cfg_organization_sudo_action_id=selected_org_sudo_action_id,
                            )
                        )
                        if not can_validate_delegated:
                            response = JSONResponse(
                                status_code=status.HTTP_403_FORBIDDEN,
                                content={
                                    "detail": "You are not allowed to validate this delegated sudo action.",
                                    "error": "SUDO_DELEGATED_VALIDATION_ACCESS_DENIED",
                                    "status_code": 403,
                                },
                            )
                            await response(scope, receive, send)
                            return

                    is_totp_valid = await self._verify_user_totp(user_id, totp, accept_language)
                    DebugService.app_debug_print(
                        f"\n[SUDO CHECK] Pending status + TOTP provided. TOTP valid={is_totp_valid}\n",
                        True,
                    )
                    if not is_totp_valid:
                        message = ResponseService.get_response_message(
                            MessageCategory.EXCEPTIONS,
                            "INVALID_TOTP_CODE",
                            accept_language,
                        )
                        response = JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            content={
                                "detail": message or "Invalid TOTP code.",
                                "error": "INVALID_TOTP_CODE",
                                "status_code": 403,
                            },
                        )
                        await response(scope, receive, send)
                        return
                else:
                    message = ResponseService.get_response_message(
                        MessageCategory.COMMON,
                        "SUDO_ACTION_NOT_VALIDATED",
                        accept_language,
                    )
                    response = JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "detail": message or "Sudo action has not been validated yet.",
                            "error": "SUDO_ACTION_PENDING",
                            "status_code": 403,
                        },
                    )
                    await response(scope, receive, send)
                    return

            # Optional URL consistency check
            stored_url = data.get("url", "")
            sudo_url_header = request.headers.get("X-Sudo-Url", "")
            if stored_url and sudo_url_header:
                stored_base = stored_url.split("?")[0]
                header_base = sudo_url_header.split("?")[0]
                if stored_base != header_base:
                    DebugService.app_debug_print(
                        f"\n[SUDO CHECK] URL mismatch: stored={stored_base} header={header_base}\n",
                        True,
                    )
                    message = ResponseService.get_response_message(
                        MessageCategory.COMMON,
                        "SUDO_ACTION_URL_MISMATCH",
                        accept_language,
                    )
                    response = JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "detail": message or "Sudo action URL does not match the request.",
                            "error": "SUDO_URL_MISMATCH",
                            "status_code": 403,
                        },
                    )
                    await response(scope, receive, send)
                    return

            # One-time use key after successful validation
            await AppRedisService.remove_redis_value(sudo_redis_key)

            DebugService.app_debug_print(
                "\n[SUDO CHECK] Validation successful. Key removed from Redis.\n",
                True,
            )

            # Expose resolved sudo context for downstream handlers (generic CRUD).
            # This allows centralized grouped/cross validation queuing without
            # re-implementing endpoint-level resolution in each controller.
            request.state.sudo_resolution = {
                "is_sudo_required": True,
                "resolved_sudo_action_type": selected_sudo_action_type,
                "cfg_organization_sudo_action_id": selected_org_sudo_action_id,
                "sys_organization_id": str(organization_id),
                "rbac_endpoint_id": str(endpoint_id),
                "sudo_instruction_key": str(sudo_instruction_key),
            }

            downstream_receive = build_receive_with_cached_body(scope) if has_cached_body(scope) else receive
            await self.app(scope, downstream_receive, send)
            return

        except Exception as e:
            DebugService.app_debug_print(
                f"\n[SUDO CHECK] Error during sudo check: {e}\n", True
            )
            accept_language = getattr(request, "headers", {}).get(
                "accept-language", DEFAULT_LANGUAGE
            )
            if isinstance(accept_language, str):
                accept_language = accept_language.split(",")[0].strip()
            message = ResponseService.get_response_message(
                MessageCategory.ERRORS, "UNEXPECTED_ERROR", accept_language
            )
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": message or "An error occurred during sudo validation",
                    "error": "SUDO_CHECK_ERROR",
                    "status_code": 500,
                },
            )
            await response(scope, receive, send)
