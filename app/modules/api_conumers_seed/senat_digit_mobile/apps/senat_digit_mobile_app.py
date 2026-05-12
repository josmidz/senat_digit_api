"""Bottom-nav apps for Senat-Digit Mobile (Flutter).

Five top-level entries mirror the GoRouter ShellRoute in
`senat_digit_app/lib/core/router/app_router.dart` (`_ShellScaffold._routes`):
Accueil / Séance / Documents / Votes / Plus.

Visibility (per top-level tab):
  - **Accueil** + **Plus** are open to MAIN_PROFILE + SYSTEM_PROFIL. Inside
    Accueil, sub-menus split SYSTEM-only tiles from MAIN-only tiles.
  - **Séance**, **Documents**, **Votes** stay MAIN_PROFILE-only — they're
    parliamentary-business tabs the system_profil cross-tenant admin
    doesn't operate.
  - consumer  : SENAT_DIGIT_MOBILE only (the Flutter app's consumer key).
  - app group : COMMON — Senat-Digit isn't sliced into transport sub-apps
                like Lokotroo, so every entry rides the COMMON bucket.

`Accueil` populates its `sub_menus` via
`apps/home/senat_digit_mobile_home_sub_menus.py`. The Flutter Home tab
reads that sub-tree from `/static/data/get-applications` and renders a
role-filtered grid (`apps_senat_home_sen_*` for sénateur,
`apps_senat_home_grf_*` for greffier, `apps_senat_home_adm_*` for the
in-org admin, `apps_senat_home_sys_*` for cross-tenant system admin).
"""

from app.modules.core.constants.common import (
    FLUTTER_AGENT_APP_API_CONSUMER_IN_ONE,
    MAIN_PROFILE_IN_ONE,
    SYSTEM_ORGANIZATION_PROFIL_IN_ONE,
)
from app.modules.core.enums.type_enum import EAppGroupFlag

from app.modules.api_conumers_seed.senat_digit_mobile.apps.home.senat_digit_mobile_home_sub_menus import (
    get_senat_digit_mobile_home_sub_menus,
)


# ── visibility presets ────────────────────────────────────────────────
# Spread into each app dict via `**`. Keep in sync with `senat_digit_admin_web`
# (Angular) which mirrors this for SYSTEM_PROFIL-restricted screens.

_SENAT_MOBILE_MAIN_PROFILE = {
    "restricted_profil_list": [*MAIN_PROFILE_IN_ONE],
    "restricted_api_consumer_list": [*FLUTTER_AGENT_APP_API_CONSUMER_IN_ONE],
    "application_group_flag": EAppGroupFlag.COMMON.value,
    "is_standalone": False,
}

# Accueil + Plus must be reachable by the system_profil super-admin too —
# the cross-tenant admin uses the Home tab to provision the main_profile
# org and manage users (see Home sub-menu seed for `_SYSTEM_ONLY` tiles).
# Dedup-safe: same profile flag listed in both presets is idempotent on
# `create_restricted_profil`.
_SENAT_MOBILE_MAIN_AND_SYSTEM = {
    "restricted_profil_list": [
        *MAIN_PROFILE_IN_ONE,
        *SYSTEM_ORGANIZATION_PROFIL_IN_ONE,
    ],
    "restricted_api_consumer_list": [*FLUTTER_AGENT_APP_API_CONSUMER_IN_ONE],
    "application_group_flag": EAppGroupFlag.COMMON.value,
    "is_standalone": False,
}


# ── icons ─────────────────────────────────────────────────────────────
# Material-style outlined glyphs. Inlined as SVG strings so the seed is
# self-contained (no FS dep). The Flutter side uses Material icons
# directly via `RbacScreenRegistry`; these are only consumed by the
# admin web's app-grid rendering. Keep them lightweight.

_SVG_HOME = (
    '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M3 11.5L12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1v-8.5z" '
    'stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>'
)
_SVG_SESSION = (
    '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<rect x="3.5" y="5" width="17" height="15" rx="2" stroke="currentColor" stroke-width="1.6"/>'
    '<path d="M8 3v4M16 3v4M3.5 10h17" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>'
    '</svg>'
)
_SVG_DOCUMENTS = (
    '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M7 3h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" '
    'stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>'
    '<path d="M14 3v5h5M9 13h6M9 17h6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>'
    '</svg>'
)
_SVG_VOTES = (
    '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M5 12l4 4L19 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    '<rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" stroke-width="1.6"/>'
    '</svg>'
)
_SVG_MORE = (
    '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<circle cx="6" cy="12" r="1.6" fill="currentColor"/>'
    '<circle cx="12" cy="12" r="1.6" fill="currentColor"/>'
    '<circle cx="18" cy="12" r="1.6" fill="currentColor"/>'
    '</svg>'
)


def get_senat_digit_mobile_seed_app():
    """Return the bottom-nav application tree for the Flutter sénateur app.

    Routes (`path` / `flag` / `path_guard`) match the Flutter `RbacScreenRegistry`
    — flag is the canonical key, the registry resolves it to a screen. The
    `path` field is informational on mobile; on admin web the same flag
    convention applies to Angular routes.
    """
    return [
        {
            "path": "/senat/home",
            "path_guard": "apps_senat_home_app",
            "svg_icon": _SVG_HOME,
            "name": "Accueil",
            "order_by": 0,
            "flag": "apps_senat_home_app",
            "description_str": "Accueil — séance en cours, ordre du jour",
            **_SENAT_MOBILE_MAIN_AND_SYSTEM,
            "sub_menus": get_senat_digit_mobile_home_sub_menus(),
        },
        {
            "path": "/senat/session",
            "path_guard": "apps_senat_session_app",
            "svg_icon": _SVG_SESSION,
            "name": "Séance",
            "order_by": 1,
            "flag": "apps_senat_session_app",
            "description_str": "Présence, agenda et historique de séance",
            **_SENAT_MOBILE_MAIN_PROFILE,
            "sub_menus": [],
        },
        {
            "path": "/senat/documents",
            "path_guard": "apps_senat_documents_app",
            "svg_icon": _SVG_DOCUMENTS,
            "name": "Documents",
            "order_by": 2,
            "flag": "apps_senat_documents_app",
            "description_str": "Documents parlementaires, lecture et annotations",
            **_SENAT_MOBILE_MAIN_PROFILE,
            "sub_menus": [],
        },
        {
            "path": "/senat/votes",
            "path_guard": "apps_senat_votes_app",
            "svg_icon": _SVG_VOTES,
            "name": "Votes",
            "order_by": 3,
            "flag": "apps_senat_votes_app",
            "description_str": "Votes en direct et résultats",
            **_SENAT_MOBILE_MAIN_PROFILE,
            "sub_menus": [],
        },
        {
            "path": "/senat/more",
            "path_guard": "apps_senat_more_app",
            "svg_icon": _SVG_MORE,
            "name": "Plus",
            "order_by": 4,
            "flag": "apps_senat_more_app",
            "description_str": "Parole, notifications, profil",
            **_SENAT_MOBILE_MAIN_AND_SYSTEM,
            "sub_menus": [],
        },
    ]
