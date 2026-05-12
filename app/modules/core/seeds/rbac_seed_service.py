


def profil_link(flag, is_link_deleted=False, is_link_activated=True, is_link_hidden=False, is_link_locked=False):
    return {
        "flag": flag,
        "is_link_activated": is_link_activated,
        "is_link_hidden": is_link_hidden,
        "is_link_locked": is_link_locked,
        "is_link_deleted": is_link_deleted,
    }


def api_consumer_link(flag, is_link_deleted=False, is_link_activated=True, is_link_hidden=False, is_link_locked=False):
    return {
        "flag": flag,
        "is_link_activated": is_link_activated,
        "is_link_hidden": is_link_hidden,
        "is_link_locked": is_link_locked,
        "is_link_deleted": is_link_deleted,
    }


def role_link(flag, is_link_deleted=False, is_link_activated=True, is_link_hidden=False, is_link_locked=False):
    return {
        "flag": flag,
        "is_link_activated": is_link_activated,
        "is_link_hidden": is_link_hidden,
        "is_link_locked": is_link_locked,
        "is_link_deleted": is_link_deleted,
    }


def app_link(flag, is_link_deleted=False, is_link_activated=True, is_link_hidden=False, is_link_locked=False):
    return {
        "flag": flag,
        "is_link_activated": is_link_activated,
        "is_link_hidden": is_link_hidden,
        "is_link_locked": is_link_locked,
        "is_link_deleted": is_link_deleted,
    }


def menu_link(flag, is_link_deleted=False, is_link_activated=True, is_link_hidden=False, is_link_locked=False):
    return {
        "flag": flag,
        "is_link_activated": is_link_activated,
        "is_link_hidden": is_link_hidden,
        "is_link_locked": is_link_locked,
        "is_link_deleted": is_link_deleted,
    }


def endpoint_entry(
    hard_code_flag,
    rbac_endpoint,
    menu_flag=None,
    app_flag=None,
    is_link_deleted=False,
    is_sudo_action=False,
    is_sudo_group_action=False,
    is_parent_field_name=False,
):
    entry = {
        "hard_code_flag": hard_code_flag,
        "rbac_endpoint": rbac_endpoint,
        "is_sudo_action": is_sudo_action,
        "is_sudo_group_action": is_sudo_group_action,
        "is_parent_field_name": is_parent_field_name,
        "is_link_deleted": is_link_deleted,
    }
    if menu_flag is not None:
        entry["menu_flag"] = menu_flag
    if app_flag is not None:
        entry["app_flag"] = app_flag
    return entry


def action_to_menu(menu_flag, action_flag, action_hard_code_flag, action_label, action_is_standalone=True):
    return {
        "menu_flag": menu_flag,
        "action_flag": action_flag,
        "action_is_standalone": action_is_standalone,
        "action_hard_code_flag": action_hard_code_flag,
        "action_label": action_label,
    }


def action_to_app(app_flag, action_flag, action_hard_code_flag, action_label, action_is_standalone=True):
    return {
        "app_flag": app_flag,
        "action_flag": action_flag,
        "action_is_standalone": action_is_standalone,
        "action_hard_code_flag": action_hard_code_flag,
        "action_label": action_label,
    }


def component_to_menu(menu_flag, component_flag, component_hard_code_flag, component_label, component_is_standalone=False):
    return {
        "menu_flag": menu_flag,
        "component_flag": component_flag,
        "component_is_standalone": component_is_standalone,
        "component_hard_code_flag": component_hard_code_flag,
        "component_label": component_label,
    }


def component_to_app(app_flag, component_flag, component_hard_code_flag, component_label, component_is_standalone=False):
    return {
        "app_flag": app_flag,
        "component_flag": component_flag,
        "component_is_standalone": component_is_standalone,
        "component_hard_code_flag": component_hard_code_flag,
        "component_label": component_label,
    }
