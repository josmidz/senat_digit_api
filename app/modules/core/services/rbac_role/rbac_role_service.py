

from typing import Optional

from bson import ObjectId
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.services.generic.generic_services import OutputDataType
from app.modules.core.services.generic.generic_services import CollectionKey
from app.modules.core.enums.profiles_enum import ESysProfileFlag
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.enums.access_level import EAccessFlag
from app.modules.core.utils.helpers.line_helper import format_exception
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.seeds.seed_core import COLLECTION_CRUD_FLAG_MAPPING
from app.modules.core.seeds.core_rbac_title import CORE_RBAC_TITLE_DB
from app.modules.core.seeds.rbac_title.profil_permission_title import PROFIL_ENDPOINTS
from app.modules.core.seeds.specific_seed_all import PROFILE_TITLE_FLAG

class RbacRoleService():
    """
    Service for handling rbac roles.

    This service implements a hybrid search strategy:
    1. Use MongoDB to filter by non-encrypted fields
    2. Fetch the filtered results and apply in-memory filtering for encrypted fields
    """

    def __init__(self, accept_language: str = DEFAULT_LANGUAGE):
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.core.services.debug.debug_service import DebugService
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        self.debug_service = DebugService(accept_language)
    
    async def ensure_profile_rbac_title_exists(self,generic_service):
        """Make sure the core profile RBAC title exists before seeding endpoints."""
        existing_title = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_TITLE,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=DEFAULT_LANGUAGE,
            query={"filter__flag": PROFILE_TITLE_FLAG}
        )

        if existing_title:
            return existing_title

        template = next((item for item in CORE_RBAC_TITLE_DB if item.get("flag") == PROFILE_TITLE_FLAG), None)
        payload = {
            "label": template.get("label", "Profil"),
            "flag": PROFILE_TITLE_FLAG,
            "is_default": template.get("is_default", True)
        } if template else {
            "label": "Profil",
            "flag": PROFILE_TITLE_FLAG,
            "is_default": True
        }

        created_title = await generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.RBAC_TITLE,
            filter_data={"flag": PROFILE_TITLE_FLAG},
            update_data=payload
        )
        print(f"✅ Ensured RBAC title '{PROFILE_TITLE_FLAG}' exists")
        return created_title
    
    
    async def fetch_rbac_endpoint_data(self,generic_service, rbac_endpoint_url):
        """Fetch RBAC endpoint data from database."""
        if not rbac_endpoint_url:
            return None

        return await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_ENDPOINT,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=DEFAULT_LANGUAGE,
            query={"filter__url": rbac_endpoint_url}
        )
    
    async def handle_all_access_core_seeds(self,all_access_core_seeds,permission_db_item,generic_service):
        try:
            print(f"all_access_core_seeds : >>>  {len(all_access_core_seeds)}")
            from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
            rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)
            # fetch all roles and update
            all_roles = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT,
                all_data=True,
                query={
                    "is_activated":True
                }
            )

            print(f"\n\n\n\n ALL ROLE : {all_roles}")

            # loop to upsert permision role
            for role in all_roles:
                # Get the corresponding CRUD flag
                await  generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                    filter_data={
                        "rbac_role_id": role['id'],
                        "rbac_permission_id": permission_db_item['id']
                    },
                    update_data={
                        "rbac_role_id": role['id'],
                        "rbac_permission_id": permission_db_item['id']
                    }
                ) 
            for crud_operation, meta_data_list in all_access_core_seeds.items():
                if not meta_data_list:  # Skip empty lists
                    continue
                # Get the corresponding CRUD flag
                crud_flag = COLLECTION_CRUD_FLAG_MAPPING.get(crud_operation)
                if not crud_flag:
                    print(f"⚠️  Unknown CRUD operation: '{crud_operation}' in all_access_core_seeds")
                    print(f"📋 Available CRUD operations: {list(COLLECTION_CRUD_FLAG_MAPPING.keys())}")
                    print(f"🔍 Suggestion: Add '{crud_operation}' to COLLECTION_CRUD_FLAG_MAPPING")

                    # Try to suggest a similar existing key
                    similar_keys = [key for key in COLLECTION_CRUD_FLAG_MAPPING.keys() if any(word in key for word in crud_operation.split('_'))]
                    if similar_keys:
                        print(f"💡 Similar existing keys: {similar_keys}")
                    continue

                # Process each meta data item in the list
                for meta_data_item in meta_data_list:

                    # Fetch RBAC endpoint data
                    rbac_endpoint_data = await self.fetch_rbac_endpoint_data(
                        generic_service, meta_data_item.get('rbac_endpoint')
                    )
                    if not rbac_endpoint_data:
                        endpoint_url = meta_data_item.get('rbac_endpoint')
                        # endpoint_url = meta_data_item.get('rbac_endpoint')
                        rbac_title = await generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.RBAC_TITLE,
                            output_data_type=OutputDataType.DEFAULT,
                            accept_language=DEFAULT_LANGUAGE,
                            query={"filter__flag": PROFILE_TITLE_FLAG}
                        )
                        if not rbac_title:
                            print(f"⚠️ RBAC title '{PROFILE_TITLE_FLAG}' missing, creating it on the fly")
                            rbac_title = await self.ensure_profile_rbac_title_exists(generic_service)
                            if not rbac_title:
                                print(f"❌ Unable to seed RBAC title '{PROFILE_TITLE_FLAG}'")
                                return
                        # filter endpoint in PROFIL_ENDPOINTS based on endpoint_url
                        
                        # Filter endpoints that match the endpoint_url with safety checks
                        filtered_endpoints = []
                        for endpoint in PROFIL_ENDPOINTS:
                            if (isinstance(endpoint, dict) and 
                                not endpoint.get("is_link_deleted", False) and
                                endpoint.get("url") == endpoint_url):
                                filtered_endpoints.append(endpoint)
                                break

                        if len(filtered_endpoints) == 0:
                            print(f"❌ RBAC endpoint not found: {endpoint_url}")
                            endpoint_item = {
                                "is_link_deleted": False,
                                "url": endpoint_url,
                                "rbac_title_id": rbac_title['id'],
                                "label": 'Unknown Label'
                            }

                            await generic_service.upsert_data_to_collection(
                                collection_key=CollectionKey.RBAC_ENDPOINT,
                                filter_data={'url': endpoint_url, "rbac_title_id": endpoint_item['rbac_title_id']},
                                update_data={
                                    "is_link_deleted": False,
                                    "url": endpoint_url,
                                    "rbac_title_id": endpoint_item['rbac_title_id'],
                                    "label": endpoint_item['label']
                                }
                            )
                            continue

                        # Ensure we have a valid endpoint dictionary
                        endpoint_data = filtered_endpoints[0]
                        if not isinstance(endpoint_data, dict):
                            print(f"❌ Invalid endpoint structure: {endpoint_data}")
                            return

                        endpoint_item = {
                            "is_link_deleted": False,
                            "url": endpoint_url,
                            "rbac_title_id": rbac_title['id'],
                            "label": endpoint_data.get('label', 'Unknown Label')
                        }

                        await generic_service.upsert_data_to_collection(
                            collection_key=CollectionKey.RBAC_ENDPOINT,
                            filter_data={'url': endpoint_url, "rbac_title_id": endpoint_item['rbac_title_id']},
                            update_data={
                                "is_link_deleted": False,
                                "url": endpoint_url,
                                "rbac_title_id": endpoint_item['rbac_title_id'],
                                "label": endpoint_item['label']
                            }
                        )
                        print(f"❌ RBAC endpoint not found 2: {meta_data_item.get('rbac_endpoint')}")
                        continue 
                    # Create or update permission target for the endpoint
                    saved_target = await generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                        filter_data={
                            "targeted_id": rbac_endpoint_data['id'],
                            "rbac_permission_id": permission_db_item['id']
                        },
                        update_data={
                            "targeted_id": rbac_endpoint_data['id'],
                            "rbac_permission_id": permission_db_item['id']
                        }
                    )

                    processed_target_id = saved_target if isinstance(saved_target, str) else str(saved_target['id'])
                    print(f"✅ Created/updated permission target for endpoint: {rbac_endpoint_data.get('label', 'N/A')}")
                    # Apply profile restrictions ESysProfileFlag, ESysProfilSuperUserRoleFlag

                    restricted_profil_list = ESysProfilSuperUserRoleFlag.__members__.values()   # ESysProfileFlag values
                    restricted_api_consumer_list = EApiConsumerFlag.__members__.values() # EApiConsumerFlag values
                    print(f"restricted_profil_list : {restricted_profil_list}")
                    for profil in restricted_profil_list:
                        # Handle new object structure - profil is now an object with flag and link fields
                        profil_flag = profil.value

                        is_link_deleted = False # profil.get('is_link_deleted', False)
                        is_link_activated =True #  profil.get('is_link_activated', True)
                        is_link_hidden = False # profil.get('is_link_hidden', False)
                        is_link_locked = False # profil.get('is_link_locked', False)

                        # Fetch profile from db by flag
                        sys_profil_db_item = await generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.RBAC_PROFILE,
                            output_data_type=OutputDataType.DEFAULT,
                            accept_language=DEFAULT_LANGUAGE,
                            query={"filter__flag": profil_flag}
                        )

                        if sys_profil_db_item:

                            # PROCESS TARGET
                            await rbac_role_service.create_restricted_profil(
                                targeted_id=processed_target_id,
                                rbac_profile_id=sys_profil_db_item['id'],
                                is_activated=is_link_activated,
                                is_hidden=is_link_hidden,
                                is_locked=is_link_locked,
                                is_deleted=is_link_deleted,
                            )
                            # PROCESS ENDPOINT AND PROFIL
                            await rbac_role_service.create_restricted_profil(
                                targeted_id=rbac_endpoint_data['id'],
                                rbac_profile_id=sys_profil_db_item['id'],
                                is_activated=is_link_activated,
                                is_hidden=is_link_hidden,
                                is_locked=is_link_locked,
                                is_deleted=is_link_deleted,
                            )
                            print(f"✅✅✅ Applied profile restriction to endpoint: {profil_flag}")

                    
                    # Apply API consumer restrictions
                    print(f"restricted_api_consumer_list : {restricted_api_consumer_list}")
                    for platform in restricted_api_consumer_list:
                        # Handle new object structure - platform is now an object with flag and link fields
                        platform_flag = platform.value

                        is_link_deleted = False # platform.get('is_link_deleted', False)
                        is_link_activated = True # platform.get('is_link_activated', True)
                        is_link_hidden = False # platform.get('is_link_hidden', False)
                        is_link_locked =False #  platform.get('is_link_locked', False)

                        # Fetch API consumer from db by flag
                        ref_api_consumer_db_item = await generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.REF_API_CONSUMER,
                            output_data_type=OutputDataType.DEFAULT,
                            accept_language=DEFAULT_LANGUAGE,
                            query={"filter__flag": platform_flag}
                        )

                        if ref_api_consumer_db_item:
                            # PROCESS TARGET
                            await rbac_role_service.create_restricted_api_consumer(
                                targeted_id=processed_target_id,
                                ref_api_consumer_id=ref_api_consumer_db_item['id'],
                                is_activated=is_link_activated,
                                is_hidden=is_link_hidden,
                                is_locked=is_link_locked,
                                is_deleted=is_link_deleted,
                            )
                            # PROCESS ENDPOINT AND PLATFORM
                            await rbac_role_service.create_restricted_api_consumer(
                                targeted_id=rbac_endpoint_data['id'],
                                ref_api_consumer_id=ref_api_consumer_db_item['id'],
                                is_activated=is_link_activated,
                                is_hidden=is_link_hidden,
                                is_locked=is_link_locked,
                                is_deleted=is_link_deleted,
                            )
                            print(f"✅ ✅ ✅ Applied API consumer restriction to endpoint: {platform_flag}")
            return True
        except Exception as e:
            print(f"❌ Error processing endpoint restrictions: {str(e)}")
            return False
        
    async def process_rbac_collection_meta_data(self, rbac_collection_meta_data_obj, core_seeds, generic_service, permission_data=None):
        """
        Flexible method to process all rbac_collection_meta_data_obj possibilities.
        Delegates to the standalone functions in seed_core.py.
        """
        from app.modules.core.seeds.seed_core import process_rbac_collection_meta_data as _process_rbac_collection_meta_data
        await _process_rbac_collection_meta_data(
            rbac_collection_meta_data_obj=rbac_collection_meta_data_obj,
            core_seeds=core_seeds,
            generic_service=generic_service,
            create_restricted_profil=self.create_restricted_profil,
            create_restricted_api_consumer=self.create_restricted_api_consumer,
            permission_data=permission_data,
        )

    async def recursive_rbac_title(self,item,rbac_title_id:Optional[str]=None):
        """
        Create default API consumers if they do not already exist.
        """
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(DEFAULT_LANGUAGE)
        try:
            # Initialize variables
            permissions_arr = []
            if "permissions" in item:
                permissions_arr = item["permissions"]
                print(f" permission ln : {len(permissions_arr)}")
                for permission_item in permissions_arr:
                    
                    print(f" core_seeds in : {True if 'core_seeds' in permission_item else False}")
                    if 'all_access_core_seeds' in permission_item:
                        print(f" >>> all_access_core_seeds in : {True if 'all_access_core_seeds' in permission_item else False}")
                        all_access_core_seeds = permission_item.get('all_access_core_seeds', {})
                        print(f" <<< all_access_core_seeds in : {all_access_core_seeds}")
                        # GET PERMISSION FROM DB BY FLAG
                        permis_db_item = await generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.RBAC_PERMISSION,
                            output_data_type=OutputDataType.DEFAULT,
                            accept_language= DEFAULT_LANGUAGE,
                            query={
                                "filter__flag":permission_item['flag']
                            }
                        )
                        print(f" permission_db_item founded : {permis_db_item}")
                        if permis_db_item:
                            await self.handle_all_access_core_seeds(all_access_core_seeds,permis_db_item,generic_service)
                        else :
                            print(f" permission_db_item not founded : {permission_item['flag']}")
                            # add missing permission
                            await generic_service.upsert_data_to_collection(
                                collection_key=CollectionKey.RBAC_PERMISSION,
                                filter_data={"flag":permission_item['flag']},
                                update_data=permission_item
                            )
                    if 'core_seeds' in permission_item:
                        core_seeds = permission_item.get('core_seeds', {}) 

                        # GET PERMISSION FROM DB BY FLAG
                        permission_db_item = await generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.RBAC_PERMISSION,
                            output_data_type=OutputDataType.DEFAULT,
                            accept_language= DEFAULT_LANGUAGE,
                            query={
                                "filter__flag":permission_item['flag']
                            }
                        )
                        if permission_db_item:
                            # Handle is_link_deleted at permission level: cascade delete all references
                            if permission_item.get('is_link_deleted', False):
                                await self.cascade_delete_permission_references(generic_service, permission_db_item['id'])
                                print(f"🗑️ Cascade deleted all references for permission: {permission_db_item['flag']}")
                                continue

                            # UPSERT RESCTICTED PROIFL
                            if 'restricted_profil_list' in core_seeds:
                                restricted_profil_list = core_seeds['restricted_profil_list']
                                for profil in restricted_profil_list:
                                    # Handle new object structure - profil is now an object with flag and link fields
                                    profil_flag = profil.get('flag') if isinstance(profil, dict) else profil

                                    # fetch profil from db by flag
                                    sys_profil_db_item = await generic_service.fetch_one_from_collection(
                                        collection_key=CollectionKey.RBAC_PROFILE,
                                        output_data_type=OutputDataType.DEFAULT,
                                        accept_language= DEFAULT_LANGUAGE,
                                        query={
                                            "filter__flag": profil_flag
                                        }
                                    )
                                    if sys_profil_db_item:
                                        # Check if entry should be deleted (is_link_deleted = True)
                                        if isinstance(profil, dict) and profil.get('is_link_deleted', False):
                                            # Find and delete existing entry
                                            existing_entry = await generic_service.fetch_one_from_collection(
                                                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                                                output_data_type=OutputDataType.DEFAULT,
                                                accept_language=DEFAULT_LANGUAGE,
                                                query={
                                                    "filter__rbac_profile_id": sys_profil_db_item['id'],
                                                    "filter__targeted_id": permission_db_item['id']
                                                }
                                            )
                                            if existing_entry:
                                                await generic_service.hard_delete_data_from_collection(
                                                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                                                    item_id=existing_entry['id']
                                                )
                                                print(f"🗑️ Deleted restricted profil entry (is_link_deleted=True): {sys_profil_db_item.get('name', 'N/A')} for permission: {permission_db_item['label']}")
                                                # Also delete from all child/cloned profiles based on rbac_profile_id
                                                children_profiles = await generic_service.fetch_data_from_collection(
                                                    collection_key=CollectionKey.RBAC_PROFILE,
                                                    output_data_type=OutputDataType.DEFAULT,
                                                    all_data=True,
                                                    query={
                                                        "filter__rbac_profile_id": sys_profil_db_item['id']
                                                    }
                                                )
                                                for child_profile in children_profiles:
                                                    child_existing_entry = await generic_service.fetch_one_from_collection(
                                                        collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                                                        output_data_type=OutputDataType.DEFAULT,
                                                        accept_language=DEFAULT_LANGUAGE,
                                                        query={
                                                            "filter__rbac_profile_id": child_profile['id'],
                                                            "filter__targeted_id": permission_db_item['id']
                                                        }
                                                    )
                                                    if child_existing_entry:
                                                        await generic_service.hard_delete_data_from_collection(
                                                            collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                                                            item_id=child_existing_entry['id']
                                                        )
                                                if children_profiles:
                                                    print(f"🗑️ Cascade deleted from {len(children_profiles)} child profiles for permission: {permission_db_item['label']}")
                                        else:
                                            # Create or update with link fields mapped to existing model fields
                                            update_data = {
                                                "rbac_profile_id": sys_profil_db_item['id'],
                                                "targeted_id": permission_db_item['id']
                                            }

                                            # Map link fields to existing model fields if profil is an object
                                            if isinstance(profil, dict):
                                                update_data["is_activated"] = profil.get('is_link_activated', True)
                                                update_data["is_hidden"] = profil.get('is_link_hidden', False)
                                                update_data["is_locked"] = profil.get('is_link_locked', False)
                                            else:
                                                # Default values for backward compatibility
                                                update_data["is_activated"] = True
                                                update_data["is_hidden"] = False
                                                update_data["is_locked"] = False

                                            await generic_service.upsert_data_to_collection(
                                                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                                                filter_data={
                                                    "rbac_profile_id": sys_profil_db_item['id'],
                                                    "targeted_id": permission_db_item['id']
                                                },
                                                update_data=update_data
                                            )
                                            print(f"✅ Saved restricted profil: {sys_profil_db_item['name']} for permission: {permission_db_item['label']}")
                                            # UPSERT ALL CHILD/CLONED PROFILES BASED ON rbac_profile_id
                                            children_profiles = await generic_service.fetch_data_from_collection(
                                                collection_key=CollectionKey.RBAC_PROFILE,
                                                output_data_type=OutputDataType.DEFAULT,
                                                all_data=True,
                                                query={
                                                    "filter__rbac_profile_id": sys_profil_db_item['id']
                                                }
                                            )
                                            for child_profile in children_profiles:
                                                child_update_data = {
                                                    "rbac_profile_id": child_profile['id'],
                                                    "targeted_id": permission_db_item['id'],
                                                    "is_activated": update_data.get("is_activated", True),
                                                    "is_hidden": update_data.get("is_hidden", False),
                                                    "is_locked": update_data.get("is_locked", False),
                                                }
                                                await generic_service.upsert_data_to_collection(
                                                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                                                    filter_data={
                                                        "rbac_profile_id": child_profile['id'],
                                                        "targeted_id": permission_db_item['id']
                                                    },
                                                    update_data=child_update_data
                                                )
                                            if children_profiles:
                                                print(f"✅ Propagated to {len(children_profiles)} child profiles for permission: {permission_db_item['label']}")
                            # UPSERT RESCTICTED PLATFORM
                            if 'restricted_api_consumer_list' in core_seeds:
                                restricted_api_consumer_list = core_seeds['restricted_api_consumer_list']
                                for platform in restricted_api_consumer_list:
                                    # Handle new object structure - platform is now an object with flag and link fields
                                    platform_flag = platform.get('flag') if isinstance(platform, dict) else platform

                                    # fetch platform from db by flag
                                    api_consumer_db_item = await generic_service.fetch_one_from_collection(
                                        collection_key=CollectionKey.REF_API_CONSUMER,
                                        output_data_type=OutputDataType.DEFAULT,
                                        accept_language= DEFAULT_LANGUAGE,
                                        query={
                                            "filter__flag": platform_flag
                                        }
                                    )
                                    if api_consumer_db_item:
                                        # Check if entry should be deleted (is_link_deleted = True)
                                        if isinstance(platform, dict) and platform.get('is_link_deleted', False):
                                            # Find and delete existing entry
                                            existing_entry = await generic_service.fetch_one_from_collection(
                                                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                                                output_data_type=OutputDataType.DEFAULT,
                                                accept_language=DEFAULT_LANGUAGE,
                                                query={
                                                    "filter__ref_api_consumer_id": api_consumer_db_item['id'],
                                                    "filter__targeted_id": permission_db_item['id']
                                                }
                                            )
                                            if existing_entry:
                                                await generic_service.hard_delete_data_from_collection(
                                                    collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                                                    item_id=existing_entry['id']
                                                )
                                                print(f"🗑️ Deleted restricted API consumer entry (is_link_deleted=True): {api_consumer_db_item.get('name', 'N/A')} for permission: {permission_db_item['label']}")
                                        else:
                                            # Create or update with link fields mapped to existing model fields
                                            update_data = {
                                                "ref_api_consumer_id": api_consumer_db_item['id'],
                                                "targeted_id": permission_db_item['id']
                                            }

                                            # Map link fields to existing model fields if platform is an object
                                            if isinstance(platform, dict):
                                                update_data["is_activated"] = platform.get('is_link_activated', True)
                                                update_data["is_hidden"] = platform.get('is_link_hidden', False)
                                                update_data["is_locked"] = platform.get('is_link_locked', False)
                                            else:
                                                # Default values for backward compatibility
                                                update_data["is_activated"] = True
                                                update_data["is_hidden"] = False
                                                update_data["is_locked"] = False

                                            await generic_service.upsert_data_to_collection(
                                                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                                                filter_data={
                                                    "ref_api_consumer_id": api_consumer_db_item['id'],
                                                    "targeted_id": permission_db_item['id']
                                                },
                                                update_data=update_data
                                            )
                                            print(f"✅ Saved restricted platform: {api_consumer_db_item['name']} for permission: {permission_db_item['label']}")

                            # UPSERT PERMISSION TARGET
                            if 'rbac_roles_list' in core_seeds:
                                rbac_roles_list = core_seeds['rbac_roles_list']
                                for role in rbac_roles_list:
                                    role_flag = role.get('flag') if isinstance(role, dict) else role
                                    # fetch role from db by flag
                                    rbac_role_db_item = await generic_service.fetch_one_from_collection(
                                        collection_key=CollectionKey.RBAC_ROLE,
                                        output_data_type=OutputDataType.DEFAULT,
                                        accept_language= DEFAULT_LANGUAGE,
                                        query={
                                            "filter__flag":role_flag
                                        }
                                    )
                                    if rbac_role_db_item:
                                        # check if we can delete 
                                        if isinstance(role, dict) and role.get('is_link_deleted', False):
                                            # Find and delete existing entry
                                            existing_entry = await generic_service.fetch_one_from_collection(
                                                collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                                                output_data_type=OutputDataType.DEFAULT,
                                                accept_language=DEFAULT_LANGUAGE,
                                                query={
                                                    "filter__rbac_role_id": rbac_role_db_item['id'],
                                                    "filter__rbac_permission_id": permission_db_item['id']
                                                }
                                            )
                                            if existing_entry:
                                                await generic_service.hard_delete_data_from_collection(
                                                    collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                                                    item_id=existing_entry['id']
                                                )
                                                print(f"🗑️ Deleted permission role entry (is_link_deleted=True): {rbac_role_db_item.get('name', 'N/A')} for permission: {permission_db_item['label']}")
                                                # check all from children from sys_core_role_id and delete
                                                children_roles = await generic_service.fetch_data_from_collection(
                                                    collection_key=CollectionKey.RBAC_ROLE,
                                                    output_data_type=OutputDataType.DEFAULT,
                                                    all_data=True,
                                                    query={
                                                        "filter__sys_core_role_id":rbac_role_db_item['id']
                                                    }
                                                )
                                                for child_role in children_roles:
                                                    # Find and delete existing entry
                                                    existing_entry = await generic_service.fetch_one_from_collection(
                                                        collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                                                        output_data_type=OutputDataType.DEFAULT,
                                                        accept_language=DEFAULT_LANGUAGE,
                                                        query={
                                                            "filter__rbac_role_id": child_role['id'],
                                                            "filter__rbac_permission_id": permission_db_item['id']
                                                        }
                                                    )
                                                    if existing_entry:
                                                        await generic_service.hard_delete_data_from_collection(
                                                            collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                                                            item_id=existing_entry['id']
                                                        )
                                        else :
                                            await generic_service.upsert_data_to_collection(
                                                collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                                                filter_data={
                                                    "rbac_role_id":rbac_role_db_item['id'],
                                                    "rbac_permission_id":permission_db_item['id']
                                                },
                                                update_data={
                                                    "rbac_role_id":rbac_role_db_item['id'],
                                                    "rbac_permission_id":permission_db_item['id']
                                                }
                                            )
                                            print(f"\n\n\n saved permission role : {rbac_role_db_item['name']} for permission : {permission_db_item['label']} \n\n\n")
                                            # UPSERT ALL ROLE CHILDREN BASED ON SYS_CORE_ROLE_ID
                                            children_roles = await generic_service.fetch_data_from_collection(
                                                collection_key=CollectionKey.RBAC_ROLE,
                                                output_data_type=OutputDataType.DEFAULT,
                                                all_data=True,
                                                query={
                                                    "filter__sys_core_role_id":rbac_role_db_item['id']
                                                }
                                            )
                                            for child_role in children_roles:
                                                await generic_service.upsert_data_to_collection(
                                                    collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                                                    filter_data={
                                                        "rbac_role_id":child_role['id'],
                                                        "rbac_permission_id":permission_db_item['id']
                                                    },
                                                    update_data={
                                                        "rbac_role_id":child_role['id'],
                                                        "rbac_permission_id":permission_db_item['id']
                                                    }
                                                )
                            # UPSERT PERMISSION TARGET AND APPLICATION
                            if 'sys_apps_list' in core_seeds:
                                sys_apps_list = core_seeds['sys_apps_list']
                                print(f"\n\n\n sys_apps_list >>> {len(sys_apps_list)}")
                                for application in sys_apps_list:

                                    # application flag
                                    application_flag = application.get('flag') if isinstance(application, dict) else application
                                    print(f"\n\n\n app flags >>> {len(application_flag)}")
                                    # fetch application from db by flag
                                    rbac_application_db_item = await generic_service.fetch_one_from_collection(
                                        collection_key=CollectionKey.SYS_APPLICATION,
                                        output_data_type=OutputDataType.DEFAULT,
                                        accept_language= DEFAULT_LANGUAGE,
                                        query={
                                            "filter__flag":application_flag
                                        }
                                    )
                                    print(f"\n\n\n app founded flags >>> {True if rbac_application_db_item else False}")
                                    if rbac_application_db_item:
                                        processed_target_id = None
                                        # check if we can delete
                                        print(f"\n\n\n app founded can delete >>> {isinstance(application, dict) and application.get('is_link_deleted', False)}")
                                        if isinstance(application, dict) and application.get('is_link_deleted', False):
                                            # Cascade delete: app permission targets + restrictions + all sub-menus
                                            await self.cascade_delete_app_references(generic_service, rbac_application_db_item['id'])
                                            print(f"🗑️ Cascade deleted all references for app: {rbac_application_db_item.get('name', 'N/A')}")
                                            continue
                                        else:
                                            saved_target = await generic_service.upsert_data_to_collection(
                                                collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                filter_data={
                                                    "targeted_id":rbac_application_db_item['id'],
                                                    "rbac_permission_id":permission_db_item['id']
                                                },
                                                update_data={
                                                    "targeted_id":rbac_application_db_item['id'],
                                                    "rbac_permission_id":permission_db_item['id']
                                                }
                                            )
                                            print(f"\n\n\n saved permission target for app : {rbac_application_db_item['name']} for permission : {permission_db_item['label']} \n\n\n")
                                            processed_target_id = saved_target if isinstance(saved_target,str) else str(saved_target['id'])
                                        # 
                                        # SAVE PROFILE RESTRICTION
                                        if 'restricted_profil_list' in core_seeds:
                                            restricted_profil_list = core_seeds['restricted_profil_list']
                                            print(f"\n\n\n restricted profil for app : {rbac_application_db_item['name']} processed_target_id : {processed_target_id} \n\n\n")
                                            for profil in restricted_profil_list:
                                                # Handle new object structure - profil is now an object with flag and link fields
                                                profil_flag = profil.get('flag') if isinstance(profil, dict) else profil

                                                print(f"\n\n app profil : {profil}")

                                                is_link_deleted = profil.get('is_link_deleted', False)
                                                is_link_activated = profil.get('is_link_activated', True)
                                                is_link_hidden = profil.get('is_link_hidden', False)
                                                is_link_locked = profil.get('is_link_locked', False)
                                                # fetch profil from db by flag
                                                sys_profil_db_item = await generic_service.fetch_one_from_collection(
                                                    collection_key=CollectionKey.RBAC_PROFILE,
                                                    output_data_type=OutputDataType.DEFAULT,
                                                    accept_language= DEFAULT_LANGUAGE,
                                                    query={
                                                        "filter__flag": profil_flag
                                                    }
                                                )
                                                print(f"\n\n app profil founded : {True if sys_profil_db_item else False}")
                                                print(f"\n\n app profil founded processed_target_id : {processed_target_id}")
                                                if sys_profil_db_item:
                                                    await self.create_restricted_profil(
                                                        targeted_id=processed_target_id,
                                                        rbac_profile_id=sys_profil_db_item['id'],
                                                        is_activated=is_link_activated,
                                                        is_hidden=is_link_hidden,
                                                        is_locked=is_link_locked,
                                                        is_deleted=is_link_deleted,
                                                    )

                                        # SAVE API CONSUMER RESTRICTION
                                        if 'restricted_api_consumer_list' in core_seeds:
                                            restricted_api_consumer_list = core_seeds['restricted_api_consumer_list']
                                            for api_consumer in restricted_api_consumer_list:
                                                # Handle new object structure - api_consumer is now an object with flag and link fields
                                                api_consumer_flag = api_consumer.get('flag') if isinstance(api_consumer, dict) else api_consumer
                                                is_link_deleted = api_consumer.get('is_link_deleted', False)
                                                is_link_activated = api_consumer.get('is_link_activated', True)
                                                is_link_hidden = api_consumer.get('is_link_hidden', False)
                                                is_link_locked = api_consumer.get('is_link_locked', False)
                                                # fetch api consumer from db by flag
                                                ref_api_consumer_db_item = await generic_service.fetch_one_from_collection(
                                                    collection_key=CollectionKey.REF_API_CONSUMER,
                                                    output_data_type=OutputDataType.DEFAULT,
                                                    accept_language= DEFAULT_LANGUAGE,
                                                    query={
                                                        "filter__flag":api_consumer_flag
                                                    }
                                                )
                                                if ref_api_consumer_db_item:
                                                    await self.create_restricted_api_consumer(
                                                        targeted_id=processed_target_id,
                                                        ref_api_consumer_id=ref_api_consumer_db_item['id'],
                                                        is_activated=is_link_activated,
                                                        is_hidden=is_link_hidden,
                                                        is_locked=is_link_locked,
                                                        is_deleted=is_link_deleted,
                                                    )

                            # UPSERT PERMISSION TARGET AND MENU
                            if 'sys_menus_list' in core_seeds:
                                sys_menus_list = core_seeds['sys_menus_list']
                                for menu in sys_menus_list:
                                    # fetch menu from db by flag
                                    rbac_menu_db_item = await generic_service.fetch_one_from_collection(
                                        collection_key=CollectionKey.SYS_MENU,
                                        output_data_type=OutputDataType.DEFAULT,
                                        accept_language= DEFAULT_LANGUAGE,
                                        query={
                                            "filter__flag":menu.get('flag') if isinstance(menu, dict) else menu
                                        } 
                                    )
                                    if rbac_menu_db_item:
                                        processed_target_id = None
                                        # check if we can delete
                                        if isinstance(menu, dict) and menu.get('is_link_deleted', False):
                                            # Cascade delete: menu permission targets + restrictions + all sub-menus
                                            await self.cascade_delete_menu_references(generic_service, rbac_menu_db_item['id'])
                                            print(f"🗑️ Cascade deleted all references for menu: {rbac_menu_db_item.get('name', 'N/A')}")
                                            continue
                                        else:
                                            saved_target = await generic_service.upsert_data_to_collection(
                                                collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                filter_data={
                                                    "targeted_id":rbac_menu_db_item['id'],
                                                    "rbac_permission_id":permission_db_item['id']
                                                },
                                                update_data={
                                                    "targeted_id":rbac_menu_db_item['id'],
                                                    "rbac_permission_id":permission_db_item['id']
                                                }
                                            )
                                            print(f"\n\n\n saved permission target : {rbac_menu_db_item['name']} for permission : {permission_db_item['label']} \n\n\n")
                                            processed_target_id = saved_target if isinstance(saved_target,str) else str(saved_target['id'])
                                        # SAVE PROFILE RESTRICTION
                                        if 'restricted_profil_list' in core_seeds:
                                            restricted_profil_list = core_seeds['restricted_profil_list']
                                            for profil in restricted_profil_list:
                                                # Handle new object structure - profil is now an object with flag and link fields
                                                profil_flag = profil.get('flag') if isinstance(profil, dict) else profil

                                                is_link_deleted = profil.get('is_link_deleted', False)
                                                is_link_activated = profil.get('is_link_activated', True)
                                                is_link_hidden = profil.get('is_link_hidden', False)
                                                is_link_locked = profil.get('is_link_locked', False)

                                                # fetch profil from db by flag
                                                sys_profil_db_item = await generic_service.fetch_one_from_collection(
                                                    collection_key=CollectionKey.RBAC_PROFILE,
                                                    output_data_type=OutputDataType.DEFAULT,
                                                    accept_language= DEFAULT_LANGUAGE,
                                                    query={
                                                        "filter__flag": profil_flag
                                                    }
                                                )
                                                if sys_profil_db_item:
                                                    await self.create_restricted_profil(
                                                        targeted_id=processed_target_id,
                                                        rbac_profile_id=sys_profil_db_item['id'],
                                                        is_activated=is_link_activated,
                                                        is_hidden=is_link_hidden,
                                                        is_locked=is_link_locked,
                                                        is_deleted=is_link_deleted,
                                                    )

                                        # SAVE API CONSUMER RESTRICTION
                                        if 'restricted_api_consumer_list' in core_seeds:
                                            restricted_api_consumer_list = core_seeds['restricted_api_consumer_list']
                                            for api_consumer in restricted_api_consumer_list:
                                                # Handle new object structure - api_consumer is now an object with flag and link fields
                                                api_consumer_flag = api_consumer.get('flag') if isinstance(api_consumer, dict) else api_consumer
                                                is_link_deleted = api_consumer.get('is_link_deleted', False)
                                                is_link_activated = api_consumer.get('is_link_activated', True)
                                                is_link_hidden = api_consumer.get('is_link_hidden', False)
                                                is_link_locked = api_consumer.get('is_link_locked', False)
                                                # fetch api consumer from db by flag
                                                ref_api_consumer_db_item = await generic_service.fetch_one_from_collection(
                                                    collection_key=CollectionKey.REF_API_CONSUMER,
                                                    output_data_type=OutputDataType.DEFAULT,
                                                    accept_language= DEFAULT_LANGUAGE,
                                                    query={
                                                        "filter__flag": api_consumer_flag
                                                    }
                                                )
                                                if ref_api_consumer_db_item:
                                                    await self.create_restricted_api_consumer(
                                                        targeted_id=processed_target_id,
                                                        ref_api_consumer_id=ref_api_consumer_db_item['id'],
                                                        is_activated=is_link_activated,
                                                        is_hidden=is_link_hidden,
                                                        is_locked=is_link_locked,
                                                        is_deleted=is_link_deleted,
                                                    )

                            # UPSERT PERMISSION TARGET AND ENDPOINT
                            if 'rbac_endpoints_list' in core_seeds:
                                rbac_endpoints_list = core_seeds['rbac_endpoints_list']
                                for endpoint in rbac_endpoints_list:
                                    # Support both plain URL string and dict with 'url' + 'is_link_deleted'
                                    endpoint_url = endpoint.get('url') if isinstance(endpoint, dict) else endpoint
                                    # fetch endpoint from db by url
                                    rbac_endpoint_db_item = await generic_service.fetch_one_from_collection(
                                        collection_key=CollectionKey.RBAC_ENDPOINT,
                                        output_data_type=OutputDataType.DEFAULT,
                                        accept_language= DEFAULT_LANGUAGE,
                                        query={
                                            "filter__url": endpoint_url
                                        }
                                    )
                                    if rbac_endpoint_db_item:
                                        processed_target_id = None
                                        # check if we can delete
                                        if isinstance(endpoint, dict) and endpoint.get('is_link_deleted', False):
                                            # Cascade delete: all permission targets + restrictions + direct restrictions on endpoint
                                            await self.delete_all_permission_targets_and_restrictions(generic_service, rbac_endpoint_db_item['id'])
                                            await generic_service.hard_delete_data_from_collection(
                                                collection_key=CollectionKey.RBAC_ENDPOINT,
                                                item_id=str(rbac_endpoint_db_item['id'])
                                            )
                                            print(f"🗑️ Cascade deleted all references for endpoint: {endpoint_url}")
                                            continue
                                        else:
                                            saved_target = await generic_service.upsert_data_to_collection(
                                                collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                filter_data={
                                                    "targeted_id":rbac_endpoint_db_item['id'],
                                                    "rbac_permission_id":permission_db_item['id']
                                                },
                                                update_data={
                                                    "targeted_id":rbac_endpoint_db_item['id'],
                                                    "rbac_permission_id":permission_db_item['id']
                                                }
                                            )
                                            print(f"\n\n\n saved permission target : {rbac_endpoint_db_item['label']} for permission : {permission_db_item['label']} \n\n\n")
                                            processed_target_id = saved_target if isinstance(saved_target,str) else str(saved_target['id'])
                                        # SAVE PROFILE RESTRICTION
                                        if 'restricted_profil_list' in core_seeds:
                                            restricted_profil_list = core_seeds['restricted_profil_list']
                                            for profil in restricted_profil_list:
                                                # Handle new object structure - profil is now an object with flag and link fields
                                                profil_flag = profil.get('flag') if isinstance(profil, dict) else profil

                                                is_link_deleted = profil.get('is_link_deleted', False)
                                                is_link_activated = profil.get('is_link_activated', True)
                                                is_link_hidden = profil.get('is_link_hidden', False)
                                                is_link_locked = profil.get('is_link_locked', False)
                                                # fetch profil from db by flag
                                                sys_profil_db_item = await generic_service.fetch_one_from_collection(
                                                    collection_key=CollectionKey.RBAC_PROFILE,
                                                    output_data_type=OutputDataType.DEFAULT,
                                                    accept_language= DEFAULT_LANGUAGE,
                                                    query={
                                                        "filter__flag": profil_flag
                                                    }
                                                )
                                                if sys_profil_db_item:
                                                    await self.create_restricted_profil(
                                                        targeted_id=processed_target_id,
                                                        rbac_profile_id=sys_profil_db_item['id'],
                                                        is_activated=is_link_activated,
                                                        is_hidden=is_link_hidden,
                                                        is_locked=is_link_locked,
                                                        is_deleted=is_link_deleted,
                                                    )

                                        # SAVE API CONSUMER RESTRICTION
                                        if 'restricted_api_consumer_list' in core_seeds:
                                            restricted_api_consumer_list = core_seeds['restricted_api_consumer_list']
                                            for api_consumer in restricted_api_consumer_list:
                                                # Handle new object structure - api_consumer is now an object with flag and link fields
                                                api_consumer_flag = api_consumer.get('flag') if isinstance(api_consumer, dict) else api_consumer
                                                is_link_deleted = api_consumer.get('is_link_deleted', False)
                                                is_link_activated = api_consumer.get('is_link_activated', True)
                                                is_link_hidden = api_consumer.get('is_link_hidden', False)
                                                is_link_locked = api_consumer.get('is_link_locked', False)
                                                
                                                # fetch api consumer from db by flag
                                                ref_api_consumer_db_item = await generic_service.fetch_one_from_collection(
                                                    collection_key=CollectionKey.REF_API_CONSUMER,
                                                    output_data_type=OutputDataType.DEFAULT,
                                                    accept_language= DEFAULT_LANGUAGE,
                                                    query={
                                                        "filter__flag": api_consumer_flag
                                                    }
                                                )
                                                if ref_api_consumer_db_item:
                                                    await self.create_restricted_api_consumer(
                                                        targeted_id=processed_target_id,
                                                        ref_api_consumer_id=ref_api_consumer_db_item['id'],
                                                        is_activated=is_link_activated,
                                                        is_hidden=is_link_hidden,
                                                        is_locked=is_link_locked,
                                                        is_deleted=is_link_deleted,
                                                    )

                            # UPSERT PERMISSTION TARGET, STANDALONE ACTION AND MENU 
                            if 'rbac_standalone_actions_obj' in core_seeds:
                                rbac_standalone_actions_obj = core_seeds['rbac_standalone_actions_obj']
                                if 'action_to_menus' in rbac_standalone_actions_obj:
                                    standalone_action_list_to_menus = rbac_standalone_actions_obj['action_to_menus']
                                    for custom_component in standalone_action_list_to_menus:
                                        is_link_deleted = custom_component.get('is_link_deleted', False)
                                        # fetch standalone action from db by flag
                                        rbac_standalone_action_db_item = await generic_service.fetch_one_from_collection(
                                            collection_key=CollectionKey.RBAC_ACTION,
                                            output_data_type=OutputDataType.DEFAULT,
                                            accept_language= DEFAULT_LANGUAGE,
                                            query={
                                                "filter__hard_code_flag":custom_component['action_hard_code_flag'],
                                                "filter__flag":custom_component['action_flag'],
                                            }
                                        )
                                        # fetch menu from db by flag
                                        rbac_menu_db_item = await generic_service.fetch_one_from_collection(
                                            collection_key=CollectionKey.SYS_MENU,
                                            output_data_type=OutputDataType.DEFAULT,
                                            accept_language= DEFAULT_LANGUAGE,
                                            query={
                                                "filter__flag":custom_component['menu_flag']
                                            }
                                        )
                                        if rbac_standalone_action_db_item and rbac_menu_db_item:
                                            if is_link_deleted == True:
                                                get_target = await generic_service.fetch_one_from_collection(
                                                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                    query={
                                                        "filter__targeted_id":rbac_menu_db_item['id'],
                                                        "filter__rbac_action_id":rbac_standalone_action_db_item['id'],
                                                        "filter__rbac_permission_id":permission_db_item['id'],
                                                    }, 
                                                )
                                                if get_target:
                                                    await generic_service.hard_delete_data_from_collection(
                                                        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                        item_id=get_target['id']
                                                    )
                                            else:
                                                saved_target = await generic_service.upsert_data_to_collection(
                                                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                    filter_data={
                                                        "targeted_id":rbac_menu_db_item['id'],
                                                        "rbac_action_id":rbac_standalone_action_db_item['id'],
                                                        "rbac_permission_id":permission_db_item['id'],
                                                    },
                                                    update_data={
                                                        "targeted_id":rbac_menu_db_item['id'],
                                                        "rbac_action_id":rbac_standalone_action_db_item['id'],
                                                        "rbac_permission_id":permission_db_item['id'],
                                                    }
                                                )
                                                print(f"\n\n\n saved permission target : {rbac_standalone_action_db_item['label']} for permission : {permission_db_item['label']} \n\n\n")
                                                processed_target_id = saved_target if isinstance(saved_target,str) else str(saved_target['id'])
                                                # SAVE PROFILE RESTRICTION
                                                if 'restricted_profil_list' in core_seeds:
                                                    restricted_profil_list = core_seeds['restricted_profil_list']
                                                    for profil in restricted_profil_list:
                                                        # Handle new object structure - profil is now an object with flag and link fields
                                                        profil_flag = profil.get('flag') if isinstance(profil, dict) else profil
                                                        is_link_deleted = profil.get('is_link_deleted', False)
                                                        is_link_activated = profil.get('is_link_activated', True)
                                                        is_link_hidden = profil.get('is_link_hidden', False)
                                                        is_link_locked = profil.get('is_link_locked', False)
                                                        # fetch profil from db by flag
                                                        sys_profil_db_item = await generic_service.fetch_one_from_collection(
                                                            collection_key=CollectionKey.RBAC_PROFILE,
                                                            output_data_type=OutputDataType.DEFAULT,
                                                            accept_language= DEFAULT_LANGUAGE,
                                                            query={
                                                                "filter__flag": profil_flag
                                                            }
                                                        )
                                                        if sys_profil_db_item:
                                                            await self.create_restricted_profil(
                                                                targeted_id=processed_target_id,
                                                                rbac_profile_id=sys_profil_db_item['id'],
                                                                is_activated=is_link_activated,
                                                                is_hidden=is_link_hidden,
                                                                is_locked=is_link_locked,
                                                                is_deleted=is_link_deleted,
                                                            )

                                                # SAVE API CONSUMER RESTRICTION
                                                if 'restricted_api_consumer_list' in core_seeds:
                                                    restricted_api_consumer_list = core_seeds['restricted_api_consumer_list']
                                                    for api_consumer in restricted_api_consumer_list:
                                                        # Handle new object structure - api_consumer is now an object with flag and link fields
                                                        api_consumer_flag = api_consumer.get('flag') if isinstance(api_consumer, dict) else api_consumer
                                                        is_link_deleted = api_consumer.get('is_link_deleted', False)
                                                        is_link_activated = api_consumer.get('is_link_activated', True)
                                                        is_link_hidden = api_consumer.get('is_link_hidden', False)
                                                        is_link_locked = api_consumer.get('is_link_locked', False)
                                                        # fetch api consumer from db by flag
                                                        ref_api_consumer_db_item = await generic_service.fetch_one_from_collection(
                                                            collection_key=CollectionKey.REF_API_CONSUMER,
                                                            output_data_type=OutputDataType.DEFAULT,
                                                            accept_language= DEFAULT_LANGUAGE,
                                                            query={
                                                                "filter__flag": api_consumer_flag
                                                            }
                                                        )
                                                        if ref_api_consumer_db_item:
                                                            await self.create_restricted_api_consumer(
                                                                targeted_id=processed_target_id,
                                                                ref_api_consumer_id=ref_api_consumer_db_item['id'],
                                                                is_activated=is_link_activated,
                                                                is_hidden=is_link_hidden,
                                                                is_locked=is_link_locked,
                                                                is_deleted=is_link_deleted,
                                                            )
                            
                                if 'action_to_apps' in rbac_standalone_actions_obj:
                                    standalone_action_list_to_apps = rbac_standalone_actions_obj['action_to_apps']
                                    for custom_component in standalone_action_list_to_apps:
                                        is_link_deleted = custom_component.get('is_link_deleted', False)
                                        # fetch standalone action from db by flag
                                        rbac_standalone_action_db_item = await generic_service.fetch_one_from_collection(
                                            collection_key=CollectionKey.RBAC_ACTION,
                                            output_data_type=OutputDataType.DEFAULT,
                                            accept_language= DEFAULT_LANGUAGE,
                                            query={
                                                "filter__hard_code_flag":custom_component['action_hard_code_flag'],
                                                "filter__flag":custom_component['action_flag'],
                                            }
                                        )
                                        # custom_component >> : {'menu_flag': '', 'action_flag': 'table_action_add', 'action_is_standalone': True, 'action_hard_code_flag': 'creation_action_flag', 'action_label': 'Créer'} 
                                        print(f"\n\n\n custom_component >> : {custom_component} \n\n\n")

                                        # fetch menu from db by flag
                                        rbac_menu_db_item = await generic_service.fetch_one_from_collection(
                                            collection_key=CollectionKey.SYS_APPLICATION,
                                            output_data_type=OutputDataType.DEFAULT,
                                            accept_language= DEFAULT_LANGUAGE,
                                            query={
                                                "filter__flag":custom_component['app_flag']
                                            }
                                        )
                                        if rbac_standalone_action_db_item and rbac_menu_db_item:
                                            if is_link_deleted == True:
                                                get_target = await generic_service.fetch_one_from_collection(
                                                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                    query={
                                                        "filter__targeted_id":rbac_menu_db_item['id'],
                                                        "filter__rbac_action_id":rbac_standalone_action_db_item['id'],
                                                        "filter__rbac_permission_id":permission_db_item['id'],
                                                    }, 
                                                )
                                                if get_target:
                                                    await generic_service.hard_delete_data_from_collection(
                                                        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                        item_id=get_target['id']
                                                    )
                                            else:
                                                saved_target = await generic_service.upsert_data_to_collection(
                                                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                    filter_data={
                                                        "targeted_id":rbac_menu_db_item['id'],
                                                        "rbac_action_id":rbac_standalone_action_db_item['id'],
                                                        "rbac_permission_id":permission_db_item['id'],
                                                    },
                                                    update_data={
                                                        "targeted_id":rbac_menu_db_item['id'],
                                                        "rbac_action_id":rbac_standalone_action_db_item['id'],
                                                        "rbac_permission_id":permission_db_item['id'],
                                                    }
                                                )
                                                print(f"\n\n\n saved permission target : {rbac_standalone_action_db_item['label']} for permission : {permission_db_item['label']} \n\n\n")
                                                processed_target_id = saved_target if isinstance(saved_target,str) else str(saved_target['id'])
                                                # SAVE PROFILE RESTRICTION
                                                if 'restricted_profil_list' in core_seeds:
                                                    restricted_profil_list = core_seeds['restricted_profil_list']
                                                    for profil in restricted_profil_list:
                                                        # Handle new object structure - profil is now an object with flag and link fields
                                                        profil_flag = profil.get('flag') if isinstance(profil, dict) else profil
                                                        is_link_deleted = profil.get('is_link_deleted', False)
                                                        is_link_activated = profil.get('is_link_activated', True)
                                                        is_link_hidden = profil.get('is_link_hidden', False)
                                                        is_link_locked = profil.get('is_link_locked', False)
                                                        # fetch profil from db by flag
                                                        sys_profil_db_item = await generic_service.fetch_one_from_collection(
                                                            collection_key=CollectionKey.RBAC_PROFILE,
                                                            output_data_type=OutputDataType.DEFAULT,
                                                            accept_language= DEFAULT_LANGUAGE,
                                                            query={
                                                                "filter__flag": profil_flag
                                                            }
                                                        )
                                                        if sys_profil_db_item:
                                                            await self.create_restricted_profil(
                                                                targeted_id=processed_target_id,
                                                                rbac_profile_id=sys_profil_db_item['id'],
                                                                is_activated=is_link_activated,
                                                                is_hidden=is_link_hidden,
                                                                is_locked=is_link_locked,
                                                                is_deleted=is_link_deleted,
                                                            )

                                                # SAVE API CONSUMER RESTRICTION
                                                if 'restricted_api_consumer_list' in core_seeds:
                                                    restricted_api_consumer_list = core_seeds['restricted_api_consumer_list']
                                                    for api_consumer in restricted_api_consumer_list:
                                                        # Handle new object structure - api_consumer is now an object with flag and link fields
                                                        api_consumer_flag = api_consumer.get('flag') if isinstance(api_consumer, dict) else api_consumer
                                                        is_link_deleted = api_consumer.get('is_link_deleted', False)
                                                        is_link_activated = api_consumer.get('is_link_activated', True)
                                                        is_link_hidden = api_consumer.get('is_link_hidden', False)
                                                        is_link_locked = api_consumer.get('is_link_locked', False)
                                                        # fetch api consumer from db by flag
                                                        ref_api_consumer_db_item = await generic_service.fetch_one_from_collection(
                                                            collection_key=CollectionKey.REF_API_CONSUMER,
                                                            output_data_type=OutputDataType.DEFAULT,
                                                            accept_language= DEFAULT_LANGUAGE,
                                                            query={
                                                                "filter__flag": api_consumer_flag
                                                            }
                                                        )
                                                        if ref_api_consumer_db_item:
                                                            await self.create_restricted_api_consumer(
                                                                targeted_id=processed_target_id,
                                                                ref_api_consumer_id=ref_api_consumer_db_item['id'],
                                                                is_activated=is_link_activated,
                                                                is_hidden=is_link_hidden,
                                                                is_locked=is_link_locked,
                                                                is_deleted=is_link_deleted,
                                                            )
                            
                            # UPSERT PERMISSTION TARGET, CUSTOM ACTION AND MENU 
                            if 'rbac_custom_actions_obj' in core_seeds:
                                rbac_custom_actions_obj = core_seeds['rbac_custom_actions_obj']
                                if 'action_to_menus' in rbac_custom_actions_obj:
                                    custom_action_list_to_menus = rbac_custom_actions_obj['action_to_menus']
                                    for custom_action_to_m in custom_action_list_to_menus:
                                        is_link_deleted = custom_action_to_m.get('is_link_deleted', False)
                                        
                                        # fetch menu from db by flag
                                        rbac_menu_db_item = await generic_service.fetch_one_from_collection(
                                            collection_key=CollectionKey.SYS_MENU,
                                            output_data_type=OutputDataType.DEFAULT,
                                            accept_language= DEFAULT_LANGUAGE,
                                            query={
                                                "filter__flag":custom_action_to_m['menu_flag']
                                            }
                                        )
                                        if not rbac_menu_db_item:
                                            continue
                                        # fetch standalone action from db by flag
                                        rbac_custom_action_db_item = await generic_service.upsert_data_to_collection(
                                            collection_key=CollectionKey.RBAC_ACTION,
                                            accept_language= DEFAULT_LANGUAGE,
                                            filter_data={
                                                "hard_code_flag":custom_action_to_m['action_hard_code_flag'],
                                                "flag":custom_action_to_m['action_flag'],
                                                "rbac_permission_id":permission_db_item['id'],
                                                "targeted_id":rbac_menu_db_item['id'],
                                            },
                                            update_data={
                                                "hard_code_flag":custom_action_to_m['action_hard_code_flag'],
                                                "flag":custom_action_to_m['action_flag'],
                                                "rbac_permission_id":permission_db_item['id'],
                                                "is_standalone":custom_action_to_m['action_is_standalone'],
                                                "label":custom_action_to_m['action_label'],
                                                "targeted_id":rbac_menu_db_item['id'],
                                            },
                                        )
                                        if isinstance(rbac_custom_action_db_item,str):
                                            rbac_custom_action_db_item = await generic_service.fetch_one_from_collection(
                                                collection_key=CollectionKey.RBAC_ACTION,
                                                output_data_type=OutputDataType.DEFAULT,
                                                accept_language= DEFAULT_LANGUAGE,
                                                query={
                                                    "filter___id":rbac_custom_action_db_item
                                                }
                                            )
                                        
                                        if rbac_custom_action_db_item and rbac_menu_db_item:
                                            # print(f"custom_action on : {custom_action}")
                                            # print(f"custom_action is deleted link : {is_link_deleted}")
                                            if is_link_deleted == True:
                                                get_target = await generic_service.fetch_one_from_collection(
                                                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                    query={
                                                        "filter__targeted_id":rbac_menu_db_item['id'],
                                                        "filter__rbac_action_id":rbac_custom_action_db_item['id'],
                                                        "filter__rbac_permission_id":permission_db_item['id'],
                                                    }, 
                                                )
                                                if get_target:
                                                    await generic_service.hard_delete_data_from_collection(
                                                        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                        item_id=get_target['id']
                                                    )
                                            else:
                                                saved_target = await generic_service.upsert_data_to_collection(
                                                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                    filter_data={
                                                        "targeted_id":rbac_menu_db_item['id'],
                                                        "rbac_action_id":rbac_custom_action_db_item['id'],
                                                        "rbac_permission_id":permission_db_item['id'],
                                                    },
                                                    update_data={
                                                        "targeted_id":rbac_menu_db_item['id'],
                                                        "rbac_action_id":rbac_custom_action_db_item['id'],
                                                        "rbac_permission_id":permission_db_item['id'],
                                                    }
                                                )
                                                print(f"\n\n\n saved permission target : {rbac_custom_action_db_item['label']} for permission : {permission_db_item['label']} \n\n\n")
                                                processed_target_id = saved_target if isinstance(saved_target,str) else str(saved_target['id'])
                                                # SAVE PROFILE RESTRICTION
                                                if 'restricted_profil_list' in core_seeds:
                                                    restricted_profil_list = core_seeds['restricted_profil_list']
                                                    for profil in restricted_profil_list:
                                                        # Handle new object structure - profil is now an object with flag and link fields
                                                        profil_flag = profil.get('flag') if isinstance(profil, dict) else profil

                                                        is_link_deleted = profil.get('is_link_deleted', False)
                                                        is_link_activated = profil.get('is_link_activated', True)
                                                        is_link_hidden = profil.get('is_link_hidden', False)
                                                        is_link_locked = profil.get('is_link_locked', False)
                                                        # fetch profil from db by flag
                                                        sys_profil_db_item = await generic_service.fetch_one_from_collection(
                                                            collection_key=CollectionKey.RBAC_PROFILE,
                                                            output_data_type=OutputDataType.DEFAULT,
                                                            accept_language= DEFAULT_LANGUAGE,
                                                            query={
                                                                "filter__flag": profil_flag
                                                            }
                                                        )
                                                        if sys_profil_db_item:
                                                            await self.create_restricted_profil(
                                                                targeted_id=processed_target_id,
                                                                rbac_profile_id=sys_profil_db_item['id'],
                                                                is_activated=is_link_activated,
                                                                is_hidden=is_link_hidden,
                                                                is_locked=is_link_locked,
                                                                is_deleted=is_link_deleted,
                                                            )

                                                # SAVE API CONSUMER RESTRICTION
                                                if 'restricted_api_consumer_list' in core_seeds:
                                                    restricted_api_consumer_list = core_seeds['restricted_api_consumer_list']
                                                    for api_consumer in restricted_api_consumer_list:
                                                        # Handle new object structure - api_consumer is now an object with flag and link fields
                                                        api_consumer_flag = api_consumer.get('flag') if isinstance(api_consumer, dict) else api_consumer
                                                        is_link_deleted = api_consumer.get('is_link_deleted', False)
                                                        is_link_activated = api_consumer.get('is_link_activated', True)
                                                        is_link_hidden = api_consumer.get('is_link_hidden', False)
                                                        is_link_locked = api_consumer.get('is_link_locked', False)
                                                        # fetch api consumer from db by flag
                                                        ref_api_consumer_db_item = await generic_service.fetch_one_from_collection(
                                                            collection_key=CollectionKey.REF_API_CONSUMER,
                                                            output_data_type=OutputDataType.DEFAULT,
                                                            accept_language= DEFAULT_LANGUAGE,
                                                            query={
                                                                "filter__flag": api_consumer_flag
                                                            }
                                                        )
                                                        if ref_api_consumer_db_item:
                                                            await self.create_restricted_api_consumer(
                                                                targeted_id=processed_target_id,
                                                                ref_api_consumer_id=ref_api_consumer_db_item['id'],
                                                                is_activated=is_link_activated,
                                                                is_hidden=is_link_hidden,
                                                                is_locked=is_link_locked,
                                                                is_deleted=is_link_deleted,
                                                            )
                        
                                if 'action_to_apps' in rbac_custom_actions_obj:
                                    custom_action_list_to_apps = rbac_custom_actions_obj['action_to_apps']
                                    for custom_action_to_m in custom_action_list_to_apps:
                                        is_link_deleted = custom_action_to_m.get('is_link_deleted', False)
                                        
                                        # fetch menu from db by flag
                                        rbac_menu_db_item = await generic_service.fetch_one_from_collection(
                                            collection_key=CollectionKey.SYS_APPLICATION,
                                            output_data_type=OutputDataType.DEFAULT,
                                            accept_language= DEFAULT_LANGUAGE,
                                            query={
                                                "filter__flag":custom_action_to_m['app_flag']
                                            }
                                        )
                                        if not rbac_menu_db_item:
                                            continue
                                        # fetch standalone action from db by flag
                                        rbac_custom_action_db_item = await generic_service.upsert_data_to_collection(
                                            collection_key=CollectionKey.RBAC_ACTION,
                                            accept_language= DEFAULT_LANGUAGE,
                                            filter_data={
                                                "hard_code_flag":custom_action_to_m['action_hard_code_flag'],
                                                "flag":custom_action_to_m['action_flag'],
                                                "rbac_permission_id":permission_db_item['id'],
                                                "targeted_id":rbac_menu_db_item['id'],
                                            },
                                            update_data={
                                                "hard_code_flag":custom_action_to_m['action_hard_code_flag'],
                                                "flag":custom_action_to_m['action_flag'],
                                                "rbac_permission_id":permission_db_item['id'],
                                                "is_standalone":custom_action_to_m['action_is_standalone'],
                                                "label":custom_action_to_m['action_label'],
                                                "targeted_id":rbac_menu_db_item['id'],
                                            },
                                        )
                                        if isinstance(rbac_custom_action_db_item,str):
                                            rbac_custom_action_db_item = await generic_service.fetch_one_from_collection(
                                                collection_key=CollectionKey.RBAC_ACTION,
                                                output_data_type=OutputDataType.DEFAULT,
                                                accept_language= DEFAULT_LANGUAGE,
                                                query={
                                                    "filter___id":rbac_custom_action_db_item
                                                }
                                            )
                                        
                                        if rbac_custom_action_db_item and rbac_menu_db_item:
                                            # print(f"custom_action on : {custom_action}")
                                            # print(f"custom_action is deleted link : {is_link_deleted}")
                                            if is_link_deleted == True:
                                                get_target = await generic_service.fetch_one_from_collection(
                                                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                    query={
                                                        "filter__targeted_id":rbac_menu_db_item['id'],
                                                        "filter__rbac_action_id":rbac_custom_action_db_item['id'],
                                                        "filter__rbac_permission_id":permission_db_item['id'],
                                                    }, 
                                                )
                                                if get_target:
                                                    await generic_service.hard_delete_data_from_collection(
                                                        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                        item_id=get_target['id']
                                                    )
                                            else:
                                                saved_target = await generic_service.upsert_data_to_collection(
                                                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                    filter_data={
                                                        "targeted_id":rbac_menu_db_item['id'],
                                                        "rbac_action_id":rbac_custom_action_db_item['id'],
                                                        "rbac_permission_id":permission_db_item['id'],
                                                    },
                                                    update_data={
                                                        "targeted_id":rbac_menu_db_item['id'],
                                                        "rbac_action_id":rbac_custom_action_db_item['id'],
                                                        "rbac_permission_id":permission_db_item['id'],
                                                    }
                                                )
                                                print(f"\n\n\n saved permission target : {rbac_custom_action_db_item['label']} for permission : {permission_db_item['label']} \n\n\n")
                                                processed_target_id = saved_target if isinstance(saved_target,str) else str(saved_target['id'])
                                                # SAVE PROFILE RESTRICTION
                                                if 'restricted_profil_list' in core_seeds:
                                                    restricted_profil_list = core_seeds['restricted_profil_list']
                                                    for profil in restricted_profil_list:
                                                        # Handle new object structure - profil is now an object with flag and link fields
                                                        profil_flag = profil.get('flag') if isinstance(profil, dict) else profil

                                                        is_link_deleted = profil.get('is_link_deleted', False)
                                                        is_link_activated = profil.get('is_link_activated', True)
                                                        is_link_hidden = profil.get('is_link_hidden', False)
                                                        is_link_locked = profil.get('is_link_locked', False)
                                                        # fetch profil from db by flag
                                                        sys_profil_db_item = await generic_service.fetch_one_from_collection(
                                                            collection_key=CollectionKey.RBAC_PROFILE,
                                                            output_data_type=OutputDataType.DEFAULT,
                                                            accept_language= DEFAULT_LANGUAGE,
                                                            query={
                                                                "filter__flag": profil_flag
                                                            }
                                                        )
                                                        if sys_profil_db_item:
                                                            await self.create_restricted_profil(
                                                                targeted_id=processed_target_id,
                                                                rbac_profile_id=sys_profil_db_item['id'],
                                                                is_activated=is_link_activated,
                                                                is_hidden=is_link_hidden,
                                                                is_locked=is_link_locked,
                                                                is_deleted=is_link_deleted,
                                                            )

                                                # SAVE API CONSUMER RESTRICTION
                                                if 'restricted_api_consumer_list' in core_seeds:
                                                    restricted_api_consumer_list = core_seeds['restricted_api_consumer_list']
                                                    for api_consumer in restricted_api_consumer_list:
                                                        # Handle new object structure - api_consumer is now an object with flag and link fields
                                                        api_consumer_flag = api_consumer.get('flag') if isinstance(api_consumer, dict) else api_consumer
                                                        is_link_deleted = api_consumer.get('is_link_deleted', False)
                                                        is_link_activated = api_consumer.get('is_link_activated', True)
                                                        is_link_hidden = api_consumer.get('is_link_hidden', False)
                                                        is_link_locked = api_consumer.get('is_link_locked', False)
                                                        # fetch api consumer from db by flag
                                                        ref_api_consumer_db_item = await generic_service.fetch_one_from_collection(
                                                            collection_key=CollectionKey.REF_API_CONSUMER,
                                                            output_data_type=OutputDataType.DEFAULT,
                                                            accept_language= DEFAULT_LANGUAGE,
                                                            query={
                                                                "filter__flag": api_consumer_flag
                                                            }
                                                        )
                                                        if ref_api_consumer_db_item:
                                                            await self.create_restricted_api_consumer(
                                                                targeted_id=processed_target_id,
                                                                ref_api_consumer_id=ref_api_consumer_db_item['id'],
                                                                is_activated=is_link_activated,
                                                                is_hidden=is_link_hidden,
                                                                is_locked=is_link_locked,
                                                                is_deleted=is_link_deleted,
                                                            )
                        
                            # UPSERT PERMISSTION TARGET, CUSTOM COMPONENT AND MENU 
                            if 'rbac_custom_components_obj' in core_seeds:
                                rbac_custom_compenents_obj = core_seeds['rbac_custom_components_obj']
                                if 'component_to_menus' in rbac_custom_compenents_obj:
                                    custom_component_list_to_menus = rbac_custom_compenents_obj['component_to_menus']
                                    for custom_component in custom_component_list_to_menus:
                                        is_link_deleted = custom_component.get('is_link_deleted', False)
                                        
                                        # fetch menu from db by flag
                                        rbac_menu_db_item = await generic_service.fetch_one_from_collection(
                                            collection_key=CollectionKey.SYS_MENU,
                                            output_data_type=OutputDataType.DEFAULT,
                                            accept_language= DEFAULT_LANGUAGE,
                                            query={
                                                "filter__flag":custom_component['menu_flag']
                                            }
                                        )
                                        if not rbac_menu_db_item:
                                            continue
                                        # fetch standalone action from db by flag
                                        rbac_custom_component_db_item = await generic_service.upsert_data_to_collection(
                                            collection_key=CollectionKey.RBAC_COMPONENT,
                                            accept_language= DEFAULT_LANGUAGE,
                                            filter_data={
                                                "hard_code_flag":custom_component['component_hard_code_flag'],
                                                "flag":custom_component['component_flag'],
                                                "rbac_permission_id":permission_db_item['id'],
                                                "targeted_id":rbac_menu_db_item['id'],
                                            },
                                            update_data={
                                                "hard_code_flag":custom_component['component_hard_code_flag'],
                                                "flag":custom_component['component_flag'],
                                                "rbac_permission_id":permission_db_item['id'],
                                                "is_standalone":custom_component['component_is_standalone'],
                                                "label":custom_component['component_label'],
                                                "targeted_id":rbac_menu_db_item['id'],
                                            },
                                        )
                                        if isinstance(rbac_custom_component_db_item,str):
                                            rbac_custom_component_db_item = await generic_service.fetch_one_from_collection(
                                                collection_key=CollectionKey.RBAC_COMPONENT,
                                                output_data_type=OutputDataType.DEFAULT,
                                                accept_language= DEFAULT_LANGUAGE,
                                                query={
                                                    "filter___id":rbac_custom_component_db_item
                                                }
                                            )
                                        
                                        if rbac_custom_component_db_item and rbac_menu_db_item:
                                            # print(f"custom_action on : {custom_action}")
                                            # print(f"custom_action is deleted link : {is_link_deleted}")
                                            if is_link_deleted == True:
                                                get_target = await generic_service.fetch_one_from_collection(
                                                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                    query={
                                                        "filter__targeted_id":rbac_menu_db_item['id'],
                                                        "filter__rbac_component_id":rbac_custom_component_db_item['id'],
                                                        "filter__rbac_permission_id":permission_db_item['id'],
                                                    }, 
                                                )
                                                if get_target:
                                                    await generic_service.hard_delete_data_from_collection(
                                                        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                        item_id=get_target['id']
                                                    )
                                            else:
                                                saved_target = await generic_service.upsert_data_to_collection(
                                                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                    filter_data={
                                                        "targeted_id":rbac_menu_db_item['id'],
                                                        "rbac_component_id":rbac_custom_component_db_item['id'],
                                                        "rbac_permission_id":permission_db_item['id'],
                                                    },
                                                    update_data={
                                                        "targeted_id":rbac_menu_db_item['id'],
                                                        "rbac_component_id":rbac_custom_component_db_item['id'],
                                                        "rbac_permission_id":permission_db_item['id'],
                                                    }
                                                )
                                                print(f"\n\n\n saved permission target : {rbac_custom_component_db_item['label']} for permission : {permission_db_item['label']} \n\n\n")
                                                processed_target_id = saved_target if isinstance(saved_target,str) else str(saved_target['id'])
                                                # SAVE PROFILE RESTRICTION
                                                if 'restricted_profil_list' in core_seeds:
                                                    restricted_profil_list = core_seeds['restricted_profil_list']
                                                    for profil in restricted_profil_list:
                                                        # Handle new object structure - profil is now an object with flag and link fields
                                                        profil_flag = profil.get('flag') if isinstance(profil, dict) else profil

                                                        is_link_deleted = profil.get('is_link_deleted', False)
                                                        is_link_activated = profil.get('is_link_activated', True)
                                                        is_link_hidden = profil.get('is_link_hidden', False)
                                                        is_link_locked = profil.get('is_link_locked', False)
                                                        # fetch profil from db by flag
                                                        sys_profil_db_item = await generic_service.fetch_one_from_collection(
                                                            collection_key=CollectionKey.RBAC_PROFILE,
                                                            output_data_type=OutputDataType.DEFAULT,
                                                            accept_language= DEFAULT_LANGUAGE,
                                                            query={
                                                                "filter__flag": profil_flag
                                                            }
                                                        )
                                                        if sys_profil_db_item:
                                                            await self.create_restricted_profil(
                                                                targeted_id=processed_target_id,
                                                                rbac_profile_id=sys_profil_db_item['id'],
                                                                is_activated=is_link_activated,
                                                                is_hidden=is_link_hidden,
                                                                is_locked=is_link_locked,
                                                                is_deleted=is_link_deleted,
                                                            )

                                                # SAVE API CONSUMER RESTRICTION
                                                if 'restricted_api_consumer_list' in core_seeds:
                                                    restricted_api_consumer_list = core_seeds['restricted_api_consumer_list']
                                                    for api_consumer in restricted_api_consumer_list:
                                                        # Handle new object structure - api_consumer is now an object with flag and link fields
                                                        api_consumer_flag = api_consumer.get('flag') if isinstance(api_consumer, dict) else api_consumer
                                                        is_link_deleted = api_consumer.get('is_link_deleted', False)
                                                        is_link_activated = api_consumer.get('is_link_activated', True)
                                                        is_link_hidden = api_consumer.get('is_link_hidden', False)
                                                        is_link_locked = api_consumer.get('is_link_locked', False)
                                                        # fetch api consumer from db by flag
                                                        ref_api_consumer_db_item = await generic_service.fetch_one_from_collection(
                                                            collection_key=CollectionKey.REF_API_CONSUMER,
                                                            output_data_type=OutputDataType.DEFAULT,
                                                            accept_language= DEFAULT_LANGUAGE,
                                                            query={
                                                                "filter__flag": api_consumer_flag
                                                            }
                                                        )
                                                        if ref_api_consumer_db_item:
                                                            await self.create_restricted_api_consumer(
                                                                targeted_id=processed_target_id,
                                                                ref_api_consumer_id=ref_api_consumer_db_item['id'],
                                                                is_activated=is_link_activated,
                                                                is_hidden=is_link_hidden,
                                                                is_locked=is_link_locked,
                                                                is_deleted=is_link_deleted,
                                                            )
                        
                                if 'component_to_apps' in rbac_custom_compenents_obj:
                                    custom_component_list_to_apps = rbac_custom_compenents_obj['component_to_apps']
                                    for custom_component in custom_component_list_to_apps:
                                        is_link_deleted = custom_component.get('is_link_deleted', False)
                                        
                                        # fetch menu from db by flag
                                        rbac_menu_db_item = await generic_service.fetch_one_from_collection(
                                            collection_key=CollectionKey.SYS_APPLICATION,
                                            output_data_type=OutputDataType.DEFAULT,
                                            accept_language= DEFAULT_LANGUAGE,
                                            query={
                                                "filter__flag":custom_component['app_flag']
                                            }
                                        )
                                        if not rbac_menu_db_item:
                                            continue
                                        # fetch standalone action from db by flag
                                        rbac_custom_component_db_item = await generic_service.upsert_data_to_collection(
                                            collection_key=CollectionKey.RBAC_COMPONENT,
                                            accept_language= DEFAULT_LANGUAGE,
                                            filter_data={
                                                "hard_code_flag":custom_component['component_hard_code_flag'],
                                                "flag":custom_component['component_flag'],
                                                "rbac_permission_id":permission_db_item['id'],
                                                "targeted_id":rbac_menu_db_item['id'],
                                            },
                                            update_data={
                                                "hard_code_flag":custom_component['component_hard_code_flag'],
                                                "flag":custom_component['component_flag'],
                                                "rbac_permission_id":permission_db_item['id'],
                                                "is_standalone":custom_component['component_is_standalone'],
                                                "label":custom_component['component_label'],
                                                "targeted_id":rbac_menu_db_item['id'],
                                            },
                                        )
                                        if isinstance(rbac_custom_component_db_item,str):
                                            rbac_custom_component_db_item = await generic_service.fetch_one_from_collection(
                                                collection_key=CollectionKey.RBAC_COMPONENT,
                                                output_data_type=OutputDataType.DEFAULT,
                                                accept_language= DEFAULT_LANGUAGE,
                                                query={
                                                    "filter___id":rbac_custom_component_db_item
                                                }
                                            )
                                        
                                        if rbac_custom_component_db_item and rbac_menu_db_item:
                                            # print(f"custom_action on : {custom_action}")
                                            # print(f"custom_action is deleted link : {is_link_deleted}")
                                            if is_link_deleted == True:
                                                get_target = await generic_service.fetch_one_from_collection(
                                                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                    query={
                                                        "filter__targeted_id":rbac_menu_db_item['id'],
                                                        "filter__rbac_component_id":rbac_custom_component_db_item['id'],
                                                        "filter__rbac_permission_id":permission_db_item['id'],
                                                    }, 
                                                )
                                                if get_target:
                                                    await generic_service.hard_delete_data_from_collection(
                                                        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                        item_id=get_target['id']
                                                    )
                                            else:
                                                saved_target = await generic_service.upsert_data_to_collection(
                                                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                                                    filter_data={
                                                        "targeted_id":rbac_menu_db_item['id'],
                                                        "rbac_component_id":rbac_custom_component_db_item['id'],
                                                        "rbac_permission_id":permission_db_item['id'],
                                                    },
                                                    update_data={
                                                        "targeted_id":rbac_menu_db_item['id'],
                                                        "rbac_component_id":rbac_custom_component_db_item['id'],
                                                        "rbac_permission_id":permission_db_item['id'],
                                                    }
                                                )
                                                print(f"\n\n\n saved permission target : {rbac_custom_component_db_item['label']} for permission : {permission_db_item['label']} \n\n\n")
                                                processed_target_id = saved_target if isinstance(saved_target,str) else str(saved_target['id'])
                                                # SAVE PROFILE RESTRICTION
                                                if 'restricted_profil_list' in core_seeds:
                                                    restricted_profil_list = core_seeds['restricted_profil_list']
                                                    for profil in restricted_profil_list:
                                                        # Handle new object structure - profil is now an object with flag and link fields
                                                        profil_flag = profil.get('flag') if isinstance(profil, dict) else profil

                                                        is_link_deleted = profil.get('is_link_deleted', False)
                                                        is_link_activated = profil.get('is_link_activated', True)
                                                        is_link_hidden = profil.get('is_link_hidden', False)
                                                        is_link_locked = profil.get('is_link_locked', False)
                                                        # fetch profil from db by flag
                                                        sys_profil_db_item = await generic_service.fetch_one_from_collection(
                                                            collection_key=CollectionKey.RBAC_PROFILE,
                                                            output_data_type=OutputDataType.DEFAULT,
                                                            accept_language= DEFAULT_LANGUAGE,
                                                            query={
                                                                "filter__flag": profil_flag
                                                            }
                                                        )
                                                        if sys_profil_db_item:
                                                            await self.create_restricted_profil(
                                                                targeted_id=processed_target_id,
                                                                rbac_profile_id=sys_profil_db_item['id'],
                                                                is_activated=is_link_activated,
                                                                is_hidden=is_link_hidden,
                                                                is_locked=is_link_locked,
                                                                is_deleted=is_link_deleted,
                                                            )

                                                # SAVE API CONSUMER RESTRICTION
                                                if 'restricted_api_consumer_list' in core_seeds:
                                                    restricted_api_consumer_list = core_seeds['restricted_api_consumer_list']
                                                    for api_consumer in restricted_api_consumer_list:
                                                        # Handle new object structure - api_consumer is now an object with flag and link fields
                                                        api_consumer_flag = api_consumer.get('flag') if isinstance(api_consumer, dict) else api_consumer
                                                        is_link_deleted = api_consumer.get('is_link_deleted', False)
                                                        is_link_activated = api_consumer.get('is_link_activated', True)
                                                        is_link_hidden = api_consumer.get('is_link_hidden', False)
                                                        is_link_locked = api_consumer.get('is_link_locked', False)
                                                        # fetch api consumer from db by flag
                                                        ref_api_consumer_db_item = await generic_service.fetch_one_from_collection(
                                                            collection_key=CollectionKey.REF_API_CONSUMER,
                                                            output_data_type=OutputDataType.DEFAULT,
                                                            accept_language= DEFAULT_LANGUAGE,
                                                            query={
                                                                "filter__flag": api_consumer_flag
                                                            }
                                                        )
                                                        if ref_api_consumer_db_item:
                                                            await self.create_restricted_api_consumer(
                                                                targeted_id=processed_target_id,
                                                                ref_api_consumer_id=ref_api_consumer_db_item['id'],
                                                                is_activated=is_link_activated,
                                                                is_hidden=is_link_hidden,
                                                                is_locked=is_link_locked,
                                                                is_deleted=is_link_deleted,
                                                            )
                        

                            # UPSERT COLLECTION META DATA
                            if 'rbac_collection_meta_data_obj' in core_seeds:
                                print(f"\n\n\n rbac_collection_meta_data_obj : {True if 'rbac_collection_meta_data_obj' in core_seeds else False} \n\n\n")

                                await self.process_rbac_collection_meta_data(
                                    rbac_collection_meta_data_obj=core_seeds['rbac_collection_meta_data_obj'],
                                    core_seeds=core_seeds,
                                    generic_service=generic_service,
                                    permission_data=permission_db_item
                                )


            # if 'endpoints' in item and isinstance(item['endpoints'],list) and len(item['endpoints']) > 0:
            #     for endpoint_item in item['endpoints']:
            #         await process_rbac_endpoint(endpoint_item,rbac_title_db_item,generic_service)               

            if 'children' in item and isinstance(item['children'],list) and len(item['children']) > 0:
                for child_item in item['children']:
                    await self.recursive_rbac_title(child_item,None)               

        except ValueError as e:
            print(f"Error in create_core_seed > : {e}")
        except PermissionError as e:
            print(f"create_core_seed Error 2: {e}")


    async def recursive_save_rbac_structure(self, item, rbac_title_id: Optional[str] = None):
        """
        Step 1 of module seeding: Recursively create RBAC titles, permissions, and endpoints in the DB.
        This creates the structural data that `recursive_rbac_title` (step 2) depends on.
        
        Usage in any module's data_seed.py:
            rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)
            for item in MY_MODULE_SEED_RBAC_TITLE_DB:
                await rbac_role_service.recursive_save_rbac_structure(item)
                await rbac_role_service.recursive_rbac_title(item, None)
        """
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(DEFAULT_LANGUAGE)
        try:
            if "label" not in item or "flag" not in item:
                print(f"⚠️  Skipping item missing label or flag: {item}")
                return None

            # Prepare title data (exclude nested structures)
            item_data = {**item}
            item_data['rbac_title_id'] = rbac_title_id
            item_data.pop('children', None)
            item_data.pop('permissions', None)
            item_data.pop('endpoints', None)

            # Save title
            saved_title = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_TITLE,
                filter_data={"flag": item['flag']},
                update_data=item_data
            )

            if not saved_title:
                print(f"❌ Failed to save title: {item['label']}")
                return None

            saved_title_id = saved_title if isinstance(saved_title, str) else saved_title.get('id')
            if not saved_title_id:
                print(f"❌ Invalid saved title format: {saved_title}")
                return None

            print(f"✅ Saved RBAC title: {item['label']} (id: {saved_title_id})")

            # Process permissions
            if "permissions" in item and isinstance(item["permissions"], list):
                for permission_item in item["permissions"]:
                    try:
                        perm_data = {**permission_item}
                        perm_data.pop('core_seeds', None)
                        perm_data.pop('all_access_core_seeds', None)
                        perm_data["rbac_title_id"] = saved_title_id

                        saved_permission = await generic_service.upsert_data_to_collection(
                            collection_key=CollectionKey.RBAC_PERMISSION,
                            filter_data={'flag': perm_data['flag'], "rbac_title_id": saved_title_id},
                            update_data=perm_data
                        )

                        if saved_permission:
                            perm_id = saved_permission if isinstance(saved_permission, str) else saved_permission.get('id')
                            print(f"  ✅ Saved permission: {perm_data.get('label', perm_data['flag'])} (id: {perm_id})")

                            # If accessible to all profiles, add restricted profiles
                            if perm_data.get('is_accessible_to_all_profil') is True and perm_id:
                                restricted_profil_list = await generic_service.fetch_data_from_collection(
                                    collection_key=CollectionKey.RBAC_PROFILE,
                                    output_data_type=OutputDataType.DEFAULT,
                                    query={"filter__is_activated": True},
                                    all_data=True
                                )
                                for profil_item in (restricted_profil_list or []):
                                    await generic_service.upsert_data_to_collection(
                                        collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                                        filter_data={
                                            "targeted_id": str(perm_id),
                                            "rbac_profile_id": str(profil_item['id'])
                                        },
                                        update_data={
                                            "rbac_profile_id": str(profil_item['id']),
                                            "targeted_id": str(perm_id),
                                        }
                                    )
                    except Exception as e:
                        print(f"  ❌ Error processing permission: {e}")

            # Process endpoints
            if "endpoints" in item and isinstance(item["endpoints"], list):
                for endpoint_item in item["endpoints"]:
                    try:
                        if 'label' not in endpoint_item or 'url' not in endpoint_item:
                            print(f"  ⚠️  Skipping endpoint missing label or url: {endpoint_item}")
                            continue

                        # Handle is_link_deleted: cascade delete the endpoint and all references
                        if endpoint_item.get('is_link_deleted', False):
                            existing_endpoint = await generic_service.fetch_one_from_collection(
                                collection_key=CollectionKey.RBAC_ENDPOINT,
                                output_data_type=OutputDataType.DEFAULT,
                                accept_language=DEFAULT_LANGUAGE,
                                query={"filter__url": endpoint_item['url']}
                            )
                            if existing_endpoint:
                                await self.cascade_delete_endpoint_references(generic_service, existing_endpoint['id'])
                                print(f"  🗑️ Cascade deleted endpoint (is_link_deleted=True): {endpoint_item['label']}")
                            else:
                                print(f"  ⏭️  Endpoint already absent (is_link_deleted=True): {endpoint_item['url']}")
                            continue

                        endpoint_data = {
                            **endpoint_item,
                            "rbac_title_id": saved_title_id
                        }
                        await generic_service.upsert_data_to_collection(
                            collection_key=CollectionKey.RBAC_ENDPOINT,
                            filter_data={'url': endpoint_data['url'], "rbac_title_id": saved_title_id},
                            update_data=endpoint_data
                        )
                        print(f"  ✅ Saved endpoint: {endpoint_data['label']}")
                    except Exception as e:
                        print(f"  ❌ Error processing endpoint: {endpoint_item.get('label', 'Unknown')}: {e}")

            # Process children recursively
            if "children" in item and isinstance(item["children"], list):
                for child_item in item["children"]:
                    await self.recursive_save_rbac_structure(child_item, saved_title_id)

            return saved_title_id

        except Exception as e:
            print(f"❌ Error processing RBAC title {item.get('label', 'unknown')}: {e}")
            return None
    # TODO:: IMPLEMENT a method with sys_organization_id,rbac_permission_id as param, to return true/false if organizatin has access to that permission based on his profil
    async def seed_rbac_from_module(self, rbac_title_db: list):
        """
        Convenience method: runs both steps (structure + seeds) for a module's RBAC title DB.
        
        Usage in any module's data_seed.py:
            rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)
            await rbac_role_service.seed_rbac_from_module(MY_MODULE_SEED_RBAC_TITLE_DB)
        """
        module_name = rbac_title_db[0].get('label', 'Unknown') if rbac_title_db else 'Empty'
        print(f"\n📦 [{module_name}] Seeding RBAC ({len(rbac_title_db)} root titles)...")

        # Step 1: Create structure (titles, permissions, endpoints)
        for index, item in enumerate(rbac_title_db):
            print(f"\n📂 [{index+1}/{len(rbac_title_db)}] Creating structure: {item.get('label', 'N/A')}")
            await self.recursive_save_rbac_structure(item)

        # Step 2: Apply core_seeds restrictions
        print(f"\n🔧 [{module_name}] Applying RBAC seeds...")
        for index, item in enumerate(rbac_title_db):
            print(f"🔧 [{index+1}/{len(rbac_title_db)}] Applying seeds: {item.get('label', 'N/A')}")
            await self.recursive_rbac_title(item, None)

        print(f"\n✅ [{module_name}] RBAC seeding complete.\n")


    async def link_permissions_to_endpoints(
        self,
        *,
        permission_to_urls: list[tuple[str, str]],
    ) -> dict[str, int]:
        """Upsert `rbac_permission_target` rows for (permission_flag, url) pairs.

        Required because the legacy `process_collection_meta_data_target`
        path expects a CRUD-keyed dict shape that the senat-digit loaders
        don't produce (they emit a flat triple list). Without these target
        rows the middleware aggregation
        `permission → permission_target → endpoint` finds nothing and
        denies every request even when the role grant exists.

        Idempotent: each (permission_id, endpoint_id) pair is upserted by
        natural key.

        Args:
            permission_to_urls: list of (permission_flag, endpoint_url)
                pairs. Both must already exist in `rbac_permission` /
                `rbac_endpoint` (call `seed_rbac_from_module` first).

        Returns:
            {"linked": N, "missing_permission": M, "missing_endpoint": K}
        """
        stats = {"linked": 0, "missing_permission": 0, "missing_endpoint": 0}
        for perm_flag, url in permission_to_urls:
            perm = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=DEFAULT_LANGUAGE,
                query={"filter__flag": perm_flag},
            )
            if not perm:
                stats["missing_permission"] += 1
                continue
            ep = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ENDPOINT,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=DEFAULT_LANGUAGE,
                query={"filter__url": url},
            )
            if not ep:
                stats["missing_endpoint"] += 1
                continue
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                filter_data={
                    "targeted_id": ep.get("id"),
                    "rbac_permission_id": perm.get("id"),
                },
                update_data={
                    "targeted_id": ep.get("id"),
                    "rbac_permission_id": perm.get("id"),
                },
            )
            stats["linked"] += 1
        print(
            f"🔗 link_permissions_to_endpoints → linked={stats['linked']} "
            f"missing_perm={stats['missing_permission']} missing_ep={stats['missing_endpoint']}"
        )
        return stats


    async def grant_permissions_to_role(
        self,
        *,
        role_flag: str,
        permission_keys: list[str],
    ) -> dict[str, int]:
        """Grant a flat list of permissions to a role by flag.

        Used by the seed pipeline to wire role → permission grants
        explicitly. Without this, `permission_check_middleware` denies
        every request because `rbac_permission_role` is empty.

        Idempotent: each (role_id, permission_id) pair is upserted so
        re-runs are safe. Permissions whose flag isn't found in
        `rbac_permission` are reported as `missing` — usually the seed
        order is wrong (call `seed_rbac_from_module` first to register
        the permissions).

        Args:
            role_flag: the `flag` field on rbac_role (e.g.
                `system_profil_super_admin`).
            permission_keys: list of permission `flag` values to grant
                (e.g. `["admin_user.create_organization", ...]`).

        Returns:
            {"granted": N, "missing": M, "skipped": K}
        """
        stats = {"granted": 0, "missing": 0, "skipped": 0}

        if not role_flag or not permission_keys:
            return stats

        role = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_ROLE,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=DEFAULT_LANGUAGE,
            query={"filter__flag": role_flag},
        )
        if not role:
            print(f"⚠ grant_permissions_to_role: role flag={role_flag} not found")
            stats["skipped"] = len(permission_keys)
            return stats
        role_id = role.get("id")

        for key in permission_keys:
            permission = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=DEFAULT_LANGUAGE,
                query={"filter__flag": key},
            )
            if not permission:
                # Most likely cause: seed_rbac_from_module wasn't called
                # for the module owning this permission.
                print(f"⚠ permission flag={key!r} not in rbac_permission — skipping grant for role={role_flag}")
                stats["missing"] += 1
                continue
            permission_id = permission.get("id")
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                filter_data={
                    "rbac_role_id": role_id,
                    "rbac_permission_id": permission_id,
                },
                update_data={
                    "rbac_role_id": role_id,
                    "rbac_permission_id": permission_id,
                },
            )
            stats["granted"] += 1

        print(
            f"🔑 grant_permissions_to_role role={role_flag} → "
            f"granted={stats['granted']} missing={stats['missing']}"
        )
        return stats


    async def create_roles_from_parent_profile(self,parent_profil_id, new_profil_id: str, saved_organization_id: str) -> bool:
        """ 
        """
        try:
            # CREATE ALL ROLES
            all_profil_roles = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={
                    "filter__rbac_profile_id":parent_profil_id,
                    "filter__system_reserved_actions":True,
                    "filter__is_default":False,
                }
            )
            self.app_debug_print(f"\n\n\n\n\n\n all_profil_roles : {all_profil_roles}",True)
            for role in all_profil_roles:
                self.app_debug_print(f"\n\n\n\n\n\n loop role : {role}",True)
                # if role['is_default'] or role['flag'] == ESysProfilSuperUserRoleFlag.SYSTEM_PROFIL_SUPER_ADMIN.value or role['flag'] == ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN.value: continue
                saved_role = await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.RBAC_ROLE,
                    data={
                        "name":f"{role['name']}", 
                        "sys_organization_id":saved_organization_id,
                        "rbac_profile_id":new_profil_id,
                        "flag":f"{role['flag']}_org_{saved_organization_id}",
                        "is_default":False,
                        "system_reserved_actions":True,
                        "sys_core_role_id":role['id']
                    }
                )
                self.app_debug_print(f"\n\n\n\n\n\n saved_role : {saved_role}",True)
                self.create_single_rbac_role_permissions_from_parent(
                    parent_rbac_role_id=role['id'],
                    rbac_role_id=saved_role
                ) 
        except ValueError as e:
            return False

    async def organization_has_permission(self, sys_organization_id: str, rbac_permission_id: str) -> bool:
        """
        Check if an organization has access to a specific RBAC permission based on its profile.

        Flow:
        1. Fetch the organization to get its rbac_profile_id
        2. Check if a RBAC_RESTRICTED_PROFIL record exists linking that profile to the permission

        Args:
            sys_organization_id: The ID of the organization to check
            rbac_permission_id: The ID of the RBAC permission to verify access for

        Returns:
            True if the organization's profile has access to the permission, False otherwise
        """
        try:
            # Step 1: Fetch the organization to get its profile ID
            organization = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={
                    "filter___id": str(sys_organization_id),
                }
            )

            if not organization:
                self.debug_service.app_debug_print(
                    f"\n[organization_has_permission] Organization not found: {sys_organization_id}\n", True
                )
                return False

            rbac_profile_id = organization.get('rbac_profile_id')
            if not rbac_profile_id:
                self.debug_service.app_debug_print(
                    f"\n[organization_has_permission] Organization {sys_organization_id} has no rbac_profile_id\n", True
                )
                return False

            # Step 2: Check if a restricted profil record exists for this profile + permission
            restricted_profil_item = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={
                    "filter__targeted_id": str(rbac_permission_id),
                    "filter__rbac_profile_id": str(rbac_profile_id),
                }
            )

            has_access = restricted_profil_item is not None
            self.debug_service.app_debug_print(
                f"\n[organization_has_permission] org={sys_organization_id} permission={rbac_permission_id} profile={rbac_profile_id} -> {has_access}\n", False
            )
            return has_access

        except Exception as e:
            format_error = format_exception("Error in organization_has_permission", e)
            self.debug_service.app_debug_print(f"\n[organization_has_permission] {format_error}\n", True)
            return False

    async def get_sudo_permissions_and_endpoints(self, sys_organization_id: str = None, rbac_profile_id: str = None) -> dict:
        """
        Return all permissions and endpoints where any sudo/validation flag is true,
        scoped to the organization's profile access.

        Uses a MongoDB aggregation pipeline starting from RBAC_RESTRICTED_PROFIL:
        1. Validate rbac_profile_id and sys_organization_id exist
        2. Match restricted profil records for the given profile
        3. $lookup RBAC_PERMISSION (join on targeted_id → _id)
        4. Filter where any sudo flag is true on the permission
        5. $lookup RBAC_PERMISSION_TARGET (join on permission._id → rbac_permission_id)
        6. $lookup RBAC_ENDPOINT (join on permission_target.targeted_id → _id)
        7. Group by endpoint _id, collecting permissions array

        Args:
            sys_organization_id: Organization ID (required)
            rbac_profile_id: Profile ID (required)

        Returns:
            dict with 'permissions' and 'endpoints' lists, grouped by endpoint
        """
        try:
            rbac_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={
                    "filter___id": str(rbac_profile_id),
                }
            )
            if not rbac_profil:
                self.debug_service.app_debug_print(
                    f"\n[get_sudo_permissions_and_endpoints] No rbac_profile_id resolved. org={sys_organization_id}\n", True
                )
                return {"permissions": [], "endpoints": [],"results":[]}

            org_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={
                    "filter___id": str(sys_organization_id),
                }
            )
            if not org_info:
                self.debug_service.app_debug_print(
                    f"\n[get_sudo_permissions_and_endpoints] No org_info resolved. org={sys_organization_id}\n", True
                )
                return {"permissions": [], "endpoints": [],"results":[]}

            # Aggregation pipeline: RBAC_RESTRICTED_PROFIL → RBAC_PERMISSION → RBAC_PERMISSION_TARGET → RBAC_ENDPOINT
            sudo_pipeline = [
                # Step 1: Match restricted profil records for this profile
                {
                    "$match": {
                        "rbac_profile_id": ObjectId(str(rbac_profile_id)),
                    }
                },
                # Step 2: Lookup the actual permission document
                {
                    "$lookup": {
                        "from": f"{CollectionKey.RBAC_PERMISSION.model_name}",
                        "localField": "targeted_id",
                        "foreignField": "_id",
                        "as": "permission"
                    }
                },
                {
                    "$unwind": {
                        "path": "$permission",
                        "preserveNullAndEmptyArrays": False
                    }
                },
                # Step 3: Filter where any sudo flag on the permission is true
                {
                    "$match": {
                        "$or": [
                            {"permission.is_sudo_delegated_action": True},
                            {"permission.is_available_for_rls": True},
                            {"permission.is_sudo_cross_organization_validation_action": True},
                            {"permission.is_sudo_inter_connected_organization_validation_action": True},
                        ]
                    }
                },
                # Step 4: Lookup permission targets (links permission to endpoints)
                {
                    "$lookup": {
                        "from": f"{CollectionKey.RBAC_PERMISSION_TARGET.model_name}",
                        "localField": "permission._id",
                        "foreignField": "rbac_permission_id",
                        "as": "permission_target"
                    }
                },
                {
                    "$unwind": {
                        "path": "$permission_target",
                        "preserveNullAndEmptyArrays": False
                    }
                },
                # Step 5: Lookup the actual endpoint document
                {
                    "$lookup": {
                        "from": f"{CollectionKey.RBAC_ENDPOINT.model_name}",
                        "localField": "permission_target.targeted_id",
                        "foreignField": "_id",
                        "as": "endpoint"
                    }
                },
                {
                    "$unwind": {
                        "path": "$endpoint",
                        "preserveNullAndEmptyArrays": False
                    }
                },
                # Step 6: Group by endpoint _id, collect permissions
                {
                    "$group": {
                        "_id": "$endpoint._id",
                        "endpoint": {"$first": "$endpoint"},
                        "permissions": {"$addToSet": "$permission"},
                    }
                },
            ]

            results = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                all_data=True,
                pipeline=sudo_pipeline,
            )

            # Extract flat lists of unique permissions and endpoints
            all_permissions = []
            all_endpoints = []
            seen_permission_ids = set()

            for group in results:
                endpoint = group.get('endpoint')
                if endpoint:
                    all_endpoints.append(endpoint)

                for perm in group.get('permissions', []):
                    perm_id = str(perm.get('_id', ''))
                    if perm_id and perm_id not in seen_permission_ids:
                        seen_permission_ids.add(perm_id)
                        all_permissions.append(perm)

            self.debug_service.app_debug_print(
                f"\n[get_sudo_permissions_and_endpoints] Found {len(all_permissions)} sudo permissions, "
                f"{len(all_endpoints)} sudo endpoints for profile {rbac_profile_id}\n", False
            )

            return {
                "results": results,
                "permissions": all_permissions,
                "endpoints": all_endpoints,
            }

        except Exception as e:
            format_error = format_exception("Error in get_sudo_permissions_and_endpoints", e)
            self.debug_service.app_debug_print(f"\n[get_sudo_permissions_and_endpoints] {format_error}\n", True)
            return {
                "results": [],
                "permissions": [],
                "endpoints": [],
            }

    async def build_profil_not_joined_to_permission_rbac_hierarchy(self, data_list, output_data_type,rbac_profile_id,sys_user_id):
        """
        Builds complete RBAC hierarchy with recursive parent fetching. rbac_profile_id

        Args:
            data_list: List of RBAC data dictionaries
            output_data_type: The output format type

        Returns:
            List of dictionaries with complete hierarchy:
            [
                {
                    'rbac_title': dict,
                    'permissions': [dict],
                    'children': list
                }
            ]
        """
        try:
            # Convert single item to list if needed
            if not isinstance(data_list, list):
                data_list = [data_list]

            # First pass: organize all data by permission_to_role
            title_map = {}
            self.debug_service.app_debug_print(f"\n\n\n\n data_list ln: {len(data_list)} \n\n\n",False)
            for data in data_list:
                rbac_title = data.get('rbac_title')
                if not rbac_title:
                    continue

                # Get title ID based on output type — always use real_value
                # for DATA_TABLE so keys are ObjectId strings.
                self.debug_service.app_debug_print(f"\n\n\n\n output_data_type : {output_data_type}",False)
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    title_id_obj = rbac_title.get('id', {})
                    title_id = title_id_obj.get('real_value') or title_id_obj.get('display_value')
                else:  # DEFAULT or TREE
                    title_id = rbac_title['id']
                self.debug_service.app_debug_print(f"\n\n\n\n title_id : {title_id}",False)
                # Create permission data (all except rbac_title)
                permission = {k: v for k, v in data.items() if k != 'rbac_title'}
                self.debug_service.app_debug_print(f"\n\n\n permission \n\n\n PROFIL ID {rbac_profile_id} |   ID : {permission['id']['display_value']} |  LABEL : {permission['rbac_permission']['label']} \n\n\n",False)
                # restricted_profil_item = await self.generic_service.fetch_one_from_collection(
                #     collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                #     output_data_type=OutputDataType.DEFAULT,
                #     accept_language= self.accept_language,
                #     query={
                #         "filter__targeted_id":permission['rbac_permission']['id']['display_value'],
                #         "filter__rbac_profile_id":rbac_profile_id,
                #     }
                # )
                # self.debug_service.app_debug_print(f"\n\n\n restricted_profil_item \n\n\n {True if restricted_profil_item is not None else False}\n\n\n",False)
                user_privilege = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_PRIVILEGE,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language= self.accept_language,
                    query={
                        "filter__rbac_permission_id":permission['rbac_permission']['id']['display_value'],
                        "filter__sys_user_id":sys_user_id,
                        "filter__status":EAccessFlag.ADDED.value,
                    }
                )
                formated_permission = {
                    **permission['rbac_permission'],
                    "role_and_permission_are_joined": True if user_privilege is not None else False,
                }
                self.debug_service.app_debug_print(f"\n\n\n formated_permission is okay : {title_map} \n\n\n",False)
                self.debug_service.app_debug_print(f"\n\n\n title_id  : {title_id} \n\n\n",False)
                # Initialize title entry if not exists
                if title_id not in title_map:
                    self.debug_service.app_debug_print(f'\n\n title_map in loop : {title_id} \n\n',False)
                    title_map[title_id] = {
                        'rbac_title': rbac_title,
                        'permissions': [],
                        'children': []
                    }

                self.debug_service.app_debug_print(f"\n\n\n title_map : after : {title_map} \n\n\n",False)
                # Add permission to this title
                title_map[title_id]['permissions'].append(formated_permission)

            # Second pass: build complete hierarchy with recursive parent fetching
            processed_titles = set()

            for title_id in list(title_map.keys()):
                if title_id not in processed_titles:
                    await self._process_title_hierarchy(title_id, title_map, processed_titles, output_data_type)

            # Return only root nodes (rbac_title_id == None)
            return [
                title_data for title_data in title_map.values()
                if self._is_root_title(title_data['rbac_title'], output_data_type)
            ]
        except Exception as e:
            self.debug_service.app_debug_print(f"\n\n\n ERROR PROFIL HIERARCHY : {e} \n\n\n",True)
            return []
    
    async def build_profil_joined_to_permission_rbac_hierarchy(self, data_list, output_data_type,rbac_profile_id):
        """
        Builds complete RBAC hierarchy with recursive parent fetching. rbac_profile_id

        Args:
            data_list: List of RBAC data dictionaries
            output_data_type: The output format type

        Returns:
            List of dictionaries with complete hierarchy:
            [
                {
                    'rbac_title': dict,
                    'permissions': [dict],
                    'children': list
                }
            ]
        """
        try:
            # Convert single item to list if needed
            if not isinstance(data_list, list):
                data_list = [data_list]

            # First pass: organize all data by permission_to_role
            title_map = {}
            self.debug_service.app_debug_print(f"\n\n\n\n data_list ln: {len(data_list)} \n\n\n",False)
            for data in data_list:
                rbac_title = data.get('rbac_title')
                if not rbac_title:
                    continue

                # Get title ID based on output type — always use real_value
                # for DATA_TABLE so keys are ObjectId strings.
                self.debug_service.app_debug_print(f"\n\n\n\n output_data_type : {output_data_type}",False)
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    title_id_obj = rbac_title.get('id', {})
                    title_id = title_id_obj.get('real_value') or title_id_obj.get('display_value')
                else:  # DEFAULT or TREE
                    title_id = rbac_title['id']
                self.debug_service.app_debug_print(f"\n\n\n\n title_id : {title_id}",False)
                # Create permission data (all except rbac_title)
                permission = {k: v for k, v in data.items() if k != 'rbac_title'}
                self.debug_service.app_debug_print(f"\n\n\n permission \n\n\n PROFIL ID {rbac_profile_id} |   ID : {permission['id']['display_value']} |  LABEL : {permission['rbac_permission']['label']} \n\n\n",False)
                restricted_profil_item = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language= self.accept_language,
                    query={
                        "filter__targeted_id":permission['rbac_permission']['id']['display_value'],
                        "filter__rbac_profile_id":rbac_profile_id,
                    }
                )
                self.debug_service.app_debug_print(f"\n\n\n restricted_profil_item \n\n\n {True if restricted_profil_item is not None else False}\n\n\n",False)
                formated_permission = {
                    **permission['rbac_permission'],
                    "role_and_permission_are_joined": True if restricted_profil_item is not None else False,
                }
                self.debug_service.app_debug_print(f"\n\n\n formated_permission is okay : {title_map} \n\n\n",False)
                self.debug_service.app_debug_print(f"\n\n\n title_id  : {title_id} \n\n\n",False)
                # Initialize title entry if not exists
                if title_id not in title_map:
                    self.debug_service.app_debug_print(f'\n\n title_map in loop : {title_id} \n\n',False)
                    title_map[title_id] = {
                        'rbac_title': rbac_title,
                        'permissions': [],
                        'children': []
                    }

                self.debug_service.app_debug_print(f"\n\n\n title_map : after : {title_map} \n\n\n",False)
                # Add permission to this title
                title_map[title_id]['permissions'].append(formated_permission)

            # Second pass: build complete hierarchy with recursive parent fetching
            processed_titles = set()

            for title_id in list(title_map.keys()):
                if title_id not in processed_titles:
                    await self._process_title_hierarchy(title_id, title_map, processed_titles, output_data_type)

            # Return only root nodes (rbac_title_id == None)
            return [
                title_data for title_data in title_map.values()
                if self._is_root_title(title_data['rbac_title'], output_data_type)
            ]
        except Exception as e:
            self.debug_service.app_debug_print(f"\n\n\n ERROR PROFIL HIERARCHY : {e} \n\n\n",True)
            return []
    
    
    async def build_extended_profil_joined_to_permission_rbac_hierarchy(self, data_list, output_data_type,rbac_profile_id):
        """
        Builds complete RBAC hierarchy with recursive parent fetching. rbac_profile_id

        Args:
            data_list: List of RBAC data dictionaries
            output_data_type: The output format type

        Returns:
            List of dictionaries with complete hierarchy:
            [
                {
                    'rbac_title': dict,
                    'permissions': [dict],
                    'children': list
                }
            ]
        """
        try:
            # Convert single item to list if needed
            if not isinstance(data_list, list):
                data_list = [data_list]

            # First pass: organize all data by permission_to_role
            title_map = {}
            self.debug_service.app_debug_print(f"\n\n\n\n data_list ln: {len(data_list)} \n\n\n",False)
            for data in data_list:
                rbac_title = data.get('rbac_title')
                if not rbac_title:
                    continue

                # Get title ID based on output type — always use real_value
                # for DATA_TABLE so keys are ObjectId strings.
                self.debug_service.app_debug_print(f"\n\n\n\n output_data_type : {output_data_type}",False)
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    title_id_obj = rbac_title.get('id', {})
                    title_id = title_id_obj.get('real_value') or title_id_obj.get('display_value')
                else:  # DEFAULT or TREE
                    title_id = rbac_title['id']
                self.debug_service.app_debug_print(f"\n\n\n\n title_id : {title_id}",False)
                # Create permission data (all except rbac_title)
                permission = {k: v for k, v in data.items() if k != 'rbac_title'}
                self.debug_service.app_debug_print(f"\n\n\n permission \n\n\n PROFIL ID {rbac_profile_id} |   ID : {permission['id']['display_value']} |  LABEL : {permission['rbac_permission']['label']} \n\n\n",False)
                restricted_profil_item = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language= self.accept_language,
                    query={
                        "filter__targeted_id":permission['rbac_permission']['id']['display_value'],
                        "filter__rbac_profile_id":rbac_profile_id,
                    }
                )
                self.debug_service.app_debug_print(f"\n\n\n restricted_profil_item \n\n\n {True if restricted_profil_item is not None else False}\n\n\n",False)
                role_and_permission_are_joined = True if restricted_profil_item is not None else False
                formated_permission = {
                    **permission['rbac_permission'],
                    "role_and_permission_are_joined":role_and_permission_are_joined
                }
                self.debug_service.app_debug_print(f"\n\n\n formated_permission is okay : {title_map} \n\n\n",False)
                self.debug_service.app_debug_print(f"\n\n\n title_id  : {title_id} \n\n\n",False)
                # Initialize title entry if not exists
                if title_id not in title_map and role_and_permission_are_joined == False:
                    self.debug_service.app_debug_print(f'\n\n title_map in loop : {title_id} \n\n',False)
                    title_map[title_id] = {
                        'rbac_title': rbac_title,
                        'permissions': [],
                        'children': []
                    }

                self.debug_service.app_debug_print(f"\n\n\n title_map : after : {title_map} \n\n\n",False)
                # Add permission to this title
                if role_and_permission_are_joined == False:
                    title_map[title_id]['permissions'].append(formated_permission)

            # Second pass: build complete hierarchy with recursive parent fetching
            processed_titles = set()

            for title_id in list(title_map.keys()):
                if title_id not in processed_titles:
                    await self._process_title_hierarchy(title_id, title_map, processed_titles, output_data_type)

            # Return only root nodes (rbac_title_id == None)
            return [
                title_data for title_data in title_map.values()
                if self._is_root_title(title_data['rbac_title'], output_data_type)
            ]
        except Exception as e:
            self.debug_service.app_debug_print(f"\n\n\n ERROR PROFIL HIERARCHY : {e} \n\n\n",True)
            return []


    async def build_rbac_hierarchy(self, data_list, output_data_type):
        """
        Builds complete RBAC hierarchy with recursive parent fetching.

        Args:
            data_list: List of RBAC data dictionaries
            output_data_type: The output format type

        Returns:
            List of dictionaries with complete hierarchy:
            [
                {
                    'rbac_title': dict,
                    'permissions': [dict],
                    'children': list
                }
            ]
        """
        # Convert single item to list if needed
        if not isinstance(data_list, list):
            data_list = [data_list]

        # First pass: organize all data by rbac_title
        title_map = {}

        for data in data_list:
            rbac_title = data.get('rbac_title')
            if not rbac_title:
                continue

            # Get title ID based on output type — always use real_value
            # for DATA_TABLE so keys are ObjectId strings (display_value
            # can be a resolved name for unwound sub-documents).
            if output_data_type == OutputDataType.DATA_TABLE.value:
                title_id_obj = rbac_title.get('id', {})
                title_id = title_id_obj.get('real_value') or title_id_obj.get('display_value')
            else:  # DEFAULT or TREE
                title_id = rbac_title['id']

            # Create permission data (all except rbac_title)
            permission = {k: v for k, v in data.items() if k != 'rbac_title'}

            # Initialize title entry if not exists
            if title_id not in title_map:
                title_map[title_id] = {
                    'rbac_title': rbac_title,
                    'permissions': [],
                    'children': []
                }

            # Add permission to this title
            title_map[title_id]['permissions'].append(permission)

        # Second pass: build complete hierarchy with recursive parent fetching
        processed_titles = set()

        for title_id in list(title_map.keys()):
            if title_id not in processed_titles:
                await self._process_title_hierarchy(title_id, title_map, processed_titles, output_data_type)

        # Return only root nodes (rbac_title_id == None)
        return [
            title_data for title_data in title_map.values()
            if self._is_root_title(title_data['rbac_title'], output_data_type)
        ]
    async def build_role_joined_to_permission_rbac_hierarchy(self, data_list, output_data_type,rbac_role_id):
        """
        Builds complete RBAC hierarchy with recursive parent fetching.

        Args:
            data_list: List of RBAC data dictionaries
            output_data_type: The output format type

        Returns:
            List of dictionaries with complete hierarchy:
            [
                {
                    'rbac_title': dict,
                    'permissions': [dict],
                    'children': list
                }
            ]
        """
        # Convert single item to list if needed
        if not isinstance(data_list, list):
            data_list = [data_list]

        # First pass: organize all data by rbac_title
        title_map = {}

        for data in data_list:
            rbac_title = data.get('rbac_title')
            if not rbac_title:
                continue

            # Get title ID based on output type — always use real_value
            # for DATA_TABLE so keys are ObjectId strings (display_value
            # can be a resolved name for unwound sub-documents).
            if output_data_type == OutputDataType.DATA_TABLE.value:
                title_id_obj = rbac_title.get('id', {})
                title_id = title_id_obj.get('real_value') or title_id_obj.get('display_value')
            else:  # DEFAULT or TREE
                title_id = rbac_title['id']

            # Create permission data (all except rbac_title)
            permission = {k: v for k, v in data.items() if k != 'rbac_title'}
            # print(f"\n\n\n permission \n\n\n ROLE ID {rbac_role_id} |   ID : {permission['id']['display_value']} |  LABEL : {permission['rbac_permission']['label']} \n\n\n")
            permission_to_role = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= self.accept_language,
                query={
                    "filter__rbac_permission_id":permission['rbac_permission']['id']['display_value'],
                    "filter__rbac_role_id":rbac_role_id,
                }
            )
            # print(f"\n\n\n permission_to_role \n\n\n {True if permission_to_role is not None else False}\n\n\n")
            formated_permission = {
                **permission['rbac_permission'],
                "role_and_permission_are_joined": True if permission_to_role is not None else False,
            }

            # self.debug_service.app_debug_print(f"\n\n\n role title_map : {title_map} \n\n\n",True)
            # self.debug_service.app_debug_print(f"\n\n\n role title_id : {title_id} \n\n\n",True)
            # Initialize title entry if not exists
            if title_id not in title_map:
                # print(f'\n\n {permission}')
                title_map[title_id] = {
                    'rbac_title': rbac_title,
                    'permissions': [],
                    'children': []
                }

            # self.debug_service.app_debug_print(f"\n\n\n role title_map after : {title_map} \n\n\n",True)
            # Add permission to this title
            title_map[title_id]['permissions'].append(formated_permission)

        # Second pass: build complete hierarchy with recursive parent fetching
        processed_titles = set()

        for title_id in list(title_map.keys()):
            if title_id not in processed_titles:
                await self._process_title_hierarchy(title_id, title_map, processed_titles, output_data_type)

        # Return only root nodes (rbac_title_id == None)
        return [
            title_data for title_data in title_map.values()
            if self._is_root_title(title_data['rbac_title'], output_data_type)
        ]

    async def _process_title_hierarchy(self, title_id, title_map, processed_titles, output_data_type):
        """
        Recursively processes title hierarchy by fetching parent titles when needed.
        """
        if title_id in processed_titles:
            return

        processed_titles.add(title_id)

        title_data = title_map[title_id]
        rbac_title = title_data['rbac_title']

        # Get parent ID based on output type
        if output_data_type == OutputDataType.DATA_TABLE.value:
            parent_id_obj = rbac_title.get('rbac_title_id', {})
            # Always use real_value for reference fields — display_value may be
            # a resolved name (e.g. "Finance") instead of the ObjectId string.
            parent_id = parent_id_obj.get('real_value')
        else:  # DEFAULT or TREE
            parent_id = rbac_title.get('rbac_title_id')

        if parent_id:
            # Fetch parent if not already in our map
            if parent_id not in title_map:
                parent_rbac_title = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_TITLE.value,
                    output_data_type=output_data_type,
                    accept_language=self.accept_language,
                    query={"filter___id": parent_id}
                )

                if parent_rbac_title:
                    # Get parent key — always use real_value for DATA_TABLE
                    if output_data_type == OutputDataType.DATA_TABLE.value:
                        parent_title_id_obj = parent_rbac_title.get('id', {})
                        parent_title_id = parent_title_id_obj.get('real_value') or parent_title_id_obj.get('display_value')
                    else:
                        parent_title_id = parent_rbac_title['id']

                    # Guard: don't overwrite an existing entry (it may already
                    # have permissions from the first pass); just add child.
                    if parent_title_id in title_map:
                        if title_data not in title_map[parent_title_id]['children']:
                            title_map[parent_title_id]['children'].append(title_data)
                    else:
                        title_map[parent_title_id] = {
                            'rbac_title': parent_rbac_title,
                            'permissions': [],
                            'children': [title_data]  # Add current title as child
                        }

                    # Process the parent recursively
                    await self._process_title_hierarchy(parent_title_id, title_map, processed_titles, output_data_type)
                else:
                    # Parent not found - treat as root
                    title_data['rbac_title']['rbac_title_id'] = None
            else:
                # Parent exists in map - just add as child if not already present
                if title_data not in title_map[parent_id]['children']:
                    title_map[parent_id]['children'].append(title_data)

                # Process the parent recursively
                await self._process_title_hierarchy(parent_id, title_map, processed_titles, output_data_type)

    def _is_root_title(self, rbac_title, output_data_type):
        """Determine if a title is a root title (has no parent) based on output data type."""
        if output_data_type == OutputDataType.DATA_TABLE.value:
            parent_id_obj = rbac_title.get('rbac_title_id', {})
            # Always use real_value for reference fields
            parent_id = parent_id_obj.get('real_value')
            return not parent_id
        else:  # DEFAULT or TREE
            return not rbac_title.get('rbac_title_id')

    async def create_restricted_api_consumer(self,ref_api_consumer_id:str,targeted_id:str,is_activated:bool=True,is_hidden:bool=False,is_locked:bool=False,is_deleted:bool=False):
        """
        Create restricted api consumer.
        """ 
        new_data = {
            "ref_api_consumer_id":ref_api_consumer_id,
            "targeted_id":targeted_id,
            "is_activated": True,
            "is_hidden": False,
            "is_locked": False
        } 
        try:
            if is_activated == False:
                new_data['is_activated'] = False
            if is_hidden == True:
                new_data['is_hidden'] = True
            if is_locked == True:
                new_data['is_locked'] = True

            if is_deleted == True: 
                restricted_item = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                    output_data_type = OutputDataType.DEFAULT,
                    query={
                        "filter__targeted_id":new_data['targeted_id'],
                        "filter__ref_api_consumer_id":new_data['ref_api_consumer_id']
                    }
                )
                if restricted_item:
                    success = await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_RESTRICTED_API_CONSUMER, restricted_item['id'])
                    if success:
                        return success
            else :
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                    filter_data={"targeted_id":new_data['targeted_id'],'ref_api_consumer_id':new_data['ref_api_consumer_id']},
                    update_data=new_data
                )
        except ValueError as e:
            print(f"Error: {e}")
        except PermissionError as e:
            print(f"Permission Error: {e}")

    async def create_restricted_profil(self,rbac_profile_id:str,targeted_id:str,is_activated:bool=True,is_hidden:bool=False,is_locked:bool=False,is_deleted:bool=False):
        """
        Create restricted profil.
        """ 
        new_data = {
            "rbac_profile_id":rbac_profile_id,
            "targeted_id":targeted_id,
            "is_activated": True,
            "is_hidden": False,
            "is_locked": False
        } 
        print(f"\n\n TRACKED TARGETED PROFIL >>>>>  : {rbac_profile_id}")
        print(f"\n\n TRACKED TARGETED PROFIL DELETION >>>>>  : {is_deleted}")
        try:
            if is_activated == False:
                new_data['is_activated'] = False
            if is_hidden == True:
                new_data['is_hidden'] = True
            if is_locked == True:
                new_data['is_locked'] = True

            if is_deleted == True: 
                # FETCH RESTRICTED PROFIL
                restricted_item = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type = OutputDataType.DEFAULT,
                    query={
                        "filter__targeted_id":new_data['targeted_id'],
                        "filter__rbac_profile_id":new_data['rbac_profile_id']
                    }
                )
                if restricted_item:
                    # DELETE RESTRICTED PROFIL
                    success = await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_RESTRICTED_PROFIL, restricted_item['id'])
                    if success:
                        # FETCH AL PROFIL CHILDREN AND DELETE
                        children_profil = await self.generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.RBAC_PROFILE,
                            output_data_type = OutputDataType.DEFAULT,
                            all_data=True,
                            query={
                                "filter__rbac_profile_id":new_data['rbac_profile_id']
                            }
                        )
                        for child_profil in children_profil:
                            # FETCH CHILD RESTRICTED PROFIL
                            restricted_item = await self.generic_service.fetch_one_from_collection(
                                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                                output_data_type = OutputDataType.DEFAULT,
                                query={
                                    "filter__targeted_id":new_data['targeted_id'],
                                    "filter__rbac_profile_id":child_profil['id']
                                }
                            )
                            if restricted_item:
                                # DELETE CHILD RESTRICTED PROFIL
                                success = await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_RESTRICTED_PROFIL, restricted_item['id'])
                        return success
            else :
                # UPSERT RESTRICTED PROFIL
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    filter_data={"targeted_id":new_data['targeted_id'],'rbac_profile_id':new_data['rbac_profile_id']},
                    update_data=new_data
                )
                # UPSERT ALL PROFIL CHILDREN
                children_profil = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.RBAC_PROFILE,
                    output_data_type = OutputDataType.DEFAULT,
                    all_data=True,
                    query={
                        "filter__rbac_profile_id":new_data['rbac_profile_id']
                    }
                )
                for child_profil in children_profil:
                    # UPSERT CHILD RESTRICTED PROFIL
                    await self.generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                        filter_data={"targeted_id":new_data['targeted_id'],'rbac_profile_id':child_profil['id']},
                        update_data={
                            "targeted_id":new_data['targeted_id'],
                            "rbac_profile_id":child_profil['id'],
                            "is_activated": True,
                            "is_hidden": False,
                            "is_locked": False
                        }
                    )
            # if tracked_id == targeted_id:
            #     print(f"\n\n TRACKED TARGETED PROFIL : {result}")
        except ValueError as e:
            print(f"Error: {e}")
        except PermissionError as e:
            print(f"Permission Error: {e}")


    async def create_rbac_default_role_permissions(self,body_profil_id):

        try:
            # Get all default permissions
            all_default_permssions  = await self.generic_service.fetch_data_from_collection(
                collection_key= CollectionKey.RBAC_PERMISSION,
                output_data_type = OutputDataType.DEFAULT,
                all_data=True,
                query={
                    "filter__is_accessible_to_all_profil":True
                }
            )

            DebugService.app_debug_print(f"\n default permissions : {len(all_default_permssions)} \n",True)
            async def saving_menu_permission_target(menu_id, permission_id,body_profil_id):
                try:
                    # GET PROFIL FORM ID
                    body_profil = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.RBAC_PROFILE,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={
                            "filter___id": body_profil_id,
                        }
                    )
                    DebugService.app_debug_print(f"--- saving permission target {menu_id} : {permission_id}",True)
                    new_permission_target_doc = {
                        "targeted_id":menu_id, # linked_menu['id'],
                        "rbac_permission_id":permission_id, # perm['id'],
                        "restricted_profil_list":[
                            body_profil['flag'] if body_profil else ESysProfileFlag.TEST_SYS_PROFIL.value,
                        ],
                        "restricted_api_consumer_list":[
                            EApiConsumerFlag.SENAT_DIGIT_ADMIN_WEB.value,
                        ],

                    }

                    saved_target = await self.generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                        filter_data={
                            "targeted_id":new_permission_target_doc['targeted_id'],
                            'rbac_permission_id':new_permission_target_doc['rbac_permission_id']
                        },
                        update_data=new_permission_target_doc)
                    
                    processed_target_id = saved_target if isinstance(saved_target,str) else str(saved_target['id'])
                    target_restricted_platform = new_permission_target_doc.get('restricted_api_consumer_list', [])
                    target_restricted_profil = new_permission_target_doc.get('restricted_profil_list', [])
                    for profil_flag in target_restricted_profil:
                        profil_info = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.RBAC_PROFILE,
                            output_data_type = OutputDataType.DEFAULT,
                            query={
                                "filter__flag":profil_flag
                            }
                        )
                        if profil_info:
                            await self.create_restricted_profil(targeted_id=processed_target_id,rbac_profile_id=profil_info['id'])

                    for api_consumer_flag in target_restricted_platform:
                        api_consumer_info = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.REF_API_CONSUMER,
                            output_data_type = OutputDataType.DEFAULT,
                            query={
                                "filter__flag":api_consumer_flag
                            }
                        )
                        if api_consumer_info:
                            await self.create_restricted_api_consumer(targeted_id=processed_target_id,ref_api_consumer_id=api_consumer_info['id'])

                    # SAVE OR UPDATE ROLE
                    all_roles = await self.self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.RBAC_ROLE,
                        output_data_type = OutputDataType.DEFAULT,
                        all_data=True,
                        query={}
                    )
                    DebugService.app_debug_print(f"--- all roles :  {len(all_roles)}",True)
                    for role in all_roles:
                        new_perm_tar_role_doc = {
                            "rbac_role_id": role['id'],
                            "rbac_permission_id":permission_id
                        }
                        await self.generic_service.upsert_data_to_collection(
                            collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                            filter_data={
                                "rbac_role_id":new_perm_tar_role_doc['rbac_role_id'],
                                'rbac_permission_id':new_perm_tar_role_doc['rbac_permission_id']
                            },
                            update_data=new_perm_tar_role_doc)
                except ValueError as e:
                    DebugService.app_debug_print(f"Error >> saving_menu_permission_target: {e}",True)
                except PermissionError as e:
                    DebugService.app_debug_print(f"Permission Error: {e}",True)
                except Exception as e:
                    format_error = format_exception("Error in create_rbac_default_role_permissions", e)
                    DebugService.app_debug_print(f"Exception Error: {format_error}",True)


            async def saving_app_or_action_or_view_permission_target(app_action_view_id, permission_id,body_profil_id):
                try:
                    # GET PROFIL FORM ID
                    body_profil = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.RBAC_PROFILE,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={
                            "filter___id": body_profil_id,
                        }
                    )
                    new_permission_target_doc = {
                        "targeted_id":app_action_view_id,
                        "rbac_permission_id":permission_id,
                        "restricted_profil_list":[
                            body_profil['flag'] if body_profil else ESysProfileFlag.TEST_SYS_PROFIL.value,
                        ],
                        "restricted_api_consumer_list":[
                            EApiConsumerFlag.SENAT_DIGIT_ADMIN_WEB.value,
                        ],

                    }
                        
                    saved_target = await self.generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                        filter_data={
                            "targeted_id":new_permission_target_doc['targeted_id'],
                            'rbac_permission_id':new_permission_target_doc['rbac_permission_id']
                        },
                        update_data=new_permission_target_doc)
                    processed_target_id = saved_target if isinstance(saved_target,str) else str(saved_target['id'])
                    # print(f"\n\n TRACKED TARGETED 1: {processed_target_id}")
                    target_restricted_platform = new_permission_target_doc.get('restricted_api_consumer_list', [])
                    target_restricted_profil = new_permission_target_doc.get('restricted_profil_list', [])
                    # print(f"\n\n TRACKED TARGETED 2 target_restricted_platform LEN : {len(target_restricted_platform)}")
                    # print(f"\n\n TRACKED TARGETED 3 target_restricted_profil LEN : {len(target_restricted_profil)}")
                    for profil_flag in target_restricted_profil:
                        profil_info = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.RBAC_PROFILE,
                            output_data_type = OutputDataType.DEFAULT,
                            query={
                                "filter__flag":profil_flag
                            }
                        )
                        if profil_info:
                            await self.create_restricted_profil(targeted_id=processed_target_id,rbac_profile_id=profil_info['id'])

                    for api_consumer_flag in target_restricted_platform:
                        api_consumer_info = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.REF_API_CONSUMER,
                            output_data_type = OutputDataType.DEFAULT,
                            query={
                                "filter__flag":api_consumer_flag
                            }
                        )
                        if api_consumer_info:
                            await self.create_restricted_api_consumer(targeted_id=processed_target_id,ref_api_consumer_id=api_consumer_info['id'])

                    # PERMISSION
                    for profil_flag in target_restricted_profil:
                        profil_info = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.RBAC_PROFILE,
                            output_data_type = OutputDataType.DEFAULT,
                            query={
                                "filter__flag":profil_flag
                            }
                        )
                        if profil_info:
                            await self.create_restricted_profil(targeted_id=permission_id,rbac_profile_id=profil_info['id'])

                    # for api_consumer_flag in target_restricted_platform:
                    #     api_consumer_info = await self.generic_service.fetch_one_from_collection(
                    #         collection_key=CollectionKey.REF_API_CONSUMER,
                    #         output_data_type = OutputDataType.DEFAULT,
                    #         query={
                    #             "filter__flag":api_consumer_flag
                    #         }
                    #     )
                    #     if api_consumer_info:
                    #         await create_restricted_api_consumer(targeted_id=permission_id,ref_api_consumer_id=api_consumer_info['id'])

                    # SAVE OR UPDATE ROLE
                    all_roles = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.RBAC_ROLE,
                        output_data_type = OutputDataType.DEFAULT,
                        all_data=True,
                        query={}
                    )
                    DebugService.app_debug_print(f"--- all roles :  {len(all_roles)}",True)
                    for role in all_roles:
                        new_perm_tar_role_doc = {
                            "rbac_role_id": role['id'],
                            "rbac_permission_id":permission_id
                        }
                        await self.generic_service.upsert_data_to_collection(
                            collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                            filter_data={
                                "rbac_role_id":new_perm_tar_role_doc['rbac_role_id'],
                                'rbac_permission_id':new_perm_tar_role_doc['rbac_permission_id']
                            },
                            update_data=new_perm_tar_role_doc)

                except ValueError as e:
                    DebugService.app_debug_print(f"Error >> saving_app_or_action_or_view_permission_target: {e}",True)
                except PermissionError as e:
                    DebugService.app_debug_print(f"Permission Error: {e}",True)
                except Exception as e:
                    format_error = format_exception("Error in create_rbac_default_role_permissions", e)
                    DebugService.app_debug_print(f"Exception Error: {format_error}",True)

            async def recursive_checking_submenus(submenu, permission_id, visited=None,body_profil_id=None):
                if visited is None:
                    visited = set()

                # Prevent infinite loops
                if submenu['id'] in visited:
                    return
                visited.add(submenu['id'])
                DebugService.app_debug_print(f"--- menu name : {submenu['name']}",True)
                if 'sys_menu_id' in submenu:
                    menu_parent = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.SYS_MENU,
                        output_data_type = OutputDataType.DEFAULT,
                        query={
                            "filter___id":submenu['sys_menu_id']
                        }
                    )
                    if menu_parent:
                        await recursive_checking_submenus(menu_parent,permission_id,visited,body_profil_id)

                if 'sys_application_id' in submenu:
                    app_parent = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.SYS_APPLICATION,
                        output_data_type = OutputDataType.DEFAULT,
                        query={
                            "filter___id":submenu['sys_application_id']
                        }
                    )
                    if app_parent:
                        await saving_app_or_action_or_view_permission_target(app_parent['id'],permission_id,body_profil_id)

                await saving_menu_permission_target(submenu['id'],permission_id,body_profil_id)


            for perm in all_default_permssions:
                # FETCH LINKED MENUS
                menu_accessible_to_all_profil_flag = perm.get('menu_accessible_to_all_profil_flag',None)
                app_accessible_to_all_profil_flag = perm.get('app_accessible_to_all_profil_flag',None)
                action_accessible_to_all_profil_flag = perm.get('action_accessible_to_all_profil_flag',None)
                component_accessible_to_all_profil_flag = perm.get('component_accessible_to_all_profil_flag',None)
                print(f"--- menu_accessible_to_all_profil_flag : {menu_accessible_to_all_profil_flag}")
                print(f"--- app_accessible_to_all_profil_flag : {app_accessible_to_all_profil_flag}")
                print(f"--- action_accessible_to_all_profil_flag : {action_accessible_to_all_profil_flag}")
                print(f"--- component_accessible_to_all_profil_flag : {component_accessible_to_all_profil_flag}")
                if menu_accessible_to_all_profil_flag is not None:
                    linked_menus = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.SYS_MENU,
                        output_data_type = OutputDataType.DEFAULT,
                        all_data=True,
                        query={
                            "filter__menu_accessible_to_all_profil_flag":menu_accessible_to_all_profil_flag
                        }
                    )
                    print(f"--- linked_menus : {len(linked_menus)}")
                    for linked_menu in linked_menus:
                        await recursive_checking_submenus(linked_menu, perm['id'], None, body_profil_id)

                if app_accessible_to_all_profil_flag is not None:
                    linked_srcs = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.SYS_APPLICATION,
                        output_data_type = OutputDataType.DEFAULT,
                        all_data=True,
                        query={
                            "filter__app_accessible_to_all_profil_flag":app_accessible_to_all_profil_flag
                        }
                    )
                    for linked_src in linked_srcs:
                        await saving_app_or_action_or_view_permission_target(linked_src['id'], perm['id'],body_profil_id)

                if action_accessible_to_all_profil_flag is not None:
                    linked_srcs = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.RBAC_ACTION,
                        output_data_type = OutputDataType.DEFAULT,
                        all_data=True,
                        query={
                            "filter__action_accessible_to_all_profil_flag":action_accessible_to_all_profil_flag
                        }
                    )
                    for linked_src in linked_srcs:
                        await saving_app_or_action_or_view_permission_target(linked_src['id'], perm['id'],body_profil_id)

                if component_accessible_to_all_profil_flag is not None:
                    linked_srcs = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.RBAC_ACTION,
                        output_data_type = OutputDataType.DEFAULT,
                        all_data=True,
                        query={
                            "filter__component_accessible_to_all_profil_flag":component_accessible_to_all_profil_flag
                        }
                    )
                    for linked_src in linked_srcs:
                        await saving_app_or_action_or_view_permission_target(linked_src['id'], perm['id'],body_profil_id)

        except ValueError as e:
            format_error = format_exception("Error in create_single_rbac_default_role_permissions", e)
            DebugService.app_debug_print(f"Error: {format_error}",True)
        except PermissionError as e:
            format_error = format_exception("Error in create_single_rbac_default_role_permissions", e)
            DebugService.app_debug_print(f"Permission Error: {format_error}",True)
        except Exception as e:
            format_error = format_exception("Error in create_single_rbac_default_role_permissions", e)
            DebugService.app_debug_print(f"Exception Error: {format_error}",True)



    async def create_single_rbac_default_role_permissions(self,rbac_role_id,body_profil_id):
        try:
            DebugService.app_debug_print(f"\n processing profil > {body_profil_id} | saved_role_id : {rbac_role_id} \n",True)
            # Get all default permissions
            all_default_permssions  = await self.generic_service.fetch_data_from_collection(
                collection_key= CollectionKey.RBAC_PERMISSION,
                output_data_type = OutputDataType.DEFAULT,
                all_data=True,
                query={
                    "filter__is_accessible_to_all_profil":True
                }
            )
 

            DebugService.app_debug_print(f"\n default permissions : {len(all_default_permssions)} \n",True)
            async def saving_menu_permission_target(menu_id, permission_id,rbac_role_id,body_profil_id):
                try:
                    # GET PROFIL FORM ID
                    body_profil = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.RBAC_PROFILE,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={
                            "filter___id": body_profil_id,
                        }
                    )
                    DebugService.app_debug_print(f"--- saving permission target {menu_id} : {permission_id}",True)
                    new_permission_target_doc = {
                        "targeted_id":menu_id, # linked_menu['id'],
                        "rbac_permission_id":permission_id, # perm['id'],
                        "restricted_profil_list":[
                            body_profil['flag'] if body_profil else ESysProfileFlag.TEST_SYS_PROFIL.value,
                        ],
                        "restricted_api_consumer_list":[
                            EApiConsumerFlag.SENAT_DIGIT_ADMIN_WEB.value,
                        ],

                    }

                    saved_target = await self.generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                        filter_data={
                            "targeted_id":new_permission_target_doc['targeted_id'],
                            'rbac_permission_id':new_permission_target_doc['rbac_permission_id']
                        },
                        update_data=new_permission_target_doc)
                    
                    processed_target_id = saved_target if isinstance(saved_target,str) else str(saved_target['id'])
                    target_restricted_platform = new_permission_target_doc.get('restricted_api_consumer_list', [])
                    target_restricted_profil = new_permission_target_doc.get('restricted_profil_list', [])
                    for profil_flag in target_restricted_profil:
                        profil_info = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.RBAC_PROFILE,
                            output_data_type = OutputDataType.DEFAULT,
                            query={
                                "filter__flag":profil_flag
                            }
                        )
                        if profil_info:
                            await self.create_restricted_profil(targeted_id=processed_target_id,rbac_profile_id=profil_info['id'])

                    for api_consumer_flag in target_restricted_platform:
                        api_consumer_info = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.REF_API_CONSUMER,
                            output_data_type = OutputDataType.DEFAULT,
                            query={
                                "filter__flag":api_consumer_flag
                            }
                        )
                        if api_consumer_info:
                            await self.create_restricted_api_consumer(targeted_id=processed_target_id,ref_api_consumer_id=api_consumer_info['id'])

                    # SAVE OR UPDATE ROLE
                    new_perm_tar_role_doc = {
                        "rbac_role_id": rbac_role_id,
                        "rbac_permission_id":permission_id
                    }
                    await self.generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                        filter_data={
                            "rbac_role_id":new_perm_tar_role_doc['rbac_role_id'],
                            'rbac_permission_id':new_perm_tar_role_doc['rbac_permission_id']
                        },
                        update_data=new_perm_tar_role_doc)
                    # all_roles = await self.self.generic_service.fetch_data_from_collection(
                    #     collection_key=CollectionKey.RBAC_ROLE,
                    #     output_data_type = OutputDataType.DEFAULT,
                    #     all_data=True,
                    #     query={}
                    # )
                    # print(f"--- all roles :  {len(all_roles)}")
                    # for role in all_roles:
                    #     new_perm_tar_role_doc = {
                    #         "rbac_role_id": role['id'],
                    #         "rbac_permission_id":permission_id
                    #     }
                    #     await self.generic_service.upsert_data_to_collection(
                    #         collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                    #         filter_data={
                    #             "rbac_role_id":new_perm_tar_role_doc['rbac_role_id'],
                    #             'rbac_permission_id':new_perm_tar_role_doc['rbac_permission_id']
                    #         },
                    #         update_data=new_perm_tar_role_doc)
                except ValueError as e:
                    DebugService.app_debug_print(f"Error >> saving_menu_permission_target: {e}",True)
                except PermissionError as e:
                    DebugService.app_debug_print(f"Permission Error: {e}",True)
                except Exception as e:
                    format_error = format_exception("Error in create_single_rbac_default_role_permissions", e)
                    DebugService.app_debug_print(f"Exception Error: {format_error}",True)
 

            async def saving_app_or_action_or_view_permission_target(app_action_view_id, permission_id,rbac_role_id,body_profil_id):
                try:
                    # GET PROFIL FORM ID
                    body_profil = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.RBAC_PROFILE,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={
                            "filter___id": body_profil_id,
                        }
                    )
                    new_permission_target_doc = {
                        "targeted_id":app_action_view_id,
                        "rbac_permission_id":permission_id,
                        "restricted_profil_list":[
                            body_profil['flag'] if body_profil else ESysProfileFlag.TEST_SYS_PROFIL.value,
                        ],
                        "restricted_api_consumer_list":[
                            EApiConsumerFlag.SENAT_DIGIT_ADMIN_WEB.value,
                        ],

                    }
                        
                    saved_target = await self.generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                        filter_data={
                            "targeted_id":new_permission_target_doc['targeted_id'],
                            'rbac_permission_id':new_permission_target_doc['rbac_permission_id']
                        },
                        update_data=new_permission_target_doc)
                    processed_target_id = saved_target if isinstance(saved_target,str) else str(saved_target['id'])
                    # print(f"\n\n TRACKED TARGETED 1: {processed_target_id}")
                    target_restricted_platform = new_permission_target_doc.get('restricted_api_consumer_list', [])
                    target_restricted_profil = new_permission_target_doc.get('restricted_profil_list', [])
                    # print(f"\n\n TRACKED TARGETED 2 target_restricted_platform LEN : {len(target_restricted_platform)}")
                    # print(f"\n\n TRACKED TARGETED 3 target_restricted_profil LEN : {len(target_restricted_profil)}")
                    for profil_flag in target_restricted_profil:
                        profil_info = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.RBAC_PROFILE,
                            output_data_type = OutputDataType.DEFAULT,
                            query={
                                "filter__flag":profil_flag
                            }
                        )
                        if profil_info:
                            await self.create_restricted_profil(targeted_id=processed_target_id,rbac_profile_id=profil_info['id'])

                    for api_consumer_flag in target_restricted_platform:
                        api_consumer_info = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.REF_API_CONSUMER,
                            output_data_type = OutputDataType.DEFAULT,
                            query={
                                "filter__flag":api_consumer_flag
                            }
                        )
                        if api_consumer_info:
                            await self.create_restricted_api_consumer(targeted_id=processed_target_id,ref_api_consumer_id=api_consumer_info['id'])

                    # PERMISSION
                    for profil_flag in target_restricted_profil:
                        profil_info = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.RBAC_PROFILE,
                            output_data_type = OutputDataType.DEFAULT,
                            query={
                                "filter__flag":profil_flag
                            }
                        )
                        if profil_info:
                            await self.create_restricted_profil(targeted_id=permission_id,rbac_profile_id=profil_info['id'])

                    # for api_consumer_flag in target_restricted_platform:
                    #     api_consumer_info = await self.generic_service.fetch_one_from_collection(
                    #         collection_key=CollectionKey.REF_API_CONSUMER,
                    #         output_data_type = OutputDataType.DEFAULT,
                    #         query={
                    #             "filter__flag":api_consumer_flag
                    #         }
                    #     )
                    #     if api_consumer_info:
                    #         await create_restricted_api_consumer(targeted_id=permission_id,ref_api_consumer_id=api_consumer_info['id'])

                    # SAVE OR UPDATE ROLE
                    # SAVE OR UPDATE ROLE
                    new_perm_tar_role_doc = {
                        "rbac_role_id": rbac_role_id,
                        "rbac_permission_id":permission_id
                    }
                    await self.generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                        filter_data={
                            "rbac_role_id":new_perm_tar_role_doc['rbac_role_id'],
                            'rbac_permission_id':new_perm_tar_role_doc['rbac_permission_id']
                        },
                        update_data=new_perm_tar_role_doc)

                except ValueError as e:
                    DebugService.app_debug_print(f"Error >> saving_app_or_action_or_view_permission_target: {e}",True)
                except PermissionError as e:
                    DebugService.app_debug_print(f"Permission Error: {e}",True)
                except Exception as e:
                    format_error = format_exception("Error in create_single_rbac_default_role_permissions", e)
                    DebugService.app_debug_print(f"Exception Error: {format_error}",True)


            async def recursive_checking_submenus(submenu, permission_id, visited=None,body_profil_id=None):
                if visited is None:
                    visited = set()

                # Prevent infinite loops
                if submenu['id'] in visited:
                    return
                visited.add(submenu['id'])
                DebugService.app_debug_print(f"--- menu name >> : {submenu['name']}",True)
                if 'sys_menu_id' in submenu:
                    menu_parent = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.SYS_MENU,
                        output_data_type = OutputDataType.DEFAULT,
                        query={
                            "filter___id":submenu['sys_menu_id']
                        }
                    )
                    if menu_parent:
                        await recursive_checking_submenus(menu_parent,permission_id,visited,body_profil_id)

                if 'sys_application_id' in submenu:
                    app_parent = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.SYS_APPLICATION,
                        output_data_type = OutputDataType.DEFAULT,
                        query={
                            "filter___id":submenu['sys_application_id']
                        }
                    )
                    if app_parent:
                        await saving_app_or_action_or_view_permission_target(
                            app_action_view_id=app_parent['id'],
                            permission_id=permission_id,
                            rbac_role_id=rbac_role_id,
                            body_profil_id=body_profil_id
                        )

                await saving_menu_permission_target(
                    menu_id=submenu['id'],
                    permission_id=permission_id,
                    rbac_role_id=rbac_role_id,
                    body_profil_id=body_profil_id
                )


            for perm in all_default_permssions:
                # FETCH LINKED MENUS
                menu_accessible_to_all_profil_flag = perm.get('menu_accessible_to_all_profil_flag',None)
                app_accessible_to_all_profil_flag = perm.get('app_accessible_to_all_profil_flag',None)
                action_accessible_to_all_profil_flag = perm.get('action_accessible_to_all_profil_flag',None)
                component_accessible_to_all_profil_flag = perm.get('component_accessible_to_all_profil_flag',None)
                self.debug_service.app_debug_print(f"--- menu_accessible_to_all_profil_flag : {menu_accessible_to_all_profil_flag}",True)
                self.debug_service.app_debug_print(f"--- menu_accessible_to_all_profil_flag : {menu_accessible_to_all_profil_flag}",True)
                self.debug_service.app_debug_print(f"--- app_accessible_to_all_profil_flag : {app_accessible_to_all_profil_flag}",True)
                self.debug_service.app_debug_print(f"--- action_accessible_to_all_profil_flag : {action_accessible_to_all_profil_flag}",True)
                self.debug_service.app_debug_print(f"--- component_accessible_to_all_profil_flag : {component_accessible_to_all_profil_flag}",True)
                if menu_accessible_to_all_profil_flag is not None:
                    linked_menus = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.SYS_MENU,
                        output_data_type = OutputDataType.DEFAULT,
                        all_data=True,
                        query={
                            "filter__menu_accessible_to_all_profil_flag":menu_accessible_to_all_profil_flag
                        }
                    )
                    self.debug_service.app_debug_print(f"--- linked_menus : {len(linked_menus)}",True)
                    for linked_menu in linked_menus:
                        await recursive_checking_submenus(linked_menu, perm['id'], None, body_profil_id)

                if app_accessible_to_all_profil_flag is not None:
                    linked_srcs = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.SYS_APPLICATION,
                        output_data_type = OutputDataType.DEFAULT,
                        all_data=True,
                        query={
                            "filter__app_accessible_to_all_profil_flag":app_accessible_to_all_profil_flag
                        }
                    )
                    for linked_src in linked_srcs:
                        await saving_app_or_action_or_view_permission_target(
                            app_action_view_id=linked_src['id'], 
                            permission_id=perm['id'],
                            rbac_role_id=rbac_role_id,
                            body_profil_id=body_profil_id
                        )

                if action_accessible_to_all_profil_flag is not None:
                    linked_srcs = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.RBAC_ACTION,
                        output_data_type = OutputDataType.DEFAULT,
                        all_data=True,
                        query={
                            "filter__action_accessible_to_all_profil_flag":action_accessible_to_all_profil_flag
                        }
                    )
                    for linked_src in linked_srcs:
                        await saving_app_or_action_or_view_permission_target(
                            app_action_view_id=linked_src['id'], 
                            permission_id=perm['id'],
                            rbac_role_id=rbac_role_id,
                            body_profil_id=body_profil_id
                        )

                if component_accessible_to_all_profil_flag is not None:
                    linked_srcs = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.RBAC_ACTION,
                        output_data_type = OutputDataType.DEFAULT,
                        all_data=True,
                        query={
                            "filter__component_accessible_to_all_profil_flag":component_accessible_to_all_profil_flag
                        }
                    )
                    for linked_src in linked_srcs:
                        await saving_app_or_action_or_view_permission_target(
                            app_action_view_id=linked_src['id'], 
                            permission_id=perm['id'],
                            rbac_role_id=rbac_role_id,
                            body_profil_id=body_profil_id
                        )

        except ValueError as e:
            format_error = format_exception("Error in create_single_rbac_default_role_permissions", e)
            DebugService.app_debug_print(f"Error: {format_error}",True)
        except PermissionError as e:
            format_error = format_exception("Error in create_single_rbac_default_role_permissions", e)
            DebugService.app_debug_print(f"Permission Error: {format_error}",True)
        except Exception as e:
            format_error = format_exception("Error in create_single_rbac_role_permissions_from_parent", e)
            DebugService.app_debug_print(f"Exception Error: {format_error}",True)

    async def create_single_rbac_role_permissions_from_parent(self,parent_rbac_role_id,rbac_role_id):
        try:
            DebugService.app_debug_print(f"\n\n[create_single_rbac_role_permissions_from_parent]  saved_role_id : {rbac_role_id} | parent_saved_role_id : {parent_rbac_role_id} \n\n",True)

            parent_saved_perm_roles = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                all_data=True,
                query={
                    'filter__rbac_role_id':parent_rbac_role_id
                },)
            DebugService.app_debug_print(f"--- parent_saved_perm_roles : {parent_saved_perm_roles}",True)
            # loop
            for perm_role in parent_saved_perm_roles:
                saved = await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                    filter_data={
                        "rbac_role_id":str(rbac_role_id),
                        'rbac_permission_id':str(perm_role['rbac_permission_id'])
                    },
                    update_data={
                        "rbac_role_id":str(rbac_role_id),
                        "rbac_permission_id":str(perm_role['rbac_permission_id'])
                    }) 
                DebugService.app_debug_print(f"--- saved perission role: {saved}",True)
            return True
        except ValueError as e:
            format_error = format_exception("Error in create_single_rbac_role_permissions_from_parent", e)
            DebugService.app_debug_print(f"Error: {format_error}",True)
            return False
        except PermissionError as e:
            format_error = format_exception("Error in create_single_rbac_role_permissions_from_parent", e)
            DebugService.app_debug_print(f"Permission Error: {format_error}",True)
            return False
        except Exception as e:
            format_error = format_exception("Error in create_single_rbac_role_permissions_from_parent", e)
            DebugService.app_debug_print(f"Exception Error: {format_error}",True)
            return False

    async def remove_single_rbac_role_permissions_from_parent(self,parent_rbac_role_id,rbac_role_id):
        try:
            DebugService.app_debug_print(f"\n\n  saved_role_id : {rbac_role_id} | parent_saved_role_id : {parent_rbac_role_id} \n\n",True)

            parent_saved_perm_roles = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                all_data=True,
                query={
                    'filter__rbac_role_id':str(parent_rbac_role_id)
                },)
            DebugService.app_debug_print(f"--- parent_saved_perm_roles : {parent_saved_perm_roles}",True)
            # loop
            for perm_role in parent_saved_perm_roles:
                deleted = await self.generic_service.hard_delete_with_query_data_from_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                    query={
                        "rbac_role_id":str(rbac_role_id),
                        'rbac_permission_id':str(perm_role['rbac_permission_id'])
                    })
                DebugService.app_debug_print(f"--- deleted perission role: {deleted}",True)
        except ValueError as e:
            format_error = format_exception("Error in remove_single_rbac_role_permissions_from_parent", e)
            DebugService.app_debug_print(f"Error: {format_error}",True)
        except PermissionError as e:
            format_error = format_exception("Error in remove_single_rbac_role_permissions_from_parent", e)
            DebugService.app_debug_print(f"Permission Error: {format_error}",True)
        except Exception as e:
            format_error = format_exception("Error in remove_single_rbac_role_permissions_from_parent", e)
            DebugService.app_debug_print(f"Exception Error: {format_error}",True)

    async def create_cloned_sys_profil_from_parent(self,parent_rbac_profile_id,rbac_profile_id):
        try:
            DebugService.app_debug_print(f"\n\n  saved_role_id : {rbac_profile_id} | parent_saved_role_id : {parent_rbac_profile_id} \n\n",True)

            # First, try to get restricted profils directly from parent
            parent_saved_restricted_profil = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                all_data=True,
                query={
                    'filter__rbac_profile_id':str(parent_rbac_profile_id)
                },)
            DebugService.app_debug_print(f"--- parent_saved_restricted_profil count : {len(parent_saved_restricted_profil)}",True)

            # If parent has no restricted profil records, we need to clone from a profile that does
            # This happens when the parent is a system reserved profile that was never given direct RBAC_RESTRICTED_PROFIL entries
            if not parent_saved_restricted_profil or len(parent_saved_restricted_profil) == 0:
                DebugService.app_debug_print(f"--- No restricted profils found for parent, attempting to clone from system profile",True)

                # Get the parent profile to check its flag
                parent_profil = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_PROFILE,
                    output_data_type=OutputDataType.DEFAULT,
                    query={
                        'filter___id': str(parent_rbac_profile_id)
                    })

                if parent_profil:
                    DebugService.app_debug_print(f"--- Parent profile flag: {parent_profil.get('flag', 'N/A')}",True)

                    # Try to find a system profile that has RBAC_RESTRICTED_PROFIL records
                    # We'll use TEST_SYS_PROFIL or SYSTEM_PROFIL as fallback since they typically have full access
                    fallback_flags = [
                        ESysProfileFlag.TEST_SYS_PROFIL.value,
                        ESysProfileFlag.SYSTEM_PROFIL.value,
                    ]

                    for fallback_flag in fallback_flags:
                        fallback_profil = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.RBAC_PROFILE,
                            output_data_type=OutputDataType.DEFAULT,
                            query={
                                'filter__flag': fallback_flag
                            })

                        if fallback_profil:
                            parent_saved_restricted_profil = await self.generic_service.fetch_data_from_collection(
                                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                                all_data=True,
                                query={
                                    'filter__rbac_profile_id': fallback_profil['id']
                                },)

                            if parent_saved_restricted_profil and len(parent_saved_restricted_profil) > 0:
                                DebugService.app_debug_print(f"--- Found {len(parent_saved_restricted_profil)} restricted profils from fallback profile: {fallback_flag}",True)
                                break

            DebugService.app_debug_print(f"--- Final parent_saved_restricted_profil count: {len(parent_saved_restricted_profil) if parent_saved_restricted_profil else 0}",True)

            # Clone the restricted profil records to the new profile
            for restricted_profil in parent_saved_restricted_profil:
                saved = await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    filter_data={
                        "targeted_id":str(restricted_profil['targeted_id']),
                        'rbac_profile_id':str(rbac_profile_id)
                    },
                    update_data={
                        "targeted_id":str(restricted_profil['targeted_id']),
                        'rbac_profile_id':str(rbac_profile_id)
                    })
                DebugService.app_debug_print(f"--- saved restricted profil: {saved}",False)
        except ValueError as e:
            format_error = format_exception("Error in create_cloned_sys_profil_from_parent", e)
            DebugService.app_debug_print(f"Error: {format_error}",True)
        except PermissionError as e:
            format_error = format_exception("Error in create_cloned_sys_profil_from_parent", e)
            DebugService.app_debug_print(f"Permission Error: {format_error}",True)
        except Exception as e:
            format_error = format_exception("Error in create_cloned_sys_profil_from_parent", e)
            DebugService.app_debug_print(f"Exception Error: {format_error}",True)



    def merge_permission_hierarchies(self, hierarchy, organization_profil_hierarchy):
        """
        Merge two permission hierarchies following the specific flow:
        1. Collect all permission IDs from hierarchy where role_and_permission_are_joined == True
        2. Remove those permissions from organization_profil_hierarchy
        3. Remove parent titles if their permissions array becomes empty

        Args:
            hierarchy: List of hierarchy items (role permissions)
            organization_profil_hierarchy: List of organization profile hierarchy items

        Returns:
            List: Filtered organization_profil_hierarchy with joined permissions removed
        """
        try:
            # Step 1: Recursively collect all permission IDs from hierarchy where role_and_permission_are_joined == True
            permissions_to_remove_list = self._collect_joined_permission_ids_recursive(hierarchy)

            self.debug_service.app_debug_print(f"\n[MERGE] Found {len(permissions_to_remove_list)} joined permissions to remove: {permissions_to_remove_list}\n", False)

            # Step 2: Filter organization_profil_hierarchy to remove permissions in the removal list
            # Step 3: Remove parent titles if their permissions array becomes empty
            filtered_result = self._remove_permissions_and_empty_parents(organization_profil_hierarchy, permissions_to_remove_list)

            self.debug_service.app_debug_print(f"\n[MERGE] Original organization hierarchy: {len(organization_profil_hierarchy)} items, Filtered result: {len(filtered_result)} items\n", False)
            return filtered_result

        except Exception as e:
            self.debug_service.app_debug_print(f"\n[MERGE ERROR] {str(e)}\n", True)
            # Fallback: return original organization hierarchy
            return organization_profil_hierarchy

    async def delete_single_rbac_role_permissions(self,rbac_role_id):
        try:
            # DELETE ALL PERMISSION ROLES
            permission_roles = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={
                    "filter__rbac_role_id": str(rbac_role_id),
                }
            )
            for permission_role in permission_roles:
                await self.generic_service.hard_delete_data_from_collection(collection_key=CollectionKey.RBAC_PERMISSION_ROLE, item_id=permission_role['id'])

            # DELETE ALL RESTRICTED PROFIL
            restricted_profil = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={
                    "filter__targeted_id": str(rbac_role_id),
                }
            )
            for restricted_profil in restricted_profil:
                await self.generic_service.hard_delete_data_from_collection(collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL, item_id=restricted_profil['id'])
        except ValueError as e:
            DebugService.app_debug_print(f"Error delete_single_rbac_role_permissions : {e}",True)
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error delete_single_rbac_role_permissions : {e}",True)

    async def cascade_delete_endpoint_references(self, generic_service, endpoint_id: str):
        """Cascade delete all RBAC references for an endpoint.

        Deletes (in order):
        1. Permission targets for the endpoint + their restrictions
        2. Direct restrictions on the endpoint
        3. CRUD info entries for the endpoint + their restrictions
        4. The endpoint record itself
        """
        try:
            # 1. Delete permission targets where targeted_id = endpoint_id, and their restrictions
            permission_targets = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                output_data_type=OutputDataType.DEFAULT,
                all_data=True,
                query={"filter__targeted_id": str(endpoint_id)}
            )
            for target in (permission_targets or []):
                await self._delete_all_restrictions_for_targeted_id(generic_service, target['id'])
                await generic_service.hard_delete_data_from_collection(
                    collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
                    item_id=target['id']
                )

            # 2. Delete direct restrictions on the endpoint itself
            await self._delete_all_restrictions_for_targeted_id(generic_service, endpoint_id)

            # 3. Delete CRUD info entries for the endpoint + their restrictions
            crud_infos = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_COLLECTION_CRUD_INFO,
                output_data_type=OutputDataType.DEFAULT,
                all_data=True,
                query={"filter__rbac_endpoint_id": str(endpoint_id)}
            )
            for crud_info in (crud_infos or []):
                await self._delete_all_restrictions_for_targeted_id(generic_service, crud_info['id'])
                await generic_service.hard_delete_data_from_collection(
                    collection_key=CollectionKey.REF_COLLECTION_CRUD_INFO,
                    item_id=crud_info['id']
                )

            # 4. Delete the endpoint record itself
            await generic_service.hard_delete_data_from_collection(
                collection_key=CollectionKey.RBAC_ENDPOINT,
                item_id=endpoint_id
            )

            DebugService.app_debug_print(f"🗑️ Cascade deleted all references for endpoint: {endpoint_id}", True)
        except Exception as e:
            format_error = format_exception("Error in cascade_delete_endpoint_references", e)
            DebugService.app_debug_print(f"Error: {format_error}", True)

    async def _delete_all_restrictions_for_targeted_id(self, generic_service, targeted_id: str):
        """Delete all RBAC_RESTRICTED_PROFIL and RBAC_RESTRICTED_API_CONSUMER entries for a targeted_id."""
        restricted_profils = await generic_service.fetch_data_from_collection(
            collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
            output_data_type=OutputDataType.DEFAULT,
            all_data=True,
            query={"filter__targeted_id": str(targeted_id)}
        )
        for rp in (restricted_profils or []):
            await generic_service.hard_delete_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                item_id=rp['id']
            )

        restricted_api_consumers = await generic_service.fetch_data_from_collection(
            collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
            output_data_type=OutputDataType.DEFAULT,
            all_data=True,
            query={"filter__targeted_id": str(targeted_id)}
        )
        for rac in (restricted_api_consumers or []):
            await generic_service.hard_delete_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_API_CONSUMER,
                item_id=rac['id']
            )

    def _get_title_id_from_item(self, title_item):
        """Extract title ID from a title item"""
        try:
            rbac_title = title_item.get('rbac_title', {})
            if isinstance(rbac_title, dict):
                # Handle both data_table format and default format
                if 'id' in rbac_title:
                    if isinstance(rbac_title['id'], dict) and 'display_value' in rbac_title['id']:
                        return rbac_title['id']['display_value']
                    else:
                        return rbac_title['id']
            return None
        except Exception as e:
            self.debug_service.app_debug_print(f"\n\n\n ERROR _get_title_id_from_item : {e} \n\n\n",True)
            return None

    def _get_permission_id_from_permission(self, permission):
        """Extract permission ID from a permission object"""
        try:
            # Handle both formats: direct ID or nested structure
            if 'id' in permission:
                if isinstance(permission['id'], dict) and 'display_value' in permission['id']:
                    return permission['id']['display_value']
                else:
                    return permission['id']
            return None
        except Exception as e:
            self.debug_service.app_debug_print(f"\n\n\n ERROR _get_permission_id_from_permission : {e} \n\n\n",True)
            return None

    def _get_role_and_permission_joined_value(self, permission):
        """Extract role_and_permission_are_joined value from a permission object"""
        try:
            # Handle direct access
            if 'role_and_permission_are_joined' in permission:
                value = permission['role_and_permission_are_joined']
                # Handle nested structure with display_value
                if isinstance(value, dict) and 'display_value' in value:
                    return value['display_value']
                else:
                    return value
            return False  # Default to False if not found
        except Exception as e:
            self.debug_service.app_debug_print(f"\n\n\n ERROR _get_role_and_permission_joined_value : {e} \n\n\n",True)
            return False

    def _build_permission_map_recursive(self, children, permission_map):
        """Recursively build permission map for children"""
        for child in children:
            title_id = self._get_title_id_from_item(child)
            if title_id and title_id not in permission_map:
                permission_map[title_id] = {}

            # Map permissions for this child
            for permission in child.get('permissions', []):
                permission_id = self._get_permission_id_from_permission(permission)
                if permission_id and title_id:
                    permission_map[title_id][permission_id] = permission

            # Process grandchildren
            self._build_permission_map_recursive(child.get('children', []), permission_map)

    def _find_title_in_hierarchy(self, hierarchy, target_title_id):
        """Find a title item in hierarchy by title ID"""
        for title_item in hierarchy:
            title_id = self._get_title_id_from_item(title_item)
            if title_id == target_title_id:
                return title_item

            # Search in children recursively
            found_in_children = self._find_title_in_hierarchy(title_item.get('children', []), target_title_id)
            if found_in_children:
                return found_in_children

        return None

    def _filter_unjoined_permissions_only(self, hierarchy):
        """
        Filter hierarchy to exclude permissions where role_and_permission_are_joined == True
        If a title has all permissions with role_and_permission_are_joined == True, exclude the entire title
        """
        filtered_hierarchy = []

        for title_item in hierarchy:
            # Create a copy of the title item
            filtered_title = {
                'rbac_title': title_item.get('rbac_title'),
                'permissions': [],
                'children': []
            }

            # Filter permissions to exclude joined ones (keep only unjoined)
            has_unjoined_permissions = False
            total_permissions = len(title_item.get('permissions', []))

            for permission in title_item.get('permissions', []):
                # Handle both direct access and nested structure
                role_and_permission_joined = self._get_role_and_permission_joined_value(permission)

                if not role_and_permission_joined:  # Keep only unjoined permissions (False)
                    filtered_title['permissions'].append(permission)
                    has_unjoined_permissions = True

            # Recursively filter children
            filtered_title['children'] = self._filter_unjoined_permissions_only(title_item.get('children', []))

            # Add title only if:
            # 1. It has unjoined permissions, OR
            # 2. It has no direct permissions but has filtered children
            if has_unjoined_permissions:
                # Title has some unjoined permissions, include it
                filtered_hierarchy.append(filtered_title)
            elif total_permissions == 0 and filtered_title['children']:
                # Title has no direct permissions but has filtered children, include it
                filtered_hierarchy.append(filtered_title)
            elif filtered_title['children']:
                # Title has only joined permissions but has filtered children
                # Promote children to avoid empty parent nodes
                filtered_hierarchy.extend(filtered_title['children'])
            # If title has only joined permissions and no children, exclude it entirely

        return filtered_hierarchy

    def test_filter_logic(self, sample_data):
        """Test method to verify filter logic with sample data"""
        print(f"\n=== TESTING FILTER LOGIC ===")
        print(f"Input: {len(sample_data)} items")

        result = self._filter_unjoined_permissions_only(sample_data)

        print(f"Output: {len(result)} items")
        for item in result:
            title_id = self._get_title_id_from_item(item)
            permissions = item.get('permissions', [])
            print(f"Title {title_id}: {len(permissions)} permissions")

            for perm in permissions:
                perm_id = self._get_permission_id_from_permission(perm)
                joined = self._get_role_and_permission_joined_value(perm)
                print(f"  - {perm_id}: joined={joined}")

        return result

    def _collect_joined_permission_ids_recursive(self, hierarchy):
        """
        Recursively collect all permission IDs from hierarchy where role_and_permission_are_joined == True
        """
        permissions_to_remove = set()

        for title_item in hierarchy:
            # Check permissions in this title
            for permission in title_item.get('permissions', []):
                role_and_permission_joined = self._get_role_and_permission_joined_value(permission)
                if role_and_permission_joined:  # If True, add to removal list
                    permission_id = self._get_permission_id_from_permission(permission)
                    if permission_id:
                        permissions_to_remove.add(permission_id)

            # Recursively process children
            child_permissions = self._collect_joined_permission_ids_recursive(title_item.get('children', []))
            permissions_to_remove.update(child_permissions)

        return permissions_to_remove

    def _remove_permissions_and_empty_parents(self, hierarchy, permissions_to_remove_list):
        """
        Remove permissions that exist in permissions_to_remove_list from hierarchy.
        Remove parent titles if their permissions array becomes empty.
        """
        filtered_hierarchy = []

        for title_item in hierarchy:
            # Create a copy of the title item
            filtered_title = {
                'rbac_title': title_item.get('rbac_title'),
                'permissions': [],
                'children': []
            }

            # Filter permissions - exclude those in removal list
            for permission in title_item.get('permissions', []):
                permission_id = self._get_permission_id_from_permission(permission)
                if permission_id not in permissions_to_remove_list:
                    filtered_title['permissions'].append(permission)

            # Recursively process children
            filtered_title['children'] = self._remove_permissions_and_empty_parents(title_item.get('children', []), permissions_to_remove_list)

            # Only add title if it has permissions OR has children with permissions
            if filtered_title['permissions'] or filtered_title['children']:
                filtered_hierarchy.append(filtered_title)

        return filtered_hierarchy

    def _build_permission_id_set_recursive(self, children, permission_map):
        """Recursively build permission ID set for children"""
        for child in children:
            title_id = self._get_title_id_from_item(child)
            if title_id and title_id not in permission_map:
                permission_map[title_id] = set()

            # Map permission IDs for this child
            for permission in child.get('permissions', []):
                permission_id = self._get_permission_id_from_permission(permission)
                if permission_id and title_id:
                    permission_map[title_id].add(permission_id)

            # Process grandchildren
            self._build_permission_id_set_recursive(child.get('children', []), permission_map)

    def _merge_new_permissions_only(self, existing_title_item, org_title_item, existing_permission_ids):
        """
        Merge permissions from org_title_item into existing_title_item, only adding new permissions
        """
        try:
            for org_permission in org_title_item.get('permissions', []):
                org_permission_id = self._get_permission_id_from_permission(org_permission)

                if org_permission_id and org_permission_id not in existing_permission_ids:
                    # Permission doesn't exist, add it
                    existing_title_item['permissions'].append(org_permission)
                    self.debug_service.app_debug_print(f"\n[MERGE] Adding new permission {org_permission_id}\n", False)
                else:
                    self.debug_service.app_debug_print(f"\n[MERGE] Skipping duplicate permission {org_permission_id}\n", False)

            # Recursively merge children
            for org_child in org_title_item.get('children', []):
                org_child_id = self._get_title_id_from_item(org_child)
                existing_child = self._find_title_in_hierarchy(existing_title_item.get('children', []), org_child_id)

                if existing_child:
                    # Child exists, merge its permissions
                    child_permission_ids = set()
                    for perm in existing_child.get('permissions', []):
                        perm_id = self._get_permission_id_from_permission(perm)
                        if perm_id:
                            child_permission_ids.add(perm_id)

                    self._merge_new_permissions_only(existing_child, org_child, child_permission_ids)
                else:
                    # Child doesn't exist, add it
                    if 'children' not in existing_title_item:
                        existing_title_item['children'] = []
                    existing_title_item['children'].append(org_child)

        except Exception as e:
            self.debug_service.app_debug_print(f"\n[MERGE ERROR] Error merging permissions: {str(e)}\n", True)

    def _merge_permissions_for_title(self, existing_title_item, org_title_item, existing_permissions_map):
        """
        Merge permissions from org_title_item into existing_title_item based on criteria:
        - Only add permissions that don't exist in existing_title_item
        - OR if they exist but role_and_permission_are_joined == False
        """
        try:
            for org_permission in org_title_item.get('permissions', []):
                org_permission_id = self._get_permission_id_from_permission(org_permission)

                if org_permission_id:
                    existing_permission = existing_permissions_map.get(org_permission_id)

                    should_add_permission = False

                    if not existing_permission:
                        # Permission doesn't exist in hierarchy, add it
                        should_add_permission = True
                        self.debug_service.app_debug_print(f"\n[MERGE] Adding new permission {org_permission_id} (not in hierarchy)\n", False)
                    else:
                        # Permission exists, check if role_and_permission_are_joined is False
                        role_and_permission_joined = existing_permission.get('role_and_permission_are_joined', True)
                        if not role_and_permission_joined:
                            should_add_permission = True
                            self.debug_service.app_debug_print(f"\n[MERGE] Adding permission {org_permission_id} (role_and_permission_are_joined=False)\n", False)
                        else:
                            self.debug_service.app_debug_print(f"\n[MERGE] Skipping permission {org_permission_id} (already joined)\n", False)

                    if should_add_permission:
                        existing_title_item['permissions'].append(org_permission)

            # Recursively merge children
            for org_child in org_title_item.get('children', []):
                org_child_id = self._get_title_id_from_item(org_child)
                existing_child = self._find_title_in_hierarchy(existing_title_item.get('children', []), org_child_id)

                if existing_child:
                    # Child exists, merge its permissions
                    child_permissions_map = {}
                    for perm in existing_child.get('permissions', []):
                        perm_id = self._get_permission_id_from_permission(perm)
                        if perm_id:
                            child_permissions_map[perm_id] = perm

                    self._merge_permissions_for_title(existing_child, org_child, child_permissions_map)
                else:
                    # Child doesn't exist, add it
                    if 'children' not in existing_title_item:
                        existing_title_item['children'] = []
                    existing_title_item['children'].append(org_child)

        except Exception as e:
            self.debug_service.app_debug_print(f"\n[MERGE ERROR] Error merging permissions: {str(e)}\n", True)

    async def delete_single_sys_profil(self,saved_profil_id):
        try:
            if saved_profil_id:
                # DELETE ALL RESTRICTED PROFIL
                parent_restricted_profil = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                    output_data_type = OutputDataType.DEFAULT,
                    all_data=True,
                    query={
                        "filter__rbac_profile_id":saved_profil_id
                    }
                )
                for restricted_profil in parent_restricted_profil:
                    await self.generic_service.hard_delete_data_from_collection(
                        collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL,
                        item_id=restricted_profil['id']
                    ) 
                # DELETE ALL ROLE FROM PROFIL
                parent_roles = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.RBAC_ROLE,
                    output_data_type = OutputDataType.DEFAULT,
                    all_data=True,
                    query={
                        "filter__rbac_profile_id":saved_profil_id
                    }
                )
                for role in parent_roles:

                    # DELETE ALL USER ACCOUNT 
                    user_accounts = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.SYS_USER,
                        output_data_type = OutputDataType.DEFAULT,
                        all_data=True,
                        query={
                            "filter__rbac_role_id":role['id']
                        }
                    )
                    for user_account in user_accounts:
                        await self.generic_service.hard_delete_data_from_collection(
                            collection_key=CollectionKey.SYS_USER,
                            item_id=user_account['id']
                        )

                    await self.generic_service.hard_delete_data_from_collection(
                        collection_key=CollectionKey.RBAC_ROLE,
                        item_id=role['id']
                    )
                # DELETE ALL ORGANIZATION FROM PROFIL
                parent_organizations = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.SYS_ORGANIZATION,
                    output_data_type = OutputDataType.DEFAULT,
                    all_data=True,
                    query={
                        "filter__rbac_profile_id":saved_profil_id
                    }
                )
                for organization in parent_organizations:
                    await self.generic_service.hard_delete_data_from_collection(
                        collection_key=CollectionKey.SYS_ORGANIZATION,
                        item_id=organization['id']
                    )
                # DELETE PROFIL
                await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_PROFILE, saved_profil_id)
        except ValueError as e:
            print(f"Error delete_single_sys_profil : {e}")
        except PermissionError as e:
            print(f"Permission Error delete_single_sys_profil : {e}")
        except Exception as e:
            format_error = format_exception("Error in delete_single_sys_profil", e)
            print(f"Exception Error delete_single_sys_profil : {format_error}")