from typing import Any, Dict, List, Optional, Set

from fastapi import HTTPException, Request, status
from beanie import PydanticObjectId

from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.types.response import CustomJSONResponse
from app.modules.security.enums.security_enum import (
    ERlsAccessTypeFlag,
    ESudoActionAccessTargetedTypeFlag,
)


class RlsUsersAccessesController(DebugService, ResponseService, ConverterService, AuthenticatedService):
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        super().__init__(accept_language)

    # ─── FETCH RLS USERS ACCESSES OVERVIEW ────────────────────────────────────

    async def fetch_rls_users_accesses(self, request: Request):
        """
        Build a per-user RLS access overview:
        - For each user: count of RLS access assignments per access type (global / revoked / custom)
        - Summary: total users, assigned users, unassigned users, coverage %
        - Per access type aggregated user counts
        - Permission stats: total RLS permissions, enabled, strict-mode
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            org_filter = {"filter__sys_organization_id": user_details["sys_organization_id"]}

            # ─── 1. Fetch all org users ───────────────────────────────────
            all_users = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.SYS_USER,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={**org_filter},
                user=user_details,
            )

            # ─── 2. Fetch all RLS access entries (user-targeted) ──────────
            all_access_entries = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_RLS_ACCESS,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    **org_filter,
                    "filter__targeted_type": ESudoActionAccessTargetedTypeFlag.USER.value,
                },
                user=user_details,
            )

            # ─── 3. Fetch group-based entries & resolve members ───────────
            group_access_entries = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_RLS_ACCESS,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    **org_filter,
                    "filter__targeted_type": ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value,
                },
                user=user_details,
            )

            # Map group_id -> list of rls access types from group entries
            group_access_map: Dict[str, List[str]] = {}
            for entry in group_access_entries:
                gid = str(entry.get("targeted_id", ""))
                rls_access_type = entry.get("rls_access_type", "")
                if gid:
                    if gid not in group_access_map:
                        group_access_map[gid] = []
                    group_access_map[gid].append(rls_access_type)

            # Resolve group members
            group_user_map: Dict[str, Set[str]] = {}  # group_id -> set of user_ids
            for gid in group_access_map:
                group_users = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
                    all_data=True,
                    page=0,
                    limit=100000,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={"filter__ref_sudo_rls_security_group_id": gid},
                    user=user_details,
                )
                user_ids = set()
                for gu in group_users:
                    uid = str(gu.get("sys_user_id", ""))
                    if uid:
                        user_ids.add(uid)
                group_user_map[gid] = user_ids

            # ─── 4. Build per-user access breakdown ──────────────────────
            access_type_keys = [
                ERlsAccessTypeFlag.GLOBAL_ACCESS.value,
                ERlsAccessTypeFlag.REVOKED_ACCESS.value,
                ERlsAccessTypeFlag.CUSTOM_ACCESS.value,
            ]

            # user_id -> {rls_access_type: count, direct / group counts}
            user_access_data: Dict[str, Dict[str, Any]] = {}

            def ensure_user(uid: str):
                if uid not in user_access_data:
                    user_access_data[uid] = {
                        "direct_count": 0,
                        "group_count": 0,
                        "total_count": 0,
                        "access_types": {at: 0 for at in access_type_keys},
                    }

            # Direct user entries
            for entry in all_access_entries:
                uid = str(entry.get("targeted_id", ""))
                rls_access_type = entry.get("rls_access_type", "")
                if uid:
                    ensure_user(uid)
                    user_access_data[uid]["direct_count"] += 1
                    user_access_data[uid]["total_count"] += 1
                    if rls_access_type in user_access_data[uid]["access_types"]:
                        user_access_data[uid]["access_types"][rls_access_type] += 1

            # Group-based entries
            for gid, access_types_list in group_access_map.items():
                member_ids = group_user_map.get(gid, set())
                for uid in member_ids:
                    ensure_user(uid)
                    for rls_access_type in access_types_list:
                        user_access_data[uid]["group_count"] += 1
                        user_access_data[uid]["total_count"] += 1
                        if rls_access_type in user_access_data[uid]["access_types"]:
                            user_access_data[uid]["access_types"][rls_access_type] += 1

            # ─── 5. Build user list with details ─────────────────────────
            users_list: List[Dict[str, Any]] = []
            assigned_user_ids: Set[str] = set()

            for user in all_users:
                uid = str(user.get("_id", user.get("id", "")))
                first_name = user.get("first_name", "")
                last_name = user.get("last_name", "")
                email = user.get("email", "")
                phone = user.get("phone", "")
                avatar = user.get("avatar", "")

                access_info = user_access_data.get(uid, {
                    "direct_count": 0,
                    "group_count": 0,
                    "total_count": 0,
                    "access_types": {at: 0 for at in access_type_keys},
                })

                is_assigned = access_info["total_count"] > 0
                if is_assigned:
                    assigned_user_ids.add(uid)

                users_list.append({
                    "user_id": uid,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "phone": phone,
                    "avatar": avatar,
                    "is_assigned": is_assigned,
                    "direct_count": access_info["direct_count"],
                    "group_count": access_info["group_count"],
                    "total_count": access_info["total_count"],
                    "access_types": access_info["access_types"],
                })

            # Sort: assigned users first, then by total_count desc, then alphabetically
            users_list.sort(key=lambda u: (-int(u["is_assigned"]), -u["total_count"], u["last_name"]))

            # ─── 6. Summary stats ─────────────────────────────────────────
            total_users = len(all_users)
            assigned_count = len(assigned_user_ids)
            unassigned_count = total_users - assigned_count
            coverage_pct = round((assigned_count / total_users) * 100, 1) if total_users > 0 else 0.0

            # Per access type: how many unique users have at least 1 entry
            access_type_user_counts: Dict[str, int] = {}
            for at in access_type_keys:
                count = sum(1 for u in users_list if u["access_types"].get(at, 0) > 0)
                access_type_user_counts[at] = count

            # ─── 7. RLS permission stats ──────────────────────────────────
            total_permissions = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.CFG_ORGANIZATION_RLS,
                accept_language=self.accept_language,
                query={**org_filter},
                user=user_details,
            )

            enabled_permissions = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.CFG_ORGANIZATION_RLS,
                accept_language=self.accept_language,
                query={
                    **org_filter,
                    "filter__is_enabled": True,
                },
                user=user_details,
            )

            strict_mode_count = await self.generic_service.count_data_from_collection(
                collection_key=CollectionKey.CFG_ORGANIZATION_RLS,
                accept_language=self.accept_language,
                query={
                    **org_filter,
                    "filter__is_strict_mode": True,
                },
                user=user_details,
            )

            enabled_pct = round((enabled_permissions / total_permissions) * 100, 1) if total_permissions > 0 else 0.0

            # ─── 8. Build response ────────────────────────────────────────
            overview = {
                "summary": {
                    "total_users": total_users,
                    "assigned_users": assigned_count,
                    "unassigned_users": unassigned_count,
                    "coverage_pct": coverage_pct,
                },
                "access_type_user_counts": access_type_user_counts,
                "permission_stats": {
                    "total": total_permissions,
                    "enabled": enabled_permissions,
                    "enabled_pct": enabled_pct,
                    "strict_mode": strict_mode_count,
                },
                "users": users_list,
            }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "RLS users accesses overview fetched successfully",
                    "data": overview,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── FETCH INDIVIDUAL USER RLS DETAIL ─────────────────────────────────────

    async def fetch_user_rls_detail(self, request: Request, user_id: str):
        """
        Fetch comprehensive RLS access overview for a single user:
        - Direct access entries (targeted_type=USER, targeted_id=user_id)
        - Group-based entries (resolved through group membership)
        - Each entry resolved with its CfgOrganizationRls permission details
        - Categorized into whitelist (global_access), blacklist (revoked_access), custom (custom_access)
        - Permission stats for the user's rules
        - Group memberships with member counts
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            org_filter = {"filter__sys_organization_id": user_details["sys_organization_id"]}

            # ─── 1. Fetch user info ───────────────────────────────────────
            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter___id": user_id},
                user=user_details,
            )

            if not user_info:
                raise HTTPException(status_code=404, detail="User not found.")

            # ─── 2. Direct access entries ─────────────────────────────────
            direct_entries = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_RLS_ACCESS,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    **org_filter,
                    "filter__targeted_type": ESudoActionAccessTargetedTypeFlag.USER.value,
                    "filter__targeted_id": user_id,
                },
                user=user_details,
            )

            # ─── 3. Fetch user's group memberships ───────────────────────
            user_group_links = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter__sys_user_id": user_id},
                user=user_details,
            )

            user_group_ids = set()
            group_info_map: Dict[str, Dict[str, Any]] = {}
            for link in user_group_links:
                gid = str(link.get("ref_sudo_rls_security_group_id", ""))
                if gid:
                    user_group_ids.add(gid)

            # Fetch group details with member counts
            for gid in user_group_ids:
                group_detail = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={"filter___id": gid},
                    user=user_details,
                )
                if group_detail:
                    # Count members in this group
                    member_count = await self.generic_service.count_data_from_collection(
                        collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
                        accept_language=self.accept_language,
                        query={"filter__ref_sudo_rls_security_group_id": gid},
                        user=user_details,
                    )
                    # Count RLS access entries for this group
                    group_rules_count = await self.generic_service.count_data_from_collection(
                        collection_key=CollectionKey.CFG_RLS_ACCESS,
                        accept_language=self.accept_language,
                        query={
                            **org_filter,
                            "filter__targeted_type": ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value,
                            "filter__targeted_id": gid,
                        },
                        user=user_details,
                    )
                    group_info_map[gid] = {
                        "group_id": gid,
                        "name": group_detail.get("name", ""),
                        "identifier": group_detail.get("identifier", ""),
                        "member_count": member_count,
                        "rules_count": group_rules_count,
                    }

            # ─── 4. Group-based access entries ────────────────────────────
            group_entries: List[Dict[str, Any]] = []
            for gid in user_group_ids:
                entries = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_RLS_ACCESS,
                    all_data=True,
                    page=0,
                    limit=100000,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={
                        **org_filter,
                        "filter__targeted_type": ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value,
                        "filter__targeted_id": gid,
                    },
                    user=user_details,
                )
                for entry in entries:
                    entry["_resolved_group"] = group_info_map.get(gid, {"group_id": gid, "name": "", "identifier": "", "member_count": 0, "rules_count": 0})
                    group_entries.append(entry)

            # ─── 5. Resolve permission details for each entry ─────────────
            async def resolve_entry(entry: Dict[str, Any], source: str, group: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
                rls_access_type = entry.get("rls_access_type", "")
                cfg_org_rls_id = str(entry.get("cfg_organization_rls_id", ""))

                # Resolve the CfgOrganizationRls permission
                permission_label = ""
                is_enabled = False
                is_strict_mode = False

                if cfg_org_rls_id:
                    perm = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.CFG_ORGANIZATION_RLS,
                        output_data_type=OutputDataType.DEFAULT.value,
                        accept_language=self.accept_language,
                        query={"filter___id": cfg_org_rls_id},
                        user=user_details,
                    )
                    if perm:
                        is_enabled = perm.get("is_enabled", False)
                        is_strict_mode = perm.get("is_strict_mode", False)

                        # Try to resolve RBAC permission label
                        rbac_perm_id = str(perm.get("rbac_permission_id", ""))
                        if rbac_perm_id:
                            rbac_perm = await self.generic_service.fetch_one_from_collection(
                                collection_key=CollectionKey.RBAC_PERMISSION,
                                output_data_type=OutputDataType.DEFAULT.value,
                                accept_language=self.accept_language,
                                query={"filter___id": rbac_perm_id},
                                user=user_details,
                            )
                            if rbac_perm:
                                permission_label = rbac_perm.get("label", rbac_perm.get("name", ""))

                                # Try to resolve RBAC title for a better display
                                rbac_title_id = str(rbac_perm.get("rbac_title_id", ""))
                                if rbac_title_id:
                                    rbac_title = await self.generic_service.fetch_one_from_collection(
                                        collection_key=CollectionKey.RBAC_TITLE,
                                        output_data_type=OutputDataType.DEFAULT.value,
                                        accept_language=self.accept_language,
                                        query={"filter___id": rbac_title_id},
                                        user=user_details,
                                    )
                                    if rbac_title:
                                        permission_label = rbac_title.get("label", permission_label)

                resolved = {
                    "id": str(entry.get("_id", entry.get("id", ""))),
                    "identifier": entry.get("identifier", ""),
                    "rls_access_type": rls_access_type,
                    "source": source,  # "direct" or "group"
                    "cfg_organization_rls_id": cfg_org_rls_id,
                    "permission_label": permission_label,
                    "is_enabled": is_enabled,
                    "is_strict_mode": is_strict_mode,
                    "collection_name": entry.get("collection_name", ""),
                    "targeted_row_id": str(entry.get("targeted_row_id", "")) if entry.get("targeted_row_id") else None,
                }

                if group:
                    resolved["group"] = group

                return resolved

            # Resolve all entries
            resolved_rules: List[Dict[str, Any]] = []

            for entry in direct_entries:
                resolved = await resolve_entry(entry, source="direct")
                resolved_rules.append(resolved)

            for entry in group_entries:
                group = entry.pop("_resolved_group", None)
                resolved = await resolve_entry(entry, source="group", group=group)
                resolved_rules.append(resolved)

            # ─── 6. Build per-type summary ────────────────────────────────
            access_type_keys = [
                ERlsAccessTypeFlag.GLOBAL_ACCESS.value,
                ERlsAccessTypeFlag.REVOKED_ACCESS.value,
                ERlsAccessTypeFlag.CUSTOM_ACCESS.value,
            ]
            type_summary: Dict[str, int] = {at: 0 for at in access_type_keys}
            for rule in resolved_rules:
                at = rule.get("rls_access_type", "")
                if at in type_summary:
                    type_summary[at] += 1

            direct_count = sum(1 for r in resolved_rules if r["source"] == "direct")
            group_count = sum(1 for r in resolved_rules if r["source"] == "group")

            # ─── 7. Permission stats from user's rules ────────────────────
            enabled_count = sum(1 for r in resolved_rules if r.get("is_enabled"))
            strict_count = sum(1 for r in resolved_rules if r.get("is_strict_mode"))
            total_rules = len(resolved_rules)
            enabled_pct = round((enabled_count / total_rules) * 100, 1) if total_rules > 0 else 0.0

            # ─── 8. Categorize rules into whitelist / blacklist / custom ──
            whitelist_rules = [r for r in resolved_rules if r.get("rls_access_type") == ERlsAccessTypeFlag.GLOBAL_ACCESS.value]
            blacklist_rules = [r for r in resolved_rules if r.get("rls_access_type") == ERlsAccessTypeFlag.REVOKED_ACCESS.value]
            custom_rules = [r for r in resolved_rules if r.get("rls_access_type") == ERlsAccessTypeFlag.CUSTOM_ACCESS.value]

            # ─── 9. Build response ────────────────────────────────────────
            user_detail = {
                "user": {
                    "user_id": str(user_info.get("_id", user_info.get("id", ""))),
                    "first_name": user_info.get("first_name", ""),
                    "last_name": user_info.get("last_name", ""),
                    "email": user_info.get("email", ""),
                    "phone": user_info.get("phone", ""),
                    "avatar": user_info.get("avatar", ""),
                },
                "summary": {
                    "total_rules": total_rules,
                    "direct_count": direct_count,
                    "group_count": group_count,
                    "access_types": type_summary,
                    "groups_count": len(user_group_ids),
                    "enabled_count": enabled_count,
                    "strict_count": strict_count,
                    "enabled_pct": enabled_pct,
                },
                "groups": list(group_info_map.values()),
                "rules": resolved_rules,
                "whitelist_rules": whitelist_rules,
                "blacklist_rules": blacklist_rules,
                "custom_rules": custom_rules,
            }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "User RLS detail fetched successfully",
                    "data": user_detail,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
