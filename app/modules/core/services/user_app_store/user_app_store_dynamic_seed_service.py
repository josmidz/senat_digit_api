"""
Dynamic seed runner: pre-populate cfg_user_app_store rows for every
NON-STATIC user so their first ``/data/get-applications`` call is served
from the L2 cache instead of running the slow aggregation.

Static profiles (TRANS_VISITOR / TRANS_CUSTOMER) are handled by
``user_app_store_seed_service.seed_static_user_app_store``. This module
is the complement for every OTHER user: admins, agents, back-office —
where the cache row is per-user (DYNAMIC), not per-profile-flag.

Whitelists (keep the matrix from exploding):
- ``USER_APP_STORE_AVAILABLE_DYNAMIC_PROFILES`` — only users whose
  profile_flag is in this list are seeded. Everything else is skipped.
- ``USER_APP_STORE_AVAILABLE_DYNAMIC_API_CONSUMERS`` — only these api
  consumers are seeded (admin web + agent mobile + customer mobile).
- ``CONSUMER_SCOPE`` — per-consumer (endpoint_flag, app_groups) tuples.
  Each consumer is seeded only for the groups it actually renders.

For each (user × consumer × app_group × output_variant × language) tuple
we call ``StaticController.run_formated_applications_core`` — the same
extracted helper the live endpoint uses on a cache miss — so the payload
the seed writes is identical to what the live endpoint would serve.

Usage::

    python3 -m app.modules.core.services.user_app_store.user_app_store_dynamic_seed_service
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from app.db.session import init_db
from app.modules.core.api.controller.static_controller import StaticController
from app.modules.core.constants.common import (
    USER_APP_STORE_AVAILABLE_DYNAMIC_API_CONSUMERS,
    USER_APP_STORE_AVAILABLE_DYNAMIC_PROFILES,
)
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.enums.type_enum import EAppGroupFlag, OutputDataType
from app.modules.core.enums.user_app_store_enum import (
    EUserAppStoreEndpointFlag,
)
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.user_app_store.user_app_store_guard import (
    user_app_store_guard,
)
from app.modules.core.services.user_app_store.user_app_store_helpers import (
    is_static_profile,
)
from app.modules.core.services.user_app_store.user_app_store_service import (
    UserAppStoreService,
)


# Languages to seed per (user × consumer × group). Each entry multiplies
# the total row count — keep short.
SEED_LANGUAGES: List[str] = ["fr", "en"]

# Output variants to seed. Each combination corresponds to a real
# wire shape one of our consumers sends:
#   - DATA_TABLE + all_data=True   → Angular admin-web app catalogue.
#   - DEFAULT    + all_data=True   → Flutter mobile (`AppsRepository.
#                                    fetchAllowedApps` sends
#                                    `?all_data=true`). Was missing
#                                    from the warm matrix, which led
#                                    to first-login cache misses
#                                    writing stale 0-row entries on
#                                    sysadmin/mobile.
#   - DEFAULT    + all_data=False  → simple/legacy consumers.
# The cache key includes `all_data_flag`, so each tuple is a distinct
# row and missing one means cold-start aggregation for that consumer.
SEED_OUTPUT_VARIANTS: List[Dict[str, Any]] = [
    {"output_data_type": OutputDataType.DATA_TABLE.value, "all_data_flag": True},
    {"output_data_type": OutputDataType.DEFAULT.value, "all_data_flag": True},
    {"output_data_type": OutputDataType.DEFAULT.value, "all_data_flag": False},
]

# Per-consumer scope. Each whitelisted consumer is seeded ONLY for the
# (endpoint_flag, app_groups) combination it actually uses at runtime.
# Stops the seed from generating cartesian garbage. SenatDigit only has the
# single ``APPLICATIONS`` endpoint flag (vs bloonio's two).
CONSUMER_SCOPE: Dict[str, Dict[str, Any]] = {
    EApiConsumerFlag.SENAT_DIGIT_ADMIN_WEB.value: {
        "endpoint_flag": EUserAppStoreEndpointFlag.APPLICATIONS,
        "app_groups": [EAppGroupFlag.COMMON.value],
    },
    EApiConsumerFlag.SENAT_DIGIT_MOBILE.value: {
        "endpoint_flag": EUserAppStoreEndpointFlag.APPLICATIONS,
        "app_groups": [EAppGroupFlag.COMMON.value],
    },
}


async def _fetch_dynamic_users(
    generic_service: GenericService,
) -> List[Dict[str, Any]]:
    """Return every non-deleted, active user — profile filtering happens later."""
    users = await generic_service.fetch_data_from_collection(
        collection_key=CollectionKey.SYS_USER,
        output_data_type=OutputDataType.DEFAULT.value,
        accept_language=DEFAULT_LANGUAGE,
        all_data=True,
        query={"filter__soft_deleted": False, "filter__is_activated": True},
        _skip_rls=True,
    )
    return users or []


async def _fetch_whitelisted_consumers(
    generic_service: GenericService,
) -> List[Dict[str, Any]]:
    """Return only the api consumers in the dynamic whitelist."""
    all_consumers = await generic_service.fetch_data_from_collection(
        collection_key=CollectionKey.REF_API_CONSUMER,
        output_data_type=OutputDataType.DEFAULT.value,
        accept_language=DEFAULT_LANGUAGE,
        all_data=True,
        query={},
        _skip_rls=True,
    )
    if not all_consumers:
        return []
    whitelist = set(USER_APP_STORE_AVAILABLE_DYNAMIC_API_CONSUMERS)
    return [c for c in all_consumers if (c.get("flag") or "") in whitelist]


async def _fetch_profile_by_id(
    generic_service: GenericService, rbac_profile_id: Any
) -> Optional[Dict[str, Any]]:
    if not rbac_profile_id:
        return None
    return await generic_service.fetch_one_from_collection(
        collection_key=CollectionKey.RBAC_PROFILE,
        output_data_type=OutputDataType.DEFAULT.value,
        accept_language=DEFAULT_LANGUAGE,
        query={"filter___id": str(rbac_profile_id)},
        _skip_rls=True,
    )


async def _seed_one_combo(
    *,
    controller: StaticController,
    user: Dict[str, Any],
    profile: Dict[str, Any],
    api_consumer: Dict[str, Any],
    application_group_flag: str,
    accept_language: str,
    output_data_type: str,
    all_data_flag: bool,
    endpoint_flag: EUserAppStoreEndpointFlag,
) -> bool:
    """Run the headless core for one tuple and upsert the result as a
    dynamic cache row. Returns True on write."""
    user_id = user.get("id") or user.get("_id")
    profile_id = profile.get("id") or profile.get("_id")
    profile_flag = profile.get("flag")
    consumer_id = api_consumer.get("id") or api_consumer.get("_id")
    consumer_flag = api_consumer.get("flag") or api_consumer.get("name")
    username = (
        user.get("username")
        or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        or str(user_id)
    )

    # Make the controller emit messages in the seeding language.
    controller.accept_language = accept_language

    try:
        response_data = await controller.run_formated_applications_core(
            user_details=user,
            api_Consumer=api_consumer,
            user_profil=profile,
            output_data_type=OutputDataType(output_data_type),
            all_data=all_data_flag,
            page=0,
            limit=50,
            application_group_flag=application_group_flag,
        )
    except Exception as e:
        print(
            f"    ✗ aggregation failed user={username} profile={profile_flag} "
            f"consumer={consumer_flag} group={application_group_flag} "
            f"lang={accept_language} output={output_data_type} "
            f"endpoint={endpoint_flag.value}: {e}"
        )
        return False

    if not isinstance(response_data, dict):
        print(
            f"    ✗ bad payload shape user={username} group={application_group_flag} "
            f"output={output_data_type} endpoint={endpoint_flag.value}"
        )
        return False

    items = response_data.get("data") or []
    saved = await UserAppStoreService.upsert(
        sys_user_id=user_id,
        ref_api_consumer_id=consumer_id,
        rbac_profile_id=profile_id,
        rbac_profile_flag=profile_flag,
        endpoint_flag=endpoint_flag,
        application_group_flag=application_group_flag,
        accept_language=accept_language,
        app_data=response_data,
        output_data_type=output_data_type,
        all_data_flag=all_data_flag,
    )
    if saved:
        print(
            f"    ✓ user={username} profile={profile_flag} consumer={consumer_flag} "
            f"group={application_group_flag} lang={accept_language} "
            f"output={output_data_type} all_data={all_data_flag} "
            f"endpoint={endpoint_flag.value} items={len(items)}"
        )
        return True
    print(
        f"    ✗ upsert failed user={username} group={application_group_flag} "
        f"lang={accept_language} output={output_data_type} endpoint={endpoint_flag.value}"
    )
    return False


async def seed_dynamic_user_app_store(
    *,
    languages: Optional[List[str]] = None,
    output_variants: Optional[List[Dict[str, Any]]] = None,
    consumer_scope: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, int]:
    """Seed dynamic rows for every whitelisted (user × consumer × group × variant × lang).

    - User must have ``rbac_profile.flag`` ∈ ``USER_APP_STORE_AVAILABLE_DYNAMIC_PROFILES``.
    - Consumer must have ``flag`` ∈ ``USER_APP_STORE_AVAILABLE_DYNAMIC_API_CONSUMERS``.
    - ``(endpoint_flag, app_groups)`` per consumer is dictated by ``CONSUMER_SCOPE``.
    """
    languages = languages or SEED_LANGUAGES
    output_variants = output_variants or SEED_OUTPUT_VARIANTS
    consumer_scope = consumer_scope or CONSUMER_SCOPE

    generic_service = GenericService(DEFAULT_LANGUAGE)
    controller = StaticController(DEFAULT_LANGUAGE)

    whitelisted_profile_flags = set(USER_APP_STORE_AVAILABLE_DYNAMIC_PROFILES)
    whitelisted_consumer_flags = set(USER_APP_STORE_AVAILABLE_DYNAMIC_API_CONSUMERS)

    print(
        "[user_app_store dynamic seed] start | "
        f"profile whitelist={sorted(whitelisted_profile_flags)} | "
        f"consumer whitelist={sorted(whitelisted_consumer_flags)} | "
        f"languages={languages} | "
        f"variants={[(v['output_data_type'], v['all_data_flag']) for v in output_variants]}"
    )

    users = await _fetch_dynamic_users(generic_service)
    if not users:
        print("[user_app_store dynamic seed] no users resolved; nothing to seed.")
        return {"ok": 0, "skipped_profile": 0, "skipped_static": 0, "failed": 0}

    api_consumers = await _fetch_whitelisted_consumers(generic_service)
    if not api_consumers:
        print(
            "[user_app_store dynamic seed] no whitelisted api_consumers found; "
            f"expected one of {sorted(whitelisted_consumer_flags)}."
        )
        return {"ok": 0, "skipped_profile": 0, "skipped_static": 0, "failed": 0}

    print(
        f"[user_app_store dynamic seed] users={len(users)} "
        f"consumers={[c.get('flag') for c in api_consumers]}"
    )

    # Purge any dynamic rows left behind by an earlier, wider-matrix seed run.
    # Static rows are untouched.
    allowed_consumer_ids = [c.get("id") or c.get("_id") for c in api_consumers]
    deleted_out_of_scope = await UserAppStoreService.delete_dynamic_rows_not_matching(
        allowed_profile_flags=list(whitelisted_profile_flags),
        allowed_consumer_ids=allowed_consumer_ids,
    )
    if deleted_out_of_scope:
        print(
            f"[user_app_store dynamic seed] purged {deleted_out_of_scope} "
            "out-of-scope dynamic rows before seeding."
        )

    stats = {
        "ok": 0,
        "skipped_profile": 0,
        "skipped_static": 0,
        "failed": 0,
        "purged_out_of_scope": deleted_out_of_scope,
    }

    # Wrap the whole fan-out in the guard so any mark_*_stale call that gets
    # triggered by the aggregation itself (e.g. through a future role-save hook)
    # becomes a no-op — otherwise we'd rebuild in a loop.
    async with user_app_store_guard():
        for user in users:
            user_id = user.get("id") or user.get("_id")
            rbac_profile_id = user.get("rbac_profile_id")
            profile = await _fetch_profile_by_id(generic_service, rbac_profile_id)
            if not profile:
                stats["skipped_profile"] += 1
                print(
                    f"  ↪ user={user_id}: profile {rbac_profile_id} not resolved, "
                    "skipping"
                )
                continue

            profile_flag = profile.get("flag")
            if is_static_profile(profile_flag):
                stats["skipped_static"] += 1
                continue
            if profile_flag not in whitelisted_profile_flags:
                stats["skipped_profile"] += 1
                print(
                    f"  ↪ user={user.get('username') or user_id}: profile_flag="
                    f"{profile_flag!r} not in dynamic whitelist, skipping"
                )
                continue

            username = user.get("username") or str(user_id)
            print(f"  • user={username} profile={profile_flag}")

            for api_consumer in api_consumers:
                consumer_flag = api_consumer.get("flag")
                scope = consumer_scope.get(consumer_flag)
                if not scope:
                    continue
                endpoint_flag = scope["endpoint_flag"]
                groups = scope["app_groups"]

                for group_flag in groups:
                    for lang in languages:
                        for variant in output_variants:
                            ok = await _seed_one_combo(
                                controller=controller,
                                user=user,
                                profile=profile,
                                api_consumer=api_consumer,
                                application_group_flag=group_flag,
                                accept_language=lang,
                                output_data_type=variant["output_data_type"],
                                all_data_flag=variant["all_data_flag"],
                                endpoint_flag=endpoint_flag,
                            )
                            if ok:
                                stats["ok"] += 1
                            else:
                                stats["failed"] += 1

    print(
        f"[user_app_store dynamic seed] done | written={stats['ok']} "
        f"failed={stats['failed']} skipped_profile={stats['skipped_profile']} "
        f"skipped_static={stats['skipped_static']} "
        f"purged_out_of_scope={stats['purged_out_of_scope']}"
    )
    return stats


async def _main() -> None:
    print("[user_app_store dynamic seed] initializing database...")
    await init_db()
    await seed_dynamic_user_app_store()


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed loop")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(_main())
