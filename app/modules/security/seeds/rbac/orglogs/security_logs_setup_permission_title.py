

from app.modules.auth.enums.common import ERbacActionFlag
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
        "flag": "security_logs_setup_page",
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]


SECURITY_LOGS_SETUP_PERMISSION_RBAC_TITLE_DB = [
    # ── 1. Fetch log setup ───────────────────────────────────────────────────
    {
        'flag': "security_logs_loading_setup_permission_flag",
        "label": "Chargement de la configuration des logs",
        "description_str": "cette permission permet de consulter la configuration des logs de l'organisation",
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
                            "rbac_endpoint": "/api/v1/securities/logs/fetch/setups",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_logs_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "update_processing_url": [],
                    "update_head_process_url": [],
                }
            }
        }
    },

    # ── 2. Toggle log enabled ────────────────────────────────────────────────
    {
        'flag': "security_logs_toggle_enabled_permission_flag",
        "label": "Activation/D\u00e9sactivation des logs",
        "description_str": "cette permission permet d'activer ou de d\u00e9sactiver le syst\u00e8me de logs CRUD de l'organisation",
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
                "action_to_menus": [
                    {
                        "menu_flag": "security_logs_setup_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                        "action_is_standalone": True,
                        "action_hard_code_flag": "logs_toggle_enabled_action_flag",
                        "action_label": "Activer/D\u00e9sactiver"
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_apps": {
                    "update_processing_url": [],
                    "update_head_process_url": [],
                },
                "collection_meta_data_to_menus": {
                    "patch_processing_url": [ 
                        {
                            "hard_code_flag": "patch_enabled_url",
                            "rbac_endpoint": "/api/v1/securities/logs/patch/setup-enabled",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_logs_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "patch_enabled_url",
                            "rbac_endpoint": "/api/v1/securities/logs/setup/patch/enabled",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_logs_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": True,
                        },
                    ],
                }
            }
        }
    },

    # ── 3. Toggle CRUD log flags ──────────────────────────────────────────────
    {
        'flag': "security_logs_toggle_crud_flags_permission_flag",
        "label": "Activation/D\u00e9sactivation des logs CRUD individuels",
        "description_str": "cette permission permet d'activer ou de d\u00e9sactiver les logs par type d'op\u00e9ration CRUD (cr\u00e9ation, lecture, modification, suppression)",
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
                "action_to_menus": [
                    {
                        "menu_flag": "security_logs_setup_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                        "action_is_standalone": True,
                        "action_hard_code_flag": "logs_toggle_crud_flags_action_flag",
                        "action_label": "Activer/D\u00e9sactiver les logs CRUD"
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_apps": {
                    "update_processing_url": [],
                    "update_head_process_url": [],
                },
                "collection_meta_data_to_menus": {
                    "patch_processing_url": [
                        {
                            "hard_code_flag": "patch_crud_flags_url",
                            "rbac_endpoint": "/api/v1/securities/logs/patch/setup-crud-flags",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_logs_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                }
            }
        }
    },

    # ── 4. Update expiration days ────────────────────────────────────────────
    {
        'flag': "security_logs_update_expiration_permission_flag",
        "label": "Mise \u00e0 jour de la dur\u00e9e de r\u00e9tention des logs",
        "description_str": "cette permission permet de modifier la dur\u00e9e de r\u00e9tention des logs CRUD de l'organisation",
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
                "action_to_menus": [
                    {
                        "menu_flag": "security_logs_setup_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                        "action_is_standalone": True,
                        "action_hard_code_flag": "logs_update_expiration_action_flag",
                        "action_label": "Modifier la dur\u00e9e de r\u00e9tention"
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_apps": {
                    "update_processing_url": [],
                    "update_head_process_url": [],
                },
                "collection_meta_data_to_menus": {
                    "patch_processing_url": [ 
                        {
                            "hard_code_flag": "patch_expiration_url",
                            "rbac_endpoint": "/api/v1/securities/logs/patch/setup-expiration",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_logs_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "patch_expiration_url",
                            "rbac_endpoint": "/api/v1/securities/logs/setup/patch/expiration",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_logs_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": True,
                        },
                    ],
                }
            }
        }
    },
]
