


from app.modules.auth.enums.common import ERbacActionFlag
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.common import ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE, ALL_ORGANIZATION_PROFIL_IN_ONE, SENAT_DIGIT_ADMIN_WEB_IN_ONE

SECURITY_RLS_SETTING_PERMISSION_RBAC_TITLE_DB = [
    {
        'flag': "loading_security_app_rls_setting_flag",
        "label": "Chargement des Paramétrages de sécurité RLS",
        "core_seeds": {
            "restricted_profil_list": [
                *ALL_ORGANIZATION_PROFIL_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE
            ],
            "sys_apps_list": [
                {
                    "flag": "security_app_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [ 
                {
                    "flag": "security_settings_menu_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }, 
                {
                    "flag": "security_settings_rls_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }, 
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [ 
                ],
                "action_to_apps": []
            },
            "rbac_custom_actions_obj": {
                "action_to_menus": [],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "fetch_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/securities/settings/rls/fetch/rls-settings",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_settings_rls_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                          
                    ],
                    "fetch_one_info_url": [],
                    
                },
                "collection_meta_data_to_apps": {
                    "fetch_url": [],
                    "update_processing_url": [],
                    "update_head_process_url": [],
                    "parent_field_name": [],
                    "delete_processing_url": [],
                    "create_child_processing_url": [],
                    "create_child_head_process_url": [],
                    "fetch_one_info_url": [],
                    "fetch_one_info_for_viewing_url": [],
                    "put_processing_url": [],
                    "patch_processing_url": []
                }

            }
        }
    },
    
    {
        'flag': "security_app_rls_strict_mode_toggle_flag",
        "label": "Activation/Désactivation du mode strict de sécurité RLS",
        "core_seeds": {
            "restricted_profil_list": [
                *ALL_ORGANIZATION_PROFIL_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE
            ],
            "sys_apps_list": [
                {
                    "flag": "security_app_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [ 
                {
                    "flag": "security_settings_menu_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }, 
                {
                    "flag": "security_settings_rls_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }, 
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [],
                "action_to_apps": []
            },
            "rbac_custom_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "security_settings_rls_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                        "action_is_standalone": True,
                        "action_hard_code_flag": 'rls_strict_mode_toggle_action_flag',
                        "action_label": 'Activer/Désactiver'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "patch_processing_url": [
                        {
                            "hard_code_flag": "rls_strict_mode_toggle_action_processing_url",
                            "rbac_endpoint": "/api/v1/securities/settings/rls/patch/rls-strict-settings",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_settings_rls_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, ], 
                },
                "collection_meta_data_to_apps": {
                    "fetch_url": [],
                    "update_processing_url": [],
                    "update_head_process_url": [],
                    "parent_field_name": [],
                    "delete_processing_url": [],
                    "create_processing_url": [],
                    "create_head_process_url": [],
                    "create_child_processing_url": [],
                    "create_child_head_process_url": [],
                    "fetch_one_info_url": [],
                    "fetch_one_info_for_viewing_url": [],
                    "put_processing_url": [],
                    "patch_processing_url": []
                }

            }
        }
    },
    {
        'flag': "security_app_rls_protection_mode_toggle_flag",
        "label": "Activation/Désactivation de la protection de la sécurité RLS",
        "core_seeds": {
            "restricted_profil_list": [
                *ALL_ORGANIZATION_PROFIL_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE
            ],
            "sys_apps_list": [
                {
                    "flag": "security_app_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [ 
                {
                    "flag": "security_settings_menu_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }, 
                {
                    "flag": "security_settings_rls_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }, 
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [],
                "action_to_apps": []
            },
            "rbac_custom_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "security_settings_rls_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                        "action_is_standalone": True,
                        "action_hard_code_flag": 'rls_protection_mode_toggle_action_flag',
                        "action_label": 'Activer/Désactiver'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "patch_processing_url": [
                        {
                            "hard_code_flag": "rls_protection_mode_toggle_action_processing_url",
                            "rbac_endpoint": "/api/v1/securities/settings/rls/patch/rls-protection-settings",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_settings_rls_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, ], 
                },
                "collection_meta_data_to_apps": {
                    "fetch_url": [],
                    "update_processing_url": [],
                    "update_head_process_url": [],
                    "parent_field_name": [],
                    "delete_processing_url": [],
                    "create_processing_url": [],
                    "create_head_process_url": [],
                    "create_child_processing_url": [],
                    "create_child_head_process_url": [],
                    "fetch_one_info_url": [],
                    "fetch_one_info_for_viewing_url": [],
                    "put_processing_url": [],
                    "patch_processing_url": []
                }

            }
        }
    }, 
]
