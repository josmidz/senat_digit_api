from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request, status
from beanie import PydanticObjectId

from app.modules.auth.enums.common import MessageCategory
from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.enums.type_enum import OutputDataType, FormatedOutPut
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.types.response import CustomJSONResponse
from app.modules.core.utils.helpers.line_helper import exception_line_info, format_exception
from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
from app.modules.security.enums.security_enum import ERlsAccessTypeFlag, ESudoActionAccessTargetedTypeFlag
from app.modules.security.models.cfg_rls_access.cfg_rls_access_model import CfgRlsAccessModel
from app.modules.security.models.ref_sudo_rls_security_group.ref_sudo_rls_security_group_model import RefSudoRlsSecurityGroupModel


class RlsSettingsController(DebugService, ResponseService, ConverterService, AuthenticatedService):
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        self.rbac_role_service = RbacRoleService(accept_language)
        super().__init__(accept_language)

    # ─── FETCH FORMATED PERMISSIONS (RBAC TITLE TREE) ─────────────────────────

    async def fetch_formated_permissions(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
        all_data: Optional[bool] = False,
        page: Optional[int] = 0,
        limit: Optional[int] = 10,
    ):
        """
        Fetch all CFG_ORGANIZATION_RLS for the org,
        format them into an RBAC title tree using build_rbac_hierarchy.
        Each permission node includes:
        - is_enabled
        - is_strict_mode
        - linked users/groups from CFG_RLS_ACCESS
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            org_id = user_details['sys_organization_id']

            # ── 1. Fetch all CFG_ORGANIZATION_RLS for this org ────────────────
            org_rls_configs = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_ORGANIZATION_RLS,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={"filter__sys_organization_id": org_id},
                user=user_details,
            )

            self.app_debug_print(f"org_rls_configs count: {len(org_rls_configs)}", False)

            # ── 2. For each org RLS config, resolve permission + title ────────
            data_for_hierarchy = []

            for orc in org_rls_configs:
                rbac_permission_id = orc.get('rbac_permission_id')
                if not rbac_permission_id:
                    continue

                # Fetch the RBAC_PERMISSION
                permission = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    query={"filter___id": str(rbac_permission_id)},
                    user=user_details,
                )
                if not permission:
                    continue

                # Extract rbac_title_id from the permission
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    rbac_title_id = permission.get('rbac_title_id', {}).get('display_value')
                else:
                    rbac_title_id = permission.get('rbac_title_id')

                if not rbac_title_id:
                    continue

                # Fetch the RBAC_TITLE
                rbac_title = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_TITLE,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    query={"filter___id": str(rbac_title_id)},
                    user=user_details,
                )
                if not rbac_title:
                    continue

                # ── 3. Fetch linked CFG_RLS_ACCESS for this RLS config ───────
                orc_id = orc.get('_id') or orc.get('id')
                linked_access_records = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_RLS_ACCESS,
                    all_data=True,
                    page=0,
                    limit=100000,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=self.accept_language,
                    query={
                        "filter__cfg_organization_rls_id": str(orc_id),
                        "filter__sys_organization_id": org_id,
                    },
                    user=user_details,
                )

                # Format each linked access record
                formatted_access = []
                for record in linked_access_records:
                    try:
                        instance = CfgRlsAccessModel(**record)
                        formatted_item = await instance.get_formated_data(
                            self.accept_language, output=FormatedOutPut.FULL
                        )
                        formatted_access.append(formatted_item)
                    except Exception as fmt_err:
                        self.app_debug_print(
                            f"Error formatting linked RLS access: {format_exception('fmt', fmt_err)}", True
                        )
                        formatted_access.append(record)

                # ── 4. Build data item for hierarchy ──────────────────────────
                is_enabled = orc.get('is_enabled', False)
                is_strict_mode = orc.get('is_strict_mode', False)

                data_for_hierarchy.append({
                    'rbac_title': rbac_title,
                    'id': permission.get('id'),
                    'rbac_permission': permission,
                    'is_enabled': is_enabled,
                    'is_strict_mode': is_strict_mode,
                    'cfg_organization_rls_id': str(orc_id),
                    'linked_validators': formatted_access,
                })

            # ── 5. Build RBAC title tree hierarchy ────────────────────────────
            hierarchy = await self.rbac_role_service.build_rbac_hierarchy(
                data_for_hierarchy, output_data_type
            )

            self.app_debug_print(f"hierarchy len: {len(hierarchy)}", False)

            extra_data = {
                "max": len(data_for_hierarchy),
                "limit": limit,
            }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": hierarchy,
                    **extra_data,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            format_error = format_exception("error fetch_formated_permissions ", e)
            self.app_debug_print(
                f"Error in fetch_formated_permissions: > 1 {format_error} {exception_line_info(e)}", True
            )
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── FETCH AVAILABLE USERS (NOT IN GLOBAL WHITELIST/BLACKLIST) ───────────

    async def fetch_available_users(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
        all_data: Optional[bool] = False,
        page: Optional[int] = 0,
        limit: Optional[int] = 10,
    ):
        """
        Fetch org users who are NOT already in the global whitelist/blacklist.
        Excludes users present in CFG_RLS_ACCESS with rls_access_type
        GLOBAL_ACCESS or REVOKED_ACCESS.
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params)

            query_params["filter__sys_organization_id"] = user_details['sys_organization_id']

            # Step 1: Fetch all RLS access records with GLOBAL_ACCESS or REVOKED_ACCESS targeting users
            global_user_entries = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_RLS_ACCESS,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__targeted_type": ESudoActionAccessTargetedTypeFlag.USER.value,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )

            # Collect user IDs that are in global whitelist/blacklist
            excluded_user_ids = set()
            for v in global_user_entries:
                rls_type = v.get("rls_access_type")
                if rls_type in [ERlsAccessTypeFlag.GLOBAL_ACCESS.value, ERlsAccessTypeFlag.REVOKED_ACCESS.value]:
                    targeted_id = v.get("targeted_id")
                    if targeted_id:
                        excluded_user_ids.add(str(targeted_id))

            # Also exclude users who are members of groups in global whitelist/blacklist
            global_group_entries = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_RLS_ACCESS,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__targeted_type": ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )

            for gv in global_group_entries:
                rls_type = gv.get("rls_access_type")
                if rls_type in [ERlsAccessTypeFlag.GLOBAL_ACCESS.value, ERlsAccessTypeFlag.REVOKED_ACCESS.value]:
                    group_id = gv.get("targeted_id")
                    if not group_id:
                        continue
                    group_users = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
                        all_data=True,
                        page=0,
                        limit=100000,
                        output_data_type=OutputDataType.DEFAULT.value,
                        accept_language=self.accept_language,
                        query={"filter__ref_sudo_rls_security_group_id": str(group_id)},
                        user=user_details,
                    )
                    for gu in group_users:
                        uid = gu.get("sys_user_id")
                        if uid:
                            excluded_user_ids.add(str(uid))

            # Step 2: Fetch all org users
            all_org_users = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.SYS_USER,
                all_data=True,
                page=0,
                limit=1000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={**query_params},
                user=user_details,
            )

            # Step 3: Filter out users in global whitelist/blacklist
            available_users = []
            for user in all_org_users:
                user_id = str(user.get("_id", user.get("id", "")))
                if user_id not in excluded_user_ids:
                    available_users.append(user)

            # Apply pagination manually
            total = len(available_users)
            if not all_data:
                start = page * limit
                end = start + limit
                available_users = available_users[start:end]

            extra_data = {}
            if not all_data:
                extra_data = {"max": total, "limit": limit}

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": available_users,
                    **extra_data,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            format_error = format_exception(f"error fetch_available_users ", e)
            self.app_debug_print(f"Error in fetch_available_users: > 1 {format_error} {exception_line_info(e)}", True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── FETCH AVAILABLE GROUPS (NOT IN GLOBAL WHITELIST/BLACKLIST) ──────────

    async def fetch_available_groups(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
        all_data: Optional[bool] = False,
        page: Optional[int] = 0,
        limit: Optional[int] = 10,
    ):
        """
        Fetch security groups NOT already in the global whitelist/blacklist.
        Excludes groups present in CFG_RLS_ACCESS with rls_access_type
        GLOBAL_ACCESS or REVOKED_ACCESS.
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params)

            query_params["filter__sys_organization_id"] = user_details['sys_organization_id']

            # Step 1: Fetch all RLS access records targeting groups with GLOBAL/REVOKED
            existing_entries = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_RLS_ACCESS,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__targeted_type": ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )

            excluded_group_ids = set()
            for v in existing_entries:
                rls_type = v.get("rls_access_type")
                if rls_type in [ERlsAccessTypeFlag.GLOBAL_ACCESS.value, ERlsAccessTypeFlag.REVOKED_ACCESS.value]:
                    targeted_id = v.get("targeted_id")
                    if targeted_id:
                        excluded_group_ids.add(str(targeted_id))

            # Step 2: Fetch org security groups
            all_org_groups = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP,
                all_data=True,
                page=0,
                limit=1000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={**query_params},
                user=user_details,
            )

            # Step 3: Filter out groups in global whitelist/blacklist
            available_groups = []
            for group in all_org_groups:
                group_id = str(group.get("_id", group.get("id", "")))
                if group_id not in excluded_group_ids:
                    # Format the group data
                    try:
                        group_instance = RefSudoRlsSecurityGroupModel(**group)
                        formatted_group = await group_instance.get_formated_data(self.accept_language, output=FormatedOutPut.MINIMAL)
                        available_groups.append(formatted_group)
                    except Exception:
                        available_groups.append(group)

            # Apply pagination manually
            total = len(available_groups)
            if not all_data:
                start = page * limit
                end = start + limit
                available_groups = available_groups[start:end]

            extra_data = {}
            if not all_data:
                extra_data = {"max": total, "limit": limit}

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": available_groups,
                    **extra_data,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            format_error = format_exception(f"error fetch_available_groups ", e)
            self.app_debug_print(f"Error in fetch_available_groups: > 1 {format_error} {exception_line_info(e)}", True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
