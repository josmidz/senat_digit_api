"""Shared role-grant lists for senat_digit_mobile RBAC seeds.

Mirrors `lokotroo_flutter_rbac_roles.py` — declares one canonical role
list per persona so per-tile rbac files don't redeclare the same
combos. Each list is consumed via `**rbac_roles_list=[...]` in a
permission's `core_seeds` block.

Why this matters: the `/static/data/get-application-user-submenus`
controller filters menus through the full RBAC chain
(`rbac_role → rbac_permission → rbac_permission_target → sys_menu`).
A menu that doesn't have at least one permission targeting it AND
granted to the caller's role gets dropped from the response — even if
the menu's `restricted_profil_list` matches.

So every tile in the Home grid needs both:
  1. a `restricted_profil_list` on its sys_menu row (handled by the
     apps seed — see `apps/home/senat_digit_mobile_home_sub_menus.py`)
  2. an rbac_permission with `rbac_roles_list=[...]` targeting it
     (handled by `home/senat_digit_mobile_home_all_rbac.py`)

Test profile is included in every list so the dev-only
`test_profil_super_admin` sees everything.
"""

from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag
from app.modules.core.seeds.rbac_seed_service import role_link


# ── Sénateur (the participant) ───────────────────────────────────────
# Voting member. Sees: signer présence, demander la parole, vote en
# cours, mes votes, donner pouvoir.
# Main_profile_super_admin gets god-mode access too — they're the
# break-glass operator who must be able to do anything in the chamber.
SENATEUR_TILE_ROLES = [
    role_link(ESysProfilSuperUserRoleFlag.SENATEUR.value),
    role_link(ESysProfilSuperUserRoleFlag.MAIN_PROFILE_SUPER_ADMIN.value),
    role_link(ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN.value),
]


# ── Greffier (the orchestrator) ──────────────────────────────────────
# Runs the chamber. Sees: open/close session, configure scrutin,
# parole queue, live presence count, agenda, manual tally.
# Main_profile_super_admin keeps god-mode access here too.
GREFFIER_TILE_ROLES = [
    role_link(ESysProfilSuperUserRoleFlag.GREFFIER.value),
    role_link(ESysProfilSuperUserRoleFlag.MAIN_PROFILE_SUPER_ADMIN.value),
    role_link(ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN.value),
]


# ── Main_profile super-admin (Sénat IT/owner) ────────────────────────
# Sénat tenant owner. In-org user + device + audit + stats. Greffier
# does NOT get this — admin tiles are deliberately out of their scope.
MAINADMIN_TILE_ROLES = [
    role_link(ESysProfilSuperUserRoleFlag.MAIN_PROFILE_SUPER_ADMIN.value),
    role_link(ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN.value),
]


# ── System_profil super-admin (cross-tenant) ─────────────────────────
# Cross-tenant ops. Sees: create main_profile org, manage users,
# login history, all devices. NOT visible to anyone else.
SYSADMIN_TILE_ROLES = [
    role_link(ESysProfilSuperUserRoleFlag.SYSTEM_PROFIL_SUPER_ADMIN.value),
    role_link(ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN.value),
]
