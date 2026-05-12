"""
Persistent application-cache service backing /data/get-applications.
Reads and writes to the ``cfg_user_app_store`` collection. See
``CfgUserAppStoreModel``.

Lookup keys:
  - **Dynamic** rows: keyed on ``sys_user_id``.
  - **Static** rows:  ``sys_user_id is None`` + ``rbac_profile_flag``.

The output_data_type / all_data_flag fields keep paginated and unpaginated
formatter variants in separate cache rows.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from beanie import PydanticObjectId
from bson import ObjectId

from app.modules.core.enums.user_app_store_enum import (
    STATIC_PROFILE_FLAGS,
    EUserAppStoreEndpointFlag,
    EUserAppStoreProfileTypeFlag,
    resolve_profile_type_flag,
)
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.cfg_user_app_store.cfg_user_app_store_model import (
    CfgUserAppStoreModel,
)
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.user_app_store.user_app_store_guard import (
    is_user_app_store_guard_active,
)


def _as_object_id(value: Any) -> Optional[ObjectId]:
    """Accepts ObjectId, str, PydanticObjectId, or the ``{"display_value": "..."}``
    shape returned by OutputDataType.DATA_TABLE formatters. Returns None on
    empty/invalid input rather than raising."""
    if value is None or value == "":
        return None
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, dict):
        value = value.get("display_value") or value.get("id") or value.get("_id")
        if value is None:
            return None
    try:
        return ObjectId(str(value))
    except Exception:
        return None


class UserAppStoreService:
    """CRUD + invalidation helpers for the user_app_store cache."""

    @staticmethod
    def compute_data_version(app_data: Dict[str, Any]) -> str:
        """Stable hash of the cached payload for staleness comparison."""
        serialized = json.dumps(app_data, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()

    @staticmethod
    def _build_lookup_filter(
        *,
        sys_user_id: Union[str, PydanticObjectId, None],
        ref_api_consumer_id: Union[str, PydanticObjectId],
        rbac_profile_flag: Optional[str],
        endpoint_flag: EUserAppStoreEndpointFlag,
        application_group_flag: Optional[str],
        accept_language: str,
        profile_type_flag: EUserAppStoreProfileTypeFlag,
        output_data_type: str = "default",
        all_data_flag: bool = False,
    ) -> Dict[str, Any]:
        base = {
            "ref_api_consumer_id": _as_object_id(ref_api_consumer_id),
            "endpoint_flag": endpoint_flag.value,
            "application_group_flag": application_group_flag,
            "accept_language": accept_language,
            "output_data_type": output_data_type or "default",
            "all_data_flag": bool(all_data_flag),
        }
        if profile_type_flag == EUserAppStoreProfileTypeFlag.STATIC:
            base["sys_user_id"] = None
            base["rbac_profile_flag"] = rbac_profile_flag
        else:
            base["sys_user_id"] = _as_object_id(sys_user_id)
        return base

    @classmethod
    async def get(
        cls,
        *,
        sys_user_id: Union[str, PydanticObjectId, None],
        ref_api_consumer_id: Union[str, PydanticObjectId],
        rbac_profile_flag: Optional[str],
        endpoint_flag: EUserAppStoreEndpointFlag,
        application_group_flag: Optional[str],
        accept_language: str = DEFAULT_LANGUAGE,
        output_data_type: str = "default",
        all_data_flag: bool = False,
    ) -> Optional[CfgUserAppStoreModel]:
        """Return a fresh (is_stale=False) cache row, or None."""
        profile_type_flag = resolve_profile_type_flag(rbac_profile_flag)
        lookup = cls._build_lookup_filter(
            sys_user_id=sys_user_id,
            ref_api_consumer_id=ref_api_consumer_id,
            rbac_profile_flag=rbac_profile_flag,
            endpoint_flag=endpoint_flag,
            application_group_flag=application_group_flag,
            accept_language=accept_language,
            profile_type_flag=profile_type_flag,
            output_data_type=output_data_type,
            all_data_flag=all_data_flag,
        )
        lookup["is_stale"] = False
        try:
            row = await CfgUserAppStoreModel.find_one(lookup)
            if row is not None:
                return row
            # Back-compat: tolerate rows written before the output_data_type /
            # all_data_flag fields existed, so previously-seeded payloads
            # still answer "default / all_data=false" lookups.
            legacy_variant_is_default = (
                (output_data_type or "default") == "default"
                and not all_data_flag
            )
            if legacy_variant_is_default:
                legacy_lookup = {
                    k: v for k, v in lookup.items()
                    if k not in {"output_data_type", "all_data_flag"}
                }
                legacy_lookup["$or"] = [
                    {"output_data_type": {"$exists": False}},
                    {"output_data_type": None},
                    {"output_data_type": "default"},
                ]
                return await CfgUserAppStoreModel.find_one(legacy_lookup)
            return None
        except Exception as e:
            DebugService.app_debug_print(f"UserAppStoreService.get error: {e}", True)
            return None

    @classmethod
    async def upsert(
        cls,
        *,
        sys_user_id: Union[str, PydanticObjectId, None],
        ref_api_consumer_id: Union[str, PydanticObjectId],
        rbac_profile_id: Union[str, PydanticObjectId, None],
        rbac_profile_flag: Optional[str],
        endpoint_flag: EUserAppStoreEndpointFlag,
        application_group_flag: Optional[str],
        accept_language: str,
        app_data: Dict[str, Any],
        output_data_type: str = "default",
        all_data_flag: bool = False,
    ) -> Optional[CfgUserAppStoreModel]:
        """Insert or refresh a cache row with the given payload."""
        profile_type_flag = resolve_profile_type_flag(rbac_profile_flag)
        lookup = cls._build_lookup_filter(
            sys_user_id=sys_user_id,
            ref_api_consumer_id=ref_api_consumer_id,
            rbac_profile_flag=rbac_profile_flag,
            endpoint_flag=endpoint_flag,
            application_group_flag=application_group_flag,
            accept_language=accept_language,
            profile_type_flag=profile_type_flag,
            output_data_type=output_data_type,
            all_data_flag=all_data_flag,
        )
        data_version = cls.compute_data_version(app_data)
        now = datetime.now(timezone.utc)
        try:
            existing = await CfgUserAppStoreModel.find_one(lookup)
            if existing:
                existing.app_data = app_data
                existing.data_version = data_version
                existing.last_built_at = now
                existing.is_stale = False
                existing.rbac_profile_id = _as_object_id(rbac_profile_id)
                existing.rbac_profile_flag = rbac_profile_flag
                existing.profile_type_flag = profile_type_flag
                existing.application_group_flag = application_group_flag
                existing.output_data_type = output_data_type or "default"
                existing.all_data_flag = bool(all_data_flag)
                await existing.save()
                return existing
            doc = CfgUserAppStoreModel(
                sys_user_id=_as_object_id(sys_user_id)
                if profile_type_flag == EUserAppStoreProfileTypeFlag.DYNAMIC
                else None,
                ref_api_consumer_id=_as_object_id(ref_api_consumer_id),
                rbac_profile_id=_as_object_id(rbac_profile_id),
                rbac_profile_flag=rbac_profile_flag,
                profile_type_flag=profile_type_flag,
                endpoint_flag=endpoint_flag,
                application_group_flag=application_group_flag,
                accept_language=accept_language,
                output_data_type=output_data_type or "default",
                all_data_flag=bool(all_data_flag),
                app_data=app_data,
                data_version=data_version,
                last_built_at=now,
                is_stale=False,
            )
            await doc.insert()
            return doc
        except Exception as e:
            import traceback
            DebugService.app_debug_print(
                f"UserAppStoreService.upsert error: {e}\n{traceback.format_exc()}",
                True,
            )
            return None

    @classmethod
    async def mark_user_stale(cls, sys_user_id: Union[str, PydanticObjectId]) -> int:
        """Mark every dynamic cache row belonging to sys_user_id as stale.

        No-ops during a seed / bulk RBAC operation (see user_app_store_guard) so
        thousands of rapid role upserts don't each trigger a rebuild cascade.
        """
        if is_user_app_store_guard_active():
            DebugService.app_debug_print(
                f"UserAppStoreService.mark_user_stale: SKIPPED (guard active) for user={sys_user_id}",
                True,
            )
            return 0
        try:
            result = await CfgUserAppStoreModel.find(
                {"sys_user_id": _as_object_id(sys_user_id)}
            ).update({"$set": {"is_stale": True}})
            modified = getattr(result, "modified_count", 0) or 0
            DebugService.app_debug_print(
                f"UserAppStoreService.mark_user_stale: user={sys_user_id} modified={modified}",
                True,
            )
            return modified
        except Exception as e:
            DebugService.app_debug_print(
                f"UserAppStoreService.mark_user_stale error: {e}", True
            )
            return 0

    @classmethod
    async def mark_role_users_stale(
        cls, rbac_role_id: Union[str, PydanticObjectId]
    ) -> int:
        """Mark every cache row whose owning user has this role as stale.

        ``cfg_user_app_store`` doesn't carry ``rbac_role_id`` directly, so
        this is a two-step:

          1. Resolve the user IDs from ``sys_user`` where the role matches.
          2. Bulk update_many on cache rows where ``sys_user_id ∈ those IDs``.

        Used by the frontend role-permission update flow — when an admin
        in the console saves a new permission set on a role, every user
        currently assigned that role gets their next request rebuilt
        against the fresh RBAC tree.

        Honors the guard so seed-driven role-permission upserts (which
        call this same helper if any) become no-ops during a seed run.
        """
        if is_user_app_store_guard_active():
            DebugService.app_debug_print(
                f"UserAppStoreService.mark_role_users_stale: SKIPPED (guard active) for role={rbac_role_id}",
                True,
            )
            return 0
        try:
            # Lazy import — SysUser lives in core models; avoid circular at boot.
            from app.modules.core.models.sys_user.sys_user_model import SysUserModel

            role_oid = _as_object_id(rbac_role_id)
            if role_oid is None:
                return 0

            user_oids = await SysUserModel.find(
                {"rbac_role_id": role_oid}, fetch_links=False
            ).distinct("_id")
            if not user_oids:
                return 0

            result = await CfgUserAppStoreModel.find(
                {"sys_user_id": {"$in": list(user_oids)}}
            ).update({"$set": {"is_stale": True}})
            modified = getattr(result, "modified_count", 0) or 0
            DebugService.app_debug_print(
                f"UserAppStoreService.mark_role_users_stale: role={rbac_role_id} "
                f"users={len(user_oids)} rows_marked={modified}",
                True,
            )
            return modified
        except Exception as e:  # noqa: BLE001
            DebugService.app_debug_print(
                f"UserAppStoreService.mark_role_users_stale error: {e}", True
            )
            return 0

    @classmethod
    async def mark_profile_stale(
        cls, rbac_profile_id: Union[str, PydanticObjectId]
    ) -> int:
        """Mark every cache row computed for a given profile as stale."""
        if is_user_app_store_guard_active():
            DebugService.app_debug_print(
                f"UserAppStoreService.mark_profile_stale: SKIPPED (guard active) for profile={rbac_profile_id}",
                True,
            )
            return 0
        try:
            result = await CfgUserAppStoreModel.find(
                {"rbac_profile_id": _as_object_id(rbac_profile_id)}
            ).update({"$set": {"is_stale": True}})
            return getattr(result, "modified_count", 0) or 0
        except Exception as e:
            DebugService.app_debug_print(
                f"UserAppStoreService.mark_profile_stale error: {e}", True
            )
            return 0

    @classmethod
    async def mark_static_stale(cls) -> int:
        """Mark every static (shared) cache row as stale.

        Used by a seed runner AFTER bulk upserts so the next request rebuilds
        against the fresh seed data. Deliberately does NOT honour the guard —
        the seed itself calls this at the end. Call outside the ``with`` block.
        """
        try:
            result = await CfgUserAppStoreModel.find(
                {"profile_type_flag": EUserAppStoreProfileTypeFlag.STATIC.value}
            ).update({"$set": {"is_stale": True}})
            return getattr(result, "modified_count", 0) or 0
        except Exception as e:
            DebugService.app_debug_print(
                f"UserAppStoreService.mark_static_stale error: {e}", True
            )
            return 0

    @classmethod
    async def mark_static_profile_flag_stale(cls, rbac_profile_flag: str) -> int:
        """Invalidate static rows belonging to a specific shared profile flag."""
        if is_user_app_store_guard_active():
            DebugService.app_debug_print(
                f"UserAppStoreService.mark_static_profile_flag_stale: SKIPPED (guard active) for flag={rbac_profile_flag}",
                True,
            )
            return 0
        try:
            result = await CfgUserAppStoreModel.find(
                {
                    "profile_type_flag": EUserAppStoreProfileTypeFlag.STATIC.value,
                    "rbac_profile_flag": rbac_profile_flag,
                }
            ).update({"$set": {"is_stale": True}})
            return getattr(result, "modified_count", 0) or 0
        except Exception as e:
            DebugService.app_debug_print(
                f"UserAppStoreService.mark_static_profile_flag_stale error: {e}", True
            )
            return 0

    @classmethod
    async def delete_for_user(cls, sys_user_id: Union[str, PydanticObjectId]) -> int:
        """Drop cache rows for a user. Useful on account deletion."""
        try:
            result = await CfgUserAppStoreModel.find(
                {"sys_user_id": _as_object_id(sys_user_id)}
            ).delete()
            return getattr(result, "deleted_count", 0) or 0
        except Exception as e:
            DebugService.app_debug_print(
                f"UserAppStoreService.delete_for_user error: {e}", True
            )
            return 0

    @classmethod
    async def delete_dynamic_rows_not_matching(
        cls,
        *,
        allowed_profile_flags: list,
        allowed_consumer_ids: list,
    ) -> int:
        """Remove every DYNAMIC row whose profile_flag or ref_api_consumer_id is
        not in the seed whitelist. Called at the top of a dynamic seed so
        previous over-seeded rows (from a wider matrix) don't linger.

        Static rows are untouched.
        """
        try:
            consumer_oids = [_as_object_id(c) for c in allowed_consumer_ids if c]
            query = {
                "profile_type_flag": EUserAppStoreProfileTypeFlag.DYNAMIC.value,
                "$or": [
                    {"rbac_profile_flag": {"$nin": list(allowed_profile_flags)}},
                    {"ref_api_consumer_id": {"$nin": consumer_oids}},
                ],
            }
            result = await CfgUserAppStoreModel.find(query).delete()
            deleted = getattr(result, "deleted_count", 0) or 0
            DebugService.app_debug_print(
                f"UserAppStoreService.delete_dynamic_rows_not_matching: "
                f"deleted {deleted} out-of-scope dynamic rows.",
                True,
            )
            return deleted
        except Exception as e:
            DebugService.app_debug_print(
                f"UserAppStoreService.delete_dynamic_rows_not_matching error: {e}",
                True,
            )
            return 0

    @classmethod
    def is_static_profile_flag(cls, rbac_profile_flag: Optional[str]) -> bool:
        return bool(rbac_profile_flag) and rbac_profile_flag in STATIC_PROFILE_FLAGS
