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
from app.modules.security.enums.security_enum import ERlsAccessTypeFlag


class RlsOverviewController(DebugService, ResponseService, ConverterService, AuthenticatedService):
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        super().__init__(accept_language)

    # ─── FETCH RLS OVERVIEW ───────────────────────────────────────────────────

    async def fetch_rls_overview(self, request: Request):
        """
        Build a dashboard overview with:
        - Security group count (RefSudoRlsSecurityGroup)
        - Access type breakdown from CfgRlsAccess (global / revoked / custom)
        - Permission stats from CfgOrganizationRls (total, enabled, strict mode)
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

            # ─── 2. Access type breakdown (CfgRlsAccess) ─────────────────
            access_types = [
                ERlsAccessTypeFlag.GLOBAL_ACCESS,
                ERlsAccessTypeFlag.REVOKED_ACCESS,
                ERlsAccessTypeFlag.CUSTOM_ACCESS,
            ]
            access_breakdown: Dict[str, int] = {}
            total_access_entries = 0
            for at in access_types:
                count = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.CFG_RLS_ACCESS,
                    accept_language=self.accept_language,
                    query={
                        **org_filter,
                        "filter__rls_access_type": at.value,
                    },
                    user=user_details,
                )
                access_breakdown[at.value] = count
                total_access_entries += count

            # ─── 3. Permission stats (CfgOrganizationRls) ────────────────
            total_permissions = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.CFG_ORGANIZATION_RLS,
                accept_language=self.accept_language,
                query={**org_filter},
                user=user_details,
            )

            enabled_permissions = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.CFG_ORGANIZATION_RLS,
                accept_language=self.accept_language,
                query={
                    **org_filter,
                    "filter__is_enabled": True,
                },
                user=user_details,
            )

            strict_mode_count = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.CFG_ORGANIZATION_RLS,
                accept_language=self.accept_language,
                query={
                    **org_filter,
                    "filter__is_strict_mode": True,
                },
                user=user_details,
            )

            disabled_permissions = total_permissions - enabled_permissions
            enabled_pct = round((enabled_permissions / total_permissions) * 100, 1) if total_permissions > 0 else 0.0
            strict_mode_pct = round((strict_mode_count / total_permissions) * 100, 1) if total_permissions > 0 else 0.0

            permission_stats = {
                "total": total_permissions,
                "enabled": enabled_permissions,
                "disabled": disabled_permissions,
                "enabled_pct": enabled_pct,
                "strict_mode": strict_mode_count,
                "strict_mode_pct": strict_mode_pct,
            }

            # ─── 4. Global security score ─────────────────────────────────
            # Score is calculated as:
            #   - 60% weight: ratio of enabled RLS permissions
            #   - 25% weight: whether access entries exist (capped at 100%)
            #   - 15% weight: whether security groups exist (capped at 100%)
            if total_permissions > 0:
                permission_ratio = (enabled_permissions / total_permissions) * 100
            else:
                permission_ratio = 0.0

            # Access coverage: having access entries assigned is good
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
                    "global_access": access_breakdown.get(ERlsAccessTypeFlag.GLOBAL_ACCESS.value, 0),
                    "revoked_access": access_breakdown.get(ERlsAccessTypeFlag.REVOKED_ACCESS.value, 0),
                    "custom_access": access_breakdown.get(ERlsAccessTypeFlag.CUSTOM_ACCESS.value, 0),
                    "total": total_access_entries,
                },
                "permission_stats": permission_stats,
                "permission_summary": {
                    "grand_total": total_permissions,
                    "grand_enabled": enabled_permissions,
                    "grand_disabled": disabled_permissions,
                    "grand_enabled_pct": enabled_pct,
                },
                "security_score": security_score,
            }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "RLS overview fetched successfully",
                    "data": overview,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
