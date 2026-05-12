from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
from app.modules.core.utils.helpers.line_helper import format_exception
from app.modules.core.enums.access_level import EUserInfoValidationFlag
from app.modules.core.schemas.user_schema import UserInfoValidation
from bson import ObjectId
from fastapi import Body, Depends, HTTPException, Query, Request,status
from app.db.dao import DAO
from app.modules.auth.enums.common import MessageCategory
from app.modules.core.types.response import CustomJSONResponse
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.encryption.encryption_service import EncryptionService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.model.model_service import ModelService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.security.services.security_validation_service import SecurityValidationService
from app.modules.core.enums.type_enum import EJWTTokenType, EMultipleValidationStatus, EMultipleValidationType, OutputDataType, TranslationStrategy
from app.modules.security.middleware.sudo_action_middleware import sudo_action_middleware
# settings
from app.modules.core.configs.config import settings



class GenericController(DebugService,AuthenticatedService,ResponseService,ConverterService,ModelService):
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.auth.services.token.token_service import TokenService
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        self.generic_service = GenericService(accept_language)
        self.token_service = TokenService(accept_language)
        super().__init__(accept_language)

    @staticmethod
    def _normalize_validation_context(
        context: Optional[Dict[str, Any]] = None,
        *,
        current_validation_request_id: Optional[Any] = None,
        parent_validation_request_id: Optional[Any] = None,
        root_validation_request_id: Optional[Any] = None,
        resolved_sudo_action_type: str = "",
        is_sudo_group_action: bool = False,
    ) -> Dict[str, Any]:
        def normalize(value: Optional[Any]) -> Optional[str]:
            if value is None:
                return None
            normalized = str(value).strip()
            return normalized or None

        normalized_context = {
            "current_validation_request_id": normalize(current_validation_request_id),
            "parent_validation_request_id": normalize(parent_validation_request_id),
            "root_validation_request_id": normalize(root_validation_request_id),
            "resolved_sudo_action_type": str(resolved_sudo_action_type or "").strip(),
            "is_sudo_group_action": bool(is_sudo_group_action),
        }
        if isinstance(context, dict):
            for key in (
                "current_validation_request_id",
                "parent_validation_request_id",
                "root_validation_request_id",
            ):
                if key in context:
                    normalized_context[key] = normalize(context.get(key))
            if "resolved_sudo_action_type" in context:
                normalized_context["resolved_sudo_action_type"] = str(
                    context.get("resolved_sudo_action_type", "") or ""
                ).strip()
            if "is_sudo_group_action" in context:
                normalized_context["is_sudo_group_action"] = bool(
                    context.get("is_sudo_group_action", False)
                )

        if (
            normalized_context["root_validation_request_id"] is None
            and normalized_context["current_validation_request_id"] is not None
        ):
            normalized_context["root_validation_request_id"] = normalized_context[
                "current_validation_request_id"
            ]

        return normalized_context

    def _build_group_validation_response(self, service_result: Any) -> Optional[CustomJSONResponse]:
        """
        Normalize grouped/cross validation queue responses returned by GenericService.
        """
        if not isinstance(service_result, dict):
            return None
        if not service_result.get("_sudo_group_validation", False):
            return None

        validation_context = self._normalize_validation_context(
            service_result.get("validation_context", None),
            current_validation_request_id=service_result.get("validation_request_id", None),
            parent_validation_request_id=service_result.get("parent_validation_request_id", None)
            or service_result.get("ops_validation_request_id", None),
            root_validation_request_id=service_result.get("root_validation_request_id", None),
            resolved_sudo_action_type=service_result.get("resolved_sudo_action_type", ""),
            is_sudo_group_action=True,
        )

        if service_result.get("blocked", False):
            status_code = int(service_result.get("status_code", status.HTTP_403_FORBIDDEN))
            return CustomJSONResponse(
                status_code=status_code,
                content={
                    "status_code": status_code,
                    "success": False,
                    "message": service_result.get("message", "Grouped validation cannot be initiated."),
                    "error": service_result.get("error_code", "SUDO_GROUP_VALIDATION_BLOCKED"),
                    "is_sudo_group_action": True,
                    "data": {
                        "resolved_sudo_action_type": service_result.get("resolved_sudo_action_type", ""),
                        "validation_context": validation_context,
                    },
                    "validation_context": validation_context,
                },
            )

        queued_message = self.get_response_message(
            MessageCategory.SUCCESS,
            "DATA_VALIDATION_QUEUED",
            self.accept_language,
        ) or service_result.get("message", "Validation request queued")
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "message": queued_message,
                "is_sudo_group_action": True,
                "data": {
                    "validation_request_id": service_result.get("validation_request_id", None),
                    "target_document_id": service_result.get("target_document_id", None),
                    "resolved_sudo_action_type": service_result.get("resolved_sudo_action_type", ""),
                    "cfg_organization_sudo_action_id": service_result.get("cfg_organization_sudo_action_id", ""),
                    "parent_validation_request_id": validation_context.get(
                        "parent_validation_request_id"
                    ),
                    "root_validation_request_id": validation_context.get(
                        "root_validation_request_id"
                    ),
                    "validation_context": validation_context,
                },
                "validation_context": validation_context,
            },
        )

    async def add_data(self,request: Request,collection_name: str, data: Dict[str, Any],):
        """
        Endpoint to add a new document to the specified collection.
        """
        try:
            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message',None)
            # sudo_can_proceed = sudo_action.get('can_proceed',True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_400_BAD_REQUEST,
            #             content={
            #                 "status_code": status.HTTP_400_BAD_REQUEST,
            #                 "message": sudo_message,
            #             }
            #         )
            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # data = {
            #     **data,
            #     "created_by_id": user_details['id']
            # }

            # # START VALIDATION PROCESS
            # validation_service = ValidationService(accept_language=self.accept_language)
            # validation_process = await validation_service.validation_process(
            #     request=request,
            #     operation_type=EMultipleValidationType.CREATE,
            #     sudo_action=sudo_action,
            #     collection_name=collection_name,
            #     data=data,
            #     user_details=user_details
            # )

            # if validation_process['is_sudo_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "is_sudo_action":True,
            #                 "message": validation_process['message'],
            #                 "data":validation_process['data']
            #             }
            #         )
            # elif validation_process['is_sudo_group_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "message": validation_process['message'],
            #             }
            #         )
            # else:
            #     # Add data to the collection
            #     item_id = await self.generic_service.add_data_to_collection(collection_key, data)
            #     message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "message": message,
            #                 "item_id":item_id
            #             }
            #         )
            # Add data to the collection
            item_id = await self.generic_service.add_data_to_collection(
                collection_key,
                data,
                accept_language=self.accept_language,
                request=request,
                user=user_details,
            )
            grouped_response = self._build_group_validation_response(item_id)
            if grouped_response:
                return grouped_response
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                        "item_id":item_id,
                        "validation_context": self._normalize_validation_context(),
                    }
                )

        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f" \n\n Exception: {e}\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))


    async def upsert_data(self,request: Request,collection_name: str, data: Dict[str, Any]):
        """
        Endpoint to upsert a new document to the specified collection.
        """
        try:
            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message',None)
            # sudo_can_proceed = sudo_action.get('can_proceed',True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_400_BAD_REQUEST,
            #             content={
            #                 "status_code": status.HTTP_400_BAD_REQUEST,
            #                 "message": sudo_message,
            #             }
            #         )

            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)


            upsert_query = data.get('query',{})
            upsert_data = data.get('data',{})
            self.app_debug_print(f" \n\n upsert_query: {upsert_query}\n\n",True)
            self.app_debug_print(f" \n\n upsert_data: {upsert_data}\n\n",True)
            if not upsert_query or not upsert_data:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_UPSERT_QUERY_OR_DATA", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Check if the data exists in the collection
            # check_data = await self.generic_service.fetch_native_query_one_from_collection(
            #     collection_key=collection_key,
            #     output_data_type=OutputDataType.DEFAULT.value,
            #     accept_language=self.accept_language,
            #     native_query=upsert_query
            # )
            # validation_service = ValidationService(accept_language=self.accept_language)
            # validation_data = {}
            # if not check_data:
            #     validation_data = {
            #         "operation_type":EMultipleValidationType.CREATE,
            #         "sudo_action":sudo_action,
            #         "collection_name":collection_name,
            #         "data":upsert_data,
            #         "user_details":user_details,
            #     }
            # else:
            #     validation_data = {
            #         "operation_type":EMultipleValidationType.UPSERT,
            #         "sudo_action":sudo_action,
            #         "collection_name":collection_name,
            #         "data":upsert_data,
            #         "user_details":user_details,
            #         "target_document_id":check_data['id'],
            #         "upsert_query":upsert_query,
            #     }
            #     # message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
            #     # raise HTTPException(status_code=404, detail=message)
            # validation_process = await validation_service.validation_process(
            #     request=request,
            #     operation_type=validation_data.get("operation_type"),
            #     sudo_action=validation_data.get('sudo_action'),
            #     collection_name=validation_data.get("collection_name"),
            #     data=validation_data.get("data"),
            #     user_details=validation_data.get("user_details"),
            #     target_document_id=validation_data.get("target_document_id") if validation_data.get("target_document_id",None) else None,
            #     upsert_query=validation_data.get("upsert_query") if validation_data.get("upsert_query",None) else None
            # )

            # if validation_process['is_sudo_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "is_sudo_action":True,
            #                 "message": validation_process['message'],
            #                 "data":validation_process['data']
            #             }
            #         )
            # elif validation_process['is_sudo_group_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "message": validation_process['message'],
            #             }
            #         )
            # else:
            #     item_id = await self.generic_service.upsert_data_to_collection(collection_key, upsert_query,upsert_data)
            #     saved_id = item_id if isinstance(item_id,str) else item_id['id']
            #     message = self.get_response_message(MessageCategory.SUCCESS, "SUCCESSFULL_OPERATION_COMPLETED", self.accept_language)
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "message": message,
            #                 "data":saved_id
            #             }
            #         )
            item_id = await self.generic_service.upsert_data_to_collection(
                collection_key,
                upsert_query,
                upsert_data,
                accept_language=self.accept_language,
                request=request,
                user=user_details,
            )
            grouped_response = self._build_group_validation_response(item_id)
            if grouped_response:
                return grouped_response
            saved_id = item_id if isinstance(item_id,str) else item_id['id']
            message = self.get_response_message(MessageCategory.SUCCESS, "SUCCESSFULL_OPERATION_COMPLETED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                        "data":saved_id,
                        "validation_context": self._normalize_validation_context(),
                    }
                )

        except PermissionError as e:
            self.app_debug_print(f" \n\n PermissionError: {e}\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f" \n\n Exception: {e}\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))



   


    async def role_add_data(self,request: Request, data: Dict[str, Any]):
        """
        Endpoint to add a new document to the specified collection.
        """
        try:


            from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            self.app_debug_print(f"\n\nbody : {data}\n\n",True)
            api_consumer_id = api_Consumer['id']
            organization_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter___id": data['rbac_profile_id'],
                },
                user=user_details,
            )
            if not organization_profil:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "ORGANIZATION_PROFIL_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            body_profil_id = data.get('rbac_profile_id',organization_profil['id'])
            sys_organization_id = data.get('sys_organization_id',user_details['sys_organization_id'])
            data_role = {
                **data,
                "sys_organization_id": sys_organization_id,
                "rbac_profile_id":body_profil_id
            }
            # Add data to the collection
            org_admin_role_id = await self.generic_service.add_data_to_collection(CollectionKey.RBAC_ROLE, data_role, user=user_details, request=request)

            # ADD ALL DEFAULT PERMISSIONS
            rbac_role_service = RbacRoleService(self.accept_language)
            await rbac_role_service.create_single_rbac_default_role_permissions(rbac_role_id=org_admin_role_id, body_profil_id=body_profil_id)

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "status_code": status.HTTP_201_CREATED,
                        "message":message,
                    }
                )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


    async def org_add_data(self,request: Request,collection_name: str, data: Dict[str, Any]):
        """
        Endpoint to add a new document to the specified collection.
        """
        try:
            self.app_debug_print(f" \n\n org_add_data : {data}\n\n",True)
            # sudo_action = await sudo_action_middleware(request)

            # self.app_debug_print(f" \n\n sudo_action : {sudo_action}\n\n",True)

            # sudo_message = sudo_action.get('message',None)
            # sudo_can_proceed = sudo_action.get('can_proceed',True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_400_BAD_REQUEST,
            #             content={
            #                 "status_code": status.HTTP_400_BAD_REQUEST,
            #                 "message": sudo_message,
            #             }
            #         )

            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            data = {
                **data,
                "sys_organization_id": user_details['sys_organization_id'],
                "created_by_id": user_details['id']
            }
            # validation_service = SecurityValidationService(accept_language=self.accept_language)
            # validation_process = await validation_service.validation_process(
            #     request=request,
            #     operation_type=EMultipleValidationType.CREATE,
            #     sudo_action=sudo_action,
            #     collection_name=collection_name,
            #     data=data,
            #     user_details=user_details
            # )

            # if validation_process['is_sudo_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "is_sudo_action":True,
            #                 "message": validation_process['message'],
            #                 "data":validation_process['data']
            #             }
            #         )
            # elif validation_process['is_sudo_group_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "message": validation_process['message'],
            #             }
            #         )
            # else:
                 # Add data to the collection
                # item_id = await self.generic_service.add_data_to_collection(collection_key, data)
                # message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
                # return CustomJSONResponse(
                #         status_code=status.HTTP_200_OK,
                #         content={
                #             "status_code": status.HTTP_200_OK,
                #             "message": message,
                #             "item_id":item_id
                #         }
                #     )
            item_id = await self.generic_service.add_data_to_collection(
                collection_key,
                data,
                accept_language=self.accept_language,
                request=request,
                user=user_details,
            )
            grouped_response = self._build_group_validation_response(item_id)
            if grouped_response:
                return grouped_response
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                        "item_id":item_id,
                        "validation_context": self._normalize_validation_context(),
                    }
                )
        except PermissionError as e:
            self.app_debug_print(f" \n\n PermissionError: {e}\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f" \n\n Exception: {e}\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))


    async def org_upsert_data(self,request: Request,collection_name: str, data: Dict[str, Any]):
        """
        Endpoint to add a new document to the specified collection.
        """
        try:
            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message',None)
            # sudo_can_proceed = sudo_action.get('can_proceed',True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_400_BAD_REQUEST,
            #             content={
            #                 "status_code": status.HTTP_400_BAD_REQUEST,
            #                 "message": sudo_message,
            #             }
            #         )
            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            upsert_query = data.get('query',{})
            upsert_data = data.get('data',{})
            self.app_debug_print(f" \n\n upsert_query: {upsert_query}\n\n",True)
            self.app_debug_print(f" \n\n upsert_data: {upsert_data}\n\n",True)

            upsert_query = {
                **upsert_query,
                "sys_organization_id": user_details['sys_organization_id']
            }
            upsert_data = {
                **upsert_data,
                "sys_organization_id": user_details['sys_organization_id'],
            }

            if not upsert_query or not upsert_data:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_UPSERT_QUERY_OR_DATA", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Check if the data exists in the collection
            # check_data = await self.generic_service.fetch_native_query_one_from_collection(
            #     collection_key=collection_key,
            #     output_data_type=OutputDataType.DEFAULT.value,
            #     accept_language=self.accept_language,
            #     native_query=upsert_query
            # )

            # validation_service = SecurityValidationService(accept_language=self.accept_language)
            # validation_data = {}
            # if not check_data:
            #     validation_data = {
            #         "operation_type":EMultipleValidationType.CREATE,
            #         "sudo_action":sudo_action,
            #         "collection_name":collection_name,
            #         "data":upsert_data,
            #         "user_details":user_details,
            #     }
            # else:
            #     validation_data = {
            #         "operation_type":EMultipleValidationType.UPSERT,
            #         "sudo_action":sudo_action,
            #         "collection_name":collection_name,
            #         "data":upsert_data,
            #         "user_details":user_details,
            #         "target_document_id":check_data['id'],
            #         "upsert_query":upsert_query,
            #     }
            #     # message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
            #     # raise HTTPException(status_code=404, detail=message)
            # validation_process = await validation_service.validation_process(
            #     request=request,
            #     operation_type=validation_data.get("operation_type"),
            #     sudo_action=validation_data.get('sudo_action'),
            #     collection_name=validation_data.get("collection_name"),
            #     data=validation_data.get("data"),
            #     user_details=validation_data.get("user_details"),
            #     target_document_id=validation_data.get("target_document_id") if validation_data.get("target_document_id",None) else None,
            #     upsert_query=validation_data.get("upsert_query") if validation_data.get("upsert_query",None) else None
            # )

            # if validation_process['is_sudo_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "is_sudo_action":True,
            #                 "message": validation_process['message'],
            #                 "data":validation_process['data']
            #             }
            #         )
            # elif validation_process['is_sudo_group_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "message": validation_process['message'],
            #             }
            #         )
            # else:
            #     item_id = await self.generic_service.upsert_data_to_collection(collection_key, upsert_query,upsert_data)
            #     saved_id = item_id if isinstance(item_id,str) else item_id['id']
            #     message = self.get_response_message(MessageCategory.SUCCESS, "SUCCESSFULL_OPERATION_COMPLETED", self.accept_language)
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "message": message,
            #                 "data":saved_id
            #             }
            #         )
            item_id = await self.generic_service.upsert_data_to_collection(
                collection_key,
                upsert_query,
                upsert_data,
                accept_language=self.accept_language,
                request=request,
                user=user_details,
            )
            grouped_response = self._build_group_validation_response(item_id)
            if grouped_response:
                return grouped_response
            saved_id = item_id if isinstance(item_id,str) else item_id['id']
            message = self.get_response_message(MessageCategory.SUCCESS, "SUCCESSFULL_OPERATION_COMPLETED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                        "data":saved_id,
                        "validation_context": self._normalize_validation_context(),
                    }
                )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


    async def soft_delete_data(self,request: Request,collection_name: str):
        """
        Endpoint to soft delete a document in the specified collection.
        """
        try:
            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message',None)
            # sudo_can_proceed = sudo_action.get('can_proceed',True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_400_BAD_REQUEST,
            #             content={
            #                 "status_code": status.HTTP_400_BAD_REQUEST,
            #                 "message": sudo_message,
            #             }
            #         )

            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            item_id = request.query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Check if the data exists in the collection
            check_data = await self.generic_service.fetch_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id":  item_id,
                },
                user=user_details,
            )
            if not check_data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # VALIDATION PROCESS
            # validation_service = SecurityValidationService(accept_language=self.accept_language)
            # validation_data = {
            #     "operation_type":EMultipleValidationType.SOFT_DELETE,
            #     "sudo_action":sudo_action,
            #     "collection_name":collection_name,
            #     "target_document_id":item_id,
            #     "user_details":user_details,
            # }
            # validation_process = await validation_service.validation_process(
            #     request=request,
            #     operation_type=validation_data.get("operation_type"),
            #     sudo_action=validation_data.get('sudo_action'),
            #     collection_name=validation_data.get("collection_name"),
            #     target_document_id=validation_data.get("target_document_id"),
            #     user_details=validation_data.get("user_details"),
            # )
            # if validation_process['is_sudo_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "is_sudo_action":True,
            #                 "message": validation_process['message'],
            #                 "data":validation_process['data']
            #             }
            #         )
            # elif validation_process['is_sudo_group_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "message": validation_process['message'],
            #             }
            #         )
            # else:
                # Soft delete the document
                # success = await self.generic_service.soft_delete_data_from_collection(collection_key, item_id,self.accept_language)
                # message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
                # if success:
                #     return CustomJSONResponse(
                #         status_code=status.HTTP_200_OK,
                #         content={
                #             "status_code": status.HTTP_200_OK,
                #             "message":message,
                #         }
                #     )
                # else:
                #     message = self.get_response_message(MessageCategory.ERRORS, "FAILLURE_OPERATION_COMPLETED", self.accept_language)
                #     raise HTTPException(status_code=404, detail=message)
            success = await self.generic_service.soft_delete_data_from_collection(
                collection_key,
                item_id,
                self.accept_language,
                request=request,
            )
            grouped_response = self._build_group_validation_response(success)
            if grouped_response:
                return grouped_response
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
            if success:
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message":message,
                        "validation_context": self._normalize_validation_context(),
                    }
                )
            else:
                message = self.get_response_message(MessageCategory.ERRORS, "FAILLURE_OPERATION_COMPLETED", self.accept_language)
                raise HTTPException(status_code=404, detail=message)



        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


    async def hard_delete_data(self,request: Request,collection_name: str):
        """
        Endpoint to soft delete a document in the specified collection.
        """

        try:
            # sudo_action = await sudo_action_middleware(request)
            # self.app_debug_print(f" sudo_action : {sudo_action}",True)
            # sudo_message = sudo_action.get('message',None)
            # sudo_can_proceed = sudo_action.get('can_proceed',True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_400_BAD_REQUEST,
            #             content={
            #                 "status_code": status.HTTP_400_BAD_REQUEST,
            #                 "message": sudo_message,
            #             }
            #         )
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # self.app_debug_print(f" user_profil : {user_profil}",True)
            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            item_id = request.query_params.get('item_id',None)
            self.app_debug_print(f" item_id : {item_id}",True)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            check_data = await self.generic_service.fetch_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id":  item_id,
                }
            )
            self.app_debug_print(f" check_data : {check_data}",True)
            if not check_data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # # VALIDATION PROCESS
            # validation_service = ValidationService(accept_language=self.accept_language)
            # validation_data = {
            #     "operation_type":EMultipleValidationType.HARD_DELETE,
            #     "sudo_action":sudo_action,
            #     "collection_name":collection_name,
            #     "target_document_id":item_id,
            #     "user_details":user_details,
            # }
            # validation_process = await validation_service.validation_process(
            #     request=request,
            #     operation_type=validation_data.get("operation_type"),
            #     sudo_action=validation_data.get('sudo_action'),
            #     collection_name=validation_data.get("collection_name"),
            #     target_document_id=validation_data.get("target_document_id"),
            #     user_details=validation_data.get("user_details"),
            # )

            # if validation_process['is_sudo_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "is_sudo_action":True,
            #                 "message": validation_process['message'],
            #                 "data":validation_process['data']
            #             }
            #         )
            # elif validation_process['is_sudo_group_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "message": validation_process['message'],
            #             }
            #         )
            # else:
            #     # Hard delete the document
            #     success = await self.generic_service.hard_delete_data_from_collection(collection_key, item_id,self.accept_language)
            #     message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
            #     if success:
            #         return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "message": message,
            #             }
            #         )
            #     else:
            #         message = self.get_response_message(MessageCategory.ERRORS, "FAILLURE_OPERATION_COMPLETED", self.accept_language)
            #         raise HTTPException(status_code=404, detail=message)
            success = await self.generic_service.hard_delete_data_from_collection(
                collection_key,
                item_id,
                self.accept_language,
                request=request,
                user=user_details
            )
            grouped_response = self._build_group_validation_response(success)
            if grouped_response:
                return grouped_response
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
            if success:
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                        "validation_context": self._normalize_validation_context(),
                    }
                )
            else:
                message = self.get_response_message(MessageCategory.ERRORS, "FAILLURE_OPERATION_COMPLETED", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

        except PermissionError as e:
            self.app_debug_print(f" ERROR HARD DELETE 2 : {e}",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            format_error = format_exception("Error in hard_delete_data", e)
            self.app_debug_print(f" ERROR HARD DELETE 3 : {format_error}",True)
            raise HTTPException(status_code=500, detail=str(e))


    async def org_hard_delete_data(self,request: Request,collection_name: str):
        """
        Endpoint to soft delete a document in the specified collection.
        """

        try:
            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message',None)
            # sudo_can_proceed = sudo_action.get('can_proceed',True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_400_BAD_REQUEST,
            #             content={
            #                 "status_code": status.HTTP_400_BAD_REQUEST,
            #                 "message": sudo_message,
            #             }
            #         )

            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)


            item_id = request.query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            check_data = await self.generic_service.fetch_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id":  item_id,
                    "filter__sys_organization_id": user_details['sys_organization_id']
                },
                user=user_details,
            )
            if not check_data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # VALIDATION PROCESS
            # validation_service = SecurityValidationService(accept_language=self.accept_language)
            # validation_data = {
            #     "operation_type":EMultipleValidationType.HARD_DELETE,
            #     "sudo_action":sudo_action,
            #     "collection_name":collection_name,
            #     "target_document_id":item_id,
            #     "user_details":user_details,
            # }
            # validation_process = await validation_service.validation_process(
            #     request=request,
            #     operation_type=validation_data.get("operation_type"),
            #     sudo_action=validation_data.get('sudo_action'),
            #     collection_name=validation_data.get("collection_name"),
            #     target_document_id=validation_data.get("target_document_id"),
            #     user_details=validation_data.get("user_details"),
            # )

            # if validation_process['is_sudo_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "is_sudo_action":True,
            #                 "message": validation_process['message'],
            #                 "data":validation_process['data']
            #             }
            #         )
            # elif validation_process['is_sudo_group_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "message": validation_process['message'],
            #             }
            #         )
            # else:
            #     # Hard delete the document
            #     success = await self.generic_service.hard_delete_data_from_collection(collection_key, item_id,self.accept_language)
            #     message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
            #     if success:
            #         return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "message": message,
            #             }
            #         )
            #     else:
            #         message = self.get_response_message(MessageCategory.ERRORS, "FAILLURE_OPERATION_COMPLETED", self.accept_language)
            #         raise HTTPException(status_code=404, detail=message)
            # Hard delete the document
            success = await self.generic_service.hard_delete_data_from_collection(
                collection_key,
                item_id,
                self.accept_language,
                request=request,
                user=user_details
            )
            grouped_response = self._build_group_validation_response(success)
            if grouped_response:
                return grouped_response
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
            if success:
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                        "validation_context": self._normalize_validation_context(),
                    }
                )
            else:
                message = self.get_response_message(MessageCategory.ERRORS, "FAILLURE_OPERATION_COMPLETED", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

        except PermissionError as e:
            self.app_debug_print(f" ERROR HARD DELETE > : {e}",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f" ERROR HARD DELETE >> : {e}",True)
            raise HTTPException(status_code=500, detail=str(e))


    async def on_update_data(self,request: Request,collection_name: str, data: Dict[str, Any]):
        """
        Endpoint to update a document in the specified collection.
        """
        try:
            self.app_debug_print(f"UPDATE STEP 0 > :",False)
            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message',None)
            # sudo_can_proceed = sudo_action.get('can_proceed',True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_400_BAD_REQUEST,
            #             content={
            #                 "status_code": status.HTTP_400_BAD_REQUEST,
            #                 "message": sudo_message,
            #             }
            #         )
            self.app_debug_print(f"UPDATE STEP 0.1 > :",False)
            user_details = await self.get_user_info(request,self.accept_language)
            api_consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            item_id = request.query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            self.app_debug_print(f"UPDATE STEP 1 > item_id : {item_id} ",True)
            # Check if the data exists in the collection
            check_data = await self.generic_service.fetch_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id":  item_id,
                },
                user=user_details,
            )
            self.app_debug_print(f"UPDATE STEP 2 > ",False)
            if not check_data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
 
            # Add data to the collection
            item_id = await self.generic_service.update_data_in_collection(
                collection_key,
                item_id,
                data,
                self.accept_language,
                request=request,
                user=user_details
            )
            grouped_response = self._build_group_validation_response(item_id)
            if grouped_response:
                return grouped_response
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                        "item_id":item_id,
                        "validation_context": self._normalize_validation_context(),
                    }
                )

        except PermissionError as e:
            self.app_debug_print(f" ERROR UPDATE > : {e}",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f" ERROR UPDATE >> : {e}",True)
            raise HTTPException(status_code=500, detail=str(e))

    async def org_on_update_data(self,request: Request,collection_name: str, body: dict = Body(...)):
        """
        Endpoint to update a document in the specified collection.
        """
        try:
            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message',None)
            # sudo_can_proceed = sudo_action.get('can_proceed',True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_400_BAD_REQUEST,
            #             content={
            #                 "status_code": status.HTTP_400_BAD_REQUEST,
            #                 "message": sudo_message,
            #             }
            #         )
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)


            try:
                collection_key = CollectionKey(collection_name)
            except ValueError as e:
                self.app_debug_print(f"\n\n\n error update org  up : {e}",False)
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            item_id = request.query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Check if the data exists in the collection
            check_data = await self.generic_service.fetch_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id":  item_id,
                    "filter__sys_organization_id": user_details['sys_organization_id']
                },
                user=user_details,
            )
            if not check_data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # START VALIDATION PROCESS
            # validation_service = SecurityValidationService(accept_language=self.accept_language)
            # validation_process = await validation_service.validation_process(
            #     request=request,
            #     operation_type=EMultipleValidationType.UPDATE,
            #     sudo_action=sudo_action,
            #     collection_name=collection_name,
            #     data=body,
            #     user_details=user_details,
            #     target_document_id=item_id
            # )

            # if validation_process['is_sudo_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "is_sudo_action":True,
            #                 "message": validation_process['message'],
            #                 "data":validation_process['data']
            #             }
            #         )
            # elif validation_process['is_sudo_group_action'] == True:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "message": validation_process['message'],
            #             }
            #         )
            # else:
            #     # Add data to the collection
            #     item_id = await self.generic_service.update_data_in_collection(collection_key,item_id,body,self.accept_language,)
            #     message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_200_OK,
            #             content={
            #                 "status_code": status.HTTP_200_OK,
            #                 "message": message,
            #                 "item_id":item_id
            #             }
            #         )
            # Add data to the collection
            item_id = await self.generic_service.update_data_in_collection(
                collection_key,
                item_id,
                body,
                self.accept_language,
                request=request,
                user=user_details
            )
            grouped_response = self._build_group_validation_response(item_id)
            if grouped_response:
                return grouped_response
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                        "item_id":item_id,
                        "validation_context": self._normalize_validation_context(),
                    }
                )
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n error update org : {e}",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n error update org 2 model_class : {e}",True)
            raise HTTPException(status_code=500, detail=str(e))


    async def update_to_ordering_data(self,request: Request,collection_name: str, body: List = Body(...)):
        """
        Endpoint to update a document in the specified collection.
        """
        try:
            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message',None)
            # sudo_can_proceed = sudo_action.get('can_proceed',True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_400_BAD_REQUEST,
            #             content={
            #                 "status_code": status.HTTP_400_BAD_REQUEST,
            #                 "message": sudo_message,
            #             }
            #         )
            self.app_debug_print(f"\n\n\n update -> {collection_name}  body : {body}",False)
            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError as e:
                self.app_debug_print(f"\n\n\n error update org  up : {e}",False)
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            list_of_ordred_items = body
            if not list_of_ordred_items:
                message = self.get_response_message(MessageCategory.COMMON, "NO_DATA_TO_UPDATE", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            list_of_formated_ordered_items = []
            for item in list_of_ordred_items:
                check_data = await self.generic_service.fetch_one_from_collection(
                    collection_key=collection_key,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={
                        "filter___id":  item['id'],
                        "filter__sys_organization_id": user_details['sys_organization_id']
                    },
                    user=user_details,
                )
                if check_data:
                    list_of_formated_ordered_items.append(check_data)

            if not list_of_formated_ordered_items:
                message = self.get_response_message(MessageCategory.COMMON, "NO_DATA_TO_UPDATE", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # START VALIDATION PROCESS
            # validation_service = SecurityValidationService(accept_language=self.accept_language)

            # Perform the update
            update_index = 0
            # is_sudo_group_action = sudo_action.get('is_sudo_group_action',False)
            for index,item in enumerate(list_of_formated_ordered_items):
                data = {
                    "order_by":index,
                }
                # validation_process = await validation_service.validation_process(
                #     request=request,
                #     operation_type=EMultipleValidationType.UPDATE,
                #     sudo_action=sudo_action,
                #     collection_name=collection_name,
                #     data=data,
                #     user_details=user_details,
                #     target_document_id=item['id'],
                #     by_pass_http_return=True,
                # )
                # if validation_process == True and is_sudo_group_action == False:
                    # updated = await self.generic_service.update_data_in_collection(
                    #     collection_key=collection_key,
                    #     item_id=item['id'],
                    #     data={
                    #         "order_by":index,
                    #     }
                    # )
                updated = await self.generic_service.update_data_in_collection(
                    collection_key=collection_key,
                    item_id=item['id'],
                    data={
                        "order_by":index,
                    },
                    user=user_details
                )

                update_index += 1
            # self.app_debug_print(f"\n\n\n update result  : {updated}",False)
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            if update_index > 0:
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message
                    }
                )
            else:
                message = self.get_response_message(MessageCategory.ERRORS, "FAILLURE_OPERATION_COMPLETED", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n error update org : {e}",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n error update org 2 model_class : {e}",True)
            raise HTTPException(status_code=500, detail=str(e))


    async def on_data_fetch(
        self,
        request: Request,
        collection_name: str,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try:


            # Convert string to CollectionKey
            try:
                self.app_debug_print(f"collection_name --> {collection_name}",True)
                collection_key = CollectionKey(collection_name)
                self.app_debug_print(f"collection_key --> {collection_key}",True)
            except ValueError as e:
                self.app_debug_print(f"collection_key --> {e}",True)
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)



            # Convert query parameters to dictionary
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)

            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            sort = request.query_params.get("sort", {'created_at':-1})
            self.app_debug_print(f"Query Parameters (SORT): {sort}",False)
            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_data_from_collection(
                collection_key=collection_key,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    **query_params
                },
                user=user_details,
                sort=sort
            )
            if len(data) > 0:
                self.app_debug_print(f"Query data: {data[0]}",False)
            extra_data = {}
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=collection_key,
                    accept_language=self.accept_language,
                    query={
                        **query_params
                    },
                    user=user_details
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": data,
                    **extra_data
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch_data: > 1 {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    async def fetch_count_native_data_from_collection(
        self,
        collection_key: CollectionKey,
        output_data_type: OutputDataType = OutputDataType.DEFAULT,
        native_query: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, int]] = {"created_at": -1},
    ) -> List[Dict[str, Any]]:
        """
        Fetch documents dynamically from a MongoDB collection using a native MongoDB query.

        This function supports:
        - Pagination (using limit and page)
        - Sorting
        - Custom output formatting based on output_data_type
        - Language-based formatting (using accept_language)
        - Retrieving all data (if all_data is True)

        :param collection_key: The key identifying the collection.
        :param all_data: Flag indicating whether to retrieve all documents.
        :param output_data_type: The desired output formatting.
        :param limit: Maximum number of documents per page.
        :param page: Page number for pagination.
        :param accept_language: Language code for translations.
        :param native_query: A native MongoDB query dictionary.
        :param sort: Optional list of sort tuples.
        :return: A list of formatted documents.

        Example:
            >>> native_query = {"status": "active"}
            >>> native_query = {
                        "$or": [
                            {"status": "active"},
                            {"priority": "high"}
                        ]
                    }
            >>> data = await fetch_native_query_data_from_collection(
            ...     collection_key=CollectionKey.USERS,
            ...     all_data=False,
            ...     output_data_type=OutputDataType.DATA_TABLE,
            ...     limit=20,
            ...     page=0,
            ...     accept_language="en",
            ...     native_query=native_query,
            ...     sort={"created_at", -1}
            ... )
            >>> print(data)
        """
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        collection_name = metadata.collection_name
        model_class = metadata.model_class

        dao = DAO(collection_name, model_class,is_read_only=True)
        assert dao.collection is not None, f"Error: Collection {collection_name} is None!"

        # Use the provided native MongoDB query, or default to an empty filter
        db_filter = native_query if native_query is not None else {}

        # If TREE output is requested, add a filter to fetch only top-level documents
        if output_data_type == OutputDataType.TREE.value:
            model_name = getattr(model_class.Settings, "name", model_class.__class__.__name__.lower())
            parent_field = f"{model_name}_id"
            self.app_debug_print(f"\n\n\n\n parent_field not in db_filter : {parent_field not in db_filter}", True)
            if parent_field not in db_filter:
                db_filter = {**db_filter, parent_field: None}

        db_filter = self.convert_query_params(db_filter)
        sort = self.process_sort(sort)
        self.app_debug_print(f"Query data native : {db_filter}", True)
        # Process the query parameters to build the MongoDB filter
        try: 
            # Convert Enum values and handle data type conversions for comparison operators
            from app.modules.core.services.converter.converter_service import ConverterService
            db_filter = ConverterService.convert_enum_to_value(db_filter)
            # Retrieve the documents from the collection
            db_filter = self.convert_query_params(db_filter)
            sort = self.process_sort(sort)
            self.app_debug_print(f"Query data: {db_filter}", False)
            count = await dao.collection.count_documents(db_filter) 
            return count

        except Exception as e:
            self.app_debug_print(f"Error during fetch_count_native_data_from_collection: {e}", False)
            return 0
        
    async def fetch_one_data(
        self,
        request: Request,
        collection_name: str,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try:


            # Convert string to CollectionKey
            try:
                self.app_debug_print(f"collection_name --> {collection_name}")
                collection_key = CollectionKey(collection_name)
                self.app_debug_print(f"collection_key --> {collection_key}")
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Convert query parameters to dictionary
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)

            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            sort = request.query_params.get("sort", {'created_at':-1})
            self.app_debug_print(f"Query Parameters (SORT): {sort}",True)
            # Fetch data from the collection using CollectionKey

            check_data = await self.generic_service.fetch_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                **query_params
                },
                user=user_details,
            )
            if not check_data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": check_data
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch_data: > 1 {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    async def fetch_org_one_data(
        self,
        request: Request,
        collection_name: str,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try:


            # Convert string to CollectionKey
            try:
                self.app_debug_print(f"collection_name --> {collection_name}")
                collection_key = CollectionKey(collection_name)
                self.app_debug_print(f"collection_key --> {collection_key}")
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)



            # Convert query parameters to dictionary
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            raw_query_params = {
                **raw_query_params,
                "filter__sys_organization_id": str(user_details['sys_organization_id'])
            }
            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            sort = request.query_params.get("sort", {'created_at':-1})
            self.app_debug_print(f"Query Parameters (SORT): {sort}",True)
            # Fetch data from the collection using CollectionKey

            check_data = await self.generic_service.fetch_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                **query_params
                },
                user=user_details,
            )
            if not check_data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": check_data
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch_data: > 1 {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    async def on_org_fetch_data(
        self,
        request: Request,
        collection_name: str,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page"),
        sort: Optional[Dict[str, int]] = {'created_at': -1},
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try:



            # Convert string to CollectionKey
            try:
                self.app_debug_print(f"collection_name --> {collection_name}")
                collection_key = CollectionKey(collection_name)
                self.app_debug_print(f"collection_key --> {collection_key}")
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)


            self.app_debug_print(f"\n\n\n sort : {sort}\n\n\n",True)
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            raw_query_params = {
                **raw_query_params,
                "filter__sys_organization_id": str(user_details['sys_organization_id'])
            }

            query_params = self.convert_query_params(raw_query_params)
            sort = query_params.get('sort', {'created_at': -1})
            # If sort is a string, parse it into a dictionary
            self.app_debug_print(f"\n\n\n sort 0 > : {sort}\n\n\n", False)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",False)
            # If sort is a string, parse it into a dictionary
            self.app_debug_print(f"\n\n\n sort 1 > : {sort}\n\n\n", False)


            self.app_debug_print(f"\n\n\n sort 2> : {sort}\n\n\n", False)

            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_data_from_collection(
                collection_key=collection_key,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    **query_params
                },
                user=user_details,
                sort=sort
            )
            extra_data = {}
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=collection_key,
                    accept_language=self.accept_language,
                    query={
                        **query_params
                    },
                    user=user_details
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": data,
                    **extra_data
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch_data: > 2 {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    async def get_collection_head(
        self,
        request: Request,
        collection_name: str,
    ):
        """
        Fetch the head of a collection: fields, types, and constraints.
        """
        # Capture query parameters from the request
        query_params = dict(request.query_params)
        try:



            # Convert collection name to CollectionKey and fetch model metadata
            try:
                collection_key = CollectionKey(collection_name)
                model_class, model_name = self.get_model_from_collection_key(
                    collection_key,
                    endpoint_call=True  # Enforce API access control
                )
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))

            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)


            # Extract and transform schema metadata
            self.app_debug_print(f" before : schema_extra ",False)
            schema_extra = model_class.model_json_schema().get("properties", {})
            self.app_debug_print(f" after : schema_extra ",False)

            model_name = self.get_collection_name_from_collection_key(collection_key)
            parent_field = f"{model_name}_id"

            # self.app_debug_print(model_class.model_json_schema())
            transformed_head = await self.generic_service.transform_schema_to_head(
                model_name=model_name,
                schema=schema_extra,
                accept_language=self.accept_language,
                query_params=query_params,
                parent_field=parent_field
                # exclude_fields=["soft_deleted", "created_at"],
                # force_include_fields=["id", "created_at"]
            )
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data": transformed_head,
                    }
                ) 

        except Exception as e:
            self.app_debug_print(f"Error fetching head: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    async def get_org_collection_head(
        self,
        request: Request,
        collection_name: str,
    ):
        """
        Fetch the head of a collection: fields, types, and constraints.
        """
        # Capture query parameters from the request
        query_params = dict(request.query_params)
        try:



            # Convert collection name to CollectionKey and fetch model metadata
            try:
                collection_key = CollectionKey(collection_name)
                model_class, model_name = self.get_model_from_collection_key(
                    collection_key,
                    endpoint_call=True  # Enforce API access control
                )
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))

            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Extract and transform schema metadata
            schema_extra = model_class.model_json_schema().get("properties", {})

            # self.app_debug_print(model_class.model_json_schema())
            transformed_head = await self.generic_service.transform_schema_to_head(
                schema=schema_extra,
                model_name=model_name,
                accept_language=self.accept_language,
                query_params=query_params,
                is_organization_head=True,
                sys_organization_id=user_details['sys_organization_id'],
                exclude_fields=['is_default','system_reserved_actions','rbac_profile_id']
                # exclude_fields=["soft_deleted", "created_at"],
                # force_include_fields=["id", "created_at"]
            )

            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data": transformed_head,
                    }
                ) 

        except Exception as e:
            self.app_debug_print(f"Error fetching head: {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    async def get_child_collection_head(
        self,
        request: Request,
        collection_name: str,
    ):
        """
        Fetch the head of a collection: fields, types, and constraints.
        """
        # Capture query parameters from the request
        query_params = dict(request.query_params)
        try:



            # Convert collection name to CollectionKey and fetch model metadata
            try:
                collection_key = CollectionKey(collection_name)
                model_class, model_name = self.get_model_from_collection_key(
                    collection_key,
                    endpoint_call=True  # Enforce API access control
                )
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))

            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Extract and transform schema metadata
            schema_extra = model_class.model_json_schema().get("properties", {})

            model_name = self.get_collection_name_from_collection_key(collection_key)
            parent_field = f"{model_name}_id"
            print(f'\n\n\n step : 1 parent_field : {parent_field}\n\n\n')
            raw_query_params: Dict[str, str] = dict(request.query_params)
            parent_id = raw_query_params.get('parent_id',None)
            if not parent_id:
                message = self.get_response_message(MessageCategory.COMMON, "NO_PARENT_ID_SENT", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            # self.app_debug_print(model_class.model_json_schema())
            print(f'\n\n\n step : 2 parent_id : {parent_id}\n\n\n')
            transformed_head = await self.generic_service.transform_schema_to_child_head(
                schema=schema_extra,
                model_name=model_name,
                accept_language=self.accept_language,
                query_params=query_params,
                parent_field=parent_field,
                parent_value=parent_id,
                is_organization_head=False,
                # exclude_fields=["soft_deleted", "created_at"],
                # force_include_fields=["id", "created_at"]
            )
            print('step : 3')
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data": transformed_head,
                    }
                ) 

        except Exception as e:
            self.app_debug_print(f"Error fetching head: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    async def get_org_child_collection_head(
        self,
        request: Request,
        collection_name: str,
    ):
        """
        Fetch the head of a collection: fields, types, and constraints.
        """
        # Capture query parameters from the request
        query_params = dict(request.query_params)
        try:



            # Convert collection name to CollectionKey and fetch model metadata
            try:
                collection_key = CollectionKey(collection_name)
                model_class, model_name = self.get_model_from_collection_key(
                    collection_key,
                    endpoint_call=True  # Enforce API access control
                )
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))

            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Extract and transform schema metadata
            schema_extra = model_class.model_json_schema().get("properties", {})

            model_name = self.get_collection_name_from_collection_key(collection_key)
            parent_field = f"{model_name}_id"
            print(f'\n\n\n\n\n step : 1 >>> {parent_field}')
            raw_query_params: Dict[str, str] = dict(request.query_params)
            parent_id = raw_query_params.get('parent_id',None)
            if not parent_id:
                message = self.get_response_message(MessageCategory.COMMON, "NO_PARENT_ID_SENT", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            # self.app_debug_print(model_class.model_json_schema())
            print('step : 2')
            print(f'\n\n\n\n\n step : 2 parent_id >>> {parent_id}')
            transformed_head = await self.generic_service.transform_schema_to_child_head(
                schema=schema_extra,
                model_name=model_name,
                accept_language=self.accept_language,
                query_params=query_params,
                parent_field=parent_field,
                parent_value=parent_id,
                is_organization_head=True,
                sys_organization_id=user_details['sys_organization_id']
                # exclude_fields=["soft_deleted", "created_at"],
                # force_include_fields=["id", "created_at"]
            )
            print('step : 3')
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data": transformed_head,
                    }
                ) 

        except Exception as e:
            self.app_debug_print(f"Error fetching head: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")



    async def get_collection_update_head(
        self,
        request: Request,
        collection_name: str,
    ):
        """
        Fetch the head of a collection: fields, types, and constraints.
        """
        # Capture query parameters from the request
        
        try:
            # Convert collection name to CollectionKey and fetch model metadata
            try:
                collection_key = CollectionKey(collection_name)
                model_class, model_name = self.get_model_from_collection_key(
                    collection_key,
                    endpoint_call=True  # Enforce API access control
                )
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))


            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # raw_query_params: Dict[str, str] = dict(request.query_params)
            # Extract and transform schema metadata
            schema_extra = model_class.model_json_schema().get("properties", {})

            model_name = self.get_collection_name_from_collection_key(collection_key)
            # parent_field = f"{model_name}_id"
            self.app_debug_print('step update head : 1',False)
            raw_query_params: Dict[str, str] = dict(request.query_params)
            item_id = raw_query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ITEM_ID_SENT", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                "filter___id":item_id
                },
                user=user_details,
            )
            if not data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # self.app_debug_print(model_class.model_json_schema())
            
            self.app_debug_print('step update head : 2 > ',data,False)
            transformed_head = await self.generic_service.transform_schema_to_update_head(
                schema=schema_extra,
                model_name=model_name,
                accept_language=self.accept_language,
                query_params=raw_query_params,
                parent_field=None,
                item_data=data,
                is_organization_head=False,
                sys_organization_id=None,
                exclude_fields=['is_default','soft_deleted_at','multiple_validated_at','multle_validation_status','updated_at','created_at','soft_deleted','is_activated','system_reserved_actions','rbac_profile_id']
            )
            self.app_debug_print('step update head : 3',False)
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data":transformed_head,
                    }
                ) 

        except Exception as e:
            self.app_debug_print(f"Error fetching head: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")



    async def get_collection_child_update_head(
        self,
        request: Request,
        collection_name: str,
    ):
        """
        Fetch the head of a collection: fields, types, and constraints.
        """
        # Capture query parameters from the request
        query_params = dict(request.query_params)
        try:



            # Convert collection name to CollectionKey and fetch model metadata
            try:
                collection_key = CollectionKey(collection_name)
                model_class, model_name = self.get_model_from_collection_key(
                    collection_key,
                    endpoint_call=True  # Enforce API access control
                )
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))


            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Extract and transform schema metadata
            schema_extra = model_class.model_json_schema().get("properties", {})

            model_name = self.get_collection_name_from_collection_key(collection_key)
            # parent_field = f"{model_name}_id"
            self.app_debug_print('step : 1')
            raw_query_params: Dict[str, str] = dict(request.query_params)
            item_id = raw_query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ITEM_ID_SENT", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                "filter___id":item_id
                },
                user=user_details,
            )
            if not data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # self.app_debug_print(model_class.model_json_schema())
            self.app_debug_print('step : 2')
            transformed_head = await self.generic_service.transform_schema_to_update_child_head(
                schema=schema_extra,
                model_name=model_name,
                accept_language=self.accept_language,
                query_params=query_params,
                parent_field=None,
                item_data=data,
                is_organization_head=False,
                sys_organization_id=None,
                exclude_fields=['is_default','system_reserved_actions','rbac_profile_id']
            )
            self.app_debug_print('step : 3')
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data":transformed_head,
                    }
                ) 

        except Exception as e:
            self.app_debug_print(f"Error fetching head: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")



    async def get_org_collection_child_update_head(
        self,
        collection_name: str,
        request: Request,
    ):
        """
        Fetch the head of a collection: fields, types, and constraints.
        """
        # Capture query parameters from the request
        query_params = dict(request.query_params)
        try:



            # Convert collection name to CollectionKey and fetch model metadata
            try:
                collection_key = CollectionKey(collection_name)
                model_class, model_name = self.get_model_from_collection_key(
                    collection_key,
                    endpoint_call=True  # Enforce API access control
                )
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))


            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Extract and transform schema metadata
            schema_extra = model_class.model_json_schema().get("properties", {})

            model_name = self.get_collection_name_from_collection_key(collection_key)
            parent_field = f"{model_name}_id"
            self.app_debug_print('step : 1')
            raw_query_params: Dict[str, str] = dict(request.query_params)
            item_id = raw_query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ITEM_ID_SENT", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                "filter___id":item_id
                },
                user=user_details,
            )
            if not data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # self.app_debug_print(model_class.model_json_schema())
            self.app_debug_print('step : 2')
            transformed_head = await self.generic_service.transform_schema_to_update_child_head(
                schema=schema_extra,
                model_name=model_name,
                accept_language=self.accept_language,
                query_params=query_params,
                parent_field=parent_field,
                item_data=data,
                is_organization_head=True,
                sys_organization_id=user_details['sys_organization_id'],
                exclude_fields=['is_default','system_reserved_actions','rbac_profile_id']
            )
            self.app_debug_print('step : 3')
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data":transformed_head,
                    }
                )  

        except Exception as e:
            self.app_debug_print(f"Error fetching head: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")



    async def get_org_collection_update_head(
        self,
        collection_name: str,
        request: Request,
    ):
        """
        Fetch the head of a collection: fields, types, and constraints.
        """
        # Capture query parameters from the request
        query_params = dict(request.query_params)
        try:



            # Convert collection name to CollectionKey and fetch model metadata
            try:
                collection_key = CollectionKey(collection_name)
                model_class, model_name = self.get_model_from_collection_key(
                    collection_key,
                    endpoint_call=True  # Enforce API access control
                )
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))


            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Extract and transform schema metadata
            schema_extra = model_class.model_json_schema().get("properties", {})

            model_name = self.get_collection_name_from_collection_key(collection_key)
            # parent_field = f"{model_name}_id"
            self.app_debug_print('step : 1')
            raw_query_params: Dict[str, str] = dict(request.query_params)
            item_id = raw_query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ITEM_ID_SENT", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                "filter___id":item_id
                },
                user=user_details,
            )
            if not data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # self.app_debug_print(model_class.model_json_schema())
            self.app_debug_print('step : 2')
            transformed_head = await self.generic_service.transform_schema_to_update_head(
                schema=schema_extra,
                model_name=model_name,
                accept_language=self.accept_language,
                query_params=query_params,
                parent_field=None,
                item_data=data,
                is_organization_head=True,
                sys_organization_id=user_details['sys_organization_id'],
                exclude_fields=['is_default','created_at','system_reserved_actions','rbac_profile_id']
            )
            self.app_debug_print('step : 3')
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data":transformed_head,
                    }
                )  

        except Exception as e:
            self.app_debug_print(f"Error fetching head: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    async def ge_org_data_overview(
        self,
        request: Request,
        collection_name: str,
    ):
        """
        Fetch the head of a collection: fields, types, and constraints.
        """
        # Capture query parameters from the request
        query_params = dict(request.query_params)
        try:



            # Convert collection name to CollectionKey and fetch model metadata
            try:
                collection_key = CollectionKey(collection_name)
                model_class, model_name = self.get_model_from_collection_key(
                    collection_key,
                    endpoint_call=True  # Enforce API access control
                )
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))

            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Extract and transform schema metadata
            schema_extra = model_class.model_json_schema().get("properties", {})

            model_name = self.get_collection_name_from_collection_key(collection_key)
            parent_field = f"{model_name}_id"
            self.app_debug_print('step : 1')
            raw_query_params: Dict[str, str] = dict(request.query_params)
            item_id = raw_query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ITEM_ID_SENT", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id":item_id
                },
                user=user_details,
            )
            if not data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # self.app_debug_print(model_class.model_json_schema())
            self.app_debug_print(f'\n\n GET ORG DATA OVERVIEW : 2 : {data}',True)
            transformed_head = await self.generic_service.transform_overview_data(
                schema=schema_extra,
                model_name=model_name,
                accept_language=self.accept_language,
                query_params=query_params,
                parent_field=parent_field,
                item_data=data,
                is_organization_head=True,
                sys_organization_id=user_details['sys_organization_id']
            )
            self.app_debug_print('step : 3')
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data":transformed_head,
                    }
                )  

        except Exception as e:
            self.app_debug_print(f"Error fetching head: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    async def get_data_overview(
        self,
        request: Request,
        collection_name: str,
    ):
        """
        Fetch the head of a collection: fields, types, and constraints.
        """
        # Capture query parameters from the request
        query_params = dict(request.query_params)
        try:



            # Convert collection name to CollectionKey and fetch model metadata
            try:
                collection_key = CollectionKey(collection_name)
                model_class, model_name = self.get_model_from_collection_key(
                    collection_key,
                    endpoint_call=True  # Enforce API access control
                )
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))

            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Extract and transform schema metadata
            schema_extra = model_class.model_json_schema().get("properties", {})

            model_name = self.get_collection_name_from_collection_key(collection_key)
            parent_field = f"{model_name}_id"
            self.app_debug_print('step : 1')
            raw_query_params: Dict[str, str] = dict(request.query_params)
            item_id = raw_query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ITEM_ID_SENT", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                "filter___id":item_id
                },
                user=user_details,
            )
            if not data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # self.app_debug_print(model_class.model_json_schema())
            self.app_debug_print('step : 2')
            transformed_head = await self.generic_service.transform_overview_data(
                schema=schema_extra,
                model_name=model_name,
                accept_language=self.accept_language,
                query_params=None,
                parent_field=parent_field,
                item_data=data,
                is_organization_head=False,
                sys_organization_id=None
            )
            self.app_debug_print('step : 3')
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data":transformed_head,
                    }
                )  

        except Exception as e:
            self.app_debug_print(f"Error fetching head: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    async def get_token_data_overview(
        self,
        request: Request,
        collection_name: str,
        body: dict = Body(...)
    ):
        """
        Fetch the head of a collection: fields, types, and constraints.
        """
        # Capture query parameters from the request
        query_params = dict(request.query_params)
        try:



            # Convert collection name to CollectionKey and fetch model metadata
            try:
                collection_key = CollectionKey(collection_name)
                model_class, model_name = self.get_model_from_collection_key(
                    collection_key,
                    endpoint_call=True  # Enforce API access control
                )
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))

            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Extract and transform schema metadata
            schema_extra = model_class.model_json_schema().get("properties", {})

            model_name = self.get_collection_name_from_collection_key(collection_key)
            parent_field = f"{model_name}_id"
            self.app_debug_print('step : 1')

            element_token_id = body.get('token',None)
            self.app_debug_print(f"\n\n element_token_id : {element_token_id}\n\n",True)
            self.app_debug_print(f"\n\n element_token_id type : {type(element_token_id)}\n\n",True)
            if not element_token_id:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ELEMENT_TOKEN_ID_SENT", self.accept_language)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

            # S'assurer que le token est une chaîne de caractères
            if not isinstance(element_token_id, str):
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_TOKEN_FORMAT", self.accept_language)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

            decoded_token = self.token_service.decode_and_verify_token(
                token=element_token_id,
                expected_type=EJWTTokenType.PENDING_REQUEST_VALIDATION
            )
            element_id = decoded_token['sub']
            self.app_debug_print(f"\n\n decoded_token : {element_id}\n\n",True)
            data = await self.generic_service.fetch_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                "filter___id":element_id
                },
                user=user_details,
            )
            if not data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # self.app_debug_print(model_class.model_json_schema())
            self.app_debug_print('step : 2')
            transformed_head = await self.generic_service.transform_overview_data(
                schema=schema_extra,
                model_name=model_name,
                accept_language=self.accept_language,
                query_params=None,
                parent_field=parent_field,
                item_data=data,
                is_organization_head=False,
                sys_organization_id=None
            )
            _validators = data['validator_users']
            list_of_validators = []
            has_validation_access = False
            for validator in _validators:
                sys_user_id = validator.sys_user_id
                if user_details['id'] == str(sys_user_id) and validator.has_validation_access == True:
                    has_validation_access = True
                    break
            self.app_debug_print('step : 3')
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data": {
                            "info":transformed_head,
                            "can_validate":has_validation_access,
                            "can_reject":has_validation_access,
                        },
                    }
                ) 
             

        except Exception as e:
            self.app_debug_print(f"Error fetching element overview: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    # Add the new data integrity endpoint
    async def check_data_integrity(
        self,
        request: Request,
        collection_name: str,
        item_id: str
    ):
        """
        Endpoint to check data integrity, focusing on encrypted fields.
        Returns metadata about whether the data has been modified outside the application.
        """
        try:



            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Import TranslationService lazily to avoid circular imports.
            from app.modules.core.services.translation.translation_service import TranslationService
            translation_service = TranslationService()

            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # Get model and metadata
            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
            if not metadata:
                raise HTTPException(status_code=400, detail="Invalid collection name")

            model_class, model_name = self.get_model_from_collection_key(
                collection_key,
                endpoint_call=True  # Enforce API access control
            )

            dao = DAO(metadata.collection_name, model_class,is_read_only=True)
            raw_document = await dao.collection.find_one({"_id": ObjectId(item_id)})

            if not raw_document:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # Convert ObjectId to string for consistency
            if "_id" in raw_document:
                raw_document["_id"] = str(raw_document["_id"])

            # Fetch the document
            document = await self.generic_service.fetch_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter___id": item_id},
                user=user_details,
            )

            if not document:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

                # Initialize integrity results with the new format

            # Initialize integrity results with the new format and translated titles
            document_info_title = await translation_service.get_static_fields_translation(
                property_name="document_info",
                accept_language=self.accept_language
            ) or "Document Information"

            integrity_status_title = await translation_service.get_static_fields_translation(
                property_name="integrity_status",
                accept_language=self.accept_language
            ) or "Integrity Status"

            encrypted_fields_title = await translation_service.get_static_fields_translation(
                property_name="encrypted_fields",
                accept_language=self.accept_language
            ) or "Encrypted Fields"

            modified_fields_title = await translation_service.get_static_fields_translation(
                property_name="modified_fields",
                accept_language=self.accept_language
            ) or "Modified Fields"

            metadata_title = await translation_service.get_static_fields_translation(
                property_name="metadata",
                accept_language=self.accept_language
            ) or "Metadata"

            formatted_results = {
                "document_info": {
                    "display_title": document_info_title,
                    "display_value": {
                        "id": {
                            "display_title": await translation_service.get_static_fields_translation(
                                property_name="document_id",
                                accept_language=self.accept_language
                            ) or "Document ID",
                            "display_value": item_id,
                            "data_type": {"is_string": True}
                        },
                        "collection": {
                            "display_title": await translation_service.get_static_fields_translation(
                                property_name="collection",
                                accept_language=self.accept_language
                            ) or "Collection",
                            "display_value": collection_name,
                            "data_type": {"is_string": True}
                        },
                        "created_at": {
                            "display_title": await translation_service.get_static_fields_translation(
                                property_name="created_at",
                                accept_language=self.accept_language
                            ) or "Created At",
                            "display_value": document.get("created_at", None),
                            "data_type": {"is_date": True}
                        },
                        "updated_at": {
                            "display_title": await translation_service.get_static_fields_translation(
                                property_name="updated_at",
                                accept_language=self.accept_language
                            ) or "Last Updated",
                            "display_value": document.get("updated_at", None),
                            "data_type": {"is_date": True}
                        }
                    },
                    "data_type": {"is_object": True}
                },
                "integrity_status": {
                    "display_title": integrity_status_title,
                    "display_value": "valid",  # Default value, will be updated if issues found
                    "data_type": {"is_string": True, "is_enum": True},
                    "meta": {
                        "enum_values": ["valid", "compromised", "error"]
                    }
                },
                "encrypted_fields": {
                    "display_title": encrypted_fields_title,
                    "display_value": {},  # Will be populated with field data
                    "data_type": {"is_object": True}
                },
                "modified_fields": {
                    "display_title": modified_fields_title,
                    "display_value": [],  # Will be populated if modifications detected
                    "data_type": {"is_array": True}
                },
                "metadata": {
                    "display_title": metadata_title,
                    "display_value": {
                        "has_encrypted_fields": {
                            "display_title": await translation_service.get_static_fields_translation(
                                property_name="has_encrypted_fields",
                                accept_language=self.accept_language
                            ) or "Has Encrypted Fields",
                            "display_value": False,  # Will be updated
                            "data_type": {"is_bool": True}
                        },
                        "total_fields": {
                            "display_title": await translation_service.get_static_fields_translation(
                                property_name="total_fields",
                                accept_language=self.accept_language
                            ) or "Total Fields",
                            "display_value": 0,  # Will be updated
                            "data_type": {"is_number": True}
                        },
                        "encrypted_fields_count": {
                            "display_title": await translation_service.get_static_fields_translation(
                                property_name="encrypted_fields_count",
                                accept_language=self.accept_language
                            ) or "Encrypted Fields Count",
                            "display_value": 0,  # Will be updated
                            "data_type": {"is_number": True}
                        },
                        "modified_fields_count": {
                            "display_title": await translation_service.get_static_fields_translation(
                                property_name="modified_fields_count",
                                accept_language=self.accept_language
                            ) or "Modified Fields Count",
                            "display_value": 0,  # Will be updated
                            "data_type": {"is_number": True}
                        }
                    },
                    "data_type": {"is_object": True}
                }
            }

            # ... existing code for checking encrypted fields ...
            schema_extra = model_class.model_json_schema().get("properties", {})
            has_encrypted_fields = False
            modified_fields = []

            for field_name, field_meta in schema_extra.items():
                # Skip special fields
                if field_name.startswith('_') or field_name in ['id', 'translations', 'encryptions']:
                    continue

                # Get field metadata
                can_be_encrypted = field_meta.get("can_be_encrypted", False)
                self.app_debug_print(f"\n\n can_be_encrypted [{field_name}] : {can_be_encrypted}\n\n\n",True)
                if can_be_encrypted:
                    has_encrypted_fields = True
                    field_value = raw_document.get(field_name)
                    self.app_debug_print(f"\n\n field_value [{field_name}] : {field_value}\n\n\n",True)
                    # Get translated field name for display
                    field_display_title = await translation_service.get_static_fields_translation(
                        property_name=field_name,
                        accept_language=self.accept_language
                    ) or field_name.replace("_", " ").title()


                    # Check if field has encryption data in translations
                    translations = document.get("translations", {})
                    field_translation = translations.get(field_name, {})
                    self.app_debug_print(f"\n\n field_translation [{field_name}] : {field_translation}\n\n\n",True)
                    field_status = {
                        "display_title": field_display_title,
                        "data_type": {"is_object": True}
                    }

                    if "__encrypted__" in field_translation:
                        # Field is encrypted, check integrity
                        try:
                            decrypted_value = EncryptionService.decrypt(field_encryption["encrypted"])
                            self.app_debug_print(f"\n\n decrypted_value [{field_name}] : {decrypted_value}\n\n\n",True)
                            # Compare with stored value (if they don't match, data was modified outside the app)
                            is_valid = field_value == decrypted_value
                            self.app_debug_print(f"\n\n is_valid [{field_name}] : {is_valid}\n\n\n",True)

                            # Get translated status labels for integrity status
                            status_valid_label = await translation_service.get_static_fields_translation(
                                property_name="status_valid",
                                accept_language=self.accept_language
                            ) or "Valid"

                            status_compromised_label = await translation_service.get_static_fields_translation(
                                property_name="status_compromised",
                                accept_language=self.accept_language
                            ) or "Compromised"

                            if not is_valid:
                                formatted_results["integrity_status"]["display_value"] = "compromised"
                                formatted_results["integrity_status"]["meta"]["valid_info"] = {
                                    "valid_label": status_valid_label,
                                    "valid_value": decrypted_value
                                }
                                formatted_results["integrity_status"]["meta"]["compromised_info"] = {
                                    "compromised_label": status_compromised_label,
                                    "compromized_value": field_value
                                }
                                modified_fields.append(field_name)

                            # Get translated status labels
                            status_valid = await translation_service.get_static_fields_translation(
                                property_name="status_valid",
                                accept_language=self.accept_language
                            ) or "valid"

                            status_modified = await translation_service.get_static_fields_translation(
                                property_name="status_modified",
                                accept_language=self.accept_language
                            ) or "modified"

                            status_title = await translation_service.get_static_fields_translation(
                                property_name="status",
                                accept_language=self.accept_language
                            ) or "Status"

                            has_encryption_data_title = await translation_service.get_static_fields_translation(
                                property_name="has_encryption_data",
                                accept_language=self.accept_language
                            ) or "Has Encryption Data"

                            field_value_title = await translation_service.get_static_fields_translation(
                                property_name="field_value",
                                accept_language=self.accept_language
                            ) or "Field Value"

                            field_status["display_value"] = {
                                "status": {
                                    "display_title": status_title,
                                    "display_value": status_valid if is_valid else status_modified,
                                    "data_type": {"is_string": True, "is_enum": True},
                                    "meta": {
                                        "enum_values": ["valid", "modified", "error", "missing_encryption"]
                                    }
                                },
                                "has_encryption_data": {
                                    "display_title": has_encryption_data_title,
                                    "display_value": True,
                                    "data_type": {"is_bool": True}
                                },
                                "field_value": {
                                    "display_title": field_value_title,
                                    "display_value": field_value,
                                    "data_type": {"is_string": True}
                                }
                            }
                        except Exception as e:
                            formatted_results["integrity_status"]["display_value"] = "error"

                            error_title = await translation_service.get_static_fields_translation(
                                property_name="error",
                                accept_language=self.accept_language
                            ) or "Error"

                            field_status["display_value"] = {
                                "status": {
                                    "display_title": await translation_service.get_static_fields_translation(
                                        property_name="status",
                                        accept_language=self.accept_language
                                    ) or "Status",
                                    "display_value": "error",
                                    "data_type": {"is_string": True, "is_enum": True},
                                    "meta": {
                                        "enum_values": ["valid", "modified", "error", "missing_encryption"]
                                    }
                                },
                                "has_encryption_data": {
                                    "display_title": await translation_service.get_static_fields_translation(
                                        property_name="has_encryption_data",
                                        accept_language=self.accept_language
                                    ) or "Has Encryption Data",
                                    "display_value": True,
                                    "data_type": {"is_bool": True}
                                },
                                "error": {
                                    "display_title": error_title,
                                    "display_value": str(e),
                                    "data_type": {"is_string": True}
                                }
                            }
                    else:
                        # Field should be encrypted but has no encryption data
                        missing_encryption_title = await translation_service.get_static_fields_translation(
                            property_name="missing_encryption",
                            accept_language=self.accept_language
                        ) or "missing_encryption"

                        field_status["display_value"] = {
                            "status": {
                                "display_title": await translation_service.get_static_fields_translation(
                                    property_name="status",
                                    accept_language=self.accept_language
                                ) or "Status",
                                "display_value": missing_encryption_title,
                                "data_type": {"is_string": True, "is_enum": True},
                                "meta": {
                                    "enum_values": ["valid", "modified", "error", "missing_encryption"]
                                }
                            },
                            "has_encryption_data": {
                                "display_title": await translation_service.get_static_fields_translation(
                                    property_name="has_encryption_data",
                                    accept_language=self.accept_language
                                ) or "Has Encryption Data",
                                "display_value": False,
                                "data_type": {"is_bool": True}
                            }
                        }

                        if field_value:  # Only mark as compromised if there's a value that should be encrypted
                            formatted_results["integrity_status"]["display_value"] = "compromised"
                            modified_fields.append(field_name)

                    formatted_results["encrypted_fields"]["display_value"][field_name] = field_status

            # Update metadata values
            formatted_results["metadata"]["display_value"]["has_encrypted_fields"]["display_value"] = has_encrypted_fields
            formatted_results["metadata"]["display_value"]["total_fields"]["display_value"] = len(schema_extra)
            formatted_results["metadata"]["display_value"]["encrypted_fields_count"]["display_value"] = len(formatted_results["encrypted_fields"]["display_value"])
            formatted_results["metadata"]["display_value"]["modified_fields_count"]["display_value"] = len(modified_fields)

            # Update modified fields list with translated field names
            formatted_results["modified_fields"]["display_value"] = []
            for field in modified_fields:
                field_display_title = await translation_service.get_static_fields_translation(
                    property_name=field,
                    accept_language=self.accept_language
                ) or field.replace("_", " ").title()

                formatted_results["modified_fields"]["display_value"].append({
                    "display_title": field_display_title,
                    "display_value": field,
                    "data_type": {"is_string": True}
                })

            message = self.get_response_message(
                MessageCategory.SUCCESS,
                "DATA_INTEGRITY_CHECK_COMPLETED",
                self.accept_language
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "data": formatted_results
                }
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except HTTPException as e:
            raise e
        except Exception as e:
            self.app_debug_print(f"Error checking data integrity: {str(e)}", True)
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    async def translate_field(
        self,
        request: Request,
        collection_name: str,
        item_id: str,
        field_name: str,
        translation_data: Dict[str, Any] = Body(...),
        translation_strategy: Optional[str] = Query("default", description="Translation strategy: default, preserve, or cascade")
    ):
        """
        Endpoint to translate a specific field in a document.
        Allows updating translations for a single field with specified translation strategy.
        """
        try:



            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # Get model and metadata
            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
            if not metadata:
                raise HTTPException(status_code=400, detail="Invalid collection name")

            model_class, model_name = self.get_model_from_collection_key(
                collection_key,
                endpoint_call=True  # Enforce API access control
            )

            # Validate translation strategy
            # from app.services.generic_service import TranslationStrategy
            valid_strategies = [strategy.value for strategy in TranslationStrategy]

            if translation_strategy not in valid_strategies:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid translation strategy. Must be one of: {', '.join(valid_strategies)}"
                )

            # Check if document exists
            dao = DAO(metadata.collection_name, model_class,is_read_only=True)
            document = await dao.get(item_id)

            if not document:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # Check if field exists in the model schema
            schema_extra = model_class.model_json_schema().get("properties", {})
            if field_name not in schema_extra:
                raise HTTPException(status_code=400, detail=f"Field '{field_name}' does not exist in this collection")

            # Get field metadata to check if it's translatable
            field_meta = schema_extra.get(field_name, {})
            is_translatable = field_meta.get("may_have_translation", False)

            if not is_translatable:
                raise HTTPException(status_code=400, detail=f"Field '{field_name}' is not translatable")

            # Prepare translations update
            translations = document.get("translations", {})
            field_translations = translations.get(field_name, {})

            # Update with new translations
            field_translations.update(translation_data)
            translations[field_name] = field_translations

            # Add translation metadata
            translation_meta = document.get("translation_meta", {})
            field_translation_meta = translation_meta.get(field_name, {})

            # Update translation metadata with strategy and timestamp
            field_translation_meta.update({
                "strategy": translation_strategy,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            translation_meta[field_name] = field_translation_meta

            # Prepare update data
            update_data = {
                "translations": translations,
                "translation_meta": translation_meta
            }

            # Update the document
            result = await dao.update({'_id':item_id}, update_data)

            if not result:
                raise HTTPException(status_code=500, detail="Failed to update translations")

            message = self.get_response_message(MessageCategory.SUCCESS, "TRANSLATION_UPDATED_SUCCESSFULLY", self.accept_language)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "data": {
                        "field": field_name,
                        "translations": field_translations,
                        "strategy": translation_strategy
                    }
                }
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except HTTPException as e:
            raise e
        except Exception as e:
            self.app_debug_print(f"Error updating field translation: {str(e)}", True)
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


    async def get_translation_field_head(
        self,
        request: Request,
        collection_name: str,
        item_id: str,
        field_name: str,
    ):
        """
        Fetch the head information for a specific translatable field.
        This endpoint provides metadata needed to generate a dynamic translation form in the frontend.
        """
        # Capture query parameters from the request
        query_params = dict(request.query_params)
        # Get available languages from CollectionKey.REF_LANGUAGE
        available_languages = {}
        try:



            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Convert collection name to CollectionKey and fetch model metadata
            try:
                # Fetch languages from the reference collection
                ref_languages_dao = DAO(CollectionKey.REF_LANGUAGE.value, None)
                languages_cursor = ref_languages_dao.collection.find({"soft_deleted": {"$ne": True}})

                async for lang in languages_cursor:
                    lang_code = lang.get("code", "")
                    lang_name = lang.get("name", "")
                    if lang_code:
                        available_languages[lang_code] = lang_name

                if not available_languages:
                    # Fallback to default languages if none found in database
                    available_languages = {"en": "English", "fr": "French"}

                collection_key = CollectionKey(collection_name)
                model_class, model_name = self.get_model_from_collection_key(
                    collection_key,
                    endpoint_call=True  # Enforce API access control
                )
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))



            self.app_debug_print(f"Accept-Language from header: {self.accept_language}")

            # Import TranslationService lazily to avoid circular imports
            from app.modules.core.services.translation.translation_service import TranslationService
            translation_service = TranslationService()

            # Get model schema and check if field exists and is translatable
            schema_extra = model_class.model_json_schema().get("properties", {})
            if field_name not in schema_extra:
                raise HTTPException(status_code=400, detail=f"Field '{field_name}' does not exist in this collection")

            field_meta = schema_extra.get(field_name, {})
            # print(f'\n\n\n field_meta: {field_meta}')
            is_translatable = field_meta.get("may_have_translation", False)

            if not is_translatable:
                raise HTTPException(status_code=400, detail=f"Field '{field_name}' is not translatable")

            # Fetch the document to get current translations
            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
            dao = DAO(metadata.collection_name, model_class,is_read_only=True)
            document = await dao.get(item_id)

            if not document:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # Get current field value and translations
            field_value = document.get(field_name, "")
            translations = document.get("translations", {}).get(field_name, {})
            translation_meta = document.get("translation_meta", {}).get(field_name, {})

            # Check if field has encryption in translations and decrypt if needed
            translations = document.get("translations", {})
            field_translation = translations.get(field_name, {})

            if "__encrypted__" in field_translation:
                try:
                    # Field is encrypted, decrypt it
                    decrypted_value = EncryptionService.decrypt(field_translation["__encrypted__"])
                    field_value = decrypted_value  # Use decrypted value instead of stored value
                except Exception as e:
                    self.app_debug_print(f"Error decrypting field {field_name}: {str(e)}")
                    # Continue with the stored value if decryption fails

            # Get translated field name for display
            field_display_title = await translation_service.get_static_fields_translation(
                property_name=field_name,
                accept_language=self.accept_language
            ) or field_name.replace("_", " ").title()

            # Prepare translation strategies
            # from app.services.generic_service import TranslationStrategy
            strategies = [strategy.value for strategy in TranslationStrategy]

            # Build the head information
            translation_head = {
                "field_info": {
                    "property_name": field_name,
                    "display_title": field_display_title,
                    "current_value": field_value,
                    "data_type": field_meta.get("data_type", "string"),
                    "extra_metas": field_meta.get("extra_metas", {}),
                },
                "translation_info": {
                    "current_translations": translations,
                    "translation_meta": translation_meta,
                    "available_languages": [
                        {
                            "code": lang_code,
                            "name": lang_name,
                            "has_translation": lang_code in translations,
                            "translation_value": translations.get(lang_code, "")
                        }
                        for lang_code, lang_name in available_languages.items()
                    ],
                    "strategies": [
                        {
                            "value": strategy,
                            "display_name": await translation_service.get_static_fields_translation(
                                property_name=f"strategy_{strategy}",
                                accept_language=self.accept_language
                            ) or strategy.capitalize()
                        }
                        for strategy in strategies
                    ],
                    "current_strategy": translation_meta.get("strategy", TranslationStrategy.DEFAULT.value)
                },
                "ui_config": {
                    "form_layout": "tabbed",  # or "grid", "stacked", etc.
                    "show_original_value": True,
                    "show_strategy_selector": True,
                    "show_language_selector": True
                }
            }

            message = self.get_response_message(MessageCategory.SUCCESS, "TRANSLATION_HEAD_FETCHED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "data": translation_head
                }
            )

        except HTTPException as e:
            raise e
        except Exception as e:
            self.app_debug_print(f"Error fetching translation head: {str(e)}")
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    async def count_data_from_collection(
        self,
        request: Request,
        collection_name: str,
        query: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Endpoint to count documents in a MongoDB collection using a CollectionKey,
        with support for filtering.

        Parameters:
            request (Request):
                The FastAPI request object.
            collection_name (str):
                The name of the collection to count documents from.
            query (Optional[Dict[str, Any]], optional):
                A dictionary of query parameters.

        Returns:
            int: The count of documents matching the query criteria.
        """
        try:
            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language, collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # Get user information for filtering
            user_details = await self.get_user_info(request, self.accept_language)

            # Count documents in the collection
            count = await self.generic_service.count_data_from_collection(
                collection_key=collection_key,
                accept_language=self.accept_language,
                query=query,
                endpoint_call=True,
                user=user_details
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "count": count
                }
            )

        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"Error counting documents: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def aggregate_count_data_from_collection(
        self,
        request: Request,
        collection_name: str,
        pipeline: List[Dict[str, Any]],
    ) -> int:
        """
        Endpoint to count documents in a MongoDB collection using an aggregation pipeline.

        Parameters:
            request (Request):
                The FastAPI request object.
            collection_name (str):
                The name of the collection to count documents from.
            pipeline (List[Dict[str, Any]]):
                A list of aggregation pipeline stages.

        Returns:
            int: The count of documents matching the aggregation criteria.
        """
        try:
            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language, collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # Count documents in the collection using the aggregation pipeline
            count = await self.generic_service.fetch_native_aggregate_count_from_collection(
                collection_key=collection_key,
                accept_language=self.accept_language,
                pipeline=pipeline
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "count": count
                }
            )

        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"Error counting documents with aggregation: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def fetch_all_countries_info(
        self,
        request: Request,
    ) -> int:
        """
        Endpoint to count documents in a MongoDB collection using an aggregation pipeline.

        Parameters:
            request (Request):
                The FastAPI request object.
            collection_name (str):
                The name of the collection to count documents from.
            pipeline (List[Dict[str, Any]]):
                A list of aggregation pipeline stages.

        Returns:
            int: The count of documents matching the aggregation criteria.
        """
        try: 
            # Count documents in the collection using the aggregation pipeline
            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_COUNTRY,
                accept_language=self.accept_language,
                all_data=True,
                query={},
                output_data_type=OutputDataType.DEFAULT
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": data
                }
            )

        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"Error counting documents with aggregation: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


    async def validate_user_infos(self, request: Request, body: dict):
        """
        Validate user information (email or phone number) by sending verification code.

        Flow:
        1. Validate input data (email/phone_number and validation_type)
        2. Generate 6-digit verification code
        3. Create Redis cache key with 20-minute expiry
        4. Send verification code via email or SMS
        5. Return encrypted validation key for verification
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            api_consumer = await self.get_api_consumer(request, self.accept_language)
            user_profil = await self.get_user_profil(request, self.accept_language)

            # Validate request body
            formatted_body = UserInfoValidation.model_validate(body, context={"language": self.accept_language})

            # Import required services
            from app.modules.core.services.email_sender.email_sender_service import EMailSenderService
            from app.modules.core.services.sms.sms_service import SmsService
            from app.modules.core.services.redis.redis_service import AppRedisService
            from app.modules.core.services.encryption.encryption_service import EncryptionService
            from app.modules.core.services.email.email_service import EmailService
            import random
            import string
            import uuid
            import json
            from datetime import datetime, timedelta

            # Extract validation data
            validation_type = formatted_body.validation_type
            email = formatted_body.email
            phone_number = formatted_body.phone_number

            # Validate required fields based on validation type
            if validation_type == EUserInfoValidationFlag.EMAIL.value:
                if not email:
                    message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "EMAIL_REQUIRED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                # Validate email format
                email_service = EmailService(self.accept_language)
                if not email_service.is_valid_email(email):
                    message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "INVALID_EMAIL_FORMAT", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                target_contact = email

            elif validation_type == EUserInfoValidationFlag.PHONE_NUMBER.value:
                if not phone_number:
                    message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "PHONE_NUMBER_REQUIRED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                target_contact = phone_number
            else:
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "INVALID_VALIDATION_TYPE", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Generate 6-digit verification code
            verification_code = ''.join(random.choices(string.digits, k=6))

            # Generate unique validation key
            validation_key = str(uuid.uuid4())

            # Create validation data for Redis cache
            validation_data = {
                "verification_code": verification_code,
                "validation_type": validation_type,
                "target_contact": target_contact,
                "user_id": user_details.get('id') if user_details else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat(),
                "attempts": 0,
                "max_attempts": 3
            }

            # Store validation data in Redis with 20-minute expiry (1200 seconds)
            redis_key = f"user_validation:{validation_key}"
            await AppRedisService.set_redis_value(
                key=redis_key,
                value=json.dumps(validation_data),
                expiry=1200,  # 20 minutes
                use_env_prefix=True
            )

            # Send verification code
            if validation_type == EUserInfoValidationFlag.EMAIL.value:
                # Send email with verification code
                email_sender = EMailSenderService(self.accept_language)
                subject = self.get_response_message(MessageCategory.EMAIL_TEMPLATE, "VERIFICATION_CODE_SUBJECT", self.accept_language)

                # Create email content
                email_content = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #333;">Verification Code</h2>
                    <p>Your verification code is:</p>
                    <div style="background-color: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0;">
                        <h1 style="color: #007bff; font-size: 32px; margin: 0; letter-spacing: 5px;">{verification_code}</h1>
                    </div>
                    <p>This code will expire in 20 minutes.</p>
                    <p>If you didn't request this verification, please ignore this email.</p>
                </div>
                """

                await email_sender.send_mail_async(
                    to=email,
                    subject=subject,
                    html_content=email_content
                )

                self.app_debug_print(f"Verification email sent to {email}", True)

            else:  # SMS validation
                # Send SMS with verification code
                sms_service = SmsService()
                sms_message = f"Your verification code is: {verification_code}. This code expires in 20 minutes."

                await sms_service.send_sms_httpx_async(
                    phone_number=phone_number,
                    message=sms_message,
                    sender_id=settings.SMS_SENDER_ID
                )

                self.app_debug_print(f"Verification SMS sent to {phone_number}", True)

            # Encrypt the validation key for client
            encrypted_validation_key = EncryptionService.encrypt_text(validation_key)

            # Prepare response data
            response_data = {
                "validation_key": encrypted_validation_key,
                "validation_type": validation_type,
                "target_contact": target_contact,
                "expires_in_minutes": 20,
                "max_attempts": 3
            }

            message = self.get_response_message(MessageCategory.SUCCESS, "VERIFICATION_CODE_SENT", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "data": response_data
                }
            )
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=error_detail)

    async def verify_user_validation_code(self, request: Request, body: dict):
        """
        Verify the validation code sent by user.

        Flow:
        1. Decrypt the validation key from client
        2. Fetch validation data from Redis
        3. Compare verification codes
        4. Update attempts counter
        5. Return success/failure response
        """
        try:
            # Import required services
            from app.modules.core.services.redis.redis_service import AppRedisService
            from app.modules.core.services.encryption.encryption_service import EncryptionService
            import json
            from datetime import datetime

            # Extract data from request body
            encrypted_validation_key = body.get('validation_key')
            submitted_code = body.get('verification_code')

            if not encrypted_validation_key or not submitted_code:
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "MISSING_VALIDATION_DATA", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Decrypt the validation key
            try:
                validation_key = EncryptionService.decrypt_text(encrypted_validation_key)
            except Exception as e:
                self.app_debug_print(f"Failed to decrypt validation key: {e}", True)
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "INVALID_VALIDATION_KEY", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Fetch validation data from Redis
            redis_key = f"user_validation:{validation_key}"
            validation_data_str = await AppRedisService.get_str_redis_value(redis_key, use_env_prefix=True)

            if not validation_data_str:
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "VALIDATION_EXPIRED_OR_INVALID", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Parse validation data
            validation_data = json.loads(validation_data_str)

            # Check if validation has expired
            expires_at = datetime.fromisoformat(validation_data['expires_at'])
            if datetime.now(timezone.utc) > expires_at:
                # Clean up expired validation
                await AppRedisService.remove_redis_value(redis_key, use_env_prefix=True)
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "VALIDATION_CODE_EXPIRED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Check attempts limit
            current_attempts = validation_data.get('attempts', 0)
            max_attempts = validation_data.get('max_attempts', 3)

            if current_attempts >= max_attempts:
                # Clean up validation after max attempts
                await AppRedisService.remove_redis_value(redis_key, use_env_prefix=True)
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "MAX_ATTEMPTS_EXCEEDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Increment attempts counter
            validation_data['attempts'] = current_attempts + 1

            # Compare verification codes
            stored_code = validation_data['verification_code']
            if submitted_code.strip() != stored_code:
                # Update attempts in Redis
                await AppRedisService.set_redis_value(
                    key=redis_key,
                    value=json.dumps(validation_data),
                    expiry=1200,  # Keep same expiry
                    use_env_prefix=True
                )

                remaining_attempts = max_attempts - validation_data['attempts']
                message = self.get_response_message(MessageCategory.VALIDATION_ERROR, "INVALID_VERIFICATION_CODE", self.accept_language)

                return CustomJSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": message,
                        "data": {
                            "valid": False,
                            "remaining_attempts": remaining_attempts,
                            "attempts_used": validation_data['attempts']
                        }
                    }
                )

            # Verification successful - clean up Redis key
            await AppRedisService.remove_redis_value(redis_key, use_env_prefix=True)

            # Prepare success response
            response_data = {
                "valid": True,
                "validation_type": validation_data['validation_type'],
                "target_contact": validation_data['target_contact'],
                "verified_at": datetime.now(timezone.utc).isoformat()
            }

            message = self.get_response_message(MessageCategory.SUCCESS, "VERIFICATION_SUCCESSFUL", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "data": response_data
                }
            )
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=error_detail)
