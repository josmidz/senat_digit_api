from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

# MIDDLEWARES
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.enums.type_enum import EMultipleValidationStatus
from app.modules.auth.middleware.api_consumer.consumer_key import ConsumerValidationMiddleware
from app.modules.auth.middleware.auth.auth_by_pass import AuthByPassMiddleware
from app.modules.auth.middleware.auth.permission_check_middleware import PermissionCheckMiddleware
from app.modules.auth.middleware.common.common_client_data import CommonClientDataMiddleware
from app.modules.core.configs.custom_exceptions import custom_http_exception_handler
from app.modules.core.services.hash.hash_service import HashService
from app.modules.core.utils.head_logs.log import LogRequestHeadersMiddleware
from app.modules.auth.middleware.auth.verify_logged_in_user import verify_logged_in_user
from app.modules.security.middleware.sudo_check_middleware import SudoActionCheckMiddleware

# ROUTES
from app.modules.core.api.endpoints.core_endpoint import router as core_router
from app.modules.auth.api.endpoints.auth_endpoint import router as auth_router
from app.modules.auth.api.endpoints.senat_auth_endpoint import router as senat_auth_router
from app.modules.session_meeting.api.endpoints.session_endpoint import router as session_router
from app.modules.agenda.api.endpoints.agenda_endpoint import router as agenda_router
from app.modules.document.api.endpoints.document_endpoint import router as document_router
from app.modules.vote.api.endpoints.vote_endpoint import router as vote_router
from app.modules.presence.api.endpoints.presence_endpoint import router as presence_router
from app.modules.parole.api.endpoints.parole_endpoint import router as parole_router
from app.modules.notification.api.endpoints.notification_endpoint import router as notification_router
from app.modules.audit_security.api.endpoints.audit_endpoint import router as audit_router
from app.modules.core.api.endpoints.generic_endpoint import router as generic_router
from app.modules.core.api.endpoints.static_endpoint import router as static_router
from app.modules.core.api.endpoints.user_endpoint import router as users_router
from app.modules.core.api.endpoints.organization_endpoint import router as orgs_router
from app.modules.edocs.api.endpoints.edoc_endpoint import router as edoc_router
from app.modules.security.api.endpoint.websocket_endpoint import router as websocket_router
from app.modules.security.api.endpoint.websocket_service_endpoint import router as websocket_service_router
from app.modules.core.api.endpoints.search_endpoint import router as search_router
# system_config_endpoint removed 2026-05-04 — was only TRANSCO bank surface
# (3 routes: /get-config-bank, /fetch/bank-accounts, /create/bank-accounts).
# A parliamentary session has no bank concept; if Senat-Digit later needs
# a bank-like configuration model (e.g. payment for member dues), it goes
# under a new feature module, not this legacy TRANSCO endpoint.
from app.modules.core.api.endpoints.webhook_endpoint import router as webhook_router
from app.modules.core.api.endpoints.diagnostic_endpoint import router as diagnostic_router
from app.modules.core.api.endpoints.system_country_endpoint import system_country_router
from app.modules.security.api.endpoint.sudo_action_endpoint import router as sudo_action_router
from app.modules.security.api.endpoint.security_endpoint import security_app
from app.modules.core.api.endpoints.history_endpoint import router as history_router

route_entry_point = FastAPI()


# #MIDDLEWARES
# Register exception handlers
route_entry_point.add_exception_handler(HTTPException, custom_http_exception_handler)

# Execution order (last registered = first executed):
# 1. ConsumerValidation → 2. LogHeaders → 3. AuthByPass → 4. CommonClientData → 5. PermissionCheck → 6. SudoActionCheck

# This will be executed LAST (after PermissionCheck) — needs request.state.user from AuthByPass
# Captures POST|PUT|DELETE|PATCH with X-Sudo-Instruction-Key header and validates against Redis
route_entry_point.add_middleware(SudoActionCheckMiddleware)

# Executed before SudoActionCheck
route_entry_point.add_middleware(PermissionCheckMiddleware)

# Executed before PermissionCheck
route_entry_point.add_middleware(CommonClientDataMiddleware)

# Executed before CommonClientData — sets request.state.user
route_entry_point.add_middleware(AuthByPassMiddleware)

# Executed after AuthByPass — resolves per-org RLS context (one DB lookup per request)
from app.modules.security.middleware.rls_middleware import RowLevelSecurityMiddleware
route_entry_point.add_middleware(RowLevelSecurityMiddleware)

# Executed before AuthByPass
route_entry_point.add_middleware(LogRequestHeadersMiddleware)

# This will be executed FIRST
route_entry_point.add_middleware(ConsumerValidationMiddleware, excluded_routes=["/api/v1/static/fetch-consumer-key"])

# Health check endpoint
@route_entry_point.get("/health")
async def health_check():
    return {"status": "healthy"}


# AUTH route
route_entry_point.include_router(
    auth_router,
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(verify_logged_in_user)]
)

# Senat-Digit auth_device — clean /verb/resource endpoints (login, refresh,
# password change, device verify). No prefix: routes are at /api/v1/login/auth
# etc. per CLAUDE.md /verb/resource convention. login/auth & verify/device are
# bypassed by AuthByPassMiddleware so they don't require a logged-in user.
route_entry_point.include_router(
    senat_auth_router,
    tags=["auth_device"],
    responses={404: {"description": "Not found"}},
)

# Senat-Digit séance module (§3.5 step 2) — lifecycle, participants, quorum.
# Routes at /api/v1/{create,list,detail,patch,open,suspend,close,assign}/session*
# and /api/v1/detail/quorum.
route_entry_point.include_router(
    session_router,
    tags=["session_meeting"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(verify_logged_in_user)],
)

# Senat-Digit ordre du jour module (§3.5 step 3) — points + ordering +
# activation (one active per session) + publish.
route_entry_point.include_router(
    agenda_router,
    tags=["agenda"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(verify_logged_in_user)],
)

# Senat-Digit document module (§3.5 step 4) — metadata in api, blobs via fs
# (signed URLs proxied through BlobProxyService).
route_entry_point.include_router(
    document_router,
    tags=["document"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(verify_logged_in_user)],
)

# Senat-Digit vote module (§3.5 step 5) — config + ballot + proxy + result.
# Includes secret-vote envelope encryption (per-resolution DEK sealed by org KMS).
route_entry_point.include_router(
    vote_router,
    tags=["vote"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(verify_logged_in_user)],
)

# Senat-Digit présence module (§3.5 step 6) — e-signature présence + read history.
# Biometric / NFC / manual-greffier methods reserved as 501 until v1.1.
route_entry_point.include_router(
    presence_router,
    tags=["presence"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(verify_logged_in_user)],
)

# Senat-Digit parole module (§3.5 step 7) — speaking-time requests
# (promoted into MVP per PPTX slide 5).
route_entry_point.include_router(
    parole_router,
    tags=["parole"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(verify_logged_in_user)],
)

# Senat-Digit notification module (§3.5 step 8) — in-app inbox.
# Wraps the existing core NtfNotificationModel with Senat event taxonomy.
# FCM/APNs push fan-out reserved for v1.1.
route_entry_point.include_router(
    notification_router,
    tags=["notification"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(verify_logged_in_user)],
)

# Senat-Digit audit_security module (§3.5 step 9 — last MVP module).
# Append-only chained audit log (SHA-256 prev-hash chain). Tamper-evidence
# is the PPTX hard requirement (slide 19 + memory: senat_pptx_requirements §5).
route_entry_point.include_router(
    audit_router,
    tags=["audit_security"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(verify_logged_in_user)],
)

# SYSTEM_PROFIL admin user-management — cross-tenant list/lock/unlock.
# Sits next to the legacy /organizations/{add/org,generate-reset-password-link}
# pair to round out the "tenant onboarding" surface. Profile-flag guard
# in the controller enforces SYSTEM_PROFIL-only.
from app.modules.admin_user.api.endpoints.admin_user_endpoint import (
    router as admin_user_router,
)
route_entry_point.include_router(
    admin_user_router,
    tags=["admin_user"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(verify_logged_in_user)],
)

# EDOC ROUTER
route_entry_point.include_router(
    edoc_router,
    prefix="/edocs",
    tags=["edocs"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(verify_logged_in_user)]
)



# WebSocket ROUTER
route_entry_point.include_router(
    websocket_router,
    prefix="/websocket",
    tags=["websocket"],
    responses={404: {"description": "Not found"}},
    # dependencies=[Depends(decode_and_get_user_from_socket_token)]
    # No authentication dependencies for WebSocket endpoints
)

# Angular WebSocket ROUTER (separate prefix for Angular clients)
route_entry_point.include_router(
    websocket_router,
    prefix="/ng-websocket",
    tags=["ng-websocket"],
    responses={404: {"description": "Not found"}},
    # dependencies=[Depends(decode_and_get_user_from_angular_socket_token)]
)

# WebSocket Service ROUTER
route_entry_point.include_router(
    websocket_service_router,
    prefix="/websocket-service",
    tags=["websocket-service"],
    dependencies=[],
)

# CORES route
route_entry_point.include_router(
    core_router,
    prefix="/cores",
    tags=["cores"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(verify_logged_in_user)]
)

# STATIC route
route_entry_point.include_router(
    static_router,
    prefix="/static",
    tags=["static"],
    dependencies=[Depends(verify_logged_in_user)]
)

# USERS route
route_entry_point.include_router(
    users_router,
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(verify_logged_in_user)]
)

# ORGS route
route_entry_point.include_router(
    orgs_router,
    prefix="/organizations",
    # prefix="/orgs",
    tags=["users"],
    dependencies=[Depends(verify_logged_in_user)]
)

# GENERIC route
route_entry_point.include_router(
    generic_router,
    prefix="/generic",
    tags=["generic"],
    dependencies=[Depends(verify_logged_in_user)]
)

# SEARCH route
route_entry_point.include_router(
    search_router,
    prefix="/search",
    tags=["search"],
    dependencies=[Depends(verify_logged_in_user)]
)

# SYSTEM CONFIG route
# /system-config router intentionally removed — see import comment above.

# HOOKS route
route_entry_point.include_router(
    webhook_router,
    prefix="/webhooks",
    tags=["webhooks"],
    # dependencies=[Depends(verify_logged_in_user)]
)
 
 
# SYSTEM COUNTRIES ROUTES
route_entry_point.include_router(
    system_country_router,
    prefix="/system-countries",
    tags=["system-countries"],
    dependencies=[Depends(verify_logged_in_user)]
)

# DIAGNOSTIC ROUTES (for debugging blocking issues)
route_entry_point.include_router(
    diagnostic_router,
    prefix="/diagnostic",
    tags=["diagnostic"],
    dependencies=[Depends(verify_logged_in_user)]
)

# SUDO ACTION ROUTES
route_entry_point.include_router(
    sudo_action_router,
    prefix="/sudo-actions",
    tags=["sudo-actions"],
    dependencies=[Depends(verify_logged_in_user)]
)

# SECURITIES ROUTES (groups, RLS, settings)
route_entry_point.include_router(
    security_app,
    prefix="/securities",
    tags=["securities"],
)

# HISTORY ROUTES (update & delete audit trail)
route_entry_point.include_router(
    history_router,
    prefix="/history",
    tags=["history"],
    dependencies=[Depends(verify_logged_in_user)]
)

