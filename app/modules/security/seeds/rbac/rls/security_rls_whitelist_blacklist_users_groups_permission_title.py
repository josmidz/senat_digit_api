
from app.modules.core.constants.common import ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE, ALL_ORGANIZATION_PROFIL_IN_ONE, SENAT_DIGIT_ADMIN_WEB_IN_ONE
from app.modules.auth.enums.common import ERbacActionFlag, ERbacActionHardCodeFlag
from app.modules.core.models.mapping_keys import CollectionKey


SECURITY_RLS_WHITELIST_BLACKLIST_USERS_AND_GROUPS_PERMISSION_RBAC_TITLE_DB = [
        {
            'flag': "loading_rls_whitelist_blacklist_users_and_groups",
            'is_default': False,
            "label": "Chargement des utilisateurs/groupes de la liste blanche/noire (RLS)",
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
                        "flag": "security_rls_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_rls_whitelist_blacklist_page",
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
                                "rbac_endpoint": "/api/v1/securities/rls/whitelists/fetch/whitelist-rls",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_rls_whitelist_blacklist_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                        ],
                        "update_processing_url": [],
                        "update_head_process_url": [],
                    },
                    "collection_meta_data_to_apps": {
                        "update_processing_url": [],
                        "update_head_process_url": [],
                    }
                }
            }
        },
        {
            'flag': "adding_user_account_in_rls_whitelist_blacklist_users_and_groups",
            'is_default': False,
            "label": "Ajouter un utilisateur/groupe dans la liste blanche/noire (RLS)",
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
                        "flag": "security_rls_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_rls_whitelist_blacklist_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                ],
                "rbac_standalone_actions_obj": {
                    "action_to_menus": [ 
                        {
                                "menu_flag": "security_rls_whitelist_blacklist_page",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                                "action_is_standalone": True,
                                "action_hard_code_flag": ERbacActionHardCodeFlag.CREATION_ACTION.value,
                                "action_label": 'Créer'
                            }
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
                                "hard_code_flag": "fetch_available_sudo_rls_security_groups_url",
                                "rbac_endpoint": "/api/v1/securities/rls/whitelists/fetch/available-groups",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_rls_whitelist_blacklist_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                            {
                                "hard_code_flag": "fetch_available_users_url",
                                "rbac_endpoint": "/api/v1/securities/rls/whitelists/fetch/available-users",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_rls_whitelist_blacklist_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                            #TODO:: REMOVE LATER
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": "/api/v1/securities/rls/fetch/whitelist-users",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_rls_whitelist_blacklist_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": True,
                            },
                            {
                                "hard_code_flag": "fetch_org_users_url",
                                "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.SYS_USER.value}",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_rls_whitelist_blacklist_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": True,
                            }
                        ],
                        "create_processing_url": [
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_RLS_ACCESS.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_rls_whitelist_blacklist_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }, 
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": "/api/v1/securities/rls/add/whitelist-user",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "is_sudo_delegated_action": False,
                                "is_sudo_cross_organization_validation_action": False,
                                "is_sudo_inter_connected_organization_validation_action": False,
                                "menu_flag": "security_rls_whitelist_blacklist_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": True,
                            },
                        ],
                        "update_processing_url": [],
                        "update_head_process_url": [],
                    },
                    "collection_meta_data_to_apps": {
                        "update_processing_url": [],
                        "update_head_process_url": [],
                    }
                }
            }
        },
        {
            'flag': "removing_user_account_in_rls_whitelist_blacklist_users_and_groups",
            'is_default': False,
            "label": "Retirer un utilisateur/groupe de la liste blanche/noire (RLS)",
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
                        "flag": "security_rls_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_rls_whitelist_blacklist_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                ],
                "rbac_standalone_actions_obj": {
                    "action_to_menus": [
                        {
                            "menu_flag": "security_rls_whitelist_blacklist_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                            "action_hard_code_flag": ERbacActionHardCodeFlag.DELETION_ACTION.value,
                            "action_is_standalone": True,
                            "action_label": 'Supprimer'
                        }
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
                                "rbac_endpoint": "/api/v1/securities/rls/whitelists/fetch/whitelist-rls",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_rls_whitelist_blacklist_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": "/api/v1/securities/rls/fetch/whitelist-users",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_rls_whitelist_blacklist_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": True,
                            }
                        ],
                        "delete_processing_url": [
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_RLS_ACCESS.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_global_validators_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER.value}",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "is_sudo_delegated_action": False,
                                "is_sudo_cross_organization_validation_action": False,
                                "is_sudo_inter_connected_organization_validation_action": False,
                                "menu_flag": "security_rls_whitelist_blacklist_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": True,
                            }
                        ],
                        "update_processing_url": [],
                        "update_head_process_url": [],
                    },
                    "collection_meta_data_to_apps": {
                        "update_processing_url": [],
                        "update_head_process_url": [],
                    }
                }
            }
        },
]
