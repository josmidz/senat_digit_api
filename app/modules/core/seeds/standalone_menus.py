
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.enums.profiles_enum import ESysProfileFlag
from app.modules.core.constants.common import ALL_ORGANIZATION_PROFIL_IN_ONE, SENAT_DIGIT_ADMIN_WEB_IN_ONE, SYSTEM_ORGANIZATION_PROFIL_IN_ONE


def get_static_sys_standalone_menu_db():
    """
    Helper function to generate the STATIC_SYS_STANDALONE_MENU_DB array with dynamic variables.

    Args:
        api_consumer_id (str): The API consumer ID
        system_profil (dict): System profile object with 'id' key
        organization_profil (dict): Organization profile object with 'id' key

    Returns:
        list: The complete STATIC_SYS_STANDALONE_MENU_DB array with substituted variables
    """
    return [
        {
            "path":"/syc/system-settings",
            "path_guard":"system_settings_page",
            "svg_icon":"""
                <svg id="fi_13337082" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg" data-name="Layer 1">
                    <g fill-rule="evenodd">
                        <g fill="#00ffb0">
                        <path d="m243.672 329.774a74.8 74.8 0 0 1 0-147.548l2.329-.388v148.324z"/>
                        <path d="m433.2 460.928a21.374 21.374 0 1 1 -21.375-21.373 21.4 21.4 0 0 1 21.375 21.373z"/>
                        <path d="m468.624 234.624a21.376 21.376 0 1 1 -21.374 21.376 21.4 21.4 0 0 1 21.374-21.376z"/>
                        <path d="m390.447 51.072a21.374 21.374 0 1 1 21.373 21.378 21.4 21.4 0 0 1 -21.373-21.378z"/>
                        </g>
                        <path d="m468.624 275.375a19.376 19.376 0 1 1 19.376-19.375 19.4 19.4 0 0 1 -19.375 19.373zm-224.624 52.425a72.8 72.8 0 0 1 0-143.6zm187.2 133.128a19.374 19.374 0 1 1 -19.375-19.374 19.394 19.394 0 0 1 19.375 19.374zm-19.38-429.228a19.376 19.376 0 1 1 -19.373 19.373 19.4 19.4 0 0 1 19.373-19.373zm56.8 180.925a43.448 43.448 0 0 0 -41.668 31.375h-158.952v-60.79h117.7a12 12 0 0 0 11.755-9.594l16.21-79.216a43.408 43.408 0 1 0 -23.335-5.675l-14.43 70.487h-119.9a96.791 96.791 0 1 0 0 193.581h119.9l14.428 70.483a43.353 43.353 0 1 0 23.335-5.675l-16.214-79.219a12 12 0 0 0 -11.755-9.59h-117.694v-60.792h158.952a43.372 43.372 0 1 0 41.672-55.379zm-444.62 13.886v58.983l48.4 8.618a12 12 0 0 1 9.485 8.7 179.3 179.3 0 0 0 17.902 43.188 12 12 0 0 1 -.551 12.869l-28.136 40.331 41.706 41.7 40.342-28.148a12 12 0 0 1 12.866-.551 178.987 178.987 0 0 0 43.168 17.9 12 12 0 0 1 8.706 9.491l8.62 48.4h17.492v-92.127c-71.8-6.114-128.372-66.507-128.372-139.865s56.572-133.751 128.372-139.86v-92.14h-17.492l-8.62 48.407a12.007 12.007 0 0 1 -8.706 9.486 179.139 179.139 0 0 0 -43.169 17.9 12 12 0 0 1 -12.867-.552l-40.34-28.141-41.706 41.705 28.14 40.341a12 12 0 0 1 .551 12.868 179.179 179.179 0 0 0 -17.9 43.171 12 12 0 0 1 -9.486 8.7zm-14.1 80.851 50.941 9.071a203.049 203.049 0 0 0 14.438 34.827l-29.617 42.449a12 12 0 0 0 1.356 15.349l55.924 55.922a12 12 0 0 0 15.352 1.358l42.46-29.623a203.316 203.316 0 0 0 34.814 14.439l9.074 50.949a12 12 0 0 0 11.814 9.9h39.544a12 12 0 0 0 12-12v-115.629a12 12 0 0 0 -12-12 116.371 116.371 0 1 1 0-232.742 12 12 0 0 0 12-12v-115.632a12 12 0 0 0 -12-12h-39.546a12 12 0 0 0 -11.812 9.9l-9.074 50.954a202.736 202.736 0 0 0 -34.818 14.431l-42.456-29.623a12 12 0 0 0 -15.352 1.358l-55.924 55.922a12 12 0 0 0 -1.356 15.358l29.62 42.454a203.44 203.44 0 0 0 -14.439 34.821l-50.943 9.067a12 12 0 0 0 -9.9 11.812v79.092a12 12 0 0 0 9.9 11.816z" fill="#143565"/>
                    </g>
                    </svg>

                """,
            # END
            "name": "System settings",
            "order_by":0,
            "flag": "system_settings",
            "is_standalone": True,
            "restricted_profil_list": [
                *SYSTEM_ORGANIZATION_PROFIL_IN_ONE
            ],
            "restricted_api_consumer_list": [
                *SENAT_DIGIT_ADMIN_WEB_IN_ONE
            ],
            "sub_menus":[]
        }, 
            {
                # NOT FOR MENU COLLECTION, ONLY FOR RBAC PATH GUARD
                "path":"/syc/profil",
                "path_guard":"profil_page",
                "svg_icon":"""
                    <svg height="512" viewBox="0 0 64 64" width="512" xmlns="http://www.w3.org/2000/svg" id="fi_3177440">
                    <g id="User">
                        <circle cx="32" cy="32" fill="#e6ecff" r="31"/>
                        <g fill="#4294ff">
                        <path d="m56.877 50.4748a31.0647 31.0647 0 0 0 -49.7651-.0156 30.9669 30.9669 0 0 0 49.7651.0156z"/>
                        <circle cx="32" cy="22" r="12"/>
                        </g>
                    </g>
                    </svg>
                    """,
                # END
                "name": "profil",
                "menu_accessible_to_all_profil_flag":"accessible_user_profil_info",
                "is_accessible_to_all_profil":True,
                "description_str":"Profil utilisateur",
                "order_by":2,
                "flag": "user_profil_info",
                "is_standalone": True,
                "restricted_profil_list": [
                    *ALL_ORGANIZATION_PROFIL_IN_ONE
                ],
                "restricted_api_consumer_list": [
                    *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                ],
                "sub_menus":[]
            },
            
        ]


# def get_static_sys_standalone_menu_db_with_defaults():
#     """
#     Helper function to get the menu array with default/placeholder values.
#     This is useful for testing or when actual values are not available.

#     Returns:
#         list: The STATIC_SYS_STANDALONE_MENU_DB array with placeholder values
#     """
#     # Default placeholder values
#     default_api_consumer_id = "placeholder_api_consumer_id"
#     default_system_profil = {"id": "placeholder_system_profil_id"}
#     default_organization_profil = {"id": "placeholder_organization_profil_id"}

#     return get_static_sys_standalone_menu_db(
#         api_consumer_id=default_api_consumer_id,
#         system_profil=default_system_profil,
#         organization_profil=default_organization_profil
#     )


# def validate_menu_parameters(api_consumer_id, system_profil, organization_profil):
#     """
#     Validate the parameters required for generating the menu array.

#     Args:
#         api_consumer_id (str): The API consumer ID
#         system_profil (dict): System profile object
#         organization_profil (dict): Organization profile object

#     Returns:
#         tuple: (is_valid, error_message)
#     """
#     if not api_consumer_id:
#         return False, "api_consumer_id is required and cannot be empty"

#     if not isinstance(system_profil, dict) or 'id' not in system_profil:
#         return False, "system_profil must be a dictionary with 'id' key"

#     if not isinstance(organization_profil, dict) or 'id' not in organization_profil:
#         return False, "organization_profil must be a dictionary with 'id' key"

#     if not system_profil['id']:
#         return False, "system_profil['id'] cannot be empty"

#     if not organization_profil['id']:
#         return False, "organization_profil['id'] cannot be empty"

#     return True, None


# def get_menu_statistics(menu_array=None):
#     """
#     Get statistics about the menu structure.

#     Args:
#         menu_array (list, optional): The menu array to analyze.
#                                    If None, uses default values.

#     Returns:
#         dict: Statistics about the menu structure
#     """
#     if menu_array is None:
#         menu_array = get_static_sys_standalone_menu_db_with_defaults()

#     def count_menus(menus, level=0):
#         count = 0
#         max_depth = level
#         for menu in menus:
#             count += 1
#             if 'sub_menus' in menu and menu['sub_menus']:
#                 sub_count, sub_depth = count_menus(menu['sub_menus'], level + 1)
#                 count += sub_count
#                 max_depth = max(max_depth, sub_depth)
#         return count, max_depth

#     total_menus, max_depth = count_menus(menu_array)

#     # Count menus by type
#     standalone_count = sum(1 for menu in menu_array if menu.get('is_standalone', True))

#     return {
#         'total_menus': total_menus,
#         'top_level_menus': len(menu_array),
#         'max_depth': max_depth,
#         'standalone_menus': standalone_count,
#         'non_standalone_menus': len(menu_array) - standalone_count
#     }


# # Example usage:
# if __name__ == "__main__":
#     # Example with actual values
#     sample_api_consumer_id = "507f1f77bcf86cd799439011"
#     sample_system_profil = {"id": "507f1f77bcf86cd799439012"}
#     sample_organization_profil = {"id": "507f1f77bcf86cd799439013"}

#     # Validate parameters
#     is_valid, error = validate_menu_parameters(
#         sample_api_consumer_id,
#         sample_system_profil,
#         sample_organization_profil
#     )

#     if is_valid:
#         # Generate menu array with actual values
#         menu_array = get_static_sys_standalone_menu_db(
#             api_consumer_id=sample_api_consumer_id,
#             system_profil=sample_system_profil,
#             organization_profil=sample_organization_profil
#         )

#         # Get statistics
#         stats = get_menu_statistics(menu_array)
#         print(f"Menu Statistics: {stats}")
#         print(f"Generated {stats['total_menus']} menus successfully")
#     else:
#         print(f"Parameter validation failed: {error}")

#     # Example with default values
#     default_menu_array = get_static_sys_standalone_menu_db_with_defaults()
#     default_stats = get_menu_statistics(default_menu_array)
#     print(f"Default Menu Statistics: {default_stats}")