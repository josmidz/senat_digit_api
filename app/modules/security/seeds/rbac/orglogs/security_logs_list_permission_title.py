

from app.modules.auth.enums.common import ERbacActionFlag, ERbacActionHardCodeFlag
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.common import ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE, ALL_ORGANIZATION_PROFIL_IN_ONE, SENAT_DIGIT_ADMIN_WEB_IN_ONE


# ─── Shared helpers ───────────────────────────────────────────────────────────

_COMMON_APPS = [
    {
        "flag": "security_app_page",
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    }
]

_COMMON_MENUS = [
    {
        "flag": "security_logs_app_page",
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": "security_logs_list_page",
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]


SECURITY_LOGS_LIST_PERMISSION_RBAC_TITLE_DB = [
    # ── 1. Fetch paginated logs ──────────────────────────────────────────────
    {
        'flag': "security_logs_loading_list_permission_flag",
        "label": "Chargement de la liste des logs",
        "description_str": "cette permission permet de consulter la liste des logs CRUD de l'organisation",
        'is_default': False,
        "is_link_deleted": False,
        "core_seeds": {
            "restricted_profil_list": [*ALL_ORGANIZATION_PROFIL_IN_ONE],
            "restricted_api_consumer_list": [*SENAT_DIGIT_ADMIN_WEB_IN_ONE],
            "rbac_roles_list": [*ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE],
            "sys_apps_list": [*_COMMON_APPS],
            "sys_menus_list": [*_COMMON_MENUS],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [],
                "action_to_apps": []
            },
            "rbac_custom_actions_obj": {
                "action_to_menus": [],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_apps": {
                    "update_processing_url": [],
                    "update_head_process_url": [],
                },
                "collection_meta_data_to_menus": {
                    "fetch_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/securities/logs/fetch/logs",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_logs_list_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }
                    ],
                    "update_processing_url": [],
                    "update_head_process_url": [],
                }
            }
        }
    },

    # ── 2. SSE real-time stream ──────────────────────────────────────────────
    {
        'flag': "security_logs_stream_permission_flag",
        "label": "Flux temps r\u00e9el des logs",
        "description_str": "cette permission permet d'acc\u00e9der au flux en temps r\u00e9el des logs CRUD de l'organisation",
        'is_default': False,
        "is_link_deleted": False,
        "core_seeds": {
            "restricted_profil_list": [*ALL_ORGANIZATION_PROFIL_IN_ONE],
            "restricted_api_consumer_list": [*SENAT_DIGIT_ADMIN_WEB_IN_ONE],
            "rbac_roles_list": [*ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE],
            "sys_apps_list": [*_COMMON_APPS],
            "sys_menus_list": [*_COMMON_MENUS],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "security_logs_list_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_VIEW.value,
                        "action_hard_code_flag": ERbacActionHardCodeFlag.VIEW_ACTION.value,
                        "action_is_standalone": True,
                        "action_label": "Flux temps r\u00e9el"
                    }
                ],
                "action_to_apps": []
            },
            "rbac_custom_actions_obj": {
                "action_to_menus": [],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_apps": {
                    "update_processing_url": [],
                    "update_head_process_url": [],
                },
                "collection_meta_data_to_menus": {
                    "fetch_url": [
                        {
                            "hard_code_flag": "stream_url",
                            "rbac_endpoint": "/api/v1/securities/logs/fetch/streams",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_logs_list_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }
                    ],
                    "update_processing_url": [],
                    "update_head_process_url": [],
                }
            }
        }
    },
]
