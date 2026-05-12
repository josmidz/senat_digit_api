

from typing import Any, Dict, List, Optional, Type

from bson import ObjectId
from fastapi import HTTPException, Request

from app.db.dao import DAO
from app.modules.auth.enums.common import MessageCategory
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.model.model_service import ModelService
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, EParentChildHead, OutputDataType, TranslationStrategy
from app.modules.core.utils.common.async_runner import AsyncExecutor
from app.modules.core.utils.helpers.line_helper import format_exception
from app.modules.core.services.icon.svg_icon_service import SvgIconService


class GenericService(ModelService,ConverterService,DebugService):
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        super().__init__(accept_language)

    # =========================================================================
    #                     ROW LEVEL SECURITY FILTER APPLICATION
    # =========================================================================
    # Every fetch_*/count_* method that touches tenant-scoped data MUST pass
    # the authenticated user through this helper before executing the query.
    # The helper is the single chokepoint where RLS rules turn into Mongo filters.
    #
    # Enforcement is PER-ORGANIZATION. Each org decides — via CfgRlsSetupModel
    # (is_enabled, is_strict_mode) — whether RLS applies to their data.
    # There is NO global env flag. The SaaS tenant config is the source of truth.
    # =========================================================================
    async def _apply_rls_filter(
        self,
        collection_key: "CollectionKey",
        db_filter: Dict[str, Any],
        user: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Returns a new filter dict that combines `db_filter` with the RLS
        constraints for `user` on `collection_key`.

        Skipped when:
          - collection is a global/ref/system table (is_tenant_scoped=False)
          - collection is an RLS meta-collection (would cause recursion when
            the RLS service reads its own config)
          - the user's org has RLS disabled in CfgRlsSetupModel

        deny_all → returns a filter that matches nothing ({"_id": {"$in": []}})
        bypass   → returns the caller's filter with sys_organization_id injected
        custom   → AND-s the caller's filter with {"_id": {"$in": extra_doc_ids}}
        """
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        from app.modules.security.services.security_rls_services import (
            RowLevelSecurityService,
            RLS_META_COLLECTIONS,
        )

        db_filter = db_filter or {}

        # RLS meta-collections: never filtered (prevents infinite recursion).
        if collection_key in RLS_META_COLLECTIONS:
            return db_filter

        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if metadata is None or not getattr(metadata, "is_tenant_scoped", False):
            return db_filter

        # ── No user or no org → RLS cannot be evaluated; skip it. ─────
        if not user or not user.get("sys_organization_id"):
            return db_filter

        # ── Fast path: middleware resolved RLS context ─────────────────
        rls_ctx = (user or {}).get("_rls_context")
        if rls_ctx:
            if rls_ctx.get("skip"):
                return db_filter

            access = rls_ctx.get("user_access")

            if access == "global":
                # Whitelisted → caller already handles org scoping.
                return db_filter

            if access == "revoked":
                # Blacklisted → see nothing.
                return {"_id": {"$in": []}}

            if access == "custom":
                row_ids = rls_ctx.get("custom_rows", {}).get(collection_key.value, [])
                if row_ids:
                    # Only inject org filter for active row-level enforcement.
                    return {"$and": [db_filter, {"_id": {"$in": row_ids}}]}
                # No rows granted for this specific collection.
                if rls_ctx.get("is_strict_mode"):
                    return {"_id": {"$in": []}}
                return db_filter  # Permissive: caller handles org scoping.

            # access is None — no grants at all.
            if rls_ctx.get("is_strict_mode"):
                return {"_id": {"$in": []}}
            return db_filter  # Permissive: caller handles org scoping.

        # ── Fallback: no middleware context (internal / batch calls) ───
        rls_service = RowLevelSecurityService(accept_language=self.accept_language)
        rls_result = await rls_service.get_rls_filter_for_user_and_collection(
            collection_key=collection_key,
            user=user,
        )

        if rls_result.get("deny_all"):
            return {"_id": {"$in": []}}

        if rls_result.get("bypass"):
            return db_filter  # Caller handles org scoping.

        extras: List[Dict[str, Any]] = []
        if rls_result.get("extra_filter"):
            extras.append(rls_result["extra_filter"])
        if rls_result.get("extra_doc_ids"):
            extras.append({"_id": {"$in": rls_result["extra_doc_ids"]}})

        if not extras:
            return db_filter
        return {"$and": [db_filter, *extras]}

    def _inject_org_filter(
        self,
        db_filter: Dict[str, Any],
        user: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Ensures the filter contains a sys_organization_id constraint matching
        the current user's organization. If the caller already specified one,
        it is preserved as-is (controllers sometimes legitimately query a
        different org for cross-tenant reference lookups).
        """
        if not user or not user.get("sys_organization_id"):
            # No user context: keep the filter as-is. The RLS evaluation above
            # will have returned deny_all if the path is sensitive.
            return db_filter

        try:
            org_id = user["sys_organization_id"]
            # str or ObjectId — accept both.
            # If the filter already specifies sys_organization_id anywhere, don't touch it.
            if self._filter_contains_key(db_filter, "sys_organization_id"):
                return db_filter
            new_filter = dict(db_filter) if db_filter else {}
            new_filter["sys_organization_id"] = org_id
            return new_filter
        except Exception as e:
            self.app_debug_print(f"[RLS] _inject_org_filter error: {e}", False)
            return db_filter

    @staticmethod
    def _filter_contains_key(db_filter: Any, key: str) -> bool:
        """Recursively check whether a Mongo filter dict references the given field name."""
        if not isinstance(db_filter, dict):
            return False
        if key in db_filter:
            return True
        for value in db_filter.values():
            if isinstance(value, dict) and GenericService._filter_contains_key(value, key):
                return True
            if isinstance(value, list):
                for item in value:
                    if GenericService._filter_contains_key(item, key):
                        return True
        return False

    async def is_system_organization(self,sys_organization_id:ObjectId) -> bool :
        try:
            
            is_system_organization = False
            system_org = await self.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SYSTEM_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sys_organization_id": str(sys_organization_id)
                }
            )
            if system_org:
                is_system_organization = True
            return is_system_organization
        
        except ValueError as e:
            return False
        
    async def create_default_application(self,app1:list[dict]) -> bool:
        try:
            for index, app in enumerate(app1):
                print(
                    f"\n\n\n STARTING APP1 : {app['name']}  INDEX : {index} \n\n\n")
                app_saved = await self.on_single_application_save(app,)
                print(
                    f"\n\n\nADDING APP1 COMPLETED : {app_saved}  INDEX : {index} \n\n\n")
                
            return True
        except ValueError as e:
            print(f"\n ERROR CALLING DEFAULT APP FX : {e} \n")
            print(f"Error: {e}")
            return False

    async def on_single_application_save(self,app) -> bool:
        try:
            from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
            rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)
            sub_menu_list = app.get('sub_menus', [])
            svg_icon = app.get('svg_icon', "")
            app_path = app.copy()
            app = {
                field_name: field_value
                for field_name, field_value in app.items()
                if field_name not in ('path', 'path_guard', 'sub_menus', 'svg_icon')
            }
            app_exist = await self.fetch_native_query_one_from_collection(
                collection_key=CollectionKey.SYS_APPLICATION,
                output_data_type=OutputDataType.DEFAULT,
                accept_language='fr',
                native_query={'flag': app['flag']}
            )
            print(f"----- APP EXIST : {app_exist}")
            
            if app.get('is_link_deleted', False):
                if app_exist:
                    await rbac_role_service.cascade_delete_app_references(self, app_exist['id'])
                    print(f"🗑️ Cascade deleted all references and the app itself: {app.get('name', 'N/A')}")
                return True

            result_app = await self.upsert_data_to_collection(collection_key=CollectionKey.SYS_APPLICATION, filter_data={'flag': app['flag']}, update_data=app)
            print("upserted result application NOT EXIST 1.", result_app)
            processed_app_id = result_app if isinstance(
                result_app, str) else str(result_app['id'])

            app_restricted_platform = app.get('restricted_api_consumer_list', [])
            app_restricted_profil = app.get('restricted_profil_list', [])
            for profil_item in app_restricted_profil:
                profil_flag = profil_item.get('flag') if isinstance(
                    profil_item, dict) else profil_item
                profil_info = await self.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_PROFILE,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=DEFAULT_LANGUAGE,
                    query={
                        "filter__flag": profil_flag
                    }
                )
                if profil_info:
                    await rbac_role_service.create_restricted_profil(targeted_id=processed_app_id, rbac_profile_id=profil_info['id'])

            for api_consumer_item in app_restricted_platform:
                api_consumer_flag = api_consumer_item.get('flag') if isinstance(
                    api_consumer_item, dict) else api_consumer_item
                api_consumer_info = await self.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_API_CONSUMER,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=DEFAULT_LANGUAGE,
                    query={
                        "filter__flag": api_consumer_flag
                    }
                )
                if api_consumer_info:
                    await rbac_role_service.create_restricted_api_consumer(targeted_id=processed_app_id, ref_api_consumer_id=api_consumer_info['id'])

            # ADD RBAC_PATH_GUARD
            rbac_path_guard = {
                "path": app_path['path'],
                "path_guard": app_path['path_guard'],
                "targeted_id": processed_app_id,
                "sys_application_id": processed_app_id,
                "label": f"Le chemin d'accès pour l'application {app_path['name']}",
                "is_standalone": False,
            }

            saved_path_guard = await self.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_PATH_GUARD,
                filter_data={
                    "targeted_id": rbac_path_guard['targeted_id'],
                    "path": rbac_path_guard['path'],
                },
                update_data=rbac_path_guard
            )
            processed_path_id = saved_path_guard if isinstance(
                saved_path_guard, str) else str(saved_path_guard['id'])
            path_restricted_platform = app_path.get(
                'restricted_api_consumer_list', [])
            path_restricted_profil = app_path.get('restricted_profil_list', [])
            for profil_item in path_restricted_profil:
                profil_flag = profil_item.get('flag') if isinstance(
                    profil_item, dict) else profil_item
                profil_info = await self.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_PROFILE,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=DEFAULT_LANGUAGE,
                    query={
                        "filter__flag": profil_flag
                    }
                )
                if profil_info:
                    await rbac_role_service.create_restricted_profil(targeted_id=processed_path_id, rbac_profile_id=profil_info['id'])

            for api_consumer_item in path_restricted_platform:
                api_consumer_flag = api_consumer_item.get('flag') if isinstance(
                    api_consumer_item, dict) else api_consumer_item
                api_consumer_info = await self.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_API_CONSUMER,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=DEFAULT_LANGUAGE,
                    query={
                        "filter__flag": api_consumer_flag
                    }
                )
                if api_consumer_info:
                    await rbac_role_service.create_restricted_api_consumer(targeted_id=processed_path_id, ref_api_consumer_id=api_consumer_info['id'])

            # APP ICON
            api_consumer_flag_to_svg = list(app['restricted_api_consumer_list'])
            if len(api_consumer_flag_to_svg) > 0:
                await SvgIconService.upload_svg_icon(
                    svg_icon=svg_icon,
                    path_value=app_path.get("path", ""),
                    icon_flag=app.get("flag", ""),
                    api_consumer_flag=api_consumer_flag_to_svg[0].get('flag'),
                ) 
                # RUN RECURSIVE ON SUB MENU
                if len(sub_menu_list) > 0:
                    print(f"\n\n\n START APP SUB MENU : {len(sub_menu_list)} \n\n\n")
                    await self.on_sub_menu_save(sub_menu_list, processed_app_id, None)
                    print(f"\n\n\n ENDED APP SUB MENU : {len(sub_menu_list)} \n\n\n")
            return True
        except ValueError as e:
            print(f"\n ERROR CALLING SINGLE APP SAVING FX : {e} \n")
            print(f"Error: {e}")
            return False
        
    async def on_sub_menu_save(self,standalone_menus, app_id: Optional[str] = None, menu_id: Optional[str] = None) -> bool:
        try:
            from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
            rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)

            for index, menu in enumerate(standalone_menus):
                menu_path = menu.copy()
                sub_menu_list = menu.get('sub_menus', [])
                print(f"\n\n\n SINGLE SUB MENU : {len(sub_menu_list)} \n\n\n")
                menu_svg_icon = menu.get('svg_icon', "")
                menu = {
                    field_name: field_value
                    for field_name, field_value in menu.items()
                    if field_name not in ('path', 'path_guard', 'sub_menus', 'svg_icon')
                }

                menu_query = {"flag": menu['flag']}
                if app_id:
                    menu_query = {
                        **menu_query,
                        "sys_application_id": app_id
                    }
                if menu_id:
                    menu_query = {
                        **menu_query,
                        "sys_menu_id": menu_id
                    }
                sub_menu_exist = await self.fetch_native_query_one_from_collection(
                    collection_key=CollectionKey.SYS_MENU,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language='fr',
                    native_query=menu_query,
                )
                
                if menu.get('is_link_deleted', False):
                    if sub_menu_exist:
                        await rbac_role_service.cascade_delete_menu_references(self, sub_menu_exist['id'])
                        print(f"🗑️ Cascade deleted all references and the menu itself: {menu.get('name', 'N/A')}")
                    continue

                menu['sys_application_id'] = app_id
                menu['sys_menu_id'] = menu_id

                processed_menu = await self.upsert_data_to_collection(
                    collection_key=CollectionKey.SYS_MENU,
                    filter_data=menu_query,
                    update_data=menu
                )
                # print("upserted MENU result.",processed_data)
                processed_menu_id = processed_menu if isinstance(
                    processed_menu, str) else str(processed_menu['id'])
                menu_restricted_platform = menu.get(
                    'restricted_api_consumer_list', [])
                menu_restricted_profil = menu.get('restricted_profil_list', [])

                for profil_item in menu_restricted_profil:
                    profil_flag = profil_item.get('flag') if isinstance(
                        profil_item, dict) else profil_item
                    profil_info = await self.fetch_one_from_collection(
                        collection_key=CollectionKey.RBAC_PROFILE,
                        output_data_type=OutputDataType.DEFAULT,
                        accept_language=DEFAULT_LANGUAGE,
                        query={
                            "filter__flag": profil_flag
                        }
                    )
                    if profil_info:
                        await rbac_role_service.create_restricted_profil(targeted_id=processed_menu_id, rbac_profile_id=profil_info['id'])

                for api_consumer_item in menu_restricted_platform:
                    api_consumer_flag = api_consumer_item.get('flag') if isinstance(
                        api_consumer_item, dict) else api_consumer_item
                    api_consumer_info = await self.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_API_CONSUMER,
                        output_data_type=OutputDataType.DEFAULT,
                        accept_language=DEFAULT_LANGUAGE,
                        query={
                            "filter__flag": api_consumer_flag
                        }
                    )
                    if api_consumer_info:
                        await rbac_role_service.create_restricted_api_consumer(targeted_id=processed_menu_id, ref_api_consumer_id=api_consumer_info['id'])

                # ADD RBAC_PATH_GUARD
                rbac_path_guard = {
                    "path": menu_path['path'],
                    "path_guard": menu_path['path_guard'],
                    "targeted_id": processed_menu_id,
                    "sys_application_id": app_id,
                    "sys_menu_id": menu_id,
                    "label": f"Le chemin d'accès pour le sous menu {menu_path['name']}",
                    "is_standalone": False,
                }

                menu_rbac_path_guard = await self.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_PATH_GUARD,
                    filter_data={
                        "targeted_id": rbac_path_guard['targeted_id'],
                        "path": rbac_path_guard['path'],
                    },
                    update_data=rbac_path_guard
                )

                processed_path_id = menu_rbac_path_guard if isinstance(
                    menu_rbac_path_guard, str) else str(menu_rbac_path_guard['id'])
                path_restricted_platform = menu_path.get(
                    'restricted_api_consumer_list', [])
                path_restricted_profil = menu_path.get(
                    'restricted_profil_list', [])
                for profil_item in path_restricted_profil:
                    profil_flag = profil_item.get('flag') if isinstance(
                        profil_item, dict) else profil_item
                    profil_info = await self.fetch_one_from_collection(
                        collection_key=CollectionKey.RBAC_PROFILE,
                        output_data_type=OutputDataType.DEFAULT,
                        accept_language=DEFAULT_LANGUAGE,
                        query={
                            "filter__flag": profil_flag
                        }
                    )
                    if profil_info:
                        await rbac_role_service.create_restricted_profil(targeted_id=processed_path_id, rbac_profile_id=profil_info['id'])

                for api_consumer_item in path_restricted_platform:
                    api_consumer_flag = api_consumer_item.get('flag') if isinstance(
                        api_consumer_item, dict) else api_consumer_item
                    api_consumer_info = await self.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_API_CONSUMER,
                        output_data_type=OutputDataType.DEFAULT,
                        accept_language=DEFAULT_LANGUAGE,
                        query={
                            "filter__flag": api_consumer_flag
                        }
                    )
                    if api_consumer_info:
                        await rbac_role_service.create_restricted_api_consumer(targeted_id=processed_path_id, ref_api_consumer_id=api_consumer_info['id'])

                # MENU ICON
                # api_consumer_flag_svg = EApiConsumerFlag.ANGULAR_SENAT_DIGIT_ADMIN_WEB_APP.value
                api_consumer_flag_svg = list(menu['restricted_api_consumer_list'])
                if len(api_consumer_flag_svg) > 0:
                    await SvgIconService.upload_svg_icon(
                        svg_icon=menu_svg_icon,
                        path_value=menu_path.get("path", ""),
                        icon_flag=menu.get("flag", ""),
                        api_consumer_flag=api_consumer_flag_svg[0].get('flag'),
                    ) 
                    print(f"\n\n\n MENUS COMPLETED {len(standalone_menus)} \n\n\n")
                    # RUN RECURSIVE ON SUB MENU
                    if len(sub_menu_list) > 0:
                        print(
                            f"\n\n\n START SUB MENU: {menu['name']} with {len(sub_menu_list)} children \n\n\n")
                        # Pass None for app_id to ensure it's not overridden
                        result = await self.on_sub_menu_save(sub_menu_list, None, processed_menu_id)
                        if not result:
                            print(
                                f"\n\n\n ERROR PROCESSING SUB MENU: {menu['name']} \n\n\n")
                        print(f"\n\n\n SUB MENU COMPLETED: {menu['name']} \n\n\n")
            return True
        except ValueError as e:
            print(f"\n ERROR CALLING MENU FX : {e} \n")
            print(f"Error: {e}")
            return False


    @staticmethod
    def convert_id_fields_to_str(data):
        """
        Recursively convert all fields ending with '_id' to strings.

        This ensures that ObjectId fields are properly serialized to strings
        when returning data from fetch methods.

        Only converts simple values (ObjectId, int, etc.) to strings, not dicts or lists
        which may be formatted output structures.

        Args:
            data: The data to convert (dict, list, or other)

        Returns:
            The data with all _id fields converted to strings
        """
        if isinstance(data, dict):
            result = {}
            for k, v in data.items():
                if k.endswith('_id') and v is not None and not isinstance(v, (str, dict, list)):
                    # Only convert simple values (ObjectId, int, etc.) to strings
                    result[k] = str(v)
                elif isinstance(v, (dict, list)):
                    # Recursively process nested structures
                    result[k] = GenericService.convert_id_fields_to_str(v)
                else:
                    result[k] = v
            return result
        elif isinstance(data, list):
            return [GenericService.convert_id_fields_to_str(item) for item in data]
        return data

    async def _format_documents_for_collection(
        self,
        documents: List[Dict[str, Any]],
        model_class: Type,
        collection_key: CollectionKey,
        output_data_type: OutputDataType,
        accept_language: str = DEFAULT_LANGUAGE,
        hidde_on_view_values: Optional[Dict[str, Any]] = None,
        force_include_fields: Optional[list] = None,
        force_exclude_fields: Optional[list] = None,
    ) -> List[Any]:
        """Shared formatting logic used by dynamic fetch helpers.

        It normalizes the output type, builds model instances from raw MongoDB
        documents (with a fallback when parsing fails), and delegates the final
        shape to each model instance's unified ``format()`` method.

        This keeps the post-retrieval behaviour identical between:
        - fetch_data_from_collection
        - fetch_native_query_data_from_collection
        - fetch_native_aggregate_data_from_collection
        """
        import asyncio
        
        if not documents:
            return []

        # Normalize output_data_type to an enum instance (supports both enum values and raw values)
        if isinstance(output_data_type, OutputDataType):
            output_enum = output_data_type
        else:
            output_enum = OutputDataType(output_data_type)

        # Prepare model instances and docs for parallel processing
        format_tasks = []
        
        for doc in documents:
            # Hide sensitive fields and normalise identifiers
            if "password" in doc:
                del doc["password"]
            if "_id" in doc and not isinstance(doc["_id"], str):
                doc["_id"] = str(doc["_id"])

            # Ensure translations exist
            if "translations" not in doc:
                doc["translations"] = {}

            # Try to build a full model instance; on failure, fall back to required fields only
            try:
                model_instance = model_class.parse_obj(doc)
            except Exception as e:
                self.app_debug_print(f"Error parsing document: {e}", True)
                required_fields: Dict[str, Any] = {}
                for field_name, field in model_class.model_fields.items():
                    if field.is_required():
                        if field_name in doc:
                            required_fields[field_name] = doc.get(field_name)
                        else:
                            if field.annotation == str:
                                required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                # Always include ID field if available
                if "_id" in doc:
                    required_fields["id"] = str(doc["_id"])
                elif "id" in doc:
                    required_fields["id"] = doc["id"]
                else:
                    required_fields["id"] = str(ObjectId())
                
                model_instance = model_class(**required_fields)

            # Use unified format() API on the model instance
            if not hasattr(model_instance, "format") or not callable(getattr(model_instance, "format")):
                raise AttributeError(f"Model {model_class} must implement a 'format' method for dynamic fetch")

            # Create format task for parallel execution
            format_tasks.append(
                model_instance.format(
                    output_data_type=output_enum,
                    accept_language=accept_language,
                    collection_key=collection_key,
                    doc=doc,
                    hidde_on_view_values=hidde_on_view_values,
                    force_include_fields=force_include_fields,
                    force_exclude_fields=force_exclude_fields,
                )
            )

        # Execute all format tasks in parallel - NO semaphore here to avoid deadlock
        formatted_data = await AsyncExecutor.gather(format_tasks)

        # Convert all _id fields to strings before returning
        return [self.convert_id_fields_to_str(doc) for doc in formatted_data]

    @staticmethod
    def _normalize_identifier(value: Any) -> str:
        if isinstance(value, dict):
            value = value.get("id", None) or value.get("_id", None)
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _as_collection_key(value: Any) -> CollectionKey:
        if isinstance(value, CollectionKey):
            return value
        return CollectionKey(value)

    @classmethod
    def _extract_user_organization_id(cls, user: Optional[Dict[str, Any]]) -> str:
        if not user:
            return ""
        return cls._normalize_identifier(user.get("sys_organization_id", None))

    @staticmethod
    def _normalize_enum_storage_value(value: Any) -> str:
        """
        Normalize enum-like values possibly persisted as enum, tuple, or plain string.
        """
        if hasattr(value, "value"):
            value = getattr(value, "value")
        if isinstance(value, (list, tuple)) and len(value) == 1:
            value = value[0]
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _build_validation_context(
        *,
        current_validation_request_id: Optional[str] = None,
        parent_validation_request_id: Optional[str] = None,
        root_validation_request_id: Optional[str] = None,
        resolved_sudo_action_type: str = "",
        is_sudo_group_action: bool = False,
        validation_process_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        def normalize(value: Optional[str]) -> Optional[str]:
            if value is None:
                return None
            normalized = str(value).strip()
            return normalized or None

        current_id = normalize(current_validation_request_id)
        parent_id = normalize(parent_validation_request_id)
        root_id = normalize(root_validation_request_id)
        process_id = normalize(validation_process_id)
        if root_id is None and current_id is not None:
            root_id = current_id

        return {
            "current_validation_request_id": current_id,
            "parent_validation_request_id": parent_id,
            "root_validation_request_id": root_id,
            "resolved_sudo_action_type": str(resolved_sudo_action_type or "").strip(),
            "is_sudo_group_action": bool(is_sudo_group_action),
            # Forwarded to the frontend so the interceptor can inject
            # X-Validation-Process-Id on subsequent sub-process calls.
            "validation_process_id": process_id,
        }

    @staticmethod
    def _grouped_like_sudo_types() -> set[str]:
        from app.modules.security.enums.security_enum import EConfigSudoActionTypeFlag

        return {
            EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value,
            EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION.value,
            EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION.value,
        }

    def _extract_group_validation_context(
        self,
        request: Optional[Request],
        user: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve grouped/cross sudo context propagated by SudoActionCheckMiddleware.

        Returns None when current request is not under grouped-style sudo flow.
        """
        if request is None:
            return None

        request_state = getattr(request, "state", None)
        sudo_resolution = getattr(request_state, "sudo_resolution", None)
        if not isinstance(sudo_resolution, dict):
            return None

        resolved_sudo_action_type = str(
            sudo_resolution.get("resolved_sudo_action_type", "")
        ).strip()
        grouped_like_types = self._grouped_like_sudo_types()
        if resolved_sudo_action_type not in grouped_like_types:
            return None

        cfg_organization_sudo_action_id = str(
            sudo_resolution.get("cfg_organization_sudo_action_id", "")
        ).strip()
        if not cfg_organization_sudo_action_id:
            return {
                "is_misconfigured": True,
                "resolved_sudo_action_type": resolved_sudo_action_type,
                "cfg_organization_sudo_action_id": "",
                "organization_id": self._extract_user_organization_id(user)
                or str(sudo_resolution.get("sys_organization_id", "")).strip(),
            }

        organization_id = self._extract_user_organization_id(user) or str(
            sudo_resolution.get("sys_organization_id", "")
        ).strip()
        return {
            "is_misconfigured": False,
            "resolved_sudo_action_type": resolved_sudo_action_type,
            "cfg_organization_sudo_action_id": cfg_organization_sudo_action_id,
            "organization_id": organization_id,
            "rbac_endpoint_id": str(sudo_resolution.get("rbac_endpoint_id", "")).strip(),
        }

    @staticmethod
    def _extract_parent_validation_request_id(request: Optional[Request]) -> str:
        """
        Resolve parent validation request id from request transport.

        Priority:
        1) Header: X-Validation-Parent-Id (canonical)
        2) Query: parent_validation_request_id
        3) Query: validation_request_parent_id (legacy alias)
        """
        if request is None:
            return ""
        from_header = str(request.headers.get("X-Validation-Parent-Id", "")).strip()
        if from_header:
            return from_header
        from_query = str(
            request.query_params.get("parent_validation_request_id", "")
        ).strip()
        if from_query:
            return from_query
        return str(
            request.query_params.get("validation_request_parent_id", "")
        ).strip()

    async def _fetch_raw_validation_request(
        self,
        validation_request_id: str,
    ) -> Optional[Dict[str, Any]]:
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING

        if not validation_request_id:
            return None
        if not ObjectId.is_valid(validation_request_id):
            return None

        metadata = COLLECTION_MODEL_MAPPING.get(CollectionKey.OPS_VALIDATION_REQUEST)
        if not metadata:
            return None

        dao = DAO(metadata.collection_name, metadata.model_class, is_read_only=True)
        assert dao.collection is not None, (
            f"Error: Collection {metadata.collection_name} is None!"
        )
        return await dao.find_one({"_id": ObjectId(validation_request_id)})

    # ------------------------------------------------------------------
    # VALIDATION PROCESS REDIS KEY HELPERS
    # ------------------------------------------------------------------

    _VALIDATION_PROCESS_TTL = 60 * 60 * 6  # 6 hours

    async def _create_or_update_validation_process_key(
        self,
        *,
        request: Optional[Request],
        validation_request_id: str,
        root_validation_request_id: str,
        parent_validation_request_id: str,
        organization_id: str,
        resolved_sudo_action_type: str,
    ) -> str:
        """
        Manage the server-side VALIDATION_PROCESS Redis key.

        Root operation (no parent):
            - Generate a new process_id (UUID4).
            - Store a fresh key and return the process_id.

        Sub-operation (has parent, X-Validation-Process-Id header present):
            - Look up the existing key and update current_validation_request_id.
            - Refresh TTL.
            - Return the existing process_id.

        Fallback (header absent / key expired): generate a new key.
        """
        import json
        from datetime import datetime, timezone
        from uuid import uuid4

        from app.modules.core.constants.keys import RedisKeys
        from app.modules.core.services.redis.redis_service import AppRedisService

        is_root = not parent_validation_request_id

        # --- Try to reuse existing process key from header ---
        existing_process_id = ""
        if not is_root and request is not None:
            existing_process_id = str(
                request.headers.get("X-Validation-Process-Id", "")
            ).strip()

        if existing_process_id:
            redis_key = RedisKeys.format_key(
                RedisKeys.VALIDATION_PROCESS, process_id=existing_process_id
            )
            try:
                raw = await AppRedisService.get_str_redis_value(redis_key)
                if raw:
                    process_data: Dict[str, Any] = json.loads(raw)
                    process_data["current_validation_request_id"] = validation_request_id
                    await AppRedisService.set_redis_value(
                        redis_key,
                        json.dumps(process_data),
                        expiry=self._VALIDATION_PROCESS_TTL,
                    )
                    return existing_process_id
            except Exception as err:
                self.app_debug_print(
                    f"_create_or_update_validation_process_key update failed: {err}", True
                )

        # --- Create a new key (root op or fallback) ---
        new_process_id = str(uuid4())
        redis_key = RedisKeys.format_key(
            RedisKeys.VALIDATION_PROCESS, process_id=new_process_id
        )
        payload: Dict[str, Any] = {
            "process_id": new_process_id,
            "root_validation_request_id": root_validation_request_id or validation_request_id,
            "current_validation_request_id": validation_request_id,
            "organization_id": str(organization_id),
            "sudo_action_type": str(resolved_sudo_action_type),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await AppRedisService.set_redis_value(
                redis_key,
                json.dumps(payload),
                expiry=self._VALIDATION_PROCESS_TTL,
            )
        except Exception as err:
            self.app_debug_print(
                f"_create_or_update_validation_process_key create failed: {err}", True
            )
        return new_process_id

    # ------------------------------------------------------------------

    async def _resolve_parent_validation_linkage(
        self,
        *,
        request: Optional[Request],
        organization_id: str,
        resolved_sudo_action_type: str,
    ) -> Dict[str, Any]:
        """
        Validate and resolve parent/root linkage for grouped recursive flows.

        Adds a Redis-backed process-key guard when the client supplies
        X-Validation-Process-Id.  If the stored current_validation_request_id
        does not match the supplied X-Validation-Parent-Id the request is
        blocked immediately (no DB chain-walk needed).  Falls back gracefully
        when the Redis key has expired or is absent.
        """
        import json

        from app.modules.core.constants.keys import RedisKeys
        from app.modules.core.services.redis.redis_service import AppRedisService

        parent_validation_request_id = self._extract_parent_validation_request_id(request)
        if not parent_validation_request_id:
            return {
                "parent_validation_request_id": "",
                "root_validation_request_id": "",
                "blocked_result": None,
            }

        # --- Redis process-key guard (non-blocking on Redis failure) ---
        process_id = ""
        if request is not None:
            process_id = str(
                request.headers.get("X-Validation-Process-Id", "")
            ).strip()

        if process_id:
            try:
                redis_key = RedisKeys.format_key(
                    RedisKeys.VALIDATION_PROCESS, process_id=process_id
                )
                raw = await AppRedisService.get_str_redis_value(redis_key)
                if raw:
                    process_data: Dict[str, Any] = json.loads(raw)
                    stored_org = str(process_data.get("organization_id", "")).strip()
                    stored_current = str(
                        process_data.get("current_validation_request_id", "")
                    ).strip()

                    if stored_org and stored_org != str(organization_id).strip():
                        return {
                            "parent_validation_request_id": "",
                            "root_validation_request_id": "",
                            "blocked_result": self._build_group_validation_blocked_result(
                                error_code="PARENT_VALIDATION_PROCESS_MISMATCH",
                                message="Validation process belongs to a different organization.",
                                resolved_sudo_action_type=resolved_sudo_action_type,
                                status_code=403,
                            ),
                        }

                    if stored_current and stored_current != parent_validation_request_id:
                        return {
                            "parent_validation_request_id": "",
                            "root_validation_request_id": "",
                            "blocked_result": self._build_group_validation_blocked_result(
                                error_code="PARENT_VALIDATION_PROCESS_MISMATCH",
                                message=(
                                    "The supplied parent validation request ID does not match "
                                    "the current step recorded for this validation process. "
                                    "Possible replay or out-of-order sub-request."
                                ),
                                resolved_sudo_action_type=resolved_sudo_action_type,
                                status_code=403,
                            ),
                        }
                # Key absent / expired → fall through to DB chain-walk.
            except Exception as redis_guard_err:
                self.app_debug_print(
                    f"Redis process-key guard non-blocking error: {redis_guard_err}", True
                )
        # --- end Redis guard ---

        base_context = self._build_validation_context(
            current_validation_request_id=None,
            parent_validation_request_id=parent_validation_request_id,
            root_validation_request_id=None,
            resolved_sudo_action_type=resolved_sudo_action_type,
            is_sudo_group_action=True,
        )
        if not ObjectId.is_valid(parent_validation_request_id):
            return {
                "parent_validation_request_id": "",
                "root_validation_request_id": "",
                "blocked_result": self._build_group_validation_blocked_result(
                    error_code="PARENT_VALIDATION_REQUEST_INVALID",
                    message="Invalid parent validation request id.",
                    resolved_sudo_action_type=resolved_sudo_action_type,
                    status_code=400,
                    validation_context=base_context,
                ),
            }

        parent_doc = await self._fetch_raw_validation_request(parent_validation_request_id)
        if not parent_doc:
            return {
                "parent_validation_request_id": "",
                "root_validation_request_id": "",
                "blocked_result": self._build_group_validation_blocked_result(
                    error_code="PARENT_VALIDATION_REQUEST_NOT_FOUND",
                    message="Parent validation request was not found.",
                    resolved_sudo_action_type=resolved_sudo_action_type,
                    status_code=404,
                    validation_context=base_context,
                ),
            }

        grouped_like_types = self._grouped_like_sudo_types()

        parent_org_id = self._normalize_identifier(parent_doc.get("sys_organization_id"))
        if not parent_org_id or parent_org_id != str(organization_id).strip():
            return {
                "parent_validation_request_id": "",
                "root_validation_request_id": "",
                "blocked_result": self._build_group_validation_blocked_result(
                    error_code="PARENT_VALIDATION_REQUEST_FORBIDDEN",
                    message="Parent validation request is not accessible for this organization.",
                    resolved_sudo_action_type=resolved_sudo_action_type,
                    status_code=403,
                    validation_context=base_context,
                ),
            }

        parent_status = self._normalize_enum_storage_value(parent_doc.get("status")).upper()
        is_parent_completed = bool(parent_doc.get("validation_is_completed", False))
        if parent_status != "PENDING" or is_parent_completed:
            return {
                "parent_validation_request_id": "",
                "root_validation_request_id": "",
                "blocked_result": self._build_group_validation_blocked_result(
                    error_code="PARENT_VALIDATION_REQUEST_NOT_PENDING",
                    message="Parent validation request is not pending.",
                    resolved_sudo_action_type=resolved_sudo_action_type,
                    status_code=403,
                    validation_context=base_context,
                ),
            }

        parent_type = self._normalize_enum_storage_value(
            parent_doc.get("validation_request_type")
        )
        if parent_type not in grouped_like_types:
            return {
                "parent_validation_request_id": "",
                "root_validation_request_id": "",
                "blocked_result": self._build_group_validation_blocked_result(
                    error_code="PARENT_VALIDATION_REQUEST_TYPE_INVALID",
                    message="Parent validation request is not a grouped validation flow.",
                    resolved_sudo_action_type=resolved_sudo_action_type,
                    status_code=403,
                    validation_context=base_context,
                ),
            }

        visited_ids = {parent_validation_request_id}
        root_validation_request_id = parent_validation_request_id
        max_depth = 20
        depth = 0
        cursor_doc = parent_doc

        while True:
            ancestor_parent_id = self._normalize_identifier(
                cursor_doc.get("ops_validation_request_id")
            )
            if not ancestor_parent_id:
                break

            depth += 1
            if depth > max_depth:
                return {
                    "parent_validation_request_id": "",
                    "root_validation_request_id": "",
                    "blocked_result": self._build_group_validation_blocked_result(
                        error_code="PARENT_VALIDATION_CHAIN_DEPTH_EXCEEDED",
                        message="Parent validation chain exceeds allowed depth.",
                        resolved_sudo_action_type=resolved_sudo_action_type,
                        status_code=400,
                        validation_context=base_context,
                    ),
                }
            if ancestor_parent_id in visited_ids:
                return {
                    "parent_validation_request_id": "",
                    "root_validation_request_id": "",
                    "blocked_result": self._build_group_validation_blocked_result(
                        error_code="PARENT_VALIDATION_CHAIN_CYCLE",
                        message="Cycle detected in parent validation chain.",
                        resolved_sudo_action_type=resolved_sudo_action_type,
                        status_code=400,
                        validation_context=base_context,
                    ),
                }

            visited_ids.add(ancestor_parent_id)
            ancestor_doc = await self._fetch_raw_validation_request(ancestor_parent_id)
            if not ancestor_doc:
                return {
                    "parent_validation_request_id": "",
                    "root_validation_request_id": "",
                    "blocked_result": self._build_group_validation_blocked_result(
                        error_code="PARENT_VALIDATION_CHAIN_BROKEN",
                        message="Parent validation chain contains a missing request.",
                        resolved_sudo_action_type=resolved_sudo_action_type,
                        status_code=400,
                        validation_context=base_context,
                    ),
                }

            ancestor_org_id = self._normalize_identifier(
                ancestor_doc.get("sys_organization_id")
            )
            if ancestor_org_id != str(organization_id).strip():
                return {
                    "parent_validation_request_id": "",
                    "root_validation_request_id": "",
                    "blocked_result": self._build_group_validation_blocked_result(
                        error_code="PARENT_VALIDATION_CHAIN_FORBIDDEN",
                        message="Parent validation chain belongs to another organization.",
                        resolved_sudo_action_type=resolved_sudo_action_type,
                        status_code=403,
                        validation_context=base_context,
                    ),
                }

            ancestor_type = self._normalize_enum_storage_value(
                ancestor_doc.get("validation_request_type")
            )
            if ancestor_type not in grouped_like_types:
                return {
                    "parent_validation_request_id": "",
                    "root_validation_request_id": "",
                    "blocked_result": self._build_group_validation_blocked_result(
                        error_code="PARENT_VALIDATION_CHAIN_TYPE_INVALID",
                        message="Parent validation chain must contain grouped validation requests only.",
                        resolved_sudo_action_type=resolved_sudo_action_type,
                        status_code=403,
                        validation_context=base_context,
                    ),
                }

            root_validation_request_id = ancestor_parent_id
            cursor_doc = ancestor_doc

        return {
            "parent_validation_request_id": parent_validation_request_id,
            "root_validation_request_id": root_validation_request_id,
            "blocked_result": None,
        }

    async def _fetch_sudo_action_access_records(
        self,
        *,
        organization_id: str,
        sudo_action_access_type: str,
        cfg_organization_sudo_action_id: Optional[str] = None,
        targeted_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {
            "filter__sys_organization_id": str(organization_id),
            "filter__sudo_action_access_type": sudo_action_access_type,
            "filter__is_activated": True,
        }
        if cfg_organization_sudo_action_id is not None:
            query["filter__cfg_organization_sudo_action_id"] = str(
                cfg_organization_sudo_action_id
            )
        if targeted_type is not None:
            query["filter__targeted_type"] = str(targeted_type)

        data = await self.fetch_data_from_collection(
            collection_key=CollectionKey.CFG_SUDO_ACTION_ACCESS,
            all_data=True,
            page=0,
            limit=100000,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=self.accept_language,
            query=query,
        )
        return data or []

    async def _resolve_validator_users_from_access_records(
        self,
        *,
        organization_id: str,
        access_records: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Expand CFG_SUDO_ACTION_ACCESS entries (users/groups) into ordered validator users.
        """
        from app.modules.security.enums.security_enum import (
            ESudoActionAccessTargetedTypeFlag,
        )

        if not access_records:
            return []

        def resolve_order(record: Dict[str, Any], fallback: int) -> int:
            value = record.get("order_by", None)
            if value is None:
                return fallback
            try:
                return int(value)
            except Exception:
                return fallback

        sorted_access_records = sorted(
            access_records,
            key=lambda item: (
                resolve_order(item, 999999),
                str(item.get("created_at", "")),
                str(item.get("id", "")),
            ),
        )

        validators_map: Dict[str, Dict[str, Any]] = {}
        synthetic_order = 0

        def register_validator(
            *,
            user_id: str,
            order_by: int,
            access_type: str,
        ) -> None:
            nonlocal validators_map
            if not user_id:
                return
            entry = validators_map.get(user_id)
            if not entry:
                validators_map[user_id] = {
                    "sys_user_id": user_id,
                    "order_by": int(order_by),
                    "has_validation_access": True,
                    "access_sources": {access_type} if access_type else set(),
                }
                return

            entry["order_by"] = min(int(entry.get("order_by", order_by)), int(order_by))
            if access_type:
                entry["access_sources"].add(access_type)

        for access_record in sorted_access_records:
            targeted_type = str(access_record.get("targeted_type", "")).strip()
            targeted_id = str(access_record.get("targeted_id", "")).strip()
            access_type = str(access_record.get("sudo_action_access_type", "")).strip()
            record_organization_id = self._normalize_identifier(
                access_record.get("sys_organization_id", None)
            ) or str(organization_id)
            base_order = resolve_order(access_record, synthetic_order)
            synthetic_order += 1

            if (
                targeted_type
                == ESudoActionAccessTargetedTypeFlag.USER.value
                and targeted_id
            ):
                register_validator(
                    user_id=targeted_id,
                    order_by=base_order,
                    access_type=access_type,
                )
                continue

            if (
                targeted_type
                == ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value
                and targeted_id
            ):
                group_members = await self.fetch_data_from_collection(
                    collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
                    all_data=True,
                    page=0,
                    limit=100000,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=self.accept_language,
                    query={
                        "filter__sys_organization_id": str(record_organization_id),
                        "filter__ref_sudo_rls_security_group_id": str(targeted_id),
                        "filter__is_activated": True,
                    },
                )
                member_ids = sorted(
                    str(member.get("sys_user_id", "")).strip()
                    for member in (group_members or [])
                    if str(member.get("sys_user_id", "")).strip()
                )
                for member_offset, member_user_id in enumerate(member_ids):
                    register_validator(
                        user_id=member_user_id,
                        order_by=(base_order + member_offset),
                        access_type=access_type,
                    )

        if not validators_map:
            return []

        validators = list(validators_map.values())
        validators.sort(
            key=lambda item: (
                int(item.get("order_by", 0)),
                str(item.get("sys_user_id", "")).lower(),
            )
        )

        # Re-index order to keep a strict deterministic sequence.
        formatted_validators: List[Dict[str, Any]] = []
        for index, validator in enumerate(validators):
            formatted_validators.append(
                {
                    "sys_user_id": str(validator.get("sys_user_id", "")).strip(),
                    "has_validation_access": bool(
                        validator.get("has_validation_access", True)
                    ),
                    "order_by": index,
                    "access_sources": sorted(
                        source
                        for source in list(validator.get("access_sources", set()) or set())
                        if source
                    ),
                }
            )

        return formatted_validators

    async def _resolve_grouped_action_validators(
        self,
        *,
        organization_id: str,
        cfg_organization_sudo_action_id: str,
    ) -> List[Dict[str, Any]]:
        from app.modules.security.enums.security_enum import ESudoActionAccessTypeFlag

        global_access_records = await self._fetch_sudo_action_access_records(
            organization_id=organization_id,
            sudo_action_access_type=ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value,
        )
        grouped_access_records = await self._fetch_sudo_action_access_records(
            organization_id=organization_id,
            sudo_action_access_type=ESudoActionAccessTypeFlag.GROUPED_ACCESS.value,
            cfg_organization_sudo_action_id=cfg_organization_sudo_action_id,
        )
        all_records = (global_access_records or []) + (grouped_access_records or [])
        return await self._resolve_validator_users_from_access_records(
            organization_id=organization_id,
            access_records=all_records,
        )

    async def _resolve_cross_org_validators_from_global_access(
        self,
        *,
        owner_organization_id: str,
        cfg_organization_sudo_action_id: Optional[str] = None,
        cross_access_type: Optional[str] = None,
        targeted_type: Optional[str] = None,
        use_sys_cross_validation_mapping: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Resolve cross/inter validators:
        1) Resolve configured peer organizations for this endpoint/action.
        2) Fetch GLOBAL_ACCESS validators from those organizations.
        """
        from app.modules.security.enums.security_enum import ESudoActionAccessTypeFlag

        target_organization_ids: List[str] = []
        if use_sys_cross_validation_mapping:
            cross_validation_organizations = await self.fetch_data_from_collection(
                collection_key=CollectionKey.SYS_CROSS_VALIDATION_ORGANIZATION,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={
                    "filter__sys_organization_id": str(owner_organization_id),
                    "filter__is_activated": True,
                },
            )
            target_organization_ids = sorted(
                {
                    str(record.get("targeted_id", "")).strip()
                    for record in (cross_validation_organizations or [])
                    if str(record.get("targeted_id", "")).strip()
                }
            )
        else:
            cross_org_records = await self._fetch_sudo_action_access_records(
                organization_id=owner_organization_id,
                sudo_action_access_type=str(cross_access_type or ""),
                cfg_organization_sudo_action_id=cfg_organization_sudo_action_id,
                targeted_type=targeted_type,
            )
            target_organization_ids = sorted(
                {
                    str(record.get("targeted_id", "")).strip()
                    for record in (cross_org_records or [])
                    if str(record.get("targeted_id", "")).strip()
                }
            )

        if not target_organization_ids:
            return []

        global_access_records: List[Dict[str, Any]] = []
        for target_org_id in target_organization_ids:
            org_global_access = await self._fetch_sudo_action_access_records(
                organization_id=target_org_id,
                sudo_action_access_type=ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value,
            )
            global_access_records.extend(org_global_access or [])

        return await self._resolve_validator_users_from_access_records(
            organization_id=owner_organization_id,
            access_records=global_access_records,
        )

    @staticmethod
    def _build_group_validation_blocked_result(
        *,
        error_code: str,
        message: str,
        resolved_sudo_action_type: str,
        status_code: int = 403,
        validation_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized_validation_context = (
            validation_context
            if isinstance(validation_context, dict)
            else GenericService._build_validation_context(
                current_validation_request_id=None,
                parent_validation_request_id=None,
                root_validation_request_id=None,
                resolved_sudo_action_type=resolved_sudo_action_type,
                is_sudo_group_action=True,
            )
        )
        return {
            "_sudo_group_validation": True,
            "queued": False,
            "blocked": True,
            "status_code": int(status_code),
            "error_code": str(error_code),
            "message": str(message),
            "resolved_sudo_action_type": str(resolved_sudo_action_type),
            "validation_request_id": normalized_validation_context.get(
                "current_validation_request_id"
            ),
            "parent_validation_request_id": normalized_validation_context.get(
                "parent_validation_request_id"
            ),
            "root_validation_request_id": normalized_validation_context.get(
                "root_validation_request_id"
            ),
            "ops_validation_request_id": normalized_validation_context.get(
                "parent_validation_request_id"
            ),
            "validation_context": normalized_validation_context,
        }

    async def _persist_validation_request_users(
        self,
        *,
        validation_request_id: str,
        validators: List[Dict[str, Any]],
        organization_id: str,
        user: Optional[Dict[str, Any]],
        accept_language: str,
    ) -> None:
        """
        Persist validator rows in OPS_VALIDATION_REQUEST_USER.
        """
        from app.modules.core.enums.type_enum import EMultipleValidationStatus

        for validator in validators or []:
            sys_user_id = str(validator.get("sys_user_id", "")).strip()
            if not sys_user_id:
                continue

            access_sources = list(validator.get("access_sources", []) or [])
            first_access_source = access_sources[0] if access_sources else None
            row_payload = {
                "ops_validation_request_id": validation_request_id,
                "sys_organization_id": organization_id,
                "sys_user_id": sys_user_id,
                "has_validation_access": bool(
                    validator.get("has_validation_access", True)
                ),
                "order_by": int(validator.get("order_by", 0)),
                "status": EMultipleValidationStatus.PENDING.value,
                "sudo_action_access_type": first_access_source,
            }
            await self.add_data_to_collection(
                collection_key=CollectionKey.OPS_VALIDATION_REQUEST_USER,
                data=row_payload,
                accept_language=accept_language,
                user=user,
                request=None,
            )

    async def _queue_group_validation_request(
        self,
        *,
        request: Optional[Request],
        collection_key: CollectionKey,
        operation_type: str,
        accept_language: str,
        user: Optional[Dict[str, Any]],
        target_document_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        upsert_query: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Queue grouped/cross validation request when endpoint resolves to grouped-like sudo type.
        Returns:
        - None if no grouped validation is needed for current request.
        - A structured dict with queued or blocked metadata otherwise.
        """
        from app.modules.core.enums.type_enum import EMultipleValidationStatus
        from app.modules.security.enums.security_enum import (
            EConfigSudoActionTypeFlag,
            ESudoActionAccessTargetedTypeFlag,
            ESudoActionAccessTypeFlag,
        )
        from app.modules.security.services.security_validation_service import (
            SecurityValidationService,
        )

        if user is None and request is not None:
            state_user = getattr(getattr(request, "state", None), "user", None)
            if isinstance(state_user, dict):
                user = state_user

        context = self._extract_group_validation_context(request=request, user=user)
        if not context:
            return None

        resolved_sudo_action_type = str(
            context.get("resolved_sudo_action_type", "")
        ).strip()
        cfg_organization_sudo_action_id = str(
            context.get("cfg_organization_sudo_action_id", "")
        ).strip()
        organization_id = str(context.get("organization_id", "")).strip()

        if context.get("is_misconfigured", False) or not cfg_organization_sudo_action_id:
            return self._build_group_validation_blocked_result(
                error_code="SUDO_GROUP_ACTION_MISCONFIGURED",
                message="Grouped sudo action is misconfigured for this endpoint.",
                resolved_sudo_action_type=resolved_sudo_action_type,
            )

        if not organization_id:
            return self._build_group_validation_blocked_result(
                error_code="INVALID_USER_ORGANIZATION",
                message="Unable to resolve organization for grouped validation.",
                resolved_sudo_action_type=resolved_sudo_action_type,
            )

        validators: List[Dict[str, Any]] = []
        blocked_error_code = "SUDO_GROUP_VALIDATORS_MISSING"
        blocked_message = (
            "Missing users/groups with global validation access or grouped access."
        )

        if (
            resolved_sudo_action_type
            == EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value
        ):
            validators = await self._resolve_grouped_action_validators(
                organization_id=organization_id,
                cfg_organization_sudo_action_id=cfg_organization_sudo_action_id,
            )

        elif (
            resolved_sudo_action_type
            == EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION.value
        ):
            validators = await self._resolve_cross_org_validators_from_global_access(
                owner_organization_id=organization_id,
                use_sys_cross_validation_mapping=True,
            )
            blocked_error_code = "SUDO_GROUP_CROSS_VALIDATION_CONFIG_MISSING"
            blocked_message = (
                "Missing cross-validation organizations or global validators configuration."
            )

        elif (
            resolved_sudo_action_type
            == EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION.value
        ):
            validators = await self._resolve_cross_org_validators_from_global_access(
                owner_organization_id=organization_id,
                cfg_organization_sudo_action_id=cfg_organization_sudo_action_id,
                cross_access_type=ESudoActionAccessTypeFlag.GROUPED_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACCESS.value,
                targeted_type=ESudoActionAccessTargetedTypeFlag.INTER_CONNECTED_ORGANIZATION.value,
            )
            blocked_error_code = "SUDO_GROUP_INTER_CONNECTED_VALIDATORS_MISSING"
            blocked_message = (
                "Missing inter-connected organization validators with global validation access."
            )

        if not validators:
            return self._build_group_validation_blocked_result(
                error_code=blocked_error_code,
                message=blocked_message,
                resolved_sudo_action_type=resolved_sudo_action_type,
            )

        next_validator_id = str(validators[0].get("sys_user_id", "")).strip()
        if not next_validator_id:
            return self._build_group_validation_blocked_result(
                error_code="SUDO_GROUP_VALIDATORS_MISSING",
                message="No eligible validator user found for this grouped operation.",
                resolved_sudo_action_type=resolved_sudo_action_type,
            )

        normalized_target_document_id = str(target_document_id).strip() if target_document_id else None

        # Parent linkage for recursive grouped validations.
        parent_validation_request_id = ""
        root_validation_request_id = ""
        parent_linkage = await self._resolve_parent_validation_linkage(
            request=request,
            organization_id=organization_id,
            resolved_sudo_action_type=resolved_sudo_action_type,
        )
        blocked_parent_linkage_result = parent_linkage.get("blocked_result", None)
        if blocked_parent_linkage_result:
            return blocked_parent_linkage_result
        parent_validation_request_id = str(
            parent_linkage.get("parent_validation_request_id", "")
        ).strip()
        root_validation_request_id = str(
            parent_linkage.get("root_validation_request_id", "")
        ).strip()

        validation_request_data: Dict[str, Any] = {
            "collection_name": collection_key.value,
            "operation_type": operation_type,
            "status": EMultipleValidationStatus.PENDING.value,
            "validator_users": [
                {
                    "sys_user_id": str(item.get("sys_user_id", "")).strip(),
                    "has_validation_access": bool(
                        item.get("has_validation_access", True)
                    ),
                }
                for item in validators
                if str(item.get("sys_user_id", "")).strip()
            ],
            "created_by_id": user.get("id", None) if user else None,
            "sys_organization_id": organization_id,
            "endpoint_path": str(request.url.path) if request else "",
            "endpoint_method": str(request.method) if request else "",
            "next_validator_id": next_validator_id,
            "validation_request_type": resolved_sudo_action_type,
        }
        if parent_validation_request_id:
            validation_request_data["ops_validation_request_id"] = parent_validation_request_id
        if normalized_target_document_id:
            validation_request_data["target_document_id"] = normalized_target_document_id
        if data is not None:
            validation_request_data["data"] = data
        if upsert_query is not None:
            validation_request_data["upsert_query"] = upsert_query

        validation_request_id = await self.add_data_to_collection(
            collection_key=CollectionKey.OPS_VALIDATION_REQUEST,
            data=validation_request_data,
            accept_language=accept_language,
            user=user,
            request=None,
        )

        await self._persist_validation_request_users(
            validation_request_id=str(validation_request_id),
            validators=validators,
            organization_id=organization_id,
            user=user,
            accept_language=accept_language,
        )

        # ------------------------------------------------------------------
        # Notifications: email + SMS to first validator (fire-and-forget).
        # ------------------------------------------------------------------
        first_validator_info: Optional[Dict[str, Any]] = None
        validation_request_info: Optional[Dict[str, Any]] = None
        try:
            first_validator_info = await self.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=accept_language,
                query={"filter___id": next_validator_id},
            )
            validation_request_info = await self.fetch_one_from_collection(
                collection_key=CollectionKey.OPS_VALIDATION_REQUEST,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=accept_language,
                query={"filter___id": str(validation_request_id)},
            )
            if first_validator_info and validation_request_info:
                validation_service = SecurityValidationService(
                    accept_language=accept_language
                )
                # Email (fire-and-forget, handled inside the method)
                await validation_service.send_first_validation_request_email(
                    data=validation_request_info,
                    user=first_validator_info,
                )
                # SMS (fire-and-forget, handled inside the method)
                await validation_service.send_first_validation_request_sms(
                    data=validation_request_info,
                    user=first_validator_info,
                )
        except Exception as notify_error:
            self.app_debug_print(
                f"Grouped validation queued but notification failed: {notify_error}",
                True,
            )

        # ------------------------------------------------------------------
        # VALIDATION_PROCESS Redis key: create (root) or update (sub-process).
        # Returns a process_id UUID the client must forward as
        # X-Validation-Process-Id on subsequent sub-calls.
        # ------------------------------------------------------------------
        normalized_validation_request_id = str(validation_request_id)
        effective_root_validation_request_id = (
            root_validation_request_id or normalized_validation_request_id
        )

        validation_process_id = ""
        try:
            validation_process_id = await self._create_or_update_validation_process_key(
                request=request,
                validation_request_id=normalized_validation_request_id,
                root_validation_request_id=effective_root_validation_request_id,
                parent_validation_request_id=parent_validation_request_id,
                organization_id=organization_id,
                resolved_sudo_action_type=resolved_sudo_action_type,
            )
        except Exception as process_key_err:
            self.app_debug_print(
                f"Grouped validation queued but process-key creation failed: {process_key_err}",
                True,
            )

        # ------------------------------------------------------------------
        validation_context = self._build_validation_context(
            current_validation_request_id=normalized_validation_request_id,
            parent_validation_request_id=parent_validation_request_id or None,
            root_validation_request_id=effective_root_validation_request_id,
            resolved_sudo_action_type=resolved_sudo_action_type,
            is_sudo_group_action=True,
            validation_process_id=validation_process_id or None,
        )

        return {
            "_sudo_group_validation": True,
            "queued": True,
            "blocked": False,
            "status_code": 200,
            "message": "Validation request queued",
            "validation_request_id": normalized_validation_request_id,
            "validation_process_id": validation_process_id,
            "target_document_id": normalized_target_document_id,
            "ops_validation_request_id": parent_validation_request_id or None,
            "parent_validation_request_id": parent_validation_request_id or None,
            "root_validation_request_id": effective_root_validation_request_id,
            "resolved_sudo_action_type": resolved_sudo_action_type,
            "cfg_organization_sudo_action_id": cfg_organization_sudo_action_id,
            "validation_context": validation_context,
        }

    async def add_data_to_collection(
        self,
        collection_key: str,
        data: Dict[str, Any],
        accept_language: str = DEFAULT_LANGUAGE,
        user: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> Any:
        """
        Add data to a collection using BaseDocument lifecycle hooks.

        Modern approach:
        - Uses save_with_hooks() for automatic translation and encryption
        - Leverages pre_save and post_save hooks
        - No manual translation handling needed

        Args:
            collection_key: The collection identifier
            data: The data to add
            accept_language: Language code for translations (default: "fr")
            user: Optional user context for created_by_id

        Returns:
            The inserted document id (default flow) or grouped-validation metadata.
        """
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        from app.modules.core.utils.model.base_document import BaseDocument

        # Get metadata for the collection
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        model_class = metadata.model_class

        # Make a copy of the data
        processed_data = data.copy()

        # Add created_by_id if user is provided
        if user:
            processed_data["created_by_id"] = user.get("id", None)

        group_validation_context = self._extract_group_validation_context(
            request=request,
            user=user,
        )
        effective_user = user
        if group_validation_context and not effective_user and request is not None:
            state_user = getattr(getattr(request, "state", None), "user", None)
            if isinstance(state_user, dict):
                effective_user = state_user

        if group_validation_context:
            from app.modules.core.enums.type_enum import EMultipleValidationStatus

            # In grouped/cross flows, created records are persisted as pending.
            processed_data["multiple_validation_status"] = (
                EMultipleValidationStatus.PENDING.value
            )
            if effective_user and effective_user.get("id", None):
                processed_data["created_by_id"] = effective_user.get("id", None)

        self.app_debug_print(f"\n\n\n add_data_to_collection - Input data: {processed_data} \n\n\n", True)

        try:
            # Convert ObjectId fields if needed
            validated_data = self.convert_id_fields(processed_data.copy())

            # Create model instance (triggers @model_validator decorators)
            model_instance = model_class.model_validate(validated_data)

            self.app_debug_print(f"\n\n\n add_data_to_collection - accept_language : {accept_language} \n\n\n", True)
            self.app_debug_print(f"\n\n\n add_data_to_collection - Model instance created \n\n\n", True)

            # Check if model uses BaseDocument (new pattern)
            if isinstance(model_instance, BaseDocument):
                # Modern approach: Use save_with_hooks
                # This automatically handles:
                # - Translation (via pre_save)
                # - Encryption (via pre_save)
                # - Timestamps (via pre_save)
                # - Post-save operations (via post_save)
                saved_instance = await model_instance.save_with_hooks(
                    accept_language=accept_language,
                    user=effective_user
                )

                self.app_debug_print(f"\n\n\n add_data_to_collection - Saved with hooks {saved_instance} \n\n\n", True)

                # Always return the identifier to keep API responses consistent
                saved_item_id = str(saved_instance.id)
                if group_validation_context:
                    queue_result = await self._queue_group_validation_request(
                        request=request,
                        collection_key=self._as_collection_key(collection_key),
                        operation_type="create",
                        accept_language=accept_language,
                        user=effective_user,
                        target_document_id=saved_item_id,
                        data=None,
                    )
                    if queue_result is not None:
                        # Roll back created pending record when queueing fails/blocked.
                        if queue_result.get("blocked", False):
                            try:
                                await self.hard_delete_data_from_collection(
                                    collection_key=self._as_collection_key(collection_key),
                                    item_id=saved_item_id,
                                    accept_language=accept_language,
                                    by_pass_exception=True,
                                    request=None,
                                    user=effective_user,
                                )
                            except Exception as rollback_error:
                                self.app_debug_print(
                                    f"Failed to rollback pending grouped create record {saved_item_id}: {rollback_error}",
                                    True,
                                )
                        queue_result.setdefault("target_document_id", saved_item_id)
                        return queue_result
                return saved_item_id

            else:
                # Legacy approach: Use DAO for models not yet migrated to BaseDocument
                self.app_debug_print(f"\n\n\n add_data_to_collection - Using legacy DAO approach \n\n\n", True)

                # Handle translations manually for legacy models
                if accept_language != DEFAULT_LANGUAGE:
                    processed_data = await self.handle_translations_for_add(
                        model_class,
                        processed_data,
                        accept_language
                    )

                # Extract validated data
                validated_data = model_instance.model_dump(exclude_unset=False)
                validated_data.pop('id', None)

                # Use DAO to add
                dao = DAO(metadata.collection_name, model_class, is_read_only=False)
                _user_id = user.get('id') if isinstance(user, dict) else None
                _org_id = user.get('sys_organization_id') if isinstance(user, dict) else None
                result = await dao.add(validated_data, sys_organization_id=_org_id, sys_user_id=_user_id)
                saved_item_id = str(result)
                if group_validation_context:
                    queue_result = await self._queue_group_validation_request(
                        request=request,
                        collection_key=self._as_collection_key(collection_key),
                        operation_type="create",
                        accept_language=accept_language,
                        user=effective_user,
                        target_document_id=saved_item_id,
                        data=None,
                    )
                    if queue_result is not None:
                        if queue_result.get("blocked", False):
                            try:
                                await self.hard_delete_data_from_collection(
                                    collection_key=self._as_collection_key(collection_key),
                                    item_id=saved_item_id,
                                    accept_language=accept_language,
                                    by_pass_exception=True,
                                    request=None,
                                    user=effective_user,
                                )
                            except Exception as rollback_error:
                                self.app_debug_print(
                                    f"Failed to rollback pending grouped create record {saved_item_id}: {rollback_error}",
                                    True,
                                )
                        queue_result.setdefault("target_document_id", saved_item_id)
                        return queue_result
                return saved_item_id

        except Exception as error:
            self.app_debug_print(f"\n\n\n add_data_to_collection - Error: {error} \n\n\n", True)
            raise HTTPException(
                status_code=422,
                detail=f"Failed to add data: {str(error)}"
            )

    async def handle_translations_for_add(
        self,
        model_class: Type[Any],
        data: Dict[str, Any],
        target_language: str
    ) -> Dict[str, Any]:

        try:
            """
            Process fields that need translation for a new document.
            """
            # Make a copy of the data to avoid modifying the original
            processed_data = data.copy()

            # Initialize translations dictionary if not present
            if "translations" not in processed_data:
                processed_data["translations"] = {}

            # Debug the model class and data
            self.app_debug_print(f"\n\n\n handle_translations_for_add - Model class: {model_class.__name__} \n\n\n", False)
            self.app_debug_print(f"\n\n\n handle_translations_for_add - Input data: {processed_data} \n\n\n", False)

            # Import BaseModelUtils for translation methods
            from app.modules.core.utils.model.base_model_utils import BaseModelUtils

            # Process each field in the model
            for field_name, field in model_class.model_fields.items():
                # Skip if field is not in data
                if field_name not in processed_data:
                    continue

                # Extract metadata for the field
                meta = field.json_schema_extra or {}

                # Check if field can be translated
                if meta.get("may_have_translation", False) and processed_data[field_name]:
                    field_value = processed_data[field_name]

                    # Skip complex types for now
                    if not isinstance(field_value, (str, int, float, bool)):
                        continue

                    # Convert to string for translation
                    if not isinstance(field_value, str):
                        field_value = str(field_value)

                    # If target language is not French, we need to translate back to French
                    if target_language != DEFAULT_LANGUAGE:
                        # Translate the field value back to French
                        french_value = await BaseModelUtils.google_translate_text(
                            text=field_value,
                            target_language=DEFAULT_LANGUAGE
                        )

                        # Update the field with the French value
                        processed_data[field_name] = french_value

                        # Ensure field has a translations entry
                        if field_name not in processed_data["translations"]:
                            processed_data["translations"][field_name] = {}

                        # Store original target language value in translations
                        processed_data["translations"][field_name][target_language] = field_value

                        # Also store the French translation
                        processed_data["translations"][field_name][DEFAULT_LANGUAGE] = french_value
                    else:
                        # If target language is French, just store it in translations
                        if field_name not in processed_data["translations"]:
                            processed_data["translations"][field_name] = {}

                        # Store original value as French
                        processed_data["translations"][field_name][DEFAULT_LANGUAGE] = field_value

            # Debug the processed data
            self.app_debug_print(f"\n\n\n handle_translations_for_add - Final data: {processed_data} \n\n\n", False)

            return processed_data
        except Exception as e:
            self.app_debug_print(f"Error in handle_translations_for_add: {e}", False)
            # Include more detailed error information
            self.app_debug_print(f"Error details: {type(e).__name__}, {str(e)}", False)
            raise HTTPException(status_code=500, detail=f"Error in handle_translations_for_add: {e}")

    def convert_id_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
            """
            Convert all fields ending with '_id' to ObjectId if they are not None and not already an ObjectId.
            """
            for key, value in data.items():
                if key == "id" and value is not None:
                    data['_id'] = ObjectId(value)
                if key == "id" and value is None:
                    data['_id'] = ObjectId()
                if key.endswith("_id") and value is not None:
                    if not isinstance(value, ObjectId):
                        try:
                            data[key] = ObjectId(value)
                        except Exception as e:
                            raise ValueError(f"Invalid ObjectId format for field '{key}': {value}") from e
            return data
    async def upsert_data_to_collection(
        self,
        collection_key: CollectionKey,
        filter_data: Dict[str, Any],
        update_data: Dict[str, Any],
        accept_language: str = DEFAULT_LANGUAGE,
        translation_strategy: TranslationStrategy = TranslationStrategy.DEFAULT,
        user: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> Any:
        """
        Perform an upsert operation for the specified collection with translation support.

        :param collection_key: The key to identify the collection.
        :param filter_data: Dictionary to filter the existing document.
        :param update_data: Dictionary with new data to update or insert.
        :param accept_language: Language code for translations. Default is DEFAULT_LANGUAGE.
        :param translation_strategy: Strategy for handling translations. Default is DEFAULT.
        :return: The inserted or updated document.
        """
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        # Retrieve model metadata
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        # Check if the collection is exposed
        if not metadata.is_exposed:
            raise PermissionError(f"Access to collection '{collection_key.value}' is not allowed.")

        # Get the model class for the collection
        model_class = metadata.model_class
        existing_doc = None
        # Handle translations if language is not French
        if model_class:
            # First, check if document exists to determine if this is an update or insert
            dao = DAO(metadata.collection_name, metadata.model_class,is_read_only=False)
            existing_doc = await dao.find_one(filter_data)

            group_validation_context = self._extract_group_validation_context(
                request=request,
                user=user,
            )
            effective_user = user
            if group_validation_context and not effective_user and request is not None:
                state_user = getattr(getattr(request, "state", None), "user", None)
                if isinstance(state_user, dict):
                    effective_user = state_user
            if group_validation_context:
                if existing_doc:
                    existing_doc_id = ""
                    if isinstance(existing_doc, dict):
                        existing_doc_id = self._normalize_identifier(
                            existing_doc.get("id", None)
                            or existing_doc.get("_id", None)
                        )
                    else:
                        existing_doc_id = self._normalize_identifier(
                            getattr(existing_doc, "id", None)
                            or getattr(existing_doc, "_id", None)
                        )

                    return await self._queue_group_validation_request(
                        request=request,
                        collection_key=self._as_collection_key(collection_key),
                        operation_type="upsert",
                        accept_language=accept_language,
                        user=effective_user,
                        target_document_id=existing_doc_id,
                        data=update_data,
                        upsert_query=filter_data,
                    )

                # Upsert-as-create under grouped flow: persist pending record then queue.
                from app.modules.core.enums.type_enum import EMultipleValidationStatus

                pending_create_data = dict(update_data or {})
                pending_create_data["multiple_validation_status"] = (
                    EMultipleValidationStatus.PENDING.value
                )
                if effective_user and effective_user.get("id", None):
                    pending_create_data["created_by_id"] = effective_user.get("id", None)

                created_item_id = await self.add_data_to_collection(
                    collection_key=self._as_collection_key(collection_key),
                    data=pending_create_data,
                    accept_language=accept_language,
                    user=effective_user,
                    request=None,
                )
                created_item_id = str(created_item_id)
                queue_result = await self._queue_group_validation_request(
                    request=request,
                    collection_key=self._as_collection_key(collection_key),
                    operation_type="create",
                    accept_language=accept_language,
                    user=effective_user,
                    target_document_id=created_item_id,
                    data=None,
                    upsert_query=None,
                )
                if queue_result is not None:
                    if queue_result.get("blocked", False):
                        try:
                            await self.hard_delete_data_from_collection(
                                collection_key=self._as_collection_key(collection_key),
                                item_id=created_item_id,
                                accept_language=accept_language,
                                by_pass_exception=True,
                                request=None,
                                user=effective_user,
                            )
                        except Exception as rollback_error:
                            self.app_debug_print(
                                f"Failed to rollback pending grouped upsert-create record {created_item_id}: {rollback_error}",
                                True,
                            )
                    queue_result.setdefault("target_document_id", created_item_id)
                    return queue_result

            if existing_doc:
                # This is an update operation
                update_data = await self.handle_translations_for_update(
                    model_class=model_class,
                    data=update_data,
                    existing_doc=existing_doc,
                    target_language=accept_language,
                    translation_strategy=translation_strategy
                )
            else:
                # This is an insert operation
                update_data = await self.handle_translations_for_add(
                    model_class=model_class,
                    data=update_data,
                    target_language=accept_language
                )

        # Debug the processed data before sending to DAO
        self.app_debug_print(f"\n\n\n upsert_data_to_collection - Processed data: {update_data} \n\n\n", False)

        # 🔹 **IMPORTANT: Run Pydantic model validation before upsert**
        try:
            # Convert ObjectId fields if needed
            validated_data = self.convert_id_fields(update_data.copy())

            # Create model instance to trigger @model_validator decorators
            if existing_doc:
                # For updates, merge with existing data to ensure all required fields are present
                merged_data = {**existing_doc, **validated_data}
                # Remove MongoDB-specific fields that might cause validation issues
                merged_data.pop('_id', None)
                model_instance = model_class.model_validate(merged_data)
            else:
                # For inserts, validate the new data directly
                model_instance = model_class.model_validate(validated_data)

            # Extract the validated data from the model instance
            # This ensures all @model_validator decorators have run
            validated_data = model_instance.model_dump(exclude_unset=False)

            # Remove the 'id' field if it exists (MongoDB uses '_id')
            validated_data.pop('id', None)

            # For existing-doc updates, only keep original payload fields
            # to avoid $set-ing the entire document and polluting history.
            # For inserts (no existing_doc), keep the full validated data.
            if existing_doc:
                original_keys = set(update_data.keys())
                validated_data = {
                    k: validated_data[k]
                    for k in validated_data
                    if k in original_keys
                }

            self.app_debug_print(f"\n\n\n upsert_data_to_collection - Validated data: {validated_data} \n\n\n", False)

        except Exception as validation_error:
            self.app_debug_print(f"\n\n\n Model validation failed: {validation_error} \n\n\n", True)
            raise HTTPException(
                status_code=422,
                detail=f"Model validation failed: {str(validation_error)}"
            )

        # Perform the upsert operation with validated data
        dao = DAO(metadata.collection_name, metadata.model_class, is_read_only=False)
        return await dao.upsert(filter_data, validated_data)




    # Update the update_data_in_collection function
    async def update_data_in_collection(
        self,
        collection_key: str,
        item_id: str,
        data: Dict[str, Any],
        accept_language: str = DEFAULT_LANGUAGE,
        translation_strategy: TranslationStrategy = TranslationStrategy.DEFAULT,
        user: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> Any:
        """
        Update data in a collection with automatic translation support.

        :param collection_key: The key identifying the collection
        :param item_id: The ID of the document to update
        :param data: The data to update
        :param accept_language: The language of the input data (default: DEFAULT_LANGUAGE)
        :param translation_strategy: Strategy for handling translations (default: DEFAULT)
        :return: The updated document
        """
        # Get the model class for the collection
        model_class = self.get_model_class_from_collection_key(collection_key)
        existing_doc = None

        # Handle translations if model class is available
        if model_class:
            # First, get the existing document to merge translations
            existing_doc = await self.fetch_one_from_collection(
                collection_key=collection_key,
                query={"filter___id": item_id},
                output_data_type=OutputDataType.DEFAULT.value
            )

        group_validation_context = self._extract_group_validation_context(
            request=request,
            user=user,
        )
        if group_validation_context:
            return await self._queue_group_validation_request(
                request=request,
                collection_key=self._as_collection_key(collection_key),
                operation_type="update",
                accept_language=accept_language,
                user=user,
                target_document_id=str(item_id),
                data=data,
            )

        # Handle translations if model class is available
        if model_class:
            data = await self.handle_translations_for_update(
                model_class=model_class,
                data=data,
                existing_doc=existing_doc,
                target_language=accept_language,
                translation_strategy=translation_strategy
            )

        # Continue with existing logic
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        # 🔹 **IMPORTANT: Run Pydantic model validation before update**
        try:
            # Convert ObjectId fields if needed
            validated_data = self.convert_id_fields(data.copy())

            # For updates, merge with existing data to ensure all required fields are present
            if existing_doc:
                merged_data = {**existing_doc, **validated_data}
                # Remove MongoDB-specific fields that might cause validation issues
                merged_data.pop('_id', None)
                model_instance = metadata.model_class.model_validate(merged_data)
            else:
                # If no existing doc, validate the new data directly
                model_instance = metadata.model_class.model_validate(validated_data)

            # Extract the validated data from the model instance
            # This ensures all @model_validator decorators have run
            validated_data = model_instance.model_dump(exclude_unset=False)

            # Remove the 'id' field if it exists (MongoDB uses '_id')
            validated_data.pop('id', None)

            # Only keep fields from the original update payload so that
            # the DAO $set and update-history diff only involve the fields
            # that were actually intended to be updated — not the entire
            # document (which would cause false diffs, e.g. password hash
            # appearing "changed" during a simple login_fail_count reset).
            original_keys = set(data.keys())
            validated_data = {
                k: validated_data[k]
                for k in validated_data
                if k in original_keys
            }

            self.app_debug_print(f"\n\n\n update_data_in_collection - Validated data: {validated_data} \n\n\n", False)

        except Exception as validation_error:
            self.app_debug_print(f"\n\n\n Model validation failed: {validation_error} \n\n\n", True)
            raise HTTPException(
                status_code=422,
                detail=f"Model validation failed: {str(validation_error)}"
            )

        dao = DAO(metadata.collection_name, metadata.model_class, is_read_only=False)
        user_id = user.get('id') if isinstance(user, dict) else None
        org_id = user.get('sys_organization_id') if isinstance(user, dict) else None
        result = await dao.update({'_id': item_id}, validated_data, updated_by_user_id=user_id, sys_organization_id=org_id, sys_user_id=user_id)
        return result
    
    async def update_data_with_query_in_collection(
        self,
        collection_key: str,
        native_query: Dict[str, Any],
        data: Dict[str, Any],
        accept_language: str = DEFAULT_LANGUAGE,
        translation_strategy: TranslationStrategy = TranslationStrategy.DEFAULT,
        user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Update data in a collection with automatic translation support.

        :param collection_key: The key identifying the collection
        :param item_id: The ID of the document to update
        :param data: The data to update
        :param accept_language: The language of the input data (default: DEFAULT_LANGUAGE)
        :param translation_strategy: Strategy for handling translations (default: DEFAULT)
        :return: The updated document
        """
        # Get the model class for the collection
        model_class = self.get_model_class_from_collection_key(collection_key)

        # Handle translations if model class is available
        if model_class:
            # First, get the existing document to merge translations
            existing_doc = await self.fetch_native_query_one_from_collection(
                collection_key=collection_key,
                native_query=native_query,
                output_data_type=OutputDataType.DEFAULT.value
            )

            data = await self.handle_translations_for_update(
                model_class=model_class,
                data=data,
                existing_doc=existing_doc,
                target_language=accept_language,
                translation_strategy=translation_strategy
            )

        # Continue with existing logic
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        # 🔹 **IMPORTANT: Run Pydantic model validation before update**
        try:
            # Convert ObjectId fields if needed
            validated_data = self.convert_id_fields(data.copy())

            # For updates, merge with existing data to ensure all required fields are present
            if existing_doc:
                merged_data = {**existing_doc, **validated_data}
                # Remove MongoDB-specific fields that might cause validation issues
                merged_data.pop('_id', None)
                model_instance = metadata.model_class.model_validate(merged_data)
            else:
                # If no existing doc, validate the new data directly
                model_instance = metadata.model_class.model_validate(validated_data)

            # Extract the validated data from the model instance
            # This ensures all @model_validator decorators have run
            validated_data = model_instance.model_dump(exclude_unset=False)

            # Remove the 'id' field if it exists (MongoDB uses '_id')
            validated_data.pop('id', None)

            # Only keep fields from the original update payload (same rationale
            # as update_data_in_collection — avoid sending the entire document
            # through $set and polluting update-history with unchanged fields).
            original_keys = set(data.keys())
            validated_data = {
                k: validated_data[k]
                for k in validated_data
                if k in original_keys
            }

            self.app_debug_print(f"\n\n\n update_data_in_collection - Validated data: {validated_data} \n\n\n", False)

        except Exception as validation_error:
            self.app_debug_print(f"\n\n\n Model validation failed: {validation_error} \n\n\n", True)
            raise HTTPException(
                status_code=422,
                detail=f"Model validation failed: {str(validation_error)}"
            )

        dao = DAO(metadata.collection_name, metadata.model_class, is_read_only=False)
        _user_id = user.get('id') if isinstance(user, dict) else None
        _org_id = user.get('sys_organization_id') if isinstance(user, dict) else None
        result = await dao.update(native_query, validated_data, sys_organization_id=_org_id, sys_user_id=_user_id)
        return result

    async def update_many_in_collection(
        self,
        collection_key: str,
        filter_data: Dict[str, Any],
        data: Dict[str, Any],
        accept_language: str = DEFAULT_LANGUAGE,
        translation_strategy: TranslationStrategy = TranslationStrategy.DEFAULT
    ) -> Dict[str, Any]:
        """
        Update multiple documents in a collection with automatic translation support.

        :param collection_key: The key identifying the collection
        :param filter_data: The filter criteria to identify documents to update
        :param data: The data to update
        :param accept_language: The language of the input data (default: DEFAULT_LANGUAGE)
        :param translation_strategy: Strategy for handling translations (default: DEFAULT)
        :return: The update result
        """
        try:
            # Get the model class for the collection
            model_class = self.get_model_class_from_collection_key(collection_key)
            self.app_debug_print(f"\n\n\n update_many_in_collection - model_class: {model_class} \n\n\n", True)

            # Handle translations if model class is available
            # For bulk updates, we handle translations differently since we don't have a single existing document
            if model_class:
                data = await self.handle_translations_for_bulk_update(
                    model_class=model_class,
                    data=data,
                    target_language=accept_language,
                    translation_strategy=translation_strategy
                )

            self.app_debug_print(f"\n\n\n update_many_in_collection - Translated data: {data} \n\n\n", True)

            # Continue with existing logic
            from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
            if not metadata:
                raise ValueError(f"Invalid collection key: {collection_key}")

            # 🔹 **IMPORTANT: Run Pydantic model validation before update**
            try:
                # Convert ObjectId fields if needed
                validated_data = self.convert_id_fields(data.copy())

                # For bulk updates, we validate only the update data without merging
                # since we don't know the existing state of all documents
                # Create a minimal instance for validation
                temp_data = validated_data.copy()

                # Add required fields with dummy values for validation if they're not in the update
                for field_name, field in metadata.model_class.model_fields.items():
                    if field.is_required() and field_name not in temp_data:
                        # Add a dummy value based on field type for validation
                        if hasattr(field, 'annotation'):
                            if field.annotation == str:
                                temp_data[field_name] = "temp_validation_value"
                            elif field.annotation == int:
                                temp_data[field_name] = 0
                            elif field.annotation == bool:
                                temp_data[field_name] = False
                            else:
                                temp_data[field_name] = None

                # Validate the structure
                model_instance = metadata.model_class.model_validate(temp_data)

                # For the actual update, only use the fields that were provided
                # Remove the 'id' field if it exists (MongoDB uses '_id')
                validated_data.pop('id', None)

                self.app_debug_print(f"\n\n\n update_many_in_collection - Validated data: {validated_data} \n\n\n", True)

            except Exception as validation_error:
                self.app_debug_print(f"\n\n\n Model validation failed: {validation_error} \n\n\n", True)
                raise validation_error
                # raise HTTPException(
                #     status_code=422,
                #     detail=f"Model validation failed: {str(validation_error)}"
                # )

            # Perform the update operation with validated data
            self.app_debug_print(f"\n\n\n update_many_in_collection - Validated data: {validated_data} \n\n\n", True)
            dao = DAO(metadata.collection_name, metadata.model_class, is_read_only=False)
            result = await dao.update_many(filter_data, validated_data)
            return result

        except Exception as e:
            self.app_debug_print(f"\n\n\n update many: {e} \n\n\n", True)
            raise e

    async def handle_translations_for_bulk_update(
        self,
        model_class: Type[Any],
        data: Dict[str, Any],
        target_language: str,
        translation_strategy: TranslationStrategy = TranslationStrategy.DEFAULT
    ) -> Dict[str, Any]:
        """
        Process fields that need translation for bulk update operations.
        Since we don't have existing documents, we handle translations differently.

        :param model_class: The model class for the documents being updated
        :param data: The update data provided by the user
        :param target_language: The target language code for translations
        :param translation_strategy: Strategy for handling translations
        :return: Updated data with translations
        """
        try:
            # Initialize translations dictionary if not present
            if "translations" not in data:
                data["translations"] = {}

            # Debug the model class and data
            self.app_debug_print(f"\n\n\n handle_translations_for_bulk_update - Model class: {model_class.__name__} \n\n\n", False)
            self.app_debug_print(f"\n\n\n handle_translations_for_bulk_update - Input data: {data} \n\n\n", False)
            self.app_debug_print(f"\n\n\n handle_translations_for_bulk_update - Strategy: {translation_strategy} \n\n\n", False)

            # Import BaseModelUtils for translation methods
            from app.modules.core.utils.model.base_model_utils import BaseModelUtils

            # Process each field in the model that's being updated
            for field_name, field in model_class.model_fields.items():
                # Skip if field is not in update data
                if field_name not in data:
                    continue

                # Extract metadata for the field
                meta = field.json_schema_extra or {}

                # Check if field can be translated
                if meta.get("may_have_translation", False) and data[field_name]:
                    field_value = data[field_name]

                    # Skip complex types for now
                    if not isinstance(field_value, (str, int, float, bool)):
                        continue

                    # Convert to string for translation
                    if not isinstance(field_value, str):
                        field_value = str(field_value)

                    # Ensure field has a translations entry
                    if field_name not in data["translations"]:
                        data["translations"][field_name] = {}

                    # Handle based on translation strategy
                    if translation_strategy == TranslationStrategy.PRESERVE:
                        # Only update the translation for the target language
                        data["translations"][field_name][target_language] = field_value

                        # Don't update the main field if the language is not French
                        if target_language != DEFAULT_LANGUAGE:
                            # Remove the field from the main update to preserve the French value
                            data.pop(field_name, None)
                        else:
                            # If target language is French, update the main field and translation
                            data["translations"][field_name][DEFAULT_LANGUAGE] = field_value

                    elif translation_strategy == TranslationStrategy.CASCADE:
                        # If target language is not French, translate to French first
                        if target_language != DEFAULT_LANGUAGE:
                            french_value = await BaseModelUtils.google_translate_text(
                                text=field_value,
                                target_language=DEFAULT_LANGUAGE
                            )
                            # Update the main field with French value
                            data[field_name] = french_value
                            # Store both translations
                            data["translations"][field_name][DEFAULT_LANGUAGE] = french_value
                            data["translations"][field_name][target_language] = field_value
                        else:
                            # If target language is French, just store it
                            data["translations"][field_name][DEFAULT_LANGUAGE] = field_value

                    else:  # DEFAULT strategy
                        # If target language is not French, we need to translate back to French
                        if target_language != DEFAULT_LANGUAGE:
                            # Translate the field value back to French
                            french_value = await BaseModelUtils.google_translate_text(
                                text=field_value,
                                target_language=DEFAULT_LANGUAGE
                            )

                            # Update the main field with the French value
                            data[field_name] = french_value

                            # Store original target language value in translations
                            data["translations"][field_name][target_language] = field_value

                            # Also store the French translation
                            data["translations"][field_name][DEFAULT_LANGUAGE] = french_value
                        else:
                            # If target language is French, just store it in translations
                            data["translations"][field_name][DEFAULT_LANGUAGE] = field_value

            # Debug the processed data
            self.app_debug_print(f"\n\n\n handle_translations_for_bulk_update - Final data: {data} \n\n\n", False)

            return data
        except Exception as e:
            self.app_debug_print(f"Error in handle_translations_for_bulk_update: {e}", False)
            # Include more detailed error information
            self.app_debug_print(f"Error details: {type(e).__name__}, {str(e)}", False)
            raise HTTPException(status_code=500, detail=f"Error in handle_translations_for_bulk_update: {e}")

    async def handle_translations_for_update(
        self,
        model_class: Type[Any],
        data: Dict[str, Any],
        existing_doc: Dict[str, Any],
        target_language: str,
        translation_strategy: TranslationStrategy = TranslationStrategy.DEFAULT
    ) -> Dict[str, Any]:
        """
        Process fields that need translation for an existing document update.
        Merges existing translations with new ones based on the translation strategy.

        :param model_class: The model class for the document being updated
        :param data: The update data provided by the user
        :param existing_doc: The existing document from the database
        :param target_language: The target language code for translations
        :param translation_strategy: Strategy for handling translations
        :return: Updated data with translations
        """
        try:
            # Initialize translations dictionary from existing document if available
            existing_translations = existing_doc.get("translations", {}) if isinstance(existing_doc, dict) else {}

            # If translations not in update data, initialize it with existing translations
            if "translations" not in data:
                data["translations"] = existing_translations.copy()

            # Debug the model class and data
            self.app_debug_print(f"\n\n\n handle_translations_for_update - Model class: {model_class.__name__} \n\n\n", False)
            self.app_debug_print(f"\n\n\n handle_translations_for_update - Input data: {data} \n\n\n", False)
            self.app_debug_print(f"\n\n\n handle_translations_for_update - Strategy: {translation_strategy} \n\n\n", False)

            # Import BaseModelUtils for translation methods
            from app.modules.core.utils.model.base_model_utils import BaseModelUtils

            # Process each field in the model that's being updated
            for field_name, field in model_class.model_fields.items():
                # Skip if field is not in update data
                if field_name not in data:
                    continue

                # Extract metadata for the field
                meta = field.json_schema_extra or {}

                # Check if field can be translated
                if meta.get("may_have_translation", False) and data[field_name]:
                    field_value = data[field_name]

                    # Skip complex types for now
                    if not isinstance(field_value, (str, int, float, bool)):
                        continue

                    # Convert to string for translation
                    if not isinstance(field_value, str):
                        field_value = str(field_value)

                    # Ensure field has a translations entry
                    if field_name not in data["translations"]:
                        data["translations"][field_name] = {}

                    # Handle based on translation strategy
                    if translation_strategy == TranslationStrategy.PRESERVE:
                        # Only update the translation for the target language
                        data["translations"][field_name][target_language] = field_value

                        # Don't update the main field if the language is not French
                        if target_language != DEFAULT_LANGUAGE:
                            # Remove the field from the main update to preserve the French value
                            data.pop(field_name, None)
                        else:
                            # If target language is French, update the main field and translation
                            data["translations"][field_name][DEFAULT_LANGUAGE] = field_value

                    elif translation_strategy == TranslationStrategy.CASCADE:
                        # If target language is not French, translate to French first
                        if target_language != DEFAULT_LANGUAGE:
                            french_value = await BaseModelUtils.google_translate_text(
                                text=field_value,
                                target_language=DEFAULT_LANGUAGE
                            )
                            # Update the main field with French value
                            data[field_name] = french_value
                            # Store both translations
                            data["translations"][field_name][DEFAULT_LANGUAGE] = french_value
                            data["translations"][field_name][target_language] = field_value
                        else:
                            # If target language is French, just store it
                            data["translations"][field_name][DEFAULT_LANGUAGE] = field_value

                        # Get all existing languages for this field
                        existing_langs = []
                        if field_name in existing_translations:
                            existing_langs = list(existing_translations[field_name].keys())

                        # Regenerate translations for all languages except the target and French
                        for lang in existing_langs:
                            if lang not in [DEFAULT_LANGUAGE, target_language]:
                                # Use the French value as source for translation
                                source_text = data["translations"][field_name][DEFAULT_LANGUAGE]
                                translated = await BaseModelUtils.google_translate_text(
                                    text=source_text,
                                    target_language=lang
                                )
                                data["translations"][field_name][lang] = translated

                    else:  # DEFAULT strategy
                        # If target language is not French, we need to translate back to French
                        if target_language != DEFAULT_LANGUAGE:
                            # Translate the field value back to French
                            french_value = await BaseModelUtils.google_translate_text(
                                text=field_value,
                                target_language=DEFAULT_LANGUAGE
                            )

                            # Update the main field with the French value
                            data[field_name] = french_value

                            # Store original target language value in translations
                            data["translations"][field_name][target_language] = field_value

                            # Also store the French translation
                            data["translations"][field_name][DEFAULT_LANGUAGE] = french_value
                        else:
                            # If target language is French, just store it in translations
                            data["translations"][field_name][DEFAULT_LANGUAGE] = field_value

                        # If there are other languages in the existing translations, preserve them
                        if field_name in existing_translations:
                            for lang, trans in existing_translations[field_name].items():
                                # Skip the languages we've already handled
                                if lang in [DEFAULT_LANGUAGE, target_language]:
                                    continue

                                # Preserve other language translations
                                data["translations"][field_name][lang] = trans

            # Debug the processed data
            self.app_debug_print(f"\n\n\n handle_translations_for_update - Final data: {data} \n\n\n", False)

            return data
        except Exception as e:
            self.app_debug_print(f"Error in handle_translations_for_update: {e}", False)
            # Include more detailed error information
            self.app_debug_print(f"Error details: {type(e).__name__}, {str(e)}", False)
            raise HTTPException(status_code=500, detail=f"Error in handle_translations_for_update: {e}")

    async def hard_delete_data_from_collection(
        self,
        collection_key: CollectionKey,
        item_id: str,
        accept_language: Optional[str] = DEFAULT_LANGUAGE,
        by_pass_exception: Optional[bool] = False,
        request: Optional[Request] = None,
        user: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Hard deletes (permanently removes) a document from the specified collection.
        """
        group_validation_context = self._extract_group_validation_context(
            request=request,
            user=user,
        )
        if group_validation_context:
            return await self._queue_group_validation_request(
                request=request,
                collection_key=self._as_collection_key(collection_key),
                operation_type="hard_delete",
                accept_language=accept_language or DEFAULT_LANGUAGE,
                user=user,
                target_document_id=str(item_id),
                data=None,
                upsert_query=None,
            )

        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        # Check if the collection is exposed
        if not metadata.is_exposed:
            raise PermissionError(f"Access to collection '{collection_key.value}' is not allowed.")

        dao = DAO(metadata.collection_name,metadata.model_class,is_read_only=False)
        user_id = user.get('id') if isinstance(user, dict) else None
        org_id = user.get('sys_organization_id') if isinstance(user, dict) else None
        return await dao.delete(item_id,accept_language,by_pass_exception, deleted_by_user_id=user_id, sys_organization_id=org_id, sys_user_id=user_id)


    async def soft_delete_data_from_collection(
        self,
        collection_key: CollectionKey,
        item_id: str,
        accept_language: Optional[str] = DEFAULT_LANGUAGE,
        by_pass_exception: Optional[bool] = False,
        request: Optional[Request] = None,
        user: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Soft deletes a document in the specified collection by updating `deleted_at`.
        """
        group_validation_context = self._extract_group_validation_context(
            request=request,
            user=user,
        )
        if group_validation_context:
            return await self._queue_group_validation_request(
                request=request,
                collection_key=self._as_collection_key(collection_key),
                operation_type="soft_delete",
                accept_language=accept_language or DEFAULT_LANGUAGE,
                user=user,
                target_document_id=str(item_id),
                data=None,
                upsert_query=None,
            )

        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        # Retrieve model metadata
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        # Check if the collection is exposed
        if not metadata.is_exposed:
            raise PermissionError(f"Access to collection '{collection_key.value}' is not allowed.")

        dao = DAO(metadata.collection_name,metadata.model_class,is_read_only=False)
        return await dao.soft_delete(item_id,accept_language,by_pass_exception)



    async def fetch_data_from_collection(
        self,
        collection_key: CollectionKey,
        all_data: bool,
        output_data_type: OutputDataType = OutputDataType.DEFAULT,
        limit: int = 10,
        page: int = 0,
        accept_language: str = DEFAULT_LANGUAGE,
        query: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, int]] = {"created_at": -1},
        endpoint_call: Optional[bool] = False,
        force_include_fields: list = [],
        user: Optional[Dict[str, Any]] = None,
        _skip_rls: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetch documents dynamically from a MongoDB collection using a CollectionKey,
        with support for filtering, pagination, sorting, and custom output formatting.
        """
        self.app_debug_print(f"\n\n\n sort 3> : {sort}\n\n\n", False)
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        if not metadata.is_exposed and endpoint_call:
            raise PermissionError(f"Access to collection '{collection_key.value}' is not allowed.")

        # Get the model class for the collection
        model_class = metadata.model_class

        # Create a DAO for the collection
        dao = DAO(metadata.collection_name, model_class,is_read_only=True)

        # Process query parameters hidde_
        processed_query = {}
        if query:
            # Create a copy of the query to avoid modifying the original
            processed_query = self.convert_query_params(dict(query))

        # Apply default sorting if not specified
        if not sort:
            sort = {"created_at", -1}  # Default: sort by created_at in descending order

        hidde_on_view_values = {
            key[len("hidde_on_view__"):]: value
            for key, value in processed_query.items()
            if key.startswith("hidde_on_view__")
        }
        # Apply pagination if not all_data
        skip = page * limit if not all_data else 0
        limit_value = limit if not all_data else 0  # 0 means no limit

        # Initialize variables for parent includes and user filters
        parent_includes = {}
        logged_user_in_filters = {}
        db_filter = {}

        # Process the query parameters to build the MongoDB filter
        try:
            # 🔹 **Parse query filters with new comparison operators**
            or_conditions = []  # Collect OR conditions properly
            ne_conditions = {}  # Collect $ne conditions for the same field

            for key, value in list(processed_query.items()):
                if key.startswith("filter__"):
                    db_field = key.split("__", 1)[1]
                    if db_field.endswith("__in"):
                        db_field = db_field.replace("__in", "")
                        db_filter[db_field] = {"$in": value}
                    elif db_field.endswith("__lt"):
                        db_field = db_field.replace("__lt", "")
                        db_filter[db_field] = {"$lt": value}
                    elif db_field.endswith("__lte"):
                        db_field = db_field.replace("__lte", "")
                        db_filter[db_field] = {"$lte": value}
                    elif db_field.endswith("__gt"):
                        db_field = db_field.replace("__gt", "")
                        db_filter[db_field] = {"$gt": value}
                    elif db_field.endswith("__gte"):
                        db_field = db_field.replace("__gte", "")
                        db_filter[db_field] = {"$gte": value}
                    else:
                        db_filter[db_field] = value
                # 🔹 **Handle filter_ne__ for $ne (not equal) conditions**
                elif key.startswith("filter_ne__"):
                    db_field = key.split("__", 1)[1]
                    # Handle multiple $ne conditions for the same field
                    if db_field not in ne_conditions:
                        ne_conditions[db_field] = []
                    ne_conditions[db_field].append(value)
                # 🔹 **New comparison operators with cleaner syntax**
                elif key.startswith("lt__"):
                    db_field = key.split("__", 1)[1]
                    db_filter[db_field] = {"$lt": value}
                elif key.startswith("lte__"):
                    db_field = key.split("__", 1)[1]
                    db_filter[db_field] = {"$lte": value}
                elif key.startswith("gt__"):
                    db_field = key.split("__", 1)[1]
                    db_filter[db_field] = {"$gt": value}
                elif key.startswith("gte__"):
                    db_field = key.split("__", 1)[1]
                    db_filter[db_field] = {"$gte": value}
                elif key.startswith("or_filter__"):
                    db_field = key.split("__", 1)[1]
                    # Handle different comparison operators within OR conditions
                    if db_field.endswith("__lt"):
                        field_name = db_field.replace("__lt", "")
                        or_conditions.append({field_name: {"$lt": value}})
                    elif db_field.endswith("__lte"):
                        field_name = db_field.replace("__lte", "")
                        or_conditions.append({field_name: {"$lte": value}})
                    elif db_field.endswith("__gt"):
                        field_name = db_field.replace("__gt", "")
                        or_conditions.append({field_name: {"$gt": value}})
                    elif db_field.endswith("__gte"):
                        field_name = db_field.replace("__gte", "")
                        or_conditions.append({field_name: {"$gte": value}})
                    elif db_field.endswith("__in"):
                        field_name = db_field.replace("__in", "")
                        or_conditions.append({field_name: {"$in": value}})
                    else:
                        # Simple equality condition
                        or_conditions.append({db_field: value})
                #from_logged_in_user__ref_entity_id
                elif key.startswith("from_logged_in_user__"):
                    logged_user_in_filters[value] = value
                    if user:
                        org = await self.fetch_native_query_one_from_collection(
                            collection_key=CollectionKey.SYS_ORGANIZATION,
                            output_data_type=OutputDataType.DEFAULT,
                            accept_language=accept_language,
                            native_query={
                                "_id": ObjectId(user.get('sys_organization_id', ''))
                            }
                        )
                        self.app_debug_print(f"\n\n\n from_logged_in_user__  org :  {True if org else False} \n\n\n", False)
                        db_field = key.split("__", 1)[1]
                        if value == 'ref_entity':
                            self.app_debug_print(f" entity value : {value}")
                            if org:
                                entity = await self.fetch_native_query_one_from_collection(
                                    collection_key=CollectionKey.REF_ENTITY,
                                    output_data_type=OutputDataType.DEFAULT,
                                    accept_language=accept_language,
                                    native_query={
                                        "_id": ObjectId(org.get('ref_entity_id', ''))
                                    }
                                )
                                if entity:
                                    db_filter[db_field] = entity['id']
                        elif value == 'sys_user':
                            self.app_debug_print(f" user value : {value}")
                            if org and user:
                                db_filter[db_field] = user['id']
                        elif value == 'sys_organization':
                            self.app_debug_print(f" organization value : {value}")
                            if org:
                                db_filter[db_field] = org['id']
                elif key.startswith("include__parent___"):
                    # Extract parent collection, alias (if exists), local key, and foreign key
                    parts = key.split("___")

                    if len(parts) < 6:
                        raise ValueError(f"Invalid include__parent format: {key}")

                    parent_collection = parts[1]
                    alias = parent_collection  # Default alias if no custom `__as__` provided
                    local_key = parts[-3]  # Always third from the end
                    foreign_key = parts[-1]  # Always last

                    # Check if an alias `__as__` is specified
                    if "as" in parts:
                        alias_index = parts.index("as")
                        alias = parts[alias_index + 1]  # Get the custom alias

                    parent_includes[alias] = {
                        "parent_collection": parent_collection,
                        "local_key": local_key,
                        "foreign_key": foreign_key,
                    }
                elif key.startswith("nullable_value__"):
                    db_field = key.split("__", 1)[1]
                    db_filter[db_field] = None

            # 🔹 **Add OR conditions to the main filter if any exist**
            if or_conditions:
                if db_filter:
                    # Combine existing AND conditions with OR conditions
                    db_filter = {"$and": [db_filter, {"$or": or_conditions}]}
                else:
                    # Only OR conditions exist
                    db_filter = {"$or": or_conditions}

            # 🔹 **Process $ne (not equal) conditions**
            for field_name, ne_values in ne_conditions.items():
                if len(ne_values) == 1:
                    # Single $ne condition
                    if field_name in db_filter:
                        # Field already has conditions, combine with $and
                        existing_condition = db_filter[field_name]
                        if isinstance(existing_condition, dict):
                            existing_condition["$ne"] = ne_values[0]
                        else:
                            db_filter[field_name] = {"$eq": existing_condition, "$ne": ne_values[0]}
                    else:
                        db_filter[field_name] = {"$ne": ne_values[0]}
                else:
                    # Multiple $ne conditions for the same field - use $nin (not in)
                    if field_name in db_filter:
                        # Field already has conditions, combine with $and
                        existing_condition = db_filter[field_name]
                        if isinstance(existing_condition, dict):
                            existing_condition["$nin"] = ne_values
                        else:
                            db_filter[field_name] = {"$eq": existing_condition, "$nin": ne_values}
                    else:
                        db_filter[field_name] = {"$nin": ne_values}

            # If TREE output is requested, add a filter to fetch only top-level documents
            if output_data_type == OutputDataType.TREE_DATA_TABLE.value or output_data_type == OutputDataType.TREE.value or output_data_type == OutputDataType.CASCADE.value or output_data_type == OutputDataType.CASCADE_ALL.value:
                model_name = getattr(metadata.model_class.Settings, "name", metadata.model_class.__class__.__name__.lower())
                parent_field = f"{model_name}_id"
                # check if parent_field is not in db_filter
                self.app_debug_print(f"\n\n\n\n parent_field not in db_filter : {parent_field not in db_filter}", True)


                if model_name not in logged_user_in_filters and parent_field not in db_filter:
                    db_filter[parent_field] = None

            # Convert Enum values and handle data type conversions for comparison operators
            from app.modules.core.services.converter.converter_service import ConverterService
            db_filter = ConverterService.convert_enum_to_value(db_filter)


            # Retrieve the documents from the collection
            db_filter = self.convert_query_params(db_filter)
            sort = self.process_sort(sort)
            # 🔒 RLS: final step before query execution. Must be the LAST mutation
            # of db_filter so no subsequent code can widen the user's scope.
            if not _skip_rls:
                db_filter = await self._apply_rls_filter(
                    collection_key=collection_key,
                    db_filter=db_filter,
                    user=user,
                )
            self.app_debug_print(f"Query data: {db_filter}", True)
            self.app_debug_print(f"Query data: {db_filter} COLLECTION : {collection_key}", True)
            if all_data:
                cursor = await AsyncExecutor.run_in_thread(
                    dao.collection.find, db_filter
                )
                # cursor = dao.collection.find(db_filter)
                if sort:
                    # app_debug_print(f"\n\n\n BEFORE SORT : {sort}\n\n\n", False)
                    sanitized_sort = self.convert_sort_to_mongo_format(sort)
                    # app_debug_print(f"\n\n\n AFTER SORT : {sort}\n\n\n", False)
                    cursor = cursor.sort(sanitized_sort)
                documents = await cursor.to_list(length=None)
            else:
                skip = page * limit if page > 0 else 0
                cursor = dao.collection.find(db_filter).skip(skip).limit(limit)
                if sort:
                    sanitized_sort = self.convert_sort_to_mongo_format(sort)
                    cursor = cursor.sort(sanitized_sort)
                documents = await cursor.to_list(length=limit)

            self.app_debug_print(f"Query data retrived: {len(documents)}", True)

            # Format each document according to the desired output_data_type
            formatted_data = await self._format_documents_for_collection(
                documents=documents,
                model_class=model_class,
                collection_key=collection_key,
                output_data_type=output_data_type,
                accept_language=accept_language,
                hidde_on_view_values=hidde_on_view_values,
                force_include_fields=force_include_fields,
                force_exclude_fields=None,
            )
            self.app_debug_print(f"\n formatted_data  >: {len(formatted_data)} \n\n", False)
            self.app_debug_print(f"\n >> parent_includes.items()  >: {parent_includes.items()} \n\n", False)

            # 🔹 **Fetch and append Parent Data for multiple includes**
            for alias, params in parent_includes.items():
                for document in formatted_data:
                    self.app_debug_print(f"\n\n >>> alias <<< : {alias} |  >>> params <<< : {params} |  >>> output_data_type <<< : {output_data_type}  \n\n",False)
                    await self.attach_recursive_data(document, alias, params, accept_language, output_data_type)

            self.app_debug_print(f"\n returned in formatted_data  >: {len(formatted_data)} \n\n", False)
            return formatted_data

        except Exception as e:
            # format error
            formatted_error = format_exception(message="fetch fail", exception=e, include_traceback=True)
            self.app_debug_print(f"Error during fetch_data_from_collection: {formatted_error}", True)
            return []

    async def fetch_native_query_data_from_collection(
        self,
        collection_key: CollectionKey,
        all_data: bool,
        output_data_type: OutputDataType = OutputDataType.DEFAULT,
        limit: int = 10,
        page: int = 0,
        accept_language: str = DEFAULT_LANGUAGE,
        native_query: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, int]] = {"created_at": -1},
        user: Optional[Dict[str, Any]] = None,
        _skip_rls: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetch documents dynamically from a MongoDB collection using a native MongoDB query.

        This function supports:
        - Pagination (using limit and page)
        - Sorting
        - Custom output formatting based on output_data_type
        - Language-based formatting (using accept_language)
        - Retrieving all data (if all_data is True)

        :param collection_key: The key identifying the collection.
        :param all_data: Flag indicating whether to retrieve all documents.
        :param output_data_type: The desired output formatting.
        :param limit: Maximum number of documents per page.
        :param page: Page number for pagination.
        :param accept_language: Language code for translations.
        :param native_query: A native MongoDB query dictionary.
        :param sort: Optional list of sort tuples.
        :return: A list of formatted documents.

        Example:
            >>> native_query = {"status": "active"}
            >>> native_query = {
                        "$or": [
                            {"status": "active"},
                            {"priority": "high"}
                        ]
                    }
            >>> data = await fetch_native_query_data_from_collection(
            ...     collection_key=CollectionKey.USERS,
            ...     all_data=False,
            ...     output_data_type=OutputDataType.DATA_TABLE,
            ...     limit=20,
            ...     page=0,
            ...     accept_language="en",
            ...     native_query=native_query,
            ...     sort={"created_at": -1}
            ... )
            >>> print(data)
        """
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        collection_name = metadata.collection_name
        model_class = metadata.model_class

        dao = DAO(collection_name, model_class,is_read_only=True)
        assert dao.collection is not None, f"Error: Collection {collection_name} is None!"

        # Use the provided native MongoDB query, or default to an empty filter
        db_filter = native_query if native_query is not None else {}

        # If TREE output is requested, add a filter to fetch only top-level documents
        if output_data_type == OutputDataType.TREE.value:
            model_name = getattr(model_class.Settings, "name", model_class.__class__.__name__.lower())
            parent_field = f"{model_name}_id"
            self.app_debug_print(f"\n\n\n\n parent_field not in db_filter : {parent_field not in db_filter}", True)
            if parent_field not in db_filter:
                db_filter = {**db_filter, parent_field: None}

        db_filter = self.convert_query_params(db_filter)
        sort = self.process_sort(sort)
        self.app_debug_print(f"Query data native : {db_filter}", True)
        # Process the query parameters to build the MongoDB filter
        try:
            logged_user_in_filters = {}

            # If TREE output is requested, add a filter to fetch only top-level documents
            # if output_data_type == OutputDataType.TREE.value or output_data_type == OutputDataType.CASCADE.value or output_data_type == OutputDataType.CASCADE_ALL.value:
            #     model_name = getattr(metadata.model_class.Settings, "name", metadata.model_class.__class__.__name__.lower())
            #     parent_field = f"{model_name}_id"
            #     if model_name not in logged_user_in_filters:
            #         db_filter[parent_field] = None

            # Convert Enum values and handle data type conversions for comparison operators
            from app.modules.core.services.converter.converter_service import ConverterService
            db_filter = ConverterService.convert_enum_to_value(db_filter)


            # Retrieve the documents from the collection
            db_filter = self.convert_query_params(db_filter)
            sort = self.process_sort(sort)
            # 🔒 RLS: final step before query execution.
            if not _skip_rls:
                db_filter = await self._apply_rls_filter(
                    collection_key=collection_key,
                    db_filter=db_filter,
                    user=user,
                )
            self.app_debug_print(f"Query data: {db_filter}", True)
            if all_data:
                cursor = dao.collection.find(db_filter)
                if sort:
                    # app_debug_print(f"\n\n\n BEFORE SORT : {sort}\n\n\n", False)
                    sanitized_sort = self.convert_sort_to_mongo_format(sort)
                    # app_debug_print(f"\n\n\n AFTER SORT : {sort}\n\n\n", False)
                    cursor = cursor.sort(sanitized_sort)
                documents = await cursor.to_list(length=None)
            else:
                skip = page * limit if page > 0 else 0
                cursor = dao.collection.find(db_filter).skip(skip).limit(limit)
                if sort:
                    sanitized_sort = self.convert_sort_to_mongo_format(sort)
                    cursor = cursor.sort(sanitized_sort)
                documents = await cursor.to_list(length=limit)

            self.app_debug_print(f"Query data retrived: {len(documents)}", True)

            # Format each document according to the desired output_data_type
            formatted_data = await self._format_documents_for_collection(
                documents=documents,
                model_class=model_class,
                collection_key=collection_key,
                output_data_type=output_data_type,
                accept_language=accept_language,
            )

            self.app_debug_print(f"\n formatted_data  >: {len(formatted_data)} \n\n", False)

            self.app_debug_print(f"\n returned in formatted_data  >: {len(formatted_data)} \n\n", False)
            return formatted_data

        except Exception as e:
            self.app_debug_print(f"Error during fetch_native_query_data_from_collection: {e}", False)
            return []

    async def fetch_one_from_collection(
        self,
        collection_key: CollectionKey,
        output_data_type: OutputDataType = OutputDataType.DEFAULT,
        accept_language: str = DEFAULT_LANGUAGE,
        query: Optional[Dict[str, Any]] = None,
        endpoint_call: Optional[bool] = False,
        sort: Optional[Dict[str, int]] = {"created_at": -1},
        # sort: Optional[Any] = None,
        force_include_fields: list = [],
        force_exclude_fields: list = [],
        user: Optional[Dict[str, Any]] = None,
        _skip_rls: bool = False,
        request : Optional[Request] =  None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single document dynamically from a MongoDB collection using a CollectionKey,
        with support for filtering, sorting, and custom output formatting.

        Parameters:
            collection_key (CollectionKey):
                The key that identifies the target MongoDB collection.
            output_data_type (OutputDataType, optional):
                Determines how the output data is formatted. Default is DEFAULT.
            accept_language (str, optional):
                Specifies the language code to use for translations. Default is DEFAULT_LANGUAGE.
            query (Optional[Dict[str, Any]], optional):
                A dictionary of query parameters.
            sort (Optional[Union[Dict[str, int], List[Tuple[str, int]]], optional):
                A dictionary or list of tuples specifying sort order. Default is {"created_at": -1}.
            endpoint_call (Optional[bool], optional):
                If True, and the collection is not exposed, a PermissionError will be raised.
            force_include_fields (list, optional):
                A list of fields to force include in the output.
            user (Optional[Dict[str, Any]], optional):
                The user making the request, used for filtering based on the logged-in user.

        Returns:
            Optional[Dict[str, Any]]:
                A formatted document (as a dictionary) from the MongoDB collection if found,
                otherwise None.
        """
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        if not metadata.is_exposed and endpoint_call:
            raise PermissionError(f"Access to collection '{collection_key.value}' is not allowed.")

        # Get the model class for the collection
        model_class = metadata.model_class

        # Create a DAO for the collection
        dao = DAO(metadata.collection_name, model_class,is_read_only=True)
        assert dao.collection is not None, f"Error: Collection {metadata.collection_name} is None!"

        # Process query parameters with enhanced data type conversion
        from app.modules.core.services.converter.converter_service import ConverterService
        processed_query = {} if query is None else ConverterService.convert_enum_to_value(query)
        db_filter = {}
        parent_includes = {}
        logged_user_in_filters = {}

        # 🔹 **Parse query filters with new comparison operators** (same as fetch_data_from_collection)
        or_conditions = []  # Collect OR conditions properly
        ne_conditions = {}  # Collect $ne conditions for the same field

        for key, value in list(processed_query.items()):  # Use list() to create a copy for iteration
            if key.startswith("filter__"):
                db_field = key.split("__", 1)[1]
                if db_field.endswith("__in"):
                    db_field = db_field.replace("__in", "")
                    db_filter[db_field] = {"$in": value}
                elif db_field.endswith("__lt"):
                    db_field = db_field.replace("__lt", "")
                    db_filter[db_field] = {"$lt": value}
                elif db_field.endswith("__lte"):
                    db_field = db_field.replace("__lte", "")
                    db_filter[db_field] = {"$lte": value}
                elif db_field.endswith("__gt"):
                    db_field = db_field.replace("__gt", "")
                    db_filter[db_field] = {"$gt": value}
                elif db_field.endswith("__gte"):
                    db_field = db_field.replace("__gte", "")
                    db_filter[db_field] = {"$gte": value}
                else:
                    db_filter[db_field] = value
            # 🔹 **Handle filter_ne__ for $ne (not equal) conditions**
            elif key.startswith("filter_ne__"):
                db_field = key.split("__", 1)[1]
                # Handle multiple $ne conditions for the same field
                if db_field not in ne_conditions:
                    ne_conditions[db_field] = []
                ne_conditions[db_field].append(value)
            # 🔹 **New comparison operators with cleaner syntax**
            elif key.startswith("lt__"):
                db_field = key.split("__", 1)[1]
                db_filter[db_field] = {"$lt": value}
            elif key.startswith("lte__"):
                db_field = key.split("__", 1)[1]
                db_filter[db_field] = {"$lte": value}
            elif key.startswith("gt__"):
                db_field = key.split("__", 1)[1]
                db_filter[db_field] = {"$gt": value}
            elif key.startswith("gte__"):
                db_field = key.split("__", 1)[1]
                db_filter[db_field] = {"$gte": value}
            elif key.startswith("or_filter__"):
                db_field = key.split("__", 1)[1]
                # Handle different comparison operators within OR conditions
                if db_field.endswith("__lt"):
                    field_name = db_field.replace("__lt", "")
                    or_conditions.append({field_name: {"$lt": value}})
                elif db_field.endswith("__lte"):
                    field_name = db_field.replace("__lte", "")
                    or_conditions.append({field_name: {"$lte": value}})
                elif db_field.endswith("__gt"):
                    field_name = db_field.replace("__gt", "")
                    or_conditions.append({field_name: {"$gt": value}})
                elif db_field.endswith("__gte"):
                    field_name = db_field.replace("__gte", "")
                    or_conditions.append({field_name: {"$gte": value}})
                elif db_field.endswith("__in"):
                    field_name = db_field.replace("__in", "")
                    or_conditions.append({field_name: {"$in": value}})
                else:
                    # Simple equality condition
                    or_conditions.append({db_field: value})
            elif key.startswith("from_logged_in_user__"):
                logged_user_in_filters[value] = value
                if user:
                    org = await self.fetch_native_query_one_from_collection(
                        collection_key=CollectionKey.SYS_ORGANIZATION,
                        output_data_type=OutputDataType.DEFAULT,
                        accept_language=accept_language,
                        native_query={
                            "_id": ObjectId(user.get('sys_organization_id', ''))
                        }
                    )
                    db_field = key.split("__", 1)[1]
                    if value == 'ref_entity':
                        if org:
                            entity = await self.fetch_native_query_one_from_collection(
                                collection_key=CollectionKey.REF_ENTITY,
                                output_data_type=OutputDataType.DEFAULT,
                                accept_language=accept_language,
                                native_query={
                                    "_id": ObjectId(org.get('ref_entity_id', ''))
                                }
                            )
                            if entity:
                                db_filter[db_field] = entity['id']
                    elif value == 'sys_user':
                        if org and user:
                            db_filter[db_field] = user['id']
                    elif value == 'sys_organization':
                        if org:
                            db_filter[db_field] = org['id']
            elif key.startswith("include__parent___"):
                # Extract parent collection, alias (if exists), local key, and foreign key
                parts = key.split("___")
                if len(parts) < 6:
                    raise ValueError(f"Invalid include__parent format: {key}")

                parent_collection = parts[1]
                alias = parent_collection  # Default alias if no custom `__as__` provided
                local_key = parts[-3]  # Always third from the end
                foreign_key = parts[-1]  # Always last

                # Check if an alias `__as__` is specified
                if "as" in parts:
                    alias_index = parts.index("as")
                    alias = parts[alias_index + 1]  # Get the custom alias

                parent_includes[alias] = {
                    "parent_collection": parent_collection,
                    "local_key": local_key,
                    "foreign_key": foreign_key,
                }
            elif key.startswith("nullable_value__"):
                db_field = key.split("__", 1)[1]
                db_filter[db_field] = None

        # 🔹 **Add OR conditions to the main filter if any exist** (same as fetch_data_from_collection)
        if or_conditions:
            if db_filter:
                # Combine existing AND conditions with OR conditions
                db_filter = {"$and": [db_filter, {"$or": or_conditions}]}
            else:
                # Only OR conditions exist
                db_filter = {"$or": or_conditions}

        # 🔹 **Process $ne (not equal) conditions** (same as fetch_data_from_collection)
        for field_name, ne_values in ne_conditions.items():
            if len(ne_values) == 1:
                # Single $ne condition
                if field_name in db_filter:
                    # Field already has conditions, combine with $and
                    existing_condition = db_filter[field_name]
                    if isinstance(existing_condition, dict):
                        existing_condition["$ne"] = ne_values[0]
                    else:
                        db_filter[field_name] = {"$eq": existing_condition, "$ne": ne_values[0]}
                else:
                    db_filter[field_name] = {"$ne": ne_values[0]}
            else:
                # Multiple $ne conditions for the same field - use $nin (not in)
                if field_name in db_filter:
                    # Field already has conditions, combine with $and
                    existing_condition = db_filter[field_name]
                    if isinstance(existing_condition, dict):
                        existing_condition["$nin"] = ne_values
                    else:
                        db_filter[field_name] = {"$eq": existing_condition, "$nin": ne_values}
                else:
                    db_filter[field_name] = {"$nin": ne_values}

        # If TREE output is requested, add a filter to fetch only top-level documents
        if output_data_type in [
            OutputDataType.TREE.value,
            OutputDataType.CASCADE.value,
            OutputDataType.CASCADE_ALL.value,
            OutputDataType.TREE_DATA_TABLE.value

        ]:
            model_name = getattr(metadata.model_class.Settings, "name", metadata.model_class.__class__.__name__.lower())
            parent_field = f"{model_name}_id"
            self.app_debug_print(f"\n\n\n\n parent_field not in db_filter : {parent_field not in db_filter}", True)
            if model_name not in logged_user_in_filters and parent_field not in db_filter:
                db_filter[parent_field] = None

        # Convert Enum values and handle data type conversions for comparison operators
        from app.modules.core.services.converter.converter_service import ConverterService
        db_filter = ConverterService.convert_enum_to_value(db_filter)
        try:
            db_filter = self.convert_query_params(db_filter)
            sort = self.process_sort(sort)
            # 🔒 RLS: final step before query execution.
            if not _skip_rls:
                db_filter = await self._apply_rls_filter(
                    collection_key=collection_key,
                    db_filter=db_filter,
                    user=user,
                )
            self.app_debug_print(f"[DEBUG] db_filter: {db_filter}  : collection key : {collection_key}", False)
            self.app_debug_print(f"[DEBUG] sort: {sort}", False)
            self.app_debug_print(f"[DEBUG] force_include_fields (before): {force_include_fields}, type: {type(force_include_fields)}", False)

            # Check if force_include_fields is a dictionary and convert to list if needed
            if isinstance(force_include_fields, dict):
                self.app_debug_print(f"[DEBUG] Converting force_include_fields from dict to list in main method: {force_include_fields}", False)
                force_include_fields = list(force_include_fields.keys())
                self.app_debug_print(f"[DEBUG] force_include_fields (after conversion): {force_include_fields}", False)

            # Fetch a single document from the collection using find_one sys_user_id
            cursor = dao.collection.find(db_filter)
            if sort:
                sanitized_sort = self.convert_sort_to_mongo_format(sort)
                cursor = cursor.sort(sanitized_sort)
            documents = await cursor.to_list(length=1)
            # document = await dao.collection.find(db_filter, sort=sort)
            self.app_debug_print(f"[DEBUG] Found documents: {len(documents) if documents else 0}", False)
            if documents:
                document = documents[0]  # Assuming only one document matches the query
                self.app_debug_print(f"[DEBUG] Document ID: {document.get('_id')}", False)
                document["_id"] = str(document["_id"])  # Convert ObjectId to string

                # Ensure translations exist
                if "translations" not in document:
                    document["translations"] = {}

                try:
                    self.app_debug_print(f"[DEBUG] Document keys: {list(document.keys())}", False)
                    self.app_debug_print(f"[DEBUG] Model class: {model_class.__name__}", False)

                    # Print a few key fields from the document
                    for key in ['id', '_id', 'identifier', 'sys_user_id']:
                        if key in document:
                            self.app_debug_print(f"[DEBUG] Document[{key}]: {document[key]}", False)

                    try:
                        model_instance = model_class.parse_obj(document)
                    except Exception as parse_error:
                        self.app_debug_print(f"[ERROR] Failed to parse document: {parse_error}", True)
                        # Try to create a model instance with required fields only
                        required_fields = {}
                        for field_name, field in model_class.model_fields.items():
                            if field.is_required():
                                # If field is in document, use that value
                                if field_name in document:
                                    required_fields[field_name] = document.get(field_name)
                                # Otherwise provide a default value based on field type
                                else:
                                    # For string fields, generate a temporary value
                                    if field.annotation == str:
                                        required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                                    # For other types, you might need different defaults
                        # Always include ID field if available
                        if "_id" in document:
                            required_fields["id"] = str(document["_id"])
                        elif "id" in document:
                            required_fields["id"] = document["id"]
                        else:
                            required_fields["id"] = str(ObjectId())
                        model_instance = model_class(**required_fields)

                    self.app_debug_print(f"[DEBUG] Created model instance of type: {type(model_instance)}", False)
                except Exception as e:
                    self.app_debug_print(f"[ERROR] Failed to create model instance: {str(e)}", True)
                    import traceback
                    self.app_debug_print(f"[ERROR] Traceback: {traceback.format_exc()}", True)
                    return None

                # Normalize output_data_type to an enum instance for the unified format() API
                if isinstance(output_data_type, OutputDataType):
                    output_enum = output_data_type
                else:
                    output_enum = OutputDataType(output_data_type)

                # Use unified format() API on the model instance
                if not hasattr(model_instance, "format") or not callable(getattr(model_instance, "format")):
                    raise AttributeError(f"Model {model_class} must implement a 'format' method for dynamic fetch")

                self.app_debug_print(f" \n\n\n user before model_instance.format document : {document} \n\n\n", False)

                formatted_doc = await model_instance.format(
                    output_data_type=output_enum,
                    accept_language=accept_language,
                    collection_key=collection_key,
                    force_include_fields=force_include_fields,
                    sort=sort,
                    doc=document,
                    force_exclude_fields=force_exclude_fields,
                )
                self.app_debug_print(f" \n\n\n user after model_instance.format formatted_doc : {formatted_doc} \n\n\n", False)

                # If formatted_doc is None or empty, use the original document
                if formatted_doc is None or (isinstance(formatted_doc, dict) and len(formatted_doc) == 0):
                    self.app_debug_print(f"[DEBUG] formatted_doc is None or empty, using original document", True)
                    formatted_doc = document.copy()
                    # Ensure we have an ID field
                    if "_id" in formatted_doc and "id" not in formatted_doc:
                        formatted_doc["id"] = str(formatted_doc["_id"])
                        formatted_doc.pop("_id", None)

                # Attach parent data if required
                for alias, params in parent_includes.items():
                    await self.attach_recursive_data(formatted_doc, alias, params, accept_language, output_data_type)

                self.app_debug_print(f" \n\n\n user before return formatted_doc : {formatted_doc} \n\n\n", False)
                # Convert all _id fields to strings before returning
                return self.convert_id_fields_to_str(formatted_doc)

            return None

        except Exception as e:
            print(f"Error during fetch_one_from_collection: {e}")
            return None

    async def fetch_native_query_one_from_collection(
        self,
        collection_key: CollectionKey,
        output_data_type: OutputDataType = OutputDataType.DEFAULT,
        accept_language: str = DEFAULT_LANGUAGE,
        native_query: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, int]] = {"created_at": -1},
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single document dynamically from a MongoDB collection using a native MongoDB query.

        This function supports:
        - Custom output formatting based on output_data_type.
        - Language-based formatting (using accept_language).
        - Sorting.

        :param collection_key: The key identifying the collection.
        :param output_data_type: The desired output formatting.
        :param accept_language: Language code for translations.
        :param native_query: A native MongoDB query dictionary.
        :param sort: Optional list of sort tuples.
        :return: A formatted document, or None if no document is found.
        Example:
            >>> native_query = {"username": "johndoe"}
            >>> native_query = {
                        "$or": [
                            {"status": "active"},
                            {"priority": "high"}
                        ]
                    }
            >>> document = await fetch_native_query_one_from_collection(
            ...     collection_key=CollectionKey.USERS,
            ...     output_data_type=OutputDataType.DEFAULT,
            ...     accept_language="en",
            ...     native_query=native_query,
            ...     sort=[("username", 1)]
            ... )
            >>> print(document)
        """
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        collection_name = metadata.collection_name
        model_class = metadata.model_class

        dao = DAO(collection_name, model_class,is_read_only=True)
        assert dao.collection is not None, f"Error: Collection {collection_name} is None!"

        # Use the provided native MongoDB query, or default to an empty filter.
        db_filter = native_query if native_query is not None else {}

        db_filter = self.convert_query_params(db_filter)
        sort = self.process_sort(sort)
        # If TREE output is requested, add a filter to fetch only top-level documents.
        if output_data_type == OutputDataType.TREE.value:
            model_name = getattr(model_class.Settings, "name", model_class.__class__.__name__.lower())
            parent_field = f"{model_name}_id"
            if parent_field not in db_filter:
                db_filter = {**db_filter, parent_field: None}
            # db_filter = {**db_filter, parent_field: None}

        try:
            # Fetch a single document from the collection.
            cursor = dao.collection.find(db_filter)
            if sort:
                sanitized_sort = self.convert_sort_to_mongo_format(sort)
                cursor = cursor.sort(sanitized_sort)
            documents = await cursor.to_list(length=1)  # Limit to 1 document

            if documents:
                document = documents[0]
                document["_id"] = str(document["_id"])  # Convert ObjectId to string

                # Ensure the document has a translations field
                if "translations" not in document:
                    document["translations"] = {}

                try:
                    model_instance = model_class.parse_obj(document)
                except Exception as e:
                    self.app_debug_print(f"Error parsing document: {e}", True)
                    # Try to create a model instance with required fields only
                    required_fields = {}
                    for field_name, field in model_class.model_fields.items():
                        if field.is_required():
                            # If field is in document, use that value
                            if field_name in document:
                                required_fields[field_name] = document.get(field_name)
                            # Otherwise provide a default value based on field type
                            else:
                                # For string fields, generate a temporary value
                                if field.annotation == str:
                                    required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                                # For other types, you might need different defaults
                    # Always include ID field if available
                    if "_id" in document:
                        required_fields["id"] = str(document["_id"])
                    elif "id" in document:
                        required_fields["id"] = document["id"]
                    else:
                        required_fields["id"] = str(ObjectId())
                    model_instance = model_class(**required_fields)

                # Normalize output_data_type to an enum instance for the unified format() API
                if isinstance(output_data_type, OutputDataType):
                    output_enum = output_data_type
                else:
                    output_enum = OutputDataType(output_data_type)

                # Use unified format() API on the model instance
                if not hasattr(model_instance, "format") or not callable(getattr(model_instance, "format")):
                    raise AttributeError(f"Model {model_class} must implement a 'format' method for dynamic fetch")

                formatted_doc = await model_instance.format(
                    output_data_type=output_enum,
                    accept_language=accept_language,
                    collection_key=collection_key,
                    doc=document,
                )

                # If formatted_doc is None or empty, use the original document
                if formatted_doc is None or (isinstance(formatted_doc, dict) and len(formatted_doc) == 0):
                    self.app_debug_print(f"[DEBUG] formatted_doc is None or empty, using original document", True)
                    formatted_doc = document.copy()
                    # Ensure we have an ID field
                    if "_id" in formatted_doc and "id" not in formatted_doc:
                        formatted_doc["id"] = str(formatted_doc["_id"])
                        formatted_doc.pop("_id", None)

                # Convert all _id fields to strings before returning
                return self.convert_id_fields_to_str(formatted_doc)

            return None

        except Exception as e:
            print(f"Error during fetch_native_query_one_from_collection: {e}")
            return None


    async def fetch_native_aggregate_data_from_collection(
        self,
        collection_key: CollectionKey,
        output_data_type: OutputDataType = OutputDataType.DEFAULT,
        limit: Optional[int] = 10,
        page: Optional[int] = 0,
        all_data: Optional[bool] = False,
        accept_language: str = DEFAULT_LANGUAGE,
        pipeline: Optional[List[Dict[str, Any]]] = None,
        sort: Optional[Dict[str, int]] = {"created_at": -1},
        force_include_fields: Optional[list] = [],
        force_exclude_fields: Optional[list] = [],
        user: Optional[Dict[str, Any]] = None,
        _skip_rls: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetch documents dynamically from a MongoDB collection using a native aggregation pipeline.

        This function supports:
        - Pagination (using limit and page) when all_data is False.
        - Optional sorting via a sort parameter.
        - Custom output formatting based on output_data_type.
        - Language-based formatting (using accept_language).

        :param collection_key: The key identifying the collection.
        :param all_data: Flag indicating whether to retrieve all documents.
        :param output_data_type: The desired output formatting.
        :param limit: Maximum number of documents per page.
        :param page: Page number for pagination.
        :param accept_language: Language code for translations.
        :param native_aggregate: A list representing the MongoDB aggregation pipeline stages.
        :param sort: Optional list of sort tuples.
        :return: A list of formatted documents.
        Example:
            >>> pipeline = [
            ...     {"$match": {"status": "active"}},
            ...     {"$group": {"_id": "$role", "count": {"$sum": 1}}}
            ... ]
            >>> aggregated_data = await fetch_native_aggregate_data_from_collection(
            ...     collection_key=CollectionKey.USERS,
            ...     all_data=True,
            ...     output_data_type=OutputDataType.DATA_TABLE,
            ...     limit=10,
            ...     page=0,
            ...     accept_language="en",
            ...     native_aggregate=pipeline,
            ...     sort=[("count", -1)]
            ... )
            >>> print(aggregated_data)
        """
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        collection_name = metadata.collection_name
        model_class = metadata.model_class

        dao = DAO(collection_name, model_class,is_read_only=True)
        assert dao.collection is not None, f"Error: Collection {collection_name} is None!"

        # Use the provided native aggregation pipeline or default to an empty pipeline.
        pipeline = pipeline.copy() if pipeline is not None else []

        # 🔒 RLS: prepend a $match stage so the RLS filter is applied BEFORE
        # any $lookup / $group / $unwind stages. Prepending (not appending) is
        # critical — Mongo pushes $match stages down through lookups only when
        # they appear before them in the pipeline.
        if not _skip_rls:
            rls_filter = await self._apply_rls_filter(
                collection_key=collection_key,
                db_filter={},
                user=user,
            )
            if rls_filter:
                pipeline = [{"$match": rls_filter}, *pipeline]

        try:
            # Add pagination stages if not all_data
            if not all_data and limit > 0:
                # Add $skip and $limit stages at the end of the pipeline
                skip_stage = {"$skip": page * limit}
                limit_stage = {"$limit": limit}

                # Check if there are already $skip or $limit stages in the pipeline
                has_skip = any("$skip" in stage for stage in pipeline)
                has_limit = any("$limit" in stage for stage in pipeline)

                # Only add if not already present
                if not has_skip:
                    pipeline.append(skip_stage)
                if not has_limit:
                    pipeline.append(limit_stage)

            # Set cursor batch size to limit memory usage
            cursor_options = {"batchSize": 100}  # Process in smaller batches
            cursor = dao.collection.aggregate(pipeline, **cursor_options)

            # Process documents in batches to reduce memory usage
            documents = []
            batch_size = 100  # Process 100 documents at a time

            while True:
                batch = await cursor.to_list(length=batch_size)
                if not batch:
                    break

                # Process this batch
                for document in batch:
                    if 'password' in document:
                        del document['password']  # Remove the password field
                    if "_id" in document:
                        document["_id"] = str(document["_id"])

                documents.extend(batch)

            self.app_debug_print(f"\n\n\n documents aggregate >> :{len(documents)} \n\n\n", False)

            # Format each document according to the desired output_data_type.
            base_model = self.get_model_class_from_collection_key(collection_key)
            formatted_data = await self._format_documents_for_collection(
                documents=documents,
                model_class=base_model,
                collection_key=collection_key,
                output_data_type=output_data_type,
                accept_language=accept_language,
                force_include_fields=force_include_fields,
                force_exclude_fields=force_exclude_fields,
            )
            self.app_debug_print(f"\n\n\n documents formatted_data >> :{len(formatted_data)} \n\n\n", False)
            return formatted_data

        except Exception as e:
            import traceback
            self.app_debug_print(
                f"❌ fetch_native_aggregate_data_from_collection FAILED "
                f"collection={collection_key} error={type(e).__name__}: {e}\n"
                f"{traceback.format_exc()}",
                True,
            )
            return []


    async def fetch_native_aggregate_one_from_collection(
        self,
        collection_key: CollectionKey,
        output_data_type: OutputDataType = OutputDataType.DEFAULT,
        accept_language: str = DEFAULT_LANGUAGE,
        pipeline: Optional[List[Dict[str, Any]]] = None,
        sort: Optional[Dict[str, int]] = {"created_at": -1},
        force_exclude_fields: Optional[list] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single document dynamically from a MongoDB collection using a native aggregation pipeline.

        This function supports:
        - Optional sorting via a sort parameter.
        - Custom output formatting based on output_data_type.
        - Language-based formatting (using accept_language).

        :param collection_key: The key identifying the collection.
        :param output_data_type: The desired output formatting.
        :param accept_language: Language code for translations.
        :param native_aggregate: A list representing the MongoDB aggregation pipeline stages.
        :param sort: Optional list of sort tuples.
        :return: A formatted document, or None if no document is found.
        Example:
            >>> pipeline = [
            ...     {"$match": {"username": "johndoe"}},
            ... ]
            >>> aggregated_document = await fetch_native_aggregate_one_from_collection(
            ...     collection_key=CollectionKey.USERS,
            ...     output_data_type=OutputDataType.DEFAULT,
            ...     accept_language="en",
            ...     native_aggregate=pipeline,
            ...     sort=[("username", 1)]
            ... )
            >>> print(aggregated_document)
        """
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        collection_name = metadata.collection_name
        model_class = metadata.model_class

        dao = DAO(collection_name, model_class,is_read_only=True)
        assert dao.collection is not None, f"Error: Collection {collection_name} is None!"

        # Use the provided native aggregation pipeline or default to an empty pipeline.
        pipeline = pipeline.copy() if pipeline is not None else []

        # Append a stage to limit the result to 1 document.
        pipeline.append({"$limit": 1})

        try:
            # Execute the aggregation pipeline.
            cursor = dao.collection.aggregate(pipeline)
            documents = await cursor.to_list(length=1)

            if documents:
                document = documents[0]
                if "_id" in document:
                    document["_id"] = str(document["_id"])
                if "translations" not in document:
                    document["translations"] = {}
                try:
                    model_instance = model_class.parse_obj(document)
                except Exception as e:
                    self.app_debug_print(f"Error parsing document: {e}", True)
                    # Try to create a model instance with required fields only
                    required_fields = {}
                    for field_name, field in model_class.model_fields.items():
                        if field.is_required():
                            # If field is in document, use that value
                            if field_name in document:
                                required_fields[field_name] = document.get(field_name)
                            # Otherwise provide a default value based on field type
                            else:
                                # For string fields, generate a temporary value
                                if field.annotation == str:
                                    required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                                # For other types, you might need different defaults
                    # Always include ID field if available
                    if "_id" in document:
                        required_fields["id"] = str(document["_id"])
                    elif "id" in document:
                        required_fields["id"] = document["id"]
                    else:
                        required_fields["id"] = str(ObjectId())
                    model_instance = model_class(**required_fields)

                # Normalize output_data_type to an enum instance for the unified format() API
                if isinstance(output_data_type, OutputDataType):
                    output_enum = output_data_type
                else:
                    output_enum = OutputDataType(output_data_type)

                # Use unified format() API on the model instance
                if not hasattr(model_instance, "format") or not callable(getattr(model_instance, "format")):
                    raise AttributeError(f"Model {model_class} must implement a 'format' method for dynamic fetch")

                formatted_doc = await model_instance.format(
                    output_data_type=output_enum,
                    accept_language=accept_language,
                    collection_key=collection_key,
                    doc=document,
                    force_exclude_fields=force_exclude_fields,
                )

                # If formatted_doc is None or empty, use the original document
                if formatted_doc is None or (isinstance(formatted_doc, dict) and len(formatted_doc) == 0):
                    self.app_debug_print(f"[DEBUG] formatted_doc is None or empty, using original document", True)
                    formatted_doc = document.copy()
                    # Ensure we have an ID field
                    if "_id" in formatted_doc and "id" not in formatted_doc:
                        formatted_doc["id"] = str(formatted_doc["_id"])
                        formatted_doc.pop("_id", None)

                # Convert all _id fields to strings before returning
                return self.convert_id_fields_to_str(formatted_doc)

            return None

        except Exception as e:
            print(f"Error during fetch_native_aggregate_one_from_collection: {e}")
            return None

    async def transform_schema_to_head(
        self,
        schema: dict,
        model_name:str,
        accept_language: str = DEFAULT_LANGUAGE,
        exclude_fields: list = None,
        force_include_fields: list = [],
        is_organization_head:bool = False,
        sys_organization_id: str = None,
        query_params: dict = None,  # Add query parameters
        parent_field: str = None,  # Add query parameters
        default_data_sources: Optional[dict] = {},
        parent_child_head: EParentChildHead = EParentChildHead.NO_SPECIFICATION.value,  # Add query parameters
    ) -> dict:
        """
        Transform schema metadata into the required format for the head.

        Args:
            schema (dict): Schema properties from the model.
            accept_language (str): Language code for translations.
            exclude_fields (list): List of fields to exclude from the head.
            force_include_fields (list): List of fields to forcefully include, overriding exclusions.

        Returns:
            dict: Transformed metadata with populated data_type, constraints, and additional keys.
        """
        # Import TranslationService lazily inside the method to avoid circular imports
        from app.modules.core.services.translation.translation_service import TranslationService
        translation_service = TranslationService()

        transformed = {}
        exclude_fields = exclude_fields or []
        force_include_fields = force_include_fields or []
        query_params = query_params or {}
        self.app_debug_print(f"\n\n step 0 head >>>> query_params : {query_params}",False)
        if is_organization_head == True:
            query_params['default__sys_organization_id'] = str(sys_organization_id)
        self.app_debug_print(f"\n\n after >>>> query_params : {query_params}",False)
        # self.app_debug_print is_cascade (f"\n\n step 0 head >>>> sys_organization_id : {sys_organization_id}",False)
        # Extract default values from query parameters
        skip_recursive_field = query_params.get('skip_recursive_field',False)
        parent_field = f"{model_name}_id"

        # handle hardcode_filter_on__rbac_role_id__filtered_by__cfg_organism_chart_id
        hard_code_filter = {}
        field_with_hardcode_filter = {}
        for key, value in query_params.items():
            if key.startswith("hardcode_filter_on__"):
                # Extract the field names after hardcode_filter_on__ and filtered_by__
                parts = key.split("__filtered_by__")
                if len(parts) == 2:
                    filter_field = parts[0].replace("hardcode_filter_on__", "")
                    filtered_by_field = parts[1]
                    field_with_hardcode_filter[filter_field] = True
                    # Update hard_code_filter with the filtered_by field value
                    if str(filtered_by_field).endswith('_id'):
                        hard_code_filter[f'{filtered_by_field}'] = None if value == 'none' else ObjectId(str(value))
                    else:
                        hard_code_filter[f'{filtered_by_field}'] = None if value == 'none' else value

        self.app_debug_print(f"\n\n hard_code_filter >>>> : {hard_code_filter}\n\n\n\n\n",False)

        default_values = {
            key[len("default__"):]: value
            for key, value in query_params.items()
            if key.startswith("default__")
        }
        constant_values = {
            key[len("constant_value__"):]: value
            for key, value in query_params.items()
            if key.startswith("constant_value__")
        }
        nullable_values = {
            key[len("nullable_value__"):]: value
            for key, value in query_params.items()
            if key.startswith("nullable_value__")
        }

        hidde_on_view_values = {
            key[len("hidde_on_view__"):]: value
            for key, value in query_params.items()
            if key.startswith("hidde_on_view__")
        }
        self.app_debug_print(f"\n\n default_values >>>> : {default_values}",True)
        for field_name, field_meta in schema.items():
            # Determine if the field should be excluded
            self.app_debug_print(f"\n\n step 4 head >>>> : {field_name}",False)
            if skip_recursive_field == True and field_name == parent_field:
                continue

            has_default_data_source = False,
            default_data_source = [],
            if field_name in default_data_sources:
                has_default_data_source = True
                default_data_source = default_data_sources[field_name]

            additional_head = field_meta.get('extra_metas',{}).get("additional_head",'')
            self.app_debug_print(f"\n\n [field_name] : {field_name} additional_headd >>>> : {additional_head}",False)
            self.app_debug_print(f"\n\n [field_name] : {field_name} default_values >>>> : {default_values}",True)
            if additional_head:
                try:
                    collection_key = CollectionKey(additional_head)
                    model_class, model_name = self.get_model_from_collection_key(
                        collection_key,
                        endpoint_call=True  # Enforce API access control
                    )
                    schema_extra = model_class.model_json_schema().get("properties", {})
                    additional_head_result = await self.transform_schema_to_head(schema=schema_extra,
                        model_name=model_name,
                        accept_language=accept_language,
                        exclude_fields=exclude_fields,
                        force_include_fields=force_include_fields,
                        is_organization_head=is_organization_head,
                        sys_organization_id=sys_organization_id,
                        query_params=query_params,
                        parent_field=parent_field,
                        parent_child_head=parent_child_head,
                        # skip_recursive_fields=True
                    )
                    transformed= {
                        **transformed,
                        **additional_head_result
                    }
                except Exception as e:
                    self.app_debug_print(f"Error fetching additional hfead >'{field_name}': {e}",False)


            is_excluded = (
                (field_name in exclude_fields and field_name not in default_values)
                or (field_name in {'is_activated',"_id", "identifier", "translations", f'{parent_field}'})
                or (field_name in {'updated_at','created_at','created_by_id','soft_deleted_by_id','soft_deleted_at','soft_deleted','multiple_validation_status','multiple_validated_at'})
                or (field_meta.get("exclude_from_head", False) and field_name not in default_values)
            )
            self.app_debug_print(f"\n\n step is_excluded head : {is_excluded}",False)
            # Override exclusions if the field is in force_include_fields
            if is_excluded and field_name not in force_include_fields:
                continue
            self.app_debug_print(f"\n\n step 5 head",)
            self.app_debug_print(f"\n\n step force_include_fields head : {force_include_fields}",False)
            # Extract metadata, provide defaults if missing
            data_type = field_meta.get("data_type", {"is_unknown": True})
            field_extra_metas = field_meta.get("extra_metas", {"is_unknown": True})
            constraints = []
            self.app_debug_print(f"\n\n field_extra_metas : {field_extra_metas}",)
            extra_metas = {
                **field_extra_metas
            }

            if field_name in default_values:
                self.app_debug_print(f"\n\n step > head default >>  [{field_name}] : {default_values[field_name]}",True)
                # Parse the default value and additional metadata if provided
                default_value = default_values[field_name]
                extra_metas.update({
                    "has_default_value": True,
                    "skip_on_view": True,  # Example of additional metadata
                })
            else:
                default_value = None

            if field_name in constant_values:
                self.app_debug_print(f"\n\n step > head [{field_name}] : {default_values}",False)
                # Parse the default value and additional metadata if provided
                default_value = constant_values[field_name]
                extra_metas.update({
                    "has_default_value": True,
                })

            if field_name in nullable_values:
                self.app_debug_print(f"\n\n step > head [{field_name}] : {default_values}",False)
                # Parse the default value and additional metadata if provided
                default_value = None # nullable_values[field_name]
                extra_metas.update({
                    "has_default_value": True,
                    "skip_on_view": True,
                })

            if field_name in hidde_on_view_values:
                extra_metas.update({
                    "skip_on_view": True,
                })

            # Handle constraints directly from the field metadata extra
            if field_meta.get("may_have_translation"):
                constraints.append({"may_have_translation": True})
            if field_meta.get("to_be_translated_in_front"):
                constraints.append({"to_be_translated_in_front": True})
            if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}" in field_extra_metas:
                extra_metas.update({
                    "has_min_length": True,
                    "min_length": field_extra_metas[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}"]
                })
            if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}" in field_extra_metas:
                extra_metas.update({
                    "has_max_length": True,
                    "max_length": field_extra_metas[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}"]
                })
            if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}" in field_extra_metas:
                extra_metas.update({
                    "is_required": field_extra_metas[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}"]
                })
            if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.PATTERN.value}" in field_meta:
                constraints.append({"has_regex": True, "regex": field_meta[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.PATTERN.value}"]})
            if field_name in schema.get("required", []):
                constraints.append({"is_required": True})

            # Get field display title with translation
            try:
                display_title = await translation_service.get_static_fields_translation(
                    property_name=field_name,
                    accept_language=accept_language,
                )
            except Exception as e:
                self.app_debug_print(f"Translation error for field '{field_name}': {e}",True)
                display_title = field_meta.get("title", field_name.replace("_", " ").title())

            if not display_title:
                display_title = field_meta.get("title", field_name.replace("_", " ").title())

            # Handle is_select for data_list and data_source
            data_list = []
            data_source = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}")  # Extract data_source from json_schema_extra
            join_organization_query = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}",False)  # Extract data_source from json_schema_extra
            join_profil_or_organization_query = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.JOIN_PROFIL_OR_ORGANIZATION_QUERY.value}",False)  # Extract data_source from json_schema_extra
            # self.app_debug_print(f" data_type : {data_type.get(f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}")}")

            # CASCADE
            cascade_model_name = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}")
            cascade_data = []
            # Add transformed field metadata
            enum_class = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}")

            self.app_debug_print(f"\n\n >>> PARENT data_type.get('{EGLOBAL_DATA_TYPE.IS_CASCADE.value}') :{ data_type.get(f'{EGLOBAL_DATA_TYPE.IS_CASCADE.value}')} | {data_type} | {EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value} : {cascade_model_name}",True)
            if data_type.get(f'{EGLOBAL_DATA_TYPE.IS_CASCADE.value}') is True and cascade_model_name and field_name != f"{parent_field}" and field_name not in default_values:

                try:
                    # collectionKey = self.get_collection_key_from_model_name(cascade_model_name)
                    # Fetch data from the data_source collection
                    # self.app_debug_print(f"\n\n >>> CASCDE MODEL KEY : {collectionKey}")
                    self.app_debug_print(f"\n\n >>> {EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value} :{join_organization_query} | | join_profil_or_organization_query : {join_profil_or_organization_query}",True)
                    query = {}
                    if join_organization_query == True:
                        query={
                            **query,
                            "filter__sys_organization_id":str(sys_organization_id)
                        }
                    if join_profil_or_organization_query == True:
                        # TODO: GET ORGANIZATION
                        organization = await self.fetch_native_query_one_from_collection(
                            collection_key=CollectionKey.SYS_ORGANIZATION,
                            output_data_type=OutputDataType.DEFAULT,
                            accept_language=accept_language,
                            native_query={
                                "_id": ObjectId(sys_organization_id)
                            }
                        )
                        # TODO: GET PROFIL
                        query={
                            "$or":[
                                {
                                    **query,
                                    "filter__sys_organization_id":str(sys_organization_id)
                                },
                                {
                                    **query,
                                    "filter__rbac_profile_id":str(organization['rbac_profile_id']) if organization else None
                                }
                            ]
                        }

                    self.app_debug_print(f"\n\n >>> CASCDE MODEL KEY : {CollectionKey(cascade_model_name)}",True)
                    cascade_data = await self.fetch_data_from_collection(
                        collection_key=CollectionKey(cascade_model_name),
                        output_data_type=OutputDataType.CASCADE.value,
                        all_data=True,
                        query=query,
                        accept_language=accept_language
                    )
                    self.app_debug_print(f"\n\n >>> CASCDE RESPONSE : {cascade_data}",True)
                    transformed[field_name] = {
                        "property_name": field_name,
                        "display_title": display_title,
                        "default_value": default_value,
                        "data_type": data_type,
                        "constraints": constraints,
                        "extra_metas": extra_metas,
                        "data_source": field_meta.get("data_source"),
                        "data_list": cascade_data,
                    }
                except Exception as e:
                    self.app_debug_print(f"Error fetching data for >>'{field_name}': {e}")
            elif data_type.get(f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}") and data_source:
                try:

                    query = {
                        "is_activated":True
                    }

                    self.app_debug_print(f"\n\n\n\n IS SELECT  >> '{field_name}' : {field_with_hardcode_filter} > {field_name in field_with_hardcode_filter} ====> {hard_code_filter}\n\n\n",True)

                    if field_name in field_with_hardcode_filter:
                        query={
                            **query,
                            **hard_code_filter
                        }
                    if join_organization_query == True:
                        query={
                            **query,
                            "sys_organization_id":ObjectId(sys_organization_id),
                        }
                    if join_profil_or_organization_query == True:
                        # TODO: GET ORGANIZATION
                        organization = await self.fetch_native_query_one_from_collection(
                            collection_key=CollectionKey.SYS_ORGANIZATION,
                            output_data_type=OutputDataType.DEFAULT,
                            accept_language=accept_language,
                            native_query={
                                "_id": ObjectId(sys_organization_id)
                            }
                        )
                        current_rbac_profile_id = hard_code_filter.get('rbac_profile_id',None)
                        self.app_debug_print(f"\n\n >>> hard_code_filter : {hard_code_filter}",True)
                        # if 'rbac_profile_id' in hard_code_filter:
                        #     query={
                        #         **query,
                        #         "sys_organization_id":ObjectId(sys_organization_id),
                        #     }
                        # else :
                        query={
                            "$or":[
                                {
                                    **query,
                                    "sys_organization_id":ObjectId(sys_organization_id)
                                },
                                {
                                    **query,
                                    "rbac_profile_id":current_rbac_profile_id if current_rbac_profile_id else ObjectId(organization['rbac_profile_id']) if organization else None
                                }
                            ]
                        }
                    self.app_debug_print(f"\n\n >>> query :{query} | | join_profil_or_organization_query : {join_profil_or_organization_query}",True)
                    # Fetch data from the data_source collection
                    input_select_list = await self.fetch_native_query_data_from_collection(
                        collection_key=CollectionKey(data_source),
                        output_data_type=OutputDataType.INPUT_SELECT,
                        all_data=True,
                        native_query=query,
                        accept_language=accept_language
                    )
                    # Filter out None values and ensure we have a valid list
                    if input_select_list is None:
                        input_select_list = []
                    elif isinstance(input_select_list, list):
                        input_select_list = [item for item in input_select_list if item is not None]
                    self.app_debug_print(f"Query: {query}, Result count: {len(input_select_list) if isinstance(input_select_list, list) else 'not a list'}", True)
                    if has_default_data_source == True:
                        transformed[field_name] = {
                            "property_name": field_name,
                            "display_title": display_title,
                            "default_value": default_value,
                            "data_type": data_type,
                            "constraints": constraints,
                            "extra_metas": extra_metas,
                            "data_source": field_meta.get("data_source"),
                            "data_list": default_data_source,
                        }
                    else:
                        transformed[field_name] = {
                            "property_name": field_name,
                            "display_title": display_title,
                            "default_value": default_value,
                            "data_type": data_type,
                            "constraints": constraints,
                            "extra_metas": extra_metas,
                            "data_source": field_meta.get("data_source"),
                            "data_list": input_select_list if input_select_list else  []
                        }
                except Exception as e:
                    self.app_debug_print(f"Error fetching data for >'{field_name}': {e}",True)

            elif data_type.get(f"{EGLOBAL_DATA_TYPE.IS_AMOUNT.value}"):
                try:
                    currency_data_source = field_extra_metas.get("currency_data_source")
                    currency_props = field_extra_metas.get("currency_props")
                    self.app_debug_print(f" currency_data_source : {currency_data_source} currency_props : {currency_props}",False)
                    self.app_debug_print(f" currency_data_source : {currency_data_source} currency_props : {currency_props}",False)
                    query = {}
                    if join_organization_query:
                        query={
                            **query,
                            "filter__sys_organization_id":str(sys_organization_id)
                        }
                    # Fetch data from the data_source collection
                    input_select_list = await self.fetch_data_from_collection(
                        collection_key=CollectionKey(currency_data_source),
                        output_data_type=OutputDataType.INPUT_SELECT,
                        all_data=True,
                        query=query,
                        accept_language=accept_language
                    )
                    if has_default_data_source == True:
                        transformed[field_name] = {
                            "property_name": field_name,
                            "display_title": display_title,
                            "default_value": default_value,
                            "data_type": data_type,
                            "constraints": constraints,
                            "extra_metas": {
                                **field_extra_metas,
                                "currency_props":currency_props,
                            },
                            "data_source": field_meta.get("data_source"),
                            "data_list": default_data_source,
                        }
                    else:
                        transformed[field_name] = {
                            "property_name": field_name,
                            "display_title": display_title,
                            "default_value": default_value,
                            "data_type": data_type,
                            "constraints": constraints,
                            "extra_metas": extra_metas,
                            "data_source": field_meta.get("data_source"),
                            "data_list": input_select_list
                        }
                except Exception as e:
                    self.app_debug_print(f"Error fetching data for >'{field_name}': {e}",True)
            elif data_type.get(f'{EGLOBAL_DATA_TYPE.IS_ENUM.value}') and enum_class:
                try:
                    self.app_debug_print(f"fetching data for '{field_name}'",False)
                    self.app_debug_print(f"fetching enum_class for '{enum_class}'",False)
                    inner_data_list = TranslationService.get_enum_translated_data_list(enum_class,field_name,accept_language)
                    self.app_debug_print(f"\n\nfetching inner_data_list for '{inner_data_list}' \n\n\n",False)
                    excluded_keys = field_extra_metas.get("except_keys_on_head","") # "key_1,key_2"
                    self.app_debug_print(f"\n\nfetching excluded_keys for '{excluded_keys}' \n\n\n",False)
                    excluded_set = set(excluded_keys.split(","))
                    filtered_data = [item for item in inner_data_list if item["id"] not in excluded_set]
                    transformed[field_name] = {
                        "property_name": field_name,
                        "display_title": display_title,
                        "default_value": default_value,
                        "data_type": data_type,
                        "constraints": constraints,
                        "extra_metas": extra_metas,
                        "data_source": field_meta.get("data_source"),
                        "data_list": filtered_data,
                    }
                except Exception as e:
                    self.app_debug_print(f"Error fetching is_enum for >>'{field_name}': {e}",True)
            else :
                transformed[field_name] = {
                    "property_name": field_name,
                    "display_title": display_title,
                    "default_value": default_value,
                    "data_type": data_type,
                    "constraints": constraints,
                    "extra_metas": extra_metas,
                    "data_source": field_meta.get("data_source"),
                    "data_list": [],
                }
        return transformed

    async def transform_schema_to_child_head(
        self,
        schema: dict,
        model_name:str,
        accept_language: str = DEFAULT_LANGUAGE,
        exclude_fields: list = None,
        force_include_fields: list = [],
        is_organization_head:bool = False,
        sys_organization_id: str = None,
        query_params: dict = None,  # Add query parameters
        parent_field: str = None,  # Add query parameters
        parent_value: str = None,  # Add query parameters
        default_data_sources: Optional[dict] = {},
        parent_child_head: EParentChildHead = EParentChildHead.NO_SPECIFICATION.value,  # Add query parameters
    ) -> dict:
        """
        Transform schema metadata into the required format for the head.

        Args:
            schema (dict): Schema properties from the model.
            accept_language (str): Language code for translations.
            exclude_fields (list): List of fields to exclude from the head.
            force_include_fields (list): List of fields to forcefully include, overriding exclusions.

        Returns:
            dict: Transformed metadata with populated data_type, constraints, and additional keys.
        """
        # Import TranslationService lazily inside the method to avoid circular imports
        from app.modules.core.services.translation.translation_service import TranslationService
        translation_service = TranslationService()

        transformed = {}
        exclude_fields = exclude_fields or []
        force_include_fields = force_include_fields or []
        query_params = query_params or {}
        self.app_debug_print(f"\n\n step 0 head >>>> query_params : {query_params}",False)
        if is_organization_head == True:
            query_params['default__sys_organization_id'] = str(sys_organization_id)
        if is_organization_head == True:
            query_params['default__sys_organization_id'] = str(sys_organization_id)
        self.app_debug_print(f"\n\n after >>>> query_params : {query_params}",False)
        # self.app_debug_print(f"\n\n step 0 head >>>> sys_organization_id : {sys_organization_id}",False)
        # Extract default values from query parameters
        skip_recursive_field = query_params.get('skip_recursive_field',False)
        # parent_field = f"{model_name}_id"

        # handle hardcode_filter_on__rbac_role_id__filtered_by__cfg_organism_chart_id
        hard_code_filter = {}
        field_with_hardcode_filter = {}
        for key, value in query_params.items():
            if key.startswith("hardcode_filter_on__"):
                # Extract the field names after hardcode_filter_on__ and filtered_by__
                parts = key.split("__filtered_by__")
                if len(parts) == 2:
                    filter_field = parts[0].replace("hardcode_filter_on__", "")
                    filtered_by_field = parts[1]
                    field_with_hardcode_filter[filter_field] = True
                    # Update hard_code_filter with the filtered_by field value
                    if str(filtered_by_field).endswith('_id'):
                        hard_code_filter[f'{filtered_by_field}'] = None if value == 'none' else ObjectId(str(value))
                    else:
                        hard_code_filter[f'{filtered_by_field}'] = None if value == 'none' else value

        self.app_debug_print(f"\n\n hard_code_filter >>>> : {hard_code_filter}\n\n\n\n\n",False)

        default_values = {
            key[len("default__"):]: value
            for key, value in query_params.items()
            if key.startswith("default__")
        }
        default_values[parent_field] = parent_value
        self.app_debug_print(f"\n\n before >>>> parent_field : {parent_field} default_values : {default_values}\n\n\n\n",True)
        constant_values = {
            key[len("constant_value__"):]: value
            for key, value in query_params.items()
            if key.startswith("constant_value__")
        }
        nullable_values = {
            key[len("nullable_value__"):]: value
            for key, value in query_params.items()
            if key.startswith("nullable_value__")
        }

        hidde_on_view_values = {
            key[len("hidde_on_view__"):]: value
            for key, value in query_params.items()
            if key.startswith("hidde_on_view__")
        }


        self.app_debug_print(f"\n\n after >>>> default_values : {default_values}",False)

        self.app_debug_print(f"\n\n default_values >>>> : {default_values}",True)
        for field_name, field_meta in schema.items():
            # Determine if the field should be excluded
            self.app_debug_print(f"\n\n step 4 head >>>> : {field_name}",False)
            # if skip_recursive_field == True and field_name == parent_field:
            #     continue

            has_default_data_source = False,
            default_data_source = [],
            if field_name in default_data_sources:
                has_default_data_source = True
                default_data_source = default_data_sources[field_name]

            additional_head = field_meta.get('extra_metas',{}).get("additional_head",'')
            self.app_debug_print(f"\n\n [field_name] : {field_name} additional_headd >>>> : {additional_head}",False)
            self.app_debug_print(f"\n\n [field_name] : {field_name} default_values >>>> : {default_values}",True)
            if additional_head:
                try:
                    collection_key = CollectionKey(additional_head)
                    model_class, model_name = self.get_model_from_collection_key(
                        collection_key,
                        endpoint_call=True  # Enforce API access control
                    )
                    schema_extra = model_class.model_json_schema().get("properties", {})
                    additional_head_result = await self.transform_schema_to_head(schema=schema_extra,
                        model_name=model_name,
                        accept_language=accept_language,
                        exclude_fields=exclude_fields,
                        force_include_fields=force_include_fields,
                        is_organization_head=is_organization_head,
                        sys_organization_id=sys_organization_id,
                        query_params=query_params,
                        parent_field=parent_field,
                        parent_child_head=parent_child_head,
                        # skip_recursive_fields=True
                    )
                    transformed= {
                        **transformed,
                        **additional_head_result
                    }
                except Exception as e:
                    self.app_debug_print(f"Error fetching additional hfead >'{field_name}': {e}",False)


            is_excluded = (
                (field_name in exclude_fields and field_name not in default_values)
                or (field_name in {'is_activated',"_id", "identifier", "translations"})
                or (field_name in {'updated_at','created_at','created_by_id','soft_deleted_by_id','soft_deleted_at','soft_deleted','multiple_validation_status','multiple_validated_at'})
                or (field_meta.get("exclude_from_head", False) and field_name not in default_values)
            )
            self.app_debug_print(f"\n\n step is_excluded head : {is_excluded}",False)
            # Override exclusions if the field is in force_include_fields
            if is_excluded and field_name not in force_include_fields:
                continue
            self.app_debug_print(f"\n\n step 5 head",)
            self.app_debug_print(f"\n\n step force_include_fields head : {force_include_fields}",False)
            # Extract metadata, provide defaults if missing
            data_type = field_meta.get("data_type", {"is_unknown": True})
            field_extra_metas = field_meta.get("extra_metas", {"is_unknown": True})
            constraints = []
            self.app_debug_print(f"\n\n field_extra_metas : {field_extra_metas}",)
            extra_metas = {
                **field_extra_metas
            }

            if field_name in default_values:
                self.app_debug_print(f"\n\n step > head default >>  [{field_name}] : {default_values[field_name]}",True)
                # Parse the default value and additional metadata if provided
                default_value = default_values[field_name]
                extra_metas.update({
                    "has_default_value": True,
                    "skip_on_view": True,  # Example of additional metadata
                })
            else:
                default_value = None

            if field_name in constant_values:
                self.app_debug_print(f"\n\n step > head [{field_name}] : {default_values}",False)
                # Parse the default value and additional metadata if provided
                default_value = constant_values[field_name]
                extra_metas.update({
                    "has_default_value": True,
                })

            if field_name in nullable_values:
                self.app_debug_print(f"\n\n step > head [{field_name}] : {default_values}",False)
                # Parse the default value and additional metadata if provided
                default_value = None # nullable_values[field_name]
                extra_metas.update({
                    "has_default_value": True,
                    "skip_on_view": True,
                })

            if field_name in hidde_on_view_values:
                extra_metas.update({
                    "skip_on_view": True,
                })

            # Handle constraints directly from the field metadata extra
            if field_meta.get("may_have_translation"):
                constraints.append({"may_have_translation": True})
            if field_meta.get("to_be_translated_in_front"):
                constraints.append({"to_be_translated_in_front": True})
            if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}" in field_extra_metas:
                extra_metas.update({
                    "has_min_length": True,
                    "min_length": field_extra_metas[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}"]
                })
            if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}" in field_extra_metas:
                extra_metas.update({
                    "has_max_length": True,
                    "max_length": field_extra_metas[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}"]
                })
            if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}" in field_extra_metas:
                extra_metas.update({
                    "is_required": field_extra_metas["is_required"]
                })
            if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.PATTERN.value}" in field_meta:
                constraints.append({"has_regex": True, "regex": field_meta[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.PATTERN.value}"]})
            if field_name in schema.get("required", []):
                constraints.append({"is_required": True})

            # Get field display title with translation
            try:
                display_title = await translation_service.get_static_fields_translation(
                    property_name=field_name,
                    accept_language=accept_language,
                )
            except Exception as e:
                self.app_debug_print(f"Translation error for field '{field_name}': {e}",True)
                display_title = field_meta.get("title", field_name.replace("_", " ").title())

            if not display_title:
                display_title = field_meta.get("title", field_name.replace("_", " ").title())

            # Handle is_select for data_list and data_source
            data_list = []
            data_source = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}")  # Extract data_source from json_schema_extra
            join_organization_query = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}",False)  # Extract data_source from json_schema_extra
            join_profil_or_organization_query = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.JOIN_PROFIL_OR_ORGANIZATION_QUERY.value}",False)  # Extract data_source from json_schema_extra
            # self.app_debug_print(f" data_type : {data_type.get(f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}")}")

            # CASCADE
            cascade_model_name = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}")
            cascade_data = []
            # Add transformed field metadata
            enum_class = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}")

            self.app_debug_print(f"\n\n >>>| PARENT data_type.get('{EGLOBAL_DATA_TYPE.IS_CASCADE.value}') >>> :{ data_type.get(f'{EGLOBAL_DATA_TYPE.IS_CASCADE.value}')} | {data_type} | cascade_model_name : {cascade_model_name}")
            if data_type.get(f'{EGLOBAL_DATA_TYPE.IS_CASCADE.value}') is True and cascade_model_name and field_name != f"{parent_field}" and field_name not in default_values:

                try:
                    # collectionKey = self.get_collection_key_from_model_name(cascade_model_name)
                    # Fetch data from the data_source collection
                    self.app_debug_print(f"\n\n >>> {EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value} :{join_organization_query} | | join_profil_or_organization_query : {join_profil_or_organization_query}")
                    query = {}
                    if join_organization_query == True:
                        query={
                            **query,
                            "filter__sys_organization_id":str(sys_organization_id)
                        }
                    if join_profil_or_organization_query == True:
                        # TODO: GET ORGANIZATION
                        organization = await self.fetch_native_query_one_from_collection(
                            collection_key=CollectionKey.SYS_ORGANIZATION,
                            output_data_type=OutputDataType.DEFAULT,
                            accept_language=accept_language,
                            native_query={
                                "_id": ObjectId(sys_organization_id)
                            }
                        )
                        # TODO: GET PROFIL
                        query={
                            "$or":[
                                {
                                    **query,
                                    "filter__sys_organization_id":str(sys_organization_id)
                                },
                                {
                                    **query,
                                    "filter__rbac_profile_id":str(organization['rbac_profile_id']) if organization else None
                                }
                            ]
                        }
                    cascade_data = await self.fetch_data_from_collection(
                        collection_key=CollectionKey(cascade_model_name),
                        output_data_type=OutputDataType.CASCADE.value,
                        all_data=True,
                        query=query,
                        accept_language=accept_language
                    )
                    transformed[field_name] = {
                        "property_name": field_name,
                        "display_title": display_title,
                        "default_value": default_value,
                        "data_type": data_type,
                        "constraints": constraints,
                        "extra_metas": extra_metas,
                        "data_source": field_meta.get("data_source"),
                        "data_list": cascade_data,
                    }
                except Exception as e:
                    self.app_debug_print(f"Error fetching data for >>'{field_name}': {e}")
            elif data_type.get(f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}") and data_source:
                try:

                    query = {
                        "is_activated":True
                    }
                    if join_organization_query == True:
                        query={
                            **query,
                            "sys_organization_id":ObjectId(sys_organization_id),
                        }
                    if field_name in field_with_hardcode_filter:
                        query={
                            **query,
                            **hard_code_filter
                        }
                    if join_profil_or_organization_query == True:
                        # TODO: GET ORGANIZATION
                        organization = await self.fetch_native_query_one_from_collection(
                            collection_key=CollectionKey.SYS_ORGANIZATION,
                            output_data_type=OutputDataType.DEFAULT,
                            accept_language=accept_language,
                            native_query={
                                "_id": ObjectId(sys_organization_id)
                            }
                        )

                        query={
                            "$or":[
                                {
                                    **query,
                                    "sys_organization_id":ObjectId(sys_organization_id)
                                },
                                {
                                    **query,
                                    "rbac_profile_id":ObjectId(organization['rbac_profile_id']) if organization else None
                                }
                            ]
                        }
                    self.app_debug_print(f"\n\n >>> query :{query} | | join_profil_or_organization_query : {join_profil_or_organization_query}",True)
                    # Fetch data from the data_source collection
                    input_select_list = await self.fetch_native_query_data_from_collection(
                        collection_key=CollectionKey(data_source),
                        output_data_type=OutputDataType.INPUT_SELECT,
                        all_data=True,
                        native_query=query,
                        accept_language=accept_language
                    )
                    # Filter out None values and ensure we have a valid list
                    if input_select_list is None:
                        input_select_list = []
                    elif isinstance(input_select_list, list):
                        input_select_list = [item for item in input_select_list if item is not None]
                    self.app_debug_print(f"Query: {query}, Result count: {len(input_select_list) if isinstance(input_select_list, list) else 'not a list'}", True)
                    if has_default_data_source == True:
                        transformed[field_name] = {
                            "property_name": field_name,
                            "display_title": display_title,
                            "default_value": default_value,
                            "data_type": data_type,
                            "constraints": constraints,
                            "extra_metas": extra_metas,
                            "data_source": field_meta.get("data_source"),
                            "data_list": default_data_source,
                        }
                    else:
                        transformed[field_name] = {
                            "property_name": field_name,
                            "display_title": display_title,
                            "default_value": default_value,
                            "data_type": data_type,
                            "constraints": constraints,
                            "extra_metas": extra_metas,
                            "data_source": field_meta.get("data_source"),
                            "data_list": input_select_list if input_select_list else  []
                        }
                except Exception as e:
                    self.app_debug_print(f"Error fetching data for >'{field_name}': {e}",True)

            elif data_type.get(f"{EGLOBAL_DATA_TYPE.IS_AMOUNT.value}"):
                try:
                    currency_data_source = field_extra_metas.get("currency_data_source")
                    currency_props = field_extra_metas.get("currency_props")
                    self.app_debug_print(f" currency_data_source : {currency_data_source} currency_props : {currency_props}",False)
                    self.app_debug_print(f" currency_data_source : {currency_data_source} currency_props : {currency_props}",False)
                    query = {}
                    if join_organization_query:
                        query={
                            **query,
                            "filter__sys_organization_id":str(sys_organization_id)
                        }
                    # Fetch data from the data_source collection
                    input_select_list = await self.fetch_data_from_collection(
                        collection_key=CollectionKey(currency_data_source),
                        output_data_type=OutputDataType.INPUT_SELECT,
                        all_data=True,
                        query=query,
                        accept_language=accept_language
                    )
                    if has_default_data_source == True:
                        transformed[field_name] = {
                            "property_name": field_name,
                            "display_title": display_title,
                            "default_value": default_value,
                            "data_type": data_type,
                            "constraints": constraints,
                            "extra_metas": {
                                **field_extra_metas,
                                "currency_props":currency_props,
                            },
                            "data_source": field_meta.get("data_source"),
                            "data_list": default_data_source,
                        }
                    else:
                        transformed[field_name] = {
                            "property_name": field_name,
                            "display_title": display_title,
                            "default_value": default_value,
                            "data_type": data_type,
                            "constraints": constraints,
                            "extra_metas": extra_metas,
                            "data_source": field_meta.get("data_source"),
                            "data_list": input_select_list
                        }
                except Exception as e:
                    self.app_debug_print(f"Error fetching data for >'{field_name}': {e}",True)
            elif data_type.get(f'{EGLOBAL_DATA_TYPE.IS_ENUM.value}') and enum_class:
                try:
                    self.app_debug_print(f"fetching data for '{field_name}'",False)
                    self.app_debug_print(f"fetching enum_class for '{enum_class}'",False)
                    inner_data_list = TranslationService.get_enum_translated_data_list(enum_class,field_name,accept_language)
                    self.app_debug_print(f"\n\nfetching inner_data_list for '{inner_data_list}' \n\n\n",False)
                    excluded_keys = field_extra_metas.get("except_keys_on_head","") # "key_1,key_2"
                    self.app_debug_print(f"\n\nfetching excluded_keys for '{excluded_keys}' \n\n\n",False)
                    excluded_set = set(excluded_keys.split(","))
                    filtered_data = [item for item in inner_data_list if item["id"] not in excluded_set]
                    transformed[field_name] = {
                        "property_name": field_name,
                        "display_title": display_title,
                        "default_value": default_value,
                        "data_type": data_type,
                        "constraints": constraints,
                        "extra_metas": extra_metas,
                        "data_source": field_meta.get("data_source"),
                        "data_list": filtered_data,
                    }
                except Exception as e:
                    self.app_debug_print(f"Error fetching is_enum for >>'{field_name}': {e}",True)
            else :
                transformed[field_name] = {
                    "property_name": field_name,
                    "display_title": display_title,
                    "default_value": default_value,
                    "data_type": data_type,
                    "constraints": constraints,
                    "extra_metas": extra_metas,
                    "data_source": field_meta.get("data_source"),
                    "data_list": [],
                }
        return transformed

    async def transform_schema_to_update_child_head(
            self,
            schema: dict,
            model_name: str,
            accept_language: str = DEFAULT_LANGUAGE,
            exclude_fields: list = None,
            force_include_fields: list = [],
            is_organization_head: bool = False,
            sys_organization_id: dict = None,
            query_params: dict = None,  # Add query parameters
            parent_field: str = None,  # Add query parameters
            item_data: Any = None,
            parent_child_head: EParentChildHead = EParentChildHead.NO_SPECIFICATION.value,  # Add query parameters
        ) -> dict:
            """
            Transform schema metadata into the required format for the head.

            Args:
                schema (dict): Schema properties from the model.
                accept_language (str): Language code for translations.
                exclude_fields (list): List of fields to exclude from the head.
                force_include_fields (list): List of fields to forcefully include, overriding exclusions.
                item_data (Any): Data containing default values for fields.

            Returns:
                dict: Transformed metadata with populated data_type, constraints, and additional keys.
            """
            # Import TranslationService lazily inside the method to avoid circular imports
            from app.modules.core.services.translation.translation_service import TranslationService
            translation_service = TranslationService()

            transformed = {}
            exclude_fields = exclude_fields or []
            force_include_fields = force_include_fields or []
            query_params = query_params or {}
            self.app_debug_print(f"\n\n step 0 head >>>> query_params : {query_params}", False)
            # Extract default values from query parameters
            skip_recursive_field = query_params.get('skip_recursive_field', False)
            parent_field = f"{model_name}_id"
            self.app_debug_print(f"\n\n step 0 head parent_field: {parent_field}", False)

            # handle hardcode_filter_on__rbac_role_id__filtered_by__cfg_organism_chart_id
            hard_code_filter = {}
            field_with_hardcode_filter = {}
            for key, value in query_params.items():
                if key.startswith("hardcode_filter_on__"):
                    # Extract the field names after hardcode_filter_on__ and filtered_by__
                    parts = key.split("__filtered_by__")
                    if len(parts) == 2:
                        filter_field = parts[0].replace("hardcode_filter_on__", "")
                        filtered_by_field = parts[1]
                        field_with_hardcode_filter[filter_field] = True
                        # Update hard_code_filter with the filtered_by field value
                        if str(filtered_by_field).endswith('_id'):
                            hard_code_filter[f'{filtered_by_field}'] = None if value == 'none' else ObjectId(str(value))
                        else:
                            hard_code_filter[f'{filtered_by_field}'] = None if value == 'none' else value

            self.app_debug_print(f"\n\n hard_code_filter >>>> : {hard_code_filter}\n\n\n\n\n",False)

            default_values = {
                key[len("default__"):]: value
                for key, value in query_params.items()
                if key.startswith("default__")
            }

            constant_values = {
                key[len("constant_value__"):]: value
                for key, value in query_params.items()
                if key.startswith("constant_value__")
            }
            nullable_values = {
                key[len("nullable_value__"):]: value
                for key, value in query_params.items()
                if key.startswith("nullable_value__")
            }

            hidde_on_view_values = {
                key[len("hidde_on_view__"):]: value
                for key, value in query_params.items()
                if key.startswith("hidde_on_view__")
            }
            for field_name, field_meta in schema.items():
                # Determine if the field should be excluded
                self.app_debug_print(f"\n\n field name >>>> : {field_name}", False)
                self.app_debug_print(f"\n\n skip_recursive_field >>>> : {skip_recursive_field}", False)

                if field_name == 'sys_organization_id' and is_organization_head:
                    continue
                if skip_recursive_field:
                    continue

                additional_head = field_meta.get('extra_metas', {}).get("additional_head", '')
                self.app_debug_print(f"\n\n [field_name] : {field_name} additional_headd >>>> : {additional_head}", False)
                if additional_head:
                    try:
                        collection_key = CollectionKey(additional_head)
                        model_class, model_name = self.get_model_from_collection_key(
                            collection_key,
                            endpoint_call=True  # Enforce API access control
                        )
                        schema_extra = model_class.model_json_schema().get("properties", {})
                        additional_head_result = await self.transform_schema_to_head(
                            schema=schema_extra,
                            model_name=model_name,
                            accept_language=accept_language,
                            exclude_fields=exclude_fields,
                            force_include_fields=force_include_fields,
                            is_organization_head=is_organization_head,
                            sys_organization_id=sys_organization_id,
                            query_params=query_params,
                            parent_field=parent_field,
                            parent_child_head=parent_child_head,
                        )
                        transformed = {
                            **transformed,
                            **additional_head_result
                        }
                    except Exception as e:
                        self.app_debug_print(f"Error fetching additional head >'{field_name}': {e}", False)


                is_excluded = (
                    (field_name in exclude_fields and field_name not in default_values)
                    or (field_name in {'is_activated',"_id", "identifier", "translations"})
                    or (field_name in {'updated_at','created_at','created_by_id','soft_deleted_by_id','soft_deleted_at','soft_deleted','multiple_validation_status','multiple_validated_at'})
                    or field_meta.get("exclude_from_update_head", False) and field_name not in default_values
                    # or (field_meta.get("exclude_from_head", False) and field_name not in default_values)
                )
                # Override exclusions if the field is in force_include_fields
                if is_excluded and field_name not in force_include_fields:
                    continue
                self.app_debug_print(f"\n\n step 5 head",)
                # Extract metadata, provide defaults if missing
                data_type = field_meta.get("data_type", {"is_unknown": True})
                field_extra_metas = field_meta.get("extra_metas", {"is_unknown": True})
                constraints = []
                self.app_debug_print(f"\n\n field_extra_metas : {field_extra_metas}",)
                self.app_debug_print(f"\n\n is_excluded : {exclude_fields}", False)
                self.app_debug_print(f"\n\n force_include_fields : {exclude_fields}", False)
                extra_metas = {}

                self.app_debug_print(f"\n\n [field_name] : {field_name}", False)
                if field_name == f"{parent_field}":
                    self.app_debug_print(f"\n\n step > head [{field_name}] : {default_values}", False)

                # Determine default value from query parameters or parent field
                if field_name in default_values:
                    self.app_debug_print(f"\n\n step > head [{field_name}] from default_values: {default_values[field_name]}", False)
                    default_value = default_values[field_name]
                    extra_metas.update({
                        "has_default_value": True,
                        "skip_on_view": True,  # Example of additional metadata
                    })

                elif field_name == f"{parent_field}":
                    # Try to get parent's default value from item_data if available
                    parent_value = item_data.get(parent_field) if item_data else None
                    self.app_debug_print(f"\n\n [field_name] == [parent_field] ----> {True}  parent_value = {parent_value}", False)
                    default_value = parent_value
                    extra_metas.update({
                        "has_default_value": True,
                        "skip_on_view": True,  # Example of additional metadata
                    })
                else:
                    default_value = None

                if field_name in constant_values:
                    self.app_debug_print(f"\n\n step > head [{field_name}] : {default_values}",False)
                    # Parse the default value and additional metadata if provided
                    default_value = constant_values[field_name]
                    extra_metas.update({
                        "has_default_value": True,
                    })

                if field_name in nullable_values:
                    self.app_debug_print(f"\n\n step > head [{field_name}] : {default_values}",False)
                    # Parse the default value and additional metadata if provided
                    default_value = None # nullable_values[field_name]
                    extra_metas.update({
                        "has_default_value": True,
                        "skip_on_view": True,
                    })

                if field_name in hidde_on_view_values:
                    extra_metas.update({
                        "skip_on_view": True,
                    })

                # Override with item_data value if provided for every field
                if item_data is not None and field_name in item_data:
                    default_value = item_data[field_name]

                self.app_debug_print(f"\n\n step 6 head",)
                # Handle constraints directly from the field metadata extra
                if field_meta.get("may_have_translation"):
                    constraints.append({"may_have_translation": True})
                if field_meta.get("to_be_translated_in_front"):
                    constraints.append({"to_be_translated_in_front": True})
                if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}" in field_extra_metas:
                    extra_metas.update({
                        "has_min_length": True,
                        "min_length": field_extra_metas[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}"]
                    })
                if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}" in field_extra_metas:
                    extra_metas.update({
                        "has_max_length": True,
                        "max_length": field_extra_metas[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}"]
                    })
                if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}" in field_extra_metas:
                    extra_metas.update({
                        "is_required": field_extra_metas[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}"]
                    })
                if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.PATTERN.value}" in field_meta:
                    constraints.append({"has_regex": True, "regex": field_meta[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.PATTERN.value}"]})
                if field_name in schema.get("required", []):
                    constraints.append({"is_required": True})

                # Get field display title with translation
                try:
                    display_title = await translation_service.get_static_fields_translation(
                        property_name=field_name,
                        accept_language=accept_language,
                    )
                except Exception as e:
                    print(f"Translation error for field '{field_name}': {e}")
                    display_title = field_meta.get("title", field_name.replace("_", " ").title())

                if not display_title:
                    display_title = field_meta.get("title", field_name.replace("_", " ").title())

                # Handle is_select for data_list and data_source
                data_list = []
                data_source = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}")  # Extract data_source from json_schema_extra
                join_organization_query = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}")  # Extract data_source from json_schema_extra
                self.app_debug_print(f" {EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value} : {join_organization_query} data_source : {data_source}", False)
                join_profil_or_organization_query = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.JOIN_PROFIL_OR_ORGANIZATION_QUERY.value}",False)
                # self.app_debug_print(f' data_type : {data_type.get(f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}")}', False)
                if data_type.get(f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}") and data_source:
                    try:
                        query = {}
                        if join_organization_query == True:
                            query={
                                **query,
                                "sys_organization_id":ObjectId(sys_organization_id)
                            }
                        if field_name in field_with_hardcode_filter:
                            query={
                                **query,
                                **hard_code_filter
                            }
                        if join_profil_or_organization_query == True:
                            # TODO: GET ORGANIZATION
                            organization = await self.fetch_native_query_one_from_collection(
                                collection_key=CollectionKey.SYS_ORGANIZATION,
                                output_data_type=OutputDataType.DEFAULT,
                                accept_language=accept_language,
                                native_query={
                                    "_id": ObjectId(sys_organization_id)
                                }
                            )

                            query={
                                "$or":[
                                    {
                                        **query,
                                        "sys_organization_id":ObjectId(sys_organization_id)
                                    },
                                    {
                                        **query,
                                        "rbac_profile_id":ObjectId(organization['rbac_profile_id']) if organization else None
                                    }
                                ]
                            }
                        # Fetch data from the data_source collection
                        self.app_debug_print(f"\n\n\n\n query >> : {query} data_source : {data_source}\n\n\n", False)
                        input_selects = await self.fetch_native_query_data_from_collection(
                            collection_key=CollectionKey(data_source),
                            output_data_type=OutputDataType.INPUT_SELECT.value,
                            all_data=True,
                            native_query=query,
                            accept_language=accept_language
                        )
                        self.app_debug_print(f"fetching data for {field_name} : '{input_selects}'", False)
                        data_list = input_selects
                        transformed[field_name] = {
                            "property_name": field_name,
                            "display_title": display_title,
                            "default_value": default_value,
                            "data_type": data_type,
                            "constraints": constraints,
                            "extra_metas": extra_metas,
                            "data_source": field_meta.get("data_source"),
                            "data_list": data_list,
                        }
                    except Exception as e:
                        self.app_debug_print(f"Error fetching data for >'{field_name}': {e}", False)
                # CASCADE
                cascade_model_name = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}")
                cascade_data = []
                # Add transformed field metadata
                enum_class = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}")
                if data_type.get(f'{EGLOBAL_DATA_TYPE.IS_CASCADE.value}') is True and cascade_model_name and field_name != f"{parent_field}" and field_name not in default_values:
                    try:
                        collectionKey = CollectionKey(cascade_model_name) # self.get_collection_key_from_model_name(cascade_model_name)
                        # Fetch data from the data_source collection
                        cascade_data = await self.fetch_data_from_collection(
                            collection_key=collectionKey,
                            output_data_type=OutputDataType.CASCADE.value,
                            all_data=True,
                            query={},
                            accept_language=accept_language
                        )
                        self.app_debug_print(f"fetching data for '{field_name}'", False)
                        data_list = cascade_data
                    except Exception as e:
                        self.app_debug_print(f"Error fetching data for >>'{field_name}': {e}")

                elif data_type.get(f'{EGLOBAL_DATA_TYPE.IS_ENUM.value}') and enum_class:
                    try:
                        self.app_debug_print(f"fetching data for '{field_name}'", False)
                        self.app_debug_print(f"fetching enum_class for '{enum_class}'", False)
                        inner_data_list = TranslationService.get_enum_translated_data_list(enum_class, field_name, accept_language)
                        self.app_debug_print(f"\n\nfetching inner_data_list for '{inner_data_list}' \n\n\n", False)
                        transformed[field_name] = {
                            "property_name": field_name,
                            "display_title": display_title,
                            "default_value": default_value,
                            "data_type": data_type,
                            "constraints": constraints,
                            "extra_metas": extra_metas,
                            "data_source": field_meta.get("data_source"),
                            "data_list": inner_data_list,
                        }
                    except Exception as e:
                        self.app_debug_print(f"Error fetching is_enum for >>'{field_name}': {e}", False)
                elif data_type.get(f'{EGLOBAL_DATA_TYPE.IS_CASCADE.value}'):
                    collectionKey = CollectionKey(cascade_model_name) # self.get_collection_key_from_model_name(cascade_model_name)
                    # Fetch data from the data_source collection
                    query = {}
                    if join_organization_query == True:
                        query={
                            **query,
                            "sys_organization_id":ObjectId(sys_organization_id)
                        }
                    if field_name in field_with_hardcode_filter:
                        query={
                            **query,
                            **hard_code_filter
                        }
                    if join_profil_or_organization_query == True:
                        # TODO: GET ORGANIZATION
                        organization = await self.fetch_native_query_one_from_collection(
                            collection_key=CollectionKey.SYS_ORGANIZATION,
                            output_data_type=OutputDataType.DEFAULT,
                            accept_language=accept_language,
                            native_query={
                                "_id": ObjectId(sys_organization_id)
                            }
                        )

                        query={
                            "$or":[
                                {
                                    **query,
                                    "sys_organization_id":ObjectId(sys_organization_id)
                                },
                                {
                                    **query,
                                    "rbac_profile_id":ObjectId(str(organization['rbac_profile_id'])) if organization else None
                                }
                            ]
                        }
                    # Fetch data from the data_source collection
                    self.app_debug_print(f"\n\n\n\n query >> : {query} data_source : {data_source}\n\n\n", False)
                    cascade_data = await self.fetch_native_query_data_from_collection(
                        collection_key=collectionKey,#CollectionKey(data_source),
                        output_data_type=OutputDataType.CASCADE.value,
                        all_data=True,
                        native_query=query,
                        accept_language=accept_language
                    )
                    # cascade_data = await self.fetch_data_from_collection(
                    #     collection_key=collectionKey,
                    #     output_data_type=OutputDataType.CASCADE.value,
                    #     all_data=True,
                    #     query={},
                    #     accept_language=accept_language
                    # )
                    transformed[field_name] = {
                        "property_name": field_name,
                        "display_title": display_title,
                        "default_value": default_value,
                        "data_type": data_type,
                        "constraints": constraints,
                        "extra_metas": extra_metas,
                        "data_source": field_meta.get("data_source"),
                        "data_list": cascade_data,
                    } 
                else:
                    transformed[field_name] = {
                        "property_name": field_name,
                        "display_title": display_title,
                        "default_value": default_value,
                        "data_type": data_type,
                        "constraints": constraints,
                        "extra_metas": extra_metas,
                        "data_source": field_meta.get("data_source"),
                        "data_list": [],
                    }
                if is_organization_head and sys_organization_id:
                    transformed['sys_organization_id'] = {
                        "property_name": 'sys_organization_id',
                        "display_title": "Organization",
                        "default_value": sys_organization_id,
                        "data_type": {"is_string": True},
                        "constraints": constraints,
                        "extra_metas": {
                            'skip_on_view': True,
                            'has_default_value': True
                        },
                        "data_source": [],
                        "data_list": [],
                    }

            return transformed
    async def transform_schema_to_update_head(
            self,
            schema: dict,
            model_name: str,
            accept_language: str = DEFAULT_LANGUAGE,
            exclude_fields: list = None,
            force_include_fields: list = [],
            is_organization_head: bool = False,
            sys_organization_id: dict = None,
            query_params: dict = None,  # Add query parameters
            parent_field: str = None,  # Add query parameters
            item_data: Any = None,
            parent_child_head: EParentChildHead = EParentChildHead.NO_SPECIFICATION.value,  # Add query parameters
        ) -> dict:
            try:
                """
                Transform schema metadata into the required format for the head.

                Args:
                    schema (dict): Schema properties from the model.
                    accept_language (str): Language code for translations.
                    exclude_fields (list): List of fields to exclude from the head.
                    force_include_fields (list): List of fields to forcefully include, overriding exclusions.
                    item_data (Any): Data containing default values for fields.

                Returns:
                    dict: Transformed metadata with populated data_type, constraints, and additional keys.
                """
                # Import TranslationService lazily inside the method to avoid circular imports
                from app.modules.core.services.translation.translation_service import TranslationService
                translation_service = TranslationService()

                transformed = {}
                exclude_fields = exclude_fields or []
                force_include_fields = force_include_fields or []
                query_params = query_params or {}
                self.app_debug_print(f"\n\n step 0 head >>>> query_params : {query_params}", False)
                # Extract default values from query parameters
                skip_recursive_field = query_params.get('skip_recursive_field', False)
                parent_field = f"{model_name}_id"
                self.app_debug_print(f"\n\n step 0 head parent_field: {parent_field}", False)

                # handle hardcode_filter_on__rbac_role_id__filtered_by__cfg_organism_chart_id
                hard_code_filter = {}
                field_with_hardcode_filter = {}
                for key, value in query_params.items():
                    if key.startswith("hardcode_filter_on__"):
                        # Extract the field names after hardcode_filter_on__ and filtered_by__
                        parts = key.split("__filtered_by__")
                        if len(parts) == 2:
                            filter_field = parts[0].replace("hardcode_filter_on__", "")
                            filtered_by_field = parts[1]
                            field_with_hardcode_filter[filter_field] = True
                            # Update hard_code_filter with the filtered_by field value
                            if str(filtered_by_field).endswith('_id'):
                                hard_code_filter[f'{filtered_by_field}'] = None if value == 'none' else ObjectId(str(value))
                            else:
                                hard_code_filter[f'{filtered_by_field}'] = None if value == 'none' else value

                self.app_debug_print(f"\n\n hard_code_filter >>>> : {hard_code_filter}\n\n\n\n\n",False)

                default_values = {
                    key[len("default__"):]: value
                    for key, value in query_params.items()
                    if key.startswith("default__")
                }

                constant_values = {
                    key[len("constant_value__"):]: value
                    for key, value in query_params.items()
                    if key.startswith("constant_value__")
                }
                nullable_values = {
                    key[len("nullable_value__"):]: value
                    for key, value in query_params.items()
                    if key.startswith("nullable_value__")
                }

                hidde_on_view_values = {
                    key[len("hidde_on_view__"):]: value
                    for key, value in query_params.items()
                    if key.startswith("hidde_on_view__")
                }
                for field_name, field_meta in schema.items():
                    # Determine if the field should be excluded
                    self.app_debug_print(f"\n\n field name >>>> : {field_name}", False)
                    self.app_debug_print(f"\n\n skip_recursive_field >>>> : {skip_recursive_field}", False)

                    if field_name == 'sys_organization_id' and is_organization_head:
                        continue
                    if skip_recursive_field:
                        continue

                    additional_head = field_meta.get('extra_metas', {}).get("additional_head", '')
                    self.app_debug_print(f"\n\n [field_name] : {field_name} additional_headd >>>> : {additional_head}", False)
                    if additional_head:
                        try:
                            collection_key = CollectionKey(additional_head)
                            model_class, model_name = self.get_model_from_collection_key(
                                collection_key,
                                endpoint_call=True  # Enforce API access control
                            )
                            schema_extra = model_class.model_json_schema().get("properties", {})
                            additional_head_result = await self.transform_schema_to_head(
                                schema=schema_extra,
                                model_name=model_name,
                                accept_language=accept_language,
                                exclude_fields=exclude_fields,
                                force_include_fields=force_include_fields,
                                is_organization_head=is_organization_head,
                                sys_organization_id=sys_organization_id,
                                query_params=query_params,
                                parent_field=parent_field,
                                parent_child_head=parent_child_head,
                            )
                            transformed = {
                                **transformed,
                                **additional_head_result
                            }
                        except Exception as e:
                            self.app_debug_print(f"Error fetching additional head >'{field_name}': {e}", True)


                    is_excluded = (
                        (field_name in exclude_fields and field_name not in default_values)
                        or (field_name in {'is_activated',"_id", "identifier", "translations",'updated_at','created_at','created_by_id','soft_deleted_by_id','soft_deleted_at','soft_deleted','multiple_validation_status','multiple_validated_at'})
                        or field_meta.get("exclude_from_update_head", False) and field_name not in default_values
                        # or (field_meta.get("exclude_from_head", False) and field_name not in default_values)
                    )
                    # Override exclusions if the field is in force_include_fields
                    if is_excluded and field_name not in force_include_fields:
                        continue
                    self.app_debug_print(f"\n\n step 5 head",)
                    # Extract metadata, provide defaults if missing
                    data_type = field_meta.get("data_type", {"is_unknown": True})
                    field_extra_metas = field_meta.get("extra_metas", {"is_unknown": True})
                    constraints = []
                    self.app_debug_print(f"\n\n field_extra_metas : {field_extra_metas}",)
                    self.app_debug_print(f"\n\n is_excluded : {exclude_fields}", False)
                    self.app_debug_print(f"\n\n force_include_fields : {exclude_fields}", False)
                    extra_metas = {}

                    self.app_debug_print(f"\n\n [field_name] : {field_name}", False)
                    if field_name == f"{parent_field}":
                        self.app_debug_print(f"\n\n step > head [{field_name}] : {default_values}", False)

                    # Determine default value from query parameters or parent field
                    if field_name in default_values:
                        self.app_debug_print(f"\n\n step > head [{field_name}] from default_values: {default_values[field_name]}", False)
                        default_value = default_values[field_name]
                        extra_metas.update({
                            "has_default_value": True,
                            "skip_on_view": True,  # Example of additional metadata
                        })
                    elif field_name == f"{parent_field}":
                        # Try to get parent's default value from item_data if available
                        parent_value = item_data.get(parent_field) if item_data else None
                        self.app_debug_print(f"\n\n [field_name] == [parent_field] ----> {True}  parent_value = {parent_value}", False)
                        default_value = parent_value
                        extra_metas.update({
                            "has_default_value": True,
                            "skip_on_view": True,  # Example of additional metadata
                        })
                    else:
                        default_value = None

                    if field_name in constant_values:
                        self.app_debug_print(f"\n\n step > head [{field_name}] : {default_values}",False)
                        # Parse the default value and additional metadata if provided
                        default_value = constant_values[field_name]
                        extra_metas.update({
                            "has_default_value": True,
                        })

                    if field_name in nullable_values:
                        self.app_debug_print(f"\n\n step > head [{field_name}] : {default_values}",False)
                        # Parse the default value and additional metadata if provided
                        default_value = None # nullable_values[field_name]
                        extra_metas.update({
                            "has_default_value": True,
                            "skip_on_view": True,
                        })

                    if field_name in hidde_on_view_values:
                        extra_metas.update({
                            "skip_on_view": True,
                        })

                    # Override with item_data value if provided for every field
                    if item_data is not None and field_name in item_data:
                        default_value = item_data[field_name]

                    self.app_debug_print(f"\n\n step 6 head",True)
                    # Handle constraints directly from the field metadata extra
                    if field_meta.get("may_have_translation"):
                        constraints.append({"may_have_translation": True})
                    if field_meta.get("to_be_translated_in_front"):
                        constraints.append({"to_be_translated_in_front": True})
                    if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}" in field_extra_metas:
                        extra_metas.update({
                            "has_min_length": True,
                            "min_length": field_extra_metas[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}"]
                        })
                    if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}" in field_extra_metas:
                        extra_metas.update({
                            "has_max_length": True,
                            "max_length": field_extra_metas[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}"]
                        })
                    if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}" in field_extra_metas:
                        extra_metas.update({
                            "is_required": field_extra_metas[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}"]
                        })
                    if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.PATTERN.value}" in field_meta:
                        constraints.append({"has_regex": True, "regex": field_meta[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.PATTERN.value}"]})
                    if field_name in schema.get("required", []):
                        constraints.append({"is_required": True})

                    # Get field display title with translation
                    try:
                        display_title = await translation_service.get_static_fields_translation(
                            property_name=field_name,
                            accept_language=accept_language,
                        )
                    except Exception as e:
                        print(f"Translation error for field '{field_name}': {e}")
                        display_title = field_meta.get("title", field_name.replace("_", " ").title())

                    if not display_title:
                        display_title = field_meta.get("title", field_name.replace("_", " ").title())

                    # CASCADE
                    cascade_model_name = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}")
                    cascade_data = []
                    # Add transformed field metadata
                    enum_class = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}")

                    # Handle is_select for data_list and data_source
                    data_list = []
                    data_source = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}")  # Extract data_source from json_schema_extra
                    join_organization_query = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}")  # Extract data_source from json_schema_extra
                    self.app_debug_print(f" {EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value} : {join_organization_query} data_source : {data_source}", False)
                    join_profil_or_organization_query = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.JOIN_PROFIL_OR_ORGANIZATION_QUERY.value}",False)
                    self.app_debug_print(f" {EGLOBAL_EXTRA_METAS.JOIN_PROFIL_OR_ORGANIZATION_QUERY.value} : {join_profil_or_organization_query} data_source : {data_source}", False)
                    # self.app_debug_print(f' data_type : {data_type.get(f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}")}', False)
                    if data_type.get(f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}") and data_source:
                        try:
                            query = {}
                            if join_organization_query == True:
                                query={
                                    **query,
                                    "sys_organization_id":ObjectId(sys_organization_id)
                                }
                            if field_name in field_with_hardcode_filter:
                                query={
                                    **query,
                                    **hard_code_filter
                                }
                            if join_profil_or_organization_query == True:
                                # TODO: GET ORGANIZATION
                                organization = await self.fetch_native_query_one_from_collection(
                                    collection_key=CollectionKey.SYS_ORGANIZATION,
                                    output_data_type=OutputDataType.DEFAULT,
                                    accept_language=accept_language,
                                    native_query={
                                        "_id": ObjectId(sys_organization_id)
                                    }
                                )

                                query={
                                    "$or":[
                                        {
                                            **query,
                                            "sys_organization_id":ObjectId(sys_organization_id)
                                        },
                                        {
                                            **query,
                                            "rbac_profile_id":ObjectId(str(organization['rbac_profile_id'])) if organization else None
                                        }
                                    ]
                                }
                            # Fetch data from the data_source collection
                            self.app_debug_print(f"\n\n\n\n query >> : {query} data_source : {data_source}\n\n\n", False)
                            input_selects = await self.fetch_native_query_data_from_collection(
                                collection_key=CollectionKey(data_source),
                                output_data_type=OutputDataType.INPUT_SELECT.value,
                                all_data=True,
                                native_query=query,
                                accept_language=accept_language
                            )
                            self.app_debug_print(f"fetching data for {field_name} : {len(input_selects)} query for select : {query}", False)
                            self.app_debug_print(f"default {field_name} : {default_value}", False)
                            data_list = input_selects
                            fetched_data_source = None
                            if default_value:
                                single_input_select = await self.fetch_one_from_collection(
                                    collection_key=CollectionKey(data_source),
                                    output_data_type=OutputDataType.INPUT_SELECT.value,
                                    query={
                                        "filter___id":default_value
                                    },
                                    accept_language=accept_language
                                )
                                self.app_debug_print(f"default {field_name} fetched data source for select : {True if single_input_select is not None else False}", True)
                                if single_input_select is not None:
                                    fetched_data_source = single_input_select

                            transformed[field_name] = {
                                "property_name": field_name,
                                "display_title": display_title,
                                "default_value": default_value,
                                "data_type": data_type,
                                "constraints": constraints,
                                "extra_metas": extra_metas,
                                "data_source": fetched_data_source,
                                "data_list": data_list,
                            }
                        except Exception as e:
                            self.app_debug_print(f"Error fetching data for >'{field_name}': {e}", True)
                    elif data_type.get(f'{EGLOBAL_DATA_TYPE.IS_CASCADE.value}') is True and cascade_model_name and field_name != f"{parent_field}" and field_name not in default_values:
                        try:
                            collectionKey = CollectionKey(cascade_model_name) # self.get_collection_key_from_model_name(cascade_model_name)
                            # Fetch data from the data_source collection
                            query = {}
                            if join_organization_query == True:
                                query={
                                    **query,
                                    "sys_organization_id":ObjectId(sys_organization_id)
                                }
                            if field_name in field_with_hardcode_filter:
                                query={
                                    **query,
                                    **hard_code_filter
                                }
                            if join_profil_or_organization_query == True:
                                # TODO: GET ORGANIZATION
                                organization = await self.fetch_native_query_one_from_collection(
                                    collection_key=CollectionKey.SYS_ORGANIZATION,
                                    output_data_type=OutputDataType.DEFAULT,
                                    accept_language=accept_language,
                                    native_query={
                                        "_id": ObjectId(sys_organization_id)
                                    }
                                )

                                query={
                                    "$or":[
                                        {
                                            **query,
                                            "sys_organization_id":ObjectId(sys_organization_id)
                                        },
                                        {
                                            **query,
                                            "rbac_profile_id":ObjectId(str(organization['rbac_profile_id'])) if organization else None
                                        }
                                    ]
                                }
                            # Fetch data from the data_source collection
                            self.app_debug_print(f"\n\n\n\n query >> : {query} data_source : {data_source}\n\n\n", False)
                            cascade_data = await self.fetch_native_query_data_from_collection(
                                collection_key=collectionKey,#CollectionKey(data_source),
                                output_data_type=OutputDataType.CASCADE.value,
                                all_data=True,
                                native_query=query,
                                accept_language=accept_language
                            )
                            # cascade_data = await self.fetch_data_from_collection(
                            #     collection_key=collectionKey,
                            #     output_data_type=OutputDataType.CASCADE.value,
                            #     all_data=True,
                            #     query={},
                            #     accept_language=accept_language
                            # )
                            self.app_debug_print(f"fetching data for '{field_name}'", False)
                            data_list = cascade_data
                            transformed[field_name] = {
                                "property_name": field_name,
                                "display_title": display_title,
                                "default_value": default_value,
                                "data_type": data_type,
                                "constraints": constraints,
                                "extra_metas": extra_metas,
                                "data_source": field_meta.get("data_source"),
                                "data_list": inner_data_list,
                            }
                        except Exception as e:
                            self.app_debug_print(f"Error fetching data for >>'{field_name}': {e}")

                    elif data_type.get(f'{EGLOBAL_DATA_TYPE.IS_ENUM.value}') and enum_class:
                        try:
                            self.app_debug_print(f"fetching data for '{field_name}'", False)
                            self.app_debug_print(f"fetching enum_class for '{enum_class}'", False)
                            inner_data_list = TranslationService.get_enum_translated_data_list(enum_class, field_name, accept_language)
                            self.app_debug_print(f"\n\nfetching inner_data_list for '{inner_data_list}' \n\n\n", False)
                            transformed[field_name] = {
                                "property_name": field_name,
                                "display_title": display_title,
                                "default_value": default_value,
                                "data_type": data_type,
                                "constraints": constraints,
                                "extra_metas": extra_metas,
                                "data_source": field_meta.get("data_source"),
                                "data_list": inner_data_list,
                            }
                        except Exception as e:
                            self.app_debug_print(f"Error fetching is_enum for >>'{field_name}': {e}", False)
                    elif data_type.get(f'{EGLOBAL_DATA_TYPE.IS_CASCADE.value}'):
                        collectionKey = CollectionKey(cascade_model_name) # self.get_collection_key_from_model_name(cascade_model_name)
                        # Fetch data from the data_source collection
                        query = {}
                        if join_organization_query == True:
                            query={
                                **query,
                                "sys_organization_id":ObjectId(sys_organization_id)
                            }
                        if field_name in field_with_hardcode_filter:
                            query={
                                **query,
                                **hard_code_filter
                            }
                        if join_profil_or_organization_query == True:
                            # TODO: GET ORGANIZATION
                            organization = await self.fetch_native_query_one_from_collection(
                                collection_key=CollectionKey.SYS_ORGANIZATION,
                                output_data_type=OutputDataType.DEFAULT,
                                accept_language=accept_language,
                                native_query={
                                    "_id": ObjectId(sys_organization_id)
                                }
                            )

                            query={
                                "$or":[
                                    {
                                        **query,
                                        "sys_organization_id":ObjectId(sys_organization_id)
                                    },
                                    {
                                        **query,
                                        "rbac_profile_id":ObjectId(str(organization['rbac_profile_id'])) if organization else None
                                    }
                                ]
                            }
                        # Fetch data from the data_source collection
                        self.app_debug_print(f"\n\n\n\n query >> : {query} data_source : {data_source}\n\n\n", False)
                        cascade_data = await self.fetch_native_query_data_from_collection(
                            collection_key=collectionKey,#CollectionKey(data_source),
                            output_data_type=OutputDataType.CASCADE.value,
                            all_data=True,
                            native_query=query,
                            accept_language=accept_language
                        ) 
                        transformed[field_name] = {
                            "property_name": field_name,
                            "display_title": display_title,
                            "default_value": default_value,
                            "data_type": data_type,
                            "constraints": constraints,
                            "extra_metas": extra_metas,
                            "data_source": field_meta.get("data_source"),
                            "data_list": cascade_data,
                        }
                    else:
                        transformed[field_name] = {
                            "property_name": field_name,
                            "display_title": display_title,
                            "default_value": default_value,
                            "data_type": data_type,
                            "constraints": constraints,
                            "extra_metas": extra_metas,
                            "data_source": field_meta.get("data_source"),
                            "data_list": [],
                        }
                    if is_organization_head and sys_organization_id:
                        transformed['sys_organization_id'] = {
                            "property_name": 'sys_organization_id',
                            "display_title": "Organization",
                            "default_value": sys_organization_id,
                            "data_type": {"is_string": True},
                            "constraints": constraints,
                            "extra_metas": {
                                'skip_on_view': True,
                                'has_default_value': True
                            },
                            "data_source": [],
                            "data_list": [],
                        }

                return transformed
            except PermissionError as e:
                self.app_debug_print(f"\n\n\n ERROR HEAD UPDATE 1 : {e} \n\n\n",True)
                raise HTTPException(status_code=403, detail=str(e))
            except Exception as e:
                self.app_debug_print(f"\n\n\n ERROR 2 HEAD UPDATE : {e} \n\n\n",True)
                raise HTTPException(status_code=500, detail=str(e))

    async def transform_overview_data(
            self,
            schema: dict,
            model_name: str,
            accept_language: str = DEFAULT_LANGUAGE,
            exclude_fields: list = None,
            force_include_fields: list = [],
            is_organization_head: bool = False,
            sys_organization_id: dict = None,
            query_params: dict = None,  # Add query parameters
            parent_field: str = None,  # Add query parameters
            item_data: Any = None,
            parent_child_head: EParentChildHead = EParentChildHead.NO_SPECIFICATION.value,  # Add query parameters
        ) -> dict:
            """
            Transform schema metadata into the required format for the head.

            Args:
                schema (dict): Schema properties from the model.
                accept_language (str): Language code for translations.
                exclude_fields (list): List of fields to exclude from the head.
                force_include_fields (list): List of fields to forcefully include, overriding exclusions.
                item_data (Any): Data containing default values for fields.

            Returns:
                dict: Transformed metadata with populated data_type, constraints, and additional keys.
            """
            # Import TranslationService lazily inside the method to avoid circular imports
            from app.modules.core.services.translation.translation_service import TranslationService
            translation_service = TranslationService()

            transformed = {}
            exclude_fields = exclude_fields or []
            force_include_fields = force_include_fields or []
            query_params = query_params or {}
            self.app_debug_print(f"\n\n step 0 head >>>> item_data : {item_data}", False)
            self.app_debug_print(f"\n\n step 0 head >>>> query_params : {query_params}", False)
            # Extract default values from query parameters
            skip_recursive_field = query_params.get('skip_recursive_field', False)
            parent_field = f"{model_name}_id"
            self.app_debug_print(f"\n\n step 0 head parent_field: {parent_field}", False)


            for field_name, field_meta in schema.items():
                # Determine if the field should be excluded
                self.app_debug_print(f"\n\n field name >>>> : {field_name}", False)
                self.app_debug_print(f"\n\n skip_recursive_field >>>> : {skip_recursive_field}", False)
                field_extra_metas = field_meta.get("extra_metas", {"is_unknown": True})
                self.app_debug_print(f"\n\n FIELD : {field_name} field_extra_metas : {field_extra_metas}", False)
                display_on_overview = field_extra_metas.get("display_on_overview",False)
                if not display_on_overview:
                    continue
                if field_name == 'sys_organization_id' and is_organization_head:
                    continue
                if skip_recursive_field:
                    continue
                overview_data_type = field_meta.get("overview_data_type", {"is_unknown": True})
                self.app_debug_print(f"\n\n FIELD : {field_name} overview_data_type : {overview_data_type}", False)

                default_value = item_data.get(field_name) if item_data else None
                additional_head = field_meta.get('extra_metas', {}).get("additional_head", '')
                if additional_head:
                    self.app_debug_print(f"\n\n [field_name] : {field_name} additional_headd >>>> : {additional_head}", False)
                    try:
                        collection_key = CollectionKey(additional_head)
                        model_class, model_name = self.get_model_from_collection_key(
                            collection_key,
                            endpoint_call=True  # Enforce API access control
                        )
                        query = {
                            f"filter___id":default_value
                        }
                        self.app_debug_print(f"\n\n\n\n query >> : {query} data_source : {additional_head}\n\n\n", False)
                        data = await self.fetch_one_from_collection(
                            collection_key=collection_key,
                            output_data_type=OutputDataType.DEFAULT.value,
                            accept_language=accept_language,
                            query=query
                        )
                        self.app_debug_print(f"\n\n [field_name] : {field_name} data >>>> : {data}", False)
                        if not data:
                            continue
                        schema_extra = model_class.model_json_schema().get("properties", {})
                        additional_head_result = await self.transform_overview_data(
                            schema=schema_extra,
                            model_name=model_name,
                            accept_language=accept_language,
                            exclude_fields=exclude_fields,
                            force_include_fields=force_include_fields,
                            is_organization_head=is_organization_head,
                            sys_organization_id=sys_organization_id,
                            query_params=query_params,
                            item_data=data,
                            parent_field=parent_field,
                            parent_child_head=parent_child_head,
                        )
                        transformed = {
                            **transformed,
                            **additional_head_result
                        }
                    except Exception as e:
                        self.app_debug_print(f"Error fetching additional head >'{field_name}': {e}", False)

                self.app_debug_print(f"\n\n step 5 head",)
                # Extract metadata, provide defaults if missing
                # data_type = field_meta.get("data_type", {"is_unknown": True})



                constraints = []
                self.app_debug_print(f"\n\n field_extra_metas : {field_extra_metas}",)

                extra_metas = {}

                self.app_debug_print(f"\n\n [field_name] : {field_name}", False)
                # if field_name == f"{parent_field}":
                #     self.app_debug_print(f"\n\n step > head [{field_name}] : {default_values}", False)

                # Determine default value from query parameters or parent field
                if field_name == f"{parent_field}":
                    # Try to get parent's default value from item_data if available
                    parent_value = item_data.get(parent_field) if item_data else None
                    self.app_debug_print(f"\n\n [field_name] == [parent_field] ----> {True}  parent_value = {parent_value}", False)
                    default_value = parent_value
                    extra_metas.update({
                        "has_default_value": True,
                        "skip_on_view": True,  # Example of additional metadata
                    })
                else:
                    default_value = None

                # Override with item_data value if provided for every field
                if item_data is not None and field_name in item_data:
                    default_value = item_data[field_name]

                self.app_debug_print(f"\n\n step 6 head",)
                # Handle constraints directly from the field metadata extra
                if field_meta.get("may_have_translation"):
                    constraints.append({"may_have_translation": True})
                if field_meta.get("to_be_translated_in_front"):
                    constraints.append({"to_be_translated_in_front": True})
                if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}" in field_extra_metas:
                    extra_metas.update({
                        "has_min_length": True,
                        "min_length": field_extra_metas[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}"]
                    })
                if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}" in field_extra_metas:
                    extra_metas.update({
                        "has_max_length": True,
                        "max_length": field_extra_metas[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}"]
                    })
                if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}" in field_extra_metas:
                    extra_metas.update({
                        "is_required": field_extra_metas[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}"]
                    })
                if f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.PATTERN.value}" in field_meta:
                    constraints.append({"has_regex": True, "regex": field_meta[f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.PATTERN.value}"]})
                if field_name in schema.get("required", []):
                    constraints.append({"is_required": True})

                # Get field display title with translation
                try:
                    display_title = await translation_service.get_static_fields_translation(
                        property_name=field_name,
                        accept_language=accept_language,
                    )
                except Exception as e:
                    print(f"Translation error for field '{field_name}': {e}")
                    display_title = field_meta.get("title", field_name.replace("_", " ").title())

                if not display_title:
                    display_title = field_meta.get("title", field_name.replace("_", " ").title())

                # Handle is_select for data_list and data_source
                data_source = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}")  # Extract data_source from json_schema_extra
                join_organization_query = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}")  # Extract data_source from json_schema_extra
                self.app_debug_print(f" {EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value} : {join_organization_query} data_source : {data_source}", False)
                # self.app_debug_print(f' data_type : {overview_data_type.get(f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}")}', False)
                # CASCADE
                # Add transformed field metadata
                enum_class = field_extra_metas.get(f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}")
                if overview_data_type.get(f"{EGLOBAL_DATA_TYPE.IS_AMOUNT.value}"):
                    try:
                        currency_data_source = field_extra_metas.get("currency_data_source")
                        currency_props = field_extra_metas.get("currency_props")
                        self.app_debug_print(f" currency_data_source : {currency_data_source} currency_props : {currency_props}",False)
                        self.app_debug_print(f" currency_data_source : {currency_data_source} currency_props : {currency_props}",False)
                        query = {}
                        if join_organization_query:
                            query={
                                **query,
                                "filter__sys_organization_id":str(sys_organization_id)
                            }
                        # Fetch data from the data_source collection
                        input_select_list = await self.fetch_data_from_collection(
                            collection_key=CollectionKey(currency_data_source),
                            output_data_type=OutputDataType.INPUT_SELECT,
                            all_data=True,
                            query=query,
                            accept_language=accept_language
                        )
                        transformed[field_name] = {
                            "property_name": field_name,
                            "display_title": display_title,
                            "default_value": default_value,
                            "data_type": overview_data_type,
                            "constraints": constraints,
                            "extra_metas": extra_metas,
                            "data_source": field_meta.get("data_source"),
                            "data_list": input_select_list
                        }
                    except Exception as e:
                        self.app_debug_print(f"Error fetching data for >'{field_name}': {e}",False)
                elif overview_data_type.get(f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}") and data_source:
                    try:
                        query = {
                            f"filter___id":default_value,
                            "filter__is_activated":True
                        }
                        self.app_debug_print(f"\n\n\n\n query >> : {query} data_source : {data_source}\n\n\n", False)
                        input_select = await self.fetch_one_from_collection(
                            collection_key=CollectionKey(data_source),
                            output_data_type=OutputDataType.INPUT_SELECT.value,
                            query=query,
                            accept_language=accept_language
                        )
                        self.app_debug_print(f"\n\n\n\n input_select >> : {input_select}\n\n\n", False)
                        if input_select:
                            transformed[field_name] = {
                                "display_title": display_title,
                                "display_value": input_select['display_value'],
                                "data_type": overview_data_type,
                                "constraints": constraints,
                                "extra_metas": extra_metas,
                            }
                    except Exception as e:
                        self.app_debug_print(f"Error fetching overview data for >'{field_name}': {e}", False)
                elif overview_data_type.get(f'{EGLOBAL_DATA_TYPE.IS_ENUM.value}') and enum_class:
                    try:
                        self.app_debug_print(f"fetching data for '{field_name}'",False)
                        self.app_debug_print(f"fetching enum_class for '{enum_class}'",False)
                        inner_data_list = TranslationService.get_enum_translated_data_list(enum_class,field_name,accept_language)
                        self.app_debug_print(f"\n\nfetching inner_data_list for '{inner_data_list}' \n\n\n",False)
                        excluded_keys = field_extra_metas.get("except_keys_on_head","") # "key_1,key_2"
                        self.app_debug_print(f"\n\nfetching excluded_keys for '{excluded_keys}' \n\n\n",False)
                        excluded_set = set(excluded_keys.split(","))
                        filtered_data = [item for item in inner_data_list if item["id"] not in excluded_set]
                        transformed[field_name] = {
                            "property_name": field_name,
                            "display_title": display_title,
                            "default_value": default_value,
                            "data_type": overview_data_type,
                            "constraints": constraints,
                            "extra_metas": extra_metas,
                            "data_source": field_meta.get("data_source"),
                            "data_list": filtered_data,
                        }
                    except Exception as e:
                        self.app_debug_print(f"Error fetching is_enum for >>'{field_name}': {e}",False)
                else:
                    transformed[field_name] = {
                        "display_title": display_title,
                        "display_value": default_value,
                        "data_type": overview_data_type,
                        "constraints": constraints,
                        "extra_metas": extra_metas,
                    }
            print(f"\n\ntransformed : {transformed}")
            return transformed

    async def attach_recursive_data(self,document, alias, params, accept_language, output_data_type):
        """
        Recursively fetch and attach the named_entity (or parent) document to every node in the tree.
        """
        try:
            # Extract the key names from the params.
            foreign_key = params["foreign_key"]
            local_key = params["local_key"]
            parent_collection = params["parent_collection"].strip()

            # If the document has a valid foreign key, fetch the related document.
            ref_id = document.get(foreign_key)
            self.app_debug_print(f"\n\n >>><< document : {document}  \n\n",False)
            self.app_debug_print(f"\n\n >>><< foreign_key : {foreign_key} : {ref_id} \n\n",False)

            if output_data_type == OutputDataType.DATA_TABLE.value:
                ref_id = None if not ref_id else ref_id['display_value']
            elif output_data_type == OutputDataType.DEFAULT.value:
                ref_id = ref_id
            elif output_data_type == OutputDataType.TREE.value:
                ref_id = ref_id
            self.app_debug_print(f"\n\n >>><< ref_id : {ref_id}\n\n",False)
            if ref_id:
                query = {f"filter__{local_key}": ref_id}
                self.app_debug_print(f"\n\n >>> query<<< : {query}\n\n",False)
                self.app_debug_print(f"\n\n >>> parent_collection <<< : {parent_collection}\n\n",False)
                additional_info = await self.fetch_one_from_collection(
                    collection_key=CollectionKey(parent_collection),
                    output_data_type=OutputDataType(output_data_type.strip()).value if OutputDataType(output_data_type.strip()).value != OutputDataType.TREE else OutputDataType.DEFAULT,
                    accept_language=accept_language,
                    query=query,
                )
                self.app_debug_print(f"\n\n >>> inclued parent : {additional_info}\n\n",False)
                if additional_info:
                    if 'sys_person_id' in additional_info:
                        person_info = await self.fetch_one_from_collection(
                            collection_key=CollectionKey.SYS_PERSON,
                            output_data_type=OutputDataType(output_data_type.strip()).value if OutputDataType(output_data_type.strip()).value != OutputDataType.TREE else OutputDataType.DEFAULT,
                            accept_language=accept_language,
                            query={
                                "filter___id":additional_info['sys_person_id']
                            },
                        )
                        if person_info:
                            document[alias] = {
                                **additional_info,
                                "person":person_info
                            }
                    else :
                        document[alias] = additional_info
            self.app_debug_print(f"\n\n >>> last inclued parent doc : {document}\n\n",False)
            # Process nested children if they exist.
            if "children" in document and isinstance(document["children"], list):
                for child in document["children"]:
                    await self.attach_recursive_data(child, alias, params, accept_language, output_data_type)
        except Exception as e:
            self.app_debug_print(f"Error fetching parent : {str(e)}",False)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    async def fetch_parent_recursive(self,document, params, accept_language, output_data_type):
        """
        Recursively fetch the parent document for the given document.
        """
        foreign_key = params["foreign_key"]
        local_key = params["local_key"]
        parent_collection = params["parent_collection"].strip()

        parent_id = document.get(foreign_key)
        if not parent_id:
            return None

        parent_query = {f"filter__{local_key}": parent_id}
        parent_document = await self.fetch_one_from_collection(
            collection_key=CollectionKey(parent_collection),
            output_data_type=OutputDataType(output_data_type.strip()).value if OutputDataType(output_data_type.strip()).value != OutputDataType.TREE else OutputDataType.DEFAULT,
            accept_language=accept_language,
            query=parent_query,
        )

        if parent_document:
            # Recursively fetch the parent's parent, if any.
            recursive_parent = await self.fetch_parent_recursive(parent_document, params, accept_language, output_data_type)
            if recursive_parent:
                # Attach the parent's parent under a key (e.g., "parent")
                parent_document["parent"] = recursive_parent

        return parent_document

    async def count_data_from_collection(
        self,
        collection_key: CollectionKey,
        accept_language: str = DEFAULT_LANGUAGE,
        query: Optional[Dict[str, Any]] = None,
        endpoint_call: Optional[bool] = False,
        user: Optional[Dict[str, Any]] = None,
        _skip_rls: bool = False,
    ) -> int:
        """
        Count documents in a MongoDB collection using a CollectionKey,
        with support for filtering. This method is optimized for performance
        as it only counts documents without fetching them.

        Parameters:
            collection_key (CollectionKey):
                The key that identifies the target MongoDB collection.
            accept_language (str, optional):
                Specifies the language code to use for translations. Default is DEFAULT_LANGUAGE.
            query (Optional[Dict[str, Any]], optional):
                A dictionary of query parameters.
            endpoint_call (Optional[bool], optional):
                If True, and the collection is not exposed, a PermissionError will be raised.
            user (Optional[Dict[str, Any]], optional):
                The user making the request, used for filtering based on the logged-in user.

        Returns:
            int: The count of documents matching the query criteria.
        """
        self.app_debug_print(f"\n\n\n count_data_from_collection - Starting count operation \n\n\n", False)
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        if not metadata.is_exposed and endpoint_call:
            raise PermissionError(f"Access to collection '{collection_key.value}' is not allowed.")

        # Get the model class for the collection
        model_class = metadata.model_class

        # Create a DAO for the collection
        dao = DAO(metadata.collection_name, model_class, is_read_only=True)

        # Process query parameters
        processed_query = {}
        hidde_on_view_values = {}
        if query:
            # Create a copy of the query to avoid modifying the original
            processed_query = self.convert_query_params(dict(query))

            # Extract hidde_on_view__ filters
            hidde_on_view_values = {
                key[len("hidde_on_view__"):]: value
                for key, value in processed_query.items()
                if key.startswith("hidde_on_view__")
            }

        # Initialize variables for user filters
        logged_user_in_filters = {}
        db_filter = {}

        # Process the query parameters to build the MongoDB filter
        try:
            # Parse query filters
            for key, value in list(processed_query.items()):  # Use list() to create a copy for iteration
                if key.startswith("filter__"):
                    db_field = key.split("__", 1)[1]
                    if db_field.endswith("__in"):
                        db_field = db_field.replace("__in", "")
                        db_filter[db_field] = {"$in": value}
                    else:
                        db_filter[db_field] = value
                # Handle from_logged_in_user__ filters
                elif key.startswith("from_logged_in_user__"):
                    logged_user_in_filters[value] = value
                    if user:
                        org = await self.fetch_native_query_one_from_collection(
                            collection_key=CollectionKey.SYS_ORGANIZATION,
                            output_data_type=OutputDataType.DEFAULT,
                            accept_language=accept_language,
                            native_query={
                                "_id": ObjectId(user.get('sys_organization_id', ''))
                            }
                        )
                        self.app_debug_print(f"\n\n\n from_logged_in_user__  org :  {True if org else False} \n\n\n", False)
                        db_field = key.split("__", 1)[1]
                        if value == 'ref_entity':
                            self.app_debug_print(f" entity value : {value}")
                            if org:
                                entity = await self.fetch_native_query_one_from_collection(
                                    collection_key=CollectionKey.REF_ENTITY,
                                    output_data_type=OutputDataType.DEFAULT,
                                    accept_language=accept_language,
                                    native_query={
                                        "_id": ObjectId(org.get('ref_entity_id', ''))
                                    }
                                )
                                if entity:
                                    db_filter[db_field] = entity['id']
                        elif value == 'sys_user':
                            self.app_debug_print(f" user value : {value}")
                            if org and user:
                                db_filter[db_field] = user['id']
                        elif value == 'sys_organization':
                            self.app_debug_print(f" organization value : {value}")
                            if org:
                                db_filter[db_field] = org['id']

            # Convert Enum values and handle data type conversions for comparison operators
            from app.modules.core.services.converter.converter_service import ConverterService
            db_filter = ConverterService.convert_enum_to_value(db_filter)
            self.app_debug_print(f"Count query filter: {db_filter}", False)

            # Add soft_deleted_at: None to exclude soft-deleted documents
            db_filter["soft_deleted_at"] = None

            # Convert the query parameters for MongoDB
            db_filter = self.convert_query_params(db_filter)

            # 🔒 RLS: final step before query execution.
            if not _skip_rls:
                db_filter = await self._apply_rls_filter(
                    collection_key=collection_key,
                    db_filter=db_filter,
                    user=user,
                )

            # Count the documents
            count = await dao.collection.count_documents(db_filter)
            self.app_debug_print(f"Count result: {count}", False)

            return count

        except Exception as e:
            self.app_debug_print(f"Error during count_data_from_collection: {e}", False)
            return 0

    async def fetch_native_aggregate_count_from_collection(
        self,
        collection_key: CollectionKey,
        accept_language: str = DEFAULT_LANGUAGE,
        pipeline: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """
        Count documents from a MongoDB collection using a native aggregation pipeline.
        This method is optimized for performance as it only returns the count without
        fetching the actual documents.

        This function supports:
        - Complex aggregation pipelines
        - Efficient counting using MongoDB's $count stage

        :param collection_key: The key identifying the collection.
        :param accept_language: Language code for translations.
        :param pipeline: A list representing the MongoDB aggregation pipeline stages.
        :return: The count of documents matching the aggregation pipeline.

        Example:
            >>> pipeline = [
            ...     {"$match": {"status": "active"}},
            ...     {"$group": {"_id": "$role"}}
            ... ]
            >>> count = await fetch_native_aggregate_count_from_collection(
            ...     collection_key=CollectionKey.USERS,
            ...     accept_language="en",
            ...     pipeline=pipeline
            ... )
            >>> print(count)
        """
        self.app_debug_print(f"\n\n\n fetch_native_aggregate_count_from_collection - Starting count operation \n\n\n", False)
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        collection_name = metadata.collection_name
        model_class = metadata.model_class

        dao = DAO(collection_name, model_class, is_read_only=True)
        assert dao.collection is not None, f"Error: Collection {collection_name} is None!"

        # Use the provided native aggregation pipeline or default to an empty pipeline
        pipeline = pipeline.copy() if pipeline is not None else []

        # Add a stage to exclude soft-deleted documents if not already in the pipeline
        has_soft_delete_filter = any(
            "$match" in stage and "soft_deleted_at" in stage["$match"]
            for stage in pipeline
        )

        if not has_soft_delete_filter:
            # Insert a $match stage at the beginning to exclude soft-deleted documents
            pipeline.insert(0, {"$match": {"soft_deleted_at": None}})

        # Add a count stage at the end of the pipeline
        count_stage = {"$count": "total"}
        pipeline.append(count_stage)

        try:
            # Execute the aggregation pipeline
            self.app_debug_print(f"Aggregate count pipeline: {pipeline}", False)
            cursor = dao.collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)

            # Extract the count from the result
            count = results[0]["total"] if results else 0
            self.app_debug_print(f"Aggregate count result: {count}", False)

            return count

        except Exception as e:
            self.app_debug_print(f"Error during fetch_native_aggregate_count_from_collection: {e}", False)
            return 0

    def _extract_field_paths(self, obj, prefix=""):
        """
        Recursively extract field paths from a MongoDB query or projection object.

        This helper method is used to analyze MongoDB aggregation stages to determine
        which fields are being accessed.

        Args:
            obj: The object to analyze (can be a dict, list, or scalar value)
            prefix: The prefix to prepend to field paths (used in recursion)

        Returns:
            A list of field paths found in the object
        """
        paths = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                # Skip operators
                if key.startswith("$"):
                    # Special handling for $reduce, $mergeObjects, etc.
                    if key == "$reduce" and isinstance(value, dict):
                        if "input" in value and isinstance(value["input"], str) and value["input"].startswith("$"):
                            paths.append(value["input"])
                        if "in" in value:
                            paths.extend(self._extract_field_paths(value["in"]))
                    elif key == "$mergeObjects" and isinstance(value, list):
                        for item in value:
                            paths.extend(self._extract_field_paths(item))
                    else:
                        # For other operators, recursively extract paths
                        paths.extend(self._extract_field_paths(value))
                else:
                    # If the value is a string starting with $, it's a field reference
                    if isinstance(value, str) and value.startswith("$"):
                        paths.append(value)
                    # If the key doesn't start with $ and the value is a dict or list,
                    # recursively extract paths with the key as prefix
                    elif isinstance(value, (dict, list)):
                        new_prefix = f"{prefix}.{key}" if prefix else key
                        paths.extend(self._extract_field_paths(value, new_prefix))
        elif isinstance(obj, list):
            for item in obj:
                paths.extend(self._extract_field_paths(item, prefix))

        return paths

    async def hard_delete_with_query_data_from_collection(
        self,
        collection_key: CollectionKey,
        query: Dict[str, Any],
        accept_language: Optional[str] = DEFAULT_LANGUAGE,
        by_pass_exception: Optional[bool] = False,
        delete_multiple: Optional[bool] = False
    ) -> bool:
        """
        Hard deletes (permanently removes) document(s) from the specified collection using a query filter.

        Args:
            collection_key: The collection key from CollectionKey enum
            query: MongoDB query filter to identify document(s) to delete
            accept_language: Language preference for error messages
            by_pass_exception: Whether to bypass exceptions and return False instead
            delete_multiple: If True, deletes all matching documents; if False, deletes only the first match

        Returns:
            bool: True if document(s) were deleted, False otherwise

        Raises:
            ValueError: If collection_key is invalid
            PermissionError: If collection is not exposed
            HTTPException: If deletion fails and by_pass_exception is False
        """
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING

        # Validate collection key
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")

        # Check if the collection is exposed
        if not metadata.is_exposed:
            raise PermissionError(f"Access to collection '{collection_key.value}' is not allowed.")

        # Create DAO instance
        dao = DAO(metadata.collection_name, metadata.model_class, is_read_only=False)

        # Perform deletion based on delete_multiple flag
        if delete_multiple:
            # Delete all documents matching the query
            return await dao.delete_many_query(query, accept_language, by_pass_exception)
        else:
            # Delete only the first document matching the query
            return await dao.delete_with_query(query, accept_language, by_pass_exception)
