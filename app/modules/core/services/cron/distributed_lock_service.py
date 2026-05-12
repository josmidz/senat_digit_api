import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.services.debug.debug_service import DebugService



class DistributedLockService:
    """
    Distributed lock service to prevent duplicate processing across multiple instances.
    Uses database-based locking mechanism.
    """
    
    # In-memory cache for locks to avoid database hits for recent locks
    _lock_cache: Dict[str, Dict[str, Any]] = {}
    _cache_ttl_seconds = 30  # Cache locks for 30 seconds
    
    @staticmethod
    async def acquire_lock(
        lock_name: str, 
        timeout_seconds: int = 300,  # 5 minutes default timeout
        retry_interval_seconds: float = 1.0
    ) -> bool:
        """
        Acquire a distributed lock.
        
        Args:
            lock_name: Unique name for the lock
            timeout_seconds: How long the lock should be held (auto-release)
            retry_interval_seconds: How long to wait between retry attempts
            
        Returns:
            True if lock was acquired, False otherwise
        """
        try:
            # Check cache first
            if DistributedLockService._is_locked_in_cache(lock_name):
                DebugService.app_debug_print(f"Lock {lock_name} found in cache, skipping", True)
                return False
            from app.modules.core.services.generic.generic_services import GenericService
            from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
            
            generic_service = GenericService(DEFAULT_LANGUAGE)
            
            # Current time
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(seconds=timeout_seconds)
            
            from app.modules.auth.enums.common import EDistributedLockStatusFlag

            # Try to create a new lock
            lock_data = {
                "lock_name": lock_name,
                "acquired_at": now,
                "expires_at": expires_at,
                "process_id_str": f"{time.time()}_{id(DistributedLockService)}",  # Unique process identifier
                "status": EDistributedLockStatusFlag.ACTIVE.value
            }
            
            # Check if lock already exists and is still valid
            existing_lock = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.DISTRIBUTED_LOCKS,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=DEFAULT_LANGUAGE,
                query={
                    "filter__lock_name": lock_name,
                    "filter__status": EDistributedLockStatusFlag.ACTIVE.value
                }
            )
            
            if existing_lock:
                # Check if lock has expired
                expires_at_existing = existing_lock.get("expires_at")
                if isinstance(expires_at_existing, str):
                    expires_at_existing = datetime.fromisoformat(expires_at_existing.replace('Z', '+00:00'))
                elif isinstance(expires_at_existing, datetime):
                    if expires_at_existing.tzinfo is None:
                        expires_at_existing = expires_at_existing.replace(tzinfo=timezone.utc)
                
                if expires_at_existing and now < expires_at_existing:
                    # Lock is still valid, cannot acquire
                    DebugService.app_debug_print(
                        f"Lock {lock_name} is already held by process {existing_lock.get('process_id_str')}, expires at {expires_at_existing}",
                        True
                    )
                    # Cache the lock info
                    DistributedLockService._cache_lock(lock_name, existing_lock)
                    return False
                else:
                    # Lock has expired, update it
                    DebugService.app_debug_print(f"Lock {lock_name} has expired, acquiring it", True)
                    await generic_service.update_data_in_collection(
                        collection_key=CollectionKey.DISTRIBUTED_LOCKS,
                        item_id=existing_lock["id"],
                        data=lock_data
                    )
            else:
                # No existing lock, create new one
                DebugService.app_debug_print(f"Creating new lock {lock_name}", True)
                await generic_service.add_data_to_collection(
                    collection_key=CollectionKey.DISTRIBUTED_LOCKS,
                    data=lock_data
                )
            
            # Cache the lock
            DistributedLockService._cache_lock(lock_name, lock_data)
            
            DebugService.app_debug_print(
                f"Successfully acquired lock {lock_name}, expires at {expires_at}",
                True
            )
            return True
            
        except Exception as e:
            DebugService.app_debug_print(
                f"Error acquiring lock {lock_name}: {str(e)}",
                True
            )
            return False
    
    @staticmethod
    async def release_lock(lock_name: str) -> bool:
        """
        Release a distributed lock.
        
        Args:
            lock_name: Name of the lock to release
            
        Returns:
            True if lock was released, False otherwise
        """
        try:
            from app.modules.core.services.generic.generic_services import GenericService
            from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
            from app.modules.core.models.mapping_keys import CollectionKey
            from app.modules.core.enums.type_enum import OutputDataType
            
            generic_service = GenericService(DEFAULT_LANGUAGE)
            
            from app.modules.auth.enums.common import EDistributedLockStatusFlag

            # Find and update the lock
            existing_lock = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.DISTRIBUTED_LOCKS,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=DEFAULT_LANGUAGE,
                query={
                    "filter__lock_name": lock_name,
                    "filter__status": EDistributedLockStatusFlag.ACTIVE.value
                }
            )

            if existing_lock:
                await generic_service.update_data_in_collection(
                    collection_key=CollectionKey.DISTRIBUTED_LOCKS,
                    item_id=existing_lock["id"],
                    data={
                        "status": EDistributedLockStatusFlag.RELEASED.value,
                        "released_at": datetime.now(timezone.utc)
                    }
                )
                
                # Remove from cache
                DistributedLockService._remove_from_cache(lock_name)
                
                DebugService.app_debug_print(f"Released lock {lock_name}", True)
                return True
            else:
                DebugService.app_debug_print(f"Lock {lock_name} not found or already released", True)
                return False
                
        except Exception as e:
            DebugService.app_debug_print(
                f"Error releasing lock {lock_name}: {str(e)}",
                True
            )
            return False
    
    @staticmethod
    def _is_locked_in_cache(lock_name: str) -> bool:
        """Check if lock exists in cache and is still valid."""
        if lock_name not in DistributedLockService._lock_cache:
            return False
            
        lock_info = DistributedLockService._lock_cache[lock_name]
        cached_at = lock_info.get("cached_at")
        
        # Check if cache entry has expired
        if time.time() - cached_at > DistributedLockService._cache_ttl_seconds:
            DistributedLockService._remove_from_cache(lock_name)
            return False
            
        return True
    
    @staticmethod
    def _cache_lock(lock_name: str, lock_data: Dict[str, Any]):
        """Cache lock information."""
        DistributedLockService._lock_cache[lock_name] = {
            **lock_data,
            "cached_at": time.time()
        }
    
    @staticmethod
    def _remove_from_cache(lock_name: str):
        """Remove lock from cache."""
        if lock_name in DistributedLockService._lock_cache:
            del DistributedLockService._lock_cache[lock_name]
    
    @staticmethod
    async def cleanup_expired_locks():
        """Clean up expired locks from the database."""
        try:
            from app.modules.core.services.generic.generic_services import GenericService
            from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
            from app.modules.core.models.mapping_keys import CollectionKey
            from app.modules.core.enums.type_enum import OutputDataType

            generic_service = GenericService(DEFAULT_LANGUAGE)
            now = datetime.now(timezone.utc)

            from app.modules.auth.enums.common import EDistributedLockStatusFlag

            # Find expired locks using new cleaner syntax
            expired_locks = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.DISTRIBUTED_LOCKS,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=DEFAULT_LANGUAGE,
                all_data=False,
                query={
                    "filter__status": EDistributedLockStatusFlag.ACTIVE.value,
                    "lt__expires_at": now.isoformat()  # Using new cleaner syntax
                }
            )

            # Update expired locks
            cleaned_count = 0
            for lock in expired_locks:
                await generic_service.update_data_in_collection(
                    collection_key=CollectionKey.DISTRIBUTED_LOCKS,
                    item_id=lock["id"],
                    data={
                        "status": EDistributedLockStatusFlag.EXPIRED.value,
                        "expired_at": now
                    }
                )
                cleaned_count += 1

            if cleaned_count > 0:
                DebugService.app_debug_print(f"Cleaned up {cleaned_count} expired locks", True)

            return {
                "status": "success",
                "message": f"Cleaned up {cleaned_count} expired locks",
                "cleaned_count": cleaned_count,
                "timestamp": now.isoformat()
            }

        except Exception as e:
            DebugService.app_debug_print(f"Error cleaning up expired locks: {str(e)}", True)
            return {
                "status": "error",
                "message": f"Error cleaning up expired locks: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
