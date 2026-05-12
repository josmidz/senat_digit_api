"""Admin_user JSON-seed bridge.

Mirrors the per-module pattern used by every senat-digit feature module
(see `app/modules/session_meeting/seeds/session_seed_loader.py`).

Reads `permission_titles_seed.json` and wraps each entry into the
core_seeds shape `RbacRoleService.seed_rbac_from_module()` understands.
"""

from __future__ import annotations

import json
import os
from typing import Any


_BASE_DIR = os.path.dirname(__file__)


def _read_json(filename: str) -> dict[str, Any]:
    path = os.path.join(_BASE_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_admin_user_permission_titles() -> list[dict[str, Any]]:
    """Return per-permission RBAC title dicts for the admin_user module."""
    raw = _read_json("permission_titles_seed.json")
    out: list[dict[str, Any]] = []
    for entry in raw.get("permission_titles", []):
        is_custom = entry.get("bucket") == "custom" or entry.get("hard_code_flag") is True
        meta_rows = [
            {
                "hard_code_flag": entry["key"],
                "rbac_endpoint": ep["path"],
                "rbac_method": ep["method"],
                "is_sudo_action": False,
                "is_sudo_group_action": False,
            }
            for ep in entry.get("endpoints", [])
        ]
        core_seeds: dict[str, Any] = {
            "rbac_standalone_actions_obj": {
                "action_to_menus": [] if is_custom else meta_rows,
                "action_to_apps": [],
            },
            "rbac_custom_actions_obj": {
                "action_to_menus": meta_rows if is_custom else [],
                "action_to_apps": [],
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": meta_rows,
            },
        }
        out.append({
            "flag": entry["key"],
            "label": entry["title_fr"],
            "label_en": entry.get("title_en"),
            "bucket": entry.get("bucket", "standalone"),
            "core_seeds": core_seeds,
        })
    return out
