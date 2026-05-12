

from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.modules.security.services.security_websocket_service import SecurityWebSocketService
from app.modules.security.api.endpoint.sudo_action_endpoint import router as sudo_action_router
from app.modules.security.api.endpoint.security_groups_endpoint import router as security_groups_router
from app.modules.security.api.endpoint.security_settings_endpoint import router as security_settings_router
from app.modules.security.api.endpoint.global_validators_endpoint import router as global_validators_router
from app.modules.security.api.endpoint.grouped_validators_endpoint import router as grouped_validators_router
from app.modules.security.api.endpoint.delegated_validators_endpoint import router as delegated_validators_router
from app.modules.security.api.endpoint.cross_validators_endpoint import router as cross_validators_router
from app.modules.security.api.endpoint.validation_configurations_endpoint import router as validation_configurations_router
from app.modules.security.api.endpoint.whitelist_blacklist_endpoint import router as whitelist_blacklist_router
from app.modules.security.api.endpoint.rls_settings_endpoint import router as rls_settings_router
from app.modules.security.api.endpoint.rls_overview_endpoint import router as rls_overview_router
from app.modules.security.api.endpoint.rls_users_accesses_endpoint import router as rls_users_accesses_router
from app.modules.security.api.endpoint.sudo_action_overview_endpoint import router as sudo_action_overview_router
from app.modules.security.api.endpoint.ops_history_endpoint import router as ops_history_router
from app.modules.security.api.endpoint.validation_requests_endpoint import router as validation_requests_router
from app.modules.security.api.endpoint.security_logs_endpoint import router as security_logs_router
from app.modules.auth.middleware.auth.verify_logged_in_user import verify_logged_in_user

security_app = APIRouter()

# sudo-actions
security_app.include_router(
    sudo_action_router,
    prefix="/sudo-actions",
    tags=["sudo-actions"],
    dependencies=[Depends(verify_logged_in_user)]
)

# security groups
security_app.include_router(
    security_groups_router,
    prefix="/groups",
    tags=["security-groups"],
    dependencies=[Depends(verify_logged_in_user)]
)

# security settings (RLS & sudo action configuration)
security_app.include_router(
    security_settings_router,
    prefix="/settings",
    tags=["security-settings"],
    dependencies=[Depends(verify_logged_in_user)]
)

# global validators (validations)
security_app.include_router(
    global_validators_router,
    prefix="/validations/global-validators",
    tags=["global-validators"],
    dependencies=[Depends(verify_logged_in_user)]
)

# sudo action overview (validations)
security_app.include_router(
    sudo_action_overview_router,
    prefix="/validations/sudo-actions",
    tags=["sudo-action-overview"],
    dependencies=[Depends(verify_logged_in_user)]
)

# grouped validators (validations)
security_app.include_router(
    grouped_validators_router,
    prefix="/validations/grouped-validators",
    tags=["grouped-validators"],
    dependencies=[Depends(verify_logged_in_user)]
)

# delegated validators (validations)
security_app.include_router(
    delegated_validators_router,
    prefix="/validations/delegated-validators",
    tags=["delegated-validators"],
    dependencies=[Depends(verify_logged_in_user)]
)

# cross validators (validations)
security_app.include_router(
    cross_validators_router,
    prefix="/validations/cross-validators",
    tags=["cross-validators"],
    dependencies=[Depends(verify_logged_in_user)]
)

# configuration (validations)
security_app.include_router(
    validation_configurations_router,
    prefix="/validations/configurations",
    tags=["configurations"],
    dependencies=[Depends(verify_logged_in_user)]
)

# whitelist / blacklist (RLS)
security_app.include_router(
    whitelist_blacklist_router,
    prefix="/rls/whitelists",
    tags=["whitelist-blacklist"],
    dependencies=[Depends(verify_logged_in_user)]
)

# RLS settings (RLS permission setup)
security_app.include_router(
    rls_settings_router,
    prefix="/rls/rls-settings",
    tags=["rls-settings"],
    dependencies=[Depends(verify_logged_in_user)]
)

# RLS overview (RLS dashboard)
security_app.include_router(
    rls_overview_router,
    prefix="/rls/overviews",
    tags=["rls-overview"],
    dependencies=[Depends(verify_logged_in_user)]
)

# RLS users accesses (RLS per-user view)
security_app.include_router(
    rls_users_accesses_router,
    prefix="/rls/users-accesses",
    tags=["rls-users-accesses"],
    dependencies=[Depends(verify_logged_in_user)]
)

# OPS history (update / delete history, restore, search)
security_app.include_router(
    ops_history_router,
    prefix="/histories",
    tags=["histories"],
    dependencies=[Depends(verify_logged_in_user)]
)

# validation requests — fetch pending, fetch single, validate/reject, validate-all
# Full prefix: /api/v1/securities/validations/requests
security_app.include_router(
    validation_requests_router,
    prefix="/validations/requests",
    tags=["validation-requests"],
    dependencies=[Depends(verify_logged_in_user)]
)

# Organization CRUD logs (setup + log list + SSE stream)
security_app.include_router(
    security_logs_router,
    prefix="/logs",
    tags=["security-logs"],
    dependencies=[Depends(verify_logged_in_user)]
)



