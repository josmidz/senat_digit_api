

from app.modules.core.constants.common import ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE, ALL_ORGANIZATION_PROFIL_IN_ONE, SENAT_DIGIT_ADMIN_WEB_IN_ONE


SECURITY_VALIDATION_USER_ACCESS_PERMISSION_RBAC_TITLE_DB = [
        {
            'flag': "loading_security_validation_user_accesses",
            'is_default': False,
            "label": "Chargement des accès de validation des utilisateurs",
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
                        "flag": "security_validations_users_sudo_action_overview_page",
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
                    "action_to_menus": [],
                    "action_to_apps": []
                },
                "rbac_collection_meta_data_obj": {
                    "collection_meta_data_to_menus": {
                        "fetch_url": [
                            {
                                "hard_code_flag": "main",
                                "rbac_endpoint": "/api/v1/securities/validations/sudo-actions/fetch/users-sudo-actions-overview",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_users_sudo_action_overview_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            }, 
                            {
                                "hard_code_flag": "fetch_user_sudo_actions_overview_url",
                                "rbac_endpoint": "/api/v1/securities/validations/sudo-actions/fetch/users-sudo-actions-overview",
                                "is_sudo_action": False,
                                "is_sudo_group_action": False,
                                "menu_flag": "security_validations_users_sudo_action_overview_page",
                                "is_parent_field_name": False,
                                "is_link_deleted": False,
                            },
                        ],
                        "update_processing_url": [],
                        "update_head_process_url": [],
                    },
                    "collection_meta_data_to_apps": {
                        "update_processing_url": [],
                        "update_head_process_url": [],
                    }
                }
            }
        },
     
]
