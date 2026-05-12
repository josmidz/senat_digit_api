from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.auth.enums.common import ERbacActionFlag, ERbacComponentFlag
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.constants.common import SENAT_DIGIT_ADMIN_WEB_IN_ONE, SYSTEM_ORGANIZATION_PROFIL_IN_ONE, SYSTEM_SUPER_ADMIN_ROLE_IN_ONE


ADMINISTRATION_ORGANIZATION_DETAILS_PERMISSION_RBAC_TITLE_DB = [
  {
    'flag': "system_loading_saas_organization_details",
    "label": "[system] Chargement des détails d'une organisation",
    "core_seeds": {
        "restricted_profil_list": [
            *SYSTEM_ORGANIZATION_PROFIL_IN_ONE,
        ],
        "restricted_api_consumer_list": [
            *SENAT_DIGIT_ADMIN_WEB_IN_ONE
        ],
        "rbac_roles_list": [
            *SYSTEM_SUPER_ADMIN_ROLE_IN_ONE
        ],
        "sys_apps_list": [
            {
                "flag": "administrations",
                "is_link_activated": True,
                "is_link_hidden": False,
                "is_link_locked": False,
                "is_link_deleted": False,
            }
        ],
        "sys_menus_list": [ 
            {
                "flag": "administrations_organizations_page",
                "is_link_activated": True,
                "is_link_hidden": False,
                "is_link_locked": False,
                "is_link_deleted": False,
            },
            {
                "flag": "administrations_organization_details_page",
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
        "rbac_custom_components_obj": {
            "component_to_menus": [
                {
                    "menu_flag": "administrations_organization_details_page",
                    "component_flag": ERbacComponentFlag.DATA_LIST_COMPONENT.value,
                    "component_is_standalone": False,
                    "component_hard_code_flag": 'system_only_organization_details_component_flag',
                    "component_label": "Composant pour les détails d'une organisation"
                }
            ],
            "component_to_apps": []
        },
        "rbac_collection_meta_data_obj": {
            "collection_meta_data_to_menus": {
                "fetch_url": [ 
                    {
                        "hard_code_flag": "main",
                        "rbac_endpoint": "/api/v1/organizations/fetch/org-details",
                        "is_sudo_action": False,
                        "is_sudo_group_action": False,
                        "menu_flag": "administrations_organization_details_page",
                        "is_parent_field_name": False,
                        "is_link_deleted": False,
                    },   
                ],
                "patch_processing_url": []
            },

        }
    }

  },    
]
