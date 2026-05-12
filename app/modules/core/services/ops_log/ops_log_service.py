# app/modules/core/services/ops_log/ops_log_service.py
"""
Service for recording organization-level CRUD log entries.

Uses raw Motor collections (like OpsHistoryService) to avoid circular imports
with DAO / model mapping layers.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.db.base import get_collection
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.debug.debug_service import DebugService


class OpsLogService:
    """Lightweight service for recording and querying organization CRUD logs."""

    _LOG_COLLECTION = CollectionKey.OPS_ORGANIZATION_LOG.model_name
    _SETUP_COLLECTION = CollectionKey.CFG_OPS_LOG_SETUP.model_name

    # In-memory cache for setup docs to avoid repeated DB lookups on every operation.
    # Key: str(sys_organization_id), Value: dict with is_enabled, expiration_days, cached_at
    _setup_cache: Dict[str, Dict[str, Any]] = {}
    _CACHE_TTL_SECONDS = 60  # Re-fetch setup every 60s

    # ------------------------------------------------------------------ #
    #  SETUP CACHE
    # ------------------------------------------------------------------ #

    @classmethod
    async def _get_setup_for_org(cls, sys_organization_id: str) -> Optional[Dict[str, Any]]:
        """Return the log setup document for an organization (cached)."""
        now = datetime.now(timezone.utc)
        cached = cls._setup_cache.get(sys_organization_id)
        if cached and (now - cached["cached_at"]).total_seconds() < cls._CACHE_TTL_SECONDS:
            return cached

        try:
            col = get_collection(cls._SETUP_COLLECTION)
            doc = await col.find_one({
                "sys_organization_id": ObjectId(sys_organization_id),
                "soft_deleted": {"$ne": True},
            })
            if doc:
                entry = {
                    "is_enabled": doc.get("is_enabled", False),
                    "is_create_log_enabled": doc.get("is_create_log_enabled", False),
                    "is_read_log_enabled": doc.get("is_read_log_enabled", False),
                    "is_update_log_enabled": doc.get("is_update_log_enabled", False),
                    "is_delete_log_enabled": doc.get("is_delete_log_enabled", False),
                    "expiration_days": doc.get("expiration_days", 30),
                    "cached_at": now,
                }
                cls._setup_cache[sys_organization_id] = entry
                return entry
        except Exception as exc:
            logging.warning(f"[OpsLog] Failed to fetch setup for org {sys_organization_id}: {exc}")
        return None

    @classmethod
    def invalidate_cache(cls, sys_organization_id: str) -> None:
        """Remove a cached setup entry (call after setup update)."""
        cls._setup_cache.pop(sys_organization_id, None)

    # ------------------------------------------------------------------ #
    #  RECORD LOG
    # ------------------------------------------------------------------ #

    @classmethod
    async def record_log(
        cls,
        crud_type: str,
        collection_name: str,
        sys_organization_id: Optional[str] = None,
        sys_user_id: Optional[str] = None,
        collection_key: Optional[str] = None,
        document_id: Optional[str] = None,
        description_str: Optional[str] = None,
    ) -> Optional[str]:
        """
        Record a CRUD log entry if logging is enabled for the organization.

        Returns the inserted document's _id as string, or None if skipped/failed.
        """
        # If no user or no org, skip (anonymous / system-level ops not tracked)
        if not sys_user_id or not sys_organization_id:
            return None

        try:
            setup = await cls._get_setup_for_org(sys_organization_id)
            if not setup or not setup.get("is_enabled", False):
                return None

            # Check per-CRUD-type enablement
            _crud_flag_map = {
                "create": "is_create_log_enabled",
                "read": "is_read_log_enabled",
                "update": "is_update_log_enabled",
                "delete": "is_delete_log_enabled",
            }
            crud_flag_key = _crud_flag_map.get(crud_type)
            if crud_flag_key and not setup.get(crud_flag_key, False):
                return None

            now = datetime.now(timezone.utc)
            expiration_days = setup.get("expiration_days", 30)
            expires_at = now + timedelta(days=expiration_days)

            col = get_collection(cls._LOG_COLLECTION)
            entry: Dict[str, Any] = {
                "sys_organization_id": ObjectId(sys_organization_id) if sys_organization_id else None,
                "sys_user_id": ObjectId(sys_user_id) if sys_user_id else None,
                "crud_type": crud_type,
                "collection_name": collection_name,
                "collection_key": collection_key,
                "document_id": document_id,
                "description_str": description_str,
                "performed_at_utc": now,
                "expires_at": expires_at,
                # TimestampMixin-compatible fields
                "created_at": now,
                "updated_at": now,
                "soft_deleted": False,
                "soft_deleted_at": None,
                "is_activated": True,
            }

            result = await col.insert_one(entry)
            DebugService.app_debug_print(
                f"[OpsLog] Recorded {crud_type} log for {collection_name}/{document_id}", True
            )
            return str(result.inserted_id)
        except Exception as exc:
            logging.warning(f"[OpsLog] Failed to record log: {exc}")
            DebugService.app_debug_print(
                f"[OpsLog] Failed to record log: {exc}", False
            )
            return None

    @classmethod
    def record_log_background(
        cls,
        crud_type: str,
        collection_name: str,
        sys_organization_id: Optional[str] = None,
        sys_user_id: Optional[str] = None,
        collection_key: Optional[str] = None,
        document_id: Optional[str] = None,
        description_str: Optional[str] = None,
    ) -> None:
        """Fire-and-forget version of record_log using asyncio task."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(cls.record_log(
                crud_type=crud_type,
                collection_name=collection_name,
                sys_organization_id=sys_organization_id,
                sys_user_id=sys_user_id,
                collection_key=collection_key,
                document_id=document_id,
                description_str=description_str,
            ))
        except RuntimeError:
            pass  # No running loop, skip

    # ------------------------------------------------------------------ #
    #  QUERY HELPERS
    # ------------------------------------------------------------------ #

    @classmethod
    async def get_logs_paginated(
        cls,
        sys_organization_id: str,
        crud_type: Optional[str] = None,
        collection_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Return paginated organization logs with optional filters.
        Joins minimal user info from sys_user.
        Returns {items, total, skip, limit}."""
        col = get_collection(cls._LOG_COLLECTION)
        query: Dict[str, Any] = {
            "sys_organization_id": ObjectId(sys_organization_id),
            "soft_deleted": {"$ne": True},
        }
        if crud_type:
            query["crud_type"] = crud_type
        if collection_name:
            query["collection_name"] = collection_name

        total = await col.count_documents(query)

        pipeline: List[Dict[str, Any]] = [
            {"$match": query},
            {"$sort": {"performed_at_utc": -1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": CollectionKey.SYS_USER.model_name,
                    "localField": "sys_user_id",
                    "foreignField": "_id",
                    "as": "_user_lookup",
                }
            },
            {
                "$addFields": {
                    "performed_by_user": {
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
    async def get_recent_logs(
        cls,
        sys_organization_id: str,
        since_utc: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return recent logs since a given timestamp (for SSE polling)."""
        col = get_collection(cls._LOG_COLLECTION)
        query: Dict[str, Any] = {
            "sys_organization_id": ObjectId(sys_organization_id),
            "soft_deleted": {"$ne": True},
        }
        if since_utc:
            query["performed_at_utc"] = {"$gt": since_utc}

        cursor = col.find(query).sort("performed_at_utc", -1).limit(limit)
        items = await cursor.to_list(length=limit)
        return cls._stringify_ids(items)

    @classmethod
    async def purge_expired_logs(cls) -> int:
        """Delete all log entries whose expires_at is in the past.
        Returns count of deleted documents."""
        col = get_collection(cls._LOG_COLLECTION)
        now = datetime.now(timezone.utc)
        result = await col.delete_many({"expires_at": {"$lt": now}})
        count = result.deleted_count
        if count > 0:
            DebugService.app_debug_print(
                f"[OpsLog] Purged {count} expired log entries", True
            )
        return count

    # ------------------------------------------------------------------ #
    #  PRIVATE HELPERS
    # ------------------------------------------------------------------ #

    @staticmethod
    def _stringify_ids(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert _id and *_id ObjectId fields to strings for JSON output."""
        for doc in docs:
            if "_id" in doc:
                doc["id"] = str(doc["_id"])
                doc["_id"] = str(doc["_id"])
            for key, val in doc.items():
                if isinstance(val, ObjectId):
                    doc[key] = str(val)
                elif isinstance(val, datetime):
                    doc[key] = val.isoformat()
        return docs
