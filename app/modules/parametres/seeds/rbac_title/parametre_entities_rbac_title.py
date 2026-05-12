

from app.modules.auth.enums.common import ERbacActionFlag
from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.common import SENAT_DIGIT_ADMIN_WEB_IN_ONE, TRANS_ADMIN_ROLE_IN_ONE, MAIN_PROFILE_IN_ONE

PARAMETRE_ENTITIES_PERMISSION_RBAC_TITLE_DB = [
    {
        'flag': "settings_loading_entities",
        "label": "Chargement des entités",
         "core_seeds": {
            "restricted_profil_list": [
                *MAIN_PROFILE_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
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
                    "flag": "apps_settings_organization_entities",
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
                            "rbac_endpoint": f"/api/v1/generic/fetch/{CollectionKey.REF_ENTITY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "fetch_current_entity_default_currency_fetch_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/fetch/current-entity-default-currency",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "fetch_current_entity_info_fetch_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/fetch/current-entity-info",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "fetch_telephone_networks_fetch_url",
                            "rbac_endpoint": "/api/v1/system-countries/telephone-networks/fetch/telnets",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        {
                            "hard_code_flag": "fetch_ewallet_prefixes_fetch_url",
                            "rbac_endpoint": "/api/v1/system-countries/ewallet-prefixes/fetch/ewallet-prefixes",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        {
                            "hard_code_flag": "fetch_telephone_network_prefixes_fetch_url",
                            "rbac_endpoint": "/api/v1/system-countries/telephone-networks/fetch/telnet-prefixes",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        {
                            "hard_code_flag": "fetch_no_existing_countries_fetch_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/fetch/no-existing-countries",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        {
                            "hard_code_flag": "fetch_all_existing_countries_fetch_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/fetch/all-existing-countries",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        {
                            "hard_code_flag": "fetch_system_country_availlable_currencies_fetch_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/fetch/system-country-availlable-currencies",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        {
                            "hard_code_flag": "fetch_system_country_country_codes_fetch_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/fetch/system-country-country-codes",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        {
                            "hard_code_flag": "fetch_system_country_currencies_fetch_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/fetch/system-country-currencies",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        {
                            "hard_code_flag": "fetch_currencies_process_url",
                            "rbac_endpoint": f"/api/v1/generic/fetch/{CollectionKey.REF_CURRENCY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                    ],
                },

            }
        }
    
    },
    {
        'flag': "settings_deleting_entities",
        "label": "Suppression des entités",
        "core_seeds": {
            "restricted_profil_list": [
                *MAIN_PROFILE_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
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
                    "flag": "apps_settings_organization_entities",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "apps_settings_organization_entities",
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
                            "rbac_endpoint": f"/api/v1/generic/hard-delete/{CollectionKey.REF_ENTITY.value}",
                            "is_sudo_action": True,
                            "is_sudo_group_action": True,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "delete_system_country_processing_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/delete/system-country",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }, 
                        {
                            "hard_code_flag": "delete_telephone_network_processing_url",
                            "rbac_endpoint": "/api/v1/system-countries/telephone-networks/delete/telephone-network",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
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
        'flag': "settings_creating_entities",
        "label": "Création d'une entité",
        "core_seeds": {
            "restricted_profil_list": [
                *MAIN_PROFILE_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
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
                    "flag": "apps_settings_organization_entities",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "apps_settings_organization_entities",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_ADD.value,
                        "action_is_standalone": True,
                        "action_hard_code_flag": 'creation_action_flag',
                        "action_label": 'Créer'
                    },
                    {
                        "menu_flag": "apps_settings_organization_entities",
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
                            "rbac_endpoint": f"/api/v1/generic/add/{CollectionKey.REF_ENTITY.value}",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "create_system_country_processing_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/add/system-country",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "check_entity_configuration_fetch_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/fetch/check-system-country-configuration",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                       
                        {
                            "hard_code_flag": "add_telephone_network_processing_url",
                            "rbac_endpoint": f"/api/v1/generic/add/{CollectionKey.REF_TELEPHONE_NETWORK.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "create_child_processing_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/add/{CollectionKey.REF_ENTITY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "create_head_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/head/{CollectionKey.REF_ENTITY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "add_system_country_network_head_processing_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/head/system-country",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "add_telephone_network_head_processing_url",
                            "rbac_endpoint": f"/api/v1/generic/head/{CollectionKey.REF_TELEPHONE_NETWORK.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "create_child_head_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/child-head/{CollectionKey.REF_ENTITY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
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
        'flag': "settings_update_entities",
        "label": "Mise à jour des entités",
        "core_seeds": {
            "restricted_profil_list": [
                *MAIN_PROFILE_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "rbac_roles_list": [
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
                    "flag": "apps_settings_organization_entities",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "apps_settings_organization_entities",
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
                            "hard_code_flag": "update_current_entity_default_currency_processing_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/update/current-entity-default-currency",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "patch_current_entity_flag_processing_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/patch/current-entity-flag",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/update/{CollectionKey.REF_ENTITY.value}",
                            "is_sudo_action": True,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                         {
                            "hard_code_flag": "update_telephone_network_processing_url",
                            "rbac_endpoint": f"/api/v1/generic/update/{CollectionKey.REF_TELEPHONE_NETWORK.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },

                    ],
                    "update_head_process_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": f"/api/v1/generic/update-head/{CollectionKey.REF_ENTITY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "update_telephone_network_head_processing_url",
                            "rbac_endpoint": f"/api/v1/generic/update-head/{CollectionKey.REF_TELEPHONE_NETWORK.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "patch_processing_url": [
                        {
                            "hard_code_flag": "patch_system_country_to_add_remove_country_code_process_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/patch/add-remove-country-code",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "patch_system_country_to_add_remove_country_phone_prefix_process_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/patch/add-remove-country-phone-prefix",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "patch_system_country_to_add_remove_wallet_prefix_process_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/patch/add-remove-wallet-prefix",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "patch_system_country_to_add_remove_currency_process_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/patch/add-remove-currency",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "patch_system_country_to_validate_email_phone_number_transfer_required_process_url",
                            "rbac_endpoint": "/api/v1/system-countries/countries/patch/validate-email-phone-number-transfer-required",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_entities",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ]
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
