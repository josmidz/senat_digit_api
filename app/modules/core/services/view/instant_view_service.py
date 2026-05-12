"""
Instant View Creation Service

This service provides instant view creation capabilities to improve user experience
by creating MongoDB views immediately when new collections are detected, rather than
waiting for periodic checks.
"""

import asyncio
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.enums.type_enum import EMultipleValidationStatus


class InstantViewService:
    """Service for instant view creation when new collections are detected."""
    
    _instance: Optional['InstantViewService'] = None
    _db: Optional[AsyncIOMotorDatabase] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InstantViewService, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    async def initialize(cls, db: AsyncIOMotorDatabase) -> 'InstantViewService':
        """Initialize the service with database connection."""
        instance = cls()
        instance._db = db
        instance._initialized = True
        DebugService.app_debug_print("🚀 InstantViewService initialized", True)
        return instance
    
    @classmethod
    def get_instance(cls) -> Optional['InstantViewService']:
        """Get the singleton instance if initialized."""
        return cls._instance if cls._instance and cls._instance._initialized else None
    
    async def create_view_for_collection(self, collection_name: str) -> bool:
        """Create a view for a specific collection that excludes soft-deleted documents."""
        if not self._initialized or self._db is None:
            DebugService.app_debug_print(f"⚠️ InstantViewService not initialized, skipping view creation for {collection_name}", True)
            return False
            
        # Vérifier si le nom de la collection commence déjà par view_
        if collection_name.startswith('view_'):
            DebugService.app_debug_print(f"⚠️ La collection {collection_name} est déjà une vue", True)
            return False

        view_name = f"view_{collection_name}"

        try:
            # Check if the view exists by listing all collections
            # This avoids direct access to system.views which is restricted in Atlas
            all_collections = await self._db.list_collection_names()
            if view_name in all_collections:
                DebugService.app_debug_print(f"ℹ️ La vue {view_name} existe déjà", True)
                return True

            pipeline = [
                {"$match": {"soft_deleted_at": None, "multiple_validation_status": EMultipleValidationStatus.APPROVED.value}},
            ]

            # Use the createView command instead of direct system.views access
            await self._db.command({
                "create": view_name,
                "viewOn": collection_name,
                "pipeline": pipeline
            })
            DebugService.app_debug_print(f"✅ Vue créée instantanément pour la collection {collection_name}", True)
            return True
            
        except Exception as e:
            DebugService.app_debug_print(f"❌ Erreur lors de la création instantanée de vue pour {collection_name}: {str(e)}", True)
            return False
    
    async def ensure_collection_has_view(self, collection_name: str) -> bool:
        """Ensure a collection has its corresponding view, create if missing."""
        if not self._initialized or self._db is None:
            return False
            
        if collection_name.startswith('view_') or collection_name in ["system.views", "system.indexes"]:
            return True
            
        view_name = f"view_{collection_name}"
        
        try:
            all_collections = await self._db.list_collection_names()
            
            if view_name not in all_collections:
                return await self.create_view_for_collection(collection_name)
            return True
            
        except Exception as e:
            DebugService.app_debug_print(f"❌ Erreur lors de la vérification de vue pour {collection_name}: {str(e)}", True)
            return False
    
    async def create_view_instantly_async(self, collection_name: str):
        """Create a view instantly in a background task without blocking the main operation."""
        if not self._initialized:
            return
            
        try:
            # Run view creation in background without waiting
            asyncio.create_task(self.ensure_collection_has_view(collection_name))
        except Exception as e:
            DebugService.app_debug_print(f"❌ Erreur lors du lancement de la création de vue en arrière-plan pour {collection_name}: {str(e)}", True)


# Global function for easy access
async def ensure_view_exists_for_collection(collection_name: str) -> bool:
    """Global function to ensure a view exists for a collection."""
    service = InstantViewService.get_instance()
    if service:
        return await service.ensure_collection_has_view(collection_name)
    return False


async def create_view_instantly_for_collection(collection_name: str):
    """Global function to create a view instantly in background."""
    service = InstantViewService.get_instance()
    if service:
        await service.create_view_instantly_async(collection_name)
