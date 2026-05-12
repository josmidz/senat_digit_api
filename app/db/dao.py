# app/db/dao.py

import asyncio
import json
from typing import Any, Dict, Optional, Tuple
from app.modules.auth.enums.common import MessageCategory
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE

from bson import ObjectId
from datetime import datetime,timezone
from app.db.base import get_collection, get_read_only_collection

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from bson import ObjectId
import logging

from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.encryption.encryption_service import EncryptionService
from app.modules.core.services.encryption.db_encryption_service import DBEncryptionService
from app.modules.core.services.model.model_service import ModelService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.services.history.ops_history_service import OpsHistoryService
from app.modules.core.services.ops_log.ops_log_service import OpsLogService
from pymongo.results import UpdateResult

from app.modules.core.utils.helpers.line_helper import format_exception


def _diff_cmp(v: Any) -> Any:
    """Canonical representation used to detect whether a field value changed."""
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return json.dumps(v, sort_keys=True, default=str)
    if isinstance(v, datetime):
        return v.replace(tzinfo=None).isoformat()
    return str(v)


def _compute_diff(existing_doc: Dict[str, Any], update_data: Dict[str, Any]):
    """Return (diff_before, diff_after) containing only fields that actually changed."""
    skip_fields = {"_id", "id", "updated_at", "created_at"}
    diff_before: Dict[str, Any] = {}
    diff_after: Dict[str, Any] = {}
    for field_key, new_val in update_data.items():
        if field_key in skip_fields:
            continue
        old_val = existing_doc.get(field_key)
        if _diff_cmp(old_val) != _diff_cmp(new_val):
            diff_before[field_key] = old_val
            diff_after[field_key] = new_val
    return diff_before, diff_after


# Global semaphore to limit concurrent DB operations across ALL requests
# This prevents one request from monopolizing all DB connections
_db_semaphore: Optional[asyncio.Semaphore] = None
_DB_MAX_CONCURRENT = 100  # Max concurrent DB operations (increased from 30 to reduce blocking)


def get_db_semaphore() -> asyncio.Semaphore:
    """Get or create the global DB semaphore."""
    global _db_semaphore
    if _db_semaphore is None:
        _db_semaphore = asyncio.Semaphore(_DB_MAX_CONCURRENT)
        DebugService.app_debug_print(f"[DAO] Initialized global DB semaphore with limit={_DB_MAX_CONCURRENT}", True)
    return _db_semaphore


class DAO:
    def __init__(self, collection_name: str, model_class: type, is_read_only: bool):
        """
        Initialize DAO with a collection name and an associated model class.
        :param collection_name: The name of the MongoDB collection.
        :param model_class: The Pydantic model class for validation.
        :param is_read_only: Whether the DAO is read-only.
        """
        self.collection_name = collection_name
        self.model_class = model_class
        self.is_read_only = is_read_only

        # Initialize the database encryption service
        self.db_encryption = DBEncryptionService()

        # Resolve history tracking flags from the collection mapping
        self.can_watch_update_history: bool = False
        self.can_watch_delete_history: bool = False
        try:
            from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
            for _key, _meta in COLLECTION_MODEL_MAPPING.items():
                if _meta.collection_name == collection_name:
                    self.can_watch_update_history = getattr(_meta, 'can_watch_update_history', False)
                    self.can_watch_delete_history = getattr(_meta, 'can_watch_delete_history', False)
                    break
        except Exception:
            pass  # Fail silently — flags stay False

        self.collection = get_read_only_collection(collection_name) if self.is_read_only else get_collection(collection_name)
        # self.collection = get_collection(collection_name) if is_read_only else None
        assert self.collection is not None, f"Error: Collection '{collection_name}' not found!"


    async def _remove_from_view(self, query: Dict[str, Any]):
        """Remove document(s) from the corresponding view collection after a hard delete.
        
        If the view is a real MongoDB view (dynamic), this is a no-op since views auto-reflect changes.
        If the view was created as a regular collection, this ensures the data is also removed.
        Errors are silently caught so this never breaks the main delete operation.
        """
        try:
            from app.db.base import mongodb
            view_name = f"view_{self.collection_name}"
            view_col = mongodb.db[view_name]
            await view_col.delete_many(query)
            DebugService.app_debug_print(f"[DAO] _remove_from_view: cleaned {view_name} with query {query}", True)
        except Exception as e:
            # Expected to fail if view is a real MongoDB view (cannot write to views)
            DebugService.app_debug_print(f"[DAO] _remove_from_view skipped for {self.collection_name}: {e}", True)


    async def delete_with_query(self, query: Dict[str, Any], accept_language: Optional[str] = DEFAULT_LANGUAGE, by_pass_exception: Optional[bool] = False, sys_organization_id: Optional[str] = None, sys_user_id: Optional[str] = None) -> bool:
        """
        Hard delete a single document matching the query with pre- and post-delete hooks.

        :param query: The query filter to identify the document to delete
        :param accept_language: Language preference for error messages
        :param by_pass_exception: Whether to bypass exceptions and return False instead
        :return: True if a document was deleted, False otherwise
        """
        try:
            # Check delete_if_not_used_in constraint before deletion
            # First, find the document to get its ID for constraint checking
            document = await self.collection.find_one(query)
            if not document:
                return False

            item_id = str(document["_id"])

            # Check constraints similar to the delete method
            for field_name, field in self.model_class.model_fields.items():
                meta = field.json_schema_extra or {}
                delete_if_not_used_in = meta.get("extra_metas", {}).get("delete_if_not_used_in", "")
                DebugService.app_debug_print(f"delete_with_query - delete_if_not_used_in: {field_name}, extra_metas: json_schema_extra: {delete_if_not_used_in}")

                if delete_if_not_used_in:
                    # Split the comma-separated collection keys
                    collection_keys = [key.strip() for key in delete_if_not_used_in.split(",") if key.strip()]

                    for collection_key in collection_keys:
                        try:
                            # Get the collection for reference checking
                            ref_collection = get_collection(collection_key)

                            if ref_collection:
                                # Check if the document is referenced in other collections
                                field_value = document.get(field_name)
                                if field_value:
                                    # Check for references using the field value
                                    ref_query = {field_name: field_value}
                                    ref_count = await ref_collection.count_documents(ref_query)

                                    if ref_count > 0:
                                        error_msg = f"Cannot delete: {field_name} is referenced in {collection_key}"
                                        DebugService.app_debug_print(error_msg, False)
                                        if by_pass_exception:
                                            return False
                                        raise ValueError(error_msg)
                        except Exception as ref_error:
                            DebugService.app_debug_print(f"Error checking references in {collection_key}: {ref_error}", False)
                            if by_pass_exception:
                                return False
                            raise ref_error

            # Proceed with deletion if no references found
            await self.pre_delete(item_id)
            result = await self.collection.delete_one(query)
            if result.deleted_count > 0:
                # Also remove from view collection
                await self._remove_from_view({"_id": document["_id"]})
                # Record delete history only if the flag is enabled for this collection
                if self.can_watch_delete_history:
                    try:
                        await OpsHistoryService.record_delete(
                            collection_name=self.collection_name,
                            document_id=item_id,
                            data_before=document,
                            operation_type="hard_delete_with_query",
                        )
                    except Exception as hist_err:
                        DebugService.app_debug_print(f"[DAO] History recording failed (delete_with_query): {hist_err}", False)

                # Record organization CRUD log (fire-and-forget)
                if sys_organization_id and sys_user_id:
                    OpsLogService.record_log_background(
                        crud_type="delete",
                        collection_name=self.collection_name,
                        sys_organization_id=sys_organization_id,
                        sys_user_id=sys_user_id,
                        document_id=item_id,
                        description_str=f"Deleted {self.collection_name}/{item_id}",
                    )

                await self.post_delete(item_id)
                return True
            return False

        except ValueError as ve:
            if by_pass_exception:
                return False
            raise ve
        except Exception as e:
            DebugService.app_debug_print(f"Error in delete_with_query: {e}", False)
            if by_pass_exception:
                return False
            raise e

    async def delete_many_query(self, query: Dict[str, Any], accept_language: Optional[str] = DEFAULT_LANGUAGE, by_pass_exception: Optional[bool] = False) -> bool:
        """
        Hard delete multiple documents matching the query with constraint checking.

        :param query: The query filter to identify documents to delete
        :param accept_language: Language preference for error messages
        :param by_pass_exception: Whether to bypass exceptions and return False instead
        :return: True if any documents were deleted, False otherwise
        """
        try:
            # First, find all documents that match the query to check constraints
            documents = await self.collection.find(query).to_list(None)
            if not documents:
                return False

            # Check constraints for each document
            for document in documents:
                item_id = str(document["_id"])

                # Check delete_if_not_used_in constraint for each document
                for field_name, field in self.model_class.model_fields.items():
                    meta = field.json_schema_extra or {}
                    delete_if_not_used_in = meta.get("extra_metas", {}).get("delete_if_not_used_in", "")
                    DebugService.app_debug_print(f"delete_many_query - delete_if_not_used_in: {field_name}, extra_metas: json_schema_extra: {delete_if_not_used_in}")

                    if delete_if_not_used_in:
                        # Split the comma-separated collection keys
                        collection_keys = [key.strip() for key in delete_if_not_used_in.split(",") if key.strip()]

                        for collection_key in collection_keys:
                            try:
                                # Get the collection for reference checking
                                ref_collection = get_collection(collection_key)

                                if ref_collection:
                                    # Check if the document is referenced in other collections
                                    field_value = document.get(field_name)
                                    if field_value:
                                        # Check for references using the field value
                                        ref_query = {field_name: field_value}
                                        ref_count = await ref_collection.count_documents(ref_query)

                                        if ref_count > 0:
                                            error_msg = f"Cannot delete document {item_id}: {field_name} is referenced in {collection_key}"
                                            DebugService.app_debug_print(error_msg, False)
                                            if by_pass_exception:
                                                return False
                                            raise ValueError(error_msg)
                            except Exception as ref_error:
                                DebugService.app_debug_print(f"Error checking references in {collection_key}: {ref_error}", False)
                                if by_pass_exception:
                                    return False
                                raise ref_error

            # If all constraint checks pass, proceed with deletion
            # Call pre_delete for each document
            for document in documents:
                item_id = str(document["_id"])
                await self.pre_delete(item_id)

            # Perform the bulk deletion
            result = await self.collection.delete_many(query)

            if result.deleted_count > 0:
                # Also remove from view collection
                await self._remove_from_view(query)
                # Call post_delete and record history for each deleted document
                for document in documents:
                    item_id = str(document["_id"])
                    if self.can_watch_delete_history:
                        try:
                            await OpsHistoryService.record_delete(
                                collection_name=self.collection_name,
                                document_id=item_id,
                                data_before=document,
                                operation_type="delete_many",
                            )
                        except Exception as hist_err:
                            DebugService.app_debug_print(f"[DAO] History recording failed (delete_many_query): {hist_err}", False)
                    await self.post_delete(item_id)
                return True
            return False

        except ValueError as ve:
            if by_pass_exception:
                return False
            raise ve
        except Exception as e:
            DebugService.app_debug_print(f"Error in delete_many_query: {e}", False)
            if by_pass_exception:
                return False
            raise e
        
    def convert_id_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert all fields ending with '_id' to ObjectId if they are not None and not already an ObjectId.
        """
        for key, value in data.items():
            if key == "id" and value is not None:
                data['_id'] = ObjectId(value)
            if key == "id" and value is None:
                data['_id'] = ObjectId()
            if key.endswith("_id") and value is not None:
                if not isinstance(value, ObjectId):
                    try:
                        data[key] = ObjectId(value)
                    except Exception as e:
                        raise ValueError(f"Invalid ObjectId format for field '{key}': {value}") from e
        return data

    async def pre_save(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Hook to run before saving a document."""
        DebugService.app_debug_print("Pre-save hook triggered.", True)
        # Convert fields ending with '_id' to ObjectId
        data = self.convert_id_fields(data)
        # Use timezone-aware UTC datetime
        data["created_at"] = datetime.now(timezone.utc)
        data["updated_at"] = datetime.now(timezone.utc)

        # Convert any enum values to their string representations
        data = ConverterService.convert_enums_to_values(data)
        
        # Encrypt fields that have can_be_encrypted=True
        for field_name, field in self.model_class.model_fields.items():
            meta = field.json_schema_extra or {}
            can_be_encrypted = meta.get("can_be_encrypted", False)

            if can_be_encrypted and field_name in data:
                field_value = data.get(field_name)
                if field_value and isinstance(field_value, str):
                    # Only encrypt if the value is not already encrypted
                    if not field_value.lower().startswith("enc:") and not field_value.lower().startswith("db_enc:"):
                        try:
                            # Use the database encryption service for database fields
                            encrypted_value = self.db_encryption.encrypt(field_value)
                            # The encrypted value already includes the prefix
                            data[field_name] = encrypted_value
                            DebugService.app_debug_print(f"Encrypted field {field_name} with DBEncryptionService", True)
                        except Exception as e:
                            DebugService.app_debug_print(f"Error encrypting field {field_name}: {e}", True)
                            # Fallback to the old encryption method if the new one fails
                            encrypted_value = EncryptionService.encrypt(field_value)
                            data[field_name] = f"enc:{encrypted_value}"
                            DebugService.app_debug_print(f"Fallback: Encrypted field {field_name} with EncryptionService", True)

        return data

    async def pre_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Hook to run before updating a document."""
        DebugService.app_debug_print(f"\n\n\n\n  Pre-update hook triggered data : {data}.\n\n\n",False)
        # Convert fields ending with '_id' to ObjectId
        data = self.convert_id_fields(data)
        # Update the timestamp
        data["updated_at"] = datetime.now(timezone.utc)

        # Only update multiple_validated_at if multiple_validation_status is being updated
        if "multiple_validation_status" in data and "multiple_validated_at" not in data:
            data["multiple_validated_at"] = datetime.now(timezone.utc)
        # If multiple_validated_at is in data but multiple_validation_status is not, remove it
        elif "multiple_validated_at" in data and "multiple_validation_status" not in data:
            DebugService.app_debug_print(f"\n\n\n\n  Removing multiple_validated_at from update data as multiple_validation_status is not present\n\n\n",False)
            data.pop("multiple_validated_at")

        # Remove fields that should not be updated
        # These fields should only be set during creation, not updates
        if "identifier" in data:
            DebugService.app_debug_print(f"\n\n\n\n  Removing identifier from update data\n\n\n",False)
            data.pop("identifier")
        if "created_at" in data:
            DebugService.app_debug_print(f"\n\n\n\n  Removing created_at from update data\n\n\n",False)
            data.pop("created_at")

        # Encrypt fields that have can_be_encrypted=True
        for field_name, field in self.model_class.model_fields.items():
            meta = field.json_schema_extra or {}
            can_be_encrypted = meta.get("can_be_encrypted", False)

            if can_be_encrypted and field_name in data:
                field_value = data.get(field_name)
                if field_value and isinstance(field_value, str):
                    # Only encrypt if the value is not already encrypted
                    if not field_value.lower().startswith("enc:") and not field_value.lower().startswith("db_enc:"):
                        try:
                            # Use the database encryption service for database fields
                            encrypted_value = self.db_encryption.encrypt(field_value)
                            # The encrypted value already includes the prefix
                            data[field_name] = encrypted_value
                            DebugService.app_debug_print(f"Encrypted field {field_name} with DBEncryptionService", False)
                        except Exception as e:
                            DebugService.app_debug_print(f"Error encrypting field {field_name}: {e}", True)
                            # Fallback to the old encryption method if the new one fails
                            encrypted_value = EncryptionService.encrypt(field_value)
                            data[field_name] = f"enc:{encrypted_value}"
                            DebugService.app_debug_print(f"Fallback: Encrypted field {field_name} with EncryptionService", False)

        return data

    async def post_save(self, result: Any) -> Any:
        """Hook to run after saving a document."""
        DebugService.app_debug_print("Post-save hook triggered.", True)
        return result

    async def pre_delete(self, item_id: str):
        """Hook to run before deleting a document."""
        DebugService.app_debug_print(f"Pre-delete hook triggered for item {item_id}.", True)

    async def post_delete(self, item_id: str):
        """Hook to run after deleting a document."""
        DebugService.app_debug_print(f"Post-delete hook triggered for item {item_id}.", True)

    async def add(self, data: Dict[str, Any], sys_organization_id: Optional[str] = None, sys_user_id: Optional[str] = None) -> str:
        """
        Add a new document to the collection, validating with the Pydantic model,
        and handling `reject_if_exist` and `upsert_if_exist` logic.
        """
        # Convert enums and preprocess data
        data = ConverterService.convert_enums_to_values(data)

        # Debug the incoming data
        DebugService.app_debug_print(f"\n\n\n\n ADD - Incoming data: {data} \n\n\n", True)

        try:
            # Validate using the model
            validated_data = self.model_class(**data).dict(by_alias=True)
            validated_data["created_at"] = datetime.now(timezone.utc)
            validated_data["updated_at"] = datetime.now(timezone.utc)

            # Debug the validated data
            DebugService.app_debug_print(f"\n\n\n\n ADD - Validated data: {validated_data} \n\n\n", True)

            # Convert any enum values in the validated data to their string representations
            validated_data = ConverterService.convert_enums_to_values(validated_data)

            # Check for `reject_if_exist`, `upsert_if_exist`, and `upsert_if_exist_with_props`
            for field_name, field in self.model_class.model_fields.items():
                meta = field.json_schema_extra or {}
                reject_if_exist = meta.get("extra_metas", {}).get("reject_if_exist", False)
                upsert_if_exist = meta.get("extra_metas", {}).get("upsert_if_exist", False)
                upsert_if_exist_with_props = meta.get("extra_metas", {}).get("upsert_if_exist_with_props", "")

                if reject_if_exist or upsert_if_exist:
                    # Check if a record with this field value already exists
                    filter_query = {field_name: validated_data.get(field_name)}
                    existing_record = await self.collection.find_one(filter_query)

                    if existing_record:
                        if reject_if_exist:
                            raise ValueError(
                                f"Record with {field_name}={validated_data[field_name]} already exists."
                            )
                        elif upsert_if_exist:
                            # Perform an update (upsert) if the record exists
                            validated_data["updated_at"] = datetime.now(timezone.utc)
                            validated_data.pop("_id", None)
                            await self.collection.update_one(filter_query, {"$set": validated_data})
                            return str(existing_record["_id"])

                elif upsert_if_exist_with_props:
                    # Handle upsert_if_exist_with_props
                    # Split the comma-separated property names
                    prop_names = [prop.strip() for prop in upsert_if_exist_with_props.split(",") if prop.strip()]

                    if prop_names:
                        # Create a filter query with all specified properties
                        filter_query = {}
                        for prop_name in prop_names:
                            if prop_name in validated_data:
                                filter_query[prop_name] = validated_data.get(prop_name)
                            else:
                                # If any required property is missing, skip this upsert check
                                DebugService.app_debug_print(f"Property {prop_name} not found in data for upsert_if_exist_with_props", True)
                                break

                        # Only proceed if all properties were found
                        if len(filter_query) == len(prop_names):
                            DebugService.app_debug_print(f"Checking for existing record with filter: {filter_query}", True)
                            existing_record = await self.collection.find_one(filter_query)

                            if existing_record:
                                DebugService.app_debug_print(f"Found existing record with ID: {existing_record['_id']}", True)
                                # Perform an update (upsert) if the record exists
                                validated_data["updated_at"] = datetime.now(timezone.utc)
                                validated_data.pop("_id", None)
                                await self.collection.update_one(filter_query, {"$set": validated_data})
                                return str(existing_record["_id"])

            # Insert the new document
            processed_data = await self.pre_save(validated_data)
            # Final check for any remaining enum values
            processed_data = ConverterService.convert_enums_to_values(processed_data)
            result = await self.collection.insert_one(processed_data)

            # Trigger instant view creation for new collections
            await self._ensure_view_exists()

            await self.post_save(result)

            # Record organization CRUD log (fire-and-forget)
            if sys_organization_id and sys_user_id:
                OpsLogService.record_log_background(
                    crud_type="create",
                    collection_name=self.collection_name,
                    sys_organization_id=sys_organization_id,
                    sys_user_id=sys_user_id,
                    document_id=str(result.inserted_id),
                    description_str=f"Created {self.collection_name}/{result.inserted_id}",
                )

            return str(result.inserted_id)
        except Exception as e:
            DebugService.app_debug_print(f"\n\n\n\n ADD - Validation error: {e} with data: {data} \n\n\n", True)
            raise

    async def _ensure_view_exists(self):
        """Ensure that a view exists for this collection.
        
        Uses the SAME DB connection as the DAO (from base.py mongodb)
        to avoid cross-client visibility delays. Awaited so the view
        is guaranteed to exist before the insert response reaches the client.
        """
        from app.modules.core.enums.type_enum import EMultipleValidationStatus
        from app.db.base import mongodb

        view_name = f"view_{self.collection_name}"

        try:
            # Skip if collection is already a view or system collection
            if self.collection_name.startswith('view_') or self.collection_name in ["system.views", "system.indexes"]:
                return

            # Check if view already exists using the SAME db as the DAO
            all_collections = await mongodb.db.list_collection_names()
            if view_name in all_collections:
                return

            # Create the view synchronously using the DAO's own DB connection
            pipeline = [
                {"$match": {"soft_deleted_at": None, "multiple_validation_status": EMultipleValidationStatus.APPROVED.value}},
            ]
            await mongodb.db.command({
                "create": view_name,
                "viewOn": self.collection_name,
                "pipeline": pipeline
            })
            DebugService.app_debug_print(f"✅ Vue créée instantanément pour {self.collection_name} (via DAO)", True)

        except Exception as e:
            # Don't let view creation errors affect the main operation
            DebugService.app_debug_print(f"⚠️ Failed to ensure view exists for {self.collection_name}: {str(e)}", True)



    async def get(self, item_id: str, sys_organization_id: Optional[str] = None, sys_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a document by ID, excluding soft-deleted documents."""
        document = await self.collection.find_one({"_id": ObjectId(item_id), "soft_deleted_at": None})
        if document:
            # Convert ObjectId to string and ensure id field exists
            id_str = str(document["_id"])
            document["_id"] = id_str
            document["id"] = id_str

            # Record read log (fire-and-forget)
            if sys_organization_id and sys_user_id:
                OpsLogService.record_log_background(
                    crud_type="read",
                    collection_name=self.collection_name,
                    sys_organization_id=sys_organization_id,
                    sys_user_id=sys_user_id,
                    document_id=id_str,
                    description_str=f"Read document {id_str} from {self.collection_name}",
                )
        return document

    async def update(self, static_filter_data: Dict[str, Any], validated_data: Dict[str, Any], updated_by_user_id: Optional[str] = None, sys_organization_id: Optional[str] = None, sys_user_id: Optional[str] = None) -> UpdateResult:
        """
        Met à jour un document dans la collection.

        Args:
            static_filter_data: Filtre pour identifier le document à mettre à jour
            validated_data: Données validées à mettre à jour

        Returns:
            UpdateResult: Résultat de la mise à jour
        """
        try:

            # Convertir les IDs dans le filtre
            db_filter = ConverterService.convert_query_params(static_filter_data)

            # Récupérer le document existant
            existing_doc = await self.collection.find_one(db_filter)
            if not existing_doc:
                print(f"Update - Document not found with filter: {db_filter}")
                return UpdateResult(raw_result={"nModified": 0, "n": 0}, acknowledged=True)

            # print(f"Update - Incoming data: {validated_data}")
            # print(f"Update - Incoming query: {db_filter}")
            # print(f"Update - existing_doc: {existing_doc}")

            # Créer un dictionnaire contenant uniquement les champs à mettre à jour
            update_data = {}
            for field, value in validated_data.items():
                # Inclure le champ même si la valeur est None
                update_data[field] = value

            # print(f"Update - update_data: {update_data}")
            update_data = ConverterService.convert_enums_to_values(update_data)
            # Utiliser $set uniquement si nous avons des champs à mettre à jour
            if update_data:
                update_data = ConverterService.track_saving_data_to_objectid(update_data)
                result = await self.collection.update_one(db_filter, {"$set": update_data})
                print(f"Update - RESULT: {result}")
                # Record update history only if the flag is enabled for this collection
                if self.can_watch_update_history:
                    try:
                        doc_id = str(existing_doc.get("_id", ""))
                        if doc_id:
                            diff_before, diff_after = _compute_diff(existing_doc, update_data)
                            if diff_before or diff_after:
                                await OpsHistoryService.record_update(
                                    collection_name=self.collection_name,
                                    document_id=doc_id,
                                    data_before=diff_before,
                                    data_after=diff_after,
                                    operation_type="update",
                                    document_identifier=existing_doc.get("identifier"),
                                    updated_fields=list(diff_after.keys()),
                                    updated_by_user_id=updated_by_user_id,
                                )
                    except Exception as hist_err:
                        DebugService.app_debug_print(f"[DAO] History recording failed (update): {hist_err}", False)

                # Record organization CRUD log (fire-and-forget)
                if sys_organization_id and sys_user_id:
                    OpsLogService.record_log_background(
                        crud_type="update",
                        collection_name=self.collection_name,
                        sys_organization_id=sys_organization_id,
                        sys_user_id=sys_user_id,
                        document_id=str(existing_doc.get("_id", "")),
                        description_str=f"Updated {self.collection_name}/{existing_doc.get('_id', '')}",
                    )

                return result
            else:
                print("Update - No fields to update")
                return UpdateResult(raw_result={"nModified": 0, "n": 0}, acknowledged=True)
        except Exception as e:
            print(f"Error in update: {e}")
            raise e

    async def update_many(self, static_filter_data: Dict[str, Any], validated_data: Dict[str, Any], updated_by_user_id: Optional[str] = None) -> UpdateResult:
        """
        Met à jour un document dans la collection.

        Args:
            static_filter_data: Filtre pour identifier le document à mettre à jour
            validated_data: Données validées à mettre à jour

        Returns:
            UpdateResult: Résultat de la mise à jour
        """
        try:

            # Convertir les IDs dans le filtre
            db_filter = ConverterService.convert_query_params(static_filter_data)

            # Récupérer le document existant
            existing_doc = await self.collection.find_one(db_filter)
            if not existing_doc:
                # print(f"Update - Document not found with filter: {db_filter}")
                return UpdateResult(raw_result={"nModified": 0, "n": 0}, acknowledged=True)

            # print(f"Update - Incoming data: {validated_data}")
            # print(f"Update - Incoming query: {db_filter}")
            # print(f"Update - existing_doc: {existing_doc}")

            # Créer un dictionnaire contenant uniquement les champs à mettre à jour
            update_data = {}
            for field, value in validated_data.items():
                # Inclure le champ même si la valeur est None
                update_data[field] = value

            # print(f"Update - update_data: {update_data}")
            update_data = ConverterService.convert_enums_to_values(update_data)
            # Utiliser $set uniquement si nous avons des champs à mettre à jour
            if update_data:
                update_data = ConverterService.track_saving_data_to_objectid(update_data)
                result = await self.collection.update_many(db_filter, {"$set": update_data})
                # print(f"Update - RESULT: {result}")
                # Record update history for the first matched document (representative)
                if self.can_watch_update_history:
                    try:
                        doc_id = str(existing_doc.get("_id", ""))
                        if doc_id:
                            diff_before, diff_after = _compute_diff(existing_doc, update_data)
                            if diff_before or diff_after:
                                await OpsHistoryService.record_update(
                                    collection_name=self.collection_name,
                                    document_id=doc_id,
                                    data_before=diff_before,
                                    data_after=diff_after,
                                    operation_type="update_many",
                                    document_identifier=existing_doc.get("identifier"),
                                    updated_fields=list(diff_after.keys()),
                                    updated_by_user_id=updated_by_user_id,
                                )
                    except Exception as hist_err:
                        DebugService.app_debug_print(f"[DAO] History recording failed (update_many): {hist_err}", False)
                return result
            else:
                # print("Update - No fields to update")
                return UpdateResult(raw_result={"nModified": 0, "n": 0}, acknowledged=True)
        except Exception as e:
            print(f"Error in update: {e}")
            raise e

    async def update_to_push(self, item_id: str, array_field: Dict[str, Any]) -> bool:
        """
        Update a document by applying an update document (e.g. with a $push operator)
        to one or more array fields. The caller must provide the appropriate update operator.

        :param item_id: The string representation of the document's ObjectId.
        :param array_field: The update document for array fields. This may contain operators such as $push.
        :return: True if at least one document was modified, False otherwise.
        :raises Exception: Propagates any exceptions raised during the update.

        Usage Example:
            # Here, we assume that 'comments' is an array field.
            update_doc = {"$push": {"comments": {"user": "john", "comment": "Nice post!"}}}
            success = await mongo_helper.update_to_push("60c72b2f9af1b2e0d8e06c4a", update_doc)
        """
        try:
            filter_query = {"_id": ObjectId(item_id)}
            # validated_data = self.model_class(**array_field).dict(by_alias=True)
            print(f" \n\n\n filter_query : {filter_query} \n\n\n")
            print(f" \n\n\n array_field : {array_field} \n\n\n")
            result = await self.collection.update_one(filter_query, array_field)
            print(f" \n\n\n result update_to_push : {result} \n\n\n")
            # ok = result.get('ok',-1)
            # if ok == -1:
            #     return result.modified_count > 0
            # else:
            #     return result.ok
            return result.modified_count > 0
        except Exception as err:
            print(f"Error in update_to_push with _id: {item_id} and update: {array_field}. Error: {err}")
            logging.error(
                f"Error in update_to_push with _id: {item_id} and update: {array_field}. Error: {err}"
            )
            raise err

    async def update_to_pull(self, item_id: str, array_field: Dict[str, Any]) -> bool:
        """
        Update a document by applying an update document (e.g. with a $pull operator)
        to one or more array fields. The caller must provide the appropriate update operator.

        :param item_id: The string representation of the document's ObjectId.
        :param array_field: The update document for array fields. This may contain operators such as $pull.
        :return: True if at least one document was modified, False otherwise.
        :raises Exception: Propagates any exceptions raised during the update.

        Usage Example:
            # Remove any comment with the specified comment_id.
            update_doc = {"$pull": {"comments": {"comment_id": "abc123"}}}
            success = await mongo_helper.update_to_pull("60c72b2f9af1b2e0d8e06c4a", update_doc)
        """
        try:
            filter_query = {"_id": ObjectId(item_id)}
            result = await self.collection.update_one(filter_query, array_field)
            return result.modified_count > 0
        except Exception as err:
            logging.error(
                f"Error in update_to_pull with _id: {item_id} and update: {array_field}. Error: {err}"
            )
            raise err

    async def update_to_remove_from_array(self, item_id: str, array_field: Dict[str, Any]) -> bool:
        """
        Update a document by applying an update document to remove elements from an array.
        The caller should provide the appropriate update operator (e.g., $pull).

        :param item_id: The string representation of the document's ObjectId.
        :param array_field: The update document containing the $pull operator and criteria.
        :return: True if at least one document was modified, False otherwise.
        :raises Exception: Propagates any exceptions raised during the update.

        Usage Example:
            # Remove any comment with the specified comment_id.
            update_doc = {"$pull": {"comments": {"comment_id": "abc123"}}}
            success = await mongo_helper.update_to_remove_from_array("60c72b2f9af1b2e0d8e06c4a", update_doc)
        """
        try:
            filter_query = {"_id": ObjectId(item_id)}
            result = await self.collection.update_one(filter_query, array_field)
            # ok = result.get('ok',-1)
            # if ok == -1:
            #     return result.modified_count > 0
            # else:
            #     return result.ok
            return result.modified_count > 0
        except Exception as err:
            logging.error(
                f"Error in update_to_remove_from_array with _id: {item_id} and update: {array_field}. Error: {err}"
            )
            raise

    async def update_to_push_in_array(self, item_id: str, push_obj: Dict[str, Any]) -> bool:
        """
        Update a document by pushing a new element into an array field.
        This helper automatically wraps the provided object with the $push operator.

        :param item_id: The string representation of the document's ObjectId.
        :param push_obj: A dictionary where keys are the array field names and values are the elements to push.
        :return: True if at least one document was modified, False otherwise.
        :raises Exception: Propagates any exceptions raised during the update.

        Usage Example:
            # Add a new tag to the 'tags' array field.
            push_data = {"tags": "new_tag"}
            success = await mongo_helper.update_to_push_in_array("60c72b2f9af1b2e0d8e06c4a", push_data)
        """
        try:
            filter_query = {"_id": ObjectId(item_id)}
            result = await self.collection.update_one(filter_query, {"$push": push_obj})
            # ok = result.get('ok',-1)
            # if ok == -1:
            #     return result.modified_count > 0
            # else:
            #     return result.ok
            return result.modified_count > 0
        except Exception as err:
            logging.error(
                f"Error in update_to_push_in_array with _id: {item_id} and push_obj: {push_obj}. Error: {err}"
            )
            raise

    async def update_to_pull_from_array(self, item_id: str, pull_obj: Dict[str, Any]) -> bool:
        """
        Update a document by pulling (removing) elements from an array field.
        This helper automatically wraps the provided object with the $pull operator.

        :param item_id: The string representation of the document's ObjectId.
        :param pull_obj: A dictionary where keys are the array field names and values specify the criteria for removal.
        :return: True if at least one document was modified, False otherwise.
        :raises Exception: Propagates any exceptions raised during the update.

        Usage Example:
            # Remove a specific tag from the 'tags' array field.
            pull_data = {"tags": "obsolete_tag"}
            success = await mongo_helper.update_to_pull_from_array("60c72b2f9af1b2e0d8e06c4a", pull_data)
        """
        try:
            filter_query = {"_id": ObjectId(item_id)}
            result = await self.collection.update_one(filter_query, {"$pull": pull_obj})
            print(f'\n\n\n result > update_to_pull_from_array: {result} \n\n')
            # ok = result.get('ok',-1)
            # if ok == -1:
            #     return result.modified_count > 0
            # else:
            #     return result.ok
            return result.modified_count > 0
        except Exception as err:
            logging.error(
                f"Error in update_to_pull_from_array with _id: {item_id} and pull_obj: {pull_obj}. Error: {err}"
            )
            raise

    async def update_to_update_in_array(self, match_obj: Dict[str, Any], set_obj: Dict[str, Any]) -> bool:
        """
        Update a document based on a match filter by setting new values in the document.
        This helper is designed to update fields (possibly within an array) by applying the $set operator.

        :param match_obj: The filter criteria to find the document (or sub-document) to update.
        :param set_obj: The update document specifying the new field values (to be wrapped with $set).
        :return: True if at least one document was modified, False otherwise.
        :raises Exception: Propagates any exceptions raised during the update.

        Usage Example:
            # Update an element inside an array or a nested field.
            match_filter = {"_id": ObjectId("60c72b2f9af1b2e0d8e06c4a"), "comments.comment_id": "abc123"}
            update_data = {"comments.$.text": "Updated comment text"}
            success = await mongo_helper.update_to_update_in_array(match_filter, update_data)
        """
        try:
            result = await self.collection.update_one(match_obj, {"$set": set_obj})
            # ok = result.get('ok',-1)
            # if ok == -1:
            #     return result.modified_count > 0
            # else:
            #     return result.ok
            return result.modified_count > 0
        except Exception as err:
            logging.error(
                f"Error in update_to_update_in_array with match_obj: {match_obj} and set_obj: {set_obj}. Error: {err}"
            )
            raise

    async def soft_delete(self, item_id: str,accept_language: Optional[str] = DEFAULT_LANGUAGE,by_pass_exception:Optional[bool] = False) -> bool:
        """Soft delete a document by setting the soft_deleted_at timestamp."""
        # Check delete_if_not_used_in constraint before soft deletion
        model_name = self.model_class.__name__.lower()
        try:
            # Check if any field has delete_if_not_used_in constraint
            for field_name, field in self.model_class.model_fields.items():
                meta = field.json_schema_extra or {}
                delete_if_not_used_in = meta.get("extra_metas", {}).get("delete_if_not_used_in", "")

                if delete_if_not_used_in and delete_if_not_used_in.lower() != "none":
                    # Split the comma-separated collection keys
                    collection_keys = [key.strip() for key in delete_if_not_used_in.split(",") if key.strip() and key.strip().lower() != "none"]

                    message = ResponseService.get_response_message(MessageCategory.EXIST_EXCEPTIONS, "CAN_NOT_DELETE_ITEM_IN_USE", accept_language)
                    # Check each collection for references
                    DebugService.app_debug_print(f" collection_keys {collection_keys}", False)
                    for collection_key in collection_keys:
                        try:
                            model_name = ModelService.get_collection_name_from_collection_key(collection_key)
                            parent_field = f"{model_name}_id"
                            
                            from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
                            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)

                            if metadata:
                                # Create a DAO for the collection
                                dao = DAO(metadata.collection_name, metadata.model_class,is_read_only=True)
                                db_filter = {
                                    parent_field: ObjectId(item_id),
                                    "soft_deleted_at": None  # Exclude soft-deleted references
                                }
                                DebugService.app_debug_print(f"db_filter deletion :  {db_filter}")
                                cursor = dao.collection.find(db_filter)
                                documents = await cursor.to_list(length=None)
                                DebugService.app_debug_print(f"reference_count :  {documents}")
                                if len(documents) > 0:
                                    raise ValueError(
                                        message
                                        # f"Cannot soft delete: Item is referenced in {collection_key} collection"
                                    )
                        except ValueError as ve:
                            if by_pass_exception == True:
                                return False
                            raise ve
                        except Exception as e:
                            DebugService.app_debug_print(f"Error checking references in {collection_key}: {e}", False)
                            if by_pass_exception == True:
                                return False
                            raise

            # Check for cascade delete with custom field name
            for field_name, field in self.model_class.model_fields.items():
                meta = field.json_schema_extra or {}
                delete_cascade_on_delete = meta.get("extra_metas", {}).get("delete_cascade_on_delete_with_custom_field_name", "")

                if delete_cascade_on_delete:
                    # Parse the cascade delete configuration
                    # Format: "<collection1,field1>,<collection2,field2>"
                    cascade_configs = []
                    for config in delete_cascade_on_delete.split('>,<'):
                        config = config.strip('<>').strip()
                        if ',' in config:
                            collection_key, field_name = config.split(',', 1)
                            cascade_configs.append((collection_key.strip(), field_name.strip()))

                    DebugService.app_debug_print(f"Cascade delete configs: {cascade_configs}", False)

                    # Process each cascade configuration
                    for collection_key, custom_field_name in cascade_configs:
                        try:
                            from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
                            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)

                            if metadata:
                                # Create a DAO for the collection
                                cascade_dao = DAO(metadata.collection_name, metadata.model_class, is_read_only=False)

                                # Find documents to cascade delete
                                db_filter = {
                                    custom_field_name: ObjectId(item_id),
                                    "soft_deleted_at": None  # Exclude already soft-deleted documents
                                }
                                DebugService.app_debug_print(f"Cascade soft delete filter: {db_filter}", False)

                                # Get documents to cascade delete
                                cursor = cascade_dao.collection.find(db_filter)
                                documents = await cursor.to_list(length=None)
                                DebugService.app_debug_print(f"Found {len(documents)} documents to cascade soft delete", False)

                                # Soft delete each document
                                for doc in documents:
                                    doc_id = str(doc["_id"])
                                    DebugService.app_debug_print(f"Cascade soft deleting document {doc_id} in {collection_key}", False)
                                    await cascade_dao.soft_delete(doc_id, accept_language, by_pass_exception)
                        except Exception as e:
                            DebugService.app_debug_print(f"Error in cascade soft delete for {collection_key}: {e}", False)
                            if by_pass_exception:
                                continue
                            raise

            # Proceed with soft deletion if no references found
            await self.pre_delete(item_id)
            result = await self.collection.update_one(
                {"_id": ObjectId(item_id)}, {"$set": {"soft_deleted_at": datetime.now(timezone.utc)}}
            )
            if result.modified_count > 0:
                await self.post_delete(item_id)
                return True
            return False
        except ValueError as ve:
            if by_pass_exception == True:
                return False
            raise ve
        except Exception as e:
            DebugService.app_debug_print(f"Error in soft_delete for item {item_id}: {e}", False)
            if by_pass_exception == True:
                return False
            raise


    async def delete(self, item_id: str,accept_language: Optional[str] = DEFAULT_LANGUAGE,by_pass_exception:Optional[bool] = False, deleted_by_user_id: Optional[str] = None, sys_organization_id: Optional[str] = None, sys_user_id: Optional[str] = None) -> bool:
        """Hard delete a document by ID with pre- and post-delete hooks."""
        # Check delete_if_not_used_in constraint before deletion
        try:
            for field_name, field in self.model_class.model_fields.items():
                meta = field.json_schema_extra or {}
                delete_if_not_used_in = meta.get("extra_metas", {}).get("delete_if_not_used_in", "")
                DebugService.app_debug_print(f"delete_if_not_used_in :  {field_name}, extra_metas : json_schema_extra : {delete_if_not_used_in}")
                if delete_if_not_used_in and delete_if_not_used_in.lower() != "none":
                    # Split the comma-separated collection keys
                    collection_keys = [key.strip() for key in delete_if_not_used_in.split(",") if key.strip() and key.strip().lower() != "none"]
                    # reference_field = f"{model_name}_id"
                    DebugService.app_debug_print(f"collection_keys :  {collection_keys}",False)

                    message = ResponseService.get_response_message(MessageCategory.EXIST_EXCEPTIONS, "CAN_NOT_DELETE_ITEM_IN_USE", accept_language)

                    # Check each collection for references
                    for collection_key in collection_keys:
                        DebugService.app_debug_print(f"collection_key :  {collection_key}",False)
                        try:
                            from app.modules.core.models.mapping_keys import CollectionKey
                            model_name = ModelService.get_collection_name_from_collection_key(CollectionKey(collection_key))
                            parent_field = f"{model_name}_id"

                            from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
                            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
                            DebugService.app_debug_print(f"metadata :  {metadata}")
                            if metadata:
                                # Create a DAO for the collection
                                dao = DAO(metadata.collection_name, metadata.model_class,is_read_only=True)
                                db_filter = {
                                    parent_field: ObjectId(item_id),
                                    "soft_deleted_at": None  # Exclude soft-deleted references
                                }
                                DebugService.app_debug_print(f"db_filter deletion :  {db_filter}")
                                cursor = dao.collection.find(db_filter)
                                documents = await cursor.to_list(length=None)
                                DebugService.app_debug_print(f"reference_count :  {documents}")
                                if len(documents) > 0:
                                    raise ValueError(
                                        message
                                        # f"Cannot delete: Item is referenced in {collection_key} collection"
                                    )
                        except ValueError as ve:
                            DebugService.app_debug_print(f"Error checking references in >>< {collection_key}: {ve}", False)
                            if by_pass_exception == True:
                                return False
                            raise ve
                        except Exception as e:
                            DebugService.app_debug_print(f"Error checking references in {collection_key}: {e}", False)
                            if by_pass_exception == True:
                                return False
                            raise



            # Check for cascade delete with custom field name
            for field_name, field in self.model_class.model_fields.items():
                meta = field.json_schema_extra or {}
                delete_cascade_on_delete = meta.get("extra_metas", {}).get("delete_cascade_on_delete_with_custom_field_name", "")

                if delete_cascade_on_delete:
                    # Parse the cascade delete configuration
                    # Format: "<collection1,field1>,<collection2,field2>"
                    cascade_configs = []
                    for config in delete_cascade_on_delete.split('>,<'):
                        config = config.strip('<>').strip()
                        if ',' in config:
                            collection_key, field_name = config.split(',', 1)
                            cascade_configs.append((collection_key.strip(), field_name.strip()))

                    DebugService.app_debug_print(f"Cascade delete configs: {cascade_configs}", False)

                    # Process each cascade configuration
                    for collection_key, custom_field_name in cascade_configs:
                        try:
                            from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
                            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)

                            if metadata:
                                # Create a DAO for the collection
                                cascade_dao = DAO(metadata.collection_name, metadata.model_class, is_read_only=False)

                                # Find documents to cascade delete
                                db_filter = {
                                    custom_field_name: ObjectId(item_id),
                                    "soft_deleted_at": None  # Exclude already soft-deleted documents
                                }
                                DebugService.app_debug_print(f"Cascade hard delete filter: {db_filter}", False)

                                # Get documents to cascade delete
                                cursor = cascade_dao.collection.find(db_filter)
                                documents = await cursor.to_list(length=None)
                                DebugService.app_debug_print(f"Found {len(documents)} documents to cascade hard delete", False)

                                # Hard delete each document
                                for doc in documents:
                                    doc_id = str(doc["_id"])
                                    DebugService.app_debug_print(f"Cascade hard deleting document {doc_id} in {collection_key}", False)
                                    await cascade_dao.delete(doc_id, accept_language, by_pass_exception)
                        except Exception as e:
                            DebugService.app_debug_print(f"Error in cascade hard delete for {collection_key}: {e}", False)
                            if by_pass_exception:
                                continue
                            raise

            # Proceed with deletion if no references found
            # Snapshot the document before deletion for history
            doc_to_delete = await self.collection.find_one({"_id": ObjectId(item_id)})
            await self.pre_delete(item_id)
            result = await self.collection.delete_one({"_id": ObjectId(item_id)})
            if result.deleted_count > 0:
                # Also remove from view collection
                await self._remove_from_view({"_id": ObjectId(item_id)})
                # Record delete history only if the flag is enabled for this collection
                if self.can_watch_delete_history:
                    try:
                        if doc_to_delete:
                            await OpsHistoryService.record_delete(
                                collection_name=self.collection_name,
                                document_id=item_id,
                                data_before=doc_to_delete,
                                operation_type="hard_delete",
                                deleted_by_user_id=deleted_by_user_id,
                            )
                    except Exception as hist_err:
                        DebugService.app_debug_print(f"[DAO] History recording failed (delete): {hist_err}", False)

                # Record organization CRUD log (fire-and-forget)
                if sys_organization_id and sys_user_id:
                    OpsLogService.record_log_background(
                        crud_type="delete",
                        collection_name=self.collection_name,
                        sys_organization_id=sys_organization_id,
                        sys_user_id=sys_user_id,
                        document_id=item_id,
                        description_str=f"Deleted {self.collection_name}/{item_id}",
                    )

                await self.post_delete(item_id)
                return True
            return False
        except ValueError as ve:
            format_error = format_exception("Error in delete", ve)
            DebugService.app_debug_print(f"Error in delete for item {item_id}: {format_error}", True)
            if by_pass_exception == True:
                return False
            raise ve
        except Exception as e:
            format_error = format_exception("Error in delete", e)
            DebugService.app_debug_print(f"Error in delete for item {item_id}: {format_error}", True)
            if by_pass_exception == True:
                return False
            raise e
        
    async def delete_with_query(self, delete_query: Dict[str, Any],accept_language: Optional[str] = DEFAULT_LANGUAGE,by_pass_exception:Optional[bool] = False) -> bool:
        """Hard delete a document by ID with pre- and post-delete hooks."""
        from app.modules.core.utils.helpers.line_helper import format_exception, line_info

        # Check delete_if_not_used_in constraint before deletion
        try:
            for field_name, field in self.model_class.model_fields.items():
                meta = field.json_schema_extra or {}
                delete_if_not_used_in = meta.get("extra_metas", {}).get("delete_if_not_used_in", "")
                DebugService.app_debug_print(f"delete_if_not_used_in: {field_name}, extra_metas: {delete_if_not_used_in}")

                if delete_if_not_used_in and delete_if_not_used_in.lower() != "none":
                    # Split the comma-separated collection keys
                    collection_keys = [key.strip() for key in delete_if_not_used_in.split(",") if key.strip() and key.strip().lower() != "none"]
                    DebugService.app_debug_print(f"collection_keys: {collection_keys}", False)

                    message = ResponseService.get_response_message(MessageCategory.EXIST_EXCEPTIONS, "CAN_NOT_DELETE_ITEM_IN_USE", accept_language)

                    # Check each collection for references
                    for collection_key in collection_keys:
                        DebugService.app_debug_print(f"Checking collection_key: {collection_key}", False)
                        try:
                            from app.modules.core.models.mapping_keys import CollectionKey
                            model_name = ModelService.get_collection_name_from_collection_key(CollectionKey(collection_key))
                            parent_field = f"{model_name}_id"

                            from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
                            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
                            DebugService.app_debug_print(f"metadata: {metadata}")

                            if metadata:
                                # Create a DAO for the collection
                                dao = DAO(metadata.collection_name, metadata.model_class, is_read_only=True)

                                # Fix: Extract the actual ID value from delete_query
                                delete_id = delete_query.get("_id") if "_id" in delete_query else delete_query

                                db_filter = {
                                    parent_field: delete_id,
                                    "soft_deleted_at": None  # Exclude soft-deleted references
                                }
                                DebugService.app_debug_print(f"db_filter deletion: {db_filter}")

                                cursor = dao.collection.find(db_filter)
                                documents = await cursor.to_list(length=None)
                                DebugService.app_debug_print(f"Found {len(documents)} references in {collection_key}")

                                if len(documents) > 0:
                                    enhanced_message = line_info(f"{message} (Referenced in {collection_key})")
                                    raise ValueError(enhanced_message)

                        except ValueError as ve:
                            error_detail = format_exception(f"Reference check failed in {collection_key}", ve)
                            DebugService.app_debug_print(error_detail, True)
                            if by_pass_exception:
                                return False
                            raise ve
                        except Exception as e:
                            error_detail = format_exception(f"Error checking references in {collection_key}", e)
                            DebugService.app_debug_print(error_detail, True)
                            if by_pass_exception:
                                return False
                            raise



            # Check for cascade delete with custom field name
            for field_name, field in self.model_class.model_fields.items():
                meta = field.json_schema_extra or {}
                delete_cascade_on_delete = meta.get("extra_metas", {}).get("delete_cascade_on_delete_with_custom_field_name", "")

                if delete_cascade_on_delete:
                    # Parse the cascade delete configuration
                    # Format: "<collection1,field1>,<collection2,field2>"
                    cascade_configs = []
                    for config in delete_cascade_on_delete.split('>,<'):
                        config = config.strip('<>').strip()
                        if ',' in config:
                            collection_key, cascade_field_name = config.split(',', 1)
                            cascade_configs.append((collection_key.strip(), cascade_field_name.strip()))

                    DebugService.app_debug_print(f"Cascade delete configs: {cascade_configs}", False)

                    # Process each cascade configuration
                    for collection_key, custom_field_name in cascade_configs:
                        try:
                            from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
                            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)

                            if metadata:
                                # Create a DAO for the collection
                                cascade_dao = DAO(metadata.collection_name, metadata.model_class, is_read_only=False)

                                # Fix: Extract the actual ID value from delete_query
                                delete_id = delete_query.get("_id") if "_id" in delete_query else delete_query

                                # Find documents to cascade delete
                                db_filter = {
                                    custom_field_name: delete_id,
                                    "soft_deleted_at": None  # Exclude already soft-deleted documents
                                }
                                DebugService.app_debug_print(f"Cascade hard delete filter: {db_filter}", False)

                                # Get documents to cascade delete
                                cursor = cascade_dao.collection.find(db_filter)
                                documents = await cursor.to_list(length=None)
                                DebugService.app_debug_print(f"Found {len(documents)} documents to cascade hard delete", False)

                                # Hard delete each document
                                for doc in documents:
                                    doc_id = str(doc["_id"])
                                    DebugService.app_debug_print(f"Cascade hard deleting document {doc_id} in {collection_key}", False)
                                    await cascade_dao.delete(doc_id, accept_language, by_pass_exception)

                        except Exception as e:
                            error_detail = format_exception(f"Error in cascade hard delete for {collection_key}", e)
                            DebugService.app_debug_print(error_detail, True)
                            if by_pass_exception:
                                continue
                            raise

            # Proceed with deletion if no references found
            # Snapshot the document before deletion for history
            doc_to_delete = await self.collection.find_one(delete_query)
            await self.pre_delete(delete_query)
            result = await self.collection.delete_one(delete_query)
            if result.deleted_count > 0:
                # Also remove from view collection
                await self._remove_from_view(delete_query)
                # Record delete history only if the flag is enabled for this collection
                if self.can_watch_delete_history:
                    try:
                        if doc_to_delete:
                            await OpsHistoryService.record_delete(
                                collection_name=self.collection_name,
                                document_id=str(doc_to_delete.get("_id", "")),
                                data_before=doc_to_delete,
                                operation_type="hard_delete_with_query",
                            )
                    except Exception as hist_err:
                        DebugService.app_debug_print(f"[DAO] History recording failed (delete_with_query): {hist_err}", False)
                await self.post_delete(delete_query)
                DebugService.app_debug_print(f"Successfully deleted document with query: {delete_query}", True)
                return True
            else:
                DebugService.app_debug_print(f"No document found to delete with query: {delete_query}", True)
                return False

        except ValueError as ve:
            # ValueError is typically from reference checks - already has line info
            if by_pass_exception:
                return False
            raise ve
        except Exception as e:
            error_detail = format_exception("Unexpected error during deletion", e)
            DebugService.app_debug_print(error_detail, True)
            if by_pass_exception:
                return False
            raise
        

    async def delete_many(self, query: Dict[str, Any],accept_language: Optional[str] = DEFAULT_LANGUAGE,by_pass_exception:Optional[bool] = False) -> bool:
        """Hard delete a document by ID with pre- and post-delete hooks."""
        try:
            # Snapshot all documents before bulk deletion for history
            docs_to_delete = []
            try:
                cursor = self.collection.find(query)
                docs_to_delete = await cursor.to_list(length=None)
            except Exception:
                pass
            result = await self.collection.delete_many(query)
            if result.deleted_count > 0:
                # Also remove from view collection
                await self._remove_from_view(query)
                # Record delete history for each deleted document only if the flag is enabled
                if self.can_watch_delete_history:
                    for doc in docs_to_delete:
                        try:
                            await OpsHistoryService.record_delete(
                                collection_name=self.collection_name,
                                document_id=str(doc.get("_id", "")),
                                data_before=doc,
                                operation_type="delete_many",
                            )
                        except Exception as hist_err:
                            DebugService.app_debug_print(f"[DAO] History recording failed (delete_many): {hist_err}", False)
                return True
            return False
        except Exception as e:
            DebugService.app_debug_print(f"Error checking references in delete_many: {e}", False)
            if by_pass_exception == True:
                return False
            raise e

    async def upsert(self, filter_data: Dict[str, Any], update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform an upsert operation:
        - If a document exists based on `filter_data`, update it with `update_data`.
        - If a document does not exist, insert a new document with the combined data.
        """
        DebugService.app_debug_print(f"\n\n\n\n step 1: [filter_data] : {filter_data} | [update_data] : {update_data} \n\n\n",False)

        # static_filter_data = self.convert_id_fields(filter_data)
        static_filter_data = ConverterService.track_saving_data_to_objectid(filter_data)
        update_data = ConverterService.track_saving_data_to_objectid(update_data)

        DebugService.app_debug_print(f"\n\n\n\n step 2: converted [filter_data] : {filter_data} \n\n\n",False)

        exist_doc = await self.collection.find_one(static_filter_data)
        DebugService.app_debug_print(f"\n\n\n\n step 3: doc existance [exist_doc] : {exist_doc} \n\n\n",False)

        if not exist_doc:
            # Si le document n'existe pas, créer un nouveau document
            combined_data = {**filter_data, **update_data}
            # Convertir les enums en valeurs avant la validation
            combined_data = ConverterService.convert_enums_to_values(combined_data)
            validated_data = self.model_class(**combined_data).dict(by_alias=True)
            validated_data["created_at"] = datetime.now(timezone.utc)
            validated_data["updated_at"] = datetime.now(timezone.utc)

            inserted_id = await self.add(validated_data)
            exist_doc = await self.collection.find_one({"_id": ObjectId(inserted_id)})
        else:
            # Snapshot before update for history
            _upsert_snapshot_before = dict(exist_doc)
            # Si le document existe, mettre à jour uniquement les champs fournis
            update_data = await self.pre_update(update_data)
            # Convertir les enums en valeurs avant la mise à jour
            update_data = ConverterService.convert_enums_to_values(update_data)
            update_data["updated_at"] = datetime.now(timezone.utc)
            # Ne pas inclure les champs qui ne sont pas dans update_data
            update_operation = {"$set": update_data}

            result = await self.collection.update_one(static_filter_data, update_operation)
            exist_doc = await self.collection.find_one(static_filter_data)

            # Record upsert (update branch) history
            if self.can_watch_update_history:
                try:
                    doc_id = str(_upsert_snapshot_before.get("_id", ""))
                    if doc_id:
                        diff_before, diff_after = _compute_diff(_upsert_snapshot_before, update_data)
                        if diff_before or diff_after:
                            await OpsHistoryService.record_update(
                                collection_name=self.collection_name,
                                document_id=doc_id,
                                data_before=diff_before,
                                data_after=diff_after,
                                operation_type="upsert",
                                document_identifier=_upsert_snapshot_before.get("identifier"),
                                updated_fields=list(diff_after.keys()),
                            )
                except Exception as hist_err:
                    DebugService.app_debug_print(f"[DAO] History recording failed (upsert): {hist_err}", False)

        # Vérifier si le document existe toujours après l'opération
        if not exist_doc:
            raise ValueError("Le document n'a pas pu être créé ou mis à jour")

        # Ensure both id and _id fields are set correctly
        # print(f"\n\n\n\n\n\n  VALUUUU : {exist_doc}")
        # print(f"\n\n\n\n\n\n  VALUUUU : {True if '_id' in exist_doc else False}")
        if '_id' in exist_doc:
            # Convert ObjectId to string and ensure id field exists
            id_str = str(exist_doc["_id"])
            # exist_doc["_id"] = id_str
            exist_doc["id"] = id_str
        # print(f"\n\n\n\n\n\n  VALUUUU LAST : {exist_doc}")
        return exist_doc



    async def find(
        self,
        query: Dict[str, Any],
        projection: Optional[Dict[str, int]] = None,
        skip: int = 0,
        limit: int = 0,
        sort: Optional[Dict[str, int]] = {"created_at": -1},
        # sort: Optional[List[Tuple[str, int]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find multiple documents matching a query, excluding soft-deleted documents.
        Uses global semaphore to prevent DB connection exhaustion.

        :param query: The query filter
        :param projection: Optional fields to include/exclude
        :param skip: Number of documents to skip (for pagination)
        :param limit: Maximum number of documents to return (0 means no limit)
        :param sort: List of (field_name, direction) tuples for sorting
        :return: List of matching documents
        """
        # Debug the incoming query
        DebugService.app_debug_print(f"\n\n\n DAO.find - Original query: {query} \n\n\n", False)

        # Make a copy of the query to avoid modifying the original
        filter_query = query.copy()

        # Remove pagination and output format parameters that might have been included
        filter_query.pop('output_data_type', None)
        filter_query.pop('all_data', None)
        filter_query.pop('page', None)
        filter_query.pop('limit', None)

        # Convert ID fields to ObjectId
        filter_query = self.convert_id_fields(filter_query)

        # Add soft delete filter only if the collection has this field
        # Check if the model has a soft_deleted_at field
        has_soft_delete = hasattr(self.model_class, 'soft_deleted_at')
        if has_soft_delete:
            filter_query["soft_deleted_at"] = None

        # Debug the processed query
        DebugService.app_debug_print(f"\n\n\n DAO.find - Processed filter: {filter_query} \n\n\n", False)

        # Use global semaphore to limit concurrent DB operations
        async with get_db_semaphore():
            # Create the find operation
            find_operation = self.collection.find(filter_query, projection)

            # Apply skip if provided
            if skip > 0:
                find_operation = find_operation.skip(skip)

            # Apply limit if provided (0 means no limit)
            if limit > 0:
                find_operation = find_operation.limit(limit)

            # Apply sort if provided
            if sort:
                # Convert the list of tuples to a list of tuples with pymongo sort direction
                sort_list = [(field, direction) for field, direction in sort]
                find_operation = find_operation.sort(sort_list)

            # Execute the query and collect results
            results = []
            async for doc in find_operation:
                # Convert ObjectId to string and ensure id field exists
                if "_id" in doc:
                    id_str = str(doc["_id"])
                    doc["_id"] = id_str
                    doc["id"] = id_str
                results.append(doc)

        # Debug the results count
        DebugService.app_debug_print(f"\n\n\n DAO.find - Found {len(results)} documents \n\n\n", False)

        return results

    async def find_one(self, query: Dict[str, Any], projection: Optional[Dict[str, int]] = None) -> Optional[Dict[str, Any]]:
        """
        Find a single document matching a query, excluding soft-deleted documents.
        Uses global semaphore to prevent DB connection exhaustion.
        """
        query = self.convert_id_fields(query)
        query["soft_deleted_at"] = None
        
        # Use global semaphore to limit concurrent DB operations
        async with get_db_semaphore():
            document = await self.collection.find_one(query, projection)
        if document and "_id" in document:
            # Convert ObjectId to string and ensure id field exists
            id_str = str(document["_id"])
            document["_id"] = id_str
            document["id"] = id_str
        return document

    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Perform aggregation, excluding soft-deleted documents.
        Uses global semaphore to prevent DB connection exhaustion.
        """
        match_stage = {"$match": {"soft_deleted_at": None}}
        pipeline.insert(0, match_stage)
        results = []
        
        # Use global semaphore to limit concurrent DB operations
        async with get_db_semaphore():
            cursor = self.collection.aggregate(pipeline)
            async for doc in cursor:
                if "_id" in doc:
                    # Convert ObjectId to string and ensure id field exists
                    id_str = str(doc["_id"])
                    doc["_id"] = id_str
                    doc["id"] = id_str
                results.append(doc)
        return results
