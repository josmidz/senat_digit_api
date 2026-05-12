from pymongo import MongoClient
from app.modules.core.configs.config import settings

async def migrate_up():
    """
    Migration: add_sys_organization_id_to_cfg_user_device

    Description:
    Adds missing fields to collections.

    Created: 2025-07-03 10:25:03
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Update cfg_user_device collection - Add sys_organization_id field
    if "cfg_user_device" in db.list_collection_names():
        result = db["cfg_user_device"].update_many(
            {"sys_organization_id": {"$exists": False}},
            {"$set": {"sys_organization_id": None}}
        )
        print(f"Migration complete for cfg_user_device.sys_organization_id: {result.modified_count} documents updated")
    else:
        print(f"Collection cfg_user_device not found")

async def migrate_down():
    """
    Rollback the migration
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Rollback cfg_user_device collection - Remove sys_organization_id field
    if "cfg_user_device" in db.list_collection_names():
        result = db["cfg_user_device"].update_many(
            {"sys_organization_id": {"$exists": True}},
            {"$unset": {"sys_organization_id": ""}}
        )
        print(f"Rollback complete for cfg_user_device.sys_organization_id: {result.modified_count} documents updated")
    else:
        print(f"Collection cfg_user_device not found")
