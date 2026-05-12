

from app.modules.core.seeds.rbac_title.notification_permission_title import NOTIFICATION_PERMISSION_RBAC_TITLE_DB
from app.modules.core.seeds.rbac_title.profil_permission_title import PROFIL_ENDPOINTS, PROFIL_PERMISSION_RBAC_TITLE_DB
from app.modules.core.seeds.rbac_title.system_config_permission_title import SYSTEM_CONFIG_PERMISSION_RBAC_TITLE_DB
from app.modules.edocs.seeds.rbac_title.edocs_file_rbac_title import EDOC_FILE_PERMISSION_RBAC_TITLE_DB
from app.modules.edocs.seeds.rbac_title.edocs_folder_rbac_title import EDOC_FOLDER_PERMISSION_RBAC_TITLE_DB
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.security.seeds.rbac.validation_rbac.validation_requested_permission_title import VALIDATION_REQUESTED_PERMISSION_RBAC_TITLE_DB
from app.modules.security.seeds.rbac.security_seed_rbac import SECURITY_SEED_RBAC_TITLE_DB

CORE_RBAC_TITLE_DB = [
    {
        "label":"E-Doc",
        "flag":"edocs_flag",
        "is_default":False,
        "permissions":[],
        "endpoints":[
            {
                "label": "Chargement du résumé de : dossier, fichier, espace utilisé, corbeille", 
                "is_leaf": True, 
                "is_link_deleted": False,
                "url": "/api/v1/edocs/org/resume-stats",  
            }, 
        ],
        "children":[
            {
                "label":"Dossier",
                "flag":"edocs_folder_flag",
                "is_default":False,
                "children":[],
                "permissions":[
                    *EDOC_FOLDER_PERMISSION_RBAC_TITLE_DB
                ],
                "endpoints":[
                    {
                        "label": "Chargement des dossiers", 
                        "is_leaf": True, 
                        "is_link_deleted": False,
                        "url": f"/api/v1/edocs/org/fetch/{CollectionKey.ARCH_FOLDER.value}",
                    }, 
                    {
                        "label": "Aperçu et stats des dossiers", 
                        "is_leaf": True, 
                        "is_link_deleted": False,
                        "url": "/api/v1/edocs/org/data/stats",
                    }, 
                    {
                        "label": "Chargement des dossiers", 
                        "is_leaf": True, 
                        "is_link_deleted": False,
                        "url": "/api/v1/edocs/org/fetch/folders-bin",
                    }, 
                    {
                        "label": "formulaire de création d'un dossier",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/head/{CollectionKey.ARCH_FOLDER.value}"
                    }, 
                    {
                        "label": "formulaire de création d'un dossier enfant",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/child-head/{CollectionKey.ARCH_FOLDER.value}"
                    }, 
                    {
                        "label": "L'url de création d'un dossier",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/add/{CollectionKey.ARCH_FOLDER.value}"
                    }, 
                    {
                        "label": "Suppression des dossiers", 
                        "is_leaf": True, 
                        "is_link_deleted": False,
                        "url": f"/api/v1/edocs/org/hard-delete/{CollectionKey.ARCH_FOLDER.value}",  
                    },
                    {
                    "label": "Chargement de formulaire de Mise à jour des dossiers", 
                        "is_leaf": True, 
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/update-head/{CollectionKey.ARCH_FOLDER.value}",  
                    }, 
                    {
                        "label": "Mise à jour d'un dossier",
                        "is_leaf": True,
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/update/{CollectionKey.ARCH_FOLDER.value}"
                    }, 
                    {
                    "label": "Téléchargement des dossiers", 
                        "is_leaf": True, 
                        "is_link_deleted": False,
                        "url": f"/api/v1/edocs/org/download/{CollectionKey.ARCH_FOLDER.value}",  
                    },
                ],
                
            },
            {
                "label":"Fichier",
                "flag":"edocs_files_flag",
                "is_default":False,
                "children":[],
                "permissions":[
                    *EDOC_FILE_PERMISSION_RBAC_TITLE_DB
                ],
                "endpoints":[
                    {
                    "label": "Accéder à la corbeille des fichiers", 
                        "is_leaf": True, 
                        "is_link_deleted": False,
                        "url": "/api/v1/edocs/org/fetch/files-bin",  
                    },
                    {
                    "label": "Mise à jour des fichiers", 
                        "is_leaf": True, 
                        "is_link_deleted": False,
                        "url": f"/api/v1/generic/org/update/{CollectionKey.ARCH_FILE.value}",
                    },
                    {
                    "label": "Chargement des fichiers", 
                        "is_leaf": True, 
                        "is_link_deleted": False,
                        "url": f"/api/v1/edocs/org/fetch/{CollectionKey.ARCH_FILE.value}",  
                    },
                    {
                    "label": "Suppression des fichiers", 
                        "is_leaf": True, 
                        "is_link_deleted": False,
                        "url": f"/api/v1/edocs/org/hard-delete/{CollectionKey.ARCH_FILE.value}",  
                    },
                    {
                        "label": "Téléchargement des fichiers", 
                        "is_leaf": True, 
                        "is_link_deleted": False,
                        "url": f"/api/v1/edocs/org/download/{CollectionKey.ARCH_FILE.value}",  
                    }, 
                    {
                        "label": "Téléversement des fichiers", 
                        "is_leaf": True, 
                        "is_link_deleted": False,
                        "url": f"/api/v1/edocs/org/add/{CollectionKey.ARCH_FILE.value}",  
                    }, 
                    {
                        "label": "Téléversement des fichiers", 
                        "is_leaf": True, 
                        "is_link_deleted": False,
                        "url": "/api/v1/edocs/org/files/upload",  
                    }, 
                    
                ],
                
            }
        ], 
    },
    {
        "label": "Validations",
        "flag": "validation_app_requests_rbac_title",
        "is_link_deleted": False,
        "is_default": False,
        "children": [
                {
                    "label": "Requête de validations",
                    "flag": "validation_app_request_list_rbac_title",
                    "is_default": True,
                    "is_link_deleted": False,
                    "children": [],
                    "permissions": [
                        *VALIDATION_REQUESTED_PERMISSION_RBAC_TITLE_DB,
                    ],
                    "endpoints": [
                        {
                            "label": "Chargement de l'aperçu des requêtes de validation",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/token-data-overview/{CollectionKey.OPS_VALIDATION_REQUEST.value}",
                        },
                        {
                            "label": "Valider/Rejeter une requête",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/securities/validations/requests/validate-or-reject",
                        },
                        {
                            "label": "Chargement des requêtes de validation en attente",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/securities/validations/requests/pending",
                        },
                        {
                            "label": "Chargement d'une requête de validation",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/securities/validations/requests/single",
                        },
                        {
                            "label": "Chargement de l'aperçu des requêtes de validation",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/data-overview/{CollectionKey.OPS_VALIDATION_REQUEST.value}",
                        },
                        {
                            "label": "Connexion au websocket",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/websocket/ws",
                        },
                        {
                            "label": " Chargement des notifications en attente via websocket",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/websocket/pending-notifications",
                        },
                        {
                            "label": "Envoi d'un pong via websocket",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/websocket/send-pong",
                        },
                        {
                            "label": "Envoi d'une action via websocket",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/websocket/send-action",
                        },
                        {
                            "label": "Chargement des requêtes de validation",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/static/data/get-validation-requests",
                        },
                        {
                            "label": "Valider/Rejeter une requête",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/static/data/validate-or-reject-validation-request",
                        },
                        {
                            "label": "Chargement de la vue des requêtes de validation",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/static/data/get-validation-request-view",
                        },
                    ],
                },
        ],
        "permissions": [],
        "endpoints": [],
    },
    {
        "label": "Notification",
        "flag": "user_notifications",
        "is_link_deleted": False,
        "is_default": True,
        "permissions": [
            *NOTIFICATION_PERMISSION_RBAC_TITLE_DB
        ],
        "endpoints": [
            {
                "label": "Chargement des notifications personnelles",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/specifics/fetch/user-own/ntfNotifications",
            },
            {
                "label": "Suppression des notifications personnelles",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/specifics/hard-delete/user-own/ntfNotifications",
            },
            {
                "label": "Lecture des nouvelles notifications personnelles",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/specifics/read/user-own/ntfNotifications"
            },
            {
                "label": "Chargement des notifications",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/get-notifications"
            },
        ],
    },
     
    {
        "label": "Système configs",
        "flag": "system_configs",
        "is_link_deleted": False,
        "is_default": False,
        "permissions": [
            *SYSTEM_CONFIG_PERMISSION_RBAC_TITLE_DB
        ],
        "endpoints": [
            {
                "label": "Chargement de permissions d'un profil",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-profile-permissions"
            },
            {
                "label": "Chargement de permissions extended d'un profil",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-extended-profile-permissions"
            },
            {
                "label": "Vérification d'accès sur core",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/check-core-access"
            },
            {
                "label": "Chargement du formulaire de mise à jour d'une permission",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update-head/{CollectionKey.RBAC_PERMISSION.value}"
            },

            # RBAC TITLES
            {
                "label": "Chargement du formulaire de création d'un titre rbac",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/head/{CollectionKey.RBAC_TITLE.value}"
            },
            {
                "label": "Chargement du formulaire de création d'un enfant rbac",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/child-head/{CollectionKey.RBAC_TITLE.value}"
            },
            {
                "label": "Mise à jour d'un titre rbac",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update/{CollectionKey.RBAC_TITLE.value}"
            },
            {
                "label": "Création d'un titre rbac",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/add/{CollectionKey.RBAC_TITLE.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour d'un titre rbac",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update-head/{CollectionKey.RBAC_TITLE.value}"
            },
            {
                "label": "Suppression d'un titre rbac",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/hard-delete/{CollectionKey.RBAC_TITLE.value}"
            },
            # END RBAC TITLES

            # RBAC PERMISSIONS
            {
                "label": "Création d'une permission",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/add/{CollectionKey.RBAC_PERMISSION.value}"
            },
            {
                "label": "Chargement du formulaire de création d'une permission",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/head/{CollectionKey.RBAC_PERMISSION.value}"
            },
            {
                "label": "Mise à jour d'une permission",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update/{CollectionKey.RBAC_PERMISSION.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour d'une permission",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update-head/{CollectionKey.RBAC_PERMISSION.value}"
            },
            {
                "label": "Suppression d'une permission",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/hard-delete/{CollectionKey.RBAC_PERMISSION.value}"
            },
            # END RBAC PERMISSIONS

            # RBAC ENDPOINTS
            {
                "label": "Chargement du formulaire de création d'un endpoint",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/head/{CollectionKey.RBAC_ENDPOINT.value}"
            },
            {
                "label": "Création d'un endpoint",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/add/{CollectionKey.RBAC_ENDPOINT.value}"
            },
            {
                "label": "Mise à jour d'un endpoint",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update/{CollectionKey.RBAC_ENDPOINT.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour d'un endpoint",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update-head/{CollectionKey.RBAC_ENDPOINT.value}"
            },
            {
                "label": "Suppression d'un endpoint",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/hard-delete/{CollectionKey.RBAC_ENDPOINT.value}"
            },
            # END RBAC ENDPOINTS

            {
                "label": "Chargement des profils api consumer",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/get-api-consumer-profiles"
            },
            {
                "label": "Chargement des rôles pour la configs",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-config-roles"
            },
            {
                "label": "Chargement des types d'affichage des enfants",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-config-children-display-type"
            },
            {
                "label": "Chargement des actions de configuration",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-config-rbac-actions"
            },
            {
                "label": "Chargement des sous-permissions de configuration",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-simplified-config-sub-permissions"
            },
            {
                "label": "Chargement des sous-endpoints de configuration",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-simplified-config-sub-endpoints"
            },
            {
                "label": "Chargement des menus de configuration",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-config-standalone-menu"
            },
            {
                "label": "Chargement des sous-menus d'une application",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-simplified-config-application-menus"
            },
            {
                "label": "Chargement des applications de configuration",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-simplified-config-applications"
            },
            {
                "label": "Chargement des guards de configuration",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-config-path-guards"
            },
            {
                "label": "Chargement des permissions de configuration",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-simplified-config-permissions"
            },
            {
                "label": "Chargement des types d'affichage des données",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-config-data-display-type"
            },

            # START COLLECTION META DATA
            {
                "label": "Chargement des données meta des collections",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-config-collection-meta-data"
            },
            {
                "label": "Chargement du formulaire de création des données meta des collections",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/head/{CollectionKey.REF_COLLECTION_CRUD_INFO.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour des données meta des collections",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update-head/{CollectionKey.REF_COLLECTION_CRUD_INFO.value}"
            },
            {
                "label": "Mise à jour des données meta des collections",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update/{CollectionKey.REF_COLLECTION_CRUD_INFO.value}"
            },
            {
                "label": "Suppression des données meta des collections",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/hard-delete/{CollectionKey.REF_COLLECTION_CRUD_INFO.value}"
            },
            # END COLLECTION META DATA


            # START DATA DISPLAY TYPE
            {
                "label": "Chargement des types d'affichage des données",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-custom-config-data-display-type"
            },
            {
                "label": "Chargement du formulaire de création des types d'affichage des données",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/head/{CollectionKey.CFG_DATA_DISPLAY_TYPE.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour des types d'affichage des données",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update-head/{CollectionKey.CFG_DATA_DISPLAY_TYPE.value}"
            },
            {
                "label": "Mise à jour des types d'affichage des données",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update/{CollectionKey.CFG_DATA_DISPLAY_TYPE.value}"
            },
            {
                "label": "Suppression des types d'affichage des données",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/hard-delete/{CollectionKey.CFG_DATA_DISPLAY_TYPE.value}"
            },
            {
                "label": "Création des types d'affichage des données",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/add/{CollectionKey.CFG_DATA_DISPLAY_TYPE.value}"
            },
            # END DATA DISPLAY TYPE

            # START CHILDREN DISPLAY TYPE
            {
                "label": "Chargement des types d'affichage des données enfants",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/cores/get-custom-config-children-display-type"
            },
            {
                "label": "Chargement du formulaire de création des types d'affichage des données enfants",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/head/{CollectionKey.CFG_CHILDREN_DISPLAY_TYPE.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour des types d'affichage des données enfants",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update-head/{CollectionKey.CFG_CHILDREN_DISPLAY_TYPE.value}"
            },
            {
                "label": "Mise à jour des types d'affichage des données enfants",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update/{CollectionKey.CFG_CHILDREN_DISPLAY_TYPE.value}"
            },
            {
                "label": "Suppression des types d'affichage des données enfants",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/hard-delete/{CollectionKey.CFG_CHILDREN_DISPLAY_TYPE.value}"
            },
            {
                "label": "Création des types d'affichage des données enfants",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/add/{CollectionKey.CFG_CHILDREN_DISPLAY_TYPE.value}"
            },
            # END CHILDREN DISPLAY TYPE

            # START ACTIONS
            {
                "label": "Chargement des actions",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/head/{CollectionKey.RBAC_ACTION.value}"
            },
            {
                "label": "Chargement du formulaire de création des actions",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/head/{CollectionKey.RBAC_ACTION.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour des actions",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update-head/{CollectionKey.RBAC_ACTION.value}"
            },
            {
                "label": "Mise à jour des actions",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update/{CollectionKey.RBAC_ACTION.value}"
            },
            {
                "label": "Suppression des actions",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/hard-delete/{CollectionKey.RBAC_ACTION.value}"
            },
            {
                "label": "Création des actions",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/add/{CollectionKey.RBAC_ACTION.value}"
            },
            # END ACTIONS

            # START COMPONENTS
            {
                "label": "Chargement des composants",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/head/{CollectionKey.RBAC_COMPONENT.value}"
            },
            {
                "label": "Chargement du formulaire de création des composants",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/head/{CollectionKey.RBAC_COMPONENT.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour des composants",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update-head/{CollectionKey.RBAC_COMPONENT.value}"
            },
            {
                "label": "Mise à jour des composants",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update/{CollectionKey.RBAC_COMPONENT.value}"
            },
            {
                "label": "Suppression des composants",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/hard-delete/{CollectionKey.RBAC_COMPONENT.value}"
            },
            {
                "label": "Création des composants",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/add/{CollectionKey.RBAC_COMPONENT.value}"
            },
            # END COMPONENTS

        ],

    },

    {
        "label": "Paramètres",
        "flag": "app_settings",
        "is_link_deleted": False,
        "is_default": False,
        "children": [
                {
                    "label": "Les utilisateurs",
                    "flag": "app_settings_users",
                    "is_link_deleted": False,
                    "is_default": False,
                    "children": [],
                    "permissions": [],
                    "endpoints": [
                        {
                            "label": "Chargement des utilisateurs hors organigramme",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/fetch/{CollectionKey.SYS_USER.value}"
                        },
                        {
                            "label": "Mise à jour des périphériques des utilisateurs",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/update/{CollectionKey.CFG_USER_DEVICE.value}"
                        },
                        {
                            "label": "Suppression d'un utilisateur hors organigramme",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.SYS_USER.value}"
                        },
                        {
                            "label": "Recherche d'un utilisateur hors organigramme",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/users/org-search"
                        },
                        {
                            "label": "Mise à jour d'un utilisateur hors organigramme",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/update/{CollectionKey.SYS_USER.value}"
                        },
                        {
                            "label": "Chargement du formulaire de Mise à jour d'un utilisateur hors organigramme",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/update-head/{CollectionKey.SYS_USER.value}"
                        },
                        {
                            "label": "création d'un utilisateur hors organigramme",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/organizations/add/{CollectionKey.SYS_USER.value}"
                        },
                        {
                            "label": "Mise à jour du nombre de device d'un utilisateur",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/organizations/update/user-device-count"
                        },
                        {
                            "label": "création des privilèges pour un utilisateur",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/organizations/add/user-privileges"
                        },
                        {
                            "label": "Chargement du formulaire de création des privilèges pour un utilisateur",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/organizations/head/user-privileges"
                        },
                        {
                            "label": "Chargement du formulaire de création d'un utilisateur hors organigramme",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/head/{CollectionKey.SYS_USER.value}"
                        },
                        {
                            "label": "Génération du lien de réinitialisation du mot de passe",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/organizations/generate-reset-password-link"
                        },
                    ],
                },
            {
                    "label": "Rôles",
                    "flag": "app_settings_organization_global_roles",
                    "is_default": False,
                    "is_link_deleted": False,
                    "children": [],
                    "permissions": [],
                    "endpoints": [],

                },
            {
                "label": "Profil rbac",
                "flag": "app_settings_organization_outof_chart_profiles",
                "is_link_deleted": False,
                "is_default": False,
                "children": [],
                "permissions": [],
                "endpoints": [
                    {
                            "label": "Le endpoint pour le chargement des profils rbac",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/fetch/{CollectionKey.RBAC_PROFILE.value}"
                        },
                    {
                            "label": "Le endpoint pour le chargement des permissions d'un profil rbac",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/static/data/org/get-profile-permissions"
                        },
                        {
                            "label": "Le endpoint pour le chargement des permissions avancées d'un profil rbac",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/static/data/org/get-extended-profile-permissions"
                        },
                        {
                            "label": "Le endpoint pour la mis à jour des permissions d'un profil rbac",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/static/data/org/upsert-profile-permissions"
                        },
                        
                        {
                            "label": "Le endpoint pour la mis à jour des permissions avancées d'un profil rbac",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/static/data/org/upsert-extended-profile-permissions"
                        },

                        {
                            "label": "Suppression des profils rbac",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/static/data/org/delete-profile"
                        },

                        {
                            "label": "L'url de création d'un profil",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/static/data/org/create-profile"
                        },
                        {
                            "label": "[system] L'url de création d'un profil",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/static/data/create-profile"
                        },
                        {
                            "label": "formulaire de création d'un profil",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/head/{CollectionKey.RBAC_PROFILE.value}"
                        },
                        {
                            "label": "[system] formulaire de création d'un profil",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/head/{CollectionKey.RBAC_PROFILE.value}"
                        },
                        {
                            "label": "Mise à jour d'un profil",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/update/{CollectionKey.RBAC_PROFILE.value}"
                        },
                        {
                            "label": "formulaire de mise à d'un profil",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/update-head/{CollectionKey.RBAC_PROFILE.value}"
                        },
                ],
                },
                {
                    "label": "Banques",
                    "flag": "app_settings_organization_banks",
                    "is_default": False,
                    "is_link_deleted": False,
                    "children": [],
                    "permissions": [],
                    "endpoints": [
                        
                    ],

            },
            {
                    "label": "Configuration des banques",
                    "flag": "app_settings_organization_bank_configs",
                    "is_default": False,
                    "children": [],
                    "permissions": [],
                    "endpoints": [
                        {
                            "label": "Le endpoint pour le chargement des banque",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/fetch/{CollectionKey.REF_BANK.value}"
                        },
                        # /system-config/get-config-bank + /system-config/
                        # get-one-config-bank entries removed 2026-05-04
                        # along with their controller — TRANSCO bank surface
                        # is not part of Senat-Digit.
                        {
                            "label": "Suppression des banque",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/hard-delete/{CollectionKey.REF_BANK.value}"
                        },

                        {
                            "label": "L'url de création d'une banque",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/add/{CollectionKey.REF_BANK.value}"
                        },
                        {
                            "label": "formulaire de création d'une banque",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/head/{CollectionKey.REF_BANK.value}"
                        },
                        {
                            "label": "Mise à jour d'une banque",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/update/{CollectionKey.REF_BANK.value}"
                        },
                        {
                            "label": "formulaire de mise à d'une banque",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/update-head/{CollectionKey.REF_BANK.value}"
                        },
                    ],

            },
            # {
            #         "label": "Pays système",
            #         "flag": "app_settings_organization_systems_countries",
            #         "is_default": False,
            #         "children": [],
            #         "permissions": [
            #             *APP_SYSTEM_COUNTRY_PERMISSION_RBAC_TITLE_DB
            #         ],
            #         "endpoints": [],

            # },
            {
                    "label": "Bénéficiaires",
                    "flag": "app_settings_organization_beneficiaries",
                    "is_default": False,
                    "children": [],
                    "permissions": [],
                    "endpoints": [
                        {
                            "label": "Le endpoint pour le chargement des bénéficiares (Personne morale)",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/fetch/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}"
                        },
                        {
                            "label": "Le endpoint pour le chargement des bénéficiares (Personne physique)",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/fetch/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}"
                        },
                        # fetch
                        {
                            "label": "Suppression des bénéficiares (Personne morale)",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}"
                        },
                        {
                            "label": "Suppression des bénéficiares (Personne physique)",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}"
                        },
                        # delete
                        {
                            "label": "L'url de création d'un bénéficiare (Personne morale)",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/add/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}"
                        },
                        {
                            "label": "L'url de création d'un bénéficiare (Personne physique)",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/add/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}"
                        },
                        # create
                        {
                            "label": "formulaire de création d'un bénéficiare (Personne morale)",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/head/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}"
                        },
                        {
                            "label": "formulaire de création d'un bénéficiare (Personne physique)",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/head/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}"
                        },
                        # update
                        {
                            "label": "Mise à jour d'un bénéficiare (Personne morale)",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/update/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}"
                        },
                        {
                            "label": "Mise à jour d'un bénéficiare (Personne physique)",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/update/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}"
                        },
                        # udpate
                        {
                            "label": "formulaire de mise à d'un bénéficiare (Personne morale)",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/update-head/{CollectionKey.CFG_LEGAL_BENEFICIARY.value}"
                        },
                        {
                            "label": "formulaire de mise à d'un bénéficiare (Personne physique)",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/update-head/{CollectionKey.CFG_PHYSICAL_BENEFICIARY.value}"
                        },
                    ],

                    },
            
            {
                    "label": "Devises",
                    "flag": "app_settings_currencies",
                    "is_default": False,
                    "children": [],
                    "permissions": [],
                    "endpoints": [

                        {
                            "label": "Chargements des devises",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/fetch/{CollectionKey.REF_CURRENCY.value}"
                        },
                        {
                            "label": "[system] Suppression des devises",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/hard-delete/{CollectionKey.REF_CURRENCY.value}",
                        },
                        {
                            "label": "[system] Création des devises",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/add/{CollectionKey.REF_CURRENCY.value}"
                        },
                        {
                            "label": "chargement du formulaire de création des devises",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/head/{CollectionKey.REF_CURRENCY.value}"
                        },
                        {
                            "label": "[system] Mise à jour des devises",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/update/{CollectionKey.REF_CURRENCY.value}"
                        },
                        {
                            "label": "[system] chargement du formulaire de mise à jour des devises",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/uphead/{CollectionKey.REF_CURRENCY.value}"
                        },
                    ],

                    },
            {
                    "label": "Taux de change",
                    "flag": "app_settings_currencies_exchanges",
                    "is_default": False,
                    "children": [],
                    "permissions": [],
                    "endpoints": [
                        {
                            "label": "Chargements du formulaire de mise à jour taux de change",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/update-head/{CollectionKey.CFG_CURRENCY_EXCHANGE.value}",
                        },
                        {
                            "label": "Chargements de taux de change",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/fetch/{CollectionKey.CFG_CURRENCY_EXCHANGE.value}",
                        },
                        {
                            "label": "chargements de paires de devises",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/static/data/get-exchanges-config"
                        },
                        {
                            "label": "Ajout de taux de change",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/add/{CollectionKey.CFG_CURRENCY_EXCHANGE.value}"
                        },
                        {
                            "label": "Suppression de taux de change",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_CURRENCY_EXCHANGE.value}"
                        },
                        {
                            "label": "Chargement du formulaire de création de taux de change",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/head/{CollectionKey.CFG_CURRENCY_EXCHANGE.value}",
                        },
                        {
                            "label": "Mise à jour de taux de change",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/update/{CollectionKey.CFG_CURRENCY_EXCHANGE.value}",
                        },
                        {
                            "label": "Historisation de taux de change",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/static/data/update-currency-exchanges",
                        },
                        {
                            "label": "Chargement de pair des devises pour la création",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/static/org/data/get-exchanges-config",
                        },
                        {
                            "label": "Chargement du formulaire de mise à jour de taux de change",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/uphead/{CollectionKey.CFG_CURRENCY_EXCHANGE.value}",
                        },
                    ],

                    },
            {
                    "label": "Entités",
                    "flag": "app_settings_entities",
                    "is_default": False,
                    "children": [],
                    "permissions": [],
                    "endpoints": [
                        {
                            "label": "[system] Chargement des entités",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/fetch/{CollectionKey.REF_ENTITY.value}",
                        },
                        {
                            "label": "[system] Suppression des entités par le système",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/hard-delete/{CollectionKey.REF_ENTITY.value}",
                            "description_str": "suppression des entités par le système"
                        },
                        {
                            "label": "[system] Création d'une entité par le système",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/add/{CollectionKey.REF_ENTITY.value}",
                            "description_str": "création d'une entité par le système"
                        },
                        {
                            "label": "[system] Chargement de formulaire de création d'une entité",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/head/{CollectionKey.REF_ENTITY.value}",
                            "description_str": "formulaire dynamique de création d'une entité par le système"
                        },
                        {
                            "label": "[system] Chargement de formulaire de création d'une entité",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/child-head/{CollectionKey.REF_ENTITY.value}",
                            "description_str": "formulaire dynamique de création d'une entité par le système"
                        },
                        {
                            "label": "[system] Mise à jour des entités par le système",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/update/{CollectionKey.REF_ENTITY.value}",
                            "description_str": "mise à jour des entités par le système"
                        },
                        {
                            "label": "[system] Chargement de formulaire de mise à jour d'une entité",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/update-head/{CollectionKey.REF_ENTITY.value}",
                            "description_str": "formulaire dynamique de mise à jour d'une entité par le système"
                        },
                        
                    ],

                    },
            {
                    "label": "Templates",
                    "flag": "app_settings_templates",
                    "is_default": False,
                    "children": [],
                    "permissions": [],
                    "endpoints": [
                        # TEMPLATES
                        {
                            "label": "Chargement des templates",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/fetch/{CollectionKey.REF_DOCUMENT_TEMPLATE.value}",
                        },
                        {
                            "label": "Suppression des templates",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/hard-delete/{CollectionKey.REF_DOCUMENT_TEMPLATE.value}",
                            "description_str": "suppression des templates"
                        },
                        {
                            "label": "Création d'un template",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/add/{CollectionKey.REF_DOCUMENT_TEMPLATE.value}",
                            "description_str": "création d'un templates"
                        },
                        {
                            "label": "Chargement du formulaire de création d'un template",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/head/{CollectionKey.REF_DOCUMENT_TEMPLATE.value}",
                            "description_str": "Chargement du formulaire de création d'un templates"
                        },
                        {
                            "label": "Chargement du formulaire de mise à jour d'un template",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/update-head/{CollectionKey.REF_DOCUMENT_TEMPLATE.value}",
                            "description_str": "Chargement du formulaire de mise à jour d'un templates"
                        },
                        # TEMPLATES TYPES
                        {
                            "label": "Chargement des types des templates",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/fetch/{CollectionKey.REF_DOCUMENT_TEMPLATE_TYPE.value}",
                        },
                        {
                            "label": "Suppression des types des templates",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/hard-delete/{CollectionKey.REF_DOCUMENT_TEMPLATE_TYPE.value}",
                            "description_str": "suppression des types des templates"
                        },
                        {
                            "label": "Création d'un type des templates",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/add/{CollectionKey.REF_DOCUMENT_TEMPLATE_TYPE.value}",
                            "description_str": "création d'un type des templates"
                        },
                        {
                            "label": "Chargement du formulaire de création d'un type des templates",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/head/{CollectionKey.REF_DOCUMENT_TEMPLATE_TYPE.value}",
                            "description_str": "Chargement du formulaire de création d'un type des templates"
                        },
                        {
                            "label": "Mise à jour d'un type des templates",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/update/{CollectionKey.REF_DOCUMENT_TEMPLATE_TYPE.value}",
                            "description_str": "Mise à jour d'un type des templates"
                        },
                        {
                            "label": "Chargement du formulaire de mise à jour d'un type des templates",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/update-head/{CollectionKey.REF_DOCUMENT_TEMPLATE_TYPE.value}",
                            "description_str": "Chargement du formulaire de mise à jour d'un type des templates"
                        },
                        # TEMPLATES PAGES
                        {
                            "label": "Chargement des pages d'un template",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/fetch/{CollectionKey.REF_DOCUMENT_TEMPLATE_PAGE.value}",
                        },
                        {
                            "label": "Suppression des pages d'un template",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/hard-delete/{CollectionKey.REF_DOCUMENT_TEMPLATE_PAGE.value}",
                            "description_str": "suppression des pages des templates"
                        },
                        {
                            "label": "Création d'une page d'un template",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/add/{CollectionKey.REF_DOCUMENT_TEMPLATE_PAGE.value}",
                            "description_str": "création d'une page d'un template"
                        },
                        {
                            "label": "Chargement du formulaire de création d'une page d'un template",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/head/{CollectionKey.REF_DOCUMENT_TEMPLATE_PAGE.value}",
                            "description_str": "Chargement du formulaire de création d'une page d'un template"
                        },
                        {
                            "label": "Chargement du formulaire de mise à jour d'une page d'un template",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/update-head/{CollectionKey.REF_DOCUMENT_TEMPLATE_PAGE.value}",
                            "description_str": "Chargement du formulaire de mise à jour d'une page d'un template"
                        },
                    ],

                    },

        ],
        "permissions": [],
        "endpoints": [
            {
                "label": "Suppression des disponibilités dans des entités",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/hard-delete/{CollectionKey.CFG_ENTITY_AVAILABILITY.value}"
            },
            {
                "label": "Création des disponibilités dans des entités",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/add/{CollectionKey.CFG_ENTITY_AVAILABILITY.value}"
            },
            {
                "label": "Chargement du formulaire de création des disponibilités dans des entités",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/head/{CollectionKey.CFG_ENTITY_AVAILABILITY.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour des disponibilités dans des entités",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update-head/{CollectionKey.CFG_ENTITY_AVAILABILITY.value}"
            },
            {
                "label": "Mise à jour des disponibilités dans des entités",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update/{CollectionKey.CFG_ENTITY_AVAILABILITY.value}"
            },

            {
                "label": "Suppression des disponibilités dans des entités",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/hard-delete/{CollectionKey.CFG_ENTITY_AVAILABILITY.value}"
            },
            {
                "label": "Création des disponibilités dans des entités",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/add/{CollectionKey.CFG_ENTITY_AVAILABILITY.value}"
            },
            {
                "label": "Chargement du formulaire de création des disponibilités dans des entités",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/head/{CollectionKey.CFG_ENTITY_AVAILABILITY.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour des disponibilités dans des entités",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update-head/{CollectionKey.CFG_ENTITY_AVAILABILITY.value}"
            },
            {
                "label": "Mise à jour des disponibilités dans des entités",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update/{CollectionKey.CFG_ENTITY_AVAILABILITY.value}"
            },

            # SYSTEM COUNTRIES
            {
                "label": "Mise à jour d'un pays système",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update/{CollectionKey.CFG_SYSTEM_COUNTRY.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour d'un pays ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update-head/{CollectionKey.CFG_SYSTEM_COUNTRY.value}"
            },
            {
                "label": "Suppression d'un pays système",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/hard-delete/{CollectionKey.CFG_SYSTEM_COUNTRY.value}"
            },
            {
                "label": "Chargement des pays système ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/fetch/{CollectionKey.CFG_SYSTEM_COUNTRY.value}"
            },
            {
                "label": "Chargement du formulaire de création d'un pays ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/head/{CollectionKey.CFG_SYSTEM_COUNTRY.value}"
            },
            {
                "label": "Création d'un pays système",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/add/{CollectionKey.CFG_SYSTEM_COUNTRY.value}"
            },
            {
                "label": "Création d'un pays ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/add/system-country"
            },
            {
                "label": "Chargement de la config d'un pays ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/fetch/check-system-country-configuration"
            },
            {
                "label": "Chargement de la devise par défaut d'un pays ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/fetch/current-entity-default-currency"
            },
            # /api/v1/system-countries/countries/fetch/current-entity-info
            {
                "label": "Chargement des informations d'un pays ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/fetch/current-entity-info"
            },
            # update default currency
            {
                "label": "Mise à jour de la devise par défaut d'un pays ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/update/current-entity-default-currency"
            },
            # /countries/patch/current-entity-flag
            {
                "label": "Mise à jour du flag d'un pays ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/patch/current-entity-flag"
            },

            {
                "label": "Chargement du formulaire de création d'un pays ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/head/system-country"
            },
            {
                "label": "Chargement des pays système ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/fetch/system-countries"
            },
            # /api/v1/system-countries/countries/fetch/entities
            {
                "label": "Chargement des entités",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/fetch/entities"
            },
            {
                "label": "Chargement des pays système pour l'application",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/fetch/app-system-countries"
            },
            {
                "label": "Chargement des pays système qui n'existent pas pour l'application",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/fetch/app-no-existing-system-countries"
            },
            {
                "label": "Chargement des réseaux téléphoniques",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/telephone-networks/fetch/telnets"
            },
            {
                "label": "Suppression des groupes de pays liés à une application",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/hard-delete/{CollectionKey.CFG_COUNTRY_RELATED_APPLICATION_GROUP.value}"
            },
            {
                "label": "Création des groupes de pays liés à une application",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/add/{CollectionKey.CFG_COUNTRY_RELATED_APPLICATION_GROUP.value}"
            },
             {
                "label": "Chargement des préfixes des wallets",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/ewallet-prefixes/fetch/ewallet-prefixes"
            },
            {
                "label": "Chargement des préfixes des réseaux téléphoniques",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/telephone-networks/fetch/telnet-prefixes"
            },
            {
                "label": "Suppression d'un réseau téléphonique",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/telephone-networks/delete/telephone-network"
            },

            {
                "label": "Chargement des pays système  qui n'existent pas",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/fetch/no-existing-countries"
            },
            {
                "label": "Chargement de tous les pays système",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/fetch/all-existing-countries"
            },
            {
                "label": "Chargement de tous les pays système et devises",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/fetch/all-system-country-and-currencies"
            },
            {
                "label": "Chargement des devises disponible pour un pays ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/fetch/system-country-availlable-currencies"
            },
            {
                "label": "Chargement des codes pays",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/fetch/system-country-country-codes"
            },
            {
                "label": "Chargement des devises d'un pays",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/fetch/system-country-currencies"
            },
            # delete
            {
                "label": "Suppression d'un pays ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/delete/system-country"
            },

            {
                "label": "Ajout ou suppression d'un code pays ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/patch/add-remove-country-code"
            },
            {
                "label": "Ajout ou suppression d'une devise ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/patch/add-remove-currency"
            },
            {
                "label": "Ajout ou suppression d'un préfixe téléphone ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/patch/add-remove-country-phone-prefix"
            },
            {
                "label": "Ajout ou suppression d'un préfixe wallet ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/patch/add-remove-wallet-prefix"
            },
            {
                "label": "Contraindre la vérification des email/numéro de téléphone dans le cas d'un transfert ",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/system-countries/countries/patch/validate-email-phone-number-transfer-required"
            },


            # TELEPHONE NETWORKS
            {
                "label": "Ajout d'un réseau téléphonique",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/add/{CollectionKey.REF_TELEPHONE_NETWORK.value}"
            },
            {
                "label": "Suppression d'un réseau téléphonique",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/hard-delete/{CollectionKey.REF_TELEPHONE_NETWORK.value}"
            },
            {
                "label": "Mise à jour d'un réseau téléphonique",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update/{CollectionKey.REF_TELEPHONE_NETWORK.value}"
            },
            {
                "label": "Chargement du formulaire de mise à jour d'un réseau téléphonique",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/update-head/{CollectionKey.REF_TELEPHONE_NETWORK.value}"
            },
            {
                "label": "Chargement du formulaire de création d'un réseau téléphonique",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/head/{CollectionKey.REF_TELEPHONE_NETWORK.value}"
            }, 
        ],
    },
    {
        "label": "Ressources humaines",
        "flag": "apps_ressources_humaines",
        "is_default": False,
        "children": [
            {
                "label": "Organigramme",
                "flag": "apps_ressources_humaines_organization_chart_flag",
                "is_default": False,
                "children": [],
                "permissions": [],
                "endpoints": [],
            },
            {
                    "label": "Les utilisateurs",
                    "flag": "apps_ressources_humaines_users",
                    "is_default": False,
                    "children": [],
                    "permissions": [],
                    "endpoints": [
                        # USER DEVICES
                        {
                            "label": "Chargement des devices des utilisateurs",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/fetch/{CollectionKey.CFG_USER_DEVICE.value}",
                        },
                        {
                            "label": "Suppression des devices des utilisateurs",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_USER_DEVICE.value}",
                        },

                        # USER LOGIN HISTORY
                        {
                            "label": "Chargement des historiques de connexion des utilisateurs",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/fetch/{CollectionKey.OPS_USER_LOGIN_HISTORY.value}",
                        },
                        {
                            "label": "Chargement des historiques de connexion des utilisateurs",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": "/api/v1/organizations/fetch/user-login-histories",
                        },
                        {
                            "label": "Suppression des historiques de connexion des utilisateurs",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.OPS_USER_LOGIN_HISTORY.value}",
                        },

                        # USER MFA
                        {
                            "label": "Chargement des configurations MFA des utilisateurs",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/fetch/{CollectionKey.CFG_USER_MFA.value}",
                        },
                        {
                            "label": "Suppression des configurations MFA des utilisateurs",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.CFG_USER_MFA.value}",
                        },

                        # USER PRIVILEGES
                        {
                            "label": "Chargement des privilèges des utilisateurs",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/fetch/{CollectionKey.RBAC_PRIVILEGE.value}",
                        },
                        {
                            "label": "Suppression des privilèges des utilisateurs",
                            "is_leaf": True,
                            "is_link_deleted": False,
                            "url": f"/api/v1/generic/org/hard-delete/{CollectionKey.RBAC_PRIVILEGE.value}",
                        },

                    ],
                },
            {
                    "label": "Rôles",
                    "flag": "apps_ressources_humaines_organization_global_roles",
                    "is_default": False,
                    "children": [],
                    "permissions": [],
                    "endpoints": [

                    ],

                    },
            {
                "label": "Profil rbac",
                "flag": "apps_ressources_humaines_organization_outof_chart_profiles",
                "is_default": False,
                "children": [],
                "permissions": [],
                "endpoints": [],
                    }


        ],
        "permissions": [],
        "endpoints": [],
    },
    {
        "label": "Profil",
        "flag": "user_profil_info",
        "children": [],
        "is_default": True,
        "permissions": [
            *PROFIL_PERMISSION_RBAC_TITLE_DB,
        ],
        "endpoints": [
            *PROFIL_ENDPOINTS
        ]
    },
    {
        "label": "Administration",
        "flag": "main_app_administration",
        "is_default": False,
        "children": [],
        "permissions": [],
        "endpoints": [],
    },
    # {
    #     "label": "Configuration",
    #     "flag": "configuration",
    #     "is_default": False,
    #     "children": [
    #         *CONFIGURATION_SEED_RBAC_TITLE_DB,
    #     ],
    #     "permissions": [],
    #     "endpoints": [],
    # },

    # SECURITY TITLES
    *SECURITY_SEED_RBAC_TITLE_DB,

]
