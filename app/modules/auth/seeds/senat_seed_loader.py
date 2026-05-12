"""Bridge from CLAUDE.md JSON seed files to the existing Python seed pipeline.

CLAUDE.md mandates that every Senat-Digit feature module ship two JSON seed
files alongside its Python code:

    seeds/app_seed.json
    seeds/permission_titles_seed.json

The reference codebase historically stores these structures as Python lists
(`*_RBAC_TITLE_DB`, `STATIC_SYS_APPS_DB`). This loader reads the JSON and
produces the same shapes the existing seed runners (`RbacRoleService.seed_rbac_from_module`
+ `GenericService.on_single_application_save`) expect, so we get the
auditable JSON catalogue without reimplementing the seed pipeline.
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


def load_auth_device_permission_titles() -> list[dict[str, Any]]:
    """Return permission titles in the shape expected by `RbacRoleService.seed_rbac_from_module`.

    The shape mirrors `system_config_permission_title.SYSTEM_CONFIG_PERMISSION_RBAC_TITLE_DB`:
    each entry has `flag`, `label`, and a nested `core_seeds` block. Because
    CLAUDE.md keeps the JSON catalogue lean (key + title + endpoints), the
    `core_seeds` block here is intentionally minimal — feature-specific
    restrictions live in the per-consumer RBAC files
    (`api_conumers_seed/senat_digit_mobile/rbac/senat_digit_mobile_rbac.py`).
    """
    raw = _read_json("permission_titles_seed.json")
    out: list[dict[str, Any]] = []
    for entry in raw.get("permission_titles", []):
        if entry.get("_status") == "reserved_v1.1":
            # Reserved permissions get registered (so the RBAC matrix surface
            # exists) but with an empty `core_seeds` so they're not yet wired
            # to any role / app. They'll be filled in v1.1.
            core_seeds: dict[str, Any] = {}
        else:
            core_seeds = {
                "rbac_standalone_actions_obj": {
                    "action_to_menus": [],
                    "action_to_apps": [],
                },
                "rbac_custom_actions_obj": {
                    "action_to_menus": [],
                    "action_to_apps": [],
                },
                "rbac_collection_meta_data_obj": {
                    "collection_meta_data_to_menus": [
                        {
                            "hard_code_flag": entry["key"],
                            "rbac_endpoint": ep["path"],
                            "rbac_method": ep["method"],
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                        }
                        for ep in entry.get("endpoints", [])
                    ]
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


def load_auth_device_apps() -> list[dict[str, Any]]:
    """Return app/menu shell entries in the shape expected by
    `GenericService.on_single_application_save`.
    """
    raw = _read_json("app_seed.json")
    return raw.get("apps", [])


# Convenience aggregator used by core/seeds/seed.py.
AUTH_DEVICE_PERMISSION_TITLES = load_auth_device_permission_titles
AUTH_DEVICE_APPS = load_auth_device_apps
