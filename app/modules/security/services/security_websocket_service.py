import json
from typing import Dict, Any, Optional, List
from fastapi import WebSocket, HTTPException, status
from app.modules.core.types.response import CustomJSONResponse

# Import the active_connections dictionary from the connection store
from app.modules import active_connections
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.hash.hash_service import HashService
from app.modules.core.services.redis.redis_service import AppRedisService
from app.modules.core.constants.keys import RedisKeys

class SecurityWebSocketService:
    """
    Service for managing WebSocket connections and sending events to clients.
    """

    @staticmethod
    async def send_event_to_client(user_account_socket_hash: str, data: Dict[str, Any],redis_data:Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send an event to a specific client using their account socket hash.

        Args:
            user_account_socket_hash: The unique hash identifying the user's socket connection
            data: The data to send to the client

        Returns:
            Dict containing status and message
        """
        try:
            DebugService.app_debug_print(f"redis_data >>> > BEFORE SAVE {redis_data}\n\n\n\n", False)
            DebugService.app_debug_print(f"json.dumps(data) > {json.dumps(data)}", False)
            DebugService.app_debug_print(f"\n\n user_account_socket_hash >>>>> BEFORE SAVE {user_account_socket_hash}\n\n\n\n", False)
            # Check if the user is connected
            DebugService.app_debug_print(f"WEBSOCKET_DEBUG: Checking connection for hash: {user_account_socket_hash}", True)
            DebugService.app_debug_print(f"WEBSOCKET_DEBUG: Active connections: {list(active_connections.keys())}", True)
            DebugService.app_debug_print(f"Event sent to client: BEFORE SAVE {user_account_socket_hash}", False)
            # Handle Redis data if provided (for instruction type messages)
            custom_type = data.get('custom_type', None)
            event_type = data.get('type', None)
            DebugService.app_debug_print(f"event_type: BEFORE SAVE {event_type}", False)
            DebugService.app_debug_print(f"custom_type: BEFORE SAVE {custom_type}", False)

            if custom_type and event_type and event_type == 'instruction':
                DebugService.app_debug_print(f"Processing instruction type message", False)
                instruction_id = data.get('params', {}).get('instruction_id', None)
                if not instruction_id and redis_data:
                    instruction_id = redis_data.get('redis_data_info',{}).get('instruction_id', None)
                DebugService.app_debug_print(f"WEBSOCKET_DEBUG: CONNECTED PATH - instruction_id: {instruction_id}", True)

                if instruction_id and redis_data:
                    DebugService.app_debug_print(f"Saving Redis data for instruction", False)
                    redis_data_key = redis_data.get('redis_data_key','')
                    redis_data_info = redis_data.get('redis_data_info','')
                    redis_expire_time = redis_data.get('redis_expire_time',120)
                    DebugService.app_debug_print(f" redis_data_key: {redis_data_key}", False)
                    DebugService.app_debug_print(f" redis_data_info: {redis_data_info}", False)
                    DebugService.app_debug_print(f" redis_expire_time: {redis_expire_time}", False)
                    if redis_data_key and redis_data_info:
                        DebugService.app_debug_print(f"WEBSOCKET_DEBUG: CONNECTED PATH - About to save Redis key: {redis_data_key}", True)
                        await AppRedisService.set_redis_value(str(redis_data_key).strip(), json.dumps(redis_data_info), expiry=redis_expire_time)
                        DebugService.app_debug_print(f"WEBSOCKET_DEBUG: CONNECTED PATH - Redis save completed for key: {redis_data_key}", True)

            # Always attempt to send WebSocket message regardless of data structure
            if user_account_socket_hash in active_connections:
                # Send the message via WebSocket
                websocket = active_connections[user_account_socket_hash]
                message_to_send = json.dumps(data)
                DebugService.app_debug_print(f"WEBSOCKET_DEBUG: Sending message to client: {message_to_send}", True)
                await websocket.send_text(message_to_send)
                DebugService.app_debug_print(f"WEBSOCKET_DEBUG: Message sent successfully to {user_account_socket_hash}", True)
                status_message = "Event sent to client"
                event_status = "success"
            else:
                # User is disconnected - store event for later delivery using standardized keys
                DebugService.app_debug_print(f"WEBSOCKET_DEBUG: User {user_account_socket_hash} not connected, queuing event", True)
                await SecurityWebSocketService._store_event_for_disconnected_user(user_account_socket_hash, data, redis_data)
                status_message = "User not connected, event queued for later delivery"
                event_status = "queued"

            return CustomJSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "status_code": status.HTTP_201_CREATED,
                        "status": event_status,
                        "message": status_message,
                        "data": data
                    }
                )
        except Exception as e:
            DebugService.app_debug_print(f"Error sending event to client: {str(e)}",True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send event: {str(e)}"
            )

    @staticmethod
    async def _store_event_for_disconnected_user(
        user_account_socket_hash: str,
        event_data: Dict[str, Any],
        redis_data: Optional[Dict[str, Any]] = None
    ):
        """
        Store events for disconnected users using standardized Redis key patterns.

        Args:
            user_account_socket_hash: The user's socket hash
            event_data: The event data to store
            redis_data: Optional Redis data with additional context
        """
        try:
            event_type = event_data.get('type', 'unknown')
            custom_type = event_data.get('custom_type', None)

            if event_type == 'instruction' and custom_type:
                # This is an instruction event - store using instruction pattern
                instruction_id = None

                # Try to get instruction_id from various sources
                if event_data.get('params', {}).get('instruction_id'):
                    instruction_id = event_data['params']['instruction_id']
                elif redis_data and redis_data.get('redis_data_info', {}).get('instruction_id'):
                    instruction_id = redis_data['redis_data_info']['instruction_id']

                if instruction_id:
                    # Use standardized instruction key pattern
                    pending_key = RedisKeys.format_key(
                        RedisKeys.PENDING_INSTRUCTION,
                        user_hash=user_account_socket_hash,
                        instruction_id=instruction_id
                    )

                    # Store the complete event data
                    event_payload = {
                        "event_data": event_data,
                        "redis_data": redis_data,
                        "stored_at": HashService.generate_hash(str(event_data))[:8],  # Simple timestamp alternative
                        "user_hash": user_account_socket_hash
                    }

                    expiry = 86400  # Default 24 hours
                    if redis_data and redis_data.get('redis_expire_time'):
                        expiry = redis_data['redis_expire_time']

                    await AppRedisService.set_redis_value(
                        pending_key,
                        json.dumps(event_payload),
                        expiry=expiry
                    )

                    DebugService.app_debug_print(f"Stored instruction event for disconnected user: {pending_key}", True)
                else:
                    DebugService.app_debug_print("No instruction_id found, cannot store instruction event", True)
            else:
                # This is a regular notification - store using notification pattern
                event_id = HashService.generate_hash(str(event_data))[:8]
                pending_key = RedisKeys.format_key(
                    RedisKeys.PENDING_NOTIFICATION,
                    user_hash=user_account_socket_hash,
                    event_id=event_id
                )

                await AppRedisService.set_redis_value(
                    pending_key,
                    json.dumps(event_data),
                    expiry=86400  # 24 hours
                )

                DebugService.app_debug_print(f"Stored notification event for disconnected user: {pending_key}", True)

        except Exception as e:
            DebugService.app_debug_print(f"Error storing event for disconnected user: {str(e)}", True)

    @staticmethod
    async def get_connection_status(user_account_socket_hash: str) -> Dict[str, Any]:
        """
        Check if a client is currently connected.

        Args:
            user_account_socket_hash: The unique hash identifying the user's socket connection

        Returns:
            Dict containing connection status
        """
        is_connected = user_account_socket_hash in active_connections

        return {
            "is_connected": is_connected,
            "user_account_socket_hash": user_account_socket_hash
        }

    @staticmethod
    async def send_event_to_target_consumers(
        user_socket_hash: str,
        consumer_hashes: List[str],
        event_data: Dict[str, Any],
        redis_data: Optional[Dict[str, Any]] = None,
        source_consumer_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an event to multiple target consumers for a given user.
        Each consumer connection key is: [consumer_hash]___[user_socket_hash]
        
        Args:
            user_socket_hash: The raw user_account_socket_hash (without consumer prefix)
            consumer_hashes: List of consumer_hash values to send to
            event_data: The event data to send
            redis_data: Optional Redis data for instruction events
            source_consumer_hash: The consumer_hash of the sender (to skip sending back to sender)
        
        Returns:
            Dict with results per consumer
        """
        results = {}
        for consumer_hash in consumer_hashes:
            # Skip sending back to the source consumer
            if source_consumer_hash and consumer_hash == source_consumer_hash:
                continue
            
            target_key = f"{consumer_hash}___{user_socket_hash}"
            DebugService.app_debug_print(
                f"WEBSOCKET_DEBUG: Sending to consumer target_key: {target_key}", True
            )
            try:
                result = await SecurityWebSocketService.send_event_to_client(
                    target_key, event_data, redis_data
                )
                results[consumer_hash] = {"status": "sent", "result": result}
            except Exception as e:
                DebugService.app_debug_print(
                    f"WEBSOCKET_DEBUG: Error sending to {target_key}: {str(e)}", True
                )
                results[consumer_hash] = {"status": "error", "error": str(e)}
        
        return results

    @staticmethod
    async def deliver_pending_events(user_connection_key: str):
        """
        Deliver any pending events stored in Redis when a client reconnects.
        Called after a WebSocket connection is established.
        
        Searches for two categories of pending events:
        1. Instruction events  – key pattern: event:instruction:{user_connection_key}:*
        2. Notification events – key pattern: event:notification:{user_connection_key}:*
        
        For each matching key the payload is sent over the live WebSocket and
        the Redis key is removed so the event is not delivered twice.
        
        Args:
            user_connection_key: The full connection key [consumer_hash]___[user_socket_hash]
        """
        if user_connection_key not in active_connections:
            DebugService.app_debug_print(
                f"DELIVER_PENDING: Skipping – {user_connection_key} is not in active_connections", True
            )
            return

        total_delivered = 0

        try:
            websocket: WebSocket = active_connections[user_connection_key]

            # ── 1. Pending instruction events ────────────────────────────
            instruction_pattern = f"event:instruction:{user_connection_key}:*"
            instruction_keys = await AppRedisService.get_keys_by_pattern(instruction_pattern)

            DebugService.app_debug_print(
                f"DELIVER_PENDING: Found {len(instruction_keys)} pending instruction event(s) for {user_connection_key}", True
            )

            for key in instruction_keys:
                try:
                    event_payload_str = await AppRedisService.get_str_redis_value(key)
                    if not event_payload_str:
                        # Key expired between scan and get – clean up
                        await AppRedisService.remove_redis_value(key)
                        continue

                    event_payload = json.loads(event_payload_str)
                    # _store_event_for_disconnected_user wraps the real data
                    # inside {"event_data": …, "redis_data": …, …}
                    event_data = event_payload.get("event_data", event_payload)

                    # Guard: the connection may have dropped while we iterate
                    if user_connection_key not in active_connections:
                        DebugService.app_debug_print(
                            "DELIVER_PENDING: Connection lost mid-delivery, aborting", True
                        )
                        return

                    await websocket.send_text(json.dumps(event_data))
                    total_delivered += 1

                    DebugService.app_debug_print(
                        f"DELIVER_PENDING: Delivered instruction event from key: {key}", True
                    )

                    # Remove only after successful send
                    await AppRedisService.remove_redis_value(key)

                except Exception as inner_e:
                    DebugService.app_debug_print(
                        f"DELIVER_PENDING: Error delivering instruction event {key}: {str(inner_e)}", True
                    )

            # ── 2. Pending notification events ───────────────────────────
            notification_pattern = f"event:notification:{user_connection_key}:*"
            notification_keys = await AppRedisService.get_keys_by_pattern(notification_pattern)

            DebugService.app_debug_print(
                f"DELIVER_PENDING: Found {len(notification_keys)} pending notification(s) for {user_connection_key}", True
            )

            for key in notification_keys:
                try:
                    notification_str = await AppRedisService.get_str_redis_value(key)
                    if not notification_str:
                        await AppRedisService.remove_redis_value(key)
                        continue

                    notification_data = json.loads(notification_str)

                    if user_connection_key not in active_connections:
                        DebugService.app_debug_print(
                            "DELIVER_PENDING: Connection lost mid-delivery, aborting", True
                        )
                        return

                    await websocket.send_text(json.dumps(notification_data))
                    total_delivered += 1

                    DebugService.app_debug_print(
                        f"DELIVER_PENDING: Delivered notification from key: {key}", True
                    )

                    await AppRedisService.remove_redis_value(key)

                except Exception as inner_e:
                    DebugService.app_debug_print(
                        f"DELIVER_PENDING: Error delivering notification {key}: {str(inner_e)}", True
                    )

            # ── 3. Also check raw user_socket_hash (without consumer prefix) ─
            # Some events may have been stored with just the raw hash
            if "___" in user_connection_key:
                raw_user_hash = user_connection_key.split("___", 1)[1]

                for pattern_prefix in ("event:instruction", "event:notification"):
                    raw_pattern = f"{pattern_prefix}:{raw_user_hash}:*"
                    raw_keys = await AppRedisService.get_keys_by_pattern(raw_pattern)

                    for key in raw_keys:
                        try:
                            payload_str = await AppRedisService.get_str_redis_value(key)
                            if not payload_str:
                                await AppRedisService.remove_redis_value(key)
                                continue

                            payload = json.loads(payload_str)
                            event_data = payload.get("event_data", payload)

                            if user_connection_key not in active_connections:
                                return

                            await websocket.send_text(json.dumps(event_data))
                            total_delivered += 1

                            DebugService.app_debug_print(
                                f"DELIVER_PENDING: Delivered raw-hash event from key: {key}", True
                            )
                            await AppRedisService.remove_redis_value(key)

                        except Exception as inner_e:
                            DebugService.app_debug_print(
                                f"DELIVER_PENDING: Error delivering raw-hash event {key}: {str(inner_e)}", True
                            )

            DebugService.app_debug_print(
                f"DELIVER_PENDING: Finished – delivered {total_delivered} event(s) to {user_connection_key}", True
            )

        except Exception as e:
            DebugService.app_debug_print(
                f"DELIVER_PENDING: Fatal error delivering pending events for {user_connection_key}: {str(e)}", True
            )