


from app.modules.auth.enums.common import ERbacActionFlag
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.common import ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE, ALL_ORGANIZATION_PROFIL_IN_ONE, SENAT_DIGIT_ADMIN_WEB_IN_ONE

SECURITY_GROUPS_PERMISSION_RBAC_TITLE_DB = [
    {
        'flag': "security_app_groups_loading_flag",
        "label": "Chargement des groupes de sécurité",
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
                    "flag": "security_groups_menu_page",
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
                            "rbac_endpoint": "/api/v1/securities/groups/fetch/groups",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_groups_menu_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        {
                            "hard_code_flag": "fetch_group_users_url",
                            "rbac_endpoint": "/api/v1/securities/groups/fetch/group-users",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_groups_menu_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "fetch_one_info_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/securities/groups/fetch/one-group",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_groups_menu_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }
                    ],
                    
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
        'flag': "security_app_groups_creation_flag",
        "label": "Création d'un groupe de sécurité",
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
                    "flag": "security_groups_menu_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }, 
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "security_groups_menu_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                        "action_is_standalone": True,
                        "action_hard_code_flag": 'creation_action_flag',
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
                    "create_processing_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP.value}",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "is_sudo_delegated_action": False,
                            "is_sudo_cross_organization_validation_action": False,
                            "is_sudo_inter_connected_organization_validation_action": False,
                            "menu_flag": "security_groups_menu_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        {
                            "hard_code_flag": "adding_user_of_group_processing_url",
                            "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER.value}",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_groups_menu_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        {
                            "hard_code_flag": "adding_bulk_user_of_group_processing_url",
                            "rbac_endpoint": "/api/v1/securities/groups/add/group-bulk-users",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_groups_menu_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "create_head_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_groups_menu_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                    ],
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
        'flag': "security_app_groups_add_user_flag",
        "label": "Ajout d'un utilisateur à un groupe de sécurité",
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
                    "flag": "security_groups_menu_page",
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
                        "menu_flag": "security_groups_menu_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                        "action_is_standalone": True,
                        "action_hard_code_flag": 'add_user_to_security_group_action_flag',
                        "action_label": 'Créer'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "fetch_url": [
                        # fetch users
                        {
                            "hard_code_flag": "fetch_org_users_for_adding_to_group_url",
                            "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.SYS_USER.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_groups_menu_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "create_processing_url": [
                        {
                            "hard_code_flag": "adding_user_to_security_group_processing_url",
                            "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER.value}",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "is_sudo_delegated_action": False,
                            "is_sudo_cross_organization_validation_action": False,
                            "is_sudo_inter_connected_organization_validation_action": False,
                            "menu_flag": "security_groups_menu_page",
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
    {
        'flag': "security_app_groups_update_flag",
        "label": "Mise à jour d'un groupe de sécurité",
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
                    "flag": "security_groups_menu_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "security_groups_menu_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                        "action_is_standalone": True,
                        "action_hard_code_flag": 'table_action_update_flag',
                        "action_label": 'Modifier'
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
                    "update_processing_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_groups_menu_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, ],
                    "update_head_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_groups_menu_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                    ],
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
        'flag': "security_app_groups_deletion_flag",
        "label": "Suppression d'un groupe de sécurité",
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
                    "flag": "security_groups_menu_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "security_groups_menu_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                        "action_hard_code_flag": 'table_action_delete_flag',
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
                    "delete_processing_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/securities/groups/delete/group",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_groups_menu_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },  
                    ],

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
        'flag': "security_app_groups_delete_user_flag",
        "label": "Suppression d'un utilisateur d'un groupe de sécurité",
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
                    "flag": "security_groups_menu_page",
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
                        "menu_flag": "security_groups_menu_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                        "action_hard_code_flag": 'delete_user_of_security_group_action_flag',
                        "action_is_standalone": True,
                        "action_label": 'Supprimer'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "delete_processing_url": [ 
                        {
                            "hard_code_flag": "delete_user_of_security_group_processing_url",
                            "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER.value}",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_groups_menu_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],

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
