

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from app.modules.auth.models.ops_user_login_history.ops_user_login_history_model import OpsUserLoginHistoryModel
from bson import ObjectId
from fastapi import Body, HTTPException, Header, Query, Request,status
from pydantic import ValidationError
from app.modules.auth.enums.auth import ELoginStatus
from app.modules.auth.enums.common import MessageCategory
from app.modules.core.types.response import CustomJSONResponse
from app.modules.core.types.saas import ESaasConfigInfoKind, ESaasConfigPurpose
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.auth.schemas.auth_schema import NewPasswordResetRequest, PasswordResetRequest
from app.modules.core.schemas.user_schema import UserConfigPayload, UserConfigsPayload, UserCreate
from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService

from app.modules.auth.services.password.password_service import PasswordService
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.device.device_service import DeviceService
from app.modules.core.services.generator.generator_service import GeneratorService
from app.modules.core.services.hash.hash_service import HashService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.services.sms.sms_service import SmsService
from app.modules.core.enums.type_enum import AccountStatusFlag, EJWTTokenType, ERegistrationOrigin, EUserThemeMode, FormatedOutPut, OutputDataType
from app.modules.core.services.email_sender.email_sender_service import EMailSenderService
from app.modules.core.services.encryption.encryption_service import EncryptionService
from app.modules.core.services.model.model_service import ModelService
from app.modules.auth.models.cfg_user_device.cfg_user_device_model import CfgUserDeviceModel
from app.modules.core.models.cfg_saas_config.cfg_saas_config_model import CfgSaasConfigModel
from app.modules.core.models.sys_user.sys_user_model import SysUserModel
from app.modules.core.models.ntf_notification.ntf_notification_model import NtfNotificationModel
from app.modules.core.utils.helpers.line_helper import format_exception
from app.modules.core.enums.profiles_enum import ESysProfileFlag
from app.modules.auth.enums.mfa import MFaFlag

class UserController(
    AuthenticatedService,
    EncryptionService,
    DebugService,
    PasswordService,
    ResponseService,
    ConverterService,
    ModelService,
    SmsService,
    EMailSenderService,
    DeviceService):
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.auth.services.token.token_service import TokenService
        from app.modules.auth.services.login.login_service import LoginService
        
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        self.token_service = TokenService(accept_language)
        self.login_service = LoginService(accept_language)
        super().__init__(accept_language)

    
    async def submit_new_password(
        self,
        request: Request, 
        payload:NewPasswordResetRequest,
        accept_language: str = Header(default=DEFAULT_LANGUAGE), 
    ):
        try: 
            # CHECK API CONSUMER EXISTANCE
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            
            # GET HASHED DEVICE ID
            device_hashed_id = await HashService.get_hashed_device_id(request) 
            
            # GET IP ADDRESS
            ip_address = self.get_real_ip_address(request)
            
            # DECODE USER HEADER TOKEN
            decoded_header_token = await self.token_service.get_decoded_header_token(request=request, expected_type=EJWTTokenType.PASSWORD_RESET_PROCESS, accept_language=accept_language)
            
            # DEVICE CHECKING  
            user_device_info:CfgUserDeviceModel = await self.device_info_from_hashed_id(device_hashed_id=device_hashed_id)
            
            saas_config_info:CfgSaasConfigModel  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                }
            )
            # print(f"\n\n saas_config_info : {saas_config_info}")
            
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            authenticationService = AuthenticatedService()
            support_email = await  authenticationService.get_system_support_email(saas_config_info,accept_language) 
            
                
            if not user_device_info: 
                message = self.get_response_message(MessageCategory.COMMON, "NO_EXISTING_USER_DEVICE", accept_language,email=support_email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
                
            # Get current time in UTC
            now = datetime.now(timezone.utc) 
            end_of_validity = now - timedelta(minutes=30)
            
            passw_reset_history_query = {
                "filter___id":decoded_header_token['sub'],
                "filter__status":ELoginStatus.RESET_PASSWORD_PROCESS_VALIDATED.value,
                "filter__created_at": {"$gte": end_of_validity}
            }
            # print(f"passw_reset_history_query :  {passw_reset_history_query}")
            
            resetPasswHistory = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                output_data_type=OutputDataType.DEFAULT.value,
                query=passw_reset_history_query,
                sort={"created_at": -1}
            )
            print(f"resetPasswHistory :  {resetPasswHistory}")
            
            if not resetPasswHistory:
                message = self.get_response_message(MessageCategory.PASSWORD_RESET, "MISSING_PASSWORD_RESET_HISTORY", accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            user = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter___id":resetPasswHistory['sys_user_id']
                },
                sort={"created_at": -1}
            )
            if not user:
                message = self.get_response_message(MessageCategory.PASSWORD_RESET, "INVALID_CREDENTIALS", accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            
            user_details = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": user['id']}
            )
            
            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", accept_language)
                raise HTTPException(status_code=404, detail=message) 
            
            # CHECK PASSWORD EQUALITY
            if payload.password != payload.repeted_password:
                message = self.get_response_message(MessageCategory.LOGIN, "OLD_AND_NEW_PASSWORD_NOT_MATCH", accept_language)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
            
            new_password = self.hash_password(payload.password)
            
            # CHECK NEW PASSWORD EQUALITY TO OLD ONE
            if new_password == user['password']:
                message = self.get_response_message(MessageCategory.PASSWORD_RESET, "NEW_PASSWOR_MUST_BE_OTHER_THEN_OLD", accept_language)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
            
            h_data = {
                "password":f"{new_password}"
            }
            print(f"\n\n h_data :  {h_data}\n\n")
            # UPDATE OTP ON LOGIN HISTORY 
            update_new_password = await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.SYS_USER,
                item_id=user['id'],
                data=h_data
            )
            
            if update_new_password == True:
                h_data = {
                    "status":ELoginStatus.RESET_PASSWORD_PROCESS_COMPLETED.value,
                }
                updated = await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                    item_id=resetPasswHistory['id'],
                    data=h_data
                )
                print(f"\n\n new updated reset pass history :  {updated}\n\n")
                
                # ADD NOTIFICATIONS
                
                # Filtered result
                filtered_support_email_info = [
                    info for info in saas_config_info['contact_info']
                    if info['purpose'] == ESaasConfigPurpose.CUSTOMER_SUPPORT.value and info['info_kind'] == ESaasConfigInfoKind.EMAIL_ADDRESS.value
                ]

                # Accessing the first match (if exists) 
                if filtered_support_email_info:
                    support_email = filtered_support_email_info[0]['contact_info']
                    print(f"Customer support email: {support_email}")
                else:
                    print("No customer support email found.")
                    message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", accept_language,)
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=message
                    )
                
                detail = user_device_info.get('user_agent')
                consideration = self.get_response_message(MessageCategory.COMMON, "ACTION_NO_IDENTIFIED", accept_language,email=support_email)
                title = self.get_response_message(MessageCategory.PASSWORD_RESET, "SUCCESS_PASSWORD_INIT_PROCESS_TITLE", accept_language)
                notification = self.get_response_message(MessageCategory.COMMON, "SELF_PASSWORD_UPDATE_SUCCEFULLY", accept_language,details=f"ip_address : {ip_address} \n info : {detail}")
                notification_data = {
                    "targeted_id":user['id'],
                    "title":title,
                    "notification":f"{notification} \n {consideration}"
                }
                not_saved = await self.generic_service.add_data_to_collection(CollectionKey.NTF_NOTIFICATION, notification_data, user=user_details, request=request)
                
                # SEND EMAIL ALERT
                mail_service = EMailSenderService()
                self.sending_translated_email(
                    email_to=user['email'],
                    subject=f"{title}", 
                    mail_title_translated=title,
                    mail_message_translated=notification,
                    second_mail_message_translated=f"ip_address : {ip_address} \n {user_device_info}",
                    mail_note_translated=f"{consideration}",
                    accept_language=accept_language
                )
                
                message = self.get_response_message(MessageCategory.COMMON, "PASSWORD_UPDATE_SUCCEFULLY", accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":message
                    }
                )
            else :
                message = self.get_response_message(MessageCategory.COMMON, "PASSWORD_UPDATE_FAILS", accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code":status.HTTP_200_OK,
                        "message":message
                    }
                ) 
        except Exception as e:
            print(f"Error CHECKING PASSWORD PROCESS TOKEN: {e}")
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", accept_language)
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
    
    async def add_new_user(self,request: Request, body: dict = Body(...)):
        """
        Endpoint to add a new document to the specified collection.
        """
        try: 
            # Validate the incoming data with context
            user_data = UserCreate.model_validate(body, context={"language": self.accept_language})
            self.app_debug_print(f"\n\n user body : {user_data}\n\n",True)
            # DECODE USER TOKEN 
            user_details = getattr(request.state, "user", None)
            # Validate the input data using the UserCreate model
            # user = UserCreate(**user_data)
        
            admin_user = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type = OutputDataType.DEFAULT,
                query={
                    "filter__username":str(user_data.username).strip()
                },
                user=user_details,
            ) 
            
            generated_password:str = user_data.password
            if user_data.is_auto_password_selected:
                generated_password = GeneratorService.strong_password_generator(10)
            generated_passwords = GeneratorService.strong_password_generator(10)
            self.app_debug_print(f"\n\n generated_passwords : {generated_passwords}\n\n",True)
            
            if admin_user:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "USER_NAME_ALREADY_TAKEN", self.accept_language,username=user_data.username)
                raise HTTPException(status_code=401, detail=message)
            #format phone numbers
            phone_numbers = []
            for phone in user_data.telephones:
                phone_numbers.append({
                    'phone_number':phone
                })
            emails = []
            for email in user_data.emails:
                emails.append({
                    "email":email
                })
            self.app_debug_print(f"\n\n generated_passwords : {generated_passwords}\n\n",True)
            
            user_data_to_save = {
                "username":user_data.username,
                "account_status":AccountStatusFlag.ACTIVE.value,
                "password":self.hash_password(generated_password),
                "sys_organization_id":user_details['sys_organization_id'],
                "email":emails[0]['email'],
                "phone_number":phone_numbers[0]['phone_number'],
                "gender":user_data.gender,
                "first_name":user_data.first_name,
                "last_name":user_data.last_name,
                "rbac_role_id":user_data.rbac_role_id,
                "phone_numbers":phone_numbers,
                "emails":emails,
                "others":user_data.others,
                "birth_day":user_data.birth_day,
                "birth_city":user_data.birth_city,
                
            }
            # Add data to the collection
            item_id = await self.generic_service.add_data_to_collection(CollectionKey.SYS_USER, user_data_to_save, user=user_details, request=request)
            ref_totp_mfa = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_MFAS,
                output_data_type=OutputDataType.DEFAULT,
                query={
                    "filter__flag": MFaFlag.SYCAMORE_2FA_APP.value
                },
                user=user_details,
            )
            if ref_totp_mfa:
                check_existing_cfg_user_mfa = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    output_data_type=OutputDataType.DEFAULT,
                    query={
                        "filter__sys_user_id": item_id,
                        "filter__ref_mfa_id": ref_totp_mfa['id']
                    },
                    user=user_details,
                )
                if not check_existing_cfg_user_mfa:
                    await self.generic_service.add_data_to_collection(
                        collection_key=CollectionKey.CFG_USER_MFA,
                        data={
                            "sys_user_id": item_id,
                            "ref_mfa_id": ref_totp_mfa['id'],
                            "is_configured": False,
                            "mfa_configuration_next_setup_at": datetime.now(),
                            "is_activated": True,
                        },
                        user=user_details, request=request,
                    )
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language,username=user_data.username)
            return CustomJSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "status_code": status.HTTP_201_CREATED,
                        "message": message,
                        "data":item_id
                    }
                )
            
        except ValidationError as e:
            # Extract error messages and format them into a single line
            errors = e.errors()
            error_messages = []
            for error in errors:
                field = ".".join(map(str, error["loc"]))  # Get the field name (e.g., "body.password")
                msg = error.get("msg", "Invalid value")  # Get the error message
                error_messages.append(f"{field}: {msg}")
            
            # Join all error messages into a single line
            raise HTTPException(status_code=400, detail="; ".join(error_messages))
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    

    async def fetch_user_data(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language) 
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            
            # ADD STATIC FILTER
            raw_query_params = {
                **raw_query_params,
                "filter__sys_organization_id": user_details['sys_organization_id']
            }
            
            
            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            
            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.SYS_USER,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    **query_params
                },
                user=user_details,
            )
            self.app_debug_print(f"Query data: {len(data)}",False)
            extra_data = {}
            formatted_data = []
            for element in data:
                user_instance = ModelService.convert_to_model_instance(SysUserModel,element)
                user = await  user_instance.get_formated_data(self.accept_language)
                formatted_data.append(user)

            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.SYS_USER,
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

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": formatted_data,
                    **extra_data
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch_data: > 4 {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
    
    async def search_users_data(
        self,
        request: Request,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language) 
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            search_key= raw_query_params.get('search_key','')
            # ADD STATIC FILTER
            query_params = {
                # **raw_query_params,
                "$or":[
                    {
                        "sys_organization_id": ObjectId(user_details['sys_organization_id']),
                        "first_name": { '$regex': f'{search_key}', '$options': "i" }
                    },
                    {
                        "sys_organization_id": ObjectId(user_details['sys_organization_id']),
                        "last_name": { '$regex': f'{search_key}', '$options': "i" }
                    },
                    {
                        "sys_organization_id": ObjectId(user_details['sys_organization_id']),
                        "sur_name": { '$regex': f'{search_key}', '$options': "i" }
                    },
                ]
            }
            
            
            # query_params = convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            
            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_native_query_data_from_collection(
                collection_key=CollectionKey.SYS_USER,
                all_data=all_data,
                page=page,
                limit=limit,
                accept_language=self.accept_language,
                native_query={
                    **query_params
                }
            )
            self.app_debug_print(f"Query data user: {len(data)}",True)
            extra_data = {}
            formatted_data = []
            for element in data:
                user_instance = ModelService.convert_to_model_instance(SysUserModel,element)
                user = await  user_instance.get_formated_data(self.accept_language)
                formatted_data.append(user)

            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.SYS_USER,
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

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": formatted_data,
                    **extra_data
                }
            )

        except PermissionError as e:
            self.app_debug_print(f"Error in users 1: {str(e)}",True)
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            self.app_debug_print(f"Error in users 2: {str(e)}",True)
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in users 1: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    async def fetch_fixed_users_data(
        self,
        request: Request,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language) 
            
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            
            # ADD STATIC FILTER
            raw_query_params = {
                # **raw_query_params,
                "sys_organization_id": user_details['sys_organization_id']
            }
            
            
            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            
            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_native_query_data_from_collection(
                collection_key=CollectionKey.SYS_USER,
                all_data=all_data,
                page=page,
                limit=limit,
                accept_language=self.accept_language,
                native_query={
                    **query_params
                }
            )
            self.app_debug_print(f"Query data user: {len(data)}",True)
            extra_data = {}
            formatted_data = []
            for element in data:
                user_instance = ModelService.convert_to_model_instance(SysUserModel,element)
                user = await  user_instance.get_formated_data(self.accept_language)
                formatted_data.append(user)

            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.SYS_USER,
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

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": formatted_data,
                    **extra_data
                }
            )

        except PermissionError as e:
            self.app_debug_print(f"Error in users 1: {str(e)}",True)
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            self.app_debug_print(f"Error in users 2: {str(e)}",True)
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in users 1: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    async def refresh_profil_info(
        self,
        request: Request, 
        accept_language: str = Header(default=DEFAULT_LANGUAGE), 
    ):
        try:
            accept_language = request.state.acceptLanguage if request.state.acceptLanguage else 'fr'
            # DECODE USER TOKEN 
            user_details = await AuthenticatedService.get_user_info(request,accept_language)
            api_Consumer = await AuthenticatedService.get_api_consumer(request,accept_language)
         
            # Generate access token
            # token = create_access_token(
            #     data={"sub":user_details['id'], "type":EJWTTokenType.LOGIN},
            #     token_type=EJWTTokenType.LOGIN,
            #     expires_delta=timedelta(days=4)  # Expires after 2 days
            # )
            # refresh_token = create_access_token(
            #     data={"sub":user_details['id'], "type":EJWTTokenType.REFRESH_TOKEN},
            #     token_type=EJWTTokenType.REFRESH_TOKEN,
            #     expires_delta=timedelta(days=7)  # Expires after 2 days
            # ) 
            user_mfas = await self.user_configured_mfa(sys_user_id=user_details['id'],accept_language=accept_language)
            
            user_signature = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_SIGNATURE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sys_user_id":user_details['id'],
                    "include__parent___files___as___arch_file___local__key____id___foreign__key___arch_file_id":'',
                },
                user=user_details,
            )
            
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK, 
                    "user":{
                        "id":f"{user_details['id']}",
                        "username":f"{user_details['username']}",
                        "first_name":f"{user_details['first_name']}",
                        "last_name":f"{user_details['last_name']}",
                        "gender":f"{user_details['gender']}",
                        "phone_number":f"{user_details['phone_number']}",
                        "email_address":f"{user_details['email']}",
                        "mfas":user_mfas,
                        "user_account_socket_hash":f"{user_details['user_account_socket_hash']}",
                    },
                    "signature":user_signature,
                }
            )  
        except Exception as e:
            self.app_debug_print(f"Error user profile: {e}")
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", accept_language)
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
     
     
     
    async def fetch_notifications(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page"),
    ):
        
        try:
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter___id": str(user_details['rbac_profile_id'])},
                user=user_details,
            )
            if not user_profil:
                raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")

            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            
            # if user_profil['flag'] == ESysProfileFlag.NEW_PROFIL.value:
            #     targeted_id = user_details['id']
            # else:
            #     targeted_id = user_details['sys_organization_id']
            targeted_id = user_details['sys_organization_id']
                
            # ADD STATIC FILTER
            raw_query_params = {
                # **raw_query_params,
                "filter__targeted_id": targeted_id
            }
            
            
            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            
            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.NTF_NOTIFICATION,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    **raw_query_params
                },
                user=user_details
            )
            self.app_debug_print(f"Query data notification: {len(data)}",True)
            extra_data = {}
            formatted_data = []
            for element in data:
                notification = await NtfNotificationModel(**element).get_formated_data(self.accept_language)
                formatted_data.append(notification)

            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.NTF_NOTIFICATION,
                    accept_language=self.accept_language,
                    query={
                        **raw_query_params
                    },
                    user=user_details,
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
                    "data": formatted_data,
                    **extra_data
                }
            )
        except Exception as e:
            formatted_error = format_exception(message="fetch fail", exception=e, include_traceback=True)
            self.app_debug_print(f"Error fetching notifications: {formatted_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    async def check_notifications_count(
        self,
        request: Request,
    ):
        """
        Get count of unread notifications for the current user.
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            user_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter___id": str(user_details['rbac_profile_id'])},
                user=user_details,
            )
            if not user_profil:
                raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")

            # Determine targeted_id based on profile
            targeted_id = user_details['sys_organization_id']

            # Count unread notifications
            unread_count = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.NTF_NOTIFICATION,
                accept_language=self.accept_language,
                query={
                    "filter__targeted_id": targeted_id,
                    "filter__is_read": False
                },
                user=user_details,
            )

            # Count total notifications
            # total_count = await self.generic_service.count_data_from_collection(
            #     collection_key=CollectionKey.NTF_NOTIFICATION,
            #     accept_language=self.accept_language,
            #     query={
            #         "filter__targeted_id": targeted_id
            #     }
            # )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Notification count fetched successfully",
                    "data": unread_count
                    # "data": {
                    #     "unread_count": unread_count,
                    #     "total_count": total_count
                    # }
                }
            )
        except Exception as e:
            formatted_error = format_exception(message="count fail", exception=e, include_traceback=True)
            self.app_debug_print(f"Error counting notifications: {formatted_error}", True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
    async def fetch_user_login_histories(
        self,
        request: Request,
    ):
        """
        Get count of unread notifications for the current user.
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            user_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter___id": str(user_details['rbac_profile_id'])},
                user=user_details,
            )
            if not user_profil:
                raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")

            # Determine targeted_id
            targeted_id = user_details['id']

            # Fetch user login history
            login_histories = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                all_data=True,
                page=0,
                limit=10,
                accept_language=self.accept_language,
                query={
                    "filter__sys_user_id": str(targeted_id),
                },
                user=user_details,
            )
            formatted_data = []
            for element in login_histories:
                login_history = await OpsUserLoginHistoryModel(**element).get_formated_data(self.accept_language,FormatedOutPut.MINIMAL)
                self.app_debug_print(f"login_history: {login_history}",True)
                # consider only login and logout
                if login_history['status'] in [ELoginStatus.LOGGED_IN.value, ELoginStatus.LOGGED_OUT.value]:
                    formatted_data.append(login_history)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": "User login history fetched successfully",
                    "data": formatted_data
                }
            )
        except Exception as e:
            formatted_error = format_exception(message="count fail", exception=e, include_traceback=True)
            self.app_debug_print(f"Error counting notifications: {formatted_error}", True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    async def mark_notifications_as_read(
        self,
        request: Request,
        notification_ids: Optional[str] = None,
        mark_all: bool = False,
    ):
        """
        Mark notifications as read.
        - If notification_ids provided: mark specific notifications as read
        - If mark_all is True: mark all notifications as read for the user
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            user_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter___id": str(user_details['rbac_profile_id'])},
                user=user_details,
            )
            if not user_profil:
                raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")

            # Determine targeted_id based on profile
            # TODO:: UPDATE THIS
            # if user_profil['flag'] == ESysProfileFlag.NEW_PROFIL.value:
            #     targeted_id = user_details['id']
            # else:
            targeted_id = user_details['sys_organization_id']

            marked_count = 0

            if mark_all:
                # Fetch all unread notifications for this user
                unread_notifications = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.NTF_NOTIFICATION,
                    all_data=True,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={
                        "filter__targeted_id": targeted_id,
                        "filter__is_read": False
                    },
                    user=user_details,
                )

                # Mark each as read
                for notification in unread_notifications:
                    await self.generic_service.update_data_in_collection(
                        collection_key=CollectionKey.NTF_NOTIFICATION,
                        item_id=str(notification['_id']),
                        data={"is_read": True}
                    )
                    marked_count += 1

            elif notification_ids:
                # Parse notification IDs (comma-separated)
                ids_list = [id.strip() for id in notification_ids.split(",") if id.strip()]

                for notification_id in ids_list:
                    # Verify the notification belongs to this user
                    notification = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.NTF_NOTIFICATION,
                        output_data_type=OutputDataType.DEFAULT.value,
                        accept_language=self.accept_language,
                        query={
                            "filter___id": notification_id,
                            "filter__targeted_id": targeted_id
                        },
                        user=user_details,
                    )

                    if notification and not notification.get("is_read", False):
                        await self.generic_service.update_data_in_collection(
                            collection_key=CollectionKey.NTF_NOTIFICATION,
                            item_id=notification_id,
                            data={"is_read": True}
                        )
                        marked_count += 1
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Either notification_ids or mark_all=true must be provided"
                )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": f"{marked_count} notification(s) marked as read",
                    "data": {
                        "marked_count": marked_count
                    }
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            formatted_error = format_exception(message="mark as read fail", exception=e, include_traceback=True)
            self.app_debug_print(f"Error marking notifications as read: {formatted_error}", True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")




    async def add_user_config(
        self,
        request: Request,
        payload: UserConfigsPayload
    ):

        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        language = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.REF_LANGUAGE.value,
            output_data_type=OutputDataType.DEFAULT.value,
            accept_language=self.accept_language,
            query={
                "filter__short_code": str(payload.language if payload.language else 'fr').strip()
            },
            user=user_details,
        )
        if not language:
            language = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_LANGUAGE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__short_code": 'fr'
                },
                user=user_details,
            )

        config_data = {
            "dark_mode": payload.theme_mode == EUserThemeMode.DARK.value,
            "theme_mode": payload.theme_mode,
            "ref_language_id": language['id'],
            "sys_user_id": user_details['id'],
        }
        self.app_debug_print(f" \n\n\n config_data to save : {config_data} \n\n\n", True)

        result = await self.generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.CFG_USER_CONFIG,
            filter_data={"sys_user_id": user_details['id']},
            update_data=config_data
        )

        self.app_debug_print(f" \n\n\n result upsert: {result} \n\n\n", False)

        query_config = {
            "filter__sys_user_id": user_details['id']
        }

        user_config = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_USER_CONFIG.value,
            output_data_type=OutputDataType.DEFAULT.value,
            accept_language=self.accept_language,
            query=query_config,
            user=user_details,
        )

        if not user_config:
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": None,
                }
            )
        self.app_debug_print(
            f" \n\n\n user_config : {user_config} \n\n\n", True)

        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": {
                    "language": language['short_code'],
                    "dark_mode": user_config['dark_mode'],
                    "theme_mode": user_config['theme_mode'],
                },
            }
        )


    async def report_suspicious_activity(
        self,
        request: Request,
        payload,
    ):
        """
        Report suspicious activity to support team.
        Sends email to support and stores report in database.
        """
        try:
            # Get user details
            user_details = await self.get_user_info(request, self.accept_language)
            api_consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            
            # Get IP address and device info
            ip_address = self.get_real_ip_address(request)
            device_hashed_id = await HashService.get_hashed_device_id(request)
            
            # Get SAAS config for support email
            saas_config_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__is_activated": True},
                user=user_details,
            )
            
            support_email = await self.get_system_support_email(saas_config_info, self.accept_language) if saas_config_info else None
            
            # Create suspicious activity report record
            report_data = {
                "sys_user_id": user_details['id'],
                "description": payload.description,
                "report_type": payload.report_type,
                "ip_address": ip_address,
                "device_hashed_id": device_hashed_id,
                "user_email": user_details.get('email', ''),
                "user_phone": user_details.get('telephone', ''),
                "user_name": f"{user_details.get('first_name', '')} {user_details.get('last_name', '')}".strip(),
                "status": "pending",
                "created_at": datetime.now(timezone.utc),
            }
            
            # Store report in database
            report_result = await self.generic_service.add_data_to_collection(
                collection_key=CollectionKey.OPS_SUSPICIOUS_ACTIVITY_REPORT,
                data=report_data,
                user=user_details, request=request,
            )
            
            # Send notification email to support
            if support_email:
                email_subject = f"🚨 Suspicious Activity Report - User: {user_details.get('email', 'Unknown')}"
                email_body = f"""
                <h2>Suspicious Activity Report</h2>
                <p><strong>Report ID:</strong> {report_result.get('id', 'N/A') if isinstance(report_result, dict) else 'N/A'}</p>
                <p><strong>User ID:</strong> {user_details['id']}</p>
                <p><strong>User Email:</strong> {user_details.get('email', 'N/A')}</p>
                <p><strong>User Name:</strong> {report_data['user_name']}</p>
                <p><strong>User Phone:</strong> {user_details.get('telephone', 'N/A')}</p>
                <p><strong>IP Address:</strong> {ip_address}</p>
                <p><strong>Report Type:</strong> {payload.report_type}</p>
                <p><strong>Timestamp:</strong> {datetime.now(timezone.utc).isoformat()}</p>
                <hr>
                <h3>Description:</h3>
                <p>{payload.description}</p>
                <hr>
                <p style="color: red;"><strong>Please investigate this report promptly.</strong></p>
                """
                
                try:
                    await self.send_support_email(
                        to_email=support_email,
                        subject=email_subject,
                        body=email_body
                    )
                except Exception as email_error:
                    self.app_debug_print(f"Failed to send email notification: {email_error}", True)
            
            # Create in-app notification for admins
            try:
                await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.NTF_NOTIFICATION,
                    data={
                        "title": "Suspicious Activity Reported",
                        "message": f"User {user_details.get('email', 'Unknown')} reported suspicious activity",
                        "notification_type": "security_alert",
                        "priority": "high",
                        "is_system_notification": True,
                        "created_at": datetime.now(timezone.utc),
                    },
                    user=user_details, request=request,
                )
            except Exception as notif_error:
                self.app_debug_print(f"Failed to create notification: {notif_error}", True)
            
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": "Suspicious activity report submitted successfully. Our support team will review it shortly.",
                }
            )
            
        except Exception as e:
            formatted_error = format_exception(message="report suspicious activity fail", exception=e, include_traceback=True)
            self.app_debug_print(f"Error reporting suspicious activity: {formatted_error}", True)
            raise HTTPException(status_code=500, detail="Failed to submit report. Please try again.")


    async def freeze_account(
        self,
        request: Request,
        payload,
    ):
        """
        Freeze user's account to prevent any transactions.
        """
        try:
            # Get user details
            user_details = await self.get_user_info(request, self.accept_language)
            ip_address = self.get_real_ip_address(request)
            
            # Create freeze record
            freeze_data = {
                "sys_user_id": user_details['id'],
                "reason": payload.reason if hasattr(payload, 'reason') and payload.reason else "User-initiated freeze",
                "is_self_freeze": payload.is_self_freeze if hasattr(payload, 'is_self_freeze') else True,
                "ip_address": ip_address,
                "frozen_at": datetime.now(timezone.utc),
                "is_active": True,
            }
            
            # Store freeze record
            await self.generic_service.add_data_to_collection(
                collection_key=CollectionKey.OPS_ACCOUNT_FREEZE,
                data=freeze_data,
                user=user_details, request=request,
            )
            
            # Update user status to frozen
            await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.SYS_USER,
                item_id=user_details['id'],
                data={"is_account_frozen": True, "frozen_at": datetime.now(timezone.utc)}
            )
            
            # End all active sessions
            await self._end_all_user_sessions(user_details['id'], exclude_current=False)
            
            # Send notification email
            try:
                await self.send_simple_notification_email(
                    to_email=user_details.get('email'),
                    subject="Account Frozen",
                    message=f"Your account has been frozen. If you did not request this, please contact support immediately."
                )
            except Exception as email_error:
                self.app_debug_print(f"Failed to send freeze notification email: {email_error}", True)
            
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": "Account frozen successfully. Contact support to unfreeze.",
                }
            )
            
        except Exception as e:
            formatted_error = format_exception(message="freeze account fail", exception=e, include_traceback=True)
            self.app_debug_print(f"Error freezing account: {formatted_error}", True)
            raise HTTPException(status_code=500, detail="Failed to freeze account. Please try again.")


    async def get_trusted_devices(
        self,
        request: Request,
    ):
        """
        Get list of user's trusted devices.
        """
        try:
            # Get user details
            user_details = await self.get_user_info(request, self.accept_language)
            
            # Fetch all devices for user
            devices = await self.generic_service.fetch_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__sys_user_id": user_details['id']},
                sort={"created_at": -1}
            )
            
            formatted_devices = []
            if devices and isinstance(devices, list):
                for device in devices:
                    device_info = device.get('device_info', {})
                    formatted_devices.append({
                        "id": str(device.get('id', device.get('_id', ''))),
                        "device_name": device_info.get('device_name', 'Unknown Device'),
                        "platform_type": device_info.get('platform_type', 'Unknown'),
                        "model": device_info.get('model', ''),
                        "brand": device_info.get('brand', ''),
                        "ip_address": device_info.get('ip_address', ''),
                        "is_trusted": device.get('status', '') == 'trusted',
                        "status": device.get('status', 'allowed'),
                        "last_used_at": str(device.get('updated_at', device.get('created_at', ''))),
                        "created_at": str(device.get('created_at', '')),
                    })
            
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": "Trusted devices fetched successfully",
                    "data": formatted_devices
                }
            )
            
        except Exception as e:
            formatted_error = format_exception(message="get trusted devices fail", exception=e, include_traceback=True)
            self.app_debug_print(f"Error getting trusted devices: {formatted_error}", True)
            raise HTTPException(status_code=500, detail="Failed to fetch trusted devices.")


    async def manage_trusted_device(
        self,
        request: Request,
        payload,
    ):
        """
        Manage trusted device status (trust, untrust, remove).
        """
        try:
            # Get user details
            user_details = await self.get_user_info(request, self.accept_language)
            
            device_id = payload.device_id
            action = payload.action.lower()
            
            # Verify device belongs to user
            device = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_DEVICE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter___id": device_id,
                    "filter__sys_user_id": user_details['id']
                },
                user=user_details,
            )
            
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")
            
            if action == "remove":
                # Delete device
                await self.generic_service.delete_data_from_collection(
                    collection_key=CollectionKey.CFG_USER_DEVICE,
                    item_id=device_id
                )
                message = "Device removed successfully"
            elif action == "trust":
                # Mark as trusted
                await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.CFG_USER_DEVICE,
                    item_id=device_id,
                    data={"status": "trusted", "trusted_at": datetime.now(timezone.utc)}
                )
                message = "Device marked as trusted"
            elif action == "untrust":
                # Remove trust status
                await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.CFG_USER_DEVICE,
                    item_id=device_id,
                    data={"status": "allowed", "trusted_at": None}
                )
                message = "Device trust removed"
            else:
                raise HTTPException(status_code=400, detail="Invalid action")
            
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": message,
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            formatted_error = format_exception(message="manage trusted device fail", exception=e, include_traceback=True)
            self.app_debug_print(f"Error managing trusted device: {formatted_error}", True)
            raise HTTPException(status_code=500, detail="Failed to manage device.")


    async def end_all_sessions(
        self,
        request: Request,
    ):
        """
        End all active sessions except the current one.
        """
        try:
            # Get user details
            user_details = await self.get_user_info(request, self.accept_language)
            
            # Get current device
            device_hashed_id = await HashService.get_hashed_device_id(request)
            
            ended_count = await self._end_all_user_sessions(
                user_id=user_details['id'], 
                exclude_device_hash=device_hashed_id
            )
            
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": f"Successfully ended {ended_count} session(s)",
                    "data": {"sessions_ended": ended_count}
                }
            )
            
        except Exception as e:
            formatted_error = format_exception(message="end all sessions fail", exception=e, include_traceback=True)
            self.app_debug_print(f"Error ending all sessions: {formatted_error}", True)
            raise HTTPException(status_code=500, detail="Failed to end sessions.")


    async def _end_all_user_sessions(
        self,
        user_id: str,
        exclude_device_hash: str = None,
        exclude_current: bool = True,
    ) -> int:
        """
        Helper method to end all user sessions.
        Returns count of sessions ended.
        """
        try:
            # Fetch all active login histories
            query = {
                "filter__sys_user_id": user_id,
                "filter__status": ELoginStatus.LOGGED_IN.value
            }
            
            active_sessions = await self.generic_service.fetch_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                output_data_type=OutputDataType.DEFAULT.value,
                query=query
            )
            
            ended_count = 0
            if active_sessions and isinstance(active_sessions, list):
                for session in active_sessions:
                    session_id = str(session.get('id', session.get('_id', '')))
                    
                    # Skip current device if requested
                    if exclude_current and exclude_device_hash:
                        session_device = session.get('cfg_user_device', {})
                        if session_device and session_device.get('device_id_str') == exclude_device_hash:
                            continue
                    
                    # Update session to logged out
                    await self.generic_service.update_data_in_collection(
                        collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                        item_id=session_id,
                        data={
                            "status": ELoginStatus.LOGGED_OUT.value,
                            "session_last_activity": datetime.now(timezone.utc)
                        }
                    )
                    ended_count += 1
            
            return ended_count
            
        except Exception as e:
            self.app_debug_print(f"Error in _end_all_user_sessions: {e}", True)
            return 0


    async def send_support_email(self, to_email: str, subject: str, body: str):
        """
        Helper method to send email to support.
        """
        try:
            # Use existing email service method
            await self.send_email(
                to_email=to_email,
                subject=subject,
                html_content=body
            )
        except Exception as e:
            self.app_debug_print(f"Failed to send support email: {e}", True)
            raise


    async def send_simple_notification_email(self, to_email: str, subject: str, message: str):
        """
        Helper method to send simple notification email.
        """
        try:
            html_body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>{subject}</h2>
                <p>{message}</p>
                <hr>
                <p style="color: #666; font-size: 12px;">This is an automated message. Please do not reply directly to this email.</p>
            </div>
            """
            await self.send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_body
            )
        except Exception as e:
            self.app_debug_print(f"Failed to send notification email: {e}", True)
