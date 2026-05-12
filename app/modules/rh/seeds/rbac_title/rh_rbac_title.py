

from app.modules.auth.enums.common import ERbacActionFlag
from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.rh.seeds.rbac_title.rh_fonction_rbac_title import RH_FONCTION_PERMISSION_RBAC_TITLE_DB
from app.modules.rh.seeds.rbac_title.rh_grade_rbac_title import RH_GRADE_PERMISSION_RBAC_TITLE_DB
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.common import SENAT_DIGIT_ADMIN_WEB_IN_ONE, TRANS_ADMIN_ROLE_IN_ONE, MAIN_PROFILE_IN_ONE, TRANS_RH_ROLE_IN_ONE

RH_PERMISSION_RBAC_TITLE_DB = [
    {
        "label": "Organigramme",
        "flag": "apps_ressources_humaines_organization_chart_list_flag",
        "is_default": False,
        "permissions": [

            {
                'flag': "apps_ressources_humaines_loading_organization_chart_list",
                "label": "Chargement des arborescences de l'organigramme",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
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
                            "flag": "ressources_humaines_organization_chart",
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
                                    "rbac_endpoint": "/api/v1/organizations/fetch/organism-charts",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                            ],
                        },

                    }
                }
        
            },
            {
                'flag': "apps_ressources_humaines_creating_organization_chart_list",
                "label": "Création d'arborescence dans l'organigramme",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
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
                            "flag": "ressources_humaines_organization_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "rbac_standalone_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                                "action_is_standalone": True,
                                "action_hard_code_flag": 'creation_action_flag',
                                "action_label": 'Créer'
                            },
                            {
                                "menu_flag": "ressources_humaines_organization_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_ADD_CHILD.value,
                                "action_is_standalone": True,
                                "action_hard_code_flag": 'table_action_add_child_flag',
                                "action_label": 'Créer'
                            },
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
                                    "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_ORGANISM_CHART.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "create_head_process_url": [
                                {
                                    "hard_code_flag": "main",
                                    "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.CFG_ORGANISM_CHART.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "create_child_processing_url": [
                                {
                                    "hard_code_flag": "main",
                                    "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_ORGANISM_CHART.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "create_child_head_process_url": [
                                {
                                    "hard_code_flag": "main",
                                    "rbac_endpoint": f"/api/v1/generic/org/child-head/{CollectionKey.CFG_ORGANISM_CHART.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_chart",
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
                'flag': "apps_ressources_humaines_updating_organization_chart_list",
                "label": "Mise à jour d'un noeud de l'arborescence dans l'organigramme",
                 "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "rbac_standalone_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_chart",
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
                                    "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.CFG_ORGANISM_CHART.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "update_head_process_url": [
                                {
                                    "hard_code_flag": "main",
                                    "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.CFG_ORGANISM_CHART.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_chart",
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
                'flag': "apps_ressources_humaines_deleting_organization_chart_list",
                "label": "Suppression d'arborescence dans l'organigramme",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
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
                            "flag": "ressources_humaines_organization_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "rbac_standalone_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_chart",
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
                                    "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_ORGANISM_CHART.value}",
                                    "is_sudo_action": True,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_chart",
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
        ],
        "endpoints": [
            {
                "label": "Chargement des arborescences dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/organizations/fetch/organism-charts"
            },
            {
                "label": "Suppression d'utilisateur",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/organizations/hard-delete/user"
            },
            {
                "label": "Chargement des arborescences dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/fetch/{CollectionKey.CFG_ORGANISM_CHART.value}"
            },
            {
                "label": "Création d'un noeud de l'arborescence dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/add/{CollectionKey.CFG_ORGANISM_CHART.value}"
            },
            {
                "label": "Chargement du formulaire de création d'un noeud parent de l'arborescence dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/head/{CollectionKey.CFG_ORGANISM_CHART.value}"
            },
            {
                "label": "Chargement du formulaire de création d'un noeud enfant de l'arborescence dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/child-head/{CollectionKey.CFG_ORGANISM_CHART.value}"
            },
            {
                "label": "Mise à jour d'un noeud de l'arborescence dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/update/{CollectionKey.CFG_ORGANISM_CHART.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour d'un noeud de l'arborescence dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/update-head/{CollectionKey.CFG_ORGANISM_CHART.value}"
            },
            {
                "label": "Suppression d'un noeud de l'arborescence dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/delete/{CollectionKey.CFG_ORGANISM_CHART.value}"
            },
            {
                "label": "Suppression définitive d'un noeud de l'arborescence dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_ORGANISM_CHART.value}"
            },
            {
                "label": "Le chargement d'une seule information d'un noeud de l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/fetch-one/{CollectionKey.CFG_ORGANISM_CHART.value}"
            },
        ],

    },
    {
        "label": "Agents",
        "flag": "apps_ressources_humaines_organization_chart_agents_flag",
        "is_default": False,
        "children": [
            {
                "label": "Compte utilisateur",
                "flag": "apps_ressources_humaines_organization_chart_agents_user_account_flag",
                "is_default": False,
                "children": [],
                "permissions": [
                    {
                        'flag': "apps_ressources_humaines_system_loading_organization_chart_agents_user_account",
                        "label": "[system] Chargement des comptes utilisateurs d'un agent"
                    },
                    {
                        'flag': "apps_ressources_humaines_system_deleting_organization_chart_agents_user_account",
                        "label": "[system] Suppression des comptes utilisateurs d'un agent",
                    },
                    {
                        'flag': "apps_ressources_humaines_creating_organization_chart_agents_user_account",
                        "label": "Création d'un nouveau compte utilisateur"
                    },
                    {
                        'flag': "apps_ressources_humaines_updating_organization_chart_agents_user_account",
                        "label": "Mise à jour d'un compte utilisateur"
                    },
                    {
                        'flag': "apps_ressources_humaines_deleting_organization_chart_agents_user_account",
                        "label": "Suppression d'un compte utilisateur"
                    },
                ],
                "endpoints": [

                ],

            },
        ],
        "permissions": [
            # {
            #     'flag': "apps_ressources_humaines_system_loading_organization_chart_agents",
            #     "label": "[system] Chargement des agents d'une organisation"
            # },
            {
                'flag': "apps_ressources_humaines_loading_organization_chart_agents",
                "label": "Chargement des agents dans l'organigramme",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_agents_from_org_chart",
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
                                    "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.SYS_ORGANIZATION_AGENT.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                }, 
                                {
                                    "hard_code_flag": "fetch_rbac_profiles_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "fetch_bulk_template_url",
                                    "rbac_endpoint": "/api/v1/organizations/fetch/agents-bulk-template",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "fetch_single_organization_chart_agent_overview_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/data-overview/{CollectionKey.SYS_ORGANIZATION_AGENT.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                
                                {
                                    "hard_code_flag": "fetch_organization_main_profil_url",
                                    "rbac_endpoint": "/api/v1/organizations/fetch-main-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                }
                            ],
                        },

                    }
                }
    
            }, 
            {
                'flag': "apps_ressources_humaines_creating_organization_chart_agents",
                "label": "Création d'un nouvel agent",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_agents_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "rbac_standalone_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
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
                                    "rbac_endpoint": "/api/v1/organizations/add/agents",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "bulk_upload_processing_url",
                                    "rbac_endpoint": "/api/v1/organizations/bulk-upload/agents",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                            ],

                            "create_head_process_url": [
                                # {
                                #     "hard_code_flag": "main",
                                #     "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.RBAC_ROLE.value}",
                                #     "is_sudo_action": False,
                                #     "is_sudo_group_action": False,
                                #     "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
                                #     "is_parent_field_name": False,
                                # },
                                {
                                    "hard_code_flag": "main",
                                    "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.SYS_ORGANIZATION_AGENT.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
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
                'flag': "apps_ressources_humaines_updating_organization_chart_agents",
                "label": "Mise à jour d'un agent",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_agents_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "rbac_standalone_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
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
                                    "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.SYS_ORGANIZATION_AGENT.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                }, 
                            ],
                            "update_head_process_url": [
                                {
                                    "hard_code_flag": "main",
                                    "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.SYS_ORGANIZATION_AGENT.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "fetch_one_info_url": [
                                {
                                    "hard_code_flag": "fetch_single_organization_chart_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/fetch-one/{CollectionKey.CFG_ORGANISM_CHART.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "fetch_single_organization_chart_agent_overview_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/data-overview/{CollectionKey.SYS_ORGANIZATION_AGENT.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                
                                {
                                    "hard_code_flag": "fetch_organization_main_profil_url",
                                    "rbac_endpoint": "/api/v1/organizations/fetch-main-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
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
                'flag': "apps_ressources_humaines_deleting_organization_chart_agents",
                "label": "Suppression d'un agent",
                 "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_agents_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "rbac_standalone_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
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
                                    "rbac_endpoint": "/api/v1/organizations/hard-delete/agents",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "fetch_one_info_url": [
                                {
                                    "hard_code_flag": "fetch_single_organization_chart_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/fetch-one/{CollectionKey.CFG_ORGANISM_CHART.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "fetch_single_organization_chart_agent_overview_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/data-overview/{CollectionKey.SYS_ORGANIZATION_AGENT.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                
                                {
                                    "hard_code_flag": "fetch_organization_main_profil_url",
                                    "rbac_endpoint": "/api/v1/organizations/fetch-main-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
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
        ],
        "endpoints": [
            {
                "label": "Chargement des agents dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/fetch/{CollectionKey.SYS_ORGANIZATION_AGENT.value}"
            },
            {
                "label": "L'url pour l'aperçu d'une dépense pour une organisation",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/data-overview/{CollectionKey.SYS_ORGANIZATION_AGENT.value}"
            },
            {
                "label": "Chargement du formulaire de création des agents dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/head/{CollectionKey.SYS_ORGANIZATION_AGENT.value}"
            },
            {
                "label": "Création d'un agent dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/organizations/add/agents"
            },
            {
                "label": "Chargement du formulaire de mise à jour des agents dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/update-head/{CollectionKey.SYS_ORGANIZATION_AGENT.value}"
            },
            {
                "label": "Chargement d'un agent",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/fetch-one/{CollectionKey.SYS_ORGANIZATION_AGENT.value}"
            },
            {
                "label": "Mise à jour des agents dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/update/{CollectionKey.SYS_ORGANIZATION_AGENT.value}"
            },
            {
                "label": "Suppression d'un agent dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/organizations/hard-delete/agents"
            },
            {
                "label": "Import en masse des agents",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/organizations/bulk-upload/agents"
            },
            {
                "label": "Téléchargement du template d'import en masse des agents",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/organizations/fetch/agents-bulk-template"
            },
        ],

    },
    {
        "label": "Utilisateurs",
        "flag": "apps_ressources_humaines_organization_chart_users_flag",
        "is_default": False,
        "children": [],
        "permissions": [

            {
                'flag': "apps_ressources_humaines_loading_organization_chart_users",
                "label": "Chargement des utilisateurs dans l'organigramme",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_users_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                        {
                            "flag": "ressources_humaines_organization_users_detail_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "rbac_standalone_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_users_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "fetch_rbac_profiles_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "fetch_single_organization_chart_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/fetch-one/{CollectionKey.CFG_ORGANISM_CHART.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_users_detail_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "fetch_organization_main_profil_url",
                                    "rbac_endpoint": "/api/v1/organizations/fetch-main-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "fetch_organization_agent_user_account_url",
                                    "rbac_endpoint": "/api/v1/static/org/get-agent-user-account",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                            ],
                        },

                    }
                }

            },
            {
                'flag': "apps_ressources_humaines_creating_organization_chart_users",
                "label": "Création d'un nouvel utilisateur dans l'organigramme",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_users_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "rbac_standalone_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_users_from_org_chart",
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
                                    "rbac_endpoint": "/api/v1/organizations/add/sysUsers",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "org_agent_user_account_head_url",
                                    "rbac_endpoint": "/api/v1/static/org/agent-user-account-head",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
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
                'flag':"apps_ressources_humaines_updating_organization_chart_users",
                "label": "Mise à jour d'un utilisateur dans l'organigramme",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_users_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "rbac_standalone_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_users_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
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
                'flag':"apps_ressources_humaines_deleting_organization_chart_users",
                "label": "Suppression d'un utilisateur dans l'organigramme",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_users_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "rbac_standalone_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_users_from_org_chart",
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
                                    "rbac_endpoint": "/api/v1/organizations/hard-delete/user",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
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

            # START USER PRIVILEGES
            {
                'flag': "apps_ressources_humaines_deleting_organization_chart_privileges",
                "label": "Chargement des privilèges des utilisateurs dans de l'organigramme",
                "core_seeds": {
                   "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_users_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                        {
                            "flag": "ressources_humaines_organization_users_privileges_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_users_privileges_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                }
                            ], 
                        },

                    }
                }

            },
            {
                'flag': "apps_ressources_humaines_deleting_users_of_org_chart_privileges",
                "label": "Suppression des privilèges des utilisateurs",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_users_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                        {
                            "flag": "ressources_humaines_organization_users_privileges_from_org_chart",
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
                                "menu_flag": "ressources_humaines_organization_users_privileges_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_users_detail_from_org_chart",
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
                'flag': "settings_granting_organization_users_out_of_org_chart_privileges",
                "label": "Octroi des privilèges à un utilisateur",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                         
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_users_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                        {
                            "flag": "ressources_humaines_organization_users_privileges_from_org_chart",
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
                                "menu_flag": "ressources_humaines_organization_users_privileges_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_users_privileges_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_users_privileges_from_org_chart",
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
                'flag': "apps_ressources_humaines_deleting_organization_chart_login_history",
                "label": "Chargement des historiques de connexion des utilisateurs dans de l'organigramme",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_users_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                        {
                            "flag": "ressources_humaines_organization_users_login_histories_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_users_login_histories_from_org_chart",
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
                'flag': "apps_ressources_humaines_deleting_organization_chart_devices",
                "label": "Chargement des devices des utilisateurs dans de l'organigramme",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_users_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                        {
                            "flag": "ressources_humaines_organization_users_devices_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_users_devices_from_org_chart",
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
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_users_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                        {
                            "flag": "ressources_humaines_organization_users_devices_from_org_chart",
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
                                "menu_flag": "ressources_humaines_organization_users_devices_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_users_devices_from_org_chart",
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
                'flag': "apps_ressources_humaines_update_users_out_of_org_chart_devices_lock_unlock",
                "label": "Bloquer/ Débloquer les terminaux des utilisateurs",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_users_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                        {
                            "flag": "ressources_humaines_organization_users_devices_from_org_chart",
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
                                "menu_flag": "ressources_humaines_organization_users_devices_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_users_devices_from_org_chart",
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
                'flag': "apps_ressources_humaines_update_users_out_of_org_chart_allowed_devices_count",
                "label": "Modifier le nombre de terminaux autorisés par utilisateur",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_users_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                        {
                            "flag": "ressources_humaines_organization_users_devices_from_org_chart",
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
                                "menu_flag": "ressources_humaines_organization_users_devices_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_users_devices_from_org_chart",
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
                'flag': "apps_ressources_humaines_update_users_out_of_org_chart_devices_validations",
                "label": "Valider les terminaux des utilisateurs",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_users_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                        {
                            "flag": "ressources_humaines_organization_users_devices_from_org_chart",
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
                                "menu_flag": "ressources_humaines_organization_users_devices_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_users_devices_from_org_chart",
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
        ],
        "endpoints": [
            {
                "label": "Chargement des utilisateurs dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/fetch/{CollectionKey.SYS_USER.value}"
            },
            {
                "label": "Chargement des profils rbac",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/fetch/{CollectionKey.RBAC_PROFILE.value}"
            },
            {
                "label": "Chargement d'un noeud de l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/fetch-one/{CollectionKey.CFG_ORGANISM_CHART.value}"
            },
            {
                "label": "Chargement du profil principal d'une organisation",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/organizations/fetch-main-profile"
            },
            {
                "label": "Création d'un utilisateur dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/organizations/add/sysUsers"
            },
            {
                "label": "Chargement du formulaire de création d'un utilisateur dans l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/head/{CollectionKey.SYS_USER.value}"
            },
            {
                "label": "Chargement du formulaire de création de compte utilisateur agent",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/org/agent-user-account-head"
            },
            {
                "label": "Mise à jour du rôle d'un utilisateur",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/update/{CollectionKey.RBAC_ROLE.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour du rôle d'un utilisateur",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/update-head/{CollectionKey.RBAC_ROLE.value}"
            },
            {
                "label": "Suppression d'un utilisateur",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/organizations/hard-delete/user"
            },
            {
                "label": "Chargement des privilèges des utilisateurs",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/fetch/{CollectionKey.RBAC_PRIVILEGE.value}"
            },
            {
                "label": "Suppression des privilèges des utilisateurs",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.RBAC_PRIVILEGE.value}"
            },
            {
                "label": "Création des privilèges des utilisateurs",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/organizations/add/user-privileges"
            },
            {
                "label": "Chargement du formulaire de création des privilèges des utilisateurs",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/organizations/head/user-privileges"
            },
            {
                "label": "Chargement des historiques de connexion des utilisateurs",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/organizations/fetch/user-login-histories"
            },
            {
                "label": "Chargement des terminaux des utilisateurs",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/fetch/{CollectionKey.CFG_USER_DEVICE.value}"
            },
            {
                "label": "Suppression des terminaux des utilisateurs",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_USER_DEVICE.value}"
            },
            {
                "label": "Mise à jour des terminaux des utilisateurs",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/update/{CollectionKey.CFG_USER_DEVICE.value}"
            },
            {
                "label": "Modification du nombre de terminaux autorisés par utilisateur",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/organizations/update/user-device-count"
            },
        ],

    },

    {
        "label": "Profil rbac",
        "flag": "apps_ressources_humaines_organization_organism_chart_profiles_flag",
        "is_default": False,
        "children": [],
        "permissions": [

            {
                'flag': "apps_ressources_humaines_loading_organization_organism_chart_profiles",
                "label": "Chargement des profils rbac sous l'arborescence de l'organigramme",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_profiles_from_org_chart",
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
                                    "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                 
                                
                            ],
                            
                            "fetch_one_info_url": [
                                {
                                    "hard_code_flag": "fetch_single_organization_chart_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/fetch-one/{CollectionKey.CFG_ORGANISM_CHART.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                }, 
                                {
                                    "hard_code_flag": "fetch_organization_main_profil_url",
                                    "rbac_endpoint": "/api/v1/organizations/fetch-main-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                            ],
                        },

                    }
                }
    
            },
            {
                'flag': "apps_ressources_humaines_creating_organization_organism_chart_profiles",
                "label": "Création d'un nouveau profil rbac sous l'arborescence de l'organigramme",
                 "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_profiles_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "rbac_standalone_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                                "action_is_standalone": True,
                                "action_hard_code_flag": 'creation_action_flag',
                                "action_label": 'Créer'
                            }
                        ],
                        "action_to_apps": []
                    },
                    "rbac_custom_actions_obj": {
                        "action_to_menus": [
                            # ACCESS FROM ROLE UNDER ORG CHART
                            {
                                "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                                "action_is_standalone": False,
                                "action_hard_code_flag": 'dynamic_can_create_rbac_profil_action_flag',
                                "action_label": 'Créer'
                            }, 
                            # ACCESS FROM USER UNDER ORG CHART
                            {
                                "menu_flag": "ressources_humaines_organization_users_from_org_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                                "action_is_standalone": False,
                                "action_hard_code_flag": 'dynamic_can_create_rbac_profil_action_flag',
                                "action_label": 'Créer'
                            }, 
                            # ACCESS FROM USER OUTOF ORG CHART
                            {
                                "menu_flag": "ressources_humaines_organization_all_users",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                                "action_is_standalone": False,
                                "action_hard_code_flag": 'dynamic_can_create_rbac_profil_action_flag',
                                "action_label": 'Créer'
                            }, 
                            # ACCESS FROM AGENT IN ORG CHART
                            {
                                "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                                "action_is_standalone": False,
                                "action_hard_code_flag": 'dynamic_can_create_rbac_profil_action_flag',
                                "action_label": 'Créer'
                            }, 
                            # ACCESS FROM USER IN PARAMETERS
                            # {
                            #     "menu_flag": "apps_settings_organization_all_users",
                            #     "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                            #     "action_is_standalone": False,
                            #     "action_hard_code_flag": 'dynamic_can_create_rbac_profil_action_flag',
                            #     "action_label": 'Créer'
                            # }, 
                        ],
                        "action_to_apps": []
                    },
                    "rbac_collection_meta_data_obj": {
                        "collection_meta_data_to_menus": {
                            "create_processing_url": [
                                {
                                    "hard_code_flag": "main",
                                    "rbac_endpoint": "/api/v1/static/data/org/create-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM ROLE UNDER ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_creation_process_url",
                                    "rbac_endpoint": "/api/v1/static/data/org/create-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM USER UNDER ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_creation_process_url",
                                    "rbac_endpoint": "/api/v1/static/data/org/create-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM USER OUTOF ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_creation_process_url",
                                    "rbac_endpoint": "/api/v1/static/data/org/create-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_all_users",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM AGENT IN ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_creation_process_url",
                                    "rbac_endpoint": "/api/v1/static/data/org/create-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM USER IN PARAMETERS
                                # {
                                #     "hard_code_flag": "rbac_profiles_creation_process_url",
                                #     "rbac_endpoint": "/api/v1/static/data/org/create-profile",
                                #     "is_sudo_action": False,
                                #     "is_sudo_group_action": False,
                                #     "menu_flag": "apps_settings_organization_all_users",
                                #     "is_parent_field_name": False,
                                # },
                            ],
                            "create_head_process_url": [
                                {
                                    "hard_code_flag": "main",
                                    "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                    "is_parent_field_name": False,
                                },
                                # ACCESS FROM ROLE UNDER ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_creation_head_process_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
                                    "is_parent_field_name": False,
                                },
                                # ACCESS FROM USER UNDER ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_creation_head_process_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
                                    "is_parent_field_name": False,
                                },
                                # ACCESS FROM USER OUTOF ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_creation_head_process_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_all_users",
                                    "is_parent_field_name": False,
                                },
                                # ACCESS FROM AGENT IN ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_creation_head_process_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                },
                                # ACCESS FROM USER IN PARAMETERS
                                # {
                                #     "hard_code_flag": "rbac_profiles_creation_head_process_url",
                                #     "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.RBAC_PROFILE.value}",
                                #     "is_sudo_action": False,
                                #     "is_sudo_group_action": False,
                                #     "menu_flag": "apps_settings_organization_all_users",
                                #     "is_parent_field_name": False,
                                # },
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
                'flag': "apps_ressources_humaines_updating_organization_organism_chart_profiles",
                "label": "Mise à jour d'un profil rbac sous l'arborescence de l'organigramme",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_profiles_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "rbac_standalone_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                                "action_is_standalone": True,
                                "action_hard_code_flag": 'table_action_update_flag',
                                "action_label": 'Modifier'
                            }
                        ],
                        "action_to_apps": []
                    },
                    "rbac_custom_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                                "action_is_standalone": False,
                                "action_hard_code_flag": 'custom_update_profil_permission_table_action_flag',
                                "action_label": 'Mettre à jour des permissions"'
                            },
                            {
                                "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                                "action_is_standalone": False,
                                "action_hard_code_flag": 'custom_extended_update_profil_permission_table_action_flag',
                                "action_label": 'Mettre à jour des permissions avancées"'
                            },
                            # ACCESS FROM ROLE UNDER ORG CHART
                            {
                                "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                                "action_is_standalone": False,
                                "action_hard_code_flag": 'dynamic_can_update_rbac_profil_action_flag',
                                "action_label": "Mettre à jour d'un profil"
                            },
                            # ACCESS FROM USER UNDER ORG CHART
                            {
                                "menu_flag": "ressources_humaines_organization_users_from_org_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                                "action_is_standalone": False,
                                "action_hard_code_flag": 'dynamic_can_update_rbac_profil_action_flag',
                                "action_label": "Mettre à jour d'un profil"
                            },
                            # ACCESS FROM USER OUTOF ORG CHART
                            {
                                "menu_flag": "ressources_humaines_organization_all_users",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                                "action_is_standalone": False,
                                "action_hard_code_flag": 'dynamic_can_update_rbac_profil_action_flag',
                                "action_label": "Mettre à jour d'un profil"
                            },
                            # ACCESS FROM AGENT IN ORG CHART
                            {
                                "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                                "action_is_standalone": False,
                                "action_hard_code_flag": 'dynamic_can_update_rbac_profil_action_flag',
                                "action_label": "Mettre à jour d'un profil"
                            },
                            # # ACCESS FROM USERS IN PARAMETERS
                            # {
                            #     "menu_flag": "apps_settings_organization_all_users",
                            #     "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                            #     "action_is_standalone": False,
                            #     "action_hard_code_flag": 'dynamic_can_update_rbac_profil_action_flag',
                            #     "action_label": "Mettre à jour d'un profil"
                            # },
                        ],
                        "action_to_apps": []
                    },
                    "rbac_collection_meta_data_obj": {
                        "collection_meta_data_to_menus": {
                            "update_processing_url": [
                                {
                                    "hard_code_flag": "main",
                                    "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "custom_profil_permission_update_process_url",
                                    "rbac_endpoint": "/api/v1/static/data/org/upsert-profile-permissions",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "custom_extended_profil_permission_update_process_url",
                                    "rbac_endpoint": "/api/v1/static/data/org/upsert-extended-profile-permissions",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM ROLE UNDER ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_update_process_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM USER UNDER ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_update_process_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM USER OUTOF ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_update_process_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_all_users",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM AGENT IN ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_update_process_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM USERS IN PARAMETERS
                                # {
                                #     "hard_code_flag": "rbac_profiles_update_process_url",
                                #     "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.RBAC_PROFILE.value}",
                                #     "is_sudo_action": False,
                                #     "is_sudo_group_action": False,
                                #     "menu_flag": "apps_settings_organization_all_users",
                                #     "is_parent_field_name": False,
                                #     "is_link_deleted": False,
                                # },
                            ],
                            "update_head_process_url": [
                                {
                                    "hard_code_flag": "custom_extended_profil_permission_update_head_process_url",
                                    "rbac_endpoint": "/api/v1/static/data/org/get-extended-profile-permissions",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "custom_profil_permission_update_head_process_url",
                                    "rbac_endpoint": "/api/v1/static/data/org/get-profile-permissions",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "main",
                                    "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM ROLE UNDER ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_update_head_process_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM USER UNDER ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_update_head_process_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM USER OUTOF ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_update_head_process_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_all_users",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM AGENT IN ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_update_head_process_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM USERS IN PARAMETERS
                                # {
                                #     "hard_code_flag": "rbac_profiles_update_head_process_url",
                                #     "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.RBAC_PROFILE.value}",
                                #     "is_sudo_action": False,
                                #     "is_sudo_group_action": False,
                                #     "menu_flag": "apps_settings_organization_all_users",
                                #     "is_parent_field_name": False,
                                #     "is_link_deleted": False,
                                # },
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
                'flag': "apps_ressources_humaines_deleting_organization_organism_chart_profiles",
                "label": "Suppression d'un profil rbac sous l'arborescence de l'organigramme",
                 "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_profiles_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "rbac_standalone_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                                "action_hard_code_flag": 'table_action_delete_flag',
                                "action_is_standalone": True,
                                "action_label": 'Supprimer'
                            },
                            {
                                "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                                "action_hard_code_flag": 'table_action_delete_flag',
                                "action_is_standalone": True,
                                "action_label": 'Supprimer'
                            },
                        ],
                        "action_to_apps": []
                    },
                    "rbac_custom_actions_obj": {
                        "action_to_menus": [
                            # ACCESS FROM ROLE UNDER ORG CHART
                            {
                                "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                                "action_hard_code_flag": 'dynamic_can_delete_rbac_profil_action_flag',
                                "action_is_standalone": False,
                                "action_label": 'Supprimer un profil RBAC'
                            },
                            # ACCESS FROM USER UNDER ORG CHART
                            {
                                "menu_flag": "ressources_humaines_organization_users_from_org_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                                "action_hard_code_flag": 'dynamic_can_delete_rbac_profil_action_flag',
                                "action_is_standalone": False,
                                "action_label": 'Supprimer un profil RBAC'
                            },
                            # ACCESS FROM USER OUTOF ORG CHART
                            {
                                "menu_flag": "ressources_humaines_organization_all_users",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                                "action_hard_code_flag": 'dynamic_can_delete_rbac_profil_action_flag',
                                "action_is_standalone": False,
                                "action_label": 'Supprimer un profil RBAC'
                            },
                            # ACCESS FROM AGENT IN ORG CHART
                            {
                                "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                                "action_hard_code_flag": 'dynamic_can_delete_rbac_profil_action_flag',
                                "action_is_standalone": False,
                                "action_label": 'Supprimer un profil RBAC'
                            },
                            # # ACCESS FROM USERS IN PARAMETERS
                            # {
                            #     "menu_flag": "apps_settings_organization_all_users",
                            #     "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                            #     "action_hard_code_flag": 'dynamic_can_delete_rbac_profil_action_flag',
                            #     "action_is_standalone": False,
                            #     "action_label": 'Supprimer un profil RBAC'
                            # },
                        ],
                        "action_to_apps": []
                    },
                    "rbac_collection_meta_data_obj": {
                        "collection_meta_data_to_menus": {
                            "delete_processing_url": [
                                {
                                    "hard_code_flag": "main",
                                    "rbac_endpoint": "/api/v1/static/data/org/delete-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_profiles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM ROLE UNDER ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_delete_process_url",
                                    "rbac_endpoint": "/api/v1/static/data/org/delete-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM USER UNDER ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_delete_process_url",
                                    "rbac_endpoint": "/api/v1/static/data/org/delete-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_users_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM USER OUTOF ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_delete_process_url",
                                    "rbac_endpoint": "/api/v1/static/data/org/delete-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_all_users",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM AGENT IN ORG CHART
                                {
                                    "hard_code_flag": "rbac_profiles_delete_process_url",
                                    "rbac_endpoint": "/api/v1/static/data/org/delete-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_agents_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                # ACCESS FROM USERS IN PARAMETERS
                                # {
                                #     "hard_code_flag": "rbac_profiles_delete_process_url",
                                #     "rbac_endpoint": "/api/v1/static/data/org/delete-profile",
                                #     "is_sudo_action": False,
                                #     "is_sudo_group_action": False,
                                #     "menu_flag": "apps_settings_organization_all_users",
                                #     "is_parent_field_name": False,
                                #     "is_link_deleted": False,
                                # },
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
        ],
        "endpoints": [
            {
                "label": "Chargement des profils rbac",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/fetch/{CollectionKey.RBAC_PROFILE.value}"
            },
            {
                "label": "Chargement d'un noeud de l'organigramme",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/fetch-one/{CollectionKey.CFG_ORGANISM_CHART.value}"
            },
            {
                "label": "Chargement du profil principal d'une organisation",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/organizations/fetch-main-profile"
            },
            {
                "label": "Création d'un profil rbac",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/org/create-profile"
            },
            {
                "label": "Chargement du formulaire de création d'un profil rbac",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/head/{CollectionKey.RBAC_PROFILE.value}"
            },
            {
                "label": "Mise à jour d'un profil rbac",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/update/{CollectionKey.RBAC_PROFILE.value}"
            },
            {
                "label": "Mise à jour des permissions d'un profil",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/org/upsert-profile-permissions"
            },
            {
                "label": "Mise à jour des permissions avancées d'un profil",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/org/upsert-extended-profile-permissions"
            },
            {
                "label": "Chargement des permissions avancées d'un profil",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/org/get-extended-profile-permissions"
            },
            {
                "label": "Chargement des permissions d'un profil",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/org/get-profile-permissions"
            },
            {
                "label": "Chargement du formulaire de mise à jour d'un profil rbac",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/update-head/{CollectionKey.RBAC_PROFILE.value}"
            },
            {
                "label": "Suppression d'un profil rbac",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/org/delete-profile"
            },
        ],

    },
    {
        "label": "Rôles",
        "flag": "apps_ressources_humaines_organization_organism_organism_chart_roles_flag",
        "is_default": False,
        "children": [],
        "permissions": [

            {
                'flag': "apps_ressources_humaines_loading_organization_organism_chart_roles",
                "label": "Chargement des rôles sous l'arborescence de l'organigramme",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_roles_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "fetch_rbac_profiles_url",
                                    "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.RBAC_PROFILE.value}",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "hard_code_flag": "fetch_organization_main_profil_url",
                                    "rbac_endpoint": "/api/v1/organizations/fetch-main-profile",
                                    "is_sudo_action": False,
                                    "is_sudo_group_action": False,
                                    "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
                                    "is_parent_field_name": False,
                                    "is_link_deleted": False,
                                }
                            ],
                        },

                    }
                }
    
            },
            {
                'flag': "apps_ressources_humaines_creating_organization_organism_chart_roles",
                "label": "Création d'un nouveau rôle sous l'arborescence de l'organigramme",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_roles_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "rbac_standalone_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
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
                'flag': "apps_ressources_humaines_updating_organization_organism_chart_roles",
                "label": "Mise à jour d'un rôle sous l'arborescence de l'organigramme",
                "core_seeds": {
                    "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_roles_from_org_chart",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "rbac_standalone_actions_obj": {
                        "action_to_menus": [
                            {
                                "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
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
                'flag': "apps_ressources_humaines_deleting_organization_organism_chart_roles",
                "label": "Suppression d'un rôle sous l'arborescence de l'organigramme",
                 "core_seeds": {
                   "restricted_profil_list": [
                        *MAIN_PROFILE_IN_ONE,
                    ],
                    "restricted_api_consumer_list": [
                        *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                    ],
                    "rbac_roles_list": [
                        *TRANS_ADMIN_ROLE_IN_ONE,
                        *TRANS_RH_ROLE_IN_ONE, 
                    ],
                    "sys_apps_list": [
                        {
                            "flag": "ressources_humaines",
                            "is_link_activated": True,
                            "is_link_hidden": False,
                            "is_link_locked": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "sys_menus_list": [
                        {
                            "flag": "ressources_humaines_organization_roles_from_org_chart",
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
                                "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
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
                                    "menu_flag": "ressources_humaines_organization_roles_from_org_chart",
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
        ],
        "endpoints": [
            {
                "label": "Chargement des rôles",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/fetch/{CollectionKey.RBAC_ROLE.value}"
            },
             
            {
                "label": "Création des rôles",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/org/create-role"
            },
            {
                "label": "Suppression des rôles",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/org/delete-role"
            },
            {
                "label": "Chargement du formulaire de création des rôles",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/head/{CollectionKey.RBAC_ROLE.value}"
            },
            # {
            #     "label": "Création des rôles",
            #     "is_leaf": True,
            # "is_link_deleted": False,
            #     "url": "/api/v1/static/data/org/create-role"
            # },
            {
                "label": "Suppression des rôles",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.RBAC_ROLE.value}"
            },
            {
                "label": "Mise à jour des rôles",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/update/{CollectionKey.RBAC_ROLE.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour des rôles",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/update-head/{CollectionKey.RBAC_ROLE.value}"
            },

            {
                "label": "Chargement des permissions d'un rôle",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/org/get-role-permissions"
            },
            {
                "label": "Mise à jour des permissions d'un rôle",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/org/update-role-permissions"
            },
        ],

    },
    {
        "label": "Grades",
        "flag": "apps_ressources_humaines_organization_grades_flag",
        "is_default": False,
        "children": [],
        "permissions": [
            *RH_GRADE_PERMISSION_RBAC_TITLE_DB
        ],
        "endpoints": [
            {
                "label": "Chargement des grades",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/fetch/{CollectionKey.CFG_GRADE.value}"
            }, 
            {
                "label": "Création d'un grade",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/add/{CollectionKey.CFG_GRADE.value}"
            },
            {
                "label": "Chargement du formulaire de création d'un grade",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/head/{CollectionKey.CFG_GRADE.value}"
            },
            {
                "label": "Suppression d'un grade",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_GRADE.value}"
            },
            {
                "label": "Mise à jour d'un grade",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/update/{CollectionKey.CFG_GRADE.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour d'un grade",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/update-head/{CollectionKey.CFG_GRADE.value}"
            }, 
        ],
    },
    {
        "label": "Fonctions",
        "flag": "apps_ressources_humaines_organization_fonctions_flag",
        "is_default": False,
        "children": [],
        "permissions": [
            *RH_FONCTION_PERMISSION_RBAC_TITLE_DB
        ],
        "endpoints": [
            {
                "label": "Chargement des fonctions",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/fetch/{CollectionKey.CFG_FUNCTION.value}"
            }, 
            {
                "label": "Création d'une fonction",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/add/{CollectionKey.CFG_FUNCTION.value}"
            },
            {
                "label": "Chargement du formulaire de création d'une fonction",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/head/{CollectionKey.CFG_FUNCTION.value}"
            },
            {
                "label": "Suppression d'une fonction",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_FUNCTION.value}"
            },
            {
                "label": "Mise à jour d'une fonction",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/update/{CollectionKey.CFG_FUNCTION.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour d'une fonction",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/org/update-head/{CollectionKey.CFG_FUNCTION.value}"
            }, 
        ],
    },

]
