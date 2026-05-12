

from app.modules.core.constants.common import ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE, ALL_ORGANIZATION_PROFIL_IN_ONE, SENAT_DIGIT_ADMIN_WEB_IN_ONE
from app.modules.auth.enums.common import ERbacActionFlag, ERbacActionHardCodeFlag
from app.modules.core.models.mapping_keys import CollectionKey


SECURITY_RLS_SETUP_PERMISSION_RBAC_TITLE_DB = [
    {
        'flag': "loading_rls_setup_flag",
        'is_default': False,
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
                    "flag": "security_rls_menu_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "security_rls_setup_page",
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
                            "rbac_endpoint": "/api/v1/securities/rls/rls-settings/fetch/formated-permissions",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_setup_page",
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
    # -----------
    {
        'flag': "security_rls_setup_enable_or_disable_rls_protection_to_a_permission_flag",
        'is_default': False,
        "label": "Activer/Désactiver la protection RLS d'une permission",
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
                    "flag": "security_rls_setup_page",
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
                        "menu_flag": "security_rls_setup_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                        "action_is_standalone": True,
                        "action_hard_code_flag": 'custom_activate_or_deactivate_rls_protection_to_a_permission_flag',
                        "action_label": 'Activer/Désactiver'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "fetch_url": [ 
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/securities/rls/rls-settings/fetch/formated-permissions",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "patch_processing_url": [
                        {
                            "hard_code_flag": "custom_activate_or_deactivate_rls_protection_to_a_permission_flag",
                            "rbac_endpoint": f"/api/v1/generic/org/patch/{CollectionKey.CFG_RLS_ACCESS.value}",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "is_sudo_delegated_action": False,
                            "is_sudo_group_cross_validation_action": False,
                            "is_sudo_group_inter_organization_validation_action": False,
                            "menu_flag": "security_rls_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },  
                    ],
                    "create_head_process_url": [],
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
    # -----------
    {
        'flag': "security_rls_setup_enable_or_disable_rls_strict_mode_to_a_permission_flag",
        'is_default': False,
        "label": "Activer/Désactiver du mode strict de la protection RLS d'une permission",
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
                    "flag": "security_rls_setup_page",
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
                        "menu_flag": "security_rls_setup_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                        "action_is_standalone": True,
                        "action_hard_code_flag": 'custom_activate_or_deactivate_strict_mode_rls_protection_flag',
                        "action_label": 'Activer/Désactiver'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "fetch_url": [ 
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/securities/rls/rls-settings/fetch/formated-permissions",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "patch_processing_url": [
                        {
                            "hard_code_flag": "custom_activate_or_deactivate_strict_mode_rls_protection_flag",
                            "rbac_endpoint": f"/api/v1/generic/org/patch/{CollectionKey.CFG_ORGANIZATION_RLS.value}",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "is_sudo_delegated_action": False,
                            "is_sudo_group_cross_validation_action": False,
                            "is_sudo_group_inter_organization_validation_action": False,
                            "menu_flag": "security_rls_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },  
                    ],
                    "create_head_process_url": [],
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

    # PERMISSION WHITE LIST
    {
        'flag': "security_rls_setup_adding_user_or_group_in_rls_whitelist_of_a_permission_flag",
        'is_default': False,
        "label": "Ajouter un utilisateur/groupe dans la liste blanche (RLS) d'une permission",
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
                    "flag": "security_rls_setup_page",
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
                        "menu_flag": "security_rls_setup_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                        "action_hard_code_flag": "custom_action_add_user_or_group_in_rls_whitelist_of_a_permission_flag",
                        "action_is_standalone": True,
                        "action_label": 'Ajouter'
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
                    "fetch_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/securities/rls/rls-settings/fetch/formated-permissions",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "fetch_available_rls_security_groups_url",
                            "rbac_endpoint": "/api/v1/securities/rls/rls-settings/fetch/available-groups",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "fetch_available_users_url",
                            "rbac_endpoint": "/api/v1/securities/rls/rls-settings/fetch/available-users",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "create_processing_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_RLS_ACCESS.value}",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_setup_page",
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
    {
        'flag': "security_rls_setup_removing_user_or_group_from_rls_whitelist_of_a_permission_flag",
        'is_default': False,
        "label": "Retirer un utilisateur/groupe d'une liste blanche (RLS) d'une permission",
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
                    "flag": "security_rls_setup_page",
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
                        "menu_flag": "security_rls_setup_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                        "action_hard_code_flag": 'custom_action_remove_user_or_group_from_rls_whitelist_of_a_permission_flag',
                        "action_is_standalone": True,
                        "action_label": 'Supprimer'
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
                    "fetch_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/securities/rls/rls-settings/fetch/formated-permissions",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                          
                    ],
                    "delete_processing_url": [
                            {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_RLS_ACCESS.value}",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_setup_page",
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
    #PERMISSION BLACK LIST
    {
        'flag': "security_rls_setup_adding_user_or_group_in_rls_blacklist_of_a_permission_flag",
        'is_default': False,
        "label": "Ajouter un utilisateur/groupe dans la liste noire (RLS) d'une permission",
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
                    "flag": "security_rls_setup_page",
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
                        "menu_flag": "security_rls_setup_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                        "action_hard_code_flag": "custom_action_add_user_or_group_in_rls_blacklist_of_a_permission_flag",
                        "action_is_standalone": True,
                        "action_label": 'Ajouter'
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
                    "fetch_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/securities/rls/rls-settings/fetch/formated-permissions",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "fetch_available_rls_security_groups_url",
                            "rbac_endpoint": "/api/v1/securities/rls/rls-settings/fetch/available-groups",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "fetch_available_users_url",
                            "rbac_endpoint": "/api/v1/securities/rls/rls-settings/fetch/available-users",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "create_processing_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_RLS_ACCESS.value}",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_setup_page",
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
    {
        'flag': "security_rls_setup_removing_user_or_group_from_rls_blacklist_of_a_permission_flag",
        'is_default': False,
        "label": "Retirer un utilisateur/groupe d'une liste noire (RLS) d'une permission",
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
                    "flag": "security_rls_setup_page",
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
                        "menu_flag": "security_rls_setup_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                        "action_hard_code_flag": 'custom_action_remove_user_or_group_from_rls_blacklist_of_a_permission_flag',
                        "action_is_standalone": True,
                        "action_label": 'Supprimer'
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
                    "fetch_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/securities/rls/rls-settings/fetch/formated-permissions",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_setup_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "delete_processing_url": [
                            {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_RLS_ACCESS.value}",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_setup_page",
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
     
]
