# app/db/session.py
from app.modules.core.enums.type_enum import EMultipleValidationStatus
from app.modules.core.services.encryption.encryption_service import EncryptionService
from app.modules.core.services.debug.debug_service import DebugService
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from beanie import init_beanie
from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
from app.modules.core.configs.config import settings
import os
import asyncio
 
# Initialize Redis client with password
redis_url = settings.REDIS_URL.format(REDIS_PASSWORD=os.getenv('REDIS_PASSWORD', ''))
redis_client = redis.from_url(redis_url)

async def drop_all_indexes():
    # Create MongoDB client with SSL configuration for Atlas
    client = AsyncIOMotorClient(
        settings.MONGO_URI,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000
    )
    db = client[settings.MONGO_DB_NAME]
    
    collections = await db.list_collection_names()
    for collection_name in collections:
        collection = db[collection_name]
        indexes = await collection.list_indexes().to_list(length=None)
        for index_name in indexes:
            # Skip the default _id index
            if index_name != "_id_":
                print(f"Dropping index: {index_name} from collection: {collection_name}")
                await collection.drop_index(index_name)
        # After dropping, let's list the remaining indexes for verification
        indexes = await collection.index_information()
        print(f"Remaining indexes for {collection_name}: {indexes}")

async def get_db():
     # Create a MongoDB client with SSL configuration for Atlas
    client = AsyncIOMotorClient(
        settings.MONGO_URI,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000
    )
    db = client[settings.MONGO_DB_NAME]
    return db

async def init_db():
    """
    Initialize MongoDB and Beanie.
    """
    # Create a MongoDB client with SSL configuration for Atlas and increased pool
    client = AsyncIOMotorClient(
        settings.MONGO_URI,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000,
        maxPoolSize=200,  # Increased from 100 to reduce blocking under concurrent load
        minPoolSize=10,   # Keep some connections warm
        maxIdleTimeMS=30000,  # Close idle connections after 30s
        waitQueueTimeoutMS=10000,  # Wait up to 10s for connection
    )
    db = client[settings.MONGO_DB_NAME]
     
    # Drop all indexes for all collections \
    # drop_all_indexes() 
    
    # Initialize Beanie with only the model classes
    await init_beanie(database=db, document_models=[metadata.model_class for metadata in COLLECTION_MODEL_MAPPING.values()])
    print("Database initialized successfully.")


async def create_view_for_collection(db, collection_name: str):
    """Create a view for a specific collection that excludes soft-deleted documents."""
    # Vérifier si le nom de la collection commence déjà par view_
    if collection_name.startswith('view_'):
        print(f"⚠️ La collection {collection_name} est déjà une vue")
        return

    view_name = f"view_{collection_name}"

    # Check if the view exists by listing all collections
    # This avoids direct access to system.views which is restricted in Atlas
    all_collections = await db.list_collection_names()
    if view_name in all_collections:
        print(f"ℹ️ La vue {view_name} existe déjà")
        return

    pipeline = [
        {"$match": {"soft_deleted_at": None,"multiple_validation_status": EMultipleValidationStatus.APPROVED.value}},
    ]

    try:
        # Use the createView command instead of direct system.views access
        await db.command({
            "create": view_name,
            "viewOn": collection_name,
            "pipeline": pipeline
        })
        print(f"✅ Vue créée pour la collection {collection_name}")
    except Exception as e:
        print(f"❌ Erreur lors de la création de la vue pour {collection_name}: {str(e)}")

async def monitor_new_collections(db):
    """Monitor for new collections using periodic checks with reduced frequency."""
    from app.modules.core.services.view.instant_view_service import InstantViewService

    # Liste des collections déjà traitées
    processed_collections = set()

    # Get the instant view service instance
    instant_view_service = InstantViewService.get_instance()

    while True:
        try:
            # Get current collections
            current_collections = set(await db.list_collection_names())

            # Filtrer les collections qui ne sont pas des vues et qui n'ont pas encore été traitées
            new_collections = {
                collection for collection in current_collections
                if not collection.startswith('view_')  # Exclure les vues existantes
                and collection not in processed_collections
                and collection not in ["system.views", "system.indexes"]
            }

            if new_collections:
                print(f"📝 Nouvelles collections détectées par le monitoring: {new_collections}")
                if instant_view_service:
                    for collection in new_collections:
                        await instant_view_service.create_view_for_collection(collection)
                else:
                    # Fallback to old method if service not available
                    for collection in new_collections:
                        await create_view_for_collection(db, collection)

                # Mettre à jour la liste des collections traitées
                processed_collections.update(new_collections)

            # Vérifier toutes les 5 minutes (réduit la fréquence pour économiser les ressources)
            await asyncio.sleep(300)

        except Exception as e:
            print(f"❌ Erreur lors de la surveillance des collections: {str(e)}")
            # Attendre 30 secondes en cas d'erreur
            await asyncio.sleep(30)

async def create_views():
    """Create MongoDB views for active (not soft-deleted) documents."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.modules.core.configs.config import settings
    from app.modules.core.services.view.instant_view_service import InstantViewService

    client = AsyncIOMotorClient(
        settings.MONGO_URI,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000
    )
    db = client[settings.MONGO_DB_NAME]

    collections = await db.list_collection_names()

    # Initialize the instant view service
    instant_view_service = await InstantViewService.initialize(db)

    # Process each collection that is not a view or system collection
    for collection in collections:
        if collection not in ["system.views", "system.indexes"] and not collection.startswith('view_'):
            await instant_view_service.create_view_for_collection(collection)

    # NOTE: monitor_new_collections is started ONLY from startup.py/start_background_tasks
    # to avoid duplicate monitors
    # from app.modules.core.services.generic.generic_services import GenericService
    # generic_service = GenericService(accept_language=DEFAULT_LANGUAGE)
    # new_key = EncryptionService.generate_new_key()
    # print(f"Replace your environment variable with:")
    # print(f"GATEWAY_ENCRYPTION_SECRET_KEY='{new_key}'")
    # mfas = await generic_service.fetch_data_from_collection(
    #     collection_key=CollectionKey.RBAC_ACTION.value,
    #     all_data=True,
    #     output_data_type=OutputDataType.DEFAULT.value,
    #     accept_language=DEFAULT_LANGUAGE,
    #     query={}
    # )
    # print(f"\n\n\n mfas : {len(mfas)}\n\n\n")


# async def async_context_manager():
#     """
#     Initialize the database and secure keys on application startup.
#     """
#     # Initialize secure keys directory
#     from app.keys.init_keys import initialize_keys
#     from app.keys.config_integration import update_settings_from_keys
#     from app.modules.core.configs.config import settings

#     # CALL TEST
#     # await test_gen_bde()

#     # Initialize keys directory
#     initialize_keys()

#     # Update settings with values from secure keys
#     update_settings_from_keys(settings)

#     # Initialize database
#     await init_db()

#     # Initialize database connection for services
#     from motor.motor_asyncio import AsyncIOMotorClient
#     client = AsyncIOMotorClient(settings.MONGO_URI)
#     db = client[settings.MONGO_DB_NAME]

#     # Initialize InstantViewService BEFORE starting monitoring
#     from app.modules.core.services.view.instant_view_service import InstantViewService
#     instant_view_service = await InstantViewService.initialize(db)
#     DebugService.app_debug_print("InstantViewService initialized", True)

#     # Create views on startup
#     await create_views()

#     # Start collection monitoring AFTER InstantViewService is initialized
#     monitoring_task = asyncio.create_task(monitor_new_collections(db))
#     DebugService.app_debug_print("Collection monitoring started", True)

#     # Initialize and start cron jobs
#     from app.modules.core.services.cron import init_cron_jobs
#     from app.modules.core.services.cron.cron_service import CronService

#     # Initialize cron jobs
#     init_cron_jobs()

#     # Start cron service in a background task
#     cron_task = asyncio.create_task(CronService.start())
#     DebugService.app_debug_print("Cron service started", True)

#     # Yield control back to FastAPI
#     yield  # This is where the app runs

#     # Stop services on shutdown
#     CronService.stop()
#     await cron_task
#     monitoring_task.cancel()  # Cancel monitoring task on shutdown



