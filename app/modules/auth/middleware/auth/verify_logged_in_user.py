from fastapi import Depends, HTTPException, Request, status
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.auth.enums.auth import ELoginStatus
from app.modules.auth.enums.common import MessageCategory
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.auth.services.token.token_service import TokenService
from app.modules.core.enums.type_enum import EJWTTokenType, OutputDataType
from jose import ExpiredSignatureError, JWTError

async def verify_logged_in_user(request: Request):

    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()  # Extract language dynamically
    token_service = TokenService(accept_language)
    generic_service = GenericService(accept_language)
    # List of excluded routes
    excluded_routes = [ 
        "/api/v1/login/auth",
        "/api/v1/auth/bearer/refresh",
        "/api/v1/static/fetch-consumer-key",
        "/api/v1/auth/login",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/validate-otp",
        "/api/v1/auth/verify-totp-login",
        "/api/v1/auth/resend-otp",
        "/api/v1/auth/refresh-token",

        "/api/v1/auth/totp-validate-otp",
        "/api/v1/auth/check-reset-password-process-token",
        "/api/v1/auth/resend-reset-password-email",
        "/api/v1/auth/init-reset-password",
        "/api/v1/auth/get-specific-otp",
        "/api/v1/static/files/download-file",
        "/api/v1/static/files/view-svg",

        "/api/v1/auth/initiate-device-activation",
        "/api/v1/auth/validate-device-activation",
        "/api/v1/static/files/download/apk",
        "/api/v1/generic/fetch/refCountries",
        # "/api/v1/generic/fetch/refCurrencies",
        
        "/api/v1/generic/fetch-ref/all-countries",
        "/api/v1/generic/fetch-ref/all-system-countries",
        "/api/v1/generic/fetch-ref/all-system-country-currencies",
        "/api/v1/system-countries/countries/fetch/all-system-country-and-currencies",
        "/api/v1/system-countries/fetch/registration-system-countries",
        "/api/v1/system-countries/fetch/init-customer-registration-process",
        "/api/v1/system-countries/countries/fetch/my-system-country-currencies",
        "/api/v1/system-countries/countries/fetch/my-system-countries-available",


        # START REGISTRATION PROCESS
        "/api/v1/auth/init-customer-registration-process",
        "/api/v1/auth/ask-info-validation",
        "/api/v1/auth/submit-info-otp-validation",
        "/api/v1/auth/check-username-taken",

        # WEBHOOKS
        "api/v1/webhooks/deploy",
        "/api/v1/health", 
 
        # SUDO
        "/api/v1/sudo-actions/init-sudo-action",
        "/api/v1/sudo-actions/reload-sudo-action",
        "/api/v1/sudo-actions/status",
        "/api/v1/sudo-actions/validate",
        "/api/v1/sudo-actions/cancel",
        "/api/v1/sudo-actions/validate-sudo-action",
        "/api/v1/sudo-actions/cancel-sudo-action",
        "/api/v1/sudo-actions/check-qrcode-sudo-action",
        "/api/v1/sudo-actions/validate-qrcode-sudo-action",
        "/api/v1/sudo-actions/get-sudo-action-status",
        "/api/v1/sudo-actions/debug/confirmation-types",
        "/api/v1/auth/get-pairing-data",
        "/api/v1/auth/complete-device-pairing",
        "/api/v1/auth/set-totp-app-pin",
        "/api/v1/auth/get-user-totps",
        "/api/v1/auth/totp-apps/logout",


        # 
        # START REGISTRATION PROCESS
        "/api/v1/auth/trans/init-customer-registration-process",
        "/api/v1/auth/trans/ask-info-validation",
        "/api/v1/auth/trans/submit-info-otp-validation",

        "/api/v1/auth/ask-info-validation",
        "/api/v1/auth/submit-info-otp-validation",
        "/api/v1/auth/check-username-taken",

        "/api/v1/auth/trans/users/email-register",
        "/api/v1/auth/trans/users/login",
        "/api/v1/auth/trans/users/get-otp",
        "/api/v1/auth/trans/users/check-visitor",
        "/api/v1/auth/trans/users/login-visitor",
        "/api/v1/auth/trans/auth-configs",


        "/api/v1/auth/trans/users/phone-register",
        "/api/v1/auth/trans/upload-user-registration-id-card",
        "/api/v1/auth/trans/upload-user-profile-photo",
        "/api/v1/auth/trans/upload-company-logo",

        "/api/v1/auth/trans/users/auth-configs",
        "/api/v1/auth/trans/auth/questions",
        "/api/v1/auth/trans/test-auto-login",
        "/api/v1/auth/trans/users/validate-otp",
        "/api/v1/auth/trans/users/validate-password",
        "/api/v1/trans/ewallets/fetch/ewallets",
        "/api/v1/trans/ewallets/search/ewallets",
        "/api/v1/auth/trans/users/email-login",
        "/api/v1/auth/trans/users/google-login",
        "/api/v1/auth/trans/get-specific-otp",
        "/api/v1/auth/trans/validate-otp",

        # AGENT
        "/api/v1/auth/core-users/login",
        "/api/v1/auth/core-users/validate-otp",
        "/api/v1/auth/core-users/get-specific-otp",
        "/api/v1/auth/core-users/resend-otp",

        # CLIENT
        "/api/v1/urban-transportations/customer-subscriptions/fetch/available-subscription-plans",
        "/api/v1/urban-transportations/customer-subscriptions/fetch/active-customer-subscription",
        "/api/v1/urban-transportations/service-trips/fetch/popular-destinations",
        "/api/v1/configurations/advertisements/fetch/customer-advertisements",
        "/api/v1/urban-transportations/customer-wallets/fetch/home-virtual-card",
        "/api/v1/urban-transportations/service-trips/fetch/nearby-bus-stops",
        "/api/v1/urban-transportations/customer-wallets/top-up",
        "/api/v1/urban-transportations/customer-wallets/topup-status",
        "/api/v1/urban-transportations/customer-subscriptions/add/customer-subscription",
        "/api/v1/urban-transportations/customer-subscriptions/subscription-status",
        "/api/v1/urban-transportations/service-trips/take/service-trip",
    ]

    # import re

    # # List of excluded route patterns
    # excluded_route_patterns = [
    #     r"^/api/v1/static/fetch-consumer-key$",
    #     r"^/api/v1/auth/login$",
    #     r"^/api/v1/auth/reset-password$",
    #     r"^/api/v1/auth/validate-otp$",
    #     r"^/api/v1/auth/check-reset-password-process-token$",
    #     r"^/api/v1/auth/resend-reset-password-email$",
    #     r"^/api/v1/auth/init-reset-password$",
    #     r"^/api/v1/auth/get-specific-otp$",
    #     r"^/api/v1/static/files/download-file/.*$",  # Matches any path starting with this base
    # ]

    # # Skip validation for excluded routes
    # if any(re.match(pattern, request.url.path) for pattern in excluded_route_patterns):
    #     DebugService.app_debug_print(f"\n Skipping validation for excluded route: {request.url.path} \n", False)
    #     return

    # Skip validation for excluded routes
    if any(request.url.path.startswith(excluded_route) for excluded_route in excluded_routes):
        DebugService.app_debug_print(f"\n [VERIFY LOGGED IN USER] [1] Skipping validation for excluded route: {request.url.path} \n", True)
        return

    # Skip validation for excluded routes
    if request.url.path in excluded_routes:
        DebugService.app_debug_print(f"\n [VERIFY LOGGED IN USER] [2] Skipping validation for excluded route: {request.url.path} \n",False)
        return

    try:
        # Extract headers
        accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
        authorization = request.headers.get("authorization")

        # Validate Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            DebugService.app_debug_print("\n Authorization header missing or invalid \n",True)
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "HEADER_TOKEN_MISSING", accept_language)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

        # Extract and validate token
        token = authorization.split(" ")[1]
        DebugService.app_debug_print(f"\n token: {token} \n",False)
        decoded_token = token_service.decode_and_verify_token(
            token=token,
            expected_type=EJWTTokenType.LOGIN,
            by_pass_exception=False
        )
        DebugService.app_debug_print(f"\n decoded_token: {decoded_token} \n",False)
        # Validate token type
        if not decoded_token or decoded_token.get("type") != EJWTTokenType.LOGIN.value:
            DebugService.app_debug_print("\n Invalid token type \n")
            message = ResponseService.get_response_message(MessageCategory.COMMON, "INVALID_TOKEN_TYPE", accept_language)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)

        # Fetch user details
        user_details = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.SYS_USER,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter___id": decoded_token["sub"]},
            sort={"created_at": -1}
        )

        DebugService.app_debug_print(f"\n\n\n\n\n\n\n\n\n\n\n\n\n\n User found {user_details}\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n",False)
        if not user_details or not isinstance(user_details, dict) or 'id' not in user_details:
            DebugService.app_debug_print("\n User not found or invalid user data \n",False)
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "USER_NOT_FOUND", accept_language)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)
        DebugService.app_debug_print(f"\n\n\n\n\n\n\n\n\n\n\n\n\n\n decoded_token found {decoded_token}\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n",False)
        device_id_str = None
        if decoded_token and 'device_id_str' in decoded_token:
            device_id_str = decoded_token['device_id_str']
        # Fetch login history (strict: with device_id_str)
        login_history_query = {
            "filter__sys_user_id": user_details['id'],
            "filter__status": ELoginStatus.LOGGED_IN.value,
            "filter__device_id_str": device_id_str
        }
        loginHistory = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
            output_data_type=OutputDataType.DEFAULT.value,
            query=login_history_query,
            sort={"created_at": -1}
        )

        # Fallback: if strict query failed, retry WITHOUT device_id_str filter
        if not loginHistory and device_id_str:
            current_device_hash = getattr(request.state, "deviceHashedId", None)
            DebugService.app_debug_print(
                f"\n [verify_logged_in_user] LOGIN HISTORY NOT FOUND (strict). "
                f"user_id={user_details['id']}, token_device_id_str={device_id_str}, "
                f"current_request_device_hash={current_device_hash}. "
                f"Trying fallback without device_id_str... \n", True
            )
            fallback_query = {
                "filter__sys_user_id": user_details['id'],
                "filter__status": ELoginStatus.LOGGED_IN.value,
            }
            loginHistory = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                output_data_type=OutputDataType.DEFAULT.value,
                query=fallback_query,
                sort={"created_at": -1}
            )
            if loginHistory:
                DebugService.app_debug_print(
                    f"\n [verify_logged_in_user] LOGIN HISTORY FOUND via fallback! "
                    f"login_history_id={loginHistory.get('id')}, "
                    f"db_device_id_str={loginHistory.get('device_id_str')} \n", True
                )

        DebugService.app_debug_print(f"\n loginHistory >>><< || : {loginHistory} \n",False)
        # Attach user and login history to request state
        request.state.user = user_details
        request.state.loginHistory = loginHistory

        # Try to fetch the role using the regular method
        try:
            user_role = await generic_service.fetch_native_query_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                native_query={"_id": user_details['rbac_role_id']},
            )
            DebugService.app_debug_print(f"\n\n ROLE ID >>> :::: {user_details['rbac_role_id']} user_role >>> : {user_role} \n",False)
        except Exception as e:
            DebugService.app_debug_print(f"\n\n\n Error fetching role: {e} \n\n\n", True)
            user_role = None

        # If the role couldn't be fetched, try to fetch it directly from the database
        if not user_role:
            DebugService.app_debug_print(f"\n\n\n Fetching role directly from database \n\n\n", False)
            try:
                from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
                from app.db.dao import DAO
                from bson import ObjectId

                # Get the collection name and model class for RBAC_ROLE
                metadata = COLLECTION_MODEL_MAPPING.get(CollectionKey.RBAC_ROLE)
                if metadata:
                    collection_name = metadata.collection_name
                    model_class = metadata.model_class

                    # Create a DAO instance
                    dao = DAO(collection_name, model_class, is_read_only=True)

                    # Fetch the role directly from the database
                    role_id = ObjectId(user_details['rbac_role_id'])
                    cursor = dao.collection.find({"_id": role_id})
                    documents = await cursor.to_list(length=1)

                    if documents:
                        document = documents[0]
                        # Convert ObjectId to string
                        document["_id"] = str(document["_id"])
                        if "rbac_profile_id" in document:
                            document["rbac_profile_id"] = str(document["rbac_profile_id"])

                        # Create a minimal role object with the required fields
                        user_role = {
                            "id": document["_id"],
                            "rbac_profile_id": document.get("rbac_profile_id"),
                            "is_default": document.get("is_default", False),
                            "name": document.get("name", "Unknown Role")
                        }
                        DebugService.app_debug_print(f"\n\n\n Direct role fetch successful: {user_role} \n\n\n", False)
            except Exception as e:
                DebugService.app_debug_print(f"\n\n\n Error fetching role directly: {e} \n\n\n", True)

        DebugService.app_debug_print(f"\n user_role >>>>> : {user_role} \n\n\n\n",False)

        if user_role:
            request.state.userRole = user_role

            # Only fetch user_profil if user_role has rbac_profile_id
            if "rbac_profile_id" in user_role and user_role["rbac_profile_id"]:
                try:
                    user_profil = await generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.RBAC_PROFILE,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___id": user_role["rbac_profile_id"]},
                    )
                    if user_profil:
                        request.state.userProfil = user_profil
                except Exception as e:
                    DebugService.app_debug_print(f"\n\n\n Error fetching user profile: {e} \n\n\n", True)

    except IndexError as e:
        DebugService.app_debug_print(f"\n Malformed Authorization header: {e} \n")
        message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "MALFORMED_AUTH_HEADER", accept_language)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    except ExpiredSignatureError as e:
        DebugService.app_debug_print(f"\n Token expired: {e} \n")
        message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "TOKEN_EXPIRED", accept_language)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

    except JWTError as e:
        DebugService.app_debug_print(f"\n JWT error: {e} \n")
        message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "TOKEN_INVALID", accept_language)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)
async def get_api_consumer_anyway(request: Request):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()  # Extract language dynamically
    token_service = TokenService(accept_language)
    generic_service = GenericService(accept_language)
    # List of excluded routes
    excluded_routes = [
        "/api/v1/static/fetch-consumer-key",
        "/api/v1/auth/login",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/validate-otp",
        "/api/v1/auth/check-reset-password-process-token",
        "/api/v1/auth/resend-reset-password-email",
        "/api/v1/auth/init-reset-password",
        "/api/v1/auth/get-specific-otp",
    ]

    # Skip validation for excluded routes
    if request.url.path in excluded_routes:
        DebugService.app_debug_print(f"\n [GET API CONSUMER ANYWAY] Skipping validation for excluded route: {request.url.path} \n",False)
        return request

    try:
        # Extract headers
        accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
        authorization = request.headers.get("authorization")

        # Validate Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            DebugService.app_debug_print("\n Authorization header missing or invalid \n",False)
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "HEADER_TOKEN_MISSING", accept_language)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

        # Extract and validate token
        token = authorization.split(" ")[1]
        DebugService.app_debug_print(f"\n token: {token} \n",False)
        decoded_token = token_service.decode_and_verify_token(
            token=token,
            expected_type=EJWTTokenType.LOGIN,
            by_pass_exception=False
        )
        DebugService.app_debug_print(f"\n decoded_token: {decoded_token} \n",False)
        # Validate token type
        if not decoded_token or decoded_token.get("type") != EJWTTokenType.LOGIN.value:
            DebugService.app_debug_print("\n Invalid token type \n")
            message = ResponseService.get_response_message(MessageCategory.COMMON, "INVALID_TOKEN_TYPE", accept_language)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)

        # Fetch user details
        user_details = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.SYS_USER,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter___id": decoded_token["sub"]},
            sort={"created_at": -1}
        )

        DebugService.app_debug_print(f"\n\n\n\n\n\n\n\n\n\n\n\n\n\n User found {user_details}\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n",False)
        if not user_details or not isinstance(user_details, dict) or 'id' not in user_details:
            DebugService.app_debug_print("\n User not found or invalid user data \n",False)
            message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "USER_NOT_FOUND", accept_language)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

        # Fetch login history
        login_history_query = {
            "filter__sys_user_id": user_details['id'],
            "filter__status": ELoginStatus.LOGGED_IN.value,
            "filter__cfg_user_device_id": decoded_token['cfg_user_device_id']
        }
        loginHistory = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
            output_data_type=OutputDataType.DEFAULT.value,
            query=login_history_query,
            sort={"created_at": -1}
        )
        DebugService.app_debug_print(f"\n loginHistory: {loginHistory} \n",False)
        # Attach user and login history to request state
        if user_details:
            request.state.user = user_details
        if loginHistory:
            request.state.loginHistory = loginHistory

    except IndexError as e:
        DebugService.app_debug_print(f"\n Malformed Authorization header: {e} \n")
        message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "MALFORMED_AUTH_HEADER", accept_language)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    except ExpiredSignatureError as e:
        DebugService.app_debug_print(f"\n Token expired: {e} \n")
        message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "TOKEN_EXPIRED", accept_language)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

    except JWTError as e:
        DebugService.app_debug_print(f"\n JWT error: {e} \n")
        message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "TOKEN_INVALID", accept_language)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)
