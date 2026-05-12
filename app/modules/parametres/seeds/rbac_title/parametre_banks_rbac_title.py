

from app.modules.auth.enums.common import ERbacActionFlag
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.common import SENAT_DIGIT_ADMIN_WEB_IN_ONE, TRANS_ADMIN_ROLE_IN_ONE, TRANS_EXPENSE_TYPE_PERSON_ROLE_IN_ONE, TRANS_FINANCER_ROLE_IN_ONE, MAIN_PROFILE_IN_ONE

PARAMETRE_BANKS_PERMISSION_RBAC_TITLE_DB = [
    {
        'flag': "settings_loading_organization_bank",
        "label": "Chargement des banques",
        "is_link_deleted": False,
        "description_str": "cette permission permet à la personne qui l'a de pouvoir accéder et voir les banques",
        "core_seeds": {
            "restricted_profil_list": [
                *MAIN_PROFILE_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TRANS_FINANCER_ROLE_IN_ONE,
                *TRANS_EXPENSE_TYPE_PERSON_ROLE_IN_ONE,
                *TRANS_ADMIN_ROLE_IN_ONE,
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
                    "flag": "apps_settings_org_gov_single_bank",
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
                            "rbac_endpoint": f"/api/v1/generic/fetch/{CollectionKey.REF_BANK.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_org_gov_single_bank",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        # menu compte
                        {
                            "hard_code_flag": "fetch_banks_process_url",
                            "rbac_endpoint": f"/api/v1/generic/fetch/{CollectionKey.REF_BANK.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "general_expensechain_basic_comptes",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        # menu saisie depense
                        {
                            "hard_code_flag": "fetch_banks_process_url",
                            "rbac_endpoint": f"/api/v1/generic/fetch/{CollectionKey.REF_BANK.value}",
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
        'flag': "settings_deleting_organization_bank",
        "label": "Suppression d'un banque",
        "is_link_deleted": False,
        "description_str": "cette permission permet à la personne qui l'a de pouvoir accéder et de supprimer une banque",
        "core_seeds": {
            "restricted_profil_list": [
                # {
                #     "flag": "system",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # },
                # {
                #     "flag": "mineconat",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # }
            ],
            "restricted_api_consumer_list": [
                # {
                #     "flag": "angular_min_eco_nat_saas_web_app",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # }
            ],
            "rbac_roles_list": [
                # {
                #     "flag": "system_super_admin",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # },
                # {
                #     "flag": "mineconat_super_admin",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # }
            ],
            "sys_apps_list": [
                # {
                #     "flag": "app_settings",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # }
            ],
            "sys_menus_list": [
                # {
                #     "flag": "apps_settings_beneficiaries_banks",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # },
                # {
                #     "flag": "apps_settings_org_gov_single_bank",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    # {
                    #     "menu_flag": "apps_settings_org_gov_single_bank",
                    #     "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                    #     "action_hard_code_flag": 'table_action_delete_flag',
                    #     "action_is_standalone": True,
                    #     "action_label": 'Supprimer',
                    # }
                ],
                "action_to_apps": []
            },
            "rbac_custom_actions_obj": {
                "action_to_menus": [
                    # # MENU COMPTE
                    # {
                    #     "menu_flag": "general_expensechain_basic_comptes",
                    #     "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                    #     "action_is_standalone": False,
                    #     "action_hard_code_flag": 'dynamic_can_delete_bank_action_flag',
                    #     "action_label": "Suppression d'une banque",
                    # },
                    # # MENU SAISIE DEPENSE
                    # {
                    #     "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
                    #     "action_flag": ERbacActionFlag.TABLE_ACTION_DELETE.value,
                    #     "action_is_standalone": False,
                    #     "action_hard_code_flag": 'dynamic_can_delete_bank_action_flag',
                    #     "action_label": "Suppression d'une banque",
                    # },
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "delete_processing_url": [
                        # {
                        #     "hard_code_flag": "main",
                        #     "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_BANK.value}",
                        #     "is_sudo_action": True,
                        #     "is_sudo_group_action": False,
                        #     "menu_flag": "apps_settings_org_gov_single_bank",
                        #     "is_parent_field_name": False,
                        # },
                        # # MENU COMPTE
                        # {
                        #     "hard_code_flag": "banks_delete_process_url",
                        #     "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_BANK.value}",
                        #     "is_sudo_action": False,
                        #     "is_sudo_group_action": False,
                        #     "menu_flag": "general_expensechain_basic_comptes",
                        #     "is_parent_field_name": False,
                        # },
                        # # MENU SAISIE DEPENSE
                        # {
                        #     "hard_code_flag": "banks_delete_process_url",
                        #     "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_BANK.value}",
                        #     "is_sudo_action": False,
                        #     "is_sudo_group_action": False,
                        #     "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
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
        'flag': "settings_creating_organization_bank",
        "label": "Création d'une banque",
        "is_link_deleted": False,
        "description_str": "cette permission permet à la personne qui l'a de pouvoir accéder et de créer une banque",
        "core_seeds": {
            "restricted_profil_list": [
                # {
                #     "flag": "system",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # },
                # {
                #     "flag": "mineconat",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # }
            ],
            "restricted_api_consumer_list": [
                # {
                #     "flag": "angular_min_eco_nat_saas_web_app",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # }
            ],
            "rbac_roles_list": [
                # {
                #     "flag": "system_super_admin",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # },
                # {
                #     "flag": "mineconat_super_admin",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # }
            ],
            "sys_apps_list": [
                # CREATING BANK IN EXPENSE ACCOUNT MENU
            ],
            "sys_menus_list": [
                # {
                #     "flag": "apps_settings_beneficiaries_banks",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # },
                # {
                #     "flag": "apps_settings_org_gov_single_bank",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # },

                # CREATING BANK IN EXPENSE ACCOUNT MENU
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    # {
                    #     "menu_flag": "apps_settings_org_gov_single_bank",
                    #     "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                    #     "action_is_standalone": True,
                    #     "action_hard_code_flag": 'creation_action_flag',
                    #     "action_label": 'Créer',
                    # },

                ],
                "action_to_apps": []
            },
            "rbac_custom_actions_obj": {
                "action_to_menus": [
                    # # MENU COMPTE
                    # {
                    #     "menu_flag": "general_expensechain_basic_comptes",
                    #     "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                    #     "action_is_standalone": False,
                    #     "action_hard_code_flag": 'dynamic_can_create_bank_action_flag',
                    #     "action_label": "Création d'une banque",
                    # },
                    # # MENU SAISIE DEPENSE
                    # {
                    #     "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
                    #     "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                    #     "action_is_standalone": False,
                    #     "action_hard_code_flag": 'dynamic_can_create_bank_action_flag',
                    #     "action_label": "Création d'une banque",
                    # },
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "create_processing_url": [
                        # {
                        #     "hard_code_flag": "main",
                        #     "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_BANK.value}",
                        #     "is_sudo_action": False,
                        #     "is_sudo_group_action": False,
                        #     "menu_flag": "apps_settings_org_gov_single_bank",
                        #     "is_parent_field_name": False,
                        # },
                        # # MENU COMPTE
                        # {
                        #     "hard_code_flag": "banks_creation_process_url",
                        #     "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_BANK.value}",
                        #     "is_sudo_action": False,
                        #     "is_sudo_group_action": False,
                        #     "menu_flag": "general_expensechain_basic_comptes",
                        #     "is_parent_field_name": False,
                        # },
                        # # MENU SAISIE DEPENSE
                        # {
                        #     "hard_code_flag": "banks_creation_process_url",
                        #     "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_BANK.value}",
                        #     "is_sudo_action": False,
                        #     "is_sudo_group_action": False,
                        #     "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
                        #     "is_parent_field_name": False,
                        # },
                    ],
                    "create_head_process_url": [
                        # {
                        #     "hard_code_flag": "main",
                        #     "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.CFG_BANK.value}",
                        #     "is_sudo_action": False,
                        #     "is_sudo_group_action": False,
                        #     "menu_flag": "apps_settings_org_gov_single_bank",
                        #     "is_parent_field_name": False,
                        # },
                        # # MENU COMPTE
                        # {
                        #     "hard_code_flag": "banks_creation_head_process_url",
                        #     "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.CFG_BANK.value}",
                        #     "is_sudo_action": False,
                        #     "is_sudo_group_action": False,
                        #     "menu_flag": "general_expensechain_basic_comptes",
                        #     "is_parent_field_name": False,
                        # },
                        # # MENU SAISIE DEPENSE
                        # {
                        #     "hard_code_flag": "banks_creation_head_process_url",
                        #     "rbac_endpoint": f"/api/v1/generic/org/head/{CollectionKey.CFG_BANK.value}",
                        #     "is_sudo_action": False,
                        #     "is_sudo_group_action": False,
                        #     "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
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
        'flag': "settings_update_organization_bank",
        "label": "Mise à jour des banques",
        "is_link_deleted": False,
        "description_str": "cette permission permet à la personne qui l'a de pouvoir accéder et de modifier les banques",
        "core_seeds": {
            "restricted_profil_list": [
                # {
                #     "flag": "system",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # },
                # {
                #     "flag": "mineconat",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # }
            ],
            "restricted_api_consumer_list": [
                # {
                #     "flag": "angular_min_eco_nat_saas_web_app",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # }
            ],
            "rbac_roles_list": [
                # {
                #     "flag": "system_super_admin",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # },
                # {
                #     "flag": "mineconat_super_admin",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # }
            ],
            "sys_apps_list": [
                # {
                #     "flag": "app_settings",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # }
            ],
            "sys_menus_list": [
                # {
                #     "flag": "apps_settings_beneficiaries_banks",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # },
                # {
                #     "flag": "apps_settings_org_gov_single_bank",
                #     "is_link_activated": True,
                #     "is_link_hidden": False,
                #     "is_link_locked": False,
                # },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    # {
                    #     "menu_flag": "apps_settings_org_gov_single_bank",
                    #     "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                    #     "action_is_standalone": True,
                    #     "action_hard_code_flag": 'table_action_update_flag',
                    #     "action_label": 'Modifier',
                    # }
                ],
                "action_to_apps": []
            },
            "rbac_custom_actions_obj": {
                "action_to_menus": [
                    # MENU COMPTE
                    # {
                    #     "menu_flag": "general_expensechain_basic_comptes",
                    #     "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                    #     "action_is_standalone": False,
                    #     "action_hard_code_flag": 'dynamic_can_update_bank_action_flag',
                    #     "action_label": "Mise à jour d'une banque",
                    # },
                    # MENU SAISIE DEPENSE
                    # {
                    #     "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
                    #     "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                    #     "action_is_standalone": False,
                    #     "action_hard_code_flag": 'dynamic_can_update_bank_action_flag',
                    #     "action_label": "Mise à jour d'une banque",
                    # },
                ],
                "action_to_apps": []
            },
            "rbac_collection_meta_data_obj": {
                "collection_meta_data_to_menus": {
                    "update_processing_url": [
                        # {
                        #     "hard_code_flag": "main",
                        #     "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.CFG_BANK.value}",
                        #     "is_sudo_action": False,
                        #     "is_sudo_group_action": False,
                        #     "menu_flag": "apps_settings_org_gov_single_bank",
                        #     "is_parent_field_name": False,
                        # },
                        # MENU COMPTE
                        # {
                        #     "hard_code_flag": "banks_update_process_url",
                        #     "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.CFG_BANK.value}",
                        #     "is_sudo_action": False,
                        #     "is_sudo_group_action": False,
                        #     "menu_flag": "general_expensechain_basic_comptes",
                        #     "is_parent_field_name": False,
                        # },
                        # MENU SAISIE DEPENSE
                        # {
                        #     "hard_code_flag": "banks_update_process_url",
                        #     "rbac_endpoint": f"/api/v1/generic/org/update/{CollectionKey.CFG_BANK.value}",
                        #     "is_sudo_action": False,
                        #     "is_sudo_group_action": False,
                        #     "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
                        #     "is_parent_field_name": False,
                        # },
                    ],
                    "update_head_process_url": [
                        # {
                        #     "hard_code_flag": "main",
                        #     "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.CFG_BANK.value}",
                        #     "is_sudo_action": False,
                        #     "is_sudo_group_action": False,
                        #     "menu_flag": "apps_settings_org_gov_single_bank",
                        #     "is_parent_field_name": False,
                        # },
                        # MENU COMPTE
                        # {
                        #     "hard_code_flag": "banks_update_head_process_url",
                        #     "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.CFG_BANK.value}",
                        #     "is_sudo_action": False,
                        #     "is_sudo_group_action": False,
                        #     "menu_flag": "general_expensechain_basic_comptes",
                        #     "is_parent_field_name": False,
                        # },
                        # MENU SAISIE DEPENSE
                        # {
                        #     "hard_code_flag": "banks_update_head_process_url",
                        #     "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.CFG_BANK.value}",
                        #     "is_sudo_action": False,
                        #     "is_sudo_group_action": False,
                        #     "menu_flag": "general_expensechain_basic_depenses_saisie_depense",
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

]
