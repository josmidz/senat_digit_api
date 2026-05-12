from pymongo import MongoClient
from app.modules.core.configs.config import settings

async def migrate_up():
    """
    Migration: update_bank_model_with_defaults

    Description:
    Adds missing fields to collections.

    Created: 2025-06-19 17:06:46
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Update ref_color collection - Add flag field
    if "ref_color" in db.list_collection_names():
        result = db["ref_color"].update_many(
            {"flag": {"$exists": False}},
            {"$set": {"flag": None}}
        )
        print(f"Migration complete for ref_color.flag: {result.modified_count} documents updated")
    else:
        print(f"Collection ref_color not found")

    # Update ref_color collection - Add description_str field
    if "ref_color" in db.list_collection_names():
        result = db["ref_color"].update_many(
            {"description_str": {"$exists": False}},
            {"$set": {"description_str": "Aucune description fournie."}}
        )
        print(f"Migration complete for ref_color.description_str: {result.modified_count} documents updated")
    else:
        print(f"Collection ref_color not found")

    # Update ref_bank collection - Add rib_account_number_format_str field
    if "ref_bank" in db.list_collection_names():
        result = db["ref_bank"].update_many(
            {"rib_account_number_format_str": {"$exists": False}},
            {"$set": {"rib_account_number_format_str": None}}
        )
        print(f"Migration complete for ref_bank.rib_account_number_format_str: {result.modified_count} documents updated")
    else:
        print(f"Collection ref_bank not found")

    # Update ref_bank collection - Add has_rib_nomenclature_constraint field
    if "ref_bank" in db.list_collection_names():
        result = db["ref_bank"].update_many(
            {"has_rib_nomenclature_constraint": {"$exists": False}},
            {"$set": {"has_rib_nomenclature_constraint": False}}
        )
        print(f"Migration complete for ref_bank.has_rib_nomenclature_constraint: {result.modified_count} documents updated")
    else:
        print(f"Collection ref_bank not found")

    # Update ref_bank collection - Add has_prefixes_constraint field
    if "ref_bank" in db.list_collection_names():
        result = db["ref_bank"].update_many(
            {"has_prefixes_constraint": {"$exists": False}},
            {"$set": {"has_prefixes_constraint": False}}
        )
        print(f"Migration complete for ref_bank.has_prefixes_constraint: {result.modified_count} documents updated")
    else:
        print(f"Collection ref_bank not found")

    # Update ref_bank collection - Add prefix_caracters_number field
    if "ref_bank" in db.list_collection_names():
        result = db["ref_bank"].update_many(
            {"prefix_caracters_number": {"$exists": False}},
            {"$set": {"prefix_caracters_number": None}}
        )
        print(f"Migration complete for ref_bank.prefix_caracters_number: {result.modified_count} documents updated")
    else:
        print(f"Collection ref_bank not found")

    # Update ref_bank collection - Add bank_account_number_prefixes field
    if "ref_bank" in db.list_collection_names():
        result = db["ref_bank"].update_many(
            {"bank_account_number_prefixes": {"$exists": False}},
            {"$set": {"bank_account_number_prefixes": []}}
        )
        print(f"Migration complete for ref_bank.bank_account_number_prefixes: {result.modified_count} documents updated")
    else:
        print(f"Collection ref_bank not found")

async def migrate_down():
    """
    Rollback the migration
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Rollback ref_color collection - Remove flag field
    if "ref_color" in db.list_collection_names():
        result = db["ref_color"].update_many(
            {"flag": {"$exists": True}},
            {"$unset": {"flag": ""}}
        )
        print(f"Rollback complete for ref_color.flag: {result.modified_count} documents updated")
    else:
        print(f"Collection ref_color not found")

    # Rollback ref_color collection - Remove description_str field
    if "ref_color" in db.list_collection_names():
        result = db["ref_color"].update_many(
            {"description_str": {"$exists": True}},
            {"$unset": {"description_str": ""}}
        )
        print(f"Rollback complete for ref_color.description_str: {result.modified_count} documents updated")
    else:
        print(f"Collection ref_color not found")

    # Rollback ref_bank collection - Remove rib_account_number_format_str field
    if "ref_bank" in db.list_collection_names():
        result = db["ref_bank"].update_many(
            {"rib_account_number_format_str": {"$exists": True}},
            {"$unset": {"rib_account_number_format_str": ""}}
        )
        print(f"Rollback complete for ref_bank.rib_account_number_format_str: {result.modified_count} documents updated")
    else:
        print(f"Collection ref_bank not found")

    # Rollback ref_bank collection - Remove has_rib_nomenclature_constraint field
    if "ref_bank" in db.list_collection_names():
        result = db["ref_bank"].update_many(
            {"has_rib_nomenclature_constraint": {"$exists": True}},
            {"$unset": {"has_rib_nomenclature_constraint": ""}}
        )
        print(f"Rollback complete for ref_bank.has_rib_nomenclature_constraint: {result.modified_count} documents updated")
    else:
        print(f"Collection ref_bank not found")

    # Rollback ref_bank collection - Remove has_prefixes_constraint field
    if "ref_bank" in db.list_collection_names():
        result = db["ref_bank"].update_many(
            {"has_prefixes_constraint": {"$exists": True}},
            {"$unset": {"has_prefixes_constraint": ""}}
        )
        print(f"Rollback complete for ref_bank.has_prefixes_constraint: {result.modified_count} documents updated")
    else:
        print(f"Collection ref_bank not found")

    # Rollback ref_bank collection - Remove prefix_caracters_number field
    if "ref_bank" in db.list_collection_names():
        result = db["ref_bank"].update_many(
            {"prefix_caracters_number": {"$exists": True}},
            {"$unset": {"prefix_caracters_number": ""}}
        )
        print(f"Rollback complete for ref_bank.prefix_caracters_number: {result.modified_count} documents updated")
    else:
        print(f"Collection ref_bank not found")

    # Rollback ref_bank collection - Remove bank_account_number_prefixes field
    if "ref_bank" in db.list_collection_names():
        result = db["ref_bank"].update_many(
            {"bank_account_number_prefixes": {"$exists": True}},
            {"$unset": {"bank_account_number_prefixes": ""}}
        )
        print(f"Rollback complete for ref_bank.bank_account_number_prefixes: {result.modified_count} documents updated")
    else:
        print(f"Collection ref_bank not found")
