

from app.modules.auth.enums.common import ERbacActionFlag
from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.common import SENAT_DIGIT_ADMIN_WEB_IN_ONE, TRANS_ACCOUNTANT_ROLE_IN_ONE, TRANS_EXPENSE_TYPE_PERSON_ROLE_IN_ONE, TRANS_FINANCER_ROLE_IN_ONE, MAIN_PROFILE_IN_ONE

PARAMETRE_CURRENCIES_PERMISSION_RBAC_TITLE_DB = [
    {
        'flag': "settings_loading_currencies",
        "label": "Chargement des devises",
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
                    "flag": "apps_settings_organization_currencies_and_exhanges",
                    "is_link_activated": True,
                    "is_link_hidden": False,
                    "is_link_locked": False,
                    "is_link_deleted": False,
                },
                {
                    "flag": "apps_settings_organization_single_currencies",
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
                            "rbac_endpoint": f"/api/v1/generic/fetch/{CollectionKey.REF_CURRENCY.value}",
                            "is_sudo_action": False,
                            "is_sudo_group_action": False,
                            "menu_flag": "apps_settings_organization_single_currencies",
                            "is_parent_field_name": False,
                            "is_link_deleted": False,
                        }
                    ],
                },

            }
        }

    },
    {
        'flag': "settings_deleting_currencies",
        "label": "[system] Suppression des devises",
    },
    {
        'flag': "settings_creating_currencies",
        "label": "[system] Création d'une devise"
    },
    {
        'flag': "settings_update_currencies",
        "label": "[system] Mise à jour des devises",
    },

]
