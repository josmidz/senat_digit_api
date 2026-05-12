"""
Centralized helpers for the cfg_user_app_store cache.

Keep everything related to static/dynamic resolution, aggregation-pipeline
building, and response-envelope shaping in one place so both request
controllers and any future seed runner use identical logic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.modules.core.configs.config import settings
from app.modules.core.constants.common import USER_APP_STORE_STATIC_PROFILES
from app.modules.core.enums.type_enum import EAppGroupFlag, OutputDataType
from app.modules.core.enums.user_app_store_enum import (
    EUserAppStoreEndpointFlag,
    EUserAppStoreProfileTypeFlag,
)
from app.modules.core.models.mapping_keys import CollectionKey


# ---------------------------------------------------------------------------
# Profile type resolution
# ---------------------------------------------------------------------------

def is_static_profile(profile_flag: Optional[str]) -> bool:
    """True when the profile flag is in the shared static list."""
    return bool(profile_flag) and profile_flag in USER_APP_STORE_STATIC_PROFILES


def resolve_profile_type(profile_flag: Optional[str]) -> EUserAppStoreProfileTypeFlag:
    """Static when the flag is in USER_APP_STORE_STATIC_PROFILES, dynamic otherwise."""
    return (
        EUserAppStoreProfileTypeFlag.STATIC
        if is_static_profile(profile_flag)
        else EUserAppStoreProfileTypeFlag.DYNAMIC
    )


def get_static_profile_flags() -> List[str]:
    """Authoritative list of static profile flags."""
    return list(USER_APP_STORE_STATIC_PROFILES)


# ---------------------------------------------------------------------------
# Response envelope
# ---------------------------------------------------------------------------

def build_response_envelope(
    formatted_data: List[Dict[str, Any]],
    *,
    status_code: int = 200,
) -> Dict[str, Any]:
    """Wrap the aggregated app list in the shape the frontend expects."""
    return {
        "status_code": status_code,
        "data": formatted_data,
        "app_menu_fetch_paradigm": settings.APP_MENU_FETCH_PARADIGM,
    }


# ---------------------------------------------------------------------------
# Aggregation pipeline builders
# ---------------------------------------------------------------------------

def build_applications_pipeline(
    *,
    user_profil_id: Any,
    api_consumer_id: Any,
    application_group_flag: str = EAppGroupFlag.COMMON.value,
    page: int = 0,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """MongoDB aggregation pipeline mirroring the one used in
    ``StaticController.fetch_formated_applications``. Factored out so the
    request path and any future seed runner share the exact same query.

    The pipeline walks ``rbac_restricted_api_consumer`` + ``rbac_restricted_profil``
    (both tied to a sys_application), filters by profile/consumer/app_group,
    de-duplicates, and paginates.
    """
    return [
        {
            "$lookup": {
                "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                "localField": "_id",
                "foreignField": "targeted_id",
                "as": "unwind__rbac_restricted_api_consumer",
            }
        },
        {"$unwind": {"path": "$unwind__rbac_restricted_api_consumer", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                "localField": "_id",
                "foreignField": "targeted_id",
                "as": "unwind__rbac_restricted_profil",
            }
        },
        {"$unwind": {"path": "$unwind__rbac_restricted_profil", "preserveNullAndEmptyArrays": True}},
        {
            "$match": {
                "unwind__rbac_restricted_profil.rbac_profile_id": ObjectId(str(user_profil_id)),
                "unwind__rbac_restricted_api_consumer.ref_api_consumer_id": ObjectId(str(api_consumer_id)),
                "unwind__rbac_restricted_profil.is_hidden": False,
                "unwind__rbac_restricted_api_consumer.is_hidden": False,
                "application_group_flag": application_group_flag,
                "is_activated": True,
            }
        },
        {
            "$group": {
                "_id": "$_id",
                "docs": {
                    "$push": {
                        "_id": "$_id",
                        "order_by": "$order_by",
                        "application_group_flag": "$application_group_flag",
                        "flag": "$flag",
                        "name": "$name",
                        "is_standalone": "$is_standalone",
                        "description_str": "$description_str",
                    }
                },
            }
        },
        {
            "$project": {
                "merged": {
                    "$reduce": {
                        "input": "$docs",
                        "initialValue": {},
                        "in": {"$mergeObjects": ["$$value", "$$this"]},
                    }
                }
            }
        },
        {"$replaceRoot": {"newRoot": "$merged"}},
        {"$sort": {"order_by": 1}},
        {"$skip": limit * page},
        {"$limit": limit},
    ]


# ---------------------------------------------------------------------------
# DB lookups
# ---------------------------------------------------------------------------

async def fetch_profile_by_flag(
    generic_service, accept_language: str, profile_flag: str
) -> Optional[Dict[str, Any]]:
    """Return the rbac_profile document for the given flag, or None."""
    return await generic_service.fetch_one_from_collection(
        collection_key=CollectionKey.RBAC_PROFILE,
        output_data_type=OutputDataType.DEFAULT.value,
        accept_language=accept_language,
        query={"filter__flag": profile_flag},
        _skip_rls=True,
    )


async def fetch_api_consumers(
    generic_service, accept_language: str
) -> List[Dict[str, Any]]:
    """All api consumers visible for cache seeding."""
    return await generic_service.fetch_data_from_collection(
        collection_key=CollectionKey.REF_API_CONSUMER,
        output_data_type=OutputDataType.DEFAULT.value,
        accept_language=accept_language,
        all_data=True,
        query={},
        _skip_rls=True,
    )


# ---------------------------------------------------------------------------
# Full aggregation runner (what both the endpoint and any seed call)
# ---------------------------------------------------------------------------

async def run_applications_aggregation(
    *,
    generic_service,
    accept_language: str,
    user_profil_id: Any,
    api_consumer_id: Any,
    application_group_flag: str = EAppGroupFlag.COMMON.value,
    page: int = 0,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Run the applications pipeline and return the formatted rows."""
    pipeline = build_applications_pipeline(
        user_profil_id=user_profil_id,
        api_consumer_id=api_consumer_id,
        application_group_flag=application_group_flag,
        page=page,
        limit=limit,
    )
    force_include_fields = ["_id", "order_by", "name", "description_str"]
    return await generic_service.fetch_native_aggregate_data_from_collection(
        collection_key=CollectionKey.SYS_APPLICATION,
        output_data_type=OutputDataType.DEFAULT.value,
        accept_language=accept_language,
        pipeline=pipeline,
        force_include_fields=force_include_fields,
    )


__all__ = [
    "EUserAppStoreEndpointFlag",
    "EUserAppStoreProfileTypeFlag",
    "is_static_profile",
    "resolve_profile_type",
    "get_static_profile_flags",
    "build_response_envelope",
    "build_applications_pipeline",
    "fetch_profile_by_flag",
    "fetch_api_consumers",
    "run_applications_aggregation",
]
