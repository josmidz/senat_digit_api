


import json
from typing import Any, Dict, Optional, Tuple

from fastapi import  HTTPException,Request, WebSocket, WebSocketDisconnect,status
from app.modules.auth.enums.mfa import MFaFlag
from app.modules.core.types.response import CustomJSONResponse
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.services.device.device_service import DeviceService
from app.modules.core.services.generator.generator_service import GeneratorService
from app.modules.core.services.hash.hash_service import HashService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.services.sms.sms_service import SmsService
from app.modules.core.enums.type_enum import  OutputDataType, EExpectedActionTypeFlag
from app.modules.core.constants.keys import RedisKeys

from app.modules.core.services.email_sender.email_sender_service import EMailSenderService
from app.modules.core.services.encryption.encryption_service import EncryptionService
from app.modules.auth.services.password.password_service import PasswordService
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.model.model_service import ModelService
# DebugService is inherited through EncryptionService
from app.modules import active_connections
from app.modules.core.services.redis.redis_service import AppRedisService
from app.modules.security.services.security_websocket_service import SecurityWebSocketService



class SecurityWebsocketController(
    AuthenticatedService,
    PasswordService,
    ResponseService,
    ConverterService,
    ModelService,
    SmsService,
    EncryptionService,  # This already inherits from DebugService, so we don't need DebugService separately
    EMailSenderService,
    DeviceService):
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.auth.services.login.login_service import LoginService
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.auth.services.token.token_service import TokenService
        
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        self.token_service = TokenService(accept_language)
        self.login_service = LoginService(accept_language)
        super().__init__(accept_language)

    async def _find_sudo_instruction_by_golden_instruction_id(
        self,
        user_id: str,
        golden_instruction_id: str
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Golden number clicks carry the nested golden instruction_id, while sudo Redis keys
        are stored with the parent instruction key: instruction:SUDO_ACTION:{user_id}_{instruction_key}.
        Resolve the parent sudo instruction by scanning user sudo keys and matching
        selected_golden_number.instruction_id.
        """
        if not user_id or not golden_instruction_id:
            return None, None

        pattern = RedisKeys.format_key(
            RedisKeys.SUDO_ACTION,
            instruction_id=f"{user_id}_*"
        )
        sudo_keys = await AppRedisService.get_keys_by_pattern(pattern)

        for key in sudo_keys:
            raw_value = await AppRedisService.get_str_redis_value(key)
            if not raw_value:
                continue

            try:
                sudo_payload = json.loads(raw_value)
            except Exception:
                continue

            selected_golden_number = sudo_payload.get('selected_golden_number', None)
            selected_instruction_id = (
                selected_golden_number.get('instruction_id', None)
                if isinstance(selected_golden_number, dict)
                else None
            )
            if selected_instruction_id == golden_instruction_id:
                return key, sudo_payload

        return None, None

    async def _deliver_pending_web_lock_if_needed(
        self,
        websocket: WebSocket,
        user_connection_hash: str,
    ) -> None:
        """
        On socket connect, enforce pending web lock status if it exists.
        The lock marker is one-time: after successful delivery to web client,
        the Redis key is removed.
        """
        if not user_connection_hash or "___" not in user_connection_hash:
            return

        connection_consumer_hash, raw_user_socket_hash = user_connection_hash.split("___", 1)
        if not raw_user_socket_hash:
            return

        lock_key = RedisKeys.format_key(
            RedisKeys.PENDING_WEB_SCREEN_LOCK,
            user_socket_hash=raw_user_socket_hash,
        )
        lock_payload_str = await AppRedisService.get_str_redis_value(lock_key)
        if not lock_payload_str:
            return

        try:
            lock_payload = json.loads(lock_payload_str)
        except Exception:
            # Corrupted payload; clear it to avoid endless retries.
            await AppRedisService.remove_redis_value(lock_key)
            return

        mobile_consumer_hashes = lock_payload.get("mobile_consumer_hashes", [])
        if isinstance(mobile_consumer_hashes, str):
            mobile_consumer_hashes = [mobile_consumer_hashes]
        if not isinstance(mobile_consumer_hashes, list):
            mobile_consumer_hashes = []

        triggered_by_consumer_hash = lock_payload.get("triggered_by_consumer_hash", "")

        # Never consume a web-lock marker from a mobile consumer reconnect.
        if (
            connection_consumer_hash in mobile_consumer_hashes
            or (triggered_by_consumer_hash and connection_consumer_hash == triggered_by_consumer_hash)
        ):
            return

        event_data = lock_payload.get("event_data", {})
        if not isinstance(event_data, dict) or not event_data:
            event_data = {
                "type": "instruction",
                "custom_type": EExpectedActionTypeFlag.LOCK_SCREEN.value,
                "params": {
                    "expected_action": EExpectedActionTypeFlag.LOCK_SCREEN.value,
                    "instruction_id": lock_payload.get("instruction_id", ""),
                    "description": "Lock screen instruction from pending redis status",
                },
            }

        await websocket.send_text(json.dumps(event_data))
        await AppRedisService.remove_redis_value(lock_key)
        self.app_debug_print(
            f"Delivered pending web lock instruction and cleared key: {lock_key}",
            True
        )
        
    async def websocket_endpoint(self,websocket: WebSocket):
        """
        WebSocket endpoint for real-time communication with users.
        
        Args:
            websocket: The WebSocket connection
            user_account_socket_hash: The unique hash identifying the user's socket connection
        """
        try:
            user_account_socket_hash = await self.token_service.get_user_account_socket_hash_from_params(websocket)
            self.app_debug_print(f"\n\n\n websocket u hash : {user_account_socket_hash} \n\n\n",True)
            user = await self.token_service.decode_and_get_user_from_socket_token(websocket)

            # If token validation failed, user is None and the WS was already
            # closed by _safe_websocket_close (which sends HTTP 403 before accept).
            # Do NOT continue — otherwise websocket.accept() would crash.
            if user is None:
                self.app_debug_print("WebSocket rejected: token validation failed (user is None)", True)
                return

            # api_consumer = await self.token_service.get_user_api_consumer_from_params(websocket)
            query_params = websocket.query_params
            accept_language = query_params.get("accept_language",DEFAULT_LANGUAGE)
            # Accept the connection
            await websocket.accept()
            self.app_debug_print(f"WebSocket connection accepted for hash: {user_account_socket_hash}",False)
            
            # Store the connection
            active_connections[user_account_socket_hash] = websocket

            # On reconnect, enforce pending web lock status (one-shot).
            try:
                await self._deliver_pending_web_lock_if_needed(websocket, user_account_socket_hash)
            except Exception as lock_reconnect_error:
                self.app_debug_print(
                    f"Error while delivering pending web lock status: {lock_reconnect_error}",
                    True
                )
            
            # Keep the connection alive and handle messages
            while True:
                # Wait for messages from the client
                data = await websocket.receive_text()
                try:
                    # Parse the message
                    message = json.loads(data)
                    # Echo back the message (for testing purposes)
                    self.app_debug_print(f"Received message: {message}",True)
                    event_type = message.get('type',None)
                    if event_type and event_type == 'instruction_response':
                        action = message.get('action',None) #"expected_action":EExpectedActionTypeFlag.UNLOCK_SCREEN.value,
                        data = message.get('data',None)
                        self.app_debug_print(f"Received action: {action}",True)
                        expected_action = message.get('expected_action',None)
                        self.app_debug_print(f"Received expected_action: {expected_action}",True)
                        if action and data:
                            instructionId = data.get('instruction_id',None)

                            # Use appropriate Redis key based on expected_action
                            if expected_action == EExpectedActionTypeFlag.SUDO_ACTION.value:
                                # Sudo actions are stored with "{user_id}_{instruction_id}" in Redis.
                                redis_local_key = RedisKeys.format_key(
                                    RedisKeys.SUDO_ACTION,
                                    instruction_id=f"{user.get('id')}_{instructionId}"
                                )
                            else:
                                redis_local_key = RedisKeys.format_key(
                                    RedisKeys.ACTIVE_INSTRUCTION,
                                    expected_action=expected_action,
                                    instruction_id=instructionId
                                )
                            self.app_debug_print(f"Received redis_local_key: {redis_local_key}",True)
                            if action == 'golden_number_clicked' and instructionId:
                                saved_instruction = await AppRedisService.get_str_redis_value(redis_local_key)
                                saved_instruction_json = json.loads(saved_instruction) if saved_instruction else None
                                if not saved_instruction_json and expected_action == EExpectedActionTypeFlag.SUDO_ACTION.value:
                                    resolved_key, resolved_payload = await self._find_sudo_instruction_by_golden_instruction_id(
                                        user_id=str(user.get('id', '')),
                                        golden_instruction_id=instructionId
                                    )
                                    if resolved_key and resolved_payload:
                                        redis_local_key = resolved_key
                                        saved_instruction_json = resolved_payload
                                        self.app_debug_print(
                                            f"WEBSOCKET_DEBUG: Resolved golden instruction to parent Redis key: {redis_local_key}",
                                            True
                                        )
                                golden_number_clicked = data.get('number',None)
                                self.app_debug_print(f"Received golden_number_clicked: {golden_number_clicked}",False)
                                self.app_debug_print(f"Received saved_instruction: {saved_instruction_json}",False)
                                #data >
                                if saved_instruction_json:
                                    savedApiConsumer = saved_instruction_json.get('api_consumer_key',None) if saved_instruction_json else None;
                                    selected_golden_number = saved_instruction_json.get('selected_golden_number',{}) if saved_instruction_json else None;
                                    selected_golden_instruction_id = selected_golden_number.get('instruction_id', None) if isinstance(selected_golden_number, dict) else None
                                    real_golden_number = (
                                        selected_golden_number.get('number',None)
                                        if isinstance(selected_golden_number, dict)
                                        else selected_golden_number
                                    )

                                    saved_instruction_id = (
                                        saved_instruction_json.get('instruction_id',None)
                                        or saved_instruction_json.get('instruction_key',None)
                                    ) if saved_instruction_json else None;

                                    # Get the ORIGINAL Angular app's hash from the saved instruction
                                    original_api_consumer_keys = saved_instruction_json.get('api_consumer_keys', []) if saved_instruction_json else []
                                    original_angular_hash = None
                                    key = saved_instruction_json.get('params',{}).get('api_consumer_key',None) if saved_instruction_json else None;
                                    if original_api_consumer_keys:
                                        # Find the Angular app hash (different from mobile app hash)
                                        mobile_hash_prefix = f"{user_account_socket_hash}".split("___")[0]
                                        original_angular_hash = f"{key}___{user_account_socket_hash.split('___')[-1]}"

                                    self.app_debug_print(f"WEBSOCKET_DEBUG: Original API consumer keys: {original_api_consumer_keys}", True)
                                    self.app_debug_print(f"WEBSOCKET_DEBUG: Calculated Angular hash: {original_angular_hash}", True)

                                    number_matches = str(real_golden_number) == str(golden_number_clicked)
                                    instruction_matches = (
                                        str(selected_golden_instruction_id) == str(instructionId)
                                        if selected_golden_instruction_id
                                        else True
                                    )

                                    if number_matches and instruction_matches:
                                        angular_instruction_id = saved_instruction_id or instructionId
                                        event_data = {
                                            "type": "instruction_response",
                                            "custom_type": "sudoActionValidated" if expected_action == EExpectedActionTypeFlag.SUDO_ACTION.value else "localAuth",
                                            "instruction_id":angular_instruction_id,
                                            "instruction_key": angular_instruction_id,
                                            "expected_action":expected_action,
                                            "status":"validated",
                                        }

                                        # UPDATE STATUS
                                        # Convert the dictionary to a JSON string before storing
                                        update_data = {
                                            **saved_instruction_json,
                                            "status": "validated",
                                        }
                                        update_data_str = json.dumps(update_data)  # Serialize to JSON string

                                        # Update Redis with validated status
                                        await AppRedisService.set_redis_value(redis_local_key, update_data_str, expiry=120)

                                        # Send to the ORIGINAL Angular app, not the mobile app
                                        angular_consumer_hash = saved_instruction_json.get('angular_consumer_hash', None)
                                        saved_user_socket_hash = saved_instruction_json.get('user_account_socket_hash', None)
                                        target_hash = (
                                            f"{angular_consumer_hash}___{saved_user_socket_hash}"
                                            if angular_consumer_hash and saved_user_socket_hash
                                            else (original_angular_hash if original_angular_hash else f"{savedApiConsumer}___{user_account_socket_hash.split('___')[-1]}")
                                        )
                                        self.app_debug_print(f"WEBSOCKET_DEBUG: About to send event to ANGULAR hash: {target_hash}", True)
                                        self.app_debug_print(f"WEBSOCKET_DEBUG: Event data: {event_data}", True)

                                        result = await SecurityWebSocketService.send_event_to_client(target_hash, event_data, None)
                                        self.app_debug_print(f"WEBSOCKET_DEBUG: Send result: {result}", True)

                            elif action == 'local_auth_succeeded' and instructionId:
                                #handle local authentication 
                                saved_instruction = await AppRedisService.get_str_redis_value(redis_local_key)
                                self.app_debug_print(f"Received saved_instruction: {saved_instruction}",True)
                                if saved_instruction: 
                                    saved_instruction_json = json.loads(saved_instruction)
                                    savedApiConsumer = saved_instruction_json.get('api_consumer_key',None) if saved_instruction_json else None;
                                    saved_instruction_id = (
                                        saved_instruction_json.get('instruction_id',None)
                                        or saved_instruction_json.get('instruction_key',None)
                                    ) if saved_instruction_json else None;

                                    # Get the ORIGINAL Angular app's hash from the saved instruction
                                    original_api_consumer_keys = saved_instruction_json.get('api_consumer_keys', []) if saved_instruction_json else []
                                    original_angular_hash = None;
                                    key = saved_instruction_json.get('params',{}).get('api_consumer_key',None) if saved_instruction_json else None;
                                    if original_api_consumer_keys:
                                        # Find the Angular app hash (different from mobile app hash)
                                        mobile_hash_prefix = f"{user_account_socket_hash}".split("___")[0]
                                        original_angular_hash = f"{key}___{user_account_socket_hash.split('___')[-1]}"
                                        # for key in original_api_consumer_keys:
                                        #     if key != mobile_hash_prefix:
                                        #         # This should be the Angular app hash
                                        #         original_angular_hash = f"{key}___{user_account_socket_hash.split('___')[-1]}"
                                        #         break

                                    # self.app_debug_print(f"WEBSOCKET_DEBUG: Mobile hash prefix: {mobile_hash_prefix}", True)
                                    self.app_debug_print(f"WEBSOCKET_DEBUG: Original API consumer keys: {original_api_consumer_keys}", True)
                                    self.app_debug_print(f"WEBSOCKET_DEBUG: Calculated Angular hash: {original_angular_hash}", True)

                                    if saved_instruction_id == instructionId:
                                        angular_instruction_id = saved_instruction_id or instructionId
                                        event_data = {
                                            "type": "instruction_response",
                                            "custom_type": "sudoActionValidated" if expected_action == EExpectedActionTypeFlag.SUDO_ACTION.value else "localAuth",
                                            "instruction_id": angular_instruction_id,
                                            "instruction_key": angular_instruction_id,
                                            "expected_action": expected_action,
                                            "status": "validated",
                                        }

                                        # UPDATE STATUS
                                        # Convert the dictionary to a JSON string before storing
                                        update_data = {
                                            **saved_instruction_json,
                                            "status": "validated",
                                        }
                                        update_data_str = json.dumps(update_data)  # Serialize to JSON string

                                        # Update Redis with validated status
                                        await AppRedisService.set_redis_value(redis_local_key, update_data_str, expiry=120)

                                        # Send to the ORIGINAL Angular app, not the mobile app
                                        angular_consumer_hash = saved_instruction_json.get('angular_consumer_hash', None)
                                        saved_user_socket_hash = saved_instruction_json.get('user_account_socket_hash', None)
                                        target_hash = (
                                            f"{angular_consumer_hash}___{saved_user_socket_hash}"
                                            if angular_consumer_hash and saved_user_socket_hash
                                            else (original_angular_hash if original_angular_hash else f"{savedApiConsumer}___{user_account_socket_hash.split('___')[-1]}")
                                        )
                                        self.app_debug_print(f"WEBSOCKET_DEBUG: About to send event to ANGULAR hash: {target_hash}", True)
                                        self.app_debug_print(f"WEBSOCKET_DEBUG: Event data: {event_data}", True)

                                        result = await SecurityWebSocketService.send_event_to_client(target_hash, event_data, None)
                                        self.app_debug_print(f"WEBSOCKET_DEBUG: Send result: {result}", True)

                                        
                            elif action == 'totp_validation_succeeded' and instructionId:
                                #handle totp validation succeeded
                                saved_instruction = await AppRedisService.get_str_redis_value(redis_local_key)
                                totp_code = data.get('totp_code',None)
                                self.app_debug_print(f"Received totp_validation_succeeded with code: {totp_code}",True)
                                if saved_instruction:
                                    saved_instruction_json = json.loads(saved_instruction)
                                    savedApiConsumer = saved_instruction_json.get('api_consumer_key',None) if saved_instruction_json else None;
                                    saved_instruction_id = (
                                        saved_instruction_json.get('instruction_id',None)
                                        or saved_instruction_json.get('instruction_key',None)
                                    ) if saved_instruction_json else None;

                                    # Get the ORIGINAL Angular app's hash from the saved instruction
                                    original_api_consumer_keys = saved_instruction_json.get('api_consumer_keys', []) if saved_instruction_json else []
                                    original_angular_hash = None
                                    key = saved_instruction_json.get('params',{}).get('api_consumer_key',None) if saved_instruction_json else None;
                                    if original_api_consumer_keys:
                                        # Find the Angular app hash (different from mobile app hash)
                                        mobile_hash_prefix = f"{user_account_socket_hash}".split("___")[0]
                                        original_angular_hash = f"{key}___{user_account_socket_hash.split('___')[-1]}"

                                    self.app_debug_print(f"WEBSOCKET_DEBUG: Original API consumer keys: {original_api_consumer_keys}", True)
                                    self.app_debug_print(f"WEBSOCKET_DEBUG: Calculated Angular hash: {original_angular_hash}", True)

                                    if totp_code and saved_instruction_id == instructionId:
                                        angular_instruction_id = saved_instruction_id or instructionId
                                        event_data = {
                                            "type": "instruction_response",
                                            "custom_type": "sudoActionValidated" if expected_action == EExpectedActionTypeFlag.SUDO_ACTION.value else "localAuth",
                                            "instruction_id": angular_instruction_id,
                                            "instruction_key": angular_instruction_id,
                                            "expected_action": expected_action,
                                            "status": "validated",
                                        }

                                        # UPDATE STATUS
                                        # Convert the dictionary to a JSON string before storing
                                        update_data = {
                                            **saved_instruction_json,
                                            "status": "validated",
                                        }
                                        update_data_str = json.dumps(update_data)  # Serialize to JSON string

                                        # Update Redis with validated status
                                        await AppRedisService.set_redis_value(redis_local_key, update_data_str, expiry=120)

                                        # Send to the ORIGINAL Angular app, not the mobile app
                                        angular_consumer_hash = saved_instruction_json.get('angular_consumer_hash', None)
                                        saved_user_socket_hash = saved_instruction_json.get('user_account_socket_hash', None)
                                        target_hash = (
                                            f"{angular_consumer_hash}___{saved_user_socket_hash}"
                                            if angular_consumer_hash and saved_user_socket_hash
                                            else (original_angular_hash if original_angular_hash else f"{savedApiConsumer}___{user_account_socket_hash.split('___')[-1]}")
                                        )
                                        self.app_debug_print(f"WEBSOCKET_DEBUG: About to send event to ANGULAR hash: {target_hash}", True)
                                        self.app_debug_print(f"WEBSOCKET_DEBUG: Event data: {event_data}", True)

                                        result = await SecurityWebSocketService.send_event_to_client(target_hash, event_data, None)
                                        self.app_debug_print(f"WEBSOCKET_DEBUG: Send result: {result}", True)

                            elif action == 'totp_number_clicked' and instructionId:
                                #handle totp number clicked
                                saved_instruction = await AppRedisService.get_str_redis_value(redis_local_key)
                                totp_number_clicked = data.get('number',None)
                                self.app_debug_print(f"Received totp_number_clicked: {totp_number_clicked}",True)
                                self.app_debug_print(f"Received totp_number_clicked: {totp_number_clicked}",True)
                                if saved_instruction:
                                    saved_instruction_json = json.loads(saved_instruction)
                                    savedApiConsumer = saved_instruction_json.get('api_consumer_key',None) if saved_instruction_json else None;
                                    saved_instruction_id = (
                                        saved_instruction_json.get('instruction_id',None)
                                        or saved_instruction_json.get('instruction_key',None)
                                    ) if saved_instruction_json else None;

                                    # Get the ORIGINAL Angular app's hash from the saved instruction
                                    original_api_consumer_keys = saved_instruction_json.get('api_consumer_keys', []) if saved_instruction_json else []
                                    original_angular_hash = None
                                    key = saved_instruction_json.get('params',{}).get('api_consumer_key',None) if saved_instruction_json else None;
                                    if original_api_consumer_keys:
                                        # Find the Angular app hash (different from mobile app hash)
                                        mobile_hash_prefix = f"{user_account_socket_hash}".split("___")[0]
                                        original_angular_hash = f"{key}___{user_account_socket_hash.split('___')[-1]}"

                                    self.app_debug_print(f"WEBSOCKET_DEBUG: Original API consumer keys: {original_api_consumer_keys}", True)
                                    self.app_debug_print(f"WEBSOCKET_DEBUG: Calculated Angular hash: {original_angular_hash}", True)

                                    if totp_number_clicked and saved_instruction_id == instructionId:
                                        
                                        # START TOTP VALIDATION
                                        mfa_query = {
                                            "filter__is_activated": True,
                                            "filter__flag": MFaFlag.SYCAMORE_2FA_APP, 
                                        }
                                        mfa = await self.generic_service.fetch_one_from_collection(
                                            collection_key=CollectionKey.REF_MFAS,
                                            output_data_type=OutputDataType.DEFAULT.value,
                                            query={
                                                **mfa_query
                                            },
                                            sort={"created_at": -1}
                                        )
                                        mfa_id =  mfa.get('id', None)
                                        user_mfas_query = {
                                            "filter__is_activated": True,
                                            "filter__sys_user_id":user['id'], 
                                            "filter__ref_mfa_id":mfa_id, 
                                        } 
                                        user_mfa = await self.generic_service.fetch_one_from_collection(
                                            collection_key=CollectionKey.CFG_USER_MFA,
                                            accept_language=accept_language,
                                            query=user_mfas_query
                                        )
                                        secret = user_mfa.get('secret') if user_mfa else None
                                        if secret and GeneratorService.verify_totp_code(secret, totp_number_clicked):
                                            angular_instruction_id = saved_instruction_id or instructionId
                                            event_data = {
                                                "type": "instruction_response",
                                                "custom_type": "sudoActionValidated" if expected_action == EExpectedActionTypeFlag.SUDO_ACTION.value else "localAuth",
                                                "instruction_id":angular_instruction_id,
                                                "instruction_key": angular_instruction_id,
                                                "expected_action":expected_action,
                                                "status":"validated",
                                            }

                                            # UPDATE STATUS
                                            # Convert the dictionary to a JSON string before storing
                                            update_data = {
                                                **saved_instruction_json,
                                                "status": "validated",
                                            }
                                            update_data_str = json.dumps(update_data)  # Serialize to JSON string

                                            # Update Redis with validated status
                                            await AppRedisService.set_redis_value(redis_local_key, update_data_str, expiry=120)

                                            # Send to the ORIGINAL Angular app, not the mobile app
                                            angular_consumer_hash = saved_instruction_json.get('angular_consumer_hash', None)
                                            saved_user_socket_hash = saved_instruction_json.get('user_account_socket_hash', None)
                                            target_hash = (
                                                f"{angular_consumer_hash}___{saved_user_socket_hash}"
                                                if angular_consumer_hash and saved_user_socket_hash
                                                else (original_angular_hash if original_angular_hash else f"{savedApiConsumer}___{user_account_socket_hash.split('___')[-1]}")
                                            )
                                            self.app_debug_print(f"WEBSOCKET_DEBUG: About to send event to ANGULAR hash: {target_hash}", True)
                                            self.app_debug_print(f"WEBSOCKET_DEBUG: Event data: {event_data}", True)

                                            result = await SecurityWebSocketService.send_event_to_client(target_hash, event_data, None)
                                            self.app_debug_print(f"WEBSOCKET_DEBUG: Send result: {result}", True)
                                
                        
                    
                    # Echo back the message (for testing purposes)
                    await websocket.send_text(json.dumps({"status": "received", "message": message}))
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({"error": "Invalid JSON format"}))
        except WebSocketDisconnect:
            # Remove the connection when the client disconnects
            if user_account_socket_hash in active_connections:
                del active_connections[user_account_socket_hash]
                self.app_debug_print(f"WebSocket connection closed for hash: {user_account_socket_hash}",True)

    async def push_notification(
        self,
        request:Request,
        user_id: str, notification: dict):
        """
        Push a notification to a specific user via their WebSocket connection.
        
        Args:
            user_id: The ID of the user to send the notification to
            notification: The notification data to send
            current_user: The authenticated user making the request
        """
        try:
            # self.app_debug_print(f"\n\n\n in push_notification \n\n\n",True)
            # # get user_account_socket_hash as param
            user_account_socket_hash = await self.token_service.get_user_account_socket_hash_from_params(request)

            current_user = await self.token_service.decode_and_get_user_from_token(request)
            # Fetch the user to get their socket hash
            user = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                query={"filter___id": user_id}
            )
            
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            
            # Get or generate the user's socket hash
            user_account_socket_hash = user.get('user_account_socket_hash')
            if not user_account_socket_hash:
                # Generate a new socket hash if one doesn't exist
                user_account_socket_hash = HashService.generate_hash(user_id)
                
                # Update the user with the new socket hash
                await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.SYS_USER,
                    item_id=user_id,
                    data={"user_account_socket_hash": user_account_socket_hash}
                )
            
            # Check if the user is connected
            if user_account_socket_hash in active_connections:
                # Send the notification via WebSocket
                websocket = active_connections[user_account_socket_hash]
                await websocket.send_text(json.dumps(notification))
                return {"status": "success", "message": "Notification sent"}
            else:
                # Store the notification in Redis for later delivery using standardized keys
                event_id = notification.get('id', HashService.generate_hash(str(notification))[:8])
                notification_key = RedisKeys.format_key(RedisKeys.PENDING_NOTIFICATION, user_hash=user_account_socket_hash, event_id=event_id)
                await AppRedisService.set_redis_value(notification_key, json.dumps(notification), expiry=86400)  # Store for 24 hours
                return {"status": "queued", "message": "User not connected, notification queued"}
        
        except Exception as e:
            self.app_debug_print(f"Error pushing notification: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get_pending_notifications(
        self,
        request:Request,
        consume: bool = False,
        ):
        """
        Retrieve pending notifications and events for a user.
        This method retrieves events that were stored when the client was disconnected,
        based on the same patterns used in send_event_to_client().

        Args:
            user_account_socket_hash: The user's socket hash
            current_user: The authenticated user making the request
        """
        try:
            user_account_socket_hash = await self.token_service.get_user_account_socket_hash_from_params(request)
            
            current_user = await self.token_service.decode_and_get_user_from_token(request)
            if not user_account_socket_hash:
                user_account_socket_hash = current_user.get('user_account_socket_hash', '')
            raw_user_socket_hash = user_account_socket_hash.split("___")[-1] if user_account_socket_hash else ''

            # Get all pending events for this user from Redis
            # This includes both notifications and instruction events
            all_events = []

            # 1. Get regular notifications using standardized pattern
            notification_patterns = set()
            if user_account_socket_hash:
                notification_patterns.add(f"event:notification:{user_account_socket_hash}:*")
            if raw_user_socket_hash:
                notification_patterns.add(f"event:notification:{raw_user_socket_hash}:*")
                notification_patterns.add(f"event:notification:*___{raw_user_socket_hash}:*")

            notification_keys = set()
            for notification_pattern in notification_patterns:
                for key in (await AppRedisService.get_keys_by_pattern(notification_pattern) or []):
                    notification_keys.add(key)

            # Fallback scan: robust against pattern mismatches across Redis variants.
            if not notification_keys and raw_user_socket_hash:
                fallback_notification_keys = await AppRedisService.get_keys_by_pattern("event:notification:*") or []
                for key in fallback_notification_keys:
                    try:
                        middle = key[len("event:notification:"):].rsplit(":", 1)[0]
                    except Exception:
                        middle = ""
                    if middle == raw_user_socket_hash or middle.endswith(f"___{raw_user_socket_hash}"):
                        notification_keys.add(key)

            for key in notification_keys:
                notification_data = await AppRedisService.get_str_redis_value(key)
                if notification_data:
                    try:
                        notification = json.loads(notification_data)
                        all_events.append({
                            "type": "notification",
                            "redis_key": key,
                            "data": notification
                        })
                        if consume:
                            await AppRedisService.delete_redis_key(key)
                    except json.JSONDecodeError:
                        self.app_debug_print(f"Error parsing notification data: {notification_data}")

            # 2. Get pending instruction events using standardized pattern
            instruction_patterns = set()
            if user_account_socket_hash:
                instruction_patterns.add(f"event:instruction:{user_account_socket_hash}:*")
            if raw_user_socket_hash:
                instruction_patterns.add(f"event:instruction:{raw_user_socket_hash}:*")
                instruction_patterns.add(f"event:instruction:*___{raw_user_socket_hash}:*")

            instruction_keys = set()
            for instruction_pattern in instruction_patterns:
                for key in (await AppRedisService.get_keys_by_pattern(instruction_pattern) or []):
                    instruction_keys.add(key)

            # Fallback scan: robust against pattern mismatches across Redis variants.
            if not instruction_keys and raw_user_socket_hash:
                fallback_instruction_keys = await AppRedisService.get_keys_by_pattern("event:instruction:*") or []
                for key in fallback_instruction_keys:
                    try:
                        middle = key[len("event:instruction:"):].rsplit(":", 1)[0]
                    except Exception:
                        middle = ""
                    if middle == raw_user_socket_hash or middle.endswith(f"___{raw_user_socket_hash}"):
                        instruction_keys.add(key)

            for key in instruction_keys:
                instruction_data = await AppRedisService.get_str_redis_value(key)
                if instruction_data:
                    try:
                        instruction_payload = json.loads(instruction_data)
                        event_data = instruction_payload.get('event_data', {})
                        redis_data = instruction_payload.get('redis_data', {})

                        all_events.append({
                            "type": "instruction",
                            "redis_key": key,
                            "data": event_data,
                            "redis_data": redis_data,
                            "instruction_id": event_data.get('params', {}).get('instruction_id'),
                            "expected_action": event_data.get('params', {}).get('expected_action'),
                            "custom_type": event_data.get('custom_type'),
                            "status": redis_data.get('redis_data_info', {}).get('status', 'pending') if redis_data else 'pending'
                        })
                        if consume:
                            await AppRedisService.delete_redis_key(key)
                    except json.JSONDecodeError:
                        self.app_debug_print(f"Error parsing instruction data: {instruction_data}")

            # 3. Get active instruction events (for backward compatibility with existing patterns)
            # These are stored with patterns like: "instruction:UNLOCK_SCREEN:instruction_id", etc.
            active_instruction_patterns = [
                "instruction:UNLOCK_SCREEN:*",
                "instruction:TOTP_VALIDATION:*",
                "instruction:LOCAL_AUTH:*",
                "instruction:SUDO_ACTION:*",
            ]

            for pattern in active_instruction_patterns:
                active_keys = await AppRedisService.get_keys_by_pattern(pattern)

                for key in active_keys:
                    instruction_data = await AppRedisService.get_str_redis_value(key)
                    if instruction_data:
                        try:
                            instruction = json.loads(instruction_data)
                            # Check if this instruction is for the current user
                            instruction_user_hash = instruction.get('user_account_socket_hash', '')
                            api_consumer_key = instruction.get('api_consumer_key', '')

                            # Check if this instruction belongs to the current user
                            hash_candidates = {h for h in [user_account_socket_hash, raw_user_socket_hash] if h}
                            belongs_to_user = any(
                                instruction_user_hash == candidate or
                                instruction_user_hash.endswith(f"___{candidate}") or
                                f"{api_consumer_key}___{candidate}" == instruction_user_hash
                                for candidate in hash_candidates
                            )

                            if belongs_to_user:

                                all_events.append({
                                    "type": "active_instruction",
                                    "redis_key": key,
                                    "data": instruction,
                                    "instruction_id": instruction.get('instruction_id'),
                                    "expected_action": instruction.get('expected_action'),
                                    "status": instruction.get('status', 'pending')
                                })
                        except json.JSONDecodeError:
                            self.app_debug_print(f"Error parsing active instruction data: {instruction_data}")

            # 3. Sort events by creation time if available
            # You might want to add timestamp to your Redis data for better sorting

            self.app_debug_print(
                f"Retrieved {len(all_events)} pending events for {user_account_socket_hash} raw={raw_user_socket_hash} (consume={consume})"
            )
            self.app_debug_print(
                f"PENDING_DEBUG notification_keys={len(notification_keys)} instruction_keys={len(instruction_keys)} "
                f"notification_patterns={list(notification_patterns)} instruction_patterns={list(instruction_patterns)}"
            )

            return {
                "events": all_events,
                "total_count": len(all_events),
                "notifications_count": len([e for e in all_events if e["type"] == "notification"]),
                "instructions_count": len([e for e in all_events if e["type"] == "instruction"])
            }

        except Exception as e:
            self.app_debug_print(f"Error retrieving pending notifications: {str(e)}")
            return {
                "events": [],
                "total_count": 0,
                "notifications_count": 0,
                "instructions_count": 0,
                "error": str(e)
            }

    async def clear_pending_notifications(
        self,
        request: Request,
        user_account_socket_hash: str,
        event_ids: list = None):
        """
        Clear specific pending notifications/events for a user after they've been processed.

        Args:
            user_account_socket_hash: The user's socket hash
            event_ids: Optional list of specific Redis keys to clear. If None, clears all.
            current_user: The authenticated user making the request
        """
        try:
            current_user = await self.token_service.decode_and_get_user_from_token(request)

            cleared_count = 0

            if event_ids:
                # Clear specific events
                for event_id in event_ids:
                    # Verify the event belongs to this user before deleting
                    if (event_id.startswith(f"notification:{user_account_socket_hash}:") or
                        await self._verify_instruction_belongs_to_user(event_id, user_account_socket_hash)):
                        await AppRedisService.delete_redis_key(event_id)
                        cleared_count += 1
            else:
                # Clear all notifications for this user
                notification_pattern = f"notification:{user_account_socket_hash}:*"
                notification_keys = await AppRedisService.get_keys_by_pattern(notification_pattern)

                for key in notification_keys:
                    await AppRedisService.delete_redis_key(key)
                    cleared_count += 1

            self.app_debug_print(f"Cleared {cleared_count} pending events for {user_account_socket_hash}")

            return {
                "status": "success",
                "cleared_count": cleared_count,
                "message": f"Cleared {cleared_count} pending events"
            }

        except Exception as e:
            self.app_debug_print(f"Error clearing pending notifications: {str(e)}")
            return {
                "status": "error",
                "cleared_count": 0,
                "error": str(e)
            }

    async def _verify_instruction_belongs_to_user(self, redis_key: str, user_account_socket_hash: str) -> bool:
        """
        Helper method to verify if an instruction Redis key belongs to the specified user.

        Args:
            redis_key: The Redis key to check
            user_account_socket_hash: The user's socket hash

        Returns:
            bool: True if the instruction belongs to the user, False otherwise
        """
        try:
            instruction_data = await AppRedisService.get_str_redis_value(redis_key)
            if instruction_data:
                instruction = json.loads(instruction_data)
                instruction_user_hash = instruction.get('user_account_socket_hash', '')
                api_consumer_key = instruction.get('api_consumer_key', '')

                return (instruction_user_hash == user_account_socket_hash or
                        instruction_user_hash.endswith(f"___{user_account_socket_hash}") or
                        f"{api_consumer_key}___{user_account_socket_hash}" == instruction_user_hash)
            return False
        except:
            return False
        

    async def send_pong(
        self,
        request:Request,
        ):
        """
        Send a 'pong' message to a specific user via their WebSocket connection.
        This is an example endpoint for testing WebSocket functionality.
        
        Args:
            user_account_socket_hash: The unique hash identifying the user's socket connection
        """
        try:
            user_account_socket_hash = await self.token_service.get_user_account_socket_hash_from_params(request)
            current_user = await  self.token_service.decode_and_get_user_from_token(request)
            
            # Check if the user is connected
            if user_account_socket_hash in active_connections:
                # Send the pong message via WebSocket
                websocket = active_connections[user_account_socket_hash]
                pong_message = {"type": "pong", "message": "Server pong response"}
                await websocket.send_text(json.dumps(pong_message))
                self.app_debug_print(f"Pong message sent to {user_account_socket_hash}",True)
                return {"status": "success", "message": "Pong message sent"}
            else:
                # Store the pong message in Redis for later delivery using standardized keys
                pong_message = {"type": "pong", "message": "Server pong response"}
                event_id = HashService.generate_hash('pong')[:8]
                message_key = RedisKeys.format_key(RedisKeys.PENDING_NOTIFICATION, user_hash=user_account_socket_hash, event_id=event_id)
                await AppRedisService.set_redis_value(message_key, json.dumps(pong_message), expiry=86400)  # Store for 24 hours
                self.app_debug_print(f"User not connected, pong message queued for {user_account_socket_hash}",True)
                return {"status": "queued", "message": "User not connected, pong message queued"}
        
        except Exception as e:
            self.app_debug_print(f"Error sending pong message: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        
        
    async def send_action(
        self,
        request:Request,
        data: Dict[str, Any]):
        """
        Send a 'pong' message to a specific user via their WebSocket connection.
        This is an example endpoint for testing WebSocket functionality.
        
        Args:
            user_account_socket_hash: The unique hash identifying the user's socket connection
        """
        try:
            user_account_socket_hash = await self.token_service.get_user_account_socket_hash_from_params(request)
            current_user = await  self.token_service.decode_and_get_user_from_token(request)
            # Check if the user is connected
            if user_account_socket_hash in active_connections:
                # Send the pong message via WebSocket
                websocket = active_connections[user_account_socket_hash]
                pong_message = data # {"type": "pong", "message": "Server pong response"}
                await websocket.send_text(json.dumps(pong_message))
                self.app_debug_print(f"data :{data} message sent to {user_account_socket_hash}",True)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "status": "success",
                        "data":data,
                        "message":  "User message sent",
                    }
                )
            else:
                # Store the action message in Redis for later delivery using standardized keys
                action_message = data
                event_id = HashService.generate_hash('action')[:8]
                message_key = RedisKeys.format_key(RedisKeys.PENDING_NOTIFICATION, user_hash=user_account_socket_hash, event_id=event_id)
                await AppRedisService.set_redis_value(message_key, json.dumps(action_message), expiry=86400)  # Store for 24 hours
                self.app_debug_print(f"User not connected, data : {data} message queued for {user_account_socket_hash}",True)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "status": "queued",
                        "data":data,
                        "message":  "User not connected, pong message queued",
                    }
                )
        
        except Exception as e:
            self.app_debug_print(f"Error sending pong message: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        

        
        
        
        
        
        
        
    
