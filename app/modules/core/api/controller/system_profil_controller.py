from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from fastapi import HTTPException, Query, Request
from fastapi import status
from bson.objectid import ObjectId
from app.modules.core.enums.type_enum import OutputDataType, EMultipleValidationStatus, EMultipleValidationType
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
from app.modules.core.models.mapping_keys import CollectionKey

from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.device.device_service import DeviceService
from app.modules.core.services.model.model_service import ModelService
from app.modules.core.types.response import CustomJSONResponse

from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.schemas.user_schema import ProfilPermissionCreate
from app.modules.security.middleware.sudo_action_middleware import sudo_action_middleware
from app.modules.auth.enums.common import MessageCategory


class SystemProfilController(
    AuthenticatedService,
    ResponseService,
    DebugService,
    ConverterService,
    ModelService,
    DeviceService):
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


    async def core_add_profile_data(self,request: Request, data: Dict[str, Any]):
        """
        Endpoint to add a new role from organization.
        """
        try:
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            self.app_debug_print(f"\n\nbody : {data}\n\n",True)

            agent_organization  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter___id": user_details['sys_organization_id'],
                },
                user=user_details,
            )
            if not agent_organization:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "AGENT_ORGANIZATION_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            parent_profil_id = data.get('rbac_profile_id', None)
            if not parent_profil_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_PARENT_PROFIL_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            profile_data = {
                **data,
                "sys_organization_id": None,
                "rbac_profile_id":None,
                "is_default":False,
                "system_reserved_actions":True,
            }
            # Add data to the collection
            org_profil_id = await self.generic_service.add_data_to_collection(CollectionKey.RBAC_PROFILE, profile_data, user=user_details, request=request)

            # ADD RESTRICTED PROFIL FROM PARENT PROFIL
            parent_restricted_profil = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type = OutputDataType.DEFAULT,
                all_data=True,
                query={
                    "filter__rbac_profile_id":parent_profil_id
                },
                user=user_details,
            )
            for restricted_profil in parent_restricted_profil:
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    filter_data={"targeted_id":restricted_profil['targeted_id'],'rbac_profile_id':org_profil_id},
                    update_data={
                        "targeted_id":restricted_profil['targeted_id'],
                        "rbac_profile_id":org_profil_id,
                    }
                )

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "status_code": status.HTTP_201_CREATED,
                        "message":message,
                        "data":org_profil_id
                    }
                )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def core_delete_profile_data(self,request: Request,):
        """
        Endpoint to add a new role from organization.
        """
        try:
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language) 

            item_id = request.query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter___id": item_id,
                },
                user=user_details,
            )
            if not profil_info:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "PROFIL_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            # DELETE ALL RESTRICTED PROFIL
            parent_restricted_profil = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type = OutputDataType.DEFAULT,
                all_data=True,
                query={
                    "filter__rbac_profile_id":profil_info['id']
                },
                user=user_details,
            )
            for restricted_profil in parent_restricted_profil:
                # DELETION
                await self.generic_service.hard_delete_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    item_id=restricted_profil['id']
                ) 

            # DELETION
            await self.generic_service.hard_delete_data_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                item_id=profil_info['id']
            ) 

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "status_code": status.HTTP_201_CREATED,
                        "message":message,
                        "data":item_id
                    }
                )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def core_get_profile_permissions(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
    ):
        try:

            user_details = await self.get_user_info(request,self.accept_language)
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request,accept_language= self.accept_language)
            user_profil = await self.get_user_profil(request=request,accept_language= self.accept_language)
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = ConverterService.convert_query_params(raw_query_params)
            rbac_profile_id = query_params.get('rbac_profile_id',None)
            if not rbac_profile_id:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            # CHECK IF THE ROLE BELONGS TO THE ORGANIZATION
            profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language= self.accept_language,
                query={
                    "filter___id":rbac_profile_id,
                    # "filter__sys_organization_id":user_details['sys_organization_id'],
                },
                user=user_details,
            )
            if not profil_info:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # PIPELINE TO RBAC_RESTRICTED_PROFIL JOIN PERMISSION WHERE TARGETED_ID IS JOINED TO RBAC_PERMISSION
            profil_permissions_pipeline = [
                {
                    '$match': {
                        'rbac_profile_id': ObjectId(profil_info['id'])
                    }
                }, {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                        'localField': 'targeted_id',
                        'foreignField': '_id',
                        'as': 'unwind__rbac_permission'
                    }
                }, {
                    '$unwind': {
                        'path': '$unwind__rbac_permission',
                        'preserveNullAndEmptyArrays': False
                    }
                }, {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_TITLE.model_name}",
                        'localField': 'unwind__rbac_permission.rbac_title_id',
                        'foreignField': '_id',
                        'as': 'unwind__rbac_title'
                    }
                }, {
                    '$unwind': {
                        'path': '$unwind__rbac_title',
                        'preserveNullAndEmptyArrays': False
                    }
                },
                {
                    '$match': {
                        "unwind__rbac_permission.is_accessible_to_all_profil":False,
                    }
                },
            ]
            profil_permissions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL.value,
                output_data_type=OutputDataType.DATA_TABLE.value,
                accept_language= self.accept_language,
                page=0,
                limit=100000,
                pipeline=profil_permissions_pipeline,
            )
            self.app_debug_print(f"\n\n\n role_permissions LEN: {len(profil_permissions)} \n\n\n",True)
            # Process your data
            hierarchy = await self.build_profil_joined_to_permission_rbac_hierarchy(profil_permissions,output_data_type,rbac_profile_id, user_details=user_details)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":hierarchy,
                }
            )
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR 1 : {e} \n\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 : {e} \n\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))



    async def core_get_extended_profile_permissions(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
    ):
        try:

            user_details = await self.get_user_info(request,self.accept_language)
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request,accept_language= self.accept_language)
            user_profil = await self.get_user_profil(request=request,accept_language= self.accept_language)
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = ConverterService.convert_query_params(raw_query_params)
            rbac_profile_id = query_params.get('rbac_profile_id',None)
            if not rbac_profile_id:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            # CHECK IF THE ROLE BELONGS TO THE ORGANIZATION
            profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language= self.accept_language,
                query={
                    "filter___id":rbac_profile_id,
                    # "filter__sys_organization_id":user_details['sys_organization_id'],
                },
                user=user_details,
            )
            if not profil_info:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # PIPELINE TO RBAC_RESTRICTED_PROFIL JOIN PERMISSION WHERE TARGETED_ID IS JOINED TO RBAC_PERMISSION
            profil_permissions_pipeline = [
                {
                    '$match': {
                        'rbac_profile_id': ObjectId(profil_info['rbac_profile_id'])
                    }
                }, {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION.model_name}", 
                        'localField': 'targeted_id', 
                        'foreignField': '_id', 
                        'as': 'unwind__rbac_permission'
                    }
                }, {
                    '$unwind': {
                        'path': '$unwind__rbac_permission', 
                        'preserveNullAndEmptyArrays': False
                    }
                }, {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_TITLE.model_name}", 
                        'localField': 'unwind__rbac_permission.rbac_title_id', 
                        'foreignField': '_id', 
                        'as': 'unwind__rbac_title'
                    }
                }, {
                    '$unwind': {
                        'path': '$unwind__rbac_title', 
                        'preserveNullAndEmptyArrays': False
                    }
                },
                {
                    '$match': {
                        "unwind__rbac_permission.is_accessible_to_all_profil":False,
                    }
                },  
            ]
            profil_permissions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL.value,
                output_data_type=OutputDataType.DATA_TABLE.value,
                accept_language= self.accept_language,
                page=0,
                limit=100000,
                pipeline=profil_permissions_pipeline,
            )
            self.app_debug_print(f"\n\n\n role_permissions LEN: {len(profil_permissions)} \n\n\n",True)
            # Process your data
            hierarchy = await self.build_extended_profil_joined_to_permission_rbac_hierarchy(profil_permissions,output_data_type,rbac_profile_id, user_details=user_details)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":hierarchy,
                }
            ) 
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR 1 : {e} \n\n\n",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 : {e} \n\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))
        

        
    async def build_profil_joined_to_permission_rbac_hierarchy(self, data_list, output_data_type,rbac_profile_id, user_details=None):
        """
        Builds complete RBAC hierarchy with recursive parent fetching. rbac_profile_id

        Args:
            data_list: List of RBAC data dictionaries
            output_data_type: The output format type

        Returns:
            List of dictionaries with complete hierarchy:
            [
                {
                    'rbac_title': dict,
                    'permissions': [dict],
                    'children': list
                }
            ]
        """
        try:
            # Convert single item to list if needed
            if not isinstance(data_list, list):
                data_list = [data_list]

            # First pass: organize all data by permission_to_role
            title_map = {}
            self.app_debug_print(f"\n\n\n\n data_list ln: {len(data_list)} \n\n\n",False)
            for data in data_list:
                rbac_title = data.get('rbac_title')
                if not rbac_title:
                    continue

                # Get title ID based on output type
                self.app_debug_print(f"\n\n\n\n output_data_type : {output_data_type}",False)
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    title_id = rbac_title['id']['display_value']
                else:  # DEFAULT or TREE
                    title_id = rbac_title['id']
                self.app_debug_print(f"\n\n\n\n title_id : {title_id}",False)
                # Create permission data (all except rbac_title)
                permission = {k: v for k, v in data.items() if k != 'rbac_title'}
                self.app_debug_print(f"\n\n\n permission \n\n\n PROFIL ID {rbac_profile_id} |   ID : {permission['id']['display_value']} |  LABEL : {permission['rbac_permission']['label']} \n\n\n",False)
                restricted_profil_item = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language= self.accept_language,
                    query={
                        "filter__targeted_id":permission['rbac_permission']['id']['display_value'],
                        "filter__rbac_profile_id":rbac_profile_id,
                    },
                    user=user_details,
                )
                self.app_debug_print(f"\n\n\n restricted_profil_item \n\n\n {True if restricted_profil_item is not None else False}\n\n\n",False)
                formated_permission = {
                    **permission['rbac_permission'],
                    "role_and_permission_are_joined": True if restricted_profil_item is not None else False,
                }
                self.app_debug_print(f"\n\n\n formated_permission is okay : {title_map} \n\n\n",False)
                self.app_debug_print(f"\n\n\n title_id  : {title_id} \n\n\n",False)
                # Initialize title entry if not exists
                if title_id not in title_map:
                    self.app_debug_print(f'\n\n title_map in loop : {title_id} \n\n',False)
                    title_map[title_id] = {
                        'rbac_title': rbac_title,
                        'permissions': [],
                        'children': []
                    }

                self.app_debug_print(f"\n\n\n title_map : after : {title_map} \n\n\n",False)
                # Add permission to this title
                title_map[title_id]['permissions'].append(formated_permission)

            # Second pass: build complete hierarchy with recursive parent fetching
            processed_titles = set()

            for title_id in list(title_map.keys()):
                if title_id not in processed_titles:
                    await self._process_title_hierarchy(title_id, title_map, processed_titles, output_data_type)

            # Return only root nodes (rbac_title_id == None)
            return [
                title_data for title_data in title_map.values()
                if self._is_root_title(title_data['rbac_title'], output_data_type)
            ]
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR PROFIL HIERARCHY : {e} \n\n\n",True)
            return []


    async def build_extended_profil_joined_to_permission_rbac_hierarchy(self, data_list, output_data_type,rbac_profile_id, user_details=None):
        """
        Builds complete RBAC hierarchy with recursive parent fetching. rbac_profile_id

        Args:
            data_list: List of RBAC data dictionaries
            output_data_type: The output format type

        Returns:
            List of dictionaries with complete hierarchy:
            [
                {
                    'rbac_title': dict,
                    'permissions': [dict],
                    'children': list
                }
            ]
        """
        try:
            # Convert single item to list if needed
            if not isinstance(data_list, list):
                data_list = [data_list]

            # First pass: organize all data by permission_to_role
            title_map = {}
            self.app_debug_print(f"\n\n\n\n data_list ln: {len(data_list)} \n\n\n",False)
            for data in data_list:
                rbac_title = data.get('rbac_title')
                if not rbac_title:
                    continue

                # Get title ID based on output type
                self.app_debug_print(f"\n\n\n\n output_data_type : {output_data_type}",False)
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    title_id = rbac_title['id']['display_value']
                else:  # DEFAULT or TREE
                    title_id = rbac_title['id']
                self.app_debug_print(f"\n\n\n\n title_id : {title_id}",False)
                # Create permission data (all except rbac_title)
                permission = {k: v for k, v in data.items() if k != 'rbac_title'}
                self.app_debug_print(f"\n\n\n permission \n\n\n PROFIL ID {rbac_profile_id} |   ID : {permission['id']['display_value']} |  LABEL : {permission['rbac_permission']['label']} \n\n\n",False)
                restricted_profil_item = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language= self.accept_language,
                    query={
                        "filter__targeted_id":permission['rbac_permission']['id']['display_value'],
                        "filter__rbac_profile_id":rbac_profile_id,
                    },
                    user=user_details,
                )
                self.app_debug_print(f"\n\n\n restricted_profil_item \n\n\n {True if restricted_profil_item is not None else False}\n\n\n",False)
                role_and_permission_are_joined = True if restricted_profil_item is not None else False
                formated_permission = {
                    **permission['rbac_permission'],
                    "role_and_permission_are_joined":role_and_permission_are_joined
                }
                self.app_debug_print(f"\n\n\n formated_permission is okay : {title_map} \n\n\n",False)
                self.app_debug_print(f"\n\n\n title_id  : {title_id} \n\n\n",False)
                # Initialize title entry if not exists
                if title_id not in title_map and role_and_permission_are_joined == False:
                    self.app_debug_print(f'\n\n title_map in loop : {title_id} \n\n',False)
                    title_map[title_id] = {
                        'rbac_title': rbac_title,
                        'permissions': [],
                        'children': []
                    }

                self.app_debug_print(f"\n\n\n title_map : after : {title_map} \n\n\n",False)
                # Add permission to this title
                if role_and_permission_are_joined == False:
                    title_map[title_id]['permissions'].append(formated_permission)

            # Second pass: build complete hierarchy with recursive parent fetching
            processed_titles = set()

            for title_id in list(title_map.keys()):
                if title_id not in processed_titles:
                    await self._process_title_hierarchy(title_id, title_map, processed_titles, output_data_type)

            # Return only root nodes (rbac_title_id == None)
            return [
                title_data for title_data in title_map.values()
                if self._is_root_title(title_data['rbac_title'], output_data_type)
            ]
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR PROFIL HIERARCHY : {e} \n\n\n",True)
            return []

    async def core_upsert_profile_permissions(
        self,
        request: Request,
        body: Dict[str, Any]
    ):
        try:
            self.app_debug_print(f" \n\n\n update_org_role_permissions : {body} \n\n\n",False)
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
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request,accept_language= self.accept_language)
            user_profil = await self.get_user_profil(request=request,accept_language= self.accept_language)

            self.app_debug_print(f" \n\n\n body : {body} \n\n\n",False)
            validator_data = ProfilPermissionCreate.model_validate(body, context={"language": self.accept_language})
            self.app_debug_print(f" \n\n\n validator_data : {validator_data} \n\n\n",False)

            profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language= self.accept_language,
                query = {
                    "filter___id":validator_data.rbac_profile_id,

                },
                user=user_details,
            )
            if not profil_info:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            profil_permissions_pipeline = [
                {
                    '$match': {
                        'rbac_profile_id': ObjectId(profil_info['id'])
                    }
                }, {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION.model_name}", 
                        'localField': 'targeted_id', 
                        'foreignField': '_id', 
                        'as': 'unwind__rbac_permission'
                    }
                }, {
                    '$unwind': {
                        'path': '$unwind__rbac_permission', 
                        'preserveNullAndEmptyArrays': False
                    }
                }, {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_TITLE.model_name}", 
                        'localField': 'unwind__rbac_permission.rbac_title_id', 
                        'foreignField': '_id', 
                        'as': 'unwind__rbac_title'
                    }
                }, {
                    '$unwind': {
                        'path': '$unwind__rbac_title', 
                        'preserveNullAndEmptyArrays': False
                    }
                },
                {
                    '$match': {
                        "unwind__rbac_permission.is_accessible_to_all_profil":False,
                    }
                },  
            ]
            profil_permissions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL.value,
                output_data_type=OutputDataType.DATA_TABLE.value,
                accept_language= self.accept_language,
                page=0,
                limit=100000,
                pipeline=profil_permissions_pipeline,
            )
            for restricted_profil in profil_permissions: 
                restricted_profil_id = restricted_profil['id']['display_value'] if isinstance(restricted_profil,dict) else None
                await self.generic_service.hard_delete_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL.value, 
                    accept_language= self.accept_language,
                    item_id=restricted_profil_id
                ) 

            # ADD NEW RBAC PERMISSION ROLES
            for permission_id in validator_data.rbac_permissions:
                new_perm_tar_role_doc = {
                    "rbac_profile_id": validator_data.rbac_profile_id,
                    "targeted_id": permission_id,
                }
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL.value,
                    filter_data={
                        "rbac_profile_id":new_perm_tar_role_doc['rbac_profile_id'],
                        'targeted_id':new_perm_tar_role_doc['targeted_id']
                    },
                    update_data=new_perm_tar_role_doc)
                
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f" \n\n Exception: {e}\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))
        

    async def core_upsert_extended_profile_permissions(
        self,
        request: Request,
        body: Dict[str, Any]
    ):
        try:
            self.app_debug_print(f" \n\n\n update_org_role_permissions : {body} \n\n\n",False)
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
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request,accept_language= self.accept_language)
            user_profil = await self.get_user_profil(request=request,accept_language= self.accept_language)

            self.app_debug_print(f" \n\n\n body : {body} \n\n\n",False)
            validator_data = ProfilPermissionCreate.model_validate(body, context={"language": self.accept_language})
            self.app_debug_print(f" \n\n\n validator_data : {validator_data} \n\n\n",False)

            profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language= self.accept_language,
                query = {
                    "filter___id":validator_data.rbac_profile_id,
                },
                user=user_details,
            )
            if not profil_info:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # ADD NEW RBAC PERMISSION ROLES
            for permission_id in validator_data.rbac_permissions:
                new_perm_tar_role_doc = {
                    "rbac_profile_id": validator_data.rbac_profile_id,
                    "targeted_id": permission_id,
                }
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL.value,
                    filter_data={
                        "rbac_profile_id":new_perm_tar_role_doc['rbac_profile_id'],
                        'targeted_id':new_perm_tar_role_doc['targeted_id']
                    },
                    update_data=new_perm_tar_role_doc)
                
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f" \n\n Exception: {e}\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))
        
