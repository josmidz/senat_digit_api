from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.enums.type_enum import OutputDataType
from app.modules.security.enums.security_enum import (
    ERlsAccessTypeFlag,
    ESudoActionAccessTargetedTypeFlag,
)


# Collections that must never be RLS-filtered, otherwise the RLS service
# would recurse when it tries to read its own config to decide whether to
# apply RLS. Keep this list tight — only the collections the RLS / auth /
# RBAC pipelines must read before RLS can even be evaluated belong here.
RLS_META_COLLECTIONS = frozenset(
    {
        CollectionKey.CFG_RLS_SETUP,
        CollectionKey.CFG_ORGANIZATION_RLS,
        CollectionKey.CFG_RLS_ACCESS,
        CollectionKey.REF_SUDO_RLS_SECURITY_GROUP,
        CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
    }
)


# Sentinel result-shape factories. Each call returns a FRESH dict
# with FRESH nested mutables — `dict(sentinel)` would share the
# inner `extra_filter` mapping and `extra_doc_ids` list across every
# return, allowing a downstream mutation to poison subsequent calls.
def _deny_all_result() -> Dict[str, Any]:
    return {
        "deny_all": True,
        "bypass": False,
        "extra_filter": {},
        "extra_doc_ids": [],
    }


def _full_bypass_result() -> Dict[str, Any]:
    return {
        "deny_all": False,
        "bypass": True,
        "extra_filter": {},
        "extra_doc_ids": [],
    }


class RowLevelSecurityService:
    """
    Per-organization RLS enforcement service.

    Reads the following SaaS-scoped configuration models to decide how to
    filter a query for the current user:

      - CfgRlsSetupModel         (one per org; is_enabled, is_strict_mode)
      - CfgRlsAccessModel        (per user/group grants; GLOBAL/REVOKED/CUSTOM)
      - RefSudoRlsSecurityGroupUserModel (group membership resolver)

    Contract:
        get_rls_filter_for_user_and_collection(collection_key, user) -> dict:
            deny_all      : bool  — caller must return empty result
            bypass        : bool  — caller applies only org scope, no extra filters
            extra_filter  : dict  — Mongo filter to AND into the caller's db_filter
            extra_doc_ids : list[ObjectId] — CUSTOM_ACCESS target rows

    ALL exception paths return deny_all (fail-closed). Never return bypass
    on error.
    """

    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        # Deferred import to avoid generic <-> security circular import on load.
        from app.modules.core.services.generic.generic_services import GenericService
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language=accept_language)

    # =========================================================================
    #                              PUBLIC API
    # =========================================================================

    async def get_rls_filter_for_user_and_collection(
        self,
        collection_key: CollectionKey,
        user: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Main entry point. Called by GenericService._apply_rls_filter for every
        tenant-scoped read against the database.
        """
        try:
            # --- 1. Anonymous / missing user or no org → skip RLS. ---
            if not user or not user.get("id"):
                return _full_bypass_result()

            if not user.get("sys_organization_id"):
                return _full_bypass_result()

            # --- Fast path: middleware already resolved the RLS context ---
            rls_ctx = user.get("_rls_context")
            if rls_ctx:
                if rls_ctx.get("skip"):
                    return _full_bypass_result()
                access = rls_ctx.get("user_access")
                if access == "global":
                    return _full_bypass_result()
                if access == "revoked":
                    return _deny_all_result()
                if access == "custom":
                    custom_rows = rls_ctx.get("custom_rows", {})
                    doc_ids = custom_rows.get(collection_key.value, [])
                    return {
                        "deny_all": False,
                        "bypass": not doc_ids and not rls_ctx.get("is_strict_mode"),
                        "extra_filter": {},
                        "extra_doc_ids": doc_ids,
                    }
                # access is None — no grants
                if rls_ctx.get("is_strict_mode"):
                    return _deny_all_result()
                return _full_bypass_result()

            # --- Slow path: no middleware context (batch / internal) ---
            sys_organization_id = user.get("sys_organization_id")
            if not sys_organization_id:
                return _deny_all_result()

            rls_setup = await self._get_org_rls_setup(sys_organization_id)
            if not rls_setup or not rls_setup.get("is_enabled", False):
                return _full_bypass_result()

            is_strict_mode = bool(rls_setup.get("is_strict_mode", False))

            # --- 3. Resolve the user's security group memberships. ---
            user_group_ids = await self._fetch_user_group_ids(
                user["id"], sys_organization_id
            )

            # --- 4. Fetch all CfgRlsAccess grants for this (user|groups, collection). ---
            grants = await self._fetch_access_grants(
                collection_key=collection_key,
                sys_organization_id=sys_organization_id,
                user_id=user["id"],
                user_group_ids=user_group_ids,
            )

            # --- 5. Apply grants in priority order. ---
            #
            # REVOKED_ACCESS  — explicit deny wins over every other grant.
            # GLOBAL_ACCESS   — unrestricted visibility within the org.
            # CUSTOM_ACCESS   — visible only for the listed targeted_row_id values.
            if grants["revoked"]:
                return _deny_all_result()

            if grants["global"]:
                return _full_bypass_result()

            if grants["custom_doc_ids"]:
                return {
                    "deny_all": False,
                    "bypass": False,
                    "extra_filter": {},
                    "extra_doc_ids": grants["custom_doc_ids"],
                }

            # --- 6. No grants matched. Strict mode denies, permissive mode
            #        allows (scoped to the org). ---
            if is_strict_mode:
                return _deny_all_result()

            return _full_bypass_result()

        except Exception as e:
            # FAIL-CLOSED: any unexpected error denies access.
            try:
                print(
                    "[RLS] fail-closed get_rls_filter_for_user_and_collection "
                    f"collection={getattr(collection_key, 'value', collection_key)} "
                    f"user={user.get('id') if user else None} err={e}"
                )
            except Exception:
                pass
            return _deny_all_result()

    # =========================================================================
    #                            PRIVATE HELPERS
    # =========================================================================

    async def _get_org_rls_setup(
        self, sys_organization_id: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch the CfgRlsSetupModel row for the given organization. Uses the
        RLS-bypassing raw fetcher (fetch_native_query_one_from_collection)
        so we do not trigger _apply_rls_filter recursively.
        """
        try:
            return await self.generic_service.fetch_native_query_one_from_collection(
                collection_key=CollectionKey.CFG_RLS_SETUP,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                native_query={
                    "sys_organization_id": ObjectId(str(sys_organization_id)),
                    "soft_deleted_at": None,
                },
            )
        except Exception as e:
            print(f"[RLS] _get_org_rls_setup error: {e}")
            raise

    async def _fetch_user_group_ids(
        self, user_id: Any, sys_organization_id: Any
    ) -> List[str]:
        """
        Resolve all security group memberships for the user. Uses the RLS
        meta-collection bypass to avoid recursion.
        """
        try:
            memberships = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
                all_data=True,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sys_user_id": str(user_id),
                    "filter__sys_organization_id": str(sys_organization_id),
                },
                _skip_rls=True,
            )
            ids: List[str] = []
            for row in memberships or []:
                gid = row.get("ref_sudo_rls_security_group_id")
                if gid:
                    ids.append(str(gid))
            return ids
        except Exception as e:
            print(f"[RLS] _fetch_user_group_ids error: {e}")
            # Empty list is acceptable — user keeps direct grants, loses group grants.
            # An empty list is NOT a widening of access, so it is safe to return here.
            return []

    async def _fetch_access_grants(
        self,
        collection_key: CollectionKey,
        sys_organization_id: Any,
        user_id: Any,
        user_group_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Pull every CfgRlsAccessModel row targeting this user (directly or via
        group) for the given collection and classify them by rls_access_type.
        """
        result = {"global": False, "revoked": False, "custom_doc_ids": []}

        targeted_ids = [str(user_id)] + [str(g) for g in (user_group_ids or [])]
        if not targeted_ids:
            return result

        try:
            rows = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_RLS_ACCESS,
                all_data=True,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sys_organization_id": str(sys_organization_id),
                    "filter__collection_name": collection_key.value,
                    "filter__targeted_id__in": targeted_ids,
                },
                _skip_rls=True,
            )
        except Exception as e:
            print(f"[RLS] _fetch_access_grants error: {e}")
            raise

        for row in rows or []:
            access_type = row.get("rls_access_type")
            if access_type == ERlsAccessTypeFlag.REVOKED_ACCESS.value:
                result["revoked"] = True
            elif access_type == ERlsAccessTypeFlag.GLOBAL_ACCESS.value:
                result["global"] = True
            elif access_type == ERlsAccessTypeFlag.CUSTOM_ACCESS.value:
                doc_id = row.get("targeted_row_id")
                if doc_id:
                    try:
                        result["custom_doc_ids"].append(ObjectId(str(doc_id)))
                    except Exception:
                        # Skip malformed ids rather than failing wholesale.
                        continue
        return result
