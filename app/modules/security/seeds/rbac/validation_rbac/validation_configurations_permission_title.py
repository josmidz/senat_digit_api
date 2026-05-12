
from app.modules.core.constants.common import ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE, ALL_ORGANIZATION_PROFIL_IN_ONE, SENAT_DIGIT_ADMIN_WEB_IN_ONE
from app.modules.auth.enums.common import ERbacActionFlag
from app.modules.core.models.mapping_keys import CollectionKey


SECURITY_VALIDATION_CONFIGURATIONS_PERMISSION_RBAC_TITLE_DB = [
        {
            'flag': "validation_configuration_loading_permission_configurations",
            'is_default': False,
            "label": "Chargement des configurations des validations",
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
                        "flag": "security_validations_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_validations_configurations_page",
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
                    "collection_meta_data_to_apps": {
                        "update_processing_url": [],
                        "update_head_process_url": [],
                    },
                    "collection_meta_data_to_menus": {
                        "fetch_url": [
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/configurations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
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


        # SUDO ACTION PERMISSION
        {
            'flag': "validation_configuration_activating_or_deactivating_sudo_action_flag",
            'is_default': False,
            "label": "Activer/Désactiver le sudo action d'une permission ( dans configurations des validations)",
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
                        "flag": "security_validations_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_validations_configurations_page",
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
                            "menu_flag": "security_validations_configurations_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                            "action_is_standalone": True,
                            "action_hard_code_flag": 'custom_activate_or_deactivate_sudo_action_flag',
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
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/configurations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }
                        ],
                        "patch_processing_url": [
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/patch/{CollectionKey.CFG_ORGANIZATION_SUDO_ACTION.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "is_sudo_delegated_action": False,
                                "is_sudo_group_cross_validation_action": False,
                                "is_sudo_group_inter_organization_validation_action": False,
                                "menu_flag": "security_validations_configurations_page",
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

        # SUDO GROUP ACTION PERMISSION
        {
            'flag': "validation_configuration_activating_or_deactivating_sudo_group_action_flag",
            'is_default': False,
            "label": "Activer/Désactiver le sudo group action d'une permission ( dans configurations des validations)",
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
                        "flag": "security_validations_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_validations_configurations_page",
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
                            "menu_flag": "security_validations_configurations_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                            "action_is_standalone": True,
                            "action_hard_code_flag": 'custom_activate_or_deactivate_sudo_group_action_flag',
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
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/configurations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }
                        ],
                        "patch_processing_url": [
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/patch/{CollectionKey.CFG_ORGANIZATION_SUDO_ACTION.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "is_sudo_delegated_action": False,
                                "is_sudo_group_cross_validation_action": False,
                                "is_sudo_group_inter_organization_validation_action": False,
                                "menu_flag": "security_validations_configurations_page",
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

        # SUDO DELEGATED ACTION PERMISSION
        {
            'flag': "validation_configuration_activating_or_deactivating_sudo_delegated_action_flag",
            'is_default': False,
            "label": "Activer/Désactiver le sudo action deléguée d'une permission ( dans configurations des validations)",
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
                        "flag": "security_validations_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_validations_configurations_page",
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
                            "menu_flag": "security_validations_configurations_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                            "action_is_standalone": True,
                            "action_hard_code_flag": 'custom_activate_or_deactivate_sudo_delegated_action_flag',
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
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/configurations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }
                        ],
                        "patch_processing_url": [
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/patch/{CollectionKey.CFG_ORGANIZATION_SUDO_ACTION.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "is_sudo_delegated_action": False,
                                "is_sudo_group_cross_validation_action": False,
                                "is_sudo_group_inter_organization_validation_action": False,
                                "menu_flag": "security_validations_configurations_page",
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

        # SUDO GROUP INTER CONNECTED ORGANIZATION VALIDATION ACTION PERMISSION ( INTER CONNECTED ORGANIZATIONS)
        {
            'flag': "validation_configuration_activating_or_deactivating_sudo_group_inter_connected_organization_validation_action_flag",
            'is_default': False,
            "label": "Activer/Désactiver le sudo group action de validation inter organisations d'une permission (Organisations inter-connectées)",
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
                        "flag": "security_validations_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_validations_configurations_page",
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
                            "menu_flag": "security_validations_configurations_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                            "action_is_standalone": True,
                            "action_hard_code_flag": 'custom_activate_or_deactivate_sudo_group_inter_connected_organization_validation_action_flag',
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
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/configurations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }
                        ],
                        "patch_processing_url": [
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/patch/{CollectionKey.CFG_ORGANIZATION_SUDO_ACTION.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "is_sudo_delegated_action": False,
                                "is_sudo_group_cross_validation_action": False,
                                "is_sudo_group_inter_organization_validation_action": False,
                                "menu_flag": "security_validations_configurations_page",
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

        # SUDO GROUP CROSS ORGANIZATION VALIDATION ACTION PERMISSION (SAME ORGANIZATION WITH HIS BRANCHES)
        {
            'flag': "validation_configuration_activating_or_deactivating_sudo_group_cross_organization_validation_action_flag",
            'is_default': False,
            "label": "Activer/Désactiver le sudo group action de validation cross organization d'une permission ( organisation et succursale)",
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
                        "flag": "security_validations_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_validations_configurations_page",
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
                            "menu_flag": "security_validations_configurations_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                            "action_is_standalone": True,
                            "action_hard_code_flag": 'custom_activate_or_deactivate_sudo_group_cross_organization_validation_action_flag',
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
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/configurations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }
                        ],
                        "patch_processing_url": [
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/patch/{CollectionKey.CFG_ORGANIZATION_SUDO_ACTION.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "is_sudo_delegated_action": False,
                                "is_sudo_group_cross_validation_action": False,
                                "is_sudo_group_inter_organization_validation_action": False,
                                "menu_flag": "security_validations_configurations_page",
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



        # DELEGATED PERMISSION
        {
            'flag': "validation_configuration_adding_user_account_or_group_to_delegated_permission_flag",
            'is_default': False,
            "label": "Ajouter un utilisateur/groupe dans une permission deléguée",
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
                        "flag": "security_validations_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_validations_configurations_page",
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
                            "menu_flag": "security_validations_configurations_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                            "action_is_standalone": True,
                            "action_hard_code_flag": 'custom_add_user_or_group_to_delegated_permission_flag',
                            "action_label": 'Ajouter un utilisateur/groupe'
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
                                "hard_code_flag": "fetch_available_sudo_rls_security_groups_url",
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/available-groups",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                            {
                                "hard_code_flag": "fetch_available_users_url",
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/available-users",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                           {
                                "hard_code_flag": "main",
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/configurations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }
                        ],
                        "create_processing_url": [
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_SUDO_ACTION_ACCESS.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
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
            'flag': "validation_configuration_removing_user_or_group_from_delegated_permission_flag",
            'is_default': False,
            "label": "Retirer un utilisateur/groupe dans une permission deléguée",
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
                        "flag": "security_validations_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_validations_configurations_page",
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
                            "menu_flag": "security_validations_configurations_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                            "action_is_standalone": True,
                            "action_hard_code_flag": 'custom_remove_user_or_group_from_delegated_permission_flag',
                            "action_label": 'Retirer un utilisateur/groupe'
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
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/configurations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                            {
                                "hard_code_flag": "fetch_users_or_groups_or_cross_org_or_inter_connected_org_validators_as_config_validators_url",
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/config-validators",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }, 
                        ],
                        "delete_processing_url": [
                             {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_SUDO_ACTION_ACCESS.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
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

        # SUDO GROUP PERMISSION
        {
            'flag': "validation_configuration_adding_user_account_or_group_to_sudo_group_permission_flag",
            'is_default': False,
            "label": "Ajouter un utilisateur/groupe dans une permission sudo group",
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
                        "flag": "security_validations_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_validations_configurations_page",
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
                            "menu_flag": "security_validations_configurations_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                            "action_is_standalone": True,
                            "action_hard_code_flag": 'custom_add_user_or_group_to_sudo_group_permission_flag',
                            "action_label": 'Ajouter un utilisateur/groupe'
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
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/configurations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                            {
                                "hard_code_flag": "fetch_available_sudo_rls_security_groups_url",
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/available-groups",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                            {
                                "hard_code_flag": "fetch_available_users_url",
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/available-users",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                            
                        ],
                        "create_processing_url": [
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_SUDO_ACTION_ACCESS.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
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
            'flag': "validation_configuration_removing_user_or_group_from_sudo_group_permission_flag",
            'is_default': False,
            "label": "Retirer un utilisateur/groupe dans une permission sudo group",
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
                        "flag": "security_validations_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_validations_configurations_page",
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
                            "menu_flag": "security_validations_configurations_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                            "action_is_standalone": True,
                            "action_hard_code_flag": 'custom_remove_user_or_group_from_sudo_group_permission_flag',
                            "action_label": 'Retirer un utilisateur/groupe'
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
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/configurations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                            {
                                "hard_code_flag": "fetch_users_or_groups_or_cross_org_or_inter_connected_org_validators_as_config_validators_url",
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/config-validators",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }, 
                        ],
                        "delete_processing_url": [
                             {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_SUDO_ACTION_ACCESS.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
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


        # SUDO GROUP CROSS ORGANIZATION VALIDATION PERMISSION
        {
            'flag': "validation_configuration_adding_user_account_or_group_to_sudo_group_cross_organization_validation_permission_flag",
            'is_default': False,
            "label": "Ajouter une organisation dans une permission sudo group de validation cross organization",
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
                        "flag": "security_validations_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_validations_configurations_page",
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
                            "menu_flag": "security_validations_configurations_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                            "action_is_standalone": True,
                            "action_hard_code_flag": 'custom_add_user_or_group_to_sudo_group_cross_organization_validation_permission_flag',
                            "action_label": 'Ajouter une organisation'
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
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/configurations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                            {
                                "hard_code_flag": "fetch_available_cross_organizations_url",
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/available-cross-organizations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }, 
                        ],
                        "create_processing_url": [
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_SUDO_ACTION_ACCESS.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
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
            'flag': "validation_configuration_removing_user_or_group_from_sudo_group_cross_validation_permission_flag",
            'is_default': False,
            "label": "Retirer une organisation dans une permission sudo group de cross validation",
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
                        "flag": "security_validations_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_validations_configurations_page",
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
                            "menu_flag": "security_validations_configurations_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                            "action_is_standalone": True,
                            "action_hard_code_flag": 'custom_remove_user_or_group_from_sudo_group_cross_validation_permission_flag',
                            "action_label": 'Retirer une organisation'
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
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/configurations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }, 
                            {
                                "hard_code_flag": "fetch_users_or_groups_or_cross_org_or_inter_connected_org_validators_as_config_validators_url",
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/config-validators",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }, 
                        ],
                        "delete_processing_url": [
                             {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_SUDO_ACTION_ACCESS.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
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

        # SUDO INTER CONNECTED ORGANIZATION VALIDATION PERMISSION
        {
            'flag': "validation_configuration_adding_user_account_or_group_to_sudo_group_inter_organization_validation_permission_flag",
            'is_default': False,
            "label": "Ajouter une organisation dans une permission sudo group de validation inter organisation",
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
                        "flag": "security_validations_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_validations_configurations_page",
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
                            "menu_flag": "security_validations_configurations_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                            "action_is_standalone": True,
                            "action_hard_code_flag": 'custom_add_user_or_group_to_sudo_group_inter_organization_validation_permission_flag',
                            "action_label": 'Ajouter une organisation'
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
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/configurations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                            {
                                "hard_code_flag": "fetch_available_sudo_rls_inter_organization_url",
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/available-inter-organizations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }, 
                        ],
                        "create_processing_url": [
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_SUDO_ACTION_ACCESS.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
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
            'flag': "validation_configuration_removing_user_or_group_from_sudo_group_inter_organization_validation_permission_flag",
            'is_default': False,
            "label": "Retirer une organisation dans une permission sudo group de validation inter organisation",
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
                        "flag": "security_validations_menu_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                    {
                        "flag": "security_validations_configurations_page",
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
                            "menu_flag": "security_validations_configurations_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                            "action_is_standalone": True,
                            "action_hard_code_flag": 'custom_remove_user_or_group_from_sudo_group_inter_organization_validation_permission_flag',
                            "action_label": 'Retirer une organisation'
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
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/configurations",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                            {
                                "hard_code_flag": "fetch_users_or_groups_or_cross_org_or_inter_connected_org_validators_as_config_validators_url",
                                "rbac_endpoint": "/api/v1/securities/validations/configurations/fetch/config-validators",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },  
                        ],
                        "delete_processing_url": [
                             {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_SUDO_ACTION_ACCESS.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_configurations_page",
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
