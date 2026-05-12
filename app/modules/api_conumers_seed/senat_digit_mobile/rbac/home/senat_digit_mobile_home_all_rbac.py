"""RBAC permission seeds for the Home tab tiles.

For each tile defined in `apps/home/senat_digit_mobile_home_sub_menus.py`,
we register an `rbac_permission` row with:
  - a unique `flag` (the tile's path_guard, reused as permission flag)
  - `rbac_roles_list` — which roles get granted this permission
  - `sys_apps_list` + `sys_menus_list` — what the permission targets
    (fed to `rbac_permission_target` rows)

This is what makes the tile actually appear in
`/static/data/get-application-user-submenus`. Without this seed, the
sys_menu row exists in Mongo but the controller's role-permission
aggregation pipeline filters it out.

Mirrors the lokotroo pattern from
`lokotroo_flutter_app/rbac/home/<leaf>/lokotroo_flutter_home_<leaf>_rbac.py`
but consolidated into one file because senat-digit's tiles have a
single permission each (no per-action sub-permissions like lokotroo's
`loading_ewallets` / `initiating_wallet_reload` etc).
"""

from app.modules.core.constants.common import (
    ALL_PROFIL_IN_ONE,
    FLUTTER_AGENT_APP_API_CONSUMER_IN_ONE,
    MAIN_PROFILE_IN_ONE,
    SYSTEM_ORGANIZATION_PROFIL_IN_ONE,
)
from app.modules.core.seeds.rbac_seed_service import app_link, menu_link

from app.modules.api_conumers_seed.senat_digit_mobile.rbac.senat_digit_mobile_rbac_roles import (
    GREFFIER_TILE_ROLES,
    MAINADMIN_TILE_ROLES,
    SENATEUR_TILE_ROLES,
    SYSADMIN_TILE_ROLES,
)


_APP_FLAG = "apps_senat_home_app"
_API_CONSUMERS = [*FLUTTER_AGENT_APP_API_CONSUMER_IN_ONE]


def _tile_permission(
    flag: str,
    label: str,
    roles: list,
    profiles: list,
) -> dict:
    """Build one permission seed dict targeting a single home tile.

    The flag is reused as both the permission flag and the menu's
    path_guard — keeps the wiring obvious end-to-end.
    """
    return {
        "flag": flag,
        "label": label,
        "description_str": "",
        "is_link_deleted": False,
        "core_seeds": {
            "restricted_profil_list": profiles,
            "restricted_api_consumer_list": _API_CONSUMERS,
            "rbac_roles_list": roles,
            "sys_apps_list": [app_link(_APP_FLAG)],
            "sys_menus_list": [menu_link(flag)],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [],
                "action_to_apps": [],
            },
            "rbac_custom_actions_obj": {
                "action_to_menus": [],
                "action_to_apps": [],
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {},
                "collection_meta_data_to_apps": {},
            },
        },
    }


# ── Sénateur tiles ───────────────────────────────────────────────────
_SEN = [
    _tile_permission(
        "apps_senat_home_sen_sign_presence_page",
        "[Sénat-Digit - Accueil - Sénateur] Signer présence",
        SENATEUR_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
    _tile_permission(
        "apps_senat_home_sen_request_parole_page",
        "[Sénat-Digit - Accueil - Sénateur] Demander la parole",
        SENATEUR_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
    _tile_permission(
        "apps_senat_home_sen_active_vote_page",
        "[Sénat-Digit - Accueil - Sénateur] Vote en cours",
        SENATEUR_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
    _tile_permission(
        "apps_senat_home_sen_my_votes_page",
        "[Sénat-Digit - Accueil - Sénateur] Mes votes",
        SENATEUR_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
    _tile_permission(
        "apps_senat_home_sen_give_proxy_page",
        "[Sénat-Digit - Accueil - Sénateur] Donner pouvoir",
        SENATEUR_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
]


# ── Greffier tiles ───────────────────────────────────────────────────
_GRF = [
    _tile_permission(
        "apps_senat_home_grf_session_control_page",
        "[Sénat-Digit - Accueil - Greffier] Ouvrir/clôturer la séance",
        GREFFIER_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
    _tile_permission(
        "apps_senat_home_grf_configure_vote_page",
        "[Sénat-Digit - Accueil - Greffier] Configurer un scrutin",
        GREFFIER_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
    _tile_permission(
        "apps_senat_home_grf_parole_queue_page",
        "[Sénat-Digit - Accueil - Greffier] File de parole",
        GREFFIER_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
    _tile_permission(
        "apps_senat_home_grf_presence_live_page",
        "[Sénat-Digit - Accueil - Greffier] Présences en direct",
        GREFFIER_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
    _tile_permission(
        "apps_senat_home_grf_agenda_manage_page",
        "[Sénat-Digit - Accueil - Greffier] Ordre du jour",
        GREFFIER_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
    _tile_permission(
        "apps_senat_home_grf_manual_tally_page",
        "[Sénat-Digit - Accueil - Greffier] Comptage manuel",
        GREFFIER_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
]


# ── Main_profile super-admin tiles ───────────────────────────────────
_ADM = [
    _tile_permission(
        "apps_senat_home_adm_users_page",
        "[Sénat-Digit - Accueil - Admin] Utilisateurs",
        MAINADMIN_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
    _tile_permission(
        "apps_senat_home_adm_devices_page",
        "[Sénat-Digit - Accueil - Admin] Validation appareils",
        MAINADMIN_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
    _tile_permission(
        "apps_senat_home_adm_org_config_page",
        "[Sénat-Digit - Accueil - Admin] Configuration organisation",
        MAINADMIN_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
    _tile_permission(
        "apps_senat_home_adm_audit_page",
        "[Sénat-Digit - Accueil - Admin] Journal d'audit",
        MAINADMIN_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
    _tile_permission(
        "apps_senat_home_adm_stats_page",
        "[Sénat-Digit - Accueil - Admin] Statistiques",
        MAINADMIN_TILE_ROLES,
        [*MAIN_PROFILE_IN_ONE],
    ),
]


# ── System_profil super-admin tiles ──────────────────────────────────
# Trimmed to 2 tiles per operator spec: org CRUD + user lock/unlock +
# reset-password link. Login history + all-devices were dropped from
# the agreed sysadmin scope — drill-down from user detail covers
# per-user device management when needed.
_SYS = [
    _tile_permission(
        "apps_senat_home_sys_org_page",
        "[Sénat-Digit - Accueil - System] Sénat (organisation)",
        SYSADMIN_TILE_ROLES,
        [*SYSTEM_ORGANIZATION_PROFIL_IN_ONE],
    ),
    _tile_permission(
        "apps_senat_home_sys_users_page",
        "[Sénat-Digit - Accueil - System] Utilisateurs Sénat",
        SYSADMIN_TILE_ROLES,
        [*SYSTEM_ORGANIZATION_PROFIL_IN_ONE],
    ),
]


# ── Top-level bottom-nav app permissions ─────────────────────────────
# Each top-level app needs an `rbac_permission` row whose
# `rbac_permission_target` points at the `sys_application` and whose
# `rbac_permission_role` is granted to the right senat roles. Without
# this, the controller's per-app double-check pipeline forces
# `is_activated=False` on the app, the Flutter `AppEntry.isVisible`
# returns false, and the bottom-nav silently drops the tab.
#
# Visibility intent (matches `apps/senat_digit_mobile_app.py` profile
# gating, but at the role-grant axis the controller actually filters
# on):
#   - Accueil + Plus  → ALL senat roles (sénateur/greffier/mainadmin/sysadmin).
#   - Séance / Documents / Votes  → main_profile roles only. Sysadmin
#     stays cross-tenant ops, doesn't run plenary business.
def _top_level_app_permission(
    flag: str,
    label: str,
    *,
    main_only: bool,
) -> dict:
    profile_scope = (
        [*MAIN_PROFILE_IN_ONE] if main_only else [*ALL_PROFIL_IN_ONE]
    )
    role_scope = [
        *SENATEUR_TILE_ROLES,
        *GREFFIER_TILE_ROLES,
        *MAINADMIN_TILE_ROLES,
    ]
    if not main_only:
        role_scope = [*role_scope, *SYSADMIN_TILE_ROLES]

    return {
        "flag": flag,
        "label": label,
        "description_str": "",
        "is_link_deleted": False,
        "core_seeds": {
            "restricted_profil_list": profile_scope,
            "restricted_api_consumer_list": _API_CONSUMERS,
            "rbac_roles_list": role_scope,
            "sys_apps_list": [app_link(flag)],
            "sys_menus_list": [],
            "rbac_standalone_actions_obj": {"action_to_menus": [], "action_to_apps": []},
            "rbac_custom_actions_obj": {"action_to_menus": [], "action_to_apps": []},
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {},
                "collection_meta_data_to_apps": {},
            },
        },
    }


_ACCUEIL_APP = _top_level_app_permission(
    "apps_senat_home_app",
    "[Sénat-Digit] Onglet Accueil",
    main_only=False,  # sysadmin uses Accueil to reach the sys-* tiles
)

_SESSION_APP = _top_level_app_permission(
    "apps_senat_session_app",
    "[Sénat-Digit] Onglet Séance",
    main_only=True,
)

_DOCUMENTS_APP = _top_level_app_permission(
    "apps_senat_documents_app",
    "[Sénat-Digit] Onglet Documents",
    main_only=True,
)

_VOTES_APP = _top_level_app_permission(
    "apps_senat_votes_app",
    "[Sénat-Digit] Onglet Votes",
    main_only=True,
)

_MORE_APP = _top_level_app_permission(
    "apps_senat_more_app",
    "[Sénat-Digit] Onglet Plus",
    main_only=False,  # Plus surfaces profile + logout — every role needs it
)


# ── Aggregate ────────────────────────────────────────────────────────
SENAT_DIGIT_MOBILE_HOME_PERMISSION_RBAC_DB = [
    _ACCUEIL_APP,
    _SESSION_APP,
    _DOCUMENTS_APP,
    _VOTES_APP,
    _MORE_APP,
    *_SEN,
    *_GRF,
    *_ADM,
    *_SYS,
]


# ── Tree-shaped catalogue for `seed_rbac_from_module` ────────────────
# `RbacRoleService.seed_rbac_from_module` expects a list of nested
# `rbac_title` nodes ({label, flag, permissions, endpoints, children}).
# Wrap the flat permission list into a single node so the existing
# pipeline picks up `core_seeds.rbac_roles_list` and writes the
# `rbac_permission_role` rows that gate the Home tiles per role.
SENAT_DIGIT_MOBILE_HOME_RBAC_TREE = [
    {
        "label": "Sénat-Digit · Onglet Accueil",
        "flag": "senat_digit_mobile_home_tab_flag",
        "is_default": False,
        "permissions": SENAT_DIGIT_MOBILE_HOME_PERMISSION_RBAC_DB,
        "endpoints": [],
        "children": [],
    }
]
