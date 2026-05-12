

from app.modules.auth.enums.common import ERbacActionFlag
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.common import SENAT_DIGIT_ADMIN_WEB_IN_ONE, TEST_ADMIN_ROLE_IN_ONE, TEST_PROFIL_IN_ONE

RH_ROLES_PERMISSION_RBAC_TITLE_DB = [
    {
        'flag': "apps_ressources_humaines_loading_organization_global_roles",
        "label": "Chargement des rôles hors l'arborescence de l'organigramme",
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
                    "flag": "app_settings",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_rbac_roles",
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
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.RBAC_ROLE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_rbac_roles",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }
                    ],
                    "fetch_one_info_url": [
                        {
                            "hard_code_flag": "fetch_single_organization_chart_url",
                            "rbac_endpoint": f"/api/v1/generic/org/fetch-one/{CollectionKey.CFG_ORGANISM_CHART.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_rbac_roles",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "fetch_organization_main_profil_url",
                            "rbac_endpoint": "/api/v1/organizations/fetch-main-profile",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_rbac_roles",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }
                    ],
                },

            }
        }
    
    },
    {
        'flag': "apps_ressources_humaines_creating_organization_global_roles",
        "label": "Création d'un nouveau rôle hors l'arborescence de l'organigramme",
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
                    "flag": "app_settings",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_rbac_roles",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "ressources_humaines_organization_rbac_roles",
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
                            "rbac_endpoint": "/api/v1/static/data/org/create-role",
                            "is_sudo_action": True,
                            "is_sudo_group_action": True,
                            "menu_flag": "ressources_humaines_organization_rbac_roles",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "create_head_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.RBAC_ROLE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_rbac_roles",
                            "is_parent_field_name": False,
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
        'flag': "apps_ressources_humaines_updating_organization_global_roles",
        "label": "Mise à jour d'un rôle hors l'arborescence de l'organigramme",
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
                    "flag": "app_settings",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_rbac_roles",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "ressources_humaines_organization_rbac_roles",
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
                            "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.RBAC_ROLE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_rbac_roles",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "update_head_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.RBAC_ROLE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_rbac_roles",
                            "is_parent_field_name": False,
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
        'flag': "apps_ressources_humaines_updating_roles_permissions_of_organization_global_roles_inner_roles",
        "label": "Modification des permissions d'un rôle",
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
                    "flag": "app_settings",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_rbac_roles",
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
                        "menu_flag": "ressources_humaines_organization_rbac_roles",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                        "action_is_standalone": False,
                        "action_hard_code_flag": 'custom_update_permission_table_action_flag',
                        "action_label": 'Mettre à jour des permissions"'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "update_processing_url": [
                        {
                            "hard_code_flag": "custom_permission_update_process_url",
                            "rbac_endpoint": "/api/v1/static/data/org/update-role-permissions",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_rbac_roles",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "update_head_process_url": [
                        {
                            "hard_code_flag": "custom_permission_update_head_process_url",
                            "rbac_endpoint": "/api/v1/static/data/org/get-role-permissions",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "ressources_humaines_organization_rbac_roles",
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
        'flag': "apps_ressources_humaines_deleting_organization_global_roles",
        "label": "Suppression d'un rôle hors l'arborescence de l'organigramme",
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
                    "flag": "app_settings",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "ressources_humaines_organization_rbac_roles",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "ressources_humaines_organization_rbac_roles",
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
                            "rbac_endpoint": "/api/v1/static/data/org/create-role",
                            "is_sudo_action": True,
                            "is_sudo_group_action": True,
                            "is_sudo_delegated_action": True,
                            "menu_flag": "ressources_humaines_organization_rbac_roles",
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
