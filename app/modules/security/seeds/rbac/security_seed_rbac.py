from app.modules.security.seeds.rbac.settings.security_group_permission_title import SECURITY_GROUPS_PERMISSION_RBAC_TITLE_DB
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.security.seeds.rbac.validation_rbac.validation_global_validators_permission_title import SECURITY_VALIDATION_GLOBAL_VALIDATORS_RBAC_TITLE_DB
from app.modules.security.seeds.rbac.validation_rbac.validation_grouped_validators_permission_title import SECURITY_VALIDATION_GROUPED_PERMISSION_RBAC_TITLE_DB
from app.modules.security.seeds.rbac.validation_rbac.validation_delegated_validators_permission_title import SECURITY_VALIDATION_DELEGATED_VALIDATORS_PERMISSION_RBAC_TITLE_DB
from app.modules.security.seeds.rbac.validation_rbac.validation_sudo_action_overview_rbac import VALIDATION_SUDO_ACTION_OVERVIEW_PERMISSION_RBAC_DB
from app.modules.security.seeds.rbac.rls.security_rls_overview_rbac import SECURITY_RLS_OVERVIEW_PERMISSION_RBAC_DB
from app.modules.security.seeds.rbac.settings.security_rls_setting_permission_title import SECURITY_RLS_SETTING_PERMISSION_RBAC_TITLE_DB
from app.modules.security.seeds.rbac.settings.security_sudo_action_setting_permission_title import SECURITY_SUDO_ACTION_SETTING_PERMISSION_RBAC_TITLE_DB
from app.modules.security.seeds.rbac.rls.security_rls_user_access_permission_title import SECURITY_RLS_USER_ACCESS_PERMISSION_RBAC_TITLE_DB
from app.modules.security.seeds.rbac.rls.security_rls_whitelist_blacklist_users_groups_permission_title import SECURITY_RLS_WHITELIST_BLACKLIST_USERS_AND_GROUPS_PERMISSION_RBAC_TITLE_DB
from app.modules.security.seeds.rbac.rls.security_rls_setup_permission_title import SECURITY_RLS_SETUP_PERMISSION_RBAC_TITLE_DB
from app.modules.security.seeds.rbac.validation_rbac.validation_cross_validators_permission_title import SECURITY_VALIDATION_CROSS_VALIDATORS_PERMISSION_RBAC_TITLE_DB
from app.modules.security.seeds.rbac.validation_rbac.validation_user_accesses_permission_title import SECURITY_VALIDATION_USER_ACCESS_PERMISSION_RBAC_TITLE_DB
from app.modules.security.seeds.rbac.validation_rbac.validation_configurations_permission_title import SECURITY_VALIDATION_CONFIGURATIONS_PERMISSION_RBAC_TITLE_DB
from app.modules.security.seeds.rbac.histories.security_delete_histories_permission_title import SECURITY_DELETE_HISTORIES_PERMISSION_RBAC_TITLE_DB
from app.modules.security.seeds.rbac.histories.security_update_histories_permission_title import SECURITY_UPDATE_HISTORIES_PERMISSION_RBAC_TITLE_DB
from app.modules.security.seeds.rbac.orglogs.security_logs_setup_permission_title import SECURITY_LOGS_SETUP_PERMISSION_RBAC_TITLE_DB
from app.modules.security.seeds.rbac.orglogs.security_logs_list_permission_title import SECURITY_LOGS_LIST_PERMISSION_RBAC_TITLE_DB


SECURITY_SEED_RBAC_TITLE_DB = [
    {
        "label": "Sécurité",
        "flag": "security_app_rbac_title",
        "is_default": False,
        "permissions": [],
        "endpoints": [],
        "children": [
            {
                "label": "Groupes de sécurité",
                "flag": "security_app_groups_rbac_title",
                "is_default": False,
                "children": [],
                "permissions": [
                    *SECURITY_GROUPS_PERMISSION_RBAC_TITLE_DB
                ],
                "endpoints": [
                    {
                        "label": "Chargement des groupes de sécurité",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/groups/fetch/groups"
                    },
                    {
                        "label": "Chargement d'un groupe de sécurité",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/groups/fetch/one-group"
                    },
                    {
                        "label": "Suppression d'un groupe de sécurité",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/groups/delete/group"
                    },
                    {
                        "label": "Ajout de plusieurs utilisateurs dans un groupe de sécurité",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/groups/add/group-bulk-users"
                    },
                    {
                        "label": "Création d'un groupe de sécurité",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/add/{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP.value}"
                    },
                    {
                        "label": "Chargement des utilisateurs d'un groupe de sécurité",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/groups/fetch/group-users"
                    },
                    {
                        "label": "Suppression d'un utilisateur d'un groupe de sécurité",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER.value}"
                    },
                    {
                        "label": "Chargement du formulaire de création d'un groupe de sécurité",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/head/{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP.value}"
                    },
                    {
                        "label": "Chargement du formulaire de mise à jour d'un groupe de sécurité",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/update-head/{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP.value}"
                    },
                    {
                        "label": "Mise à jour d'un groupe de sécurité",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/update/{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP.value}"
                    },
                    {
                        "label": "Ajout d'un utilisateur dans un groupe de sécurité",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/add/{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER.value}"
                    },

                ],
            },
            {
                "label": "Validations",
                "flag": "security_app_validations_menu_rbac_title",
                "is_default": False,
                "children": [
                    {
                        "label": "Aperçu des actions sudo",
                        "flag": "security_app_validations_sudo_action_overview_rbac_title",
                        "is_default": False,
                        "children": [],
                        "permissions": [
                            *VALIDATION_SUDO_ACTION_OVERVIEW_PERMISSION_RBAC_DB,
                        ],
                        "endpoints": [
                            {
                                "label": "Chargement de l'aperçu des actions sudo",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": "/api/v1/securities/validations/sudo-actions/fetch/sudo-actions-overview"
                            },
                            
                        ],
                    },
                    {
                        "label": "Validateurs globaux",
                        "flag": "security_app_validations_global_validators_rbac_title",
                        "is_default": False,
                        "children": [],
                        "permissions": [
                            *SECURITY_VALIDATION_GLOBAL_VALIDATORS_RBAC_TITLE_DB,
                        ],
                        "endpoints": [
                            {
                                "label": "Chargement des validateurs globaux",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": "/api/v1/securities/validations/global-validators/fetch/global-validators"
                            },
                            {
                                "label": "Chargement des utilisateurs qui n'existent pas dans la liste de validateurs globaux",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": "/api/v1/securities/validations/global-validators/fetch/available-users"
                            },
                            {
                                "label": "Chargement des groupes qui n'existent pas dans la liste de validateurs globaux",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": "/api/v1/securities/validations/global-validators/fetch/available-groups"
                            },
                            {
                                "label": "Retirer un utilisateur/groupe de validateurs globaux",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_SUDO_ACTION_ACCESS.value}"
                            },
                            {
                                "label": "Ajouter un utilisateur/groupe de validateurs globaux",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": f"/api/v1/generic/org/add/{CollectionKey.CFG_SUDO_ACTION_ACCESS.value}"
                            }, 
                        ],
                    }, 
                    {
                        "label": "Configurations des validations",
                        "flag": "security_app_validations_configurations_rbac_title",
                        "is_default": False,
                        "children": [],
                        "permissions": [
                            *SECURITY_VALIDATION_CONFIGURATIONS_PERMISSION_RBAC_TITLE_DB
                        ],
                        "endpoints": [
                            {
                                "label": "Chargement des configurations des validations",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": "/api/v1/securities/validations/configurations/fetch/configurations"
                            }, 
                            {
                                "label": "Chargement des groupes ou d'utilisateurs ou d'organisations comme validateurs d'une permission",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": "/api/v1/securities/validations/configurations/fetch/config-validators"
                            },
                            {
                                "label": "Chargement des utilisateurs qui n'existent pas dans la liste de validateurs d'une permission",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": "/api/v1/securities/validations/configurations/fetch/available-users"
                            },
                            {
                                "label": "Chargement des groupes qui n'existent pas dans la liste de validateurs d'une permission",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": "/api/v1/securities/validations/configurations/fetch/available-groups"
                            },
                            {
                                "label": "Chargement des organisations qui n'existent pas dans la liste de validateurs d'une permission",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": "/api/v1/securities/validations/configurations/fetch/available-inter-organizations"
                            }, 
                            {
                                "label": "Retirer un utilisateur/groupe d'un groupe des validateurs d'une permission",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_SUDO_ACTION_ACCESS.value}",
                            },
                            {
                                "label": "Ajouter un utilisateur/groupe dans un groupe des validateurs d'une permission",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": f"/api/v1/generic/org/add/{CollectionKey.CFG_SUDO_ACTION_ACCESS.value}",
                            },
                            {
                                "label": "Activer/Désactiver le sudo action d'une permission ( Sudo action/Sudo group action/ sudo action de délégation / Sudo group action de cross organization validation / Sudo group action de inter organization validation )",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": f"/api/v1/generic/org/patch/{CollectionKey.CFG_ORGANIZATION_SUDO_ACTION.value}",
                            },
                        ],
                    }, 
                    {
                        "label": "Accès de validation des utilisateurs",
                        "flag": "security_app_validations_user_accesses_rbac_title",
                        "is_default": False,
                        "children": [],
                        "permissions": [
                            *SECURITY_VALIDATION_USER_ACCESS_PERMISSION_RBAC_TITLE_DB
                        ],
                        "endpoints": [ 
                            {
                                "label": "Chargement des accès de validation des utilisateurs",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": "/api/v1/securities/validations/sudo-actions/fetch/users-sudo-actions-overview"
                            },
                            {
                                "label": "Chargement de l'aperçu des accès sudo des utilisateurs",
                                "is_leaf": True,
                                "is_link_deleted": False,
                                "url": "/api/v1/securities/validations/sudo-actions/fetch/users-sudo-actions-overview"
                            },
                        ],
                    },
                ],
                "permissions": [],
                "endpoints": [],
            },
            {
                "label": "Sécurité au niveau de ligne",
                "flag": "security_app_line_level_rbac_title",
                "is_default": False,
                "children": [
                    {
                        "label": "Aperçu des règles de sécurité",
                        "flag": "security_app_line_level_overview_rbac_title",
                        "is_default": False,
                        "children": [],
                        "permissions": [
                            *SECURITY_RLS_OVERVIEW_PERMISSION_RBAC_DB,
                        ],
                        "endpoints": [],
                    },
                    {
                        "label": "Utilisateurs/groupes de la liste blanche ou la liste noire (RLS)",
                        "flag": "security_app_line_level_whitelist_blacklist_rbac_title",
                        "is_default": False,
                        "children": [],
                        "permissions": [
                            *SECURITY_RLS_WHITELIST_BLACKLIST_USERS_AND_GROUPS_PERMISSION_RBAC_TITLE_DB,
                        ],
                        "endpoints": [],
                    },
                    {
                        "label": "Paramétrage de sécurité RLS",
                        "flag": "security_app_line_level_rls_setup_rbac_title",
                        "is_default": False,
                        "children": [],
                        "permissions": [
                            *SECURITY_RLS_SETUP_PERMISSION_RBAC_TITLE_DB,
                        ],
                        "endpoints": [],
                    },
                    {
                        "label": "Accès RLS des utilisateurs",
                        "flag": "security_app_line_level_user_accesses_rbac_title",
                        "is_default": False,
                        "children": [],
                        "permissions": [
                            *SECURITY_RLS_USER_ACCESS_PERMISSION_RBAC_TITLE_DB,
                        ],
                        "endpoints": [],
                    },
                    
                ],
                "permissions": [],
                "endpoints": [
                    {
                        "label": "Chargement de l'aperçu des règles de sécurité",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/rls/overviews/fetch/overview"
                    },
                    {
                        "label": "Chargement des accès des utilisateurs",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/rls/users-accesses/fetch/user-accesses"
                    },
                    {
                        "label": "Chargement des utilisateurs/groupes de la liste blanche ou la liste noire (RLS)",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/rls/whitelists/fetch/whitelist-rls"
                    },
                    {
                        "label": "Chargement des groupes de sécurité",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/rls/whitelists/fetch/available-groups"
                    },
                    {
                        "label": "Chargement des utilisateurs",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/rls/whitelists/fetch/available-users"
                    },
                    {
                        "label": "Chargement des permissions",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/rls/rls-settings/fetch/formated-permissions"
                    },
                    {
                        "label": "Chargement des groupes de sécurité",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/rls/rls-settings/fetch/available-groups"
                    },
                    {
                        "label": "Chargement des utilisateurs",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/rls/rls-settings/fetch/available-users"
                    },
                    {
                        "label": "Chargement des accès des utilisateurs",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/rls/users-accesses/fetch/user-accesses"
                    },
                    {
                        "label": "Ajout d'un utilisateur/groupe de la liste blanche ou la liste noire (RLS)",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/add/{CollectionKey.CFG_RLS_ACCESS.value}"
                    },
                    {
                        "label": "Suppression d'un utilisateur/groupe de la liste blanche ou la liste noire (RLS)",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_RLS_ACCESS.value}"
                    }, 
                    {
                        "label": "Mise à jour d'un utilisateur/groupe de la liste blanche ou la liste noire (RLS)",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/patch/{CollectionKey.CFG_RLS_ACCESS.value}"
                    },
                    {
                        "label": "Mise à jour des paramètres de protection de la sécurité RLS",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/patch/{CollectionKey.CFG_ORGANIZATION_RLS.value}"
                    },
                    
                ],
            },
            {
                "label": "Paramètrage de sécurité RLS & Actions sudo",
                "flag": "security_app_rls_and_sudo_actions_setting_rbac_title",
                "is_default": False,
                "children": [
                    {
                        "label": "Paramètrage de sécurité RLS",
                        "flag": "security_app_rls_setting_rbac_title",
                        "is_default": False,
                        "children": [],
                        "permissions": [
                            *SECURITY_RLS_SETTING_PERMISSION_RBAC_TITLE_DB,
                        ],
                        "endpoints": [],
                    },
                    {
                        "label": "Paramètrage des actions sudo",
                        "flag": "security_app_sudo_actions_setting_rbac_title",
                        "is_default": False,
                        "children": [],
                        "permissions": [
                            *SECURITY_SUDO_ACTION_SETTING_PERMISSION_RBAC_TITLE_DB,
                        ],
                        "endpoints": [],
                    },
                    
                ],
                "permissions": [],
                "endpoints": [
                    {
                        "label": "Chargement des Paramétrages de sécurité RLS",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/settings/rls/fetch/rls-settings"
                    },
                    {
                        "label": "Chargement des Paramétrages des actions sudo",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/settings/sudo-actions/fetch/sudo-action-settings"
                    },
                    {
                        "label": "Mise à jour des Paramétrages de protection de la sécurité RLS",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/settings/rls/patch/rls-protection-settings"
                    },
                    {
                        "label": "Mise à jour des Paramétrages du mode strict de la sécurité RLS",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/settings/rls/patch/rls-strict-settings"
                    },
                    {
                        "label": "Mise à jour des Paramétrages des actions sudo",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/settings/sudo-actions/patch/sudo-action-settings"
                    },
                ],
            },
            {
                "label": "Logs - Modifications & Suppressions",
                "flag": "security_deletions_and_updates_logs_rbac_title",
                "is_default": False,
                "children": [
                    {
                        "label": "Logs - Modifications",
                        "flag": "security_updates_logs_child_rbac_title",
                        "is_default": False,
                        "children": [],
                        "permissions": [
                            *SECURITY_UPDATE_HISTORIES_PERMISSION_RBAC_TITLE_DB,
                        ],
                        "endpoints": [],
                    },
                    {
                        "label": "Logs - Modifications",
                        "flag": "security_deletions_logs_child_rbac_title",
                        "is_default": False,
                        "children": [],
                        "permissions": [
                            *SECURITY_DELETE_HISTORIES_PERMISSION_RBAC_TITLE_DB,
                        ],
                        "endpoints": [],
                    },
                    
                ],
                "permissions": [],
                "endpoints": [
                    {
                        "label": "Chargement des logs - Suppressions",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/histories/fetch/deletes",
                    }, 
                    {
                        "label": "Chargement des logs - Modifications",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/histories/fetch/updates",
                    },
                    {
                        "label": "Recherche des logs par identifiant",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/histories/search",
                    },
                    {
                        "label": "Consultation des logs par identifiant",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/histories/by-identifier",
                    },
                    {
                        "label": "Restauration depuis les logs - Suppressions",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/histories/restore/delete",
                    },
                    {
                        "label": "Restauration depuis les logs - Modifications",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/histories/restore/update",
                    },
                ],
            },
            {
                "label": "Logs CRUD d'organisation",
                "flag": "security_org_logs_rbac_title",
                "is_default": False,
                "children": [
                    {
                        "label": "Configuration des logs",
                        "flag": "security_org_logs_setup_rbac_title",
                        "is_default": False,
                        "children": [],
                        "permissions": [
                            *SECURITY_LOGS_SETUP_PERMISSION_RBAC_TITLE_DB,
                        ],
                        "endpoints": [],
                    },
                    {
                        "label": "Liste des logs",
                        "flag": "security_org_logs_list_rbac_title",
                        "is_default": False,
                        "children": [],
                        "permissions": [
                            *SECURITY_LOGS_LIST_PERMISSION_RBAC_TITLE_DB,
                        ],
                        "endpoints": [],
                    },
                ],
                "permissions": [],
                "endpoints": [
                    {
                        "label": "Chargement de la configuration des logs",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/logs/fetch/setups",
                    },
                    {
                        "label": "Activation/D\u00e9sactivation des logs",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/logs/patch/setup-enabled",
                    },
                    {
                        "label": "Activation/D\u00e9sactivation des logs CRUD individuels",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/logs/patch/setup-crud-flags",
                    },
                    {
                        "label": "Mise \u00e0 jour de la dur\u00e9e de r\u00e9tention",
                        "is_leaf": True,
                        "is_link_deleted": True,
                        "url": "/api/v1/securities/logs/setup/patch/expiration",
                    },
                    {
                        "label": "Mise \u00e0 jour de la dur\u00e9e de r\u00e9tention",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/logs/patch/setup-expiration",
                    },
                    {
                        "label": "Chargement de la liste des logs",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/logs/fetch/logs",
                    },
                    {
                        "label": "Flux temps r\u00e9el des logs",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": "/api/v1/securities/logs/fetch/streams",
                    },
                ],
            },
        ]
    }
]
