


import time
from datetime import datetime
import json
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import HTTPException, Query, Request,status
from app.db.dao import DAO
from app.modules.auth.enums.common import MessageCategory

from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.types.response import CustomJSONResponse
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.application.application_service import ApplicationService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.device.device_service import DeviceService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.services.sms.sms_service import SmsService
from app.modules.core.enums.type_enum import OutputDataType
from app.modules.auth.services.password.password_service import PasswordService
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.model.model_service import ModelService
from app.modules.core.services.email_sender.email_sender_service import EMailSenderService
from app.modules.core.enums.profiles_enum import ESysProfileFlag


class CoreController(
    AuthenticatedService,
    DebugService,
    PasswordService,
    ResponseService,
    ConverterService,
    ModelService,
    SmsService,
    DeviceService,
    EMailSenderService):
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.auth.services.login.login_service import LoginService
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.auth.services.token.token_service import TokenService
        
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        self.token_service = TokenService(accept_language)
        self.login_service = LoginService(accept_language)
        self.device_service = DeviceService(accept_language=accept_language)
        super().__init__(accept_language)
        
        
    async def check_core_access(
        self,
        request: Request,
    ):
        """
        Endpoint to check if user has core access

        Args:
            request (Request): The FastAPI request object containing headers.

        Returns:
            dict: Success response if user does have access.

        Raises:
            HTTPException: If the user doesn't have access.
        """
        user_as_access = self.token_service.decode_and_get_user_from_token(request)
        ip_address = self.get_real_ip_address(request)
        
        # Access user details attached by the middleware
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        # print(f"API Consumer: {api_Consumer}")
        if user_profil['flag'] != ESysProfileFlag.SYSTEM_PROFIL.value and user_profil['flag'] != ESysProfileFlag.TEST_SYS_PROFIL.value:
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "ACCESS_DENIED_MESSAGE", self.accept_language)
            raise HTTPException(status_code=401, detail=message)

        
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "success",
            }
        )
        
    async def update_all_default_access_roles(
        self,
        request: Request,
    ):
        """
        Endpoint to check if user has core access

        Args:
            request (Request): The FastAPI request object containing headers.

        Returns:
            dict: Success response if user does have access.

        Raises:
            HTTPException: If the user doesn't have access.
        """
        user_as_access = self.token_service.decode_and_get_user_from_token(request)
        ip_address = self.get_real_ip_address(request)
        
        # Access user details attached by the middleware
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        all_restricted_platforms  = await self.generic_service.fetch_data_from_collection(
            collection_key= CollectionKey.REF_API_CONSUMER,
            output_data_type = OutputDataType.DEFAULT,
            all_data=True,
            query={
                "filter__is_activated":True
            },
            user=user_details,
        ) 
        all_profiles  = await self.generic_service.fetch_data_from_collection(
            collection_key= CollectionKey.RBAC_PROFILE,
            output_data_type = OutputDataType.DEFAULT,
            all_data=True,
            query={
                "filter__is_activated":True
            },
            user=user_details,
        ) 
        restricted_profil = []
        for index,profile in enumerate(all_profiles):
            restricted_profil.append({
                "rbac_profile_id": profile['id'],
                "is_activated": True,
            })
        restricted_platform = []
        for index,platform in enumerate(all_restricted_platforms):
            restricted_platform.append({
                "ref_api_consumer_id": platform['id'],
                "is_activated": True,
            })
            
        all_default_permssions  = await self.generic_service.fetch_data_from_collection(
            collection_key= CollectionKey.RBAC_PERMISSION,
            output_data_type = OutputDataType.DEFAULT,
            all_data=True,
            query={
                "filter__is_accessible_to_all_profil":True
            },
            user=user_details,
        ) 
        
        print(f"\n default permissions : {len(all_default_permssions)} \n")
        async def saving_menu_permission_target(menu_id, permission_id):
            try:
                print(f"--- saving permission target {menu_id} : {permission_id}")
                new_permission_target_doc = { 
                    "targeted_id":menu_id, # linked_menu['id'],
                    "rbac_permission_id":permission_id, # perm['id'],
                    "restricted_platform":restricted_platform,
                    "restricted_profil":restricted_profil,
                    
                }
                perm_tart_exist = await self.generic_service.fetch_native_query_one_from_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language='fr',
                    native_query={
                        "targeted_id":new_permission_target_doc['targeted_id'],
                        'rbac_permission_id':new_permission_target_doc['rbac_permission_id']
                    }
                )
                if perm_tart_exist:
                    new_permission_target_doc.pop('restricted_platform', None)
                    new_permission_target_doc.pop('restricted_profil', None)
                    
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                    filter_data={
                        "targeted_id":new_permission_target_doc['targeted_id'],
                        'rbac_permission_id':new_permission_target_doc['rbac_permission_id']
                    },
                    user=user_details, request=request,
                    update_data=new_permission_target_doc)
                
                # SAVE OR UPDATE ALL ROLES
                all_roles = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.RBAC_ROLE,
                    output_data_type = OutputDataType.DEFAULT,
                    all_data=True,
                    query={},
                    user=user_details,
                )
                print(f"--- all roles :  {len(all_roles)}")
                for role in all_roles:
                    new_perm_tar_role_doc = {
                        "rbac_role_id": role['id'],
                        "rbac_permission_id":permission_id
                    }
                    await self.generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                        filter_data={
                            "rbac_role_id":new_perm_tar_role_doc['rbac_role_id'],
                            'rbac_permission_id':new_perm_tar_role_doc['rbac_permission_id']
                        },
                        user=user_details, request=request,
                        update_data=new_perm_tar_role_doc)
            except ValueError as e:
                print(f"Error >> saving_menu_permission_target: {e}")
            except PermissionError as e:
                print(f"Permission Error: {e}")
                
        async def saving_app_or_action_or_view_permission_target(app_action_view_id, permission_id):
            try:
                new_permission_target_doc = { 
                    "targeted_id":app_action_view_id, 
                    "rbac_permission_id":permission_id,
                    "restricted_platform":restricted_platform,
                    "restricted_profil":restricted_profil,
                    
                }
                perm_tart_exist = await self.generic_service.fetch_native_query_one_from_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language='fr',
                    native_query={
                        "targeted_id":new_permission_target_doc['targeted_id'],
                        'rbac_permission_id':new_permission_target_doc['rbac_permission_id']
                    }
                )
                if perm_tart_exist:
                    new_permission_target_doc.pop('restricted_platform', None)
                    new_permission_target_doc.pop('restricted_profil', None)
                    
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                    filter_data={
                        "targeted_id":new_permission_target_doc['targeted_id'],
                        'rbac_permission_id':new_permission_target_doc['rbac_permission_id']
                    },
                    user=user_details, request=request,
                    update_data=new_permission_target_doc)
                
                # SAVE OR UPDATE ALL ROLES
                all_roles = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.RBAC_ROLE,
                    output_data_type = OutputDataType.DEFAULT,
                    all_data=True,
                    query={},
                    user=user_details,
                )
                for role in all_roles:
                    new_perm_tar_role_doc = {
                        "rbac_role_id": role['id'],
                        "rbac_permission_id":permission_id
                    }
                    await self.generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                        filter_data={
                            "rbac_role_id":new_perm_tar_role_doc['rbac_role_id'],
                            'rbac_permission_id':new_perm_tar_role_doc['rbac_permission_id']
                        },
                        user=user_details, request=request,
                        update_data=new_perm_tar_role_doc) 

            except ValueError as e:
                print(f"Error >> saving_app_or_action_or_view_permission_target: {e}")
            except PermissionError as e:
                print(f"Permission Error: {e}")

        async def recursive_checking_submenus(submenu, permission_id, visited=None):
            if visited is None:
                visited = set()
            
            # Prevent infinite loops
            if submenu['id'] in visited:
                return
            visited.add(submenu['id'])
            print(f"--- menu name : {submenu['name']}")
            if 'sys_menu_id' in submenu:
                menu_parent = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.SYS_MENU,
                    output_data_type = OutputDataType.DEFAULT,
                    query={
                        "filter___id":submenu['sys_menu_id']
                    },
                    user=user_details,
                )
                if menu_parent:
                    await recursive_checking_submenus(menu_parent,permission_id,visited)
                    
            if 'sys_application_id' in submenu:
                app_parent = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.SYS_APPLICATION,
                    output_data_type = OutputDataType.DEFAULT,
                    query={
                        "filter___id":submenu['sys_application_id']
                    },
                    user=user_details,
                )
                if app_parent:
                    await saving_app_or_action_or_view_permission_target(app_parent['id'],permission_id)
                        
            await saving_menu_permission_target(submenu['id'],permission_id)
            
        
        for perm in all_default_permssions:
            # FETCH LINKED MENUS
            menu_accessible_to_all_profil_flag = perm.get('menu_accessible_to_all_profil_flag',None)
            app_accessible_to_all_profil_flag = perm.get('app_accessible_to_all_profil_flag',None)
            action_accessible_to_all_profil_flag = perm.get('action_accessible_to_all_profil_flag',None)
            component_accessible_to_all_profil_flag = perm.get('component_accessible_to_all_profil_flag',None)
            print(f"--- menu_accessible_to_all_profil_flag : {menu_accessible_to_all_profil_flag}")
            print(f"--- app_accessible_to_all_profil_flag : {app_accessible_to_all_profil_flag}")
            print(f"--- action_accessible_to_all_profil_flag : {action_accessible_to_all_profil_flag}")
            print(f"--- component_accessible_to_all_profil_flag : {component_accessible_to_all_profil_flag}")
            if menu_accessible_to_all_profil_flag is not None:
                linked_menus = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.SYS_MENU,
                    output_data_type = OutputDataType.DEFAULT,
                    all_data=True,
                    query={
                        "filter__menu_accessible_to_all_profil_flag":menu_accessible_to_all_profil_flag
                    },
                    user=user_details,
                )
                print(f"--- linked_menus : {len(linked_menus)}")
                for linked_menu in linked_menus:
                    await recursive_checking_submenus(linked_menu, perm['id'])  
                    
            if app_accessible_to_all_profil_flag is not None:
                linked_srcs = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.SYS_APPLICATION,
                    output_data_type = OutputDataType.DEFAULT,
                    all_data=True,
                    query={
                        "filter__app_accessible_to_all_profil_flag":app_accessible_to_all_profil_flag
                    },
                    user=user_details,
                )
                for linked_src in linked_srcs:
                    await saving_app_or_action_or_view_permission_target(linked_src['id'], perm['id'])
                    
            if action_accessible_to_all_profil_flag is not None:
                linked_srcs = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.RBAC_ACTION,
                    output_data_type = OutputDataType.DEFAULT,
                    all_data=True,
                    query={
                        "filter__action_accessible_to_all_profil_flag":action_accessible_to_all_profil_flag
                    },
                    user=user_details,
                )
                for linked_src in linked_srcs:
                    await saving_app_or_action_or_view_permission_target(linked_src['id'], perm['id'])
                    
            if component_accessible_to_all_profil_flag is not None:
                linked_srcs = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.RBAC_ACTION,
                    output_data_type = OutputDataType.DEFAULT,
                    all_data=True,
                    query={
                        "filter__component_accessible_to_all_profil_flag":component_accessible_to_all_profil_flag
                    },
                    user=user_details,
                )
                for linked_src in linked_srcs:
                    await saving_app_or_action_or_view_permission_target(linked_src['id'], perm['id'])
        

        
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "success",
            }
        )
        
    async def fetch_config_roles(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ): 
        # DECODE USER TOKEN 
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        saas_config_info  = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )
        
        if not saas_config_info:
            message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        authenticationService = AuthenticatedService()
        support_email = await  self.get_system_support_email(saas_config_info,self.accept_language) 
        
        role_pipeline = [
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PERMISSION_ROLE.model_name}",
                    'localField': "_id",
                    'foreignField': "rbac_role_id",
                    'as': "unwind__rbac_permission_role"
                }
            },
            {
            "$match": {
                    "system_reserved_actions":True,
                }
            },
            
        ]
        roles = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key = CollectionKey.RBAC_ROLE,
            output_data_type=output_data_type,
            all_data=True,
            accept_language=self.accept_language,
            pipeline=role_pipeline,
        ) 
        
        extra_data = {
            "max": 0,
            "limit": limit
        }
        self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")
        # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
        if not all_data:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                accept_language=self.accept_language,
                query={},
                user=user_details,
            )
            extra_data = {
                "max":max_data,
                "limit":limit
            }
            self.app_debug_print(f"\n\n\n after extra_data : {extra_data} \n\n")

        return  CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":roles,
                    "limit":extra_data['limit'],
                    "max":extra_data['max'],
                }
            ) 
        
        
    async def fetch_config_rbac_actions(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
       
        # DECODE USER TOKEN 
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        saas_config_info  = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )
        
        if not saas_config_info:
            message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        authenticationService = AuthenticatedService()
        support_email = await  self.get_system_support_email(saas_config_info,self.accept_language) 
        rbac_actions =  await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_ACTION,
                all_data=True,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={},
            user=user_details,
        ) 
        self.app_debug_print(f"\n\n\n rbac_actions : {rbac_actions} \n\n",False)
        extra_data = {
            "max": 0,
            "limit": limit
        }
        formated_rbac_actions = []
        for action in rbac_actions:
            if output_data_type == OutputDataType.DATA_TABLE.value:
                action_targeted_id = action['id']['display_value']
            elif output_data_type == OutputDataType.DEFAULT.value:
                action_targeted_id = action['id']
            elif output_data_type == OutputDataType.TREE.value:
                action_targeted_id = action['id']
            else :
                action_targeted_id:None
            list_of_guard_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(action_targeted_id)),
                        }
                    }, 
                ],
                all_data=True
            )

            list_of_guard_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(action_targeted_id)),
                        }
                    }, 
                ],
                all_data=True
            )
            action_current_item = {
                **action,
                'restricted_platform':list_of_guard_restricted_platforms,
                'restricted_profil':list_of_guard_restricted_profils,
            } 
            formated_rbac_actions.append(action_current_item)

        self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")
        # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
        if not all_data:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.RBAC_ACTION,
                accept_language=self.accept_language,
                query={},
                user=user_details,
            )
            extra_data = {
                "max":max_data,
                "limit":limit
            }
            self.app_debug_print(f"\n\n\n after extra_data : {extra_data} \n\n")

        return  CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":formated_rbac_actions,
                    "limit":extra_data['limit'],
                    "max":extra_data['max'],
                }
            ) 
    
    async def fetch_config_single_rbac_actions(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
       
        # DECODE USER TOKEN 
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        saas_config_info  = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )
        
        if not saas_config_info:
            message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        item_id = request.query_params.get('item_id',None)
        if not item_id:
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
            raise HTTPException(status_code=400, detail=message)
        authenticationService = AuthenticatedService()
        support_email = await  self.get_system_support_email(saas_config_info,self.accept_language) 
        rbac_actions =  await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_ACTION,
                all_data=True,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    "filter___id":item_id
                },
            user=user_details,
        ) 
        self.app_debug_print(f"\n\n\n rbac_actions : {rbac_actions} \n\n",False)
        extra_data = {
            "max": 0,
            "limit": limit
        }
        formated_rbac_actions = []
        for action in rbac_actions:
            if output_data_type == OutputDataType.DATA_TABLE.value:
                action_targeted_id = action['id']['display_value']
            elif output_data_type == OutputDataType.DEFAULT.value:
                action_targeted_id = action['id']
            elif output_data_type == OutputDataType.TREE.value:
                action_targeted_id = action['id']
            else :
                action_targeted_id:None
            list_of_guard_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(action_targeted_id)),
                        }
                    }, 
                ],
                all_data=True
            )

            list_of_guard_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(action_targeted_id)),
                        }
                    }, 
                ],
                all_data=True
            )
            action_current_item = {
                **action,
                'restricted_platform':list_of_guard_restricted_platforms,
                'restricted_profil':list_of_guard_restricted_profils,
            } 
            formated_rbac_actions.append(action_current_item)

        self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")
        # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
        if not all_data:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.RBAC_ACTION,
                accept_language=self.accept_language,
                query={},
                user=user_details,
            )
            extra_data = {
                "max":max_data,
                "limit":limit
            }
            self.app_debug_print(f"\n\n\n after extra_data : {extra_data} \n\n")

        return  CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":formated_rbac_actions,
                    "limit":extra_data['limit'],
                    "max":extra_data['max'],
                }
            ) 
    
    
    async def fetch_config_collection_meta_datas(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
       
        # DECODE USER TOKEN 
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        saas_config_info  = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )
        
        if not saas_config_info:
            message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        authenticationService = AuthenticatedService()
        support_email = await  self.get_system_support_email(saas_config_info,self.accept_language) 

        raw_query_params: Dict[str, str] = dict(request.query_params)
            
        query_params = self.convert_query_params(raw_query_params)
        self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
        sort = request.query_params.get("sort", {'created_at':-1})
        self.app_debug_print(f"Query Parameters (SORT): {sort}",False)
    
        crud_meta_datas =  await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_COLLECTION_CRUD_INFO,
                all_data=False,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    **query_params
                },
                sort=sort,
                limit=limit,
                page=page,
            user=user_details,
        ) 
        self.app_debug_print(f"\n\n\n crud_meta_datas : {len(crud_meta_datas)} \n\n",True)
        extra_data = {
            "max": 0,
            "limit": limit
        }
        self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")

        formated_crud_meta_datas = []
        for crud_meta_data in crud_meta_datas:
            crud_meta_data_rbac_endpoint_id = crud_meta_data.get('rbac_endpoint_id',{}).get('real_value',None)
            targeted_id = crud_meta_data.get('targeted_id',{}).get('real_value',None)
            if output_data_type == OutputDataType.DATA_TABLE.value:
                crud_meta_data_targeted_id = crud_meta_data['id']['display_value']
            elif output_data_type == OutputDataType.DEFAULT.value:
                crud_meta_data_targeted_id = crud_meta_data['id']
            elif output_data_type == OutputDataType.TREE.value:
                crud_meta_data_targeted_id = crud_meta_data['id']
            else :
                targeted_id = None
            
            list_of_guard_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(crud_meta_data_targeted_id)),
                        }
                    }, 
                ],
                all_data=True
            )

            list_of_guard_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(crud_meta_data_targeted_id)),
                        }
                    }, 
                ],
                all_data=True
            )
            rbac_endpoint = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ENDPOINT,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                query={
                    "filter___id":crud_meta_data_rbac_endpoint_id,
                },
                user=user_details,
            )

            app_item = await ApplicationService.get_single_app_item(
                app_id=targeted_id,
                apiConsumer=api_Consumer,
                accept_language= self.accept_language,
                output_data_type=output_data_type,
            )

            menu_item = await ApplicationService.get_single_menu_item(
                menu_id=targeted_id,
                apiConsumer=api_Consumer,
                accept_language= self.accept_language,
                output_data_type=output_data_type,
            )
            action_current_item = {
                **crud_meta_data,
                "app":app_item,
                "menu":menu_item,
                'restricted_platform':list_of_guard_restricted_platforms,
                'restricted_profil':list_of_guard_restricted_profils,
                'rbac_endpoint':rbac_endpoint,
            } 
            formated_crud_meta_datas.append(action_current_item)
        self.app_debug_print(f"\n\n\n list crud_meta_data : {len(formated_crud_meta_datas)} \n\n",True)
        if not all_data:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.REF_COLLECTION_CRUD_INFO,
                accept_language=self.accept_language,
                query={
                        **query_params
                    },
                user=user_details,
            )
            extra_data = {
                "max":max_data,
                "limit":limit
            }
            self.app_debug_print(f"\n\n\n after extra_data : {extra_data} \n\n")

        return  CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":formated_crud_meta_datas,
                    "limit":extra_data['limit'],
                    "max":extra_data['max'],
                }
            ) 
    async def fetch_custom_config_data_display_types(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
       
        # DECODE USER TOKEN 
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        saas_config_info  = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )
        
        if not saas_config_info:
            message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        authenticationService = AuthenticatedService()
        support_email = await  self.get_system_support_email(saas_config_info,self.accept_language) 

        raw_query_params: Dict[str, str] = dict(request.query_params)
            
        query_params = self.convert_query_params(raw_query_params)
        self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
        sort = request.query_params.get("sort", {'created_at':-1})
        self.app_debug_print(f"Query Parameters (SORT): {sort}",False)
    
        cfg_data_display_types =  await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_DATA_DISPLAY_TYPE,
                all_data=False,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    **query_params
                },
                sort=sort,
                limit=limit,
                page=page,
            user=user_details,
        ) 
        self.app_debug_print(f"\n\n\n cfg_data_display_types : {len(cfg_data_display_types)} \n\n",False)
        extra_data = {
            "max": 0,
            "limit": limit
        }
        self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")

        formated_crud_meta_datas = []
        for cfg_data_display_type in cfg_data_display_types:
            if output_data_type == OutputDataType.DATA_TABLE.value:
                targeted_id = cfg_data_display_type['targeted_id']['display_value']
                data_display_type_id = cfg_data_display_type['id']['display_value']
                ref_data_display_type_id = cfg_data_display_type['ref_data_display_type_id']['display_value']
            elif output_data_type == OutputDataType.DEFAULT.value:
                data_display_type_id = cfg_data_display_type['id']
                ref_data_display_type_id = cfg_data_display_type['ref_data_display_type_id']
                targeted_id = cfg_data_display_type['targeted_id']
            elif output_data_type == OutputDataType.TREE.value:
                data_display_type_id = cfg_data_display_type['id']
                ref_data_display_type_id = cfg_data_display_type['ref_data_display_type_id']
                targeted_id = cfg_data_display_type['targeted_id']
            else :
                data_display_type_id:None
                ref_data_display_type_id:None
                targeted_id = None

            list_of_guard_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(data_display_type_id)),
                        }
                    }, 
                ],
                all_data=True
            )

            list_of_guard_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(data_display_type_id)),
                        }
                    }, 
                ],
                all_data=True
            )
            ref_data_display_type = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_DATA_DISPLAY_TYPE,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                query={
                    "filter___id":ref_data_display_type_id,
                },
                user=user_details,
            )

            app_item = await ApplicationService.get_single_app_item(
                app_id=targeted_id,
                apiConsumer=api_Consumer,
                accept_language= self.accept_language,
                output_data_type=output_data_type,
            )

            menu_item = await ApplicationService.get_single_menu_item(
                menu_id=targeted_id,
                apiConsumer=api_Consumer,
                accept_language= self.accept_language,
                output_data_type=output_data_type,
            )
            action_current_item = {
                **cfg_data_display_type,
                "app":app_item,
                "menu":menu_item,
                'restricted_platform':list_of_guard_restricted_platforms,
                'restricted_profil':list_of_guard_restricted_profils,
                'ref_data_display_type':ref_data_display_type,
            } 
            formated_crud_meta_datas.append(action_current_item)

        if not all_data:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.CFG_DATA_DISPLAY_TYPE,
                accept_language=self.accept_language,
                query={
                        **query_params
                    },
                user=user_details,
            )
            extra_data = {
                "max":max_data,
                "limit":limit
            }
            self.app_debug_print(f"\n\n\n after extra_data : {extra_data} \n\n")

        return  CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":formated_crud_meta_datas,
                    "limit":extra_data['limit'],
                    "max":extra_data['max'],
                }
            ) 
    async def fetch_custom_config_children_display_types(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
       
        # DECODE USER TOKEN 
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        saas_config_info  = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )
        
        if not saas_config_info:
            message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        authenticationService = AuthenticatedService()
        support_email = await  self.get_system_support_email(saas_config_info,self.accept_language) 

        raw_query_params: Dict[str, str] = dict(request.query_params)
            
        query_params = self.convert_query_params(raw_query_params)
        self.app_debug_print(f"Query Parameters (converted): {query_params}",False)
        sort = request.query_params.get("sort", {'created_at':-1})
        self.app_debug_print(f"Query Parameters (SORT): {sort}",False)
    
        cfg_children_display_types =  await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_CHILDREN_DISPLAY_TYPE,
                all_data=False,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    **query_params
                },
                sort=sort,
                limit=limit,
                page=page,
            user=user_details,
        ) 
        self.app_debug_print(f"\n\n\n cfg_children_display_types : {len(cfg_children_display_types)} \n\n",False)
        extra_data = {
            "max": 0,
            "limit": limit
        }
        self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")

        formated_crud_meta_datas = []
        for cfg_children_display_type in cfg_children_display_types:
            if output_data_type == OutputDataType.DATA_TABLE.value:
                targeted_id = cfg_children_display_type['targeted_id']['display_value']
                data_display_type_id = cfg_children_display_type['id']['display_value']
                ref_children_display_type_id = cfg_children_display_type['ref_children_display_type_id']['display_value']
            elif output_data_type == OutputDataType.DEFAULT.value:
                data_display_type_id = cfg_children_display_type['id']
                ref_children_display_type_id = cfg_children_display_type['ref_children_display_type_id']
                targeted_id = cfg_children_display_type['targeted_id']
            elif output_data_type == OutputDataType.TREE.value:
                data_display_type_id = cfg_children_display_type['id']
                ref_children_display_type_id = cfg_children_display_type['ref_children_display_type_id']
                targeted_id = cfg_children_display_type['targeted_id']
            else :
                data_display_type_id:None
                ref_children_display_type_id:None
                targeted_id = None

            list_of_guard_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(data_display_type_id)),
                        }
                    }, 
                ],
                all_data=True
            )

            list_of_guard_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(data_display_type_id)),
                        }
                    }, 
                ],
                all_data=True
            )
            ref_children_display_type = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_CHILDREN_DISPLAY_TYPE,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                query={
                    "filter___id":ref_children_display_type_id,
                },
                user=user_details,
            )

            app_item = await ApplicationService.get_single_app_item(
                app_id=targeted_id,
                apiConsumer=api_Consumer,
                accept_language= self.accept_language,
                output_data_type=output_data_type,
            )

            menu_item = await ApplicationService.get_single_menu_item(
                menu_id=targeted_id,
                apiConsumer=api_Consumer,
                accept_language= self.accept_language,
                output_data_type=output_data_type,
            )
            action_current_item = {
                **cfg_children_display_type,
                "app":app_item,
                "menu":menu_item,
                'restricted_platform':list_of_guard_restricted_platforms,
                'restricted_profil':list_of_guard_restricted_profils,
                'ref_children_display_type':ref_children_display_type,
            } 
            formated_crud_meta_datas.append(action_current_item)

        if not all_data:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.CFG_CHILDREN_DISPLAY_TYPE,
                accept_language=self.accept_language,
                query={
                        **query_params
                    },
                user=user_details,
            )
            extra_data = {
                "max":max_data,
                "limit":limit
            }
            self.app_debug_print(f"\n\n\n after extra_data : {extra_data} \n\n")

        return  CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":formated_crud_meta_datas,
                    "limit":extra_data['limit'],
                    "max":extra_data['max'],
                }
            ) 
    

    async def fetch_config_data_display_types(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
       
        # DECODE USER TOKEN 
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        saas_config_info  = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )
        
        if not saas_config_info:
            message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        authenticationService = AuthenticatedService()
        support_email = await  self.get_system_support_email(saas_config_info,self.accept_language) 
        data_display_types =  await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_DATA_DISPLAY_TYPE,
                all_data=True,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={},
            user=user_details,
        ) 
        self.app_debug_print(f"\n\n\n data_display_types : {len(data_display_types)} \n\n",False)
        extra_data = {
            "max": 0,
            "limit": limit
        }
        self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")
        # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
        if not all_data:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.CFG_DATA_DISPLAY_TYPE,
                accept_language=self.accept_language,
                query={},
                user=user_details,
            )
            extra_data = {
                "max":max_data,
                "limit":limit
            }
            self.app_debug_print(f"\n\n\n after extra_data : {extra_data} \n\n")

        return  CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":data_display_types,
                    "limit":extra_data['limit'],
                    "max":extra_data['max'],
                }
            ) 

    async def fetch_config_children_display_types(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
       
        # DECODE USER TOKEN 
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        saas_config_info  = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )
        
        if not saas_config_info:
            message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        authenticationService = AuthenticatedService()
        support_email = await  self.get_system_support_email(saas_config_info,self.accept_language) 
        children_display_types =  await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_CHILDREN_DISPLAY_TYPE,
                all_data=True,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={},
            user=user_details,
        ) 
        self.app_debug_print(f"\n\n\n children_display_types : {len(children_display_types)} \n\n",False)
        extra_data = {
            "max": 0,
            "limit": limit
        }
        self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")
        # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
        if not all_data:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.CFG_CHILDREN_DISPLAY_TYPE,
                accept_language=self.accept_language,
                query={},
                user=user_details,
            )
            extra_data = {
                "max":max_data,
                "limit":limit
            }
            self.app_debug_print(f"\n\n\n after extra_data : {extra_data} \n\n")

        return  CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":children_display_types,
                    "limit":extra_data['limit'],
                    "max":extra_data['max'],
                }
            ) 
    
    async def fetch_config_rbac_components(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
       
        # DECODE USER TOKEN  rbac_permission_target
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        saas_config_info  = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )
        
        if not saas_config_info:
            message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        authenticationService = AuthenticatedService()
        support_email = await  self.get_system_support_email(saas_config_info,self.accept_language) 
        rbac_components =  await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_COMPONENT,
                all_data=True,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={},
            user=user_details,
        ) 
        
        extra_data = {
            "max": 0,
            "limit": limit
        }
        self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")
        formated_rbac_components = []
        for component in rbac_components:
            if output_data_type == OutputDataType.DATA_TABLE.value:
                action_targeted_id = component['id']['display_value']
            elif output_data_type == OutputDataType.DEFAULT.value:
                action_targeted_id = component['id']
            elif output_data_type == OutputDataType.TREE.value:
                action_targeted_id = component['id']
            else :
                action_targeted_id:None
            list_of_guard_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(action_targeted_id)),
                        }
                    }, 
                ],
                all_data=True
            )

            list_of_guard_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(action_targeted_id)),
                        }
                    }, 
                ],
                all_data=True
            )
            action_current_item = {
                **component,
                'restricted_platform':list_of_guard_restricted_platforms,
                'restricted_profil':list_of_guard_restricted_profils,
            } 
            formated_rbac_components.append(action_current_item)
        # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
        if not all_data:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.RBAC_COMPONENT,
                accept_language=self.accept_language,
                query={},
                user=user_details,
            )
            extra_data = {
                "max":max_data,
                "limit":limit
            }
            self.app_debug_print(f"\n\n\n after extra_data : {extra_data} \n\n")

        return  CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":formated_rbac_components,
                    "limit":extra_data['limit'],
                    "max":extra_data['max'],
                }
            ) 
        
    async def fetch_config_permissions(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ): 
        
        try:
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                user=user_details,
            )
            
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            authenticationService = AuthenticatedService()
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language) 
            
            print("in permission config step 1 ")
            rbac_titles = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_TITLE,
                output_data_type=OutputDataType(output_data_type).value,
                limit=limit,
                page=page,
                accept_language= self.accept_language,
                pipeline=[
                    
                    {
                        "$match": {
                            "rbac_title_id":None,
                            "is_activated":True
                        }
                    }, 
                    {
                        "$project":{
                            "_id":1,
                            "label":1,
                            "rbac_title_id":1,
                            "description_str":1,
                        }
                    },
                    
                    {
                        "$skip":limit * page
                    },
                    {
                        "$limit":limit
                    },
                     
                ]
            )
            self.app_debug_print("in permission config step 2 ")
            if not rbac_titles:
                extra_data = {
                    "max": 0,
                    "limit": limit
                }
                if not all_data:
                    # get max
                    max_data = await self.generic_service.count_data_from_collection(
                        collection_key=CollectionKey.RBAC_TITLE,
                        accept_language= self.accept_language,
                        query={
                            "filter__rbac_title_id":None,
                            "filter__is_activated":True,
                        },
                        user=user_details,
                    )
                    extra_data = {
                        "max":max_data,
                        "limit":limit
                    }
                return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data":[],
                        "limit":extra_data['limit'],
                        "max":extra_data['max'],
                    }
                )
                # message = self.get_response_message(MessageCategory.EXCEPTIONS, "RBAC_TITLE_MISSING", self.accept_language,email=support_email)
                # self.app_debug_print(f" missing rbac_titles : {message}",)
                # raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
            
            self.app_debug_print("in permission config step 3 ")
            
            # RECURSIVE RBAC TITLE 
            async def rbac_title_recursive_children(rbac_title,parent_rbac_title_id=None):
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    rbac_title_id = rbac_title['id']['display_value'] 
                elif output_data_type == OutputDataType.DEFAULT.value:
                    rbac_title_id = rbac_title['id'] 
                else :
                    rbac_title_id = rbac_title['id']
                
                permission_pipeline = [
                    # // STAGE 1: Early filtering before lookup
                    {
                        "$match": {
                            "rbac_title_id": ObjectId(rbac_title_id)
                        }
                    },
                    
                    # // STAGE 2: Efficient lookup with projection
                    {
                        "$lookup": {
                        "from": f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                        "let": { "doc_id": "$_id" },
                        "pipeline": [
                            {
                            "$match": {
                                "$expr": { "$eq": ["$rbac_permission_id", "$$doc_id"] }
                            }
                            },
                            {
                            "$project": {
                                "_id": 1,
                                "rbac_action_id": 1,
                                "targeted_id": 1,
                                "rbac_component_id": 1,
                                "rbac_permission_id": 1
                            }
                            }
                        ],
                        "as": "unwind__rbac_permission_target"
                        }
                    },
                    
                    # // STAGE 3: Final projection with optimized field selection
                    {
                        "$project": {
                        "_id": 1,
                        "label": 1,
                        # "description_str": 1,
                        "url": 1,
                        "rbac_title_id": 1,
                        "is_sudo_action": 1,
                        "is_sudo_group_action": 1,
                        # "flag": 1,
                        "unwind__rbac_permission_target": {
                            "$map": {
                            "input": "$unwind__rbac_permission_target",
                            "as": "target",
                            "in": {
                                "_id": "$$target._id",
                                "rbac_action_id": "$$target.rbac_action_id",
                                "targeted_id": "$$target.targeted_id",
                                "rbac_component_id": "$$target.rbac_component_id",
                                "rbac_permission_id": "$$target.rbac_permission_id"
                            }
                            }
                        }
                        }
                    }
                ]
                
                permissions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key = CollectionKey.RBAC_PERMISSION,
                    output_data_type=output_data_type,
                    accept_language= self.accept_language,
                    pipeline=permission_pipeline,
                ) 
                
                formatted_permissions = []
                self.app_debug_print(f"\n\n\n element step: 0 {len(permissions)} \n\n")
                for i,element in enumerate(permissions):
                    self.app_debug_print(f"\n\n\n element step: 1 {len(element['rbac_permission_target'])} \n\n")
                    # element['rbac_permission_target'] 
                    list_of_permission_targets = element['rbac_permission_target'];
                    
                    if output_data_type == OutputDataType.DATA_TABLE.value:
                        permission_targeted_id = element['id']['display_value']
                    elif output_data_type == OutputDataType.DEFAULT.value:
                        permission_targeted_id = element['id']
                    elif output_data_type == OutputDataType.TREE.value:
                        permission_targeted_id = element['id']
                    else :
                        permission_targeted_id:None

                    
                    self.app_debug_print(f"\n\n\n element step: 2 \n\n")
                    list_of_permission_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                        collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                        output_data_type=output_data_type,
                        accept_language=self.accept_language,
                        pipeline=[ 
                            {
                                "$match": {
                                    "targeted_id":ObjectId(str(permission_targeted_id)),
                                }
                            }, 
                            {
                                "$project":{
                                    "_id":"$_id",
                                    "targeted_id":"$targeted_id",
                                    "is_hidden":"$is_hidden",
                                    "is_locked":"$is_locked",
                                    "is_activated":"$is_activated",
                                    "rbac_profile_id":"$rbac_profile_id",
                                }
                            }
                        ],  
                        all_data=True,
                    )
                    if permission_targeted_id == '6825c5fa5951622b74875cba':
                        self.app_debug_print(f"\n\n\n\n\n\n\n\n\n permission_target_found : {len(list_of_permission_targets)} \n\n\n\n\n\n",False)
                    # print(f"\n\n\n element step: 3 \n\n")
                    list_of_permission_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                        collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                        output_data_type=output_data_type,
                        accept_language=self.accept_language,
                        pipeline=[ 
                            {
                                "$match": {
                                    "targeted_id":ObjectId(str(permission_targeted_id)),
                                }
                            }, 
                            {
                                "$project":{
                                    "_id":"$_id",
                                    "targeted_id":"$targeted_id",
                                    "is_hidden":"$is_hidden",
                                    "is_locked":"$is_locked",
                                    "is_activated":"$is_activated",
                                    "ref_api_consumer_id":"$ref_api_consumer_id",
                                }
                            }
                        ],  
                        all_data=True,
                    )
                    self.app_debug_print(f"\n\n\n element step: 4 \n\n")
                    #FORMAT PERMISSION TARGET
                    permission_targets = []

                    for permission_target in list_of_permission_targets:
                        
                        if output_data_type == OutputDataType.DATA_TABLE.value:
                            targeted_id = permission_target['id']['display_value']
                        elif output_data_type == OutputDataType.DEFAULT.value:
                            targeted_id = permission_target['id']
                        elif output_data_type == OutputDataType.TREE.value:
                            targeted_id = permission_target['id']
                        else :
                            targeted_id = None
                            
                        permission_target_found = await self.generic_service.fetch_native_aggregate_one_from_collection(
                            collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                            output_data_type=OutputDataType(output_data_type).value,
                            accept_language= self.accept_language,
                            pipeline=[
                                {
                                    "$match": {
                                        "_id":ObjectId(str(targeted_id)),
                                    }
                                }, 
                                {
                                    "$project":{
                                        "_id":"$_id",
                                        "targeted_id":"$targeted_id",
                                        "rbac_action_id":"$rbac_action_id",
                                        "rbac_component_id":"$rbac_component_id",
                                        "rbac_permission_id":"$rbac_permission_id",
                                    }
                                }
                            ] 
                        )
                        if permission_target_found: 
                            list_of_target_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                                output_data_type=output_data_type,
                                accept_language=self.accept_language,
                                pipeline=[ 
                                    {
                                        "$match": {
                                           "targeted_id":ObjectId(str(targeted_id)),
                                        }
                                    }, 
                                    {
                                        "$project":{
                                            "_id":"$_id",
                                            "targeted_id":"$targeted_id",
                                            "is_hidden":"$is_hidden",
                                            "is_locked":"$is_locked",
                                            "is_activated":"$is_activated",
                                            "rbac_profile_id":"$rbac_profile_id",
                                        }
                                    }
                                ],
                                all_data=True
                            )

                            list_of_target_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                                output_data_type=output_data_type,
                                accept_language=self.accept_language,
                                pipeline=[ 
                                    {
                                        "$match": {
                                           "targeted_id":ObjectId(str(targeted_id)),
                                        }
                                    }, 
                                    {
                                        "$project":{
                                            "_id":"$_id",
                                            "targeted_id":"$targeted_id",
                                            "is_hidden":"$is_hidden",
                                            "is_locked":"$is_locked",
                                            "is_activated":"$is_activated",
                                            "ref_api_consumer_id":"$ref_api_consumer_id",
                                        }
                                    }
                                ],
                                all_data=True
                            ) 
                            
                            permission_targets.append({
                                **permission_target_found,
                                'restricted_platform':list_of_target_restricted_platforms,
                                'restricted_profil':list_of_target_restricted_profils,
                            }) 
                                
                    formatted_permissions.append({
                        **element,
                        'restricted_platform':list_of_permission_restricted_platforms,
                        'rbac_permission_target':permission_targets,
                        'restricted_profil':list_of_permission_restricted_profils,
                    })
                
                endpoints_pipeline = [
                    # // STAGE 1: Early filtering before lookup
                    {
                        "$match": {
                            "rbac_title_id": ObjectId(rbac_title_id)
                        }
                    },
                    
                    # // STAGE 2: Efficient lookup with projection
                    {
                        "$lookup": {
                        "from": f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                        "let": { "doc_id": "$_id" },
                        "pipeline": [
                            {
                            "$match": {
                                "$expr": { "$eq": ["$targeted_id", "$$doc_id"] }
                            }
                            },
                            {
                            "$project": {
                                "_id": 1,
                                "rbac_action_id": 1,
                                "targeted_id": 1,
                                "rbac_component_id": 1,
                                "rbac_permission_id": 1
                            }
                            }
                        ],
                        "as": "unwind__rbac_permission_target"
                        }
                    },
                    
                    # // STAGE 3: Final projection with optimized field selection
                    {
                        "$project": {
                        "_id": 1,
                        "label": 1,
                        # "description_str": 1,
                        "url": 1,
                        "rbac_title_id": 1,
                        "is_sudo_action": 1,
                        "is_sudo_group_action": 1,
                        # "flag": 1,
                        "unwind__rbac_permission_target": {
                            "$map": {
                            "input": "$unwind__rbac_permission_target",
                            "as": "target",
                            "in": {
                                "_id": "$$target._id",
                                "rbac_action_id": "$$target.rbac_action_id",
                                "targeted_id": "$$target.targeted_id",
                                "rbac_component_id": "$$target.rbac_component_id",
                                "rbac_permission_id": "$$target.rbac_permission_id"
                            }
                            }
                        }
                        }
                    }
                ]

                
                endpoints = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key = CollectionKey.RBAC_ENDPOINT,
                    output_data_type=output_data_type,
                    accept_language= self.accept_language,
                    pipeline=endpoints_pipeline,
                ) 
                
                self.app_debug_print(f"\n\n\n element step: 5 \n\n")
                formatted_endpoints = []
                for i,element in enumerate(endpoints):
                    list_of_permission_targets = element['rbac_permission_target'];
                    if output_data_type == OutputDataType.DATA_TABLE.value:
                        endpoint_targeted_id = element['id']['display_value']
                    elif output_data_type == OutputDataType.DEFAULT.value:
                        endpoint_targeted_id = element['id']
                    elif output_data_type == OutputDataType.TREE.value:
                        endpoint_targeted_id = element['id']
                    else :
                        endpoint_targeted_id:None 
                        
                    list_of_endpoint_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                        collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                        output_data_type=output_data_type,
                        accept_language=self.accept_language,
                        pipeline=[ 
                            {
                                "$match": {
                                    "targeted_id":ObjectId(str(endpoint_targeted_id)),
                                }
                            }, 
                            {
                                "$project":{
                                    "_id":"$_id",
                                    "targeted_id":"$targeted_id",
                                    "is_hidden":"$is_hidden",
                                    "is_locked":"$is_locked",
                                    "is_activated":"$is_activated",
                                    "rbac_profile_id":"$rbac_profile_id",
                                }
                            }
                        ],
                        all_data=True 
                    )

                    list_of_endpoint_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                        collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                        output_data_type=output_data_type,
                        accept_language=self.accept_language,
                        pipeline=[ 
                            {
                                "$match": {
                                    "targeted_id":ObjectId(str(endpoint_targeted_id)),
                                }
                            }, 
                            {
                                "$project":{
                                    "_id":"$_id",
                                    "targeted_id":"$targeted_id",
                                    "is_hidden":"$is_hidden",
                                    "is_locked":"$is_locked",
                                    "is_activated":"$is_activated",
                                    "ref_api_consumer_id":"$ref_api_consumer_id",
                                }
                            }
                        ],

                        all_data=True
                    ) 
                    #FORMAT PERMISSION TARGET
                    permission_targets = []
                    for permission_target in list_of_permission_targets:
                        if output_data_type == OutputDataType.DATA_TABLE.value:
                            targeted_id = permission_target['id']['display_value']
                        elif output_data_type == OutputDataType.DEFAULT.value:
                            targeted_id = permission_target['id']
                        elif output_data_type == OutputDataType.TREE.value:
                            targeted_id = permission_target['id']
                        else :
                            targeted_id = None
                            
                        # permission_target_found = await self.generic_service.fetch_one_from_collection(
                        #     collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                        #     output_data_type=OutputDataType(output_data_type).value,
                        #     accept_language= self.accept_language,
                        #     query={
                        #         "filter___id":targeted_id,
                        #     }
                        # )
                        permission_target_found = await self.generic_service.fetch_native_aggregate_one_from_collection(
                            collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                            output_data_type=OutputDataType(output_data_type).value,
                            accept_language= self.accept_language,
                            pipeline=[
                                {
                                    "$match": {
                                        "_id":ObjectId(str(targeted_id)),
                                    }
                                }, 
                                {
                                    "$project":{
                                        "_id":"$_id",
                                        "targeted_id":"$targeted_id",
                                        "rbac_action_id":"$rbac_action_id",
                                        "rbac_component_id":"$rbac_component_id",
                                        "rbac_permission_id":"$rbac_permission_id",
                                    }
                                }
                            ] 
                        )
                        self.app_debug_print(f"\n\n\n\n\n\n\n\n\n permission_target_found : {permission_target_found} \n\n\n\n\n\n",False)
                        if permission_target_found: 
                            list_of_target_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                                output_data_type=output_data_type,
                                accept_language=self.accept_language,
                                pipeline=[ 
                                    {
                                        "$match": {
                                           "targeted_id":ObjectId(str(targeted_id)),
                                        }
                                    }, 
                                    {
                                        "$project":{
                                            "_id":"$_id",
                                            "targeted_id":"$targeted_id",
                                            "is_hidden":"$is_hidden",
                                            "is_locked":"$is_locked",
                                            "is_activated":"$is_activated",
                                            "rbac_profile_id":"$rbac_profile_id",
                                        }
                                    }
                                ],
                                all_data=True,
                            )

                            list_of_target_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                                output_data_type=output_data_type,
                                accept_language=self.accept_language,
                                pipeline=[ 
                                    {
                                        "$match": {
                                           "targeted_id":ObjectId(str(targeted_id)),
                                        }
                                    }, 
                                    {
                                        "$project":{
                                            "_id":"$_id",
                                            "targeted_id":"$targeted_id",
                                            "is_hidden":"$is_hidden",
                                            "is_locked":"$is_locked",
                                            "is_activated":"$is_activated",
                                            "ref_api_consumer_id":"$ref_api_consumer_id",
                                        }
                                    }
                                ],
                                all_data=True,
                            ) 
                            permission_targets.append({
                                **permission_target_found,
                                'restricted_platform':list_of_target_restricted_platforms,
                                'restricted_profil':list_of_target_restricted_profils,
                            }) 
                                
                    
                    formatted_endpoints.append({
                        **element,
                        'restricted_platform':list_of_endpoint_restricted_platforms,
                        'rbac_permission_target':permission_targets,
                        'restricted_profil':list_of_endpoint_restricted_profils,
                    })
                
                
                self.app_debug_print(f"\n\n\n element step: 6 \n\n")
                # FETCH CHILDREN FROM HERE
                children_rbac_titles = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_TITLE,
                    output_data_type=OutputDataType(output_data_type).value,
                    limit=100,#limit,
                    page=0,#page,
                    accept_language= self.accept_language,
                    pipeline=[
                        {
                            "$match": {
                                "rbac_title_id":ObjectId(str(parent_rbac_title_id)),
                                "is_activated":True
                            }
                        }, 
                        {
                            "$project":{
                                "_id":1,
                                "label":1,
                                "rbac_title_id":1,
                                "description_str":1,
                            }
                        }
                    ]
                )
                formatted_children_data = []
                self.app_debug_print(f"\n\n\n element step: 7 \n\n")
                for rbac_title_child in children_rbac_titles:
                    if output_data_type == OutputDataType.DATA_TABLE.value:
                        rbac_title_id = rbac_title_child['id']['display_value'] 
                    elif output_data_type == OutputDataType.DEFAULT.value:
                        rbac_title_id = rbac_title_child['id'] 
                    else :
                        rbac_title_id = rbac_title_child['id']
                    
                    formated_from_recursive = await rbac_title_recursive_children(rbac_title_child,rbac_title_id)
                    formatted_children_data.append(formated_from_recursive)
                return {
                    "rbac_title":rbac_title,
                    "permissions":formatted_permissions,
                    "endpoints":formatted_endpoints,
                    "children":formatted_children_data
                }
            formatted_data = [];
            # Get the start time
            start_time = time.time()  # in seconds since epoch
            start_datetime = datetime.now()
            self.app_debug_print(f"rbac_titles Starting at: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            for index,rbac_title in enumerate(rbac_titles):
                if index == 0:
                    self.app_debug_print(f"\n\n\n rbac_title : {rbac_title} \n\n\n\n\n\n",False)
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    rbac_title_id = rbac_title['id']['display_value'] 
                elif output_data_type == OutputDataType.DEFAULT.value:
                    rbac_title_id = rbac_title['id'] 
                else :
                    rbac_title_id = rbac_title['id']
                
                formated_from_recursive = await rbac_title_recursive_children(rbac_title, parent_rbac_title_id=rbac_title_id) 
                formatted_data.append(formated_from_recursive)
                
            # Initialize extra_data unconditionally. len(
            extra_data = {
                "max": 0,
                "limit": limit
            }
            self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.RBAC_TITLE,
                    accept_language= self.accept_language,
                    query={
                        "filter__rbac_title_id":None,
                        "filter__is_activated":True,
                    },
                    user=user_details,
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }
            self.app_debug_print(f"\n\n\n LAST CONFIG PERMISSION LN: {len(formatted_data)} \n\n")
            # Get the end time
            end_time = time.time()
            end_datetime = datetime.now()

            # Calculate differences
            time_diff_seconds = end_time - start_time
            time_diff_datetime = end_datetime - start_datetime

            self.app_debug_print(f"\n\n\n\n\nCONFIG PERMISSION Finished at: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            self.app_debug_print(f"Time taken (seconds): {time_diff_seconds:.2f}")
            self.app_debug_print(f"Time taken (HH:MM:SS): {str(time_diff_datetime)}")
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data":formatted_data,
                        "limit":extra_data['limit'],
                        "max":extra_data['max'],
                    }
                ) 
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR CONFIG PERM 1 : {e} \n\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 CONFIG PERM : {e} \n\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))
    
    async def fetch_simplified_config_rbac_title_sub_permissions(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ): 
        
        try:
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                user=user_details,
            )
            
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            authenticationService = AuthenticatedService()
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language) 
            item_id = request.query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            
            # Get the start time
            start_time = time.time()  # in seconds since epoch
            start_datetime = datetime.now()

            permission_pipeline = [
                # // STAGE 1: Early filtering before lookup
                {
                    "$match": {
                        "rbac_title_id": ObjectId(item_id)
                    }
                },
                
                # // STAGE 2: Efficient lookup with projection
                {
                    "$lookup": {
                    "from": f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                    "let": { "doc_id": "$_id" },
                    "pipeline": [
                        {
                        "$match": {
                            "$expr": { "$eq": ["$rbac_permission_id", "$$doc_id"] }
                        }
                        },
                        {
                        "$project": {
                            "_id": 1,
                            "rbac_action_id": 1,
                            "targeted_id": 1,
                            "rbac_component_id": 1,
                            "rbac_permission_id": 1
                        }
                        }
                    ],
                    "as": "unwind__rbac_permission_target"
                    }
                },
                
                # // STAGE 3: Final projection with optimized field selection
                {
                    "$project": {
                    "_id": 1,
                    "label": 1,
                    # "description_str": 1,
                    "url": 1,
                    "rbac_title_id": 1,
                    "is_sudo_action": 1,
                    "is_sudo_group_action": 1,
                    # "flag": 1,
                    "unwind__rbac_permission_target": {
                        "$map": {
                        "input": "$unwind__rbac_permission_target",
                        "as": "target",
                        "in": {
                            "_id": "$$target._id",
                            "rbac_action_id": "$$target.rbac_action_id",
                            "targeted_id": "$$target.targeted_id",
                            "rbac_component_id": "$$target.rbac_component_id",
                            "rbac_permission_id": "$$target.rbac_permission_id"
                        }
                        }
                    }
                    }
                }
            ]
            
            permissions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key = CollectionKey.RBAC_PERMISSION,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                all_data=True,
                page=0,
                limit=1000,
                pipeline=permission_pipeline,
            ) 
            
            formatted_permissions = []
            self.app_debug_print(f"\n\n\n element step: 0 {len(permissions)} \n\n")
            for i,element in enumerate(permissions):
                self.app_debug_print(f"\n\n\n element step: 1 {len(element['rbac_permission_target'])} \n\n")
                # element['rbac_permission_target'] 
                list_of_permission_targets = element['rbac_permission_target'];
                
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    permission_targeted_id = element['id']['display_value']
                elif output_data_type == OutputDataType.DEFAULT.value:
                    permission_targeted_id = element['id']
                elif output_data_type == OutputDataType.TREE.value:
                    permission_targeted_id = element['id']
                else :
                    permission_targeted_id:None

                
                self.app_debug_print(f"\n\n\n element step: 2 \n\n")
                list_of_permission_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=[ 
                        {
                            "$match": {
                                "targeted_id":ObjectId(str(permission_targeted_id)),
                            }
                        }, 
                        {
                            "$project":{
                                "_id":"$_id",
                                "targeted_id":"$targeted_id",
                                "is_hidden":"$is_hidden",
                                "is_locked":"$is_locked",
                                "is_activated":"$is_activated",
                                "rbac_profile_id":"$rbac_profile_id",
                            }
                        }
                    ],  
                    all_data=True,
                )
                if permission_targeted_id == '6825c5fa5951622b74875cba':
                    self.app_debug_print(f"\n\n\n\n\n\n\n\n\n permission_target_found : {len(list_of_permission_targets)} \n\n\n\n\n\n",False)
                # print(f"\n\n\n element step: 3 \n\n")
                list_of_permission_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=[ 
                        {
                            "$match": {
                                "targeted_id":ObjectId(str(permission_targeted_id)),
                            }
                        }, 
                        {
                            "$project":{
                                "_id":"$_id",
                                "targeted_id":"$targeted_id",
                                "is_hidden":"$is_hidden",
                                "is_locked":"$is_locked",
                                "is_activated":"$is_activated",
                                "ref_api_consumer_id":"$ref_api_consumer_id",
                            }
                        }
                    ],  
                    all_data=True,
                )
                self.app_debug_print(f"\n\n\n element step: 4 \n\n")
                #FORMAT PERMISSION TARGET
                permission_targets = []

                for permission_target in list_of_permission_targets:
                    
                    if output_data_type == OutputDataType.DATA_TABLE.value:
                        targeted_id = permission_target['id']['display_value']
                    elif output_data_type == OutputDataType.DEFAULT.value:
                        targeted_id = permission_target['id']
                    elif output_data_type == OutputDataType.TREE.value:
                        targeted_id = permission_target['id']
                    else :
                        targeted_id = None
                        
                    permission_target_found = await self.generic_service.fetch_native_aggregate_one_from_collection(
                        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language= self.accept_language,
                        pipeline=[
                            {
                                "$match": {
                                    "_id":ObjectId(str(targeted_id)),
                                }
                            }, 
                            {
                                "$project":{
                                    "_id":"$_id",
                                    "targeted_id":"$targeted_id",
                                    "rbac_action_id":"$rbac_action_id",
                                    "rbac_component_id":"$rbac_component_id",
                                    "rbac_permission_id":"$rbac_permission_id",
                                }
                            }
                        ] 
                    )
                    if permission_target_found: 
                        list_of_target_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                            collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                            output_data_type=output_data_type,
                            accept_language=self.accept_language,
                            pipeline=[ 
                                {
                                    "$match": {
                                        "targeted_id":ObjectId(str(targeted_id)),
                                    }
                                }, 
                                {
                                    "$project":{
                                        "_id":"$_id",
                                        "targeted_id":"$targeted_id",
                                        "is_hidden":"$is_hidden",
                                        "is_locked":"$is_locked",
                                        "is_activated":"$is_activated",
                                        "rbac_profile_id":"$rbac_profile_id",
                                    }
                                }
                            ],
                            all_data=True
                        )

                        list_of_target_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                            collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                            output_data_type=output_data_type,
                            accept_language=self.accept_language,
                            pipeline=[ 
                                {
                                    "$match": {
                                        "targeted_id":ObjectId(str(targeted_id)),
                                    }
                                }, 
                                {
                                    "$project":{
                                        "_id":"$_id",
                                        "targeted_id":"$targeted_id",
                                        "is_hidden":"$is_hidden",
                                        "is_locked":"$is_locked",
                                        "is_activated":"$is_activated",
                                        "ref_api_consumer_id":"$ref_api_consumer_id",
                                    }
                                }
                            ],
                            all_data=True
                        ) 
                        
                        permission_targets.append({
                            **permission_target_found,
                            'restricted_platform':list_of_target_restricted_platforms,
                            'restricted_profil':list_of_target_restricted_profils,
                        }) 
                            
                formatted_permissions.append({
                    **element,
                    'restricted_platform':list_of_permission_restricted_platforms,
                    'rbac_permission_target':permission_targets,
                    'restricted_profil':list_of_permission_restricted_profils,
                })
            
             
            extra_data = {
                "max": 0,
                "limit": limit
            }
            self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION,
                    accept_language= self.accept_language,
                    query={
                        "filter__rbac_title_id":item_id,
                    },
                    user=user_details,
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }
            self.app_debug_print(f"\n\n\n LAST CONFIG PERMISSION LN: {len(formatted_permissions)} \n\n")
            # Get the end time
            end_time = time.time()
            end_datetime = datetime.now()

            # Calculate differences
            time_diff_seconds = end_time - start_time
            time_diff_datetime = end_datetime - start_datetime

            self.app_debug_print(f"\n\n\n\n\nCONFIG PERMISSION Finished at: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            self.app_debug_print(f"Time taken (seconds): {time_diff_seconds:.2f}")
            self.app_debug_print(f"Time taken (HH:MM:SS): {str(time_diff_datetime)}")
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data":formatted_permissions,
                        "limit":extra_data['limit'],
                        "max":extra_data['max'],
                    }
                ) 
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR CONFIG PERM 1 : {e} \n\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 CONFIG PERM : {e} \n\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))
        
    async def fetch_simplified_config_rbac_title_single_permission(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ): 
        
        try:
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                user=user_details,
            )
            
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            authenticationService = AuthenticatedService()
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language) 
            item_id = request.query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            
            # Get the start time
            print(f"\n\n\nitem_id : {item_id}")
            start_time = time.time()  # in seconds since epoch
            start_datetime = datetime.now()

            permission_pipeline = [
                # // STAGE 1: Early filtering before lookup
                {
                    "$match": {
                        "_id": ObjectId(item_id)
                    }
                },
                
                # // STAGE 2: Efficient lookup with projection
                {
                    "$lookup": {
                    "from": f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                    "let": { "doc_id": "$_id" },
                    "pipeline": [
                        {
                        "$match": {
                            "$expr": { "$eq": ["$rbac_permission_id", "$$doc_id"] }
                        }
                        },
                        {
                        "$project": {
                            "_id": 1,
                            "rbac_action_id": 1,
                            "targeted_id": 1,
                            "rbac_component_id": 1,
                            "rbac_permission_id": 1
                        }
                        }
                    ],
                    "as": "unwind__rbac_permission_target"
                    }
                },
                
                # // STAGE 3: Final projection with optimized field selection
                {
                    "$project": {
                    "_id": 1,
                    "label": 1,
                    # "description_str": 1,
                    "url": 1,
                    "rbac_title_id": 1,
                    "is_sudo_action": 1,
                    "is_sudo_group_action": 1,
                    # "flag": 1,
                    "unwind__rbac_permission_target": {
                        "$map": {
                        "input": "$unwind__rbac_permission_target",
                        "as": "target",
                        "in": {
                            "_id": "$$target._id",
                            "rbac_action_id": "$$target.rbac_action_id",
                            "targeted_id": "$$target.targeted_id",
                            "rbac_component_id": "$$target.rbac_component_id",
                            "rbac_permission_id": "$$target.rbac_permission_id"
                        }
                        }
                    }
                    }
                }
            ]
            
            permissions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key = CollectionKey.RBAC_PERMISSION,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=permission_pipeline,
            ) 
            
            formatted_permissions = []
            self.app_debug_print(f"\n\n\n element step: 0 {len(permissions)} \n\n")
            for i,element in enumerate(permissions):
                self.app_debug_print(f"\n\n\n element step: 1 {len(element['rbac_permission_target'])} \n\n")
                # element['rbac_permission_target'] 
                list_of_permission_targets = element['rbac_permission_target'];
                
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    permission_targeted_id = element['id']['display_value']
                elif output_data_type == OutputDataType.DEFAULT.value:
                    permission_targeted_id = element['id']
                elif output_data_type == OutputDataType.TREE.value:
                    permission_targeted_id = element['id']
                else :
                    permission_targeted_id:None

                
                self.app_debug_print(f"\n\n\n element step: 2 \n\n")
                list_of_permission_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=[ 
                        {
                            "$match": {
                                "targeted_id":ObjectId(str(permission_targeted_id)),
                            }
                        }, 
                        {
                            "$project":{
                                "_id":"$_id",
                                "targeted_id":"$targeted_id",
                                "is_hidden":"$is_hidden",
                                "is_locked":"$is_locked",
                                "is_activated":"$is_activated",
                                "rbac_profile_id":"$rbac_profile_id",
                            }
                        }
                    ],  
                    all_data=True,
                )
                if permission_targeted_id == '6825c5fa5951622b74875cba':
                    self.app_debug_print(f"\n\n\n\n\n\n\n\n\n permission_target_found : {len(list_of_permission_targets)} \n\n\n\n\n\n",False)
                # print(f"\n\n\n element step: 3 \n\n")
                list_of_permission_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=[ 
                        {
                            "$match": {
                                "targeted_id":ObjectId(str(permission_targeted_id)),
                            }
                        }, 
                        {
                            "$project":{
                                "_id":"$_id",
                                "targeted_id":"$targeted_id",
                                "is_hidden":"$is_hidden",
                                "is_locked":"$is_locked",
                                "is_activated":"$is_activated",
                                "ref_api_consumer_id":"$ref_api_consumer_id",
                            }
                        }
                    ],  
                    all_data=True,
                )
                self.app_debug_print(f"\n\n\n element step: 4 \n\n")
                #FORMAT PERMISSION TARGET
                permission_targets = []

                for permission_target in list_of_permission_targets:
                    
                    if output_data_type == OutputDataType.DATA_TABLE.value:
                        targeted_id = permission_target['id']['display_value']
                    elif output_data_type == OutputDataType.DEFAULT.value:
                        targeted_id = permission_target['id']
                    elif output_data_type == OutputDataType.TREE.value:
                        targeted_id = permission_target['id']
                    else :
                        targeted_id = None
                        
                    permission_target_found = await self.generic_service.fetch_native_aggregate_one_from_collection(
                        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language= self.accept_language,
                        pipeline=[
                            {
                                "$match": {
                                    "_id":ObjectId(str(targeted_id)),
                                }
                            }, 
                            {
                                "$project":{
                                    "_id":"$_id",
                                    "targeted_id":"$targeted_id",
                                    "rbac_action_id":"$rbac_action_id",
                                    "rbac_component_id":"$rbac_component_id",
                                    "rbac_permission_id":"$rbac_permission_id",
                                }
                            }
                        ] 
                    )
                    if permission_target_found: 
                        list_of_target_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                            collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                            output_data_type=output_data_type,
                            accept_language=self.accept_language,
                            pipeline=[ 
                                {
                                    "$match": {
                                        "targeted_id":ObjectId(str(targeted_id)),
                                    }
                                }, 
                                {
                                    "$project":{
                                        "_id":"$_id",
                                        "targeted_id":"$targeted_id",
                                        "is_hidden":"$is_hidden",
                                        "is_locked":"$is_locked",
                                        "is_activated":"$is_activated",
                                        "rbac_profile_id":"$rbac_profile_id",
                                    }
                                }
                            ],
                            all_data=True
                        )

                        list_of_target_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                            collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                            output_data_type=output_data_type,
                            accept_language=self.accept_language,
                            pipeline=[ 
                                {
                                    "$match": {
                                        "targeted_id":ObjectId(str(targeted_id)),
                                    }
                                }, 
                                {
                                    "$project":{
                                        "_id":"$_id",
                                        "targeted_id":"$targeted_id",
                                        "is_hidden":"$is_hidden",
                                        "is_locked":"$is_locked",
                                        "is_activated":"$is_activated",
                                        "ref_api_consumer_id":"$ref_api_consumer_id",
                                    }
                                }
                            ],
                            all_data=True
                        ) 
                        
                        permission_targets.append({
                            **permission_target_found,
                            'restricted_platform':list_of_target_restricted_platforms,
                            'restricted_profil':list_of_target_restricted_profils,
                        }) 
                            
                formatted_permissions.append({
                    **element,
                    'restricted_platform':list_of_permission_restricted_platforms,
                    'rbac_permission_target':permission_targets,
                    'restricted_profil':list_of_permission_restricted_profils,
                })
            
             
            extra_data = {
                "max": 0,
                "limit": limit
            }
            self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION,
                    accept_language= self.accept_language,
                    query={
                        "filter__rbac_title_id":item_id,
                    },
                    user=user_details,
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }
            self.app_debug_print(f"\n\n\n LAST CONFIG PERMISSION LN: {len(formatted_permissions)} \n\n")
            # Get the end time
            end_time = time.time()
            end_datetime = datetime.now()

            # Calculate differences
            time_diff_seconds = end_time - start_time
            time_diff_datetime = end_datetime - start_datetime

            self.app_debug_print(f"\n\n\n\n\nCONFIG PERMISSION Finished at: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            self.app_debug_print(f"Time taken (seconds): {time_diff_seconds:.2f}")
            self.app_debug_print(f"Time taken (HH:MM:SS): {str(time_diff_datetime)}")
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data":formatted_permissions,
                        "limit":extra_data['limit'],
                        "max":extra_data['max'],
                    }
                ) 
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR CONFIG PERM 1 : {e} \n\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 CONFIG PERM : {e} \n\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))
    
    async def fetch_simplified_config_rbac_title_sub_endpoints(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ): 
        
        try:
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                user=user_details,
            )
            
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            authenticationService = AuthenticatedService()
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language) 
            
            item_id = request.query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            endpoints_pipeline = [
                # // STAGE 1: Early filtering before lookup
                {
                    "$match": {
                        "rbac_title_id": ObjectId(item_id)
                    }
                },
                
                # // STAGE 2: Efficient lookup with projection
                {
                    "$lookup": {
                    "from": f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                    "let": { "doc_id": "$_id" },
                    "pipeline": [
                        {
                        "$match": {
                            "$expr": { "$eq": ["$targeted_id", "$$doc_id"] }
                        }
                        },
                        {
                        "$project": {
                            "_id": 1,
                            "rbac_action_id": 1,
                            "targeted_id": 1,
                            "rbac_component_id": 1,
                            "rbac_permission_id": 1
                        }
                        }
                    ],
                    "as": "unwind__rbac_permission_target"
                    }
                },
                
                # // STAGE 3: Final projection with optimized field selection
                {
                    "$project": {
                    "_id": 1,
                    "label": 1,
                    # "description_str": 1,
                    "url": 1,
                    "rbac_title_id": 1,
                    "is_sudo_action": 1,
                    "is_sudo_group_action": 1,
                    # "flag": 1,
                    "unwind__rbac_permission_target": {
                        "$map": {
                        "input": "$unwind__rbac_permission_target",
                        "as": "target",
                        "in": {
                            "_id": "$$target._id",
                            "rbac_action_id": "$$target.rbac_action_id",
                            "targeted_id": "$$target.targeted_id",
                            "rbac_component_id": "$$target.rbac_component_id",
                            "rbac_permission_id": "$$target.rbac_permission_id"
                        }
                        }
                    }
                    }
                }
            ]

            
            # Get the start time
            start_time = time.time()  # in seconds since epoch
            start_datetime = datetime.now()
            endpoints = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key = CollectionKey.RBAC_ENDPOINT,
                output_data_type=output_data_type,
                all_data=True,
                page=0,
                limit=1000,
                accept_language= self.accept_language,
                pipeline=endpoints_pipeline,
            ) 
            
            self.app_debug_print(f"\n\n\n element step: 5 \n\n")
            formatted_endpoints = []
            for i,element in enumerate(endpoints):
                list_of_permission_targets = element['rbac_permission_target'];
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    endpoint_targeted_id = element['id']['display_value']
                elif output_data_type == OutputDataType.DEFAULT.value:
                    endpoint_targeted_id = element['id']
                elif output_data_type == OutputDataType.TREE.value:
                    endpoint_targeted_id = element['id']
                else :
                    endpoint_targeted_id:None 
                    
                list_of_endpoint_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=[ 
                        {
                            "$match": {
                                "targeted_id":ObjectId(str(endpoint_targeted_id)),
                            }
                        }, 
                        {
                            "$project":{
                                "_id":"$_id",
                                "targeted_id":"$targeted_id",
                                "is_hidden":"$is_hidden",
                                "is_locked":"$is_locked",
                                "is_activated":"$is_activated",
                                "rbac_profile_id":"$rbac_profile_id",
                            }
                        }
                    ],
                    all_data=True 
                )

                list_of_endpoint_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=[ 
                        {
                            "$match": {
                                "targeted_id":ObjectId(str(endpoint_targeted_id)),
                            }
                        }, 
                        {
                            "$project":{
                                "_id":"$_id",
                                "targeted_id":"$targeted_id",
                                "is_hidden":"$is_hidden",
                                "is_locked":"$is_locked",
                                "is_activated":"$is_activated",
                                "ref_api_consumer_id":"$ref_api_consumer_id",
                            }
                        }
                    ],

                    all_data=True
                ) 
                #FORMAT PERMISSION TARGET
                permission_targets = []
                for permission_target in list_of_permission_targets:
                    if output_data_type == OutputDataType.DATA_TABLE.value:
                        targeted_id = permission_target['id']['display_value']
                    elif output_data_type == OutputDataType.DEFAULT.value:
                        targeted_id = permission_target['id']
                    elif output_data_type == OutputDataType.TREE.value:
                        targeted_id = permission_target['id']
                    else :
                        targeted_id = None
                        
                    # permission_target_found = await self.generic_service.fetch_one_from_collection(
                    #     collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                    #     output_data_type=OutputDataType(output_data_type).value,
                    #     accept_language= self.accept_language,
                    #     query={
                    #         "filter___id":targeted_id,
                    #     }
                    # )
                    permission_target_found = await self.generic_service.fetch_native_aggregate_one_from_collection(
                        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language= self.accept_language,
                        pipeline=[
                            {
                                "$match": {
                                    "_id":ObjectId(str(targeted_id)),
                                }
                            }, 
                            {
                                "$project":{
                                    "_id":"$_id",
                                    "targeted_id":"$targeted_id",
                                    "rbac_action_id":"$rbac_action_id",
                                    "rbac_component_id":"$rbac_component_id",
                                    "rbac_permission_id":"$rbac_permission_id",
                                }
                            }
                        ] 
                    )
                    self.app_debug_print(f"\n\n\n\n\n\n\n\n\n permission_target_found : {permission_target_found} \n\n\n\n\n\n",False)
                    if permission_target_found: 
                        list_of_target_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                            collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                            output_data_type=output_data_type,
                            accept_language=self.accept_language,
                            pipeline=[ 
                                {
                                    "$match": {
                                        "targeted_id":ObjectId(str(targeted_id)),
                                    }
                                }, 
                                {
                                    "$project":{
                                        "_id":"$_id",
                                        "targeted_id":"$targeted_id",
                                        "is_hidden":"$is_hidden",
                                        "is_locked":"$is_locked",
                                        "is_activated":"$is_activated",
                                        "rbac_profile_id":"$rbac_profile_id",
                                    }
                                }
                            ],
                            all_data=True,
                        )

                        list_of_target_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                            collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                            output_data_type=output_data_type,
                            accept_language=self.accept_language,
                            pipeline=[ 
                                {
                                    "$match": {
                                        "targeted_id":ObjectId(str(targeted_id)),
                                    }
                                }, 
                                {
                                    "$project":{
                                        "_id":"$_id",
                                        "targeted_id":"$targeted_id",
                                        "is_hidden":"$is_hidden",
                                        "is_locked":"$is_locked",
                                        "is_activated":"$is_activated",
                                        "ref_api_consumer_id":"$ref_api_consumer_id",
                                    }
                                }
                            ],
                            all_data=True,
                        ) 
                        permission_targets.append({
                            **permission_target_found,
                            'restricted_platform':list_of_target_restricted_platforms,
                            'restricted_profil':list_of_target_restricted_profils,
                        }) 
                            
                
                formatted_endpoints.append({
                    **element,
                    'restricted_platform':list_of_endpoint_restricted_platforms,
                    'rbac_permission_target':permission_targets,
                    'restricted_profil':list_of_endpoint_restricted_profils,
                })
                 
            extra_data = {
                "max": 0,
                "limit": limit
            }
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.RBAC_ENDPOINT,
                    accept_language= self.accept_language,
                    query={
                        "filter__rbac_title_id":item_id,
                    },
                    user=user_details,
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }
            # Get the end time
            end_time = time.time()
            end_datetime = datetime.now()

            # Calculate differences
            time_diff_seconds = end_time - start_time
            time_diff_datetime = end_datetime - start_datetime

            self.app_debug_print(f"\n\n\n\n\nCONFIG ENDPOINTS Finished at: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            self.app_debug_print(f"Time taken (seconds): {time_diff_seconds:.2f}")
            self.app_debug_print(f"Time taken (HH:MM:SS): {str(time_diff_datetime)}")
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data":formatted_endpoints,
                        "limit":extra_data['limit'],
                        "max":extra_data['max'],
                    }
                ) 
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR CONFIG PERM 1 : {e} \n\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 CONFIG PERM : {e} \n\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))
        
    async def fetch_simplified_config_rbac_title_single_endpoint(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ): 
        
        try:
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                user=user_details,
            )
            
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            authenticationService = AuthenticatedService()
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language) 
            
            item_id = request.query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            endpoints_pipeline = [
                # // STAGE 1: Early filtering before lookup
                {
                    "$match": {
                        "_id": ObjectId(item_id)
                    }
                },
                
                # // STAGE 2: Efficient lookup with projection
                {
                    "$lookup": {
                    "from": f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                    "let": { "doc_id": "$_id" },
                    "pipeline": [
                        {
                        "$match": {
                            "$expr": { "$eq": ["$targeted_id", "$$doc_id"] }
                        }
                        },
                        {
                        "$project": {
                            "_id": 1,
                            "rbac_action_id": 1,
                            "targeted_id": 1,
                            "rbac_component_id": 1,
                            "rbac_permission_id": 1
                        }
                        }
                    ],
                    "as": "unwind__rbac_permission_target"
                    }
                },
                
                # // STAGE 3: Final projection with optimized field selection
                {
                    "$project": {
                    "_id": 1,
                    "label": 1,
                    # "description_str": 1,
                    "url": 1,
                    "rbac_title_id": 1,
                    "is_sudo_action": 1,
                    "is_sudo_group_action": 1,
                    # "flag": 1,
                    "unwind__rbac_permission_target": {
                        "$map": {
                        "input": "$unwind__rbac_permission_target",
                        "as": "target",
                        "in": {
                            "_id": "$$target._id",
                            "rbac_action_id": "$$target.rbac_action_id",
                            "targeted_id": "$$target.targeted_id",
                            "rbac_component_id": "$$target.rbac_component_id",
                            "rbac_permission_id": "$$target.rbac_permission_id"
                        }
                        }
                    }
                    }
                }
            ]

            
            # Get the start time
            start_time = time.time()  # in seconds since epoch
            start_datetime = datetime.now()
            endpoints = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key = CollectionKey.RBAC_ENDPOINT,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=endpoints_pipeline,
            ) 
            
            self.app_debug_print(f"\n\n\n element step: 5 \n\n")
            formatted_endpoints = []
            for i,element in enumerate(endpoints):
                list_of_permission_targets = element['rbac_permission_target'];
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    endpoint_targeted_id = element['id']['display_value']
                elif output_data_type == OutputDataType.DEFAULT.value:
                    endpoint_targeted_id = element['id']
                elif output_data_type == OutputDataType.TREE.value:
                    endpoint_targeted_id = element['id']
                else :
                    endpoint_targeted_id:None 
                    
                list_of_endpoint_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=[ 
                        {
                            "$match": {
                                "targeted_id":ObjectId(str(endpoint_targeted_id)),
                            }
                        }, 
                        {
                            "$project":{
                                "_id":"$_id",
                                "targeted_id":"$targeted_id",
                                "is_hidden":"$is_hidden",
                                "is_locked":"$is_locked",
                                "is_activated":"$is_activated",
                                "rbac_profile_id":"$rbac_profile_id",
                            }
                        }
                    ],
                    all_data=True 
                )

                list_of_endpoint_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=[ 
                        {
                            "$match": {
                                "targeted_id":ObjectId(str(endpoint_targeted_id)),
                            }
                        }, 
                        {
                            "$project":{
                                "_id":"$_id",
                                "targeted_id":"$targeted_id",
                                "is_hidden":"$is_hidden",
                                "is_locked":"$is_locked",
                                "is_activated":"$is_activated",
                                "ref_api_consumer_id":"$ref_api_consumer_id",
                            }
                        }
                    ],

                    all_data=True
                ) 
                #FORMAT PERMISSION TARGET
                permission_targets = []
                for permission_target in list_of_permission_targets:
                    if output_data_type == OutputDataType.DATA_TABLE.value:
                        targeted_id = permission_target['id']['display_value']
                    elif output_data_type == OutputDataType.DEFAULT.value:
                        targeted_id = permission_target['id']
                    elif output_data_type == OutputDataType.TREE.value:
                        targeted_id = permission_target['id']
                    else :
                        targeted_id = None
                        
                    # permission_target_found = await self.generic_service.fetch_one_from_collection(
                    #     collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                    #     output_data_type=OutputDataType(output_data_type).value,
                    #     accept_language= self.accept_language,
                    #     query={
                    #         "filter___id":targeted_id,
                    #     }
                    # )
                    permission_target_found = await self.generic_service.fetch_native_aggregate_one_from_collection(
                        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language= self.accept_language,
                        pipeline=[
                            {
                                "$match": {
                                    "_id":ObjectId(str(targeted_id)),
                                }
                            }, 
                            {
                                "$project":{
                                    "_id":"$_id",
                                    "targeted_id":"$targeted_id",
                                    "rbac_action_id":"$rbac_action_id",
                                    "rbac_component_id":"$rbac_component_id",
                                    "rbac_permission_id":"$rbac_permission_id",
                                }
                            }
                        ] 
                    )
                    self.app_debug_print(f"\n\n\n\n\n\n\n\n\n permission_target_found : {permission_target_found} \n\n\n\n\n\n",False)
                    if permission_target_found: 
                        list_of_target_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                            collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                            output_data_type=output_data_type,
                            accept_language=self.accept_language,
                            pipeline=[ 
                                {
                                    "$match": {
                                        "targeted_id":ObjectId(str(targeted_id)),
                                    }
                                }, 
                                {
                                    "$project":{
                                        "_id":"$_id",
                                        "targeted_id":"$targeted_id",
                                        "is_hidden":"$is_hidden",
                                        "is_locked":"$is_locked",
                                        "is_activated":"$is_activated",
                                        "rbac_profile_id":"$rbac_profile_id",
                                    }
                                }
                            ],
                            all_data=True,
                        )

                        list_of_target_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                            collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                            output_data_type=output_data_type,
                            accept_language=self.accept_language,
                            pipeline=[ 
                                {
                                    "$match": {
                                        "targeted_id":ObjectId(str(targeted_id)),
                                    }
                                }, 
                                {
                                    "$project":{
                                        "_id":"$_id",
                                        "targeted_id":"$targeted_id",
                                        "is_hidden":"$is_hidden",
                                        "is_locked":"$is_locked",
                                        "is_activated":"$is_activated",
                                        "ref_api_consumer_id":"$ref_api_consumer_id",
                                    }
                                }
                            ],
                            all_data=True,
                        ) 
                        permission_targets.append({
                            **permission_target_found,
                            'restricted_platform':list_of_target_restricted_platforms,
                            'restricted_profil':list_of_target_restricted_profils,
                        }) 
                            
                
                formatted_endpoints.append({
                    **element,
                    'restricted_platform':list_of_endpoint_restricted_platforms,
                    'rbac_permission_target':permission_targets,
                    'restricted_profil':list_of_endpoint_restricted_profils,
                })
                 
            extra_data = {
                "max": 0,
                "limit": limit
            }
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.RBAC_ENDPOINT,
                    accept_language= self.accept_language,
                    query={
                        "filter__rbac_title_id":item_id,
                    },
                    user=user_details,
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }
            # Get the end time
            end_time = time.time()
            end_datetime = datetime.now()

            # Calculate differences
            time_diff_seconds = end_time - start_time
            time_diff_datetime = end_datetime - start_datetime

            self.app_debug_print(f"\n\n\n\n\nCONFIG ENDPOINTS Finished at: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            self.app_debug_print(f"Time taken (seconds): {time_diff_seconds:.2f}")
            self.app_debug_print(f"Time taken (HH:MM:SS): {str(time_diff_datetime)}")
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data":formatted_endpoints,
                        "limit":extra_data['limit'],
                        "max":extra_data['max'],
                    }
                ) 
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR CONFIG PERM 1 : {e} \n\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 CONFIG PERM : {e} \n\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))
    
    async def fetch_simplified_config_rbac_titles(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ): 
        
        try:
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                user=user_details,
            )
            
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            authenticationService = AuthenticatedService()
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language) 
            
            self.app_debug_print("in permission config step 1 ")
            rbac_titles = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_TITLE,
                output_data_type=OutputDataType(output_data_type).value,
                limit=limit,
                page=page,
                accept_language= self.accept_language,
                pipeline=[
                    
                    {
                        "$match": {
                            "rbac_title_id":None,
                            "is_activated":True
                        }
                    }, 
                    {
                        "$project":{
                            "_id":1,
                            "label":1,
                            "rbac_title_id":1,
                            "description_str":1,
                        }
                    },
                    
                    {
                        "$skip":limit * page
                    },
                    {
                        "$limit":limit
                    },
                     
                ]
            )
            self.app_debug_print("in permission config step 2 ")
            if not rbac_titles:
                extra_data = {
                    "max": 0,
                    "limit": limit
                }
                if not all_data:
                    # get max
                    max_data = await self.generic_service.count_data_from_collection(
                        collection_key=CollectionKey.RBAC_TITLE,
                        accept_language= self.accept_language,
                        query={
                            "filter__rbac_title_id":None,
                            "filter__is_activated":True,
                        },
                        user=user_details,
                    )
                    extra_data = {
                        "max":max_data,
                        "limit":limit
                    }
                return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data":[],
                        "limit":extra_data['limit'],
                        "max":extra_data['max'],
                    }
                )
                # message = self.get_response_message(MessageCategory.EXCEPTIONS, "RBAC_TITLE_MISSING", self.accept_language,email=support_email)
                # self.app_debug_print(f" missing rbac_titles : {message}",)
                # raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
            
            self.app_debug_print("in permission config step 3 ")
            
            # RECURSIVE RBAC TITLE 
            async def rbac_title_recursive_children(rbac_title,parent_rbac_title_id=None):
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    rbac_title_id = rbac_title['id']['display_value'] 
                elif output_data_type == OutputDataType.DEFAULT.value:
                    rbac_title_id = rbac_title['id'] 
                else :
                    rbac_title_id = rbac_title['id']
                 
                formatted_permissions = []
                 
                self.app_debug_print(f"\n\n\n element step: 5 \n\n")
                formatted_endpoints = []
                 
                
                self.app_debug_print(f"\n\n\n element step: 6 \n\n")
                # FETCH CHILDREN FROM HERE
                children_rbac_titles = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_TITLE,
                    output_data_type=OutputDataType(output_data_type).value,
                    limit=100,#limit,
                    page=0,#page,
                    accept_language= self.accept_language,
                    pipeline=[
                        {
                            "$match": {
                                "rbac_title_id":ObjectId(str(parent_rbac_title_id)),
                                "is_activated":True
                            }
                        }, 
                        {
                            "$project":{
                                "_id":1,
                                "label":1,
                                "rbac_title_id":1,
                                "description_str":1,
                            }
                        }
                    ]
                )
                formatted_children_data = []
                self.app_debug_print(f"\n\n\n element step: 7 \n\n")
                for rbac_title_child in children_rbac_titles:
                    if output_data_type == OutputDataType.DATA_TABLE.value:
                        rbac_title_id = rbac_title_child['id']['display_value'] 
                    elif output_data_type == OutputDataType.DEFAULT.value:
                        rbac_title_id = rbac_title_child['id'] 
                    else :
                        rbac_title_id = rbac_title_child['id']
                    
                    formated_from_recursive = await rbac_title_recursive_children(rbac_title_child,rbac_title_id)
                    formatted_children_data.append(formated_from_recursive)
                return {
                    "rbac_title":rbac_title,
                    "permissions":formatted_permissions,
                    "endpoints":formatted_endpoints,
                    "children":formatted_children_data
                }
            formatted_data = [];
            # Get the start time
            start_time = time.time()  # in seconds since epoch
            start_datetime = datetime.now()
            self.app_debug_print(f"rbac_titles Starting at: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}",True)
            for index,rbac_title in enumerate(rbac_titles):
                if index == 0:
                    self.app_debug_print(f"\n\n\n rbac_title : {rbac_title} \n\n\n\n\n\n",False)
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    rbac_title_id = rbac_title['id']['display_value'] 
                elif output_data_type == OutputDataType.DEFAULT.value:
                    rbac_title_id = rbac_title['id'] 
                else :
                    rbac_title_id = rbac_title['id']
                
                formated_from_recursive = await rbac_title_recursive_children(rbac_title, parent_rbac_title_id=rbac_title_id) 
                formatted_data.append(formated_from_recursive)
                
            # Initialize extra_data unconditionally. len(
            extra_data = {
                "max": 0,
                "limit": limit
            }
            self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.RBAC_TITLE,
                    accept_language= self.accept_language,
                    query={
                        "filter__rbac_title_id":None,
                        "filter__is_activated":True,
                    },
                    user=user_details,
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }
            self.app_debug_print(f"\n\n\n LAST CONFIG PERMISSION LN: {len(formatted_data)} \n\n")
            # Get the end time
            end_time = time.time()
            end_datetime = datetime.now()

            # Calculate differences
            time_diff_seconds = end_time - start_time
            time_diff_datetime = end_datetime - start_datetime

            self.app_debug_print(f"\n\n\n\n\nCONFIG PERMISSION Finished at: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            self.app_debug_print(f"Time taken (seconds): {time_diff_seconds:.2f}",True)
            self.app_debug_print(f"Time taken (HH:MM:SS): {str(time_diff_datetime)}",True)
            return  CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "data":formatted_data,
                        "limit":extra_data['limit'],
                        "max":extra_data['max'],
                    }
                ) 
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR CONFIG PERM 1 : {e} \n\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 CONFIG PERM : {e} \n\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))

        
    async def fetch_config_path_guards(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ): 
        # DECODE USER TOKEN 
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        authenticationService = AuthenticatedService()
        
        
        rbac_path_guards = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.RBAC_PATH_GUARD,
            output_data_type=OutputDataType.DATA_TABLE.value,
            limit=limit,
            page=page,
            accept_language= self.accept_language,
            pipeline=[
                {
                    "$match": {
                        "is_activated":True
                    }
                }, 
                {
                    "$project":{
                        "_id":1,
                        "label":1,
                        "targeted_id":1,
                        "is_standalone":1,
                        "sys_menu_id":1,
                        "sys_application_id":1,
                        "path":1,
                        "path_guard":1,
                    }
                }
            ],
        )
        print(f"\n\n\n\n\n rbac_path_guards : {len(rbac_path_guards)} \n\n\n\n")
        # Initialize extra_data unconditionally.
        extra_data = {
            "max": 0,
            "limit": limit
        }
        self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")
        # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
        list_of_formated_rbac_path_guard = []
        for guard in rbac_path_guards:
            if output_data_type == OutputDataType.DATA_TABLE.value:
                guard_targeted_id = guard['id']['display_value']
            elif output_data_type == OutputDataType.DEFAULT.value:
                guard_targeted_id = guard['id']
            elif output_data_type == OutputDataType.TREE.value:
                guard_targeted_id = guard['id']
            else :
                guard_targeted_id:None
            list_of_guard_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(guard_targeted_id)),
                        }
                    }, 
                    {
                        "$project":{
                            "_id":"$_id",
                            "targeted_id":"$targeted_id",
                            "is_hidden":"$is_hidden",
                            "is_locked":"$is_locked",
                            "is_activated":"$is_activated",
                            "rbac_profile_id":"$rbac_profile_id",
                        }
                    }
                ],
                all_data=True
            )

            list_of_guard_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(guard_targeted_id)),
                        }
                    }, 
                    {
                        "$project":{
                            "_id":"$_id",
                            "targeted_id":"$targeted_id",
                            "is_hidden":"$is_hidden",
                            "is_locked":"$is_locked",
                            "is_activated":"$is_activated",
                            "ref_api_consumer_id":"$ref_api_consumer_id",
                        }
                    }
                ],
                all_data=True
            )
            guard_current_item = {
                **guard,
                'restricted_platform':list_of_guard_restricted_platforms,
                'restricted_profil':list_of_guard_restricted_profils,
            } 
            list_of_formated_rbac_path_guard.append(guard_current_item)
        if not all_data:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.RBAC_PATH_GUARD,
                accept_language= self.accept_language,
                query={},
                user=user_details,
            )
            extra_data = {
                "max":max_data,
                "limit":limit
            }
            self.app_debug_print(f"\n\n\n after extra_data : {extra_data} \n\n")
        return  CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":list_of_formated_rbac_path_guard,
                    "limit":extra_data['limit'],
                    "max":extra_data['max'],
                }
            ) 


    async def fetch_config_applications(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ): 
        # DECODE USER TOKEN 
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        saas_config_info  = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )
        if not saas_config_info:
            message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        authenticationService = AuthenticatedService()
        support_email = await  self.get_system_support_email(saas_config_info,self.accept_language) 
         
        app_pipeline = [ 
            
            # {
            #     "$sort":{
            #         "order_by":1
            #     }
            # },
            # Group by the sys_application _id and push matching documents into an array field "docs"
            {
                "$group": {
                    "_id": "$_id",
                    "docs": { "$push": "$$ROOT" }
                }
            },
            # Merge the array of documents into one object per group.
            {
                "$project": {
                    "merged": {
                        "$reduce": {
                            "input": "$docs",
                            "initialValue": {},
                            "in": { "$mergeObjects": [ "$$value", "$$this" ] }
                        }
                    }
                }
            },
            # Replace the root with the merged document so that fields are at the top level.
            {
                "$replaceRoot": { "newRoot": "$merged" }
            },
            {
                "$skip":limit * page
            },
            {
                "$limit":limit
            },
        ]
        # self.app_debug_print(f"\n\n app_pipeline :{app_pipeline}\n\n",True)
 
        applications = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key = CollectionKey.SYS_APPLICATION,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=app_pipeline,
            )
        self.app_debug_print(f" \n\n applications : {len(applications)} \n\n",True)
        
        
        formatted_data = [] 
        for index, apps in enumerate(applications):
            # if index == 0:
                # self.app_debug_print(f" \n\n application : {apps} \n\n",True)
            if output_data_type == OutputDataType.DATA_TABLE.value:
                targeted_id = apps['id']['display_value']
                # order_by =  apps['order_by']['display_value']
            elif output_data_type == OutputDataType.DEFAULT.value:
                targeted_id = apps['id']
                # order_by =  apps['order_by']
            elif output_data_type == OutputDataType.TREE.value:
                targeted_id = apps['id']
                # order_by =  index
            else :
                targeted_id:None
                # order_by =  index

            list_of_app_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=output_data_type,
                accept_language=self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(targeted_id)),
                        }
                    }, 
                    {
                        "$project":{
                            "_id":"$_id",
                            "targeted_id":"$targeted_id",
                            "is_hidden":"$is_hidden",
                            "is_locked":"$is_locked",
                            "is_activated":"$is_activated",
                            "rbac_profile_id":"$rbac_profile_id",
                        }
                    }
                ],
                all_data=True,
            )
            list_of_app_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                output_data_type=output_data_type,
                accept_language=self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(targeted_id)),
                        }
                    }, 
                    {
                        "$project":{
                            "_id":"$_id",
                            "targeted_id":"$targeted_id",
                            "is_hidden":"$is_hidden",
                            "is_locked":"$is_locked",
                            "is_activated":"$is_activated",
                            "ref_api_consumer_id":"$ref_api_consumer_id",
                        }
                    }
                ],
                all_data=True,
            ) 
            nested_icon_pipeline = [
                {
                    "$lookup": {
                        "from": "rbac_restricted_api_consumer",
                        "localField": "_id",
                        "foreignField": "targeted_id",
                        "as": "unwind__rbac_restricted_api_consumer"
                    }
                },
                {
                    "$unwind": {
                        "path": "$unwind__rbac_restricted_api_consumer",
                        "preserveNullAndEmptyArrays": True
                    }
                },
                {
                    "$match": {
                        "targeted_id": ObjectId(targeted_id),
                        "unwind__rbac_restricted_api_consumer.ref_api_consumer_id":ObjectId(api_Consumer['id']),
                    }
                },  
            ]
            
            
            # Create a cache key based on user, API consumer, profile, and pagination params
            # cache_nested_icon_key = f"nested_config_icon_{targeted_id}_{user_details['id']}_{api_Consumer['id']}_{user_profil['id']}_{output_data_type}"
            # # Cache expiration time in seconds (10 minutes)
            # cache_nested_icon_expiration = 600 * 5
            # # Try to get data from cache first
            # cached_nested_icon_data = await AppRedisService.get_str_redis_value(cache_nested_icon_key)
            nested_icon = None
            # if cached_nested_icon_data:
            #     self.app_debug_print(f"Returning cached config nested_icon data", True)
            #     cached_nested_icon_json = json.loads(cached_nested_icon_data)
            #     nested_icon = cached_nested_icon_json
            # else:
            nested_icon = await self.generic_service.fetch_native_aggregate_one_from_collection(
                collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language= self.accept_language,
                pipeline=nested_icon_pipeline
            )
            #     # Convert to serializable format and cache the result with expiration
            #     serializable_nested_icon = self.convert_to_serializable(nested_icon)
            #     await AppRedisService.set_redis_value(
            #         key=cache_nested_icon_key,
            #         value=json.dumps(serializable_nested_icon),
            #         expiry=cache_nested_icon_expiration
            #     )

            rbac_path_guard_pipeline = [ 
                {
                    "$match": {
                        "targeted_id": ObjectId(targeted_id), 
                    }
                },
                {
                    "$project":{
                        "_id": "$_id",
                        "targeted_id":1,
                        "path":1,
                        "label":1,
                        "path_guard":1,
                        "sys_menu_id":1,
                        "path_guard":1,
                        "sys_application_id":1,
                    }
                }  
            ]
            rbac_path_guard_list = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_PATH_GUARD,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language= self.accept_language,
                pipeline=rbac_path_guard_pipeline,
                all_data=True,
            )
            sub_menus = await ApplicationService.get_application_submenus_config(
                application_id=targeted_id,
                apiConsumer=api_Consumer,
                page=page,
                limit=limit,
                all_data=True,
                accept_language= self.accept_language,
                output_data_type=OutputDataType(output_data_type).value,
            );
             
            app = {
                **apps,
                'ishidden':False,
                'isactivated':True,
                'restricted_platform':list_of_app_restricted_platforms,
                'restricted_profil':list_of_app_restricted_profils,
            }
            list_of_formated_rbac_path_guard = []
            # print(f"\n\n\n rbac_path_guard_list <<< : {len(rbac_path_guard_list)} \n\n",)
            for guard in rbac_path_guard_list:
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    guard_targeted_id = guard['id']['display_value']
                elif output_data_type == OutputDataType.DEFAULT.value:
                    guard_targeted_id = guard['id']
                elif output_data_type == OutputDataType.TREE.value:
                    guard_targeted_id = guard['id']
                else :
                    # order_by = index
                    guard_targeted_id:None

                list_of_guard_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(guard_targeted_id)),
                        }
                    }, 
                    {
                        "$project":{
                            "_id":"$_id",
                            "targeted_id":"$targeted_id",
                            "is_hidden":"$is_hidden",
                            "is_locked":"$is_locked",
                            "is_activated":"$is_activated",
                            "rbac_profile_id":"$rbac_profile_id",
                        }
                    }
                ], 
                    all_data=True,
                )

                list_of_guard_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=[ 
                        {
                            "$match": {
                                "targeted_id":ObjectId(str(guard_targeted_id)),
                            }
                        }, 
                        {
                            "$project":{
                                "_id":"$_id",
                                "targeted_id":"$targeted_id",
                                "is_hidden":"$is_hidden",
                                "is_locked":"$is_locked",
                                "is_activated":"$is_activated",
                                "ref_api_consumer_id":"$ref_api_consumer_id",
                            }
                        }
                    ], 
                    all_data=True,
                )
                single_item  = {
                    **guard,
                    'restricted_platform':list_of_guard_restricted_platforms,
                    'restricted_profil':list_of_guard_restricted_profils,
                }
                # print(f"\n\n\n single_item <<<>>> : {single_item} \n\n",)
                list_of_formated_rbac_path_guard.append(single_item)
            current_item = {
                **app,
                'order_by':0,#order_by,
                'rbac_path_guard':list_of_formated_rbac_path_guard,
                "sub_menus":[*sub_menus]
            }
            formatted_data.append({
                **current_item,
            })
            if nested_icon:
                icon_payload = ApplicationService._build_svg_icon_payload(
                    menu_or_app_data=app,
                    rbac_path_guard=list_of_formated_rbac_path_guard,
                    api_consumer_flag=api_Consumer.get('flag'),
                )
                if icon_payload:
                    index_of_menu = formatted_data.index(current_item)
                    formatted_data[index_of_menu] = {
                        **formatted_data[index_of_menu],
                        **icon_payload,
                    }
                    self.app_debug_print(f"\n\n index_of_app: {index_of_menu}\n\n",False)

            
            # Now, sort formatted_data by 'order_by' ascending:
            # formatted_data.sort(key=lambda item: item['order_by'])
        # Initialize extra_data unconditionally.
        extra_data = {
            "max": 0,
            "limit": limit  # Ensure that 'limit' is defined prior to this.
        }
        self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")

        if not all_data:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.SYS_APPLICATION,
                accept_language= self.accept_language,
                query={},
                user=user_details,
            )
            # Update keys in the existing dictionary.
            extra_data["max"] = max_data
            extra_data["limit"] = limit  # If needed.
            self.app_debug_print(f"\n\n\n after extra_data : {extra_data} \n\n",True)

        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": formatted_data,
                "limit": extra_data["limit"],
                "max": extra_data["max"],
            }
        )
        
    async def fetch_simplified_config_applications(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ): 
        # DECODE USER TOKEN 
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        saas_config_info  = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )
        if not saas_config_info:
            message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        authenticationService = AuthenticatedService()
        support_email = await  self.get_system_support_email(saas_config_info,self.accept_language) 
         
        app_pipeline = [ 
            
            # {
            #     "$sort":{
            #         "order_by":1
            #     }
            # },
            # Group by the sys_application _id and push matching documents into an array field "docs"
            {
                "$group": {
                    "_id": "$_id",
                    "docs": { "$push": "$$ROOT" }
                }
            },
            # Merge the array of documents into one object per group.
            {
                "$project": {
                    "merged": {
                        "$reduce": {
                            "input": "$docs",
                            "initialValue": {},
                            "in": { "$mergeObjects": [ "$$value", "$$this" ] }
                        }
                    }
                }
            },
            # Replace the root with the merged document so that fields are at the top level.
            {
                "$replaceRoot": { "newRoot": "$merged" }
            },
            {
                "$skip":limit * page
            },
            {
                "$limit":limit
            },
        ]
        # self.app_debug_print(f"\n\n app_pipeline :{app_pipeline}\n\n",True)
 
        applications = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key = CollectionKey.SYS_APPLICATION,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                pipeline=app_pipeline,
            )
        self.app_debug_print(f" \n\n applications : {len(applications)} \n\n",True)
        
        
        formatted_data = [] 
        for index, apps in enumerate(applications):
            # if index == 0:
                # self.app_debug_print(f" \n\n application : {apps} \n\n",True)
            if output_data_type == OutputDataType.DATA_TABLE.value:
                targeted_id = apps['id']['display_value']
                # order_by =  apps['order_by']['display_value']
            elif output_data_type == OutputDataType.DEFAULT.value:
                targeted_id = apps['id']
                # order_by =  apps['order_by']
            elif output_data_type == OutputDataType.TREE.value:
                targeted_id = apps['id']
                # order_by =  index
            else :
                targeted_id:None
                # order_by =  index

            list_of_app_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=output_data_type,
                accept_language=self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(targeted_id)),
                        }
                    }, 
                    {
                        "$project":{
                            "_id":"$_id",
                            "targeted_id":"$targeted_id",
                            "is_hidden":"$is_hidden",
                            "is_locked":"$is_locked",
                            "is_activated":"$is_activated",
                            "rbac_profile_id":"$rbac_profile_id",
                        }
                    }
                ],
                all_data=True,
            )
            list_of_app_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                output_data_type=output_data_type,
                accept_language=self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(targeted_id)),
                        }
                    }, 
                    {
                        "$project":{
                            "_id":"$_id",
                            "targeted_id":"$targeted_id",
                            "is_hidden":"$is_hidden",
                            "is_locked":"$is_locked",
                            "is_activated":"$is_activated",
                            "ref_api_consumer_id":"$ref_api_consumer_id",
                        }
                    }
                ],
                all_data=True,
            ) 
            nested_icon_pipeline = [
                {
                    "$lookup": {
                        "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                        "localField": "_id",
                        "foreignField": "targeted_id",
                        "as": "unwind__rbac_restricted_api_consumer"
                    }
                },
                {
                    "$unwind": {
                        "path": "$unwind__rbac_restricted_api_consumer",
                        "preserveNullAndEmptyArrays": True
                    }
                },
                {
                    "$match": {
                        "targeted_id": ObjectId(targeted_id),
                        "unwind__rbac_restricted_api_consumer.ref_api_consumer_id":ObjectId(api_Consumer['id']),
                    }
                },  
            ]
             
            nested_icon = await self.generic_service.fetch_native_aggregate_one_from_collection(
                collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language= self.accept_language,
                pipeline=nested_icon_pipeline
            ) 
            rbac_path_guard_pipeline = [ 
                {
                    "$match": {
                        "targeted_id": ObjectId(targeted_id), 
                    }
                },
                {
                    "$project":{
                        "_id": "$_id",
                        "targeted_id":1,
                        "path":1,
                        "label":1,
                        "path_guard":1,
                        "sys_menu_id":1,
                        "path_guard":1,
                        "sys_application_id":1,
                    }
                }  
            ]
            rbac_path_guard_list = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_PATH_GUARD,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language= self.accept_language,
                pipeline=rbac_path_guard_pipeline,
                all_data=True,
            )
            sub_menus = []
            # await ApplicationService.get_application_submenus_config(
            #     application_id=targeted_id,
            #     apiConsumer=api_Consumer,
            #     page=page,
            #     limit=limit,
            #     all_data=True,
            #     accept_language= self.accept_language,
            #     output_data_type=OutputDataType(output_data_type).value,
            # );
             
            app = {
                **apps,
                'ishidden':False,
                'isactivated':True,
                'restricted_platform':list_of_app_restricted_platforms,
                'restricted_profil':list_of_app_restricted_profils,
            }
            list_of_formated_rbac_path_guard = []
            # print(f"\n\n\n rbac_path_guard_list <<< : {len(rbac_path_guard_list)} \n\n",)
            for guard in rbac_path_guard_list:
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    guard_targeted_id = guard['id']['display_value']
                elif output_data_type == OutputDataType.DEFAULT.value:
                    guard_targeted_id = guard['id']
                elif output_data_type == OutputDataType.TREE.value:
                    guard_targeted_id = guard['id']
                else :
                    # order_by = index
                    guard_targeted_id:None

                list_of_guard_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(guard_targeted_id)),
                        }
                    }, 
                    {
                        "$project":{
                            "_id":"$_id",
                            "targeted_id":"$targeted_id",
                            "is_hidden":"$is_hidden",
                            "is_locked":"$is_locked",
                            "is_activated":"$is_activated",
                            "rbac_profile_id":"$rbac_profile_id",
                        }
                    }
                ], 
                    all_data=True,
                )

                list_of_guard_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=[ 
                        {
                            "$match": {
                                "targeted_id":ObjectId(str(guard_targeted_id)),
                            }
                        }, 
                        {
                            "$project":{
                                "_id":"$_id",
                                "targeted_id":"$targeted_id",
                                "is_hidden":"$is_hidden",
                                "is_locked":"$is_locked",
                                "is_activated":"$is_activated",
                                "ref_api_consumer_id":"$ref_api_consumer_id",
                            }
                        }
                    ], 
                    all_data=True,
                )
                single_item  = {
                    **guard,
                    'restricted_platform':list_of_guard_restricted_platforms,
                    'restricted_profil':list_of_guard_restricted_profils,
                }
                # print(f"\n\n\n single_item <<<>>> : {single_item} \n\n",)
                list_of_formated_rbac_path_guard.append(single_item)
            current_item = {
                **app,
                'order_by':0,#order_by,
                'rbac_path_guard':list_of_formated_rbac_path_guard,
                "sub_menus":[*sub_menus]
            }
            formatted_data.append({
                **current_item,
            })
            if nested_icon:
                icon_payload = ApplicationService._build_svg_icon_payload(
                    menu_or_app_data=app,
                    rbac_path_guard=list_of_formated_rbac_path_guard,
                    api_consumer_flag=api_Consumer.get('flag'),
                )
                if icon_payload:
                    index_of_menu = formatted_data.index(current_item)
                    formatted_data[index_of_menu] = {
                        **formatted_data[index_of_menu],
                        **icon_payload,
                    }
                    self.app_debug_print(f"\n\n index_of_app: {index_of_menu}\n\n",False)

            
            # Now, sort formatted_data by 'order_by' ascending:
            # formatted_data.sort(key=lambda item: item['order_by'])
        # Initialize extra_data unconditionally.
        extra_data = {
            "max": 0,
            "limit": limit  # Ensure that 'limit' is defined prior to this.
        }
        self.app_debug_print(f"\n\n\n before extra_data : {extra_data} \n\n")

        if not all_data:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.SYS_APPLICATION,
                accept_language= self.accept_language,
                query={},
                user=user_details,
            )
            # Update keys in the existing dictionary.
            extra_data["max"] = max_data
            extra_data["limit"] = limit  # If needed.
            self.app_debug_print(f"\n\n\n after extra_data : {extra_data} \n\n",True)

        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": formatted_data,
                "limit": extra_data["limit"],
                "max": extra_data["max"],
            }
        )
        
    
    async def fetch_simplified_config_application_menus(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ): 
        # DECODE USER TOKEN 
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        saas_config_info  = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )
        if not saas_config_info:
            message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        authenticationService = AuthenticatedService()
        support_email = await  self.get_system_support_email(saas_config_info,self.accept_language) 
         
        item_id = request.query_params.get('item_id',None)
        if not item_id:
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
            raise HTTPException(status_code=400, detail=message)
        sub_menus = await ApplicationService.get_application_submenus_config(
            application_id=item_id,
            apiConsumer=api_Consumer,
            page=page,
            limit=limit,
            all_data=True,
            accept_language= self.accept_language,
            output_data_type=OutputDataType(output_data_type).value,
        );
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": sub_menus,
            }
        )
        
    
    async def fetch_config_single_application(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ): 
        # DECODE USER TOKEN 
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        saas_config_info  = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )
        if not saas_config_info:
            message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        authenticationService = AuthenticatedService()
        support_email = await  self.get_system_support_email(saas_config_info,self.accept_language) 
        item_id = request.query_params.get('item_id',None)
        if not item_id:
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
            raise HTTPException(status_code=400, detail=message)
        app_pipeline = [ 
            
            # {
            #     "$sort":{
            #         "order_by":1
            #     }
            # },
            # Group by the sys_application _id and push matching documents into an array field "docs"
            {
                "$group": {
                    "_id": "$_id",
                    "docs": { "$push": "$$ROOT" }
                }
            },
            # Merge the array of documents into one object per group.
            {
                "$project": {
                    "merged": {
                        "$reduce": {
                            "input": "$docs",
                            "initialValue": {},
                            "in": { "$mergeObjects": [ "$$value", "$$this" ] }
                        }
                    }
                }
            },
            # Replace the root with the merged document so that fields are at the top level.
            {
                "$replaceRoot": { "newRoot": "$merged" }
            },
            {
                "$skip":limit * page
            },
            {
                "$limit":limit
            },
        ]
        # self.app_debug_print(f"\n\n app_pipeline :{app_pipeline}\n\n",True)
 
        single_application = await self.generic_service.fetch_one_from_collection(
                collection_key = CollectionKey.SYS_APPLICATION,
                output_data_type=output_data_type,
                accept_language= self.accept_language,
                query={
                    "filter___id":item_id
                },
            user=user_details,
            )
        
        if not single_application:
            message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
            raise HTTPException(status_code=404, detail=message)
        
        formatted_data = [] 
        apps = single_application
        # if index == 0:
            # self.app_debug_print(f" \n\n application : {apps} \n\n",True)
        if output_data_type == OutputDataType.DATA_TABLE.value:
            targeted_id = apps['id']['display_value']
            # order_by =  apps['order_by']['display_value']
        elif output_data_type == OutputDataType.DEFAULT.value:
            targeted_id = apps['id']
            # order_by =  apps['order_by']
        elif output_data_type == OutputDataType.TREE.value:
            targeted_id = apps['id']
            # order_by =  index
        else :
            targeted_id:None
            # order_by =  index

        list_of_app_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
            output_data_type=output_data_type,
            accept_language=self.accept_language,
            pipeline=[ 
                {
                    "$match": {
                        "targeted_id":ObjectId(str(targeted_id)),
                    }
                }, 
                {
                    "$project":{
                        "_id":"$_id",
                        "targeted_id":"$targeted_id",
                        "is_hidden":"$is_hidden",
                        "is_locked":"$is_locked",
                        "is_activated":"$is_activated",
                        "rbac_profile_id":"$rbac_profile_id",
                    }
                }
            ],
            all_data=True,
        )
        list_of_app_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
            output_data_type=output_data_type,
            accept_language=self.accept_language,
            pipeline=[ 
                {
                    "$match": {
                        "targeted_id":ObjectId(str(targeted_id)),
                    }
                }, 
                {
                    "$project":{
                        "_id":"$_id",
                        "targeted_id":"$targeted_id",
                        "is_hidden":"$is_hidden",
                        "is_locked":"$is_locked",
                        "is_activated":"$is_activated",
                        "ref_api_consumer_id":"$ref_api_consumer_id",
                    }
                }
            ],
            all_data=True,
        ) 
        nested_icon_pipeline = [
            {
                "$lookup": {
                    "from": "rbac_restricted_api_consumer",
                    "localField": "_id",
                    "foreignField": "targeted_id",
                    "as": "unwind__rbac_restricted_api_consumer"
                }
            },
            {
                "$unwind": {
                    "path": "$unwind__rbac_restricted_api_consumer",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$match": {
                    "targeted_id": ObjectId(targeted_id),
                    "unwind__rbac_restricted_api_consumer.ref_api_consumer_id":ObjectId(api_Consumer['id']),
                }
            },  
        ]
        
            
        nested_icon = await self.generic_service.fetch_native_aggregate_one_from_collection(
            collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
            output_data_type=OutputDataType(output_data_type).value,
            accept_language= self.accept_language,
            pipeline=nested_icon_pipeline
        ) 
        rbac_path_guard_pipeline = [ 
            {
                "$match": {
                    "targeted_id": ObjectId(targeted_id), 
                }
            },
            {
                "$project":{
                    "_id": "$_id",
                    "targeted_id":1,
                    "path":1,
                    "label":1,
                    "path_guard":1,
                    "sys_menu_id":1,
                    "path_guard":1,
                    "sys_application_id":1,
                }
            }  
        ]
        rbac_path_guard_list = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.RBAC_PATH_GUARD,
            output_data_type=OutputDataType(output_data_type).value,
            accept_language= self.accept_language,
            pipeline=rbac_path_guard_pipeline,
            all_data=True,
        )
        sub_menus = []
        # sub_menus = await ApplicationService.get_application_submenus_config(
        #     application_id=targeted_id,
        #     apiConsumer=api_Consumer,
        #     page=page,
        #     limit=limit,
        #     all_data=True,
        #     accept_language= self.accept_language,
        #     output_data_type=OutputDataType(output_data_type).value,
        # );
            
        app = {
            **apps,
            'ishidden':False,
            'isactivated':True,
            'restricted_platform':list_of_app_restricted_platforms,
            'restricted_profil':list_of_app_restricted_profils,
        }
        list_of_formated_rbac_path_guard = []
        # print(f"\n\n\n rbac_path_guard_list <<< : {len(rbac_path_guard_list)} \n\n",)
        for guard in rbac_path_guard_list:
            if output_data_type == OutputDataType.DATA_TABLE.value:
                guard_targeted_id = guard['id']['display_value']
            elif output_data_type == OutputDataType.DEFAULT.value:
                guard_targeted_id = guard['id']
            elif output_data_type == OutputDataType.TREE.value:
                guard_targeted_id = guard['id']
            else :
                # order_by = index
                guard_targeted_id:None

            list_of_guard_restricted_profils = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=output_data_type,
                accept_language=self.accept_language,
                pipeline=[ 
                {
                    "$match": {
                        "targeted_id":ObjectId(str(guard_targeted_id)),
                    }
                }, 
                {
                    "$project":{
                        "_id":"$_id",
                        "targeted_id":"$targeted_id",
                        "is_hidden":"$is_hidden",
                        "is_locked":"$is_locked",
                        "is_activated":"$is_activated",
                        "rbac_profile_id":"$rbac_profile_id",
                    }
                }
            ], 
                all_data=True,
            )

            list_of_guard_restricted_platforms = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                output_data_type=output_data_type,
                accept_language=self.accept_language,
                pipeline=[ 
                    {
                        "$match": {
                            "targeted_id":ObjectId(str(guard_targeted_id)),
                        }
                    }, 
                    {
                        "$project":{
                            "_id":"$_id",
                            "targeted_id":"$targeted_id",
                            "is_hidden":"$is_hidden",
                            "is_locked":"$is_locked",
                            "is_activated":"$is_activated",
                            "ref_api_consumer_id":"$ref_api_consumer_id",
                        }
                    }
                ], 
                all_data=True,
            )
            single_item  = {
                **guard,
                'restricted_platform':list_of_guard_restricted_platforms,
                'restricted_profil':list_of_guard_restricted_profils,
            }
            # print(f"\n\n\n single_item <<<>>> : {single_item} \n\n",)
            list_of_formated_rbac_path_guard.append(single_item)
        current_item = {
            **app,
            'order_by':0,#order_by,
            'rbac_path_guard':list_of_formated_rbac_path_guard,
            "sub_menus":[*sub_menus]
        }
        formatted_data.append({
            **current_item,
        })
        if nested_icon:
            icon_payload = ApplicationService._build_svg_icon_payload(
                menu_or_app_data=app,
                rbac_path_guard=list_of_formated_rbac_path_guard,
                api_consumer_flag=api_Consumer.get('flag'),
            )
            if icon_payload:
                index_of_menu = formatted_data.index(current_item)
                formatted_data[index_of_menu] = {
                    **formatted_data[index_of_menu],
                    **icon_payload,
                }
                self.app_debug_print(f"\n\n index_of_app: {index_of_menu}\n\n",False)

             
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": formatted_data,
            }
        )
        
    
    async def fetch_config_sub_menus(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
        print(f"Accept-Language from header: {accept_language}")
        
        # DECODE USER TOKEN 
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        
        raw_query_params: Dict[str, str] = dict(request.query_params)
        sys_application_id = raw_query_params['sys_application_id']
        sub_menus_all = await ApplicationService.get_application_submenus_config(
            application_id=sys_application_id,
            apiConsumer=api_Consumer,
            page=page,
            limit=limit,
            all_data=all_data,
            accept_language= self.accept_language,
            output_data_type=OutputDataType(output_data_type).value,
        );
        
        # Initialize extra_data unconditionally.
        extra_data = {
            "max": 0,
            "limit": limit
        }
        
        # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
        if not all_data:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.SYS_MENU,
                accept_language= self.accept_language,
                query={
                    "filter__sys_application_id": ObjectId(sys_application_id),
                },
                user=user_details,
            )
            extra_data = {
                "max":max_data,
                "limit":limit
            }
        return  CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":sub_menus_all,
                    **extra_data
                }
            ) 
    
    
    async def fetch_standalone_menu_for_configs(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(200, description="Number of items per page")
    ):
        accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
        print(f"Accept-Language from header: {accept_language}")
        
        # DECODE USER TOKEN 
        user_details = await self.get_user_info(request,self.accept_language)
        api_Consumer = await self.get_api_consumer(request,self.accept_language)
        user_profil = await self.get_user_profil(request,self.accept_language)
        
        
        raw_query_params: Dict[str, str] = dict(request.query_params)
        sub_menus_all = await ApplicationService.get_config_standalone_menus(
            apiConsumer=api_Consumer,
            page=page,
            limit=limit,
            all_data=True,
            accept_language= self.accept_language,
            output_data_type=OutputDataType(output_data_type).value,
        );
        
        # Initialize extra_data unconditionally.
        extra_data = {
            "max": 0,
            "limit": limit
        }
        
        # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
        if not all_data:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.SYS_MENU,
                accept_language= self.accept_language,
                query={
                    "filter__is_standalone": True,
                },
                user=user_details,
            )
            extra_data = {
                "max":max_data,
                "limit":limit
            }
        return  CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":sub_menus_all,
                    **extra_data
                }
            ) 
    
    
    async def update_apiconsumer_data(
        self,
        request: Request,
        collection_name: str, 
        datas: Dict[str, Any]):
        """
        Endpoint to update a document in the specified collection.
        """
        try:
            print(f'\n\n\n {datas} \n\n')
            accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
            self.app_debug_print(f"Accept-Language from header: {accept_language}",False)
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # Check if collection is exposed
            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
            if not metadata:
                raise HTTPException(status_code=400, detail="Invalid collection name")
            
            query = datas.get('query',{})
            data_to_save = datas.get('data',{})

            targeted_id = data_to_save.get('targeted_id',None)
            ref_api_consumer_id = data_to_save['ref_api_consumer_id']
            is_activated = data_to_save.get('is_activated',False)

            api_consumer_doc = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_API_CONSUMER,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                query={
                    "filter___id":ref_api_consumer_id,
                },
                user=user_details,
            )
            if not api_consumer_doc:
                message = self.get_response_message(MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            new_data = {
                "ref_api_consumer_id":ref_api_consumer_id,
                "targeted_id":targeted_id,
            } 
            restricted_profil_doc = await self.generic_service.fetch_native_query_one_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                native_query=query
            ) 
            print(f"\n\n\n NO DATA TO SAVE PROFIL :")
            if not restricted_profil_doc:
                if is_activated == False:
                    message = self.get_response_message(MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                    raise HTTPException(status_code=404, detail=message)
                
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                    filter_data={"targeted_id":new_data['targeted_id'],'ref_api_consumer_id':new_data['ref_api_consumer_id']},
                    update_data=new_data,
                    user=user_details, request=request,
                )

                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message":message,
                    }
                )
            
            if is_activated == False:
                # Soft delete the document
                success = await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_RESTRICTED_API_CONSUMER, restricted_profil_doc['id'])
                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
                if success:
                    return CustomJSONResponse(
                        status_code=status.HTTP_200_OK,
                        content={
                            "status_code": status.HTTP_200_OK,
                            "message": message,
                        }
                    )
            
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                filter_data={"targeted_id":new_data['targeted_id'],'ref_api_consumer_id':new_data['ref_api_consumer_id']},
                update_data=new_data,
                user=user_details, request=request,
            )

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message":message,
                }
            )
         
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR 1 : {e} \n\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 : {e} \n\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))
    
    async def update_apiconsumer_target_data(
        self,
        request: Request,
        collection_name: str, 
        datas: Dict[str, Any]):
        """
        Endpoint to update a document in the specified collection.
        """
        try:
            print(f'\n\n\n {datas} \n\n')
            accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
            self.app_debug_print(f"Accept-Language from header: {accept_language}",False)
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # Check if collection is exposed
            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
            if not metadata:
                raise HTTPException(status_code=400, detail="Invalid collection name")
            
            {'data': {
                'is_activated': True, 
                'ref_api_consumer_id': '681443627121cc71c37e7b59'}, 
            'query': {'targeted_id': '6814439bea8b6de2e2936f9a', 'rbac_permission_id': '681443226b2b02414566941e'}} 
            query = datas.get('query',{})
            data_to_save = datas.get('data',{})

            ref_api_consumer_id = data_to_save['ref_api_consumer_id']
            is_activated = data_to_save.get('is_activated',False)

            api_consumer_doc = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_API_CONSUMER,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                query={
                    "filter___id":ref_api_consumer_id,
                },
                user=user_details,
            )
            if not api_consumer_doc:
                message = self.get_response_message(MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            
            api_consumer_target = await self.generic_service.fetch_native_query_one_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                native_query=query
            ) 
            if not api_consumer_target:
                message = self.get_response_message(MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            new_data = {
                "ref_api_consumer_id":ref_api_consumer_id,
                "targeted_id":api_consumer_target['id'],
            } 
            restricted_api_consumer_doc = await self.generic_service.fetch_native_query_one_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                native_query=new_data
            ) 
            print(f"\n\n\n NO DATA TO SAVE PROFIL :")
            if not restricted_api_consumer_doc:
                if is_activated == False:
                    message = self.get_response_message(MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                    raise HTTPException(status_code=404, detail=message)
                
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                    filter_data={"targeted_id":new_data['targeted_id'],'ref_api_consumer_id':new_data['ref_api_consumer_id']},
                    update_data=new_data,
                    user=user_details, request=request,
                )

                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message":message,
                    }
                )
            
            if is_activated == False:
                # Soft delete the document
                success = await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_RESTRICTED_API_CONSUMER, restricted_api_consumer_doc['id'])
                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
                if success:
                    return CustomJSONResponse(
                        status_code=status.HTTP_200_OK,
                        content={
                            "status_code": status.HTTP_200_OK,
                            "message": message,
                        }
                    )
            
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                filter_data={"targeted_id":new_data['targeted_id'],'ref_api_consumer_id':new_data['ref_api_consumer_id']},
                update_data=new_data,
                user=user_details, request=request,
            )

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message":message,
                }
            )
         
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR 1 : {e} \n\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 : {e} \n\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))

    async def update_sysprofil_data(
        self,
        request: Request,
        collection_name: str, 
        datas: Dict[str, Any]):
        """
        Endpoint to update a document in the specified collection.
        """
        try:
            accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
            self.app_debug_print(f"Accept-Language from header: {accept_language}",False)
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # Convert string to CollectionKey .get
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # Check if collection is exposed
            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
            if not metadata:
                raise HTTPException(status_code=400, detail="Invalid collection name")
            
            
            query = datas.get('query',{})
            data_to_save = datas.get('data',{})
            
            print(f"\n\n\n QUERY PROFIL : {query}")
            print(f"\n\n\n DATA TO SAVE PROFIL : {data_to_save}")
            rbac_profile_id = data_to_save['rbac_profile_id']
            targeted_id = data_to_save['targeted_id']
            is_activated = data_to_save.get('is_activated',False)

            sysprofil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                query={
                    "filter___id":rbac_profile_id,
                },
                user=user_details,
            )
            if not sysprofil:
                message = self.get_response_message(MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            new_data = {
                "rbac_profile_id":rbac_profile_id,
                "targeted_id":targeted_id,
            } 
            restricted_profil_doc = await self.generic_service.fetch_native_query_one_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                native_query=query
            ) 
            print(f"\n\n\n NO DATA TO SAVE PROFIL :")
            if not restricted_profil_doc:
                if is_activated == False:
                    message = self.get_response_message(MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                    raise HTTPException(status_code=404, detail=message)
                
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    filter_data={"targeted_id":new_data['targeted_id'],'rbac_profile_id':new_data['rbac_profile_id']},
                    update_data=new_data,
                    user=user_details, request=request,
                )

                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message":message,
                    }
                )
            
            if is_activated == False:
                # Soft delete the document
                success = await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_RESTRICTED_PROFIL, restricted_profil_doc['id'])
                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
                if success:
                    return CustomJSONResponse(
                        status_code=status.HTTP_200_OK,
                        content={
                            "status_code": status.HTTP_200_OK,
                            "message": message,
                        }
                    )
            
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                filter_data={"targeted_id":new_data['targeted_id'],'rbac_profile_id':new_data['rbac_profile_id']},
                update_data=new_data,
                user=user_details, request=request,
            )

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message":message,
                }
            ) 
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR 1 : {e} \n\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 : {e} \n\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))
        
        
    async def update_sysprofil_target_data(
        self,
        request: Request,
        collection_name: str, 
        datas: Dict[str, Any]):
        """
        Endpoint to update a document in the specified collection.
        """
        try:
            accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
            self.app_debug_print(f"Accept-Language from header: {accept_language}",False)
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # Convert string to CollectionKey .get
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # Check if collection is exposed
            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
            if not metadata:
                raise HTTPException(status_code=400, detail="Invalid collection name")
            
            
            query = datas.get('query',{})
            data_to_save = datas.get('data',{})
            
            print(f"\n\n\n QUERY PROFIL : {query}")
            print(f"\n\n\n DATA TO SAVE PROFIL : {data_to_save}")
            rbac_profile_id = data_to_save['rbac_profile_id']
            is_activated = data_to_save.get('is_activated',False)

            sysprofil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                query={
                    "filter___id":rbac_profile_id,
                },
                user=user_details,
            )
            if not sysprofil:
                message = self.get_response_message(MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            
            profil_target = await self.generic_service.fetch_native_query_one_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                native_query=query
            ) 

            if not profil_target:
                if is_activated == False:
                    message = self.get_response_message(MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                    raise HTTPException(status_code=404, detail=message)


            new_data = {
                "rbac_profile_id":rbac_profile_id,
                "targeted_id":profil_target['id'],
            }   
            restricted_profil_doc = await self.generic_service.fetch_native_query_one_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                native_query=new_data
            ) 
            print(f"\n\n\n NO DATA TO SAVE PROFIL :")
            if not restricted_profil_doc:
                if is_activated == False:
                    message = self.get_response_message(MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                    raise HTTPException(status_code=404, detail=message)
                
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    filter_data={"targeted_id":new_data['targeted_id'],'rbac_profile_id':new_data['rbac_profile_id']},
                    update_data=new_data,
                    user=user_details, request=request,
                )

                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message":message,
                    }
                )
            
            if is_activated == False:
                # Soft delete the document
                success = await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_RESTRICTED_PROFIL, restricted_profil_doc['id'])
                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
                if success:
                    return CustomJSONResponse(
                        status_code=status.HTTP_200_OK,
                        content={
                            "status_code": status.HTTP_200_OK,
                            "message": message,
                        }
                    )
            
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                filter_data={"targeted_id":new_data['targeted_id'],'rbac_profile_id':new_data['rbac_profile_id']},
                update_data=new_data,
                user=user_details, request=request,
            )

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message":message,
                }
            ) 
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR 1 : {e} \n\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 : {e} \n\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))

    async def update_targeted_data(
        self,
        request: Request,
        collection_name: str, 
        datas: Dict[str, Any]):
        """
        Endpoint to update a document in the specified collection.
        """
        try:
            accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
            self.app_debug_print(f"Accept-Language from header: {accept_language}",False)
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # Convert string to CollectionKey .get
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # Check if collection is exposed
            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
            if not metadata:
                raise HTTPException(status_code=400, detail="Invalid collection name")
            
            
            query = datas.get('query',{})
            data_to_save = datas.get('data',{})
            print(f"\n\n\n QUERY TARGETED : {query}")
            print(f"\n\n\n DATA TO SAVE TARGETED : {data_to_save}")
            targeted_id = data_to_save.get('targeted_id',None)
            is_activated = data_to_save.get('is_activated',False) 
            itemToUpdate = await self.generic_service.fetch_native_query_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                native_query=query
            ) 
            if not itemToUpdate or not targeted_id:
                message = self.get_response_message(MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            data_update = {
                "targeted_id": targeted_id if is_activated == True else None,
            }
            result = await self.generic_service.update_data_in_collection(collection_key=collection_key, item_id=itemToUpdate['id'], data=data_update)
            if result:
                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message":message,
                    }
                )
            else:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "DATA_UPDATED_FAILS", self.accept_language)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) 
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR 1 : {e} \n\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 : {e} \n\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))

    async def update_permission_target_data(
        self,
        request: Request,
        collection_name: str, 
        datas: Dict[str, Any]):
        """
        Endpoint to update a document in the specified collection.
        """
        try:
            accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
            self.app_debug_print(f"Accept-Language from header: {accept_language}",False)
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # Check if collection is exposed
            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
            if not metadata:
                raise HTTPException(status_code=400, detail="Invalid collection name")
            
            query = datas.get('query',{})
            data_to_save = datas.get('data',{})
            print(f'\n\n data_to_save : {data_to_save}')
            print(f'\n\n query : {query}')
            
            rbac_permission_id = data_to_save.get('rbac_permission_id',None)
            rbac_action_id = data_to_save.get('rbac_action_id',None)
            rbac_component_id = data_to_save.get('rbac_component_id',None)
            targeted_id = data_to_save.get('targeted_id',None)
            is_activated = data_to_save.get('is_activated',False)
             
            permission = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                query={
                    "filter___id":rbac_permission_id,
                },
                user=user_details,
            )
            if not permission:
                message = self.get_response_message(MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            
            permission_target = await self.generic_service.fetch_native_query_one_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                native_query=query
            )
            
            if not permission_target:
                new_permission_target_doc = { 
                    "targeted_id":targeted_id,
                    "rbac_permission_id":rbac_permission_id,  
                    "rbac_action_id":rbac_action_id,  
                    "rbac_component_id":rbac_component_id,  
                }
                saved = await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                    filter_data={
                        "targeted_id":new_permission_target_doc['targeted_id'],
                        'rbac_permission_id':new_permission_target_doc['rbac_permission_id'],
                        'rbac_action_id':rbac_action_id,  
                        'rbac_component_id':rbac_component_id,  
                    },
                    user=user_details, request=request,
                    update_data=new_permission_target_doc)
                print(f'\n\n saved permissin target : {saved}\n\n')
            # UPDATE ONLY ACTIVATED PROPERTY
            new_permission_target_doc = { 
                "targeted_id":targeted_id,
                "rbac_permission_id":rbac_permission_id, 
                'rbac_action_id':rbac_action_id,  
                'rbac_component_id':rbac_component_id,
                'is_activated':is_activated,  
            }
            saved = await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                    filter_data=query, 
                user=user_details, request=request,
                    update_data=new_permission_target_doc)
            
            self.app_debug_print(f'\n\n updated permissin target : {saved}\n\n')
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message":message,
                }
            )
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR 1 : {e} \n\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 : {e} \n\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))

    async def update_permission_role_data(
        self,
        request: Request,
        collection_name: str, 
        datas: Dict[str, Any]):
        """
        Endpoint to update a document in the specified collection.
        """
        try:
            accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
            self.app_debug_print(f"Accept-Language from header: {accept_language}",False)
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # Check if collection is exposed
            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
            if not metadata:
                raise HTTPException(status_code=400, detail="Invalid collection name")
            query = datas.get('query',{})
            data_to_save = datas.get('data',{})
            self.app_debug_print(f'\n\n\n data_to_save : {data_to_save}\n\n\n')
            self.app_debug_print(f'\n\n\n query : {query} \n\n\n')
            itemToUpdate = await self.generic_service.fetch_native_query_one_from_collection(
                collection_key=collection_key,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                native_query=query
            )  
            rbac_permission_id = data_to_save.get('rbac_permission_id',None)
            self.app_debug_print(f"\n\n\nrbac_permission_id : {rbac_permission_id}\n\n\n")
            rbac_role_id = data_to_save.get('rbac_role_id',None)
            self.app_debug_print(f"\n\n\nrbac_role_id : {rbac_role_id}\n\n\n")
            is_activated = data_to_save.get('is_activated',False)
            rbac_role = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                query={
                    "filter___id":rbac_role_id,
                },
                user=user_details,
            )
            self.app_debug_print(f"\n\n\nitemToUpdate : {itemToUpdate}\n\n\n")
            if not rbac_role:
                message = self.get_response_message(MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            permission = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                query={
                    "filter___id":rbac_permission_id,
                },
                user=user_details,
            )
            if not permission:
                message = self.get_response_message(MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            if not itemToUpdate:
                new_permission_target_doc = { 
                    "rbac_role_id":rbac_role_id,
                    "rbac_permission_id":rbac_permission_id,  
                }
                saved = await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                    filter_data={
                        "rbac_role_id":new_permission_target_doc['rbac_role_id'],
                        'rbac_permission_id':new_permission_target_doc['rbac_permission_id']
                    },
                    user=user_details, request=request,
                    update_data=new_permission_target_doc)
                self.app_debug_print(f'\n\n saved permissin target : {saved}\n\n')
                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message":message,
                    }
                )
            # UPDATE ONLY ACTIVATED PROPERTY
            
            if is_activated == False:
                # Soft delete the document
                success = await self.generic_service.hard_delete_data_from_collection(collection_key, itemToUpdate['id'])
                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
                if success:
                    return CustomJSONResponse(
                        status_code=status.HTTP_200_OK,
                        content={
                            "status_code": status.HTTP_200_OK,
                            "message": message,
                        }
                    )
                
            new_permission_target_doc = { 
                "rbac_role_id":itemToUpdate['rbac_role_id'],
                "rbac_permission_id":rbac_permission_id, 
                "is_activated":is_activated,  
            }
            saved = await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                    filter_data={
                        "rbac_role_id":new_permission_target_doc['rbac_role_id'],
                        'rbac_permission_id':new_permission_target_doc['rbac_permission_id']
                    },
                user=user_details, request=request,
                    update_data=new_permission_target_doc)
            
            self.app_debug_print(f'\n\n updated permissin target : {saved}\n\n',True)
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message":message,
                }
            )
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR 1 : {e} \n\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 : {e} \n\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))
        
        
        
        
