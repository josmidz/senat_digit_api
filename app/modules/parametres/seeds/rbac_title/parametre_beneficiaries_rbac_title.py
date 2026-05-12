

from app.modules.auth.enums.common import ERbacActionFlag
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.common import SENAT_DIGIT_ADMIN_WEB_IN_ONE, TRANS_ACCOUNTANT_ROLE_IN_ONE, TRANS_ADMIN_ROLE_IN_ONE, TRANS_EXPENSE_TYPE_PERSON_ROLE_IN_ONE, TRANS_FINANCER_ROLE_IN_ONE, MAIN_PROFILE_IN_ONE

PARAMETRE_BENEFICIARIES_PERMISSION_RBAC_TITLE_DB = [
    {
        'flag': "settings_loading_organization_beneficiaries",
        "label": "Chargement des bénéficiaires",
        "core_seeds": {
            "restricted_profil_list": [
                *MAIN_PROFILE_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TRANS_FINANCER_ROLE_IN_ONE,
                *TRANS_ACCOUNTANT_ROLE_IN_ONE,
                *TRANS_EXPENSE_TYPE_PERSON_ROLE_IN_ONE,
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
                    "flag": "apps_settings_beneficiaries_banks",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "apps_settings_single_beneficiary",
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
                            "hard_code_flag": "fetch_legal_beneficiaries_url",
                            "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_single_beneficiary",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        {
                            "hard_code_flag": "fetch_physical_beneficiaries_url",
                            "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_single_beneficiary",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        # FOR EXPENSE CHAIN ENTRY SCREEN
                        {
                            "hard_code_flag": "fetch_physical_beneficiaries_url",
                            "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "fetch_legal_beneficiaries_url",
                            "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                },

            }
        }

    },
    {
        'flag': "settings_deleting_organization_beneficiaries",
        "label": "Suppression d'un benéficiaire",
        "core_seeds": {
            "restricted_profil_list": [
                *MAIN_PROFILE_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TRANS_ACCOUNTANT_ROLE_IN_ONE,
                *TRANS_EXPENSE_TYPE_PERSON_ROLE_IN_ONE,
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
                    "flag": "apps_settings_beneficiaries_banks",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "apps_settings_single_beneficiary",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "apps_settings_single_beneficiary",
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
                            "hard_code_flag": "delete_legal_beneficiary_url",
                            "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_single_beneficiary",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "delete_physical_beneficiary_url",
                            "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_single_beneficiary",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        # FOR EXPENSE ENTRY PAGE
                        {
                            "hard_code_flag": "delete_legal_beneficiary_url",
                            "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "delete_physical_beneficiary_url",
                            "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
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
        'flag': "settings_creating_organization_beneficiaries",
        "label": "Création d'un benéficiaire",
        "core_seeds": {
            "restricted_profil_list": [
                *MAIN_PROFILE_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TRANS_ACCOUNTANT_ROLE_IN_ONE,
                *TRANS_EXPENSE_TYPE_PERSON_ROLE_IN_ONE,
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
                    "flag": "apps_settings_beneficiaries_banks",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "apps_settings_single_beneficiary",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "apps_settings_single_beneficiary",
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
                            "hard_code_flag": "add_legal_beneficiary_url",
                            "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_single_beneficiary",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "add_physical_beneficiary_url",
                            "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_single_beneficiary",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        # EXPENSE ENTRY
                        {
                            "hard_code_flag": "add_legal_beneficiary_url",
                            "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "add_physical_beneficiary_url",
                            "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "create_head_process_url": [
                         
                        {
                            "hard_code_flag": "add_legal_beneficiary_head_url",
                            "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_single_beneficiary",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "add_physical_beneficiary_head_url",
                            "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_single_beneficiary",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        # EXPENSE ENTRY
                        {
                            "hard_code_flag": "add_legal_beneficiary_head_url",
                            "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "add_physical_beneficiary_head_url",
                            "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
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
        'flag': "settings_update_organization_beneficiaries",
        "label": "Mise à jour des benéficiaires",
        "core_seeds": {
            "restricted_profil_list": [
                *MAIN_PROFILE_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TRANS_ACCOUNTANT_ROLE_IN_ONE,
                *TRANS_EXPENSE_TYPE_PERSON_ROLE_IN_ONE,
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
                    "flag": "apps_settings_beneficiaries_banks",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "apps_settings_single_beneficiary",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "apps_settings_single_beneficiary",
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
                            "hard_code_flag": "update_legal_beneficiary_url",
                            "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_single_beneficiary",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "update_physical_beneficiary_url",
                            "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_single_beneficiary",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },

                        # EXPENSE ENTRY
                        {
                            "hard_code_flag": "update_legal_beneficiary_url",
                            "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "update_physical_beneficiary_url",
                            "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "update_head_process_url": [
                        
                        {
                            "hard_code_flag": "update_legal_beneficiary_head_url",
                            "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_single_beneficiary",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "update_physical_beneficiary_head_url",
                            "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_single_beneficiary",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },

                        # EXPENSE ENTRY
                        {
                            "hard_code_flag": "update_legal_beneficiary_head_url",
                            "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "update_physical_beneficiary_head_url",
                            "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
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
