

from app.modules.auth.enums.common import ERbacActionFlag
from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.common import SENAT_DIGIT_ADMIN_WEB_IN_ONE, TEST_ADMIN_ROLE_IN_ONE, TEST_PROFIL_IN_ONE
 


RH_USERS_PERMISSION_RBAC_TITLE_DB = [
    {
        'flag': "apps_ressources_humaines_loading_users_out_of_org_chart",
        "label": "Chargement des utilisateurs hors de l'organigramme",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE,
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE,
            ],
            "sys_apps_list": [
                {
                    "flag": "ressources_humaines",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_all_users",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "ressources_humaines_organization_all_users",
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
                    "fetch_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.SYS_USER.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_all_users",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "fetch_rbac_profiles_url",
                            "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.RBAC_PROFILE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_all_users",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }
                    ],
                    "fetch_one_info_url": [ 
                        {
                            "hard_code_flag": "fetch_organization_main_profil_url",
                            "rbac_endpoint": "/api/v1/organizations/fetch-main-profile",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_all_users",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "fetch_single_user_info_url",
                            "rbac_endpoint": "/api/v1/organizations/fetch-single-user-info",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                },

            }
        }

    },

    # START USER PRIVILEGES
    {
        'flag': "apps_ressources_humaines_loading_users_out_of_org_chart_privileges",
        "label": "Chargement des privilèges des utilisateurs hors de l'organigramme",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE,
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE,
            ],
            "sys_apps_list": [
                {
                    "flag": "ressources_humaines",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_all_users",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "ressources_humaines_organization_users_detail_outof_org_chart",
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
                "action_to_menus": [],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "fetch_url": [ 
                        {
                            "hard_code_flag": "fetch_user_privileges_url",
                            "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.RBAC_PRIVILEGE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }
                    ], 
                },

            }
        }

    },
    {
        'flag': "apps_ressources_humaines_deleting_users_out_of_org_chart_privileges",
        "label": "Suppression des privilèges des utilisateurs",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE,
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE,
            ],
            "sys_apps_list": [
                {
                    "flag": "ressources_humaines",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_all_users",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "ressources_humaines_organization_users_detail_outof_org_chart",
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
                        "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                        "action_hard_code_flag": 'custom_user_privilege_action_delete_flag',
                        "action_is_standalone": False,
                        "action_label": 'Supprimer un privilège'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "delete_processing_url": [
                        {
                            "hard_code_flag": "custom_user_privilege_deletion_process_url",
                            "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.RBAC_PRIVILEGE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
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
        'flag': "apps_ressources_humaines_granting_organization_users_out_of_org_chart_privileges",
        "label": "Octroi des privilèges à un utilisateur",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE,
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE,
            ],
            "sys_apps_list": [
                {
                    "flag": "ressources_humaines",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_all_users",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "ressources_humaines_organization_users_detail_outof_org_chart",
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
                "action_to_menus": [
                    {
                        "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                        "action_is_standalone": False,
                        "action_hard_code_flag": 'custom_user_privilege_action_create_flag',
                        "action_label": 'Octroi des privilèges'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "create_processing_url": [
                        {
                            "hard_code_flag": "custom_user_privilege_creation_process_url",
                            "rbac_endpoint": "/api/v1/organizations/add/user-privileges",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "create_head_process_url": [
                        {
                            "hard_code_flag": "custom_user_privilege_creation_head_process_url",
                            "rbac_endpoint": "/api/v1/organizations/head/user-privileges",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
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
    # END USER PRIVILEGES

    # START USER LOGIN HISTORY
    {
        'flag': "apps_ressources_humaines_loading_users_out_of_org_chart_login_history",
        "label": "Chargement des historiques de connexion des utilisateurs hors de l'organigramme",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE,
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE,
            ],
            "sys_apps_list": [
                {
                    "flag": "ressources_humaines",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_all_users",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "ressources_humaines_organization_users_detail_outof_org_chart",
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
                "action_to_menus": [],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "fetch_url": [ 
                        {
                            "hard_code_flag": "fetch_user_login_history_url",
                            "rbac_endpoint": "/api/v1/organizations/fetch/user-login-histories",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        
                    ], 
                },

            }
        }
    },
    # END USER LOGIN HISTORY

    # START USER DEVICES
    {
        'flag': "apps_ressources_humaines_loading_users_out_of_org_chart_devices",
        "label": "Chargement des devices des utilisateurs hors de l'organigramme",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE,
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE,
            ],
            "sys_apps_list": [
                {
                    "flag": "ressources_humaines",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_all_users",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "ressources_humaines_organization_users_detail_outof_org_chart",
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
                "action_to_menus": [],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "fetch_url": [ 
                        {
                            "hard_code_flag": "fetch_user_devices_url",
                            "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.CFG_USER_DEVICE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }
                    ], 
                },

            }
        }

    },
    {
        'flag': "apps_ressources_humaines_deleting_users_out_of_org_chart_devices",
        "label": "Suppression des devices des utilisateurs",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE,
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE,
            ],
            "sys_apps_list": [
                {
                    "flag": "ressources_humaines",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_all_users",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "ressources_humaines_organization_users_detail_outof_org_chart",
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
                        "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                        "action_hard_code_flag": 'custom_user_device_action_delete_flag',
                        "action_is_standalone": False,
                        "action_label": 'Supprimer'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "delete_processing_url": [
                        {
                            "hard_code_flag": "delete_user_device_url",
                            "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_USER_DEVICE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
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
        'flag': "apps_ressources_humaines_org_chart_devices_lock_unlock",
        "label": "Bloquer/ Débloquer les terminaux des utilisateurs",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE,
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE,
            ],
            "sys_apps_list": [
                {
                    "flag": "ressources_humaines",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_all_users",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "ressources_humaines_organization_users_detail_outof_org_chart",
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
                        "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
                        "action_flag": ERbacActionFlag.COMMON_LOCK_ACTION.value,
                        "action_is_standalone": True,
                        "action_hard_code_flag": 'custom_user_device_action_lock_unlock_flag',
                        "action_label": 'Bloquer/ Débloquer'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "update_processing_url": [
                        {
                            "hard_code_flag": "update_user_device_status_url",
                            "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.CFG_USER_DEVICE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
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
        'flag': "apps_ressources_humaines_org_chart_allowed_devices_count",
        "label": "Modifier le nombre de terminaux autorisés par utilisateur",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE,
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE,
            ],
            "sys_apps_list": [
                {
                    "flag": "ressources_humaines",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_all_users",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "ressources_humaines_organization_users_detail_outof_org_chart",
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
                        "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                        "action_is_standalone": True,
                        "action_hard_code_flag": 'custom_user_allowed_device_count_action_update_flag',
                        "action_label": 'Valider'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "update_processing_url": [#update_user_device_count_url
                        {
                            "hard_code_flag": "update_user_device_count_url",
                            "rbac_endpoint": "/api/v1/organizations/update/user-device-count",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
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
        'flag': "apps_ressources_humaines_org_chart_devices_validations",
        "label": "Valider les terminaux des utilisateurs",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE,
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE,
            ],
            "sys_apps_list": [
                {
                    "flag": "ressources_humaines",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_all_users",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "ressources_humaines_organization_users_detail_outof_org_chart",
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
                        "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                        "action_is_standalone": True,
                        "action_hard_code_flag": 'custom_user_device_action_validation_flag',
                        "action_label": 'Valider'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "update_processing_url": [
                        {
                            "hard_code_flag": "update_user_device_status_url",
                            "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.CFG_USER_DEVICE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_users_detail_outof_org_chart",
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
    # END USER DEVICES


    {
        'flag': "apps_ressources_humaines_org_creating_organization_users_out_of_org_chart",
        "label": "Création d'un nouvel utilisateur hors de l'organigramme",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE,
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE,
            ],
            "sys_apps_list": [
                {
                    "flag": "ressources_humaines",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_all_users",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "ressources_humaines_organization_all_users",
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
                            "rbac_endpoint": f"/api/v1/organizations/add/{CollectionKey.SYS_USER.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_all_users",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "create_head_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.SYS_USER.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_all_users",
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
        'flag': "apps_ressources_humaines_org_updating_organization_users_in_all_or_under_chart",
        "label": "Mise à jour d'un utilisateur hors organigramme"
    },
    {
        'flag': "apps_ressources_humaines_org_deleting_organization_users_in_all_outof_chart",
        "label": "Suppression d'un utilisateur hors organigramme"
    },
    {
        'flag': "apps_ressources_humaines_org_generating_organization_users_password_reset_link",
        "label": "Génération du lien de réinitialisation du mot de passe",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE,
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE,
            ],
            "sys_apps_list": [
                {
                    "flag": "ressources_humaines",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_all_users",
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
                        "menu_flag": "ressources_humaines_organization_all_users",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                        "action_is_standalone": False,
                        "action_hard_code_flag": 'custom_generate_initpassword_link_action_unlock_flag',
                        "action_label": 'Générer le lien de modification de mot de passe.'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "create_processing_url": [
                        {
                            "hard_code_flag": "password_reset_link_generation_process_url",
                            "rbac_endpoint": "/api/v1/organizations/generate-reset-password-link",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_all_users",
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
]

