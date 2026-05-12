"""
Seed runner: populate cfg_user_app_store rows for every STATIC profile flag.

Called from bash/seeds/run.seed.*.sh after the RBAC + sys_application seeds
so the aggregation has fresh input. For every (static_profile, api_consumer,
language) triple, runs the applications aggregation once and persists the
result as a STATIC row keyed by ``rbac_profile_flag`` (not ``sys_user_id``).
All users sharing that profile then read from the same row on their next
fetch.

Usage::

    python3 -m app.modules.core.services.user_app_store.user_app_store_seed_service
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from app.db.session import init_db
from app.modules.core.enums.type_enum import EAppGroupFlag
from app.modules.core.enums.user_app_store_enum import EUserAppStoreEndpointFlag
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.user_app_store.user_app_store_guard import (
    user_app_store_guard,
)
from app.modules.core.services.user_app_store.user_app_store_helpers import (
    build_response_envelope,
    fetch_api_consumers,
    fetch_profile_by_flag,
    get_static_profile_flags,
    run_applications_aggregation,
)
from app.modules.core.services.user_app_store.user_app_store_service import (
    UserAppStoreService,
)


# Languages to seed per (profile, consumer). Each combo is one aggregation
# + one Mongo upsert — keep short.
SEED_LANGUAGES: List[str] = ["fr", "en"]


async def _seed_one_combo(
    *,
    generic_service: GenericService,
    profile: Dict[str, Any],
    api_consumer: Dict[str, Any],
    accept_language: str,
    endpoint_flag: EUserAppStoreEndpointFlag,
    application_group_flag: str,
) -> bool:
    """Run the aggregation for one (profile, consumer, lang) triple and
    upsert the result as a STATIC row. Returns True on success."""
    profile_id = profile.get("id") or profile.get("_id")
    profile_flag = profile.get("flag")
    consumer_id = api_consumer.get("id") or api_consumer.get("_id")
    consumer_name = api_consumer.get("name") or api_consumer.get("flag")

    try:
        applications = await run_applications_aggregation(
            generic_service=generic_service,
            accept_language=accept_language,
            user_profil_id=profile_id,
            api_consumer_id=consumer_id,
            application_group_flag=application_group_flag,
        )
    except Exception as e:
        print(
            f"  ✗ aggregation failed for profile={profile_flag} "
            f"consumer={consumer_name} lang={accept_language}: {e}"
        )
        return False

    if not applications:
        print(
            f"  ↪ skipped (empty) profile={profile_flag} "
            f"consumer={consumer_name} lang={accept_language}"
        )
        return False

    response_data = build_response_envelope(applications)
    saved = await UserAppStoreService.upsert(
        sys_user_id=None,
        ref_api_consumer_id=consumer_id,
        rbac_profile_id=profile_id,
        rbac_profile_flag=profile_flag,
        endpoint_flag=endpoint_flag,
        application_group_flag=application_group_flag,
        accept_language=accept_language,
        app_data=response_data,
    )
    if saved:
        print(
            f"  ✓ seeded profile={profile_flag} consumer={consumer_name} "
            f"lang={accept_language} items={len(applications)}"
        )
        return True
    print(
        f"  ✗ upsert failed for profile={profile_flag} "
        f"consumer={consumer_name} lang={accept_language}"
    )
    return False


async def seed_static_user_app_store(
    *,
    languages: Optional[List[str]] = None,
    endpoint_flag: EUserAppStoreEndpointFlag = EUserAppStoreEndpointFlag.APPLICATIONS,
    application_group_flag: str = EAppGroupFlag.COMMON.value,
) -> Dict[str, int]:
    """Seed static rows for every (static_profile × api_consumer × language).

    Static profiles in senat_digit are TRANS_VISITOR + TRANS_CUSTOMER — the
    public/customer profiles where every user sees the same menu set.
    Dynamic admin/agent profiles populate on-demand on first request.
    """
    languages = languages or SEED_LANGUAGES
    generic_service = GenericService(DEFAULT_LANGUAGE)

    static_profile_flags = get_static_profile_flags()
    print(
        f"[user_app_store seed] static profiles: {static_profile_flags} | "
        f"languages: {languages} | endpoint: {endpoint_flag.value} | "
        f"group: {application_group_flag}"
    )

    # Resolve profiles once (same across all consumers).
    profiles_by_flag: Dict[str, Dict[str, Any]] = {}
    for flag in static_profile_flags:
        doc = await fetch_profile_by_flag(generic_service, DEFAULT_LANGUAGE, flag)
        if doc:
            profiles_by_flag[flag] = doc
        else:
            print(f"  ✗ static profile not found in DB: {flag}")

    if not profiles_by_flag:
        print("[user_app_store seed] no static profiles resolved; nothing to seed.")
        return {"ok": 0, "skipped": 0, "failed": 0}

    api_consumers = await fetch_api_consumers(generic_service, DEFAULT_LANGUAGE)
    if not api_consumers:
        print("[user_app_store seed] no api_consumers found; nothing to seed.")
        return {"ok": 0, "skipped": 0, "failed": 0}

    stats = {"ok": 0, "skipped": 0, "failed": 0}
    async with user_app_store_guard():
        for profile_flag, profile in profiles_by_flag.items():
            print(f"[user_app_store seed] profile={profile_flag}")
            for api_consumer in api_consumers:
                for lang in languages:
                    ok = await _seed_one_combo(
                        generic_service=generic_service,
                        profile=profile,
                        api_consumer=api_consumer,
                        accept_language=lang,
                        endpoint_flag=endpoint_flag,
                        application_group_flag=application_group_flag,
                    )
                    if ok:
                        stats["ok"] += 1
                    else:
                        stats["skipped"] += 1

    print(
        f"[user_app_store seed] done | written={stats['ok']} "
        f"skipped/empty={stats['skipped']}"
    )
    return stats


async def _main() -> None:
    print("[user_app_store seed] initializing database...")
    await init_db()
    await seed_static_user_app_store()


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed loop")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(_main())
