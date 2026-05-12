
from app.modules.core.models.mapping_keys import CollectionKey


# ──────────────────────────────────────────────────
# STATIC PERMISSIONS
# ──────────────────────────────────────────────────

ACCESSING_ALL_SAAS_SOCKET_SETUP_DATA_PERMISSION_ITEM = {
    "flag": "accessing_all_saas_socket_setup_data",
    "label": "Accès au socket",
    "description_str": "",
    "is_link_deleted": False,
}

LOADING_ALL_SAAS_DEFAULT_SETUP_DATA_PERMISSION_ITEM = {
    "flag": "loading_all_saas_default_setup_data",
    "label": "Chargement des données fonctionnelles",
    "description_str": "",
    "is_link_deleted": False,
}

SET_OR_UPDATE_ALL_SAAS_DEFAULT_SETUP_DATA_PERMISSION_ITEM = {
    "flag": "set_or_update_all_saas_default_setup_data",
    "label": "Configuration des données fonctionnelles",
    "description_str": "",
    "is_link_deleted": False,
}


# ──────────────────────────────────────────────────
# EXPORT
# ──────────────────────────────────────────────────

PROFIL_PERMISSION_RBAC_TITLE_DB = [
    {
        **ACCESSING_ALL_SAAS_SOCKET_SETUP_DATA_PERMISSION_ITEM,
        "is_default": True,
        "menu_accessible_to_all_profil_flag": "accessible_user_profil_info",
        "is_accessible_to_all_profil": True,
        "all_access_core_seeds": {
            "fetch_url": [
                {
                    "hard_code_flag": "user_loading_agents_applications_url",
                    "rbac_endpoint": "/api/v1/static/data/get-agent-applications",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },
                {
                    "hard_code_flag": "user_loading_notifications_url",
                    "rbac_endpoint": "/api/v1/static/data/get-notifications",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },
                {
                    "hard_code_flag": "user_send_lock_webapp_screen",
                    "rbac_endpoint": "/api/v1/sudo-actions/send-lock-screen",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },
                {
                    "hard_code_flag": "user_init_sudo_action_url",
                    "rbac_endpoint": "/api/v1/sudo-actions/init-sudo-action",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },
                {
                    "hard_code_flag": "user_validate_sudo_action_url",
                    "rbac_endpoint": "/api/v1/sudo-actions/validate-sudo-action",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },
                {
                    "hard_code_flag": "user_cancel_sudo_action_url",
                    "rbac_endpoint": "/api/v1/sudo-actions/cancel-sudo-action",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },
                {
                    "hard_code_flag": "user_check_qrcode_sudo_action_url",
                    "rbac_endpoint": "/api/v1/sudo-actions/check-qrcode-sudo-action",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },
                {
                    "hard_code_flag": "user_validate_qrcode_sudo_action_url",
                    "rbac_endpoint": "/api/v1/sudo-actions/validate-qrcode-sudo-action",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },
                {
                    "hard_code_flag": "user_get_sudo_action_status_url",
                    "rbac_endpoint": "/api/v1/sudo-actions/get-sudo-action-status",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },
                {
                    "hard_code_flag": "user_refresh_token_url",
                    "rbac_endpoint": "/api/v1/auth/refresh-token",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                # /api/v1/users/profile
                {
                    "hard_code_flag": "user_loading_user_profile_url",
                    "rbac_endpoint": "/api/v1/users/profile",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },
                {
                    "hard_code_flag": "user_loading_all_saas_applications_groups_url",
                    "rbac_endpoint": "/api/v1/static/data/get-application-groups",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_validating_user_infos_url",
                    "rbac_endpoint": "/api/v1/generic/validate-user-infos",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_verifying_user_validation_code_url",
                    "rbac_endpoint": "/api/v1/generic/verify-user-validation-code",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },
                {
                    "hard_code_flag": "user_syncing_totp_validation_url",
                    "rbac_endpoint": "/api/v1/auth/verify-totp-validation",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "senat_digit_auth_apk_download_url",
                    "rbac_endpoint": "/api/v1/static/files/download/apk",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },  
                {
                    "hard_code_flag": "user_loading_saas_applications_groups_url",
                    "rbac_endpoint": f"/api/v1/generic/fetch/{CollectionKey.REF_APPLICATION_GROUP.value}",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_loading_validation_requests_overview_url",
                    "rbac_endpoint": f"/api/v1/generic/data-overview/{CollectionKey.OPS_VALIDATION_REQUEST.value}",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_loading_pending_validation_requests_url",
                    "rbac_endpoint": "/api/v1/securities/validations/requests/pending",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_loading_validation_requests_token_overview_url",
                    "rbac_endpoint": f"/api/v1/generic/token-data-overview/{CollectionKey.OPS_VALIDATION_REQUEST.value}",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_validating_or_rejecting_pending_validation_requests_url",
                    "rbac_endpoint": "/api/v1/securities/validations/requests/validate-or-reject",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_connecting_to_websocket_url",
                    "rbac_endpoint": "/api/v1/websocket/ws",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_loading_pending_notifications_url",
                    "rbac_endpoint": "/api/v1/websocket/pending-notifications",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_sending_pong_url",
                    "rbac_endpoint": "/api/v1/websocket/send-pong",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_sending_action_url",
                    "rbac_endpoint": "/api/v1/websocket/send-action",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },  
                
            ],
            "fetch_one_info_url": [],
        }
    },
    {
        **LOADING_ALL_SAAS_DEFAULT_SETUP_DATA_PERMISSION_ITEM,
        "is_default": True,
        "menu_accessible_to_all_profil_flag": "accessible_user_profil_info",
        "is_accessible_to_all_profil": True,
        "all_access_core_seeds": {
            "fetch_url": [
                {
                    "hard_code_flag": "user_downloading_file_url",
                    "rbac_endpoint": "/api/v1/static/files/download-file",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_downloading_local_file_url",
                    "rbac_endpoint": "/api/v1/static/files/local-download-file",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_viewing_file_from_gen_id_url",
                    "rbac_endpoint": "/api/v1/static/files/viewfiles",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_viewing_file_from_file_id_url",
                    "rbac_endpoint": "/api/v1/static/files/view-file",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_loading_saas_user_config_url",
                    "rbac_endpoint": "/api/v1/static/data/get-user-config",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_loading_saas_applications_url",
                    "rbac_endpoint": "/api/v1/static/data/get-applications",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_loading_saas_menu_sub_menus_url",
                    "rbac_endpoint": "/api/v1/static/data/get-menu-user-sub-menus",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_loading_saas_standalone_menus_url",
                    "rbac_endpoint": "/api/v1/static/data/get-standalone-menus",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_loading_saas_application_user_submenus_url",
                    "rbac_endpoint": "/api/v1/static/data/get-application-user-submenus",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_unlock_screen_url",
                    "rbac_endpoint": "/api/v1/auth/unlock-screen",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_totp_validate_otp_url",
                    "rbac_endpoint": "/api/v1/auth/totp-validate-otp",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_validate_otp_url",
                    "rbac_endpoint": "/api/v1/auth/validate-otp",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_signature_config_url",
                    "rbac_endpoint": "/api/v1/auth/signature-config",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_senat_digit_apps_makila_2fa_config_url",
                    "rbac_endpoint": "/api/v1/auth/syc-auth-config",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_get_signature_url",
                    "rbac_endpoint": "/api/v1/auth/get-signature",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_delete_signature_url",
                    "rbac_endpoint": "/api/v1/auth/delete-signature",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_upload_signature_url",
                    "rbac_endpoint": "/api/v1/auth/upload-signature",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_verify_totp_unlock_url",
                    "rbac_endpoint": "/api/v1/auth/verify-totp-unlock",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_senat_digit_apps_makila_2fa_config_update_url",
                    "rbac_endpoint": "/api/v1/auth/syc-auth-config-update",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_refresh_token_url",
                    "rbac_endpoint": "/api/v1/auth/refresh-token",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                {
                    "hard_code_flag": "user_refresh_token_from_mobile_app_url",
                    "rbac_endpoint": "/api/v1/auth/refresh",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                }, 
                
            ],
            "fetch_one_info_url": [],
        }
    },
    {
        **SET_OR_UPDATE_ALL_SAAS_DEFAULT_SETUP_DATA_PERMISSION_ITEM,
        "is_default": True,
        "menu_accessible_to_all_profil_flag": "accessible_user_profil_info",
        "is_accessible_to_all_profil": True,
        "all_access_core_seeds": {
            "fetch_url": [
                {
                    "hard_code_flag": "user_skip_totp_setup_url",
                    "rbac_endpoint": "/api/v1/auth/skip-totp-setup",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },  
                {
                    "hard_code_flag": "user_create_or_update_user_config_url",
                    "rbac_endpoint": "/api/v1/static/data/add-user-config",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },  
                {
                    "hard_code_flag": "user_reset_password_url",
                    "rbac_endpoint": "/api/v1/auth/reset-password",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },  
                {
                    "hard_code_flag": "user_logout_url",
                    "rbac_endpoint": "/api/v1/auth/logout",
                    "is_sudo_action": False,
                    "is_sudo_group_action": False,
                    "menu_flag": "user_profil_info",
                    "is_parent_field_name": False,
                    "is_link_deleted": False,
                },  
                
            ],
            "fetch_one_info_url": [],
        }
    },
]




PROFIL_ENDPOINTS =  [
            #"/api/v1/sudo-actions/init-sudo-action",
            # "/api/v1/sudo-actions/validate-sudo-action",
            # "/api/v1/sudo-actions/cancel-sudo-action",
            # "/api/v1/sudo-actions/check-qrcode-sudo-action",
            # "/api/v1/sudo-actions/validate-qrcode-sudo-action",
            # "/api/v1/sudo-actions/get-sudo-action-status", 
            {
                "label": "Initialisation d'une action sudo",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/sudo-actions/init-sudo-action"
            },
            {
                "label": "Chargement des applications agents",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/get-agent-applications"
            },
            {
                "label": "Validation d'une action sudo",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/sudo-actions/validate-sudo-action"
            },
            {
                "label": "Annulation d'une action sudo",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/sudo-actions/cancel-sudo-action"
            },
            {
                "label": "Vérification du qrcode d'une action sudo",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/sudo-actions/check-qrcode-sudo-action"
            },
            {
                "label": "Validation du qrcode d'une action sudo",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/sudo-actions/validate-qrcode-sudo-action"
            },
            {
                "label": "Chargement du statut d'une action sudo",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/sudo-actions/get-sudo-action-status"
            },
            {
                "label": "Validation des données utilisateur",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/generic/validate-user-infos"
            },
            {
                "label": "Vérification du code utilisateur",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/generic/verify-user-validation-code"
            },
            {
                "label": "Téléchargement de l'apk",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/files/download/apk"
            },
            
            {
                "label": "Vérification et validation totp",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/verify-totp-validation"
            },  
            {
                "label": "Chargement des applications groupes",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": f"/api/v1/generic/fetch/{CollectionKey.REF_APPLICATION_GROUP.value}"
            },
            {
                "label": "Chargement des applications groupes",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/get-application-groups"
            },
            {
                "label": "Téléchargement de fichier",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/files/download-file"
            },
            {
                "label": "Téléchargement de fichier local",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/files/local-download-file"
            },
            {
                "label": "Aperçu de fichier à partir de son id générique",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/files/viewfiles"
            },
            {
                "label": "Aperçu de fichier à partir de son id",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/files/view-file"
            },
            {
                "label": "création ou mise à jour des données de configuration de son propre compte utilisateur",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/add-user-config"
            },
            # /api/v1/auth/skip-totp-setup
            {
                "label": "Saut de la configuration du totp",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/skip-totp-setup"
            },
            {
                "label": "chargement des données de configuration de son propre compte utilisateur",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/get-user-config"
            },
            {
                "label": "Modification de son mot de passe",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/reset-password"
            },
            {
                "label": "Déconnexion",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/logout"
            },
            {
                "label": "Déverrouillage de l'écran",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/unlock-screen"
            },
            {
                "label": "Validation de l'otp",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/totp-validate-otp"
            },
            {
                "label": "Validation de l'otp from mobile app",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/validate-otp"
            },
            {
                "label": "Configuration de la signature",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/signature-config"
            },
            {
                "label": "Get SenatDigit 2fa config",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/syc-auth-config"
            },
            {
                "label": "Get SenatDigit signature config",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/get-signature"
            },
            {
                "label": "Delete SenatDigit signature config",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/delete-signature"
            },
            # /api/v1/users/profile
            {
                "label": "Get user profile",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/users/profile"
            },
            {
                "label": "Upload SenatDigit signature config",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/upload-signature"
            },
            {
                "label": "Unlock screen with totp",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/verify-totp-unlock"
            },
            {
                "label": "Update SenatDigit 2fa config",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/syc-auth-config-update"
            },
            {
                "label": "Refresh token",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/refresh-token"
            },
            {
                "label": "Refresh token from mobile app",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/auth/refresh"
            },

            # ALL MAIN URLS
            {
                "label": "Chargement des applications",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/get-applications"
            },
            {
                "label": "Chargement des menus",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/get-standalone-menus"
            },
            {
                "label": "Chargement des sous menus d'un menu",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/get-menu-user-sub-menus"
            },
            {
                "label": "Chargement des sous-menus d'une application",
                "is_leaf": True,
                "is_link_deleted": False,
                "url": "/api/v1/static/data/get-application-user-submenus"
            },
        ],
    
