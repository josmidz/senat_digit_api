"""Home tab sub-menus for Senat-Digit Mobile (Flutter).

Mirrors the lokotroo_flutter_app pattern (`apps/home/lokotroo_app_home_sub_menus.py`)
— each tile is a `SYS_MENU` row with a `path_guard` flag, gated at the
profile level via `restricted_profil_list`.

──────────────────────────────────────────────────────────────────────
Role gating reality
──────────────────────────────────────────────────────────────────────
The app/menu seed defines the raw catalogue and profile/API-consumer
scope. The role-level split is applied by the RBAC permission seed in
`rbac/home/senat_digit_mobile_home_all_rbac.py`, where each tile flag is
granted to the matching `SENATEUR_TILE_ROLES`, `GREFFIER_TILE_ROLES`,
`MAINADMIN_TILE_ROLES`, or `SYSADMIN_TILE_ROLES` list.

Profile scope still matters before role grants are evaluated:

  - `_SYSTEM_ONLY`     → only SYSTEM_PROFIL super-admin catalogue rows.
  - `_MAIN_ONLY`       → MAIN_PROFILE catalogue rows.

Naming convention for `path_guard` flags so the client can split
unambiguously after the backend returns the role-filtered tree:

  - `apps_senat_home_sen_*`  → sénateur tiles
  - `apps_senat_home_grf_*`  → greffier tiles
  - `apps_senat_home_adm_*`  → main_profile_super_admin tiles
  - `apps_senat_home_sys_*`  → system_profil_super_admin tiles

`order_by` orders tiles within the Home grid (sénateur tiles first,
greffier second, admin last — matches the typical user mix).
"""

from app.modules.core.constants.common import (
    FLUTTER_AGENT_APP_API_CONSUMER_IN_ONE,
    MAIN_PROFILE_IN_ONE,
    SYSTEM_ORGANIZATION_PROFIL_IN_ONE,
)
from app.modules.core.enums.type_enum import EAppGroupFlag


# ── Visibility presets ────────────────────────────────────────────────
# Spread into each menu dict via `**`.

_MAIN_ONLY = {
    "restricted_profil_list": [*MAIN_PROFILE_IN_ONE],
    "restricted_api_consumer_list": [*FLUTTER_AGENT_APP_API_CONSUMER_IN_ONE],
    "application_group_flag": EAppGroupFlag.COMMON.value,
    "is_standalone": False,
}

_SYSTEM_ONLY = {
    "restricted_profil_list": [*SYSTEM_ORGANIZATION_PROFIL_IN_ONE],
    "restricted_api_consumer_list": [*FLUTTER_AGENT_APP_API_CONSUMER_IN_ONE],
    "application_group_flag": EAppGroupFlag.COMMON.value,
    "is_standalone": False,
}


def get_senat_digit_mobile_home_sub_menus() -> list[dict]:
    """Return the Home tab sub-menu tree for the Flutter mobile consumer.

    Order is rendering order in the Home grid. Sénateur tiles come first
    (the most common user), then greffier, then admins. The system_profil
    tiles render at the bottom — they're rare and admin-only.
    """
    return [
        # ══════════════════════════════════════════════════════════════
        # Sénateur tiles (the participant)
        # ══════════════════════════════════════════════════════════════
        {
            "path": "/home/sen/sign-presence",
            "path_guard": "apps_senat_home_sen_sign_presence_page",
            "name": "Signer présence",
            "order_by": 0,
            "flag": "apps_senat_home_sen_sign_presence_page",
            "description_str": "Marquer sa présence à la séance en cours",
            **_MAIN_ONLY,
            "sub_menus": [],
        },
        {
            "path": "/home/sen/request-parole",
            "path_guard": "apps_senat_home_sen_request_parole_page",
            "name": "Demander la parole",
            "order_by": 1,
            "flag": "apps_senat_home_sen_request_parole_page",
            "description_str": "Lever la main pour intervenir en séance",
            **_MAIN_ONLY,
            "sub_menus": [],
        },
        {
            "path": "/home/sen/active-vote",
            "path_guard": "apps_senat_home_sen_active_vote_page",
            "name": "Vote en cours",
            "order_by": 2,
            "flag": "apps_senat_home_sen_active_vote_page",
            "description_str": "Voter sur le scrutin ouvert",
            **_MAIN_ONLY,
            "sub_menus": [],
        },
        {
            "path": "/home/sen/my-votes",
            "path_guard": "apps_senat_home_sen_my_votes_page",
            "name": "Mes votes",
            "order_by": 3,
            "flag": "apps_senat_home_sen_my_votes_page",
            "description_str": "Historique de mes votes",
            **_MAIN_ONLY,
            "sub_menus": [],
        },
        {
            "path": "/home/sen/give-proxy",
            "path_guard": "apps_senat_home_sen_give_proxy_page",
            "name": "Donner pouvoir",
            "order_by": 4,
            "flag": "apps_senat_home_sen_give_proxy_page",
            "description_str": "Confier sa procuration à un autre sénateur",
            **_MAIN_ONLY,
            "sub_menus": [],
        },

        # ══════════════════════════════════════════════════════════════
        # Greffier tiles (the orchestrator)
        # ══════════════════════════════════════════════════════════════
        {
            "path": "/home/grf/session-control",
            "path_guard": "apps_senat_home_grf_session_control_page",
            "name": "Ouvrir / clôturer la séance",
            "order_by": 10,
            "flag": "apps_senat_home_grf_session_control_page",
            "description_str": "Démarrer, suspendre, reprendre ou clôturer la séance",
            **_MAIN_ONLY,
            "sub_menus": [],
        },
        {
            "path": "/home/grf/configure-vote",
            "path_guard": "apps_senat_home_grf_configure_vote_page",
            "name": "Configurer un scrutin",
            "order_by": 11,
            "flag": "apps_senat_home_grf_configure_vote_page",
            "description_str": "Paramétrer un nouveau scrutin avant ouverture",
            **_MAIN_ONLY,
            "sub_menus": [],
        },
        {
            "path": "/home/grf/parole-queue",
            "path_guard": "apps_senat_home_grf_parole_queue_page",
            "name": "File de parole",
            "order_by": 12,
            "flag": "apps_senat_home_grf_parole_queue_page",
            "description_str": "Gérer la file des demandes de parole",
            **_MAIN_ONLY,
            "sub_menus": [],
        },
        {
            "path": "/home/grf/presence-live",
            "path_guard": "apps_senat_home_grf_presence_live_page",
            "name": "Présences (en direct)",
            "order_by": 13,
            "flag": "apps_senat_home_grf_presence_live_page",
            "description_str": "Compteur de présences et liste en temps réel",
            **_MAIN_ONLY,
            "sub_menus": [],
        },
        {
            "path": "/home/grf/agenda-manage",
            "path_guard": "apps_senat_home_grf_agenda_manage_page",
            "name": "Ordre du jour",
            "order_by": 14,
            "flag": "apps_senat_home_grf_agenda_manage_page",
            "description_str": "Gérer l'ordre du jour de la séance",
            **_MAIN_ONLY,
            "sub_menus": [],
        },
        {
            "path": "/home/grf/manual-tally",
            "path_guard": "apps_senat_home_grf_manual_tally_page",
            "name": "Comptage manuel",
            "order_by": 15,
            "flag": "apps_senat_home_grf_manual_tally_page",
            "description_str": "Saisir un comptage manuel pour un scrutin",
            **_MAIN_ONLY,
            "sub_menus": [],
        },

        # ══════════════════════════════════════════════════════════════
        # Main_profile super-admin tiles (Sénat IT/owner)
        # ══════════════════════════════════════════════════════════════
        {
            "path": "/home/adm/users",
            "path_guard": "apps_senat_home_adm_users_page",
            "name": "Utilisateurs",
            "order_by": 20,
            "flag": "apps_senat_home_adm_users_page",
            "description_str": "Gérer les comptes du Sénat",
            **_MAIN_ONLY,
            "sub_menus": [],
        },
        {
            "path": "/home/adm/devices",
            "path_guard": "apps_senat_home_adm_devices_page",
            "name": "Validation appareils",
            "order_by": 21,
            "flag": "apps_senat_home_adm_devices_page",
            "description_str": "Valider et révoquer les appareils des utilisateurs",
            **_MAIN_ONLY,
            "sub_menus": [],
        },
        {
            "path": "/home/adm/org-config",
            "path_guard": "apps_senat_home_adm_org_config_page",
            "name": "Configuration organisation",
            "order_by": 22,
            "flag": "apps_senat_home_adm_org_config_page",
            "description_str": "Paramètres de l'organisation Sénat",
            **_MAIN_ONLY,
            "sub_menus": [],
        },
        {
            "path": "/home/adm/audit",
            "path_guard": "apps_senat_home_adm_audit_page",
            "name": "Journal d'audit",
            "order_by": 23,
            "flag": "apps_senat_home_adm_audit_page",
            "description_str": "Consulter le journal d'audit",
            **_MAIN_ONLY,
            "sub_menus": [],
        },
        {
            "path": "/home/adm/stats",
            "path_guard": "apps_senat_home_adm_stats_page",
            "name": "Statistiques",
            "order_by": 24,
            "flag": "apps_senat_home_adm_stats_page",
            "description_str": "Tableau de bord d'activité",
            **_MAIN_ONLY,
            "sub_menus": [],
        },

        # ══════════════════════════════════════════════════════════════
        # System_profil tiles (cross-tenant ops)
        #
        # Tight scope per operator spec: the cross-tenant admin only
        # needs two tiles on Home — manage the main_profile org
        # (CRUD) and its users (lock/unlock + reset password). Login
        # history + all-devices were dropped (drill-down from user
        # detail is enough; cross-user device inventory wasn't part of
        # the agreed sysadmin scope).
        # ══════════════════════════════════════════════════════════════
        {
            "path": "/home/sys/org",
            "path_guard": "apps_senat_home_sys_org_page",
            "name": "Sénat (organisation)",
            "order_by": 30,
            "flag": "apps_senat_home_sys_org_page",
            "description_str": "Voir et gérer l'organisation main_profile",
            **_SYSTEM_ONLY,
            "sub_menus": [],
        },
        {
            "path": "/home/sys/users",
            "path_guard": "apps_senat_home_sys_users_page",
            "name": "Utilisateurs Sénat",
            "order_by": 31,
            "flag": "apps_senat_home_sys_users_page",
            "description_str": "Verrouiller / déverrouiller + lien de réinitialisation",
            **_SYSTEM_ONLY,
            "sub_menus": [],
        },
    ]
