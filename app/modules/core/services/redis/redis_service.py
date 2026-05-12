from app.modules.core.utils.common.async_runner import AsyncExecutor
import redis
from typing import TypeVar, Type, Optional, Any
import json
from app.modules.core.configs.config import settings
import os


T = TypeVar("T")


class AppRedisService:
    def __init__(self, host='localhost', port=6379, db=0):
        pass  # Not needed; using static async Redis connections per method

    @staticmethod
    def get_env_prefix() -> str:
        env = settings.ENV.lower()
        return f"{env}_"

    @staticmethod
    async def set_redis_value(key: str, value: str, expiry: Optional[int] = None, use_env_prefix: bool = True):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url)
        prefixed_key = f"{AppRedisService.get_env_prefix()}{key}" if use_env_prefix else key

        try:
            if expiry:
                await AsyncExecutor.run_in_thread(redis_client.set, prefixed_key, value, ex=expiry)
            else:
                await AsyncExecutor.run_in_thread(redis_client.set, prefixed_key, value)
        finally:
            await AsyncExecutor.run_in_thread(redis_client.close)

    @staticmethod
    async def remove_redis_value(key: str, use_env_prefix: bool = True) -> bool:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url)
        prefixed_key = f"{AppRedisService.get_env_prefix()}{key}" if use_env_prefix else key

        try:
            result = await AsyncExecutor.run_in_thread(redis_client.delete, prefixed_key)
            return result > 0
        finally:
            await AsyncExecutor.run_in_thread(redis_client.close)

    @staticmethod
    async def get_str_redis_value(key: str, use_env_prefix: bool = True) -> Optional[str]:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url)
        prefixed_key = f"{AppRedisService.get_env_prefix()}{key}" if use_env_prefix else key

        try:
            value = await AsyncExecutor.run_in_thread(redis_client.get, prefixed_key)
            return value.decode() if value else None
        finally:
            await AsyncExecutor.run_in_thread(redis_client.close)

    @staticmethod
    async def get_obj_redis_value(key: str, obj_type: Type[T], use_env_prefix: bool = True) -> Optional[T]:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url)
        prefixed_key = f"{AppRedisService.get_env_prefix()}{key}" if use_env_prefix else key

        try:
            value = await AsyncExecutor.run_in_thread(redis_client.get, prefixed_key)
            if not value:
                return None
            return obj_type(**json.loads(value.decode()))
        finally:
            await AsyncExecutor.run_in_thread(redis_client.close)

    @staticmethod
    async def refresh_expiry(key: str, expiry: int, use_env_prefix: bool = True) -> bool:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url)
        prefixed_key = f"{AppRedisService.get_env_prefix()}{key}" if use_env_prefix else key

        try:
            exists = await AsyncExecutor.run_in_thread(redis_client.exists, prefixed_key)
            if exists:
                await AsyncExecutor.run_in_thread(redis_client.expire, prefixed_key, expiry)
                return True
            return False
        finally:
            await AsyncExecutor.run_in_thread(redis_client.close)

    @staticmethod
    async def cache_user_data(user_id: str, user_data: dict, use_env_prefix: bool = True):
        await AppRedisService.set_redis_value(
            f"user_data:{user_id}", json.dumps(user_data), expiry=3600, use_env_prefix=use_env_prefix
        )

    @staticmethod
    async def get_user_data(user_id: str, use_env_prefix: bool = True) -> Optional[dict]:
        cached_data = await AppRedisService.get_str_redis_value(f"user_data:{user_id}", use_env_prefix=use_env_prefix)
        if cached_data:
            return json.loads(cached_data)
        return None

    @staticmethod
    async def update_user_data(user_id: str, updated_data: dict, use_env_prefix: bool = True):
        await AppRedisService.set_redis_value(
            f"user_data:{user_id}", json.dumps(updated_data), expiry=3600, use_env_prefix=use_env_prefix
        )

    @staticmethod
    async def invalidate_user_cache(user_id: str, use_env_prefix: bool = True):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url)
        prefixed_key = f"{AppRedisService.get_env_prefix()}user_data:{user_id}" if use_env_prefix else f"user_data:{user_id}"

        try:
            await AsyncExecutor.run_in_thread(redis_client.delete, prefixed_key)
        finally:
            await AsyncExecutor.run_in_thread(redis_client.close)

    @staticmethod
    async def get_keys_by_pattern(pattern: str, use_env_prefix: bool = True) -> list:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url)
        prefixed_pattern = f"{AppRedisService.get_env_prefix()}{pattern}" if use_env_prefix else pattern

        try:
            keys = await AsyncExecutor.run_in_thread(lambda: list(redis_client.scan_iter(match=prefixed_pattern)))
            # Remove prefix if added
            if use_env_prefix:
                env_prefix = AppRedisService.get_env_prefix()
                keys = [k.decode()[len(env_prefix):] if k.decode().startswith(env_prefix) else k.decode() for k in keys]
            else:
                keys = [k.decode() for k in keys]
            return keys
        finally:
            await AsyncExecutor.run_in_thread(redis_client.close)

    @staticmethod
    async def delete_keys_by_pattern(pattern: str, use_env_prefix: bool = True) -> int:
        """Delete all Redis keys matching the given pattern. Returns the number of deleted keys."""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url)
        prefixed_pattern = f"{AppRedisService.get_env_prefix()}{pattern}" if use_env_prefix else pattern

        try:
            keys = await AsyncExecutor.run_in_thread(lambda: list(redis_client.scan_iter(match=prefixed_pattern)))
            if not keys:
                return 0
            deleted = await AsyncExecutor.run_in_thread(redis_client.delete, *keys)
            return deleted
        finally:
            await AsyncExecutor.run_in_thread(redis_client.close)

    @staticmethod
    async def get_all_caches_by_prefix(prefix: str, use_env_prefix: bool = True) -> dict:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url)
        prefixed_pattern = f"{AppRedisService.get_env_prefix()}{prefix}*" if use_env_prefix else f"{prefix}*"

        try:
            keys = await AsyncExecutor.run_in_thread(lambda: list(redis_client.scan_iter(match=prefixed_pattern)))
            if not keys:
                return {}
            values = await AsyncExecutor.run_in_thread(redis_client.mget, keys)
            result = {}
            for key, value in zip(keys, values):
                decoded_key = key.decode()
                if use_env_prefix:
                    env_prefix = AppRedisService.get_env_prefix()
                    if decoded_key.startswith(env_prefix):
                        decoded_key = decoded_key[len(env_prefix):]
                result[decoded_key] = value.decode() if value else None
            return result
        finally:
            await AsyncExecutor.run_in_thread(redis_client.close)

    @staticmethod
    async def debug_redis_keys(prefix: str = "*", use_env_prefix: bool = True) -> dict:
        caches = await AppRedisService.get_all_caches_by_prefix(prefix, use_env_prefix)
        return {"keys": caches, "debug_info": {"prefix": prefix, "keys_found": len(caches)}}

    @staticmethod
    async def debug_sudo_action_keys(instruction_id: str = None) -> dict:
        if instruction_id:
            value = await AppRedisService.get_str_redis_value(f"sudoAction:{instruction_id}", use_env_prefix=True)
            return {"value": value, "debug_info": {"instruction_id": instruction_id, "value_found": value is not None}}
        else:
            keys_with_env = await AppRedisService.get_all_caches_by_prefix("sudoAction:", use_env_prefix=True)
            keys_without_env = await AppRedisService.get_all_caches_by_prefix("sudoAction:", use_env_prefix=False)
            return {"keys_with_env": keys_with_env, "keys_without_env": keys_without_env}
