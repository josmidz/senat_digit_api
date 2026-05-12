

from app.modules.auth.enums.common import ERbacActionFlag
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.common import SENAT_DIGIT_ADMIN_WEB_IN_ONE, TRANS_ADMIN_ROLE_IN_ONE, TRANS_FINANCER_ROLE_IN_ONE, MAIN_PROFILE_IN_ONE

PARAMETRE_EXCHANGES_CURRENCIES_PERMISSION_RBAC_TITLE_DB = [
    { 
        'flag': "settings_loading_currency_exchange",
        "label": "Chargement des taux de change",
        "core_seeds": {
            "restricted_profil_list": [
                *MAIN_PROFILE_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TRANS_FINANCER_ROLE_IN_ONE,
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
                    "flag": "apps_settings_organization_currencies_and_exhanges",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "apps_settings_organizations_single_exchanges_rates",
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
                            "rbac_endpoint": f"/api/v1/generic/org/fetch/{CollectionKey.CFG_CURRENCY_EXCHANGE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "is_available_for_rls": True,
                            "menu_flag": "apps_settings_organizations_single_exchanges_rates",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }
                    ],
                },

            }
        }
    
    },
     
    {
        'flag': "settings_deleting_currency_exchange",
        "label": "Suppression des taux de change",
        "core_seeds": {
            "restricted_profil_list": [
                *MAIN_PROFILE_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TRANS_FINANCER_ROLE_IN_ONE,
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
                    "flag": "apps_settings_organization_currencies_and_exhanges",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "apps_settings_organizations_single_exchanges_rates",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "apps_settings_organizations_single_exchanges_rates",
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
                            "rbac_endpoint": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_CURRENCY_EXCHANGE.value}",
                            "is_sudo_action": True,
                            "is_sudo_group_action": True,
                            "menu_flag": "apps_settings_organizations_single_exchanges_rates",
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
        'flag': "settings_creating_currency_exchange",
        "label": "Création des taux de change",
        "core_seeds": {
            "restricted_profil_list": [
                *MAIN_PROFILE_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TRANS_FINANCER_ROLE_IN_ONE,
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
                    "flag": "apps_settings_organization_currencies_and_exhanges",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "apps_settings_organizations_single_exchanges_rates",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "apps_settings_organizations_single_exchanges_rates",
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
                            "rbac_endpoint": f"/api/v1/generic/org/add/{CollectionKey.CFG_CURRENCY_EXCHANGE.value}",
                            "is_sudo_action": True,
                            "is_sudo_group_action": True,
                            "menu_flag": "apps_settings_organizations_single_exchanges_rates",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "create_head_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/static/org/data/get-exchanges-config",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organizations_single_exchanges_rates",
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
        'flag': "settings_update_currency_exchange",
        "label": "Mise à jour des taux de change",
        "core_seeds": {
            "restricted_profil_list": [
                *MAIN_PROFILE_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
                *TRANS_FINANCER_ROLE_IN_ONE,
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
                    "flag": "apps_settings_organization_currencies_and_exhanges",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "apps_settings_organizations_single_exchanges_rates",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "apps_settings_organizations_single_exchanges_rates",
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
                            "rbac_endpoint": "/api/v1/static/data/update-currency-exchanges",
                            "is_sudo_action": True,
                            "is_sudo_group_action": True,
                            "menu_flag": "apps_settings_organizations_single_exchanges_rates",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },

                    ],
                    "update_head_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/org/update-head/{CollectionKey.CFG_CURRENCY_EXCHANGE.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organizations_single_exchanges_rates",
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
