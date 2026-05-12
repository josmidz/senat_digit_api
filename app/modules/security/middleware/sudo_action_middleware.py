

import json
import random
from typing import Any, Dict
from fastapi import HTTPException, Request,status

from app.modules.auth.enums.common import MessageCategory
from app.modules.auth.enums.mfa import MFaFlag
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.generator.generator_service import GeneratorService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.redis.redis_service import AppRedisService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.security.services.security_websocket_service import SecurityWebSocketService
from app.modules.core.enums.type_enum import EExpectedActionTypeFlag, ESudoActionTypeFlag, OutputDataType


async def sudo_action_middleware(request: Request) -> Dict[str, Any]:
    """
    Middleware for sudo actions.
    """
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    user_details = await AuthenticatedService.get_user_info(request,accept_language)
    api_Consumer = await AuthenticatedService.get_api_consumer(request,accept_language)
    DebugService.app_debug_print(f" user_details : {user_details} ",False)
    # SUDO ACTION CHECKING
    generic_service = GenericService(accept_language)
    current_path = request.url.path
    user_account_socket_hash = user_details.get('user_account_socket_hash', None)
    if not user_account_socket_hash:
        message = ResponseService.get_response_message(MessageCategory.COMMON, "INVALID_USER_ACCOUNT", accept_language)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

    DebugService.app_debug_print(f" current_path : {current_path} ",True)
    rbac_endpoint = await generic_service.fetch_one_from_collection(
        collection_key=CollectionKey.RBAC_ENDPOINT,
        output_data_type=OutputDataType.DEFAULT.value,
        accept_language=accept_language,
        query={
            "filter__url":  current_path,
        }
    )
    if not rbac_endpoint:
        # TODO:: CHECK CONSTRAINT ON MISSING URL IN RBAC_ENDPOINT TABLE
        return {
            "is_sudo_action":False,
            "is_sudo_group_action":False,
            "sudo_group_users":[],
            "instruction_id":'',
            "can_proceed":True,
        }
    DebugService.app_debug_print(f"\n\n\n\n is_sudo_action  : {rbac_endpoint['is_sudo_action']} ",True)
    DebugService.app_debug_print(f" rbac_endpoint >> : {rbac_endpoint} ",True)
    sudo_action_confirmation_types = await generic_service.fetch_data_from_collection(
        collection_key=CollectionKey.RBAC_SUDO_ACTION_CONFIRMATION_TYPE,
        all_data=True,
        page=0,
        limit=10,
        output_data_type=OutputDataType.DEFAULT,
        accept_language=accept_language,
        query={
            "filter__is_activated": True,
        },
    )
    is_sudo_group_action = False
    sudo_group_users = await generic_service.fetch_data_from_collection(
        collection_key=CollectionKey.RBAC_USER_VALIDATOR,
        all_data=True,
        page=0,
        limit=10,
        output_data_type=OutputDataType.DEFAULT,
        accept_language=accept_language,
        query={
            "filter__sys_organization_id": user_details['sys_organization_id'],
            "filter__rbac_sudo_action_id":None
        },
    )

    instructionId = GeneratorService.generate_encryption_key()
    DebugService.app_debug_print(f" sudo_action_confirmation_types is >  0 : {len(sudo_action_confirmation_types) > 0} ",True)
    DebugService.app_debug_print(f" sudo_action_confirmation_types > 0 : {len(sudo_action_confirmation_types)} ",True)
    if rbac_endpoint and len(sudo_action_confirmation_types) > 0:
        is_sudo_action = rbac_endpoint['is_sudo_action']
        is_sudo_group_action = rbac_endpoint['is_sudo_group_action']
        DebugService.app_debug_print(f"\n\n\n\n is_sudo_action  : {is_sudo_action} ",True)
        rbac_sudo_action = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_SUDO_ACTION,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter__targeted_id":rbac_endpoint['id']},
            sort={'created_at':-1}
        )
        DebugService.app_debug_print(f"\n\n\n\n rbac_sudo_action  : {rbac_sudo_action} ",True)
        if not rbac_sudo_action or is_sudo_action is False:
            return {
                "is_sudo_action":False,
                "is_sudo_group_action":False,
                "sudo_group_users":[],
                "instruction_id":'',
                "can_proceed":True,
            }
        if rbac_sudo_action:
            customized_sudo_group_users = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_USER_VALIDATOR,
                all_data=True,
                page=0,
                limit=10,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=accept_language,
                query={
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                    "filter__rbac_sudo_action_id":rbac_sudo_action['id']
                },
            )
            if len(customized_sudo_group_users) > 0:
                sudo_group_users = customized_sudo_group_users

        # FOCUSED ON SINGLE RBAC_SUDO_ACTION_CONFIRMATION_TYPE TEST
        # random_action = await generic_service.fetch_one_from_collection(
        #     collection_key=CollectionKey.RBAC_SUDO_ACTION_CONFIRMATION_TYPE,
        #     output_data_type=OutputDataType.DEFAULT.value,
        #     query={"filter__flag":ESudoActionTypeFlag.GOLDEN_NUMBER.value},
        #     sort={'created_at':-1}
        # )
        # if not random_action:
        #     # RETURN MISSING EXCEPTION
        #     return {
        #         "is_sudo_action":False,
        #         "is_sudo_group_action":False,
        #         "sudo_group_users":[],
        #         "instruction_id":'',
        #         "can_proceed":False,
        #         "message": ResponseService.get_response_message(MessageCategory.COMMON, "NO_SUDO_ACTION_INSTRUCTION", accept_language)
        #     }


        # # TODO: FOCUSED ON SINGLE RBAC_SUDO_ACTION_CONFIRMATION_TYPE TEST
        random_action = random.choice(sudo_action_confirmation_types)
        redis_data = {}
        event_data = {}
        random_selected_golden_number = 0

        param_instruction_id = request.query_params.get('instruction_id', None)
        param_totp = request.query_params.get('totp', None)
        # Use standardized Redis key pattern
        from app.modules.core.constants.keys import RedisKeys
        sudo_action_key = RedisKeys.format_key(RedisKeys.SUDO_ACTION, instruction_id=param_instruction_id)
        if param_instruction_id:
            DebugService.app_debug_print(f" GETTING KEY : {sudo_action_key}", True)
            saved_instruction = await AppRedisService.get_str_redis_value(sudo_action_key)

            # Check if saved_instruction is None before parsing JSON
            if saved_instruction is None:
                DebugService.app_debug_print(f" SUDO ACTION KEY NOT FOUND IN REDIS : {sudo_action_key}", True)
                return {
                    "is_sudo_group_action":is_sudo_group_action,
                    "sudo_group_users":sudo_group_users,
                    "instruction_id":instructionId,
                    "message": ResponseService.get_response_message(MessageCategory.COMMON, "NO_SUDO_ACTION_INSTRUCTION", accept_language),
                    "can_proceed":False,
                }

            saved_instruction_json = json.loads(saved_instruction)
            get_status = saved_instruction_json.get('status','none')
            DebugService.app_debug_print(f"\n\n\n >>> || get_status : {get_status} \n\n\n", True)
            DebugService.app_debug_print(f"\n\n\n >>> || saved_instruction_json : {saved_instruction_json} \n\n\n", True)
            if get_status == "validated":
                await AppRedisService.remove_redis_value(sudo_action_key)
                return {
                    "is_sudo_group_action":is_sudo_group_action,
                    "sudo_group_users":sudo_group_users,
                    "instruction_id":instructionId,
                    "can_proceed":True,
                }
            if param_totp is not None and get_status == "pending":
                mfa_query = {
                    "filter__is_activated": True,
                    "filter__flag": MFaFlag.SYCAMORE_2FA_APP, 
                }
                mfa = await generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_MFAS,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={
                            **mfa_query
                        },
                        sort={"created_at": -1}
                    )

                # Defensive: mfa may be None when the seed didn't run.
                # The previous form `mfa_id = mfa.get(...)` raised
                # AttributeError on None BEFORE the `if not mfa` guard
                # fired — caller saw a 500 rather than the intended 404.
                if not mfa:
                    message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",accept_language)
                    raise HTTPException(status_code=404, detail=message)

                mfa_id =  mfa.get('id', None)
                if not mfa_id :
                    message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",accept_language)
                    raise HTTPException(status_code=404, detail=message)
                
                user_mfas_query = {
                    "filter__is_activated": True,
                    "filter__sys_user_id":user_details['id'], 
                    "filter__ref_mfa_id":mfa_id, 
                } 
                user_mfa = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    accept_language=accept_language,
                    query=user_mfas_query
                )
                # self.app_debug_print(f"\n\n user_mfa : {user_mfa}",True)
                if not user_mfa:
                    message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",accept_language)
                    raise HTTPException(status_code=404, detail=message)
                
                if not mfa or not mfa_id :
                    message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "MFA_NOT_FOUND",accept_language)
                    raise HTTPException(status_code=404, detail=message)
                
                secret = user_mfa.get('secret')
                if not secret:
                    raise HTTPException(status_code=404, detail="User not found")
                
                # Allow a valid window of 1 time-step before and after to account for clock skew.
                if GeneratorService.verify_totp_code(secret,param_totp):
                    message = ResponseService.get_response_message(MessageCategory.SUCCESS, "TOTP_ACTIVATED_SUCCESSFULLY",accept_language)
                    
                    # self.app_debug_print(f"message : {message}",True)
                    
                    await AppRedisService.remove_redis_value(sudo_action_key)
                    return {
                        "is_sudo_group_action":is_sudo_group_action,
                        "sudo_group_users":sudo_group_users,
                        "instruction_id":instructionId,
                        "can_proceed":True,
                    }
                else:
                    message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_TOTP_CODE",accept_language)
                    raise HTTPException(status_code=401, detail=message)
            else:
                return {
                    "is_sudo_group_action":is_sudo_group_action,
                    "sudo_group_users":sudo_group_users,
                    "instruction_id":instructionId,
                    "message": ResponseService.get_response_message(MessageCategory.COMMON, "NO_SUDO_ACTION_INSTRUCTION", accept_language),
                    "can_proceed":False,
                }
        else:
            # Don't create sudo_action_key here yet - instructionId might change for GOLDEN_NUMBER type
            DebugService.app_debug_print(f" INIT instructionId >> : {instructionId} ",True)
            if is_sudo_action == True:
                message = ResponseService.get_response_message(MessageCategory.SUCCESS, "SUDO_ACTION_IS_REQUIRED", accept_language)
                numbers = []
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

                    # IMPORTANT: instructionId gets overwritten here for GOLDEN_NUMBER type!
                    old_instructionId = instructionId
                    instructionId = random_golden_number['instruction_id']
                    random_selected_golden_number = random_golden_number['number']

                    DebugService.app_debug_print(f" GOLDEN_NUMBER: instructionId changed from {old_instructionId} to {instructionId} ",True)

                    sudo_action_key = RedisKeys.format_key(RedisKeys.SUDO_ACTION, instruction_id=instructionId)
                    DebugService.app_debug_print(f" GOLDEN_NUMBER: Final sudo_action_key >> : {sudo_action_key} ",True)
                    redis_data = {
                        "redis_data_key": sudo_action_key,
                        "redis_data_info": {
                            **event_data,
                            "api_consumer_key":api_Consumer['consumer_hash'],
                            "selected_golden_number":random_golden_number,
                            "status": "pending",
                            "instruction_id": instructionId,
                        },
                        "redis_expire_time":60 * 3,
                    }

                    totpAppApiConsumers = await generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.REF_API_CONSUMER,
                        output_data_type=OutputDataType.DEFAULT.value,
                        all_data=True,
                        page=0,
                        limit=10,
                        query={"filter__can_receive_totp_validation_push":True}, 
                        sort={'created_at':-1}
                    )

                    if totpAppApiConsumers:
                        DebugService.app_debug_print(f'\n\n\n totpAppApiConsumers  : {totpAppApiConsumers} \n\n\n',False)
                        for totpAppApiConsumer in totpAppApiConsumers:
                            user_account_socket_hash = f"{totpAppApiConsumer['consumer_hash']}___{user_account_socket_hash}"
                            result = await SecurityWebSocketService.send_event_to_client(user_account_socket_hash, event_data,redis_data)

                elif random_action['flag'] == ESudoActionTypeFlag.LOCAL_AUTH.value :
                    event_data = {
                        "type": "instruction",
                        "custom_type": random_action['flag'],
                        "params": {
                            "expected_action":EExpectedActionTypeFlag.SUDO_ACTION.value,
                            "instruction_id": instructionId,
                            "description": random_action['totp_app_description_str'],
                        }
                    }
                    sudo_action_key = RedisKeys.format_key(RedisKeys.SUDO_ACTION, instruction_id=instructionId)
                    DebugService.app_debug_print(f" LOCAL_AUTH: Final sudo_action_key >> : {sudo_action_key} ",True)
                    redis_data = {
                        "redis_data_key": sudo_action_key,
                        "redis_data_info": {
                            **event_data,
                            "api_consumer_key":api_Consumer['consumer_hash'],
                            "status": "pending",
                            "instruction_id": instructionId,
                        },
                        "redis_expire_time":60 * 3,
                    }
                    # totpAppApiConsumer = await generic_service.fetch_one_from_collection(
                    #     collection_key=CollectionKey.REF_API_CONSUMER,
                    #     output_data_type=OutputDataType.DEFAULT.value,
                    #     query={"filter__flag":'flutter_validation_and_totp_app_min_economies'},
                    #     sort={'created_at':-1}
                    # )

                    totpAppApiConsumers = await generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.REF_API_CONSUMER,
                            output_data_type=OutputDataType.DEFAULT.value,
                            all_data=True,
                            page=0,
                            limit=10,
                            query={"filter__can_receive_totp_validation_push":True}, 
                            sort={'created_at':-1}
                        )   

                    DebugService.app_debug_print(f" LOCAL_AUTH: totpAppApiConsumers found: {totpAppApiConsumers is not None} ",True)

                    if totpAppApiConsumers:
                        DebugService.app_debug_print(f'\n\n\n totpAppApiConsumers  : {totpAppApiConsumers} \n\n\n',False)
                        for totpAppApiConsumer in totpAppApiConsumers:
                            user_account_socket_hash = f"{totpAppApiConsumer['consumer_hash']}___{user_account_socket_hash}"
                            DebugService.app_debug_print(f" LOCAL_AUTH: About to call WebSocketService.send_event_to_client with hash: {user_account_socket_hash} ",True)
                            result = await SecurityWebSocketService.send_event_to_client(user_account_socket_hash, event_data,redis_data)
                        DebugService.app_debug_print(f" LOCAL_AUTH: WebSocketService.send_event_to_client completed ",True)
                    else:
                        DebugService.app_debug_print(f" LOCAL_AUTH: totpAppApiConsumer NOT FOUND - WebSocket service will NOT be called! ",True)
                elif random_action['flag'] == ESudoActionTypeFlag.TOTP.value :
                    event_data = {
                        "type": "instruction",
                        "custom_type": random_action['flag'],
                        "params": {
                            "instruction_id": instructionId,
                            "expected_action":EExpectedActionTypeFlag.SUDO_ACTION.value,
                            "description": random_action['totp_app_description_str'],
                        }
                    }
                    sudo_action_key = RedisKeys.format_key(RedisKeys.SUDO_ACTION, instruction_id=instructionId)
                    DebugService.app_debug_print(f" TOTP: Final sudo_action_key >> : {sudo_action_key} ",True)
                    redis_data = {
                        "redis_data_key": sudo_action_key,
                        "redis_data_info": {
                            **event_data,
                            "api_consumer_key":api_Consumer['consumer_hash'],
                            "status": "pending",
                            "instruction_id": instructionId,
                        },
                        "redis_expire_time":60 * 3,
                    }
                    totpAppApiConsumers = await generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.REF_API_CONSUMER,
                            output_data_type=OutputDataType.DEFAULT.value,
                            all_data=True,
                            page=0,
                            limit=10,
                            query={"filter__can_receive_totp_validation_push":True}, 
                            sort={'created_at':-1}
                        )   
                    if totpAppApiConsumers:
                        DebugService.app_debug_print(f'\n\n\n totpAppApiConsumers  : {totpAppApiConsumers} \n\n\n',False)
                        for totpAppApiConsumer in totpAppApiConsumers:
                            user_account_socket_hash = f"{totpAppApiConsumer['consumer_hash']}___{user_account_socket_hash}"
                            result = await SecurityWebSocketService.send_event_to_client(user_account_socket_hash, event_data,redis_data)
                    # totpAppApiConsumer = await generic_service.fetch_one_from_collection(
                    #     collection_key=CollectionKey.REF_API_CONSUMER,
                    #     output_data_type=OutputDataType.DEFAULT.value,
                    #     query={"filter__flag":'flutter_validation_and_totp_app_min_economies'},
                    #     sort={'created_at':-1}
                    # )

                    # if totpAppApiConsumer:
                    #     DebugService.app_debug_print(f'\n\n\n totpAppApiConsumer  : {totpAppApiConsumer} \n\n\n',False)
                    #     user_account_socket_hash = f"{totpAppApiConsumer['consumer_hash']}___{user_account_socket_hash}"
                    #     result = await SecurityWebSocketService.send_event_to_client(user_account_socket_hash, event_data,redis_data)

                return {
                    "is_sudo_action":True,
                    "message": message,
                    "instruction_id":instructionId,
                    "selected_golden_number":random_selected_golden_number,
                    "random_sudo_action_info": random_action,
                    "can_proceed":True,
                }
    return {
        "is_sudo_action":False,
        "is_sudo_group_action":is_sudo_group_action,
        "sudo_group_users":sudo_group_users,
        "instruction_id":instructionId,
        "message": ResponseService.get_response_message(MessageCategory.COMMON, "NO_SUDO_ACTION_INSTRUCTION", accept_language),
        "can_proceed":False,
    }