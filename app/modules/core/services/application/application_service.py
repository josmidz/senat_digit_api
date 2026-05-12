

import asyncio
import json
from typing import Any, Dict, Optional
from bson import ObjectId
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.icon.svg_icon_service import SvgIconService
from app.modules.core.utils.common.async_runner import AsyncExecutor


class ApplicationService:
    def __init__(self):
        # DebugService.app_debug_print('init app service')
        pass

    @staticmethod
    def convert_to_serializable(data):
        """
        Convert MongoDB ObjectId, datetime objects, and custom classes to serializable format.
        Works with nested dictionaries and lists.
        """
        from datetime import datetime
        import types

        if isinstance(data, dict):
            return {k: ApplicationService.convert_to_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [ApplicationService.convert_to_serializable(item) for item in data]
        elif isinstance(data, ObjectId):
            return str(data)
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, types.MappingProxyType):
            # Handle mappingproxy objects by converting them to dictionaries
            return ApplicationService.convert_to_serializable(dict(data))
        elif hasattr(data, '__dict__'):
            try:
                # Handle custom class objects by converting them to dictionaries
                # Use dict() to convert mappingproxy to a regular dict
                return ApplicationService.convert_to_serializable(dict(data.__dict__))
            except Exception as e:
                # If we can't convert the __dict__, try to extract attributes manually
                result = {}
                for attr in dir(data):
                    if not attr.startswith('_') and not callable(getattr(data, attr)):
                        result[attr] = getattr(data, attr)
                return ApplicationService.convert_to_serializable(result)
        else:
            return data

    @staticmethod
    def _extract_scalar_value(value: Any) -> Optional[str]:
        if isinstance(value, dict):
            for key in ("display_value", "real_value", "value", "id", "_id"):
                candidate = value.get(key)
                if candidate not in (None, ""):
                    return str(candidate)
            return None
        if value in (None, ""):
            return None
        return str(value)

    @classmethod
    def _extract_guard_path(cls, guard_value: Any) -> Optional[str]:
        if isinstance(guard_value, dict):
            return cls._extract_scalar_value(guard_value.get("path"))

        if isinstance(guard_value, list):
            for guard_item in guard_value:
                if not isinstance(guard_item, dict):
                    continue
                path_value = cls._extract_scalar_value(guard_item.get("path"))
                if path_value:
                    return path_value

        return None

    @classmethod
    def _build_svg_icon_payload(
        cls,
        menu_or_app_data: Optional[Dict[str, Any]],
        rbac_path_guard: Any,
        api_consumer_flag: Optional[str],
    ) -> Optional[Dict[str, Dict[str, Dict[str, str]]]]:
        # Use _extract_scalar_value for the debug print so it works for both
        # data_table format ({'real_value': ...}) and default format (plain string).
        _name_dbg = cls._extract_scalar_value((menu_or_app_data or {}).get("name"))
        _flag_dbg = cls._extract_scalar_value((menu_or_app_data or {}).get("flag"))
        DebugService.app_debug_print(
            f"[_build_svg_icon_payload] menu_or_app_data_names : [{_name_dbg}]/[{_flag_dbg}] "
            f"| {(menu_or_app_data or {}).get('flag')} rbac_path_guard : {rbac_path_guard} "
            f"api_consumer_flag : {api_consumer_flag} \n\n",
            True,
        )
        flag_value = cls._extract_scalar_value((menu_or_app_data or {}).get("flag"))
        path_value = cls._extract_guard_path(rbac_path_guard)
        consumer_flag = str(api_consumer_flag or "").strip()

        DebugService.app_debug_print(f"[_build_svg_icon_payload] flag_values : {flag_value} path_value : {path_value} consumer_flag : {consumer_flag} \n\n", True)

        if not flag_value or not path_value or not consumer_flag:
            return {
                "icon": {
                    "icon": {
                        "display_value": None,
                    }
                }
            }

        icon_url = SvgIconService.build_svg_icon_file_server_url(
            menu_or_app_path=path_value,
            menu_or_app_flag=flag_value,
            api_consumer_flag=consumer_flag,
        )

        if not icon_url:
            return {
                "icon": {
                    "icon": {
                        "display_value": None,
                    }
                }
            }

        return {
            "icon": {
                "icon": {
                    "display_value": icon_url,
                }
            }
        }

    @staticmethod
    async def get_single_app_children_display_type_item(
            app_id: str,
            apiConsumer: dict,
            userProfil: dict,
            accept_language: str = DEFAULT_LANGUAGE,
            output_data_type: OutputDataType = OutputDataType.DEFAULT):
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(accept_language)

        children_display_type_pipeline = [
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "localField": "_id",
                    "foreignField": "targeted_id",
                    "as": f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}"
                }
            },
            {
                "$unwind": {
                    "path": f"$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                    "localField": "_id",
                    "foreignField": "targeted_id",
                    "as": f"unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}"
                }
            },
            {
                "$unwind": {
                    "path": f"$unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                    "preserveNullAndEmptyArrays": True
                }
            },

            # // application
            {
                "$lookup": {
                    "from": f"{CollectionKey.SYS_APPLICATION.model_name}",
                    "localField": "targeted_id",
                    "foreignField": "_id",
                    "as": f"unwind__{CollectionKey.SYS_APPLICATION.model_name}"
                }
            },
            {
                "$unwind": {
                    "path": f"$unwind__{CollectionKey.SYS_APPLICATION.model_name}",
                    "preserveNullAndEmptyArrays": False
                }
            },

            # // app api consumer
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "localField": f"unwind__{CollectionKey.SYS_APPLICATION.model_name}._id",
                    "foreignField": "targeted_id",
                    "as": "app__rbac_restricted_api_consumer"
                }
            },
            {
                "$unwind": {
                    "path": "$app__rbac_restricted_api_consumer",
                    "preserveNullAndEmptyArrays": False
                }
            },
            # // app profil
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                    "localField": "_id",
                    "foreignField": "targeted_id",
                    "as": "app__rbac_restricted_profil"
                }
            },
            {
                "$unwind": {
                    "path": "$app__rbac_restricted_profil",
                    "preserveNullAndEmptyArrays": False
                }
            },
            {
                "$match": {
                    "targeted_id": ObjectId(str(app_id)),

                    f"unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.rbac_profile_id": ObjectId(str(userProfil['id'])),
                    f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id": ObjectId(str(apiConsumer['id'])),

                    "app__rbac_restricted_profil.rbac_profile_id": ObjectId(str(userProfil['id'])),
                    f"app__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id": ObjectId(str(apiConsumer['id'])),


                    f"unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.is_hidden": False,
                    f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.is_hidden": False
                }
            },
            {
                "$sort": {
                    "order_by": 1
                }
            },
            {
                "$group": {
                    "_id": "$_id",
                    "docs": {
                        "$push": {
                            "_id": "$_id",
                            "name": "$name",
                            "order_by": "$order_by",
                            "application_group_flag": "$application_group_flag",
                            "sys_application_id": "$sys_application_id",
                            "sys_menu_id": "$sys_menu_id",
                            "is_standalone": "$is_standalone",
                            f"unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}"
                        }
                    }
                }
            },
            {
                "$project": {
                    "merged": {
                        "$reduce": {
                            "input": "$docs",
                            "initialValue": {},
                            "in": {"$mergeObjects": ["$$value", "$$this"]}
                        }
                    }
                }
            },
            {
                "$replaceRoot": {"newRoot": "$merged"}
            }
        ]
        children_display_types = await generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.CFG_CHILDREN_DISPLAY_TYPE,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=accept_language,
            pipeline=children_display_type_pipeline
        )

        if not children_display_types:
            return None

        # getch icon
        if output_data_type == OutputDataType.DATA_TABLE.value:
            targeted_id = children_display_types[0]['id']['display_value'] if children_display_types else None
            order_by = children_display_types[0]['order_by']['display_value'] if children_display_types else 0
        elif output_data_type == OutputDataType.DEFAULT.value:
            targeted_id = children_display_types[0]['id'] if children_display_types else None
            order_by = children_display_types[0]['order_by'] if children_display_types else 0
        elif output_data_type == OutputDataType.TREE.value:
            targeted_id = children_display_types[0]['id'] if children_display_types else None
            order_by = 0
        else:
            targeted_id = None
            order_by = 0
        nested_icon_pipeline = [
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "localField": "_id",
                    "foreignField": "targeted_id",
                    "as": f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}"
                }
            },
            {
                "$unwind": {
                    "path": f"$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$match": {
                    "targeted_id": ObjectId(targeted_id),
                    f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id": ObjectId(apiConsumer['id']),
                }
            },
            {
                "$project": {
                    "id": "$_id",
                    "ref_icon_id": "$ref_icon_id",
                    "rbac_permission_id": "$rbac_permission_id",
                    "targeted_id": "$targeted_id",
                }
            }
        ]
        nested_icon = await generic_service.fetch_native_aggregate_one_from_collection(
            collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
            output_data_type=OutputDataType(output_data_type).value,
            accept_language=accept_language,
            pipeline=nested_icon_pipeline
        )
        rbac_path_guard_pipeline = [
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "localField": "_id",
                    "foreignField": "targeted_id",
                    "as": f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}"
                }
            },
            {
                "$unwind": {
                    "path": f"$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$match": {
                    "targeted_id": ObjectId(targeted_id),
                    # f"unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.rbac_profile_id":ObjectId(user_profil['id']),
                    f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id": ObjectId(apiConsumer['id']),
                    # f"unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.is_hidden":False,
                    f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.is_hidden": False
                }
            },
        ]
        rbac_path_guard = await generic_service.fetch_native_aggregate_one_from_collection(
            collection_key=CollectionKey.RBAC_PATH_GUARD,
            output_data_type=OutputDataType(output_data_type).value,
            accept_language=accept_language,
            pipeline=rbac_path_guard_pipeline
        )

        single_app_profil = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=accept_language,
            query={
                "filter__targeted_id": targeted_id,
            },
        )
        single_app_api_consumer = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=accept_language,
            query={
                "filter__targeted_id": targeted_id,
            },
        )
        is_hidden = False
        is_activated = True
        sub_menus = []
         

        rbac_path_guard_dict = rbac_path_guard if rbac_path_guard else {}
        formatted_data = {
            **(children_display_types[0] if children_display_types else {}),
            'order_by': order_by,
            'ishidden': is_hidden,
            'isactivated': is_activated,
            'restricted_platform': single_app_api_consumer,
            'restricted_profil': single_app_profil,
            'rbac_path_guard': {
                **rbac_path_guard_dict,
            } if is_activated == True else {},
            "sub_menus": [*sub_menus]if is_activated == True else []
        }

        icon_payload = ApplicationService._build_svg_icon_payload(
            menu_or_app_data=children_display_types[0] if children_display_types else {},
            rbac_path_guard=rbac_path_guard_dict,
            api_consumer_flag=apiConsumer.get('flag'),
        )
        if icon_payload:
            formatted_data = {
                **formatted_data,
                **icon_payload,
            }
        return formatted_data

    @staticmethod
    async def get_single_app_item(
            app_id: str,
            apiConsumer: dict,
            accept_language: str = DEFAULT_LANGUAGE,
            output_data_type: OutputDataType = OutputDataType.DEFAULT):
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(accept_language)
        if not app_id:
            return None
        DebugService.app_debug_print(
            f"\n\n\n apps app_id >>>>  : {app_id} \n\n\n", False)
        apps = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.SYS_APPLICATION,
            output_data_type=output_data_type,
            accept_language=accept_language,
            query={
                "filter___id": app_id,
            }
        )
        if not apps:
            return None
        DebugService.app_debug_print(
            f"\n\n\n apps >>>>  : {apps} \n\n\n", False)
        # if not apps:
        # return None
        # getch icon
        if output_data_type == OutputDataType.DATA_TABLE.value:
            targeted_id = apps['id']['display_value']
            order_by = apps['order_by']['display_value']
        elif output_data_type == OutputDataType.DEFAULT.value:
            targeted_id = apps['id']
            order_by = apps['order_by']
        elif output_data_type == OutputDataType.TREE.value:
            targeted_id = apps['id']
            order_by = 0
        else:
            targeted_id: None
            order_by = 0
        nested_icon_pipeline = [
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "localField": "_id",
                    "foreignField": "targeted_id",
                    "as": f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}"
                }
            },
            {
                "$unwind": {
                    "path": f"$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$match": {
                    "targeted_id": ObjectId(targeted_id),
                    f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id": ObjectId(apiConsumer['id']),
                }
            },
            {
                "$project": {
                    "id": "$_id",
                    "ref_icon_id": "$ref_icon_id",
                    "rbac_permission_id": "$rbac_permission_id",
                    "targeted_id": "$targeted_id",
                }
            }
        ]
        nested_icon = await generic_service.fetch_native_aggregate_one_from_collection(
            collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
            output_data_type=OutputDataType(output_data_type).value,
            accept_language=accept_language,
            pipeline=nested_icon_pipeline
        )
        rbac_path_guard_pipeline = [
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "localField": "_id",
                    "foreignField": "targeted_id",
                    "as": f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}"
                }
            },
            {
                "$unwind": {
                    "path": f"$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$match": {
                    "targeted_id": ObjectId(targeted_id),
                    # f"unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.rbac_profile_id":ObjectId(user_profil['id']),
                    f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id": ObjectId(apiConsumer['id']),
                    # f"unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.is_hidden":False,
                    f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.is_hidden": False
                }
            },
        ]
        rbac_path_guard = await generic_service.fetch_native_aggregate_one_from_collection(
            collection_key=CollectionKey.RBAC_PATH_GUARD,
            output_data_type=OutputDataType(output_data_type).value,
            accept_language=accept_language,
            pipeline=rbac_path_guard_pipeline
        )

        single_app_profil = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=accept_language,
            query={
                "filter__targeted_id": targeted_id,
            },
        )
        single_app_api_consumer = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=accept_language,
            query={
                "filter__targeted_id": targeted_id,
            },
        )
        is_hidden = False
        is_activated = True
        sub_menus = []
        # sub_menus = await ApplicationService.get_application_submenus_config(
        #     application_id=targeted_id,
        #     apiConsumer=apiConsumer,
        #     accept_language= accept_language,
        #     output_data_type=OutputDataType(output_data_type).value,
        # );
        # if index == 0:

        rbac_path_guard_dict = rbac_path_guard if rbac_path_guard else {}
        formatted_data = {
            **apps,
            'order_by': order_by,
            'ishidden': is_hidden,
            'isactivated': is_activated,
            'restricted_platform': single_app_api_consumer,
            'restricted_profil': single_app_profil,
            'rbac_path_guard': {
                **rbac_path_guard_dict,
            } if is_activated == True else {},
            "sub_menus": [*sub_menus]if is_activated == True else []
        }

        icon_payload = ApplicationService._build_svg_icon_payload(
            menu_or_app_data=apps,
            rbac_path_guard=rbac_path_guard_dict,
            api_consumer_flag=apiConsumer.get('flag'),
        )
        if icon_payload:
            formatted_data = {
                **formatted_data,
                **icon_payload,
            }
        return formatted_data

    @staticmethod
    async def get_single_menu_item(
            menu_id: str,
            apiConsumer: dict,
            accept_language: str = DEFAULT_LANGUAGE,
            output_data_type: OutputDataType = OutputDataType.DEFAULT):
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(accept_language)

        menu_item = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.SYS_MENU,
            output_data_type=output_data_type,
            accept_language=accept_language,
            query={
                "filter___id": menu_id,
            }
        )
        if not menu_item:
            return None

        # getch icon
        if output_data_type == OutputDataType.DATA_TABLE.value:
            targeted_id = menu_item['id']['display_value']
            order_by = menu_item['order_by']['display_value']
        elif output_data_type == OutputDataType.DEFAULT.value:
            targeted_id = menu_item['id']
            order_by = menu_item['order_by']
        elif output_data_type == OutputDataType.TREE.value:
            targeted_id = menu_item['id']
            order_by = 0
        else:
            targeted_id: None
            order_by = 0
        nested_icon_pipeline = [
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "localField": "_id",
                    "foreignField": "targeted_id",
                    "as": f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}"
                }
            },
            {
                "$unwind": {
                    "path": f"$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$match": {
                    "targeted_id": ObjectId(targeted_id),
                    f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id": ObjectId(apiConsumer['id']),
                }
            },
            {
                "$project": {
                    "id": "$_id",
                    "ref_icon_id": "$ref_icon_id",
                    "rbac_permission_id": "$rbac_permission_id",
                    "targeted_id": "$targeted_id",
                }
            }
        ]
        nested_icon = await generic_service.fetch_native_aggregate_one_from_collection(
            collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
            output_data_type=OutputDataType(output_data_type).value,
            accept_language=accept_language,
            pipeline=nested_icon_pipeline
        )
        rbac_path_guard_pipeline = [
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "localField": "_id",
                    "foreignField": "targeted_id",
                    "as": f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}"
                }
            },
            {
                "$unwind": {
                    "path": f"$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$match": {
                    "targeted_id": ObjectId(targeted_id),
                    # f"unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.rbac_profile_id":ObjectId(user_profil['id']),
                    f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id": ObjectId(apiConsumer['id']),
                    # f"unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.is_hidden":False,
                    f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.is_hidden": False
                }
            },
        ]
        rbac_path_guard = await generic_service.fetch_native_aggregate_one_from_collection(
            collection_key=CollectionKey.RBAC_PATH_GUARD,
            output_data_type=OutputDataType(output_data_type).value,
            accept_language=accept_language,
            pipeline=rbac_path_guard_pipeline
        )

        single_app_profil = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=accept_language,
            query={
                "filter__targeted_id": targeted_id,
            },
        )
        single_app_api_consumer = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=accept_language,
            query={
                "filter__targeted_id": targeted_id,
            },
        )
        is_hidden = False
        is_activated = True
        sub_menus = []
        # sub_menus = await ApplicationService.get_application_submenus_config(
        #     application_id=targeted_id,
        #     apiConsumer=apiConsumer,
        #     accept_language= accept_language,
        #     output_data_type=OutputDataType(output_data_type).value,
        # );
        rbac_path_guard_dict = rbac_path_guard if rbac_path_guard else {}
        formatted_data = {
            **menu_item,
            'order_by': order_by,
            'ishidden': is_hidden,
            'isactivated': is_activated,
            'restricted_platform': single_app_api_consumer,
            'restricted_profil': single_app_profil,
            'rbac_path_guard': {
                **rbac_path_guard_dict,
            } if is_activated == True else {},
            "sub_menus": [*sub_menus]if is_activated == True else []
        }

        icon_payload = ApplicationService._build_svg_icon_payload(
            menu_or_app_data=menu_item,
            rbac_path_guard=rbac_path_guard_dict,
            api_consumer_flag=apiConsumer.get('flag'),
        )
        if icon_payload:
            formatted_data = {
                **formatted_data,
                **icon_payload,
            }
        return formatted_data

    @staticmethod
    async def get_user_application_submenus_compact(
            application_id: str,
            apiConsumer: dict,
            user: dict,
            userProfil: dict,
            page: int = 0,
            limit: int = 50,
            all_data: bool = True,
            accept_language: str = DEFAULT_LANGUAGE,
            output_data_type: OutputDataType = OutputDataType.DEFAULT):
        """
        Compact fetch paradigm: Fetches ALL menus + auxiliary data for an application
        using batch queries (~7 total) instead of recursive per-item queries (~240).
        Returns a tree structure with sub_menus nested under their parents.
        """
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(accept_language)

        DebugService.app_debug_print(
            f"\n\n COMPACT MODE: Fetching all submenus for app {application_id}\n", True)

        # ─────────────────────────────────────────────────────────────────
        # STEP 1: Fetch ALL menus for this application (same pipeline as default)
        # ─────────────────────────────────────────────────────────────────
        pipeline = [
            {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_ROLE.model_name}',
                    'localField': 'rbac_role_id',
                    'foreignField': '_id',
                    'as': f'unwind__{CollectionKey.RBAC_ROLE.model_name}'
                }
            }, {
                '$unwind': {
                    'path': f'$unwind__{CollectionKey.RBAC_ROLE.model_name}',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_PERMISSION.model_name}',
                    'localField': 'rbac_permission_id',
                    'foreignField': '_id',
                    'as': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
                }
            }, {
                '$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_PRIVILEGE.model_name}',
                    'let': {
                        'permissionId': '$rbac_permission_id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {'$eq': ['$rbac_permission_id', '$$permissionId']},
                                        {'$eq': ['$sys_user_id', ObjectId(user['id'])]},
                                        {'$eq': ['$status', 'added']}
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'direct_privileges'
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_PERMISSION_TARGET.model_name}',
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id',
                    'foreignField': 'rbac_permission_id',
                    'as': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
                }
            }, {
                '$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.SYS_MENU.model_name}',
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.targeted_id',
                    'foreignField': '_id',
                    'as': f'unwind__{CollectionKey.SYS_MENU.model_name}'
                }
            }, {
                '$unwind': f'$unwind__{CollectionKey.SYS_MENU.model_name}'
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_PATH_GUARD.model_name}',
                    'localField': f'unwind__{CollectionKey.SYS_MENU.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}'
                }
            }, {
                '$unwind': f'$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}'
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}',
                    'localField': f'unwind__{CollectionKey.SYS_MENU.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': 'menu_rbac_restricted_api_consumer'
                }
            }, {
                '$unwind': {
                    'path': '$menu_rbac_restricted_api_consumer',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}',
                    'localField': f'unwind__{CollectionKey.SYS_MENU.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': 'menu_rbac_restricted_profil'
                }
            }, {
                '$unwind': {
                    'path': '$menu_rbac_restricted_profil',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}',
                    'localField': f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': 'guard_rbac_restricted_api_consumer'
                }
            }, {
                '$unwind': {
                    'path': '$guard_rbac_restricted_api_consumer',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}',
                    'localField': f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': 'guard_rbac_restricted_profil'
                }
            }, {
                '$unwind': {
                    'path': '$guard_rbac_restricted_profil',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_PRIVILEGE.model_name}',
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id',
                    'foreignField': 'rbac_permission_id',
                    'as': f'unwind__{CollectionKey.RBAC_PRIVILEGE.model_name}'
                }
            }, {
                '$unwind': {
                    'path': f'$unwind__{CollectionKey.RBAC_PRIVILEGE.model_name}',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                # ── COMPACT FIX: Allow BOTH root menus (sys_application_id)
                #    AND child menus (sys_menu_id) at any depth. Children at
                #    depth ≥2 only carry sys_menu_id, not sys_application_id,
                #    so filtering solely on sys_application_id excluded them.
                #    The in-memory tree builder (Step 2.5) already filters
                #    root_items to the target application_id.
                '$match': {
                    f'unwind__{CollectionKey.SYS_MENU.model_name}.is_activated': True,
                    'menu_rbac_restricted_profil.rbac_profile_id': ObjectId(str(userProfil['id'])),
                    'menu_rbac_restricted_api_consumer.ref_api_consumer_id': ObjectId(str(apiConsumer['id'])),
                    'guard_rbac_restricted_profil.rbac_profile_id': ObjectId(str(userProfil['id'])),
                    'guard_rbac_restricted_api_consumer.ref_api_consumer_id': ObjectId(str(apiConsumer['id'])),
                    'menu_rbac_restricted_profil.is_hidden': False,
                    'menu_rbac_restricted_api_consumer.is_hidden': False,
                    'guard_rbac_restricted_profil.is_hidden': False,
                    'guard_rbac_restricted_api_consumer.is_hidden': False,
                    '$and': [
                        # Condition 1: Menu belongs to this app OR is a child menu (has sys_menu_id)
                        {
                            '$or': [
                                {f'unwind__{CollectionKey.SYS_MENU.model_name}.sys_application_id': ObjectId(str(application_id).strip())},
                                {f'unwind__{CollectionKey.SYS_MENU.model_name}.sys_menu_id': {'$exists': True, '$ne': None}},
                            ]
                        },
                        # Condition 2: User has access via role OR direct privilege
                        {
                            '$or': [
                                {f'unwind__{CollectionKey.RBAC_ROLE.model_name}._id': ObjectId(user['rbac_role_id'])},
                                {'direct_privileges': {'$ne': []}}
                            ]
                        }
                    ]
                }
            }, {
                '$group': {
                    '_id': f'$unwind__{CollectionKey.SYS_MENU.model_name}._id',
                    'docs': {
                        '$push': {
                            '_id': '$_id',
                            f'unwind__{CollectionKey.SYS_MENU.model_name}': f'$unwind__{CollectionKey.SYS_MENU.model_name}',
                            f'unwind__{CollectionKey.RBAC_ROLE.model_name}': f'$unwind__{CollectionKey.RBAC_ROLE.model_name}',
                            f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}',
                            f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}': f'$unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}',
                            f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}': f'$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}',
                            'menu_rbac_restricted_api_consumer': '$menu_rbac_restricted_api_consumer',
                            'menu_rbac_restricted_profil': '$menu_rbac_restricted_profil',
                            'guard_rbac_restricted_api_consumer': '$guard_rbac_restricted_api_consumer',
                            'guard_rbac_restricted_profil': '$guard_rbac_restricted_profil',
                            'rbac_role_id': '$rbac_role_id',
                            'rbac_permission_id': '$rbac_permission_id'
                        }
                    }
                }
            }, {
                '$project': {
                    'merged': {
                        '$reduce': {
                            'input': '$docs',
                            'initialValue': {},
                            'in': {
                                '$mergeObjects': ['$$value', '$$this']
                            }
                        }
                    }
                }
            }, {
                '$project': {
                    '_id': '$merged._id',
                    'rbac_permission_id': '$merged.rbac_permission_id',
                    'rbac_role_id': '$merged.rbac_role_id',
                    f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}': {
                        '_id': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}._id',
                        'path_guard': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.path_guard',
                        'path': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.path',
                        'targeted_id': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.targeted_id',
                        'sys_menu_id': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.sys_menu_id',
                        'sys_application_id': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.sys_application_id'
                    },
                    f'unwind__{CollectionKey.SYS_MENU.model_name}': {
                        '_id': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}._id',
                        'is_standalone': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.is_standalone',
                        'name': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.name',
                        'flag': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.flag',
                        'description_str': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.description_str',
                        "application_group_flag": f"$merged.unwind__{CollectionKey.SYS_MENU.model_name}.application_group_flag",
                        'sys_application_id': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.sys_application_id',
                        'sys_menu_id': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.sys_menu_id',
                        'order_by': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.order_by',
                        'is_skipable_menu_on_view': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.is_skipable_menu_on_view'
                    }
                }
            }, {
                '$sort': {
                    f'unwind__{CollectionKey.SYS_MENU.model_name}.order_by': 1
                }
            }
        ]

        infos = await generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
            output_data_type=output_data_type,
            accept_language=accept_language,
            pipeline=pipeline,
            all_data=True,
        )

        DebugService.app_debug_print(
            f"\n COMPACT: Fetched {len(infos)} menus for app {application_id}\n", True)

        if not infos:
            return []

        # ─────────────────────────────────────────────────────────────────
        # STEP 2: Collect all menu IDs
        # ─────────────────────────────────────────────────────────────────
        sys_menu_key = f'unwind__{CollectionKey.SYS_MENU.model_name}'
        path_guard_key = f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}'

        def extract_id(val):
            """Extract ID from potentially dict-wrapped value."""
            if isinstance(val, dict):
                return str(val.get('display_value') or val.get('real_value') or val.get('id') or val.get('_id') or '')
            return str(val) if val else ''

        menu_items_map = {}

        for item in infos:
            sys_menu = item.get(sys_menu_key) or item.get('sys_menu')
            if not sys_menu:
                continue

            raw_id = sys_menu.get('_id') or sys_menu.get('id')
            menu_id = extract_id(raw_id) if isinstance(raw_id, dict) else str(raw_id) if raw_id else None
            if not menu_id:
                continue

            rbac_path_guard = item.get(path_guard_key) or item.get('rbac_path_guard') or {}
            sys_menu_parent_id = sys_menu.get('sys_menu_id')
            parent_id = extract_id(sys_menu_parent_id) if isinstance(sys_menu_parent_id, dict) else str(sys_menu_parent_id) if sys_menu_parent_id else None

            order_by_val = sys_menu.get('order_by', 0)
            if isinstance(order_by_val, dict):
                order_by_val = order_by_val.get('display_value', 0) or 0

            menu_items_map[menu_id] = {
                **sys_menu,
                '_id': menu_id,
                'id': sys_menu.get('id', menu_id),
                'sys_menu_id': parent_id,
                'order_by': order_by_val,
                'ishidden': False,
                'isactivated': True,
                'rbac_path_guard': rbac_path_guard,
                'rbac_actions': [],
                'rbac_components': [],
                'ref_children_display_type': None,
                'ref_data_display_type': None,
                'collection_crud_info': [],
                'sub_menus': [],
            }

        # ─────────────────────────────────────────────────────────────────
        # STEP 2.5: Build bare tree and filter for the target application
        # ─────────────────────────────────────────────────────────────────
        DebugService.app_debug_print(
            f"COMPACT: Building tree from {len(menu_items_map)} menu items in memory map\n", True)

        root_items = []
        orphan_count = 0
        nested_count = 0
        for menu_id, menu_data in menu_items_map.items():
            parent_id = menu_data.get('sys_menu_id')
            parent_found = False

            if parent_id and str(parent_id) in menu_items_map:
                parent = menu_items_map[str(parent_id)]
                parent['sub_menus'].append(menu_data)
                parent_found = True
                nested_count += 1

            if not parent_found:
                # Valid root items MUST belong to the targeted application!
                raw_app_id = menu_data.get('sys_application_id', '')
                app_id_str = extract_id(raw_app_id) if isinstance(raw_app_id, dict) else str(raw_app_id) if raw_app_id else ''
                if app_id_str == str(application_id):
                    root_items.append(menu_data)
                else:
                    orphan_count += 1

        DebugService.app_debug_print(
            f"COMPACT: Tree built — {len(root_items)} roots, {nested_count} nested, "
            f"{orphan_count} orphans (other apps) for app {application_id}\n", True)

        # Collect all valid IDs by recursively traversing the target root_items
        unique_target_ids = set()
        def collect_ids(items, depth=0):
            for item in items:
                unique_target_ids.add(str(item.get('_id')))
                children = item.get('sub_menus') or []
                if children:
                    # `name` may be a plain string (DEFAULT format) or a dict (DATA_TABLE format).
                    _name_val = item.get('name')
                    _name_dbg = (
                        _name_val.get('real_value', item.get('_id'))
                        if isinstance(_name_val, dict)
                        else (_name_val if _name_val is not None else item.get('_id'))
                    )
                    DebugService.app_debug_print(
                        f"COMPACT:   depth={depth} menu={_name_dbg} has {len(children)} children\n", True)
                    collect_ids(children, depth + 1)
        
        collect_ids(root_items, depth=0)
        unique_target_ids = list(unique_target_ids)

        DebugService.app_debug_print(
            f"COMPACT: {len(unique_target_ids)} unique menu IDs collected for application {application_id}\n", True)

        # ─────────────────────────────────────────────────────────────────
        # STEP 3: Batch fetch ALL auxiliary data in parallel
        # ─────────────────────────────────────────────────────────────────
        oid_targets = [ObjectId(i) for i in unique_target_ids]

        async def batch_fetch_actions():
            """Batch fetch RBAC actions for ALL menu IDs."""
            action_pipeline = [
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                        'localField': '_id',
                        'foreignField': 'rbac_action_id',
                        'as': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
                    }
                },
                {'$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'},
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.rbac_permission_id',
                        'foreignField': '_id',
                        'as': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
                    }
                },
                {'$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}'},
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                        'let': {'permissionId': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id'},
                        'pipeline': [
                            {'$match': {'$expr': {'$and': [
                                {'$eq': ['$rbac_permission_id', '$$permissionId']},
                                {'$eq': ['$sys_user_id', ObjectId(user['id'])]},
                                {'$eq': ['$status', 'added']}
                            ]}}}
                        ],
                        'as': 'direct_privileges'
                    }
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION_ROLE.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id',
                        'foreignField': 'rbac_permission_id',
                        'as': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}_role'
                    }
                },
                {'$unwind': {'path': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}_role', 'preserveNullAndEmptyArrays': True}},
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_ROLE.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}_role.rbac_role_id',
                        'foreignField': '_id',
                        'as': f'unwind__{CollectionKey.RBAC_ROLE.model_name}'
                    }
                },
                {'$unwind': {'path': f'$unwind__{CollectionKey.RBAC_ROLE.model_name}', 'preserveNullAndEmptyArrays': True}},
                {
                    '$lookup': {
                        'from': f"{CollectionKey.SYS_MENU.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.targeted_id',
                        'foreignField': '_id',
                        'as': f'unwind__{CollectionKey.SYS_MENU.model_name}'
                    }
                },
                {'$unwind': f'$unwind__{CollectionKey.SYS_MENU.model_name}'},
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}._id',
                        'foreignField': 'targeted_id',
                        'as': f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}'
                    }
                },
                {'$unwind': {'path': f'$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}', 'preserveNullAndEmptyArrays': True}},
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}._id',
                        'foreignField': 'targeted_id',
                        'as': f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}'
                    }
                },
                {'$unwind': {'path': f'$unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}', 'preserveNullAndEmptyArrays': True}},
                {
                    '$match': {
                        '$or': [
                            {
                                f'unwind__{CollectionKey.RBAC_ROLE.model_name}._id': ObjectId(user['rbac_role_id']),
                                f'unwind__{CollectionKey.SYS_MENU.model_name}._id': {"$in": oid_targets},
                                f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.rbac_profile_id': ObjectId(userProfil['id']),
                                f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id': ObjectId(apiConsumer['id'])
                            },
                            {
                                'direct_privileges': {'$ne': []},
                                f'unwind__{CollectionKey.SYS_MENU.model_name}._id': {"$in": oid_targets},
                                f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.rbac_profile_id': ObjectId(userProfil['id']),
                                f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id': ObjectId(apiConsumer['id'])
                            }
                        ]
                    }
                },
                {
                    '$project': {
                        '_id': 1, 'is_standalone': 1, 'label': 1, 'flag': 1,
                        'hard_code_flag': 1,
                        'access_via': {
                            '$cond': [
                                {'$gt': [{'$size': '$direct_privileges'}, 0]},
                                'privilege', 'role'
                            ]
                        },
                        'menu_id': f'$unwind__{CollectionKey.SYS_MENU.model_name}._id'
                    }
                }
            ]
            return await generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_ACTION,
                output_data_type=output_data_type,
                accept_language=accept_language,
                pipeline=action_pipeline,
                all_data=True
            )

        async def batch_fetch_components():
            """Batch fetch RBAC components for ALL menu IDs."""
            comp_pipeline = [
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                        'localField': '_id',
                        'foreignField': 'rbac_component_id',
                        'as': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
                    }
                },
                {'$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'},
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.rbac_permission_id',
                        'foreignField': '_id',
                        'as': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
                    }
                },
                {'$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}'},
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                        'let': {'permissionId': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id'},
                        'pipeline': [
                            {'$match': {'$expr': {'$and': [
                                {'$eq': ['$rbac_permission_id', '$$permissionId']},
                                {'$eq': ['$sys_user_id', ObjectId(user['id'])]},
                                {'$eq': ['$status', 'added']}
                            ]}}}
                        ],
                        'as': 'direct_privileges'
                    }
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION_ROLE.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id',
                        'foreignField': 'rbac_permission_id',
                        'as': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}_role'
                    }
                },
                {'$unwind': {'path': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}_role', 'preserveNullAndEmptyArrays': True}},
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_ROLE.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}_role.rbac_role_id',
                        'foreignField': '_id',
                        'as': f'unwind__{CollectionKey.RBAC_ROLE.model_name}'
                    }
                },
                {'$unwind': {'path': f'$unwind__{CollectionKey.RBAC_ROLE.model_name}', 'preserveNullAndEmptyArrays': True}},
                {
                    '$lookup': {
                        'from': f"{CollectionKey.SYS_MENU.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.targeted_id',
                        'foreignField': '_id',
                        'as': f'unwind__{CollectionKey.SYS_MENU.model_name}'
                    }
                },
                {'$unwind': f'$unwind__{CollectionKey.SYS_MENU.model_name}'},
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}._id',
                        'foreignField': 'targeted_id',
                        'as': f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}'
                    }
                },
                {'$unwind': {'path': f'$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}', 'preserveNullAndEmptyArrays': True}},
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}._id',
                        'foreignField': 'targeted_id',
                        'as': f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}'
                    }
                },
                {'$unwind': {'path': f'$unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}', 'preserveNullAndEmptyArrays': True}},
                {
                    '$match': {
                        '$or': [
                            {
                                f'unwind__{CollectionKey.RBAC_ROLE.model_name}._id': ObjectId(user['rbac_role_id']),
                                f'unwind__{CollectionKey.SYS_MENU.model_name}._id': {"$in": oid_targets},
                                f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.rbac_profile_id': ObjectId(userProfil['id']),
                                f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id': ObjectId(apiConsumer['id'])
                            },
                            {
                                'direct_privileges': {'$ne': []},
                                f'unwind__{CollectionKey.SYS_MENU.model_name}._id': {"$in": oid_targets},
                                f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.rbac_profile_id': ObjectId(userProfil['id']),
                                f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id': ObjectId(apiConsumer['id'])
                            }
                        ]
                    }
                },
                {
                    '$project': {
                        '_id': 1, 'is_standalone': 1, 'label': 1, 'flag': 1,
                        'hard_code_flag': 1,
                        'access_via': {
                            '$cond': [
                                {'$gt': [{'$size': '$direct_privileges'}, 0]},
                                'privilege', 'role'
                            ]
                        },
                        'menu_id': f'$unwind__{CollectionKey.SYS_MENU.model_name}._id'
                    }
                }
            ]
            return await generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_COMPONENT,
                output_data_type=output_data_type,
                accept_language=accept_language,
                pipeline=comp_pipeline,
                all_data=True
            )

        async def batch_fetch_crud_info():
            """Batch fetch collection_crud_info for ALL menu IDs."""
            crud_pipeline = [
                {'$match': {'targeted_id': {'$in': oid_targets}}},
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_ENDPOINT.model_name}",
                        'let': {'endpoint_id': '$rbac_endpoint_id'},
                        'pipeline': [
                            {'$match': {'$expr': {'$eq': ['$_id', '$$endpoint_id']}}},
                            {'$project': {
                                '_id': 1, 'url': 1, 'label': 1, 'flag': 1,
                                'is_sudo_action': 1, 'is_sudo_group_action': 1,
                                'is_sudo_delegated_action': 1,
                                'is_sudo_group_cross_validation_action': 1,
                                'is_sudo_group_inter_organization_validation_action': 1,
                            }}
                        ],
                        'as': 'endpoints'
                    }
                },
                {'$unwind': {'path': '$endpoints', 'preserveNullAndEmptyArrays': True}},
                {'$sort': {'order_by': 1}},
                {
                    '$project': {
                        '_id': 1, 'targeted_id': 1, 'rbac_endpoint_id': 1,
                        'label': 1, 'flag': 1, 'hard_code_flag': 1,
                        'parent_field_name': 1, 'order_by': 1,
                        f'unwind__{CollectionKey.RBAC_ENDPOINT.model_name}': {
                            '_id': '$endpoints._id',
                            'url': '$endpoints.url',
                            'label': '$endpoints.label',
                            'flag': '$endpoints.flag',
                            'is_sudo_action': '$endpoints.is_sudo_action',
                            'is_sudo_group_action': '$endpoints.is_sudo_group_action',
                            'is_sudo_delegated_action': '$endpoints.is_sudo_delegated_action',
                            'is_sudo_group_cross_validation_action': '$endpoints.is_sudo_group_cross_validation_action',
                            'is_sudo_group_inter_organization_validation_action': '$endpoints.is_sudo_group_inter_organization_validation_action',
                        }
                    }
                }
            ]
            return await generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.REF_COLLECTION_CRUD_INFO,
                output_data_type=output_data_type,
                accept_language=accept_language,
                pipeline=crud_pipeline,
                all_data=True
            )

        async def batch_fetch_visibility():
            """Batch fetch is_hidden/is_activated for ALL menu IDs."""
            vis_pipeline = [
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                        'localField': 'rbac_permission_id',
                        'foreignField': '_id',
                        'as': 'permissions'
                    }
                },
                {'$unwind': '$permissions'},
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                        'let': {'permissionId': '$permissions._id'},
                        'pipeline': [
                            {'$match': {'$expr': {'$and': [
                                {'$eq': ['$rbac_permission_id', '$$permissionId']},
                                {'$eq': ['$sys_user_id', ObjectId(user['id'])]},
                                {'$eq': ['$status', 'added']}
                            ]}}}
                        ],
                        'as': 'direct_privileges'
                    }
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                        'localField': 'permissions._id',
                        'foreignField': 'rbac_permission_id',
                        'as': 'permission_targets'
                    }
                },
                {'$unwind': {'path': '$permission_targets', 'preserveNullAndEmptyArrays': True}},
                {
                    '$lookup': {
                        'from': f"{CollectionKey.SYS_MENU.model_name}",
                        'localField': 'permission_targets.targeted_id',
                        'foreignField': '_id',
                        'as': 'menus'
                    }
                },
                {'$unwind': {'path': '$menus', 'preserveNullAndEmptyArrays': True}},
                {
                    '$match': {
                        'menus._id': {'$in': oid_targets}
                    }
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                        'let': {'menu_id': '$menus._id'},
                        'pipeline': [
                            {'$match': {'$expr': {'$eq': ['$targeted_id', '$$menu_id']}}},
                            {'$match': {'ref_api_consumer_id': ObjectId(apiConsumer['id'])}},
                            {'$project': {'_id': 1, 'is_hidden': 1, 'is_activated': 1, 'is_locked': 1, 'ref_api_consumer_id': 1}}
                        ],
                        'as': 'api_consumers'
                    }
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                        'let': {'menu_id': '$menus._id'},
                        'pipeline': [
                            {'$match': {'$expr': {'$eq': ['$targeted_id', '$$menu_id']}}},
                            {'$match': {'rbac_profile_id': ObjectId(userProfil['id'])}},
                            {'$project': {'_id': 1, 'is_hidden': 1, 'is_activated': 1, 'is_locked': 1, 'rbac_profile_id': 1}}
                        ],
                        'as': 'profiles'
                    }
                },
                {
                    '$match': {
                        '$or': [
                            {
                                'rbac_role_id': ObjectId(user['rbac_role_id']),
                                'api_consumers': {'$ne': []},
                                'profiles': {'$ne': []},
                                'permissions._id': {'$exists': True}
                            },
                            {
                                'direct_privileges': {'$ne': []},
                                'api_consumers': {'$ne': []},
                                'profiles': {'$ne': []}
                            }
                        ]
                    }
                },
                {
                    '$group': {
                        '_id': '$menus._id',
                        'rbac_role_id': {'$first': '$rbac_role_id'},
                        'rbac_permission_id': {'$first': '$permissions._id'},
                        'result': {
                            '$first': {
                                'rbac_restricted_api_consumer': {'$arrayElemAt': ['$api_consumers', 0]},
                                'rbac_restricted_profil': {'$arrayElemAt': ['$profiles', 0]},
                            }
                        }
                    }
                },
                {'$replaceRoot': {'newRoot': {'$mergeObjects': ['$result', {'menu_id': '$_id', 'rbac_role_id': '$rbac_role_id', 'rbac_permission_id': '$rbac_permission_id'}]}}}
            ]
            return await generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=accept_language,
                pipeline=vis_pipeline
            )

        async def noop():
            return []

        # Execute ALL batch fetches in parallel
        batch_results = await AsyncExecutor.gather_with_limit([
            batch_fetch_actions(),
            batch_fetch_components(),
            batch_fetch_crud_info(),
            batch_fetch_visibility(),
        ], limit=10)

        actions_list = batch_results[0] if batch_results[0] else []
        components_list = batch_results[1] if batch_results[1] else []
        crud_info_list = batch_results[2] if batch_results[2] else []
        visibility_list = batch_results[3] if batch_results[3] else []

        DebugService.app_debug_print(
            f"COMPACT: Batch results - actions:{len(actions_list)}, "
            f"components:{len(components_list)}, crud:{len(crud_info_list)}, "
            f"visibility:{len(visibility_list)}", True)

        # ─────────────────────────────────────────────────────────────────
        # STEP 4: Build lookup maps from batch results
        # ─────────────────────────────────────────────────────────────────
        # Actions map: menu_id -> [actions]
        actions_map = {}
        for action in actions_list:
            m_id = extract_id(action.get('menu_id'))
            if m_id:
                if m_id not in actions_map:
                    actions_map[m_id] = []
                action_copy = {k: v for k, v in action.items() if k != 'menu_id'}
                actions_map[m_id].append(action_copy)

        # Components map: menu_id -> [components]
        components_map = {}
        for comp in components_list:
            m_id = extract_id(comp.get('menu_id'))
            if m_id:
                if m_id not in components_map:
                    components_map[m_id] = []
                comp_copy = {k: v for k, v in comp.items() if k != 'menu_id'}
                components_map[m_id].append(comp_copy)

        # CRUD info map: targeted_id -> [crud_info entries]
        crud_info_map = {}
        for crud in crud_info_list:
            tid = extract_id(crud.get('targeted_id'))
            if tid:
                if tid not in crud_info_map:
                    crud_info_map[tid] = []
                crud_info_map[tid].append(crud)

        # Visibility map: menu_id -> {is_hidden, is_activated}
        visibility_map = {}
        for vis in visibility_list:
            m_id = extract_id(vis.get('menu_id'))
            if m_id:
                is_hidden = False
                is_activated = True

                profil_info = vis.get('rbac_restricted_profil')
                api_info = vis.get('rbac_restricted_api_consumer')

                if profil_info:
                    if profil_info.get('is_locked') == True or profil_info.get('is_activated') == False:
                        is_activated = False
                    if profil_info.get('is_hidden') == False:
                        is_hidden = False

                if api_info:
                    if api_info.get('is_locked') == True or api_info.get('is_activated') == False:
                        is_activated = False
                    if api_info.get('is_hidden') == False:
                        is_hidden = False

                visibility_map[m_id] = {
                    'is_hidden': is_hidden,
                    'is_activated': is_activated
                }

        # ─────────────────────────────────────────────────────────────────
        # STEP 5: Attach auxiliary data + icons to each valid menu item
        # ─────────────────────────────────────────────────────────────────
        for menu_id in unique_target_ids:
            menu_data = menu_items_map[menu_id]
            # Actions
            if menu_id in actions_map:
                menu_data['rbac_actions'] = actions_map[menu_id]

            # Components
            if menu_id in components_map:
                menu_data['rbac_components'] = components_map[menu_id]

            # CRUD info
            if menu_id in crud_info_map:
                menu_data['collection_crud_info'] = crud_info_map[menu_id]

            # Visibility
            if menu_id in visibility_map:
                vis = visibility_map[menu_id]
                menu_data['ishidden'] = vis['is_hidden']
                menu_data['isactivated'] = vis['is_activated']

            # Icon
            icon_payload = ApplicationService._build_svg_icon_payload(
                menu_or_app_data=menu_data,
                rbac_path_guard=menu_data.get('rbac_path_guard'),
                api_consumer_flag=apiConsumer.get('flag'),
            )
            if icon_payload:
                menu_data.update(icon_payload)

        # ─────────────────────────────────────────────────────────────────
        # STEP 6: Filter hidden menus and sort tree recursively by order_by
        # ─────────────────────────────────────────────────────────────────
        def finalize_tree(items):
            visible_items = [item for item in items if not item.get('ishidden', False)]
            visible_items.sort(key=lambda x: x.get('order_by', 0) or 0)
            for item in visible_items:
                if item.get('sub_menus'):
                    item['sub_menus'] = finalize_tree(item['sub_menus'])
            return visible_items

        root_items = finalize_tree(root_items)

        DebugService.app_debug_print(
            f"COMPACT: Returning {len(root_items)} root menu items with nested children\n", True)

        return root_items

    @staticmethod
    async def get_user_application_submenus(
            application_id: str,
            apiConsumer: dict,
            user: dict,
            userProfil: dict,
            page: int = 0,
            limit: int = 10,
            all_data: bool = False,
            accept_language: str = DEFAULT_LANGUAGE,
            output_data_type: OutputDataType = OutputDataType.DEFAULT):
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(accept_language)

     
        pipeline = [
            {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_ROLE.model_name}',
                    'localField': 'rbac_role_id',
                    'foreignField': '_id',
                    'as': f'unwind__{CollectionKey.RBAC_ROLE.model_name}'
                }
            }, {
                '$unwind': f'$unwind__{CollectionKey.RBAC_ROLE.model_name}'
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_PERMISSION.model_name}',
                    'localField': 'rbac_permission_id',
                    'foreignField': '_id',
                    'as': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
                }
            }, {
                '$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_PRIVILEGE.model_name}',
                    'let': {
                        'permissionId': '$rbac_permission_id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {
                                            '$eq': [
                                                '$rbac_permission_id', '$$permissionId'
                                            ]
                                        }, {
                                            '$eq': [
                                                '$sys_user_id', ObjectId(
                                                    user['id'])
                                            ]
                                        }, {
                                            '$eq': [
                                                '$status', 'added'
                                            ]
                                        }
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'direct_privileges'
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_PERMISSION_TARGET.model_name}',
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id',
                    'foreignField': 'rbac_permission_id',
                    'as': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
                }
            }, {
                '$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.SYS_MENU.model_name}',
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.targeted_id',
                    'foreignField': '_id',
                    'as': f'unwind__{CollectionKey.SYS_MENU.model_name}'
                }
            }, {
                '$unwind': f'$unwind__{CollectionKey.SYS_MENU.model_name}'
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_PATH_GUARD.model_name}',
                    'localField': f'unwind__{CollectionKey.SYS_MENU.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}'
                }
            }, {
                '$unwind': f'$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}'
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}',
                    'localField': f'unwind__{CollectionKey.SYS_MENU.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': 'menu_rbac_restricted_api_consumer'
                }
            }, {
                '$unwind': {
                    'path': '$menu_rbac_restricted_api_consumer',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}',
                    'localField': f'unwind__{CollectionKey.SYS_MENU.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': 'menu_rbac_restricted_profil'
                }
            }, {
                '$unwind': {
                    'path': '$menu_rbac_restricted_profil',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}',
                    'localField': f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': 'guard_rbac_restricted_api_consumer'
                }
            }, {
                '$unwind': {
                    'path': '$guard_rbac_restricted_api_consumer',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}',
                    'localField': f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': 'guard_rbac_restricted_profil'
                }
            }, {
                '$unwind': {
                    'path': '$guard_rbac_restricted_profil',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_PRIVILEGE.model_name}',
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id',
                    'foreignField': 'rbac_permission_id',
                    'as': f'unwind__{CollectionKey.RBAC_PRIVILEGE.model_name}'
                }
            }, {
                '$unwind': {
                    'path': f'$unwind__{CollectionKey.RBAC_PRIVILEGE.model_name}',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$match': {
                    f'unwind__{CollectionKey.SYS_MENU.model_name}.sys_application_id': ObjectId(str(application_id).strip()),
                    f'unwind__{CollectionKey.SYS_MENU.model_name}.is_activated': True,
                    'menu_rbac_restricted_profil.rbac_profile_id': ObjectId(str(userProfil['id'])),
                    'menu_rbac_restricted_api_consumer.ref_api_consumer_id': ObjectId(str(apiConsumer['id'])),
                    'guard_rbac_restricted_profil.rbac_profile_id': ObjectId(str(userProfil['id'])),
                    'guard_rbac_restricted_api_consumer.ref_api_consumer_id': ObjectId(str(apiConsumer['id'])),
                    'menu_rbac_restricted_profil.is_hidden': False,
                    'menu_rbac_restricted_api_consumer.is_hidden': False,
                    'guard_rbac_restricted_profil.is_hidden': False,
                    'guard_rbac_restricted_api_consumer.is_hidden': False,
                    '$or': [
                        {
                            f'unwind__{CollectionKey.RBAC_ROLE.model_name}._id': ObjectId(user['rbac_role_id'])
                        }, {
                            'direct_privileges': {
                                '$ne': []
                            }
                        }
                    ]
                }
            }, {
                '$group': {
                    '_id': f'$unwind__{CollectionKey.SYS_MENU.model_name}._id',
                    'docs': {
                        '$push': {
                            '_id': '$_id',
                            f'unwind__{CollectionKey.SYS_MENU.model_name}': f'$unwind__{CollectionKey.SYS_MENU.model_name}',
                            f'unwind__{CollectionKey.RBAC_ROLE.model_name}': f'$unwind__{CollectionKey.RBAC_ROLE.model_name}',
                            f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}',
                            f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}': f'$unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}',
                            f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}': f'$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}',
                            'menu_rbac_restricted_api_consumer': '$menu_rbac_restricted_api_consumer',
                            'menu_rbac_restricted_profil': '$menu_rbac_restricted_profil',
                            'guard_rbac_restricted_api_consumer': '$guard_rbac_restricted_api_consumer',
                            'guard_rbac_restricted_profil': '$guard_rbac_restricted_profil',
                            'rbac_role_id': '$rbac_role_id',
                            'rbac_permission_id': '$rbac_permission_id'
                        }
                    }
                }
            }, {
                '$project': {
                    'merged': {
                        '$reduce': {
                            'input': '$docs',
                            'initialValue': {},
                            'in': {
                                '$mergeObjects': [
                                    '$$value', '$$this'
                                ]
                            }
                        }
                    }
                }
            }, {
                '$project': {
                    '_id': '$merged._id',
                    'rbac_permission_id': '$merged.rbac_permission_id',
                    'rbac_role_id': '$merged.rbac_role_id',
                    f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}': {
                        '_id': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}._id',
                        'path_guard': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.path_guard',
                        'path': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.path',
                        'targeted_id': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.targeted_id',
                        'sys_menu_id': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.sys_menu_id',
                        'sys_application_id': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.sys_application_id'
                    },
                    f'unwind__{CollectionKey.SYS_MENU.model_name}': {
                        '_id': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}._id',
                        'is_standalone': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.is_standalone',
                        'name': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.name',
                        'flag': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.flag',
                        'description_str': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.description_str',
                        "application_group_flag": f"$merged.unwind__{CollectionKey.SYS_MENU.model_name}.application_group_flag",
                        'sys_application_id': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.sys_application_id',
                        'sys_menu_id': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.sys_menu_id',
                        'order_by': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.order_by',
                        'is_skipable_menu_on_view': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.is_skipable_menu_on_view'
                    }
                }
            }, {
                '$sort': {
                    f'unwind__{CollectionKey.SYS_MENU.model_name}.order_by': 1
                }
            }
        ]

        infos = await generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
            output_data_type=output_data_type,
            accept_language=accept_language,
            pipeline=pipeline,
            all_data=True,
        )

        DebugService.app_debug_print(
            f"\n\n\n SUB MENU LN : {len(infos)} \n\n", True)
        
        # DEBUG: Print sample to check IDs
        if len(infos) > 0:
            sample = infos[0]
            m_id = sample.get('_id')
            p_id = sample.get(f'unwind__{CollectionKey.SYS_MENU.model_name}', {}).get('sys_menu_id')
            app_id_val = sample.get(f'unwind__{CollectionKey.SYS_MENU.model_name}', {}).get('sys_application_id')
            print(f"DEBUG: Sample Menu ID: {m_id}, Parent ID: {p_id}, App ID: {app_id_val}")
            print(f"DEBUG: Sample Keys: {sample.keys()}")
            
            # Check if any have a parent
            has_parent = [i for i in infos if i.get(f'unwind__{CollectionKey.SYS_MENU.model_name}', {}).get('sys_menu_id')]
            print(f"DEBUG: Items with parent: {len(has_parent)}")

        
        # ---------------------------------------------------------
        # OPTIMIZED BATCH FETCHING STRATEGY
        # ---------------------------------------------------------
        
        # 1. Collect Metadata from initial fetch
        menu_items_map = {}
        target_ids = []
        children_display_type_ids = []
        data_display_type_ids = []
        
        # Helper to get value from potential keys
        def get_value(d, keys):
            for k in keys:
                if k in d:
                    return d[k]
            return None

        # Key names
        sys_menu_key = f'unwind__{CollectionKey.SYS_MENU.model_name}'
        sys_menu_alt_key = 'sys_menu' # Based on debug logs
        path_guard_key = f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}'
        path_guard_alt_key = 'rbac_path_guard'

        for item in infos:
            sys_menu = get_value(item, [sys_menu_key, sys_menu_alt_key])
            if sys_menu:
                # Handle id/_id difference and data_table format (dict vs value)
                raw_id = sys_menu.get('_id') or sys_menu.get('id')
                menu_id = None
                if isinstance(raw_id, dict):
                    menu_id = raw_id.get('display_value') or raw_id.get('value') or raw_id.get('id')
                else:
                    menu_id = raw_id
                
                if menu_id:
                    target_ids.append(menu_id)
                    
                    # Helper to extract ID from potential dict
                    def get_id_val(val):
                        if isinstance(val, dict):
                            return val.get('display_value') or val.get('value') or val.get('id')
                        return val

                    # Collect display type IDs if present
                    if 'ref_children_display_type_id' in sys_menu and sys_menu['ref_children_display_type_id']:
                        val = get_id_val(sys_menu['ref_children_display_type_id'])
                        if val: children_display_type_ids.append(val)
                    if 'ref_data_display_type_id' in sys_menu and sys_menu['ref_data_display_type_id']:
                        val = get_id_val(sys_menu['ref_data_display_type_id'])
                        if val: data_display_type_ids.append(val)

                    # Initialize menu item entry
                    menu_items_map[str(menu_id)] = {
                        **sys_menu,
                        'id': sys_menu.get('id') if 'id' in sys_menu else menu_id, # Keep original structure if possible
                        '_id': menu_id, # Normalize
                        'sys_menu_id': get_id_val(sys_menu.get('sys_menu_id')), # Extract parent ID value
                        'ishidden': False,
                        'isactivated': True,
                        # Handle order_by if it's a dict
                        'order_by': get_id_val(sys_menu.get('order_by', 0)),
                        'rbac_path_guard': get_value(item, [path_guard_key, path_guard_alt_key]) or {},
                        'rbac_actions': [],
                        'rbac_components': [],
                        'sub_menus': [],
                    }
            else:
                print(f"DEBUG: Skipping item - No sys_menu found. Keys: {item.keys()}")

        unique_target_ids = list(set([str(i) for i in target_ids])) # Ensure strings for set
        DebugService.app_debug_print(f"DEBUG: Found {len(unique_target_ids)} unique menu IDs.", True)
        
        # 2. Batch Fetch Auxiliary Data (Parallel)
        # We fetch all related data for ALL menus in one go
        
        async def fetch_icons():
            # Find icons for these menus + current apiConsumer
            # Pipeline to match user_recursive_menu_children logic: 
            # Lookup CFG_ICON_API_CONSUMER where targeted_id IN menu_ids AND ref_api_consumer_id matches
            pipeline = [
                {
                    "$match": {
                        "targeted_id": {"$in": [ObjectId(i) for i in unique_target_ids]}
                    }
                },
                {
                    "$lookup": {
                        "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                        "localField": "_id",
                        "foreignField": "targeted_id",
                        "as": "restriction"
                    }
                },
                {
                    "$unwind": "$restriction"
                },
                {
                    "$match": {
                        "restriction.ref_api_consumer_id": ObjectId(apiConsumer['id'])
                    }
                },
                {
                    "$addFields": {
                        "lookup_icon_id": {"$ifNull": ["$ref_icon_id._id", "$ref_icon_id"]}
                    }
                },
                {
                    "$project": {
                        "targeted_id": 1,
                        "ref_icon_id": 1,
                        "lookup_icon_id": 1
                    }
                }
            ]
            DebugService.app_debug_print(f"DEBUG: Fetching icons for {len(unique_target_ids)} targets...", True)
            try:
                res = await generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
                    pipeline=pipeline,
                    all_data=True,
                    output_data_type=output_data_type,
                    accept_language=accept_language
                )
                DebugService.app_debug_print(f"DEBUG: Fetched {len(res)} icon configs.", True)
                return res
            except Exception as e:
                 DebugService.app_debug_print(f"DEBUG: Error fetching icons: {str(e)}", True)
                 return []

        async def fetch_actions():
            # Batch fetch actions for all these menus
            # Replicating the logic from 'rbac_actions_pipeline' but matching ANY of the target menu IDs
            
            pipeline = [
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                        'localField': '_id',
                        'foreignField': 'rbac_action_id',
                        'as': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
                    }
                },
                {
                    '$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.rbac_permission_id',
                        'foreignField': '_id',
                        'as': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
                    }
                },
                {
                    '$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                        'let': {'permissionId': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id'},
                        'pipeline': [
                            {
                                '$match': {
                                    '$expr': {
                                        '$and': [
                                            {'$eq': ['$rbac_permission_id',
                                             '$$permissionId']},
                                            {'$eq': ['$sys_user_id',
                                             ObjectId(user['id'])]},
                                            {'$eq': ['$status', 'added']}
                                        ]
                                    }
                                }
                            }
                        ],
                        'as': 'direct_privileges'
                    }
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION_ROLE.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id',
                        'foreignField': 'rbac_permission_id',
                        'as': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}_role'
                    }
                },
                {
                    '$unwind': {
                        'path': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}_role',
                        'preserveNullAndEmptyArrays': True
                    }
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_ROLE.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}_role.rbac_role_id',
                        'foreignField': '_id',
                        'as': f'unwind__{CollectionKey.RBAC_ROLE.model_name}'
                    }
                },
                {
                    '$unwind': {
                        'path': f'$unwind__{CollectionKey.RBAC_ROLE.model_name}',
                        'preserveNullAndEmptyArrays': True
                    }
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.SYS_MENU.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.targeted_id',
                        'foreignField': '_id',
                        'as': f'unwind__{CollectionKey.SYS_MENU.model_name}'
                    }
                },
                {
                    '$unwind': f'$unwind__{CollectionKey.SYS_MENU.model_name}'
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}._id',
                        'foreignField': 'targeted_id',
                        'as': f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}'
                    }
                },
                {
                    '$unwind': {
                        'path': f'$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}',
                        'preserveNullAndEmptyArrays': True
                    }
                },
                {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                        'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}._id',
                        'foreignField': 'targeted_id',
                        'as': f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}'
                    }
                },
                {
                    '$unwind': {
                        'path': f'$unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}',
                        'preserveNullAndEmptyArrays': True
                    }
                },
                {
                    '$match': {
                        '$or': [
                            {
                                f'unwind__{CollectionKey.RBAC_ROLE.model_name}._id': ObjectId(user['rbac_role_id']),
                                f'unwind__{CollectionKey.SYS_MENU.model_name}._id': {"$in": [ObjectId(i) for i in unique_target_ids]},
                                f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.rbac_profile_id': ObjectId(userProfil['id']),
                                f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id': ObjectId(apiConsumer['id'])
                            },
                            {
                                'direct_privileges': {'$ne': []},
                                f'unwind__{CollectionKey.SYS_MENU.model_name}._id': {"$in": [ObjectId(i) for i in unique_target_ids]},
                                f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.rbac_profile_id': ObjectId(userProfil['id']),
                                f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id': ObjectId(apiConsumer['id'])
                            }
                        ]
                    }
                },
                {
                    '$project': {
                        '_id': 1,
                        'is_standalone': 1,
                        'label': 1,
                        'flag': 1,
                        'hard_code_flag': 1,
                        'access_via': {
                            '$cond': [
                                {'$gt': [{'$size': '$direct_privileges'}, 0]},
                                'privilege',
                                'role'
                            ]
                        },
                        'menu_id': f'$unwind__{CollectionKey.SYS_MENU.model_name}._id'
                    }
                }
            ]
            
            return await generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_ACTION,
                output_data_type=output_data_type,
                accept_language=accept_language,
                pipeline=pipeline,
                all_data=True
            )

       
        async def noop():
            return None

        # Refined fetch tasks
        tasks = [
            fetch_icons(),
            generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.CFG_CHILDREN_DISPLAY_TYPE,
                pipeline=[{'$match': {'_id': {'$in': [ObjectId(i) for i in children_display_type_ids]}}}],
                all_data=True,
                output_data_type=output_data_type,
                accept_language=accept_language
            ) if children_display_type_ids else noop(),
            generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.CFG_DATA_DISPLAY_TYPE,
                pipeline=[{'$match': {'_id': {'$in': [ObjectId(i) for i in data_display_type_ids]}}}],
                all_data=True,
                output_data_type=output_data_type,
                accept_language=accept_language
            ) if data_display_type_ids else noop(),
             generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.REF_COLLECTION_CRUD_INFO,
                pipeline=[
                    {'$match': {'targeted_id': {'$in': [ObjectId(i) for i in unique_target_ids]}}},
                    # Lookup endpoint data
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_ENDPOINT.model_name}",
                            'let': {'endpoint_id': '$rbac_endpoint_id'},
                            'pipeline': [
                                {
                                    '$match': {
                                        '$expr': {'$eq': ['$_id', '$$endpoint_id']}
                                    }
                                },
                                {
                                    '$project': {
                                        '_id': 1,
                                        'url': 1,
                                        'label': 1,
                                        'flag': 1,
                                        'is_sudo_action': 1,
                                        'is_sudo_group_action': 1,
                                        'is_sudo_delegated_action': 1,
                                        'is_sudo_group_cross_validation_action': 1,
                                        'is_sudo_group_inter_organization_validation_action': 1,
                                    }
                                }
                            ],
                            'as': 'endpoints'
                        }
                    },
                    {'$unwind': {'path': '$endpoints', 'preserveNullAndEmptyArrays': True}},
                    {'$sort': {'order_by': 1}},
                    # Project with endpoint and exclude unnecessary fields
                    {
                        '$project': {
                            '_id': 1,
                            'targeted_id': 1,
                            'rbac_endpoint_id': 1,
                            'label': 1,
                            'flag': 1,
                            'hard_code_flag': 1,
                            'parent_field_name': 1,
                            'order_by': 1,
                            f'unwind__{CollectionKey.RBAC_ENDPOINT.model_name}': {
                                '_id': '$endpoints._id',
                                'url': '$endpoints.url',
                                'label': '$endpoints.label',
                                'flag': '$endpoints.flag',
                                'is_sudo_action': '$endpoints.is_sudo_action',
                                'is_sudo_group_action': '$endpoints.is_sudo_group_action',
                                'is_sudo_delegated_action': '$endpoints.is_sudo_delegated_action',
                                'is_sudo_group_cross_validation_action': '$endpoints.is_sudo_group_cross_validation_action',
                                'is_sudo_group_inter_organization_validation_action': '$endpoints.is_sudo_group_inter_organization_validation_action',
                            }
                        }
                    }
                ],
                all_data=True,
                output_data_type=output_data_type,
                accept_language=accept_language
            ),
            fetch_actions(),
        ]
        
        # We'll skip complex Action/Component/Restriction fetching for this optimization step 
        # to ensure stability, unless critical. 'infos' pipeline validates access.
        # Icons and Display Types are visual requirements.
        
        batch_results = await AsyncExecutor.gather_with_limit(tasks, limit=10)
        
        icons_data = batch_results[0] if batch_results[0] else []
        children_display_types = batch_results[1] if len(batch_results) > 1 and batch_results[1] else []
        data_display_types = batch_results[2] if len(batch_results) > 2 and batch_results[2] else []
        crud_info_list = batch_results[3] if len(batch_results) > 3 and batch_results[3] else []
        actions_list = batch_results[4] if len(batch_results) > 4 and batch_results[4] else []
        
        # 3. Process Batch Data into Maps
        # icon_cfg_list = icons_data
        
        # Helper to extract actual ID from potentially dict-wrapped or raw value
        def extract_id(val):
            if isinstance(val, dict):
                return str(val.get('display_value') or val.get('real_value') or val.get('id') or val.get('_id') or '')
            return str(val) if val else ''

        if icons_data:
            DebugService.app_debug_print(f"DEBUG: First icon config sample: {icons_data[0]}", True)

        # Build final Icon Map: targeted_id -> icon url payload
        icon_map = {}
        for menu_id, menu_data in menu_items_map.items():
            icon_payload = ApplicationService._build_svg_icon_payload(
                menu_or_app_data=menu_data,
                rbac_path_guard=menu_data.get('rbac_path_guard'),
                api_consumer_flag=apiConsumer.get('flag'),
            )
            if icon_payload:
                icon_map[menu_id] = icon_payload

        DebugService.app_debug_print(f"DEBUG: Mapped icons for {len(icon_map)} menus. Sample keys: {list(icon_map.keys())[:3]}", True)

        
        children_display_map = {extract_id(i.get('id') or i.get('_id')): i for i in children_display_types}
        data_display_map = {extract_id(i.get('id') or i.get('_id')): i for i in data_display_types}
        
        # CRUD Info Map: A menu can have multiple CRUD info entries
        crud_info_map = {}
        for crud_info in crud_info_list:
            tid = extract_id(crud_info.get('targeted_id'))
            if tid:
                if tid not in crud_info_map:
                    crud_info_map[tid] = []
                crud_info_map[tid].append(crud_info)
        
        # Actions Map: One menu can have multiple actions
        actions_map = {}
        for action in actions_list:
            m_id = extract_id(action.get('menu_id'))
            if m_id not in actions_map:
                actions_map[m_id] = []
            # Clean up temporary menu_id field from action object if desired, or keep it
            if 'menu_id' in action:
                del action['menu_id']
            actions_map[m_id].append(action)
        
        # 4. Attach Data to Menu Items
        DebugService.app_debug_print(f"DEBUG: menu_items_map keys: {list(menu_items_map.keys())[:5]}", True)
        DebugService.app_debug_print(f"DEBUG: icon_map keys: {list(icon_map.keys())[:5]}", True)
        
        for menu_id, menu_data in menu_items_map.items():
            # Icon
            if menu_id in icon_map:
                icon_detail = icon_map[menu_id]
                DebugService.app_debug_print(f"DEBUG: Found icon for menu {menu_id}: {icon_detail}", False)
                if icon_detail and 'icon' in icon_detail:
                     menu_data['icon'] = icon_detail['icon']
            else:
                DebugService.app_debug_print(f"DEBUG: NO icon for menu {menu_id}", True)
            
            # Display Types
            if 'ref_children_display_type_id' in menu_data:
                dt_id = extract_id(menu_data['ref_children_display_type_id'])
                if dt_id in children_display_map:
                    menu_data['ref_children_display_type'] = children_display_map[dt_id]
            
            if 'ref_data_display_type_id' in menu_data:
                dt_id = extract_id(menu_data['ref_data_display_type_id'])
                if dt_id in data_display_map:
                    menu_data['ref_data_display_type'] = data_display_map[dt_id]
            
            # CRUD Info - now a list of all entries
            if menu_id in crud_info_map:
                menu_data['collection_crud_info'] = crud_info_map[menu_id]
            
            # Actions
            if menu_id in actions_map:
                menu_data['rbac_actions'] = actions_map[menu_id]
                
        # 5. Build Tree
        root_items = []
        for menu_id, menu_data in menu_items_map.items():
            sys_menu_id = menu_data.get('sys_menu_id')
            parent_found = False
            
            if sys_menu_id:
                parent_id = str(sys_menu_id)
                if parent_id in menu_items_map:
                    menu_items_map[parent_id]['sub_menus'].append(menu_data)
                    parent_found = True
            
            if not parent_found:
                root_items.append(menu_data)
        
        # 6. Sort recursively
        def sort_menu_tree(items):
            items.sort(key=lambda x: x.get('order_by', 0) or 0)
            for item in items:
                if item['sub_menus']:
                    sort_menu_tree(item['sub_menus'])
                    
        sort_menu_tree(root_items)
        
        # 7. Use recursive function to fully populate sub_menus with all data
        # This approach from backup ensures nested children have collection_crud_info
        async def process_menu(menu):
            return await ApplicationService.user_recursive_menu_children(
                menu=menu,  # Pass original menu format from infos
                user=user,
                userProfil=userProfil,
                accept_language=accept_language,
                output_data_type=output_data_type,
                apiConsumer=apiConsumer,
            )
        
        # Execute all menu processing tasks concurrently
        results = await AsyncExecutor.gather_with_limit(
            [process_menu(menu) for menu in infos],
            limit=5,
            return_exceptions=True
        )
        
        # Filter out None results and exceptions
        formatted_data = [result for result in results if result is not None and not isinstance(result, Exception)]
        
        DebugService.app_debug_print(f"Optimized Menu Fetch: {len(formatted_data)} items from {len(infos)} initial.", True)
        return formatted_data
    
    @staticmethod
    async def get_user_menu_submenus(
            sys_menu_id: str,
            apiConsumer: dict,
            user: dict,
            userProfil: dict,
            page: int = 0,
            limit: int = 10,
            all_data: bool = False,
            accept_language: str = DEFAULT_LANGUAGE,
            output_data_type: OutputDataType = OutputDataType.DEFAULT):
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(accept_language)
 
        pipeline = [
            {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_ROLE.model_name}',
                    'localField': 'rbac_role_id',
                    'foreignField': '_id',
                    'as': f'unwind__{CollectionKey.RBAC_ROLE.model_name}'
                }
            }, {
                '$unwind': f'$unwind__{CollectionKey.RBAC_ROLE.model_name}'
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_PERMISSION.model_name}',
                    'localField': 'rbac_permission_id',
                    'foreignField': '_id',
                    'as': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
                }
            }, {
                '$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_PRIVILEGE.model_name}',
                    'let': {
                        'permissionId': '$rbac_permission_id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {
                                            '$eq': [
                                                '$rbac_permission_id', '$$permissionId'
                                            ]
                                        }, {
                                            '$eq': [
                                                '$sys_user_id', ObjectId(
                                                    user['id'])
                                            ]
                                        }, {
                                            '$eq': [
                                                '$status', 'added'
                                            ]
                                        }
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'direct_privileges'
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_PERMISSION_TARGET.model_name}',
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id',
                    'foreignField': 'rbac_permission_id',
                    'as': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
                }
            }, {
                '$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.SYS_MENU.model_name}',
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.targeted_id',
                    'foreignField': '_id',
                    'as': f'unwind__{CollectionKey.SYS_MENU.model_name}'
                }
            }, {
                '$unwind': f'$unwind__{CollectionKey.SYS_MENU.model_name}'
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_PATH_GUARD.model_name}',
                    'localField': f'unwind__{CollectionKey.SYS_MENU.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}'
                }
            }, {
                '$unwind': f'$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}'
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}',
                    'localField': f'unwind__{CollectionKey.SYS_MENU.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': 'menu_rbac_restricted_api_consumer'
                }
            }, {
                '$unwind': {
                    'path': '$menu_rbac_restricted_api_consumer',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}',
                    'localField': f'unwind__{CollectionKey.SYS_MENU.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': 'menu_rbac_restricted_profil'
                }
            }, {
                '$unwind': {
                    'path': '$menu_rbac_restricted_profil',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}',
                    'localField': f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': 'guard_rbac_restricted_api_consumer'
                }
            }, {
                '$unwind': {
                    'path': '$guard_rbac_restricted_api_consumer',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}',
                    'localField': f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': 'guard_rbac_restricted_profil'
                }
            }, {
                '$unwind': {
                    'path': '$guard_rbac_restricted_profil',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$lookup': {
                    'from': f'{CollectionKey.RBAC_PRIVILEGE.model_name}',
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id',
                    'foreignField': 'rbac_permission_id',
                    'as': f'unwind__{CollectionKey.RBAC_PRIVILEGE.model_name}'
                }
            }, {
                '$unwind': {
                    'path': f'$unwind__{CollectionKey.RBAC_PRIVILEGE.model_name}',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$match': {
                    f'unwind__{CollectionKey.SYS_MENU.model_name}.sys_menu_id': ObjectId(str(sys_menu_id).strip()),
                    f'unwind__{CollectionKey.SYS_MENU.model_name}.is_activated': True,
                    'menu_rbac_restricted_profil.rbac_profile_id': ObjectId(str(userProfil['id'])),
                    'menu_rbac_restricted_api_consumer.ref_api_consumer_id': ObjectId(str(apiConsumer['id'])),
                    'guard_rbac_restricted_profil.rbac_profile_id': ObjectId(str(userProfil['id'])),
                    'guard_rbac_restricted_api_consumer.ref_api_consumer_id': ObjectId(str(apiConsumer['id'])),
                    'menu_rbac_restricted_profil.is_hidden': False,
                    'menu_rbac_restricted_api_consumer.is_hidden': False,
                    'guard_rbac_restricted_profil.is_hidden': False,
                    'guard_rbac_restricted_api_consumer.is_hidden': False,
                    '$or': [
                        {
                            f'unwind__{CollectionKey.RBAC_ROLE.model_name}._id': ObjectId(user['rbac_role_id'])
                        }, {
                            'direct_privileges': {
                                '$ne': []
                            }
                        }
                    ]
                }
            }, {
                '$group': {
                    '_id': f'$unwind__{CollectionKey.SYS_MENU.model_name}._id',
                    'docs': {
                        '$push': {
                            '_id': '$_id',
                            f'unwind__{CollectionKey.SYS_MENU.model_name}': f'$unwind__{CollectionKey.SYS_MENU.model_name}',
                            f'unwind__{CollectionKey.RBAC_ROLE.model_name}': f'$unwind__{CollectionKey.RBAC_ROLE.model_name}',
                            f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}',
                            f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}': f'$unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}',
                            f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}': f'$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}',
                            'menu_rbac_restricted_api_consumer': '$menu_rbac_restricted_api_consumer',
                            'menu_rbac_restricted_profil': '$menu_rbac_restricted_profil',
                            'guard_rbac_restricted_api_consumer': '$guard_rbac_restricted_api_consumer',
                            'guard_rbac_restricted_profil': '$guard_rbac_restricted_profil',
                            'rbac_role_id': '$rbac_role_id',
                            'rbac_permission_id': '$rbac_permission_id'
                        }
                    }
                }
            }, {
                '$project': {
                    'merged': {
                        '$reduce': {
                            'input': '$docs',
                            'initialValue': {},
                            'in': {
                                '$mergeObjects': [
                                    '$$value', '$$this'
                                ]
                            }
                        }
                    }
                }
            }, {
                '$project': {
                    '_id': '$merged._id',
                    'rbac_permission_id': '$merged.rbac_permission_id',
                    'rbac_role_id': '$merged.rbac_role_id',
                    f'unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}': {
                        '_id': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}._id',
                        'path_guard': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.path_guard',
                        'path': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.path',
                        'targeted_id': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.targeted_id',
                        'sys_menu_id': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.sys_menu_id',
                        'sys_application_id': f'$merged.unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.sys_application_id'
                    },
                    f'unwind__{CollectionKey.SYS_MENU.model_name}': {
                        '_id': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}._id',
                        'is_standalone': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.is_standalone',
                        'name': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.name',
                        'flag': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.flag',
                        "application_group_flag": f"$merged.unwind__{CollectionKey.SYS_MENU.model_name}.application_group_flag",
                        'description_str': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.description_str',
                        'sys_application_id': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.sys_application_id',
                        'sys_menu_id': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.sys_menu_id',
                        'order_by': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.order_by',
                        'is_skipable_menu_on_view': f'$merged.unwind__{CollectionKey.SYS_MENU.model_name}.is_skipable_menu_on_view'
                    }
                }
            }, {
                '$sort': {
                    f'unwind__{CollectionKey.SYS_MENU.model_name}.order_by': 1
                }
            }
        ]

        infos = await generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
            output_data_type=output_data_type,
            accept_language=accept_language,
            pipeline=pipeline,
            all_data=True,
        )

        DebugService.app_debug_print(
            f"\n\n\n SUB MENU LN : {len(infos)} \n\n", True)
        
        # Process all menus in parallel using asyncio.gather for non-blocking execution
        async def process_menu(menu):
            return await ApplicationService.user_recursive_menu_children(
                menu=menu,
                user=user,
                userProfil=userProfil,
                accept_language=accept_language,
                output_data_type=output_data_type,
                apiConsumer=apiConsumer,
            )
        
        # Execute all menu processing tasks with concurrency limit
        results = await AsyncExecutor.gather_with_limit(
            [process_menu(menu) for menu in infos],
            limit=5,  # Limit to 5 concurrent to prevent overwhelming DB
            return_exceptions=True
        )
        
        # Filter out None results and exceptions
        formatted_data = [result for result in results if result is not None and not isinstance(result, Exception)]

        # Now, sort formatted_data by 'order_by' ascending:
        DebugService.app_debug_print(
            f"\n\n formatted_data SUB MENU > : {len(formatted_data)}\n\n", False)
        # formatted_data.sort(key=lambda item: item['order_by'])
        # DebugService.app_debug_print(f"\n\n ordered SUB MENU: {len(formatted_data)}\n\n",True)
        return formatted_data

    @staticmethod
    async def get_application_submenus_config(
            application_id: str,
            apiConsumer: dict,
            page: int = 0,
            limit: int = 200,
            all_data: bool = False,
            accept_language: str = DEFAULT_LANGUAGE,
            output_data_type: OutputDataType = OutputDataType.DEFAULT):
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(accept_language)
        pipeline = [
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PATH_GUARD.model_name}",
                    'localField': "_id",
                    'foreignField': "targeted_id",
                    'as': f"unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}"
                }
            },
            # {
            #     '$unwind': {
            #         "path": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}",
            #         "preserveNullAndEmptyArrays": False
            #     }
            # },
            {
                "$match": {
                    "sys_application_id": ObjectId(str(application_id).strip()),

                }
            },
            # Group by the sys_menu _id and push matching documents into an array field "docs"
            {
                "$group": {
                    "_id": "$_id",
                    "docs": {"$push": "$$ROOT"}
                }
            },
            # Merge the array of documents into one object per group.
            {
                "$project": {
                    "merged": {
                        "$reduce": {
                            "input": "$docs",
                            "initialValue": {},
                            "in": {"$mergeObjects": ["$$value", "$$this"]}
                        }
                    }
                }
            },
            # Replace the root with the merged document so that fields are at the top level.
            {
                "$replaceRoot": {"newRoot": "$merged"}
            },
            {
                "$sort": {
                    "order_by": 1
                }
            },
            # Apply limit to reduce memory usage
            {
                "$limit": 100
            }
        ]

        infos = await generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.SYS_MENU,
            output_data_type=output_data_type,
            accept_language=accept_language,
            pipeline=pipeline,
            all_data=True
        )
        formatted_data = []
        # RESURSIVE FX

        async def recursive_menu_children(menu):
            try:
             # getch icon
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    targeted_id = menu['id']['display_value']
                    order_by = menu['order_by']['display_value']
                elif output_data_type == OutputDataType.DEFAULT.value:
                    targeted_id = menu['id']
                    order_by = menu['order_by']
                elif output_data_type == OutputDataType.TREE.value:
                    targeted_id = menu['id']
                    order_by = index
                else:
                    order_by = index
                    targeted_id: None

                DebugService.app_debug_print(
                    f"output_data_type : {output_data_type}")
                nested_icon_pipeline = [
                    {
                        "$lookup": {
                            "from": "rbac_restricted_api_consumer",
                            "localField": "_id",
                            "foreignField": "targeted_id",
                            "as": f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}"
                        }
                    },
                    {
                        "$unwind": {
                            "path": f"$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                            "preserveNullAndEmptyArrays": True
                        }
                    },
                    {
                        "$match": {
                            "targeted_id": ObjectId(targeted_id),
                            f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id": ObjectId(apiConsumer['id']),
                        }
                    },
                    {
                        "$project": {
                            "id": "$_id",
                            "ref_icon_id": "$ref_icon_id",
                            "rbac_permission_id": "$rbac_permission_id",
                            "targeted_id": "$targeted_id",
                        }
                    }
                ]
                nested_icon = await generic_service.fetch_native_aggregate_one_from_collection(
                    collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=accept_language,
                    pipeline=nested_icon_pipeline
                )

                list_of_formated_rbac_path_guard = []
                for guard in menu['rbac_path_guard']:
                    if output_data_type == OutputDataType.DATA_TABLE.value:
                        guard_targeted_id = guard['id']['display_value']
                    elif output_data_type == OutputDataType.DEFAULT.value:
                        guard_targeted_id = guard['id']
                    elif output_data_type == OutputDataType.TREE.value:
                        guard_targeted_id = guard['id']
                    else:
                        order_by = index
                        guard_targeted_id: None

                    list_of_guard_restricted_profils = await generic_service.fetch_native_aggregate_data_from_collection(
                        collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                        output_data_type=output_data_type,
                        accept_language=accept_language,
                        pipeline=[
                            {
                                "$match": {
                                    "targeted_id": ObjectId(str(guard_targeted_id)),
                                }
                            },
                            {
                                "$project": {
                                    "_id": 1,
                                    "rbac_profile_id": 1,
                                    "targeted_id": 1,
                                    "is_activated": 1,
                                    "is_hidden": 1
                                }
                            },
                            {
                                "$limit": 10  # Limit the number of results to reduce memory usage
                            }
                        ],
                        all_data=True
                    )

                    list_of_guard_restricted_platforms = await generic_service.fetch_native_aggregate_data_from_collection(
                        collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                        output_data_type=output_data_type,
                        accept_language=accept_language,
                        pipeline=[
                            {
                                "$match": {
                                    "targeted_id": ObjectId(str(guard_targeted_id)),
                                }
                            },
                            {
                                "$project": {
                                    "_id": 1,
                                    "ref_api_consumer_id": 1,
                                    "targeted_id": 1,
                                    "is_activated": 1,
                                    "is_hidden": 1
                                }
                            },
                            {
                                "$limit": 10  # Limit the number of results to reduce memory usage
                            }
                        ],
                        all_data=True
                    )

                    guard_current_item = {
                        **guard,
                        'restricted_platform': list_of_guard_restricted_platforms,
                        'restricted_profil': list_of_guard_restricted_profils,
                    }
                    # if '6814439bea8b6de2e293700c' == str(targeted_id):
                    #     print(f"\n\n\n\n\n\n\n\n\n\n >>>>>>> guard : {guard['path']} current_item : {guard_current_item['restricted_platform']}\n\n")
                    # print(f"\n\n\n\n\n\n\n\n\n\n >>>>>>> current_item : {current_item['restricted_platform']}\n\n")
                    list_of_formated_rbac_path_guard.append(guard_current_item)

                # Use a more efficient approach - fetch only necessary fields
                list_of_restricted_profils = await generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type=output_data_type,
                    accept_language=accept_language,
                    pipeline=[
                        {
                            "$match": {
                                "targeted_id": ObjectId(str(targeted_id)),
                            }
                        },
                        {
                            "$project": {
                                "_id": "$_id",
                                "targeted_id": "$targeted_id",
                                "is_hidden": "$is_hidden",
                                "is_locked": "$is_locked",
                                "is_activated": "$is_activated",
                                "rbac_profile_id": "$rbac_profile_id",
                            }
                        }
                    ],
                    all_data=True
                )
                list_of_restricted_platforms = await generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                    output_data_type=output_data_type,
                    accept_language=accept_language,
                    pipeline=[
                        {
                            "$match": {
                                "targeted_id": ObjectId(str(targeted_id)),
                            }
                        },
                        {
                            "$project": {
                                "_id": "$_id",
                                "targeted_id": "$targeted_id",
                                "is_hidden": "$is_hidden",
                                "is_locked": "$is_locked",
                                "is_activated": "$is_activated",
                                "ref_api_consumer_id": "$ref_api_consumer_id",
                            }
                        }
                    ],
                    all_data=True
                )

                current_item = {
                    **menu,
                    'order_by': order_by,
                    'restricted_platform': list_of_restricted_platforms,
                    'restricted_profil': list_of_restricted_profils,
                    'rbac_path_guard': list_of_formated_rbac_path_guard,
                    'sub_menus': []
                }

                icon_payload = ApplicationService._build_svg_icon_payload(
                    menu_or_app_data=menu,
                    rbac_path_guard=list_of_formated_rbac_path_guard,
                    api_consumer_flag=apiConsumer.get('flag'),
                )
                if icon_payload:
                    current_item = {
                        **current_item,
                        **icon_payload,
                    }
                # CHECK CHILDREN
                list_of_children = []
                sub_menu_pipeline = [
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PATH_GUARD.model_name}",
                            'localField': "_id",
                            'foreignField': "targeted_id",
                            'as': f"unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}"
                        }
                    },

                    {
                        "$match": {
                            "sys_menu_id": ObjectId(targeted_id)
                        }
                    },
                    # Group by the sys_menu _id and push matching documents into an array field "docs"
                    {
                        "$group": {
                            "_id": "$_id",
                            "docs": {
                                "$push": {
                                    "_id": "$_id",
                                    "rbac_role_id": "$rbac_role_id",
                                    "rbac_permission_id": "$rbac_permission_id",
                                    "name": "$name",
                                    "flag": "$flag",
                                    "order_by": "$order_by",
                                    "application_group_flag": "$application_group_flag",
                                    "sys_application_id": "$sys_application_id",
                                    "sys_menu_id": "$sys_menu_id",
                                    "is_standalone": "$is_standalone",
                                    f"unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}"
                                }
                            }
                        }
                    },
                    # Merge the array of documents into one object per group.
                    {
                        "$project": {
                            "merged": {
                                "$reduce": {
                                    "input": "$docs",
                                    "initialValue": {},
                                    "in": {"$mergeObjects": ["$$value", "$$this"]}
                                }
                            }
                        }
                    },
                    # Replace the root with the merged document so that fields are at the top level.
                    {
                        "$replaceRoot": {"newRoot": "$merged"}
                    },
                    {
                        "$sort": {
                            "order_by": 1
                        }
                    },
                    # Apply limit to reduce memory usage
                    {
                        "$limit": 50
                    }
                ]
                # Get children for current menu item
                children = await generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.SYS_MENU,
                    output_data_type=output_data_type,
                    accept_language=accept_language,
                    pipeline=sub_menu_pipeline,
                    all_data=True
                )

                # Process children recursively
                for sub_menu in children:
                    child_menu = await recursive_menu_children(sub_menu)
                    if child_menu:
                        list_of_children.append(child_menu)

                # Return the current menu with its children
                return {
                    **current_item,
                    "sub_menus": list_of_children
                }
            except Exception as e:
                print(f"\n\n\n error : {e}\n\n")
                return None

        for index, menu in enumerate(infos):
            formated_sub_menu = await recursive_menu_children(menu)
            if formated_sub_menu:
                formatted_data.append(formated_sub_menu)

        # print(f"\n\n\n formatted_data >>>>< : {len(formatted_data)}\n\n")
        # Now, sort formatted_data by 'order_by' ascending:
        formatted_data.sort(key=lambda item: item['order_by'])
        return formatted_data

    @staticmethod
    async def get_config_standalone_menus(
            apiConsumer: dict,
            page: int = 0,
            limit: int = 100,
            all_data: bool = False,
            accept_language: str = DEFAULT_LANGUAGE,
            output_data_type: OutputDataType = OutputDataType.DEFAULT):
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(accept_language)
        pipeline = [
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PATH_GUARD.model_name}",
                    'localField': "_id",
                    'foreignField': "targeted_id",
                    'as': f"unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}"
                }
            },
            {
                "$match": {
                    "is_standalone": True,
                }
            },
            {
                "$group": {
                    "_id": "$_id",
                    "docs": {
                        "$push": {
                            "_id": "$_id",
                            "name": "$name",
                            "order_by": "$order_by",
                            "application_group_flag": "$application_group_flag",
                            "sys_application_id": "$sys_application_id",
                            "sys_menu_id": "$sys_menu_id",
                            "is_standalone": "$is_standalone",
                            f"unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}"
                        }
                    }
                }
            },
            {
                "$project": {
                    "merged": {
                        "$reduce": {
                            "input": "$docs",
                            "initialValue": {},
                            "in": {"$mergeObjects": ["$$value", "$$this"]}
                        }
                    }
                }
            },
            {
                "$replaceRoot": {"newRoot": "$merged"}
            },
            {
                "$sort": {
                    "order_by": 1
                }
            },
            {
                "$skip": limit * page
            },
            {
                "$limit": limit
            }
        ]

        infos = await generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.SYS_MENU,
            output_data_type=output_data_type,
            accept_language=accept_language,
            pipeline=pipeline,
            all_data=True
        )
        formatted_data = []

        print(f"\n\n\n infos standalone menu : {len(infos)}\n\n")

        # RESURSIVE FX
        async def recursive_menu_children(menu):
            try:
             # getch icon
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    targeted_id = menu['id']['display_value']
                    order_by = menu['order_by']['display_value']
                elif output_data_type == OutputDataType.DEFAULT.value:
                    targeted_id = menu['id']
                    order_by = menu['order_by']
                elif output_data_type == OutputDataType.TREE.value:
                    targeted_id = menu['id']
                    order_by = index
                else:
                    order_by = index
                    targeted_id: None

                DebugService.app_debug_print(
                    f"output_data_type : {output_data_type}")
                nested_icon_pipeline = [
                    {
                        "$lookup": {
                            "from": "rbac_restricted_api_consumer",
                            "localField": "_id",
                            "foreignField": "targeted_id",
                            "as": f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}"
                        }
                    },
                    {
                        "$unwind": {
                            "path": f"$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                            "preserveNullAndEmptyArrays": True
                        }
                    },
                    {
                        "$match": {
                            "targeted_id": ObjectId(targeted_id),
                            f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id": ObjectId(apiConsumer['id']),
                        }
                    },
                    {
                        "$project": {
                            "id": "$_id",
                            "ref_icon_id": "$ref_icon_id",
                            "rbac_permission_id": "$rbac_permission_id",
                            "targeted_id": "$targeted_id",
                        }
                    }
                ]
                nested_icon = await generic_service.fetch_native_aggregate_one_from_collection(
                    collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=accept_language,
                    pipeline=nested_icon_pipeline
                )

                list_of_formated_rbac_path_guard = []
                for guard in menu['rbac_path_guard']:
                    if output_data_type == OutputDataType.DATA_TABLE.value:
                        guard_targeted_id = guard['id']['display_value']
                    elif output_data_type == OutputDataType.DEFAULT.value:
                        guard_targeted_id = guard['id']
                    elif output_data_type == OutputDataType.TREE.value:
                        guard_targeted_id = guard['id']
                    else:
                        order_by = index
                        guard_targeted_id: None

                    # Use fetch_one_from_collection instead of fetch_native_aggregate_data_from_collection
                    # to avoid validation issues with RbacPermissionRoleModel
                    list_of_guard_restricted_profils = await generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                        output_data_type=output_data_type,
                        accept_language=accept_language,
                        query={
                            "filter__targeted_id": str(guard_targeted_id),
                        },
                        all_data=True,
                    )

                    # Use fetch_data_from_collection instead of fetch_native_aggregate_data_from_collection
                    # to avoid validation issues with RbacPermissionRoleModel
                    list_of_guard_restricted_platforms = await generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                        output_data_type=output_data_type,
                        accept_language=accept_language,
                        query={
                            "filter__targeted_id": str(guard_targeted_id),
                        },
                        all_data=True,
                    )

                    list_of_formated_rbac_path_guard.append({
                        **guard,
                        'restricted_platform': list_of_guard_restricted_platforms,
                        'restricted_profil': list_of_guard_restricted_profils,
                    })

                # Use fetch_data_from_collection instead of fetch_native_aggregate_data_from_collection
                # to avoid validation issues with RbacPermissionRoleModel
                list_of_restricted_profils = await generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type=output_data_type,
                    accept_language=accept_language,
                    query={
                        "filter__targeted_id": str(targeted_id),
                    },
                    all_data=True,
                )
                # Use fetch_data_from_collection instead of fetch_native_aggregate_data_from_collection
                # to avoid validation issues with RbacPermissionRoleModel
                list_of_restricted_platforms = await generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                    output_data_type=output_data_type,
                    accept_language=accept_language,
                    query={
                        "filter__targeted_id": str(targeted_id),
                    },
                    all_data=True,
                )

                current_item = {
                    **menu,
                    'order_by': order_by,
                    'restricted_platform': list_of_restricted_platforms,
                    'restricted_profil': list_of_restricted_profils,
                    'rbac_path_guard': list_of_formated_rbac_path_guard,
                    'sub_menus': []
                }

                icon_payload = ApplicationService._build_svg_icon_payload(
                    menu_or_app_data=menu,
                    rbac_path_guard=list_of_formated_rbac_path_guard,
                    api_consumer_flag=apiConsumer.get('flag'),
                )
                if icon_payload:
                    current_item = {
                        **current_item,
                        **icon_payload,
                    }
                # CHECK CHILDREN
                list_of_children = []
                sub_menu_pipeline = [
                    {
                        '$lookup': {
                            'from': f"{CollectionKey.RBAC_PATH_GUARD.model_name}",
                            'localField': "_id",
                            'foreignField': "targeted_id",
                            'as': f"unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}"
                        }
                    },

                    {
                        "$match": {
                            "sys_menu_id": ObjectId(targeted_id)
                        }
                    },
                    # Group by the sys_menu _id and push matching documents into an array field "docs"
                    {
                        "$group": {
                            "_id": "$_id",
                            "docs": {"$push": "$$ROOT"}
                        }
                    },
                    # Merge the array of documents into one object per group.
                    {
                        "$project": {
                            "merged": {
                                "$reduce": {
                                    "input": "$docs",
                                    "initialValue": {},
                                    "in": {"$mergeObjects": ["$$value", "$$this"]}
                                }
                            }
                        }
                    },
                    # Replace the root with the merged document so that fields are at the top level.
                    {
                        "$replaceRoot": {"newRoot": "$merged"}
                    },
                    {
                        "$sort": {
                            "order_by": 1
                        }
                    },
                    # Apply limit to reduce memory usage
                    {
                        "$limit": 50
                    }
                ]
                # Get children for current menu item
                children = await generic_service.fetch_native_aggregate_data_from_collection(
                    collection_key=CollectionKey.SYS_MENU,
                    output_data_type=output_data_type,
                    accept_language=accept_language,
                    pipeline=sub_menu_pipeline,
                    all_data=True
                )

                # Process children recursively
                for sub_menu in children:
                    child_menu = await recursive_menu_children(sub_menu)
                    if child_menu:
                        list_of_children.append(child_menu)

                # Return the current menu with its children
                return {
                    **current_item,
                    "sub_menus": list_of_children
                }
            except Exception as e:
                print(f"\n\n\n error : {e}\n\n")
                return None

        for index, menu in enumerate(infos):
            formated_sub_menu = await recursive_menu_children(menu)
            if formated_sub_menu:
                formatted_data.append(formated_sub_menu)

        # print(f"\n\n\n formatted_data >>>>< : {len(formatted_data)}\n\n")
        # Now, sort formatted_data by 'order_by' ascending:
        formatted_data.sort(key=lambda item: item['order_by'])
        return formatted_data

    @staticmethod
    async def user_recursive_menu_children(menu: dict, user: dict, userProfil: dict, apiConsumer: dict, output_data_type: OutputDataType, accept_language: str = DEFAULT_LANGUAGE, index=0) -> Optional[Dict[str, Any]]:
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(accept_language)
        DebugService.app_debug_print(
            f"\n\n\n menu >  : {menu['rbac_path_guard']} \n\n\n", False)
        # DebugService.app_debug_print(f"\n\n\n menu >  : {menu} \n\n\n",False)
        # return None
        # getch icon
        if output_data_type == OutputDataType.DATA_TABLE.value:
            targeted_id = menu['sys_menu']['id']['display_value']
            order_by = menu['sys_menu']['order_by']['display_value']
        elif output_data_type == OutputDataType.DEFAULT.value:
            targeted_id = menu['sys_menu']['id']
            order_by = menu['sys_menu']['order_by']
        elif output_data_type == OutputDataType.TREE.value:
            targeted_id = menu['sys_menu']['id']
            order_by = index
        else:
            order_by = index
            targeted_id: None

        nested_icon_pipeline = [
            {
                "$lookup": {
                    "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "localField": "_id",
                    "foreignField": "targeted_id",
                    "as": f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}"
                }
            },
            {
                "$unwind": {
                    "path": f"$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$match": {
                    "targeted_id": ObjectId(targeted_id),
                    f"unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id": ObjectId(apiConsumer['id']),
                }
            },
            {
                "$project": {
                    "id": "$_id",
                    "ref_icon_id": "$ref_icon_id",
                    "rbac_permission_id": "$rbac_permission_id",
                    "targeted_id": "$targeted_id",
                }
            }
        ]

        # Build double_check_pipeline here to run in parallel with initial queries
        double_check_pipeline = [
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                    'localField': 'rbac_permission_id',
                    'foreignField': '_id',
                    'as': 'permissions'
                }
            }, {
                '$unwind': '$permissions'
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                    'let': {
                        'permissionId': '$permissions._id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {'$eq': ['$rbac_permission_id', '$$permissionId']},
                                        {'$eq': ['$sys_user_id', ObjectId(user['id'])]},
                                        {'$eq': ['$status', 'added']}
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'direct_privileges'
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                    'localField': 'permissions._id',
                    'foreignField': 'rbac_permission_id',
                    'as': 'permission_targets'
                }
            }, {
                '$unwind': {
                    'path': '$permission_targets',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.SYS_MENU.model_name}",
                    'localField': 'permission_targets.targeted_id',
                    'foreignField': '_id',
                    'as': 'menus'
                }
            }, {
                '$unwind': {
                    'path': '$menus',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$match': {
                    'menus._id': ObjectId(targeted_id)
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    'let': {'menu_id': '$menus._id'},
                    'pipeline': [
                        {'$match': {'$expr': {'$eq': ['$targeted_id', '$$menu_id']}}},
                        {'$match': {'ref_api_consumer_id': ObjectId(apiConsumer['id'])}},
                        {'$project': {'_id': 1, 'is_hidden': 1, 'is_activated': 1, 'is_locked': 1, 'ref_api_consumer_id': 1}}
                    ],
                    'as': 'api_consumers'
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                    'let': {'menu_id': '$menus._id'},
                    'pipeline': [
                        {'$match': {'$expr': {'$eq': ['$targeted_id', '$$menu_id']}}},
                        {'$match': {'rbac_profile_id': ObjectId(userProfil['id'])}},
                        {'$project': {'_id': 1, 'is_hidden': 1, 'is_activated': 1, 'is_locked': 1, 'rbac_profile_id': 1}}
                    ],
                    'as': 'profiles'
                }
            }, {
                '$match': {
                    '$or': [
                        {
                            'rbac_role_id': ObjectId(user['rbac_role_id']),
                            'api_consumers': {'$ne': []},
                            'profiles': {'$ne': []},
                            'permissions._id': {'$exists': True}
                        }, {
                            'direct_privileges': {'$ne': []},
                            'api_consumers': {'$ne': []},
                            'profiles': {'$ne': []}
                        }
                    ]
                }
            }, {
                '$group': {
                    '_id': '$menus._id',
                    'result': {
                        '$first': {
                            '_id': '$_id',
                            'rbac_role_id': '$rbac_role_id',
                            'rbac_permission_id': '$rbac_permission_id',
                            'rbac_restricted_api_consumer': {'$arrayElemAt': ['$api_consumers', 0]},
                            'rbac_restricted_profil': {'$arrayElemAt': ['$profiles', 0]},
                            'has_privilege': {'$gt': [{'$size': '$direct_privileges'}, 0]}
                        }
                    }
                }
            }, {
                '$replaceRoot': {'newRoot': '$result'}
            }
        ]

        # Parallelize ALL initial fetch calls
        single_menu_profil, single_menu_api_consumer, double_check_info = await AsyncExecutor.gather([
            # generic_service.fetch_native_aggregate_one_from_collection(
            #     collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
            #     output_data_type=OutputDataType(output_data_type).value,
            #     accept_language=accept_language,
            #     pipeline=nested_icon_pipeline
            # ),
            generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=accept_language,
                query={
                    "filter__targeted_id": targeted_id,
                },
            ),
            generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=accept_language,
                query={
                    "filter__targeted_id": targeted_id,
                },
            ),
            generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=accept_language,
                pipeline=double_check_pipeline
            ),
        ])
        DebugService.app_debug_print(f" step 1", True)
        is_hidden = True
        is_activated = False
        if single_menu_profil and single_menu_api_consumer:
            profil_is_hidden = single_menu_profil['is_hidden']
            profil_is_activated = single_menu_profil['is_activated']

            api_consumer_is_hidden = single_menu_api_consumer['is_hidden']
            api_consumer_is_activated = single_menu_api_consumer['is_activated']

            if profil_is_hidden == False and api_consumer_is_hidden == False:
                is_hidden = False

            if profil_is_activated == True and api_consumer_is_activated == True:
                is_activated = True

        # double_check_info already fetched in parallel above - process the result
        DebugService.app_debug_print(f" step 2", False)
        # START REDIS
        if double_check_info and len(double_check_info) > 0:
            single_info = double_check_info[0]
            if 'rbac_restricted_profil' in single_info:
                restricted_profil = single_info['rbac_restricted_profil']
                if restricted_profil['is_locked'] == True or restricted_profil['is_activated'] == False:
                    is_activated = False

            if 'rbac_restricted_profil' in single_info:
                restricted_profil = single_info['rbac_restricted_profil']
                if restricted_profil['is_hidden'] == False:
                    is_hidden = False

            if 'rbac_restricted_api_consumer' in single_info:
                restricted_api_consumer = single_info['rbac_restricted_api_consumer']
                if restricted_api_consumer['is_locked'] == True or restricted_api_consumer['is_activated'] == False:
                    is_activated = False

            if 'rbac_restricted_api_consumer' in single_info:
                if restricted_api_consumer['is_hidden'] == False:
                    is_hidden = False
        else:
            is_activated = False

        # # SKIP IF HIDDEN
        if is_hidden:
            return None

        # RBAC COMPONENTS
        rbac_components_pipeline = [
            # // Lookup permission targets
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                    'localField': '_id',
                    'foreignField': 'rbac_component_id',
                    'as': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
                }
            },
            {
                '$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
            },
            # // Lookup permissions
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.rbac_permission_id',
                    'foreignField': '_id',
                    'as': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
                }
            },
            {
                '$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
            },
            # // Lookup direct privileges for these permissions
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                    'let': {'permissionId': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id'},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {'$eq': ['$rbac_permission_id',
                                         '$$permissionId']},
                                        {'$eq': ['$sys_user_id',
                                         ObjectId(user['id'])]},
                                        {'$eq': ['$status', 'added']}
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'direct_privileges'
                }
            },
            # // Lookup permission roles (for role-based access)
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PERMISSION_ROLE.model_name}",
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id',
                    'foreignField': 'rbac_permission_id',
                    'as': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}_role'
                }
            },
            {
                '$unwind': {
                    'path': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}_role',
                    'preserveNullAndEmptyArrays': True
                }
            },
            # // Lookup roles
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_ROLE.model_name}",
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}_role.rbac_role_id',
                    'foreignField': '_id',
                    'as': f'unwind__{CollectionKey.RBAC_ROLE.model_name}'
                }
            },
            {
                '$unwind': {
                    'path': f'$unwind__{CollectionKey.RBAC_ROLE.model_name}',
                    'preserveNullAndEmptyArrays': True
                }
            },
            # // Lookup menu
            {
                '$lookup': {
                    'from': f"{CollectionKey.SYS_MENU.model_name}",
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.targeted_id',
                    'foreignField': '_id',
                    'as': f'unwind__{CollectionKey.SYS_MENU.model_name}'
                }
            },
            {
                '$unwind': f'$unwind__{CollectionKey.SYS_MENU.model_name}'
            },
            # // Lookup API consumer restrictions
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}'
                }
            },
            {
                '$unwind': {
                    'path': f'$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}',
                    'preserveNullAndEmptyArrays': True
                }
            },
            # // Lookup profile restrictions
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}'
                }
            },
            {
                '$unwind': {
                    'path': f'$unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}',
                    'preserveNullAndEmptyArrays': True
                }
            },
            # // Final matching - handles both role-based and privilege-based access
            {
                '$match': {
                    '$or': [
                        # // Role-based access path
                        {
                            f'unwind__{CollectionKey.RBAC_ROLE.model_name}._id': ObjectId(user['rbac_role_id']),
                            f'unwind__{CollectionKey.SYS_MENU.model_name}._id': ObjectId(targeted_id),
                            f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.rbac_profile_id': ObjectId(userProfil['id']),
                            f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id': ObjectId(apiConsumer['id'])
                        },
                        # // Privilege-based access path
                        {
                            'direct_privileges': {'$ne': []},
                            f'unwind__{CollectionKey.SYS_MENU.model_name}._id': ObjectId(targeted_id),
                            f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.rbac_profile_id': ObjectId(userProfil['id']),
                            f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id': ObjectId(apiConsumer['id'])
                        }
                    ]
                }
            },
            # // Projection
            {
                '$project': {
                    '_id': 1,
                    'is_standalone': 1,
                    'label': 1,
                    'flag': 1,
                    'hard_code_flag': 1,
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
        
        # RBAC ACTIONS
        rbac_actions_pipeline = [
            # // Lookup permission targets
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                    'localField': '_id',
                    'foreignField': 'rbac_action_id',
                    'as': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
                }
            },
            {
                '$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}'
            },
            # // Lookup permissions
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.rbac_permission_id',
                    'foreignField': '_id',
                    'as': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
                }
            },
            {
                '$unwind': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}'
            },
            # // Lookup direct privileges for these permissions
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                    'let': {'permissionId': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id'},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {'$eq': ['$rbac_permission_id',
                                         '$$permissionId']},
                                        {'$eq': ['$sys_user_id',
                                         ObjectId(user['id'])]},
                                        {'$eq': ['$status', 'added']}
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'direct_privileges'
                }
            },
            # // Lookup permission roles (for role-based access)
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_PERMISSION_ROLE.model_name}",
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id',
                    'foreignField': 'rbac_permission_id',
                    'as': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}_role'
                }
            },
            {
                '$unwind': {
                    'path': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}_role',
                    'preserveNullAndEmptyArrays': True
                }
            },
            # // Lookup roles
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_ROLE.model_name}",
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION.model_name}_role.rbac_role_id',
                    'foreignField': '_id',
                    'as': f'unwind__{CollectionKey.RBAC_ROLE.model_name}'
                }
            },
            {
                '$unwind': {
                    'path': f'$unwind__{CollectionKey.RBAC_ROLE.model_name}',
                    'preserveNullAndEmptyArrays': True
                }
            },
            # // Lookup menu
            {
                '$lookup': {
                    'from': f"{CollectionKey.SYS_MENU.model_name}",
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.targeted_id',
                    'foreignField': '_id',
                    'as': f'unwind__{CollectionKey.SYS_MENU.model_name}'
                }
            },
            {
                '$unwind': f'$unwind__{CollectionKey.SYS_MENU.model_name}'
            },
            # // Lookup API consumer restrictions
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}'
                }
            },
            {
                '$unwind': {
                    'path': f'$unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}',
                    'preserveNullAndEmptyArrays': True
                }
            },
            # // Lookup profile restrictions
            {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                    'localField': f'unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}._id',
                    'foreignField': 'targeted_id',
                    'as': f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}'
                }
            },
            {
                '$unwind': {
                    'path': f'$unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}',
                    'preserveNullAndEmptyArrays': True
                }
            },
            # // Final matching - handles both role-based and privilege-based access
            {
                '$match': {
                    '$or': [
                        # // Role-based access path
                        {
                            f'unwind__{CollectionKey.RBAC_ROLE.model_name}._id': ObjectId(user['rbac_role_id']),
                            f'unwind__{CollectionKey.SYS_MENU.model_name}._id': ObjectId(targeted_id),
                            f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.rbac_profile_id': ObjectId(userProfil['id']),
                            f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id': ObjectId(apiConsumer['id'])
                        },
                        # // Privilege-based access path
                        {
                            'direct_privileges': {'$ne': []},
                            f'unwind__{CollectionKey.SYS_MENU.model_name}._id': ObjectId(targeted_id),
                            f'unwind__{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}.rbac_profile_id': ObjectId(userProfil['id']),
                            f'unwind__{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}.ref_api_consumer_id': ObjectId(apiConsumer['id'])
                        }
                    ]
                }
            },
            # // Projection
            {
                '$project': {
                    '_id': 1,
                    'is_standalone': 1,
                    'label': 1,
                    'flag': 1,
                    'hard_code_flag': 1,
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
 
        # Parallelize actions and components fetch calls
        formated_actions, formated_components = await AsyncExecutor.gather([
            generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_ACTION,
                output_data_type=output_data_type,
                accept_language=accept_language,
                pipeline=rbac_actions_pipeline,
                all_data=True
            ),
            generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_COMPONENT,
                output_data_type=output_data_type,
                accept_language=accept_language,
                pipeline=rbac_components_pipeline,
                all_data=True
            ),
        ])
        DebugService.app_debug_print(f" step 7", True)

        # CHILDREN DISPLAY TYPE
        children_display_type_pipeline = [
            {
                '$match': {
                    'targeted_id': ObjectId(targeted_id)
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    'let': {
                        'target_id': '$_id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$eq': [
                                        '$targeted_id', '$$target_id'
                                    ]
                                },
                                'ref_api_consumer_id': ObjectId(apiConsumer["id"]),
                                'is_hidden': False
                            }
                        }, {
                            '$project': {
                                '_id': 1,
                                'targeted_id': 1,
                                'ref_api_consumer_id': 1
                            }
                        }
                    ],
                    'as': 'api_consumers'
                }
            }, {
                '$match': {
                    'api_consumers': {
                        '$ne': []
                    }
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                    'let': {
                        'target_id': '$_id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$eq': [
                                        '$targeted_id', '$$target_id'
                                    ]
                                },
                                'rbac_profile_id': ObjectId(userProfil["id"]),
                                'is_hidden': False
                            }
                        }, {
                            '$project': {
                                '_id': 1,
                                'targeted_id': 1,
                                'rbac_profile_id': 1
                            }
                        }
                    ],
                    'as': 'profiles'
                }
            }, {
                '$match': {
                    'profiles': {
                        '$ne': []
                    }
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.SYS_MENU.model_name}",
                    'let': {
                        'target_id': '$targeted_id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$eq': [
                                        '$_id', '$$target_id'
                                    ]
                                }
                            }
                        }, {
                            '$lookup': {
                                'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                                'let': {
                                    'menu_id': '$_id'
                                },
                                'pipeline': [
                                    {
                                        '$match': {
                                            '$expr': {
                                                '$eq': [
                                                    '$targeted_id', '$$menu_id'
                                                ]
                                            },
                                            'ref_api_consumer_id': ObjectId(apiConsumer['id'])
                                        }
                                    }
                                ],
                                'as': 'menu_consumers'
                            }
                        }, {
                            '$lookup': {
                                'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                                'let': {
                                    'menu_id': '$_id'
                                },
                                'pipeline': [
                                    {
                                        '$match': {
                                            '$expr': {
                                                '$eq': [
                                                    '$targeted_id', '$$menu_id'
                                                ]
                                            },
                                            'rbac_profile_id': ObjectId(userProfil["id"])
                                        }
                                    }
                                ],
                                'as': 'menu_profiles'
                            }
                        }, {
                            '$match': {
                                'menu_consumers': {
                                    '$ne': []
                                },
                                'menu_profiles': {
                                    '$ne': []
                                }
                            }
                        }
                    ],
                    'as': 'menus'
                }
            }, {
                '$match': {
                    'menus': {
                        '$ne': []
                    }
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.REF_CHILDREN_DISPLAY_TYPE.model_name}",
                    'let': {
                        'children_display_type_id': '$ref_children_display_type_id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$eq': [
                                        '$_id', '$$children_display_type_id'
                                    ]
                                }
                            }
                        }, {
                            '$project': {
                                '_id': 1,
                                'url': 1,
                                'label': 1,
                                'flag': 1
                            }
                        }
                    ],
                    'as': 'children_display_types'
                }
            }, {
                '$unwind': {
                    'path': '$children_display_types',
                    'preserveNullAndEmptyArrays': False
                }
            }, {
                '$sort': {
                    'order_by': 1
                }
            }, {
                '$project': {
                    '_id': 1,
                    'targeted_id': 1,
                    'ref_children_display_type_id': 1,
                    f'unwind__{CollectionKey.REF_CHILDREN_DISPLAY_TYPE.model_name}': {
                        '_id': '$children_display_types._id',
                        'label': '$children_display_types.label',
                        'flag': '$children_display_types.flag'
                    }
                }
            }
        ]
        # Note: children_display_types will be fetched later in parallel with data_display_types
        DebugService.app_debug_print(f" step 9", True)

        # DATA DISPLAY TYPE
        data_display_type_pipeline = [
            {
                '$match': {
                    'targeted_id': ObjectId(targeted_id)
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    'let': {
                        'target_id': '$_id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$eq': [
                                        '$targeted_id', '$$target_id'
                                    ]
                                },
                                'ref_api_consumer_id': ObjectId(apiConsumer["id"]),
                                'is_hidden': False
                            }
                        }, {
                            '$project': {
                                '_id': 1,
                                'targeted_id': 1,
                                'ref_api_consumer_id': 1
                            }
                        }
                    ],
                    'as': 'api_consumers'
                }
            }, {
                '$match': {
                    'api_consumers': {
                        '$ne': []
                    }
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                    'let': {
                        'target_id': '$_id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$eq': [
                                        '$targeted_id', '$$target_id'
                                    ]
                                },
                                'rbac_profile_id': ObjectId(userProfil["id"]),
                                'is_hidden': False
                            }
                        }, {
                            '$project': {
                                '_id': 1,
                                'targeted_id': 1,
                                'rbac_profile_id': 1
                            }
                        }
                    ],
                    'as': 'profiles'
                }
            }, {
                '$match': {
                    'profiles': {
                        '$ne': []
                    }
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.SYS_MENU.model_name}",
                    'let': {
                        'target_id': '$targeted_id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {
                                            '$eq': [
                                                '$_id', '$$target_id'
                                            ]
                                        }, {
                                            '$eq': [
                                                '$_id', ObjectId(targeted_id)
                                            ]
                                        }
                                    ]
                                }
                            }
                        }, {
                            '$lookup': {
                                'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                                'let': {
                                    'menu_id': '$_id'
                                },
                                'pipeline': [
                                    {
                                        '$match': {
                                            '$expr': {
                                                '$eq': [
                                                    '$targeted_id', '$$menu_id'
                                                ]
                                            },
                                            'ref_api_consumer_id': ObjectId(apiConsumer["id"])
                                        }
                                    }
                                ],
                                'as': 'menu_consumers'
                            }
                        }, {
                            '$lookup': {
                                'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                                'let': {
                                    'menu_id': '$_id'
                                },
                                'pipeline': [
                                    {
                                        '$match': {
                                            '$expr': {
                                                '$eq': [
                                                    '$targeted_id', '$$menu_id'
                                                ]
                                            },
                                            'rbac_profile_id': ObjectId(userProfil["id"])
                                        }
                                    }
                                ],
                                'as': 'menu_profiles'
                            }
                        }, {
                            '$match': {
                                'menu_consumers': {
                                    '$ne': []
                                },
                                'menu_profiles': {
                                    '$ne': []
                                }
                            }
                        }
                    ],
                    'as': 'menus'
                }
            }, {
                '$match': {
                    'menus': {
                        '$ne': []
                    }
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.REF_DATA_DISPLAY_TYPE.model_name}",
                    'let': {
                        'data_display_type_id': '$ref_data_display_type_id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$eq': [
                                        '$_id', '$$data_display_type_id'
                                    ]
                                }
                            }
                        }, {
                            '$project': {
                                '_id': 1,
                                'url': 1,
                                'label': 1,
                                'flag': 1
                            }
                        }
                    ],
                    'as': 'data_display_types'
                }
            }, {
                '$unwind': {
                    'path': '$data_display_types',
                    'preserveNullAndEmptyArrays': False
                }
            }, {
                '$sort': {
                    'order_by': 1
                }
            }, {
                '$project': {
                    '_id': 1,
                    'targeted_id': 1,
                    'ref_data_display_type_id': 1,
                    f'unwind__{CollectionKey.REF_DATA_DISPLAY_TYPE.model_name}': {
                        '_id': '$data_display_types._id',
                        'label': '$data_display_types.label',
                        'flag': '$data_display_types.flag'
                    }
                }
            }
        ]

        # Note: data_display_types will be fetched in parallel below

        # COLLECTION CRUD INFO
        collection_crud_info_pipeline = [
            {
                '$match': {
                    'targeted_id': ObjectId(targeted_id)
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                    'let': {
                        'target_id': '$_id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$eq': [
                                        '$targeted_id', '$$target_id'
                                    ]
                                },
                                'ref_api_consumer_id': ObjectId(apiConsumer['id']),
                                'is_hidden': False
                            }
                        }, {
                            '$project': {
                                '_id': 1,
                                'targeted_id': 1,
                                'ref_api_consumer_id': 1
                            }
                        }
                    ],
                    'as': 'api_consumers'
                }
            }, {
                '$match': {
                    'api_consumers': {
                        '$ne': []
                    }
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                    'let': {
                        'target_id': '$_id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$eq': [
                                        '$targeted_id', '$$target_id'
                                    ]
                                },
                                'rbac_profile_id': ObjectId(userProfil['id']),
                                'is_hidden': False
                            }
                        }, {
                            '$project': {
                                '_id': 1,
                                'targeted_id': 1,
                                'rbac_profile_id': 1
                            }
                        }
                    ],
                    'as': 'profiles'
                }
            }, {
                '$match': {
                    'profiles': {
                        '$ne': []
                    }
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.SYS_MENU.model_name}",
                    'let': {
                        'target_id': '$targeted_id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {
                                            '$eq': [
                                                '$_id', '$$target_id'
                                            ]
                                        }, {
                                            '$eq': [
                                                '$_id', ObjectId(targeted_id)
                                            ]
                                        }
                                    ]
                                }
                            }
                        }, {
                            '$lookup': {
                                'from': f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
                                'let': {
                                    'menu_id': '$_id'
                                },
                                'pipeline': [
                                    {
                                        '$match': {
                                            '$expr': {
                                                '$eq': [
                                                    '$targeted_id', '$$menu_id'
                                                ]
                                            },
                                            'ref_api_consumer_id': ObjectId(apiConsumer['id'])
                                        }
                                    }
                                ],
                                'as': 'app_consumers'
                            }
                        }, {
                            '$lookup': {
                                'from': f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
                                'let': {
                                    'menu_id': '$_id'
                                },
                                'pipeline': [
                                    {
                                        '$match': {
                                            '$expr': {
                                                '$eq': [
                                                    '$targeted_id', '$$menu_id'
                                                ]
                                            },
                                            'rbac_profile_id': ObjectId(userProfil['id'])
                                        }
                                    }
                                ],
                                'as': 'menu_profiles'
                            }
                        }, {
                            '$match': {
                                'app_consumers': {
                                    '$ne': []
                                },
                                'menu_profiles': {
                                    '$ne': []
                                }
                            }
                        }
                    ],
                    'as': 'menus'
                }
            }, {
                '$match': {
                    'menus': {
                        '$ne': []
                    }
                }
            }, {
                '$lookup': {
                    'from': f"{CollectionKey.RBAC_ENDPOINT.model_name}",
                    'let': {
                        'endpoint_id': '$rbac_endpoint_id'
                    },
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$eq': [
                                        '$_id', '$$endpoint_id'
                                    ]
                                }
                            }
                        }, {
                            '$project': {
                                '_id': 1,
                                'url': 1,
                                'label': 1,
                                'flag': 1,
                                'is_sudo_action': 1,
                                'is_sudo_group_action': 1,
                                'is_sudo_delegated_action': 1,
                                'is_sudo_group_cross_validation_action': 1,
                                'is_sudo_group_inter_organization_validation_action': 1,
                            }
                        }
                    ],
                    'as': 'endpoints'
                }
            }, {
                '$unwind': {
                    'path': '$endpoints',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$sort': {
                    'order_by': 1
                }
            }, {
                '$project': {
                    '_id': 1,
                    'targeted_id': 1,
                    'rbac_endpoint_id': 1,
                    "label": 1,
                    'flag': 1,
                    'hard_code_flag': 1,
                    'parent_field_name': 1,
                    f'unwind__{CollectionKey.RBAC_ENDPOINT.model_name}': {
                        '_id': '$endpoints._id',
                        'url': '$endpoints.url',
                        'label': '$endpoints.label',
                        'flag': '$endpoints.flag',
                        'is_sudo_action': '$endpoints.is_sudo_action',
                        'is_sudo_group_action': '$endpoints.is_sudo_group_action',
                        'is_sudo_delegated_action': '$endpoints.is_sudo_delegated_action',
                        'is_sudo_group_cross_validation_action': '$endpoints.is_sudo_group_cross_validation_action',
                        'is_sudo_group_inter_organization_validation_action': '$endpoints.is_sudo_group_inter_organization_validation_action',
                    }
                }
            }
        ]

        # Parallelize display types fetches
        children_display_types, data_display_types, collection_crud_info = await AsyncExecutor.gather([
            generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.CFG_CHILDREN_DISPLAY_TYPE,
                output_data_type=output_data_type,
                accept_language=accept_language,
                pipeline=children_display_type_pipeline
            ),
            generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.CFG_DATA_DISPLAY_TYPE,
                output_data_type=output_data_type,
                accept_language=accept_language,
                pipeline=data_display_type_pipeline
            ),
            generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.REF_COLLECTION_CRUD_INFO,
                output_data_type=output_data_type,
                accept_language=accept_language,
                pipeline=collection_crud_info_pipeline,
                all_data=True,
                limit=300
            ),
        ])
        ref_children_display_type_info = children_display_types[0]['ref_children_display_type'] if len(
            children_display_types) > 0 else None
        ref_data_display_type_info = data_display_types[0]['ref_data_display_type'] if len(
            data_display_types) > 0 else None
        current_item = {
            **menu['sys_menu'],
            'ishidden': is_hidden,
            'order_by': order_by,
            'isactivated': is_activated,
            'rbac_path_guard': {
                **menu['rbac_path_guard'],
            },
            "rbac_actions": formated_actions,
            "rbac_components": formated_components,

            'ref_children_display_type': ref_children_display_type_info,
            'ref_data_display_type': ref_data_display_type_info,
            'collection_crud_info': collection_crud_info,
        }
        icon_payload = ApplicationService._build_svg_icon_payload(
            menu_or_app_data=menu.get('sys_menu', {}),
            rbac_path_guard=menu.get('rbac_path_guard', {}),
            api_consumer_flag=apiConsumer.get('flag'),
        )
        if icon_payload:
            current_item = {
                **current_item,
                **icon_payload,
            }
        # CHECK CHILDREN
        list_of_children = []
        sub_menu_pipeline = [
    # // Lookup role (keep but make unwind preserve null/empty)
    {
        '$lookup': {
            'from': f"{CollectionKey.RBAC_ROLE.model_name}",
            'localField': "rbac_role_id",
            'foreignField': "_id",
            'as': f"unwind__{CollectionKey.RBAC_ROLE.model_name}"
        }
    },
    {
        '$unwind': {
            "path": f"$unwind__{CollectionKey.RBAC_ROLE.model_name}",
            "preserveNullAndEmptyArrays": True
        }
    },

    # // Lookup permission
    {
        '$lookup': {
            'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
            'localField': "rbac_permission_id",
            'foreignField': "_id",
            'as': f"unwind__{CollectionKey.RBAC_PERMISSION.model_name}"
        }
    },
    {
        '$unwind': f"$unwind__{CollectionKey.RBAC_PERMISSION.model_name}"
    },
    
    # // Add privilege lookup
    {
        '$lookup': {
            'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
            'let': { 'permissionId': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id' },
            'pipeline': [
                {
                    '$match': {
                        '$expr': {
                            '$and': [
                                {'$eq': ['$rbac_permission_id', '$$permissionId']},
                                {'$eq': ['$sys_user_id', ObjectId(user['id'])]},
                                {'$eq': ['$status', 'added']}
                            ]
                        }
                    }
                }
            ],
            'as': 'direct_privileges'
        }
    },

    # // Continue with permission target lookup
    {
        '$lookup': {
            'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
            'localField': f"unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id",
            'foreignField': "rbac_permission_id",
            'as': f"unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}"
        }
    },
    {
        '$unwind': f"$unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}"
    },

    # // Menu lookup
    {
        '$lookup': {
            'from': f"{CollectionKey.SYS_MENU.model_name}",
            'localField': f"unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.targeted_id",
            'foreignField': "_id",
            'as': f"unwind__{CollectionKey.SYS_MENU.model_name}"
        }
    },
    {
        '$unwind': f"$unwind__{CollectionKey.SYS_MENU.model_name}"
    },
    
    # // Path guard lookup
    {
        '$lookup': {
            'from': f"{CollectionKey.RBAC_PATH_GUARD.model_name}",
            'localField': f"unwind__{CollectionKey.SYS_MENU.model_name}._id",
            'foreignField': "targeted_id",
            'as': f"unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}"
        }
    },
    {
        '$unwind': {
            "path": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}",
            "preserveNullAndEmptyArrays": True
        }
    },
    
    # // Menu restrictions
    {
        "$lookup": {
            "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
            "localField": f"unwind__{CollectionKey.SYS_MENU.model_name}._id",
            "foreignField": "targeted_id",
            "as": "menu_rbac_restricted_api_consumer"
        }
    },
    {
        "$unwind": {
            "path": "$menu_rbac_restricted_api_consumer",
            "preserveNullAndEmptyArrays": True
        }
    },
    {
        "$lookup": {
            "from": f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
            "localField": f"unwind__{CollectionKey.SYS_MENU.model_name}._id",
            "foreignField": "targeted_id",
            "as": "menu_rbac_restricted_profil"
        }
    },
    {
        "$unwind": {
            "path": "$menu_rbac_restricted_profil",
            "preserveNullAndEmptyArrays": True
        }
    },
    
    # // Guard restrictions
    {
        "$lookup": {
            "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
            "localField": f"unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}._id",
            "foreignField": "targeted_id",
            "as": "guard_rbac_restricted_api_consumer"
        }
    },
    {
        "$unwind": {
            "path": "$guard_rbac_restricted_api_consumer",
            "preserveNullAndEmptyArrays": True
        }
    },
    {
        "$lookup": {
            "from": f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
            "localField": f"unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}._id",
            "foreignField": "targeted_id",
            "as": "guard_rbac_restricted_profil"
        }
    },
    {
        "$unwind": {
            "path": "$guard_rbac_restricted_profil",
            "preserveNullAndEmptyArrays": True
        }
    },
    
    # // Final matching - handles both role-based and privilege-based access
    {
        "$match": {
            "$or": [
                # // Role-based access path
                {
                    f"unwind__{CollectionKey.RBAC_ROLE.model_name}._id": ObjectId(user['rbac_role_id']),
                    f"unwind__{CollectionKey.SYS_MENU.model_name}.is_activated": True,
                    f"unwind__{CollectionKey.SYS_MENU.model_name}.sys_menu_id": ObjectId(targeted_id),
                    "menu_rbac_restricted_profil.rbac_profile_id": ObjectId(userProfil['id']),
                    "menu_rbac_restricted_api_consumer.ref_api_consumer_id": ObjectId(apiConsumer['id']),
                    "menu_rbac_restricted_profil.is_hidden": False,
                    "menu_rbac_restricted_api_consumer.is_hidden": False,
                    "guard_rbac_restricted_profil.rbac_profile_id": ObjectId(userProfil['id']),
                    "guard_rbac_restricted_api_consumer.ref_api_consumer_id": ObjectId(apiConsumer['id']),
                    "guard_rbac_restricted_profil.is_hidden": False,
                    "guard_rbac_restricted_api_consumer.is_hidden": False
                },
                # // Privilege-based access path
                {
                    "direct_privileges": {"$ne": []},
                    f"unwind__{CollectionKey.SYS_MENU.model_name}.is_activated": True,
                    f"unwind__{CollectionKey.SYS_MENU.model_name}.sys_menu_id": ObjectId(targeted_id),
                    "menu_rbac_restricted_profil.rbac_profile_id": ObjectId(userProfil['id']),
                    "menu_rbac_restricted_api_consumer.ref_api_consumer_id": ObjectId(apiConsumer['id']),
                    "menu_rbac_restricted_profil.is_hidden": False,
                    "menu_rbac_restricted_api_consumer.is_hidden": False,
                    "guard_rbac_restricted_profil.rbac_profile_id": ObjectId(userProfil['id']),
                    "guard_rbac_restricted_api_consumer.ref_api_consumer_id": ObjectId(apiConsumer['id']),
                    "guard_rbac_restricted_profil.is_hidden": False,
                    "guard_rbac_restricted_api_consumer.is_hidden": False
                }
            ]
        }
    },
    
    # // Grouping and merging
    {
        "$group": {
            "_id": f"$unwind__{CollectionKey.SYS_MENU.model_name}._id",
            "docs": {
                "$push": {
                    "_id": "$_id",
                    f"unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}": {
                        "_id": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}._id",
                        "path_guard": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.path_guard",
                        "path": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.path",
                        "targeted_id": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.targeted_id",
                        "sys_menu_id": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.sys_menu_id",
                        "sys_application_id": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.sys_application_id",
                    },
                    f"unwind__{CollectionKey.SYS_MENU.model_name}": {
                        "_id": f"$unwind__{CollectionKey.SYS_MENU.model_name}._id",
                        "is_standalone": f"$unwind__{CollectionKey.SYS_MENU.model_name}.is_standalone",
                        "name": f"$unwind__{CollectionKey.SYS_MENU.model_name}.name",
                        "flag": f"$unwind__{CollectionKey.SYS_MENU.model_name}.flag",
                        "description_str": f"$unwind__{CollectionKey.SYS_MENU.model_name}.description_str",
                        "sys_application_id": f"$unwind__{CollectionKey.SYS_MENU.model_name}.sys_application_id",
                        "application_group_flag": f"$unwind__{CollectionKey.SYS_MENU.model_name}.application_group_flag",
                        "sys_menu_id": f"$unwind__{CollectionKey.SYS_MENU.model_name}.sys_menu_id",
                        "order_by": f"$unwind__{CollectionKey.SYS_MENU.model_name}.order_by",
                        "is_skipable_menu_on_view": f"$unwind__{CollectionKey.SYS_MENU.model_name}.is_skipable_menu_on_view",
                    },
                    "access_via": {
                        "$cond": [
                            {"$gt": [{"$size": "$direct_privileges"}, 0]},
                            "privilege",
                            "role"
                        ]
                    }
                }
            }
        }
    },
    {
        "$project": {
            "merged": {
                "$reduce": {
                    "input": "$docs",
                    "initialValue": {},
                    "in": {"$mergeObjects": ["$$value", "$$this"]}
                }
            }
        }
    },
    {
        "$replaceRoot": {"newRoot": "$merged"}
    },
    {
        "$sort": {
            f"unwind__{CollectionKey.SYS_MENU.model_name}.order_by": 1
        }
    }
]
        # Return the current menu with its children
        return {
            **current_item,
            "sub_menus": list_of_children
        }

    @staticmethod
    async def get_user_standalone_menus(
            apiConsumer: dict,
            user: dict,
            userProfil: dict,
            page: int = 0,
            limit: int = 10,
            all_data: bool = False,
            accept_language: str = DEFAULT_LANGUAGE,
            output_data_type: OutputDataType = OutputDataType.DEFAULT):
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(accept_language)
        pipeline = [
    # // Lookup role (with preserveNullAndEmptyArrays for privilege access)
    {
        '$lookup': {
            'from': f"{CollectionKey.RBAC_ROLE.model_name}",
            'localField': "rbac_role_id",
            'foreignField': "_id",
            'as': f"unwind__{CollectionKey.RBAC_ROLE.model_name}"
        }
    },
    {
        '$unwind': {
            "path": f"$unwind__{CollectionKey.RBAC_ROLE.model_name}",
            "preserveNullAndEmptyArrays": True
        }
    },

    # // Lookup permission
    {
        '$lookup': {
            'from': f"{CollectionKey.RBAC_PERMISSION.model_name}",
            'localField': "rbac_permission_id",
            'foreignField': "_id",
            'as': f"unwind__{CollectionKey.RBAC_PERMISSION.model_name}"
        }
    },
    {
        '$unwind': f"$unwind__{CollectionKey.RBAC_PERMISSION.model_name}"
    },
    
    # // Add privilege lookup
    {
        '$lookup': {
            'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
            'let': { 'permissionId': f'$unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id' },
            'pipeline': [
                {
                    '$match': {
                        '$expr': {
                            '$and': [
                                {'$eq': ['$rbac_permission_id', '$$permissionId']},
                                {'$eq': ['$sys_user_id', ObjectId(user['id'])]},
                                {'$eq': ['$status', 'added']}
                            ]
                        }
                    }
                }
            ],
            'as': 'direct_privileges'
        }
    },

    # // Continue with permission target lookup
    {
        '$lookup': {
            'from': f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
            'localField': f"unwind__{CollectionKey.RBAC_PERMISSION.model_name}._id",
            'foreignField': "rbac_permission_id",
            'as': f"unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}"
        }
    },
    {
        '$unwind': f"$unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}"
    },

    # // Menu lookup
    {
        '$lookup': {
            'from': f"{CollectionKey.SYS_MENU.model_name}",
            'localField': f"unwind__{CollectionKey.RBAC_PERMISSION_TARGET.model_name}.targeted_id",
            'foreignField': "_id",
            'as': f"unwind__{CollectionKey.SYS_MENU.model_name}"
        }
    },
    {
        '$unwind': f"$unwind__{CollectionKey.SYS_MENU.model_name}"
    },
    
    # // Path guard lookup
    {
        '$lookup': {
            'from': f"{CollectionKey.RBAC_PATH_GUARD.model_name}",
            'localField': f"unwind__{CollectionKey.SYS_MENU.model_name}._id",
            'foreignField': "targeted_id",
            'as': f"unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}"
        }
    },
    {
        '$unwind': {
            "path": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}",
            "preserveNullAndEmptyArrays": True
        }
    },
    
    # // Menu restrictions
    {
        "$lookup": {
            "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
            "localField": f"unwind__{CollectionKey.SYS_MENU.model_name}._id",
            "foreignField": "targeted_id",
            "as": "menu_rbac_restricted_api_consumer"
        }
    },
    {
        "$unwind": {
            "path": "$menu_rbac_restricted_api_consumer",
            "preserveNullAndEmptyArrays": True
        }
    },
    {
        "$lookup": {
            "from": f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
            "localField": f"unwind__{CollectionKey.SYS_MENU.model_name}._id",
            "foreignField": "targeted_id",
            "as": "menu_rbac_restricted_profil"
        }
    },
    {
        "$unwind": {
            "path": "$menu_rbac_restricted_profil",
            "preserveNullAndEmptyArrays": True
        }
    },
    
    # // Guard restrictions
    {
        "$lookup": {
            "from": f"{CollectionKey.RBAC_RESTRICTED_API_CONSUMER.model_name}",
            "localField": f"unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}._id",
            "foreignField": "targeted_id",
            "as": "guard_rbac_restricted_api_consumer"
        }
    },
    {
        "$unwind": {
            "path": "$guard_rbac_restricted_api_consumer",
            "preserveNullAndEmptyArrays": True
        }
    },
    {
        "$lookup": {
            "from": f"{CollectionKey.RBAC_RESTRICTED_PROFIL.model_name}",
            "localField": f"unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}._id",
            "foreignField": "targeted_id",
            "as": "guard_rbac_restricted_profil"
        }
    },
    {
        "$unwind": {
            "path": "$guard_rbac_restricted_profil",
            "preserveNullAndEmptyArrays": True
        }
    },
    
    # // Final matching - handles both role-based and privilege-based access
    {
        "$match": {
            "$and": [
                # // Common requirements for both paths
                {
                    f"unwind__{CollectionKey.SYS_MENU.model_name}.is_standalone": True,
                    f"unwind__{CollectionKey.SYS_MENU.model_name}.sys_menu_id": None,
                    "menu_rbac_restricted_profil.rbac_profile_id": ObjectId(userProfil['id']),
                    "menu_rbac_restricted_api_consumer.ref_api_consumer_id": ObjectId(apiConsumer['id']),
                    "menu_rbac_restricted_profil.is_hidden": False,
                    "menu_rbac_restricted_api_consumer.is_hidden": False,
                    "guard_rbac_restricted_profil.rbac_profile_id": ObjectId(userProfil['id']),
                    "guard_rbac_restricted_api_consumer.ref_api_consumer_id": ObjectId(apiConsumer['id']),
                    "guard_rbac_restricted_profil.is_hidden": False,
                    "guard_rbac_restricted_api_consumer.is_hidden": False
                },
                # // Either role or privilege must be valid
                {
                    "$or": [
                        # // Role-based access path
                        {
                            f"unwind__{CollectionKey.RBAC_ROLE.model_name}._id": ObjectId(user['rbac_role_id'])
                        },
                        # // Privilege-based access path
                        {
                            "direct_privileges": {"$ne": []}
                        }
                    ]
                }
            ]
        }
    },
    
    # // Grouping and merging
    {
        "$group": {
            "_id": f"$unwind__{CollectionKey.SYS_MENU.model_name}._id",
            "docs": {
                "$push": {
                    "_id": "$_id",
                    "rbac_role_id": "$rbac_role_id",
                    "rbac_permission_id": "$rbac_permission_id",
                    f"unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}": {
                        "_id": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}._id",
                        "path_guard": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.path_guard",
                        "path": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.path",
                        "targeted_id": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.targeted_id",
                        "sys_menu_id": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.sys_menu_id",
                        "sys_application_id": f"$unwind__{CollectionKey.RBAC_PATH_GUARD.model_name}.sys_application_id",
                    },
                    f"unwind__{CollectionKey.SYS_MENU.model_name}": {
                        "_id": f"$unwind__{CollectionKey.SYS_MENU.model_name}._id",
                        "is_standalone": f"$unwind__{CollectionKey.SYS_MENU.model_name}.is_standalone",
                        "name": f"$unwind__{CollectionKey.SYS_MENU.model_name}.name",
                        "flag": f"$unwind__{CollectionKey.SYS_MENU.model_name}.flag",
                        "description_str": f"$unwind__{CollectionKey.SYS_MENU.model_name}.description_str",
                        "sys_application_id": f"$unwind__{CollectionKey.SYS_MENU.model_name}.sys_application_id",
                        "application_group_flag": f"$unwind__{CollectionKey.SYS_MENU.model_name}.application_group_flag",
                        "sys_menu_id": f"$unwind__{CollectionKey.SYS_MENU.model_name}.sys_menu_id",
                        "order_by": f"$unwind__{CollectionKey.SYS_MENU.model_name}.order_by",
                        "is_skipable_menu_on_view": f"$unwind__{CollectionKey.SYS_MENU.model_name}.is_skipable_menu_on_view",
                    },
                    "access_via": {
                        "$cond": [
                            {"$gt": [{"$size": "$direct_privileges"}, 0]},
                            "privilege",
                            "role"
                        ]
                    }
                }
            }
        }
    },
    {
        "$project": {
            "merged": {
                "$reduce": {
                    "input": "$docs",
                    "initialValue": {},
                    "in": {"$mergeObjects": ["$$value", "$$this"]}
                }
            }
        }
    },
    {
        "$replaceRoot": {"newRoot": "$merged"}
    }
]
       
        # print(f"\n\n\n output_data_type  >>> : {output_data_type} \n\n")
        infos = await generic_service.fetch_native_aggregate_data_from_collection(
            collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
            output_data_type=output_data_type,
            accept_language=accept_language,
            pipeline=pipeline,
            all_data=True
        )
        print(f"\n\n\n STANDALONE MENUS USER  >>> 1: {len(infos)} \n\n")
        # Parallelize processing of all standalone menus
        async def process_standalone_menu(menu):
            return await ApplicationService.user_recursive_menu_children(
                menu=menu,
                user=user,
                userProfil=userProfil,
                accept_language=accept_language,
                output_data_type=output_data_type,
                apiConsumer=apiConsumer,
            )
        
        results = await AsyncExecutor.gather_with_limit(
            [process_standalone_menu(menu) for menu in infos],
            limit=5,
            return_exceptions=True
        )
        formatted_data = [r for r in results if r is not None and not isinstance(r, Exception)]
        # formatted_data.sort(key=lambda item: item['order_by'])
        return formatted_data
