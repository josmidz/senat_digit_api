"""Request schemas for the admin user-management surface.

Owned by:
  - system_profil_super_admin (cross-tenant)
  - main_profile_super_admin  (in-org IT/owner)
  - greffier                  (device validation only)
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.modules.core.enums.type_enum import AccountStatusFlag


class AccountStatusPatchRequest(BaseModel):
    """Body for `POST /patch/sys_user_account_status`.

    Toggles a user's `account_status` to one of the lockable states.
    `LOCKED` and `LOCKED_BY_SYSTEM` differ only in attribution: the former
    is a manual admin action (audit trail flag), the latter is set by the
    auth pipeline after N failed login attempts. Admin lock/unlock from
    this endpoint always uses `LOCKED` / `ACTIVE`.

    `reason` is free-form text — surfaced in the audit log so the next
    admin reviewing the user knows why it was locked.
    """

    user_id: str = Field(..., description="Target sys_user._id (24-char hex).")
    account_status: AccountStatusFlag = Field(
        ...,
        description="ACTIVE to unlock, LOCKED to lock manually.",
    )
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Admin-supplied note explaining the action.",
    )


class DeviceActivateRequest(BaseModel):
    """Body for `POST /patch/sys_user_device_activate`.

    Promotes a `cfg_user_device` row from `pending_validation` to
    `allowed`. The greffier or main_profile_super_admin reviewing the
    request acts as the human gate the legacy email-link flow would
    have provided.
    """
    device_id: str = Field(..., description="Target cfg_user_device._id (24-char hex).")


class DeviceRevokeRequest(BaseModel):
    """Body for `POST /patch/sys_user_device_revoke`.

    Flips the device to `revoqued` (typo preserved from the legacy
    `EUserDeviceStatus` enum). Use to reject a suspicious activation
    request or to cancel access for a lost device.
    """
    device_id: str = Field(..., description="Target cfg_user_device._id (24-char hex).")
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Admin-supplied note. Stored on the device row + surfaced in the audit log.",
    )


class CreateOrgUserRequest(BaseModel):
    """Body for `POST /create/sys_user_in_organization`.

    Creates a user under the caller's organisation (or an explicit
    `sys_organization_id` when the caller is on the system profil).
    Role is identified by `role_flag` (e.g. `senateur`, `greffier`) —
    the controller resolves it to the matching `rbac_role` row scoped
    to MAIN_PROFILE. Same shape works for both demo and prod.

    Password is hashed server-side with the standard PasswordService.
    `allowed_device_count` is set to 5 by default so the user can pair
    multiple devices through their lifecycle without admin intervention.
    """
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=128)
    last_name: str = Field(..., min_length=1, max_length=128)
    email: str = Field(..., min_length=3, max_length=320)
    phone_number: Optional[str] = Field(None, max_length=64)

    role_flag: str = Field(
        ...,
        description=(
            "Role to assign — resolved against `rbac_role.flag` under "
            "MAIN_PROFILE. Typical values: `senateur`, `greffier`, "
            "`main_profile_super_admin`."
        ),
    )
    gender: Optional[str] = Field(
        "m",
        description="`m` | `f`. Required by the legacy SysUser model.",
    )

    sys_organization_id: Optional[str] = Field(
        None,
        description=(
            "Optional cross-tenant override. Honored ONLY when the "
            "caller's profile is `system_profil`. Every other role is "
            "forced to their own org regardless of what they pass."
        ),
    )

    should_update_password: bool = Field(
        True,
        description=(
            "When true (default), the user is required to change their "
            "password on first login. Recommended for any non-self "
            "creation: the admin sets a temporary, the user rotates."
        ),
    )
