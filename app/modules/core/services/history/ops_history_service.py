# app/modules/core/services/history/ops_history_service.py
"""
Service for recording update and delete history entries.

This service is called from the DAO layer (pre_update / pre_delete hooks)
so that every mutating operation is transparently audited.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.db.base import get_collection
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.debug.debug_service import DebugService


class OpsHistoryService:
    """Lightweight, import-safe service – uses raw Motor collections to
    avoid circular imports with DAO / model mapping."""

    # Collection names derived directly from the CollectionKey enum values
    _UPDATE_COLLECTION = CollectionKey.OPS_UPDATE_HISTORY.model_name   # "ops_update_history"
    _DELETE_COLLECTION = CollectionKey.OPS_DELETE_HISTORY.model_name   # "ops_delete_history"

    # ------------------------------------------------------------------ #
    #  UPDATE HISTORY
    # ------------------------------------------------------------------ #

    @classmethod
    async def record_update(
        cls,
        collection_name: str,
        document_id: str,
        data_before: Dict[str, Any],
        data_after: Dict[str, Any],
        operation_type: str = "update",
        collection_key: Optional[str] = None,
        updated_by_user_id: Optional[str] = None,
        document_identifier: Optional[str] = None,
        updated_fields: Optional[list] = None,
    ) -> Optional[str]:
        """
        Insert a new entry into ``opsUpdateHistories``.

        Args:
            collection_name:  snake_case model name of the source collection.
            document_id:      ``_id`` of the updated document (as string).
            data_before:      snapshot of the document *before* the update.
            data_after:       the ``$set`` payload (or full doc after upsert).
            operation_type:   ``update`` | ``upsert`` | ``update_many`` | ``patch``.
            collection_key:   optional camelCase CollectionKey value.
            updated_by_user_id: optional user id who triggered the change.
            document_identifier: optional short identifier of the updated document.

        Returns:
            The inserted document's ``_id`` as string, or ``None`` on failure.
        """
        try:
            col = get_collection(cls._UPDATE_COLLECTION)
            now = datetime.now(timezone.utc)

            entry: Dict[str, Any] = {
                "collection_name": collection_name,
                "collection_key": collection_key,
                "document_id": str(document_id),
                "document_identifier": document_identifier,
                "operation_type": operation_type,
                "data_before": cls._sanitize_for_mongo(data_before),
                "data_after": cls._sanitize_for_mongo(data_after),
                "updated_fields": updated_fields or [],
                "updated_by_user_id": ObjectId(updated_by_user_id) if updated_by_user_id else None,
                "updated_at_utc": now,
                # TimestampMixin-compatible fields
                "created_at": now,
                "updated_at": now,
                "soft_deleted_at": None,
                "soft_deleted": False,
                "is_activated": True,
            }

            result = await col.insert_one(entry)
            DebugService.app_debug_print(
                f"[OpsHistory] Recorded UPDATE history for {collection_name}/{document_id}", True
            )
            return str(result.inserted_id)
        except Exception as exc:
            # History recording should NEVER break the main operation
            logging.warning(f"[OpsHistory] Failed to record update history: {exc}")
            DebugService.app_debug_print(
                f"[OpsHistory] ⚠️ Failed to record update history: {exc}", False
            )
            return None

    # ------------------------------------------------------------------ #
    #  DELETE HISTORY
    # ------------------------------------------------------------------ #

    @classmethod
    async def record_delete(
        cls,
        collection_name: str,
        document_id: str,
        data_before: Dict[str, Any],
        operation_type: str = "hard_delete",
        collection_key: Optional[str] = None,
        deleted_by_user_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Insert a new entry into ``opsDeleteHistories``.

        Args:
            collection_name:   snake_case model name of the source collection.
            document_id:       ``_id`` of the deleted document (as string).
            data_before:       full snapshot of the document at deletion time.
            operation_type:    ``hard_delete`` | ``hard_delete_with_query`` | ``delete_many``.
            collection_key:    optional camelCase CollectionKey value.
            deleted_by_user_id: optional user id who triggered the deletion.

        Returns:
            The inserted document's ``_id`` as string, or ``None`` on failure.
        """
        try:
            col = get_collection(cls._DELETE_COLLECTION)
            now = datetime.now(timezone.utc)

            entry: Dict[str, Any] = {
                "collection_name": collection_name,
                "collection_key": collection_key,
                "document_id": str(document_id),
                "operation_type": operation_type,
                "data_before": cls._sanitize_for_mongo(data_before),
                "deleted_by_user_id": ObjectId(deleted_by_user_id) if deleted_by_user_id else None,
                "deleted_at_utc": now,
                # TimestampMixin-compatible fields
                "created_at": now,
                "updated_at": now,
                "soft_deleted_at": None,
                "soft_deleted": False,
                "is_activated": True,
            }

            result = await col.insert_one(entry)
            DebugService.app_debug_print(
                f"[OpsHistory] Recorded DELETE history for {collection_name}/{document_id}", True
            )
            return str(result.inserted_id)
        except Exception as exc:
            logging.warning(f"[OpsHistory] Failed to record delete history: {exc}")
            DebugService.app_debug_print(
                f"[OpsHistory] ⚠️ Failed to record delete history: {exc}", False
            )
            return None

    # ------------------------------------------------------------------ #
    #  RESTORE HELPER
    # ------------------------------------------------------------------ #

    @classmethod
    async def restore_from_delete_history(
        cls,
        history_entry_id: str,
        restored_by_user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Restore a previously deleted document using its delete-history entry.

        The ``data_before`` snapshot stored at deletion time is re-inserted into
        the original collection.  A new ``_id`` is generated so there is no
        conflict with any document that may have been re-created in the
        meantime.  The history entry is then soft-deleted so it no longer
        appears in the active delete-history feed.

        Args:
            history_entry_id:    ``_id`` of the delete-history entry.
            restored_by_user_id: optional user id who triggered the restore.

        Returns:
            The restored document (with its new ``_id``), or ``None`` on failure.
        """
        try:
            history_col = get_collection(cls._DELETE_COLLECTION)

            # 1. Fetch the history entry
            entry = await history_col.find_one({"_id": ObjectId(history_entry_id), "soft_deleted_at": None})
            if not entry:
                logging.warning(f"[OpsHistory] Delete-history entry {history_entry_id} not found or already restored.")
                return None

            data_before: Dict[str, Any] = entry.get("data_before", {})
            if not data_before:
                logging.warning(f"[OpsHistory] Delete-history entry {history_entry_id} has no data_before snapshot.")
                return None

            collection_name: str = entry.get("collection_name", "")
            if not collection_name:
                logging.warning(f"[OpsHistory] Delete-history entry {history_entry_id} has no collection_name.")
                return None

            # 2. Prepare the document for re-insertion
            restored_doc = dict(data_before)
            # Remove old _id so Mongo generates a fresh one
            restored_doc.pop("_id", None)
            restored_doc.pop("id", None)
            # Reset soft-delete fields
            now = datetime.now(timezone.utc)
            restored_doc["soft_deleted_at"] = None
            restored_doc["soft_deleted"] = False
            restored_doc["updated_at"] = now
            restored_doc["restored_at"] = now
            restored_doc["restored_by_user_id"] = ObjectId(restored_by_user_id) if restored_by_user_id else None

            # Convert string ObjectIds back to real ObjectIds for known _id fields
            restored_doc = cls._rehydrate_object_ids(restored_doc)

            # 3. Re-insert into the original collection
            target_col = get_collection(collection_name)
            result = await target_col.insert_one(restored_doc)
            restored_doc["_id"] = str(result.inserted_id)

            # 4. Soft-delete the history entry so it's marked as restored
            await history_col.update_one(
                {"_id": ObjectId(history_entry_id)},
                {"$set": {
                    "soft_deleted_at": now,
                    "soft_deleted": True,
                    "restored_at": now,
                    "restored_by_user_id": ObjectId(restored_by_user_id) if restored_by_user_id else None,
                    "restored_document_id": str(result.inserted_id),
                }},
            )

            DebugService.app_debug_print(
                f"[OpsHistory] Restored document from delete-history {history_entry_id} → {collection_name}/{result.inserted_id}",
                True,
            )
            return cls._sanitize_for_mongo(restored_doc)

        except Exception as exc:
            logging.warning(f"[OpsHistory] Failed to restore from delete history: {exc}")
            DebugService.app_debug_print(
                f"[OpsHistory] ⚠️ Failed to restore from delete history: {exc}", False
            )
            return None

    @classmethod
    async def restore_from_update_history(
        cls,
        history_entry_id: str,
        restored_by_user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Revert a document to its previous state using an update-history entry.

        The ``data_before`` snapshot stored at update time is written back
        to the document via ``$set``, effectively undoing the update.
        The history entry is then soft-deleted so it no longer appears in
        the active update-history feed.

        Args:
            history_entry_id:    ``_id`` of the update-history entry.
            restored_by_user_id: optional user id who triggered the revert.

        Returns:
            The reverted document dict, or ``None`` on failure.
        """
        try:
            history_col = get_collection(cls._UPDATE_COLLECTION)

            # 1. Fetch the history entry
            entry = await history_col.find_one({"_id": ObjectId(history_entry_id), "soft_deleted_at": None})
            if not entry:
                logging.warning(f"[OpsHistory] Update-history entry {history_entry_id} not found or already restored.")
                return None

            data_before: Dict[str, Any] = entry.get("data_before", {})
            if not data_before:
                logging.warning(f"[OpsHistory] Update-history entry {history_entry_id} has no data_before snapshot.")
                return None

            collection_name: str = entry.get("collection_name", "")
            document_id: str = entry.get("document_id", "")
            if not collection_name or not document_id:
                logging.warning(f"[OpsHistory] Update-history entry {history_entry_id} missing collection_name or document_id.")
                return None

            # 2. Prepare the revert payload (exclude _id and immutable fields)
            revert_data = dict(data_before)
            revert_data.pop("_id", None)
            revert_data.pop("id", None)
            revert_data.pop("created_at", None)

            now = datetime.now(timezone.utc)
            revert_data["updated_at"] = now
            revert_data["reverted_at"] = now
            revert_data["reverted_by_user_id"] = ObjectId(restored_by_user_id) if restored_by_user_id else None

            # Convert string ObjectIds back for _id-suffixed fields
            revert_data = cls._rehydrate_object_ids(revert_data)

            # 3. Update the document in the original collection
            target_col = get_collection(collection_name)
            result = await target_col.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": revert_data},
            )

            if result.matched_count == 0:
                logging.warning(f"[OpsHistory] Document {document_id} not found in {collection_name} for revert.")
                return None

            # 4. Soft-delete the history entry so it's marked as reverted
            await history_col.update_one(
                {"_id": ObjectId(history_entry_id)},
                {"$set": {
                    "soft_deleted_at": now,
                    "soft_deleted": True,
                    "reverted_at": now,
                    "reverted_by_user_id": ObjectId(restored_by_user_id) if restored_by_user_id else None,
                }},
            )

            # 5. Fetch the reverted document to return it
            reverted_doc = await target_col.find_one({"_id": ObjectId(document_id)})

            DebugService.app_debug_print(
                f"[OpsHistory] Reverted document from update-history {history_entry_id} → {collection_name}/{document_id}",
                True,
            )
            return cls._sanitize_for_mongo(reverted_doc)

        except Exception as exc:
            logging.warning(f"[OpsHistory] Failed to restore from update history: {exc}")
            DebugService.app_debug_print(
                f"[OpsHistory] ⚠️ Failed to restore from update history: {exc}", False
            )
            return None

    # ------------------------------------------------------------------ #
    #  QUERY HELPERS (used by the endpoints)
    # ------------------------------------------------------------------ #

    @classmethod
    async def get_update_history_for_document(
        cls,
        collection_name: str,
        document_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return paginated update history for a specific document."""
        col = get_collection(cls._UPDATE_COLLECTION)
        query = {
            "collection_name": collection_name,
            "document_id": str(document_id),
            "soft_deleted_at": None,
        }
        cursor = col.find(query).sort("updated_at_utc", -1).skip(skip).limit(limit)
        results = await cursor.to_list(length=limit)
        return cls._stringify_ids(results)

    @classmethod
    async def get_delete_history_for_collection(
        cls,
        collection_name: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return paginated deletion history for a whole collection."""
        col = get_collection(cls._DELETE_COLLECTION)
        query = {
            "collection_name": collection_name,
            "soft_deleted_at": None,
        }
        cursor = col.find(query).sort("deleted_at_utc", -1).skip(skip).limit(limit)
        results = await cursor.to_list(length=limit)
        return cls._stringify_ids(results)

    @classmethod
    async def get_update_history_paginated(
        cls,
        collection_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Return paginated update history, optionally filtered by collection_name.
        Joins minimal user info (first_name, last_name, email) from ``sys_user``
        when ``updated_by_user_id`` is present.
        Returns ``{items, total, skip, limit}``."""
        col = get_collection(cls._UPDATE_COLLECTION)
        query: Dict[str, Any] = {"soft_deleted_at": None}
        if collection_name:
            query["collection_name"] = collection_name

        total = await col.count_documents(query)

        pipeline: List[Dict[str, Any]] = [
            {"$match": query},
            {"$sort": {"updated_at_utc": -1}},
            {"$skip": skip},
            {"$limit": limit},
            # join user minimal info
            {
                "$lookup": {
                    "from": CollectionKey.SYS_USER.model_name,
                    "localField": "updated_by_user_id",
                    "foreignField": "_id",
                    "as": "_user_lookup",
                }
            },
            {
                "$addFields": {
                    "updated_by_user": {
                        "$cond": {
                            "if": {"$gt": [{"$size": "$_user_lookup"}, 0]},
                            "then": {
                                "first_name": {"$arrayElemAt": ["$_user_lookup.first_name", 0]},
                                "last_name": {"$arrayElemAt": ["$_user_lookup.last_name", 0]},
                                "email": {"$arrayElemAt": ["$_user_lookup.email", 0]},
                            },
                            "else": None,
                        }
                    }
                }
            },
            {"$project": {"_user_lookup": 0}},
        ]

        items = await col.aggregate(pipeline).to_list(length=limit)
        return {
            "items": cls._stringify_ids(items),
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    @classmethod
    async def get_delete_history_paginated(
        cls,
        collection_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Return paginated delete history, optionally filtered by collection_name.
        Joins minimal user info (first_name, last_name, email) from ``sys_user``
        when ``deleted_by_user_id`` is present.
        Returns ``{items, total, skip, limit}``."""
        col = get_collection(cls._DELETE_COLLECTION)
        query: Dict[str, Any] = {"soft_deleted_at": None}
        if collection_name:
            query["collection_name"] = collection_name

        total = await col.count_documents(query)

        pipeline: List[Dict[str, Any]] = [
            {"$match": query},
            {"$sort": {"deleted_at_utc": -1}},
            {"$skip": skip},
            {"$limit": limit},
            # join user minimal info
            {
                "$lookup": {
                    "from": CollectionKey.SYS_USER.model_name,
                    "localField": "deleted_by_user_id",
                    "foreignField": "_id",
                    "as": "_user_lookup",
                }
            },
            {
                "$addFields": {
                    "deleted_by_user": {
                        "$cond": {
                            "if": {"$gt": [{"$size": "$_user_lookup"}, 0]},
                            "then": {
                                "first_name": {"$arrayElemAt": ["$_user_lookup.first_name", 0]},
                                "last_name": {"$arrayElemAt": ["$_user_lookup.last_name", 0]},
                                "email": {"$arrayElemAt": ["$_user_lookup.email", 0]},
                            },
                            "else": None,
                        }
                    }
                }
            },
            {"$project": {"_user_lookup": 0}},
        ]

        items = await col.aggregate(pipeline).to_list(length=limit)
        return {
            "items": cls._stringify_ids(items),
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    @classmethod
    async def search_history_by_identifier(
        cls,
        identifier: str,
        history_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Search update and/or delete history by ``document_identifier`` or ``document_id``.

        Args:
            identifier:   value to match against ``document_identifier`` or ``document_id``.
            history_type: ``"update"`` | ``"delete"`` | ``None`` (both).
            skip / limit: pagination controls.

        Returns:
            ``{update_items, delete_items, total_update, total_delete}``
        """
        id_filter = {
            "$or": [
                {"document_identifier": {"$regex": identifier, "$options": "i"}},
                {"document_id": identifier},
            ],
            "soft_deleted_at": None,
        }

        result: Dict[str, Any] = {
            "update_items": [],
            "total_update": 0,
            "delete_items": [],
            "total_delete": 0,
            "skip": skip,
            "limit": limit,
        }

        if history_type in (None, "update"):
            update_col = get_collection(cls._UPDATE_COLLECTION)
            result["total_update"] = await update_col.count_documents(id_filter)
            cursor = update_col.find(id_filter).sort("updated_at_utc", -1).skip(skip).limit(limit)
            result["update_items"] = cls._stringify_ids(await cursor.to_list(length=limit))

        if history_type in (None, "delete"):
            delete_col = get_collection(cls._DELETE_COLLECTION)
            result["total_delete"] = await delete_col.count_documents(id_filter)
            cursor = delete_col.find(id_filter).sort("deleted_at_utc", -1).skip(skip).limit(limit)
            result["delete_items"] = cls._stringify_ids(await cursor.to_list(length=limit))

        return result

    @classmethod
    async def get_histories_for_identifier(
        cls,
        collection_name: str,
        identifier: str,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Fetch both update and delete histories for a specific document identifier
        within a given collection.

        Args:
            collection_name: the source collection's model name.
            identifier:      ``document_id`` or ``document_identifier`` of the target document.
            skip / limit:    pagination controls (applied independently to each list).

        Returns:
            ``{update_items, delete_items, total_update, total_delete}``
        """
        base_filter: Dict[str, Any] = {
            "collection_name": collection_name,
            "$or": [
                {"document_identifier": {"$regex": identifier, "$options": "i"}},
                {"document_id": identifier},
            ],
            "soft_deleted_at": None,
        }

        update_col = get_collection(cls._UPDATE_COLLECTION)
        delete_col = get_collection(cls._DELETE_COLLECTION)

        total_update = await update_col.count_documents(base_filter)
        total_delete = await delete_col.count_documents(base_filter)

        update_cursor = update_col.find(base_filter).sort("updated_at_utc", -1).skip(skip).limit(limit)
        delete_cursor = delete_col.find(base_filter).sort("deleted_at_utc", -1).skip(skip).limit(limit)

        update_items = cls._stringify_ids(await update_cursor.to_list(length=limit))
        delete_items = cls._stringify_ids(await delete_cursor.to_list(length=limit))

        return {
            "update_items": update_items,
            "delete_items": delete_items,
            "total_update": total_update,
            "total_delete": total_delete,
            "skip": skip,
            "limit": limit,
        }

    @classmethod
    async def count_update_history(cls, collection_name: str, document_id: str) -> int:
        """Count total update history entries for a document."""
        col = get_collection(cls._UPDATE_COLLECTION)
        return await col.count_documents({
            "collection_name": collection_name,
            "document_id": str(document_id),
            "soft_deleted_at": None,
        })

    @classmethod
    async def count_delete_history(cls, collection_name: str) -> int:
        """Count total delete history entries for a collection."""
        col = get_collection(cls._DELETE_COLLECTION)
        return await col.count_documents({
            "collection_name": collection_name,
            "soft_deleted_at": None,
        })

    # ------------------------------------------------------------------ #
    #  PRIVATE HELPERS
    # ------------------------------------------------------------------ #

    @staticmethod
    def _sanitize_for_mongo(data: Any) -> Any:
        """Recursively convert ObjectId → str and datetime → isoformat
        so the snapshot is safe to store as a plain dict."""
        if data is None:
            return None
        if isinstance(data, ObjectId):
            return str(data)
        if isinstance(data, datetime):
            return data.isoformat()
        if isinstance(data, dict):
            return {k: OpsHistoryService._sanitize_for_mongo(v) for k, v in data.items()}
        if isinstance(data, list):
            return [OpsHistoryService._sanitize_for_mongo(item) for item in data]
        return data

    @staticmethod
    def _stringify_ids(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert ``_id`` and ``*_id`` ObjectId fields to strings for JSON output."""
        for doc in docs:
            if "_id" in doc:
                doc["id"] = str(doc["_id"])
                doc["_id"] = str(doc["_id"])
            for key, val in doc.items():
                if isinstance(val, ObjectId):
                    doc[key] = str(val)
        return docs

    @staticmethod
    def _rehydrate_object_ids(data: Dict[str, Any]) -> Dict[str, Any]:
        """Best-effort conversion of string values back to ``ObjectId``
        for fields whose name ends with ``_id`` and whose value looks
        like a valid 24-hex ObjectId string."""
        for key, val in data.items():
            if key.endswith("_id") and isinstance(val, str) and len(val) == 24:
                try:
                    data[key] = ObjectId(val)
                except Exception:
                    pass
        return data
