from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Query, Request, status
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
from app.modules.security.enums.security_enum import EConfigSudoActionTypeFlag, ESudoActionAccessTypeFlag, ESudoActionAccessTargetedTypeFlag
from app.modules.security.models.cfg_sudo_action_access.cfg_sudo_action_access_model import CfgSudoActionAccessModel
from app.modules.security.models.ref_sudo_rls_security_group.ref_sudo_rls_security_group_model import RefSudoRlsSecurityGroupModel
from app.modules.core.models.sys_organization.sys_organization_model import SysOrganizationModel


class ValidationConfigurationsController(DebugService, ResponseService, ConverterService, AuthenticatedService):
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        self.rbac_role_service = RbacRoleService(accept_language)
        super().__init__(accept_language)

    # ─── FETCH CONFIG VALIDATORS ──────────────────────────

    async def fetch_config_validators(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Fetch all CFG_ORGANIZATION_SUDO_ACTION for the org,
        format them into an RBAC title tree using build_rbac_hierarchy.
        Each permission node includes:
        - is_enabled based on sudo_action_type
        - linked groups/users from CFG_SUDO_ACTION_ACCESS
        """
        try:

            user_details = await self.get_user_info(request, self.accept_language)

            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params)

            sudo_action_access_type = query_params.get("filter__sudo_action_access_type", ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value)
            rbac_permission_id = query_params.get("filter__rbac_permission_id", None)
            config_sudo_action_type_flag = query_params.get("filter__config_sudo_action_type_flag", None) #EConfigSudoActionTypeFlag

            cfg_organization_sudo_action = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sudo_action_type": config_sudo_action_type_flag,
                    "filter__rbac_permission_id": rbac_permission_id,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )

            if not cfg_organization_sudo_action:
                message = self.get_response_message(MessageCategory.ERRORS, "SUDO_ACTION_ORG_CONFIG_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)


            validators = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_SUDO_ACTION_ACCESS,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    "filter__sudo_action_access_type": sudo_action_access_type,
                    "filter__cfg_organization_sudo_action_id": cfg_organization_sudo_action['id'],
                },
                user=user_details,
            )

            formatted_validators = []
            for record in validators:
                try:
                    instance = CfgSudoActionAccessModel(**record)
                    formatted_item = await instance.get_formated_data(
                        self.accept_language, output=FormatedOutPut.FULL
                    )
                    formatted_validators.append(formatted_item)
                except Exception as fmt_err:
                    self.app_debug_print(
                        f"Error formatting linked validator: {format_exception('fmt', fmt_err)}", True
                    )
                    formatted_validators.append(record) 


            extra_data = {
                "max": 0,
                "limit": limit,
            }
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.CFG_SUDO_ACTION_ACCESS,
                    accept_language=self.accept_language,
                    query={
                        "filter__sudo_action_access_type": sudo_action_access_type,
                        "filter__cfg_organization_sudo_action_id": cfg_organization_sudo_action['id'],
                    },
                    user=user_details,
                )
                extra_data = {
                    "max": max_data,
                    "limit": limit,
                }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": formatted_validators,
                    **extra_data,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            format_error = format_exception("error fetch_configurations ", e)
            self.app_debug_print(
                f"Error in fetch_configurations: > 1 {format_error} {exception_line_info(e)}", True
            )
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
    # ─── FETCH VALIDATION CONFIGURATIONS (RBAC TITLE TREE) ──────────────────────────

    async def fetch_configurations(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
        all_data: Optional[bool] = False,
        page: Optional[int] = 0,
        limit: Optional[int] = 10,
    ):
        """
        Fetch all CFG_ORGANIZATION_SUDO_ACTION for the org,
        format them into an RBAC title tree using build_rbac_hierarchy.
        Each permission node includes:
        - is_enabled based on sudo_action_type
        - linked groups/users from CFG_SUDO_ACTION_ACCESS
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            org_id = user_details['sys_organization_id']

            # ── 1. Fetch all CFG_ORGANIZATION_SUDO_ACTION for this org ────────
            org_sudo_actions = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={"filter__sys_organization_id": org_id},
                user=user_details,
            )

            self.app_debug_print(f"org_sudo_actions count: {len(org_sudo_actions)}", False)

            # ── 2. For each org sudo action, resolve permission + title ───────
            data_for_hierarchy = []

            for osa in org_sudo_actions:
                rbac_permission_id = osa.get('rbac_permission_id')
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

                # ── 3. Fetch linked CFG_SUDO_ACTION_ACCESS for this action ───
                osa_id = osa.get('_id') or osa.get('id')
                linked_access_records = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_SUDO_ACTION_ACCESS,
                    all_data=True,
                    page=0,
                    limit=100000,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=self.accept_language,
                    query={
                        "filter__cfg_organization_sudo_action_id": str(osa_id),
                        "filter__sys_organization_id": org_id,
                    },
                    user=user_details,
                )

                # Format each linked validator
                formatted_validators = []
                for record in linked_access_records:
                    try:
                        instance = CfgSudoActionAccessModel(**record)
                        formatted_item = await instance.get_formated_data(
                            self.accept_language, output=FormatedOutPut.FULL
                        )
                        formatted_validators.append(formatted_item)
                    except Exception as fmt_err:
                        self.app_debug_print(
                            f"Error formatting linked validator: {format_exception('fmt', fmt_err)}", True
                        )
                        formatted_validators.append(record)

                # ── 4. Determine is_enabled from sudo_action_type ─────────────
                sudo_action_type = osa.get('sudo_action_type', EConfigSudoActionTypeFlag.NONE.value)
                is_enabled = osa.get('is_enabled', False)

                # Build data item for hierarchy
                data_for_hierarchy.append({
                    'rbac_title': rbac_title,
                    'id': permission.get('id'),
                    'rbac_permission': permission,
                    'is_enabled': is_enabled,
                    'sudo_action_type': sudo_action_type,
                    'cfg_organization_sudo_action_id': str(osa_id),
                    'linked_validators': formatted_validators,
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
            format_error = format_exception("error fetch_configurations ", e)
            self.app_debug_print(
                f"Error in fetch_configurations: > 1 {format_error} {exception_line_info(e)}", True
            )
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")



        # ─── FETCH AVAILABLE USERS (NOT YET GLOBAL VALIDATORS) ───────────────────

    async def fetch_available_users(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
        all_data: Optional[bool] = False,
        page: Optional[int] = 0,
        limit: Optional[int] = 10,
    ):
        """
        Fetch org users who are NOT already in the global validators list.
        1. Get all CfgSudoActionAccess with type=GLOBAL_ACCESS and targeted_type=USER
        2. Get all org users
        3. Exclude users already in the global validators
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params)

            sudo_action_access_type = query_params.get("filter__sudo_action_access_type", ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value)
            rbac_permission_id = query_params.get("filter__rbac_permission_id", None)
            config_sudo_action_type_flag = query_params.get("filter__config_sudo_action_type_flag", None) #EConfigSudoActionTypeFlag

            cfg_organization_sudo_action = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sudo_action_type": config_sudo_action_type_flag,
                    "filter__rbac_permission_id": rbac_permission_id,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )

            if not cfg_organization_sudo_action:
                message = self.get_response_message(MessageCategory.ERRORS, "SUDO_ACTION_ORG_CONFIG_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)


            # Step 1a: Fetch all global validator records targeting users directly
            existing_user_validators = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_SUDO_ACTION_ACCESS,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sudo_action_access_type": sudo_action_access_type,
                    "filter__targeted_type": ESudoActionAccessTargetedTypeFlag.USER.value,
                    "filter__cfg_organization_sudo_action_id": cfg_organization_sudo_action['id'],
                },
                user=user_details,
            )

            existing_user_ids = set()
            for v in existing_user_validators:
                targeted_id = v.get("targeted_id")
                if targeted_id:
                    existing_user_ids.add(str(targeted_id))

            # Step 1b: Fetch all global validator records targeting groups,
            # then fetch the members of those groups to also exclude them
            existing_group_validators = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_SUDO_ACTION_ACCESS,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sudo_action_access_type": sudo_action_access_type,
                    "filter__targeted_type": ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value,
                    "filter__cfg_organization_sudo_action_id": cfg_organization_sudo_action['id'],
                },
                user=user_details,
            )
 

            for gv in existing_group_validators:
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
                query={
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )

            # Step 3: Filter out users already in global validators
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
            format_error = format_exception(f"error fetch_available_users ",e)
            self.app_debug_print(f"Error in fetch_available_users: > 1 {format_error} {exception_line_info(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── FETCH AVAILABLE GROUPS (NOT YET GLOBAL VALIDATORS) ──────────────────

    async def fetch_available_groups(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
        all_data: Optional[bool] = False,
        page: Optional[int] = 0,
        limit: Optional[int] = 10,
    ):
        """
        Fetch security groups NOT already in the global validators list.
        1. Get all CfgSudoActionAccess with type=GLOBAL_ACCESS and targeted_type=SUDO_RLS_SECURITY_GROUP
        2. Get all org security groups
        3. Exclude groups already in the global validators
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params) 

            sudo_action_access_type = query_params.get("filter__sudo_action_access_type", ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value)
            rbac_permission_id = query_params.get("filter__rbac_permission_id", None)
            config_sudo_action_type_flag = query_params.get("filter__config_sudo_action_type_flag", None) #EConfigSudoActionTypeFlag

            cfg_organization_sudo_action = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sudo_action_type": config_sudo_action_type_flag,
                    "filter__rbac_permission_id": rbac_permission_id,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )

            if not cfg_organization_sudo_action:
                message = self.get_response_message(MessageCategory.ERRORS, "SUDO_ACTION_ORG_CONFIG_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # Step 1: Fetch all global validator records targeting groups
            existing_validators = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_SUDO_ACTION_ACCESS,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sudo_action_access_type": sudo_action_access_type,
                    "filter__targeted_type": ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value,
                    "filter__cfg_organization_sudo_action_id": cfg_organization_sudo_action['id'],
                },
                user=user_details,
            )

            existing_group_ids = set()
            for v in existing_validators:
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
                query={
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )

            # Step 3: Filter out groups already in global validators
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
            format_error = format_exception(f"error fetch_available_groups ",e)
            self.app_debug_print(f"Error in fetch_available_groups: > 1 {format_error} {exception_line_info(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    # ─── FETCH AVAILABLE CROSS ORGANIZATIONS (NOT YET CROSS ORGANIZATIONS) ──────────────────

    async def fetch_available_cross_organizations(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
        all_data: Optional[bool] = False,
        page: Optional[int] = 0,
        limit: Optional[int] = 10,
    ):
        """
        Fetch security groups NOT already in the global validators list.
        1. Get all CfgSudoActionAccess with type=GLOBAL_ACCESS and targeted_type=SUDO_RLS_SECURITY_GROUP
        2. Get all org security groups
        3. Exclude groups already in the global validators
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params) 

            organization = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id": user_details['sys_organization_id'],
                },
                user=user_details,
            )

            if not organization:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ORG_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            sudo_action_access_type = query_params.get("filter__sudo_action_access_type", ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value)
            rbac_permission_id = query_params.get("filter__rbac_permission_id", None)
            config_sudo_action_type_flag = query_params.get("filter__config_sudo_action_type_flag", None) #EConfigSudoActionTypeFlag

            cfg_organization_sudo_action = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sudo_action_type": config_sudo_action_type_flag,
                    "filter__rbac_permission_id": rbac_permission_id,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )

            if not cfg_organization_sudo_action:
                message = self.get_response_message(MessageCategory.ERRORS, "SUDO_ACTION_ORG_CONFIG_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # Step 1: Fetch all global validator records targeting groups
            existing_cross_organizations = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_SUDO_ACTION_ACCESS,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sudo_action_access_type": sudo_action_access_type,
                    "filter__targeted_type": ESudoActionAccessTargetedTypeFlag.CROSS_ORGANIZATION.value,
                    "filter__cfg_organization_sudo_action_id": cfg_organization_sudo_action['id'],
                },
                user=user_details,
            )

            existing_cross_organization_ids = set()
            for v in existing_cross_organizations:
                targeted_id = v.get("targeted_id")
                if targeted_id:
                    existing_cross_organization_ids.add(str(targeted_id))

            
            ami_parent_org = True if not organization.get("sys_organization_id", None) else False # if sys_organization_id is null, then it is a parent org

            # Step 2: Fetch org organizations
            all_org_organizations = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                all_data=True,
                page=0,
                limit=1000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sys_organization_id": user_details['sys_organization_id'] if ami_parent_org else organization.get("sys_organization_id", None),
                },
                user=user_details,
            )

            # Step 3: Filter out organizations already in cross validators
            available_organizations = []
            for organization in all_org_organizations:
                organization_id = str(organization.get("_id", organization.get("id", "")))
                if organization_id not in existing_cross_organization_ids:
                    # Format the organization data
                    try:
                        organization_instance = SysOrganizationModel(**organization)
                        formatted_organization = await organization_instance.get_formated_data(self.accept_language, output=FormatedOutPut.MINIMAL)
                        available_organizations.append(formatted_organization)
                    except Exception:
                        available_organizations.append(organization)

            # Apply pagination manually
            total = len(available_organizations)
            if not all_data:
                start = page * limit
                end = start + limit
                available_organizations = available_organizations[start:end]

            extra_data = {}
            if not all_data:
                extra_data = {"max": total, "limit": limit}

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": available_organizations,
                    **extra_data,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            format_error = format_exception(f"error fetch_available_groups ",e)
            self.app_debug_print(f"Error in fetch_available_groups: > 1 {format_error} {exception_line_info(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    # ─── FETCH AVAILABLE INTER CONNECTED ORGANIZATIONS (NOT YET CROSS ORGANIZATIONS) ──────────────────

    async def fetch_available_inter_connected_organizations(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
        all_data: Optional[bool] = False,
        page: Optional[int] = 0,
        limit: Optional[int] = 10,
    ):
        """
        Fetch security groups NOT already in the global validators list.
        1. Get all CfgSudoActionAccess with type=GLOBAL_ACCESS and targeted_type=SUDO_RLS_SECURITY_GROUP
        2. Get all org security groups
        3. Exclude groups already in the global validators
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params) 

            organization = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id": user_details['sys_organization_id'],
                },
                user=user_details,
            )

            if not organization:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ORG_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            sudo_action_access_type = query_params.get("filter__sudo_action_access_type", ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value)
            rbac_permission_id = query_params.get("filter__rbac_permission_id", None)
            config_sudo_action_type_flag = query_params.get("filter__config_sudo_action_type_flag", None) #EConfigSudoActionTypeFlag

            cfg_organization_sudo_action = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sudo_action_type": config_sudo_action_type_flag,
                    "filter__rbac_permission_id": rbac_permission_id,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )

            if not cfg_organization_sudo_action:
                message = self.get_response_message(MessageCategory.ERRORS, "SUDO_ACTION_ORG_CONFIG_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # Step 1: Fetch all global validator records targeting groups
            existing_cross_organizations = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_SUDO_ACTION_ACCESS,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sudo_action_access_type": sudo_action_access_type,
                    "filter__targeted_type": ESudoActionAccessTargetedTypeFlag.INTER_CONNECTED_ORGANIZATION.value,
                    "filter__cfg_organization_sudo_action_id": cfg_organization_sudo_action['id'],
                },
                user=user_details,
            )

            existing_cross_organization_ids = set()
            for v in existing_cross_organizations:
                targeted_id = v.get("targeted_id")
                if targeted_id:
                    existing_cross_organization_ids.add(str(targeted_id))

             
            # Step 2: Fetch org organizations
            # TODO:: FETCH REMOTE INTER CONNECTED ORGANIZATIONS
            all_org_organizations = []

            # Step 3: Filter out organizations already in cross validators
            available_organizations = []
            for organization in all_org_organizations:
                organization_id = str(organization.get("_id", organization.get("id", "")))
                if organization_id not in existing_cross_organization_ids:
                    # Format the organization data
                    try:
                        organization_instance = SysOrganizationModel(**organization)
                        formatted_organization = await organization_instance.get_formated_data(self.accept_language, output=FormatedOutPut.MINIMAL)
                        available_organizations.append(formatted_organization)
                    except Exception:
                        available_organizations.append(organization)

            # Apply pagination manually
            total = len(available_organizations)
            if not all_data:
                start = page * limit
                end = start + limit
                available_organizations = available_organizations[start:end]

            extra_data = {}
            if not all_data:
                extra_data = {"max": total, "limit": limit}

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": available_organizations,
                    **extra_data,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            format_error = format_exception(f"error fetch_available_groups ",e)
            self.app_debug_print(f"Error in fetch_available_groups: > 1 {format_error} {exception_line_info(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")



