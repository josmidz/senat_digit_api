"""Senat-Digit module RBAC aggregator.

Each Senat-Digit feature module (`auth`, `session_meeting`, `presence`,
`agenda`, `document`, `vote`, `parole`, `notification`, `audit_security`)
ships a `seeds/permission_titles_seed.json` and a corresponding
`*_seed_loader.py` that returns a *flat* list of permission entries:

    [{flag, label, label_en, bucket, core_seeds}, ...]

The legacy seed pipeline (`RbacRoleService.seed_rbac_from_module` +
`create_rbac_titles` in `core/seeds/seed.py`) consumes a *nested*
`rbac_title` tree shape — one root per module, with `permissions`,
`endpoints`, and `children` arrays.

This module bridges the two by wrapping each loader's flat permission
list into the legacy nested shape:

    {
      "label": "Vote (Sénat-Digit)",
      "flag":  "senat_vote_flag",
      "is_default": False,
      "permissions": [...flat list from loader...],
      "endpoints": [...hoisted from each permission's core_seeds...],
      "children": [],
    }

Endpoints are hoisted from `core_seeds.rbac_collection_meta_data_obj.
collection_meta_data_to_menus` and de-duplicated by `(url, method)` so
multiple permissions sharing a URL don't double-register.

Per `_planning/_followup_batch.md` F2: the loaders existed since §3.5
but were never wired into `init_data()`. This file closes that gap.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from app.modules.admin_user.seeds.admin_user_seed_loader import (
    load_admin_user_permission_titles,
)
from app.modules.core.seeds.core_static.core_static_seed_loader import (
    load_core_static_permission_titles,
)
from app.modules.agenda.seeds.agenda_seed_loader import (
    load_agenda_permission_titles,
)
from app.modules.audit_security.seeds.audit_seed_loader import (
    load_audit_security_permission_titles,
)
from app.modules.auth.seeds.senat_seed_loader import (
    load_auth_device_permission_titles,
)
from app.modules.document.seeds.document_seed_loader import (
    load_document_permission_titles,
)
from app.modules.notification.seeds.notification_seed_loader import (
    load_notification_permission_titles,
)
from app.modules.parole.seeds.parole_seed_loader import (
    load_parole_permission_titles,
)
from app.modules.presence.seeds.presence_seed_loader import (
    load_presence_permission_titles,
)
from app.modules.session_meeting.seeds.session_seed_loader import (
    load_session_meeting_permission_titles,
)
from app.modules.vote.seeds.vote_seed_loader import (
    load_vote_permission_titles,
)


def _hoist_endpoints(permissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collect every (url, method) pair exposed by a module's permissions
    into a top-level rbac_endpoint shape, de-duplicated.

    Each permission's `core_seeds.rbac_collection_meta_data_obj.
    collection_meta_data_to_menus` is the source of truth for which URLs
    that permission gates."""
    out: List[Dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for perm in permissions:
        seeds = perm.get("core_seeds") or {}
        cmd_obj = seeds.get("rbac_collection_meta_data_obj") or {}
        rows = cmd_obj.get("collection_meta_data_to_menus") or []
        for r in rows:
            url = (r.get("rbac_endpoint") or "").strip()
            method = (r.get("rbac_method") or "GET").strip().upper()
            if not url:
                continue
            key = (url, method)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "label": perm.get("label", url),
                    "is_leaf": True,
                    "is_link_deleted": False,
                    "url": url,
                    "method": method,
                }
            )
    return out


def _normalize_core_seeds(permission: Dict[str, Any]) -> Dict[str, Any]:
    """Strip every block step-2 (`recursive_rbac_title`) would touch.

    All three `core_seeds` blocks the senat-digit loaders emit have a
    *flat list* shape — (hard_code_flag, rbac_endpoint, rbac_method)
    triples. The legacy step-2 seeder expects a CRUD-keyed *dict* for
    `collection_meta_data_to_menus` and `action_*` keys for the standalone/
    custom blocks. Passing the flat lists crashes step 2 with
    `AttributeError: 'list' object has no attribute 'items'`.

    Step 1 (`recursive_save_rbac_structure`) registers every URL via the
    module-level `endpoints` array we hoist in `_hoist_endpoints`.
    The `rbac_permission_target` rows that link each permission to its
    endpoint(s) are written directly by `RbacRoleService.
    link_permissions_to_endpoints` — the (perm_flag, url) pairs come
    straight from the unmodified loader output (we read it before this
    normalize step strips it for step 2).
    """
    seeds = permission.get("core_seeds")
    if not isinstance(seeds, dict):
        return permission
    safe_seeds = {
        "rbac_standalone_actions_obj": {
            "action_to_menus": [],
            "action_to_apps": [],
        },
        "rbac_custom_actions_obj": {
            "action_to_menus": [],
            "action_to_apps": [],
        },
        # rbac_collection_meta_data_obj omitted: step 2 only iterates
        # this block when present, so leaving it out skips the loop.
    }
    return {**permission, "core_seeds": safe_seeds}


def _wrap_module(
    label: str,
    flag: str,
    loader: Callable[[], List[Dict[str, Any]]],
) -> Dict[str, Any]:
    permissions = [_normalize_core_seeds(p) for p in loader()]
    return {
        "label": label,
        "flag": flag,
        "is_default": False,
        "permissions": permissions,
        "endpoints": _hoist_endpoints(loader()),
        "children": [],
    }


def build_senat_digit_modules_rbac_title_db() -> List[Dict[str, Any]]:
    """Materialise the nested rbac_title tree on demand.

    Called at seed time only. Returns a fresh list each time so callers
    cannot accidentally mutate cached state across seed runs.
    """
    return [
        _wrap_module(
            "Authentification (Sénat-Digit)",
            "senat_auth_device_flag",
            load_auth_device_permission_titles,
        ),
        _wrap_module(
            "Séance plénière",
            "senat_session_meeting_flag",
            load_session_meeting_permission_titles,
        ),
        _wrap_module(
            "Présence",
            "senat_presence_flag",
            load_presence_permission_titles,
        ),
        _wrap_module(
            "Ordre du jour",
            "senat_agenda_flag",
            load_agenda_permission_titles,
        ),
        _wrap_module(
            "Documents parlementaires",
            "senat_document_flag",
            load_document_permission_titles,
        ),
        _wrap_module(
            "Vote (scrutin)",
            "senat_vote_flag",
            load_vote_permission_titles,
        ),
        _wrap_module(
            "Demande de parole",
            "senat_parole_flag",
            load_parole_permission_titles,
        ),
        _wrap_module(
            "Notifications",
            "senat_notification_flag",
            load_notification_permission_titles,
        ),
        _wrap_module(
            "Audit & sécurité",
            "senat_audit_security_flag",
            load_audit_security_permission_titles,
        ),
        # SYSTEM_PROFIL tenant-management surface — cross-org create/list/lock
        # operations + the password-reset-link issuer. Granted exclusively to
        # SYSTEM_PROFIL_SUPER_ADMIN downstream (see `seed_role_permissions_*`).
        _wrap_module(
            "Administration système",
            "senat_admin_user_flag",
            load_admin_user_permission_titles,
        ),
        # Shared static reads (bottom-nav, menus, own user-config, own
        # notification inbox, signed-URL files). Granted to EVERY role
        # downstream — without these, the Flutter shell silently 403s
        # on app launch because /static/data/get-applications is the
        # very first call the consumer makes after login.
        _wrap_module(
            "Lectures statiques partagées",
            "senat_core_static_flag",
            load_core_static_permission_titles,
        ),
    ]
