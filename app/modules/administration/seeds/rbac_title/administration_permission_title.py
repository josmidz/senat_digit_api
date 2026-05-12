from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.auth.enums.common import ERbacActionFlag, ERbacComponentFlag
from app.modules.administration.seeds.rbac_title.administration_details_permission_title import ADMINISTRATION_ORGANIZATION_DETAILS_PERMISSION_RBAC_TITLE_DB
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.common import SENAT_DIGIT_ADMIN_WEB_IN_ONE, SYSTEM_ORGANIZATION_PROFIL_IN_ONE, SYSTEM_SUPER_ADMIN_ROLE_IN_ONE, TEST_ADMIN_ROLE_IN_ONE, TRANS_ADMIN_ROLE_IN_ONE, MAIN_PROFILE_IN_ONE


ADMINISTRATION_PERMISSION_RBAC_TITLE_DB = [
            {
                "label": "Organisations",
                "flag": "administrations_organisation_flag",
                "is_default": False,
                "children": [
                    {
                        "label": "Détails de l'organisation",
                        "flag": "administrations_organization_details_flag",
                        "is_default": False,
                        "children": [],
                        "permissions": [
                            *ADMINISTRATION_ORGANIZATION_DETAILS_PERMISSION_RBAC_TITLE_DB
                        ],
                        "endpoints": [],
                    }
                ],
                "permissions": [
                    {
                        'flag': "system_loading_saas_organizations",
                        "label": "[system] Chargement des organisations",
                        "core_seeds": {
                            "restricted_profil_list": [
                                *SYSTEM_ORGANIZATION_PROFIL_IN_ONE,
                            ],
                            "restricted_api_consumer_list": [
                                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                            ],
                            "rbac_roles_list": [
                                *SYSTEM_SUPER_ADMIN_ROLE_IN_ONE
                            ],
                            "sys_apps_list": [
                                {
                                    "flag": "administrations",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                }
                            ],
                            "sys_menus_list": [ 
                                {
                                    "flag": "administrations_organizations_page",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                },
                                {
                                    "flag": "administrations_organization_details_page",
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
                            "rbac_custom_components_obj": {
                                "component_to_menus": [
                                    {
                                        "menu_flag": "administrations_organizations_page",
                                        "component_flag": ERbacComponentFlag.DATA_LIST_COMPONENT.value,
                                        "component_is_standalone": False,
                                        "component_hard_code_flag": 'system_only_organization_list_component_flag',
                                        "component_label": "Composant pour la liste des organisations"
                                    }
                                ],
                                "component_to_apps": []
                            },
                            "rbac_collection_meta_data_obj": {
                                "collection_meta_data_to_menus": {
                                    "fetch_url": [
                                        {
                                            "hard_code_flag": "main",
                                            "rbac_endpoint": "/api/v1/organizations/fetch/org",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organizations_page",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                        {
                                            "hard_code_flag": "main",
                                            "rbac_endpoint": "/api/v1/organizations/fetch/org-details",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organization_details_page",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                        # fetch entities
                                        {
                                            "hard_code_flag": "fetch_entities_url",
                                            "rbac_endpoint": f"/api/v1/generic/fetch/{CollectionKey.REF_ENTITY.value}",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organizations_page",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                        # fetch profiles
                                        {
                                            "hard_code_flag": "fetch_profiles_url",
                                            "rbac_endpoint": f"/api/v1/generic/fetch/{CollectionKey.RBAC_PROFILE.value}",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organizations_page",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                        # search organization
                                        {
                                            "hard_code_flag": "search_organization_process_url",
                                            "rbac_endpoint": "/api/v1/organizations/search-org",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organizations_page",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                         
                                        {
                                            "hard_code_flag": "fetch_organization_available_profiles_url",
                                            "rbac_endpoint": "/api/v1/organizations/fetch/organization-available-profiles",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organizations_page",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        }, 
                                         
                                    ],
                                    "patch_processing_url": [ ]
                                },

                            }
                        }
    
                    },
                    {
                        'flag': "org_loading_own_organization_info",
                        "label": "Chargement des infos de l'organisation",
                        "core_seeds": {
                            "restricted_profil_list": [
                                *MAIN_PROFILE_IN_ONE,
                            ],
                            "restricted_api_consumer_list": [
                                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                            ],
                            "rbac_roles_list": [
                                *TRANS_ADMIN_ROLE_IN_ONE
                            ],
                            "sys_apps_list": [
                                {
                                    "flag": "administrations",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                }
                            ],
                            "sys_menus_list": [ 
                                {
                                    "flag": "administrations_organizations_page",
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
                            "rbac_custom_components_obj": {
                                "component_to_menus": [
                                    {
                                        "menu_flag": "administrations_organizations_page",
                                        "component_flag": ERbacComponentFlag.OWN_INFO_COMPONENT.value,
                                        "component_is_standalone": False,
                                        "component_hard_code_flag": 'own_organization_info_component_flag',
                                        "component_label": "Composant pour les infos de l'organisation",
                                        "is_link_deleted": False,
                                    }
                                ],
                                "component_to_apps": []
                            },
                            "rbac_collection_meta_data_obj": {
                                "collection_meta_data_to_menus": {
                                    "fetch_one_info_url": [
                                        {
                                            "hard_code_flag": "main",
                                            "rbac_endpoint": "/api/v1/organizations/fetch/own-info",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organizations_page",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        }
                                    ],
                                },

                            }
                        }
    
                    },
                    {
                        'flag': "system_deleting_saas_organization",
                        "label": "[system] Suppression des organisations",
                         "core_seeds": {
                            "restricted_profil_list": [
                                {
                                    "flag": ESysProfileFlag.TEST_SYS_PROFIL.value,
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "restricted_api_consumer_list": [
                                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                            ],
                            "rbac_roles_list": [
                                *TEST_ADMIN_ROLE_IN_ONE
                            ],
                            "sys_apps_list": [
                                {
                                    "flag": "administrations",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                }
                            ],
                            "sys_menus_list": [ 
                                {
                                    "flag": "administrations_organizations_page",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "rbac_standalone_actions_obj": {
                                "action_to_menus": [
                                    {
                                        "menu_flag": "administrations_organizations_page",
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
                                            "rbac_endpoint": "/api/v1/organizations/hard-delete/org",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organizations_page",
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
                        'flag': "system_creating_saas_organizations",
                        "label": "[system] Création d'une nouvelle organisation",
                        "core_seeds": {
                            "restricted_profil_list": [
                                *SYSTEM_ORGANIZATION_PROFIL_IN_ONE,
                            ],
                            "restricted_api_consumer_list": [
                                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                            ],
                            "rbac_roles_list": [
                                *SYSTEM_SUPER_ADMIN_ROLE_IN_ONE
                            ],
                            "sys_apps_list": [
                                {
                                    "flag": "administrations",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                }
                            ],
                            "sys_menus_list": [ 
                                {
                                    "flag": "administrations_organizations_page",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "rbac_standalone_actions_obj": {
                                "action_to_menus": [
                                    {
                                        "menu_flag": "administrations_organizations_page",
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
                                    "update_processing_url": [ 
                                        {
                                            "hard_code_flag": "upload_organization_logo_process_url",
                                            "rbac_endpoint": "/api/v1/organizations/upload-logo",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organizations_page",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },

                                    ],
                                    "create_processing_url": [
                                        {
                                            "hard_code_flag": "main",
                                            "rbac_endpoint": "/api/v1/organizations/add/org",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organizations_page",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                    ],
                                    "create_head_process_url": [
                                        {
                                            "hard_code_flag": "main",
                                            "rbac_endpoint": "/api/v1/organizations/head/org",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organizations_page",
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
                        'flag': "system_update_saas_organizations",
                        "label": "[system] Mise à jour d'une organisation",
                         "core_seeds": {
                            "restricted_profil_list": [ 
                                {
                                    "flag": ESysProfileFlag.TEST_SYS_PROFIL.value,
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "restricted_api_consumer_list": [
                               *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                            ],
                            "rbac_roles_list": [  
                                *TEST_ADMIN_ROLE_IN_ONE
                            ],
                            "sys_apps_list": [
                                {
                                    "flag": "administrations",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                }
                            ],
                            "sys_menus_list": [ 
                                {
                                    "flag": "administrations_organizations_page",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "rbac_standalone_actions_obj": {
                                "action_to_menus": [
                                    {
                                        "menu_flag": "administrations_organizations_page",
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
                                            "rbac_endpoint": "/api/v1/organizations/update/org",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organizations_page",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                        {
                                            "hard_code_flag": "upload_organization_logo_process_url",
                                            "rbac_endpoint": "/api/v1/organizations/upload-logo",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organizations_page",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },

                                    ],
                                    "update_head_process_url": [
                                        {
                                            "hard_code_flag": "main",
                                            "rbac_endpoint": "/api/v1/organizations/update-head/org",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organizations_page",
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
                        'flag': "system_generating_organization_password_reset_link",
                        "label": "[system] Générer le lien de réinitialisation du mot de passe pour une organisation",
                         "core_seeds": {
                            "restricted_profil_list": [
                                *SYSTEM_ORGANIZATION_PROFIL_IN_ONE,
                            ],
                            "restricted_api_consumer_list": [
                                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                            ],
                            "rbac_roles_list": [
                                *SYSTEM_SUPER_ADMIN_ROLE_IN_ONE
                            ],
                            "sys_apps_list": [
                                {
                                    "flag": "administrations",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                }
                            ],
                            "sys_menus_list": [ 
                                {
                                    "flag": "administrations_organizations_page",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "rbac_standalone_actions_obj": {
                                "action_to_menus": [
                                     {
                                        "menu_flag": "administrations_organizations_page",
                                        "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                                        "action_is_standalone": True,
                                        "action_hard_code_flag": 'custom_generate_initpassword_link_action_unlock_flag',
                                        "action_label": 'Générer le lien de réinitialisation du mot de passe'
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
                                            "hard_code_flag": "password_reset_link_generation_process_url",
                                            "rbac_endpoint": "/api/v1/organizations/generate-reset-password-link",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organizations_page",
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
                        "label": "Chargement des applications d'une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/organizations/fetch/profile-application-access"
                    },
                    {
                        "label": "Mettre à jour l'access des applications d'une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/organizations/patch/profile-application-access"
                    },
                    {
                        "label": "Updater les permissions d'un profil",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/cores/upsert-profile-permissions"
                    },
                    {
                        "label": "Updater les permissions d'un profil",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/cores/upsert-extended-profile-permissions"
                    },
                    {
                        "label": "Recherche des organisations",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/search-org"
                    },
                    {
                        "label": "Chargement des profils disponibles pour une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/organization-available-profiles"
                    },
                    {
                        "label": "Chargement des profils liés à une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/organization-related-profiles"
                    },
                    {
                        "label": "Ajout ou suppression d'un groupe d'application liée à une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/patch/add-remove-organization-application-group"
                    },
                    {
                        "label": "Ajout ou suppression d'un profil liée à une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/patch/add-remove-organization-profile"
                    },
                    {
                        "label": "Chargement des utilisateurs d'une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/organization-users"
                    },
                    {
                        "label": "Chargement des groupes d'applications",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/application-groups"
                    },
                    {
                        "label": "Chargement des groupes d'applications liés à une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/linked-application-groups"
                    },
                    {
                        "label": "Génération du lien de réinitialisation du mot de passe pour une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/generate-reset-password-link"
                    },
                    {
                        "label": "Chargement des branches d'une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/organization-branches"
                    },
                    {
                        "label": "Chargement des portefeuilles électroniques liés à une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/organization-related-ewallet"
                    },
                    {
                        "label": "Chargement des commissions retro d'une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/retro-commissions"
                    },
                    {
                        "label": "Ajout d'une commission retro à une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/add/retro-commission"
                    },
                    {
                        "label": "Mise à jour d'une commission retro d'une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/patch/retro-commission"
                    },
                    {
                        "label": "Chargement des infos d'un e-wallet",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/ewallet-info"
                    },
                    {
                        "label": "Chargement des tarifications personnalisées d'une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/custom-tarifications"
                    },
                    {
                        "label": "Ajout ou suppression d'une clé d'application liée à une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/patch/add-remove-organization-application-key"
                    },
                    {
                        "label": "Chargement des clés d'application liées à une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/organization-application-keys"
                    },


                    # SMS COVERAGE
                    {
                        "label": "Ajout ou suppression d'un sms coverage liée à une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/patch/add-remove-organization-sms-coverage"
                    },
                    {
                        "label": "Chargement des sms coverage liés à une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/organization-sms-coverage"
                    },


                    # FONDS
                    {
                        "label": "Créditer/débiter un ewallet de fonds",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/patch/credit-debit-fund-ewallet"
                    },
                    {
                        "label": "Chargement des historiques de fonds d'une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/organization-funds-histories"
                    }, 



                    {
                        "label": "Téléversement du logo de l'organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/upload-logo"
                    }, 
                    {
                        "label": "Création d'une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/add/org"
                    }, 
                    {
                        "label": "Chargement du profil principal d'une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch-main-profile"
                    }, 
                    {
                        "label": "Chargement du compte utilisateur d'un agent",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/static/org/get-agent-user-account"
                    }, 
                    {
                        "label": "Chargement des infos d'un utilisateur",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch-single-user-info"
                    }, 
                    {
                        "label": "Mise à jour d'une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/update/org"
                    }, 
                    
                    {
                        "label": "Chargement du formulaire de création d'une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/head/org"
                    }, 

                    {
                        "label": "Chargement du formulaire de mise à jour d'une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/update-head/org"
                    }, 
                     
                    {
                        "label": "Suppression d'une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/hard-delete/org"
                    }, 
                    {
                        "label": "Chargement des organisations",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/org"
                    }, 
                    
                    {
                        "label": "Chargement des détails d'une organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/org-details"
                    }, 

                    {
                        "label": "Chargement des infos de l'organisation",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/own-info"
                    }, 
                ],
            },
            {
                "label": "Succursales",
                "flag": "administrations_organisation_branches_flag",
                "is_default": False,
                "children": [],
                "permissions": [
                    {
                        'flag': "loading_organization_branches",
                        "label": "Chargement des succursales de l'organisation",
                        "core_seeds": {
                            "restricted_profil_list": [
                                *MAIN_PROFILE_IN_ONE,
                            ],
                            "restricted_api_consumer_list": [
                                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                            ],
                            "rbac_roles_list": [
                                *TRANS_ADMIN_ROLE_IN_ONE
                            ],
                            "sys_apps_list": [
                                {
                                    "flag": "administrations",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                }
                            ],
                            "sys_menus_list": [ 
                                {
                                    "flag": "administrations_succursales",
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
                            "rbac_custom_components_obj": {
                                "component_to_menus": [],
                                "component_to_apps": []
                            },
                            "rbac_collection_meta_data_obj": {
                                "collection_meta_data_to_menus": {
                                    "fetch_url": [
                                        {
                                            "hard_code_flag": "main",
                                            "rbac_endpoint": "/api/v1/organizations/fetch/org-branches",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_succursales",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                        {
                                            "hard_code_flag": "search_organization_branch_process_url",
                                            "rbac_endpoint": "/api/v1/organizations/search-branches",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_succursales",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                        # fetch entities
                                        {
                                            "hard_code_flag": "fetch_entities_url",
                                            "rbac_endpoint": f"/api/v1/generic/fetch/{CollectionKey.REF_ENTITY.value}",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_succursales",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                        # fetch profiles
                                        {
                                            "hard_code_flag": "fetch_org_profiles_url",
                                            "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.RBAC_PROFILE.value}",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_organizations_page",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                    ],
                                },

                            }
                        }
    
                    },
                    {
                        'flag': "deleting_organization_branches",
                        "label": "Suppression des succursales",
                         "core_seeds": {
                            "restricted_profil_list": [
                                *MAIN_PROFILE_IN_ONE,
                            ],
                            "restricted_api_consumer_list": [
                                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                            ],
                            "rbac_roles_list": [
                                *TRANS_ADMIN_ROLE_IN_ONE
                            ],
                            "sys_apps_list": [
                                {
                                    "flag": "administrations",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                }
                            ],
                            "sys_menus_list": [ 
                                {
                                    "flag": "administrations_succursales",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "rbac_standalone_actions_obj": {
                                "action_to_menus": [
                                    {
                                        "menu_flag": "administrations_succursales",
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
                                            "rbac_endpoint": "/api/v1/organizations/hard-delete/org-branches",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_succursales",
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
                        'flag': "creating_organization_branches",
                        "label": "Création d'une nouvelle succursale",
                         "core_seeds": {
                            "restricted_profil_list": [
                                *MAIN_PROFILE_IN_ONE,
                            ],
                            "restricted_api_consumer_list": [
                                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                            ],
                            "rbac_roles_list": [
                                *TRANS_ADMIN_ROLE_IN_ONE
                            ],
                            "sys_apps_list": [
                                {
                                    "flag": "administrations",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                }
                            ],
                            "sys_menus_list": [ 
                                {
                                    "flag": "administrations_succursales",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "rbac_standalone_actions_obj": {
                                "action_to_menus": [
                                    {
                                        "menu_flag": "administrations_succursales",
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
                                            "rbac_endpoint": "/api/v1/organizations/fetch/org-branches",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_succursales",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                        {
                                            "hard_code_flag": "search_organization_branch_process_url",
                                            "rbac_endpoint": "/api/v1/organizations/search-branches",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_succursales",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                        # fetch entities
                                        {
                                            "hard_code_flag": "fetch_entities_url",
                                            "rbac_endpoint": f"/api/v1/generic/fetch/{CollectionKey.REF_ENTITY.value}",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_succursales",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                        # fetch profiles
                                        {
                                            "hard_code_flag": "fetch_org_profiles_url",
                                            "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.RBAC_PROFILE.value}",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_succursales",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                    ],
                                    "update_processing_url": [ 
                                        {
                                            "hard_code_flag": "upload_organization_logo_process_url",
                                            "rbac_endpoint": "/api/v1/organizations/upload-logo",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_succursales",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },

                                    ],
                                    "create_processing_url": [
                                        {
                                            "hard_code_flag": "main",
                                            "rbac_endpoint": "/api/v1/organizations/add/org-branches",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_succursales",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                    ],
                                    "create_head_process_url": [
                                        {
                                            "hard_code_flag": "main",
                                            "rbac_endpoint": "/api/v1/organizations/head/org-branches",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_succursales",
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
                        'flag': "updating_organization_branches",
                        "label": "Mise à jour d'une succursale",
                        "core_seeds": {
                            "restricted_profil_list": [
                                *MAIN_PROFILE_IN_ONE,
                            ],
                            "restricted_api_consumer_list": [
                                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                            ],
                            "rbac_roles_list": [
                                *TRANS_ADMIN_ROLE_IN_ONE
                            ],
                            "sys_apps_list": [
                                {
                                    "flag": "administrations",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                }
                            ],
                            "sys_menus_list": [ 
                                {
                                    "flag": "administrations_succursales",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "rbac_standalone_actions_obj": {
                                "action_to_menus": [
                                    {
                                        "menu_flag": "administrations_succursales",
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
                                            "rbac_endpoint": "/api/v1/organizations/update/org-branches",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_succursales",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },
                                        {
                                            "hard_code_flag": "upload_organization_logo_process_url",
                                            "rbac_endpoint": "/api/v1/organizations/upload-logo",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_succursales",
                                            "is_parent_field_name": False,
                                            "is_link_deleted": False,
                                        },

                                    ],
                                    "update_head_process_url": [
                                        {
                                            "hard_code_flag": "main",
                                            "rbac_endpoint": "/api/v1/organizations/update-head/org-branches",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_succursales",
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
                        'flag': "generating_organization_branches_password_reset_link",
                        "label": "Générer le lien de la réinitialisation du mot de passe pour une succursale",
                        "core_seeds": {
                            "restricted_profil_list": [
                                *MAIN_PROFILE_IN_ONE,
                            ],
                            "restricted_api_consumer_list": [
                                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                            ],
                            "rbac_roles_list": [
                                *TRANS_ADMIN_ROLE_IN_ONE
                            ],
                            "sys_apps_list": [
                                {
                                    "flag": "administrations",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                }
                            ],
                            "sys_menus_list": [ 
                                {
                                    "flag": "administrations_succursales",
                                    "is_link_activated": True,
                                    "is_link_hidden": False,
                                    "is_link_locked": False,
                                    "is_link_deleted": False,
                                },
                            ],
                            "rbac_standalone_actions_obj": {
                                "action_to_menus": [
                                    {
                                        "menu_flag": "administrations_succursales",
                                        "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                                        "action_is_standalone": True,
                                        "action_hard_code_flag": 'custom_generate_initpassword_link_action_unlock_flag',
                                        "action_label": 'Générer le lien de réinitialisation du mot de passe'
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
                                            "hard_code_flag": "password_reset_link_generation_process_url",
                                            "rbac_endpoint": "/api/v1/organizations/generate-reset-password-link",
                                            "is_sudo_action": False,
                                            "is_sudo_group_action": False,
                                            "menu_flag": "administrations_succursales",
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
                        "label": "Recherche des succursales",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/search-branches"
                    },
                    {
                        "label": "Chargement des succursales",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/fetch/org-branches"
                    },
                    {
                        "label": "Chargement du formulaire de création d'une succursale",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/head/org-branches"
                    },
                    {
                        "label": "Création d'une succursale",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/add/org-branches"
                    }, 
                    {
                        "label": "Suppression d'une succursale",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/hard-delete/org-branches"
                    }, 
                    {
                        "label": "Mise à jour d'une succursale",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/update/org-branches"
                    }, 
                    {
                        "label": "Chargement du formulaire de Mise à jour d'une succursale",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/organizations/update-head/org-branches"
                    }, 
                ],
            },

            # PROFIL RBAC
             {
                "label": "Profil RBAC System",
                "flag": "administrations_system_rbac_profiles_flag",
                "is_default": False,
                "children": [],
                "permissions": [
                    # {
                    #     'flag': "loading_system_rbac_profile",
                    #     "label": "Chargement des profils RBAC System",
                    #     "core_seeds": {
                    #         "restricted_profil_list": [
                    #              {
                    #                     "flag": ESysProfileFlag.SYSTEM_PROFIL,
                    #                     "is_link_activated": True,
                    #                     "is_link_hidden": False,
                    #                     "is_link_locked": False,
                    #                     "is_link_deleted": False,
                    #             }, 
                    #             {
                    #                 "flag": ESysProfileFlag.TEST_SYS_PROFIL.value,
                    #                 "is_link_activated": True,
                    #                 "is_link_hidden": False,
                    #                 "is_link_locked": False,
                    #                 "is_link_deleted": False,
                    #             },
                    #         ],
                    #         "restricted_api_consumer_list": [
                    #             {
                    #                 "flag": EApiConsumerFlag.ANGULAR_SENAT_DIGIT_ADMIN_WEB_APP.value,
                    #                 "is_link_activated": True,
                    #                 "is_link_hidden": False,
                    #                 "is_link_locked": False,
                    #                 "is_link_deleted": False,
                    #             }
                    #         ],
                    #         "rbac_roles_list": [
                    #             {
                    #                     "flag": ESysProfilSuperUserRoleFlag.SYSTEM_PROFIL_SUPER_ADMIN,
                    #                     "is_link_activated": True,
                    #                     "is_link_hidden": False,
                    #                     "is_link_locked": False,
                    #                     "is_link_deleted": False,
                    #                 }, 
                    #                 {
                    #                     "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN,
                    #                     "is_link_activated": True,
                    #                     "is_link_hidden": False,
                    #                     "is_link_locked": False,
                    #                     "is_link_deleted": False,
                    #                 }, 
                    #         ],
                    #         "sys_apps_list": [
                    #             {
                    #                 "flag": "administrations",
                    #                 "is_link_activated": True,
                    #                 "is_link_hidden": False,
                    #                 "is_link_locked": False,
                    #                 "is_link_deleted": False,
                    #             }
                    #         ],
                    #         "sys_menus_list": [ 
                    #             {
                    #                 "flag": "administrations_system_rbac_profiles",
                    #                 "is_link_activated": True,
                    #                 "is_link_hidden": False,
                    #                 "is_link_locked": False,
                    #                 "is_link_deleted": False,
                    #             },
                    #         ],
                    #         "rbac_standalone_actions_obj": {
                    #             "action_to_menus": [],
                    #             "action_to_apps": []
                    #         },
                    #         "rbac_custom_actions_obj": {
                    #             "action_to_menus": [],
                    #             "action_to_apps": []
                    #         },
                    #         "rbac_custom_components_obj": {
                    #             "component_to_menus": [],
                    #             "component_to_apps": []
                    #         },
                    #         "rbac_collection_meta_data_obj": {
                    #             "collection_meta_data_to_menus": {
                    #                 "fetch_url": [
                    #                     {
                    #                         "hard_code_flag": "main",
                    #                         "rbac_endpoint": f"/api/v1/generic/fetch/{CollectionKey.RBAC_PROFILE.value}",
                    #                         "is_sudo_action": False,
                    #                         "is_sudo_group_action": False,
                    #                         "menu_flag": "administrations_system_rbac_profiles",
                    #                         "is_parent_field_name": False,
                    #                         "is_link_deleted": False,
                    #                     },
                    #                     {
                    #                         "hard_code_flag": "fetch_profil_application_access_process_url",
                    #                         "rbac_endpoint": f"/api/v1/organizations/fetch/profile-application-access",
                    #                         "is_sudo_action": False,
                    #                         "is_sudo_group_action": False,
                    #                         "menu_flag": "administrations_system_rbac_profiles",
                    #                         "is_parent_field_name": False,
                    #                         "is_link_deleted": False,
                    #                     }
                    #                 ],
                    #             },

                    #         }
                    #     }
    
                    # },
                    # {
                    #     'flag': "deleting_system_rbac_profile",
                    #     "label": "Suppression des profils RBAC System",
                    #      "core_seeds": {
                    #         "restricted_profil_list": [
                    #              {
                    #                     "flag": ESysProfileFlag.SYSTEM_PROFIL,
                    #                     "is_link_activated": True,
                    #                     "is_link_hidden": False,
                    #                     "is_link_locked": False,
                    #                     "is_link_deleted": False,
                    #             },  
                    #                 {
                    #                     "flag": ESysProfileFlag.TEST_SYS_PROFIL.value,
                    #                     "is_link_activated": True,
                    #                     "is_link_hidden": False,
                    #                     "is_link_locked": False,
                    #                     "is_link_deleted": False,
                    #                 },
                    #         ],
                            
                    #         "restricted_api_consumer_list": [
                    #             {
                    #                 "flag": EApiConsumerFlag.ANGULAR_SENAT_DIGIT_ADMIN_WEB_APP.value,
                    #                 "is_link_activated": True,
                    #                 "is_link_hidden": False,
                    #                 "is_link_locked": False,
                    #                 "is_link_deleted": False,
                    #             }
                    #         ],
                    #         "rbac_roles_list": [
                    #              {
                    #                     "flag": ESysProfilSuperUserRoleFlag.SYSTEM_PROFIL_SUPER_ADMIN,
                    #                     "is_link_activated": True,
                    #                     "is_link_hidden": False,
                    #                     "is_link_locked": False,
                    #                     "is_link_deleted": False,
                    #                 }, 
                    #                 {
                    #                     "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN,
                    #                     "is_link_activated": True,
                    #                     "is_link_hidden": False,
                    #                     "is_link_locked": False,
                    #                     "is_link_deleted": False,
                    #                 }, 
                    #         ],
                            
                    #         "sys_apps_list": [
                    #             {
                    #                 "flag": "administrations",
                    #                 "is_link_activated": True,
                    #                 "is_link_hidden": False,
                    #                 "is_link_locked": False,
                    #                 "is_link_deleted": False,
                    #             }
                    #         ],
                    #         "sys_menus_list": [ 
                    #             {
                    #                 "flag": "administrations_system_rbac_profiles",
                    #                 "is_link_activated": True,
                    #                 "is_link_hidden": False,
                    #                 "is_link_locked": False,
                    #                 "is_link_deleted": False,
                    #             },
                    #         ],
                    #         "rbac_standalone_actions_obj": {
                    #             "action_to_menus": [
                    #                 {
                    #                     "menu_flag": "administrations_system_rbac_profiles",
                    #                     "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                    #                     "action_hard_code_flag": 'table_action_delete_flag',
                    #                     "action_is_standalone": True,
                    #                     "action_label": 'Supprimer'
                    #                 }
                    #             ],
                    #             "action_to_apps": []
                    #         },
                    #         "rbac_custom_actions_obj": {
                    #             "action_to_menus": [],
                    #             "action_to_apps": []
                    #         },
                    #         "rbac_collection_meta_data_obj": {
                    #             "collection_meta_data_to_menus": {
                    #                 "delete_processing_url": [
                    #                     {
                    #                         "hard_code_flag": "main",
                    #                         "rbac_endpoint": f"/api/v1/generic/hard-delete/{CollectionKey.RBAC_PROFILE.value}",
                    #                         "is_sudo_action": False,
                    #                         "is_sudo_group_action": False,
                    #                         "menu_flag": "administrations_system_rbac_profiles",
                    #                         "is_parent_field_name": False,
                    #                         "is_link_deleted": False,
                    #                     },
                    #                 ],

                    #             },
                    #             "collection_meta_data_to_apps": {
                    #                 "fetch_url": [],
                    #                 "update_processing_url": [],
                    #                 "update_head_process_url": [],
                    #                 "parent_field_name": [],
                    #                 "delete_processing_url": [],
                    #                 "create_processing_url": [],
                    #                 "create_head_process_url": [],
                    #                 "create_child_processing_url": [],
                    #                 "create_child_head_process_url": [],
                    #                 "fetch_one_info_url": [],
                    #                 "fetch_one_info_for_viewing_url": [],
                    #                 "put_processing_url": [],
                    #                 "patch_processing_url": []
                    #             }

                    #         }
                    #     }
    
                    # },
                    # {
                    #     'flag': "creating_system_rbac_profile",
                    #     "label": "Création d'un profil RBAC System",
                    #      "core_seeds": {
                    #         "restricted_profil_list": [
                    #              {
                    #                     "flag": ESysProfileFlag.SYSTEM_PROFIL,
                    #                     "is_link_activated": True,
                    #                     "is_link_hidden": False,
                    #                     "is_link_locked": False,
                    #                     "is_link_deleted": False,
                    #             }, 
                    #                 {
                    #                     "flag": ESysProfileFlag.TEST_SYS_PROFIL.value,
                    #                     "is_link_activated": True,
                    #                     "is_link_hidden": False,
                    #                     "is_link_locked": False,
                    #                     "is_link_deleted": False,
                    #                 },
                    #         ],
                            
                    #         "restricted_api_consumer_list": [
                    #             {
                    #                 "flag": EApiConsumerFlag.ANGULAR_SENAT_DIGIT_ADMIN_WEB_APP.value,
                    #                 "is_link_activated": True,
                    #                 "is_link_hidden": False,
                    #                 "is_link_locked": False,
                    #                 "is_link_deleted": False,
                    #             }
                    #         ],
                    #         "rbac_roles_list": [
                    #              {
                    #                     "flag": ESysProfilSuperUserRoleFlag.SYSTEM_PROFIL_SUPER_ADMIN,
                    #                     "is_link_activated": True,
                    #                     "is_link_hidden": False,
                    #                     "is_link_locked": False,
                    #                     "is_link_deleted": False,
                    #                 }, 
                    #                 {
                    #                     "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN,
                    #                     "is_link_activated": True,
                    #                     "is_link_hidden": False,
                    #                     "is_link_locked": False,
                    #                     "is_link_deleted": False,
                    #                 }, 
                    #         ],
                           
                    #         "sys_apps_list": [
                    #             {
                    #                 "flag": "administrations",
                    #                 "is_link_activated": True,
                    #                 "is_link_hidden": False,
                    #                 "is_link_locked": False,
                    #                 "is_link_deleted": False,
                    #             }
                    #         ],
                    #         "sys_menus_list": [ 
                    #             {
                    #                 "flag": "administrations_system_rbac_profiles",
                    #                 "is_link_activated": True,
                    #                 "is_link_hidden": False,
                    #                 "is_link_locked": False,
                    #                 "is_link_deleted": False,
                    #             },
                    #         ],
                    #         "rbac_standalone_actions_obj": {
                    #             "action_to_menus": [
                    #                 {
                    #                     "menu_flag": "administrations_system_rbac_profiles",
                    #                     "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                    #                     "action_is_standalone": True,
                    #                     "action_hard_code_flag": 'creation_action_flag',
                    #                     "action_label": 'Créer'
                    #                 }
                    #             ],
                    #             "action_to_apps": []
                    #         },
                    #         "rbac_custom_actions_obj": { 
                    #             "action_to_menus": [],
                    #             "action_to_apps": []
                    #         },
                    #         "rbac_collection_meta_data_obj": {
                    #             "collection_meta_data_to_menus": {
                    #                 "create_processing_url": [
                    #                     {
                    #                         "hard_code_flag": "main",
                    #                         "rbac_endpoint": "/api/v1/cores/create-profile",
                    #                         "is_sudo_action": False,
                    #                         "is_sudo_group_action": False,
                    #                         "menu_flag": "administrations_system_rbac_profiles",
                    #                         "is_parent_field_name": False,
                    #                         "is_link_deleted": False,
                    #                     },
                    #                 ],
                    #                 "create_head_process_url": [
                    #                     {
                    #                         "hard_code_flag": "main",
                    #                         "rbac_endpoint": f"/api/v1/generic/head/{CollectionKey.RBAC_PROFILE.value}",
                    #                         "is_sudo_action": False,
                    #                         "is_sudo_group_action": False,
                    #                         "menu_flag": "administrations_system_rbac_profiles",
                    #                         "is_parent_field_name": False,
                    #                         "is_link_deleted": False,
                    #                     },
                    #                 ],
                    #             },
                    #             "collection_meta_data_to_apps": {
                    #                 "fetch_url": [],
                    #                 "update_processing_url": [],
                    #                 "update_head_process_url": [],
                    #                 "parent_field_name": [],
                    #                 "delete_processing_url": [],
                    #                 "create_processing_url": [],
                    #                 "create_head_process_url": [],
                    #                 "create_child_processing_url": [],
                    #                 "create_child_head_process_url": [],
                    #                 "fetch_one_info_url": [],
                    #                 "fetch_one_info_for_viewing_url": [],
                    #                 "put_processing_url": [],
                    #                 "patch_processing_url": []
                    #             }

                    #         }
                    #     }

                    # },
                    # {
                    #     'flag': "updating_system_rbac_profile",
                    #     "label": "Mise à jour d'un profil RBAC System",
                    #     "core_seeds": {
                    #         "restricted_profil_list": [
                    #              {
                    #                     "flag": ESysProfileFlag.SYSTEM_PROFIL,
                    #                     "is_link_activated": True,
                    #                     "is_link_hidden": False,
                    #                     "is_link_locked": False,
                    #                     "is_link_deleted": False,
                    #             }, 
                    #                 {
                    #                     "flag": ESysProfileFlag.TEST_SYS_PROFIL.value,
                    #                     "is_link_activated": True,
                    #                     "is_link_hidden": False,
                    #                     "is_link_locked": False,
                    #                     "is_link_deleted": False,
                    #                 },
                    #         ],
                            
                    #         "restricted_api_consumer_list": [
                    #             {
                    #                 "flag": EApiConsumerFlag.ANGULAR_SENAT_DIGIT_ADMIN_WEB_APP.value,
                    #                 "is_link_activated": True,
                    #                 "is_link_hidden": False,
                    #                 "is_link_locked": False,
                    #                 "is_link_deleted": False,
                    #             }
                    #         ],
                    #         "rbac_roles_list": [
                    #              {
                    #                     "flag": ESysProfilSuperUserRoleFlag.SYSTEM_PROFIL_SUPER_ADMIN,
                    #                     "is_link_activated": True,
                    #                     "is_link_hidden": False,
                    #                     "is_link_locked": False,
                    #                     "is_link_deleted": False,
                    #                 }, 
                    #                 {
                    #                     "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN,
                    #                     "is_link_activated": True,
                    #                     "is_link_hidden": False,
                    #                     "is_link_locked": False,
                    #                     "is_link_deleted": False,
                    #                 }, 
                    #         ],
                           
                    #         "sys_apps_list": [
                    #             {
                    #                 "flag": "administrations",
                    #                 "is_link_activated": True,
                    #                 "is_link_hidden": False,
                    #                 "is_link_locked": False,
                    #                 "is_link_deleted": False,
                    #             }
                    #         ],
                    #         "sys_menus_list": [ 
                    #             {
                    #                 "flag": "administrations_system_rbac_profiles",
                    #                 "is_link_activated": True,
                    #                 "is_link_hidden": False,
                    #                 "is_link_locked": False,
                    #                 "is_link_deleted": False,
                    #             },
                    #         ],
                    #         "rbac_standalone_actions_obj": {
                    #             "action_to_menus": [
                    #                 {
                    #                     "menu_flag": "administrations_system_rbac_profiles",
                    #                     "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                    #                     "action_is_standalone": True,
                    #                     "action_hard_code_flag": 'table_action_update_flag',
                    #                     "action_label": 'Modifier'
                    #                 }
                    #             ],
                    #             "action_to_apps": []
                    #         },
                    #         "rbac_custom_actions_obj": {
                    #             "action_to_menus": [
                    #                 {
                    #                     "menu_flag": "administrations_system_rbac_profiles",
                    #                     "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                    #                     "action_is_standalone": False,
                    #                     "action_hard_code_flag": 'custom_update_profil_permission_table_action_flag',
                    #                     "action_label": 'Mettre à jour des permissions"'
                    #                 },
                    #                 {
                    #                     "menu_flag": "administrations_system_rbac_profiles",
                    #                     "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                    #                     "action_is_standalone": False,
                    #                     "action_hard_code_flag": 'custom_extended_update_profil_permission_table_action_flag',
                    #                     "action_label": 'Mettre à jour des permissions avancées"'
                    #                 }
                    #             ],
                    #             "action_to_apps": []
                    #         },
                    #         "rbac_collection_meta_data_obj": {
                    #             "collection_meta_data_to_menus": {
                    #                 "update_processing_url": [
                    #                     {
                    #                         "hard_code_flag": "main",
                    #                         "rbac_endpoint": f"/api/v1/generic/update/{CollectionKey.RBAC_PROFILE.value}",
                    #                         "is_sudo_action": False,
                    #                         "is_sudo_group_action": False,
                    #                         "menu_flag": "administrations_system_rbac_profiles",
                    #                         "is_parent_field_name": False,
                    #                         "is_link_deleted": False,
                    #                     },
                    #                     {
                    #                         "hard_code_flag": "custom_profil_permission_update_process_url",
                    #                         "rbac_endpoint": "/api/v1/cores/upsert-profile-permissions",
                    #                         "is_sudo_action": False,
                    #                         "is_sudo_group_action": False,
                    #                         "menu_flag": "administrations_system_rbac_profiles",
                    #                         "is_parent_field_name": False,
                    #                         "is_link_deleted": False,
                    #                     },
                    #                     {
                    #                         "hard_code_flag": "custom_extended_profil_permission_update_process_url",
                    #                         "rbac_endpoint": "/api/v1/cores/upsert-extended-profile-permissions",
                    #                         "is_sudo_action": False,
                    #                         "is_sudo_group_action": False,
                    #                         "menu_flag": "administrations_system_rbac_profiles",
                    #                         "is_parent_field_name": False,
                    #                         "is_link_deleted": False,
                    #                     },
                                        

                    #                 ],
                    #                 "update_head_process_url": [
                    #                     {
                    #                         "hard_code_flag": "main",
                    #                         "rbac_endpoint": f"/api/v1/generic/update-head/{CollectionKey.RBAC_PROFILE.value}",
                    #                         "is_sudo_action": False,
                    #                         "is_sudo_group_action": False,
                    #                         "menu_flag": "administrations_system_rbac_profiles",
                    #                         "is_parent_field_name": False,
                    #                         "is_link_deleted": False,
                    #                     },
                    #                     {
                    #                         "hard_code_flag": "custom_profil_permission_update_head_process_url",
                    #                         "rbac_endpoint": "/api/v1/cores/get-profile-permissions",
                    #                         "is_sudo_action": False,
                    #                         "is_sudo_group_action": False,
                    #                         "menu_flag": "administrations_system_rbac_profiles",
                    #                         "is_parent_field_name": False,
                    #                         "is_link_deleted": False,
                    #                     }, 
                    #                     {
                    #                         "hard_code_flag": "custom_extended_profil_permission_update_head_process_url",
                    #                         "rbac_endpoint": "/api/v1/cores/get-extended-profile-permissions",
                    #                         "is_sudo_action": False,
                    #                         "is_sudo_group_action": False,
                    #                         "menu_flag": "administrations_system_rbac_profiles",
                    #                         "is_parent_field_name": False,
                    #                         "is_link_deleted": False,
                    #                     },
                    #                 ],
                    #                 "patch_processing_url": [
                    #                     {
                    #                         "hard_code_flag": "patch_profil_application_access_process_url",
                    #                         "rbac_endpoint": "/api/v1/organizations/patch/profile-application-access",
                    #                         "is_sudo_action": False,
                    #                         "is_sudo_group_action": False,
                    #                         "menu_flag": "administrations_system_rbac_profiles",
                    #                         "is_parent_field_name": False,
                    #                         "is_link_deleted": False,
                    #                     },
                    #                 ]
                    #             },
                    #             "collection_meta_data_to_apps": {
                    #                 "fetch_url": [],
                    #                 "update_processing_url": [],
                    #                 "update_head_process_url": [],
                    #                 "parent_field_name": [],
                    #                 "delete_processing_url": [],
                    #                 "create_processing_url": [],
                    #                 "create_head_process_url": [],
                    #                 "create_child_processing_url": [],
                    #                 "create_child_head_process_url": [],
                    #                 "fetch_one_info_url": [],
                    #                 "fetch_one_info_for_viewing_url": [],
                    #                 "put_processing_url": [],
                    #                 "patch_processing_url": []
                    #             }

                    #         }
                    #     }
    
                    # },
                
                ],
                "endpoints": [
                    {
                        "label": "Chargement des profils RBAC System",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/fetch/{CollectionKey.RBAC_PROFILE.value}"
                    },
                    {
                        "label": "Chargement du formulaire de création d'un profil RBAC System",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/head/{CollectionKey.RBAC_PROFILE.value}"
                    },
                    {
                        "label": "Création d'un profil RBAC System",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/cores/create-profile"
                    }, 
                    {
                        "label": "Suppression d'un profil RBAC System",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/cores/delete-profile"
                    }, 
                    {
                        "label": "Mise à jour d'un profil RBAC System",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/update/{CollectionKey.RBAC_PROFILE.value}"
                    }, 
                    {
                        "label": "Chargement du formulaire de Mise à jour d'un profil RBAC System",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/update-head/{CollectionKey.RBAC_PROFILE.value}"
                    }, 
                    {
                        "label": "Suppression d'un profil RBAC System",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/hard-delete/{CollectionKey.RBAC_PROFILE.value}"
                    }, 
                ],
            },
             
             
        ]
