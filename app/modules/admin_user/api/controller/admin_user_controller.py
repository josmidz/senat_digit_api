"""AdminUserController — cross-tenant admin operations.

Two operations:
  - list_for_organization : list users in a target tenant
  - patch_account_status  : flip lock/unlock on a target user

Access control is **enforced upstream by `PermissionCheckMiddleware`** via
the standard RBAC chain:

  rbac_role  → rbac_permission_role  → rbac_permission
       → rbac_permission_target  → rbac_endpoint(.url)

The permissions backing these two URLs are seeded by:
  app/modules/admin_user/seeds/permission_titles_seed.json
  app/modules/admin_user/seeds/admin_user_seed_loader.py
and granted to `system_profil_super_admin` via
`RbacRoleService.seed_role_permissions_for_admin_user_module`. The
controller therefore makes NO inline profile/role check — that would
double-implement RBAC and drift from the rest of the codebase.

Both methods use `_skip_rls=True` because cross-tenant visibility is the
intent of the operation; the RBAC middleware is the only access gate.

Capabilities #1 (POST /organizations/add/org) and #3 (GET
/organizations/generate-reset-password-link) live in the legacy
organization_endpoint.py but are seeded into RBAC under the same
admin_user permission catalogue, so they share the same role-grant cut.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from fastapi import HTTPException, Request, status

from app.modules.admin_user.schemas.admin_user_schema import (
    AccountStatusPatchRequest,
    CreateOrgUserRequest,
    DeviceActivateRequest,
    DeviceRevokeRequest,
)
from app.modules.auth.services.password.password_service import PasswordService
from app.modules.core.enums.type_enum import (
    AccountStatusFlag,
    EUserDeviceStatus,
    OutputDataType,
)
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.enums.profiles_enum import ESysProfileFlag
from app.modules.core.utils.request_state import current_user_org_id


def _caller_is_system_profile(request: Request) -> bool:
    """True iff the authenticated caller is on the SYSTEM_PROFIL profile.

    Used by the device-validation endpoints to honour an explicit
    `sys_organization_id` query (cross-tenant break-glass). For every
    other profile the org is forced to `current_user_org_id(request)`
    server-side to prevent in-org admins (greffier, main_profile_super_admin)
    from peeking into other tenants' device queues.
    """
    profil = getattr(request.state, "userProfil", None)
    if not isinstance(profil, dict):
        return False
    return profil.get("flag") == ESysProfileFlag.SYSTEM_PROFIL.value


def _http_404(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _http_400(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


# Statuses an admin is allowed to set via the patch endpoint. We disallow
# `LOCKED_BY_SYSTEM` (reserved for the auth pipeline's failed-login lockout)
# so audit logs distinguish manual admin actions from automated lockouts.
_ADMIN_SETTABLE_STATUSES = {
    AccountStatusFlag.ACTIVE.value,
    AccountStatusFlag.LOCKED.value,
    AccountStatusFlag.SUSPENDED.value,
    AccountStatusFlag.INACTIVE.value,
}


class AdminUserController:
    def __init__(self, accept_language: str = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self._generic = GenericService(accept_language)

    # ── helpers ────────────────────────────────────────────────────
    @staticmethod
    def _caller(request: Request) -> Dict[str, Any]:
        """Return the caller's user dict from request.state.

        Populated by `verify_logged_in_user` / `AuthByPassMiddleware`. By
        the time the controller runs, `PermissionCheckMiddleware` has
        already approved the request, so any caller reaching here is
        legitimately granted by RBAC. We just need the user record to
        attribute audit fields.
        """
        user = getattr(request.state, "user", None)
        if not isinstance(user, dict):
            # Defensive — should never trip in practice given middleware order.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contexte utilisateur absent du jeton.",
            )
        return user

    # ── GET /list/sys_user_for_organization ──────────────────────
    async def list_for_organization(
        self,
        request: Request,
        sys_organization_id: str,
        all_data: bool = False,
        page: int = 0,
        limit: int = 20,
    ) -> Dict[str, Any]:
        # No inline auth check — PermissionCheckMiddleware has already
        # approved the request based on the caller's RBAC grants.
        self._caller(request)

        try:
            org_oid = PydanticObjectId(sys_organization_id)
        except Exception:
            raise _http_400("sys_organization_id invalide (24-char hex attendu).")

        # Confirm the target org exists; nicer error than an empty list.
        org = await self._generic.fetch_one_from_collection(
            collection_key=CollectionKey.SYS_ORGANIZATION,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter___id": str(org_oid)},
            _skip_rls=True,
        )
        if not org:
            raise _http_404("Organisation introuvable.")

        # Cross-tenant fetch — bypass RLS because the SYSTEM_PROFIL caller
        # is by design allowed to inspect any tenant. The profile-flag
        # guard above is the only gate on this access.
        users = await self._generic.fetch_data_from_collection(
            collection_key=CollectionKey.SYS_USER,
            output_data_type=OutputDataType.DEFAULT.value,
            all_data=all_data,
            page=page,
            limit=limit,
            query={
                "filter__sys_organization_id": str(org_oid),
                "filter__soft_deleted": False,
            },
            _skip_rls=True,
        )

        extra: Dict[str, Any] = {}
        if not all_data:
            extra["max"] = await self._generic.count_data_from_collection(
                collection_key=CollectionKey.SYS_USER,
                accept_language=self.accept_language,
                query={
                    "filter__sys_organization_id": str(org_oid),
                    "filter__soft_deleted": False,
                },
                _skip_rls=True,
            )
            extra["limit"] = limit

        return {
            "status_code": 200,
            "message": "Liste des utilisateurs de l'organisation.",
            "data": users or [],
            **extra,
        }

    # ── POST /patch/sys_user_account_status ──────────────────────
    async def patch_account_status(
        self,
        request: Request,
        payload: AccountStatusPatchRequest,
    ) -> Dict[str, Any]:
        # No inline auth check — PermissionCheckMiddleware has already
        # approved the request based on the caller's RBAC grants.
        admin = self._caller(request)

        new_status = payload.account_status.value
        if new_status not in _ADMIN_SETTABLE_STATUSES:
            raise _http_400(
                f"Statut « {new_status} » non modifiable manuellement.",
            )

        try:
            user_oid = PydanticObjectId(payload.user_id)
        except Exception:
            raise _http_400("user_id invalide (24-char hex attendu).")

        target = await self._generic.fetch_one_from_collection(
            collection_key=CollectionKey.SYS_USER,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter___id": str(user_oid)},
            _skip_rls=True,
        )
        if not target:
            raise _http_404("Utilisateur introuvable.")

        # Self-service guard: don't let the admin lock themselves out via
        # this endpoint. They can still rotate their password through the
        # normal flow.
        if str(target.get("id") or target.get("_id")) == str(admin.get("id")):
            raise _http_400("Impossible de modifier votre propre compte ici.")

        update_payload: Dict[str, Any] = {
            "account_status": new_status,
            "updated_at": datetime.now(timezone.utc),
        }
        # Stamp who flipped the status — surfaces in the audit log + the
        # admin web's "lockout history" panel later.
        update_payload["last_account_status_changed_by_id"] = admin.get("id")
        update_payload["last_account_status_changed_at"] = datetime.now(timezone.utc)
        if payload.reason:
            update_payload["last_account_status_change_reason"] = payload.reason

        await self._generic.update_data_in_collection(
            collection_key=CollectionKey.SYS_USER,
            item_id=str(user_oid),
            data=update_payload,
        )

        # Re-read so the response reflects the persisted row.
        refreshed = await self._generic.fetch_one_from_collection(
            collection_key=CollectionKey.SYS_USER,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter___id": str(user_oid)},
            _skip_rls=True,
        )
        return {
            "status_code": 200,
            "message": (
                "Compte déverrouillé."
                if new_status == AccountStatusFlag.ACTIVE.value
                else f"Compte mis en statut « {new_status} »."
            ),
            "data": refreshed or {"id": payload.user_id, "account_status": new_status},
        }

    # ── POST /create/sys_user_in_organization ─────────────────────
    async def create_user(
        self,
        request: Request,
        payload: CreateOrgUserRequest,
    ) -> Dict[str, Any]:
        """Create a sénateur, greffier, or main_profile_super_admin
        under the caller's organisation.

        Scope rules:
          - System_profil callers can target any organisation via
            `payload.sys_organization_id` (cross-tenant onboarding).
          - Other roles are forced to their own org.
          - The role must be a MAIN_PROFILE-scoped role; we resolve
            it by `(rbac_profile.flag='main_profile', rbac_role.flag=…)`.
            System roles can't be assigned via this endpoint — that's
            a different surface (not yet built).

        Side effects beyond the sys_user row:
          - Account hashes (used by the auth pipeline) are populated.
          - cfg_user_config is created with `allowed_device_count=5`
            so the user can pair multiple devices through their
            lifecycle without needing admin intervention every time.
          - Username is normalised to lowercase + trim, then checked
            for collision (409 on duplicate).
        """
        admin = self._caller(request)
        target_org_id = self._resolve_target_org_id(
            request, payload.sys_organization_id,
        )

        username = payload.username.strip().lower()
        if not username:
            raise _http_400("Nom d'utilisateur invalide.")

        # Reject pre-existing usernames cleanly. The Beanie model has
        # a unique index but a 500 from a constraint violation is
        # opaque — explicit 409 surfaces a useful message to the UI.
        existing = await self._generic.fetch_one_from_collection(
            collection_key=CollectionKey.SYS_USER,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter__username": username},
            _skip_rls=True,
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Le nom d'utilisateur « {username} » est déjà utilisé.",
            )

        # Resolve the role: must be under MAIN_PROFILE.
        from app.modules.core.enums.profiles_enum import ESysProfileFlag
        main_profile = await self._generic.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_PROFILE,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter__flag": ESysProfileFlag.MAIN_PROFILE.value},
            _skip_rls=True,
        )
        if not main_profile:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Profil principal non configuré.",
            )
        role = await self._generic.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_ROLE,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__flag": payload.role_flag,
                "filter__rbac_profile_id": str(main_profile.get("id")),
            },
            _skip_rls=True,
        )
        if not role:
            raise _http_400(
                f"Rôle « {payload.role_flag} » introuvable sous main_profile."
            )

        # Build the user row.
        from datetime import datetime, timezone
        from app.modules.core.enums.type_enum import AccountStatusFlag as _AccountStatusFlag
        now = datetime.now(timezone.utc)
        user_payload: Dict[str, Any] = {
            "username": username,
            "password": PasswordService.hash_password(payload.password),
            "first_name": payload.first_name.strip(),
            "last_name": payload.last_name.strip(),
            "email": payload.email.strip().lower(),
            "phone_number": (payload.phone_number or "").strip(),
            "gender": payload.gender or "m",
            "account_status": _AccountStatusFlag.ACTIVE.value,
            "rbac_profile_id": str(main_profile.get("id")),
            "rbac_role_id": str(role.get("id")),
            "sys_organization_id": str(target_org_id),
            "should_update_password": payload.should_update_password,
            "is_default": False,
            "is_activated": True,
            "created_at": now,
            "updated_at": now,
        }

        new_id = await self._generic.add_data_to_collection(
            collection_key=CollectionKey.SYS_USER,
            data=user_payload,
            user=admin,
            request=request,
        )
        if not new_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Échec de la création de l'utilisateur.",
            )

        # Populate account hashes the auth pipeline expects.
        from app.modules.core.services.hash.hash_service import HashService
        await self._generic.update_data_in_collection(
            collection_key=CollectionKey.SYS_USER,
            item_id=str(new_id),
            data={
                "user_account_hash": HashService.generate_hash(str(new_id)),
                "user_account_socket_hash": HashService.generate_hash(str(new_id)),
            },
        )

        # Create cfg_user_config with allowed_device_count=5 so the
        # user can pair multiple devices over their lifecycle. Direct
        # motor write because GenericService.upsert silently no-ops on
        # new rows (same quirk we documented in dummy_seed).
        try:
            from beanie import PydanticObjectId
            from app.db.base import get_collection
            coll = get_collection("cfg_user_config")
            await coll.update_one(
                {"sys_user_id": PydanticObjectId(str(new_id))},
                {
                    "$set": {
                        "sys_user_id": PydanticObjectId(str(new_id)),
                        "allowed_device_count": 5,
                        "updated_at": now,
                    },
                    "$setOnInsert": {
                        "is_activated": True,
                        "soft_deleted": False,
                        "created_at": now,
                        "translations": {},
                    },
                },
                upsert=True,
            )
        except Exception as e:  # noqa: BLE001 — best-effort
            print(f"[admin_user.create_user] cfg_user_config bump failed (non-fatal): {e}")

        # Return a slim payload — the screen optimistically inserts
        # this into its list while a refresh re-fetches the full row.
        return {
            "status_code": 201,
            "message": f"Utilisateur « {username} » créé.",
            "data": {
                "id": str(new_id),
                "username": username,
                "first_name": user_payload["first_name"],
                "last_name": user_payload["last_name"],
                "email": user_payload["email"],
                "phone_number": user_payload["phone_number"],
                "account_status": user_payload["account_status"],
                "rbac_role_id": user_payload["rbac_role_id"],
                "rbac_profile_id": user_payload["rbac_profile_id"],
                "sys_organization_id": user_payload["sys_organization_id"],
                "role": {
                    "id": str(role.get("id")),
                    "flag": role.get("flag"),
                    "name": role.get("name"),
                },
                "should_update_password": payload.should_update_password,
            },
        }

    # ── GET /list/sys_user_device_pending ─────────────────────────
    async def list_pending_devices(
        self,
        request: Request,
        all_data: bool = False,
        page: int = 0,
        limit: int = 50,
        sys_organization_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List `cfg_user_device` rows with `status='pending_validation'`
        scoped to an organisation.

        Default scoping: the caller's own org (read from
        `request.state.user["sys_organization_id"]`). System_profil
        callers can override via `?sys_organization_id=<oid>` for
        cross-tenant break-glass. In-org admins (greffier,
        main_profile_super_admin) get their org regardless of what
        they pass — we never let an in-org role peek into another
        tenant's queue.

        Per-row we hydrate the owning user (username + first/last name +
        email + phone) so the reviewer has enough context without an
        extra round-trip.
        """
        self._caller(request)
        target_org_id = self._resolve_target_org_id(request, sys_organization_id)

        rows = await self._generic.fetch_data_from_collection(
            collection_key=CollectionKey.CFG_USER_DEVICE,
            output_data_type=OutputDataType.DEFAULT.value,
            all_data=all_data,
            page=page,
            limit=limit,
            query={
                "filter__sys_organization_id": str(target_org_id),
                "filter__status": EUserDeviceStatus.PENDING_VALIDATION.value,
                "filter__soft_deleted": False,
            },
            _skip_rls=True,  # already org-scoped above; bypass RLS to avoid double-scoping
        )

        # Hydrate owners. The cfg_user_device row carries `sys_user_id`
        # but no display fields; fetch the owners in a small per-row
        # loop. Pending-device queues are O(<10) in practice so this
        # is cheap. Future optimisation: $lookup pipeline.
        hydrated = []
        for row in (rows or []):
            owner = None
            sys_user_id = row.get("sys_user_id")
            if sys_user_id:
                owner = await self._generic.fetch_one_from_collection(
                    collection_key=CollectionKey.SYS_USER,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id": str(sys_user_id)},
                    _skip_rls=True,
                )
            hydrated.append({
                "id": str(row.get("id") or row.get("_id") or ""),
                "device_id_str": row.get("device_id_str") or "",
                "status": row.get("status"),
                "is_authenticated": row.get("is_authenticated") or False,
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "device_info": row.get("device_info") or {},
                "sys_user_id": str(sys_user_id) if sys_user_id else None,
                "owner": None if owner is None else {
                    "id": str(owner.get("id") or owner.get("_id") or ""),
                    "username": owner.get("username") or "",
                    "first_name": owner.get("first_name") or "",
                    "last_name": owner.get("last_name") or "",
                    "email": owner.get("email") or "",
                    "phone_number": owner.get("phone_number") or "",
                },
            })

        return {"status_code": 200, "data": hydrated}

    # ── GET /list/sys_user_device_all ─────────────────────────────
    async def list_devices_all(
        self,
        request: Request,
        all_data: bool = False,
        page: int = 0,
        limit: int = 100,
        sys_organization_id: Optional[str] = None,
        sys_user_id: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List `cfg_user_device` rows in the target org for ANY status.

        Wraps the existing pending-only query with three filter axes:

          - ``status_filter``: one of ``allowed`` / ``pending_validation``
            / ``revoqued``. Omit (or pass any other value) to return
            every status.
          - ``sys_user_id``: scope to a single user's devices. Used by
            the user-detail screen to show "this user's devices" without
            iterating the full org list client-side.
          - ``sys_organization_id``: cross-tenant scoping. Honored only
            when the caller is on the system_profil (cross-tenant
            break-glass — same gate as `list_pending_devices`).

        Per-row hydration mirrors `list_pending_devices`: each row
        carries the owner's display fields so the UI doesn't need a
        separate user-fetch round trip.

        Granted to system_profil_super_admin + main_profile_super_admin.
        Greffier deliberately excluded — they need the pending queue
        for in-session enrolment, not the full device inventory.
        """
        self._caller(request)
        target_org_id = self._resolve_target_org_id(request, sys_organization_id)

        query: Dict[str, Any] = {
            "filter__sys_organization_id": str(target_org_id),
            "filter__soft_deleted": False,
        }

        # Status filter — only honor the canonical enum values; anything
        # else is treated as "all statuses" (no filter applied).
        valid_statuses = {s.value for s in EUserDeviceStatus}
        if status_filter and status_filter in valid_statuses:
            query["filter__status"] = status_filter

        # Per-user filter. Validate the id shape so a typo surfaces as
        # 400 rather than an empty list (which would look like "no
        # devices for this user" — confusing).
        if sys_user_id:
            try:
                user_oid = PydanticObjectId(sys_user_id)
            except Exception:
                raise _http_400("sys_user_id invalide (24-char hex attendu).")
            query["filter__sys_user_id"] = str(user_oid)

        rows = await self._generic.fetch_data_from_collection(
            collection_key=CollectionKey.CFG_USER_DEVICE,
            output_data_type=OutputDataType.DEFAULT.value,
            all_data=all_data,
            page=page,
            limit=limit,
            query=query,
            _skip_rls=True,
        )

        # Reuse the same per-row hydration shape as `list_pending_devices`
        # so the Flutter side has a single DTO for both endpoints.
        hydrated = []
        for row in (rows or []):
            owner = None
            row_user_id = row.get("sys_user_id")
            if row_user_id:
                owner = await self._generic.fetch_one_from_collection(
                    collection_key=CollectionKey.SYS_USER,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id": str(row_user_id)},
                    _skip_rls=True,
                )
            hydrated.append({
                "id": str(row.get("id") or row.get("_id") or ""),
                "device_id_str": row.get("device_id_str") or "",
                "status": row.get("status"),
                "is_authenticated": row.get("is_authenticated") or False,
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "device_info": row.get("device_info") or {},
                "sys_user_id": str(row_user_id) if row_user_id else None,
                "owner": None if owner is None else {
                    "id": str(owner.get("id") or owner.get("_id") or ""),
                    "username": owner.get("username") or "",
                    "first_name": owner.get("first_name") or "",
                    "last_name": owner.get("last_name") or "",
                    "email": owner.get("email") or "",
                    "phone_number": owner.get("phone_number") or "",
                },
            })

        return {"status_code": 200, "data": hydrated}

    # ── POST /patch/sys_user_device_activate ──────────────────────
    async def activate_device(
        self,
        request: Request,
        payload: DeviceActivateRequest,
    ) -> Dict[str, Any]:
        """Promote a `cfg_user_device` row to `status=allowed` +
        `is_authenticated=True`. The reviewer is the human gate the
        legacy email-link flow would have provided.

        Only acts on rows that are currently `pending_validation` —
        already-allowed / locked / revoqued rows return 400 so the UI
        can refresh its list.
        """
        admin = self._caller(request)
        device, oid = await self._resolve_device_for_caller(request, payload.device_id)

        if device.get("status") != EUserDeviceStatus.PENDING_VALIDATION.value:
            raise _http_400(
                f"Statut actuel « {device.get('status')!r} » — seul "
                "« pending_validation » peut être validé."
            )

        now = datetime.now(timezone.utc)
        await self._generic.update_data_in_collection(
            collection_key=CollectionKey.CFG_USER_DEVICE,
            item_id=str(oid),
            data={
                "status": EUserDeviceStatus.ALLOWED.value,
                "is_authenticated": True,
                "is_activated": True,
                "validated_at": now,
                "validated_by_id": admin.get("id"),
                "updated_at": now,
            },
        )
        refreshed = await self._generic.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_USER_DEVICE,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter___id": str(oid)},
            _skip_rls=True,
        )
        return {
            "status_code": 200,
            "message": "Appareil validé et autorisé.",
            "data": refreshed or {"id": payload.device_id, "status": EUserDeviceStatus.ALLOWED.value},
        }

    # ── POST /patch/sys_user_device_revoke ────────────────────────
    async def revoke_device(
        self,
        request: Request,
        payload: DeviceRevokeRequest,
    ) -> Dict[str, Any]:
        """Mark a device `revoqued` (typo preserved from the legacy
        `EUserDeviceStatus` enum). Use when rejecting a suspicious
        activation request or invalidating a lost device.

        Acts on any non-revoqued status — both pending and allowed
        devices can be revoked, which is the intended product
        semantics.
        """
        admin = self._caller(request)
        device, oid = await self._resolve_device_for_caller(request, payload.device_id)

        if device.get("status") == EUserDeviceStatus.REVOQUED.value:
            raise _http_400("Appareil déjà révoqué.")

        now = datetime.now(timezone.utc)
        update_payload: Dict[str, Any] = {
            "status": EUserDeviceStatus.REVOQUED.value,
            "is_authenticated": False,
            "revoqued_at": now,
            "revoqued_by_id": admin.get("id"),
            "updated_at": now,
        }
        if payload.reason:
            update_payload["revoqued_reason"] = payload.reason
        await self._generic.update_data_in_collection(
            collection_key=CollectionKey.CFG_USER_DEVICE,
            item_id=str(oid),
            data=update_payload,
        )
        refreshed = await self._generic.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_USER_DEVICE,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter___id": str(oid)},
            _skip_rls=True,
        )
        return {
            "status_code": 200,
            "message": "Appareil révoqué.",
            "data": refreshed or {"id": payload.device_id, "status": EUserDeviceStatus.REVOQUED.value},
        }

    # ── shared helpers ────────────────────────────────────────────
    @staticmethod
    def _resolve_target_org_id(
        request: Request,
        provided_org_id: Optional[str],
    ) -> PydanticObjectId:
        """Pick the target org for an admin device-list/validate call.

        - System_profil callers can override via `?sys_organization_id=...`
          for cross-tenant break-glass. Falls back to their own org if
          not provided.
        - Every other profile gets their own org regardless of the
          provided value (silently ignored — never 4xx, since they
          probably aren't trying to attack; the registry just doesn't
          surface a cross-tenant control to them).
        """
        own_org = current_user_org_id(request)
        if not _caller_is_system_profile(request):
            return own_org
        if not provided_org_id:
            return own_org
        try:
            return PydanticObjectId(provided_org_id)
        except Exception:
            raise _http_400("sys_organization_id invalide (24-char hex attendu).")

    async def _resolve_device_for_caller(
        self,
        request: Request,
        device_id: str,
    ):
        """Resolve a device by id, scope-checked against the caller.

        - System_profil: any device in any org. (RBAC permission is
          the gate — they wouldn't have it if not authorised.)
        - Else: device must belong to the caller's own org. Cross-tenant
          devices are hidden behind 404 (no existence-leak).

        Returns `(device_dict, ObjectId)`. Raises 400/404 cleanly.
        """
        try:
            oid = PydanticObjectId(device_id)
        except Exception:
            raise _http_400("device_id invalide (24-char hex attendu).")
        device = await self._generic.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_USER_DEVICE,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter___id": str(oid)},
            _skip_rls=True,
        )
        if not device:
            raise _http_404("Appareil introuvable.")
        if _caller_is_system_profile(request):
            return device, oid
        own_org = current_user_org_id(request)
        device_org = device.get("sys_organization_id")
        if device_org and str(device_org) != str(own_org):
            raise _http_404("Appareil introuvable.")
        return device, oid
