
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
from app.modules.security.enums.security_enum import EConfigSudoActionTypeFlag

# Prevents loop errors by allowing re-entry into the same event loop
# uvloop already supports nested async calls natively, so patching is not needed/possible
try:
    nest_asyncio.apply()
except ValueError:
    pass

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


# Seed Data
async def init_data():
    """
    Initialize the database and seed default data.
    """
    await init_db()
    await create_core_infos()



async def process_rbac_collection_meta_data(
    rbac_collection_meta_data_obj,
    core_seeds,
    generic_service,
    create_restricted_profil,
    create_restricted_api_consumer,
    permission_data=None
):
    """
    Flexible function to process all rbac_collection_meta_data_obj possibilities.

    Args:
        rbac_collection_meta_data_obj (dict): The collection meta data object
        core_seeds (dict): The core seeds data containing restrictions
        generic_service: The generic service instance
        create_restricted_profil: Function to create profile restrictions
        create_restricted_api_consumer: Function to create API consumer restrictions
    """
    print(f"\n🔄 Processing RBAC Collection Meta Data...")

    # Process collection_meta_data_to_menus
    if 'collection_meta_data_to_menus' in rbac_collection_meta_data_obj:
        print(f"📋 Processing collection_meta_data_to_menus...")
        await process_collection_meta_data_target(
            target_type='menus',
            collection_meta_data=rbac_collection_meta_data_obj['collection_meta_data_to_menus'],
            core_seeds=core_seeds,
            generic_service=generic_service,
            create_restricted_profil=create_restricted_profil,
            create_restricted_api_consumer=create_restricted_api_consumer,
            permission_data=permission_data
        )

    # Process collection_meta_data_to_apps
    if 'collection_meta_data_to_apps' in rbac_collection_meta_data_obj:
        print(f"📱 Processing collection_meta_data_to_apps...")
        await process_collection_meta_data_target(
            target_type='apps',
            collection_meta_data=rbac_collection_meta_data_obj['collection_meta_data_to_apps'],
            core_seeds=core_seeds,
            generic_service=generic_service,
            create_restricted_profil=create_restricted_profil,
            create_restricted_api_consumer=create_restricted_api_consumer,
            permission_data=permission_data
        )

async def process_collection_meta_data_target(
    target_type,
    collection_meta_data,
    core_seeds,
    generic_service,
    create_restricted_profil,
    create_restricted_api_consumer,
    permission_data=None
):
    """
    Process collection meta data for a specific target type (menus or apps).

    Args:
        target_type (str): Either 'menus' or 'apps'
        collection_meta_data (dict): The collection meta data for the target type
        core_seeds (dict): The core seeds data
        generic_service: The generic service instance
        create_restricted_profil: Function to create profile restrictions
        create_restricted_api_consumer: Function to create API consumer restrictions
    """
    print(f"🎯 Processing {target_type} collection meta data...")

    # Iterate through all CRUD operations
    for crud_operation, meta_data_list in collection_meta_data.items():
        if not meta_data_list:  # Skip empty lists
            continue

        # print(f">>  Processing {meta_data_list} for {target_type}...")
        print(f"⚙️  Processing {crud_operation} for {target_type}...")

        # Get the corresponding CRUD flag
        crud_flag = COLLECTION_CRUD_FLAG_MAPPING.get(crud_operation)
        if not crud_flag:
            print(f"⚠️  Unknown CRUD operation: '{crud_operation}'")
            print(f"📋 Available CRUD operations: {list(COLLECTION_CRUD_FLAG_MAPPING.keys())}")
            print(f"🔍 Suggestion: Add '{crud_operation}' to COLLECTION_CRUD_FLAG_MAPPING")

            # Try to suggest a similar existing key
            similar_keys = [key for key in COLLECTION_CRUD_FLAG_MAPPING.keys() if 'delete' in key and 'delete' in crud_operation]
            if similar_keys:
                print(f"💡 Similar existing keys: {similar_keys}")
            continue

        # Process each meta data item in the list
        for meta_data_item in meta_data_list:
            await process_single_meta_data_item(
                target_type=target_type,
                crud_operation=crud_operation,
                crud_flag=crud_flag,
                meta_data_item=meta_data_item,
                core_seeds=core_seeds,
                generic_service=generic_service,
                create_restricted_profil=create_restricted_profil,
                create_restricted_api_consumer=create_restricted_api_consumer,
                permission_data=permission_data
            )

async def process_single_meta_data_item(
    target_type,
    crud_operation,
    crud_flag,
    meta_data_item,
    core_seeds,
    generic_service,
    create_restricted_profil,
    create_restricted_api_consumer,
    permission_data=None,
):
    """
    Process a single meta data item.

    Args:
        target_type (str): Either 'menus' or 'apps'
        crud_operation (str): The CRUD operation name
        crud_flag: The corresponding ECollectionCrudInfoFlag
        crud_hard_code_flag: The corresponding hard code flag
        meta_data_item (dict): The individual meta data item
        core_seeds (dict): The core seeds data
        generic_service: The generic service instance
        create_restricted_profil: Function to create profile restrictions
        create_restricted_api_consumer: Function to create API consumer restrictions
    """
    try:
        print(f"🔍 Processing {crud_operation} item for {target_type}: {meta_data_item.get('hard_code_flag', 'N/A')}")

        # Skip if parent field name is True (special case)
        if meta_data_item.get('is_parent_field_name', False):
            print(f"⏭️  Skipping parent field name item")
            return
        
        # Get crud_hard_code_flag
        crud_hard_code_flag = meta_data_item.get('hard_code_flag', 'main')

        # Fetch RBAC endpoint data
        rbac_endpoint_data = await fetch_rbac_endpoint_data(
            generic_service, meta_data_item.get('rbac_endpoint')
        )
        if not rbac_endpoint_data:
            print(f"❌ RBAC endpoint not found: {meta_data_item.get('rbac_endpoint')}")
            print(f"💡 Suggestion: Check the URL in the meta data item")
            return

        # Fetch target data (menu or app)
        target_data = await fetch_target_data(
            generic_service, target_type, meta_data_item
        )
        if not target_data:
            target_flag = meta_data_item.get('menu_flag') or meta_data_item.get('app_flag')
            print(f"❌ Target {target_type} not found: {target_flag}")
            return

        # Handle sudo actions before creating collection CRUD info
        if permission_data:
            await handle_sudo_actions(
                generic_service=generic_service,
                meta_data_item=meta_data_item,
                rbac_endpoint_data=rbac_endpoint_data,
                permission_data=permission_data,
                core_seeds=core_seeds,
                create_restricted_profil=create_restricted_profil,
                create_restricted_api_consumer=create_restricted_api_consumer
            )

        # Create or update collection CRUD info
        saved_collection_crud_info_id = await upsert_collection_crud_info(
            generic_service=generic_service,
            target_data=target_data,
            rbac_endpoint_data=rbac_endpoint_data,
            crud_flag=crud_flag,
            crud_hard_code_flag=crud_hard_code_flag,
            meta_data_item=meta_data_item,
        )

        if saved_collection_crud_info_id:
            print(f"✅ Saved collection CRUD info: {saved_collection_crud_info_id}")

            # Apply restrictions to collection CRUD info
            await apply_restrictions(
                saved_collection_crud_info_id=saved_collection_crud_info_id,
                core_seeds=core_seeds,
                generic_service=generic_service,
                create_restricted_profil=create_restricted_profil,
                create_restricted_api_consumer=create_restricted_api_consumer
            )

        # Process endpoint restrictions from collection_meta_data_to_menus
        if rbac_endpoint_data and permission_data:
            await process_endpoint_restrictions_from_meta_data(
                rbac_endpoint_data=rbac_endpoint_data,
                permission_data=permission_data,
                core_seeds=core_seeds,
                generic_service=generic_service,
                create_restricted_profil=create_restricted_profil,
                create_restricted_api_consumer=create_restricted_api_consumer
            )

    except Exception as e:
        print(f"❌ Error processing meta data item: {str(e)}")
        import traceback
        traceback.print_exc()

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

async def fetch_target_data(generic_service, target_type, meta_data_item):
    """Fetch target data (menu or app) from database."""
    if target_type == 'menus':
        target_flag = meta_data_item.get('menu_flag')
        collection_key = CollectionKey.SYS_MENU
    elif target_type == 'apps':
        target_flag = meta_data_item.get('app_flag')
        collection_key = CollectionKey.SYS_APPLICATION
    else:
        return None

    if not target_flag:
        return None

    return await generic_service.fetch_one_from_collection(
        collection_key=collection_key,
        output_data_type=OutputDataType.DEFAULT,
        accept_language=DEFAULT_LANGUAGE,
        query={"filter__flag": target_flag}
    )

async def upsert_collection_crud_info(
        generic_service, 
        target_data, rbac_endpoint_data, crud_flag,crud_hard_code_flag,meta_data_item):
    """Create or update collection CRUD info."""

    is_link_deleted = meta_data_item.get('is_link_deleted', False)
    print(f"🗑️ is_link_deleted: {is_link_deleted}")
    # Check if the link is deleted
    if is_link_deleted:
        # DELETE ITEM
        collection_crud_info = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.REF_COLLECTION_CRUD_INFO,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=DEFAULT_LANGUAGE,
            query={
                "filter__targeted_id": target_data['id'],
                "filter__rbac_endpoint_id": rbac_endpoint_data['id'],
                "filter__flag": crud_flag,
                "filter__hard_code_flag": crud_hard_code_flag
            }
        )
        if collection_crud_info:
            # Delete restrictions on the collection_crud_info entry first
            await delete_all_restrictions_for_targeted_id(generic_service, collection_crud_info['id'])
            await generic_service.hard_delete_data_from_collection(
                collection_key=CollectionKey.REF_COLLECTION_CRUD_INFO,
                item_id=collection_crud_info['id']
            )
            print(f"🗑️ Deleted collection CRUD info + restrictions: {collection_crud_info['id']}")
        return None
    else:
        saved_collection_crud_info = await generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.REF_COLLECTION_CRUD_INFO,
            filter_data={
                "targeted_id": target_data['id'],
                "rbac_endpoint_id": rbac_endpoint_data['id'],
                "flag": crud_flag,
                "hard_code_flag": crud_hard_code_flag
            },
            update_data={
                "targeted_id": target_data['id'],
                "label": rbac_endpoint_data['label'],
                "rbac_endpoint_id": rbac_endpoint_data['id'],
                "flag": crud_flag,
                "hard_code_flag": crud_hard_code_flag
            }
        )

        return saved_collection_crud_info if isinstance(saved_collection_crud_info, str) else str(saved_collection_crud_info['id'])

async def apply_restrictions(
    saved_collection_crud_info_id,
    core_seeds,
    generic_service,
    create_restricted_profil,
    create_restricted_api_consumer
):
    """Apply profile and API consumer restrictions."""
    # Apply profile restrictions
    if 'restricted_profil_list' in core_seeds:
        restricted_profil_list = core_seeds['restricted_profil_list']
        for profil in restricted_profil_list:
            # Handle new object structure - profil is now an object with flag and link fields
            profil_flag = profil.get('flag') if isinstance(profil, dict) else profil
            # Fetch profile from db by flag
            sys_profil_db_item = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=DEFAULT_LANGUAGE,
                query={"filter__flag": profil_flag}
            )
            if sys_profil_db_item:
                await create_restricted_profil(
                    targeted_id=saved_collection_crud_info_id,
                    rbac_profile_id=sys_profil_db_item['id']
                )
                print(f"✅ Applied profile restriction: {profil}")

    # Apply API consumer restrictions
    if 'restricted_api_consumer_list' in core_seeds:
        restricted_api_consumer_list = core_seeds['restricted_api_consumer_list']
        for api_consumer in restricted_api_consumer_list:
            # Handle new object structure - api_consumer is now an object with flag and link fields
            api_consumer_flag = api_consumer.get('flag') if isinstance(api_consumer, dict) else api_consumer
            # Fetch API consumer from db by flag
            ref_api_consumer_db_item = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_API_CONSUMER,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=DEFAULT_LANGUAGE,
                query={"filter__flag": api_consumer_flag}
            )
            if ref_api_consumer_db_item:
                await create_restricted_api_consumer(
                    targeted_id=saved_collection_crud_info_id,
                    ref_api_consumer_id=ref_api_consumer_db_item['id']
                )
                print(f"✅ Applied API consumer restriction: {api_consumer}")

async def process_endpoint_restrictions_from_meta_data(
    rbac_endpoint_data,
    permission_data,
    core_seeds,
    generic_service,
    create_restricted_profil,
    create_restricted_api_consumer
):
    """
    Process endpoint restrictions from collection_meta_data_to_menus.
    Creates permission targets for endpoints and applies profile/API consumer restrictions.

    Args:
        rbac_endpoint_data: The RBAC endpoint data
        permission_data: The permission data
        core_seeds: The core seeds data
        generic_service: The generic service instance
        create_restricted_profil: Function to create profile restrictions
        create_restricted_api_consumer: Function to create API consumer restrictions
    """
    try:
        print(f"🔗 Processing endpoint restrictions for: {rbac_endpoint_data.get('label', 'N/A')}")

        # Create or update permission target for the endpoint
        saved_target = await generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
            filter_data={
                "targeted_id": rbac_endpoint_data['id'],
                "rbac_permission_id": permission_data['id']
            },
            update_data={
                "targeted_id": rbac_endpoint_data['id'],
                "rbac_permission_id": permission_data['id']
            }
        )

        processed_target_id = saved_target if isinstance(saved_target, str) else str(saved_target['id'])
        print(f"✅ Created/updated permission target for endpoint: {rbac_endpoint_data.get('label', 'N/A')}")

        # Apply profile restrictions
        if 'restricted_profil_list' in core_seeds:
            restricted_profil_list = core_seeds['restricted_profil_list']
            for profil in restricted_profil_list:
                # Handle new object structure - profil is now an object with flag and link fields
                profil_flag = profil.get('flag') if isinstance(profil, dict) else profil

                is_link_deleted = profil.get('is_link_deleted', False)
                is_link_activated = profil.get('is_link_activated', True)
                is_link_hidden = profil.get('is_link_hidden', False)
                is_link_locked = profil.get('is_link_locked', False)

                # Fetch profile from db by flag
                sys_profil_db_item = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_PROFILE,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=DEFAULT_LANGUAGE,
                    query={"filter__flag": profil_flag}
                )

                if sys_profil_db_item:

                    # PROCESS TARGET
                    await create_restricted_profil(
                        targeted_id=processed_target_id,
                        rbac_profile_id=sys_profil_db_item['id'],
                        is_activated=is_link_activated,
                        is_hidden=is_link_hidden,
                        is_locked=is_link_locked,
                        is_deleted=is_link_deleted,
                    )
                    # PROCESS ENDPOINT AND PROFIL
                    await create_restricted_profil(
                        targeted_id=rbac_endpoint_data['id'],
                        rbac_profile_id=sys_profil_db_item['id'],
                        is_activated=is_link_activated,
                        is_hidden=is_link_hidden,
                        is_locked=is_link_locked,
                        is_deleted=is_link_deleted,
                    )
                    print(f"✅✅✅ Applied profile restriction to endpoint: {profil_flag}")

        # Apply API consumer restrictions
        if 'restricted_api_consumer_list' in core_seeds:
            restricted_api_consumer_list = core_seeds['restricted_api_consumer_list']
            for platform in restricted_api_consumer_list:
                # Handle new object structure - platform is now an object with flag and link fields
                platform_flag = platform.get('flag') if isinstance(platform, dict) else platform

                is_link_deleted = platform.get('is_link_deleted', False)
                is_link_activated = platform.get('is_link_activated', True)
                is_link_hidden = platform.get('is_link_hidden', False)
                is_link_locked = platform.get('is_link_locked', False)

                # Fetch API consumer from db by flag
                ref_api_consumer_db_item = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_API_CONSUMER,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language=DEFAULT_LANGUAGE,
                    query={"filter__flag": platform_flag}
                )

                if ref_api_consumer_db_item:
                    # PROCESS TARGET
                    await create_restricted_api_consumer(
                        targeted_id=processed_target_id,
                        ref_api_consumer_id=ref_api_consumer_db_item['id'],
                        is_activated=is_link_activated,
                        is_hidden=is_link_hidden,
                        is_locked=is_link_locked,
                        is_deleted=is_link_deleted,
                    )
                    # PROCESS ENDPOINT AND PLATFORM
                    await create_restricted_api_consumer(
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
        import traceback
        traceback.print_exc()

async def handle_sudo_actions(
    generic_service,
    meta_data_item,
    rbac_endpoint_data,
    permission_data,
    core_seeds,
    create_restricted_profil,
    create_restricted_api_consumer
):
    """
    Handle sudo action and sudo group action flags.

    Args:
        generic_service: The generic service instance
        meta_data_item (dict): The meta data item containing sudo flags
        rbac_endpoint_data (dict): The RBAC endpoint data
        core_seeds (dict): The core seeds data
        create_restricted_profil: Function to create profile restrictions
        create_restricted_api_consumer: Function to create API consumer restrictions
    """
    is_sudo_action = meta_data_item.get('is_sudo_action', False)
    is_sudo_group_action = meta_data_item.get('is_sudo_group_action', False)
    is_available_for_rls = meta_data_item.get('is_available_for_rls', False)
    is_sudo_delegated_action = meta_data_item.get('is_sudo_delegated_action', False)
    is_sudo_cross_organization_validation_action = meta_data_item.get('is_sudo_cross_organization_validation_action', False)
    is_sudo_inter_connected_organization_validation_action = meta_data_item.get('is_sudo_inter_connected_organization_validation_action', False)

    print(f"🔐 Processing sudo actions - sudo_action: {is_sudo_action}, sudo_group_action: {is_sudo_group_action}")

    # Update endpoint sudo flags
    await update_endpoint_sudo_flags(
        generic_service=generic_service,
        rbac_endpoint_data=rbac_endpoint_data,
        is_sudo_action=is_sudo_action,
        is_sudo_group_action=is_sudo_group_action,
        is_available_for_rls=is_available_for_rls,
        is_sudo_delegated_action=is_sudo_delegated_action,
        permission_data=permission_data,
        is_sudo_cross_organization_validation_action=is_sudo_cross_organization_validation_action,
        is_sudo_inter_connected_organization_validation_action=is_sudo_inter_connected_organization_validation_action
    )

    # Update permission sudo flags
    await update_permission_sudo_flags(
        generic_service=generic_service,
        permission_data=permission_data,
        is_sudo_action=is_sudo_action,
        is_sudo_group_action=is_sudo_group_action,
        is_sudo_delegated_action=is_sudo_delegated_action,
        is_available_for_rls=is_available_for_rls
    )

    # Handle RBAC_SUDO_ACTION upsert if either flag is True
    if is_sudo_action or is_sudo_group_action:
        await handle_rbac_sudo_action_upsert(
            generic_service=generic_service,
            rbac_endpoint_data=rbac_endpoint_data,
            permission_data=permission_data,
            is_sudo_action=is_sudo_action,
            is_sudo_group_action=is_sudo_group_action,
            core_seeds=core_seeds,
            create_restricted_profil=create_restricted_profil,
            create_restricted_api_consumer=create_restricted_api_consumer
        )

async def update_endpoint_sudo_flags(generic_service, rbac_endpoint_data, is_sudo_action, is_sudo_group_action, is_available_for_rls, is_sudo_delegated_action, permission_data, is_sudo_cross_organization_validation_action, is_sudo_inter_connected_organization_validation_action):
    """Update the RBAC endpoint sudo flags."""
    from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
    rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)
    try:
        data = {
                "is_sudo_action": is_sudo_action,
                "is_sudo_group_action": is_sudo_group_action,
                "is_available_for_rls": is_available_for_rls,
                "is_sudo_delegated_action": is_sudo_delegated_action,
                "is_sudo_cross_organization_validation_action": is_sudo_cross_organization_validation_action,
                "is_sudo_inter_connected_organization_validation_action": is_sudo_inter_connected_organization_validation_action
            }
        await generic_service.update_data_in_collection(
            collection_key=CollectionKey.RBAC_ENDPOINT,
            item_id=rbac_endpoint_data['id'],
            data=data
        )
        
        all_orgs = await generic_service.fetch_data_from_collection(
            collection_key=CollectionKey.SYS_ORGANIZATION,
            output_data_type=OutputDataType.DEFAULT,
            all_data=True,
            query={
                "is_activated": True
            }
        ) 
        sudo_action_type = EConfigSudoActionTypeFlag.NONE.value
        
        if is_sudo_action or is_sudo_group_action or is_sudo_delegated_action or is_sudo_cross_organization_validation_action or is_sudo_inter_connected_organization_validation_action or is_available_for_rls:
            for org in all_orgs:
                as_access_to_permission = await rbac_role_service.organization_has_permission(org['id'],permission_data['id'])
                
                # IS_SUDO_ACTION
                if is_sudo_action and as_access_to_permission:
                    sudo_action_type = EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value
                    await generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                        filter_data={
                            "rbac_endpoint_id": rbac_endpoint_data['id'],
                            "rbac_permission_id": permission_data['id'],
                            "sys_organization_id": str(org['id']),
                            "sudo_action_type": sudo_action_type,
                        },
                        update_data={
                            "rbac_endpoint_id": rbac_endpoint_data['id'],
                            "rbac_permission_id": permission_data['id'],
                            "sys_organization_id": str(org['id']),
                            "sudo_action_type": sudo_action_type,
                            # "is_enabled": False
                        } 
                    )
                
                # IS_SUDO_GROUP_ACTION
                if is_sudo_group_action and as_access_to_permission:
                    sudo_action_type = EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value
                    await generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                        filter_data={
                            "rbac_endpoint_id": rbac_endpoint_data['id'],
                            "rbac_permission_id": permission_data['id'],
                            "sys_organization_id": str(org['id']),
                            "sudo_action_type": sudo_action_type,
                        },
                        update_data={
                            "rbac_endpoint_id": rbac_endpoint_data['id'],
                            "rbac_permission_id": permission_data['id'],
                            "sys_organization_id": str(org['id']),
                            "sudo_action_type": sudo_action_type,
                            # "is_enabled": False
                        } 
                    )

                # IS_SUDO_DELEGATED_ACTION
                if is_sudo_delegated_action and as_access_to_permission:
                    sudo_action_type = EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION.value
                    await generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                        filter_data={
                            "rbac_endpoint_id": rbac_endpoint_data['id'],
                            "rbac_permission_id": permission_data['id'],
                            "sys_organization_id": str(org['id']),
                            "sudo_action_type": sudo_action_type,
                        },
                        update_data={
                            "rbac_endpoint_id": rbac_endpoint_data['id'],
                            "rbac_permission_id": permission_data['id'],
                            "sys_organization_id": str(org['id']),
                            "sudo_action_type": sudo_action_type,
                            # "is_enabled": False
                        }
                    )

                # IS_SUDO_GROUP_CROSS_VALIDATION_ACTION output_data_type
                if is_sudo_cross_organization_validation_action and as_access_to_permission:
                    sudo_action_type = EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION.value
                    await generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                        filter_data={
                            "rbac_endpoint_id": rbac_endpoint_data['id'],
                            "rbac_permission_id": permission_data['id'],
                            "sys_organization_id": str(org['id']),
                            "sudo_action_type": sudo_action_type,
                        },
                        update_data={
                            "rbac_endpoint_id": rbac_endpoint_data['id'],
                            "rbac_permission_id": permission_data['id'],
                            "sys_organization_id": str(org['id']),
                            "sudo_action_type": sudo_action_type,
                            # "is_enabled": False
                        } 
                    ) 

                # IS_SUDO_GROUP_INTER_ORGANIZATION_VALIDATION_ACTION
                if is_sudo_inter_connected_organization_validation_action and as_access_to_permission:
                    sudo_action_type = EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION.value
                    await generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                        filter_data={
                            "rbac_endpoint_id": rbac_endpoint_data['id'],
                            "rbac_permission_id": permission_data['id'],
                            "sys_organization_id": str(org['id']),
                            "sudo_action_type": sudo_action_type,
                        },
                        update_data={
                            "rbac_endpoint_id": rbac_endpoint_data['id'],
                            "rbac_permission_id": permission_data['id'],
                            "sys_organization_id": str(org['id']),
                            "sudo_action_type": sudo_action_type,
                        } 
                    ) 


                if is_available_for_rls:
                    await generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.CFG_ORGANIZATION_RLS,
                        filter_data={
                            "sys_organization_id":str(org['id']),
                            "rbac_endpoint_id": rbac_endpoint_data['id'],
                            "rbac_permission_id": permission_data['id']},
                        update_data={
                            "rbac_endpoint_id": rbac_endpoint_data['id'],
                            "rbac_permission_id": permission_data['id'],
                            "sys_organization_id": str(org['id']),
                        } 
                    )
                

                await generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.CFG_RLS_SETUP,
                    filter_data={"sys_organization_id":str(org['id'])},
                    update_data={
                        "sys_organization_id": str(org['id']),
                    } 
                ) 
                await generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.CFG_SUDO_ACTION_SETUP,
                    filter_data={"sys_organization_id":str(org['id'])},
                    update_data={
                        "sys_organization_id": str(org['id']),
                    }
                )
                 
            
        # if rbac_endpoint_data['url'] == '/api/v1/generic/org/add/cfgBanks':
        #     print(f"✅ Updated endpoint sudo flags: {rbac_endpoint_data} data : {data} id : {rbac_endpoint_data['id']}")
        print(f"✅ Updated endpoint sudo flags: {rbac_endpoint_data['url']} data : {data} id : {rbac_endpoint_data['id']}")
    except Exception as e:
        print(f"❌ Error updating endpoint sudo flags > : {str(e)}")



async def update_permission_sudo_flags(generic_service, permission_data, is_sudo_action, is_sudo_group_action, is_available_for_rls, is_sudo_delegated_action):
    """Update the RBAC permission sudo flags."""
    try:
        await generic_service.update_data_in_collection(
            collection_key=CollectionKey.RBAC_PERMISSION,
            item_id=permission_data['id'],
            data={
                "is_sudo_action": is_sudo_action,
                "is_sudo_group_action": is_sudo_group_action,
                "is_available_for_rls": is_available_for_rls,
                "is_sudo_delegated_action": is_sudo_delegated_action
            }
        )
        print(f"✅ Updated permission sudo flags: {permission_data['flag']}")
    except Exception as e:
        print(f"❌ Error updating permission sudo flags: {str(e)}")

async def handle_rbac_sudo_action_upsert(
    generic_service,
    rbac_endpoint_data,
    permission_data,
    is_sudo_action,
    is_sudo_group_action,
    core_seeds,
    create_restricted_profil,
    create_restricted_api_consumer
):
    """Handle RBAC_SUDO_ACTION upsert and apply restrictions."""
    try:
        # Upsert RBAC_SUDO_ACTION
        saved_sudo_action = await generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.RBAC_SUDO_ACTION,
            filter_data={
                "targeted_id": rbac_endpoint_data['id'],
                "rbac_permission_id": permission_data['id']
            },
            update_data={
                "targeted_id": rbac_endpoint_data['id'],
                "rbac_permission_id": permission_data['id'],
                "is_sudo_action": is_sudo_action,
                "is_sudo_group_action": is_sudo_group_action,
                "description_str": f"Sudo action for {rbac_endpoint_data['url']} - {permission_data['flag']}"
            }
        )

        saved_sudo_action_id = saved_sudo_action if isinstance(saved_sudo_action, str) else str(saved_sudo_action['id'])
        print(f"✅ Saved RBAC sudo action: {saved_sudo_action_id}")

        # Apply restrictions to the sudo action
        await apply_restrictions(
            saved_collection_crud_info_id=saved_sudo_action_id,
            core_seeds=core_seeds,
            generic_service=generic_service,
            create_restricted_profil=create_restricted_profil,
            create_restricted_api_consumer=create_restricted_api_consumer
        )

    except Exception as e:
        print(f"❌ Error handling RBAC sudo action upsert: {str(e)}")


async def handle_all_access_core_seeds(all_access_core_seeds,permission_db_item,generic_service):
    try:
        print(f"all_access_core_seeds : >>>  {len(all_access_core_seeds)}")
        from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
        rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)
        # fetch all roles and update
        # all_roles = await generic_service.fetch_data_from_collection(
        #     collection_key=CollectionKey.RBAC_ROLE,
        #     output_data_type=OutputDataType.DEFAULT,
        #     all_data=True,
        #     query={
        #         "is_activated":True
        #     }
        # )

        # print(f"\n\n\n\n ALL ROLE : {all_roles}")

        # # loop to upsert permision role
        # for role in all_roles:
        #     # Get the corresponding CRUD flag
        #     await  generic_service.upsert_data_to_collection(
        #         collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
        #         filter_data={
        #             "targeted_id": role['id'],
        #             "rbac_permission_id": permission_db_item['id']
        #         },
        #         update_data={
        #             "targeted_id": role['id'],
        #             "rbac_permission_id": permission_db_item['id']
        #         }
        #     )
        # Iterate through all CRUD operations
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
                    # endpoint_url = meta_data_item.get('rbac_endpoint')
                    # await generic_service.upsert_data_to_collection(
                    #     collection_key=CollectionKey.RBAC_ENDPOINT,
                    #     filter_data={'url':endpoint_url,"rbac_title_id":endpoint_item['rbac_title_id']},
                    #     update_data=endpoint_item
                    # )
                    print(f"❌ RBAC endpoint not found: {meta_data_item.get('rbac_endpoint')}")
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


async def process_rbac_endpoint(endpoint_item,rbac_title_db_item,generic_service):
    from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
    rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)
    try:
        # Handle is_link_deleted: cascade delete the endpoint and all references
        if endpoint_item.get('is_link_deleted', False):
            existing_endpoint = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ENDPOINT,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=DEFAULT_LANGUAGE,
                query={"filter__url": endpoint_item['url']}
            )
            if existing_endpoint:
                await cascade_delete_endpoint_references(generic_service, existing_endpoint['id'])
                print(f"🗑️ Cascade deleted endpoint (is_link_deleted=True): {endpoint_item.get('label', endpoint_item['url'])}")
            else:
                print(f"⏭️  Endpoint already absent (is_link_deleted=True): {endpoint_item['url']}")
            return

        # GET ENDPOINT FROM DB BY URL
        await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_ENDPOINT,
                # "is_link_deleted": False,
                filter_data={"url":endpoint_item['url']},
                update_data=endpoint_item
            )
        rbac_endpoint_db_item = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_ENDPOINT,
            output_data_type=OutputDataType.DEFAULT,
            accept_language= DEFAULT_LANGUAGE,
            query={
                "filter__url":endpoint_item['url']
            }
        )
        if rbac_endpoint_db_item:
            print(f"rbac_endpoint_db_item founded : {rbac_endpoint_db_item}")
        else :
            print(f"rbac_endpoint_db_item not founded : {endpoint_item['url']}")
            # add missing endpoint
            await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.RBAC_ENDPOINT,
                # "is_link_deleted": False,
                filter_data={"url":endpoint_item['url']},
                update_data=endpoint_item
            )
            rbac_endpoint_db_item = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ENDPOINT,
                output_data_type=OutputDataType.DEFAULT,
                accept_language= DEFAULT_LANGUAGE,
                query={
                    "filter__url":endpoint_item['url']
                }
            )
            if rbac_endpoint_db_item:
                print(f"rbac_endpoint_db_item added : {rbac_endpoint_db_item}") 
    except Exception as e:
        print(f"❌ Error processing endpoint restrictions: {str(e)}")



async def delete_all_restrictions_for_targeted_id(generic_service, targeted_id):
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
    print(f"🗑️ Deleted all restrictions for targeted_id: {targeted_id}")


async def delete_all_permission_targets_and_restrictions(generic_service, targeted_id):
    """Delete all RBAC_PERMISSION_TARGET entries for a targeted_id, plus their restrictions and direct restrictions."""
    permission_targets = await generic_service.fetch_data_from_collection(
        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
        output_data_type=OutputDataType.DEFAULT,
        all_data=True,
        query={"filter__targeted_id": str(targeted_id)}
    )
    for target in (permission_targets or []):
        await delete_all_restrictions_for_targeted_id(generic_service, target['id'])
        await generic_service.hard_delete_data_from_collection(
            collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
            item_id=target['id']
        )
    # Also delete direct restrictions on the item itself
    await delete_all_restrictions_for_targeted_id(generic_service, targeted_id)
    print(f"🗑️ Deleted all permission targets and restrictions for: {targeted_id}")


async def cascade_delete_menu_references(generic_service, menu_id):
    """Cascade delete all RBAC references for a menu and its sub-menus (sys_menu_id = menu_id)."""
    await delete_all_permission_targets_and_restrictions(generic_service, menu_id)
    sub_menus = await generic_service.fetch_data_from_collection(
        collection_key=CollectionKey.SYS_MENU,
        output_data_type=OutputDataType.DEFAULT,
        all_data=True,
        query={"filter__sys_menu_id": str(menu_id)}
    )
    for sub_menu in (sub_menus or []):
        await cascade_delete_menu_references(generic_service, sub_menu['id'])
    print(f"🗑️ Cascade deleted all RBAC references for menu: {menu_id}")


async def cascade_delete_app_references(generic_service, app_id):
    """Cascade delete all RBAC references for an app, its menus, and their sub-menus."""
    await delete_all_permission_targets_and_restrictions(generic_service, app_id)
    app_menus = await generic_service.fetch_data_from_collection(
        collection_key=CollectionKey.SYS_MENU,
        output_data_type=OutputDataType.DEFAULT,
        all_data=True,
        query={"filter__sys_application_id": str(app_id)}
    )
    for menu in (app_menus or []):
        await cascade_delete_menu_references(generic_service, menu['id'])
    print(f"🗑️ Cascade deleted all RBAC references for app: {app_id}")


async def cascade_delete_endpoint_references(generic_service, endpoint_id):
    """Cascade delete all RBAC references for an endpoint:
    - RBAC_PERMISSION_TARGET (where targeted_id = endpoint_id) + their restrictions
    - RBAC_RESTRICTED_PROFIL / RBAC_RESTRICTED_API_CONSUMER (where targeted_id = endpoint_id)
    - REF_COLLECTION_CRUD_INFO (where rbac_endpoint_id = endpoint_id) + their restrictions
    - RBAC_ENDPOINT itself
    """
    # 1. Delete permission targets + their restrictions + direct restrictions
    await delete_all_permission_targets_and_restrictions(generic_service, endpoint_id)

    # 2. Delete all REF_COLLECTION_CRUD_INFO entries referencing this endpoint
    collection_crud_infos = await generic_service.fetch_data_from_collection(
        collection_key=CollectionKey.REF_COLLECTION_CRUD_INFO,
        output_data_type=OutputDataType.DEFAULT,
        all_data=True,
        query={"filter__rbac_endpoint_id": str(endpoint_id)}
    )
    for crud_info in (collection_crud_infos or []):
        await delete_all_restrictions_for_targeted_id(generic_service, crud_info['id'])
        await generic_service.hard_delete_data_from_collection(
            collection_key=CollectionKey.REF_COLLECTION_CRUD_INFO,
            item_id=crud_info['id']
        )

    # 3. Delete the endpoint itself
    await generic_service.hard_delete_data_from_collection(
        collection_key=CollectionKey.RBAC_ENDPOINT,
        item_id=str(endpoint_id)
    )
    print(f"🗑️ Cascade deleted all RBAC references for endpoint: {endpoint_id}")


async def cascade_delete_permission_references(generic_service, permission_id):
    """Delete all RBAC references for a permission (targets, restrictions, roles)."""
    permission_targets = await generic_service.fetch_data_from_collection(
        collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
        output_data_type=OutputDataType.DEFAULT,
        all_data=True,
        query={"filter__rbac_permission_id": str(permission_id)}
    )
    for target in (permission_targets or []):
        await delete_all_restrictions_for_targeted_id(generic_service, target['id'])
        await generic_service.hard_delete_data_from_collection(
            collection_key=CollectionKey.RBAC_PERMISSION_TARGET,
            item_id=target['id']
        )
    # Delete direct restrictions on the permission itself
    await delete_all_restrictions_for_targeted_id(generic_service, permission_id)
    # Delete all RBAC_PERMISSION_ROLE entries for this permission
    permission_roles = await generic_service.fetch_data_from_collection(
        collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
        output_data_type=OutputDataType.DEFAULT,
        all_data=True,
        query={"filter__rbac_permission_id": str(permission_id)}
    )
    for pr in (permission_roles or []):
        await generic_service.hard_delete_data_from_collection(
            collection_key=CollectionKey.RBAC_PERMISSION_ROLE,
            item_id=pr['id']
        )
    print(f"🗑️ Cascade deleted all RBAC references for permission: {permission_id}")
 
async def create_core_infos():
    try:
        from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
        rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)
        """
        Create default API consumers if they do not already exist.
        """
        generic_service = GenericService(DEFAULT_LANGUAGE)
        rbac_titles = CORE_RBAC_TITLE_DB
        print(f" rbac_titles ln : {len(rbac_titles)}")
        # Check for and extract "label" and "flag"
        

        # Loop through each item in the list
        for index,item in enumerate(rbac_titles):
            print(f" rbac_title index : {index}")
            await rbac_role_service.recursive_rbac_title(item,None)
    
    except ValueError as e:
        print(f"Error in create_core_infos : {e}")
    except PermissionError as e:
        print(f"Permission Error: {e}")
    

# if __name__ == "__main__":
if __name__ == "__main__":
    loop = asyncio.get_event_loop()  # Get the current event loop
    loop.run_until_complete(init_data())  # Run without creating a nested loop
