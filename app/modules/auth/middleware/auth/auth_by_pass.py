from fastapi import Request
from jose import jwt
from starlette.types import ASGIApp, Receive, Scope, Send
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.auth.services.token.token_service import TokenService

from app.modules.core.enums.type_enum import AccountStatusFlag, EJWTTokenType, OutputDataType

class AuthByPassMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        try:
            accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
            DebugService.app_debug_print(f"\nAuthByPassMiddleware processing: {request.url.path}\n", False)
            
            token_service = TokenService(accept_language)
            generic_service = GenericService(accept_language)
            
            # Define routes that bypass authentication
            excluded_routes = [
                "/api/v1/auth/bearer/refresh",
                "/api/v1/websocket/ws",  # WebSocket connections
                "/api/v1/ng-websocket/ws",  # Angular WebSocket connections
                "/api/v1/websocket/pending-notifications",  # WebSocket connections
                "/api/v1/websocket/send-pong",  # WebSocket connections
                "/api/v1/websocket/send-action",  # WebSocket connections
                "/api/v1/websocket-service/send-unlock-screen",  # WebSocket connections
                "/api/v1/websocket-service/reload-sudo-action",  # WebSocket connections

                "/api/v1/static/fetch-consumer-key",

                # ─────────────────────────────────────────────────────
                # SENAT-DIGIT mobile auth surface
                # Paths registered by senat_auth_endpoint.py — no token
                # available yet at these calls. `/patch/password` is NOT
                # listed: the user has just logged in successfully and
                # carries the (force-update) JWT, so the auth middleware
                # should still validate it.
                # ─────────────────────────────────────────────────────
                "/api/v1/login/auth",
                "/api/v1/refresh/auth",
                "/api/v1/verify/device",

                # ─────────────────────────────────────────────────────
                # Forgot-password flow — UNAUTHENTICATED by design.
                # /start carries no token; /verify + /complete carry
                # the short-lived reset-session + reset JWTs minted by
                # the previous step (decoded by the controller, NOT by
                # this middleware — bypass keeps the decode local).
                # ─────────────────────────────────────────────────────
                "/api/v1/auth/forgot-password/start",
                "/api/v1/auth/forgot-password/verify",
                "/api/v1/auth/forgot-password/complete",

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
                "/api/v1/auth/complete-device-pairing",
                "/api/v1/auth/get-pairing-data",
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
                # "/api/v1/auth/resend-otp",
                # "/api/v1/auth/initiate-device-activation",
                # "/api/v1/auth/validate-device-activation",

                # START REGISTRATION PROCESS
                "/api/v1/auth/init-customer-registration-process",
                "/api/v1/auth/ask-info-validation",
                "/api/v1/auth/submit-info-otp-validation",
                "/api/v1/auth/check-username-taken",

                # WEBHOOKS
                "api/v1/webhooks/deploy",
                "/api/v1/health",
                "/api/v1/org/upload-logo",




                # USERS
                "/api/v1/users/add-user-config",


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
            
            # Skip authentication for excluded routes (check if path starts with any excluded route)
            request_path = request.url.path
            if any(request_path.startswith(route) for route in excluded_routes):
                DebugService.app_debug_print(f"\nRoute {request_path} is excluded from authentication\n", False)
                await self.app(scope, receive, send)
                return
                
            # For all other routes, require authentication
            authorization = request.headers.get("authorization")
            if not authorization or not authorization.startswith("Bearer "):
                DebugService.app_debug_print(f"\nNo valid Authorization header found\n", False)
                await self.app(scope, receive, send)
                return
                
            # Process the token
            token = authorization.split(" ")[1]
            DebugService.app_debug_print(f"\nProcessing token for route: {request.url.path}\n", False)
            
            # Handle special routes with special token types
            special_routes = {
                "/api/v1/auth/validate-otp": EJWTTokenType.MFA_VERIFICATION,
                "/api/v1/auth/get-specific-otp": EJWTTokenType.MFA_VERIFICATION,
                "/api/v1/auth/resend-otp": EJWTTokenType.MFA_VERIFICATION,
                "/api/v1/auth/init-reset-password": EJWTTokenType.PASSWORD_INIT_PROCESS,
                "/api/v1/auth/resend-reset-password-email": EJWTTokenType.PASSWORD_INIT_PROCESS,
                "/api/v1/auth/check-reset-password-process-token": EJWTTokenType.PASSWORD_RESET_REDIRECTED,
                "/api/v1/auth/reset-password": EJWTTokenType.PASSWORD_RESET_PROCESS,
                "/api/v1/auth/initiate-device-activation": EJWTTokenType.INITIATE_DEVICE_ACTIVATION_PROCESS,
                "/api/v1/auth/validate-device-activation": EJWTTokenType.REQUEST_DEVICE_ACTIVATION,
                "/api/v1/auth/bearer/refresh": EJWTTokenType.REFRESH_TOKEN,
                "/api/v1/auth/get-pairing-data": EJWTTokenType.LOGIN,
                "/api/v1/auth/complete-device-pairing": EJWTTokenType.LOGIN,
            }
            
            token_type = special_routes.get(request.url.path, EJWTTokenType.LOGIN)
            decoded_token = token_service.decode_and_verify_token(
                token=token,
                expected_type=token_type,
                by_pass_exception=True
            )
            
            if not decoded_token:
                DebugService.app_debug_print(f"\nInvalid or expired token for route: {request.url.path}\n", False)
                await self.app(scope, receive, send)
                return
                
            # Get user details
            user_details = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": decoded_token["sub"]},
            )
            
            DebugService.app_debug_print(f"\nUser details from token: {user_details}\n", False)

            # Check if user_details is valid and has required fields
            if (not user_details or
                not isinstance(user_details, dict) or
                'account_status' not in user_details or
                user_details['account_status'] != AccountStatusFlag.ACTIVE):
                DebugService.app_debug_print(f"\nInvalid user or inactive account\n", False)
                await self.app(scope, receive, send)
                return
                
            # Set user in request state
            request.state.user = user_details
            DebugService.app_debug_print(f"\nSuccessfully authenticated user: {user_details.get('id')}\n", False)
            
        except jwt.ExpiredSignatureError:
            DebugService.app_debug_print("\nToken expired\n", False)
        except jwt.JWTError:
            DebugService.app_debug_print("\nInvalid token\n", False)
        except Exception as e:
            DebugService.app_debug_print(f"\nError in AuthByPassMiddleware: {str(e)}\n", False)
            
        # Continue to next middleware/endpoint
        await self.app(scope, receive, send)

 
