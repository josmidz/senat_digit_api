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
from app.modules.security.enums.security_enum import ERlsAccessTypeFlag, ESudoActionAccessTargetedTypeFlag
from app.modules.security.models.cfg_rls_access.cfg_rls_access_model import CfgRlsAccessModel
from app.modules.security.models.ref_sudo_rls_security_group.ref_sudo_rls_security_group_model import RefSudoRlsSecurityGroupModel


class WhitelistBlacklistController(DebugService, ResponseService, ConverterService, AuthenticatedService):
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        super().__init__(accept_language)

    # ─── FETCH ALL WHITELIST / BLACKLIST ENTRIES ─────────────────────────────

    async def fetch_whitelist_rls(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
        all_data: Optional[bool] = False,
        page: Optional[int] = 0,
        limit: Optional[int] = 10,
    ):
        """
        Fetch all CfgRlsAccess records (whitelist = GLOBAL_ACCESS, blacklist = REVOKED_ACCESS).
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params)
            sort = request.query_params.get("sort", {"created_at": -1})

            query_params["filter__sys_organization_id"] = user_details['sys_organization_id']

            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_RLS_ACCESS,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={**query_params},
                user=user_details,
                sort=sort,
            )

            formatted_data = []
            for item in data:
                self.app_debug_print(f"item whitelist rls : {item}", False)
                instance = CfgRlsAccessModel(**item)
                formatted_item = await instance.get_formated_data(self.accept_language, output=FormatedOutPut.FULL)
                formatted_data.append(formatted_item)

            extra_data = {}
            if not all_data:
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.CFG_RLS_ACCESS,
                    accept_language=self.accept_language,
                    query={**query_params},
                    user=user_details,
                )
                extra_data = {"max": max_data, "limit": limit}

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": formatted_data,
                    **extra_data,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            format_error = format_exception(f"error fetch_whitelist_rls ", e)
            self.app_debug_print(f"Error in fetch_whitelist_rls: > 1 {format_error} {exception_line_info(e)}", True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── FETCH AVAILABLE USERS (NOT YET IN WHITELIST/BLACKLIST) ──────────────

    async def fetch_available_users(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
        all_data: Optional[bool] = False,
        page: Optional[int] = 0,
        limit: Optional[int] = 10,
    ):
        """
        Fetch org users who are NOT already in the whitelist/blacklist.
        1. Get all CfgRlsAccess with targeted_type=USER
        2. Get all org users
        3. Exclude users already in the list
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params)

            query_params["filter__sys_organization_id"] = user_details['sys_organization_id']

            # Step 1a: Fetch all RLS access records targeting users directly
            existing_user_entries = await self.generic_service.fetch_data_from_collection(
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

            existing_user_ids = set()
            for v in existing_user_entries:
                targeted_id = v.get("targeted_id")
                if targeted_id:
                    existing_user_ids.add(str(targeted_id))

            # Step 1b: Fetch all RLS access records targeting groups,
            # then fetch the members of those groups to also exclude them
            existing_group_entries = await self.generic_service.fetch_data_from_collection(
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

            for gv in existing_group_entries:
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
                        existing_user_ids.add(str(uid))

            # Step 2: Fetch org users
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

            # Step 3: Filter out users already in the list
            available_users = []
            for user in all_org_users:
                user_id = str(user.get("_id", user.get("id", "")))
                if user_id not in existing_user_ids:
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

    # ─── FETCH AVAILABLE GROUPS (NOT YET IN WHITELIST/BLACKLIST) ─────────────

    async def fetch_available_groups(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
        all_data: Optional[bool] = False,
        page: Optional[int] = 0,
        limit: Optional[int] = 10,
    ):
        """
        Fetch security groups NOT already in the whitelist/blacklist.
        1. Get all CfgRlsAccess with targeted_type=SUDO_RLS_SECURITY_GROUP
        2. Get all org security groups
        3. Exclude groups already in the list
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params)

            query_params["filter__sys_organization_id"] = user_details['sys_organization_id']

            # Step 1: Fetch all RLS access records targeting groups
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

            existing_group_ids = set()
            for v in existing_entries:
                targeted_id = v.get("targeted_id")
                if targeted_id:
                    existing_group_ids.add(str(targeted_id))

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

            # Step 3: Filter out groups already in the list
            available_groups = []
            for group in all_org_groups:
                group_id = str(group.get("_id", group.get("id", "")))
                if group_id not in existing_group_ids:
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
