

from app.modules.auth.enums.common import ERbacActionFlag
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.common import SENAT_DIGIT_ADMIN_WEB_IN_ONE, TEST_ADMIN_ROLE_IN_ONE, TEST_PROFIL_IN_ONE

PARAMETRE_TEMPLATES_PERMISSION_RBAC_TITLE_DB = [

    # TEMPLATES
    {
        'flag': "settings_loading_of_document_templates",
        "label": "Chargement des templates",
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
                    "flag": "apps_settings_organization_system_templates",
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
                            "rbac_endpoint": f"/api/v1/generic/fetch/{CollectionKey.REF_DOCUMENT_TEMPLATE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "fetch_one_info_url": [],
                },

            }
        }
    },
    {
        'flag': "settings_deleting_of_document_templates",
        "label": "Suppression des templates",
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
                    "flag": "apps_settings_organization_system_templates",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "apps_settings_organization_system_templates",
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
                            "rbac_endpoint": f"/api/v1/generic/hard-delete/{CollectionKey.REF_DOCUMENT_TEMPLATE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
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
        'flag': "settings_creating_of_document_templates",
        "label": "Création d'un template",
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
                    "flag": "apps_settings_organization_system_templates",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "apps_settings_organization_system_templates",
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
                            "rbac_endpoint": f"/api/v1/generic/add/{CollectionKey.REF_DOCUMENT_TEMPLATE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "create_head_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/head/{CollectionKey.REF_DOCUMENT_TEMPLATE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
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
        'flag': "settings_update_of_document_templates",
        "label": "Mise à jout d'un template",
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
                    "flag": "apps_settings_organization_system_templates",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "apps_settings_organization_system_templates",
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
                            "rbac_endpoint": f"/api/v1/generic/update/{CollectionKey.REF_DOCUMENT_TEMPLATE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        
                    ],
                    "update_head_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/update-head/{CollectionKey.REF_DOCUMENT_TEMPLATE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
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
    # TEMPLATES TYPES
    {
        'flag': "settings_loading_types_of_document_templates",
        "label": "Chargement des types des templates",
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
                    "flag": "apps_settings_organization_system_templates",
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
                            "hard_code_flag": "template_doc_type_fetch_url",
                            "rbac_endpoint": f"/api/v1/generic/fetch/{CollectionKey.REF_DOCUMENT_TEMPLATE_TYPE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        
                    ],
                    "fetch_one_info_url": [],
                },

            }
        }
    },
    {
        'flag': "settings_deleting_types_of_document_templates",
        "label": "Suppression des types des templates",
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
                    "flag": "apps_settings_organization_system_templates",
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
                        "menu_flag": "apps_settings_organization_system_templates",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                        "action_hard_code_flag": 'custom_template_type_table_action_delete_flag',
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
                            "hard_code_flag": "template_doc_type_delete_process_url",
                            "rbac_endpoint": f"/api/v1/generic/hard-delete/{CollectionKey.REF_DOCUMENT_TEMPLATE_TYPE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
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
        'flag': "settings_creating_types_of_document_templates",
        "label": "Création d'un type des templates",
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
                    "flag": "apps_settings_organization_system_templates",
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
                        "menu_flag": "apps_settings_organization_system_templates",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                        "action_is_standalone": False,
                        "action_hard_code_flag": 'custom_template_type_creation_action_flag',
                        "action_label": 'Créer'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "create_processing_url": [
                        {
                            "hard_code_flag": "template_doc_type_process_url",
                            "rbac_endpoint": f"/api/v1/generic/add/{CollectionKey.REF_DOCUMENT_TEMPLATE_TYPE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "create_head_process_url": [
                        {
                            "hard_code_flag": "template_doc_type_head_process_url",
                            "rbac_endpoint": f"/api/v1/generic/head/{CollectionKey.REF_DOCUMENT_TEMPLATE_TYPE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
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
        'flag': "settings_loading_update_for_types_of_document_templates",
        "label": "Mise à jour d'un type des templates",
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
                    "flag": "apps_settings_organization_system_templates",
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
                        "menu_flag": "apps_settings_organization_system_templates",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                        "action_is_standalone": False,
                        "action_hard_code_flag": 'custom_template_type_table_action_update_flag',
                        "action_label": 'Modifier'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "update_processing_url": [
                        {
                            "hard_code_flag": "template_doc_type_update_process_url",
                            "rbac_endpoint": f"/api/v1/generic/update/{CollectionKey.REF_DOCUMENT_TEMPLATE_TYPE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        
                    ],
                    "update_head_process_url": [
                        {
                            "hard_code_flag": "template_doc_type_update_head_process_url",
                            "rbac_endpoint": f"/api/v1/generic/update-head/{CollectionKey.REF_DOCUMENT_TEMPLATE_TYPE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
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
    # TEMPLATES PAGES
    {
        'flag': "settings_loading_pages_of_document_template",
        "label": "Chargement des pages d'un template",
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
                    "flag": "apps_settings_organization_system_templates",
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
                            "hard_code_flag": "fetch_template_doc_page_process_url",
                            "rbac_endpoint": f"/api/v1/generic/fetch/{CollectionKey.REF_DOCUMENT_TEMPLATE_PAGE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        
                    ],
                    "fetch_one_info_url": [],
                },

            }
        }
    },
    {
        'flag': "settings_deleting_pages_of_document_template",
        "label": "Suppression des pages d'un template",
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
                    "flag": "apps_settings_organization_system_templates",
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
                        "menu_flag": "apps_settings_organization_system_templates",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                        "action_hard_code_flag": 'custom_template_page_table_action_delete_flag',
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
                            "hard_code_flag": "template_doc_page_delete_process_url",
                            "rbac_endpoint": f"/api/v1/generic/hard-delete/{CollectionKey.REF_DOCUMENT_TEMPLATE_PAGE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
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
        'flag': "settings_creating_pages_of_document_template",
        "label": "Création des pages d'un template",
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
                    "flag": "apps_settings_organization_system_templates",
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
                        "menu_flag": "apps_settings_organization_system_templates",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                        "action_is_standalone": False,
                        "action_hard_code_flag": 'custom_template_page_creation_action_flag',
                        "action_label": 'Créer'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "create_processing_url": [
                        {
                            "hard_code_flag": "template_doc_page_process_url",
                            "rbac_endpoint": f"/api/v1/generic/add/{CollectionKey.REF_DOCUMENT_TEMPLATE_PAGE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                    "create_head_process_url": [
                        {
                            "hard_code_flag": "template_doc_page_head_process_url",
                            "rbac_endpoint": f"/api/v1/generic/head/{CollectionKey.REF_DOCUMENT_TEMPLATE_PAGE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
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
        'flag': "settings_loading_update_for_pages_of_document_template",
        "label": "Mise à jour des pages d'un template",
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
                    "flag": "apps_settings_organization_system_templates",
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
                        "menu_flag": "apps_settings_organization_system_templates",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                        "action_is_standalone": False,
                        "action_hard_code_flag": 'custom_template_page_table_action_update_flag',
                        "action_label": 'Modifier'
                    }
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "update_processing_url": [
                        {
                            "hard_code_flag": "template_doc_page_update_process_url",
                            "rbac_endpoint": f"/api/v1/generic/update/{CollectionKey.REF_DOCUMENT_TEMPLATE_PAGE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        
                    ],
                    "update_head_process_url": [
                        {
                            "hard_code_flag": "template_doc_page_update_head_process_url",
                            "rbac_endpoint": f"/api/v1/generic/update-head/{CollectionKey.REF_DOCUMENT_TEMPLATE_PAGE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_system_templates",
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
