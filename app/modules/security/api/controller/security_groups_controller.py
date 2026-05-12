from typing import Any, Dict, List, Optional

from fastapi import Body, HTTPException, Request, status
from pydantic import BaseModel

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
from app.modules.security.models.ref_sudo_rls_security_group.ref_sudo_rls_security_group_model import RefSudoRlsSecurityGroupModel


# ─── Request Body Schemas ─────────────────────────────────────────────────────

class GroupBulkUsersRequest(BaseModel):
    """Body schema for adding multiple users to a security group."""
    ref_sudo_rls_security_group_id: str
    sys_user_ids: List[str]


# ─── Controller ───────────────────────────────────────────────────────────────

class SecurityGroupsController(DebugService, ResponseService, ConverterService, AuthenticatedService):
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        super().__init__(accept_language)

    # ─── FETCH ALL SECURITY GROUPS ────────────────────────────────────────────

    async def fetch_groups(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
        all_data: Optional[bool] = False,
        page: Optional[int] = 0,
        limit: Optional[int] = 10,
    ):
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params)
            sort = request.query_params.get("sort", {"created_at": -1})

            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={**query_params},
                user=user_details,
                sort=sort,
            )

            formatted_data = []
            for group in data:
                group_instance = RefSudoRlsSecurityGroupModel(**group)
                formatted_group = await group_instance.get_formated_data(self.accept_language, output=FormatedOutPut.MINIMAL)
                formatted_data.append({
                    **formatted_group,
                })

            extra_data = {}
            if not all_data:
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP,
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
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── FETCH ONE SECURITY GROUP ─────────────────────────────────────────────

    async def fetch_one_group(
        self,
        request: Request,
        item_id: str,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
    ):
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={"filter___id": item_id},
                user=user_details,
            )

            if not data:
                message = self.get_response_message(
                    MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language
                )
                raise HTTPException(status_code=404, detail=message)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": data,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── DELETE A SECURITY GROUP ──────────────────────────────────────────────

    async def delete_group(
        self,
        request: Request,
        item_id: str,
    ):
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            # First, delete all user memberships associated with this group
            await self.generic_service.hard_delete_with_query_data_from_collection(
                collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
                query={"filter__ref_sudo_rls_security_group_id": item_id},
                accept_language=self.accept_language,
                delete_multiple=True,
            )

            # Then delete the group itself
            success = await self.generic_service.hard_delete_data_from_collection(
                collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP,
                item_id=item_id,
                accept_language=self.accept_language,
            )

            if success:
                message = self.get_response_message(
                    MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language
                )
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    },
                )
            else:
                message = self.get_response_message(
                    MessageCategory.ERRORS, "FAILLURE_OPERATION_COMPLETED", self.accept_language
                )
                raise HTTPException(status_code=404, detail=message)

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── ADD MULTIPLE USERS TO A SECURITY GROUP ──────────────────────────────

    async def add_group_bulk_users(
        self,
        request: Request,
        body: dict = Body(...),
    ):
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            validated_body = GroupBulkUsersRequest.model_validate(body)

            group_id = validated_body.ref_sudo_rls_security_group_id
            sys_user_ids = validated_body.sys_user_ids

            # Verify the group exists
            group = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter___id": group_id},
                user=user_details,
            )

            if not group:
                message = self.get_response_message(
                    MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language
                )
                raise HTTPException(status_code=404, detail=message)

            # Fetch existing users in this group to avoid duplicates
            existing_group_users = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter__ref_sudo_rls_security_group_id": group_id},
                user=user_details,
            )

            existing_user_ids = set()
            if existing_group_users:
                for gu in existing_group_users:
                    existing_user_ids.add(str(gu.get("sys_user_id", "")))

            # Add each user that doesn't already exist in the group
            added_count = 0
            for sys_user_id in sys_user_ids:
                if str(sys_user_id) in existing_user_ids:
                    continue

                await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER.value,
                    data={
                        "ref_sudo_rls_security_group_id": group_id,
                        "sys_user_id": sys_user_id,
                        "sys_organization_id": user_details["sys_organization_id"],
                    },
                    accept_language=self.accept_language,
                    user=user_details,
                )
                added_count += 1

            message = self.get_response_message(
                MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language
            )
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "data": {
                        "added_count": added_count,
                        "skipped_count": len(sys_user_ids) - added_count,
                    },
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── FETCH USERS OF A SECURITY GROUP ──────────────────────────────────────

    async def fetch_group_users(
        self,
        request: Request,
        group_id: str,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
        all_data: Optional[bool] = False,
        page: Optional[int] = 0,
        limit: Optional[int] = 10,
    ):
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params)
            sort = request.query_params.get("sort", {"created_at": -1})

            # Force filter by the target group
            query_params["filter__ref_sudo_rls_security_group_id"] = group_id

            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={**query_params},
                user=user_details,
                sort=sort,
            )

            extra_data = {}
            if not all_data:
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
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
                    "data": data,
                    **extra_data,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
