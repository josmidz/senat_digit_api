

from typing import Any, Dict, Optional

from fastapi import HTTPException, BackgroundTasks, status, File, Form, Query, Request, UploadFile
from app.modules.auth.enums.common import MessageCategory
from app.modules.core.types.response import CustomJSONResponse
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.auth.services.password.password_service import PasswordService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.device.device_service import DeviceService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.services.sms.sms_service import SmsService
from app.modules.core.enums.type_enum import EMultipleValidationType, OutputDataType
from app.modules.core.services.model.model_service import ModelService
from app.modules.core.utils.common.helpers import extract_field_on_output_data_element
from app.modules.core.configs.config import settings
from bson import ObjectId
import httpx

class EdocController(
    AuthenticatedService,
    DebugService,
    PasswordService,
    ResponseService,
    ConverterService,
    ModelService,
    SmsService,
    DeviceService):
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.auth.services.login.login_service import LoginService
        from app.modules.core.services.generic.generic_services import GenericService
        
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        self.login_service = LoginService(accept_language)
        super().__init__(accept_language)

    
    async def add_folder_data(
        self,
        request: Request,data: Dict[str, Any]):
        """
        Endpoint to add a new document to the specified collection.
        """
        try:
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            
            self.app_debug_print(f"Accept-Language from header: {self.accept_language}",True)
            
            # Add data to the collection
            data_org = {
                **data,
                "sys_organization_id": user_details['sys_organization_id'],
            }
            item_id = await self.generic_service.add_data_to_collection(CollectionKey.ARCH_FOLDER, data_org, user=user_details, request=request)
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
            raise HTTPException(status_code=500, detail=str(e))  
        

    async def hard_delete_folder_data(self,request: Request):
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
            self.app_debug_print(f" user_profil : {user_profil}",True)
             
            item_id = request.query_params.get('item_id',None)
            self.app_debug_print(f" item_id : {item_id}",True)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            check_data = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.ARCH_FOLDER,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id":  item_id,
                },
                user=user_details
            )
            self.app_debug_print(f" check_data : {check_data}",True)
            if not check_data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # VALIDATION PROCESS
            # validation_service = ValidationService(accept_language=self.accept_language)
            # validation_data = {
            #     "operation_type":EMultipleValidationType.HARD_DELETE,
            #     "sudo_action":sudo_action,
            #     "collection_name":CollectionKey.ARCH_FOLDER,
            #     "target_document_id":item_id,
            #     "user_details":user_details,
            #     "cascade_chilren":[
            #         {
            #             "collection_name":CollectionKey.ARCH_FILE,
            #             "field_name":"arch_folder_id"
            #         }
            #     ],
            # }
            # validation_process = await validation_service.validation_process(
            #     request=request,
            #     operation_type=validation_data.get("operation_type"),
            #     sudo_action=validation_data.get('sudo_action'),
            #     collection_name=validation_data.get("collection_name"),
            #     target_document_id=validation_data.get("target_document_id"),
            #     user_details=validation_data.get("user_details"),
            #     cascade_children=validation_data.get("cascade_children"),
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
            # Hard delete the document
            success = await self.generic_service.hard_delete_data_from_collection(CollectionKey.ARCH_FOLDER, item_id,self.accept_language)
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
            if success:
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
            else:
                message = self.get_response_message(MessageCategory.ERRORS, "FAILLURE_OPERATION_COMPLETED", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

        except PermissionError as e:
            self.app_debug_print(f" ERROR HARD DELETE 2 : {e}",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f" ERROR HARD DELETE FOLDER 3 : {e}",True)
            raise HTTPException(status_code=500, detail=str(e))


        
    async def fetch_org_folder_data(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page"),
        sort: Optional[Dict[str, int]] = {'created_at': -1},
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try:
            # Convert string to CollectionKey
            user_details = await self.get_user_info(request, self.accept_language)
            api_Consumer = await self.get_api_consumer(request, self.accept_language)
            user_profil = await self.get_user_profil(request, self.accept_language)

            # Fetch `Accept-Language` from headers, default to 'fr'
            self.app_debug_print(f"\n\n\n sort : {sort}\n\n\n", False)
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            raw_query_params = {
                **raw_query_params,
                "filter__moved_to_trash": False,
                "filter__sys_organization_id": str(user_details['sys_organization_id'])
            }

            query_params = self.convert_query_params(raw_query_params)
            sort = query_params.get('sort', {'created_at': -1})
            # If sort is a string, parse it into a dictionary
            self.app_debug_print(f"\n\n\n sort 0 > : {sort}\n\n\n", False)
            self.app_debug_print(
                f"Query Parameters (converted): {query_params}", False)
            # If sort is a string, parse it into a dictionary
            self.app_debug_print(f"\n\n\n sort 1 > : {sort}\n\n\n", False)

            self.app_debug_print(f"\n\n\n sort 2> : {sort}\n\n\n", False)

            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.ARCH_FOLDER,
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

            formated_folder = []
            for folder in data:
                folder_id = extract_field_on_output_data_element(folder,'id',OutputDataType(output_data_type).value)
                sub_folders = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.ARCH_FOLDER,
                    accept_language=self.accept_language,
                    query={
                        "filter__arch_folder_id": folder_id,
                    },
                    user=user_details
                )
                folder_files = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.ARCH_FILE,
                    accept_language=self.accept_language,
                    query={
                        "filter__arch_folder_id": folder_id,
                    },
                    user=user_details
                )
                cumulate_file_size_pipeline = [
                    {
                        '$match': {
                            'moved_to_trash': False,
                            'arch_folder_id': ObjectId(str(folder_id))
                        }
                    }, {
                        '$group': {
                            '_id': None,
                            'totalSizeBytes': {
                                '$sum': {
                                    '$toLong': '$file_size'
                                }
                            }
                        }
                    }, {
                        '$project': {
                            '_id': 0,
                            'totalSizeBytes': 1,
                            'humanReadable': {
                                '$switch': {
                                    'branches': [
                                        {
                                            'case': {
                                                '$gte': [
                                                    '$totalSizeBytes', 1024 * 1024 * 1024 * 1024
                                                ]
                                            },
                                            'then': {
                                                '$concat': [
                                                    {
                                                        '$toString': {
                                                            '$round': [
                                                                {
                                                                    '$divide': [
                                                                        '$totalSizeBytes', 1024 * 1024 * 1024 * 1024
                                                                    ]
                                                                }, 1
                                                            ]
                                                        }
                                                    }, ' TB'
                                                ]
                                            }
                                        }, {
                                            'case': {
                                                '$gte': [
                                                    '$totalSizeBytes', 1024 * 1024 * 1024
                                                ]
                                            },
                                            'then': {
                                                '$concat': [
                                                    {
                                                        '$toString': {
                                                            '$round': [
                                                                {
                                                                    '$divide': [
                                                                        '$totalSizeBytes', 1024 * 1024 * 1024
                                                                    ]
                                                                }, 1
                                                            ]
                                                        }
                                                    }, ' GB'
                                                ]
                                            }
                                        }, {
                                            'case': {
                                                '$gte': [
                                                    '$totalSizeBytes', 1024 * 1024
                                                ]
                                            },
                                            'then': {
                                                '$concat': [
                                                    {
                                                        '$toString': {
                                                            '$round': [
                                                                {
                                                                    '$divide': [
                                                                        '$totalSizeBytes', 1024 * 1024
                                                                    ]
                                                                }, 1
                                                            ]
                                                        }
                                                    }, ' MB'
                                                ]
                                            }
                                        }, {
                                            'case': {
                                                '$gte': [
                                                    '$totalSizeBytes', 1024
                                                ]
                                            },
                                            'then': {
                                                '$concat': [
                                                    {
                                                        '$toString': {
                                                            '$round': [
                                                                {
                                                                    '$divide': [
                                                                        '$totalSizeBytes', 1024
                                                                    ]
                                                                }, 1
                                                            ]
                                                        }
                                                    }, ' KB'
                                                ]
                                            }
                                        }
                                    ],
                                    'default': {
                                        '$concat': [
                                            {
                                                '$toString': '$totalSizeBytes'
                                            }, ' B'
                                        ]
                                    }
                                }
                            }
                        }
                    }
                ]

                # Use raw aggregation for size calculation to avoid document formatting
                from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
                from app.db.dao import DAO

                metadata = COLLECTION_MODEL_MAPPING.get(CollectionKey.ARCH_FILE)
                dao = DAO(metadata.collection_name, metadata.model_class, is_read_only=True)

                # Execute raw aggregation pipeline
                cursor = dao.collection.aggregate(cumulate_file_size_pipeline)
                all_file_size = await cursor.to_list(length=None)

                print(f"\n\n\n RAW AGGREGATION RESULT: {all_file_size} \n\n\n")

                storage_used = "0 Ko"
                if len(all_file_size) > 0 and 'humanReadable' in all_file_size[0]:
                    storage_used = all_file_size[0]['humanReadable']
                    # print(f"\n\n\n STORAGE USED: {storage_used} \n\n\n")
                formated_folder.append({
                    "id": folder['id'],
                    "name": folder['name'],
                    "description_str": folder['description_str'],
                    "subfolder_count": sub_folders,
                    "files_count": folder_files,
                    "storage_used": storage_used,
                    "createdAt": folder['created_at'],
                })

            extra_data = {}
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.ARCH_FOLDER,
                    accept_language=self.accept_language,
                    query={
                        **query_params
                    },
                    user=user_details
                )
                extra_data = {
                    "max": max_data,
                    "limit": limit
                }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": formated_folder,
                    **extra_data
                }
            )

        except PermissionError:
            raise HTTPException(
                status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            self.app_debug_print(f"Error in HTTPException : > 2 {str(e)}", True)
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in HTTPException: > 2 {str(e)}", True)
            raise HTTPException(
                status_code=500, detail="An unexpected error occurred.")



    async def fetch_org_folder_bin_data(
        self,
        request: Request,
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
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            # Fetch `Accept-Language` from headers, default to 'fr'
            self.app_debug_print(f"\n\n\n sort : {sort}\n\n\n",False)
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            raw_query_params = {
                **raw_query_params,
                "filter__added_to_bin": True,
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
                collection_key=CollectionKey.ARCH_FOLDER,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language= self.accept_language,
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
                    collection_key=CollectionKey.ARCH_FOLDER,
                    accept_language= self.accept_language,
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
    
    async def add_org_file_data(
        self,
        request: Request,
        arch_folder_id: str = Form(...), 
        upload_file: UploadFile = File(...),
    ):
        """
        Upload a single file and forward it to another API endpoint with progress updates.
        """
        try:
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request, self.accept_language)
            api_Consumer = await self.get_api_consumer(request, self.accept_language)
            user_profil = await self.get_user_profil(request, self.accept_language)
            self.app_debug_print(f"Received arch_folder_id: {arch_folder_id}", True)
            self.app_debug_print(f"Received file: {upload_file}", True)
            # Read the file content
            # org_info = await self.generic_service.fetch_native_query_one_from_collection(
            #     collection_key=CollectionKey.SYS_ORGANIZATION,
            #     accept_language= self.accept_language,
            #     native_query={
            #         "_id": ObjectId(id),
            #     }
            # )
            # if not org_info:
            #     message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
            #     raise HTTPException(status_code=404, detail=message)

            # Read the entire file content first
            file_content = await upload_file.read()

            # Reset file pointer for potential reuse
            await upload_file.seek(0)

            # Use httpx AsyncClient to post the file to the target endpoint
            async with httpx.AsyncClient() as client:
                headers = {
                    "authorization": f"Bearer {settings.POST_NANGA_FILE_BEARER_TOKEN}"
                }
                # math
                self.app_debug_print(f"\n\n\n headers : {headers} \n\n", False)
                response = await client.post(
                    f"{settings.POST_NANGA_FILE_SYSTEM_URL}/files/upload?base_dir={settings.POST_NANGA_FILE_ORGANIZATION_LOGO_BASE_DIR}",
                    files={"upload_file": (upload_file.filename, file_content, upload_file.content_type)},
                    headers=headers
                )
                self.app_debug_print(f"Forwarded file upload response status: {response.status_code}", False)

            self.app_debug_print(f" UPLOADED FILE response : {isinstance(response.status_code, int)}", True)
            self.app_debug_print(f" UPLOADED FILE all response : {response.json()}", True)

            # You may want to validate the response from the target endpoint.
            if response.status_code == 200 or response.status_code == 201:
                # Assuming response.data is a dictionary or an object with attributes
                resp = response.json()
                data = resp.get('data', {})


                # Access the fields from response.data
                # Access the fields from response.data
                id = data.get('id')
                file_name = data.get('file_name')
                file_url = data.get('file_url')
                # created_at = data.get('created_at')
                file_size = data.get('file_size')
                file_type = data.get('file_type')
                file_path = data.get('file_path')
                # identifier = data.get('identifier')
                file_original_name = data.get('file_original_name')
                file_extension = data.get('file_extension')
                file_str_id_composed = data.get('file_str_id_composed')

                # PREPARE ARCH FILE DATA
                file_url_composed = f"{settings.MAIN_APP_BASE_URL}/static/files/view-file/{file_str_id_composed}"
                arch_file_data = {
                    "remote_arch_file_id":data.get('id'),
                    "remote_arch_file_url":file_url,
                    "file_name":file_name,
                    "file_str_id_composed":file_str_id_composed,
                    "file_url":file_url_composed,
                    "file_original_name":file_original_name,
                    "file_extension":file_extension,
                    "sys_organization_id":user_details['sys_organization_id'],
                    "file_type":file_type,
                    "file_size":file_size,
                    "file_path":file_path,
                    "arch_folder_id":arch_folder_id if ObjectId.is_valid(arch_folder_id) else None,
                }
                # Call the asynchronous function to update the collection
                added_file_id = await self.generic_service.add_data_to_collection(collection_key=CollectionKey.ARCH_FILE, data=arch_file_data, user=user_details, request=request)
                self.app_debug_print(f" added_file_id: {added_file_id}", False)

                message = self.get_response_message(MessageCategory.SUCCESS, "FILE_UPLOADED_SUCCESSFULLY", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
            raise HTTPException(status_code=response.status_code, detail="Failed to forward the file to the target API.")

        except Exception as e:
            self.app_debug_print(f"Error during file upload edocs: {e}", True)
            raise HTTPException(status_code=500, detail="An error occurred while processing the file.")
       
            

    async def fetch_org_edoc_stats(
        self,
        request: Request,
    ):
        try:
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            # print(f"\n\n user_details['sys_organization_id'] : {user_details['sys_organization_id']} \n\n")
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params)
            sort = query_params.get('sort', {'created_at': -1})
            all_folder_count = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.ARCH_FOLDER,
                accept_language= self.accept_language,
                query={
                   "filter__moved_to_trash": False,
                    "filter__sys_organization_id": str(user_details['sys_organization_id'])
                },
                user=user_details
            )
            all_folder_in_bin_count = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.ARCH_FOLDER,
                accept_language= self.accept_language,
                query={
                   "filter__moved_to_trash": True,
                    "filter__sys_organization_id": str(user_details['sys_organization_id'])
                },
                user=user_details
            )

            all_file_count = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.ARCH_FILE,
                accept_language= self.accept_language,
                query={
                   "filter__moved_to_trash": False,
                    "filter__sys_organization_id": str(user_details['sys_organization_id'])
                },
                user=user_details
            )
            all_file_in_bin_count = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.ARCH_FILE,
                accept_language= self.accept_language,
                query={
                   "filter__moved_to_trash": False,
                    "filter__sys_organization_id": str(user_details['sys_organization_id'])
                },
                user=user_details
            )
            cumulate_file_size_pipeline = [
                {
                    '$match': {
                        'moved_to_trash': False,
                        'sys_organization_id': ObjectId(str(user_details['sys_organization_id']))
                    }
                }, {
                    '$group': {
                        '_id': None,
                        'totalSizeBytes': {
                            '$sum': {
                                '$toLong': '$file_size'
                            }
                        }
                    }
                }, {
                    '$project': {
                        '_id': 0,
                        'totalSizeBytes': 1,
                        'humanReadable': {
                            '$switch': {
                                'branches': [
                                    {
                                        'case': {
                                            '$gte': [
                                                '$totalSizeBytes', 1024 * 1024 * 1024 * 1024
                                            ]
                                        },
                                        'then': {
                                            '$concat': [
                                                {
                                                    '$toString': {
                                                        '$round': [
                                                            {
                                                                '$divide': [
                                                                    '$totalSizeBytes', 1024 * 1024 * 1024 * 1024
                                                                ]
                                                            }, 1
                                                        ]
                                                    }
                                                }, ' TB'
                                            ]
                                        }
                                    }, {
                                        'case': {
                                            '$gte': [
                                                '$totalSizeBytes', 1024 * 1024 * 1024
                                            ]
                                        },
                                        'then': {
                                            '$concat': [
                                                {
                                                    '$toString': {
                                                        '$round': [
                                                            {
                                                                '$divide': [
                                                                    '$totalSizeBytes', 1024 * 1024 * 1024
                                                                ]
                                                            }, 1
                                                        ]
                                                    }
                                                }, ' GB'
                                            ]
                                        }
                                    }, {
                                        'case': {
                                            '$gte': [
                                                '$totalSizeBytes', 1024 * 1024
                                            ]
                                        },
                                        'then': {
                                            '$concat': [
                                                {
                                                    '$toString': {
                                                        '$round': [
                                                            {
                                                                '$divide': [
                                                                    '$totalSizeBytes', 1024 * 1024
                                                                ]
                                                            }, 1
                                                        ]
                                                    }
                                                }, ' MB'
                                            ]
                                        }
                                    }, {
                                        'case': {
                                            '$gte': [
                                                '$totalSizeBytes', 1024
                                            ]
                                        },
                                        'then': {
                                            '$concat': [
                                                {
                                                    '$toString': {
                                                        '$round': [
                                                            {
                                                                '$divide': [
                                                                    '$totalSizeBytes', 1024
                                                                ]
                                                            }, 1
                                                        ]
                                                    }
                                                }, ' KB'
                                            ]
                                        }
                                    }
                                ],
                                'default': {
                                    '$concat': [
                                        {
                                            '$toString': '$totalSizeBytes'
                                        }, ' B'
                                    ]
                                }
                            }
                        }
                    }
                }
            ]

            all_file_size = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.ARCH_FILE,
                accept_language=self.accept_language,
                pipeline=cumulate_file_size_pipeline
            )
            self.app_debug_print(f"\n\n\n all_file_size : {all_file_size} \n\n\n")
            storage_used = "0 Ko"
            if len(all_file_size) > 0:
                storage_used = all_file_size[0]['humanReadable']
            reponse_data = {
                "folders":all_folder_count,
                "files":all_file_count,
                "bin":{
                    "files":all_file_in_bin_count,
                    "folders":all_folder_in_bin_count,
                },
                "storage_used":storage_used,
            }
            
            
            
            return  CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "data":reponse_data
                }
            ) 
            
        except Exception as e:
            self.app_debug_print(f"Error edoc stats : {e}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                ) 
    
        
        
        
        
        
        
        
        
        