

from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.core.constants.common import ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE, ALL_ORGANIZATION_PROFIL_IN_ONE, SENAT_DIGIT_ADMIN_WEB_IN_ONE
from app.modules.auth.enums.common import ERbacActionFlag, ERbacActionHardCodeFlag
from app.modules.core.models.mapping_keys import CollectionKey


SECURITY_VALIDATION_CROSS_VALIDATORS_PERMISSION_RBAC_TITLE_DB = [
        {
            'flag': "loading_permission_cross_validators",
            'is_default': False,
            "label": "Chargement des validateurs croisés d'une permission ( dans validateurs croisés)",
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
                        "flag": "security_validations_cross_validation_page",
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
                                "rbac_endpoint": "/api/v1/securities/validations/cross-validators/fetch/cross-validators",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_cross_validation_page",
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
        {
            'flag': "adding_user_account_from_permission_grouped_validator_group",
            'is_default': False,
            "label": "Activer/Désactiver le sudo action d'une permission ( dans validateurs croisés)",
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
                        "flag": "security_validations_cross_validation_page",
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
                            "menu_flag": "security_validations_cross_validation_page",
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
                                "hard_code_flag": "fetch_formated_permissions_url",
                                "rbac_endpoint": "/api/v1/securities/validations/grouped-validators/fetch/formated-permissions",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_cross_validation_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                        ],
                        "patch_processing_url": [
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/patch/{CollectionKey.CFG_ORGANIZATION_SUDO_ACTION.value}",
                                "is_sudo_action": True,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_cross_validation_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }, 
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": f"/api/v1/generic/org/patch/{CollectionKey.CFG_SUDO_ACTION_ACCESS.value}",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_cross_validation_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": True,
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
            'flag': "adding_org_from_permission_cross_validator_group",
            'is_default': False,
            "label": "Ajouter une organisation dans un groupe des validateurs croisés d'une permission",
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
                        "flag": "security_validations_cross_validation_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                ],
                "rbac_standalone_actions_obj": {
                    "action_to_menus": [
                        {
                            "menu_flag": "security_validations_cross_validation_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                            "action_hard_code_flag": ERbacActionHardCodeFlag.CREATION_ACTION.value,
                            "action_is_standalone": True,
                            "action_label": 'Ajouter'
                        }
                    ],
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
                                "hard_code_flag": "fetch_available_cross_validator_orgs_url",
                                "rbac_endpoint": "/api/v1/securities/validations/cross-validators/fetch/available-orgs",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_cross_validation_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }, 
                            {
                                "hard_code_flag": "fetch_formated_permissions_url",
                                "rbac_endpoint": "/api/v1/securities/validations/grouped-validators/fetch/formated-permissions",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_cross_validation_page",
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
                                "menu_flag": "security_validations_cross_validation_page",
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
            'flag': "removing_org_from_permission_cross_validator_group",
            'is_default': False,
            "label": "Retirer une organisation d'un groupe des validateurs croisés d'une permission",
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
                        "flag": "security_validations_cross_validation_page",
                        "is_link_activated": True,
                        "is_link_hidden": False,
                        "is_link_locked": False,
                        "is_link_deleted": False,
                    },
                ],
                "rbac_standalone_actions_obj": {
                    "action_to_menus": [
                        {
                            "menu_flag": "security_validations_cross_validation_page",
                            "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                            "action_hard_code_flag": ERbacActionHardCodeFlag.DELETION_ACTION.value,
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
                    "collection_meta_data_to_apps": {
                        "update_processing_url": [],
                        "update_head_process_url": [],
                    },
                    "collection_meta_data_to_menus": {
                        "fetch_url": [
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": "/api/v1/securities/validations/cross-validators/fetch/cross-validators",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_cross_validation_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                            {
                                "hard_code_flag": "fetch_formated_permissions_url",
                                "rbac_endpoint": "/api/v1/securities/validations/grouped-validators/fetch/formated-permissions",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_cross_validation_page",
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
                                "menu_flag": "security_validations_cross_validation_page",
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
