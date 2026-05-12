from bson import ObjectId
from fastapi import Request, HTTPException, status
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.enums.type_enum import EJWTTokenType, OutputDataType
from app.modules.auth.enums.common import MessageCategory
from app.modules.auth.services.token.token_service import TokenService


class PermissionCheckMiddleware:
    """
    Middleware that checks if the logged-in user has permission to access the requested URL.
    This middleware runs after AuthByPassMiddleware and expects request.state.user to be set.

    Permission Flow:
    1. User has a role (rbac_role_id)
    2. Role is linked to permissions via rbac_permission_role
    3. Permissions are linked to endpoints via rbac_permission_target
    4. Check if the current URL matches any endpoint the user has permission for
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        try:
            # Get language from headers
            accept_language = request.headers.get(
                "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()

            # Debug current request
            DebugService.app_debug_print(
                f"\n[PERMISSION CHECK] Checking URL:::> {request.url.path} \n", True)

            # Define routes that don't require permission checking
            excluded_routes = [
                "/api/v1/auth/bearer/refresh",
                "/api/v1/login/auth",
                "/api/v1/refresh/auth",
                "/api/v1/verify/device",
                # Forgot-password flow — unauthenticated; bypasses RBAC.
                "/api/v1/auth/forgot-password/start",
                "/api/v1/auth/forgot-password/verify",
                "/api/v1/auth/forgot-password/complete",
                "/api/v1/static/fetch-consumer-key",
                # Authenticated companion stream for /static/data/get-applications.
                # Token validation still runs in AuthByPassMiddleware; this only
                # avoids requiring a separate RBAC endpoint permission for SSE.
                "/api/v1/static/data/get-applications/sse",
                "/api/v1/static/data/get-senat-digit-applications/sse",
                "/api/v1/auth/login",
                "/api/v1/auth/reset-password",
                "/api/v1/auth/validate-otp",
                "/api/v1/auth/check-reset-password-process-token",
                "/api/v1/auth/resend-reset-password-email",
                "/api/v1/auth/init-reset-password",
                "/api/v1/auth/get-specific-otp",
                "/api/v1/auth/logout",
                "/api/v1/auth/initiate-device-activation",
                "/api/v1/auth/refresh",
                "/api/v1/auth/validate-device-activation",
                "/api/v1/websocket/ws",  # WebSocket connections
                "/api/v1/ng-websocket/ws",  # Angular WebSocket connections
                "/api/v1/websocket/send-pong",  # WebSocket connections
                "/api/v1/websocket/send-action",  # WebSocket connections
                "/api/v1/websocket/pending-notifications",  # WebSocket connections
                "/api/v1/websocket-service/send-unlock-screen",  # WebSocket connections
                "/api/v1/websocket-service/reload-sudo-action",  # WebSocket connections
                "/api/v1/auth/resend-otp",  # WebSocket connections
                "/api/v1/auth/refresh-token",
                "/docs",  # API documentation
                "/redoc",  # API documentation
                "/openapi.json",  # OpenAPI schema
                "/api/v1/static/files/download/apk",
                "/api/v1/static/files/view-svg",
                "/api/v1/auth/verify-totp-login",

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

            # Skip permission check for excluded routes
            if any(request.url.path.startswith(route) for route in excluded_routes):
                print(f'\n\n\n\n request.headers >> : {request.headers}\n\n\n')
                DebugService.app_debug_print(
                    f"\n[PERMISSION CHECK] Route excluded from permission check \n", True)
                await self.app(scope, receive, send)
                return

            # Skip permission check for CORS preflight requests (OPTIONS)
            if request.method == "OPTIONS":
                DebugService.app_debug_print(
                    f"\n[PERMISSION CHECK] Skipping CORS preflight request (OPTIONS): {request.url.path} \n", False)
                await self.app(scope, receive, send)
                return

            # Check if user is logged in (set by AuthByPassMiddleware)
            if not hasattr(request.state, 'user') or not request.state.user:
                generic_service = GenericService(accept_language)
                # Return 403 since this is a protected route that requires authentication
                # Check if token is provided
                authorization = request.headers.get("authorization")
                DebugService.app_debug_print(
                    f"\n[PERMISSION CHECK] Authorization header: {authorization} \n", True)
                if not authorization or not authorization.startswith("Bearer "):
                    DebugService.app_debug_print(
                        f"\n[PERMISSION CHECK] No TOKEN found in request state for protected route: {request.url.path} \n", True)
                    message = ResponseService.get_response_message(
                        MessageCategory.COMMON, "AUTHENTICATION_REQUIRED", accept_language)
                    response = JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "detail": message,
                            "error": "AUTHENTICATION_REQUIRED",
                            "status_code": 403
                        }
                    )
                    await response(scope, receive, send)
                    return
                # Decode JWT token
                token = authorization.split(" ")[1]
                decoded_token = TokenService(accept_language=accept_language).decode_and_verify_token(
                    token=token,
                    expected_type=EJWTTokenType.LOGIN,
                    by_pass_exception=True
                )
                DebugService.app_debug_print(
                    f"\n[PERMISSION CHECK] decoded_token: {decoded_token} FOR : {token} \n", True)
                if not decoded_token:
                    decoded_token = TokenService(accept_language=accept_language).decode_and_verify_token(
                        token=token,
                        expected_type=EJWTTokenType.MFA_VERIFICATION,
                        by_pass_exception=True
                    )
                    DebugService.app_debug_print(
                        f"\n[PERMISSION CHECK] decoded_token: {decoded_token} \n", True)
                    if decoded_token:
                        request.state.user = decoded_token
                    else :
                        DebugService.app_debug_print(
                            f"\n[PERMISSION CHECK] No TOKEN found in request state for protected route: {request.url.path} \n", True)
                        message = ResponseService.get_response_message(
                            MessageCategory.COMMON, "AUTHENTICATION_REQUIRED", accept_language)
                        response = JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            content={
                                "detail": message,
                                "error": "AUTHENTICATION_REQUIRED",
                                "status_code": 403
                            }
                        )
                        await response(scope, receive, send)
                        return
                # Fetch user details
                user_details = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.SYS_USER,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id": decoded_token["sub"]},
                )
                if user_details:
                    request.state.user = user_details
                    DebugService.app_debug_print(
                        f"\n[PERMISSION CHECK] User found: {user_details.get('id', 'Unknown')} \n", True)
                else:
                    DebugService.app_debug_print(
                        f"\n[PERMISSION CHECK] No user found in request state for protected route: {request.url.path} \n", True)
                    message = ResponseService.get_response_message(
                        MessageCategory.COMMON, "AUTHENTICATION_REQUIRED", accept_language)
                    response = JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "detail": message,
                            "error": "AUTHENTICATION_REQUIRED",
                            "status_code": 403
                        }
                    )
                    await response(scope, receive, send)
                    return

            user_details = request.state.user
            DebugService.app_debug_print(
                f"\n[PERMISSION CHECK] User found: {user_details.get('id', 'Unknown')} \n", True)

            # Check user permissions
            has_permission = await self._check_user_permission(
                user_details=user_details,
                current_url=request.url.path,
                accept_language=accept_language
            )

            if not has_permission:
                DebugService.app_debug_print(
                    f"\n[PERMISSION CHECK] Access denied for user {user_details.get('id')} to {request.url.path} \n", True)
                # ---- audit chain (F14): PERMISSION_DENIED ----
                # Best-effort emit; never blocks the 403 response. The
                # security forensics use-case is "who tried what when",
                # captured per request — not per failing aggregation step.
                await self._emit_permission_denied_audit(request, user_details)
                # Return a proper 403 JSON response instead of raising HTTPException
                message = ResponseService.get_response_message(
                    MessageCategory.COMMON, "ACCESS_DENIED_MESSAGE", accept_language)
                response = JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": message,
                        "error": message,
                        "status_code": 403
                    }
                )
                await response(scope, receive, send)
                return

            DebugService.app_debug_print(
                f"\n[PERMISSION CHECK] Access granted for user {user_details.get('id')} to {request.url.path} \n", True)

        except HTTPException:
            # Re-raise HTTP exceptions (like 403 Forbidden)
            raise
        except Exception as e:
            DebugService.app_debug_print(
                f"\n[PERMISSION CHECK] Error during permission check: {e} \n", True)
            # On error, allow access (fail-open for now, you might want to fail-closed in production)
            pass

        # Proceed to the next middleware or endpoint
        await self.app(scope, receive, send)

    async def _check_user_permission(
        self,
        user_details: dict,
        current_url: str,
        accept_language: str
    ) -> bool:
        """
        Check if the user has permission to access the current URL.

        Args:
            user_details: User information from request.state.user
            current_url: The current request URL path
            accept_language: Language for responses

        Returns:
            bool: True if user has permission, False otherwise
        """
        try:
            generic_service = GenericService(accept_language)

            # Get user's role ID
            user_role_id = user_details.get('rbac_role_id')
            if not user_role_id:
                DebugService.app_debug_print(
                    f"\n[PERMISSION CHECK] User has no role assigned \n", True)
                return False

            DebugService.app_debug_print(
                f"\n[PERMISSION CHECK] Checking permissions for role: {user_role_id} \n", True)

            # Build aggregation pipeline to check permissions
            pipeline = [
                # // REMOVED initial role filter to allow privilege-based access
                # // Lookup permissions
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                        'localField': 'rbac_permission_id',
                        'foreignField': '_id',
                        'as': 'rbac_permissions'
                    }
                },
                {
                    '$unwind': '$rbac_permissions'
                },

                # // Add privilege lookup
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                        'let': {'permissionId': '$rbac_permissions._id'},
                        'pipeline': [
                            {
                                '$match': {
                                    '$expr': {
                                        '$and': [
                                            {'$eq': ['$rbac_permission_id',
                                                     '$$permissionId']},
                                            {'$eq': ['$sys_user_id',
                                                     ObjectId(user_details['id'])]},
                                            {'$eq': ['$status', 'added']}
                                        ]
                                    }
                                }
                            }
                        ],
                        'as': 'direct_privileges'
                    }
                },

                # // Lookup permission targets
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                        'localField': 'rbac_permission_id',
                        'foreignField': 'rbac_permission_id',
                        'as': 'rbac_permission_targets'
                    }
                },
                {
                    '$unwind': '$rbac_permission_targets'
                },

                # // Lookup endpoints
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_ENDPOINT.model_name}",
                        'localField': 'rbac_permission_targets.targeted_id',
                        'foreignField': '_id',
                        'as': 'rbac_endpoints'
                    }
                },
                {
                    '$unwind': '$rbac_endpoints'
                },

                # // Final matching - handles both role-based and privilege-based access
                {
                    '$match': {
                        '$and': [
                            # // URL must always match
                            {
                                'rbac_endpoints.url': str(current_url).strip()
                            },
                            # // Either role or privilege must be valid
                            {
                                '$or': [
                                    # // Role-based access
                                    {
                                        'rbac_role_id': ObjectId(str(user_role_id))
                                    },
                                    # // Privilege-based access
                                    {
                                        'direct_privileges': {'$ne': []}
                                    }
                                ]
                            }
                        ]
                    }
                },

                # // Project results
                {
                    '$project': {
                        'endpoint_url': '$rbac_endpoints.url',
                        'endpoint_label': '$rbac_endpoints.label',
                        'permission_name': '$rbac_permissions.name',
                        'rbac_role_id': '$rbac_role_id',
                        'rbac_permission_id': '$rbac_permission_targets.rbac_permission_id',
                        'access_via': {
                            '$cond': [
                                {'$gt': [{'$size': '$direct_privileges'}, 0]},
                                'privilege',
                                'role'
                            ]
                        }
                    }
                }
            ] 

            # Execute the aggregation with error handling
            try:
                user_permissions = await generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                    all_data=True,
                    output_data_type=OutputDataType.DEFAULT.value,
                    pipeline=pipeline
                )
            except Exception as agg_error:
                DebugService.app_debug_print(
                    f"\n[PERMISSION CHECK] Error in aggregation: {agg_error} \n", True)
                # Fall back to simple permission check
                return False

            DebugService.app_debug_print(
                f"\n[PERMISSION CHECK] Found {len(user_permissions)} permission entries \n", True)
            if len(user_permissions) > 0:
                return True
            else:
                return False
        except Exception as e:
            error_msg = str(e)
            DebugService.app_debug_print(
                f"\n[PERMISSION CHECK] Error checking user permission: {error_msg} \n", True)

            # Check if this is a validation error related to AppResponse
            if "validation error for AppResponse" in error_msg or "string_type" in error_msg:
                DebugService.app_debug_print(
                    f"\n[PERMISSION CHECK] Detected AppResponse validation error, allowing access (fail-open) \n", True)
                return True  # Allow access on validation errors

            return False

    async def _emit_permission_denied_audit(
        self,
        request: Request,
        user_details: dict,
    ) -> None:
        """Emit a `PERMISSION_DENIED` event to the audit chain.

        Per `_planning/_followup_batch.md` F14: every authenticated request
        that the RBAC layer refuses is recorded so security forensics can
        reconstruct "who tried to access what when" from the chain alone.

        Best-effort by design — failures here MUST NOT block the 403
        response (the user still gets denied; we just lose one row of
        provenance). Same try/except pattern as every other emit in the
        codebase (vote/parole/document/agenda/session/auth services).
        """
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )

            org_id = user_details.get("sys_organization_id")
            user_id = user_details.get("id")
            if not org_id:
                return  # Audit chain requires sys_organization_id.

            consumer_flag = request.headers.get("X-Api-Consumer-Flag")
            device_id = request.headers.get("X-Device-Id")
            await AuditChainService(DEFAULT_LANGUAGE).emit(
                sys_organization_id=org_id,
                event_type=EAuditEventType.PERMISSION_DENIED,
                actor_user_id=user_id,
                actor_api_consumer_flag=consumer_flag,
                actor_device_id_str=device_id,
                details={
                    "url": str(request.url.path),
                    "method": request.method,
                    "rbac_role_id": str(user_details.get("rbac_role_id"))
                    if user_details.get("rbac_role_id") is not None
                    else None,
                },
            )
        except Exception as e:
            DebugService.app_debug_print(
                f"\n[PERMISSION CHECK] Audit emit failed (silent): {e} \n", False
            )
