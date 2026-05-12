
from app.modules.core.enums.type_enum import EAppGroupFlag
from app.modules.core.constants.common import ALL_ORGANIZATION_PROFIL_IN_ONE, SENAT_DIGIT_ADMIN_WEB_IN_ONE


def get_static_validation_app_db():
    """
    Helper function to generate the STATIC_SYS_APPS_DB array with dynamic variables.

    Args:
        api_consumer_id (str): The API consumer ID
        system_profil (dict): System profile object with 'id' key
        organization_profil (dict): Organization profile object with 'id' key

    Returns:
        list: The complete STATIC_SYS_APPS_DB array with substituted variables
    """ 
    return [
            {
                "path":"/syc/validations/validation-requests",
                "path_guard":"validation_app_request_list_page",
                "svg_icon":"""
                    <svg id="fi_9948779" enable-background="new 0 0 66 66" height="512" viewBox="0 0 66 66" width="512" xmlns="http://www.w3.org/2000/svg">
                        <g>
                            <g>
                            <path d="m2.5 15.7 6.2 44.9c.3 2.2 2.3 3.7 4.5 3.4l30.7-4.2c2.2-.3 3.7-2.3 3.4-4.5v-.3c-.4.1-.8.2-1.3.2h-31c-2.2 0-4-1.8-4-4v-40.7l-5.1.7c-2.2.3-3.7 2.3-3.4 4.5z" fill="#ef6561"/>
                            <path d="m12.5 65c-1.1 0-2.1-.3-3-1-1.1-.8-1.7-2-1.9-3.3l-6.1-44.9c-.4-2.7 1.5-5.2 4.2-5.6l5.1-.7c.3 0 .6 0 .8.2s.3.5.3.8v40.8c0 1.6 1.3 3 2.9 3h31c.3 0 .7-.1 1-.2s.6-.1.9.1.4.5.4.8v.2c.3 2.7-1.6 5.2-4.2 5.5l-30.7 4.3c-.2 0-.4 0-.7 0zm-2.6-53.4-3.9.6c-1.6.2-2.7 1.7-2.5 3.3l6.2 44.9c.1.8.5 1.5 1.2 2 .6.5 1.4.7 2.2.6l30.7-4.2c1.3-.2 2.3-1.2 2.5-2.5-.1 0-.2 0-.3 0h-31c-2.7 0-4.9-2.2-4.9-5v-39.7z" fill="#101f2d"/>
                            </g>
                            <g>
                            <path d="m45.8 56.3h-31c-2.7 0-5-2.2-5-5v-45.3c0-2.7 2.2-5 5-5h31c2.7 0 5 2.2 5 5v45.3c0 2.7-2.2 5-5 5zm-31-53.3c-1.6 0-3 1.3-3 3v45.3c0 1.6 1.3 3 3 3h31c1.6 0 3-1.3 3-3v-45.3c0-1.6-1.3-3-3-3z" fill="#101f2d"/>
                            </g>
                            <g>
                            <path d="m63.6 12.6c0 4.9-4 8.9-8.9 8.9-1.8 0-3.4-.5-4.8-1.4l-4.1.8.8-4.5c-.5-1.1-.8-2.4-.8-3.7 0-4.9 4-8.9 8.9-8.9s8.9 3.9 8.9 8.8z" fill="#64c4f6"/>
                            <path d="m54.7 22.5c-1.7 0-3.5-.5-5-1.3l-3.7.6c-.3.1-.7 0-.9-.3-.2-.2-.3-.6-.3-.9l.8-4.2c-.5-1.2-.8-2.5-.8-3.8 0-5.4 4.4-9.9 9.9-9.9 5.4 0 9.9 4.4 9.9 9.9s-4.4 9.9-9.9 9.9zm-4.7-3.4c.2 0 .4.1.5.2 1.3.8 2.7 1.2 4.2 1.2 4.3 0 7.9-3.5 7.9-7.9s-3.5-7.9-7.9-7.9-7.9 3.5-7.9 7.9c0 1.1.2 2.3.7 3.3.1.2.1.4.1.6l-.6 3.1 2.7-.5z" fill="#101f2d"/>
                            </g>
                            <g>
                            <path d="m53.1 16.6c-.4 0-.8-.2-1.1-.4l-1.8-1.8c-.6-.6-.6-1.5 0-2.1s1.5-.6 2.1 0l.7.7 4-3.9c.6-.6 1.5-.6 2.1 0s.6 1.5 0 2.1l-4.9 4.9c-.3.3-.7.5-1.1.5z" fill="#fff"/>
                            </g>
                            <g>
                            <g>
                                <path d="m43.9 48-3.6-3.6 19.3-19.4c.5-.5 1.3-.5 1.9 0l1.8 1.8c.5.5.5 1.3 0 1.9z" fill="#64c4f6"/>
                                <path d="m43.9 49c-.3 0-.5-.1-.7-.3l-3.6-3.6c-.2-.2-.3-.4-.3-.7s.1-.5.3-.7l19.3-19.3c.9-.9 2.4-.9 3.3 0l1.8 1.8c.9.9.9 2.4 0 3.3l-19.4 19.2c-.2.2-.5.3-.7.3zm-2.2-4.6 2.2 2.2 18.6-18.6c.1-.1.1-.3 0-.4l-1.8-1.8c-.2-.2-.3-.2-.4 0z" fill="#101f2d"/>
                            </g>
                            <g>
                                <path d="m38.4 50.8c-.3 0-.5-.1-.7-.3-.3-.3-.4-.7-.2-1l1.8-5.5c.2-.5.7-.8 1.3-.6.5.2.8.7.6 1.3l-1.2 3.6 3.6-1.2c.5-.2 1.1.1 1.3.6s-.1 1.1-.6 1.3l-5.5 1.8c-.2 0-.3 0-.4 0z" fill="#101f2d"/>
                            </g>
                            <g>
                                <path d="m60.7 32.2c-.3 0-.5-.1-.7-.3l-3.6-3.6c-.4-.4-.4-1 0-1.4s1-.4 1.4 0l3.6 3.6c.4.4.4 1 0 1.4-.2.2-.5.3-.7.3z" fill="#101f2d"/>
                            </g>
                            </g>
                            <g>
                            <path d="m18.1 13.5c-.3 0-.5-.1-.7-.3l-2.2-2.2c-.4-.4-.4-1 0-1.4s1-.4 1.4 0l1.5 1.5 4.7-4.7c.4-.4 1-.4 1.4 0s.4 1 0 1.4l-5.4 5.4c-.2.3-.4.3-.7.3z" fill="#101f2d"/>
                            </g>
                            <g>
                            <path d="m17 22.9c-.3 0-.5-.1-.7-.3-.4-.4-.4-1 0-1.4l5.4-5.4c.4-.4 1-.4 1.4 0s.4 1 0 1.4l-5.4 5.4c-.2.2-.4.3-.7.3z" fill="#ef6561"/>
                            </g>
                            <g>
                            <path d="m22.4 22.9c-.3 0-.5-.1-.7-.3l-5.4-5.4c-.4-.4-.4-1 0-1.4s1-.4 1.4 0l5.4 5.4c.4.4.4 1 0 1.4-.1.2-.4.3-.7.3z" fill="#ef6561"/>
                            </g>
                            <g>
                            <path d="m17 41.7c-.3 0-.5-.1-.7-.3-.4-.4-.4-1 0-1.4l5.4-5.4c.4-.4 1-.4 1.4 0s.4 1 0 1.4l-5.4 5.4c-.2.2-.4.3-.7.3z" fill="#ef6561"/>
                            </g>
                            <g>
                            <path d="m22.4 41.7c-.3 0-.5-.1-.7-.3l-5.4-5.4c-.4-.4-.4-1 0-1.4s1-.4 1.4 0l5.4 5.4c.4.4.4 1 0 1.4-.1.2-.4.3-.7.3z" fill="#ef6561"/>
                            </g>
                            <g>
                            <path d="m18.1 32.3c-.3 0-.5-.1-.7-.3l-2.2-2.2c-.4-.4-.4-1 0-1.4s1-.4 1.4 0l1.5 1.5 4.7-4.7c.4-.4 1-.4 1.4 0s.4 1 0 1.4l-5.4 5.4c-.2.2-.4.3-.7.3z" fill="#101f2d"/>
                            </g>
                            <g>
                            <path d="m18.1 51.1c-.3 0-.5-.1-.7-.3l-2.2-2.2c-.4-.4-.4-1 0-1.4s1-.4 1.4 0l1.5 1.5 4.7-4.7c.4-.4 1-.4 1.4 0s.4 1 0 1.4l-5.4 5.4c-.2.2-.4.3-.7.3z" fill="#64c4f6"/>
                            </g>
                            <g>
                            <g>
                                <path d="m35.2 8.7h-7.5c-.6 0-1-.4-1-1s.4-1 1-1h7.5c.6 0 1 .4 1 1s-.5 1-1 1z" fill="#101f2d"/>
                            </g>
                            <g>
                                <path d="m40 13h-12.4c-.6 0-1-.4-1-1s.4-1 1-1h12.4c.6 0 1 .4 1 1s-.5 1-1 1z" fill="#101f2d"/>
                            </g>
                            </g>
                            <g>
                            <g>
                                <path d="m35.2 18.1h-7.5c-.6 0-1-.4-1-1s.4-1 1-1h7.5c.6 0 1 .4 1 1s-.5 1-1 1z" fill="#101f2d"/>
                            </g>
                            <g>
                                <path d="m40 22.4h-12.4c-.6 0-1-.4-1-1s.4-1 1-1h12.4c.6 0 1 .4 1 1s-.5 1-1 1z" fill="#101f2d"/>
                            </g>
                            </g>
                            <g>
                            <g>
                                <path d="m35.2 27.5h-7.5c-.6 0-1-.4-1-1s.4-1 1-1h7.5c.6 0 1 .4 1 1s-.5 1-1 1z" fill="#101f2d"/>
                            </g>
                            <g>
                                <path d="m44.7 31.8h-17.1c-.6 0-1-.4-1-1s.4-1 1-1h17.1c.6 0 1 .4 1 1s-.4 1-1 1z" fill="#101f2d"/>
                            </g>
                            </g>
                            <g>
                            <g>
                                <path d="m35.2 36.9h-7.5c-.6 0-1-.4-1-1s.4-1 1-1h7.5c.6 0 1 .4 1 1s-.5 1-1 1z" fill="#101f2d"/>
                            </g>
                            <g>
                                <path d="m37.6 41.2h-9.9c-.6 0-1-.4-1-1s.4-1 1-1h9.9c.6 0 1 .4 1 1s-.5 1-1 1z" fill="#101f2d"/>
                            </g>
                            </g>
                            <g>
                            <g>
                                <path d="m35.2 46.3h-7.5c-.6 0-1-.4-1-1s.4-1 1-1h7.5c.6 0 1 .4 1 1s-.5 1-1 1z" fill="#101f2d"/>
                            </g>
                            <g>
                                <path d="m33.6 50.6h-5.9c-.6 0-1-.4-1-1s.4-1 1-1h5.9c.6 0 1 .4 1 1s-.5 1-1 1z" fill="#101f2d"/>
                            </g>
                            </g>
                        </g>
                        </svg>

                    """,
                # END
                "name": "Requête de validation",
                "description_str": "Requête de validation (en attente, validée(s), rejetée(s))",
                "menu_accessible_to_all_profil_flag":"accessible_user_validation_requests",
                "is_accessible_to_all_profil":True,
                "is_skipable_menu_on_view":True,
                "is_parameterized_menu":True,
                "order_by":0,
                "application_group_flag": EAppGroupFlag.COMMON.value,
                "flag": "validation_app_request_list_page",
                "is_standalone": False,
                "is_link_deleted": False,
                "restricted_profil_list":[
                   *ALL_ORGANIZATION_PROFIL_IN_ONE 
                ],
                "restricted_api_consumer_list":[
                    *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                ],
                "sub_menus":[]
            },
            {
                "path":"/syc/validations/requested",
                "path_guard":"validation_app_requested_overview_page",
                "svg_icon":"""
                    <svg id="fi_12178805" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg" data-name="Layer 1">
                        <path d="m81.244 464.8h165.628a7 7 0 0 0 0-14h-165.628a11.607 11.607 0 0 1 -11.594-11.6v-358.551h47.622a19.056 19.056 0 0 0 19.021-19.049v-47.593h234.737a11.577 11.577 0 0 1 11.57 11.564v271.9a7 7 0 0 0 14 0v-271.9a25.6 25.6 0 0 0 -25.57-25.571h-241.739a7 7 0 0 0 -4.951 2.051l-66.64 66.649a7.008 7.008 0 0 0 -2.051 4.951v365.549a25.627 25.627 0 0 0 25.595 25.6zm36.028-398.154h-37.719l42.736-42.737v37.691a5.037 5.037 0 0 1 -5.017 5.046zm-25.767 273.571a7 7 0 0 1 7-7h73.049a7 7 0 0 1 0 14h-73.047a7 7 0 0 1 -7.002-7zm0 31.266a7 7 0 0 1 7-7h42.1a7 7 0 0 1 0 14h-42.098a7 7 0 0 1 -7.002-7zm140.515 0a7 7 0 0 1 -7 7h-62.676a7 7 0 1 1 0-14h62.674a7 7 0 0 1 7.002 7zm-140.515 31.238a7 7 0 0 1 7-7h126.513a7 7 0 1 1 0 14h-126.511a7 7 0 0 1 -7.002-7zm267.213-190.053a7 7 0 0 1 0 9.9l-45.61 45.61a7.005 7.005 0 0 1 -4.951 2.05 7.008 7.008 0 0 1 -4.952-2.055l-14.428-14.457a7 7 0 1 1 9.913-9.893l9.476 9.5 40.653-40.653a7 7 0 0 1 9.899-.002zm-267.213 11.045a7 7 0 0 1 7-7h73.049a7 7 0 1 1 0 14h-73.047a7 7 0 0 1 -7.002-7zm0 31.266a7 7 0 0 1 7-7h42.1a7 7 0 1 1 0 14h-42.098a7 7 0 0 1 -7.002-7zm140.515 0a7 7 0 0 1 -7 7h-62.676a7 7 0 1 1 0-14h62.674a7 7 0 0 1 7.002 7zm0 31.238a7 7 0 0 1 -7 7h-126.513a7 7 0 1 1 0-14h126.511a7 7 0 0 1 7.002 7zm126.7-180.151-45.61 45.61a7.006 7.006 0 0 1 -4.951 2.051 7.009 7.009 0 0 1 -4.952-2.056l-14.428-14.457a7 7 0 0 1 9.913-9.893l9.476 9.5 40.653-40.653a7 7 0 0 1 9.9 9.9zm-267.215 1.143a7 7 0 0 1 7-7h73.049a7 7 0 0 1 0 14h-73.047a7 7 0 0 1 -7.002-7zm140.515 31.267a7 7 0 0 1 -7 7h-62.676a7 7 0 1 1 0-14h62.674a7 7 0 0 1 7.002 7zm-140.515 0a7 7 0 0 1 7-7h42.1a7 7 0 0 1 0 14h-42.098a7 7 0 0 1 -7.002-7zm140.515 31.265a7 7 0 0 1 -7 7h-126.513a7 7 0 0 1 0-14h126.511a7 7 0 0 1 7.002 7zm120.58 342.259a103.763 103.763 0 1 0 -103.744-103.751 103.866 103.866 0 0 0 103.744 103.751zm0-193.521a89.759 89.759 0 1 1 -89.744 89.773 89.861 89.861 0 0 1 89.744-89.776zm-77.828 78.8a78.591 78.591 0 1 1 0 21.927 7 7 0 0 1 13.868-1.943 64.588 64.588 0 1 0 0-18.041 7 7 0 0 1 -13.868-1.943zm84.83-39.054v45.99l22.124 12.775a7 7 0 1 1 -7 12.127l-25.625-14.8a7 7 0 0 1 -3.5-6.063v-50.037a7 7 0 1 1 14 0zm-32.48-252.15a7 7 0 0 1 -7 7h-40.222v49.662h49.663v-16.212a7 7 0 1 1 14 0v23.216a7 7 0 0 1 -7 7h-63.663a7 7 0 0 1 -7-7v-63.666a7 7 0 0 1 7-7h47.22a7 7 0 0 1 7.002 7zm-61.229 116.5a7 7 0 0 1 7-7h47.227a7 7 0 1 1 0 14h-40.22v49.634h49.663v-16.18a7 7 0 1 1 14 0v23.188a7 7 0 0 1 -7 7h-63.663a7 7 0 0 1 -7-7z"/>
                        </svg>
                    """,
                # END
                "name": "Aperçu des requêtes de validation",
                "description_str": "Aperçu des requêtes de validation",
                "menu_accessible_to_all_profil_flag":"accessible_user_validation_requests",
                "is_accessible_to_all_profil":True,
                "is_skipable_menu_on_view":True,
                "is_parameterized_menu":True,
                "order_by":1,
                "application_group_flag": EAppGroupFlag.COMMON.value,
                "flag": "validation_app_requested_overview_page",
                "is_standalone": False,
                "is_link_deleted": False,
                "restricted_profil_list":[
                    *ALL_ORGANIZATION_PROFIL_IN_ONE 
                ],
                "restricted_api_consumer_list":[
                    *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                ],
                "sub_menus":[]
            },
            {
                "path":"/syc/validations/overview",
                "path_guard":"validation_app_requests_overview_page",
                "svg_icon":"""
                    <svg id="fi_10501216" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" data-name="flat gradient"><linearGradient id="b88db297-0345-4d0a-a419-beea2cdb8069" gradientUnits="userSpaceOnUse" x1="4" x2="60" y1="31.955" y2="31.955"><stop offset="0" stop-color="#00c0ff"></stop><stop offset="1" stop-color="#5558ff"></stop></linearGradient><path d="m59.82 34.11c-15.98533-21.5501-39.73288-21.45813-55.64.00043a1.00771 1.00771 0 0 0 0 1.14958c16.15431 21.50977 39.67772 21.46611 55.64-.01045a.99185.99185 0 0 0 0-1.13956zm-27.82 12.86a12.29964 12.29964 0 0 1 -12.29-12.29c.67814-16.3041 23.90432-16.29933 24.58.0001a12.29965 12.29965 0 0 1 -12.29 12.2899zm-21.65135-26.01115c11.445-11.21783 31.8308-11.24048 43.30267-.01064a1.00043 1.00043 0 0 1 -1.36325 1.46423c-10.71425-10.49818-29.83679-10.51661-40.57616.00992a1 1 0 0 1 -1.36326-1.46351zm21.65135 3.43115a10.30669 10.30669 0 0 0 -10.29 10.29c.57773 13.65271 20.00432 13.64869 20.58-.00007a10.30671 10.30671 0 0 0 -10.29-10.28993zm0 17.57a1.07484 1.07484 0 0 1 -1.14-1.23 5.24639 5.24639 0 0 0 -5.01-6.45 1.00833 1.00833 0 0 1 -.95-1.22 7.24714 7.24714 0 0 1 7.1-5.66c9.65183.38031 9.64905 14.18732 0 14.56zm5.28-7.28a5.27842 5.27842 0 0 1 -4.29 5.18c.01-.1.01-.2.01-.3a7.23837 7.23837 0 0 0 -5.78-7.13 5.28213 5.28213 0 0 1 10.06 2.25z" fill="url(#b88db297-0345-4d0a-a419-beea2cdb8069)"></path>
                    </svg>
                    """,
                # END
                "name": "Aperçu de la requête de validation",
                "description_str": "Aperçu de la requête de validation",
                "menu_accessible_to_all_profil_flag":"accessible_user_validation_requests",
                "is_accessible_to_all_profil":True,
                "is_skipable_menu_on_view":True,
                "is_parameterized_menu":True,
                "order_by":1,
                "application_group_flag": EAppGroupFlag.COMMON.value,
                "flag": "validation_app_requests_overview_page",
                "is_standalone": False,
                "is_link_deleted": False,
                "restricted_profil_list":[
                    *ALL_ORGANIZATION_PROFIL_IN_ONE 
                ],
                "restricted_api_consumer_list":[
                    *SENAT_DIGIT_ADMIN_WEB_IN_ONE
                ],
                "sub_menus":[]
            }, 
        ]