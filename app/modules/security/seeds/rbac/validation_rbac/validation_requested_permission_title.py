

from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.constants.common import ALL_PROFIL_IN_ONE, ALL_STATIC_ROLE_IN_ONE
from app.modules.auth.enums.common import ERbacActionFlag
 
VALIDATION_REQUESTED_PERMISSION_RBAC_TITLE_DB = [
    # {
    #     'flag': "loading_validation_requests",
    #     'is_default': True,
    #     "label": "Chargement des requêtes de validation",
    #     "app_accessible_to_all_profil_flag": "accessible_user_validation_requests",
    #     "menu_accessible_to_all_profil_flag": "accessible_user_validation_requests",
    #     "is_accessible_to_all_profil": True,
    # },
    # {
    #     'flag': "validate_or_reject_validation_requests",
    #     'is_default': True,
    #     "label": "Valider/Rejeter une requête",
    #     "app_accessible_to_all_profil_flag": "accessible_user_validation_requests",
    #     "menu_accessible_to_all_profil_flag": "accessible_user_validation_requests",
    #     "is_accessible_to_all_profil": True,
    # },
    # {
    #     'flag': "user_validation_requested_overview",
    #     'is_default': True,
    #     "label": "Aperçu des requêtes de validation",
    #     "app_accessible_to_all_profil_flag": "accessible_user_validation_requests",
    #     "menu_accessible_to_all_profil_flag": "accessible_user_validation_requests",
    #     "is_accessible_to_all_profil": True,
    # },
    # {
    #     'flag': "loading_validation_request_view",
    #     'is_default': True,
    #     "label": "Chargement de la vue des requêtes de validation",
    #     "app_accessible_to_all_profil_flag": "accessible_user_validation_requests",
    #     "menu_accessible_to_all_profil_flag": "accessible_user_validation_requests",
    #     "is_accessible_to_all_profil": True,
    # },
    {
        'flag': "loading_single_validation_request_overview",
        'is_default': True,
        "app_accessible_to_all_profil_flag": "accessible_user_validation_requests",
        "menu_accessible_to_all_profil_flag": "accessible_user_validation_requests",
        "is_accessible_to_all_profil": True,
        "label": "Chargement d'une requête de validation",
        "core_seeds": {
            "restricted_profil_list": [
                *ALL_PROFIL_IN_ONE
            ],
            "restricted_api_consumer_list": [
                {
                    "flag": EApiConsumerFlag.SENAT_DIGIT_ADMIN_WEB.value,
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": EApiConsumerFlag.FLUTTER_VALIDATION_AND_TOTP_MFA_APPS.value,
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_roles_list": [
                *ALL_STATIC_ROLE_IN_ONE 
            ],
            "sys_apps_list": [
                {
                    "flag": "validation_app_requests_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "validation_app_requested_overview_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "validation_app_requests_overview_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "sys_menus_list": [
                {
                    "flag": "validation_app_request_list_page",
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
                            "rbac_endpoint": "/api/v1/securities/validations/requests/pending",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "validation_app_request_list_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "fetch_one_info_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/securities/validations/requests/single",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "validation_app_request_list_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ],
                    "patch_processing_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/securities/validations/requests/validate-or-reject",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "validation_app_request_list_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                        {
                            "hard_code_flag": "bulk_validate",
                            "rbac_endpoint": "/api/v1/securities/validations/requests/validate-all",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "validation_app_request_list_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ]
                },

            }
        }

    },
    {
        'flag': "validate_or_reject_validation_requests",
        'is_default': True,
        "app_accessible_to_all_profil_flag": "accessible_user_validation_requests",
        "menu_accessible_to_all_profil_flag": "accessible_user_validation_requests",
        "is_accessible_to_all_profil": True,
        "label": "Valider/Rejeter une requête",
        "core_seeds": {
            "restricted_profil_list": [
                *ALL_PROFIL_IN_ONE
            ],
            "restricted_api_consumer_list": [
                {
                    "flag": EApiConsumerFlag.SENAT_DIGIT_ADMIN_WEB.value,
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": EApiConsumerFlag.FLUTTER_VALIDATION_AND_TOTP_MFA_APPS.value,
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_roles_list": [
                *ALL_STATIC_ROLE_IN_ONE 
            ],
            "sys_apps_list": [
                {
                    "flag": "validation_app_requests_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "validation_app_request_list_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_standalone_actions_obj": {
                "action_to_menus": [
                    {
                        "menu_flag": "validation_app_request_list_page",
                        "action_flag": ERbacActionFlag.TABLE_ACTION_UPDATE.value,
                        "action_is_standalone": True,
                        "action_hard_code_flag": 'table_action_update_flag',
                        "action_label": 'Valider/Rejeter une requête'
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
                    "patch_processing_url": [
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/securities/validations/requests/validate-or-reject",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "validation_app_request_list_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ]
                },

            }
        }

    },
    {
        'flag': "validate_all_pending_validation_requests",
        'is_default': True,
        "app_accessible_to_all_profil_flag": "accessible_user_validation_requests",
        "menu_accessible_to_all_profil_flag": "accessible_user_validation_requests",
        "is_accessible_to_all_profil": True,
        "label": "Valider toutes les requêtes en attente",
        "core_seeds": {
            "restricted_profil_list": [
                *ALL_PROFIL_IN_ONE
            ],
            "restricted_api_consumer_list": [
                {
                    "flag": EApiConsumerFlag.SENAT_DIGIT_ADMIN_WEB.value,
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": EApiConsumerFlag.FLUTTER_VALIDATION_AND_TOTP_MFA_APPS.value,
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
            ],
            "rbac_roles_list": [
                *ALL_STATIC_ROLE_IN_ONE
            ],
            "sys_apps_list": [
                {
                    "flag": "validation_app_requests_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                }
            ],
            "sys_menus_list": [
                {
                    "flag": "validation_app_request_list_page",
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
                    "patch_processing_url": [
                        {
                            "hard_code_flag": "bulk_validate",
                            "rbac_endpoint": "/api/v1/securities/validations/requests/validate-all",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "validation_app_request_list_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },
                    ]
                },

            }
        }

    },
]
