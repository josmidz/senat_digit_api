
from app.modules.core.constants.common import ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE, ALL_ORGANIZATION_PROFIL_IN_ONE, SENAT_DIGIT_ADMIN_WEB_IN_ONE


SECURITY_RLS_OVERVIEW_PERMISSION_RBAC_DB = [
    {
        'flag': "security_rls_overview_loading_of_vehicles",
        "label": "Chargement de l'aperçu des règles de sécurité",
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
                    "flag": "security_rls_menu_page",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "security_rls_overview_page",
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
                            "rbac_endpoint": "/api/v1/securities/rls/overviews/fetch/overview",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_overview_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        },   
                        {
                            "hard_code_flag": "main",
                            "rbac_endpoint": "/api/v1/securities/rls/fetch/overview",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "security_rls_overview_page",
                            "is_parent_field_name": False,
                            "is_link_deleted": True,
                        },   
                    ],
                    "fetch_one_info_url": [ ],
                },

            }
        }
    }, 
]
