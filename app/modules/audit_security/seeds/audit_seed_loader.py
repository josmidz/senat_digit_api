"""Audit JSON-seed bridge — same template as session_meeting/seeds/session_seed_loader.py."""

from __future__ import annotations

import json
import os
from typing import Any


_BASE_DIR = os.path.dirname(__file__)


def _read_json(filename: str) -> dict[str, Any]:
    with open(os.path.join(_BASE_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)


def load_audit_security_permission_titles() -> list[dict[str, Any]]:
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


def load_audit_security_apps() -> list[dict[str, Any]]:
    raw = _read_json("app_seed.json")
    return raw.get("apps", [])
