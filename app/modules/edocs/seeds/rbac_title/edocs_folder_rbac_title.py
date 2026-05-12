

from app.modules.auth.enums.common import ERbacActionFlag
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.common import ANGULAR_API_CONSUMER_IN_ONE, TEST_ADMIN_ROLE_IN_ONE, TEST_PROFIL_IN_ONE

EDOC_FOLDER_PERMISSION_RBAC_TITLE_DB = [
    {
        'flag': "can_create_folder_in_edoc_man_system",
        "label": "Créer un dossier",
        "is_link_deleted": False,
        "description_str": "cette permission permet à la personne qui l'a de pouvoir créer un dossier ou sous dossier",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE
            ],
            "restricted_api_consumer_list": [
                 *ANGULAR_API_CONSUMER_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE
            ],
            "sys_apps_list": [
                {
                    "flag": "e_document_management_system",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "e_document_management_system_folders",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }, 
            ],
            
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "e_document_management_system_folders",
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
                            "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.ARCH_FOLDER.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_folders",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "create_head_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.ARCH_FOLDER.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_folders",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        
                    ],
                    "create_child_processing_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.ARCH_FOLDER.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_folders",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "create_child_head_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/child-head/{CollectionKey.ARCH_FOLDER.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_folders",
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
        'flag': "can_access_folder_in_edoc_man_system",
        "label": "Peut accéder aux dossiers",
        "is_link_deleted": False,
        "description_str": "cette permission permet à la personne qui l'a de pouvoir accéder et voir les dossiers et sous-dossiers",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE
            ],
            "restricted_api_consumer_list": [
                 *ANGULAR_API_CONSUMER_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE
            ],
            "sys_apps_list": [
                {
                    "flag": "e_document_management_system",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "e_document_management_system_folders",
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
                            "rbac_endpoint": "/api/v1/edocs/org/fetch/archFolders",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_folders",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "fetch_global_file_folder_stats_url",
                            "rbac_endpoint": "/api/v1/edocs/org/data/stats",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_folders",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                },

            }
        }

    },
    {
        'flag': "can_access_folder_bins_in_edoc_man_system",
        "label": "Peut accéder à la corbeille des dossiers",
        "is_link_deleted": False,
        "description_str": "cette permission permet à la personne qui l'a de pouvoir accéder à la corbeille des dossiers",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE
            ],
            "restricted_api_consumer_list": [
                 *ANGULAR_API_CONSUMER_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE
            ],
            "sys_apps_list": [
                {
                    "flag": "e_document_management_system",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "e_document_management_system_folders",
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
                        "menu_flag": "e_document_management_system_folders",
                        "action_flag": ERbacActionFlag.STANDALONE_ACTION.value,
                        "action_hard_code_flag": 'can_access_folder_bins_in_edoc_man_system',
                        "action_is_standalone": False,
                        "action_label": 'Accès à la corbeille des dossiers'
                    }, 
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "fetch_url": [
                        {
                            "hard_code_flag": "fetch_folder_bin_url",
                            "rbac_endpoint": "/api/v1/edocs/org/fetch/folders-bin",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_folders",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                },

            }
        }
        
    },
    {
        'flag': "updating_folder_in_edoc_man_system",
        "label": "Mise à jour des dossiers",
        "is_link_deleted": False,
        "description_str": "cette permission permet à la personne qui l'a de pouvoir modifier les dossiers",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE
            ],
            "restricted_api_consumer_list": [
                 *ANGULAR_API_CONSUMER_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE
            ],
            "sys_apps_list": [
                {
                    "flag": "e_document_management_system",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "e_document_management_system_folders",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }, 
            ],
            
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "e_document_management_system_folders",
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
                            "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.ARCH_FOLDER.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_folders",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        
                    ],
                    "update_head_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.ARCH_FOLDER.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_folders",
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
        'flag': "deleting_folders_in_doc_man_system",
        "label": "Suppression des dossiers",
        "is_link_deleted": False,
        "description_str": "cette permission permet à la personne qui l'a de pouvoir supprimer des dossiers",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE
            ],
            "restricted_api_consumer_list": [
                 *ANGULAR_API_CONSUMER_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE
            ],
            "sys_apps_list": [
                {
                    "flag": "e_document_management_system",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "e_document_management_system_folders",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }, 
            ],
            
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "e_document_management_system_folders",
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
                            "rbac_endpoint": "/api/v1/edocs/org/hard-delete/archFolders",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_folders",
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
        'flag': "downloading_folders_in_doc_man_system",
        "label": "Téléchargement des dossiers",
        "is_link_deleted": False,
        "description_str": "cette permission permet à la personne qui l'a de pouvoir télécharger des dossiers",
        "core_seeds": {
            "restricted_profil_list": [
                *TEST_PROFIL_IN_ONE
            ],
            "restricted_api_consumer_list": [
                 *ANGULAR_API_CONSUMER_IN_ONE
            ],
            "rbac_roles_list": [
                *TEST_ADMIN_ROLE_IN_ONE
            ],
            "sys_apps_list": [
                {
                    "flag": "e_document_management_system",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "e_document_management_system_folders",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }, 
            ],
            
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "e_document_management_system_folders",
                        "action_flag": ERbacActionFlag.COMMON_DOWNLOAD_ACTION.value,
                        "action_is_standalone": False,
                        "action_hard_code_flag": 'common_action_download_flag',
                        "action_label": "Téléchargement des dossiers"
                    }
                ],
                "action_to_apps": []
            },
            "rbac_custom_actions_obj": {
                "action_to_menus": [

                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "download_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/edocs/org/download/archFolders",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_folders",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                },

            }
        }
                    
    },

]
