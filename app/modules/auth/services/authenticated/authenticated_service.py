from datetime import datetime, timedelta, timezone

from app.modules.auth.enums.mfa import EMfaPurpose, MFaFlag
from app.modules.core.types.saas import ESaasConfigInfoKind, ESaasConfigPurpose
from fastapi import HTTPException, Request,status
from typing import Any, Dict, List, Optional

from app.modules.auth.enums.common import MessageCategory
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.enums.type_enum import AccountStatusFlag, EJWTTokenType, OutputDataType
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.types.response import CustomJSONResponse
from app.modules.core.utils.common.helpers import extract_field_on_output_data_element

class CustomJSONResponseException(Exception):
    """Custom exception that carries a CustomJSONResponse"""
    def __init__(self, response: CustomJSONResponse):
        self.response = response
        super().__init__(f"CustomJSONResponse with status {response.status_code}")
from app.modules.auth.services.token.token_service import TokenService
from app.modules.auth.enums.auth import ELoginStatus


class AuthenticatedService:

    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.core.services.generic.generic_services import GenericService
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language=accept_language)

    @staticmethod
    async def get_decoded_token(request: Request,expected_type:EJWTTokenType,accept_language:str = 'fr') -> Optional[dict[str, Any]]:
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.auth.services.token.token_service import TokenService
        generic_service = GenericService(accept_language)
        authorization = request.headers.get("authorization")
        DebugService.app_debug_print(f"\n\n\n authorization >> {authorization} \n\n\n",False)
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            DebugService.app_debug_print(f"\n\n\n token >> {token} \n\n\n",False)
            decoded_token = TokenService(accept_language=accept_language).decode_and_verify_token(
                token=token,
                expected_type=expected_type,
                by_pass_exception=True
            )
            DebugService.app_debug_print(f"\n\n\n decoded_token >> {decoded_token} \n\n\n",False)
            if not decoded_token:
                return None
            
            return decoded_token
        return None
    
    
    async def get_decoded_given_token(self,token: str,expected_type:EJWTTokenType,accept_language:str = 'fr') -> Optional[dict[str, Any]]:
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.auth.services.token.token_service import TokenService
        decoded_token = TokenService(accept_language=accept_language).decode_and_verify_token(
            token=token,
            expected_type=expected_type,
            by_pass_exception=True
        )
        DebugService.app_debug_print(f"\n\n\n decoded_token >> {decoded_token} \n\n\n",False)
        if not decoded_token:
            return None
        
        return decoded_token

    @staticmethod
    async def get_device_info_from_db(request: Request,sys_user_id:str,accept_language:str = 'fr') -> Optional[dict[str, Any]]:
        from app.modules.core.services.device.device_service import DeviceService
        try:
            device_hashed_id = getattr(request.state, "deviceHashedId", None)
            device_db_info = await DeviceService(accept_language=accept_language).device_info_from_db_and_user_id(
                device_hashed_id=device_hashed_id,
                sys_user_id=sys_user_id,
            )
            DebugService.app_debug_print(f"\n\n\n device_db_info >> {device_db_info} \n\n\n",False)
            return device_db_info
        except Exception as e:
            return None
        
    async def user_available_login_mfa(self,sys_user_id:str,accept_language:str = DEFAULT_LANGUAGE)-> List[Dict[str, Any]]:
        try:
            from bson import ObjectId

            # Convert sys_user_id to ObjectId for MongoDB queries
            user_object_id = ObjectId(sys_user_id)

            # MFA aggregation pipeline
            mfa_pipeline = [
                # Match stage - filter MFAs based on criteria
                {
                    "$match": {
                        "is_activated": True,
                        "is_default": True,
                        "purpose": {
                            "$in": [
                                EMfaPurpose.LOGIN_ONLY.value,
                                EMfaPurpose.LOGIN_AND_RESET_PASSWORD.value,
                                EMfaPurpose.LOGIN_AND_LOCKED_SCREEN.value,
                                EMfaPurpose.LOCKED_SCREEN_AND_LOGIN.value
                            ]
                        }
                    }
                },
                # Lookup stage - join with CFG_USER_MFAS
                {
                    "$lookup": {
                        "from": f"{CollectionKey.CFG_USER_MFA.model_name}",
                        "let": {"mfa_id": "$_id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$and": [
                                            {"$eq": ["$ref_mfa_id", "$$mfa_id"]},
                                            {"$eq": ["$is_configured", True]},
                                            {"$eq": ["$sys_user_id", ObjectId(user_object_id)]}  # ← Change this line
                                        ]
                                    }
                                }
                            }
                        ],
                        "as": "user_mfas"
                    }
                }, 
                # Match stage - include MFAs that have user associations OR are default
                {
                    "$match": {
                        "$or": [
                            {"user_mfas": {"$ne": []}},  # Has user MFA associations
                            {"is_default": True}         # Or is a default MFA
                        ]
                    }
                },
                # Group stage - group by flag
                {
                    "$group": {
                        "_id": "$flag",
                        "mfas": {
                            "$push": {
                                "_id": "$_id",
                                "name": "$name",
                                "flag": "$flag",
                                "purpose": "$purpose",
                                "is_activated": "$is_activated",
                                "is_default": "$is_default",
                                "config_description": "$config_description",
                                "usage_description": "$usage_description",
                                "user_mfas": "$user_mfas"
                            }
                        },
                        "count": {"$sum": 1}
                    }
                },
                # Unwind to restore individual MFA documents
                {
                    "$unwind": "$mfas"
                },
                # Replace root to restore original structure
                {
                    "$replaceRoot": {
                        "newRoot": {
                            "$mergeObjects": [
                                "$mfas",
                                {
                                    "flag_group": "$_id",
                                    "group_count": "$count"
                                }
                            ]
                        }
                    }
                }
            ]
            

            # Initialize mfas as a list to store MFA documents
            mfas = []

            # Fetch default MFAs using aggregation
            default_mfas = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.REF_MFAS,
                all_data=True,
                output_data_type=OutputDataType.DATA_TABLE.value,
                pipeline=mfa_pipeline
            )

            # return default_mfas

            # Add default MFAs to the list
            DebugService.app_debug_print(f"[DEBUG] default_mfas type: {default_mfas}", False)
            DebugService.app_debug_print(f"[DEBUG] default_mfas value: {len(default_mfas)}", False)

            if isinstance(default_mfas, list):
                DebugService.app_debug_print(f"[DEBUG] default_mfas is a list with {len(default_mfas)} items", False)
                mfas.extend(default_mfas)
            elif default_mfas:  # If it's a dictionary or other non-None value
                DebugService.app_debug_print(f"[DEBUG] default_mfas is not a list, appending directly", False)
                mfas.append(default_mfas)

            # SET DEFAULT MFA
            # default_mfa = mfas[0] if len(mfas) > 0 else None

            DebugService.app_debug_print(f"mfas len: {len(mfas)}",False)  # Use curly braces for formatted strings

            # Use fetch_native_query_data_from_collection for user MFAs as well
            user_mfas = await self.generic_service.fetch_native_query_data_from_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    all_data=True,
                    output_data_type=OutputDataType.DATA_TABLE.value,
                    accept_language=accept_language,
                    native_query={
                        "is_configured": True,
                        "sys_user_id": ObjectId(user_object_id)
                    }
                )
            DebugService.app_debug_print(f"mfas user_mfas: {user_mfas}",False)
            # LOOP THROUGH user MFAs
            for element in user_mfas:
                mfa_id = extract_field_on_output_data_element(element,'ref_mfa_id',OutputDataType.DATA_TABLE.value)
                DebugService.app_debug_print(f"[DEBUG] Processing user MFA with id: {mfa_id}", False)

                if mfa_id:
                    document = await self.generic_service.fetch_native_query_one_from_collection(
                        collection_key=CollectionKey.REF_MFAS,
                        output_data_type=OutputDataType.DATA_TABLE.value,
                        native_query={"_id": ObjectId(mfa_id)}
                    )

                    DebugService.app_debug_print(f"[DEBUG] Fetched document type: {type(document)}", False)

                    if document:
                        mfas.append(document) 
            DebugService.app_debug_print(f"--user mfas >>>> : {len(mfas)}",False)
            return mfas

        except Exception as e:
            DebugService.app_debug_print(f"Error in mfa available : {e}",True)
            # Get translated message
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", accept_language)
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


    async def user_configured_mfa(self,sys_user_id:str,accept_language:str = DEFAULT_LANGUAGE)-> List[Dict[str, Any]]:
        try:
            # default_mfa = None
            # Use fetch_native_query_data_from_collection instead of fetch_data_from_collection
            mfas = await self.generic_service.fetch_native_query_data_from_collection(
                    collection_key=CollectionKey.REF_MFAS,
                    all_data=False,
                    output_data_type=OutputDataType.DATA_TABLE.value,
                    accept_language=accept_language,
                    native_query={"is_activated": True}
            )

            user_mfas = []
            for mfa in mfas:
                # print(f"loog : {mfa}")
                query = {
                    "filter__ref_mfa_id": mfa["id"]['display_value'],
                    "filter__sys_user_id": sys_user_id,
                    "filter__is_activated": True,
                }
                document = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    output_data_type=OutputDataType.DATA_TABLE.value,
                    query=query
                )
                flag = mfa.get('flag', {}).get('real_value')
                # print(f' -- {document}')
                if document:
                    yes_lbl = ResponseService.get_response_message(MessageCategory.COMMON, "YES_LABEL", accept_language)
                    config_lbl = ResponseService.get_response_message(MessageCategory.COMMON, "CONFIGURED_LABEL", accept_language)
                    real_value = True
                    if flag == MFaFlag.SYCAMORE_2FA_APP.value:
                        real_value = document.get('is_configured', {}).get('real_value')
                    user_mfas.append({
                        "is_configured": {
                            "display_value": f"{config_lbl} ?",
                            "display_value": yes_lbl,
                            "real_value":real_value,
                            "data_type": {
                                "is_boolean": True
                            },
                            "meta": {
                                "to_be_translated_in_front": False,
                                "missing_translation": False
                            }
                        },
                        **mfa
                    })
                else:
                    no_lbl = ResponseService.get_response_message(MessageCategory.COMMON, "NO_LABEL", accept_language)
                    config_lbl = ResponseService.get_response_message(MessageCategory.COMMON, "CONFIGURED_LABEL", accept_language)
                    user_mfas.append({
                        "is_configured": {
                            "display_value": f"{config_lbl} ?",
                            "display_value": no_lbl,
                            "real_value":False,
                            "data_type": {
                                "is_boolean": True
                            },
                            "meta": {
                                "to_be_translated_in_front": False,
                                "missing_translation": False
                            }
                        },
                        **mfa
                    })


            return user_mfas

        except Exception as e:
            print(f"Error : {e}")
            # Get translated message
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", accept_language)
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

    @staticmethod
    async def get_user_profil(request: Request,accept_language:str = 'fr') -> dict:
        user_profil = getattr(request.state, "userProfil", None)
        # app_debug_print(f" state {request.state.__dict__}",True)
        if not user_profil:
            DebugService.app_debug_print(f" NO user_profil",False)
            message = ResponseService.get_response_message(MessageCategory.COMMON, "USER_PROFIL_MISSING", accept_language)
            DebugService.app_debug_print(f" missing user_profil : {message}",False)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        return user_profil

    @staticmethod
    async def get_user_login_history(request: Request,accept_language:str = 'fr') -> dict:
        loginHistory = getattr(request.state, "loginHistory", None)

        if not loginHistory:
            DebugService.app_debug_print(f" NO loginHistory",False)
            message = ResponseService.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY", accept_language)
            raise HTTPException(status_code=404, detail=message)
        return loginHistory
    
    @staticmethod
    async def get_endpoint_url_from_request(request: Request,accept_language:str = 'fr') -> str:
        return request.url.path
    
    @staticmethod
    async def get_endpoint_from_db(request: Request,accept_language:str = 'fr') -> dict:
        from app.modules.core.models.rbac_endpoint.rbac_endpoint_model import RbacEndpointModel
        endpoint_url = await AuthenticatedService.get_endpoint_url_from_request(request,accept_language)
        endpoint = await RbacEndpointModel.find_one(RbacEndpointModel.url == endpoint_url).to_dict()
        # formated_endpoint = await generic_service.format_object(
        #     endpoint,
        #     OutputDataType.DEFAULT.value,
        #     accept_language,
        #     collection_key=CollectionKey.RBAC_ENDPOINT
        # )
        # endpoint = await generic_service.fetch_one_from_collection(
        #     collection_key=CollectionKey.RBAC_ENDPOINT,
        #     output_data_type=OutputDataType.DEFAULT.value,
        #     query={
        #         "filter__url": endpoint_url
        #     }
        # )
        return endpoint

    @staticmethod
    async def get_user_info(request: Request,accept_language:str = 'fr') -> dict:
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.auth.services.token.token_service import TokenService
        generic_service = GenericService(accept_language)
        user_details = getattr(request.state, "user", None)
        loginHistory = getattr(request.state, "loginHistory", None)
        device_info = getattr(request.state, "deviceInfo", None)
        ip_address = getattr(request.state, "ipAddress", None)
        location_info = getattr(request.state, "locationInfo", None)
        device_hashed_id = getattr(request.state, "deviceHashedId", None)

        saas_config_info  = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            }
        )
        
        if not saas_config_info:
            message = ResponseService.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        support_email = await AuthenticatedService(accept_language=accept_language).get_system_support_email(saas_config_info,accept_language)

        DebugService.app_debug_print(f"\n\n\n user_details >><> {user_details} \n\n\n",False)
        if not user_details:
            DebugService.app_debug_print(f"\n\n\n NO user_details request.headers {request.headers} \n\n\n",True)
            DebugService.app_debug_print(f"\n\n\n NO user_details {user_details} \n\n\n",False)

            # TODO: TRY TO GET BEARER TOKEN AND FIND USER
            authorization = request.headers.get("authorization")
            if authorization and authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]
                DebugService.app_debug_print(f"\n\n\n token {token} \n\n\n",False)
                decoded_token = TokenService(accept_language=accept_language).decode_and_verify_token(
                    token=token,
                    expected_type=EJWTTokenType.LOGIN,
                    by_pass_exception=True
                )
                DebugService.app_debug_print(f"\n\n\n decoded_token {decoded_token} \n\n\n",False)
                if decoded_token:
                    user_details = await generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.SYS_USER,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___id": decoded_token["sub"]},
                    )
                    DebugService.app_debug_print(f"\n\n\n user_details from token {user_details} \n\n\n",False)
                    if user_details is None:
                        message = ResponseService.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", accept_language)
                        raise HTTPException(status_code=404, detail=message)
                    login_history_query = {
                        "filter__sys_user_id": user_details['id'],
                        "filter__status": ELoginStatus.LOGGED_IN.value,
                        "filter__device_id_str":device_hashed_id
                    }
                    loginHistory = await generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query=login_history_query,
                        sort={"created_at": -1}
                    )

                    # Fallback: retry WITHOUT device_id_str filter
                    if not loginHistory and device_hashed_id:
                        DebugService.app_debug_print(
                            f"\n\n\n [get_user_info/token_path] No login history found for user {user_details['id']} "
                            f"with device_hashed_id={device_hashed_id}. Trying fallback... \n\n\n", True
                        )
                        fallback_query = {
                            "filter__sys_user_id": user_details['id'],
                            "filter__status": ELoginStatus.LOGGED_IN.value,
                        }
                        loginHistory = await generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query=fallback_query,
                            sort={"created_at": -1}
                        )
                        if loginHistory:
                            DebugService.app_debug_print(
                                f"\n\n\n [get_user_info/token_path] Fallback found login history! "
                                f"db_device_id_str={loginHistory.get('device_id_str')} \n\n\n", True
                            )

                    # Check if loginHistory was found in database
                    if not loginHistory:
                        DebugService.app_debug_print(f"\n\n\n No login history found in database for user {user_details['id']} with status LOGGED_IN \n\n\n", True)
                        message = ResponseService.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY", accept_language)
                        raise HTTPException(status_code=404, detail=message)

                else :
                    message = ResponseService.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", accept_language)
                    raise HTTPException(status_code=404, detail=message)
            else :
                message = ResponseService.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", accept_language)
                raise HTTPException(status_code=404, detail=message)
        DebugService.app_debug_print(f"\n\n\n user_details all infogs > >  {user_details} \n\n\n",False)

        # get device device_hashed_id
        user_device_info = await AuthenticatedService.get_device_info_from_db(request=request,sys_user_id=user_details['id'])
        
        if user_details['account_status'] not in [AccountStatusFlag.ACTIVE,AccountStatusFlag.INACTIVE]:
            DebugService.app_debug_print(f" \n\n\n USER ACCOUNT BAD STATUS {user_details} \n\n\n",False)
            if user_details['account_status'] in [AccountStatusFlag.LOCKED,AccountStatusFlag.LOCKED_BY_SYSTEM]:
                message = ResponseService.get_response_message(MessageCategory.LOGIN, "ACCOUNT_LOCKED", accept_language)
                token = TokenService(accept_language=accept_language).create_access_token(
                    data={"sub": str(user_device_info['id']), "device_id_str":device_hashed_id, "type":EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS},
                    token_type=EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS,
                    expires_delta=timedelta(minutes=20)  # Expires after 20 minutes 400
                )
                # Initialize token expiration variables
                token_expiry_duration = timedelta(minutes=20)
                token_expires_at = datetime.now(timezone.utc) + token_expiry_duration
                token_expires_in = token_expiry_duration.total_seconds()
                raise CustomJSONResponseException(
                    CustomJSONResponse(
                        status_code=status.HTTP_423_LOCKED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_account_related_issue":True,
                            "token":token,
                            "expires_in":token_expires_in,
                            "expires_at":token_expires_at,
                        }
                    )
                )
            # RETURN 401
            message = ResponseService.get_response_message(MessageCategory.LOGIN, "ACCOUNT_NOT_ACTIVE", accept_language)
            token = TokenService(accept_language=accept_language).create_access_token(
                data={"sub": str(user_device_info['id']), "device_id_str":device_hashed_id, "type":EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS},
                token_type=EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS,
                expires_delta=timedelta(minutes=20)  # Expires after 20 minutes 400
            )
            # Initialize token expiration variables
            token_expiry_duration = timedelta(minutes=20)
            token_expires_at = datetime.now(timezone.utc) + token_expiry_duration
            token_expires_in = token_expiry_duration.total_seconds()
            raise CustomJSONResponseException(
                CustomJSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "message":message,
                        "support_email":support_email,
                        "is_account_related_issue":True,
                        "token":token,
                        "expires_in":token_expires_in,
                        "expires_at":token_expires_at,
                    }
                )
            )

        elif user_details['account_status'] == AccountStatusFlag.INACTIVE:
            message = ResponseService.get_response_message(MessageCategory.LOGIN, "ACCOUNT_NOT_ACTIVE", accept_language)
            token = TokenService(accept_language=accept_language).create_access_token(
                data={"sub": str(user_details['id']), "device_id_str":device_hashed_id, "type":EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS},
                token_type=EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS,
                expires_delta=timedelta(minutes=20)  # Expires after 20 minutes 400
            )
            # Initialize token expiration variables
            token_expiry_duration = timedelta(minutes=20)
            token_expires_at = datetime.now(timezone.utc) + token_expiry_duration
            token_expires_in = token_expiry_duration.total_seconds()
            raise CustomJSONResponseException(
                CustomJSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "message":message,
                        "support_email":support_email,
                        "is_account_related_issue":True,
                        "token":token,
                        "expires_in":token_expires_in,
                        "expires_at":token_expires_at,
                    }
                )
            )
        
       
        # filter by user id
        if user_device_info:
            user_device_info = user_device_info
        else:
            # exception
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "MISSING_USER_DEVICE", accept_language)
            token = TokenService(accept_language=accept_language).create_access_token(
                data={"sub": str(user_details['id']), "device_id_str":device_hashed_id, "type":EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS},
                token_type=EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS,
                expires_delta=timedelta(minutes=20)  # Expires after 20 minutes 400
            )
            # Initialize token expiration variables
            token_expiry_duration = timedelta(minutes=20)
            token_expires_at = datetime.now(timezone.utc) + token_expiry_duration
            token_expires_in = token_expiry_duration.total_seconds()
            raise CustomJSONResponseException(
                CustomJSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "message":message,
                        "support_email":support_email,
                        "is_device_related_issue":True,
                        "token":token,
                        "expires_in":token_expires_in,
                        "expires_at":token_expires_at,
                    }
                )
            )
        # print(f'\n\n\n user_device_info : {user_device_info}')
        # print(f'\n\n\n loginHistory (((((()))))): {loginHistory}')
        # if not user_device_info:
        #     message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "MISSING_USER_DEVICE", accept_language)
        #     raise HTTPException(status_code=404, detail=message)
        
        # CHECK IF LOGIN HISTORY HASH DEVICE ID IS != TO ACTUAL ONE
        # DebugService.app_debug_print(f"\n\n\n cfg_user_device_id : {str(loginHistory['device_id_str'])} \n\n\n",True)
        # DebugService.app_debug_print(f"\n\n\n user_device_info : {str(user_device_info)} \n\n\n",True)
        # if user_device_info is not None and str(loginHistory['device_id_str']) != str(user_device_info['device_id_str']):
        #     message = ResponseService.get_response_message(MessageCategory.LOGIN, "DEVICE_CHANGED", accept_language)
        #     raise CustomJSONResponse(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         content={
        #             "message":message,
        #             "support_email":support_email,
        #             "is_device_related_issue":True
        #         }
        #     ) 

        # debug
        DebugService.app_debug_print(f"\n\n\n user_device_info : {user_device_info} \n\n\n",False)
        device_id_str = None
        if user_device_info and 'device_id_str' in user_device_info:
            device_id_str = user_device_info['device_id_str']
        # Check if loginHistory exists before accessing it
        if not loginHistory:
            DebugService.app_debug_print(
                f"\n\n\n [get_user_info] No loginHistory from middleware for user {user_details.get('id', 'unknown')}. "
                f"device_id_str={device_id_str}, device_hashed_id={device_hashed_id} \n\n\n", True
            )
            # First attempt: strict query with device_id_str
            login_history_query = {
                "filter__sys_user_id": user_details['id'],
                "filter__status": ELoginStatus.LOGGED_IN.value,
                "filter__device_id_str": device_id_str 
            }
            loginHistory = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                output_data_type=OutputDataType.DEFAULT.value,
                query=login_history_query,
                sort={"created_at": -1}
            )
            # Fallback: retry WITHOUT device_id_str filter
            if not loginHistory and device_id_str:
                DebugService.app_debug_print(
                    f"\n\n\n [get_user_info] Strict query failed for user {user_details.get('id', 'unknown')}. "
                    f"Trying fallback without device_id_str... \n\n\n", True
                )
                fallback_query = {
                    "filter__sys_user_id": user_details['id'],
                    "filter__status": ELoginStatus.LOGGED_IN.value,
                }
                loginHistory = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query=fallback_query,
                    sort={"created_at": -1}
                )
                if loginHistory:
                    DebugService.app_debug_print(
                        f"\n\n\n [get_user_info] LOGIN HISTORY FOUND via fallback! "
                        f"login_history_id={loginHistory.get('id')}, "
                        f"db_device_id_str={loginHistory.get('device_id_str')}, "
                        f"queried_device_id_str={device_id_str} \n\n\n", True
                    )
            if not loginHistory:
                DebugService.app_debug_print(
                    f"\n\n\n [get_user_info] No loginHistory found at all for user {user_details.get('id', 'unknown')} \n\n\n", True
                )
                message = ResponseService.get_response_message(MessageCategory.LOGIN, "MISSING_LOGIN_HISTORY", accept_language)
                raise HTTPException(status_code=404, detail=message)

        # UPDATE LAST ACTIVITY
        await generic_service.update_data_in_collection(
            collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
            item_id=loginHistory['id'],
            data={"last_activity":datetime.now(timezone.utc)}
        )

        # CHECK DAILY ACTIVITY OR UPSERT
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=2)
        
        daily_activity_query = {
            "sys_user_id":user_details['id'],
            # "device_info":device_info,
            "ip_address":ip_address,
            # "location_info":location_info,
            "ops_user_login_history_id":loginHistory['id'],
            "created_at": {"$gte": start_of_day, "$lt": end_of_day}  # Date range for today
        }
        # daily_activity = await generic_service.fetch_one_from_collection(
        #     collection_key=CollectionKey.OPS_USER_LOGIN_DAILY_ACTIVITY,
        #     output_data_type=OutputDataType.DEFAULT.value,
        #     query=daily_activity_query,
        #     sort={"created_at": -1}
        # )
        # if not daily_activity:
        # debug
        DebugService.app_debug_print(f"\n\n\n daily_activity_query : {daily_activity_query} \n\n\n",False)
        await generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.OPS_USER_LOGIN_DAILY_ACTIVITY,
            filter_data=daily_activity_query,
            update_data={
                "sys_user_id":user_details['id'],
                "device_info":device_info,
                "ip_address":ip_address,
                "location_info":location_info,
                "ops_user_login_history_id":loginHistory['id'],
            }
        )

        # Attach RLS context resolved by RowLevelSecurityMiddleware (once per request)
        rls_context = getattr(request.state, "rls_context", None)
        if rls_context is not None:
            user_details["_rls_context"] = rls_context

        return user_details


    @staticmethod
    async def get_optional_user_info(request: Request,accept_language:str = 'fr') -> Optional[Any]:
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.auth.services.token.token_service import TokenService
        generic_service = GenericService(accept_language)
        user_details = getattr(request.state, "user", None)
        loginHistory = getattr(request.state, "loginHistory", None)
        device_info = getattr(request.state, "deviceInfo", None)
        ip_address = getattr(request.state, "ipAddress", None)
        location_info = getattr(request.state, "locationInfo", None)
        device_hashed_id = getattr(request.state, "deviceHashedId", None)

        saas_config_info  = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            }
        )
        
        if not saas_config_info:
            return None
        support_email = await AuthenticatedService(accept_language=accept_language).get_system_support_email(saas_config_info,accept_language)

        DebugService.app_debug_print(f"\n\n\n user_details >><> {user_details} \n\n\n",False)
        if not user_details:
            DebugService.app_debug_print(f"\n\n\n NO user_details request.headers {request.headers} \n\n\n",False)
            DebugService.app_debug_print(f"\n\n\n NO user_details {user_details} \n\n\n",False)

            # TODO: TRY TO GET BEARER TOKEN AND FIND USER
            authorization = request.headers.get("authorization")
            if authorization and authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]
                DebugService.app_debug_print(f"\n\n\n token {token} \n\n\n",False)
                decoded_token = TokenService(accept_language=accept_language).decode_and_verify_token(
                    token=token,
                    expected_type=EJWTTokenType.LOGIN,
                    by_pass_exception=True
                )
                DebugService.app_debug_print(f"\n\n\n decoded_token {decoded_token} \n\n\n",False)
                if decoded_token:
                    user_details = await generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.SYS_USER,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___id": decoded_token["sub"]},
                    )
                    DebugService.app_debug_print(f"\n\n\n user_details from token {user_details} \n\n\n",False)
                    if user_details is None:
                        return None
                    login_history_query = {
                        "filter__sys_user_id": user_details['id'],
                        "filter__status": ELoginStatus.LOGGED_IN.value,
                        "filter__device_id_str":device_hashed_id
                    }
                    loginHistory = await generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query=login_history_query,
                        sort={"created_at": -1}
                    )

                    # Check if loginHistory was found in database
                    if not loginHistory:
                        DebugService.app_debug_print(f"\n\n\n No login history found in database for user {user_details['id']} with status LOGGED_IN \n\n\n", False)
                        return None

                else :
                    return None
            else :
                return None
        DebugService.app_debug_print(f"\n\n\n user_details all infogs > >  {user_details} \n\n\n",False)

        if user_details['account_status'] not in [AccountStatusFlag.ACTIVE,AccountStatusFlag.INACTIVE]:
            return None

        elif user_details['account_status'] == AccountStatusFlag.INACTIVE:
            return None
        
        # get device device_hashed_id
        user_device_info = None
        list_of_user_devices = getattr(request.state, "listOfUserDevices", [])
        # DebugService.app_debug_print(f"\n\n\n list_of_user_devices : {list_of_user_devices} \n\n\n",True)
        DebugService.app_debug_print(f"\n\n\n list_of_user_devices ln : {len(list_of_user_devices)} \n\n\n",False)
        
        # filter by user id
        filtered_user_device_info = list(filter(lambda x: str(x['sys_user_id']) == str(user_details['id']) and device_hashed_id == str(x['device_id_str']), list_of_user_devices))
        DebugService.app_debug_print(f"\n\n\n filtered_user_device_info : {filtered_user_device_info} \n\n\n",False)
        if len(filtered_user_device_info) > 0 :
            user_device_info = filtered_user_device_info[0]
            # DebugService.app_debug_print(f"\n\n\n user_device_info ln : {len(list_of_user_devices)} \n\n\n",True)

        else:
            # exception
            return None 
        DebugService.app_debug_print(f"\n\n\n user_device_info : {user_device_info} \n\n\n",False)

        # Check if loginHistory exists before accessing it
        if not loginHistory:
            DebugService.app_debug_print(f"\n\n\n No loginHistory found for user {user_details.get('id', 'unknown')} \n\n\n", False)
            return None

        # UPDATE LAST ACTIVITY
        await generic_service.update_data_in_collection(
            collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
            item_id=loginHistory['id'],
            data={"last_activity":datetime.now(timezone.utc)}
        )

        # CHECK DAILY ACTIVITY OR UPSERT
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=2)
        
        daily_activity_query = {
            "sys_user_id":user_details['id'],
            # "device_info":device_info,
            "ip_address":ip_address,
            # "location_info":location_info,
            "ops_user_login_history_id":loginHistory['id'],
            "created_at": {"$gte": start_of_day, "$lt": end_of_day}  # Date range for today
        }
        # daily_activity = await generic_service.fetch_one_from_collection(
        #     collection_key=CollectionKey.OPS_USER_LOGIN_DAILY_ACTIVITY,
        #     output_data_type=OutputDataType.DEFAULT.value,
        #     query=daily_activity_query,
        #     sort={"created_at": -1}
        # )
        # if not daily_activity:
        # debug
        DebugService.app_debug_print(f"\n\n\n daily_activity_query : {daily_activity_query} \n\n\n",False)
        await generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.OPS_USER_LOGIN_DAILY_ACTIVITY,
            filter_data=daily_activity_query,
            update_data={
                "sys_user_id":user_details['id'],
                "device_info":device_info,
                "ip_address":ip_address,
                "location_info":location_info,
                "ops_user_login_history_id":loginHistory['id'],
            }
        )

        # Attach RLS context resolved by RowLevelSecurityMiddleware (once per request)
        rls_context = getattr(request.state, "rls_context", None)
        if rls_context is not None:
            user_details["_rls_context"] = rls_context

        return user_details

    
    @staticmethod
    async def get_user_info_from_unsecured_path(request: Request,accept_language:str = 'fr',expected_type:EJWTTokenType = EJWTTokenType.LOGIN) -> dict:
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.auth.services.token.token_service import TokenService
        generic_service = GenericService(accept_language)
        user_details = getattr(request.state, "user", None)
        DebugService.app_debug_print(f"\n\n\n user_details {user_details} \n\n\n",False)

        if not user_details:
            # try to get bearer token and fetch user info
            authorization = request.headers.get("authorization")
            DebugService.app_debug_print(f"\n\n\n authorization >> {authorization} \n\n\n",False)
            if authorization and authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]
                DebugService.app_debug_print(f"\n\n\n token >> {token} \n\n\n",False)
                decoded_token = TokenService(accept_language=accept_language).decode_and_verify_token(
                    token=token,
                    expected_type=expected_type,
                    by_pass_exception=True
                )
                DebugService.app_debug_print(f"\n\n\n decoded_token >> {decoded_token} \n\n\n",False)
                if decoded_token:
                    user_details = await generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.SYS_USER,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___id": decoded_token["sub"]},
                    )

        # Check if user_details is None or doesn't have required 'id' field
        if not user_details or not isinstance(user_details, dict) or 'id' not in user_details:
            DebugService.app_debug_print(f"\n\n\n NO user_details or missing id field: {user_details} \n\n\n",False)
            message = ResponseService.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", accept_language)
            raise HTTPException(status_code=404, detail=message)

        DebugService.app_debug_print(f"\n\n\n user_details all infogs > >  {user_details['id']} \n\n\n",False)

        saas_config_info  = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            }
        )
        
        if not saas_config_info:
            message = ResponseService.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        support_email = await AuthenticatedService(accept_language=accept_language).get_system_support_email(saas_config_info,accept_language)

        # Additional safety check for account_status field
        if 'account_status' not in user_details:
            DebugService.app_debug_print(f"\n\n\n Missing account_status field in user_details: {user_details} \n\n\n",False)
            message = ResponseService.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", accept_language)
            raise HTTPException(status_code=404, detail=message)

        if user_details['account_status'] not in [AccountStatusFlag.ACTIVE,AccountStatusFlag.INACTIVE]:
            DebugService.app_debug_print(f" \n\n\n USER ACCOUNT BAD STATUS {user_details} \n\n\n",False)
            if user_details['account_status'] in [AccountStatusFlag.LOCKED,AccountStatusFlag.LOCKED_BY_SYSTEM]:
                message = ResponseService.get_response_message(MessageCategory.LOGIN, "ACCOUNT_LOCKED", accept_language)
                raise CustomJSONResponseException(
                    CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_account_related_issue":True
                        }
                    )
                ) 
            # RETURN 401
            message = ResponseService.get_response_message(MessageCategory.LOGIN, "ACCOUNT_NOT_ACTIVE", accept_language)
            raise CustomJSONResponseException(
                    CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_account_related_issue":True
                        }
                    )
                )
        
        elif user_details['account_status'] == AccountStatusFlag.INACTIVE:
            message = ResponseService.get_response_message(MessageCategory.LOGIN, "ACCOUNT_NOT_ACTIVE", accept_language)
            raise CustomJSONResponseException(
                    CustomJSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "message":message,
                            "support_email":support_email,
                            "is_account_related_issue":True
                        }
                    )
                )

        # Attach RLS context resolved by RowLevelSecurityMiddleware (once per request)
        rls_context = getattr(request.state, "rls_context", None)
        if rls_context is not None:
            user_details["_rls_context"] = rls_context

        return user_details

    @staticmethod
    async def get_api_consumer(request: Request,accept_language:str = 'fr') -> dict:
        api_Consumer = getattr(request.state, "apiConsumer", None)
        if not api_Consumer:
            DebugService.app_debug_print(f"\n\n\n NO api_Consumer \n\n\n",False)
            message = ResponseService.get_response_message(MessageCategory.COMMON, "CONSUMER_KEY_MISSING", accept_language)
            DebugService.app_debug_print(f" missing api_Consumer ---- : {message}",False)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        return api_Consumer

    @staticmethod
    async def get_location_from_ip_secure(request: Request,accept_language:str = 'fr') -> dict:
        locationInfo = getattr(request.state, "locationInfo", None)
        return locationInfo

    @staticmethod
    async def get_optional_api_address(request: Request,accept_language:str = 'fr') -> Optional[Any]:
        ip_address = getattr(request.state, "ipAddress", None)
        return ip_address
    @staticmethod
    def get_optional_device_hashed_id(request: Request,accept_language:str = 'fr') -> Optional[Any]:
        device_hashed_id = getattr(request.state, "deviceHashedId", None)
        return device_hashed_id

    @staticmethod
    async def get_optional_device_info(request: Request,accept_language:str = 'fr') -> Optional[Any]:
        device_info = getattr(request.state, "deviceInfo", None)
        return device_info

    async def get_system_support_email(self, saas_config_info:Any,accept_language:str = 'fr') -> str:
        if not saas_config_info:
            message = ResponseService.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )

        contact_info = saas_config_info.get('contact_info', {})
        if not contact_info:
            DebugService.app_debug_print("No customer support email found.")
            message = ResponseService.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", accept_language)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,  # Use 404 for missing resources
                detail=message
            )

        # Filtered result
        filtered_support_email_info = [
            info for info in contact_info
            if info['purpose'] == ESaasConfigPurpose.CUSTOMER_SUPPORT.value and info['info_kind'] == ESaasConfigInfoKind.EMAIL_ADDRESS.value
        ]
        # Accessing the first match (if exists)
        if len(filtered_support_email_info) > 0:
            support_email = filtered_support_email_info[0]['contact_info']
            DebugService.app_debug_print(f"Customer support email: {support_email}")
            return support_email  # Return the first matching email address found in the system configuration information
        else:
            DebugService.app_debug_print("No customer support email found.")
            message = ResponseService.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", accept_language)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,  # Use 404 for missing resources
                detail=message
            )




