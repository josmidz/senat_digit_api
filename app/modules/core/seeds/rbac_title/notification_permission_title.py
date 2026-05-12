# ──────────────────────────────────────────────────
# STATIC PERMISSIONS
# ──────────────────────────────────────────────────

LOADING_OWN_NOTIFICATIONS_PERMISSION_ITEM = {
    "flag": "loading_own_notifications",
    "label": "Chargement des notifications personnelles",
    "description_str": "",
    "is_link_deleted": False,
}

DELETING_OWN_NOTIFICATIONS_PERMISSION_ITEM = {
    "flag": "deleting_own_notifications",
    "label": "Suppression des notifications personnelles",
    "description_str": "",
    "is_link_deleted": False,
}

READING_OWN_NOREAD_NOTIFICATIONS_PERMISSION_ITEM = {
    "flag": "reading_own_noread_notifications",
    "label": "Lecture des nouvelles notifications personnelles",
    "description_str": "",
    "is_link_deleted": False,
}


# ──────────────────────────────────────────────────
# EXPORT
# ──────────────────────────────────────────────────

NOTIFICATION_PERMISSION_RBAC_TITLE_DB = [
    {
        **LOADING_OWN_NOTIFICATIONS_PERMISSION_ITEM,
        "is_default": True,
        "app_accessible_to_all_profil_flag": "accessible_user_notifications",
        "is_accessible_to_all_profil": True,
    },
    {
        **DELETING_OWN_NOTIFICATIONS_PERMISSION_ITEM,
        "is_default": True,
        "app_accessible_to_all_profil_flag": "accessible_user_notifications",
        "is_accessible_to_all_profil": True,
    },
    {
        **READING_OWN_NOREAD_NOTIFICATIONS_PERMISSION_ITEM,
        "is_default": True,
        "app_accessible_to_all_profil_flag": "accessible_user_notifications",
        "is_accessible_to_all_profil": True,
    },
]
