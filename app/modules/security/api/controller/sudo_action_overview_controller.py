from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request, status
from beanie import PydanticObjectId

from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.types.response import CustomJSONResponse
from app.modules.security.enums.security_enum import (
    EConfigSudoActionTypeFlag,
    ESudoActionAccessTypeFlag,
)


class SudoActionOverviewController(DebugService, ResponseService, ConverterService, AuthenticatedService):
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        super().__init__(accept_language)

    # ─── FETCH SUDO ACTIONS OVERVIEW ──────────────────────────────────────────

    async def fetch_sudo_actions_overview(self, request: Request):
        """
        Build a dashboard overview with:
        - Security group count (RefSudoRlsSecurityGroup)
        - Access type breakdown from CfgSudoActionAccess (global / grouped / delegated)
        - Per sudo-action-type stats from CfgOrganizationSudoAction (total vs enabled)
        - Calculated security score %
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            org_filter = {"filter__sys_organization_id": user_details["sys_organization_id"]}

            # ─── 1. Security group count ──────────────────────────────────
            security_group_count = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP,
                accept_language=self.accept_language,
                query={**org_filter},
                user=user_details,
            )

            # ─── 2. Access type breakdown (CfgSudoActionAccess) ───────────
            access_types = [
                ESudoActionAccessTypeFlag.GLOBAL_ACCESS,
                ESudoActionAccessTypeFlag.GROUPED_ACCESS,
                ESudoActionAccessTypeFlag.DELEGATED_ACCESS,
            ]
            access_breakdown: Dict[str, int] = {}
            total_access_entries = 0
            for at in access_types:
                count = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.CFG_SUDO_ACTION_ACCESS,
                    accept_language=self.accept_language,
                    query={
                        **org_filter,
                        "filter__sudo_action_access_type": at.value,
                    },
                    user=user_details,
                )
                access_breakdown[at.value] = count
                total_access_entries += count

            # ─── 3. Per sudo-action-type stats (CfgOrganizationSudoAction) ─
            action_types = [
                EConfigSudoActionTypeFlag.IS_SUDO_ACTION,
                EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION,
                EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION,
                EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION,
                EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION,
            ]

            permission_stats: List[Dict[str, Any]] = []
            grand_total = 0
            grand_enabled = 0

            for at in action_types:
                total = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                    accept_language=self.accept_language,
                    query={
                        **org_filter,
                        "filter__sudo_action_type": at.value,
                    },
                    user=user_details,
                )
                enabled = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                    accept_language=self.accept_language,
                    query={
                        **org_filter,
                        "filter__sudo_action_type": at.value,
                        "filter__is_enabled": True,
                    },
                    user=user_details,
                )
                pct = round((enabled / total) * 100, 1) if total > 0 else 0.0
                permission_stats.append({
                    "sudo_action_type": at.value,
                    "total": total,
                    "enabled": enabled,
                    "disabled": total - enabled,
                    "enabled_pct": pct,
                })
                grand_total += total
                grand_enabled += enabled

            # ─── 4. Global security score ─────────────────────────────────
            # Score is calculated as:
            #   - 60% weight: ratio of enabled sudo-action permissions
            #   - 25% weight: whether access validators exist (capped at 100%)
            #   - 15% weight: whether security groups exist (capped at 100%)
            if grand_total > 0:
                permission_ratio = (grand_enabled / grand_total) * 100
            else:
                permission_ratio = 0.0

            # Access coverage: having validators assigned is good
            access_score = min(total_access_entries * 10, 100.0)  # cap at 100

            # Group coverage: having security groups is good
            group_score = min(security_group_count * 20, 100.0)  # cap at 100

            security_score = round(
                (permission_ratio * 0.60) +
                (access_score * 0.25) +
                (group_score * 0.15),
                1,
            )

            # ─── 5. Build response ────────────────────────────────────────
            overview = {
                "security_group_count": security_group_count,
                "access_breakdown": {
                    "global_access": access_breakdown.get(ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value, 0),
                    "grouped_access": access_breakdown.get(ESudoActionAccessTypeFlag.GROUPED_ACCESS.value, 0),
                    "delegated_access": access_breakdown.get(ESudoActionAccessTypeFlag.DELEGATED_ACCESS.value, 0),
                    "total": total_access_entries,
                },
                "permission_stats": permission_stats,
                "permission_summary": {
                    "grand_total": grand_total,
                    "grand_enabled": grand_enabled,
                    "grand_disabled": grand_total - grand_enabled,
                    "grand_enabled_pct": round((grand_enabled / grand_total) * 100, 1) if grand_total > 0 else 0.0,
                },
                "security_score": security_score,
            }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Sudo actions overview fetched successfully",
                    "data": overview,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
