import json
from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from bson import ObjectId
from fastapi import BackgroundTasks, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse, Response
import httpx
from app.db.dao import DAO
from app.modules.auth.enums.common import MessageCategory
from app.modules.core.types.response import CustomJSONResponse
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.schemas.user_schema import GlobalValidatorCreate, PendingValidationRequestCreate, PermissionValidatorCreate, ProfilPermissionCreate, RolePermissionCreate, UserConfigPayload
from app.modules.core.services.application.application_service import ApplicationService
from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.services.device.device_service import DeviceService
from app.modules.core.services.hash.hash_service import HashService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.services.sms.sms_service import SmsService
from app.modules.security.services.security_validation_service import SecurityValidationService
from app.modules.core.enums.type_enum import EAppGroupFlag, EMultipleValidationStatus, EMultipleValidationType, OutputDataType
from datetime import datetime, timezone, time
from app.modules.security.middleware.sudo_action_middleware import sudo_action_middleware
import time
import io
from app.modules.core.configs.config import settings
import os
import hashlib
import asyncio

from app.modules.core.services.redis.redis_service import AppRedisService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
from app.modules.core.services.model.model_service import ModelService
from app.modules.core.services.encryption.encryption_service import EncryptionService
from app.modules.core.services.icon.svg_icon_service import SvgIconService
from app.modules.core.services.sse.lokotroo_rbac_sse_service import SenatDigitAppsSseService
from app.modules.core.utils.common.helpers import extract_field_on_output_data_element


class StaticController(
        AuthenticatedService,
        ResponseService,
        SmsService,
        DeviceService,
        ModelService,
        DebugService):
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.auth.services.login.login_service import LoginService
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService

        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        self.login_service = LoginService(accept_language)
        self.rbac_role_service = RbacRoleService(accept_language)
        super().__init__(accept_language)


    def _generate_cache_key(self, user_id: str, method_name: str, **params) -> str:
        """
        Generate a unique cache key based on user ID, method name, and parameters
        """
        # Create a string representation of all parameters
        param_str = json.dumps(params, sort_keys=True, default=str)

        # Create a hash of the parameters to keep key length manageable
        param_hash = hashlib.md5(param_str.encode()).hexdigest()

        # Format: static_cache:{user_id}:{method_name}:{param_hash}
        return f"static_cache:{user_id}:{method_name}:{param_hash}"

    async def _get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from cache with timing
        """
        start_time = time.time()
        try:
            cached_data = await AppRedisService.get_str_redis_value(cache_key, use_env_prefix=True)
            fetch_time = round((time.time() - start_time) * 1000, 2)  # Convert to milliseconds

            if cached_data:
                self.app_debug_print(f"🎯 Cache HIT for key: {cache_key} | Fetch time: {fetch_time}ms", True)
                return json.loads(cached_data)
            else:
                self.app_debug_print(f"❌ Cache MISS for key: {cache_key} | Check time: {fetch_time}ms", True)
                return None
        except Exception as e:
            fetch_time = round((time.time() - start_time) * 1000, 2)
            self.app_debug_print(f"⚠️ Cache retrieval error: {str(e)} | Time: {fetch_time}ms", True)
            return None

    async def _set_cached_data(self, cache_key: str, data: Dict[str, Any], ttl: int = 300) -> None:
        """
        Store data in cache with TTL and timing (default 5 minutes)
        """
        start_time = time.time()
        try:
            serialized_data = json.dumps(data, default=str)
            await AppRedisService.set_redis_value(cache_key, serialized_data, expiry=ttl, use_env_prefix=True)
            store_time = round((time.time() - start_time) * 1000, 2)
            data_size = len(serialized_data)
            self.app_debug_print(f"💾 Cache SET for key: {cache_key} | TTL: {ttl}s | Store time: {store_time}ms | Size: {data_size} bytes", True)
        except Exception as e:
            store_time = round((time.time() - start_time) * 1000, 2)
            self.app_debug_print(f"⚠️ Cache storage error: {str(e)} | Time: {store_time}ms", True)

    async def _update_cache_background(self, cache_key: str, fetch_function, ttl: int = 300):
        """
        Update cache in background (fire and forget)
        """
        try:
            # Schedule the cache update to run in background
            asyncio.create_task(self._background_cache_update(cache_key, fetch_function, ttl))
        except Exception as e:
            self.app_debug_print(f"Background cache update scheduling error: {str(e)}", True)

    async def _resolve_application_cache_ttl(self, user_details=None) -> int:
        """Pick the L1 cache TTL for /data/get-applications.

        Order of precedence:
          1. Per-tenant override on ``CfgSaasConfig.cache_application_ttl_seconds``
             (when set, must be > 0)
          2. Global default ``settings.CACHE_DEFAULT_APPLICATION_TIMEOUT``

        Errors fall through to the default — a missing config row, a
        bad lookup, or any unexpected failure must never block the
        cache write. Cheap: one indexed find_one per cache miss.
        """
        try:
            org_id = (user_details or {}).get("sys_organization_id")
            if not org_id:
                return int(settings.CACHE_DEFAULT_APPLICATION_TIMEOUT)
            saas = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sys_organization_id": str(org_id),
                    "filter__is_activated": True,
                },
                _skip_rls=True,
            )
            override = (saas or {}).get("cache_application_ttl_seconds")
            if override is not None and int(override) > 0:
                return int(override)
        except Exception as exc:  # noqa: BLE001
            self.app_debug_print(
                f"_resolve_application_cache_ttl: lookup failed (non-fatal): {exc}",
                True,
            )
        return int(settings.CACHE_DEFAULT_APPLICATION_TIMEOUT)

    async def _push_event_to_user(self, user_id, event: str, message=None) -> bool:
        """Best-effort WebSocket push of ``{event, message}`` to one user.

        Looks up ``SysUser.user_account_socket_hash`` and calls
        ``SecurityWebSocketService.send_event_to_client``. The hash is the
        same per-user identifier the messaging service uses, so push
        fans out to every device the user has connected.

        Returns True if a hash was found AND the dispatch didn't raise;
        False otherwise. All errors are logged + swallowed: a failed push
        must never break the caller's response.
        """
        if not user_id:
            return False
        try:
            user_doc = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                accept_language=self.accept_language,
                query={"filter___id": str(user_id)},
                _skip_rls=True,
            )
            socket_hash = (user_doc or {}).get("user_account_socket_hash")
            if not socket_hash:
                return False
            from app.modules.security.services.security_websocket_service import (
                SecurityWebSocketService,
            )
            await SecurityWebSocketService.send_event_to_client(
                user_account_socket_hash=str(socket_hash),
                data={"event": event, "message": message or {}},
            )
            return True
        except Exception as exc:  # noqa: BLE001
            self.app_debug_print(
                f"_push_event_to_user: dispatch failed for user={user_id} event={event}: {exc}",
                True,
            )
            return False

    async def _invalidate_l1_for_user_ids(self, user_ids) -> int:
        """Bulk-delete L1 (Redis) static_cache:* entries for a set of user IDs.

        Companion to ``UserAppStoreService.mark_*_stale`` — those flip the
        Mongo-backed L2 cache rows; this sweeps the volatile Redis L1 keys
        for the same users so admins don't have to wait the 30-min TTL
        before a permission change becomes visible.

        Pattern: ``static_cache:{user_id}:*`` matches every cached method
        result for that user (different methods, different params, different
        languages). Errors are swallowed per-user so a single bad scan
        never breaks the wider cache invalidation flow.
        """
        if not user_ids:
            return 0
        total_deleted = 0
        for uid in user_ids:
            try:
                deleted = await AppRedisService.delete_keys_by_pattern(
                    f"static_cache:{uid}:*", use_env_prefix=True,
                )
                total_deleted += int(deleted or 0)
            except Exception as exc:  # noqa: BLE001
                self.app_debug_print(
                    f"_invalidate_l1_for_user_ids: pattern delete failed for {uid}: {exc}",
                    True,
                )
        return total_deleted

    async def _background_cache_update(self, cache_key: str, fetch_function, ttl: int):
        """
        Background task to update cache with fresh data
        """
        try:
            fresh_data = await fetch_function()
            await self._set_cached_data(cache_key, fresh_data, ttl)
            self.app_debug_print(f"Background cache update completed for key: {cache_key}", True)
        except Exception as e:
            self.app_debug_print(f"Background cache update error: {str(e)}", True)

    async def _cached_method_wrapper(self,
                                   user_id: str,
                                   method_name: str,
                                   fetch_function,
                                   cache_params: Dict[str, Any],
                                   ttl: int = 300,
                                   enable_background_update: bool = True) -> Dict[str, Any]:
        """
        Generic cache wrapper for any method

        Args:
            user_id: User identifier for cache key
            method_name: Method name for cache key
            fetch_function: Async function that fetches fresh data
            cache_params: Parameters to include in cache key
            ttl: Time to live in seconds (default 5 minutes)
            enable_background_update: Whether to update cache in background

        Returns:
            Dict containing the response data
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(
                user_id=user_id,
                method_name=method_name,
                **cache_params
            )

            # Check cache first
            cached_data = await self._get_cached_data(cache_key)

            if cached_data:
                # If background update is enabled, schedule cache refresh
                if enable_background_update:
                    await self._update_cache_background(cache_key, fetch_function, ttl)

                return cached_data

            # Cache miss - fetch fresh data
            fresh_data = await fetch_function()

            # Cache the fresh data
            await self._set_cached_data(cache_key, fresh_data, ttl)

            return fresh_data

        except Exception as e:
            self.app_debug_print(f"Cache wrapper error for {method_name}: {str(e)}", True)
            # Fallback to direct fetch if cache fails
            return await fetch_function()

    async def _clear_user_cache(self, user_id: str, method_name: Optional[str] = None) -> None:
        """
        Clear cache for a specific user and optionally specific method
        """
        try:
            if method_name:
                # Clear specific method cache for user
                pattern = f"static_cache:{user_id}:{method_name}:*"
            else:
                # Clear all cache for user
                pattern = f"static_cache:{user_id}:*"

            # Use AppRedisService to get keys by pattern and delete them
            keys = await AppRedisService.get_keys_by_pattern(pattern, use_env_prefix=True)
            deleted_count = 0
            for key in keys:
                # Remove environment prefix from key for deletion
                clean_key = key.replace(AppRedisService.get_env_prefix(), "")
                if await AppRedisService.remove_redis_value(clean_key, use_env_prefix=True):
                    deleted_count += 1

            self.app_debug_print(f"🗑️ Cache cleared: {deleted_count} keys deleted for pattern: {pattern}", True)
        except Exception as e:
            self.app_debug_print(f"⚠️ Cache clear error: {str(e)}", True)

    async def _verify_cache_storage(self, cache_key: str) -> bool:
        """
        Verify if data was actually stored in cache
        """
        try:
            cached_data = await AppRedisService.get_str_redis_value(cache_key, use_env_prefix=True)
            if cached_data:
                self.app_debug_print(f"✅ Cache verification SUCCESS - Data found for key: {cache_key}", True)
                return True
            else:
                self.app_debug_print(f"❌ Cache verification FAILED - No data found for key: {cache_key}", True)
                return False
        except Exception as e:
            self.app_debug_print(f"⚠️ Cache verification error: {str(e)}", True)
            return False

    async def _debug_all_cache_keys(self, user_id: str) -> None:
        """
        Debug method to list all cache keys for a user
        """
        try:
            pattern = f"static_cache:{user_id}:*"
            keys = await AppRedisService.get_keys_by_pattern(pattern, use_env_prefix=True)
            self.app_debug_print(f"🔍 Found {len(keys)} cache keys for user {user_id}:", True)
            for key in keys:
                clean_key = key.replace(AppRedisService.get_env_prefix(), "")
                self.app_debug_print(f"  📋 {clean_key}", True)
        except Exception as e:
            self.app_debug_print(f"⚠️ Debug cache keys error: {str(e)}", True)


    def convert_to_serializable(self, data):
        """
        Convert MongoDB ObjectId, datetime objects, and custom classes to serializable format.
        Works with nested dictionaries and lists.
        """
        from bson import ObjectId
        from datetime import datetime
        import types

        if isinstance(data, dict):
            return {k: self.convert_to_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.convert_to_serializable(item) for item in data]
        elif isinstance(data, ObjectId):
            return str(data)
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, types.MappingProxyType):
            # Handle mappingproxy objects by converting them to dictionaries
            return self.convert_to_serializable(dict(data))
        elif hasattr(data, '__dict__'):
            try:
                # Handle custom class objects by converting them to dictionaries
                # Use dict() to convert mappingproxy to a regular dict
                return self.convert_to_serializable(dict(data.__dict__))
            except Exception as e:
                # If we can't convert the __dict__, try to extract attributes manually
                result = {}
                for attr in dir(data):
                    if not attr.startswith('_') and not callable(getattr(data, attr)):
                        result[attr] = getattr(data, attr)
                return self.convert_to_serializable(result)
        else:
            return data

    async def fetch_encrypted_consumer_key(self, request: Request):
        try:
            """
            Endpoint to fetch encrypted consumer key from the consumer hash provided in the request header.

            Args:
                request (Request): The FastAPI request object containing headers.

            Returns:
                dict: Encrypted consumer key if the consumer hash is valid.

            Raises:
                HTTPException: If the consumer hash is missing or invalid.
            """
            from app.modules.core.services.generic.generic_services import GenericService
            consumer_hash = request.headers.get("consumer-hash")
            print(f"consumer_hash : {consumer_hash}")
            generic_service = GenericService(self.accept_language)
            if not consumer_hash:
                raise HTTPException(
                    status_code=400, detail="Consumer hash is missing in the headers.")

            # Find the API consumer by the consumer_hash
            # api_consumer = await generic_service.fetch_data_from_collection(
            #     collection_key=CollectionKey.REF_ENTITY,
            #     output_data_type=OutputDataType.TREE.value,
            #     all_data=True,
            #     query={},
            # )

            # if not api_consumer:
            #     raise HTTPException(status_code=404, detail="No API consumer found for the provided consumer hash.")

            # Encrypt the consumer key
            # encrypted_consumer_key = self.encrypt_data(api_consumer['consumer_key'])
            api_consumer = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_API_CONSUMER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__consumer_hash": str(consumer_hash).strip()},
            )

            if not api_consumer:
                raise HTTPException(
                    status_code=404, detail="No API consumer found for the provided consumer hash.")

            # Encrypt the consumer key
            encrypted_consumer_key = EncryptionService.encrypt_data(
                api_consumer['consumer_key'])

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": encrypted_consumer_key
                }
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            print(f"consumer_hash ERROR : {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def fetch_menu_configs(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
    ):
        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)
        # user_details = await self.get_user_info(request=request,accept_language=accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
        self.app_debug_print(f"\n\n user_profil :{user_profil}\n\n", False)
        pipeline = [
            # 1. Lookup the ref_named_entity document(s).
            {
                '$lookup': {
                    'from': f"{CollectionKey.REF_NAMED_ENTITY.model_name}",
                    'localField': "ref_named_entity_id",
                    'foreignField': "_id",
                    'as': "unwind__ref_named_entity"
                }
            },
            # 2. Unwind the unwind__ref_named_entity array.
            {
                '$unwind': "$unwind__ref_named_entity"
            },

            {
                "$group": {
                    "_id": None,
                    "docs": {"$push": "$$ROOT"}
                }
            },
            # Merge the array of documents into one object per group.
            {
                "$project": {
                    "merged": {
                        "$reduce": {
                            "input": "$docs",
                            "initialValue": {},
                            "in": {"$mergeObjects": ["$$value", "$$this"]}
                        }
                    }
                }
            },
            # Replace the root with the merged document so that fields are at the top level.
            {
                "$replaceRoot": {"newRoot": "$merged"}
            }
        ]

        infos = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.REF_ENTITY,
            output_data_type=output_data_type,
            accept_language=self.accept_language,
            pipeline=pipeline,
        )

        self.app_debug_print(
            f"\n\n\n infos entities  >>> : {len(infos)} \n\n\n", True)

        raw_query_params: Dict[str, str] = dict(request.query_params)
        query_params = ConverterService.convert_query_params(raw_query_params)
        self.app_debug_print(
            f"\n Query Parameters (converted): {query_params} \n", True)

        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": infos
            }
        )

    async def fetch_menus(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
    ):

        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)
        # user_details = await self.get_user_info(request=request,accept_language=accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
        self.app_debug_print(f"\n\n user_profil :{user_profil}\n\n", False)
        pipeline = [
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_ROLE.model_name}",
                    'localField': "rbac_role_id",
                    'foreignField': "_id",
                    'as': "unwind__rbac_role"
                }
            },
            {
                '$unwind': "$unwind__rbac_role"
            },

            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                    'localField': "rbac_permission_id",
                    'foreignField': "_id",
                    'as': "unwind__rbac_permission"
                }
            },
            {
                '$unwind': "$unwind__rbac_permission"
            },
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                    'localField': "unwind__rbac_permission._id",
                    'foreignField': "rbac_permission_id",
                    'as': "unwind__rbac_permission_target"
                }
            },

            {
                '$unwind': "$unwind__rbac_permission_target"
            },

            {
                '$lookup': {
                    'from': f"{CollectionKey.SYS_MENU.model_name}",
                    'localField': "unwind__rbac_permission_target.targeted_id",
                    'foreignField': "_id",
                    'as': "unwind__sys_menu"
                }
            },
            {
                '$unwind': "$unwind__sys_menu"
            },
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PATH_GUARD.model_name}",
                    'localField': "unwind__sys_menu._id",
                    'foreignField': "targeted_id",
                    'as': "unwind__rbac_path_guard"
                }
            },
            {
                '$unwind': "$unwind__rbac_path_guard"
            },
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "localField": "unwind__sys_menu._id",
                    "foreignField": "targeted_id",
                    "as": "menu_rbac_restricted_api_consumer"
                }
            },
            {
                "$unwind": {
                    "path": "$menu_rbac_restricted_api_consumer",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                    "localField": "unwind__sys_menu._id",
                    "foreignField": "targeted_id",
                    "as": "menu_rbac_restricted_profil"
                }
            },
            {
                "$unwind": {
                    "path": "$menu_rbac_restricted_profil",
                    "preserveNullAndEmptyArrays": True
                }
            },
            # API CONSUMER
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "localField": "unwind__rbac_path_guard._id",
                    "foreignField": "targeted_id",
                    "as": "guard_rbac_restricted_api_consumer"
                }
            },
            {
                "$unwind": {
                    "path": "$guard_rbac_restricted_api_consumer",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                    "localField": "unwind__rbac_path_guard._id",
                    "foreignField": "targeted_id",
                    "as": "guard_rbac_restricted_profil"
                }
            },
            {
                "$unwind": {
                    "path": "$guard_rbac_restricted_profil",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$match": {
                    "unwind__rbac_role._id":  ObjectId(user_details['rbac_role_id']),
                    "unwind__sys_menu.is_standalone": True,
                    # "unwind__sys_menu.sys_menu_id":None,


                    "menu_rbac_restricted_profil.rbac_profile_id": ObjectId(user_profil['id']),
                    "menu_rbac_restricted_api_consumer.ref_api_consumer_id": ObjectId(api_Consumer['id']),
                    "menu_rbac_restricted_profil.is_hidden": False,
                    "menu_rbac_restricted_api_consumer.is_hidden": False,

                    "guard_rbac_restricted_profil.rbac_profile_id": ObjectId(user_profil['id']),
                    "guard_rbac_restricted_api_consumer.ref_api_consumer_id": ObjectId(api_Consumer['id']),
                    "guard_rbac_restricted_profil.is_hidden": False,
                    "guard_rbac_restricted_api_consumer.is_hidden": False

                }
            },
            {
                "$group": {
                    "_id": "$unwind__sys_menu._id",
                    "docs": {"$push": {
                        "_id": "$_id",
                        "rbac_permission_id": "$rbac_permission_id",
                        "unwind__rbac_restricted_profil": "$unwind__rbac_restricted_profil",
                        "unwind__rbac_restricted_api_consumer": "$unwind__rbac_restricted_api_consumer",
                    }}
                }
            },
            {
                "$project": {
                    "merged": {
                        "$reduce": {
                            "input": "$docs",
                            "initialValue": {},
                            "in": {"$mergeObjects": ["$$value", "$$this"]}
                        }
                    }
                }
            },
            {
                "$project": {
                    "_id": "$merged._id",
                    "rbac_permission_id": "$merged.rbac_permission_id",
                    "unwind__rbac_restricted_profil": {
                        "is_hidden": "$merged.unwind__rbac_restricted_profil.is_hidden",
                        "is_activated": "$merged.unwind__rbac_restricted_profil.is_activated",
                    },
                    "unwind__rbac_restricted_api_consumer": {
                        "is_hidden": "$merged.unwind__rbac_restricted_api_consumer.is_hidden",
                        "is_activated": "$merged.unwind__rbac_restricted_api_consumer.is_activated",
                    }
                }
            },
            # {
            #     "$replaceRoot": { "newRoot": "$merged" }
            # },
            {
                "$sort": {
                    "order_by": 1
                }
            },
        ]

        infos = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
            output_data_type=output_data_type,
            accept_language=self.accept_language,
            pipeline=pipeline,
        )

        self.app_debug_print(f"\n\n\n infos  >>> : {len(infos)} \n\n\n", True)

        raw_query_params: Dict[str, str] = dict(request.query_params)
        query_params = ConverterService.convert_query_params(raw_query_params)
        self.app_debug_print(
            f"\n Query Parameters (converted): {query_params} \n", True)

        formatted_data = []
        for index, menu in enumerate(infos):

            # getch icon
            if output_data_type == OutputDataType.DATA_TABLE.value:
                targeted_id = menu['sys_menu']['id']['display_value']
            elif output_data_type == OutputDataType.DEFAULT.value:
                targeted_id = menu['sys_menu']['id']
            elif output_data_type == OutputDataType.TREE.value:
                targeted_id = menu['sys_menu']['id']
            else:
                targeted_id: None

            # queries = {
            #     "filter__targeted_id":targeted_id,
            #     "filter__ref_api_consumer_id":api_Consumer['id']
            # }
            self.app_debug_print(f"output_data_type : {output_data_type}")
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
                        "unwind__rbac_restricted_api_consumer.ref_api_consumer_id": ObjectId(api_Consumer['id']),
                    }
                },
                {
                    "$project": {
                        "id": "$_id",
                        "ref_icon_id": "$ref_icon_id",
                        "rbac_permission_id": "$rbac_permission_id",
                        "targeted_id": "$targeted_id",
                    }
                }
            ]

            nested_icon = await self.generic_service.fetch_native_aggregate_one_from_collection(
                collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                pipeline=nested_icon_pipeline
            )
            self.app_debug_print(f"\n\n nested_icon : {nested_icon}\n\n")
            current_item = {
                **menu['sys_menu'],
                'rbac_path_guard': {
                    **menu['rbac_path_guard'],
                }
            }
            formatted_data.append({
                **current_item
            })
            if nested_icon:
                icon_payload = ApplicationService._build_svg_icon_payload(
                    menu_or_app_data=menu.get('sys_menu', {}),
                    rbac_path_guard=menu.get('rbac_path_guard', {}),
                    api_consumer_flag=api_Consumer.get('flag'),
                )
                if icon_payload:
                    index_of_menu = formatted_data.index(current_item)
                    formatted_data[index_of_menu] = {
                        **formatted_data[index_of_menu],
                        **icon_payload,
                    }
                    self.app_debug_print(
                        f"\n\n index_of_menu: {index_of_menu}\n\n", True)

        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": formatted_data
            }
        )
    
    async def fetch_formated_application_groups(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page")
    ):

        # 🕐 START TIMING
        method_start_time = time.time()
        self.app_debug_print(f"🚀 Starting fetch_formated_application_groups at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}", True)

        try:
            # DECODE USER TOKEN
            auth_start_time = time.time()
            user_details = await self.get_user_info(request, self.accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
            auth_time = round((time.time() - auth_start_time) * 1000, 2)
            self.app_debug_print(f"🔐 Authentication completed in {auth_time}ms", True)

            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = ConverterService.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}", True)
            sort = request.query_params.get("sort", {'order_by':1})

            # CACHE IMPLEMENTATION
            user_id = user_details.get('id', 'anonymous')
            cache_params = {
                'output_data_type': output_data_type.value if output_data_type else 'default',
                'all_data': all_data,
                'page': page,
                'limit': limit,
                'query_params': query_params,
                'accept_language': self.accept_language
            }

            cache_key = self._generate_cache_key(
                user_id=user_id,
                method_name='fetch_formated_application_groups',
                **cache_params
            )

            # 1. Check cache first
            cache_check_start = time.time()
            cached_data = await self._get_cached_data(cache_key)
            cache_check_time = round((time.time() - cache_check_start) * 1000, 2)

            if cached_data:
                total_time = round((time.time() - method_start_time) * 1000, 2)

                # Schedule background cache update
                async def fetch_fresh_data():
                    pipeline = [
                        # {
                        #     "$lookup": {
                        #         "from": f"{CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY.model_name}",
                        #         "localField": "_id",
                        #         "foreignField": "ref_application_group_id",
                        #         "as": "unwind__cfg_application_group_accessibility"
                        #     }
                        # },
                        # {
                        #     "$unwind": {
                        #         "path": "$unwind__cfg_application_group_accessibility",
                        #         "preserveNullAndEmptyArrays": True
                        #     }
                        # },
                        # {
                        #     "$match": {
                        #         "unwind__cfg_application_group_accessibility.targeted_id": ObjectId(user_details['sys_organization_id'])
                        #     }
                        # }
                    ]
                    applicationGroups = await self.generic_service.fetch_native_aggregate_data_from_collection(
                        collection_key=CollectionKey.REF_APPLICATION_GROUP,
                        all_data=all_data,
                        page=page,
                        limit=limit,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language=self.accept_language,
                        pipeline=pipeline
                    )



                    formatted_data = []
                    for index, apps in enumerate(applicationGroups):
                        formatted_data.append(apps)

                    return {
                        "status_code": status.HTTP_200_OK,
                        "data": formatted_data
                    }

                # 2. Update cache in background
                await self._update_cache_background(cache_key, fetch_fresh_data, ttl=settings.CACHE_DEFAULT_APPLICATION_TIMEOUT)

                # Return cached data immediately
                self.app_debug_print(f"⚡ CACHE HIT - Returning cached application groups | Total time: {total_time}ms", True)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content=cached_data
                )

            # Cache miss - continue with database fetch
            self.app_debug_print(f"💾 Cache check completed in {cache_check_time}ms - proceeding with DB fetch", True)

            # Cache miss - fetch data and cache it
            db_fetch_start = time.time()

            # AGGREGATION WITH CFG_APPLICATION_GROUP_ACCESSIBILITY
            pipeline = [
                # {
                #     "$lookup": {
                #         "from": f"{CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY.model_name}",
                #         "localField": "_id",
                #         "foreignField": "ref_application_group_id",
                #         "as": "unwind__cfg_application_group_accessibility"
                #     }
                # },
                # {
                #     "$unwind": {
                #         "path": "$unwind__cfg_application_group_accessibility",
                #         "preserveNullAndEmptyArrays": True
                #     }
                # },
                {
                    "$match": {
                        # "unwind__cfg_application_group_accessibility.targeted_id": ObjectId(user_details['sys_organization_id'])
                        "is_activated":True,
                    }
                }
            ]
            applicationGroups = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.REF_APPLICATION_GROUP,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                pipeline=pipeline
            )
            # applicationGroups = await self.generic_service.fetch_data_from_collection(
            #     collection_key=CollectionKey.REF_APPLICATION_GROUP,
            #     all_data=all_data,
            #     page=page,
            #     limit=limit,
            #     output_data_type=OutputDataType(output_data_type).value,
            #     accept_language=self.accept_language,
            #     query={**query_params}
            # )

            formatted_data = []
            for index, apps in enumerate(applicationGroups):
                # self.app_debug_print(f"-> apps >> : {apps}", False)
                formatted_data.append(apps)

            # Calculate timing
            db_fetch_time = round((time.time() - db_fetch_start) * 1000, 2)
            total_method_time = round((time.time() - method_start_time) * 1000, 2)

            response_data = {
                "status_code": status.HTTP_200_OK,
                "data": formatted_data
            }

            # Cache the response (with verification)
            cache_store_start = time.time()
            await self._set_cached_data(cache_key, response_data, ttl=settings.CACHE_DEFAULT_APPLICATION_TIMEOUT)  # 30 minutes
            # await self._set_cached_data(cache_key, response_data, ttl=1800)  # 30 minutes
            cache_store_time = round((time.time() - cache_store_start) * 1000, 2)

            # Verify cache was stored
            await self._verify_cache_storage(cache_key)

            # Log performance metrics
            self.app_debug_print(f"🏁 DB FETCH COMPLETE | DB time: {db_fetch_time}ms | Cache store: {cache_store_time}ms | Total time: {total_method_time}ms | Records: {len(formatted_data)}", True)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content=response_data
            )

        except Exception as e:
            self.app_debug_print(f"Error fetch_formated_application_groups: {str(e)}", True)
            raise HTTPException(
                status_code=500, detail="An unexpected error occurred.")
        
    async def fetch_formated_applications(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page"),
        sse_key: Optional[str] = None,
    ):

        # 🕐 START TIMING
        method_start_time = time.time()
        self.app_debug_print(f"🚀 Starting fetch_formated_applications at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}", True)

        try:
            if sse_key:
                await SenatDigitAppsSseService.publish(
                    sse_key,
                    {
                        "event": "started",
                        "message": "Chargement des autorisations…",
                        "percent": 5,
                    },
                )
            # DECODE USER TOKEN
            auth_start_time = time.time()
            user_details = await self.get_user_info(request, self.accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
            auth_time = round((time.time() - auth_start_time) * 1000, 2)
            self.app_debug_print(f"🔐 Authentication completed in {auth_time}ms", True)

            # CACHE IMPLEMENTATION
            application_group_flag = request.query_params.get(
                "filter__application_group_flag", EAppGroupFlag.COMMON.value)

            cache_params = {
                'output_data_type': output_data_type.value if output_data_type else 'default',
                'all_data': all_data,
                'page': page,
                'limit': limit,
                'application_group_flag': application_group_flag,
                'user_profil_id': user_profil['id'],
                'api_consumer_id': api_Consumer['id'],
                'accept_language': self.accept_language,
                'app_menu_fetch_paradigm': settings.APP_MENU_FETCH_PARADIGM,
            }

            cache_key = self._generate_cache_key(
                user_id=user_details.get('id', 'anonymous'),
                method_name='fetch_formated_applications',
                **cache_params
            )

            # TODO :: ADD FETCH TIME 
            # 1. Check cache first
            cache_check_start = time.time()
            cached_data = await self._get_cached_data(cache_key)
            cache_check_time = round((time.time() - cache_check_start) * 1000, 2)

            if cached_data:
                total_time = round((time.time() - method_start_time) * 1000, 2)
                self.app_debug_print(f"⚡ CACHE HIT - Returning cached applications data | Total time: {total_time}ms", True)
                # Ensure paradigm is always current even in cached responses
                if isinstance(cached_data, dict):
                    cached_data['app_menu_fetch_paradigm'] = settings.APP_MENU_FETCH_PARADIGM
                if sse_key:
                    await SenatDigitAppsSseService.publish(
                        sse_key,
                        {
                            "event": "complete",
                            "message": "Terminé",
                            "percent": 100,
                            "applications_length": len(cached_data.get("data", []) or []),
                            "duration_ms": total_time,
                            "from_cache": True,
                        },
                    )
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content=cached_data
                )

            # Cache miss - continue with database fetch
            self.app_debug_print(f"💾 Cache check completed in {cache_check_time}ms - proceeding with DB fetch", True)

            # ── L2 cache: user_app_store (persistent / Mongo) ──────────────
            # Faster than rerunning the aggregation, slower than Redis L1.
            # Survives Redis flushes + process restarts. Lookup is index-
            # covered so the latency hit on miss is negligible.
            try:
                from app.modules.core.enums.user_app_store_enum import (
                    EUserAppStoreEndpointFlag,
                )
                from app.modules.core.services.user_app_store.user_app_store_service import (
                    UserAppStoreService,
                )
                l2_check_start = time.time()
                l2_row = await UserAppStoreService.get(
                    sys_user_id=user_details.get("id"),
                    ref_api_consumer_id=api_Consumer["id"],
                    rbac_profile_flag=user_profil.get("flag"),
                    endpoint_flag=EUserAppStoreEndpointFlag.APPLICATIONS,
                    application_group_flag=application_group_flag,
                    accept_language=self.accept_language,
                    output_data_type=(
                        output_data_type.value if output_data_type else "default"
                    ),
                    all_data_flag=bool(all_data),
                )
                l2_check_time = round((time.time() - l2_check_start) * 1000, 2)
                if l2_row and l2_row.app_data:
                    # L2 hit — promote to Redis L1 so the next request stays fast,
                    # then return with refreshed paradigm marker.
                    payload = dict(l2_row.app_data)
                    if isinstance(payload, dict):
                        payload["app_menu_fetch_paradigm"] = settings.APP_MENU_FETCH_PARADIGM
                    await self._set_cached_data(
                        cache_key, payload,
                        ttl=settings.CACHE_DEFAULT_APPLICATION_TIMEOUT,
                    )
                    total_time = round((time.time() - method_start_time) * 1000, 2)
                    self.app_debug_print(
                        f"⚡ L2 user_app_store HIT | check={l2_check_time}ms total={total_time}ms",
                        True,
                    )
                    if sse_key:
                        await SenatDigitAppsSseService.publish(
                            sse_key,
                            {
                                "event": "complete",
                                "message": "Terminé",
                                "percent": 100,
                                "applications_length": len(payload.get("data", []) or []),
                                "duration_ms": total_time,
                                "from_cache": True,
                            },
                        )
                    return CustomJSONResponse(
                        status_code=status.HTTP_200_OK,
                        content=payload,
                    )
                self.app_debug_print(
                    f"💾 L2 user_app_store MISS in {l2_check_time}ms — running aggregation",
                    True,
                )
            except Exception as l2_err:
                # Cache layer must never break the request — fall through to
                # the aggregation path on any L2 lookup error.
                self.app_debug_print(
                    f"⚠ L2 user_app_store lookup error: {l2_err}", True
                )

            # Cache miss — delegate to the headless helper. Auth + cache I/O
            # stay in this wrapper; the helper is reusable from the dynamic seed.
            db_fetch_start = time.time()
            response_data = await self.run_formated_applications_core(
                user_details=user_details,
                api_Consumer=api_Consumer,
                user_profil=user_profil,
                output_data_type=output_data_type,
                all_data=all_data,
                page=page,
                limit=limit,
                application_group_flag=application_group_flag,
                sse_key=sse_key,
            )
            # Re-expose locals the existing log message at the bottom of this
            # block uses (formatted_data + db_fetch_time). Keeping them avoids
            # touching cache-write / log code below.
            formatted_data = response_data.get('data', []) if isinstance(response_data, dict) else []
            db_fetch_time = round((time.time() - db_fetch_start) * 1000, 2)
            total_method_time = round((time.time() - method_start_time) * 1000, 2)

            # 2. Cache the response data (with verification). TTL is
            # resolved per-tenant: a SaaS-config row may override the
            # global default for stable orgs that want longer cache.
            cache_store_start = time.time()
            ttl_seconds = await self._resolve_application_cache_ttl(user_details)
            await self._set_cached_data(cache_key, response_data, ttl=ttl_seconds)
            cache_store_time = round((time.time() - cache_store_start) * 1000, 2)

            # Verify cache was stored
            await self._verify_cache_storage(cache_key)

            # ── L2 cache: persist to user_app_store ────────────────────────
            # Best-effort; failures are logged but never break the response.
            try:
                from app.modules.core.enums.user_app_store_enum import (
                    EUserAppStoreEndpointFlag,
                )
                from app.modules.core.services.user_app_store.user_app_store_service import (
                    UserAppStoreService,
                )
                l2_store_start = time.time()
                await UserAppStoreService.upsert(
                    sys_user_id=user_details.get("id"),
                    ref_api_consumer_id=api_Consumer["id"],
                    rbac_profile_id=user_profil.get("id"),
                    rbac_profile_flag=user_profil.get("flag"),
                    endpoint_flag=EUserAppStoreEndpointFlag.APPLICATIONS,
                    application_group_flag=application_group_flag,
                    accept_language=self.accept_language,
                    app_data=response_data,
                    output_data_type=(
                        output_data_type.value if output_data_type else "default"
                    ),
                    all_data_flag=bool(all_data),
                )
                l2_store_time = round((time.time() - l2_store_start) * 1000, 2)
                self.app_debug_print(
                    f"💾 L2 user_app_store upsert: {l2_store_time}ms", True,
                )
            except Exception as l2_err:
                self.app_debug_print(
                    f"⚠ L2 user_app_store upsert failed (non-fatal): {l2_err}", True,
                )

            # Log performance metrics
            self.app_debug_print(f"🏁 DB FETCH COMPLETE | DB time: {db_fetch_time}ms | Cache store: {cache_store_time}ms | Total time: {total_method_time}ms | Records: {len(formatted_data)}", True)

            if sse_key:
                await SenatDigitAppsSseService.publish(
                    sse_key,
                    {
                        "event": "complete",
                        "message": "Terminé",
                        "percent": 100,
                        "applications_length": len(formatted_data),
                        "duration_ms": total_method_time,
                    },
                )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content=response_data
            )

        except HTTPException as e:
            if sse_key:
                await SenatDigitAppsSseService.publish(
                    sse_key,
                    {
                        "event": "error",
                        "message": str(e.detail),
                    },
                )
            raise
        except Exception as e:
            if sse_key:
                await SenatDigitAppsSseService.publish(
                    sse_key,
                    {
                        "event": "error",
                        "message": str(e),
                    },
                )
            self.app_debug_print(f"Error fetch_formated_applications: {str(e)}", True)
            raise HTTPException(
                status_code=500, detail="An unexpected error occurred.")

    async def stream_applications_sse(self, request: Request, sse_key: str):
        return StreamingResponse(
            SenatDigitAppsSseService.stream(sse_key=sse_key, request=request),
            media_type="text/event-stream",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async def fetch_senat_digit_app_formated_applications(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
        sse_key: Optional[str] = None,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page"),
    ):
        return await self.fetch_formated_applications(
            request=request,
            output_data_type=output_data_type,
            endpoint_call=endpoint_call,
            all_data=all_data,
            page=page,
            limit=limit,
            sse_key=sse_key,
        )

    async def stream_senat_digit_applications_sse(self, request: Request, sse_key: str):
        return await self.stream_applications_sse(request=request, sse_key=sse_key)
        
    async def fetch_agent_app_formated_applications(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page")
    ):
        # 🕐 START TIMING
        method_start_time = time.time()
        self.app_debug_print(f"🚀 Starting fetch_agent_app_formated_applications at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}", True)

        try:
            # FORCE DEFAULT output for mobile — plain values, no ConfigDataStruc wrappers
            output_data_type = OutputDataType.DEFAULT.value

            # DECODE USER TOKEN
            auth_start_time = time.time()
            user_details = await self.get_user_info(request, self.accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
            auth_time = round((time.time() - auth_start_time) * 1000, 2)
            self.app_debug_print(f"🔐 Authentication completed in {auth_time}ms", True)

            # CACHE IMPLEMENTATION
            application_group_flag = EAppGroupFlag.COMMON.value
            # request.query_params.get(
            #     "filter__application_group_flag", EAppGroupFlag.COMMON.value)

            # Start database operations timing
            db_fetch_start = time.time()
            self.app_debug_print(f"\n\n user_profil :{user_profil}\n\n", True)
            self.app_debug_print(f"\n\n user_details :{user_details}\n\n", True)
            self.app_debug_print(f"\n\n api_Consumer :{api_Consumer}\n\n", True)

            saas_config_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                user=user_details,
            )

            if not saas_config_info:
                message = self.get_response_message(
                    MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                ) 
            app_pipeline = [
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
                    "$lookup": {
                        "from": f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                        "localField": "_id",
                        "foreignField": "targeted_id",
                        "as": "unwind__rbac_restricted_profil"
                    }
                },
                {
                    "$unwind": {
                        "path": "$unwind__rbac_restricted_profil",
                        "preserveNullAndEmptyArrays": True
                    }
                },
                {
                    "$match": {
                        "unwind__rbac_restricted_profil.rbac_profile_id": ObjectId(user_profil['id']),
                        "unwind__rbac_restricted_api_consumer.ref_api_consumer_id": ObjectId(api_Consumer['id']),
                        "unwind__rbac_restricted_profil.is_hidden": False,
                        "unwind__rbac_restricted_api_consumer.is_hidden": False,
                        "application_group_flag":application_group_flag,
                        "is_activated": True,
                    }
                },
                {
                    "$group": {
                        "_id": "$_id",
                        "docs": {"$push": {
                            "_id": "$_id",
                            "order_by": "$order_by",
                            "application_group_flag": "$application_group_flag",
                            "flag": "$flag",
                            "name": "$name",
                                    "is_standalone": "$is_standalone",
                                    "description_str": "$description_str",
                        }}
                    }
                },
                {
                    "$project": {
                        "merged": {
                            "$reduce": {
                                "input": "$docs",
                                "initialValue": {},
                                "in": {"$mergeObjects": ["$$value", "$$this"]}
                            }
                        }
                    }
                },
                {
                    "$replaceRoot": {"newRoot": "$merged"}
                },
                {
                    "$sort": {
                        "order_by": 1
                    }
                },
                {
                    "$skip": limit * page
                },
                {
                    "$limit": limit
                }
            ]
            
            self.app_debug_print(
                f"-> apps  app_pipeline >> : {app_pipeline}", False)
            force_include_fields = ['_id', 'order_by', 'name', 'description_str']

            applications = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.SYS_APPLICATION,
                output_data_type=OutputDataType.DEFAULT.value,
                # output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                pipeline=app_pipeline,
                force_include_fields=force_include_fields
            )
            self.app_debug_print(
                f" \n\n applications : {len(applications)} \n\n", True)

            formatted_data = []
            for index, apps in enumerate(applications):
                self.app_debug_print(f"-> apps >> : {apps}", False)
                # continue
                # getch icon
                targeted_id = apps['id']
                order_by = index
                self.app_debug_print(f"-> apps  senat_digit apps >> : targeted_id : {targeted_id}", True)
                # queries = {
                #     "filter__targeted_id":targeted_id,
                #     "filter__ref_api_consumer_id":api_Consumer['id']
                # }
                if index == 0:
                    self.app_debug_print(
                        f"output_data_type : {output_data_type}", True)
                rbac_path_guard_pipeline = [
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
                            # "unwind__rbac_restricted_profil.rbac_profile_id":ObjectId(user_profil['id']),
                            "unwind__rbac_restricted_api_consumer.ref_api_consumer_id": ObjectId(api_Consumer['id']),
                            # "unwind__rbac_restricted_profil.is_hidden":False,
                            "unwind__rbac_restricted_api_consumer.is_hidden": False
                        }
                    },
                    {
                        "$project": {
                            "_id": "$_id",
                            "targeted_id": 1,
                            "path": 1,
                            "path_guard": 1,
                        }
                    }
                ]
                rbac_path_guard = await self.generic_service.fetch_native_aggregate_one_from_collection(
                    collection_key=CollectionKey.RBAC_PATH_GUARD,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    pipeline=rbac_path_guard_pipeline
                )
                self.app_debug_print(
                    f" \n\n rbac_path_guard senat_digit apps: {'Yes' if rbac_path_guard else 'No'} \n\n", True)
                # if not rbac_path_guard : continue

                single_app_profil = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={
                        "filter__targeted_id": targeted_id,
                    },
                    user=user_details,
                )
                single_app_api_consumer = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=self.accept_language,
                    query={
                        "filter__targeted_id": targeted_id,
                    },
                    user=user_details,
                )
                is_hidden = True
                is_activated = False
                self.app_debug_print(
                    f"\n\n\n\ single_app_api_consumer  senat_digit apps: {single_app_api_consumer}\n\n\n\n",True)
                self.app_debug_print(
                    f"\n\n\n\ single_app_profil  senat_digit apps: {single_app_profil}\n\n\n\n",True)
                if single_app_profil and single_app_api_consumer:
                    profil_is_hidden = single_app_profil['is_hidden']
                    profil_is_activated = single_app_profil['is_activated']

                    api_consumer_is_hidden = single_app_api_consumer['is_hidden']
                    api_consumer_is_activated = single_app_api_consumer['is_activated']

                    if profil_is_hidden == False and api_consumer_is_hidden == False:
                        is_hidden = False

                    if profil_is_activated == True and api_consumer_is_activated == True:
                        is_activated = True

                # DOUBLE CHECK
                start_time = time.time()
                double_check_pipeline = [
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                            'localField': 'rbac_permission_id',
                            'foreignField': '_id',
                            'as': 'permissions'
                        }
                    }, {
                        '$unwind': '$permissions'
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                            'let': {
                                'permissionId': '$permissions._id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$and': [
                                                {
                                                    '$eq': [
                                                        '$rbac_permission_id', '$$permissionId'
                                                    ]
                                                }, {
                                                    '$eq': [
                                                        '$sys_user_id', ObjectId(
                                                            user_details['id'])
                                                    ]
                                                }, {
                                                    '$eq': [
                                                        '$status', 'added'
                                                    ]
                                                }
                                            ]
                                        }
                                    }
                                }
                            ],
                            'as': 'direct_privileges'
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                            'localField': 'permissions._id',
                            'foreignField': 'rbac_permission_id',
                            'as': 'permission_targets'
                        }
                    }, {
                        '$unwind': {
                            'path': '$permission_targets',
                            'preserveNullAndEmptyArrays': True
                        }
                    }, {
                        '$lookup': {
                            'from': 'sys_application',
                            'localField': 'permission_targets.targeted_id',
                            'foreignField': '_id',
                            'as': 'applications'
                        }
                    }, {
                        '$unwind': {
                            'path': '$applications',
                            'preserveNullAndEmptyArrays': True
                        }
                    }, {
                        '$match': {
                            'applications._id': ObjectId(str(targeted_id))
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                            'let': {
                                'app_id': '$applications._id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$targeted_id', '$$app_id'
                                            ]
                                        }
                                    }
                                }, {
                                    '$match': {
                                        'ref_api_consumer_id': ObjectId(api_Consumer['id'])
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'is_hidden': 1,
                                        'is_activated': 1,
                                        'ref_api_consumer_id': 1
                                    }
                                }
                            ],
                            'as': 'api_consumers'
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                            'let': {
                                'app_id': '$applications._id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$targeted_id', '$$app_id'
                                            ]
                                        }
                                    }
                                }, {
                                    '$match': {
                                        'rbac_profile_id': ObjectId(user_profil['id'])
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'is_hidden': 1,
                                        'is_activated': 1,
                                        'rbac_profile_id': 1
                                    }
                                }
                            ],
                            'as': 'profiles'
                        }
                    }, {
                        '$match': {
                            '$or': [
                                {
                                    'rbac_role_id': ObjectId(user_details['rbac_role_id']),
                                    'api_consumers': {
                                        '$ne': []
                                    },
                                    'profiles': {
                                        '$ne': []
                                    },
                                    'permissions._id': {
                                        '$exists': True
                                    }
                                }, {
                                    'direct_privileges': {
                                        '$ne': []
                                    },
                                    'api_consumers': {
                                        '$ne': []
                                    },
                                    'profiles': {
                                        '$ne': []
                                    }
                                }
                            ]
                        }
                    }, {
                        '$group': {
                            '_id': '$applications._id',
                            'result': {
                                '$first': {
                                    '_id': '$_id',
                                    'rbac_role_id': '$rbac_role_id',
                                    'rbac_permission_id': '$rbac_permission_id',
                                    'rbac_restricted_api_consumer': {
                                        '$arrayElemAt': [
                                            '$api_consumers', 0
                                        ]
                                    },
                                    'rbac_restricted_profil': {
                                        '$arrayElemAt': [
                                            '$profiles', 0
                                        ]
                                    },
                                    'has_privilege': {
                                        '$gt': [
                                            {
                                                '$size': '$direct_privileges'
                                            }, 0
                                        ]
                                    }
                                }
                            }
                        }
                    }, {
                        '$replaceRoot': {
                            'newRoot': '$result'
                        }
                    }
                ]

            
                double_check_info = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=self.accept_language,
                    pipeline=double_check_pipeline
                )
                self.app_debug_print(
                    f"\n\n\n\ double_check_info  senat_digit apps: {len(double_check_info)}\n\n\n\n",True)
                self.app_debug_print(
                    f"\n\n\n\ time : {time.time() - start_time}\n\n\n\n",True)
                # # break
                if double_check_info and len(double_check_info) > 0:
                    single_info = double_check_info[0]
                    if 'rbac_restricted_profil' in single_info:
                        restricted_profil = single_info['rbac_restricted_profil']
                        if restricted_profil['is_locked'] == True or restricted_profil['is_activated'] == False:
                            is_activated = False

                    if 'rbac_restricted_profil' in single_info:
                        restricted_profil = single_info['rbac_restricted_profil']
                        if restricted_profil['is_hidden'] == False:
                            is_hidden = False

                    if 'rbac_restricted_api_consumer' in single_info:
                        restricted_api_consumer = single_info['rbac_restricted_api_consumer']
                        if restricted_api_consumer['is_locked'] == True or restricted_api_consumer['is_activated'] == False:
                            is_activated = False

                    if 'rbac_restricted_api_consumer' in single_info:
                        if restricted_api_consumer['is_hidden'] == False:
                            is_hidden = False
                else:
                    is_activated = False

                # # SKIP IF HIDDEN
                if is_hidden:
                    continue

                # COLLECTION CRUD INFO
                collection_crud_info_pipeline = [
                    {
                        '$match': {
                            'targeted_id': ObjectId(targeted_id)
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                            'let': {
                                'target_id': '$_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$targeted_id', '$$target_id'
                                            ]
                                        },
                                        'ref_api_consumer_id': ObjectId(api_Consumer["id"]),
                                        'is_hidden': False
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'targeted_id': 1,
                                        'ref_api_consumer_id': 1
                                    }
                                }
                            ],
                            'as': 'api_consumers'
                        }
                    }, {
                        '$match': {
                            'api_consumers': {
                                '$ne': []
                            }
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                            'let': {
                                'target_id': '$_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$targeted_id', '$$target_id'
                                            ]
                                        },
                                        'rbac_profile_id': ObjectId(user_profil["id"]),
                                        'is_hidden': False
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'targeted_id': 1,
                                        'rbac_profile_id': 1
                                    }
                                }
                            ],
                            'as': 'profiles'
                        }
                    }, {
                        '$match': {
                            'profiles': {
                                '$ne': []
                            }
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.SYS_APPLICATION.model_name}",
                            'let': {
                                'target_id': '$targeted_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$and': [
                                                {
                                                    '$eq': [
                                                        '$_id', '$$target_id'
                                                    ]
                                                }, {
                                                    '$eq': [
                                                        '$_id', ObjectId(
                                                            targeted_id)
                                                    ]
                                                }
                                            ]
                                        }
                                    }
                                }, {
                                    '$lookup': {
                                        'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                                        'let': {
                                            'app_id': '$_id'
                                        },
                                        'pipeline': [
                                            {
                                                '$match': {
                                                    '$expr': {
                                                        '$eq': [
                                                            '$targeted_id', '$$app_id'
                                                        ]
                                                    },
                                                    'ref_api_consumer_id': ObjectId(api_Consumer["id"])
                                                }
                                            }
                                        ],
                                        'as': 'app_consumers'
                                    }
                                }, {
                                    '$lookup': {
                                        'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                                        'let': {
                                            'app_id': '$_id'
                                        },
                                        'pipeline': [
                                            {
                                                '$match': {
                                                    '$expr': {
                                                        '$eq': [
                                                            '$targeted_id', '$$app_id'
                                                        ]
                                                    },
                                                    'rbac_profile_id': ObjectId(user_profil["id"])
                                                }
                                            }
                                        ],
                                        'as': 'menu_profiles'
                                    }
                                }, {
                                    '$match': {
                                        'app_consumers': {
                                            '$ne': []
                                        },
                                        'menu_profiles': {
                                            '$ne': []
                                        }
                                    }
                                }
                            ],
                            'as': 'apps'
                        }
                    }, {
                        '$match': {
                            'apps': {
                                '$ne': []
                            }
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_ENDPOINT.model_name}",
                            'let': {
                                'endpoint_id': '$rbac_endpoint_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$_id', '$$endpoint_id'
                                            ]
                                        }
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'url': 1,
                                        'label': 1,
                                        'flag': 1,
                                        'is_sudo_action': 1,
                                        'is_sudo_group_action': 1,
                                        'is_sudo_delegated_action': 1,
                                        'is_sudo_group_cross_validation_action': 1,
                                        'is_sudo_group_inter_organization_validation_action': 1,
                                    }
                                }
                            ],
                            'as': 'endpoints'
                        }
                    }, {
                        '$unwind': {
                            'path': '$endpoints',
                            'preserveNullAndEmptyArrays': True
                        }
                    }, {
                        '$sort': {
                            'order_by': 1
                        }
                    }, {
                        '$project': {
                            '_id': 1,
                            'targeted_id': 1,
                            'rbac_endpoint_id': 1,
                            'flag': 1,
                            'hard_code_flag': 1,
                            'parent_field_name': 1,
                            "label": 1,
                            'unwind__rbac_endpoint': {
                                '_id': '$endpoints._id',
                                'url': '$endpoints.url',
                                'label': '$endpoints.label',
                                'flag': '$endpoints.flag',
                                "rbac_title_id": '$endpoints.rbac_title_id',
                                "is_sudo_action": '$endpoints.is_sudo_action',
                                "is_sudo_group_action": '$endpoints.is_sudo_group_action',
                                "is_sudo_delegated_action": '$endpoints.is_sudo_delegated_action',
                                "is_sudo_group_cross_validation_action": '$endpoints.is_sudo_group_cross_validation_action',
                                "is_sudo_group_inter_organization_validation_action": '$endpoints.is_sudo_group_inter_organization_validation_action',
                            }
                        }
                    }
                ]
                collection_crud_info = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.REF_COLLECTION_CRUD_INFO,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=collection_crud_info_pipeline,
                    all_data=True
                )
                rbac_path_guard_dict = rbac_path_guard if rbac_path_guard else {}

                # RBAC COMPONENTS
                rbac_components_pipeline = [
                    # // Lookup permission targets for components
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                            'localField': '_id',
                            'foreignField': 'rbac_component_id',
                            'as': 'unwind__rbac_permission_target'
                        }
                    },
                    {
                        '$unwind': '$unwind__rbac_permission_target'
                    },

                    # // Lookup permissions
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                            'localField': 'unwind__rbac_permission_target.rbac_permission_id',
                            'foreignField': '_id',
                            'as': 'unwind__rbac_permission'
                        }
                    },
                    {
                        '$unwind': '$unwind__rbac_permission'
                    },

                    # // Add privilege lookup
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                            'let': {'permissionId': '$unwind__rbac_permission._id'},
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$and': [
                                                {'$eq': ['$rbac_permission_id',
                                                        '$$permissionId']},
                                                {'$eq': ['$sys_user_id', ObjectId(
                                                    user_details['id'])]},
                                                {'$eq': ['$status', 'added']}
                                            ]
                                        }
                                    }
                                }
                            ],
                            'as': 'direct_privileges'
                        }
                    },

                    # // Lookup permission roles (for role-based access)
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION_ROLE.model_name}",
                            'localField': 'unwind__rbac_permission._id',
                            'foreignField': 'rbac_permission_id',
                            'as': 'unwind__rbac_permission_role'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_permission_role',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Lookup roles
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_ROLE.model_name}",
                            'localField': 'unwind__rbac_permission_role.rbac_role_id',
                            'foreignField': '_id',
                            'as': 'unwind__rbac_role'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_role',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Lookup menu (sub-menu level: targeted_id is a SYS_MENU ID)
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.SYS_MENU.model_name}",
                            'localField': 'unwind__rbac_permission_target.targeted_id',
                            'foreignField': '_id',
                            'as': 'unwind__sys_menu'
                        }
                    },
                    {
                        '$unwind': '$unwind__sys_menu'
                    },

                    # // Lookup API consumer restrictions
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                            'localField': 'unwind__rbac_permission_target._id',
                            'foreignField': 'targeted_id',
                            'as': 'unwind__rbac_restricted_api_consumer'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_restricted_api_consumer',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Lookup profile restrictions
                    {
                        '$lookup': {
                            'from':f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                            'localField': 'unwind__rbac_permission_target._id',
                            'foreignField': 'targeted_id',
                            'as': 'unwind__rbac_restricted_profil'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_restricted_profil',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Final matching - handles both role-based and privilege-based access
                    {
                        '$match': {
                            '$and': [
                                # // Common requirements for both paths
                                {
                                    'unwind__sys_menu._id': ObjectId(targeted_id),
                                    'unwind__rbac_restricted_profil.rbac_profile_id': ObjectId(user_profil['id']),
                                    'unwind__rbac_restricted_api_consumer.ref_api_consumer_id': ObjectId(api_Consumer['id'])
                                },
                                # // Either role or privilege must be valid
                                {
                                    '$or': [
                                        # // Role-based access path
                                        {
                                            'unwind__rbac_role._id': ObjectId(user_details["rbac_role_id"])
                                        },
                                        # // Privilege-based access path
                                        {
                                            'direct_privileges': {'$ne': []}
                                        }
                                    ]
                                }
                            ]
                        }
                    },

                    # // Project results
                    {
                        '$project': {
                            '_id': 1,
                            'is_standalone': 1,
                            'label': 1,
                            'flag': 1,
                            'hard_code_flag': 1,
                            'access_via': {
                                '$cond': [
                                    {'$gt': [{'$size': '$direct_privileges'}, 0]},
                                    'privilege',
                                    'role'
                                ]
                            }
                        }
                    }
                ]

                # RBAC ACTIONS
                rbac_actions_pipelineXXXX = [
                    # // Lookup permission targets
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                            'localField': '_id',
                            'foreignField': 'rbac_action_id',
                            'as': 'unwind__rbac_permission_target'
                        }
                    },
                    {
                        '$unwind': '$unwind__rbac_permission_target'
                    },

                    # // Lookup permissions
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                            'localField': 'unwind__rbac_permission_target.rbac_permission_id',
                            'foreignField': '_id',
                            'as': 'unwind__rbac_permission'
                        }
                    },
                    {
                        '$unwind': '$unwind__rbac_permission'
                    },
                    # // Add privilege lookup
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                            'let': {'permissionId': '$unwind__rbac_permission._id'},
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$and': [
                                                {'$eq': ['$rbac_permission_id',
                                                        '$$permissionId']},
                                                {'$eq': ['$sys_user_id', ObjectId(
                                                    user_details['id'])]},
                                                {'$eq': ['$status', 'added']}
                                            ]
                                        }
                                    }
                                }
                            ],
                            'as': 'direct_privileges'
                        }
                    },

                    # // Lookup permission roles (for role-based access)
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION_ROLE.model_name}",
                            'localField': 'unwind__rbac_permission._id',
                            'foreignField': 'rbac_permission_id',
                            'as': 'unwind__rbac_permission_role'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_permission_role',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Lookup roles
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_ROLE.model_name}",
                            'localField': 'unwind__rbac_permission_role.rbac_role_id',
                            'foreignField': '_id',
                            'as': 'unwind__rbac_role'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_role',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Lookup menu (sub-menu level: targeted_id is a SYS_MENU ID)
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.SYS_MENU.model_name}",
                            'localField': 'unwind__rbac_permission_target.targeted_id',
                            'foreignField': '_id',
                            'as': 'unwind__sys_menu'
                        }
                    },
                    {
                        '$unwind': '$unwind__sys_menu'
                    },

                    # // Lookup API consumer restrictions
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                            'localField': 'unwind__rbac_permission_target._id',
                            'foreignField': 'targeted_id',
                            'as': 'unwind__rbac_restricted_api_consumer'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_restricted_api_consumer',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Lookup profile restrictions
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                            'localField': 'unwind__rbac_permission_target._id',
                            'foreignField': 'targeted_id',
                            'as': 'unwind__rbac_restricted_profil'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_restricted_profil',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Final matching - handles both role-based and privilege-based access
                    {
                        '$match': {
                            '$and': [
                                # // Common requirements for both paths
                                {
                                    'unwind__sys_menu._id': ObjectId(targeted_id),
                                    'unwind__rbac_restricted_profil.rbac_profile_id': ObjectId(user_profil['id']),
                                    'unwind__rbac_restricted_api_consumer.ref_api_consumer_id': ObjectId(api_Consumer['id'])
                                },
                                # // Either role or privilege must be valid
                                {
                                    '$or': [
                                        # // Role-based access path
                                        {
                                            'unwind__rbac_role._id': ObjectId(user_details['rbac_role_id'])
                                        },
                                        # // Privilege-based access path
                                        {
                                            'direct_privileges': {'$ne': []}
                                        }
                                    ]
                                }
                            ]
                        }
                    },

                    # // Project results
                    {
                        '$project': {
                            '_id': 1,
                            'is_standalone': 1,
                            'label': 1,
                            'flag': 1,
                            'hard_code_flag': 1,
                            'access_via': {
                                '$cond': [
                                    {'$gt': [{'$size': '$direct_privileges'}, 0]},
                                    'privilege',
                                    'role'
                                ]
                            }
                        }
                    }
                ]
                
                rbac_actions_pipeline = [
                    # // Lookup permission targets
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                            'localField': '_id',
                            'foreignField': 'rbac_action_id',
                            'as': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
                        }
                    },
                    {
                        '$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
                    },

                    # // Lookup permissions
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                            'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.rbac_permission_id',
                            'foreignField': '_id',
                            'as': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
                        }
                    },
                    {
                        '$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
                    },
                    # // Add privilege lookup
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                            'let': {'permissionId': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id'},
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$and': [
                                                {'$eq': ['$rbac_permission_id',
                                                        '$$permissionId']},
                                                {'$eq': ['$sys_user_id', ObjectId(
                                                    user_details['id'])]},
                                                {'$eq': ['$status', 'added']}
                                            ]
                                        }
                                    }
                                }
                            ],
                            'as': 'direct_privileges'
                        }
                    },

                    # // Lookup permission roles (for role-based access)
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION_ROLE.model_name}",
                            'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id',
                            'foreignField': 'rbac_permission_id',
                            'as': f'unwind__{CollectionKey.RBAC_PERMISSION_ROLE.model_name}'
                        }
                    },
                    {
                        '$unwind': {
                            'path': f'$unwind__{CollectionKey.RBAC_PERMISSION_ROLE.model_name}',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Lookup roles
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_ROLE.model_name}",
                            'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_ROLE.model_name}.rbac_role_id',
                            'foreignField': '_id',
                            'as': 'unwind__rbac_role'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_role',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Lookup application
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.SYS_APPLICATION.model_name}",
                            'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.targeted_id',
                            'foreignField': '_id',
                            'as': f'unwind__{CollectionKey.SYS_APPLICATION.model_name}'
                        }
                    },
                    {
                        '$unwind': f'$unwind__{CollectionKey.SYS_APPLICATION.model_name}'
                    },

                    # // Lookup API consumer restrictions
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                            'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}._id',
                            'foreignField': 'targeted_id',
                            'as': f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}'
                        }
                    },
                    {
                        '$unwind': {
                            'path': f'$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Lookup profile restrictions
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                            'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}._id',
                            'foreignField': 'targeted_id',
                            'as': f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}'
                        }
                    },
                    {
                        '$unwind': {
                            'path': f'$unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Final matching - handles both role-based and privilege-based access
                    {
                        '$match': {
                            '$and': [
                                # // Common requirements for both paths
                                {
                                    f'unwind__{CollectionKey.SYS_APPLICATION.model_name}._id': ObjectId(targeted_id),
                                    f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.rbac_profile_id': ObjectId(user_profil['id']),
                                    f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id': ObjectId(api_Consumer['id'])
                                },
                                # // Either role or privilege must be valid
                                {
                                    '$or': [
                                        # // Role-based access path
                                        {
                                            'unwind__rbac_role._id': ObjectId(user_details['rbac_role_id'])
                                        },
                                        # // Privilege-based access path
                                        {
                                            'direct_privileges': {'$ne': []}
                                        }
                                    ]
                                }
                            ]
                        }
                    },

                    # // Project results
                    {
                        '$project': {
                            '_id': 1,
                            'is_standalone': 1,
                            'label': 1,
                            'flag': 1,
                            'hard_code_flag': 1,
                            'access_via': {
                                '$cond': [
                                    {'$gt': [{'$size': '$direct_privileges'}, 0]},
                                    'privilege',
                                    'role'
                                ]
                            }
                        }
                    }
                ]
                
                formated_actions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_ACTION,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=rbac_actions_pipeline,
                    all_data=True
                )
                formated_components = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_COMPONENT,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=rbac_components_pipeline,
                    all_data=True
                )
                sub_menus_list = []
                current_item = {
                    **apps,
                    'order_by': order_by,
                    'ishidden': is_hidden,
                    'isactivated': is_activated,
                    # 'ref_children_display_type': ref_children_display_type_info,
                    # 'ref_data_display_type': ref_data_display_type_info,
                    'collection_crud_info': collection_crud_info,

                    "rbac_actions": formated_actions,
                    "rbac_components": formated_components,

                    'rbac_path_guard': {
                        **rbac_path_guard_dict,
                    } if is_activated == True else {},
                    "sub_menus": sub_menus_list
                }
                formatted_data.append({
                    **current_item,
                })

                nested_icon = {}
                cached_app_icon_data = None
                
                if cached_app_icon_data:
                    
                    self.app_debug_print(
                        f"Returning cached app nested_icon data  senat_digit apps", True)
                    cached_app_icon_json = json.loads(cached_app_icon_data)
                    nested_icon = cached_app_icon_json
                else:
                    menu_or_app_flag = extract_field_on_output_data_element(apps, 'flag', output_data_type)
                    menu_or_app_path = extract_field_on_output_data_element(rbac_path_guard_dict, 'path', output_data_type)
                    api_consumer_flag = api_Consumer['flag']
                    nested_url_icon = SvgIconService.build_svg_icon_file_server_url(
                        menu_or_app_flag=menu_or_app_flag,
                        menu_or_app_path=menu_or_app_path,
                        api_consumer_flag=api_consumer_flag,
                    )

                    self.app_debug_print(f" \n\n nested_url_icon new version  senat_digit apps: {nested_url_icon} \n\n", True)

                    # Ensure first response (cache miss) still contains icon URL.
                    nested_icon = {
                        "icon_url": nested_url_icon
                    } 
                index_of_menu = formatted_data.index(current_item)
                # Update the item at the found index — flat icon for mobile
                formatted_data[index_of_menu] = {
                    **formatted_data[index_of_menu],
                    "icon": {
                        "icon_url": nested_icon.get('icon_url', None)
                    }
                }
                # Now, sort formatted_data by 'order_by' ascending:
                formatted_data.sort(key=lambda item: item['order_by'])

            # In compact mode, embed sub-menus for each application
            if settings.APP_MENU_FETCH_PARADIGM == "compact":
                formatted_data = await self._embed_compact_submenus(
                    formatted_data=formatted_data,
                    api_consumer=api_Consumer,
                    user_details=user_details,
                    user_profil=user_profil,
                    output_data_type=output_data_type,  # already forced to 'default' at the top of this method
                    label="lokotroo-mobile",
                )

            # Calculate database fetch time
            db_fetch_time = round((time.time() - db_fetch_start) * 1000, 2)
            total_method_time = round((time.time() - method_start_time) * 1000, 2)

            # ── Slim down response for mobile: only needed fields ──
            def slim_menu(item):
                """Strip a menu/application dict to only mobile-needed fields."""
                def _str_val(v):
                    """Extract .value from Enum instances, pass strings through."""
                    import enum
                    return v.value if isinstance(v, enum.Enum) else v

                rbac_pg = item.get('rbac_path_guard', {})
                actionx = item.get('rbac_actions')
                print(f"\n\n\n\n ACTIONS :>>>>: {actionx}\n\n\n")
                return {
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'description_str': item.get('description_str'),
                    'application_group_flag': item.get('application_group_flag'),
                    'flag': item.get('flag'),
                    'order_by': item.get('order_by'),
                    'ishidden': item.get('ishidden', False),
                    'isactivated': item.get('isactivated', True),
                    'rbac_path_guard': {
                        'path': rbac_pg.get('path'),
                        'path_guard': rbac_pg.get('path_guard'),
                    },
                    'rbac_actions': [
                        {
                            'flag': _str_val(a.get('flag')),
                            'hard_code_flag': _str_val(a.get('hard_code_flag')),
                            'label': a.get('label'),
                        }
                        for a in (item.get('rbac_actions') or [])
                    ],
                    'rbac_components': [
                        {
                            'flag': _str_val(c.get('flag')),
                            'hard_code_flag': _str_val(c.get('hard_code_flag')),
                            'label': c.get('label'),
                        }
                        for c in (item.get('rbac_components') or [])
                    ],
                    'collection_crud_info': [
                        {
                            'flag': _str_val(ci.get('flag')),
                            'hard_code_flag': ci.get('hard_code_flag'),
                            'rbac_endpoint': {
                                'url': ep.get('url'),
                                'is_sudo_action': ep.get('is_sudo_action'),
                                'is_sudo_group_action': ep.get('is_sudo_group_action'),
                            } if ep else None,
                        }
                        for ci in (item.get('collection_crud_info') or [])
                        for ep in [ci.get('rbac_endpoint') or ci.get('unwind__rbac_endpoint')]
                    ],
                    'icon': item.get('icon', {}),
                    'sub_menus': [slim_menu(sm) for sm in (item.get('sub_menus') or [])],
                }


            formatted_data = [slim_menu(app) for app in formatted_data]

            print(f"\n\n\n\n formatted_data :>>>>: {formatted_data}\n\n\n")
            # Prepare response data
            response_data = {
                "status_code": status.HTTP_200_OK,
                "data": formatted_data,
                "app_menu_fetch_paradigm": settings.APP_MENU_FETCH_PARADIGM,
            }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content=response_data
            )

        except Exception as e:
            self.app_debug_print(f"Error fetch_agent_app_formated_applications: {str(e)}", True)
            raise HTTPException(
                status_code=500, detail="An unexpected error occurred.")
        

    async def _embed_compact_submenus(
        self,
        formatted_data: list,
        api_consumer: dict,
        user_details: dict,
        user_profil: dict,
        output_data_type: str,
        label: str,
        progress_callback: Optional[Any] = None,
    ) -> list:
        """Embed sub_menus tree under each application in `formatted_data`.

        `output_data_type` must be the string value ('default' or 'data_table').
        Handles both the dict-wrapped (data_table) and plain (default) id shapes.
        `label` is appended to debug prints so mobile vs web are distinguishable.
        """
        if not formatted_data:
            return formatted_data

        self.app_debug_print(
            f"🚀 [{label}] COMPACT MODE: Embedding sub-menus for {len(formatted_data)} applications",
            True,
        )
        compact_start = time.time()

        async def fetch_app_submenus(app_data):
            raw_id = app_data.get('id')
            if isinstance(raw_id, dict):
                app_id = raw_id.get('display_value') or raw_id.get('real_value')
            else:
                app_id = raw_id

            if not app_id:
                return app_data

            if progress_callback is not None:
                await progress_callback(
                    {
                        "event": "app_started",
                        "message": "Chargement des menus…",
                        "percent": 80,
                        "application_id": str(app_id),
                        "application_flag": app_data.get("flag"),
                        "application_name": app_data.get("name"),
                    }
                )

            try:
                sub_menus = await ApplicationService.get_user_application_submenus_compact(
                    application_id=app_id,
                    apiConsumer=api_consumer,
                    user=user_details,
                    userProfil=user_profil,
                    page=0,
                    limit=50,
                    all_data=True,
                    accept_language=self.accept_language,
                    output_data_type=output_data_type,
                )
                app_data['sub_menus'] = sub_menus or []
                self.app_debug_print(
                    f"📦 [{label}] app {app_id} → {len(app_data['sub_menus'])} sub_menus",
                    True,
                )
                if progress_callback is not None:
                    await progress_callback(
                        {
                            "event": "app_completed",
                            "message": "Chargement des menus…",
                            "percent": 90,
                            "application_id": str(app_id),
                            "application_flag": app_data.get("flag"),
                            "application_name": app_data.get("name"),
                            "sub_menus_count": len(app_data["sub_menus"]),
                        }
                    )
            except Exception as e:
                self.app_debug_print(
                    f"❌ [{label}] fetch_app_submenus exception for app {app_id}: "
                    f"{type(e).__name__}: {str(e)}",
                    True,
                )
                app_data['sub_menus'] = []
                if progress_callback is not None:
                    await progress_callback(
                        {
                            "event": "app_failed",
                            "message": str(e),
                            "application_id": str(app_id),
                            "application_flag": app_data.get("flag"),
                            "application_name": app_data.get("name"),
                        }
                    )
            return app_data

        from app.modules.core.utils.common.async_runner import AsyncExecutor
        compact_results = await AsyncExecutor.gather_with_limit(
            [fetch_app_submenus(app) for app in formatted_data],
            limit=5,
            return_exceptions=True,
        )
        formatted_data = [
            r for r in compact_results
            if r is not None and not isinstance(r, Exception)
        ]
        formatted_data.sort(key=lambda item: item.get('order_by', 0) or 0)

        compact_time = round((time.time() - compact_start) * 1000, 2)
        self.app_debug_print(
            f"🏁 [{label}] COMPACT sub-menus embedded in {compact_time}ms", True
        )
        return formatted_data
    
   
   
    async def fetch_formated_application_user_sub_menus(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page")
    ):
        # 🕐 START TIMING
        method_start_time = time.time()
        self.app_debug_print(f"🚀 Starting fetch_formated_application_user_sub_menus at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}", True)

        try:
            # DECODE USER TOKEN convert_query_params
            auth_start_time = time.time()
            user_details = await self.get_user_info(request, self.accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
            auth_time = round((time.time() - auth_start_time) * 1000, 2)
            self.app_debug_print(f"🔐 Authentication completed in {auth_time}ms", True)

            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = ConverterService.convert_query_params(raw_query_params)
            sys_application_id = query_params.get('sys_application_id', None)

            # CACHE IMPLEMENTATION
            cache_params = {
                'output_data_type': output_data_type.value if output_data_type else 'default',
                'all_data': all_data,
                'page': page,
                'limit': limit,
                'sys_application_id': sys_application_id,
                'user_profil_id': user_profil['id'],
                'api_consumer_id': api_Consumer['id'],
                'accept_language': self.accept_language,
                'app_menu_fetch_paradigm': settings.APP_MENU_FETCH_PARADIGM,
            }

            cache_key = self._generate_cache_key(
                user_id=user_details.get('id', 'anonymous'),
                method_name='fetch_formated_application_user_sub_menus',
                **cache_params
            )

            # 1. Check cache first
            cache_check_start = time.time()
            cached_data = await self._get_cached_data(cache_key)
            cache_check_time = round((time.time() - cache_check_start) * 1000, 2)

            if cached_data:
                total_time = round((time.time() - method_start_time) * 1000, 2)
                self.app_debug_print(f"⚡ CACHE HIT - Returning cached sub menus data | Total time: {total_time}ms", True)
                # Ensure paradigm is always current even in cached responses
                if isinstance(cached_data, dict):
                    cached_data['app_menu_fetch_paradigm'] = settings.APP_MENU_FETCH_PARADIGM
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content=cached_data
                )

            # Cache miss - continue with service call
            self.app_debug_print(f"💾 Cache check completed in {cache_check_time}ms - proceeding with service fetch", True)

            # Start service call timing
            service_fetch_start = time.time()

            # Compact mode: batch fetch all sub-menus in ~7 queries
            if settings.APP_MENU_FETCH_PARADIGM == "compact":
                self.app_debug_print(f"🚀 COMPACT MODE: Fetching all sub-menus in batch", True)
                sub_menus_list = await ApplicationService.get_user_application_submenus_compact(
                    application_id=sys_application_id,
                    apiConsumer=api_Consumer,
                    user=user_details,
                    userProfil=user_profil,
                    page=0,
                    limit=50,
                    all_data=True,
                    accept_language=self.accept_language,
                    output_data_type=OutputDataType(output_data_type).value,
                )
            else:
                sub_menus_list = await ApplicationService.get_user_application_submenus(
                    application_id=sys_application_id,
                    apiConsumer=api_Consumer,
                    user=user_details,
                    userProfil=user_profil,
                    page=0,
                    limit=50,
                    all_data=True,
                    accept_language=self.accept_language,
                    output_data_type=OutputDataType(output_data_type).value,
                )

            # Calculate timing
            service_fetch_time = round((time.time() - service_fetch_start) * 1000, 2)
            total_method_time = round((time.time() - method_start_time) * 1000, 2)

            # Prepare response data
            response_data = {
                "status_code": status.HTTP_200_OK,
                "data": sub_menus_list,
                "app_menu_fetch_paradigm": settings.APP_MENU_FETCH_PARADIGM,
            }

            # 2. Cache the response data (with verification)
            cache_store_start = time.time()
            await self._set_cached_data(cache_key, response_data, ttl=settings.CACHE_DEFAULT_APPLICATION_TIMEOUT)  # 30 minutes
            cache_store_time = round((time.time() - cache_store_start) * 1000, 2)

            # Verify cache was stored
            await self._verify_cache_storage(cache_key)

            # Log performance metrics
            self.app_debug_print(f"🏁 SERVICE FETCH COMPLETE | Service time: {service_fetch_time}ms | Cache store: {cache_store_time}ms | Total time: {total_method_time}ms | Records: {len(sub_menus_list) if isinstance(sub_menus_list, list) else 'N/A'}", True)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content=response_data
            )

        except Exception as e:
            self.app_debug_print(f"Error fetch_formated_application_user_sub_menus: {str(e)}", True)
            raise HTTPException(
                status_code=500, detail="An unexpected error occurred.")

    async def fetch_formated_menu_user_sub_menus(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            50, description="Number of items per page")
    ):
        # 🕐 START TIMING
        method_start_time = time.time()
        self.app_debug_print(f"🚀 Starting fetch_formated_menu_user_sub_menus at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}", True)

        try:
            # DECODE USER TOKEN convert_query_params
            auth_start_time = time.time()
            user_details = await self.get_user_info(request, self.accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
            auth_time = round((time.time() - auth_start_time) * 1000, 2)
            self.app_debug_print(f"🔐 Authentication completed in {auth_time}ms", True)

            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = ConverterService.convert_query_params(raw_query_params)
            sys_menu_id = query_params.get('sys_menu_id', None)

            # CACHE IMPLEMENTATION
            cache_params = {
                'output_data_type': output_data_type.value if output_data_type else 'default',
                'all_data': all_data,
                'page': page,
                'limit': limit,
                'sys_menu_id': sys_menu_id,
                'user_profil_id': user_profil['id'],
                'api_consumer_id': api_Consumer['id'],
                'accept_language': self.accept_language,
                'app_menu_fetch_paradigm': settings.APP_MENU_FETCH_PARADIGM,
            }

            cache_key = self._generate_cache_key(
                user_id=user_details.get('id', 'anonymous'),
                method_name='fetch_formated_menu_user_sub_menus',
                **cache_params
            )

            # 1. Check cache first
            cache_check_start = time.time()
            cached_data = await self._get_cached_data(cache_key)
            cache_check_time = round((time.time() - cache_check_start) * 1000, 2)

            if cached_data:
                total_time = round((time.time() - method_start_time) * 1000, 2)
                self.app_debug_print(f"⚡ CACHE HIT - Returning cached menu sub menus data | Total time: {total_time}ms", True)
                # Ensure paradigm is always current even in cached responses
                if isinstance(cached_data, dict):
                    cached_data['app_menu_fetch_paradigm'] = settings.APP_MENU_FETCH_PARADIGM
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content=cached_data
                )

            # Cache miss - continue with service call
            self.app_debug_print(f"💾 Cache check completed in {cache_check_time}ms - proceeding with service fetch", True)

            # Start service call timing
            service_fetch_start = time.time()
            sub_menus_list = await ApplicationService.get_user_menu_submenus(
                sys_menu_id=sys_menu_id,
                apiConsumer=api_Consumer,
                user=user_details,
                userProfil=user_profil,
                page=0,
                limit=50,
                all_data=True,
                accept_language=self.accept_language,
                output_data_type=OutputDataType(output_data_type).value,
            )

            # Calculate timing
            service_fetch_time = round((time.time() - service_fetch_start) * 1000, 2)
            total_method_time = round((time.time() - method_start_time) * 1000, 2)

            # Prepare response data
            response_data = {
                "status_code": status.HTTP_200_OK,
                "data": sub_menus_list,
                "app_menu_fetch_paradigm": settings.APP_MENU_FETCH_PARADIGM,
            }

            # 2. Cache the response data (with verification)
            cache_store_start = time.time()
            await self._set_cached_data(cache_key, response_data, ttl=settings.CACHE_DEFAULT_APPLICATION_TIMEOUT)  # 30 minutes
            cache_store_time = round((time.time() - cache_store_start) * 1000, 2)

            # Verify cache was stored
            await self._verify_cache_storage(cache_key)

            # Debug: Show all cache keys for this user
            await self._debug_all_cache_keys(user_details.get('id', 'anonymous'))

            # Log performance metrics
            self.app_debug_print(f"🏁 SERVICE FETCH COMPLETE | Service time: {service_fetch_time}ms | Cache store: {cache_store_time}ms | Total time: {total_method_time}ms | Records: {len(sub_menus_list) if isinstance(sub_menus_list, list) else 'N/A'}", True)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content=response_data
            )

        except Exception as e:
            self.app_debug_print(f"Error fetch_formated_menu_user_sub_menus: {str(e)}", True)
            raise HTTPException(
                status_code=500, detail="An unexpected error occurred.")


    async def fetch_formated_organization_roles(
        self,
        request: Request,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page"),
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
    ):

        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)
        # user_details = await self.get_user_info(request=request,accept_language=accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
        self.app_debug_print(f"\n\n user_profil :{user_profil}\n\n", False)

        saas_config_info = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SAAS_CONFIG,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )

        if not saas_config_info:
            message = self.get_response_message(
                MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        authenticationService = AuthenticatedService()
        support_email = self.get_system_support_email(
            saas_config_info, self.accept_language)

        role_pipeline = [

            # 1.
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PERMISSION_ROLE.model_name}",
                    'localField': "_id",
                    'foreignField': "rbac_role_id",
                    'as': "unwind__rbac_permission_role"
                }
            },
            # 2. Unwind the rbac_permission_role array.
            {
                '$unwind': "$unwind__rbac_permission_role"
            },
            # 3.
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                    'localField': "unwind__rbac_permission_role.rbac_permission_id",
                    'foreignField': "_id",
                    'as': "unwind__rbac_permission"
                }
            },
            {
                "$match": {
                    "$or": [
                        {
                            "sys_organization_id": ObjectId(user_details['sys_organization_id']),
                            "rbac_profile_id": ObjectId(user_profil['id'])
                        },
                        {
                            "sys_organization_id": None,
                            "rbac_profile_id": ObjectId(user_profil['id']),
                        }
                    ],
                }
            },
            {
                "$sort": {
                    "name": 1
                }
            },
            # Group by the sys_application _id and push matching documents into an array field "docs"
            {
                "$group": {
                    "_id": "$_id",
                    "docs": {"$push": "$$ROOT"}
                }
            },
            # Merge the array of documents into one object per group.
            {
                "$project": {
                    "merged": {
                        "$reduce": {
                            "input": "$docs",
                            "initialValue": {},
                            "in": {"$mergeObjects": ["$$value", "$$this"]}
                        }
                    }
                }
            },
            # Replace the root with the merged document so that fields are at the top level.
            {
                "$replaceRoot": {"newRoot": "$merged"}
            }
        ]
        roles = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.RBAC_ROLE,
            output_data_type=output_data_type,
            accept_language=self.accept_language,
            pipeline=role_pipeline,
        )

        self.app_debug_print(f" \n\n roles : {len(roles)} \n\n", True)

        # Now, sort formatted_data by 'order_by' ascending:
        roles.sort(key=lambda item: item['name'])
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": roles
            }
        )

    async def fetch_api_consumer_profiles(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page")
    ):

        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)

        # allApiConsumer = await self.generic_service.fetch_data_from_collection(
        #     collection_key=CollectionKey.REF_API_CONSUMER,
        #     all_data=all_data,
        #     output_data_type=OutputDataType(output_data_type).value,
        #     accept_language= self.accept_language,
        #     limit=limit,
        #     page=page,
        #     query={}
        # )
        self.app_debug_print(
            f"\n\n output_data_type >< : {output_data_type} \n\n", False)
        # allApiConsumer = []
        allApiConsumer = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.REF_API_CONSUMER,
            output_data_type=OutputDataType(output_data_type).value,
            accept_language=self.accept_language,
            limit=limit,
            page=page,
            pipeline=[
                {
                    "$match": {
                        "is_activated": True
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "name": 1,
                        "description_str": 1,
                    }
                }
            ]
        )

        allProfiles = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.RBAC_PROFILE,
            limit=limit,
            page=page,
            output_data_type=OutputDataType(output_data_type).value,
            accept_language=self.accept_language,
            pipeline=[
                {
                    "$match": {
                        "is_activated": True
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "name": 1,
                        "description_str": 1,
                        # "flag":1,
                    }
                }
            ]
        )
        self.app_debug_print(
            f"\n\n allApiConsumer : {allApiConsumer} \n\n", False)
        self.app_debug_print(f"\n\n allProfiles : {allProfiles} \n\n", False)
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": {
                    "profiles": allProfiles,
                    "apiConsumer": allApiConsumer
                },
            }
        )

    async def fetch_global_user_validators(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page"),
        endpoint_call: Optional[bool] = False
    ):
        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)
        # user_details = await self.get_user_info(request=request,accept_language=accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
        print(f"\n\n\n output_data_type : {output_data_type} \n\n\n")
        print(f"\n\n\n all_data : {all_data} \n\n\n")
        print(f"\n\n\n limit : {limit} \n\n\n")
        pipeline = [
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_USER_VALIDATOR.model_name}",
                    "localField": "_id",
                    "foreignField": "sys_user_id",
                    "as": "unwind__rbac_user_validator"
                }
            },
            {
                "$unwind": "$unwind__rbac_user_validator"
            },
            {
                "$match": {
                    "sys_organization_id": ObjectId(user_details['sys_organization_id']),
                    "unwind__rbac_user_validator.rbac_sudo_action_id": None
                }
            },
            {
                "$limit": limit
            },
            {
                "$skip": limit * page
            },
        ]

        all_pipeline = [
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_USER_VALIDATOR.model_name}",
                    "localField": "_id",
                    "foreignField": "sys_user_id",
                    "as": "unwind__rbac_user_validator"
                }
            },
            {
                "$unwind": "$unwind__rbac_user_validator"
            },
            {
                "$match": {
                    "sys_organization_id": ObjectId(user_details['sys_organization_id']),
                    "unwind__rbac_user_validator.rbac_sudo_action_id": None
                }
            },
        ]

        sudo_group_users = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.SYS_USER,
            output_data_type=output_data_type,
            accept_language=self.accept_language,
            pipeline=pipeline,
        )
        self.app_debug_print(
            f" sudo_group_users len : {len(sudo_group_users)}", True)
        extra_data = {
            "limit": limit,
            "max": 0
        }
        if not all_data:
            # get max
            max_data = await self.generic_service.fetch_native_aggregate_count_from_collection(
                collection_key=CollectionKey.SYS_USER,
                accept_language=self.accept_language,
                pipeline=all_pipeline,
            )
            extra_data = {
                "max": max_data,
                "limit": limit
            }
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": sudo_group_users,
                **extra_data
            }
        )

    async def fetch_pending_validation_requests(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page"),
        endpoint_call: Optional[bool] = Query(False, description="Endpoint call")
    ):
        from app.modules.security.models.ops_validation_request.ops_validation_request_model import OpsValidationRequestModel
        from app.modules.security.models.ops_validation_request_user.ops_validation_request_user_model import OpsValidationRequestUserModel

        # Helper to wrap a value in data-table ApiProperty format
        def _prop(name: str, value, title: str = "", data_type: dict = None):
            return {
                "property_name": name,
                "display_title": title or name,
                "default_value": value,
                "display_value": value,
                "data_type": data_type or {"is_string": True},
                "constraints": {},
                "extra_metas": {},
            }

        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)

        raw_query_params: Dict[str, str] = dict(request.query_params)
        query_params = ConverterService.convert_query_params(raw_query_params)

        # Find validation requests where the current user is a linked validator
        current_user_oid = ObjectId(user_details['id'])
        org_oid = ObjectId(user_details['sys_organization_id'])

        # Get OpsValidationRequestUser rows for this user in this org
        user_validator_rows = await OpsValidationRequestUserModel.find(
            OpsValidationRequestUserModel.sys_user_id == current_user_oid,
            OpsValidationRequestUserModel.sys_organization_id == org_oid,
        ).to_list()

        request_ids = list({row.ops_validation_request_id for row in user_validator_rows})

        if not request_ids:
            extra_data = {"max": 0, "limit": limit} if not all_data else {}
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": [],
                    **extra_data
                }
            )

        # Paginated fetch of the actual OpsValidationRequest documents
        total_count = await OpsValidationRequestModel.find(
            {"_id": {"$in": request_ids}}
        ).count()

        validation_requests = await OpsValidationRequestModel.find(
            {"_id": {"$in": request_ids}}
        ).sort("-created_at").skip(limit * page).limit(limit).to_list()

        formated_data = []
        for vr in validation_requests:
            # Get formatted data from model (includes validation_request_users with sys_user info)
            formatted = await vr.get_formated_data(self.accept_language)

            # Determine current user's validator row for this request
            current_status = formatted.get("status", EMultipleValidationStatus.PENDING.value)
            next_validator_id = str(vr.next_validator_id) if vr.next_validator_id else None
            created_by_id = str(vr.created_by_id) if hasattr(vr, 'created_by_id') and vr.created_by_id else None

            validation_request_users = formatted.get("validation_request_users", [])

            # Count validators with validation access
            validator_count = sum(1 for u in validation_request_users if u.get("has_validation_access") == True)

            # Compute decision count (users who already submitted a decision)
            decision_count = sum(
                1 for u in validation_request_users
                if u.get("has_validation_access") == True
                and u.get("decision") is not None
                and u.get("decision") != EMultipleValidationStatus.PENDING.value
            )

            # Is the request still actionable?
            is_pending_or_in_progress = current_status in (
                EMultipleValidationStatus.PENDING.value,
                EMultipleValidationStatus.IN_PROGRESS.value,
            )

            # Determine if current user is the next validator and still pending
            is_current_validator = (
                user_details['id'] == next_validator_id
                and is_pending_or_in_progress
            )

            # Find current user's row to check their decision status
            current_user_row = None
            for u in validation_request_users:
                if u.get("sys_user_id") == user_details['id']:
                    current_user_row = u
                    break

            user_has_validation_access = (
                current_user_row.get("has_validation_access", False) if current_user_row else False
            )
            user_decision = current_user_row.get("decision") if current_user_row else None
            user_has_not_decided = user_decision is None or user_decision == EMultipleValidationStatus.PENDING.value

            can_validate = (
                user_has_validation_access
                and is_current_validator
                and user_has_not_decided
            )
            can_reject = can_validate  # same permission
            can_delete = (
                user_details['id'] == created_by_id
                and current_status == EMultipleValidationStatus.PENDING.value
            )

            # Enrich each validation_request_user with is_current_validator flag
            enriched_users = []
            for vu in validation_request_users:
                vu_sys_user_id = vu.get("sys_user_id")
                vu_is_current = (
                    vu_sys_user_id == next_validator_id
                    and is_pending_or_in_progress
                    and vu.get("has_validation_access") == True
                )
                # Build user sub-object from sys_user data
                sys_user = vu.get("sys_user") or {}
                user_obj = {
                    "id": _prop("id", vu.get("id"), "ID"),
                    "first_name": _prop("first_name", sys_user.get("first_name", ""), "First Name"),
                    "last_name": _prop("last_name", sys_user.get("last_name", ""), "Last Name"),
                    "email": _prop("email", sys_user.get("email", ""), "Email"),
                    "phone_number": _prop("phone_number", sys_user.get("phone_number", ""), "Phone"),
                    "username": _prop("username", sys_user.get("username", ""), "Username"),
                    "sys_user_id": _prop("sys_user_id", vu_sys_user_id, "User ID"),
                    "has_validation_access": _prop("has_validation_access", vu.get("has_validation_access", False), "Has Validation Access", {"is_boolean": True}),
                    "is_current_validator": _prop("is_current_validator", vu_is_current, "Is Current Validator", {"is_boolean": True}),
                }

                enriched_users.append({
                    "id": _prop("id", vu.get("id"), "ID"),
                    "comment": _prop("comment", vu.get("comment"), "Comment"),
                    "user": user_obj,
                    "sys_user_id": _prop("sys_user_id", vu_sys_user_id, "User ID"),
                    "status": _prop("status", current_status, "Status"),
                    "decision_status": _prop("decision_status", vu.get("decision") or EMultipleValidationStatus.PENDING.value, "Decision Status"),
                    "decided_at": _prop("decided_at", vu.get("decided_at"), "Decided At", {"is_date": True}),
                    "device_info": _prop("device_info", vu.get("device_info"), "Device Info"),
                    "ip_address": _prop("ip_address", vu.get("ip_address"), "IP Address"),
                    "location_info": _prop("location_info", vu.get("location_info"), "Location Info"),
                    "created_at": _prop("created_at", vu.get("created_at"), "Created At", {"is_date": True}),
                })

            # Find the current_validator user object
            current_validator_obj = None
            for eu in enriched_users:
                if eu["user"]["is_current_validator"]["display_value"] == True:
                    current_validator_obj = eu["user"]
                    break

            formated_data.append({
                "id": _prop("id", formatted.get("id"), "ID"),
                "identifier": _prop("identifier", formatted.get("identifier"), "Identifier"),
                "created_at": _prop("created_at", formatted.get("created_at"), "Created At", {"is_date": True}),
                "endpoint_path": _prop("endpoint_path", formatted.get("endpoint_path"), "Endpoint Path"),
                "endpoint_method": _prop("endpoint_method", formatted.get("endpoint_method"), "Endpoint Method"),
                "status": _prop("status", current_status, "Status"),
                "operation_type": _prop("operation_type", formatted.get("operation_type"), "Operation Type"),
                "list_of_formated_validation_decisions": enriched_users,
                "list_of_validators": [eu["user"] for eu in enriched_users],
                "current_validator": current_validator_obj,
                "validator_count": _prop("validator_count", validator_count, "Validator Count", {"is_number": True}),
                "decision_count": _prop("decision_count", decision_count, "Decision Count", {"is_number": True}),
                "is_current_validator": _prop("is_current_validator", is_current_validator, "Is Current Validator", {"is_boolean": True}),
                "can_validate": _prop("can_validate", can_validate, "Can Validate", {"is_boolean": True}),
                "can_reject": _prop("can_reject", can_reject, "Can Reject", {"is_boolean": True}),
                "can_delete": _prop("can_delete", can_delete, "Can Delete", {"is_boolean": True}),
                # Permission / endpoint metadata resolved from endpoint_path (endpoint label, permission label/flag)
                "permission_info": formatted.get("permission_info", None),
            })

        extra_data = {}
        if not all_data:
            extra_data = {
                "max": total_count,
                "limit": limit
            }
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": formated_data,
                **extra_data
            }
        )
    async def fetch_single_validation_request(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page"),
        endpoint_call: Optional[bool] = False
    ):
        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)
        # user_details = await self.get_user_info(request=request,accept_language=accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
 
        raw_query_params: Dict[str, str] = dict(request.query_params)
        validation_request_id = raw_query_params.get('item_id', None)
        if not validation_request_id:
            message = self.get_response_message(
                MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
            raise HTTPException(status_code=404, detail=message)

        query_params = ConverterService.convert_query_params(raw_query_params)
        self.app_debug_print(
            f"Query Parameters (converted): {query_params}", True)
        sort = request.query_params.get("sort", {'created_at': -1})
        self.app_debug_print(f"Query Parameters (SORT): {sort}", True)
        # Fetch data from the collection using CollectionKey
        pipeline = [
            {
                "$match": {
                    "sys_organization_id": ObjectId(user_details['sys_organization_id']),
                    "validator_users": {
                        "$elemMatch": {
                            "sys_user_id": ObjectId(user_details['id'])
                        }
                    },
                    "_id": ObjectId(validation_request_id)
                }
            },
            {
                "$sort": {
                    "created_at": -1
                }
            },
            {
                "$skip": limit * page
            },
            {
                "$limit": limit
            },

        ]
        data = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.OPS_VALIDATION_REQUEST,
            output_data_type=output_data_type,
            accept_language=self.accept_language,
            pipeline=pipeline,
            all_data=False,
            page=page,
            limit=limit
        ) 
        self.app_debug_print(
            f"Pending validation requests data: {len(data)}", True)

        # REFORMAT DATA
        formated_data = []
        current_validation_status = None
        is_user_validation_in_pending_state = False
        for item in data:
            print(
                f"\n\n\n item created_by_id : {item.get('created_by_id',None)} \n\n\n")
            created_by_id = None
            list_of_validators = []
            list_of_formated_validation_decisions = []
            if output_data_type == OutputDataType.DATA_TABLE.value:
                _validators = item['validator_users']['display_value']
                created_by_id = item['created_by_id']['display_value']
                current_validation_status = item['status']['display_value']
                next_validator_id = item['next_validator_id']['display_value']
            elif output_data_type == OutputDataType.DEFAULT.value:
                _validators = item['validator_users']
                created_by_id = item['created_by_id']
                current_validation_status = item['status']
                next_validator_id = item['next_validator_id']
            elif output_data_type == OutputDataType.TREE.value:
                _validators = item['validator_users']
                created_by_id = item['created_by_id']
                current_validation_status = item['status']
                next_validator_id = item['next_validator_id']
            else:
                _validators = []
                created_by_id = None
                current_validation_status = None
                next_validator_id = None

            validator_count = 0
            current_validator = None
            for validator in _validators:
                print(f"\n\n\n validator : {validator} \n\n\n")
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    sys_user_id = validator['sys_user_id']['display_value']
                elif output_data_type == OutputDataType.DEFAULT.value:
                    sys_user_id = validator['sys_user_id']
                elif output_data_type == OutputDataType.TREE.value:
                    sys_user_id = validator['sys_user_id']
                else:
                    sys_user_id = None
                user_info = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.SYS_USER,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    query={"filter___id": sys_user_id},
                    user=user_details,
                )
                if not user_info:
                    continue
                _has_validation_access = False
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    _has_validation_access = validator['has_validation_access']['display_value']
                elif output_data_type == OutputDataType.DEFAULT.value:
                    _has_validation_access = validator['has_validation_access']
                elif output_data_type == OutputDataType.TREE.value:
                    _has_validation_access = validator['has_validation_access']
                else:
                    _has_validation_access = False

                validator_element = {
                    "id":  validator['id'] if 'id' in validator else validator['_id'] if '_id' in validator else None,
                    "first_name": user_info['first_name'],
                    "last_name": user_info['last_name'],
                    "email": user_info['email'],
                    "phone_number": user_info['phone_number'],
                    "username": user_info['username'],
                    "sys_user_id": {
                        "property_name": "is_current_validator",
                        "display_title": "Is current validator",
                        "default_value": sys_user_id,
                        "display_value": sys_user_id,
                        "data_type": {"is_boolean": True},
                        "constraints": {},
                        "extra_metas": {},
                    } if output_data_type == OutputDataType.DATA_TABLE.value else sys_user_id,
                    "has_validation_access": {
                        "property_name": "is_current_validator",
                        "display_title": "Is current validator",
                        "default_value": _has_validation_access,
                        "display_value": _has_validation_access,
                        "data_type": {"is_boolean": True},
                        "constraints": {},
                        "extra_metas": {},
                    } if output_data_type == OutputDataType.DATA_TABLE.value else _has_validation_access,
                    "is_current_validator": {
                        "property_name": "is_current_validator",
                        "display_title": "Is current validator",
                        "default_value": (
                            user_details['id'] == next_validator_id and
                            is_user_validation_in_pending_state
                        ),
                        "display_value": (
                            user_details['id'] == next_validator_id and
                            is_user_validation_in_pending_state
                        ),
                        "data_type": {"is_boolean": True},
                        "constraints": {},
                        "extra_metas": {},
                    },
                    # "is_current_validator":{
                    #     "property_name":"is_current_validator",
                    #     "display_title":"Is current validator",
                    #     "default_value":sys_user_id == next_validator_id,
                    #     "display_value":sys_user_id == next_validator_id,
                    #     "data_type":{"is_boolean":True},
                    #     "constraints":{},
                    #     "extra_metas":{},
                    # } if output_data_type == OutputDataType.DATA_TABLE.value else sys_user_id == next_validator_id,


                }
                if _has_validation_access == True:
                    validator_count += 1
                    if sys_user_id == next_validator_id:
                        current_validator = validator_element
                list_of_validators.append(validator_element)

            # validator_decisions = item.get('validator_decisions',[])
            if output_data_type == OutputDataType.DATA_TABLE.value:
                validator_decisions = item['validator_decisions']['display_value']
            elif output_data_type == OutputDataType.DEFAULT.value:
                validator_decisions = item['validator_decisions']
            elif output_data_type == OutputDataType.TREE.value:
                validator_decisions = item['validator_decisions']
            else:
                validator_decisions = []

            if not validator_decisions:
                validator_decisions = []

            for user in list_of_validators:
                # filter validator_decisions by sys_user_id
                user_validator_decisions = []
                for decision in validator_decisions:
                    self.app_debug_print(
                        f" \n\n\n decision loop >> : {decision['sys_user_id']} \n\n\n", True)
                    if output_data_type == OutputDataType.DATA_TABLE.value:
                        sys_user_id = validator['sys_user_id']['display_value']
                        current_user_id = user['sys_user_id']['display_value']
                    elif output_data_type == OutputDataType.DEFAULT.value:
                        sys_user_id = validator['sys_user_id']
                        current_user_id = user['sys_user_id']
                    elif output_data_type == OutputDataType.TREE.value:
                        sys_user_id = validator['sys_user_id']  # is_array
                        current_user_id = user['sys_user_id']
                    else:
                        sys_user_id = None
                        current_user_id = None
                    self.app_debug_print(
                        f" \n\n\n decision loop >> sys_user_id : {sys_user_id} \n\n\n", True)
                    self.app_debug_print(
                        f" \n\n\n decision loop >> current_user_id : {current_user_id} \n\n\n", True)
                    if sys_user_id == current_user_id:
                        user_validator_decisions.append(decision)

                # user_validator_decisions = [decision for decision in validator_decisions if decision['sys_user_id'] == user['sys_user_id']]

                self.app_debug_print(
                    f" \n\n\n user_validator_decisions : {user_validator_decisions} \n\n\n", True)
                if not user_validator_decisions:

                    is_user_validation_in_pending_state = (
                        user_details['id'] == next_validator_id and
                        (current_validation_status == EMultipleValidationStatus.PENDING.value or
                         current_validation_status == EMultipleValidationStatus.IN_PROGRESS.value)
                    )
                    list_of_formated_validation_decisions.append({
                        "id": {
                            "property_name": "id",
                            "display_title": "id",
                            "default_value": None,
                            "display_value": None,
                            "data_type": {"is_string": True},
                            "constraints": {},
                            "extra_metas": {},
                        },
                        "sys_user_id": {
                            "property_name": "sys_user_id",
                            "display_title": "User id",
                            "default_value": user['sys_user_id'],
                            "display_value": user['sys_user_id'],
                            "data_type": {"is_string": True},
                            "constraints": {},
                            "extra_metas": {},
                        },
                        "status": {
                            "property_name": "status",
                            "display_title": "Status",
                            "default_value": EMultipleValidationStatus.PENDING,
                            "display_value": EMultipleValidationStatus.PENDING,
                            "data_type": {"is_string": True},
                            "constraints": {},
                            "extra_metas": {},
                        },
                        "decision_status": {
                            "property_name": "status",
                            "display_title": "Status",
                            "default_value": EMultipleValidationStatus.PENDING,
                            "display_value": EMultipleValidationStatus.PENDING,
                            "data_type": {"is_string": True},
                            "constraints": {},
                            "extra_metas": {},
                        },
                        "created_at": item['created_at'],
                        "comment": {
                            "property_name": "comment",
                            "display_title": "comment",
                            "default_value": None,
                            "display_value": None,
                            "data_type": {"is_string": True},
                            "constraints": {},
                            "extra_metas": {},
                        },
                        "decided_at": {
                            "property_name": "decided_at",
                            "display_title": "decided_at",
                            "default_value": None,
                            "display_value": None,
                            "data_type": {"is_string": True},
                            "constraints": {},
                            "extra_metas": {},
                        },
                        "device_info": {
                            "property_name": "device_info",
                            "display_title": "device_info",
                            "default_value": None,
                            "display_value": None,
                            "data_type": {"is_string": True},
                            "constraints": {},
                            "extra_metas": {},
                        },
                        "location_info": {
                            "property_name": "location_info",
                            "display_title": "location_info",
                            "default_value": None,
                            "display_value": None,
                            "data_type": {"is_string": True},
                            "constraints": {},
                            "extra_metas": {},
                        },
                        "ip_address": {
                            "property_name": "ip_address",
                            "display_title": "ip_address",
                            "default_value": None,
                            "display_value": None,
                            "data_type": {"is_string": True},
                            "constraints": {},
                            "extra_metas": {},
                        },
                        "user": user
                    })
                else:
                    is_user_validation_in_pending_state = (
                        user_details['id'] == next_validator_id and
                        user_validator_decisions[0]['decision'] == EMultipleValidationStatus.PENDING.value
                    )
                    list_of_formated_validation_decisions.append({
                        "id": user_validator_decisions[0]['id'],
                        "sys_user_id": user_validator_decisions[0]['sys_user_id'],
                        "decision_status": user_validator_decisions[0]['decision'],
                        "status": item['status'],
                        "comment": user_validator_decisions[0]['comment'],
                        "decided_at": user_validator_decisions[0]['decided_at'],
                        "device_info": user_validator_decisions[0]['device_info'],
                        "location_info": user_validator_decisions[0]['location_info'],
                        "ip_address": user_validator_decisions[0]['ip_address'],
                        "created_at": item['created_at'],
                        "user": user
                    })
            # print(f"CAN DELETE { (user_details['id'] == created_by_id and (current_validation_status == EMultipleValidationStatus.PENDING.value))}")
            formated_data.append({
                "id": item['id'],
                "identifier": item['identifier'],
                "created_at": item['created_at'],
                "endpoint_path": item['endpoint_path'],
                "endpoint_method": item['endpoint_method'],
                "status": item['status'],
                "operation_type": item['operation_type'],
                "validator_decisions": item['validator_decisions'],
                "list_of_validators": list_of_validators,
                "list_of_formated_validation_decisions": list_of_formated_validation_decisions,
                "current_validator": current_validator,
                "validator_count": {
                    "property_name": "validator_count",
                    "display_title": "Validator count",
                    "default_value": validator_count,
                    "display_value": validator_count,
                    "data_type": {"is_number": True},
                    "constraints": {},
                    "extra_metas": {},
                },
                "is_current_validator": {
                    "property_name": "is_current_validator",
                    "display_title": "Is current validator",
                    "default_value": (
                        user_details['id'] == next_validator_id and
                        is_user_validation_in_pending_state
                    ),
                    "display_value": (
                        user_details['id'] == next_validator_id and
                        is_user_validation_in_pending_state
                    ),
                    "data_type": {"is_boolean": True},
                    "constraints": {},
                    "extra_metas": {},
                },
                "can_validate": {
                    "property_name": "can_validate",
                    "display_title": "Can validate",
                    "default_value": (
                        user['has_validation_access'] and
                        is_user_validation_in_pending_state and
                        user_details['id'] == next_validator_id
                    ),
                    "display_value": (
                        user['has_validation_access'] and
                        is_user_validation_in_pending_state and
                        user_details['id'] == next_validator_id
                    ),
                    "data_type": {"is_boolean": True},
                    "constraints": {},
                    "extra_metas": {},
                },
                "can_reject": {
                    "property_name": "can_reject",
                    "display_title": "Can reject",
                    "default_value": (
                        user['has_validation_access'] and
                        is_user_validation_in_pending_state and
                        user_details['id'] == next_validator_id
                    ),
                    "display_value": (
                        user['has_validation_access'] and
                        is_user_validation_in_pending_state and
                        user_details['id'] == next_validator_id
                    ),
                    "data_type": {"is_boolean": True},
                    "constraints": {},
                    "extra_metas": {},
                },
                "can_delete": {
                    "property_name": "can_delete",
                    "display_title": "Can delete",
                    "default_value": (
                        user_details['id'] == created_by_id and
                        (current_validation_status ==
                         EMultipleValidationStatus.PENDING.value)
                    ),
                    "display_value": (
                        user_details['id'] == created_by_id and
                        (current_validation_status ==
                         EMultipleValidationStatus.PENDING.value)
                    ),
                    "data_type": {"is_boolean": True},
                    "constraints": {},
                    "extra_metas": {},
                },
            })
        extra_data = {}
        if not all_data:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.OPS_VALIDATION_REQUEST,
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
                "data": formated_data,
                **extra_data
            }
        )

    async def fetch_no_sudo_global_user_validators(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page"),
        endpoint_call: Optional[bool] = False
    ):
        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)
        # user_details = await self.get_user_info(request=request,accept_language=accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)

        pipeline = [
            # Match users in the organization
            {
                "$match": {
                    "sys_organization_id": ObjectId(user_details['sys_organization_id'])
                }
            },
            # Lookup rbac validator records
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_USER_VALIDATOR.model_name}",
                    "localField": "_id",
                    "foreignField": "sys_user_id",
                    "as": "rbac_records"
                }
            },
            # Add rbac analysis fields
            {
                "$limit": limit
            },
            {
                "$skip": limit * page
            },
            {
                "$addFields": {
                    "has_null_action": {
                        "$anyElementTrue": {
                            "$map": {
                                "input": "$rbac_records",
                                "as": "record",
                                "in": {"$eq": ["$$record.rbac_sudo_action_id", None]}
                            }
                        }
                    },
                    "has_non_null_action": {
                        "$anyElementTrue": {
                            "$map": {
                                "input": "$rbac_records",
                                "as": "record",
                                "in": {"$ne": ["$$record.rbac_sudo_action_id", None]}
                            }
                        }
                    },
                    "has_no_rbac_records": {
                        "$eq": [{"$size": "$rbac_records"}, 0]
                    },
                    # Add required fields with defaults
                    "first_name": {"$ifNull": ["$first_name", "$sur_name"]},
                    "last_name": {"$ifNull": ["$last_name", ""]},
                    # Ensure rbac_role_id exists
                    "rbac_role_id": {"$ifNull": ["$rbac_role_id", None]}
                }
            },
            # Filter according to requirements
            {
                "$match": {
                    "$or": [
                        {"has_no_rbac_records": True},
                        {
                            "$and": [
                                {"has_null_action": False},
                                {"has_non_null_action": True}
                            ]
                        }
                    ]
                }
            },
            # Add rbac_status field
            {
                "$addFields": {
                    "rbac_status": {
                        "has_records": {"$not": ["$has_no_rbac_records"]},
                        "has_only_non_null_actions": {
                            "$and": [
                                {"$not": ["$has_null_action"]},
                                {"$not": ["$has_no_rbac_records"]}
                            ]
                        }
                    }
                }
            },
            # Remove temporary fields
            {
                "$project": {
                    "rbac_records": 0,
                    "has_null_action": 0,
                    "has_non_null_action": 0,
                    "has_no_rbac_records": 0
                }
            }
        ]

        all_pipeline = [
            # Match users in the organization
            {
                "$match": {
                    "sys_organization_id": ObjectId(user_details['sys_organization_id'])
                }
            },
            # Lookup rbac validator records
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_USER_VALIDATOR.model_name}",
                    "localField": "_id",
                    "foreignField": "sys_user_id",
                    "as": "rbac_records"
                }
            },
            # Add rbac analysis fields
            {
                "$addFields": {
                    "has_null_action": {
                        "$anyElementTrue": {
                            "$map": {
                                "input": "$rbac_records",
                                "as": "record",
                                "in": {"$eq": ["$$record.rbac_sudo_action_id", None]}
                            }
                        }
                    },
                    "has_non_null_action": {
                        "$anyElementTrue": {
                            "$map": {
                                "input": "$rbac_records",
                                "as": "record",
                                "in": {"$ne": ["$$record.rbac_sudo_action_id", None]}
                            }
                        }
                    },
                    "has_no_rbac_records": {
                        "$eq": [{"$size": "$rbac_records"}, 0]
                    },
                    # Add required fields with defaults
                    "first_name": {"$ifNull": ["$first_name", "$sur_name"]},
                    "last_name": {"$ifNull": ["$last_name", ""]},
                    # Ensure rbac_role_id exists
                    "rbac_role_id": {"$ifNull": ["$rbac_role_id", None]}
                }
            },
            # Filter according to requirements
            {
                "$match": {
                    "$or": [
                        {"has_no_rbac_records": True},
                        {
                            "$and": [
                                {"has_null_action": False},
                                {"has_non_null_action": True}
                            ]
                        }
                    ]
                }
            },
            # Add rbac_status field
            {
                "$addFields": {
                    "rbac_status": {
                        "has_records": {"$not": ["$has_no_rbac_records"]},
                        "has_only_non_null_actions": {
                            "$and": [
                                {"$not": ["$has_null_action"]},
                                {"$not": ["$has_no_rbac_records"]}
                            ]
                        }
                    }
                }
            },
            # Remove temporary fields
            {
                "$project": {
                    "rbac_records": 0,
                    "has_null_action": 0,
                    "has_non_null_action": 0,
                    "has_no_rbac_records": 0
                }
            }
        ]

        infos = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.SYS_USER,
            output_data_type=output_data_type,
            accept_language=self.accept_language,
            pipeline=pipeline,
            all_data=False,
            page=page,
            limit=limit
        )

        self.app_debug_print(f" no sudo users len : {len(infos)}", True)
        extra_data = {
            "limit": limit,
            "max": 0
        }
        if not all_data:
            # get max
            max_data = await self.generic_service.fetch_native_aggregate_count_from_collection(
                collection_key=CollectionKey.SYS_USER,
                accept_language=self.accept_language,
                pipeline=all_pipeline,
            )
            extra_data = {
                "max": max_data,
                "limit": limit
            }
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": infos,
                **extra_data
            }
        )

    async def fetch_no_sudo_per_permission_user_validators(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page"),
        endpoint_call: Optional[bool] = False
    ):
        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)
        # user_details = await self.get_user_info(request=request,accept_language=accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
        # RBAC_SUDO_ACTION
        raw_query_params: Dict[str, str] = dict(request.query_params)
        query_params = ConverterService.convert_query_params(raw_query_params)
        rbac_permission_id = query_params.get('rbac_permission_id', None)
        if not rbac_permission_id:
            message = self.get_response_message(
                MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": message
                }
            )
        action_info = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_SUDO_ACTION.value,
            output_data_type=OutputDataType.DEFAULT.value,
            accept_language=self.accept_language,
            query={
                "filter__rbac_permission_id": rbac_permission_id,
                # "filter__sys_organization_id": user_details['sys_organization_id'],
            },
            user=user_details,
        )
        if not action_info:
            message = self.get_response_message(
                MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": message
                }
            )
        per_permission_pipeline = [
            # Match users in the organization
            {
                "$match": {
                    "sys_organization_id": ObjectId(user_details['sys_organization_id'])
                }
            },
            # Lookup rbac validator records
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_USER_VALIDATOR.model_name}",
                    "localField": "_id",
                    "foreignField": "sys_user_id",
                    "as": "rbac_records"
                }
            },
            # Add rbac analysis fields
            {
                "$addFields": {
                    # Check for records matching the specific action ID (the one we want to exclude)
                    "has_specific_action": {
                        "$anyElementTrue": {
                            "$map": {
                                "input": "$rbac_records",
                                "as": "record",
                                "in": {"$eq": ["$$record.rbac_sudo_action_id", ObjectId(action_info['id'])]}
                            }
                        }
                    },
                    # Add required fields with defaults
                    "first_name": {"$ifNull": ["$first_name", "$sur_name"]},
                    "last_name": {"$ifNull": ["$last_name", ""]},
                    "rbac_role_id": {"$ifNull": ["$rbac_role_id", None]}
                }
            },
            # Filter to EXCLUDE users with the specific action ID
            {
                "$match": {
                    "has_specific_action": False
                }
            },
            # Add rbac_status field with more detailed info
            {
                "$addFields": {
                    "rbac_status": {
                        "has_records": {"$gt": [{"$size": "$rbac_records"}, 0]},
                        "has_specific_action": "$has_specific_action"
                    }
                }
            },
            # Pagination - do this after filtering but before removing fields
            {"$skip": limit * page},
            {"$limit": limit},
            # Remove temporary fields
            {
                "$project": {
                    "rbac_records": 0,
                    "has_specific_action": 0
                }
            }
        ]
        all_pipeline = [
            # Match users in the organization
            {
                "$match": {
                    "sys_organization_id": ObjectId(user_details['sys_organization_id'])
                }
            },
            # Lookup rbac validator records
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_USER_VALIDATOR.model_name}",
                    "localField": "_id",
                    "foreignField": "sys_user_id",
                    "as": "rbac_records"
                }
            },
            # Add rbac analysis fields
            {
                "$addFields": {
                    # Check for records matching the specific action ID (the one we want to exclude)
                    "has_specific_action": {
                        "$anyElementTrue": {
                            "$map": {
                                "input": "$rbac_records",
                                "as": "record",
                                "in": {"$eq": ["$$record.rbac_sudo_action_id", ObjectId(action_info['id'])]}
                            }
                        }
                    },
                    # Add required fields with defaults
                    "first_name": {"$ifNull": ["$first_name", "$sur_name"]},
                    "last_name": {"$ifNull": ["$last_name", ""]},
                    "rbac_role_id": {"$ifNull": ["$rbac_role_id", None]}
                }
            },
            # Filter to EXCLUDE users with the specific action ID
            {
                "$match": {
                    "has_specific_action": False
                }
            },
            # Add rbac_status field with more detailed info
            {
                "$addFields": {
                    "rbac_status": {
                        "has_records": {"$gt": [{"$size": "$rbac_records"}, 0]},
                        "has_specific_action": "$has_specific_action"
                    }
                }
            },
            # Remove temporary fields
            {
                "$project": {
                    "rbac_records": 0,
                    "has_specific_action": 0
                }
            }
        ]
        infos = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.SYS_USER,
            output_data_type=output_data_type,
            accept_language=self.accept_language,
            pipeline=per_permission_pipeline,
            all_data=False,
            page=page,
            limit=limit
        )
        
        self.app_debug_print(f" no sudo users len : {len(infos)}", True)
        extra_data = {
            "limit": limit,
            "max": 0
        }
        if not all_data:
            # get max
            max_data = await self.generic_service.fetch_native_aggregate_count_from_collection(
                collection_key=CollectionKey.SYS_USER,
                accept_language=self.accept_language,
                pipeline=all_pipeline,
            )
            extra_data = {
                "max": max_data,
                "limit": limit
            }
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": infos,
                **extra_data
            }
        )

    async def add_global_user_validators(
        self,
        request: Request,
        body: Dict[str, Any]
    ):
        try:
            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message', None)
            # sudo_can_proceed = sudo_action.get('can_proceed', True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_400_BAD_REQUEST,
            #         content={
            #             "status_code": status.HTTP_400_BAD_REQUEST,
            #             "message": sudo_message,
            #         }
            #     )
            user_details = await self.get_user_info(request, self.accept_language)
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)

            validator_data = GlobalValidatorCreate.model_validate(
                body, context={"language": self.accept_language})

            # user_from_org = await self.generic_service.fetch_one_from_collection(
            #     collection_key=CollectionKey.SYS_USER.value,
            #     output_data_type=OutputDataType.DEFAULT.value,
            #     accept_language=self.accept_language,
            #     query={
            #         "filter___id": validator_data.sys_user_id,
            #         "filter__sys_organization_id": user_details['sys_organization_id'],
            #     }
            # )
            # if not user_from_org:
            #     message = self.get_response_message(
            #         MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_404_NOT_FOUND,
            #         content={
            #             "status_code": status.HTTP_404_NOT_FOUND,
            #             "message": message
            #         }
            #     )

            global_user_data = {
                "sys_organization_id": user_details['sys_organization_id'],
                "sys_user_id": validator_data.sys_user_id,
                "has_validation_access": validator_data.has_validation_access,
                "rbac_sudo_action_id": None
            }

            # self.app_debug_print(
            #     f" \n\n\n global_user_data to save : {global_user_data} \n\n\n", True)
            # # START VALIDATION PROCESS
            # validation_service = SecurityValidationService(
            #     accept_language=self.accept_language)
            # validation_process = await validation_service.validation_process(
            #     request=request,
            #     operation_type=EMultipleValidationType.UPSERT,
            #     sudo_action=sudo_action,
            #     collection_name=CollectionKey.RBAC_USER_VALIDATOR.value,
            #     data=global_user_data,
            #     user_details=user_details,
            #     upsert_query={
            #         "sys_organization_id": user_details['sys_organization_id'],
            #         "sys_user_id": validator_data.sys_user_id,
            #         "rbac_sudo_action_id": None
            #     },
            # )

            # if validation_process['is_sudo_action'] == True:
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_200_OK,
            #         content={
            #             "status_code": status.HTTP_200_OK,
            #             "is_sudo_action": True,
            #             "message": validation_process['message'],
            #             "data": validation_process['data']
            #         }
            #     )
            # elif validation_process['is_sudo_group_action'] == True:
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_200_OK,
            #         content={
            #             "status_code": status.HTTP_200_OK,
            #             "message": validation_process['message'],
            #         }
            #     )
            # else:
            #     # Add data to the collection
            #     result = await self.generic_service.upsert_data_to_collection(
            #         collection_key=CollectionKey.RBAC_USER_VALIDATOR,
            #         filter_data={"rbac_sudo_action_id": None, "sys_user_id": global_user_data[
            #             'sys_user_id'], "sys_organization_id": global_user_data['sys_organization_id']},
            #         update_data=global_user_data
            #     )
            #     message = self.get_response_message(
            #         MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_200_OK,
            #         content={
            #             "status_code": status.HTTP_200_OK,
            #             "message": message,
            #             "item_id": result if isinstance(result, str) else result['id']
            #         }
            #     )
            # Add data to the collection
            result = await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_USER_VALIDATOR,
                filter_data={"rbac_sudo_action_id": None, "sys_user_id": global_user_data[
                    'sys_user_id'], "sys_organization_id": global_user_data['sys_organization_id']},
                update_data=global_user_data,
                user=user_details, request=request,
            )
            message = self.get_response_message(
                MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "item_id": result if isinstance(result, str) else result['id']
                }
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def add_permission_user_validators(
        self,
        request: Request,
        body: Dict[str, Any]
    ):
        try:
            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message', None)
            # sudo_can_proceed = sudo_action.get('can_proceed', True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_400_BAD_REQUEST,
            #         content={
            #             "status_code": status.HTTP_400_BAD_REQUEST,
            #             "message": sudo_message,
            #         }
            #     )
            user_details = await self.get_user_info(request, self.accept_language)
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)

            validator_data = PermissionValidatorCreate.model_validate(
                body, context={"language": self.accept_language})
            # RBAC_SUDO_ACTION
            action_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_SUDO_ACTION.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__rbac_permission_id": validator_data.rbac_permission_id,
                    # "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )
            if not action_info:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status_code": status.HTTP_404_NOT_FOUND,
                        "message": message
                    }
                )
            global_user_data = {
                "sys_organization_id": user_details['sys_organization_id'],
                "sys_user_id": validator_data.sys_user_id,
                "has_validation_access": validator_data.has_validation_access,
                # validator_data.rbac_permission_id
                "rbac_sudo_action_id": action_info['id']
            }

            # self.app_debug_print(
            #     f" \n\n\n global_user_data to save : {global_user_data} \n\n\n", True)
            # START VALIDATION PROCESS
            # validation_service = SecurityValidationService(
            #     accept_language=self.accept_language)
            # validation_process = await validation_service.validation_process(
            #     request=request,
            #     operation_type=EMultipleValidationType.UPSERT,
            #     sudo_action=sudo_action,
            #     collection_name=CollectionKey.RBAC_USER_VALIDATOR.value,
            #     data=global_user_data,
            #     user_details=user_details,
            #     upsert_query={
            #         "sys_organization_id": user_details['sys_organization_id'],
            #         "sys_user_id": validator_data.sys_user_id,
            #         # validator_data.rbac_permission_id
            #         "rbac_sudo_action_id": action_info['id']
            #     },
            # )

            # if validation_process['is_sudo_action'] == True:
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_200_OK,
            #         content={
            #             "status_code": status.HTTP_200_OK,
            #             "is_sudo_action": True,
            #             "message": validation_process['message'],
            #             "data": validation_process['data']
            #         }
            #     )
            # elif validation_process['is_sudo_group_action'] == True:
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_200_OK,
            #         content={
            #             "status_code": status.HTTP_200_OK,
            #             "message": validation_process['message'],
            #         }
            #     )
            # else:
            #     # Add data to the collection
            #     result = await self.generic_service.upsert_data_to_collection(
            #         collection_key=CollectionKey.RBAC_USER_VALIDATOR,
            #         filter_data={"rbac_sudo_action_id": global_user_data["rbac_sudo_action_id"], "sys_user_id": global_user_data[
            #             'sys_user_id'], "sys_organization_id": global_user_data['sys_organization_id']},
            #         update_data=global_user_data
            #     )
            #     message = self.get_response_message(
            #         MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_200_OK,
            #         content={
            #             "status_code": status.HTTP_200_OK,
            #             "message": message,
            #             "item_id": result if isinstance(result, str) else result['id']
            #         }
            #     )
            result = await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_USER_VALIDATOR,
                filter_data={"rbac_sudo_action_id": global_user_data["rbac_sudo_action_id"], "sys_user_id": global_user_data[
                    'sys_user_id'], "sys_organization_id": global_user_data['sys_organization_id']},
                update_data=global_user_data,
                user=user_details, request=request,
            )
            message = self.get_response_message(
                MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "item_id": result if isinstance(result, str) else result['id']
                }
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def update_currency_exchanges(
        self,
        request: Request,
        body: Dict[str, Any]
    ):
        try:
            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message', None)
            # sudo_can_proceed = sudo_action.get('can_proceed', True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_400_BAD_REQUEST,
            #         content={
            #             "status_code": status.HTTP_400_BAD_REQUEST,
            #             "message": sudo_message,
            #         }
            #     )

            self.app_debug_print(f" \n\n\n body : {body} \n\n\n", True)
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request, self.accept_language)
            api_Consumer = await self.get_api_consumer(request, self.accept_language)
            user_profil = await self.get_user_profil(request, self.accept_language)

            item_id = request.query_params.get('item_id', None)
            if not item_id:
                message = self.get_response_message(
                    MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            self.app_debug_print(f" \n\n\n item_id : {item_id} \n\n\n", True)
            # GET EXCHANGE FROM ID
            exchange = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_CURRENCY_EXCHANGE,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={
                    "filter___id": item_id,
                    "filter__sys_organization_id": user_details['sys_organization_id']
                },
                user=user_details,
            )
            self.app_debug_print(f" \n\n\n exchange : {exchange} \n\n\n", True)
            if not exchange:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            data = {
                "base_currency_id": exchange['base_currency_id'],
                "targeted_currency_id": exchange['targeted_currency_id'],
                "value": float(str(body['value'])),
                "sys_organization_id": user_details['sys_organization_id'],
                "created_by_id": user_details['id']
            }

            self.app_debug_print(f" \n\n\n data : {data} \n\n\n", True)

            # START VALIDATION PROCESS
            # validation_service = SecurityValidationService(
            #     accept_language=self.accept_language)
            # validation_process = await validation_service.validation_process(
            #     request=request,
            #     operation_type=EMultipleValidationType.CREATE,
            #     sudo_action=sudo_action,
            #     collection_name=CollectionKey.CFG_CURRENCY_EXCHANGE.value,
            #     data=data,
            #     user_details=user_details
            # )
            # self.app_debug_print(
            #     f" \n\n\n validation_process : {validation_process} \n\n\n", True)

            # SET ALL EXISTING EXHANGE IS ACTIVATED TO FALSE
            filter_data = {
                "sys_organization_id": user_details['sys_organization_id'],
                "base_currency_id": exchange['base_currency_id'],
                "targeted_currency_id": exchange['targeted_currency_id'],
            }
            self.app_debug_print(
                f" \n\n\n filter_data : {filter_data} \n\n\n", True)
            update_data = {"is_activated": False}
            self.app_debug_print(
                f" \n\n\n update_data : {update_data} \n\n\n", True)
            await self.generic_service.update_many_in_collection(
                collection_key=CollectionKey.CFG_CURRENCY_EXCHANGE,
                data=update_data,
                filter_data=filter_data
            )

            # if validation_process['is_sudo_action'] == True:
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_200_OK,
            #         content={
            #             "status_code": status.HTTP_200_OK,
            #             "is_sudo_action": True,
            #             "message": validation_process['message'],
            #             "data": validation_process['data']
            #         }
            #     )
            # elif validation_process['is_sudo_group_action'] == True:
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_200_OK,
            #         content={
            #             "status_code": status.HTTP_200_OK,
            #             "message": validation_process['message'],
            #         }
            #     )
            # else:
                # Add data to the collection
                # item_id = await self.generic_service.add_data_to_collection(CollectionKey.CFG_CURRENCY_EXCHANGE, data)
                # message = self.get_response_message(
                #     MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
                # return CustomJSONResponse(
                #     status_code=status.HTTP_200_OK,
                #     content={
                #         "status_code": status.HTTP_200_OK,
                #         "message": message,
                #         "item_id": item_id
                #     }
                # ),
            item_id = await self.generic_service.add_data_to_collection(CollectionKey.CFG_CURRENCY_EXCHANGE, data, user=user_details, request=request)
            message = self.get_response_message(
                MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "item_id": item_id
                }
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f" \n\n Exception >: {e}\n\n", True)
            raise HTTPException(status_code=500, detail=str(e))

    async def validate_or_reject_pending_validation_request(
        self,
        request: Request,
        body: Dict[str, Any]
    ):
        try:
            from app.modules.security.models.ops_validation_request.ops_validation_request_model import OpsValidationRequestModel
            from app.modules.security.models.ops_validation_request_user.ops_validation_request_user_model import OpsValidationRequestUserModel

            user_details = await self.get_user_info(request, self.accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
            device_info = await self.get_optional_device_info(request=request, accept_language=self.accept_language)
            location_info = await self.get_location_from_ip_secure(request=request, accept_language=self.accept_language)
            ip_address = await self.get_optional_api_address(request=request, accept_language=self.accept_language)
            from app.modules.core.services.messaging.messaging_service import MessengingService
            messaging_service = MessengingService(
                accept_language=self.accept_language)

            # Check if collection is exposed
            metadata = COLLECTION_MODEL_MAPPING.get(
                CollectionKey.OPS_VALIDATION_REQUEST.value)
            if not metadata:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME",
                                                    self.accept_language, collection_name=CollectionKey.OPS_VALIDATION_REQUEST.value)
                raise HTTPException(status_code=400, detail=message)

            validator_data = PendingValidationRequestCreate.model_validate(
                body, context={"language": self.accept_language})

            # Fetch the OpsValidationRequest document
            vr_instance = await OpsValidationRequestModel.get(ObjectId(validator_data.ops_validation_request_id))
            if not vr_instance:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status_code": status.HTTP_404_NOT_FOUND,
                        "message": message
                    }
                )

            current_status = vr_instance.status.value if hasattr(vr_instance.status, 'value') else vr_instance.status
            if current_status == EMultipleValidationStatus.APPROVED.value:
                message = self.get_response_message(
                    MessageCategory.EXCEPTIONS, "VALIDATION_REQUEST_ALREADY_APPROVED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": message
                    }
                )
            if current_status == EMultipleValidationStatus.REJECTED.value:
                message = self.get_response_message(
                    MessageCategory.EXCEPTIONS, "VALIDATION_REQUEST_ALREADY_REJECTED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": message
                    }
                )

            # Find the current user's OpsValidationRequestUserModel row
            current_user_oid = ObjectId(user_details['id'])
            user_row = await OpsValidationRequestUserModel.find_one(
                OpsValidationRequestUserModel.ops_validation_request_id == vr_instance.id,
                OpsValidationRequestUserModel.sys_user_id == current_user_oid,
            )

            if not user_row:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status_code": status.HTTP_404_NOT_FOUND,
                        "message": message
                    }
                )

            # Check if user already decided
            existing_decision = user_row.decision.value if user_row.decision and hasattr(user_row.decision, 'value') else user_row.decision
            if existing_decision == EMultipleValidationStatus.APPROVED.value:
                message = self.get_response_message(
                    MessageCategory.COMMON, "USER_ALREADY_APPROVED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": message
                    }
                )
            elif existing_decision == EMultipleValidationStatus.REJECTED.value:
                message = self.get_response_message(
                    MessageCategory.COMMON, "USER_ALREADY_REJECTED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": message
                    }
                )

            # Update the user row with the decision
            user_row.decision = validator_data.decision
            user_row.status = validator_data.decision
            user_row.comment = validator_data.comment
            user_row.device_info = device_info
            user_row.location_info = location_info
            user_row.ip_address = ip_address
            user_row.decided_at = datetime.now(timezone.utc)
            await user_row.save()

            # Send notification to current validator (confirmation of their action)
            if validator_data.decision.value == EMultipleValidationStatus.REJECTED.value:
                current_validator_validation_mail_title_translated = self.get_response_message(
                    MessageCategory.MULTI_VALIDATION,
                    "CURRENT_VALIDATOR_REJECTED_REQUEST_TITLE",
                    self.accept_language
                )
                current_validator_notification_message_translated = self.get_response_message(
                    MessageCategory.MULTI_VALIDATION,
                    "CURRENT_VALIDATOR_REJECTED_REQUEST_BODY",
                    self.accept_language,
                    name=f"{user_details['first_name']} {user_details['last_name']}",
                    reference=str(vr_instance.identifier).upper(),
                    date=vr_instance.created_at.strftime("%d/%m/%Y") if vr_instance.created_at else "",
                    time=vr_instance.created_at.strftime("%H:%M:%S") if vr_instance.created_at else ""
                )
            else:
                current_validator_validation_mail_title_translated = self.get_response_message(
                    MessageCategory.MULTI_VALIDATION,
                    "CURRENT_VALIDATOR_APPROVED_REQUEST_TITLE",
                    self.accept_language
                )
                current_validator_notification_message_translated = self.get_response_message(
                    MessageCategory.MULTI_VALIDATION,
                    "CURRENT_VALIDATOR_APPROVED_REQUEST_BODY",
                    self.accept_language,
                    name=f"{user_details['first_name']} {user_details['last_name']}",
                    reference=str(vr_instance.identifier).upper(),
                    date=vr_instance.created_at.strftime("%d/%m/%Y") if vr_instance.created_at else "",
                    time=vr_instance.created_at.strftime("%H:%M:%S") if vr_instance.created_at else ""
                )

            await messaging_service.save_local_notification(
                title=current_validator_validation_mail_title_translated,
                notification=current_validator_notification_message_translated,
                targeted_id=user_details['id']
            )
            await messaging_service.send_email_to_users(
                emails=[user_details['email']],
                subject=current_validator_validation_mail_title_translated,
                body=current_validator_notification_message_translated
            )

            # Now recompute the global status by checking all validator user rows
            all_user_rows = await OpsValidationRequestUserModel.find(
                OpsValidationRequestUserModel.ops_validation_request_id == vr_instance.id,
            ).sort("+order_by").to_list()

            # Filter to only validators (not observers)
            validator_rows = [r for r in all_user_rows if r.has_validation_access == True]

            approved_count = 0
            rejected_count = 0
            next_validator_user_info = None

            for row in validator_rows:
                row_decision = row.decision.value if row.decision and hasattr(row.decision, 'value') else row.decision
                if row_decision == EMultipleValidationStatus.APPROVED.value:
                    approved_count += 1
                elif row_decision == EMultipleValidationStatus.REJECTED.value:
                    rejected_count += 1
                elif next_validator_user_info is None:
                    # This validator hasn't decided yet -> they are the next validator
                    from app.modules.core.models.sys_user.sys_user_model import SysUserModel
                    try:
                        next_user_instance = await SysUserModel.get(row.sys_user_id)
                        if next_user_instance:
                            next_validator_user_info = await next_user_instance.get_formated_data(self.accept_language)
                    except Exception:
                        pass

            # ALL validators approved -> globally approve
            if approved_count == len(validator_rows):
                vr_instance.status = EMultipleValidationStatus.APPROVED
                vr_instance.validation_is_completed = False
                vr_instance.next_validator_id = None
                await vr_instance.save()

                # Notify all other validators about global approval
                notifications = []
                validator_emails = []
                for row in all_user_rows:
                    if str(row.sys_user_id) == user_details['id']:
                        continue
                    from app.modules.core.models.sys_user.sys_user_model import SysUserModel
                    try:
                        u_instance = await SysUserModel.get(row.sys_user_id)
                        if not u_instance:
                            continue
                        u_info = await u_instance.get_formated_data(self.accept_language)
                    except Exception:
                        continue
                    notifications.append({
                        "title": self.get_response_message(MessageCategory.MULTI_VALIDATION, "NOTIFICATION_VALIDATION_REQUEST_GLOBAL_APPROVED_TITLE", self.accept_language),
                        "notification": self.get_response_message(
                            MessageCategory.MULTI_VALIDATION, "NOTIFICATION_VALIDATION_REQUEST_GLOBAL_APPROVED_BODY", self.accept_language,
                            name=f"{u_info.get('first_name','')} {u_info.get('last_name','')}",
                            reference=str(vr_instance.identifier).upper(),
                            date=vr_instance.created_at.strftime("%d/%m/%Y") if vr_instance.created_at else "",
                            time=vr_instance.created_at.strftime("%H:%M:%S") if vr_instance.created_at else ""
                        ),
                        "targeted_id": str(row.sys_user_id)
                    })
                    if u_info.get('email'):
                        validator_emails.append(u_info['email'])

                await messaging_service.save_multiple_local_notifications(notifications)
                if validator_emails:
                    await messaging_service.send_email_to_users(
                        emails=validator_emails,
                        subject=self.get_response_message(MessageCategory.MULTI_VALIDATION, "NOTIFICATION_VALIDATION_REQUEST_GLOBAL_APPROVED_TITLE", self.accept_language),
                        body=self.get_response_message(
                            MessageCategory.MULTI_VALIDATION, "NOTIFICATION_VALIDATION_REQUEST_GLOBAL_APPROVED_BODY", self.accept_language,
                            name=f"{user_details['first_name']} {user_details['last_name']}",
                            reference=str(vr_instance.identifier).upper(),
                            date=vr_instance.created_at.strftime("%d/%m/%Y") if vr_instance.created_at else "",
                            time=vr_instance.created_at.strftime("%H:%M:%S") if vr_instance.created_at else ""
                        )
                    )

                message = self.get_response_message(
                    MessageCategory.SUCCESS, "VALIDATION_REQUEST_PROCESS_COMPLETED_SUCCESSFULLY", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )

            # ANY rejection -> globally reject
            elif rejected_count > 0:
                vr_instance.status = EMultipleValidationStatus.REJECTED
                vr_instance.validation_is_completed = False
                vr_instance.next_validator_id = None
                await vr_instance.save()

                # Notify all other validators about global rejection
                notifications = []
                validator_emails = []
                for row in all_user_rows:
                    if str(row.sys_user_id) == user_details['id']:
                        continue
                    from app.modules.core.models.sys_user.sys_user_model import SysUserModel
                    try:
                        u_instance = await SysUserModel.get(row.sys_user_id)
                        if not u_instance:
                            continue
                        u_info = await u_instance.get_formated_data(self.accept_language)
                    except Exception:
                        continue
                    notifications.append({
                        "title": self.get_response_message(MessageCategory.MULTI_VALIDATION, "NOTIFICATION_VALIDATION_REQUEST_GLOBAL_REJECTION_TITLE", self.accept_language),
                        "notification": self.get_response_message(
                            MessageCategory.MULTI_VALIDATION, "NOTIFICATION_VALIDATION_REQUEST_GLOBAL_REJECTION_BODY", self.accept_language,
                            name=f"{u_info.get('first_name','')} {u_info.get('last_name','')}",
                            reference=str(vr_instance.identifier).upper(),
                            validator_name=f"{user_details['first_name']} {user_details['last_name']}",
                            reason=validator_data.comment or "",
                            date=vr_instance.created_at.strftime("%d/%m/%Y") if vr_instance.created_at else "",
                            time=vr_instance.created_at.strftime("%H:%M:%S") if vr_instance.created_at else ""
                        ),
                        "targeted_id": str(row.sys_user_id)
                    })
                    if u_info.get('email'):
                        validator_emails.append(u_info['email'])

                await messaging_service.save_multiple_local_notifications(notifications)
                if validator_emails:
                    await messaging_service.send_email_to_users(
                        emails=validator_emails,
                        subject=self.get_response_message(MessageCategory.MULTI_VALIDATION, "EMAIL_VALIDATION_REQUEST_GLOBAL_REJECTION_SUBJECT", self.accept_language),
                        body=self.get_response_message(
                            MessageCategory.MULTI_VALIDATION, "EMAIL_VALIDATION_REQUEST_GLOBAL_REJECTION_BODY", self.accept_language,
                            name=f"{user_details['first_name']} {user_details['last_name']}",
                            reference=str(vr_instance.identifier).upper(),
                            validator_name=f"{user_details['first_name']} {user_details['last_name']}",
                            reason=validator_data.comment or "",
                            date=vr_instance.created_at.strftime("%d/%m/%Y") if vr_instance.created_at else "",
                            time=vr_instance.created_at.strftime("%H:%M:%S") if vr_instance.created_at else ""
                        )
                    )

                message = self.get_response_message(
                    MessageCategory.SUCCESS, "VALIDATION_REQUEST_PROCESS_COMPLETED_BUT_REJECTED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )

            # Not complete yet — update next_validator_id and update status to IN_PROGRESS, notify next validator
            if next_validator_user_info:
                vr_instance.next_validator_id = ObjectId(next_validator_user_info.get('id'))
                vr_instance.status = EMultipleValidationStatus.IN_PROGRESS
                await vr_instance.save()

                next_validator_validation_mail_title_translated = self.get_response_message(
                    MessageCategory.MULTI_VALIDATION,
                    "PROGRESSIVE_MULTI_VALIDATION_TITLE",
                    self.accept_language
                )
                next_validator_notification_message_translated = self.get_response_message(
                    MessageCategory.MULTI_VALIDATION,
                    "NOTIFICATION_USER_VALIDATION_REQUEST_ADDED_BODY",
                    self.accept_language,
                    name=f"{user_details['first_name']} {user_details['last_name']}",
                    reference=str(vr_instance.identifier).upper(),
                    date=vr_instance.created_at.strftime("%d/%m/%Y") if vr_instance.created_at else "",
                    time=vr_instance.created_at.strftime("%H:%M:%S") if vr_instance.created_at else ""
                )
                await messaging_service.save_local_notification(
                    title=next_validator_validation_mail_title_translated,
                    notification=next_validator_notification_message_translated,
                    targeted_id=next_validator_user_info['id']
                )
                await messaging_service.send_email_to_users(
                    emails=[next_validator_user_info['email']],
                    subject=next_validator_validation_mail_title_translated,
                    body=next_validator_notification_message_translated
                )

            message = self.get_response_message(
                MessageCategory.SUCCESS, "USER_VALIDATION_REQUEST_APPROVED", self.accept_language)
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
            self.app_debug_print(
                f" \n\n\n error in the validation process : {e} \n\n\n", True)
            raise HTTPException(status_code=500, detail=str(e))

    async def validate_all_pending_validation_requests(
        self,
        request: Request,
        body: Dict[str, Any],
    ):
        """
        Bulk-approve all pending validation requests where the current user is
        the next validator and has validation access.

        Body:
            decision  (str)  – must be APPROVED (bulk reject is disallowed for
                               safety; rejections should always be deliberate).
            comment   (str)  – optional comment applied to every decision.

        Returns the count of successfully validated requests and any IDs that
        could not be processed.
        """
        try:
            from datetime import datetime, timezone
            from bson import ObjectId
            from app.modules.security.models.ops_validation_request.ops_validation_request_model import OpsValidationRequestModel
            from app.modules.security.models.ops_validation_request_user.ops_validation_request_user_model import OpsValidationRequestUserModel
            from app.modules.core.enums.type_enum import EMultipleValidationStatus

            user_details = await self.get_user_info(request, self.accept_language)
            device_info = await self.get_optional_device_info(request=request, accept_language=self.accept_language)
            location_info = await self.get_location_from_ip_secure(request=request, accept_language=self.accept_language)
            ip_address = await self.get_optional_api_address(request=request, accept_language=self.accept_language)

            # Only APPROVED is accepted for bulk operations
            decision_raw = str(body.get("decision", "APPROVED")).strip().upper()
            if decision_raw != EMultipleValidationStatus.APPROVED.value:
                message = self.get_response_message(
                    MessageCategory.EXCEPTIONS, "BULK_VALIDATE_ONLY_APPROVE_ALLOWED", self.accept_language
                )
                raise HTTPException(status_code=400, detail=message)

            comment = str(body.get("comment", "")).strip() or None
            current_user_oid = ObjectId(user_details["id"])
            org_oid = ObjectId(user_details["sys_organization_id"])

            # Fetch all pending/in-progress requests where this user is the next validator
            eligible_requests = await OpsValidationRequestModel.find(
                OpsValidationRequestModel.sys_organization_id == org_oid,
                OpsValidationRequestModel.next_validator_id == current_user_oid,
                {"status": {"$in": [
                    EMultipleValidationStatus.PENDING.value,
                    EMultipleValidationStatus.IN_PROGRESS.value,
                ]}},
            ).to_list()

            validated_ids: list = []
            skipped_ids: list = []

            for vr in eligible_requests:
                try:
                    # Find the user's validator row
                    user_row = await OpsValidationRequestUserModel.find_one(
                        OpsValidationRequestUserModel.ops_validation_request_id == vr.id,
                        OpsValidationRequestUserModel.sys_user_id == current_user_oid,
                    )
                    if not user_row or not user_row.has_validation_access:
                        skipped_ids.append(str(vr.id))
                        continue

                    existing_decision = str(user_row.decision or "").upper() if user_row.decision else None
                    if existing_decision in (
                        EMultipleValidationStatus.APPROVED.value,
                        EMultipleValidationStatus.REJECTED.value,
                    ):
                        skipped_ids.append(str(vr.id))
                        continue

                    # Record the decision
                    user_row.decision = EMultipleValidationStatus.APPROVED.value
                    user_row.status = EMultipleValidationStatus.APPROVED.value
                    user_row.comment = comment
                    user_row.device_info = device_info
                    user_row.location_info = location_info
                    user_row.ip_address = ip_address
                    user_row.decided_at = datetime.now(timezone.utc)
                    await user_row.save()

                    # Recompute global status
                    all_rows = await OpsValidationRequestUserModel.find(
                        OpsValidationRequestUserModel.ops_validation_request_id == vr.id
                    ).sort("+order_by").to_list()

                    validator_rows = [r for r in all_rows if r.has_validation_access]
                    approved_count = sum(
                        1 for r in validator_rows
                        if str(r.decision or "").upper() == EMultipleValidationStatus.APPROVED.value
                    )
                    rejected_count = sum(
                        1 for r in validator_rows
                        if str(r.decision or "").upper() == EMultipleValidationStatus.REJECTED.value
                    )

                    if rejected_count > 0:
                        vr.status = EMultipleValidationStatus.REJECTED.value
                        vr.next_validator_id = None
                        await vr.save()
                    elif approved_count == len(validator_rows):
                        vr.status = EMultipleValidationStatus.APPROVED.value
                        vr.next_validator_id = None
                        await vr.save()
                    else:
                        # Advance to next undecided validator
                        next_validator = next(
                            (
                                r for r in validator_rows
                                if str(r.decision or "").upper()
                                not in (
                                    EMultipleValidationStatus.APPROVED.value,
                                    EMultipleValidationStatus.REJECTED.value,
                                )
                            ),
                            None,
                        )
                        vr.status = EMultipleValidationStatus.IN_PROGRESS.value
                        vr.next_validator_id = next_validator.sys_user_id if next_validator else None
                        await vr.save()

                    validated_ids.append(str(vr.id))
                except Exception as inner_err:
                    self.app_debug_print(
                        f"bulk_validate: failed for request {vr.id}: {inner_err}", True
                    )
                    skipped_ids.append(str(vr.id))

            message = self.get_response_message(
                MessageCategory.SUCCESS, "BULK_VALIDATION_COMPLETED", self.accept_language
            )
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "data": {
                        "validated_count": len(validated_ids),
                        "skipped_count": len(skipped_ids),
                        "validated_ids": validated_ids,
                        "skipped_ids": skipped_ids,
                    },
                },
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"validate_all_pending error: {e}", True)
            raise HTTPException(status_code=500, detail=str(e))

    async def remove_global_user_validators(
        self,
        request: Request,
    ):
        try:

            user_details = await self.get_user_info(request, self.accept_language)
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = ConverterService.convert_query_params(
                raw_query_params)
            sys_user_id = query_params.get('sys_user_id', None)
            global_user_data = {
                "sys_organization_id": user_details['sys_organization_id'],
                "sys_user_id": sys_user_id,
                "rbac_sudo_action_id": None
            }
            global_validation_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_USER_VALIDATOR.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sys_organization_id": global_user_data['sys_organization_id'],
                    "filter__sys_user_id": global_user_data['sys_user_id'],
                    "filter__rbac_sudo_action_id": global_user_data['rbac_sudo_action_id'],
                },
                user=user_details,
            )
            if not global_validation_info:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message', None)
            # sudo_can_proceed = sudo_action.get('can_proceed', True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_400_BAD_REQUEST,
            #         content={
            #             "status_code": status.HTTP_400_BAD_REQUEST,
            #             "message": sudo_message,
            #         }
            #     )

            self.app_debug_print(
                f" \n\n\n global_user_data to save : {global_user_data} \n\n\n", True)
            # START VALIDATION PROCESS
            # validation_service = SecurityValidationService(
            #     accept_language=self.accept_language)
            # validation_process = await validation_service.validation_process(
            #     request=request,
            #     operation_type=EMultipleValidationType.HARD_DELETE,
            #     sudo_action=sudo_action,
            #     collection_name=CollectionKey.RBAC_USER_VALIDATOR.value,
            #     data=global_user_data,
            #     user_details=user_details,
            #     upsert_query=global_user_data,
            # )

            # if validation_process['is_sudo_action'] == True:
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_200_OK,
            #         content={
            #             "status_code": status.HTTP_200_OK,
            #             "is_sudo_action": True,
            #             "message": validation_process['message'],
            #             "data": validation_process['data']
            #         }
            #     )
            # elif validation_process['is_sudo_group_action'] == True:
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_200_OK,
            #         content={
            #             "status_code": status.HTTP_200_OK,
            #             "message": validation_process['message'],
            #         }
            #     )
            # else:
            #     # Add data to the collection
            #     result = await self.generic_service.hard_delete_data_from_collection(
            #         collection_key=CollectionKey.RBAC_USER_VALIDATOR,
            #         accept_language=self.accept_language,
            #         item_id=global_validation_info['id']
            #     )
            #     message = self.get_response_message(
            #         MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_200_OK,
            #         content={
            #             "status_code": status.HTTP_200_OK,
            #             "message": message,
            #         }
            #     )
            result = await self.generic_service.hard_delete_data_from_collection(
                collection_key=CollectionKey.RBAC_USER_VALIDATOR,
                accept_language=self.accept_language,
                item_id=global_validation_info['id']
            )
            message = self.get_response_message(
                MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
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

    async def fetch_org_role_permissions(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
    ):
        try:

            user_details = await self.get_user_info(request, self.accept_language)
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = ConverterService.convert_query_params(
                raw_query_params)
            rbac_role_id = query_params.get('rbac_role_id', None)
            if not rbac_role_id:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            # CHECK IF THE ROLE BELONGS TO THE ORGANIZATION
            role_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id": rbac_role_id,
                    # "filter__sys_organization_id":user_details['sys_organization_id'],
                },
                user=user_details,
            )
            if not role_info:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            rbac_profile_id = role_info.get('rbac_profile_id', user_profil['id'])

            # PIPELINE TO RBAC_RESTRICTED_PROFIL JOIN PERMISSION WHERE TARGETED_ID IS JOINED TO RBAC_PERMISSION
            role_permissions_pipeline = [
                {
                    '$match': {
                        'rbac_profile_id': ObjectId(rbac_profile_id)
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
                        'from': 'rbac_title',
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
                        "unwind__rbac_permission.is_accessible_to_all_profil": False,
                    }
                },
            ]
            role_permissions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL.value,
                output_data_type=OutputDataType.DATA_TABLE.value,
                accept_language=self.accept_language,
                page=0,
                limit=100000,
                pipeline=role_permissions_pipeline,
            )
            print(f"\n\n\n role_permissions LEN: {len(role_permissions)}")
            # Process your data
            hierarchy = await self.rbac_role_service.build_role_joined_to_permission_rbac_hierarchy(role_permissions, output_data_type, rbac_role_id)

            # Count total permissions recursively in the tree
            def _count_permissions(nodes):
                total = 0
                for node in nodes:
                    total += len(node.get('permissions', []))
                    total += _count_permissions(node.get('children', []))
                return total

            total_permissions = _count_permissions(hierarchy)
            print(f"\n\n\n hierarchy root_nodes: {len(hierarchy)} | total_permissions_in_tree: {total_permissions}")

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": hierarchy,
                    "max": total_permissions,
                }
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


    async def _update_org_role_permissions_background(
        self,
        validator_data: RolePermissionCreate,
        user_details: Dict[str, Any],
        api_Consumer: Dict[str, Any],
        user_profil: Dict[str, Any]
    ):
        try:
            # PIPELINE TO RBAC PERMISSION ROLE WHERE RBAC_PERMISSION IS NOT ACCESSIBLE TO ALL PROFIL AND ROLE IS CURRENT ROLE
            role_permissions_pipeline = [
                {
                    '$match': {
                        'rbac_role_id': ObjectId(validator_data.rbac_role_id)
                    }
                }, {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                        'localField': 'rbac_permission_id',
                        'foreignField': '_id',
                        'as': 'unwind__rbac_permission'
                    }
                }, {
                    '$unwind': {
                        'path': '$unwind__rbac_permission',
                        'preserveNullAndEmptyArrays': False
                    }
                }, {
                    '$match': {
                        'unwind__rbac_permission.is_accessible_to_all_profil': False
                    }
                }
            ]
            role_permissions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION_ROLE.value,
                output_data_type=OutputDataType.DATA_TABLE.value,
                accept_language=self.accept_language,
                pipeline=role_permissions_pipeline,
            )
            for permission_role in role_permissions:
                query = {
                    "filter__rbac_role_id": validator_data.rbac_role_id,
                    "filter__rbac_permission_id": permission_role['rbac_permission']['id']['display_value'],
                }
                # get on permission role
                single_permission_role = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=self.accept_language,
                    query=query,
                    user=user_details,
                )
                if single_permission_role is not None:
                    await self.generic_service.hard_delete_data_from_collection(
                        collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                        accept_language=self.accept_language,
                        item_id=single_permission_role['id']
                    )

            # ADD NEW RBAC PERMISSION ROLES
            for permission_id in validator_data.rbac_permissions:
                new_perm_tar_role_doc = {
                    "rbac_role_id": validator_data.rbac_role_id,
                    "rbac_permission_id": permission_id,
                }
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                    filter_data={
                        "rbac_role_id": new_perm_tar_role_doc['rbac_role_id'],
                        'rbac_permission_id': new_perm_tar_role_doc['rbac_permission_id']
                    },
                    user=user_details, request=request,
                    update_data=new_perm_tar_role_doc)

            # Invalidate the application cache (L1 Redis + L2 user_app_store)
            # for every user assigned to this role so their next
            # /data/get-applications call rebuilds against the fresh
            # permission set. The guard is always inactive on this code
            # path (frontend HTTP request, not seed) so the calls fire.
            try:
                from app.modules.core.services.user_app_store.user_app_store_service import (
                    UserAppStoreService,
                )
                from app.modules.core.models.sys_user.sys_user_model import (
                    SysUserModel,
                )

                # L2: bulk-mark cache rows stale for users in this role.
                invalidated = await UserAppStoreService.mark_role_users_stale(
                    validator_data.rbac_role_id
                )

                # L1: sweep Redis keys for the same users so they don't
                # see the stale 30-min-TTL cache before L2 takes over.
                role_oid = ObjectId(str(validator_data.rbac_role_id))
                user_ids = await SysUserModel.find(
                    {"rbac_role_id": role_oid}, fetch_links=False,
                ).distinct("_id")
                l1_deleted = await self._invalidate_l1_for_user_ids(user_ids)

                self.app_debug_print(
                    f"[update_org_role_permissions] role={validator_data.rbac_role_id} "
                    f"users={len(user_ids)} L2_marked={invalidated} L1_deleted={l1_deleted}",
                    True,
                )
            except Exception as cache_err:
                self.app_debug_print(
                    f"[update_org_role_permissions] cache invalidation failed (non-fatal): {cache_err}",
                    True,
                )
            return True
        except Exception as e:
            self.app_debug_print(f"Error in _update_org_role_permissions_background: {str(e)}",True)
            return False
    async def update_org_role_permissions(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        body: Dict[str, Any]
    ):
        try:
            self.app_debug_print(
                f" \n\n\n update_org_role_permissions : {body} \n\n\n", False) 
            user_details = await self.get_user_info(request, self.accept_language)
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)

            self.app_debug_print(f" \n\n\n body : {body} \n\n\n", False)
            validator_data = RolePermissionCreate.model_validate(
                body, context={"language": self.accept_language})
            self.app_debug_print(
                f" \n\n\n validator_data : {validator_data} \n\n\n", False)

            role_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id": validator_data.rbac_role_id,
                },
                user=user_details,
            )
            if not role_info:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)


            # COMPLETE PROCESS IN BACKGROUND
            asyncio.create_task(
                self._update_org_role_permissions_background(
                    validator_data=validator_data,
                    user_details=user_details,
                    api_Consumer=api_Consumer,
                    user_profil=user_profil
                )
            )

            message = self.get_response_message(
                MessageCategory.SUCCESS, "DATA_UPDATE_CONTINUED_IN_BACKGROUND", self.accept_language)
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
            self.app_debug_print(f" \n\n Exception: {e}\n\n", True)
            raise HTTPException(status_code=500, detail=str(e))

    async def remove_permission_user_validators(
        self,
        request: Request,
    ):
        try:

            user_details = await self.get_user_info(request, self.accept_language)
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = ConverterService.convert_query_params(
                raw_query_params)
            sys_user_id = query_params.get('sys_user_id', None)
            rbac_sudo_action_id = query_params.get('rbac_sudo_action_id', None)
            global_user_data = {
                "sys_organization_id": user_details['sys_organization_id'],
                "sys_user_id": sys_user_id,
                "rbac_sudo_action_id": rbac_sudo_action_id
            }
            global_validation_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_USER_VALIDATOR.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sys_organization_id": global_user_data['sys_organization_id'],
                    "filter__sys_user_id": global_user_data['sys_user_id'],
                    "filter__rbac_sudo_action_id": global_user_data['rbac_sudo_action_id'],
                },
                user=user_details,
            )
            if not global_validation_info:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
 
            self.app_debug_print(
                f" \n\n\n global_user_data to save : {global_user_data} \n\n\n", True) 
            result = await self.generic_service.hard_delete_data_from_collection(
                collection_key=CollectionKey.RBAC_USER_VALIDATOR,
                accept_language=self.accept_language,
                item_id=global_validation_info['id']
            )
            message = self.get_response_message(
                MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
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

    async def fetch_validator_users_per_permission(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page")
    ):
        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)
        # user_details = await self.get_user_info(request=request,accept_language=accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
        raw_query_params: Dict[str, str] = dict(request.query_params)
        query_params = ConverterService.convert_query_params(raw_query_params)
        rbac_permission_id = query_params.get('rbac_permission_id', None)
        if not rbac_permission_id:
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": [],
                    "max": 0,
                    "limit": limit
                }
            )
        action_info = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_SUDO_ACTION.value,
            output_data_type=OutputDataType.DEFAULT.value,
            accept_language=self.accept_language,
            query={
                "filter__rbac_permission_id": rbac_permission_id,
                # "filter__sys_organization_id": user_details['sys_organization_id'],
            },
            user=user_details,
        )

        if not action_info:
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": [],
                    "max": 0,
                    "limit": limit
                }
            )

        pipeline = [
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_USER_VALIDATOR.model_name}",
                    "localField": "_id",
                    "foreignField": "sys_user_id",
                    "as": "unwind__rbac_user_validator"
                }
            },
            {
                "$unwind": "$unwind__rbac_user_validator"
            },
            {
                "$match": {
                    "sys_organization_id": ObjectId(user_details['sys_organization_id']),
                    "unwind__rbac_user_validator.rbac_sudo_action_id": ObjectId(action_info['id'])
                }
            },
            {
                "$limit": limit
            },
            {
                "$skip": limit * page
            },
        ]

        all_pipeline = [
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_USER_VALIDATOR.model_name}",
                    "localField": "_id",
                    "foreignField": "sys_user_id",
                    "as": "unwind__rbac_user_validator"
                }
            },
            {
                "$unwind": "$unwind__rbac_user_validator"
            },
            {
                "$match": {
                    "sys_organization_id": ObjectId(user_details['sys_organization_id']),
                    "unwind__rbac_user_validator.rbac_sudo_action_id": ObjectId(action_info['id'])
                }
            },
        ]

        sudo_group_users = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.SYS_USER,
            output_data_type=output_data_type,
            accept_language=self.accept_language,
            pipeline=pipeline,
        )
        self.app_debug_print(
            f" sudo_group_users len : {len(sudo_group_users)}", True)
        extra_data = {
            "limit": limit,
            "max": 0
        }
        if not all_data:
            # get max
            max_data = await self.generic_service.fetch_native_aggregate_count_from_collection(
                collection_key=CollectionKey.SYS_USER,
                accept_language=self.accept_language,
                pipeline=all_pipeline,
            )
            extra_data = {
                "max": max_data,
                "limit": limit
            }
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": sudo_group_users,
                **extra_data
            }
        )

    async def get_sudo_permissions(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page")
    ):
        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)
        # user_details = await self.get_user_info(request=request,accept_language=accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
        raw_query_params: Dict[str, str] = dict(request.query_params)
        query_params = ConverterService.convert_query_params(raw_query_params)
        rbac_permission_id = query_params.get('rbac_permission_id', None)

        pipeline = [

            {
                '$lookup': {
                    'from': "rbac_sudo_action",
                    'localField': "_id",
                    'foreignField': "rbac_permission_id",
                    'as': "unwind__rbac_sudo_action"
                }
            },
            {
                '$unwind': "$unwind__rbac_sudo_action"
            },
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_TITLE.model_name}",
                    'localField': "rbac_title_id",
                    'foreignField': "_id",
                    'as': "unwind__rbac_title"
                }
            },
            {
                '$unwind': "$unwind__rbac_title"
            },
            {
                '$match': {
                    "unwind__rbac_sudo_action.is_sudo_group_action": True,
                    "restricted_profil": {
                        '$elemMatch': {'rbac_profile_id': ObjectId(user_profil['id'])}
                    }
                }
            },

            # Pagination - do this after filtering but before removing fields
            {"$skip": limit * page},
            {"$limit": limit},
            
        ]

        max_pipeline = [

            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_SUDO_ACTION.model_name}",
                    'localField': "rbac_permission_id",
                    'foreignField': "_id",
                    'as': "unwind__rbac_sudo_action"
                }
            },
            {
                '$unwind': "$unwind__rbac_sudo_action"
            },
            {
                '$match': {
                    "unwind__rbac_sudo_action.is_sudo_group_action": True,
                    "restricted_profil": {
                        '$elemMatch': {'rbac_profile_id': ObjectId(user_profil['id'])}
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "docs": {"$push": "$$ROOT"}
                }
            },
            # Merge the array of documents into one object per group.
            {
                "$project": {
                    "merged": {
                        "$reduce": {
                            "input": "$docs",
                            "initialValue": {},
                            "in": {"$mergeObjects": ["$$value", "$$this"]}
                        }
                    }
                }
            },
            # Replace the root with the merged document so that fields are at the top level.
            {
                "$replaceRoot": {"newRoot": "$merged"}
            }
        ]

        sudo_group_action_infos = await self.generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.RBAC_PERMISSION.value,
            output_data_type=output_data_type,
            accept_language=self.accept_language,
            pipeline=pipeline,
            all_data=False,
            page=page,
            limit=limit
        )

        # Process your data
        hierarchy = await self.build_rbac_hierarchy(sudo_group_action_infos, output_data_type)

        self.app_debug_print(f" hierarchy len : {len(hierarchy)}", True)
        extra_data = {
            'max': 0,
            'limit': limit
        }
        if not all_data:
            # get max
            max_data = await self.generic_service.fetch_native_aggregate_count_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION.value,
                accept_language=self.accept_language,
                pipeline=max_pipeline,
            )
            extra_data = {
                "max": max_data,
                "limit": limit
            }
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": hierarchy,
                **extra_data
            }
        )

    async def fetch_standalone_menus(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
    ):
        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)
        # user_details = await self.get_user_info(request=request,accept_language=accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)

        formatted_data = await ApplicationService.get_user_standalone_menus(
            apiConsumer=api_Consumer,
            user=user_details,
            userProfil=user_profil,
            page=0,
            limit=100,
            all_data=False,
            accept_language=self.accept_language,
            output_data_type=OutputDataType(output_data_type).value,
        )
        self.app_debug_print(
            f" standalone menus len : {len(formatted_data)}", True)
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": formatted_data
            }
        )

    async def fetch_notifications(
        self,
        request: Request,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page"),
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
    ):
        ip_address = self.get_real_ip_address(request)
        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)
        # user_details = await self.get_user_info(request=request,accept_language=accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)

        # Get the hashed device ID from the request
        device_hashed_id = await HashService.get_hashed_device_id(request)

        # Example: Perform device-based login logic
        print(f"Device Hashed ID: {device_hashed_id}")

        # Get the device info from the request
        device_info = await self.get_device_info(request=request)
        # Log the device information
        print(f"Device Info: {device_info}")

        location_info = await self.get_location_from_ip_secure(request)
        print(f"Location Info: {location_info}")

        metadata = COLLECTION_MODEL_MAPPING.get(CollectionKey.NTF_NOTIFICATION)
        if not metadata:
            raise ValueError(
                f"Invalid collection key: {CollectionKey.SYS_MENU.value}")

        if not metadata.is_exposed and endpoint_call:
            raise PermissionError(
                f"Access to collection '{CollectionKey.SYS_MENU.value}' is not allowed.")

        raw_query_params: Dict[str, str] = dict(request.query_params)
        query_params = ConverterService.convert_query_params(raw_query_params)
        print(f"Query Parameters (converted): {query_params}")
        query_params = {
            **query_params,
            "filter__targeted_id": user_details['id']
        }

        data = await self.generic_service.fetch_data_from_collection(
            collection_key=CollectionKey.NTF_NOTIFICATION,
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

        # Initialize extra_data unconditionally.
        extra_data = {
            "max": 0,
            "limit": limit
        }

        if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE.value:
            # get max
            max_data = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.NTF_NOTIFICATION,
                accept_language=self.accept_language,
                query={
                    **query_params
                },
                user=user_details,
            )
            extra_data = {
                "max": max_data,
                "limit": limit
            }

        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": data,
                **extra_data
            }
        )

    async def fetch_exchanges_config(
        self,
        request: Request,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page"),
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
    ):

        ip_address = self.get_real_ip_address(request)
        user_details = await self.get_user_info(request, self.accept_language)
        # user_details = await self.get_user_info(request=request,accept_language=accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)

        application_group_flag = request.query_params.get(
            "filter__application_group_flag", EAppGroupFlag.COMMON.value)
        


        # print(f" \n\n\n api_consumer :  \n\n\n")
        all_currencies = await self.generic_service.fetch_data_from_collection(
            collection_key=CollectionKey.REF_CURRENCY.value,
            all_data=True,
            output_data_type=OutputDataType.DEFAULT.value,
            accept_language=self.accept_language,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )
        self.app_debug_print(
            f" \n\n\n all_currencies : {all_currencies} \n\n\n")

        _currencies_tb = list(all_currencies)
        _currencies_tb2 = list(all_currencies)
        _coupled_tab = []

        for index, element in enumerate(_currencies_tb):
            self.app_debug_print(
                f" \n\n\n index loop : {index} -> {element} \n\n\n")
            for elem in _currencies_tb2:
                if str(element['id']) == str(elem['id']):
                    continue

                _some = any(
                    (str(v['base_currency_id']) == str(element['id']) and str(v['targeted_currency_id']) == str(elem['id'])) or
                    (str(v['targeted_currency_id']) == str(element['id'])
                     and str(v['base_currency_id']) == str(elem['id']))
                    for v in _coupled_tab
                )

                if _some:
                    continue
                
                self.app_debug_print(
            f" \n\n\n application_group_flag : {application_group_flag} \n\n\n",True)
                _couple_does_exist1 = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_CURRENCY_EXCHANGE.value,
                    all_data=True,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={
                        "filter__base_currency_id": str(element['id']),
                        "filter__targeted_currency_id": str(elem['id']),
                        "filter__application_group_flag": application_group_flag
                    },
                    user=user_details,
                )
                self.app_debug_print(
                    f" _couple_does_exist1 : {len(_couple_does_exist1)}",True)

                _couple_does_exist2 = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_CURRENCY_EXCHANGE.value,
                    all_data=True,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={
                        "filter__base_currency_id": str(elem['id']),
                        "filter__targeted_currency_id": str(element['id']),
                        "filter__application_group_flag": application_group_flag
                    },
                    user=user_details,
                )

                self.app_debug_print(
                    f" _couple_does_exist2 : {len(_couple_does_exist2)}",True)

                if not _couple_does_exist1 and not _couple_does_exist2:
                    _coupled_tab.append({
                        "base_currency_id": element["id"],
                        "targeted_currency_id": elem["id"],
                        "value": 1
                    })
                    _coupled_tab.append({
                        "base_currency_id": elem["id"],
                        "targeted_currency_id": element["id"],
                        "value": 1
                    })
                elif not _couple_does_exist1 and _couple_does_exist2:
                    _coupled_tab.append({
                        "base_currency_id": element['id'],
                        "targeted_currency_id": elem["id"],
                        "value": 1
                    })
                elif _couple_does_exist1 and not _couple_does_exist2:
                    _coupled_tab.append({
                        "base_currency_id": elem['id'],
                        "targeted_currency_id": element['id'],
                        "value": 1
                    })
                else:
                    continue

        _latest_tb = []
        for element in _coupled_tab:
            base_currency = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_CURRENCY.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id": element['base_currency_id']
                },
                user=user_details,
            )
            target_currency = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_CURRENCY.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id": element['targeted_currency_id']
                },
                user=user_details,
            )
            _latest_tb.append({
                **element,
                "id": None,
                "base_currency": base_currency if base_currency else None,
                "targeted_currency": target_currency if target_currency else None,
            })

        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": _latest_tb,
            }
        )

    async def fetch_org_exchanges_config(
        self,
        request: Request,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page"),
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
    ):
        ip_address = self.get_real_ip_address(request)
        user_details = await self.get_user_info(request, self.accept_language)
        # user_details = await self.get_user_info(request=request,accept_language=accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)

        application_group_flag = request.query_params.get(
            "filter__application_group_flag", EAppGroupFlag.COMMON.value)

        # print(f" \n\n\n api_consumer :  \n\n\n")
        all_currencies = await self.generic_service.fetch_data_from_collection(
            collection_key=CollectionKey.REF_CURRENCY.value,
            all_data=True,
            output_data_type=OutputDataType.DEFAULT.value,
            accept_language=self.accept_language,
            query={
                "filter__is_activated": True
            },
            user=user_details,
        )
        self.app_debug_print(
            f" \n\n\n all_currencies : {all_currencies} \n\n\n")

        _currencies_tb = list(all_currencies)
        _currencies_tb2 = list(all_currencies)
        _coupled_tab = []

        for index, element in enumerate(_currencies_tb):
            self.app_debug_print(
                f" \n\n\n index loop : {index} -> {element} \n\n\n")
            for elem in _currencies_tb2:
                if str(element['id']) == str(elem['id']):
                    continue

                _some = any(
                    (str(v['base_currency_id']) == str(element['id']) and str(v['targeted_currency_id']) == str(elem['id'])) or
                    (str(v['targeted_currency_id']) == str(element['id'])
                     and str(v['base_currency_id']) == str(elem['id']))
                    for v in _coupled_tab
                )

                if _some:
                    continue

                _couple_does_exist1 = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_CURRENCY_EXCHANGE.value,
                    all_data=True,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={
                        "filter__base_currency_id": str(element['id']),
                        "filter__targeted_currency_id": str(elem['id']),
                        "filter__sys_organization_id": user_details['sys_organization_id'],
                        "filter__application_group_flag": application_group_flag
                    },
                    user=user_details,
                )
                self.app_debug_print(
                    f" _couple_does_exist1 : {_couple_does_exist1}")

                _couple_does_exist2 = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_CURRENCY_EXCHANGE.value,
                    all_data=True,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={
                        "filter__base_currency_id": str(elem['id']),
                        "filter__targeted_currency_id": str(element['id']),
                        "filter__sys_organization_id": user_details['sys_organization_id'],
                        "filter__application_group_flag": application_group_flag
                    },
                    user=user_details,
                )

                self.app_debug_print(
                    f" _couple_does_exist2 : {_couple_does_exist2}")

                if not _couple_does_exist1 and not _couple_does_exist2:
                    _coupled_tab.append({
                        "base_currency_id": element["id"],
                        "targeted_currency_id": elem["id"],
                        "value": 1
                    })
                    _coupled_tab.append({
                        "base_currency_id": elem["id"],
                        "targeted_currency_id": element["id"],
                        "value": 1
                    })
                elif not _couple_does_exist1 and _couple_does_exist2:
                    _coupled_tab.append({
                        "base_currency_id": element['id'],
                        "targeted_currency_id": elem["id"],
                        "value": 1
                    })
                elif _couple_does_exist1 and not _couple_does_exist2:
                    _coupled_tab.append({
                        "base_currency_id": elem['id'],
                        "targeted_currency_id": element['id'],
                        "value": 1
                    })
                else:
                    continue

        _latest_tb = []
        for element in _coupled_tab:
            base_currency = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_CURRENCY.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id": element['base_currency_id']
                },
                user=user_details,
            )
            target_currency = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_CURRENCY.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id": element['targeted_currency_id']
                },
                user=user_details,
            )
            _latest_tb.append({
                **element,
                "id": None,
                "base_currency": base_currency if base_currency else None,
                "targeted_currency": target_currency if target_currency else None,
            })

        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": _latest_tb,
            }
        )

    async def fetch_user_config(
        self,
        request: Request,
    ):

        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)
        # user_details = await self.get_user_info(request=request,accept_language=accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)

        self.app_debug_print(f" \n\n\n api_consumer : {api_Consumer}  \n\n\n")
        self.app_debug_print(
            f" \n\n\n user_details['id'] : {user_details['id']}  \n\n\n", False)

        user_config = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_USER_CONFIG.value,
            output_data_type=OutputDataType.DEFAULT.value,
            accept_language=self.accept_language,
            query={
                "filter__sys_user_id": user_details['id']
            },
            user=user_details,
        )
        if not user_config:
            language = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_LANGUAGE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__short_code": str(self.accept_language).strip()
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
                "dark_mode": False,
                "ref_language_id": language['id'],
                "sys_user_id": user_details['id'],
            }
            self.app_debug_print(
                f" \n\n\n config_data to save : {config_data} \n\n\n", True)
            result = await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_USER_CONFIG,
                filter_data={"sys_user_id": user_details['id']},
                update_data=config_data,
                user=user_details, request=request,
            )

            self.app_debug_print(
                f" \n\n\n result upsert : {result} \n\n\n", True)

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
                f" \n\n\n user_config : {user_config} \n\n\n", False)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": {
                        "language": language['short_code'],
                        "dark_mode": user_config['dark_mode'],
                    },
                }
            )

        language = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.REF_LANGUAGE.value,
            output_data_type=OutputDataType.DEFAULT.value,
            accept_language=self.accept_language,
            query={
                "filter__short_code": str(self.accept_language).strip()
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

        self.app_debug_print(f" \n\n\n user_config : {user_config} \n\n\n",)

        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": {
                    "language": language['short_code'],
                    "dark_mode": user_config['dark_mode'],
                },
            }
        )

    async def add_exchanges_config(
        self,
        request: Request,
        payload: UserConfigPayload
    ):

        # DECODE USER TOKEN
        user_details = await self.get_user_info(request, self.accept_language)
        # user_details = await self.get_user_info(request=request,accept_language=accept_language)
        api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
        user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)

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
            "dark_mode": payload.dark_mode if payload.dark_mode else False,
            "ref_language_id": language['id'],
            "sys_user_id": user_details['id'],
        }
        result = await self.generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.CFG_USER_CONFIG,
            filter_data={"sys_user_id": user_details['id']},
            update_data=config_data,
            user=user_details, request=request,
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
            f" \n\n\n user_config : {user_config} \n\n\n", False)

        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "data": {
                    "language": language['short_code'],
                    "dark_mode": user_config['dark_mode'],
                },
            }
        )

    async def add_translation_data(self, request: Request, data: Dict[str, Any]):
        """
        Endpoint to add a new document to the specified collection.
        """
        try:
            # Add data to the collection
            item_id = await self.generic_service.add_data_to_collection(CollectionKey.CFG_TRANSLATION, data)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data added successfully",
                }
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_agent_user_account_head(
        self,
        request: Request,
    ):
        """
        Fetch the head of a collection: fields, types, and constraints.
        """
        # Capture query parameters from the request
        query_params = dict(request.query_params)
        try:
            # Convert collection name to CollectionKey and fetch model metadata
            try:
                collection_key = CollectionKey.SYS_USER
                model_class, model_name = self.get_model_from_collection_key(
                    collection_key,
                    endpoint_call=True  # Enforce API access control
                )
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid collection")
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))

            # DECODE USER TOKEN
            user_details = await self.get_user_info(request, self.accept_language)
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)

            sys_organization_agent_id = query_params.get(
                'default__sys_organization_agent_id', None)
            if not sys_organization_agent_id:
                message = self.get_response_message(
                    MessageCategory.COMMON, "INVALID_QUERY_PARAMS", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            pipeline = [
                {
                    "$match": {
                        "_id": ObjectId(sys_organization_agent_id),
                    }
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.SYS_PERSON.model_name}",
                        'localField': "sys_person_id",
                        'foreignField': "_id",
                        'as': "unwind__sys_person"
                    }
                },
                {
                    '$unwind': "$unwind__sys_person"
                },
                {
                    "$group": {
                        "_id": None,
                        "docs": {"$push": "$$ROOT"}
                    }
                },
                # Merge the array of documents into one object per group.
                {
                    "$project": {
                        "merged": {
                            "$reduce": {
                                "input": "$docs",
                                "initialValue": {},
                                "in": {"$mergeObjects": ["$$value", "$$this"]}
                            }
                        }
                    }
                },
                # Replace the root with the merged document so that fields are at the top level.
                {
                    "$replaceRoot": {"newRoot": "$merged"}
                }
            ]
            agent_info = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION_AGENT,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                pipeline=pipeline,
            )

            self.app_debug_print(
                f"\n\nfetching head agent_info: {agent_info}\n\n", True)
            if not agent_info:
                message = self.get_response_message(
                    MessageCategory.COMMON, "AGENT_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # Extract and transform schema metadata
            schema_extra = model_class.model_json_schema().get("properties", {})
 
            # print(f"\n\n default_roles : {default_roles}") 
            query_params = {
                **query_params,
                "default__first_name": agent_info[0]['sys_person']['first_name'],
                "default__last_name": agent_info[0]['sys_person']['last_name'],
                "default__sur_name": agent_info[0]['sys_person'].get('sur_name', ''),
                "default__address": agent_info[0]['sys_person'].get('address_line1', ''),
                "default__gender": agent_info[0]['sys_person']['gender'],
                "default__birth_day": None,
                "default__birth_city": None,
                "default__cfg_organism_chart_id":agent_info[0]['cfg_organism_chart_id'],
                # "default__cfg_organism_chart_id":str(agent_info[0].get('cfg_organism_chart_id',None)),
                "default__sys_person_id": str(agent_info[0]['sys_person_id']),
            }
            # self.app_debug_print(model_class.model_json_schema())
            transformed_head = await self.generic_service.transform_schema_to_head(
                schema=schema_extra,
                model_name=model_name,
                accept_language=self.accept_language,
                query_params=query_params,
                is_organization_head=True,
                sys_organization_id=user_details['sys_organization_id'],
                exclude_fields=[],  # 'rbac_profile_id'
                # exclude_fields=['is_default','system_reserved_actions'],#'rbac_profile_id'
                # exclude_fields=["soft_deleted", "created_at"],
                # force_include_fields=["sys_person_id", "sys_person_id"],
                # default_data_sources={'rbac_role_id':default_roles}
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": transformed_head,
                }
            )

        except Exception as e:
            self.app_debug_print(f"Error fetching head: {str(e)}", True)
            raise HTTPException(
                status_code=500, detail="An unexpected error occurred.")

    async def get_saas_users(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(
            0, description="Page number for pagination"),
        limit: Optional[int] = Query(
            10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            api_Consumer = await self.get_api_consumer(request, self.accept_language)
            user_profil = await self.get_user_profil(request, self.accept_language)
            # Convert query parameters to dictionary
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)

            query_params = ConverterService.convert_query_params(
                raw_query_params)
            self.app_debug_print(
                f"Query Parameters (converted): {query_params}", True)
            sort = request.query_params.get("sort", {'created_at': -1})
            self.app_debug_print(f"Query Parameters (SORT): {sort}", False)
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
                sort=sort
            )
            self.app_debug_print(f"Query data: {len(data)}", False)
            extra_data = {}
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.SYS_USER,
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
                    "data": data,
                    **extra_data
                }
            )
        except Exception as e:
            self.app_debug_print(f"Error fetching head: {str(e)}", True)
            raise HTTPException(
                status_code=500, detail="An unexpected error occurred.")

    async def get_agent_user_account(
        self,
        request: Request,
    ):
        """
        Fetch the head of a collection: fields, types, and constraints.
        """
        # Capture query parameters from the request
        query_params = dict(request.query_params)
        try:
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request, self.accept_language)
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)

            sys_organization_agent_id = query_params.get(
                'sys_organizatin_agent_id', None)
            if not sys_organization_agent_id:
                message = self.get_response_message(
                    MessageCategory.COMMON, "INVALID_QUERY_PARAMS", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            pipeline = [
                {
                    "$match": {
                        "_id": ObjectId(sys_organization_agent_id),
                    }
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.SYS_PERSON.model_name}",
                        'localField': "sys_person_id",
                        'foreignField': "_id",
                        'as': "unwind__sys_person"
                    }
                },
                {
                    '$unwind': "$unwind__sys_person"
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.SYS_USER.model_name}",
                        'localField': "sys_user_id",
                        'foreignField': "_id",
                        'as': "unwind__sys_user"
                    }
                },
                {
                    '$unwind': "$unwind__sys_user"
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_ROLE.model_name}",
                        'localField': "unwind__sys_user.rbac_role_id",
                        'foreignField': "_id",
                        'as': "unwind__rbac_role"
                    }
                },
                {
                    '$unwind': "$unwind__rbac_role"
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION_ROLE.model_name}",
                        'localField': "unwind__rbac_role._id",
                        'foreignField': "rbac_role_id",
                        'as': "unwind__rbac_permission_role"
                    }
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                        'localField': "unwind__rbac_permission_role.rbac_permission_id",
                        'foreignField': "_id",
                        'as': "unwind__rbac_permission"
                    }
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                        'localField': "unwind__rbac_permission._id",
                        'foreignField': "rbac_permission_id",
                        'as': "unwind__rbac_privilege"
                    }
                }, 
                {
                    "$group": {
                        "_id": None,
                        "docs": {"$push": "$$ROOT"}
                    }
                },
                # Merge the array of documents into one object per group.
                {
                    "$project": {
                        "merged": {
                            "$reduce": {
                                "input": "$docs",
                                "initialValue": {},
                                "in": {"$mergeObjects": ["$$value", "$$this"]}
                            }
                        }
                    }
                },
                # Replace the root with the merged document so that fields are at the top level.
                {
                    "$replaceRoot": {"newRoot": "$merged"}
                }
            ]
            usesr_account_infos = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION_AGENT,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                pipeline=pipeline,
            )
            self.app_debug_print(
                f"\n\n fetching  usesr_account_infos : {len(usesr_account_infos)}\n\n", True)
            # Recursive function to remove password fields

            def remove_password(data):
                if isinstance(data, dict):
                    # Remove 'password' key if it exists
                    if 'password' in data:
                        del data['password']
                    # Recursively process all values in the dictionary
                    for key, value in data.items():
                        data[key] = remove_password(value)
                elif isinstance(data, list):
                    # Recursively process all items in the list
                    data = [remove_password(item) for item in data]
                return data

            # Your existing code

            user_account_info = {}
            if len(usesr_account_infos) > 0:
                user_account_info = {
                    **usesr_account_infos[0],
                }

                profil_permission_pipeline = [
                    {
                        '$match': {
                            "restricted_profil": {
                                '$elemMatch': {'rbac_profile_id': ObjectId(user_profil['id'])}
                            }
                        }
                    }
                ]
                profil_permissions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_ROLE,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    pipeline=profil_permission_pipeline,
                )

                login_histories = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                    all_data=False,
                    page=0,
                    limit=20,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={
                        "filter__sys_user_id": str(usesr_account_infos[0]['sys_user']['id'])
                    },
                    user=user_details
                )
                permissions = [
                    permission for permission in usesr_account_infos[0]['rbac_permission']
                    if permission['is_default'] == False
                ]

                list_of_privileges = usesr_account_infos[0]['rbac_privilege']
                if list_of_privileges:
                    formated_permissions = []
                    for privilege in list_of_privileges:
                        perm = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.RBAC_PERMISSION,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={"filter___id": str(
                                privilege['rbac_permission_id'])},
                            user=user_details,
                        )
                        if perm:
                            formated_permissions.append(perm)
                    user_account_info = {
                        **user_account_info,
                        "privilege_permissions": formated_permissions,
                        "rbac_permission": permissions,
                        "login_histories": login_histories,
                        "profil_permissions": profil_permissions,
                    }
                else:
                    user_account_info = {
                        **user_account_info,
                        "privilege_permissions": [],
                        "rbac_permission": permissions,
                        "login_histories": login_histories,
                        "profil_permissions": profil_permissions,
                    }

                # Remove any password fields from user_account_info
                user_account_info = remove_password(user_account_info)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": user_account_info if user_account_info else None,
                }
            )

        except Exception as e:
            self.app_debug_print(f"Error fetching head: {str(e)}", True)
            raise HTTPException(
                status_code=500, detail="An unexpected error occurred.")

    async def view_file(self, request: Request, file_id: str):
        """
        Serve a file directly in the browser by fetching it from a remote API endpoint.
        """
        self.app_debug_print(f"SENT FILE ID: {file_id}", True)
        file_id = request.query_params.get('file_id', None)
        if not file_id:
            message = self.get_response_message(
                MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
            raise HTTPException(status_code=400, detail=message)
        file_id = f"{file_id}".strip().lower()
        # Query the file information from the database
        parent_query = {f"filter__file_str_id_composed": file_id}
        file_info = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.ARCH_FILE,
            output_data_type=OutputDataType.DEFAULT.value,
            accept_language=self.accept_language,
            query=parent_query,
        )

        self.app_debug_print(f"FILE FOUNDED: {file_info}", True)

        # Check if the file info exists
        missing_message = self.get_response_message(
            MessageCategory.MISSING, "MISSING_FILE_FROM_ID", self.accept_language, file_id=file_id
        )
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=missing_message)

        # Fetch the file from the remote API endpoint
        # Assuming the file_info contains a 'file_url' field
        remote_file_url = file_info.get("remote_arch_file_url")
        if not remote_file_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File URL not found in the file information.",
            )

        # Stream the file from the remote API
        async def stream_file():
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", remote_file_url) as response:
                    if response.status_code != 200:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="File not found on the remote server.",
                        )
                    async for chunk in response.aiter_bytes():
                        yield chunk

        # Determine the media type (default to "application/octet-stream")
        media_type = file_info.get("file_type", "application/octet-stream")

        return StreamingResponse(
            stream_file(),
            media_type=media_type,
            headers={
                "Content-Disposition": f"inline; filename={file_info.get('file_name', 'file')}"},
        )

    # Fallback SVG returned by view-svg when the real icon cannot be served.
    # Guarantees <img src="…/view-svg?q=…"> always receives valid SVG
    # instead of a JSON error body that the browser cannot render.
    _FALLBACK_SVG = ("""<svg version="1.1" id="fi_456793" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" viewBox="0 0 512 512" style="enable-background:new 0 0 512 512;" xml:space="preserve">
            <polygon style="fill:#BCBCBC;" points="0,118.908 512,118.908 512,75.708 194.856,75.708 169.184,50.316 30.728,50.316 0,81.036 "/>
            <rect x="21.608" y="97.324" style="fill:#FFFFFF;" width="468.8" height="21.584"/>
            <rect y="118.908" style="fill:#E5E5E5;" width="512" height="342.768"/>
            <rect y="449.116" style="fill:#BCBCBC;" width="512" height="12.568"/>
            <g/>
            <g/>
            <g/>
            <g/>
            <g/>
            <g/>
            <g/>
            <g/>
            <g/>
            <g/>
            <g/>
            <g/>
            <g/>
            <g/>
            <g/>
            </svg>"""
    )

    async def view_svg_icon(self, request: Request):
        """
        Serve an SVG icon by decrypting a single query payload and forwarding to file system service.
        Always returns image/svg+xml so <img> tags never receive a JSON error.
        """
        def _fallback(reason: str = ""):
            if reason:
                self.app_debug_print(f"view_svg_icon fallback: {reason}", True)
            return Response(
                content=self._FALLBACK_SVG,
                media_type="image/svg+xml",
                headers={"Cache-Control": "no-cache"},
            )

        try:
            encrypted_query = request.query_params.get("q", "")
            if not encrypted_query:
                return _fallback("missing q param")

            try:
                decrypted_payload = EncryptionService.decrypt_data_url_safe(encrypted_query)
            except Exception as dec_err:
                return _fallback(f"decrypt error: {dec_err}")

            payload = json.loads(str(decrypted_payload or "{}"))

            menu_or_app_path = str(payload.get("menu_or_app_path", "")).strip()
            menu_or_app_flag = str(payload.get("menu_or_app_flag", "")).strip()
            api_consumer_flag = str(payload.get("api_consumer_flag", "")).strip()

            safe_flag = SvgIconService._sanitize_component(menu_or_app_flag)
            safe_api_consumer_flag = SvgIconService._sanitize_component(api_consumer_flag)
            if not menu_or_app_path or not safe_flag or not safe_api_consumer_flag:
                return _fallback("invalid payload fields")

            file_server_base_url = str(settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL or "").strip().rstrip("/")
            if not file_server_base_url:
                return _fallback("SENAT_DIGIT_APPS_FILE_SYSTEM_URL not configured")

            file_name = f"{safe_flag}___{safe_api_consumer_flag}.svg"
            base_dir = SvgIconService._build_base_dir_from_path(menu_or_app_path)
            params = {
                "file_name": file_name,
                "api_consumer_flag": safe_api_consumer_flag,
            }
            if base_dir:
                params["base_dir"] = base_dir

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{file_server_base_url}/files/fetch-svg",
                    params=params,
                )

            if response.status_code != 200:
                return _fallback(f"file server returned {response.status_code}")

            return Response(
                content=response.content,
                media_type=response.headers.get("content-type", "image/svg+xml"),
                headers={"Cache-Control": "public, max-age=3600"},
            )
        except Exception as e:
            self.app_debug_print(f"Error while serving svg icon: {e}", True)
            return _fallback(f"exception: {e}")

    async def view_file_from_gen_id(self, request: Request, gen_id: str):
        """
        Serve a file directly in the browser by fetching it from a remote API endpoint.
        """
        self.app_debug_print(f"SENT FILE ID: {gen_id}", True)
        gen_id = request.query_params.get('gen_id', None)
        if not gen_id:
            message = self.get_response_message(
                MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
            raise HTTPException(status_code=400, detail=message)
        
        gen_id = f"{gen_id}".strip().lower()
        # Query the file information from the database
        parent_query = {f"filter__file_generated_id": gen_id}
        file_info = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.ARCH_FILE,
            output_data_type=OutputDataType.DEFAULT.value,
            accept_language=self.accept_language,
            query=parent_query,
        )

        self.app_debug_print(f"FILE FOUNDED: {file_info}", True)

        # Check if the file info exists
        missing_message = self.get_response_message(
            MessageCategory.MISSING, "MISSING_FILE_FROM_ID", self.accept_language, file_id=gen_id
        )
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=missing_message)

        # Fetch the file from the remote API endpoint
        # Assuming the file_info contains a 'file_url' field
        remote_file_url = file_info.get("remote_arch_file_url")
        if not remote_file_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File URL not found in the file information.",
            )

        # Stream the file from the remote API
        async def stream_file():
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", remote_file_url) as response:
                    if response.status_code != 200:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="File not found on the remote server.",
                        )
                    async for chunk in response.aiter_bytes():
                        yield chunk

        # Determine the media type (default to "application/octet-stream")
        media_type = file_info.get("file_type", "application/octet-stream")

        return StreamingResponse(
            stream_file(),
            media_type=media_type,
            headers={
                "Content-Disposition": f"inline; filename={file_info.get('file_name', 'file')}"},
        )

    async def download_file(self, request: Request):
        """
        Serve a file directly in the browser by fetching it from a remote API endpoint.
        """
        # Extract the accept-language header
        self.app_debug_print(f"SENT FILE ID: {file_id}", True)

        # file_id
        file_id = request.query_params.get('file_id', None)
        if not file_id:
            message = self.get_response_message(
                MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
            raise HTTPException(status_code=400, detail=message)

        # Normalize the file_id
        file_id = file_id.strip().lower()

        # Query the file information from the database
        parent_query = {"filter__file_str_id_composed": file_id}
        file_info = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.ARCH_FILE,
            output_data_type=OutputDataType.DEFAULT.value,
            accept_language=self.accept_language,
            query=parent_query,
        )

        self.app_debug_print(f"FILE FOUND: {file_info['id']}", True)

        # Check if the file info exists
        if not file_info:
            missing_message = self.get_response_message(
                MessageCategory.MISSING, "MISSING_FILE_FROM_ID", self.accept_language, file_id=file_id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=missing_message)

        # Fetch the file URL from the file info
        # remote_file_url: Optional[str] = file_info.get("file_url",'')
        remote_file_url: Optional[str] = file_info.get(
            "remote_arch_file_url", '')
        self.app_debug_print(f"remote_file_url >>> : {remote_file_url}", True)
        if not remote_file_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File URL not found in the file information.",
            )

        # Stream the file from the remote API
        async def stream_file():
            async with httpx.AsyncClient() as client:
                try:
                    async with client.stream("GET", remote_file_url) as response:
                        self.app_debug_print(
                            f"\n\n\n\nresponse.status_code >>> : {response.status_code}", True)
                        if response.status_code != 200:
                            raise HTTPException(
                                status_code=status.HTTP_404_NOT_FOUND,
                                detail="File not found on the remote server.",
                            )
                        # Log the content type and size
                        content_type = response.headers.get("content-type")
                        content_length = response.headers.get("content-length")
                        self.app_debug_print(
                            f"Remote file content-type: {content_type}", True)
                        self.app_debug_print(
                            f"Remote file content-length: {content_length}", True)

                        # Stream the file in chunks
                        async for chunk in response.aiter_bytes():
                            yield chunk
                except httpx.RequestError as e:
                    self.app_debug_print(
                        f"\n\n\n\n err from the remote server >>> : {e}", True)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to fetch the file from the remote server: {str(e)}",
                    )

        # Determine the media type (default to "application/octet-stream")
        media_type = file_info.get("file_type", "application/octet-stream")

        # Set the filename for the Content-Disposition header
        filename = file_info.get("file_name", "file")

        return StreamingResponse(
            stream_file(),
            media_type=media_type,
            headers={"Content-Disposition": f"inline; filename={filename}"},
        )

    async def download_local_file(self, request: Request):
        """
        Serve a file directly from the local filesystem instead of fetching from a remote API endpoint.
        """
        # Extract the accept-language header
        self.app_debug_print(f"SENT FILE ID: {file_id}", True)
        file_id = request.query_params.get('file_id', None)
        if not file_id:
            message = self.get_response_message(
                MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
            raise HTTPException(status_code=400, detail=message)

        # Normalize the file_id
        file_id = file_id.strip().lower()

        # Query the file information from the database
        parent_query = {"filter__file_str_id_composed": file_id}
        file_info = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.ARCH_FILE,
            output_data_type=OutputDataType.DEFAULT.value,
            accept_language=self.accept_language,
            query=parent_query,
        )

        self.app_debug_print(f"FILE FOUND: {file_info}", True)

        # Check if the file info exists
        if not file_info:
            missing_message = self.get_response_message(
                MessageCategory.MISSING, "MISSING_FILE_FROM_ID", self.accept_language, file_id=file_id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=missing_message)

        # Check if this is a local file
        is_local_file = file_info.get("is_local_file", False)
        file_path = file_info.get("file_path")

        if not is_local_file or not file_path:
            # Fall back to remote URL if not a local file
            remote_file_url = file_info.get("remote_arch_file_url")
            if not remote_file_url:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File URL not found in the file information.",
                )

            # Stream from remote URL as fallback
            async def stream_remote_file():
                async with httpx.AsyncClient() as client:
                    try:
                        async with client.stream("GET", remote_file_url) as response:
                            if response.status_code != 200:
                                raise HTTPException(
                                    status_code=status.HTTP_404_NOT_FOUND,
                                    detail="File not found on the remote server.",
                                )
                            async for chunk in response.aiter_bytes():
                                yield chunk
                    except httpx.RequestError as e:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to fetch the file from the remote server: {str(e)}",
                        )

            return StreamingResponse(
                stream_remote_file(),
                media_type=file_info.get(
                    "file_type", "application/octet-stream"),
                headers={
                    "Content-Disposition": f"attachment; filename={file_info.get('file_name', 'file')}"},
            )

        # Check if the file exists on the local filesystem
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Local file not found at path: {file_path}",
            )

        # Stream the file from the local filesystem
        async def stream_local_file():
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):  # Read in 8KB chunks
                    yield chunk

        # Determine the media type (default to "application/octet-stream")
        media_type = file_info.get("file_type", "application/octet-stream")

        # Set the filename for the Content-Disposition header
        filename = file_info.get("file_name", "file")

        return StreamingResponse(
            stream_local_file(),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    

    async def _org_add_profile_data_background(
        self,
        data: Dict[str, Any],
        user_details: Dict[str, Any],
        organization_profil: Dict[str, Any]
    ):
        try:
            profile_data = {
                **data,
                "sys_organization_id": user_details['sys_organization_id'],
                "rbac_profile_id": organization_profil['id']
            }
            # Add data to the collection
            org_profil_id = await self.generic_service.add_data_to_collection(CollectionKey.RBAC_PROFILE, profile_data, user=user_details, request=request)

            # ADD RESTRICTED PROFIL FROM PARENT PROFIL
            parent_restricted_profil = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=OutputDataType.DEFAULT,
                all_data=True,
                query={
                    "filter__rbac_profile_id": organization_profil['id']
                },
                user=user_details,
            )
            for restricted_profil in parent_restricted_profil:
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    filter_data={
                        "targeted_id": restricted_profil['targeted_id'], 'rbac_profile_id': org_profil_id},
                    update_data={
                        "targeted_id": restricted_profil['targeted_id'],
                        "rbac_profile_id": org_profil_id,
                    },
                    user=user_details, request=request,
                )
            return True
        except Exception as e:
            self.app_debug_print(f"Error in _org_add_profile_data_background: {str(e)}",True)
            return False

    async def org_add_profile_data(self, request: Request,background_tasks: BackgroundTasks, data: Dict[str, Any]):
        """
        Endpoint to add a new role from organization.
        """
        try:
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request, self.accept_language)
            api_Consumer = await self.get_api_consumer(request, self.accept_language)
            user_profil = await self.get_user_profil(request, self.accept_language)

            self.app_debug_print(f"\n\nbody : {data}\n\n", True)

            agent_organization = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter___id": user_details['sys_organization_id'],
                },
                user=user_details,
            )
            if not agent_organization:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "AGENT_ORGANIZATION_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            api_consumer_id = api_Consumer['id']
            organization_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter___id": agent_organization['rbac_profile_id'],
                },
                user=user_details,
            )
            if not organization_profil:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "ORGANIZATION_PROFIL_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # PROCESS CONTINUE IN BACKGROUND
            asyncio.create_task(
                self._org_add_profile_data_background(
                    data=data,
                    user_details=user_details,
                    organization_profil=organization_profil
                )
            )

            message = self.get_response_message(
                MessageCategory.SUCCESS, "DATA_ADD_CONTINUED_IN_BACKGROUND", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "status_code": status.HTTP_201_CREATED,
                    "message": message,
                    "data": None
                }
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        

    async def _org_delete_profile_data_background(
        self,
        profil_info: Dict[str, Any]
    ):
        try:
            # DELETE ALL RESTRICTED PROFIL
            parent_restricted_profil = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=OutputDataType.DEFAULT,
                all_data=True,
                query={
                    "filter__rbac_profile_id": profil_info['id']
                }
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

            return True
        except Exception as e:
            self.app_debug_print(f"Error in _org_delete_profile_data_background: {str(e)}",True)
            return False

    async def org_delete_profile_data(self, request: Request,background_tasks: BackgroundTasks):
        """
        Endpoint to add a new role from organization.
        """
        try:
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request, self.accept_language)
            api_Consumer = await self.get_api_consumer(request, self.accept_language)
            user_profil = await self.get_user_profil(request, self.accept_language)

            item_id = request.query_params.get('item_id', None)
            if not item_id:
                message = self.get_response_message(
                    MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter___id": item_id,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )
            if not profil_info:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "PROFIL_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            # PROCESS CONTINUE IN BACKGROUND
            asyncio.create_task(
                self._org_delete_profile_data_background(
                    profil_info=profil_info
                )
            )

            message = self.get_response_message(
                MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "status_code": status.HTTP_201_CREATED,
                    "message": message,
                    "data": item_id
                }
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def org_get_profile_permissions(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
    ):
        try:

            user_details = await self.get_user_info(request, self.accept_language)
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = ConverterService.convert_query_params(
                raw_query_params)
            rbac_profile_id = query_params.get('rbac_profile_id', None)
            if not rbac_profile_id:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            # CHECK IF THE ROLE BELONGS TO THE ORGANIZATION
            profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id": rbac_profile_id,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )
            if not profil_info:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
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
                        "unwind__rbac_permission.is_accessible_to_all_profil": False,
                    }
                },
            ]
            profil_permissions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL.value,
                output_data_type=OutputDataType.DATA_TABLE.value,
                accept_language=self.accept_language,
                page=0,
                limit=100000,
                pipeline=profil_permissions_pipeline,
            )
            self.app_debug_print(
                f"\n\n\n role_permissions LEN: {len(profil_permissions)} \n\n\n", True)
            # Process your data
            hierarchy = await self.rbac_role_service.build_profil_joined_to_permission_rbac_hierarchy(profil_permissions, output_data_type, rbac_profile_id)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": hierarchy,
                }
            )
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR 1 : {e} \n\n\n", True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 : {e} \n\n\n", True)
            raise HTTPException(status_code=500, detail=str(e))

    async def org_get_extended_profile_permissions(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        endpoint_call: Optional[bool] = False,
    ):
        try:

            user_details = await self.get_user_info(request, self.accept_language)
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = ConverterService.convert_query_params(
                raw_query_params)
            rbac_profile_id = query_params.get('rbac_profile_id', None)
            if not rbac_profile_id:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            # CHECK IF THE ROLE BELONGS TO THE ORGANIZATION
            profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id": rbac_profile_id,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )
            if not profil_info:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
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
                        "unwind__rbac_permission.is_accessible_to_all_profil": False,
                    }
                },
            ]
            profil_permissions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL.value,
                output_data_type=OutputDataType.DATA_TABLE.value,
                accept_language=self.accept_language,
                page=0,
                limit=100000,
                pipeline=profil_permissions_pipeline,
            )
            self.app_debug_print(
                f"\n\n\n role_permissions LEN: {len(profil_permissions)} \n\n\n", True)
            # Process your data
            hierarchy = await self.rbac_role_service.build_extended_profil_joined_to_permission_rbac_hierarchy(profil_permissions, output_data_type, rbac_profile_id)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": hierarchy,
                }
            )
        except PermissionError as e:
            self.app_debug_print(f"\n\n\n ERROR 1 : {e} \n\n\n", True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f"\n\n\n ERROR 2 : {e} \n\n\n", True)
            raise HTTPException(status_code=500, detail=str(e))
        


    async def _update_org_profil_permissions_background(
        self,
        validator_data: ProfilPermissionCreate,
        user_details: Dict[str, Any],
        profil_info: Dict[str, Any]
    ):
        try:
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
                        "unwind__rbac_permission.is_accessible_to_all_profil": False,
                    }
                },
            ]
            profil_permissions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL.value,
                output_data_type=OutputDataType.DATA_TABLE.value,
                accept_language=self.accept_language,
                page=0,
                limit=100000,
                pipeline=profil_permissions_pipeline,
            )
            for restricted_profil in profil_permissions:
                restricted_profil_id = restricted_profil['id']['display_value'] if isinstance(
                    restricted_profil, dict) else None
                await self.generic_service.hard_delete_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL.value,
                    accept_language=self.accept_language,
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
                        "rbac_profile_id": new_perm_tar_role_doc['rbac_profile_id'],
                        'targeted_id': new_perm_tar_role_doc['targeted_id']
                    },
                    user=user_details, request=request,
                    update_data=new_perm_tar_role_doc)

            # Invalidate the application cache (L1 Redis + L2 user_app_store)
            # for every cache row + user computed for this profile.
            # Frontend-only path; the guard would suppress these calls
            # during a seed run anyway.
            try:
                from app.modules.core.services.user_app_store.user_app_store_service import (
                    UserAppStoreService,
                )
                from app.modules.core.models.sys_user.sys_user_model import (
                    SysUserModel,
                )

                # L2: bulk-mark cache rows stale for this profile.
                invalidated = await UserAppStoreService.mark_profile_stale(
                    validator_data.rbac_profile_id
                )

                # L1: sweep Redis keys for users in this profile.
                profile_oid = ObjectId(str(validator_data.rbac_profile_id))
                user_ids = await SysUserModel.find(
                    {"rbac_profile_id": profile_oid}, fetch_links=False,
                ).distinct("_id")
                l1_deleted = await self._invalidate_l1_for_user_ids(user_ids)

                # If the profile is a STATIC one (visitor / customer),
                # also invalidate the static rows keyed by profile_flag.
                profile_flag = (profil_info or {}).get("flag")
                static_invalidated = 0
                if profile_flag and UserAppStoreService.is_static_profile_flag(profile_flag):
                    static_invalidated = await UserAppStoreService.mark_static_profile_flag_stale(profile_flag)

                self.app_debug_print(
                    f"[update_org_profil_permissions] profile={validator_data.rbac_profile_id} "
                    f"users={len(user_ids)} L2_marked={invalidated} "
                    f"L2_static_marked={static_invalidated} L1_deleted={l1_deleted}",
                    True,
                )
            except Exception as cache_err:
                self.app_debug_print(
                    f"[update_org_profil_permissions] cache invalidation failed (non-fatal): {cache_err}",
                    True,
                )

        except Exception as e:
            self.app_debug_print(f"Error in _update_org_profil_permissions_background: {str(e)}",True)
            return False

    async def org_upsert_profile_permissions(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        body: Dict[str, Any]
    ):
        try:
            self.app_debug_print(
                f" \n\n\n update_org_role_permissions : {body} \n\n\n", False)
            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message', None)
            # sudo_can_proceed = sudo_action.get('can_proceed', True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_400_BAD_REQUEST,
            #         content={
            #             "status_code": status.HTTP_400_BAD_REQUEST,
            #             "message": sudo_message,
            #         }
            #     )

            user_details = await self.get_user_info(request, self.accept_language)
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)

            self.app_debug_print(f" \n\n\n body : {body} \n\n\n", False)
            validator_data = ProfilPermissionCreate.model_validate(
                body, context={"language": self.accept_language})
            self.app_debug_print(
                f" \n\n\n validator_data : {validator_data} \n\n\n", False)

            profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id": validator_data.rbac_profile_id,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )
            if not profil_info:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # PROCESS CONTINUE IN BACKGROUND
            asyncio.create_task(
                self._update_org_profil_permissions_background(
                    validator_data=validator_data,
                    user_details=user_details,
                    profil_info=profil_info
                )
            )

            message = self.get_response_message(
                MessageCategory.SUCCESS, "DATA_UPDATE_CONTINUED_IN_BACKGROUND", self.accept_language)
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
            self.app_debug_print(f" \n\n Exception: {e}\n\n", True)
            raise HTTPException(status_code=500, detail=str(e))


    async def _update_extended_org_profil_permissions_background(
        self,
        validator_data: ProfilPermissionCreate,
        user_details: Dict[str, Any],
        profil_info: Dict[str, Any]
    ):
        try:
            # ADD NEW RBAC PERMISSION ROLES
            for permission_id in validator_data.rbac_permissions:
                new_perm_tar_role_doc = {
                    "rbac_profile_id": validator_data.rbac_profile_id,
                    "targeted_id": permission_id,
                }
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL.value,
                    filter_data={
                        "rbac_profile_id": new_perm_tar_role_doc['rbac_profile_id'],
                        'targeted_id': new_perm_tar_role_doc['targeted_id']
                    },
                    user=user_details, request=request,
                    update_data=new_perm_tar_role_doc)

            # Same dual-cache invalidation as the non-extended path:
            # L1 Redis keys swept per-user, L2 user_app_store rows flipped
            # stale by profile (and by flag if static).
            try:
                from app.modules.core.services.user_app_store.user_app_store_service import (
                    UserAppStoreService,
                )
                from app.modules.core.models.sys_user.sys_user_model import (
                    SysUserModel,
                )

                invalidated = await UserAppStoreService.mark_profile_stale(
                    validator_data.rbac_profile_id
                )

                profile_oid = ObjectId(str(validator_data.rbac_profile_id))
                user_ids = await SysUserModel.find(
                    {"rbac_profile_id": profile_oid}, fetch_links=False,
                ).distinct("_id")
                l1_deleted = await self._invalidate_l1_for_user_ids(user_ids)

                profile_flag = (profil_info or {}).get("flag")
                static_invalidated = 0
                if profile_flag and UserAppStoreService.is_static_profile_flag(profile_flag):
                    static_invalidated = await UserAppStoreService.mark_static_profile_flag_stale(profile_flag)

                self.app_debug_print(
                    f"[update_extended_org_profil_permissions] profile={validator_data.rbac_profile_id} "
                    f"users={len(user_ids)} L2_marked={invalidated} "
                    f"L2_static_marked={static_invalidated} L1_deleted={l1_deleted}",
                    True,
                )
            except Exception as cache_err:
                self.app_debug_print(
                    f"[update_extended_org_profil_permissions] cache invalidation failed (non-fatal): {cache_err}",
                    True,
                )
            return True
        except Exception as e:
            self.app_debug_print(f"Error in _update_extended_org_profil_permissions_background: {str(e)}",True)
            return False
    async def org_upsert_extended_profile_permissions(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        body: Dict[str, Any]
    ):
        try:
            self.app_debug_print(
                f" \n\n\n update_org_role_permissions : {body} \n\n\n", False)
            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message', None)
            # sudo_can_proceed = sudo_action.get('can_proceed', True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #         status_code=status.HTTP_400_BAD_REQUEST,
            #         content={
            #             "status_code": status.HTTP_400_BAD_REQUEST,
            #             "message": sudo_message,
            #         }
            #     )

            user_details = await self.get_user_info(request, self.accept_language)
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request, accept_language=self.accept_language)
            user_profil = await self.get_user_profil(request=request, accept_language=self.accept_language)

            self.app_debug_print(f" \n\n\n body : {body} \n\n\n", False)
            validator_data = ProfilPermissionCreate.model_validate(
                body, context={"language": self.accept_language})
            self.app_debug_print(
                f" \n\n\n validator_data : {validator_data} \n\n\n", False)

            profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter___id": validator_data.rbac_profile_id,
                },
                user=user_details,
            )
            if not profil_info:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # CONTINUE IN BACKGROUND
            asyncio.create_task(
                self._update_extended_org_profil_permissions_background(
                    validator_data=validator_data,
                    user_details=user_details,
                    profil_info=profil_info
                )
            )

            message = self.get_response_message(
                MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
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
            self.app_debug_print(f" \n\n Exception: {e}\n\n", True)
            raise HTTPException(status_code=500, detail=str(e))
        

    async def _org_add_role_data_background(
        self,
        data: Dict[str, Any],
        user_details: Dict[str, Any],
        organization_profil: Dict[str, Any]
    ):
        try:
            body_profil_id = data.get(
                'rbac_profile_id', organization_profil['id'])
            data_role = {
                **data,
                "sys_organization_id": user_details['sys_organization_id'],
                "rbac_profile_id": body_profil_id
            }
            # Add data to the collection
            org_admin_role_id = await self.generic_service.add_data_to_collection(CollectionKey.RBAC_ROLE, data_role, user=user_details)
            # ADD ALL DEFAULT PERMISSIONS
            rbac_role_service = RbacRoleService(self.accept_language)
            await rbac_role_service.create_single_rbac_default_role_permissions(rbac_role_id=org_admin_role_id, body_profil_id=body_profil_id)

            return True
        except Exception as e:
            self.app_debug_print(f"Error in _org_add_role_data_background: {str(e)}",True)
            return False

    async def org_add_role_data(self, request: Request,background_tasks: BackgroundTasks, data: Dict[str, Any]):
        """
        Endpoint to add a new role from organization.
        """
        try:
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request, self.accept_language)
            api_Consumer = await self.get_api_consumer(request, self.accept_language)
            user_profil = await self.get_user_profil(request, self.accept_language)

            self.app_debug_print(f"\n\nbody role > : {data}\n\n", True)

            agent_organization = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter___id": user_details['sys_organization_id'],
                },
                user=user_details,
            )
            if not agent_organization:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "AGENT_ORGANIZATION_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            api_consumer_id = api_Consumer['id']
            organization_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter___id": agent_organization['rbac_profile_id'],
                },
                user=user_details,
            )
            if not organization_profil:
                message = self.get_response_message(
                    MessageCategory.NOT_FOUND, "ORGANIZATION_PROFIL_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            

            # PROCESS CONTINUE IN BACKGROUND
            asyncio.create_task(
                self._org_add_role_data_background(
                    data=data,
                    user_details=user_details,
                    organization_profil=organization_profil
                )
            )

            
            message = self.get_response_message(
                MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "status_code": status.HTTP_201_CREATED,
                    "message": message,
                    "data": None
                }
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        

    async def _org_delete_role_data_background(
        self,
        item_id: str
    ):
        try:
            # DELETE ALL PERMISSION ROLES
            rbac_role_service = RbacRoleService(self.accept_language)
            await rbac_role_service.delete_single_rbac_role_permissions(rbac_role_id=item_id, generic_service=self.generic_service)

            # Soft delete the document
            success = await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_ROLE, item_id)
            return True
        except Exception as e:
            self.app_debug_print(f"Error in _org_delete_role_data_background: {str(e)}",True)
            return False

    async def org_delete_role_data(self, request: Request,background_tasks: BackgroundTasks):
        """
        Endpoint to add a new role from organization.
        """
        try:
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request, self.accept_language)
            api_Consumer = await self.get_api_consumer(request, self.accept_language)
            user_profil = await self.get_user_profil(request, self.accept_language)

            item_id = request.query_params.get('item_id', None)
            if not item_id:
                message = self.get_response_message(
                    MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            rbac_role = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter___id": item_id,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
                user=user_details,
            )
            if not rbac_role:
                message = self.get_response_message(
                    MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            if rbac_role.get('system_reserved_actions', False) or rbac_role.get('is_default', False):
                message = self.get_response_message(
                    MessageCategory.EXCEPTIONS, "CANT_DELETE_RESERVED_OR_DEFAULT_ROLE", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # PROCESS CONTINUE IN BACKGROUND
            asyncio.create_task(
                self._org_delete_role_data_background(
                    item_id=item_id
                )
            )
            message = self.get_response_message(
                MessageCategory.SUCCESS, "DATA_DELETE_CONTINUED_IN_BACKGROUND", self.accept_language)
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
            self.app_debug_print(f"\n\n\n ERROR 2 : {e} \n\n\n", True)
            raise HTTPException(status_code=500, detail=str(e))

    async def mark_all_notifications_read(self, request: Request):
        """Bulk-flip every NTF_NOTIFICATION targeted to the caller to read.

        Owner-only by construction (filter scoped to ``targeted_id``). Uses
        a single ``update_many`` for cheapness — typical inboxes have at
        most a few hundred unread rows.
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            if not user_details or not user_details.get("id"):
                raise HTTPException(status_code=401, detail="User session not found.")
            user_id = str(user_details["id"])

            # Lazy import — avoids loading the model at module init.
            from app.modules.core.models.ntf_notification.ntf_notification_model import (
                NtfNotificationModel,
            )

            try:
                pid = PydanticObjectId(user_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid user id.")

            result = await NtfNotificationModel.find(
                {"targeted_id": pid, "is_read": False},
                fetch_links=False,
            ).update({"$set": {"is_read": True}})

            updated = int(getattr(result, "modified_count", 0) or 0)

            # Multi-device sync: push a `notification:all_read` event to
            # every connection this user has open so other tabs / devices
            # zero their badge instantly. Skipped when nothing changed.
            if updated > 0:
                await self._push_event_to_user(
                    user_id=user_id,
                    event="notification:all_read",
                    message={"updated": updated},
                )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Notifications marked as read.",
                    "data": {"updated": updated},
                },
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"Error in mark_all_notifications_read: {e}", True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    async def mark_notification_read(self, request: Request, notification_id: str):
        """Flip one notification's ``is_read`` to True. Owner-only.

        Owner check: the update query filters on ``targeted_id == caller``
        so a non-owner's PATCH simply matches zero rows and returns
        ``updated: 0``.
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            if not user_details or not user_details.get("id"):
                raise HTTPException(status_code=401, detail="User session not found.")
            user_id = str(user_details["id"])

            from app.modules.core.models.ntf_notification.ntf_notification_model import (
                NtfNotificationModel,
            )

            try:
                user_pid = PydanticObjectId(user_id)
                notif_pid = PydanticObjectId(notification_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid id.")

            result = await NtfNotificationModel.find(
                {
                    "_id": notif_pid,
                    "targeted_id": user_pid,
                    "is_read": False,
                },
                fetch_links=False,
            ).update({"$set": {"is_read": True}})

            updated = int(getattr(result, "modified_count", 0) or 0)

            # Multi-device sync: tell every connection this user has open
            # which notification was read so peer devices can drop the
            # badge count + refresh their list. Skipped on no-op (already
            # read or wrong owner — nothing for peers to mirror).
            if updated > 0:
                await self._push_event_to_user(
                    user_id=user_id,
                    event="notification:read",
                    message={
                        "notification_id": str(notification_id),
                        "updated": updated,
                    },
                )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Notification marked as read." if updated else "No change.",
                    "data": {"updated": updated},
                },
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"Error in mark_notification_read: {e}", True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    async def run_formated_applications_core(
        self,
        user_details: dict,
        api_Consumer: dict,
        user_profil: dict,
        output_data_type=None,
        all_data: bool = False,
        page: int = 0,
        limit: int = 50,
        application_group_flag: str = None,
        sse_key: Optional[str] = None,
    ) -> dict:
        """Headless core of fetch_formated_applications.

        Pure compute: runs the saas-config check, RBAC pipeline aggregation,
        per-app formatting, and returns the response_data dict. NO auth, NO
        cache I/O, NO HTTP wrapping — those belong to the wrapper.

        Used by:
          - ``fetch_formated_applications`` (live HTTP endpoint) on cache miss.
          - ``user_app_store_dynamic_seed_service`` to pre-warm per-user cache
            rows during seed runs.

        All RBAC inputs (``user_details`` / ``api_Consumer`` / ``user_profil``)
        must already be resolved by the caller.
        """
        from app.modules.core.enums.type_enum import OutputDataType, EAppGroupFlag
        if output_data_type is None:
            output_data_type = OutputDataType.DEFAULT
        if application_group_flag is None:
            application_group_flag = EAppGroupFlag.COMMON.value
        # Local timing baselines for diagnostic logs that live inside the body.
        method_start_time = time.time()

        try:
            async def publish_progress(payload: Dict[str, Any]) -> None:
                if sse_key:
                    await SenatDigitAppsSseService.publish(sse_key, payload)

            # Start database operations timing
            db_fetch_start = time.time()
            self.app_debug_print(f"\n\n user_profil :{user_profil}\n\n", True)
            self.app_debug_print(f"\n\n user_details :{user_details}\n\n", True)
            self.app_debug_print(f"\n\n api_Consumer :{api_Consumer}\n\n", True)

            saas_config_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                },
                user=user_details,
            )

            if not saas_config_info:
                message = self.get_response_message(
                    MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                ) 
            await publish_progress({
                "event": "resolving_permissions",
                "message": "Chargement des autorisations…",
                "percent": 15,
            })
            app_pipeline = [
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
                    "$lookup": {
                        "from": f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                        "localField": "_id",
                        "foreignField": "targeted_id",
                        "as": "unwind__rbac_restricted_profil"
                    }
                },
                {
                    "$unwind": {
                        "path": "$unwind__rbac_restricted_profil",
                        "preserveNullAndEmptyArrays": True
                    }
                },
                {
                    "$match": {
                        "unwind__rbac_restricted_profil.rbac_profile_id": ObjectId(user_profil['id']),
                        "unwind__rbac_restricted_api_consumer.ref_api_consumer_id": ObjectId(api_Consumer['id']),
                        "unwind__rbac_restricted_profil.is_hidden": False,
                        "unwind__rbac_restricted_api_consumer.is_hidden": False,
                        "application_group_flag":application_group_flag,
                        "is_activated": True,
                    }
                },
                {
                    "$group": {
                        "_id": "$_id",
                        "docs": {"$push": {
                            "_id": "$_id",
                            "order_by": "$order_by",
                            "application_group_flag": "$application_group_flag",
                            "flag": "$flag",
                            "name": "$name",
                                    "is_standalone": "$is_standalone",
                                    "description_str": "$description_str",
                        }}
                    }
                },
                {
                    "$project": {
                        "merged": {
                            "$reduce": {
                                "input": "$docs",
                                "initialValue": {},
                                "in": {"$mergeObjects": ["$$value", "$$this"]}
                            }
                        }
                    }
                },
                {
                    "$replaceRoot": {"newRoot": "$merged"}
                },
                {
                    "$sort": {
                        "order_by": 1
                    }
                },
                {
                    "$skip": limit * page
                },
                {
                    "$limit": limit
                }
            ]
            
            self.app_debug_print(
                f"-> apps  app_pipeline >> : {app_pipeline}", False)
            force_include_fields = ['_id', 'order_by', 'name', 'description_str']

            applications = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.SYS_APPLICATION,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                pipeline=app_pipeline,
                force_include_fields=force_include_fields
            )
            self.app_debug_print(
                f" \n\n applications : {len(applications)} \n\n", True)
            await publish_progress({
                "event": "applications_discovered",
                "message": "Chargement des menus…",
                "percent": 30,
                "applications_length": len(applications),
                "applications": [
                    {
                        "id": str(app.get("id", "")),
                        "flag": app.get("flag"),
                        "name": app.get("name"),
                    }
                    for app in applications
                ],
            })

            formatted_data = []
            for index, apps in enumerate(applications):
                self.app_debug_print(f"-> apps >> : {apps}", False)
                # continue
                # getch icon
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    targeted_id = apps['id']['display_value']
                    order_by = apps['order_by']['display_value']
                elif output_data_type == OutputDataType.DEFAULT.value:
                    targeted_id = apps['id']
                    order_by = apps['order_by']
                elif output_data_type == OutputDataType.TREE.value:
                    targeted_id = apps['id']
                    order_by = index
                else:
                    targeted_id: None
                    order_by = index
                self.app_debug_print(f"-> apps >> : targeted_id : {targeted_id}", True)
                # queries = {
                #     "filter__targeted_id":targeted_id,
                #     "filter__ref_api_consumer_id":api_Consumer['id']
                # }
                if index == 0:
                    self.app_debug_print(
                        f"output_data_type : {output_data_type}", True)
                rbac_path_guard_pipeline = [
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
                            # "unwind__rbac_restricted_profil.rbac_profile_id":ObjectId(user_profil['id']),
                            "unwind__rbac_restricted_api_consumer.ref_api_consumer_id": ObjectId(api_Consumer['id']),
                            # "unwind__rbac_restricted_profil.is_hidden":False,
                            "unwind__rbac_restricted_api_consumer.is_hidden": False
                        }
                    },
                    {
                        "$project": {
                            "_id": "$_id",
                            "targeted_id": 1,
                            "path": 1,
                            "path_guard": 1,
                        }
                    }
                ]
                rbac_path_guard = await self.generic_service.fetch_native_aggregate_one_from_collection(
                    collection_key=CollectionKey.RBAC_PATH_GUARD,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    pipeline=rbac_path_guard_pipeline
                )
                self.app_debug_print(
                    f" \n\n rbac_path_guard : {'Yes' if rbac_path_guard else 'No'} \n\n", True)
                # if not rbac_path_guard : continue

                single_app_profil = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=self.accept_language,
                    query={
                        "filter__targeted_id": targeted_id,
                    },
                    user=user_details,
                )
                single_app_api_consumer = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=self.accept_language,
                    query={
                        "filter__targeted_id": targeted_id,
                    },
                    user=user_details,
                )
                is_hidden = True
                is_activated = False
                self.app_debug_print(
                    f"\n\n\n\ single_app_api_consumer : {single_app_api_consumer}\n\n\n\n")
                self.app_debug_print(
                    f"\n\n\n\ single_app_profil : {single_app_profil}\n\n\n\n")
                if single_app_profil and single_app_api_consumer:
                    profil_is_hidden = single_app_profil['is_hidden']
                    profil_is_activated = single_app_profil['is_activated']

                    api_consumer_is_hidden = single_app_api_consumer['is_hidden']
                    api_consumer_is_activated = single_app_api_consumer['is_activated']

                    if profil_is_hidden == False and api_consumer_is_hidden == False:
                        is_hidden = False

                    if profil_is_activated == True and api_consumer_is_activated == True:
                        is_activated = True

                # DOUBLE CHECK
                start_time = time.time()
                double_check_pipeline = [
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                            'localField': 'rbac_permission_id',
                            'foreignField': '_id',
                            'as': 'permissions'
                        }
                    }, {
                        '$unwind': '$permissions'
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                            'let': {
                                'permissionId': '$permissions._id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$and': [
                                                {
                                                    '$eq': [
                                                        '$rbac_permission_id', '$$permissionId'
                                                    ]
                                                }, {
                                                    '$eq': [
                                                        '$sys_user_id', ObjectId(
                                                            user_details['id'])
                                                    ]
                                                }, {
                                                    '$eq': [
                                                        '$status', 'added'
                                                    ]
                                                }
                                            ]
                                        }
                                    }
                                }
                            ],
                            'as': 'direct_privileges'
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                            'localField': 'permissions._id',
                            'foreignField': 'rbac_permission_id',
                            'as': 'permission_targets'
                        }
                    }, {
                        '$unwind': {
                            'path': '$permission_targets',
                            'preserveNullAndEmptyArrays': True
                        }
                    }, {
                        '$lookup': {
                            'from': 'sys_application',
                            'localField': 'permission_targets.targeted_id',
                            'foreignField': '_id',
                            'as': 'applications'
                        }
                    }, {
                        '$unwind': {
                            'path': '$applications',
                            'preserveNullAndEmptyArrays': True
                        }
                    }, {
                        '$match': {
                            'applications._id': ObjectId(str(targeted_id))
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                            'let': {
                                'app_id': '$applications._id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$targeted_id', '$$app_id'
                                            ]
                                        }
                                    }
                                }, {
                                    '$match': {
                                        'ref_api_consumer_id': ObjectId(api_Consumer['id'])
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'is_hidden': 1,
                                        'is_activated': 1,
                                        'ref_api_consumer_id': 1
                                    }
                                }
                            ],
                            'as': 'api_consumers'
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                            'let': {
                                'app_id': '$applications._id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$targeted_id', '$$app_id'
                                            ]
                                        }
                                    }
                                }, {
                                    '$match': {
                                        'rbac_profile_id': ObjectId(user_profil['id'])
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'is_hidden': 1,
                                        'is_activated': 1,
                                        'rbac_profile_id': 1
                                    }
                                }
                            ],
                            'as': 'profiles'
                        }
                    }, {
                        '$match': {
                            '$or': [
                                {
                                    'rbac_role_id': ObjectId(user_details['rbac_role_id']),
                                    'api_consumers': {
                                        '$ne': []
                                    },
                                    'profiles': {
                                        '$ne': []
                                    },
                                    'permissions._id': {
                                        '$exists': True
                                    }
                                }, {
                                    'direct_privileges': {
                                        '$ne': []
                                    },
                                    'api_consumers': {
                                        '$ne': []
                                    },
                                    'profiles': {
                                        '$ne': []
                                    }
                                }
                            ]
                        }
                    }, {
                        '$group': {
                            '_id': '$applications._id',
                            'result': {
                                '$first': {
                                    '_id': '$_id',
                                    'rbac_role_id': '$rbac_role_id',
                                    'rbac_permission_id': '$rbac_permission_id',
                                    'rbac_restricted_api_consumer': {
                                        '$arrayElemAt': [
                                            '$api_consumers', 0
                                        ]
                                    },
                                    'rbac_restricted_profil': {
                                        '$arrayElemAt': [
                                            '$profiles', 0
                                        ]
                                    },
                                    'has_privilege': {
                                        '$gt': [
                                            {
                                                '$size': '$direct_privileges'
                                            }, 0
                                        ]
                                    }
                                }
                            }
                        }
                    }, {
                        '$replaceRoot': {
                            'newRoot': '$result'
                        }
                    }
                ]

               
                double_check_info = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=self.accept_language,
                    pipeline=double_check_pipeline
                )
                self.app_debug_print(
                    f"\n\n\n\ double_check_info : {len(double_check_info)}\n\n\n\n")
                self.app_debug_print(
                    f"\n\n\n\ time : {time.time() - start_time}\n\n\n\n")
                # # break
                if double_check_info and len(double_check_info) > 0:
                    single_info = double_check_info[0]
                    if 'rbac_restricted_profil' in single_info:
                        restricted_profil = single_info['rbac_restricted_profil']
                        if restricted_profil['is_locked'] == True or restricted_profil['is_activated'] == False:
                            is_activated = False

                    if 'rbac_restricted_profil' in single_info:
                        restricted_profil = single_info['rbac_restricted_profil']
                        if restricted_profil['is_hidden'] == False:
                            is_hidden = False

                    if 'rbac_restricted_api_consumer' in single_info:
                        restricted_api_consumer = single_info['rbac_restricted_api_consumer']
                        if restricted_api_consumer['is_locked'] == True or restricted_api_consumer['is_activated'] == False:
                            is_activated = False

                    if 'rbac_restricted_api_consumer' in single_info:
                        if restricted_api_consumer['is_hidden'] == False:
                            is_hidden = False
                else:
                    is_activated = False

                # # SKIP IF HIDDEN
                if is_hidden:
                    continue

                # CHILDREN DISPLAY TYPE
                children_display_type_pipeline = [
                    {
                        '$match': {
                            'targeted_id': ObjectId(targeted_id)
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                            'let': {
                                'target_id': '$_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$targeted_id', '$$target_id'
                                            ]
                                        },
                                        'ref_api_consumer_id': ObjectId(api_Consumer["id"]),
                                        'is_hidden': False
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'targeted_id': 1,
                                        'ref_api_consumer_id': 1
                                    }
                                }
                            ],
                            'as': 'api_consumers'
                        }
                    }, {
                        '$match': {
                            'api_consumers': {
                                '$ne': []
                            }
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                            'let': {
                                'target_id': '$_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$targeted_id', '$$target_id'
                                            ]
                                        },
                                        'rbac_profile_id': ObjectId(user_profil['id']),
                                        'is_hidden': False
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'targeted_id': 1,
                                        'rbac_profile_id': 1
                                    }
                                }
                            ],
                            'as': 'profiles'
                        }
                    }, {
                        '$match': {
                            'profiles': {
                                '$ne': []
                            }
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.SYS_APPLICATION.model_name}",
                            'let': {
                                'target_id': '$targeted_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$_id', '$$target_id'
                                            ]
                                        }
                                    }
                                }, {
                                    '$lookup': {
                                        'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                                        'let': {
                                            'app_id': '$_id'
                                        },
                                        'pipeline': [
                                            {
                                                '$match': {
                                                    '$expr': {
                                                        '$eq': [
                                                            '$targeted_id', '$$app_id'
                                                        ]
                                                    },
                                                    'ref_api_consumer_id': ObjectId(api_Consumer["id"])
                                                }
                                            }
                                        ],
                                        'as': 'app_consumers'
                                    }
                                }, {
                                    '$lookup': {
                                        'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                                        'let': {
                                            'app_id': '$_id'
                                        },
                                        'pipeline': [
                                            {
                                                '$match': {
                                                    '$expr': {
                                                        '$eq': [
                                                            '$targeted_id', '$$app_id'
                                                        ]
                                                    },
                                                    'rbac_profile_id': ObjectId(user_profil["id"])
                                                }
                                            }
                                        ],
                                        'as': 'app_profiles'
                                    }
                                }, {
                                    '$match': {
                                        'app_consumers': {
                                            '$ne': []
                                        },
                                        'app_profiles': {
                                            '$ne': []
                                        }
                                    }
                                }
                            ],
                            'as': 'applications'
                        }
                    }, {
                        '$match': {
                            'applications': {
                                '$ne': []
                            }
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.REF_CHILDREN_DISPLAY_TYPE.model_name}",
                            'let': {
                                'children_display_type_id': '$ref_children_display_type_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$_id', '$$children_display_type_id'
                                            ]
                                        }
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'url': 1,
                                        'label': 1,
                                        'flag': 1
                                    }
                                }
                            ],
                            'as': 'children_display_types'
                        }
                    }, {
                        '$unwind': {
                            'path': '$children_display_types',
                            'preserveNullAndEmptyArrays': False
                        }
                    }, {
                        '$sort': {
                            'order_by': 1
                        }
                    }, {
                        '$project': {
                            '_id': 1,
                            'targeted_id': 1,
                            'ref_children_display_type_id': 1,
                            'unwind__ref_children_display_type': {
                                '_id': '$children_display_types._id',
                                'label': '$children_display_types.label',
                                'flag': '$children_display_types.flag'
                            }
                        }
                    }
                ]
                children_display_types = []
                children_display_types = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.CFG_CHILDREN_DISPLAY_TYPE,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=self.accept_language,
                    pipeline=children_display_type_pipeline
                )
                self.app_debug_print(
                    f"\n\n\n\ children_display_types : {len(children_display_types)}\n\n\n\n")

                ref_children_display_type_info = children_display_types[0] if len(
                    children_display_types) > 0 else None
                # DATA DISPLAY TYPE
                data_display_type_pipeline = [
                    {
                        '$match': {
                            'targeted_id': ObjectId(targeted_id)
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                            'let': {
                                'target_id': '$_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$targeted_id', '$$target_id'
                                            ]
                                        },
                                        'ref_api_consumer_id': ObjectId(api_Consumer["id"]),
                                        'is_hidden': False
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'targeted_id': 1,
                                        'ref_api_consumer_id': 1
                                    }
                                }
                            ],
                            'as': 'api_consumers'
                        }
                    }, {
                        '$match': {
                            'api_consumers': {
                                '$ne': []
                            }
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                            'let': {
                                'target_id': '$_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$targeted_id', '$$target_id'
                                            ]
                                        },
                                        'rbac_profile_id': ObjectId(user_profil["id"]),
                                        'is_hidden': False
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'targeted_id': 1,
                                        'rbac_profile_id': 1
                                    }
                                }
                            ],
                            'as': 'profiles'
                        }
                    }, {
                        '$match': {
                            'profiles': {
                                '$ne': []
                            }
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.SYS_APPLICATION.model_name}",
                            'let': {
                                'target_id': '$targeted_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$and': [
                                                {
                                                    '$eq': [
                                                        '$_id', '$$target_id'
                                                    ]
                                                }, {
                                                    '$eq': [
                                                        '$_id', ObjectId(
                                                            targeted_id)
                                                    ]
                                                }
                                            ]
                                        }
                                    }
                                }, {
                                    '$lookup': {
                                        'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                                        'let': {
                                            'app_id': '$_id'
                                        },
                                        'pipeline': [
                                            {
                                                '$match': {
                                                    '$expr': {
                                                        '$eq': [
                                                            '$targeted_id', '$$app_id'
                                                        ]
                                                    },
                                                    'ref_api_consumer_id': ObjectId(api_Consumer["id"])
                                                }
                                            }
                                        ],
                                        'as': 'app_consumers'
                                    }
                                }, {
                                    '$lookup': {
                                        'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                                        'let': {
                                            'app_id': '$_id'
                                        },
                                        'pipeline': [
                                            {
                                                '$match': {
                                                    '$expr': {
                                                        '$eq': [
                                                            '$targeted_id', '$$app_id'
                                                        ]
                                                    },
                                                    'rbac_profile_id': ObjectId(user_profil["id"])
                                                }
                                            }
                                        ],
                                        'as': 'app_profiles'
                                    }
                                }, {
                                    '$match': {
                                        'app_consumers': {
                                            '$ne': []
                                        },
                                        'app_profiles': {
                                            '$ne': []
                                        }
                                    }
                                }
                            ],
                            'as': 'apps'
                        }
                    }, {
                        '$match': {
                            'apps': {
                                '$ne': []
                            }
                        }
                    }, {
                        '$lookup': {
                            'from':f"{CollectionKey.REF_DATA_DISPLAY_TYPE.model_name}",
                            'let': {
                                'data_display_type_id': '$ref_data_display_type_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$_id', '$$data_display_type_id'
                                            ]
                                        }
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'url': 1,
                                        'label': 1,
                                        'flag': 1
                                    }
                                }
                            ],
                            'as': 'data_display_types'
                        }
                    }, {
                        '$unwind': {
                            'path': '$data_display_types',
                            'preserveNullAndEmptyArrays': False
                        }
                    }, {
                        '$sort': {
                            'order_by': 1
                        }
                    }, {
                        '$project': {
                            '_id': 1,
                            'targeted_id': 1,
                            'ref_data_display_type_id': 1,
                            'unwind__ref_data_display_type': {
                                '_id': '$data_display_types._id',
                                'label': '$data_display_types.label',
                                'flag': '$data_display_types.flag'
                            }
                        }
                    }
                ]
                data_display_types = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.CFG_DATA_DISPLAY_TYPE,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=self.accept_language,
                    pipeline=data_display_type_pipeline
                )
                ref_data_display_type_info = data_display_types[0] if len(
                    data_display_types) > 0 else None

                # COLLECTION CRUD INFO
                collection_crud_info_pipeline = [
                    {
                        '$match': {
                            'targeted_id': ObjectId(targeted_id)
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                            'let': {
                                'target_id': '$_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$targeted_id', '$$target_id'
                                            ]
                                        },
                                        'ref_api_consumer_id': ObjectId(api_Consumer["id"]),
                                        'is_hidden': False
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'targeted_id': 1,
                                        'ref_api_consumer_id': 1
                                    }
                                }
                            ],
                            'as': 'api_consumers'
                        }
                    }, {
                        '$match': {
                            'api_consumers': {
                                '$ne': []
                            }
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                            'let': {
                                'target_id': '$_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$targeted_id', '$$target_id'
                                            ]
                                        },
                                        'rbac_profile_id': ObjectId(user_profil["id"]),
                                        'is_hidden': False
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'targeted_id': 1,
                                        'rbac_profile_id': 1
                                    }
                                }
                            ],
                            'as': 'profiles'
                        }
                    }, {
                        '$match': {
                            'profiles': {
                                '$ne': []
                            }
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.SYS_APPLICATION.model_name}",
                            'let': {
                                'target_id': '$targeted_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$and': [
                                                {
                                                    '$eq': [
                                                        '$_id', '$$target_id'
                                                    ]
                                                }, {
                                                    '$eq': [
                                                        '$_id', ObjectId(
                                                            targeted_id)
                                                    ]
                                                }
                                            ]
                                        }
                                    }
                                }, {
                                    '$lookup': {
                                        'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                                        'let': {
                                            'app_id': '$_id'
                                        },
                                        'pipeline': [
                                            {
                                                '$match': {
                                                    '$expr': {
                                                        '$eq': [
                                                            '$targeted_id', '$$app_id'
                                                        ]
                                                    },
                                                    'ref_api_consumer_id': ObjectId(api_Consumer["id"])
                                                }
                                            }
                                        ],
                                        'as': 'app_consumers'
                                    }
                                }, {
                                    '$lookup': {
                                        'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                                        'let': {
                                            'app_id': '$_id'
                                        },
                                        'pipeline': [
                                            {
                                                '$match': {
                                                    '$expr': {
                                                        '$eq': [
                                                            '$targeted_id', '$$app_id'
                                                        ]
                                                    },
                                                    'rbac_profile_id': ObjectId(user_profil["id"])
                                                }
                                            }
                                        ],
                                        'as': 'menu_profiles'
                                    }
                                }, {
                                    '$match': {
                                        'app_consumers': {
                                            '$ne': []
                                        },
                                        'menu_profiles': {
                                            '$ne': []
                                        }
                                    }
                                }
                            ],
                            'as': 'apps'
                        }
                    }, {
                        '$match': {
                            'apps': {
                                '$ne': []
                            }
                        }
                    }, {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_ENDPOINT.model_name}",
                            'let': {
                                'endpoint_id': '$rbac_endpoint_id'
                            },
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$eq': [
                                                '$_id', '$$endpoint_id'
                                            ]
                                        }
                                    }
                                }, {
                                    '$project': {
                                        '_id': 1,
                                        'url': 1,
                                        'label': 1,
                                        'flag': 1,
                                        'is_sudo_action': 1,
                                        'is_sudo_group_action': 1,
                                        'is_sudo_delegated_action': 1,
                                        'is_sudo_group_cross_validation_action': 1,
                                        'is_sudo_group_inter_organization_validation_action': 1,
                                    }
                                }
                            ],
                            'as': 'endpoints'
                        }
                    }, {
                        '$unwind': {
                            'path': '$endpoints',
                            'preserveNullAndEmptyArrays': True
                        }
                    }, {
                        '$sort': {
                            'order_by': 1
                        }
                    }, {
                        '$project': {
                            '_id': 1,
                            'targeted_id': 1,
                            'rbac_endpoint_id': 1,
                            'flag': 1,
                            'hard_code_flag': 1,
                            'parent_field_name': 1,
                            "label": 1,
                            'unwind__rbac_endpoint': {
                                '_id': '$endpoints._id',
                                'url': '$endpoints.url',
                                'label': '$endpoints.label',
                                'flag': '$endpoints.flag',
                                "rbac_title_id": '$endpoints.rbac_title_id',
                                "is_sudo_action": '$endpoints.is_sudo_action',
                                "is_sudo_group_action": '$endpoints.is_sudo_group_action',
                                "is_sudo_delegated_action": '$endpoints.is_sudo_delegated_action',
                                "is_sudo_group_cross_validation_action": '$endpoints.is_sudo_group_cross_validation_action',
                                "is_sudo_group_inter_organization_validation_action": '$endpoints.is_sudo_group_inter_organization_validation_action',
                            }
                        }
                    }
                ]
                collection_crud_info = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.REF_COLLECTION_CRUD_INFO,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=collection_crud_info_pipeline,
                    all_data=True
                )
                rbac_path_guard_dict = rbac_path_guard if rbac_path_guard else {}

                # RBAC COMPONENTS
                rbac_components_pipeline = [
                    # // Lookup permission targets for components
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                            'localField': '_id',
                            'foreignField': 'rbac_component_id',
                            'as': 'unwind__rbac_permission_target'
                        }
                    },
                    {
                        '$unwind': '$unwind__rbac_permission_target'
                    },

                    # // Lookup permissions
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                            'localField': 'unwind__rbac_permission_target.rbac_permission_id',
                            'foreignField': '_id',
                            'as': 'unwind__rbac_permission'
                        }
                    },
                    {
                        '$unwind': '$unwind__rbac_permission'
                    },

                    # // Add privilege lookup
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                            'let': {'permissionId': '$unwind__rbac_permission._id'},
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$and': [
                                                {'$eq': ['$rbac_permission_id',
                                                        '$$permissionId']},
                                                {'$eq': ['$sys_user_id', ObjectId(
                                                    user_details['id'])]},
                                                {'$eq': ['$status', 'added']}
                                            ]
                                        }
                                    }
                                }
                            ],
                            'as': 'direct_privileges'
                        }
                    },

                    # // Lookup permission roles (for role-based access)
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION_ROLE.model_name}",
                            'localField': 'unwind__rbac_permission._id',
                            'foreignField': 'rbac_permission_id',
                            'as': 'unwind__rbac_permission_role'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_permission_role',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Lookup roles
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_ROLE.model_name}",
                            'localField': 'unwind__rbac_permission_role.rbac_role_id',
                            'foreignField': '_id',
                            'as': 'unwind__rbac_role'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_role',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Lookup application
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.SYS_APPLICATION.model_name}",
                            'localField': 'unwind__rbac_permission_target.targeted_id',
                            'foreignField': '_id',
                            'as': 'unwind__sys_application'
                        }
                    },
                    {
                        '$unwind': '$unwind__sys_application'
                    },

                    # // Lookup API consumer restrictions
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                            'localField': 'unwind__rbac_permission_target._id',
                            'foreignField': 'targeted_id',
                            'as': 'unwind__rbac_restricted_api_consumer'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_restricted_api_consumer',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Lookup profile restrictions
                    {
                        '$lookup': {
                            'from':f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                            'localField': 'unwind__rbac_permission_target._id',
                            'foreignField': 'targeted_id',
                            'as': 'unwind__rbac_restricted_profil'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_restricted_profil',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Final matching - handles both role-based and privilege-based access
                    {
                        '$match': {
                            '$and': [
                                # // Common requirements for both paths
                                {
                                    'unwind__sys_application._id': ObjectId(targeted_id),
                                    'unwind__rbac_restricted_profil.rbac_profile_id': ObjectId(user_profil['id']),
                                    'unwind__rbac_restricted_api_consumer.ref_api_consumer_id': ObjectId(api_Consumer['id'])
                                },
                                # // Either role or privilege must be valid
                                {
                                    '$or': [
                                        # // Role-based access path
                                        {
                                            'unwind__rbac_role._id': ObjectId(user_details["rbac_role_id"])
                                        },
                                        # // Privilege-based access path
                                        {
                                            'direct_privileges': {'$ne': []}
                                        }
                                    ]
                                }
                            ]
                        }
                    },

                    # // Project results
                    {
                        '$project': {
                            '_id': 1,
                            'is_standalone': 1,
                            'label': 1,
                            'flag': 1,
                            'hard_code_flag': 1,
                            'access_via': {
                                '$cond': [
                                    {'$gt': [{'$size': '$direct_privileges'}, 0]},
                                    'privilege',
                                    'role'
                                ]
                            }
                        }
                    }
                ]

                # RBAC ACTIONS
                rbac_actions_pipeline = [
                    # // Lookup permission targets
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                            'localField': '_id',
                            'foreignField': 'rbac_action_id',
                            'as': 'unwind__rbac_permission_target'
                        }
                    },
                    {
                        '$unwind': '$unwind__rbac_permission_target'
                    },

                    # // Lookup permissions
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                            'localField': 'unwind__rbac_permission_target.rbac_permission_id',
                            'foreignField': '_id',
                            'as': 'unwind__rbac_permission'
                        }
                    },
                    {
                        '$unwind': '$unwind__rbac_permission'
                    },
                    # // Add privilege lookup
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                            'let': {'permissionId': '$unwind__rbac_permission._id'},
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {
                                            '$and': [
                                                {'$eq': ['$rbac_permission_id',
                                                        '$$permissionId']},
                                                {'$eq': ['$sys_user_id', ObjectId(
                                                    user_details['id'])]},
                                                {'$eq': ['$status', 'added']}
                                            ]
                                        }
                                    }
                                }
                            ],
                            'as': 'direct_privileges'
                        }
                    },

                    # // Lookup permission roles (for role-based access)
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PERMISSION_ROLE.model_name}",
                            'localField': 'unwind__rbac_permission._id',
                            'foreignField': 'rbac_permission_id',
                            'as': 'unwind__rbac_permission_role'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_permission_role',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Lookup roles
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_ROLE.model_name}",
                            'localField': 'unwind__rbac_permission_role.rbac_role_id',
                            'foreignField': '_id',
                            'as': 'unwind__rbac_role'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_role',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Lookup application
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.SYS_APPLICATION.model_name}",
                            'localField': 'unwind__rbac_permission_target.targeted_id',
                            'foreignField': '_id',
                            'as': 'unwind__sys_application'
                        }
                    },
                    {
                        '$unwind': '$unwind__sys_application'
                    },

                    # // Lookup API consumer restrictions
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                            'localField': 'unwind__rbac_permission_target._id',
                            'foreignField': 'targeted_id',
                            'as': 'unwind__rbac_restricted_api_consumer'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_restricted_api_consumer',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Lookup profile restrictions
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                            'localField': 'unwind__rbac_permission_target._id',
                            'foreignField': 'targeted_id',
                            'as': 'unwind__rbac_restricted_profil'
                        }
                    },
                    {
                        '$unwind': {
                            'path': '$unwind__rbac_restricted_profil',
                            'preserveNullAndEmptyArrays': True
                        }
                    },

                    # // Final matching - handles both role-based and privilege-based access
                    {
                        '$match': {
                            '$and': [
                                # // Common requirements for both paths
                                {
                                    'unwind__sys_application._id': ObjectId(targeted_id),
                                    'unwind__rbac_restricted_profil.rbac_profile_id': ObjectId(user_profil['id']),
                                    'unwind__rbac_restricted_api_consumer.ref_api_consumer_id': ObjectId(api_Consumer['id'])
                                },
                                # // Either role or privilege must be valid
                                {
                                    '$or': [
                                        # // Role-based access path
                                        {
                                            'unwind__rbac_role._id': ObjectId(user_details['rbac_role_id'])
                                        },
                                        # // Privilege-based access path
                                        {
                                            'direct_privileges': {'$ne': []}
                                        }
                                    ]
                                }
                            ]
                        }
                    },

                    # // Project results
                    {
                        '$project': {
                            '_id': 1,
                            'is_standalone': 1,
                            'label': 1,
                            'flag': 1,
                            'hard_code_flag': 1,
                            'access_via': {
                                '$cond': [
                                    {'$gt': [{'$size': '$direct_privileges'}, 0]},
                                    'privilege',
                                    'role'
                                ]
                            }
                        }
                    }
                ]
                
                await publish_progress({
                    "event": "loading_actions",
                    "message": "Chargement des actions…",
                    "percent": 45,
                    "application_id": str(targeted_id),
                    "application_flag": extract_field_on_output_data_element(apps, 'flag', output_data_type),
                    "application_name": extract_field_on_output_data_element(apps, 'name', output_data_type),
                })
                formated_actions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_ACTION,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=rbac_actions_pipeline,
                    all_data=True
                )
                await publish_progress({
                    "event": "loading_components",
                    "message": "Chargement des composants…",
                    "percent": 60,
                    "application_id": str(targeted_id),
                    "application_flag": extract_field_on_output_data_element(apps, 'flag', output_data_type),
                    "application_name": extract_field_on_output_data_element(apps, 'name', output_data_type),
                })
                formated_components = await self.generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_COMPONENT,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    pipeline=rbac_components_pipeline,
                    all_data=True
                )
                sub_menus_list = []
                current_item = {
                    **apps,
                    'order_by': order_by,
                    'ishidden': is_hidden,
                    'isactivated': is_activated,
                    'ref_children_display_type': ref_children_display_type_info,
                    'ref_data_display_type': ref_data_display_type_info,
                    'collection_crud_info': collection_crud_info,

                    "rbac_actions": formated_actions,
                    "rbac_components": formated_components,

                    'rbac_path_guard': {
                        **rbac_path_guard_dict,
                    } if is_activated == True else {},
                    "sub_menus": sub_menus_list
                }
                formatted_data.append({
                    **current_item,
                })

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
                            "unwind__rbac_restricted_api_consumer.ref_api_consumer_id": ObjectId(api_Consumer['id']),
                        }
                    },
                    {
                        "$project": {
                            "id": "$_id",
                            "ref_icon_id": "$ref_icon_id",
                            "rbac_permission_id": "$rbac_permission_id",
                            "targeted_id": "$targeted_id",
                        }
                    }
                ]

                # START REDIS
                cache_app_icon_key = f"apps_icon_{targeted_id}_{user_details['id']}_{api_Consumer['id']}_{user_profil['id']}_{output_data_type}"
                # Cache expiration time in seconds (1 minutes)
                cache_app_icon_expiration = 60
                # Try to get data from cache first
                cached_app_icon_data = await AppRedisService.get_str_redis_value(cache_app_icon_key)

                nested_icon = {}

                
                if cached_app_icon_data:
                    
                    self.app_debug_print(
                        f"Returning cached app nested_icon data", True)
                    cached_app_icon_json = json.loads(cached_app_icon_data)
                    nested_icon = cached_app_icon_json
                else:
                    menu_or_app_flag = extract_field_on_output_data_element(apps, 'flag', output_data_type)
                    menu_or_app_path = extract_field_on_output_data_element(rbac_path_guard_dict, 'path', output_data_type)
                    api_consumer_flag = api_Consumer['flag']
                    nested_url_icon = SvgIconService.build_svg_icon_file_server_url(
                        menu_or_app_flag=menu_or_app_flag,
                        menu_or_app_path=menu_or_app_path,
                        api_consumer_flag=api_consumer_flag,
                    )

                    self.app_debug_print(f" \n\n nested_url_icon new version : {nested_url_icon} \n\n", True)

                    # Ensure first response (cache miss) still contains icon URL.
                    nested_icon = {
                        "icon_url": nested_url_icon
                    }

                    await AppRedisService.set_redis_value(
                        key=cache_app_icon_key,
                        value=json.dumps({
                            "icon_url": nested_url_icon
                        }),
                        expiry=cache_app_icon_expiration
                    )
                    #


                    # nested_icon = await self.generic_service.fetch_native_aggregate_one_from_collection(
                    #     collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
                    #     output_data_type=OutputDataType(output_data_type).value,
                    #     accept_language=self.accept_language,
                    #     pipeline=nested_icon_pipeline
                    # )
                    # # Convert to serializable format and cache the result with expiration
                    # serializable_nested_icon = self.convert_to_serializable(
                    #     nested_icon)
                    # await AppRedisService.set_redis_value(
                    #     key=cache_app_icon_key,
                    #     value=json.dumps(serializable_nested_icon),
                    #     expiry=cache_app_icon_expiration
                    # )
                index_of_menu = formatted_data.index(current_item)
                # Update the item at the found index
                formatted_data[index_of_menu] = {
                    **formatted_data[index_of_menu],
                    "icon": {
                        "icon": {
                            "display_value": nested_icon.get('icon_url', None)
                        }
                    }
                }

                # nested_icon = await self.generic_service.fetch_native_aggregate_one_from_collection(
                #     collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
                #     output_data_type=OutputDataType(output_data_type).value,
                #     accept_language=self.accept_language,
                #     pipeline=nested_icon_pipeline
                # )
                # self.app_debug_print(
                #     f" \n\n nested_icon : {'Yes' if nested_icon else 'No'} \n\n", True)
                # if nested_icon:
                #     if output_data_type == OutputDataType.DATA_TABLE.value:
                #         ref_icon_id = nested_icon['ref_icon_id']['display_value']
                #     elif output_data_type == OutputDataType.DEFAULT.value:
                #         ref_icon_id = nested_icon['id']
                #     elif output_data_type == OutputDataType.TREE.value:
                #         ref_icon_id = nested_icon['id']
                #     else:
                #         ref_icon_id: None

                #     icon_query = {
                #         "filter___id": ref_icon_id,
                #     }
                #     ref_icon = await self.generic_service.fetch_one_from_collection(
                #         collection_key=CollectionKey.REF_ICON,
                #         output_data_type=OutputDataType(output_data_type).value,
                #         accept_language=self.accept_language,
                #         query={
                #             **icon_query
                #         }
                #     )
                #     if ref_icon:
                #         # Assuming `menu` is an item in the `formatted_data` list
                #         index_of_menu = formatted_data.index(current_item)

                #         # Update the item at the found index
                #         formatted_data[index_of_menu] = {
                #             **formatted_data[index_of_menu],
                #             "icon": {
                #                 "icon": ref_icon['icon']
                #             }
                #         }
                #         # self.app_debug_print(f"\n\n index_of_app: {index_of_menu}\n\n",True)

                # Now, sort formatted_data by 'order_by' ascending:
                formatted_data.sort(key=lambda item: item['order_by'])

            # In compact mode, embed sub-menus for each application
            if settings.APP_MENU_FETCH_PARADIGM == "compact":
                await publish_progress({
                    "event": "loading_submenus",
                    "message": "Chargement des menus…",
                    "percent": 75,
                })
                formatted_data = await self._embed_compact_submenus(
                    formatted_data=formatted_data,
                    api_consumer=api_Consumer,
                    user_details=user_details,
                    user_profil=user_profil,
                    output_data_type=OutputDataType(output_data_type).value,
                    label="senat-digit-apps",
                    progress_callback=publish_progress if sse_key else None,
                )

            # Calculate database fetch time
            db_fetch_time = round((time.time() - db_fetch_start) * 1000, 2)
            total_method_time = round((time.time() - method_start_time) * 1000, 2)

            # Prepare response data
            response_data = {
                "status_code": status.HTTP_200_OK,
                "data": formatted_data,
                "app_menu_fetch_paradigm": settings.APP_MENU_FETCH_PARADIGM,
            }

            return response_data
        except Exception as e:
            self.app_debug_print(f"Error in run_formated_applications_core: {str(e)}", True)
            raise
