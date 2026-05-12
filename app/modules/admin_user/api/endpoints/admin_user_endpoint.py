"""Admin user-management endpoints.

| Method | Path                              | Granted to                                  |
|--------|-----------------------------------|---------------------------------------------|
| GET    | /list/sys_user_for_organization   | system admin · main_profile_super_admin     |
| POST   | /patch/sys_user_account_status    | system admin · main_profile_super_admin     |
| GET    | /list/sys_user_device_pending     | system · main_profile_super_admin · greffier|
| POST   | /patch/sys_user_device_activate   | system · main_profile_super_admin · greffier|
| POST   | /patch/sys_user_device_revoke     | system · main_profile_super_admin · greffier|

Mounted at the API root (no prefix) per CLAUDE.md `/verb/resource`
convention. Auth is enforced by `verify_logged_in_user` + RBAC by
`PermissionCheckMiddleware` — both of which run on every request, no
inline guards in the controller.
"""

from fastapi import APIRouter, Query, Request

from app.modules.admin_user.api.controller.admin_user_controller import (
    AdminUserController,
)
from app.modules.admin_user.schemas.admin_user_schema import (
    AccountStatusPatchRequest,
    CreateOrgUserRequest,
    DeviceActivateRequest,
    DeviceRevokeRequest,
)
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE


router = APIRouter()


def _accept_language(request: Request) -> str:
    return request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()


@router.get("/list/sys_user_for_organization")
async def list_sys_user_for_organization(
    request: Request,
    sys_organization_id: str = Query(..., min_length=12, description="Cible: _id de sys_organization"),
    all_data: bool = Query(False),
    page: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
):
    return await AdminUserController(_accept_language(request)).list_for_organization(
        request=request,
        sys_organization_id=sys_organization_id,
        all_data=all_data,
        page=page,
        limit=limit,
    )


@router.post("/patch/sys_user_account_status")
async def patch_sys_user_account_status(
    request: Request,
    payload: AccountStatusPatchRequest,
):
    return await AdminUserController(_accept_language(request)).patch_account_status(
        request=request,
        payload=payload,
    )


@router.post("/create/sys_user_in_organization")
async def create_sys_user_in_organization(
    request: Request,
    payload: CreateOrgUserRequest,
):
    return await AdminUserController(_accept_language(request)).create_user(
        request=request, payload=payload,
    )


@router.get("/list/sys_user_device_pending")
async def list_sys_user_device_pending(
    request: Request,
    all_data: bool = Query(False),
    page: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sys_organization_id: str | None = Query(
        None,
        description=(
            "Optional cross-tenant override. Honored ONLY when the caller's "
            "profile is `system_profil` (cross-tenant break-glass). For every "
            "other role the caller's own organisation is used regardless."
        ),
    ),
):
    return await AdminUserController(_accept_language(request)).list_pending_devices(
        request=request,
        all_data=all_data,
        page=page,
        limit=limit,
        sys_organization_id=sys_organization_id,
    )


@router.get("/list/sys_user_device_all")
async def list_sys_user_device_all(
    request: Request,
    all_data: bool = Query(False),
    page: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sys_organization_id: str | None = Query(
        None,
        description=(
            "Cross-tenant override. Honored ONLY when caller is on "
            "`system_profil`. In-org admins are forced to their own org."
        ),
    ),
    sys_user_id: str | None = Query(
        None,
        description="Scope to a single user's devices (24-char hex).",
    ),
    status_filter: str | None = Query(
        None,
        description=(
            "One of `allowed` / `pending_validation` / `revoqued`. "
            "Omit (or pass any other value) to return every status."
        ),
    ),
):
    return await AdminUserController(_accept_language(request)).list_devices_all(
        request=request,
        all_data=all_data,
        page=page,
        limit=limit,
        sys_organization_id=sys_organization_id,
        sys_user_id=sys_user_id,
        status_filter=status_filter,
    )


@router.post("/patch/sys_user_device_activate")
async def patch_sys_user_device_activate(
    request: Request,
    payload: DeviceActivateRequest,
):
    return await AdminUserController(_accept_language(request)).activate_device(
        request=request, payload=payload,
    )


@router.post("/patch/sys_user_device_revoke")
async def patch_sys_user_device_revoke(
    request: Request,
    payload: DeviceRevokeRequest,
):
    return await AdminUserController(_accept_language(request)).revoke_device(
        request=request, payload=payload,
    )
