
#app/modules/core/seeds/core.seed.py

import asyncio
from typing import Optional
from app.db.session import init_db
from app.modules.core.enums.type_enum import AccountStatusFlag, ECollectionCrudInfoFlag, OutputDataType
import nest_asyncio

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.seeds.core_rbac_title import CORE_RBAC_TITLE_DB
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag
from app.modules.core.seeds.rbac_title.profil_permission_title import PROFIL_ENDPOINTS, PROFIL_PERMISSION_RBAC_TITLE_DB

# Prevents loop errors by allowing re-entry into the same event loop
nest_asyncio.apply()

# CRUD flag mapping for collection meta data
COLLECTION_CRUD_FLAG_MAPPING = {
    # Standard CRUD operations
    'fetch_url': ECollectionCrudInfoFlag.FETCH_URL,
    'fetch_one_info_url': ECollectionCrudInfoFlag.FETCH_ONE_INFO_URL,
    'fetch_one_info_for_viewing_url': ECollectionCrudInfoFlag.FETCH_ONE_INFO_FOR_VIEWING_URL,
    'update_processing_url': ECollectionCrudInfoFlag.UPDATE_PROCESSING_URL,
    'update_head_process_url': ECollectionCrudInfoFlag.UPDATE_HEAD_PROCESS_URL,
    'delete_processing_url': ECollectionCrudInfoFlag.DELETE_PROCESSING_URL,
    'create_processing_url': ECollectionCrudInfoFlag.CREATE_PROCESSING_URL,
    'create_head_process_url': ECollectionCrudInfoFlag.CREATE_HEAD_PROCESS_URL,
    'create_child_processing_url': ECollectionCrudInfoFlag.CREATE_CHILD_PROCESSING_URL,
    'create_child_head_process_url': ECollectionCrudInfoFlag.CREATE_CHILD_HEAD_PROCESS_URL,
    'put_processing_url': ECollectionCrudInfoFlag.PUT_PROCESSING_URL,
    'patch_processing_url': ECollectionCrudInfoFlag.PATCH_PROCESSING_URL,
    'parent_field_name': ECollectionCrudInfoFlag.PARENT_FIELD_NAME,
    'download_process_url': ECollectionCrudInfoFlag.DOWNLOAD_PROCESS_URL,

    # Custom/specific operations (add more as needed)
    'delete_legal_beneficiary_url': ECollectionCrudInfoFlag.DELETE_PROCESSING_URL,
    'create_legal_beneficiary_url': ECollectionCrudInfoFlag.CREATE_PROCESSING_URL,
    'update_legal_beneficiary_url': ECollectionCrudInfoFlag.UPDATE_PROCESSING_URL,
    'fetch_legal_beneficiary_url': ECollectionCrudInfoFlag.FETCH_URL,
    'delete_physical_beneficiary_url': ECollectionCrudInfoFlag.DELETE_PROCESSING_URL,
    'create_physical_beneficiary_url': ECollectionCrudInfoFlag.CREATE_PROCESSING_URL,
    'delete_agent_beneficiary_url': ECollectionCrudInfoFlag.DELETE_PROCESSING_URL,
    'create_agent_beneficiary_url': ECollectionCrudInfoFlag.CREATE_PROCESSING_URL,
}


tracked_id = None
PROFILE_TITLE_FLAG = "user_profil_info"

# Helpers
async def ensure_profile_rbac_title_exists(generic_service: GenericService):
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
# Seed Data
async def init_data():
    """
    Initialize the database and seed default data.
    """
    await init_db()
    await create_core_infos()


 
async def fetch_rbac_endpoint_data(generic_service, rbac_endpoint_url):
    """Fetch RBAC endpoint data from database."""
    if not rbac_endpoint_url:
        return None

    return await generic_service.fetch_one_from_collection(
        collection_key=CollectionKey.RBAC_ENDPOINT,
        output_data_type=OutputDataType.DEFAULT,
        accept_language=DEFAULT_LANGUAGE,
        query={"filter__url": rbac_endpoint_url}
    )
async def handle_all_access_core_seeds(all_access_core_seeds,permission_db_item,generic_service):
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
                rbac_endpoint_data = await fetch_rbac_endpoint_data(
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
                        rbac_title = await ensure_profile_rbac_title_exists(generic_service)
                        if not rbac_title:
                            print(f"❌ Unable to seed RBAC title '{PROFILE_TITLE_FLAG}'")
                            return
                    # filter endpoint in PROFIL_ENDPOINTS based on endpoint_url
                    
                    # Filter endpoints that match the endpoint_url with safety checks
                    filtered_endpoints = []
                    for endpoint in PROFIL_ENDPOINTS:
                        if (isinstance(endpoint, dict) and 
                            not endpoint.get("is_link_deleted") and
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
    
    except Exception as e:
        print(f"❌ Error processing endpoint restrictions: {str(e)}")

 
async def create_core_infos():
    try:
        from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
        rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)
        """
        Create default API consumers if they do not already exist.
        """
        generic_service = GenericService(DEFAULT_LANGUAGE)
        # rbac_titles = CORE_RBAC_TITLE_DB
        permissions_all = PROFIL_PERMISSION_RBAC_TITLE_DB;
        print(f" permissions_all ln : {len(permissions_all)}")
        await ensure_profile_rbac_title_exists(generic_service)
        # Check for and extract "label" and "flag"
        for perm in permissions_all:
            print(f" permission ln : {perm['label']}")
            permission_item = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PERMISSION,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= DEFAULT_LANGUAGE,
                query={
                    "filter__flag":perm['flag']
                }
            )
            all_access_core_seeds = perm.get('all_access_core_seeds', {})
            if permission_item:
                await handle_all_access_core_seeds(all_access_core_seeds,permission_item,generic_service)
 
    except ValueError as e:
        print(f"Error in create_core_infos : {e}")
    except PermissionError as e:
        print(f"Permission Error: {e}")
    

# if __name__ == "__main__":
if __name__ == "__main__":
    loop = asyncio.get_event_loop()  # Get the current event loop
    loop.run_until_complete(init_data())  # Run without creating a nested loop
