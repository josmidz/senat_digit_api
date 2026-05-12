

from app.modules.auth.enums.common import ERbacActionFlag
from app.modules.core.constants.common import ANGULAR_API_CONSUMER_IN_ONE, TEST_ADMIN_ROLE_IN_ONE, TEST_PROFIL_IN_ONE

EDOC_FILE_PERMISSION_RBAC_TITLE_DB = [
    {
        'flag': "can_access_files_bins_in_edoc_man_system",
        "label": "Peut accéder à la corbeille des fichiers",
        "is_link_deleted": False,
        "description_str": "cette permission permet à la personne qui l'a de pouvoir accéder à la corbeille des fichiers",
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
                    "flag": "e_document_management_system_file",
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
                        "menu_flag": "e_document_management_system_file",
                        "action_flag": ERbacActionFlag.STANDALONE_ACTION.value,
                        "action_hard_code_flag": 'can_access_file_bins_in_edoc_man_system',
                        "action_is_standalone": False,
                        "action_label": 'Accès à la corbeille des fichiers'
                    }, 
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "fetch_url": [
                        {
                            "hard_code_flag": "fetch_file_bin_url",
                            "rbac_endpoint": "/api/v1/edocs/org/fetch/files-bin",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_file",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                },

            }
        }
        
    },
    {
        'flag': "uploading_new_file_in_edoc_man_system",
        "label": "Ajout d'un fichier",
        "is_link_deleted": False,
        "description_str": "cette permission permet à la personne qui l'a de pouvoir ajouter un fichier",
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
                    "flag": "e_document_management_system_file",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }, 
            ],
            
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "e_document_management_system_file",
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
                            "rbac_endpoint": "/api/v1/edocs/org/files/upload",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_file",
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
        'flag': "loading_files_in_doc_man_system",
        "label": "Accès aux fichiers",
        "is_link_deleted": False,
        "description_str": "cette permission permet à la personne qui l'a de pouvoir accéder et voir les fichiers",
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
                    "flag": "e_document_management_system_file",
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
                            "rbac_endpoint": "/api/v1/edocs/org/fetch/archFiles",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_file",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                },

            }
        }
    }, 
    {
        'flag': "deleting_files_in_doc_man_system",
        "label": "Suppression des fichiers",
        "is_link_deleted": False,
        "description_str": "cette permission permet à la personne qui l'a de pouvoir supprimer des fichiers",
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
                    "flag": "e_document_management_system_file",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }, 
            ],
            
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "e_document_management_system_file",
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
                            "rbac_endpoint": "/api/v1/edocs/org/hard-delete/archFiles",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_file",
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
        'flag': "downloading_files_in_doc_man_system",
        "label": "Téléchargement des fichiers",
        "is_link_deleted": False,
        "description_str": "cette permission permet à la personne qui l'a de pouvoir télécharger des fichiers",
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
                    "flag": "e_document_management_system_file",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }, 
            ],
            
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "e_document_management_system_file",
                        "action_flag": ERbacActionFlag.COMMON_DOWNLOAD_ACTION.value,
                        "action_is_standalone": False,
                        "action_hard_code_flag": 'common_action_download_flag',
                        "action_label": "Téléchargement des fichiers"
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
                            "rbac_endpoint": "/api/v1/edocs/org/download/archFiles",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "e_document_management_system_file",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                },

            }
        }
       
    },

]
