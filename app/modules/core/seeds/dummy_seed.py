# app/modules/core/seeds/dummy_seed.py
"""
Demo seed — populates a believable, end-to-end scrutin so the Flutter app
has something rich to render at every screen.

Idempotent: safe to re-run. Each helper checks for existence by a stable
natural key before creating, then upserts.

Run via:
    bash/seeds/run.dummy-seed.local.sh    (existing wrapper)
    bash/seeds/run.dummy-seed.dev.sh      (added in this commit)
    bash/seeds/run.dummy-seed.test.sh     (added in this commit)

What it creates (all under the SYSTEM_PROFIL org so RLS lets the demo
sénateurs see everything):
    1 demo organization (RDC Sénat — keeps existing system org untouched
      and adds an `is_default=True` flag-based variant).
    6 sys_users:
       - greffier1 / Greffier2026!
       - senateur1 .. senateur5 / Senat2026!
    1 session_meeting in OUVERTE status (opened ~30 min ago).
    6 agenda_item (1 active, 5 queued, all published).
    3 document_meta (TEXTE_LOI, RESOLUTION, RAPPORT) with arch_file_id
      left null — the FS service stores PDFs out of band; in dev we keep
      the metadata-only state so the read CTA degrades gracefully and
      the typology-color rail is still visible.
    1 vote_config + 1 vote_result on the RESOLUTION (decision=ADOPTE,
      majority met, sample tally) so the slide-14 moneyshot renders.
    A handful of notifications targeting senateur1 (mix of unread/read,
      one of each event type) so the inbox has texture.

Nothing here writes to /api endpoints — we go through GenericService
upserts directly to keep the seed fast and not rely on auth tokens.

References:
    seed_apps.py — same upsert idiom (filter_data + update_data).
    senat_pptx_requirements.md — 4-choice vote, pouvoirs/proxies, secret
                                  votes, audit prev-hash chain.
"""

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import nest_asyncio
from beanie import PydanticObjectId


def _stable_oid_hex(s: str) -> str:
    """Return a deterministic 24-char hex string usable wherever an
    ObjectId-typed field needs a value but we want re-runs to converge.

    `version_chain_id` (DocumentMetaModel) and similar `_id` fields are
    typed `PydanticObjectId`, which the GenericService validates strictly
    via `convert_id_fields`. We can't pass a human-readable identifier
    there, but we still need idempotency across seed runs — so we hash
    the natural key into a stable 24-char hex (first 24 chars of md5).
    """
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:24]

from app.db.session import init_db
from app.modules.auth.services.password.password_service import PasswordService
from app.modules.core.configs.config import settings
from app.modules.core.enums.profiles_enum import (
    ESysProfileFlag,
    ESysProfilSuperUserRoleFlag,
)
from app.modules.core.enums.type_enum import (
    AccountStatusFlag,
    EAppGroupFlag,
    EGender,
    OutputDataType,
)
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.models.ntf_notification.ntf_notification_model import (
    NtfNotificationModel,
)
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.hash.hash_service import HashService
from app.modules.document.enums.document_enum import EDocumentTypology
from app.modules.notification.enums.notification_enum import (
    ENotificationEventType,
)
from app.modules.session_meeting.enums.session_enum import (
    ESessionMode,
    ESessionParticipantRole,
    ESessionStatus,
)
from app.modules.vote.enums.vote_enum import (
    EVoteBallotType,
    EVoteMajorityType,
    EVoteStatus,
)

# uvloop runs natively without nest_asyncio; older event loops need the
# patch. Mirroring the seed_apps.py defensive pattern.
try:
    nest_asyncio.apply()
except ValueError:
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

DEMO_ORG_NAME = "Sénat de la République Démocratique du Congo"
# We seed under the **main** (non-system) profil — same flag the rest of
# the senat_digit catalogue is keyed on. SYSTEM_PROFIL is reserved for
# back-office automation; greffiers and sénateurs live under the main
# profil so RBAC permissions evaluate normally.
DEMO_ORG_FLAG = ESysProfileFlag.MAIN_PROFILE.value
DEMO_ORG_REF_ENTITY_UNIQUE_FLAG = "rdc-town-kinshasa"

# Predictable credentials — printed at the end of the run so the user can
# paste them into 1Password / a sticky note. Keep these short and
# memorable; they are *demo only* and never make it to prod (the
# run.dummy-seed.prod.sh wrapper does not exist on purpose).
DEMO_PASSWORD_MAIN_ADMIN = "MainAdmin2026!"
DEMO_PASSWORD_GREFFIER = "Greffier2026!"
DEMO_PASSWORD_SENATEUR = "Senat2026!"

MAIN_ADMIN_USERNAME = "mainadmin1"
GREFFIER_USERNAME = "greffier1"

SENATEURS: List[Dict[str, str]] = [
    {"username": "senateur1", "first_name": "Jean",  "last_name": "Mukendi",  "gender": EGender.MALE.value,   "phone": "243810000001", "email": "senateur1@senat-rdc.cd"},
    {"username": "senateur2", "first_name": "Marie", "last_name": "Tshombe",  "gender": EGender.FEMALE.value, "phone": "243810000002", "email": "senateur2@senat-rdc.cd"},
    {"username": "senateur3", "first_name": "Paul",  "last_name": "Kabasele", "gender": EGender.MALE.value,   "phone": "243810000003", "email": "senateur3@senat-rdc.cd"},
    {"username": "senateur4", "first_name": "Esther","last_name": "Ilunga",   "gender": EGender.FEMALE.value, "phone": "243810000004", "email": "senateur4@senat-rdc.cd"},
    {"username": "senateur5", "first_name": "Patrice","last_name": "Lumumba", "gender": EGender.MALE.value,   "phone": "243810000005", "email": "senateur5@senat-rdc.cd"},
]

SESSION_TITLE = "Séance plénière du 30 avril 2026"
SESSION_DESCRIPTION = (
    "Examen et adoption de la résolution sur le budget rectificatif 2026, "
    "et points divers à l'ordre du jour."
)

AGENDA_ITEMS: List[Dict[str, Any]] = [
    {
        "title": "Ouverture de la séance et appel nominal",
        "description": "Vérification du quorum et appel des sénateurs présents.",
        "is_active": False,
    },
    {
        "title": "Adoption de l'ordre du jour",
        "description": "Validation de l'ordre du jour proposé par la conférence des présidents.",
        "is_active": False,
    },
    {
        "title": "Examen de la résolution sur le budget rectificatif 2026",
        "description": (
            "Présentation du rapport de la commission des finances suivie d'un "
            "débat général puis vote sur la résolution. Documents joints : texte "
            "de loi, résolution, rapport de commission."
        ),
        "is_active": True,
    },
    {
        "title": "Examen des amendements proposés",
        "description": "Discussion article par article des amendements déposés.",
        "is_active": False,
    },
    {
        "title": "Questions orales au gouvernement",
        "description": "Période de questions adressées aux ministres présents.",
        "is_active": False,
    },
    {
        "title": "Clôture de la séance",
        "description": "Lecture du procès-verbal et clôture officielle.",
        "is_active": False,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

async def init_data() -> None:
    print("\n[demo-seed] starting…", flush=True)
    await init_db()

    svc = GenericService(DEFAULT_LANGUAGE)

    # 0a. SaaS config — global row the legacy auth_controller.login pipeline
    # reads to surface a support email on auth-error screens. Without it
    # every login bounces with a generic 401 "configurations système
    # manquantes". One row per system; idempotent on `is_activated=True`.
    await _ensure_saas_config(svc)

    # 0b. Consumer secrets — provisions HMAC signing secrets for
    # senat_digit_mobile + admin_web + fs. Idempotent: re-runs only
    # generate a secret when the row doesn't have one yet. The mobile
    # secret is echoed at the end of the seed so the dev can paste it
    # into bash/run.dev.sh (or run.dev.sh reads it from Mongo directly).
    consumer_secrets = await _ensure_consumer_secrets(svc)

    # 0c. Reference languages — `device_service.create_or_get_user_config`
    # looks up `ref_language` by `short_code` to populate `ref_language_id`
    # on the per-user config row. Without it, login crashes silently
    # inside a bare `except` and surfaces as 401 NO_EXISTING_USER_CONFIG.
    # The full seed.create_languages() ships 10 locales; for the demo we
    # only need the two we actively support.
    await _ensure_languages(svc)

    # 0d. SYSTEM bootstrap — make sure the system tenant + its super-admin
    # exist so this seed is fully self-sufficient. If `seed_apps` already
    # ran them they're left untouched (idempotent); if it didn't, this
    # creates them so we never need to "log in as system admin to
    # provision the main org" — the seed does it directly.
    sys_profil_id = await _resolve_profil_id(
        svc, ESysProfileFlag.SYSTEM_PROFIL.value
    )
    if not sys_profil_id:
        print(
            "[demo-seed] aborting: SYSTEM_PROFIL not seeded yet. "
            "Run run.seed.<env>.app.sh first."
        )
        return
    sys_org_id = await _ensure_system_org(svc, profil_id=sys_profil_id)
    sys_admin_id = await _ensure_system_super_admin(
        svc, system_org_id=sys_org_id, system_profil_id=sys_profil_id
    )

    # 1. Main profil + main org + main role.
    profil_id = await _resolve_main_profil_id(svc)
    if not profil_id:
        print(
            "[demo-seed] aborting: main profil (MAIN_PROFILE) not seeded yet. "
            "Run run.seed.<env>.app.sh first."
        )
        return

    # Resolve the three parliamentary-role IDs. Each MUST exist (seeded
    # by seed_apps.create_profiles); a missing role aborts the seed
    # because the demo without per-role assignment defeats the slice's
    # purpose.
    senateur_role_id = await _resolve_role_id(
        svc,
        profil_id=profil_id,
        role_flag=ESysProfilSuperUserRoleFlag.SENATEUR.value,
    )
    greffier_role_id = await _resolve_role_id(
        svc,
        profil_id=profil_id,
        role_flag=ESysProfilSuperUserRoleFlag.GREFFIER.value,
    )
    main_admin_role_id = await _resolve_role_id(
        svc,
        profil_id=profil_id,
        role_flag=ESysProfilSuperUserRoleFlag.MAIN_PROFILE_SUPER_ADMIN.value,
    )
    if not senateur_role_id or not greffier_role_id or not main_admin_role_id:
        print(
            "[demo-seed] aborting: SENATEUR/GREFFIER/MAIN_PROFILE_SUPER_ADMIN "
            "roles not seeded yet. Run run.seed.<env>.app.sh first."
        )
        return

    org_id = await _ensure_main_org(svc, profil_id=profil_id)
    if not org_id:
        print("[demo-seed] aborting: could not create/resolve main organization.")
        return

    # 2. Users
    # ─ mainadmin1   → MAIN_PROFILE_SUPER_ADMIN  (Sénat IT/owner: in-org user mgmt)
    # ─ greffier1    → GREFFIER                  (session orchestration; no user mgmt)
    # ─ senateur1..5 → SENATEUR                  (participation only)
    #
    # Each role's permission grants are seeded in
    # seed_apps.seed_senat_digit_modules_rbac → see senat_digit_role_matrix.
    main_admin_id = await _ensure_user(
        svc,
        username=MAIN_ADMIN_USERNAME,
        password=DEMO_PASSWORD_MAIN_ADMIN,
        first_name="Direction",
        last_name="Permanente",
        gender=EGender.MALE.value,
        email="direction@senat-rdc.cd",
        phone="243800000098",
        org_id=org_id,
        profil_id=profil_id,
        role_id=main_admin_role_id,
    )
    greffier_id = await _ensure_user(
        svc,
        username=GREFFIER_USERNAME,
        password=DEMO_PASSWORD_GREFFIER,
        first_name="Greffier",
        last_name="Principal",
        gender=EGender.MALE.value,
        email="greffier@senat-rdc.cd",
        phone="243800000099",
        org_id=org_id,
        profil_id=profil_id,
        role_id=greffier_role_id,
    )
    senateur_ids: List[str] = []
    for s in SENATEURS:
        uid = await _ensure_user(
            svc,
            username=s["username"],
            password=DEMO_PASSWORD_SENATEUR,
            first_name=s["first_name"],
            last_name=s["last_name"],
            gender=s["gender"],
            email=s["email"],
            phone=s["phone"],
            org_id=org_id,
            profil_id=profil_id,
            role_id=senateur_role_id,
        )
        if uid:
            senateur_ids.append(uid)

    # 3. Session (OUVERTE, opened 30 min ago)
    session_id = await _ensure_session(svc, org_id=org_id)
    if not session_id:
        print("[demo-seed] aborting: failed to create session.")
        return

    # 4. Session participants (greffier + 5 sénateurs)
    if greffier_id:
        await _ensure_participant(
            svc,
            session_id=session_id,
            org_id=org_id,
            user_id=greffier_id,
            role=ESessionParticipantRole.GREFFIER.value,
            can_vote=False,
        )
    for uid in senateur_ids:
        await _ensure_participant(
            svc,
            session_id=session_id,
            org_id=org_id,
            user_id=uid,
            role=ESessionParticipantRole.SENATEUR.value,
            can_vote=True,
        )

    # 5. Agenda
    agenda_ids = await _ensure_agenda(svc, org_id=org_id, session_id=session_id)
    if len(agenda_ids) < 3:
        print("[demo-seed] warning: agenda items short, scrutin will not link.")
        # We still continue — vote linking will be skipped below.

    # 6. Documents (1 TEXTE_LOI, 1 RESOLUTION, 1 RAPPORT) linked to the
    # active agenda item (index 2 in AGENDA_ITEMS = "Examen de la résolution
    # sur le budget rectificatif 2026").
    active_agenda_id = agenda_ids[2] if len(agenda_ids) >= 3 else None
    doc_ids = await _ensure_documents(
        svc,
        org_id=org_id,
        session_id=session_id,
        active_agenda_id=active_agenda_id,
    )
    resolution_doc_id = doc_ids.get(EDocumentTypology.RESOLUTION.value)

    # 7. Link the documents back to the active agenda item.
    if active_agenda_id and doc_ids:
        await _link_docs_to_agenda(
            svc,
            agenda_id=active_agenda_id,
            doc_ids=list(doc_ids.values()),
        )

    # 8. Vote (CLOS, decision=ADOPTE) on the resolution — drives the
    # slide-14 moneyshot screen.
    if resolution_doc_id:
        vote_cfg_id = await _ensure_vote_config(
            svc,
            org_id=org_id,
            session_id=session_id,
            resolution_id=resolution_doc_id,
        )
        if vote_cfg_id:
            await _ensure_vote_result(
                svc,
                org_id=org_id,
                vote_config_id=vote_cfg_id,
            )

    # 9. Notifications — target senateur1 with one row per event type so
    # the inbox shows the full design vocabulary.
    if senateur_ids:
        await _ensure_notifications(
            svc,
            org_id=org_id,
            target_user_id=senateur_ids[0],
            session_id=session_id,
            agenda_id=active_agenda_id,
            doc_id=doc_ids.get(EDocumentTypology.TEXTE_LOI.value),
            vote_config_id=vote_cfg_id if resolution_doc_id else None,
        )

    # 10. Pre-warm cfg_user_app_store for every dynamic-profile user we just
    # created. The /static/data/get-applications endpoint reads this L2
    # cache before falling back to the (slow) restriction-join aggregation.
    # Without pre-warming, the senateur's first login would block ~1-3s on
    # the cold aggregation; pre-warming makes it sub-50ms.
    #
    # This MUST come after _ensure_user / _ensure_system_super_admin so
    # there are users to warm. The seed is whitelisted internally —
    # only MAIN_PROFILE + SYSTEM_PROFIL users on the admin-web/mobile
    # consumers are touched. Failures are logged and never break dummy_seed.
    await _warm_user_app_store()

    _print_summary(
        senateur_ids=senateur_ids,
        greffier_id=greffier_id,
        main_admin_id=main_admin_id,
        consumer_secrets=consumer_secrets,
        sys_admin_id=sys_admin_id,
    )


async def _warm_user_app_store() -> None:
    """Pre-warm cfg_user_app_store for every dynamic-profile user.

    Wraps `seed_dynamic_user_app_store` with a try/except so a cache-warm
    failure never breaks the demo seed (the /get-applications endpoint
    still works on a cold cache; it's just slower the first time).
    """
    try:
        from app.modules.core.services.user_app_store.user_app_store_dynamic_seed_service import (
            seed_dynamic_user_app_store,
        )
        print("\n[demo-seed] warming cfg_user_app_store …")
        stats = await seed_dynamic_user_app_store()
        print(f"[demo-seed] cfg_user_app_store warm: {stats}")
    except Exception as e:  # noqa: BLE001 — best-effort cache warming
        print(f"[demo-seed] WARN: cfg_user_app_store warm failed (non-fatal): {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 0. SaaS config (system-wide, single row)
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_saas_config(svc: GenericService) -> Optional[str]:
    """Create the global cfg_saas_config row if missing.

    `auth_controller.login` calls `get_system_support_email(saas_config_info)`
    which expects a row with at least one `contact_info` entry where
    `purpose=customer_support` and `info_kind=email_address`. Without it the
    login flow short-circuits with a generic 401 "configurations système
    manquantes".

    Single row per system — keyed on `is_activated=True`. Re-runs are no-ops.
    """
    existing = await svc.fetch_one_from_collection(
        collection_key=CollectionKey.CFG_SAAS_CONFIG,
        output_data_type=OutputDataType.DEFAULT,
        query={"filter__is_activated": True},
    )
    if existing:
        print(f"[demo-seed] cfg_saas_config already present → {existing.get('id')}")
        return existing.get("id")

    payload = {
        "sms_sender_name": "SenatDigit",
        "contact_info": [
            {
                "contact_info": "support@senat-rdc.cd",
                "is_activated": True,
                "purpose": "customer_support",
                "info_kind": "email_address",
                "ref_entity_id": None,
            },
            {
                "contact_info": "+243 81 333 87 77",
                "is_activated": True,
                "purpose": "customer_support",
                "info_kind": "phone_number",
                "ref_entity_id": None,
            },
        ],
        "currency_exchange_setup_scope": "system",
    }
    result = await svc.upsert_data_to_collection(
        collection_key=CollectionKey.CFG_SAAS_CONFIG,
        # No natural key → we want exactly one row, so filter on
        # `is_activated=True` (only one active row at a time).
        filter_data={"is_activated": True},
        update_data=payload,
    )
    cfg_id = result if isinstance(result, str) else result.get("id")
    print(f"[demo-seed] cfg_saas_config created → {cfg_id}")
    return cfg_id


# ─────────────────────────────────────────────────────────────────────────────
# 0c. Reference languages
# ─────────────────────────────────────────────────────────────────────────────

# Minimal locale set the auth flow + user config depend on. Mirrors the
# shape of seed.create_languages() so re-running the full base seed later
# is a no-op (filter_data uses `name` as the natural key).
_DEMO_LANGUAGES = (
    {"name": "Français", "short_code": "fr", "long_code": "fr-FR"},
    {"name": "English",  "short_code": "en", "long_code": "en-US"},
)


async def _ensure_languages(svc: GenericService) -> None:
    """Idempotent upsert of `fr` + `en` into `ref_language`.

    `device_service.create_or_get_user_config` reads this collection
    during login to populate `cfg_user_config.ref_language_id`. If it
    can't find a row matching the request's `accept-language` header
    OR a fallback `fr` row, it raises a TypeError that the service
    silently swallows and surfaces as a 401 NO_EXISTING_USER_CONFIG.
    """
    created = 0
    for lang in _DEMO_LANGUAGES:
        existing = await svc.fetch_one_from_collection(
            collection_key=CollectionKey.REF_LANGUAGE,
            output_data_type=OutputDataType.DEFAULT,
            query={"filter__name": lang["name"]},
        )
        if existing:
            continue
        await svc.upsert_data_to_collection(
            collection_key=CollectionKey.REF_LANGUAGE,
            filter_data={"name": lang["name"]},
            update_data=lang,
        )
        created += 1
    if created:
        print(f"[demo-seed] ref_language: created {created}")
    else:
        print(f"[demo-seed] ref_language: all {len(_DEMO_LANGUAGES)} present")


# ─────────────────────────────────────────────────────────────────────────────
# 0b. Consumer secrets (HMAC signing)
# ─────────────────────────────────────────────────────────────────────────────

# Flags we provision a secret for. Order matters only for the printout.
_CONSUMER_FLAGS_NEEDING_SECRET = (
    "senat_digit_mobile",
    "senat_digit_admin_web",
    "senat_digit_fs",
)


async def _ensure_consumer_secrets(svc: GenericService) -> Dict[str, str]:
    """Ensure each known consumer has a `consumer_secret`.

    Idempotent: rows that already have a secret are left untouched
    (re-running the seed must not break in-flight clients). New rows or
    rows without a secret get a freshly-generated 256-bit hex value.

    Returns a mapping `flag → secret` for every consumer covered, so the
    summary printer + the run.dev.sh helper can surface them to the dev.
    """
    from app.modules.auth.services.signature.signature_service import (
        SignatureService,
    )

    out: Dict[str, str] = {}
    for flag in _CONSUMER_FLAGS_NEEDING_SECRET:
        consumer = await svc.fetch_one_from_collection(
            collection_key=CollectionKey.REF_API_CONSUMER,
            output_data_type=OutputDataType.DEFAULT,
            query={"filter__flag": flag},
        )
        if not consumer:
            print(f"[demo-seed] WARN: consumer flag={flag} not seeded — skipping")
            continue

        existing_secret = consumer.get("consumer_secret")
        if existing_secret:
            out[flag] = existing_secret
            print(f"[demo-seed] consumer_secret already present for flag={flag}")
            continue

        new_secret = SignatureService.generate_consumer_secret()
        await svc.update_data_in_collection(
            collection_key=CollectionKey.REF_API_CONSUMER,
            item_id=consumer.get("id"),
            data={"consumer_secret": new_secret},
        )
        out[flag] = new_secret
        print(f"[demo-seed] consumer_secret generated for flag={flag}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 0d. System bootstrap (idempotent)
#
# These helpers make the demo seed self-sufficient. If `seed_apps` already
# created the system tenant + admin (the production path), the helpers are
# no-ops. If it didn't (a fresh DB where only `seed_apps.create_profiles`
# ran), the helpers fill the gap so we never need to "log in as system
# super admin" manually to provision the main org — the seed plays that
# role itself.
# ─────────────────────────────────────────────────────────────────────────────

# Generic profil resolver — folded into one function so we don't duplicate
# the lookup logic for SYSTEM vs MAIN. `_resolve_main_profil_id` below
# delegates here for back-compat.
async def _resolve_profil_id(
    svc: GenericService, profil_flag: str
) -> Optional[str]:
    """Look up an RBAC profil by its flag (`system_profil` / `main_profile`)."""
    profil = await svc.fetch_one_from_collection(
        collection_key=CollectionKey.RBAC_PROFILE,
        output_data_type=OutputDataType.DEFAULT,
        query={"filter__flag": profil_flag},
    )
    return profil.get("id") if isinstance(profil, dict) else None


async def _resolve_role_id(
    svc: GenericService, *, profil_id: str, role_flag: str
) -> Optional[str]:
    """Look up an RBAC role under a given profil by its flag."""
    role = await svc.fetch_one_from_collection(
        collection_key=CollectionKey.RBAC_ROLE,
        output_data_type=OutputDataType.DEFAULT,
        query={
            "filter__flag": role_flag,
            "filter__rbac_profile_id": profil_id,
        },
    )
    if not role:
        # Fallback: any default role under this profil.
        role = await svc.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_ROLE,
            output_data_type=OutputDataType.DEFAULT,
            query={
                "filter__is_default": True,
                "filter__rbac_profile_id": profil_id,
            },
        )
    return role.get("id") if isinstance(role, dict) else None


async def _ensure_system_org(
    svc: GenericService, *, profil_id: str
) -> Optional[str]:
    """Ensure the SYSTEM organization exists (idempotent).

    Mirrors `seed_apps.create_organization` for SYSTEM_PROFIL — same
    recipe (sys_organization + cfg_system_organization +
    cfg_related_system_profil + COMMON app-group accessibility) so a
    seed that only ran `create_profiles()` still ends up with a fully
    wired system tenant.
    """
    existing = await svc.fetch_one_from_collection(
        collection_key=CollectionKey.SYS_ORGANIZATION,
        output_data_type=OutputDataType.DEFAULT,
        query={"filter__flag": ESysProfileFlag.SYSTEM_PROFIL.value},
    )
    if existing:
        org_id = existing.get("id")
        print(f"[demo-seed] system org already present → {org_id}")
        return org_id

    # Anchor on the same Kinshasa ref_entity used elsewhere; warn if
    # missing rather than failing (system org has no business data
    # downstream that depends on the entity).
    ref_entity = await svc.fetch_one_from_collection(
        collection_key=CollectionKey.REF_ENTITY,
        output_data_type=OutputDataType.DEFAULT,
        query={"filter__unique_flag": DEMO_ORG_REF_ENTITY_UNIQUE_FLAG},
    )
    ref_entity_id = ref_entity.get("id") if isinstance(ref_entity, dict) else None

    payload = {
        "name": "Système Senat-Digit",
        "flag": ESysProfileFlag.SYSTEM_PROFIL.value,
        "is_default": True,
        "rbac_profile_id": profil_id,
        "ref_entity_id": ref_entity_id,
        "phone_numbers": [{"phone_number": "243831642022"}],
        "emails": [{"email": "system@senat-rdc.cd"}],
        "others": [],
        "address": "Système — administration interne",
        "contact_person": {
            "first_name": "Système",
            "last_name": "Senat-Digit",
            "gender": EGender.MALE.value,
            "email": "system@senat-rdc.cd",
            "phone_number": "243831642022",
        },
    }
    result = await svc.upsert_data_to_collection(
        collection_key=CollectionKey.SYS_ORGANIZATION,
        filter_data={
            "flag": ESysProfileFlag.SYSTEM_PROFIL.value,
            "rbac_profile_id": profil_id,
        },
        update_data=payload,
    )
    org_id = result if isinstance(result, str) else str(result.get("id"))
    print(f"[demo-seed] system org created → {org_id}")

    # Same companion config rows as the main org.
    await svc.upsert_data_to_collection(
        collection_key=CollectionKey.CFG_SYSTEM_ORGANIZATION,
        filter_data={"sys_organization_id": org_id},
        update_data={"sys_organization_id": org_id},
    )
    await svc.upsert_data_to_collection(
        collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
        filter_data={"targeted_id": org_id, "rbac_profile_id": profil_id},
        update_data={"targeted_id": org_id, "rbac_profile_id": profil_id},
    )
    common = await svc.fetch_one_from_collection(
        collection_key=CollectionKey.REF_APPLICATION_GROUP,
        output_data_type=OutputDataType.DEFAULT,
        query={"filter__flag": EAppGroupFlag.COMMON.value},
    )
    if isinstance(common, dict) and common.get("id"):
        await svc.upsert_data_to_collection(
            collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
            filter_data={
                "targeted_id": org_id,
                "ref_application_group_id": common["id"],
            },
            update_data={
                "targeted_id": org_id,
                "ref_application_group_id": common["id"],
            },
        )
    return org_id


# Hardcoded fallbacks used when the running env doesn't supply
# `ADMIN_*` settings. Local-dev only; deployed envs MUST set the env
# vars — see `senat_digit_api/.env.<env>`.
_SYSTEM_ADMIN_FALLBACKS = {
    "username": "admindpsenat",
    "password": "12345@Qwerty",
    "email": "system-admin@senat-rdc.cd",
    "phone_number": "243831642022",
    "first_name": "Système",
    "last_name": "Administrateur",
    "gender": EGender.MALE.value,
}


async def _ensure_system_super_admin(
    svc: GenericService,
    *,
    system_org_id: Optional[str],
    system_profil_id: str,
) -> Optional[str]:
    """Ensure the SYSTEM super-admin user exists (idempotent).

    Resolves credentials from `settings.ADMIN_*` (set by .env.<env>) and
    falls back to hardcoded local defaults when those settings are
    blank. Re-runs leave existing rows untouched — the user can rotate
    the password through the admin web later without the seed
    overwriting it.
    """
    if not system_org_id:
        print("[demo-seed] no system org id — skipping system super admin")
        return None

    # Settings from .env.<env>; fall back to safe local defaults.
    username = (settings.ADMIN_USERNAME or _SYSTEM_ADMIN_FALLBACKS["username"]).strip()
    password = settings.ADMIN_PASSWORD or _SYSTEM_ADMIN_FALLBACKS["password"]
    email = settings.ADMIN_EMAIL or _SYSTEM_ADMIN_FALLBACKS["email"]
    phone = settings.ADMIN_PHONE_NUMBER or _SYSTEM_ADMIN_FALLBACKS["phone_number"]
    first_name = settings.ADMIN_FIRST_NAME or _SYSTEM_ADMIN_FALLBACKS["first_name"]
    last_name = settings.ADMIN_LAST_NAME or _SYSTEM_ADMIN_FALLBACKS["last_name"]
    gender = settings.ADMIN_GENDER or _SYSTEM_ADMIN_FALLBACKS["gender"]

    # Idempotent: do NOT touch an existing row. Operators may have
    # rotated the password through the admin web, and we don't want
    # the seed to clobber it.
    existing = await svc.fetch_one_from_collection(
        collection_key=CollectionKey.SYS_USER,
        output_data_type=OutputDataType.DEFAULT,
        query={"filter__username": username.lower()},
    )
    if existing:
        user_id = existing.get("id")
        # Even on re-runs the bootstrap admin must remain reachable —
        # bump allowed_device_count if the legacy auth pipeline left it
        # at 0 from an earlier failed-login attempt.
        await _ensure_user_can_login(svc, user_id=user_id)
        print(f"[demo-seed] system super admin '{username}' already exists → {user_id}")
        return user_id

    role_id = await _resolve_role_id(
        svc,
        profil_id=system_profil_id,
        role_flag=ESysProfilSuperUserRoleFlag.SYSTEM_PROFIL_SUPER_ADMIN.value,
    )
    if not role_id:
        print(
            "[demo-seed] aborting system admin: SYSTEM_PROFIL_SUPER_ADMIN role "
            "not seeded yet."
        )
        return None

    payload = {
        "username": username,
        "account_status": AccountStatusFlag.ACTIVE.value,
        "password": PasswordService.hash_password(password),
        "sys_organization_id": system_org_id,
        "email": email,
        "phone_number": phone,
        "is_default": True,
        "rbac_profile_id": system_profil_id,
        "rbac_role_id": role_id,
        "gender": gender,
        "first_name": first_name,
        "last_name": last_name,
        "should_update_password": False,
    }
    result = await svc.upsert_data_to_collection(
        collection_key=CollectionKey.SYS_USER,
        filter_data={"username": username},
        update_data=payload,
    )
    user_id = result if isinstance(result, str) else result.get("id")
    if user_id:
        await svc.update_data_in_collection(
            collection_key=CollectionKey.SYS_USER,
            item_id=user_id,
            data={
                "user_account_hash": HashService.generate_hash(str(user_id)),
                "user_account_socket_hash": HashService.generate_hash(str(user_id)),
            },
        )
        # Same login-eligibility safeguard as `_ensure_user`. The system
        # admin is the bootstrap entry point — they MUST be reachable
        # right after seeding, otherwise no one can provision tenants.
        await _ensure_user_can_login(svc, user_id=user_id)
    print(f"[demo-seed] system super admin created → username={username} id={user_id}")
    return user_id


# ─────────────────────────────────────────────────────────────────────────────
# 0e. Login eligibility — make the seeded user actually reachable
# ─────────────────────────────────────────────────────────────────────────────

# Number of concurrent devices a demo account can pair. 5 covers the
# common dev case (laptop + phone + emulator + a couple of curl smoke
# devices). Production tenants keep the legacy default (1) by setting a
# narrower cfg_saas_config policy — this constant only governs the demo
# seed.
_DEMO_ALLOWED_DEVICE_COUNT = 5


async def _ensure_user_can_login(svc: GenericService, *, user_id: str) -> None:
    """Make sure the demo user can actually log in.

    The legacy auth pipeline lazily creates `cfg_user_config` on the first
    login with `allowed_device_count: 0`, which then locks every
    subsequent login with the "périphériques autorisés" 401. For a demo
    tenant that's a footgun — every reseed leaves us unable to validate
    the bootstrap flow without first hand-editing Mongo.

    Idempotent: upserts a config row keyed on `sys_user_id` and only
    bumps `allowed_device_count` when it's below the demo floor (so an
    operator who tightened the value won't get clobbered).

    Implementation note: bypasses GenericService and goes through the
    raw motor client because the legacy upsert_data_to_collection
    silently no-ops when no row exists for new users (likely a quirk of
    the multi-step pipeline + group-validation context). Seed-time
    direct DB access is the established pattern (see _ensure_notifications
    using NtfNotificationModel directly for the same reason).
    """
    from datetime import datetime, timezone
    from beanie import PydanticObjectId
    from app.db.base import get_collection
    coll = get_collection("cfg_user_config")
    user_oid = (
        user_id
        if isinstance(user_id, PydanticObjectId)
        else PydanticObjectId(str(user_id))
    )
    now = datetime.now(timezone.utc)
    await coll.update_one(
        {"sys_user_id": user_oid},
        {
            "$set": {
                "sys_user_id": user_oid,
                "allowed_device_count": _DEMO_ALLOWED_DEVICE_COUNT,
                "updated_at": now,
            },
            "$setOnInsert": {
                "is_activated": True,
                "soft_deleted": False,
                "created_at": now,
                "translations": {},
            },
        },
        upsert=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Main profil / org / role
# ─────────────────────────────────────────────────────────────────────────────

async def _resolve_main_profil_id(svc: GenericService) -> Optional[str]:
    """Back-compat wrapper around `_resolve_profil_id` for the main profil."""
    return await _resolve_profil_id(svc, ESysProfileFlag.MAIN_PROFILE.value)


async def _ensure_main_org(
    svc: GenericService, *, profil_id: str
) -> Optional[str]:
    """Create (or update) the main organisation for the demo.

    Mirrors `seed_apps.create_organization` 1:1 — same recipe so RLS and
    auth see this exactly like a real tenant:
       - SYS_ORGANIZATION row keyed on (flag, rbac_profile_id)
       - CFG_SYSTEM_ORGANIZATION linked to it
       - CFG_RELATED_SYSTEM_PROFIL binding org → profil
       - CFG_APPLICATION_GROUP_ACCESSIBILITY for the COMMON app group so
         the catalogue routes are reachable.

    `seed_apps` only creates the SYSTEM_PROFIL org out of the box; this
    helper fills in the missing main org for senat_digit demo runs.
    """
    # Resolve a ref_entity for the org. We anchor on Kinshasa (rdc-town-
    # kinshasa is the same node `seed_apps` uses for the system org).
    ref_entity = await svc.fetch_one_from_collection(
        collection_key=CollectionKey.REF_ENTITY,
        output_data_type=OutputDataType.DEFAULT,
        query={"filter__unique_flag": DEMO_ORG_REF_ENTITY_UNIQUE_FLAG},
    )
    ref_entity_id = ref_entity.get("id") if isinstance(ref_entity, dict) else None
    if not ref_entity_id:
        print(
            "[demo-seed] WARN: ref_entity 'rdc-town-kinshasa' missing — geo "
            "hierarchy seed may not have run. Continuing without ref_entity."
        )

    new_org = {
        "name": DEMO_ORG_NAME,
        "flag": DEMO_ORG_FLAG,
        "is_default": True,
        "rbac_profile_id": profil_id,
        "ref_entity_id": ref_entity_id,
        "phone_numbers": [{"phone_number": "243831000000"}],
        "emails": [{"email": "contact@senat-rdc.cd"}],
        "others": [],
        "address": "Place du Cinquantenaire, Kinshasa, R.D. Congo",
        "contact_person": {
            "first_name": "Greffier",
            "last_name": "Principal",
            "gender": EGender.MALE.value,
            "email": "greffier@senat-rdc.cd",
            "phone_number": "243800000099",
        },
    }

    result = await svc.upsert_data_to_collection(
        collection_key=CollectionKey.SYS_ORGANIZATION,
        filter_data={
            "flag": DEMO_ORG_FLAG,
            "rbac_profile_id": profil_id,
        },
        update_data=new_org,
    )
    org_id = result if isinstance(result, str) else str(result.get("id"))
    print(f"[demo-seed] main org_id={org_id}")

    # Bind the org to the system_organization config row (used by quorum,
    # vote-secret crypto, RLS-enable settings — defaults are fine for demo).
    await svc.upsert_data_to_collection(
        collection_key=CollectionKey.CFG_SYSTEM_ORGANIZATION,
        filter_data={"sys_organization_id": org_id},
        update_data={"sys_organization_id": org_id},
    )

    # Bind org → profil so the auth handshake can resolve the right profil
    # when a user logs in.
    await svc.upsert_data_to_collection(
        collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
        filter_data={
            "targeted_id": org_id,
            "rbac_profile_id": profil_id,
        },
        update_data={
            "targeted_id": org_id,
            "rbac_profile_id": profil_id,
        },
    )

    # Grant access to the COMMON app group so the auth/profile/notification
    # routes are visible. Without this the post-login app-fetch returns an
    # empty catalogue and the Flutter app sits on a blank shell.
    common = await svc.fetch_one_from_collection(
        collection_key=CollectionKey.REF_APPLICATION_GROUP,
        output_data_type=OutputDataType.DEFAULT,
        query={"filter__flag": EAppGroupFlag.COMMON.value},
    )
    if isinstance(common, dict) and common.get("id"):
        await svc.upsert_data_to_collection(
            collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
            filter_data={
                "targeted_id": org_id,
                "ref_application_group_id": common["id"],
            },
            update_data={
                "targeted_id": org_id,
                "ref_application_group_id": common["id"],
            },
        )

    return org_id


# ─────────────────────────────────────────────────────────────────────────────
# 2. Users
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_user(
    svc: GenericService,
    *,
    username: str,
    password: str,
    first_name: str,
    last_name: str,
    gender: str,
    email: str,
    phone: str,
    org_id: str,
    profil_id: str,
    role_id: str,
) -> Optional[str]:
    existing = await svc.fetch_one_from_collection(
        collection_key=CollectionKey.SYS_USER,
        output_data_type=OutputDataType.DEFAULT,
        query={"filter__username": username},
    )
    if existing:
        user_id = existing.get("id")
        # Reconcile role/profil on re-runs. Earlier dummy_seed runs assigned
        # everyone to MAIN_PROFILE_SUPER_ADMIN; the SENATEUR/GREFFIER split
        # was added later. Without this update, re-seeding leaves demo
        # users with their old (now-mismatched) role and the RBAC matrix
        # we just seeded never applies. Password is intentionally NOT
        # rewritten — preserves any rotation done through the admin web.
        existing_role = str(existing.get("rbac_role_id") or "")
        existing_profil = str(existing.get("rbac_profile_id") or "")
        if existing_role != str(role_id) or existing_profil != str(profil_id):
            await svc.update_data_in_collection(
                collection_key=CollectionKey.SYS_USER,
                item_id=user_id,
                data={
                    "rbac_role_id": role_id,
                    "rbac_profile_id": profil_id,
                },
            )
            print(
                f"[demo-seed] user {username} reconciled → role_id={role_id} profil_id={profil_id}"
            )
        else:
            print(f"[demo-seed] user {username} already exists → {user_id}")
        # Reconcile login eligibility on every re-run too. Earlier seed
        # runs (or a failed first login) may have left cfg_user_config
        # with allowed_device_count=0, locking the user out.
        await _ensure_user_can_login(svc, user_id=user_id)
        return user_id

    payload = {
        "username": username,
        "account_status": AccountStatusFlag.ACTIVE.value,
        "password": PasswordService.hash_password(password),
        "sys_organization_id": org_id,
        "email": email,
        "phone_number": phone,
        "is_default": False,
        "rbac_profile_id": profil_id,
        "rbac_role_id": role_id,
        "gender": gender,
        "first_name": first_name,
        "last_name": last_name,
        # Demo accounts are pre-configured — no forced password update on
        # first login, otherwise reviewers get bounced to /force-password.
        "should_update_password": False,
    }
    result = await svc.upsert_data_to_collection(
        collection_key=CollectionKey.SYS_USER,
        filter_data={"username": username},
        update_data=payload,
    )
    user_id = result if isinstance(result, str) else result.get("id")
    if user_id:
        # Populate the account hashes the auth flow expects.
        await svc.update_data_in_collection(
            collection_key=CollectionKey.SYS_USER,
            item_id=user_id,
            data={
                "user_account_hash": HashService.generate_hash(str(user_id)),
                "user_account_socket_hash": HashService.generate_hash(str(user_id)),
            },
        )
        # Ensure the user can actually log in. The legacy auth pipeline
        # creates cfg_user_config on first login with `allowed_device_count: 0`,
        # which then blocks every subsequent login with "Désolé ! vous avez
        # atteint le nombre maximum de périphériques autorisés". For a demo
        # tenant we want every seeded user to be reachable out of the box.
        await _ensure_user_can_login(svc, user_id=user_id)
    print(f"[demo-seed] created user {username} → {user_id}")
    return user_id


# ─────────────────────────────────────────────────────────────────────────────
# 3. Session
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_session(
    svc: GenericService, *, org_id: str
) -> Optional[str]:
    # We key on a synthetic identifier so the same demo run upserts cleanly.
    DEMO_SESSION_IDENTIFIER = "demo-session-2026-04-30"
    existing = await svc.fetch_one_from_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        output_data_type=OutputDataType.DEFAULT,
        query={"filter__identifier": DEMO_SESSION_IDENTIFIER},
    )
    now = datetime.now(timezone.utc)
    opened_at = now - timedelta(minutes=30)
    scheduled_at = now - timedelta(hours=2)

    payload = {
        "identifier": DEMO_SESSION_IDENTIFIER,
        "sys_organization_id": org_id,
        "title": SESSION_TITLE,
        "description_str": SESSION_DESCRIPTION,
        "scheduled_at": scheduled_at,
        "mode": ESessionMode.PRESENTIEL.value,
        "status": ESessionStatus.OUVERTE.value,
        "opened_at": opened_at,
        "total_seats": 109,            # taille du Sénat congolais
        "required_quorum_count": 55,   # majorité simple sur 109
    }
    if existing:
        await svc.update_data_in_collection(
            collection_key=CollectionKey.SESSION_MEETING,
            item_id=existing.get("id"),
            data=payload,
        )
        print(f"[demo-seed] session updated → {existing.get('id')}")
        return existing.get("id")

    result = await svc.upsert_data_to_collection(
        collection_key=CollectionKey.SESSION_MEETING,
        filter_data={"identifier": DEMO_SESSION_IDENTIFIER},
        update_data=payload,
    )
    sid = result if isinstance(result, str) else result.get("id")
    print(f"[demo-seed] session created → {sid}")
    return sid


# ─────────────────────────────────────────────────────────────────────────────
# 4. Session participants
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_participant(
    svc: GenericService,
    *,
    session_id: str,
    org_id: str,
    user_id: str,
    role: str,
    can_vote: bool,
) -> Optional[str]:
    existing = await svc.fetch_one_from_collection(
        collection_key=CollectionKey.SESSION_PARTICIPANT,
        output_data_type=OutputDataType.DEFAULT,
        query={
            "filter__session_meeting_id": session_id,
            "filter__sys_user_id": user_id,
        },
    )
    if existing:
        return existing.get("id")
    payload = {
        "session_meeting_id": session_id,
        "sys_user_id": user_id,
        "sys_organization_id": org_id,
        "role": role,
        "can_vote": can_vote,
    }
    result = await svc.upsert_data_to_collection(
        collection_key=CollectionKey.SESSION_PARTICIPANT,
        filter_data={
            "session_meeting_id": session_id,
            "sys_user_id": user_id,
        },
        update_data=payload,
    )
    return result if isinstance(result, str) else result.get("id")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Agenda items
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_agenda(
    svc: GenericService, *, org_id: str, session_id: str
) -> List[str]:
    ids: List[str] = []
    now = datetime.now(timezone.utc)
    for i, item in enumerate(AGENDA_ITEMS):
        identifier = f"demo-agenda-{i+1:02d}-{session_id}"
        existing = await svc.fetch_one_from_collection(
            collection_key=CollectionKey.AGENDA_ITEM,
            output_data_type=OutputDataType.DEFAULT,
            query={"filter__identifier": identifier},
        )
        payload: Dict[str, Any] = {
            "identifier": identifier,
            "session_meeting_id": session_id,
            "sys_organization_id": org_id,
            "title": item["title"],
            "description_str": item["description"],
            "order_index": i,
            "is_active": item["is_active"],
            "is_published": True,
            "published_at": now - timedelta(hours=1),
        }
        if item["is_active"]:
            payload["activated_at"] = now - timedelta(minutes=15)

        if existing:
            await svc.update_data_in_collection(
                collection_key=CollectionKey.AGENDA_ITEM,
                item_id=existing.get("id"),
                data=payload,
            )
            ids.append(existing.get("id"))
        else:
            result = await svc.upsert_data_to_collection(
                collection_key=CollectionKey.AGENDA_ITEM,
                filter_data={"identifier": identifier},
                update_data=payload,
            )
            new_id = result if isinstance(result, str) else result.get("id")
            if new_id:
                ids.append(new_id)
    print(f"[demo-seed] agenda items: {len(ids)}")
    return ids


# ─────────────────────────────────────────────────────────────────────────────
# 6. Documents (metadata-only — arch_file_id stays null)
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_documents(
    svc: GenericService,
    *,
    org_id: str,
    session_id: str,
    active_agenda_id: Optional[str],
) -> Dict[str, str]:
    """Returns a mapping `typology_value → doc_id`."""
    docs: Dict[str, Dict[str, Any]] = {
        EDocumentTypology.TEXTE_LOI.value: {
            "title": "Projet de loi portant budget rectificatif de l'exercice 2026",
            "description": (
                "Texte soumis par le gouvernement portant ajustement des "
                "recettes et dépenses publiques au titre de l'exercice 2026."
            ),
            "identifier": "demo-doc-texte-loi-2026",
        },
        EDocumentTypology.RESOLUTION.value: {
            "title": "Résolution sur le budget rectificatif 2026",
            "description": (
                "Résolution proposée à l'adoption du Sénat suite à l'examen "
                "du projet de loi portant budget rectificatif 2026."
            ),
            "identifier": "demo-doc-resolution-2026",
        },
        EDocumentTypology.RAPPORT.value: {
            "title": "Rapport de la Commission des finances et du budget",
            "description": (
                "Rapport circonstancié de la commission permanente des "
                "finances et du budget sur le projet de loi rectificative."
            ),
            "identifier": "demo-doc-rapport-2026",
        },
    }
    now = datetime.now(timezone.utc)
    out: Dict[str, str] = {}
    for typology_value, meta in docs.items():
        existing = await svc.fetch_one_from_collection(
            collection_key=CollectionKey.DOCUMENT_META,
            output_data_type=OutputDataType.DEFAULT,
            query={"filter__identifier": meta["identifier"]},
        )
        payload: Dict[str, Any] = {
            "identifier": meta["identifier"],
            "sys_organization_id": org_id,
            "title": meta["title"],
            "description_str": meta["description"],
            "typology": typology_value,
            # version_chain_id is a PydanticObjectId — derive a stable 24-char
            # hex from the human identifier so re-runs of the seed converge.
            "version_chain_id": _stable_oid_hex(meta["identifier"]),
            "current_version_number": 1,
            # arch_file_id intentionally omitted: dev DB has no FS upload.
            # Flutter degrades to "Métadonnées seules" + disabled CTA.
            "linked_session_id": session_id,
            "linked_agenda_item_ids": [active_agenda_id] if active_agenda_id else [],
            "is_published": True,
            "published_at": now - timedelta(hours=1),
        }
        if existing:
            await svc.update_data_in_collection(
                collection_key=CollectionKey.DOCUMENT_META,
                item_id=existing.get("id"),
                data=payload,
            )
            out[typology_value] = existing.get("id")
        else:
            result = await svc.upsert_data_to_collection(
                collection_key=CollectionKey.DOCUMENT_META,
                filter_data={"identifier": meta["identifier"]},
                update_data=payload,
            )
            new_id = result if isinstance(result, str) else result.get("id")
            if new_id:
                out[typology_value] = new_id
    print(f"[demo-seed] documents created: {list(out.keys())}")
    return out


async def _link_docs_to_agenda(
    svc: GenericService,
    *,
    agenda_id: str,
    doc_ids: List[str],
) -> None:
    if not agenda_id or not doc_ids:
        return
    await svc.update_data_in_collection(
        collection_key=CollectionKey.AGENDA_ITEM,
        item_id=agenda_id,
        data={"linked_document_ids": doc_ids},
    )
    print(f"[demo-seed] linked {len(doc_ids)} docs → agenda {agenda_id}")


# ─────────────────────────────────────────────────────────────────────────────
# 7-8. Vote config + result (CLOS, decision=ADOPTE)
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_vote_config(
    svc: GenericService,
    *,
    org_id: str,
    session_id: str,
    resolution_id: str,
) -> Optional[str]:
    DEMO_VOTE_IDENTIFIER = "demo-vote-resolution-2026"
    existing = await svc.fetch_one_from_collection(
        collection_key=CollectionKey.VOTE_CONFIG,
        output_data_type=OutputDataType.DEFAULT,
        query={"filter__identifier": DEMO_VOTE_IDENTIFIER},
    )
    now = datetime.now(timezone.utc)
    opened_at = now - timedelta(minutes=20)
    closed_at = now - timedelta(minutes=10)

    payload = {
        "identifier": DEMO_VOTE_IDENTIFIER,
        "sys_organization_id": org_id,
        "session_meeting_id": session_id,
        "resolution_id": resolution_id,
        "title": "Adoption de la résolution sur le budget rectificatif 2026",
        "description_str": (
            "Vote sur l'adoption de la résolution portant budget rectificatif "
            "de l'exercice 2026, suite à l'examen en commission et au débat en séance."
        ),
        "ballot_type": EVoteBallotType.OUI_NON.value,
        "is_secret": False,
        "majority_type": EVoteMajorityType.RELATIVE.value,
        "duration_seconds": 120,
        "allow_proxies": True,
        "status": EVoteStatus.CLOS.value,
        "opened_at": opened_at,
        "closed_at": closed_at,
        "ballots_cast_count": 87,
    }
    if existing:
        await svc.update_data_in_collection(
            collection_key=CollectionKey.VOTE_CONFIG,
            item_id=existing.get("id"),
            data=payload,
        )
        return existing.get("id")
    result = await svc.upsert_data_to_collection(
        collection_key=CollectionKey.VOTE_CONFIG,
        filter_data={"identifier": DEMO_VOTE_IDENTIFIER},
        update_data=payload,
    )
    cfg_id = result if isinstance(result, str) else result.get("id")
    print(f"[demo-seed] vote_config created → {cfg_id}")
    return cfg_id


async def _ensure_vote_result(
    svc: GenericService, *, org_id: str, vote_config_id: str
) -> Optional[str]:
    DEMO_RESULT_IDENTIFIER = f"demo-vote-result-{vote_config_id}"
    existing = await svc.fetch_one_from_collection(
        collection_key=CollectionKey.VOTE_RESULT,
        output_data_type=OutputDataType.DEFAULT,
        query={"filter__identifier": DEMO_RESULT_IDENTIFIER},
    )
    # Tally that adopts comfortably under the majorité relative — also
    # gives a balanced 4-segment donut so the legend isn't all-blue.
    count_pour = 64
    count_contre = 14
    count_abstention = 7
    count_npv = 2
    total = count_pour + count_contre + count_abstention + count_npv  # 87
    payload = {
        "identifier": DEMO_RESULT_IDENTIFIER,
        "sys_organization_id": org_id,
        "vote_config_id": vote_config_id,
        "count_pour": count_pour,
        "count_contre": count_contre,
        "count_abstention": count_abstention,
        "count_npv": count_npv,
        "ballot_headcount": 87,
        "total_weighted": total,
        "majority_required_count": 44,   # 87 / 2 + 1, majorité relative arrondie
        "majority_met": True,
        "decision": "ADOPTE",
        "computed_at": datetime.now(timezone.utc),
    }
    if existing:
        await svc.update_data_in_collection(
            collection_key=CollectionKey.VOTE_RESULT,
            item_id=existing.get("id"),
            data=payload,
        )
        return existing.get("id")
    result = await svc.upsert_data_to_collection(
        collection_key=CollectionKey.VOTE_RESULT,
        filter_data={"identifier": DEMO_RESULT_IDENTIFIER},
        update_data=payload,
    )
    res_id = result if isinstance(result, str) else result.get("id")
    print(f"[demo-seed] vote_result created → {res_id} (decision=ADOPTE)")
    return res_id


# ─────────────────────────────────────────────────────────────────────────────
# 9. Notifications
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_notifications(
    svc: GenericService,
    *,
    org_id: str,
    target_user_id: str,
    session_id: str,
    agenda_id: Optional[str],
    doc_id: Optional[str],
    vote_config_id: Optional[str],
) -> None:
    """Mix of unread + read across event types so the inbox shows the
    full design vocabulary (red unread border, day-grouping, type label)."""
    now = datetime.now(timezone.utc)
    notifs: List[Dict[str, Any]] = [
        {
            "title": "Séance ouverte",
            "body": f"{SESSION_TITLE} — la séance est désormais en cours.",
            "alert_type": ENotificationEventType.SESSION_OPENED.value,
            "snapshot_id": session_id,
            "created_at": now - timedelta(minutes=30),
            "is_read": True,
        },
        {
            "title": "Ordre du jour publié",
            "body": "L'ordre du jour de la séance a été publié et est consultable.",
            "alert_type": ENotificationEventType.AGENDA_PUBLISHED.value,
            "snapshot_id": None,
            "created_at": now - timedelta(minutes=28),
            "is_read": True,
        },
        {
            "title": "Document publié",
            "body": "Projet de loi portant budget rectificatif 2026 — disponible en lecture.",
            "alert_type": ENotificationEventType.DOCUMENT_PUBLISHED.value,
            "snapshot_id": doc_id,
            "created_at": now - timedelta(minutes=25),
            "is_read": False,
        },
        {
            "title": "Point activé",
            "body": "Le point « Examen de la résolution sur le budget rectificatif 2026 » est en discussion.",
            "alert_type": ENotificationEventType.AGENDA_ITEM_ACTIVATED.value,
            "snapshot_id": agenda_id,
            "created_at": now - timedelta(minutes=15),
            "is_read": False,
        },
        {
            "title": "Scrutin ouvert",
            "body": "Vote sur la résolution — vous avez 2 minutes pour voter.",
            "alert_type": ENotificationEventType.VOTE_OPENED.value,
            "snapshot_id": vote_config_id,
            "created_at": now - timedelta(minutes=20),
            "is_read": True,
        },
        {
            "title": "Scrutin clos",
            "body": "Résolution sur le budget rectificatif 2026 — résultats disponibles.",
            "alert_type": ENotificationEventType.VOTE_CLOSED.value,
            "snapshot_id": vote_config_id,
            "created_at": now - timedelta(minutes=10),
            "is_read": False,
        },
        {
            "title": "Annonce du greffier",
            "body": "La séance se poursuit avec les questions orales au gouvernement.",
            "alert_type": ENotificationEventType.BROADCAST.value,
            "snapshot_id": None,
            "created_at": now - timedelta(minutes=5),
            "is_read": False,
        },
    ]

    # GenericService's `convert_id_fields` blindly coerces any value with
    # an `_id`-suffixed key into an ObjectId — even when the model declares
    # it as `Optional[str]` (the case for `snapshot_id`). Production
    # bypasses GenericService for this collection and uses the Beanie model
    # directly (see notification_service.NotificationService.emit_one).
    # We mirror that pattern here.
    target_oid = (
        target_user_id
        if isinstance(target_user_id, PydanticObjectId)
        else PydanticObjectId(str(target_user_id))
    )
    inserted = 0
    skipped = 0
    for n in notifs:
        identifier = (
            f"demo-notif-{target_user_id}-{n['alert_type']}-"
            f"{int(n['created_at'].timestamp())}"
        )
        # Idempotent: skip if a row with this identifier already exists.
        # Notifications are immutable events — re-runs don't rewrite them.
        existing = await NtfNotificationModel.find_one(
            NtfNotificationModel.identifier == identifier
        )
        if existing is not None:
            skipped += 1
            continue
        row = NtfNotificationModel(
            identifier=identifier,
            title=n["title"],
            notification=n["body"],
            targeted_id=target_oid,
            is_read=n["is_read"],
            alert_type=n["alert_type"],
            snapshot_id=n["snapshot_id"],
            created_at=n["created_at"],
        )
        await row.insert()
        inserted += 1
    print(
        f"[demo-seed] notifications: inserted={inserted}, skipped={skipped}, "
        f"target={target_user_id}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Final summary
# ─────────────────────────────────────────────────────────────────────────────

def _print_summary(
    *,
    senateur_ids: List[str],
    greffier_id: Optional[str],
    main_admin_id: Optional[str],
    consumer_secrets: Dict[str, str],
    sys_admin_id: Optional[str],
) -> None:
    sys_admin_username = (
        settings.ADMIN_USERNAME or _SYSTEM_ADMIN_FALLBACKS["username"]
    ).strip()
    sys_admin_password = (
        settings.ADMIN_PASSWORD or _SYSTEM_ADMIN_FALLBACKS["password"]
    )

    print("\n" + "═" * 78)
    print("[demo-seed] DONE — credentials")
    print("═" * 78)
    print("  ── SYSTEM_PROFIL (cross-tenant / bootstrap) ───────────────────────")
    print(
        f"  Sys admin     → {sys_admin_username}    /  {sys_admin_password}    "
        f"(creates orgs; cross-tenant break-glass)"
    )
    print()
    print("  ── MAIN_PROFILE (Sénat de la RDC tenant) ──────────────────────────")
    print(
        f"  Direction     → {MAIN_ADMIN_USERNAME}    /  {DEMO_PASSWORD_MAIN_ADMIN}    "
        f"(in-org IT/owner: create users, lock, password reset)"
    )
    print(
        f"  Greffier      → {GREFFIER_USERNAME}    /  {DEMO_PASSWORD_GREFFIER}    "
        f"(session orchestration; no user mgmt)"
    )
    for s in SENATEURS:
        print(
            f"  Sénateur      → {s['username']}    /  {DEMO_PASSWORD_SENATEUR}    "
            f"({s['first_name']} {s['last_name']})"
        )
    print()
    print(f"  sys_admin_id   = {sys_admin_id}")
    print(f"  greffier_id    = {greffier_id}")
    print(f"  senateur_ids   = {senateur_ids}")
    print()
    print("  Demo session   → ouverte depuis 30 min · 6 points · 1 actif")
    print("  Demo vote      → CLOS · décision ADOPTÉ · majorité atteinte")
    print("  Inbox          → 7 notifications targeting senateur1 (mix lu/non lu)")

    if consumer_secrets:
        print()
        print("  HMAC consumer_secrets (bake into client builds — ⚠ treat as creds):")
        for flag, secret in consumer_secrets.items():
            print(f"    {flag:32s}  {secret}")
        print()
        print("  bash/run.dev.sh reads the mobile secret from Mongo automatically.")
        print("  For other clients pass it via env at build time, e.g.")
        print("    --dart-define=SENAT_API_CONSUMER_SECRET=<secret>")
    print("═" * 78 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Entry
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_data())
