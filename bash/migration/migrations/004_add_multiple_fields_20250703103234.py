from pymongo import MongoClient
from app.modules.core.configs.config import settings

async def migrate_up():
    """
    Migration: add_multiple_fields

    Description:
    Adds missing fields to collections.

    Created: 2025-07-03 10:32:34
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Update ops_user_login_history collection - Add session_expected_expiration field
    if "ops_user_login_history" in db.list_collection_names():
        result = db["ops_user_login_history"].update_many(
            {"session_expected_expiration": {"$exists": False}},
            {"$set": {"session_expected_expiration": None}}
        )
        print(f"Migration complete for ops_user_login_history.session_expected_expiration: {result.modified_count} documents updated")
    else:
        print(f"Collection ops_user_login_history not found")

    # Update ops_user_login_history collection - Add session_id_str field
    if "ops_user_login_history" in db.list_collection_names():
        result = db["ops_user_login_history"].update_many(
            {"session_id_str": {"$exists": False}},
            {"$set": {"session_id_str": ""}}
        )
        print(f"Migration complete for ops_user_login_history.session_id_str: {result.modified_count} documents updated")
    else:
        print(f"Collection ops_user_login_history not found")

async def migrate_down():
    """
    Rollback the migration
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Rollback ops_user_login_history collection - Remove session_expected_expiration field
    if "ops_user_login_history" in db.list_collection_names():
        result = db["ops_user_login_history"].update_many(
            {"session_expected_expiration": {"$exists": True}},
            {"$unset": {"session_expected_expiration": ""}}
        )
        print(f"Rollback complete for ops_user_login_history.session_expected_expiration: {result.modified_count} documents updated")
    else:
        print(f"Collection ops_user_login_history not found")

    # Rollback ops_user_login_history collection - Remove session_id_str field
    if "ops_user_login_history" in db.list_collection_names():
        result = db["ops_user_login_history"].update_many(
            {"session_id_str": {"$exists": True}},
            {"$unset": {"session_id_str": ""}}
        )
        print(f"Rollback complete for ops_user_login_history.session_id_str: {result.modified_count} documents updated")
    else:
        print(f"Collection ops_user_login_history not found")
