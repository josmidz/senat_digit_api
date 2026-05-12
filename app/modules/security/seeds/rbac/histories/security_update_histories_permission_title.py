

from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.core.constants.common import ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE, ALL_ORGANIZATION_PROFIL_IN_ONE, SENAT_DIGIT_ADMIN_WEB_IN_ONE
from app.modules.auth.enums.common import ERbacActionFlag, ERbacActionHardCodeFlag
from app.modules.core.models.mapping_keys import CollectionKey


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
        "flag": "security_histories_app_page",
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": "security_histories_updates_menu_page",
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]


SECURITY_UPDATE_HISTORIES_PERMISSION_RBAC_TITLE_DB = [
    # ── 1. Load / fetch update histories ──────────────────────────────────
    {
        'flag': "security_histories_loading_of_updates_histories_permission_flag",
        "label": "Chargement des logs - Modifications",
        "description_str": "cette permission permet à la personne qui l'a de pouvoir accéder aux logs - Modifications",
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
                            "rbac_endpoint": "/api/v1/securities/histories/fetch/updates",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_histories_updates_menu_page",
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

    # ── 2. Search update histories by identifier ──────────────────────────
    {
        'flag': "security_histories_search_updates_histories_permission_flag",
        "label": "Recherche des logs - Modifications",
        "description_str": "cette permission permet de rechercher dans les logs de modifications par identifiant",
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
                        "menu_flag": "security_histories_updates_menu_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_VIEW.value,
                        "action_hard_code_flag": ERbacActionHardCodeFlag.VIEW_ACTION.value,
                        "action_is_standalone": True,
                        "action_label": "Rechercher"
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
                            "hard_code_flag": "search_updates_url",
                            "rbac_endpoint": "/api/v1/securities/histories/search",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_histories_updates_menu_page",
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

    # ── 3. Fetch update histories by specific identifier ──────────────────
    {
        'flag': "security_histories_by_identifier_updates_histories_permission_flag",
        "label": "Consultation par identifiant - Logs Modifications",
        "description_str": "cette permission permet de consulter les logs de modifications d'un document spécifique",
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
                        "menu_flag": "security_histories_updates_menu_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_VIEW.value,
                        "action_hard_code_flag": ERbacActionHardCodeFlag.VIEW_ACTION.value,
                        "action_is_standalone": True,
                        "action_label": "Consulter par identifiant"
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
                            "hard_code_flag": "by_identifier_updates_url",
                            "rbac_endpoint": "/api/v1/securities/histories/by-identifier",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_histories_updates_menu_page",
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

    # ── 4. Restore (revert) from update history ──────────────────────────
    {
        'flag': "security_histories_restore_update_history_permission_flag",
        "label": "Restauration depuis les logs - Modifications",
        "description_str": "cette permission permet de restaurer un document à son état précédent depuis les logs de modifications",
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
                        "menu_flag": "security_histories_updates_menu_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                        "action_hard_code_flag": ERbacActionHardCodeFlag.UPDATE_ACTION.value,
                        "action_is_standalone": True,
                        "action_label": "Restaurer"
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
                    "fetch_url": [],
                    "update_processing_url": [
                        {
                            "hard_code_flag": "restore_update_url",
                            "rbac_endpoint": "/api/v1/securities/histories/restore/update",
                            "is_sudo_action": True,
                            "is_sudo_group_action": True,
                            "menu_flag": "security_histories_updates_menu_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }
                    ],
                    "update_head_process_url": [],
                }
            }
        }
    },
]
