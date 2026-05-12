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
from app.modules.security.enums.security_enum import EConfigSudoActionTypeFlag, ESudoActionAccessTypeFlag, ESudoActionAccessTargetedTypeFlag
from app.modules.security.models.cfg_sudo_action_access.cfg_sudo_action_access_model import CfgSudoActionAccessModel


class GroupedValidatorsController(DebugService, ResponseService, ConverterService, AuthenticatedService):
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        self.rbac_role_service = RbacRoleService(accept_language)
        super().__init__(accept_language)

    # ─── FETCH GROUPED VALIDATORS (RBAC TITLE TREE) ──────────────────────────

    async def fetch_grouped_validators(
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
            format_error = format_exception("error fetch_grouped_validators ", e)
            self.app_debug_print(
                f"Error in fetch_grouped_validators: > 1 {format_error} {exception_line_info(e)}", True
            )
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
