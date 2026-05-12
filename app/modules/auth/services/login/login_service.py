

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException,status
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE

from app.modules.auth.enums.auth import ELoginStatus
from app.modules.auth.enums.common import MessageCategory
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.auth.models.ops_user_login_history.ops_user_login_history_model import OpsUserLoginHistoryModel
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.response.response_service import ResponseService

from app.modules.core.enums.type_enum import OutputDataType

class LoginService(ResponseService,DebugService):
    """
    Service for handling login and authentication.
    """
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.core.services.generic.generic_services import GenericService
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language=accept_language)
        super().__init__(accept_language)
        
    async def get_or_create_init_with_data_history(
        self,
        data:any,
        filter_query:any,
        accept_language:str = DEFAULT_LANGUAGE,):
        try:
            now = datetime.now(timezone.utc) 
            # Start and end of the current day
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            self.app_debug_print(f"\n get or creation password reset history_query :  {data}")
            loginHistory = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                output_data_type=OutputDataType.DEFAULT.value,
                query=filter_query,
                sort={"created_at": -1}
            )
            self.app_debug_print(f"\n get or creation loginHistory :  {loginHistory}")
            if not loginHistory:
                # login_history_data = OpsUserLoginHistoryModel(
                #     sys_user_id=data['sys_user_id'],
                #     ip_address=data['ip_address'],
                #     cfg_user_device_id=data['cfg_user_device_id'],
                #     status=data['status'], 
                # )
                _login_history_data = {
                    "sys_user_id":data['sys_user_id'],
                    "ip_address":data['ip_address'],
                    "cfg_user_device_id":data['cfg_user_device_id'],
                    "status":data['status'], 
                    # "otp":data['otp'],
                }
                # Convert enums to values
                # processed_data = ConverterService.convert_enums_to_values(login_history_data.model_dump(by_alias=True))
                # processed_data = ConverterService.convert_enums_to_values(_login_history_data)
                saved = await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                    data=_login_history_data
                )
                loginHistory = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id":saved},
                    sort={"created_at": -1}
                )
                
            return loginHistory
        except Exception as e:
            self.app_debug_print(f"Error get_or_create_init_with_data_history in : {e}",True)
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

    async def get_or_create_init_login_history(
        self,
        sys_user_id:str,
        ip_address:str,
        cfg_user_device_id:str,
        sys_organization_id:str,
        accept_language:str = DEFAULT_LANGUAGE,):
        try:
            now = datetime.now(timezone.utc) 
            # Start and end of the current day
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            login_history_query = {
                "filter__sys_user_id":sys_user_id,
                "filter__status":ELoginStatus.INIT_LOGIN.value,
                "filter__created_at": {"$gte": start_of_day, "$lt": end_of_day}  # Date range for today
            }
            self.app_debug_print(f"\n get or creation login_history_query :  {login_history_query}")
            loginHistory = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                output_data_type=OutputDataType.DEFAULT.value,
                query=login_history_query,
                sort={"created_at": -1}
            )
            self.app_debug_print(f"\n get or creation loginHistory :  {loginHistory}")
            if not loginHistory:
                # login_history_data = OpsUserLoginHistoryModel(
                #     sys_user_id=sys_user_id,
                #     ip_address=ip_address,
                #     cfg_user_device_id=cfg_user_device_id,
                #     status=ELoginStatus.INIT_LOGIN, 
                # )
                _loginHistory = {
                    "sys_user_id":sys_user_id,
                    "ip_address":ip_address,
                    "cfg_user_device_id":cfg_user_device_id,
                    "status":ELoginStatus.INIT_LOGIN.value, 
                    "sys_organization_id":sys_organization_id,
                }

                # Convert enums to values
                # processed_data = ConverterService.convert_enums_to_values(login_history_data.model_dump(by_alias=True))
                # Convert enums to values
                # processed_data = ConverterService.convert_enums_to_values(_loginHistory)
                loginHistory = await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                    data=_loginHistory
                )
                
            return loginHistory
        except Exception as e:
            self.app_debug_print(f"Error get_or_create_init_login_history in : {e}",True)
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

    async def get_or_create_init_login_history_in_30_min(
        self,
        sys_user_id:str,
        ip_address:str,
        cfg_user_device_id:str,
        sys_organization_id:str,
        device_id_str:str,
        accept_language:str = DEFAULT_LANGUAGE,):
        try:
            now = datetime.now(timezone.utc)

            # Calculate the time 30 minutes ago
            start_time = now - timedelta(minutes=10)

            # Query to fetch login history from the last 10 minutes
            login_history_query = {
                "filter__sys_user_id": sys_user_id,
                "filter__status": ELoginStatus.INIT_LOGIN.value,  # Use .value to get the string value
                "filter__created_at": {"$gte": start_time, "$lt": now},
                "filter__device_id_str":device_id_str
            } 
            self.app_debug_print(f"\n get or creation login_history_query : {login_history_query}",False)
            
            # Use a dictionary for sort instead of a set
            sort_dict = {"created_at": -1}
            
            loginHistory = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                output_data_type=OutputDataType.DEFAULT.value,
                query=login_history_query,
                sort=sort_dict
            )
            self.app_debug_print(f"\n  after get or creation loginHistory : {loginHistory}",False)
            if not loginHistory:
                _login_history_data = {
                    "sys_user_id": sys_user_id,
                    "ip_address": ip_address,
                    "cfg_user_device_id": cfg_user_device_id,
                    "status": ELoginStatus.INIT_LOGIN.value,  # Use .value to get the string value
                    "sys_organization_id": sys_organization_id,
                    "device_id_str":device_id_str
                } 
                loginHistory = await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                    data=_login_history_data
                )
                
            return loginHistory
        except Exception as e:
            self.app_debug_print(f"Error get_or_create_init_login_history_in_30_min in : {e}",True)
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

    async def get_today_init_login_history(
        self,
        sys_user_id:str,
        cfg_user_device_id:str,
        accept_language:str = DEFAULT_LANGUAGE,):
        try:
            now = datetime.now(timezone.utc) 
            # Start and end of the current day
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            # print(f"userInfo :  {sys_user_id}")
            login_history_query = {
                "sys_user_id":sys_user_id,
                "cfg_user_device_id":cfg_user_device_id,
                "status":ELoginStatus.INIT_LOGIN.value,
                "created_at": {"$gte": start_of_day, "$lt": end_of_day}  # Date range for today 
            }
            self.app_debug_print(f"login_history_query :  {login_history_query}")
            
            loginHistory = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                output_data_type=OutputDataType.DEFAULT.value,
                query=login_history_query,
                sort={"created_at": -1}
            )
            self.app_debug_print(f"\n\nloginHistory founded :  {loginHistory}")
            return loginHistory
        except Exception as e:
            self.app_debug_print(f"Error get_today_init_login_history in : {e}",True)
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
        
        
