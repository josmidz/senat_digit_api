


import json
import random
from typing import Any, Dict, Optional

from fastapi import Body, HTTPException, Request,status

from app.modules.auth.enums.common import MessageCategory
from app.modules.core.types.response import CustomJSONResponse

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.device.device_service import DeviceService
from app.modules.core.services.generator.generator_service import GeneratorService

from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.services.sms.sms_service import SmsService
from app.modules.security.services.security_websocket_service import SecurityWebSocketService
from app.modules.core.enums.type_enum import  EExpectedActionTypeFlag, ESudoActionTypeFlag, OutputDataType
from app.modules.core.constants.keys import RedisKeys
from app.modules.core.services.redis.redis_service import AppRedisService

class SecurityWebsocketServiceController(
    AuthenticatedService,
    ResponseService,
    SmsService,
    DeviceService,
    DebugService):
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.auth.services.login.login_service import LoginService
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.auth.services.token.token_service import TokenService
        
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        self.token_service = TokenService(accept_language)
        self.login_service = LoginService(accept_language)
        super().__init__(accept_language)

    async def send_event_to_client(
        self,
        request:Request,
        user_account_socket_hash: str, 
        data: Dict[str, Any],
    ):
        """
        Send an event to a specific client using the WebSocket service.
        
        Args:
            user_account_socket_hash: The unique hash identifying the user's socket connection
            data: The data to send to the client
            current_user: The authenticated user making the request
        """
        try:
            current_user = self.token_service.decode_and_get_user_from_token(request)
            result = await SecurityWebSocketService.send_event_to_client(user_account_socket_hash, data)
            return result
        except Exception as e:
            self.app_debug_print(f"Error in send_event_to_client endpoint: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    async def send_unlock_event_to_client(
        self,
        request: Request,
        data: dict = Body(...),
    ):
        """
        Send an event to a specific client using the WebSocket service.
        
        Args:
            user_account_socket_hash: The unique hash identifying the user's socket connection
            data: The data to send to the client
            current_user: The authenticated user making the request
        """
        try:
            current_user = await self.token_service.decode_and_get_user_from_token(request)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            self.app_debug_print(f'\n\n\n api_Consumer  : {api_Consumer} \n\n\n',True)
            self.app_debug_print(f'\n\n\n data  : {data} \n\n\n',True)
            instructionId = GeneratorService.generate_encryption_key()
            event_data = {
                "type": "instruction",
                "custom_type": "localAuth",
                "params": {
                    "instruction_id": instructionId,
                    "description": "unlock screen instructions",
                    "expected_action":EExpectedActionTypeFlag.UNLOCK_SCREEN.value,
                    "api_consumer_key":api_Consumer['consumer_hash']
                }
            }
            user_account_socket_hash = current_user['user_account_socket_hash']
            self.app_debug_print(f"user_account_socket_hash >>>>>: {user_account_socket_hash}",True)

            # totpAppApiConsumer = await self.generic_service.fetch_one_from_collection(
            #         collection_key=CollectionKey.REF_API_CONSUMER,
            #         output_data_type=OutputDataType.DEFAULT.value,
            #         query={"filter__can_receive_totp_validation_push":True}, 
            #         sort={'created_at':-1}
            # )
            totpAppApiConsumers = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_API_CONSUMER,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                page=0,
                limit=10,
                query={"filter__can_receive_totp_validation_push":True}, 
                sort={'created_at':-1}
            )
            result = None
            if totpAppApiConsumers:
                self.app_debug_print(f'\n\n\n totpAppApiConsumers  : {totpAppApiConsumers} \n\n\n',True)
                # FIX: Use the ORIGINAL user_account_socket_hash (raw hash without consumer prefix)
                # and construct each key independently to avoid hash accumulation
                raw_user_hash = user_account_socket_hash
                for totpAppApiConsumer in totpAppApiConsumers:
                    consumer_key = f"{totpAppApiConsumer['consumer_hash']}___{raw_user_hash}"
                    self.app_debug_print(f" sending unlock screen to consumer key >>>>>: {consumer_key}",True)
                    result = await SecurityWebSocketService.send_event_to_client(consumer_key, event_data, None)
                instruction_key = RedisKeys.format_key(RedisKeys.ACTIVE_INSTRUCTION, expected_action=EExpectedActionTypeFlag.UNLOCK_SCREEN.value, instruction_id=instructionId)
                self.app_debug_print(f" sending unlock screen key >>>>>: {instruction_key}",True)
                redis_data = {
                    "redis_data_key": instruction_key,
                    "redis_data_info": {
                        **event_data,
                        "api_consumer_key":totpAppApiConsumers[0]['consumer_hash'],
                        "api_consumer_keys":[totpAppApiConsumer['consumer_hash'] for totpAppApiConsumer in totpAppApiConsumers],
                        "status": "pending",
                        "instruction_id": instructionId,
                    },
                    "redis_expire_time": 120,  
                }
                # Store the Redis data (no longer sending via send_event_to_client since we already sent above)
                await AppRedisService.set_redis_value(
                    instruction_key,
                    json.dumps(redis_data["redis_data_info"]),
                    redis_data["redis_expire_time"]
                )
            
            self.app_debug_print(f"send_event_to_client result: {result}",True)
            message = self.get_response_message(MessageCategory.SUCCESS, "EVENT_SENT_SUCCESSFULLY", self.accept_language,)
            return CustomJSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "status_code": status.HTTP_201_CREATED,
                        "message": message,
                        "data":instructionId
                    }
                )
        except Exception as e:
            self.app_debug_print(f"Error in send_event_to_client endpoint: {str(e)}",True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            

    async def get_unlock_event_result(
        self,
        request: Request,
        data: dict = Body(...),
    ):
        """
        Send an event to a specific client using the WebSocket service.
        
        Args:
            user_account_socket_hash: The unique hash identifying the user's socket connection
            data: The data to send to the client
            current_user: The authenticated user making the request
        """
        try:
            current_user = await  self.token_service.decode_and_get_user_from_token(request)
            
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            self.app_debug_print(f'\n\n\n current_user  : {current_user} \n\n\n',False)
            self.app_debug_print(f'\n\n\n data  : {data} \n\n\n',False)
            instructionId = GeneratorService.generate_encryption_key()
            event_data = {
                "type": "instruction",
                "custom_type": ESudoActionTypeFlag.LOCAL_AUTH.value,
                "params": {
                    "instruction_id": instructionId,
                    "expected_action":EExpectedActionTypeFlag.UNLOCK_SCREEN.value,
                    "description": "unlock screen instructions"
                }
            }
            instruction_key = RedisKeys.format_key(RedisKeys.ACTIVE_INSTRUCTION, expected_action=EExpectedActionTypeFlag.UNLOCK_SCREEN.value, instruction_id=instructionId)
            redis_data = {
                "redis_data_key": instruction_key,
                "redis_data_info": {
                    **event_data,
                    "api_consumer_key":api_Consumer['consumer_hash'],
                    "status": "pending",
                    "instruction_id": instructionId,
                },
                "redis_expire_time": 120,  
            }
            user_account_socket_hash = current_user['user_account_socket_hash']
            self.app_debug_print(f"user_account_socket_hash >>>>>: {user_account_socket_hash}",False)
            result = await SecurityWebSocketService.send_event_to_client(user_account_socket_hash, event_data,redis_data)
            
            self.app_debug_print(f"send_event_to_client result: {result}",False)
            message = self.get_response_message(MessageCategory.SUCCESS, "EVENT_SENT_SUCCESSFULLY", self.accept_language,)
            return CustomJSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "status_code": status.HTTP_201_CREATED,
                        "message": message,
                        "data":instructionId
                    }
                )
        except Exception as e:
            self.app_debug_print(f"Error in send_event_to_client endpoint: {str(e)}",True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
            
    async def reload_sudo_action_result(
        self,
        request: Request, 
    ):
        """
        Send an event to a specific client using the WebSocket service.
        
        Args:
            user_account_socket_hash: The unique hash identifying the user's socket connection
            data: The data to send to the client
            current_user: The authenticated user making the request
        """
        try:
            current_user =  await  self.token_service.decode_and_get_user_from_token(request)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            self.app_debug_print(f'\n\n\n current_user  : {current_user} \n\n\n',False)
            
            sentInstructionId = request.query_params.get("instruction_id",None)
            if not sentInstructionId:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail= self.get_response_message(MessageCategory.ERRORS, "INSTRUCTION_ID_REQUIRED", self.accept_language,)
                )
                
            sudo_action_types = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_SUDO_ACTION_CONFIRMATION_TYPE,
                all_data=True,
                page=0,
                limit=10,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                query={
                    "filter__is_activated": True,
                },
            )
            # INIT sudo_action_key >> : sudoAction:vlH8JhWKyQpDJRV18tHg4pQzx3KM5M6DQSHa4v7Wb1g= 
            random_action = random.choice(sudo_action_types)
            redis_local_key = RedisKeys.format_key(RedisKeys.SUDO_ACTION, instruction_id=sentInstructionId)
            self.app_debug_print(f'\n\n\n redis_local_key  : {redis_local_key} \n\n\n',True)
            all_caches = await AppRedisService.get_all_caches_by_prefix("instruction:SUDO_ACTION:")
            self.app_debug_print(f'\n\n\n ALL INFOS   : {all_caches} \n\n\n',True)
            saved_instruction = await AppRedisService.get_str_redis_value(str(redis_local_key).strip())
            self.app_debug_print(f'\n\n\n FETCHED FROM redis_local_key  : {saved_instruction} \n\n\n',True)
            if not saved_instruction:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail= self.get_response_message(MessageCategory.ERRORS, "INSTRUCTION_NOT_FOUND", self.accept_language,)
                )
            redis_data = {}
            event_data = {}
            random_selected_golden_number = 0
            saved_instruction_json = json.loads(saved_instruction)
            if saved_instruction_json.get('status') != 'pending':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail= self.get_response_message(MessageCategory.ERRORS, "INSTRUCTION_ALREADY_PROCESSED", self.accept_language,)
                )
                
            self.app_debug_print(f'\n\n\n sentInstructionId  : {sentInstructionId} \n\n\n',False)
            # Generate new instruction ID for the new sudo action
            new_instructionId = GeneratorService.generate_encryption_key()
            sudo_action_key = RedisKeys.format_key(RedisKeys.SUDO_ACTION, instruction_id=new_instructionId)

            # Initialize variables
            response_instruction_id = new_instructionId
            random_selected_golden_number = 0

            if random_action['flag'] == ESudoActionTypeFlag.GOLDEN_NUMBER.value :
                numbers = GeneratorService.generate_random_golden_numbers(3)
                random_golden_number = random.choice(numbers)
                event_data = {
                    "type": "instruction",
                    "custom_type": random_action['flag'],
                    "params": {
                        "numbers": numbers,
                        "description": random_action['totp_app_description_str'],
                        "expected_action":EExpectedActionTypeFlag.SUDO_ACTION.value,
                    }
                }
                redis_data = {
                    "redis_data_key": sudo_action_key,
                    "redis_data_info": {
                        **event_data,
                        "api_consumer_key":api_Consumer['consumer_hash'],
                        "selected_golden_number":random_golden_number,
                        "status": "pending",
                        "instruction_id": new_instructionId,  # Use the new instruction ID
                    },
                    "redis_expire_time": 120,
                }

                # Use the golden number's instruction_id for response, but keep new_instructionId for Redis storage
                response_instruction_id = random_golden_number['instruction_id']
                random_selected_golden_number = random_golden_number['number']
                
            elif random_action['flag'] == ESudoActionTypeFlag.LOCAL_AUTH.value :
                event_data = {
                    "type": "instruction",
                    "custom_type": random_action['flag'],
                    "params": {
                        "expected_action":EExpectedActionTypeFlag.SUDO_ACTION.value,
                        "instruction_id": new_instructionId,
                        "description": random_action['totp_app_description_str'],
                    }
                }
                redis_data = {
                    "redis_data_key": sudo_action_key,
                    "redis_data_info": {
                        **event_data,
                        "api_consumer_key":api_Consumer['consumer_hash'],
                        "status": "pending",
                        "instruction_id": new_instructionId,
                    },
                    "redis_expire_time": 120,
                }
                # For LOCAL_AUTH, use the new instruction ID for response as well
                response_instruction_id = new_instructionId
                random_selected_golden_number = 0  # No golden number for LOCAL_AUTH

            elif random_action['flag'] == ESudoActionTypeFlag.TOTP.value :
                event_data = {
                    "type": "instruction",
                    "custom_type": random_action['flag'],
                    "params": {
                        "instruction_id": new_instructionId,
                        "expected_action":EExpectedActionTypeFlag.SUDO_ACTION.value,
                        "description": random_action['totp_app_description_str'],
                    }
                }
                redis_data = {
                    "redis_data_key": sudo_action_key,
                    "redis_data_info": {
                        **event_data,
                        "api_consumer_key":api_Consumer['consumer_hash'],
                        "status": "pending",
                        "instruction_id": new_instructionId,
                    },
                    "redis_expire_time": 120,
                }
                # For TOTP, use the new instruction ID for response as well
                response_instruction_id = new_instructionId
                random_selected_golden_number = 0  # No golden number for TOTP
            user_account_socket_hash = current_user['user_account_socket_hash']
            self.app_debug_print(f"user_account_socket_hash >>>>>: {user_account_socket_hash}",False)
            result = await SecurityWebSocketService.send_event_to_client(user_account_socket_hash, event_data,redis_data)
            
            self.app_debug_print(f"send_event_to_client result: {result}",False)
            message = self.get_response_message(MessageCategory.SUCCESS, "EVENT_SENT_SUCCESSFULLY", self.accept_language,)
            return CustomJSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "status_code": status.HTTP_201_CREATED,
                        "message": message,
                        "data":{
                            "instruction_id": response_instruction_id,
                            "selected_golden_number": random_selected_golden_number,
                            "random_sudo_action_info": random_action
                        },
                    }
                )
        except Exception as e:
            self.app_debug_print(f"Error in send_event_to_client endpoint: {str(e)}",True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    async def get_connection_status(
        self,
        request: Request,
        user_account_socket_hash: str,
    ):
        """
        Check if a client is currently connected.
        
        Args:
            user_account_socket_hash: The unique hash identifying the user's socket connection
            current_user: The authenticated user making the request
        """
        try:
            current_user =  await  self.token_service.decode_and_get_user_from_token(request)
            result = await SecurityWebSocketService.get_connection_status(user_account_socket_hash)
            return result
        except Exception as e:
            self.app_debug_print(f"Error in get_connection_status endpoint: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
        
        
        
        