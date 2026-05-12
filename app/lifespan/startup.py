import asyncio



from motor.motor_asyncio import AsyncIOMotorClient
async def initialize_application():
    """Main startup function"""
    from app.modules.core.configs.config import settings
    from app.modules.core.services.debug.debug_service import DebugService
    from app.modules.core.services.sms.sms_service import SmsService
    
    resources = {
        "client": None,
        "db": None,
        "monitoring_task": None,
        "cron_task": None
    }
    
    DebugService.app_debug_print("Starting application initialization...", True)
    
    try:
        await initialize_keys_and_settings()
        await initialize_firebase()
        client, db = await initialize_database()
        resources["client"] = client
        resources["db"] = db
        DebugService.app_debug_print(f"Database client set: {client is not None}", True)

        await initialize_services(db)
        monitoring_task, cron_task = await start_background_tasks(db)
        resources["monitoring_task"] = monitoring_task
        resources["cron_task"] = cron_task
        
        DebugService.app_debug_print("Application startup completed successfully", True)
        DebugService.app_debug_print(f"Final resources: { {k: v is not None for k, v in resources.items()} }", True)
 

        return resources
        
    except Exception as e:
        DebugService.app_debug_print(f"Application startup failed: {e}", True)
        import traceback
        DebugService.app_debug_print(f"Startup traceback: {traceback.format_exc()}", True)
        # Clean up any partially created resources
        await cleanup_partial_resources(resources)
        raise
# async def initialize_application():
#     """Main startup function"""
#     from app.modules.core.configs.config import settings
#     from app.modules.core.services.debug.debug_service import DebugService
    
#     resources = {
#         "client": None,
#         "db": None,
#         "monitoring_task": None,
#         "cron_task": None
#     }
    
#     try:
#         await initialize_keys_and_settings()
#         client, db = await initialize_database()
#         resources["client"] = client
#         resources["db"] = db
        
#         await initialize_services(db)
#         monitoring_task, cron_task = await start_background_tasks(db)
#         resources["monitoring_task"] = monitoring_task
#         resources["cron_task"] = cron_task
        
#         DebugService.app_debug_print("Application startup completed successfully", True)
#         return resources
        
#     except Exception as e:
#         DebugService.app_debug_print(f"Application startup failed: {e}", True)
#         # Clean up any partially created resources
#         await cleanup_partial_resources(resources)
#         raise

async def cleanup_partial_resources(resources):
    """Clean up resources if startup fails partially"""
    from app.modules.core.services.debug.debug_service import DebugService
    
    try:
        if resources.get("client"):
            await resources["client"].close()
        if resources.get("monitoring_task"):
            resources["monitoring_task"].cancel()
        if resources.get("cron_task"):
            # You might need to handle this differently depending on CronService implementation
            pass
    except Exception as e:
        DebugService.app_debug_print(f"Error during partial cleanup: {e}", True)

async def initialize_keys_and_settings():
    """Initialize secure keys and update settings"""
    from app.keys.init_keys import initialize_keys
    from app.keys.config_integration import update_settings_from_keys
    from app.modules.core.configs.config import settings
    from app.modules.core.services.debug.debug_service import DebugService
    
    initialize_keys()
    update_settings_from_keys(settings)
    DebugService.app_debug_print("Keys and settings initialized", True)

async def initialize_database():
    """Initialize database connection and setup"""
    from app.modules.core.configs.config import settings
    from app.modules.core.services.debug.debug_service import DebugService
    from app.db.session import init_db
    from app.modules.core.utils.common.async_runner import GlobalDBSemaphore, AsyncExecutor
    
    # Initialize the global DB semaphore for concurrency control
    # This limits total concurrent DB operations across ALL requests
    GlobalDBSemaphore.init(max_concurrent=50)
    DebugService.app_debug_print("GlobalDBSemaphore initialized with max_concurrent=50", True)
    
    # Initialize thread/process pools for AsyncExecutor
    AsyncExecutor.init_pools(max_threads=50, max_processes=4)
    DebugService.app_debug_print("AsyncExecutor pools initialized", True)
    
    # Initialize database
    await init_db()
    
    # Create database connection with increased pool size
    client = AsyncIOMotorClient(
        settings.MONGO_URI,
        maxPoolSize=100,  # Increase connection pool
        minPoolSize=10,   # Keep some connections warm
        maxIdleTimeMS=30000,  # Close idle connections after 30s
        waitQueueTimeoutMS=10000,  # Wait up to 10s for connection
    )
    db = client[settings.MONGO_DB_NAME]
    
    DebugService.app_debug_print("Database initialized with maxPoolSize=100", True)
    return client, db

async def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    from app.modules.core.services.firebase.firebase_service import firebase_service
    from app.modules.core.services.debug.debug_service import DebugService

    try:
        # Initialize Firebase Admin SDK
        # It will use Application Default Credentials or GOOGLE_APPLICATION_CREDENTIALS env var
        firebase_service.initialize()
        DebugService.app_debug_print("Firebase Admin SDK initialized", True)
    except Exception as e:
        DebugService.app_debug_print(f"Warning: Firebase Admin SDK initialization failed: {e}", True)
        DebugService.app_debug_print("Google Sign-In will not work without Firebase Admin SDK", True)


async def initialize_services(db):
    """Initialize application services."""
    from app.modules.core.services.view.instant_view_service import InstantViewService
    from app.modules.core.services.debug.debug_service import DebugService
    from app.db.session import create_views

    instant_view_service = await InstantViewService.initialize(db)
    DebugService.app_debug_print("InstantViewService initialized", True)

    await create_views()
    DebugService.app_debug_print("Database views created", True)

    # Senat-Digit has no GPS-bound collections at MVP. Geospatial indexes for
    # bus_stop / launching_service / service_trip (SENAT_DIGIT) were removed in
    # the §3.4 restructure pass alongside the urban_transportation module.


async def start_background_tasks(db):
    """Start background tasks and cron jobs.

    Senat-Digit cron jobs (PV auto-export retries, audit chain verification,
    etc.) are added in §3.5 feature module work. The SENAT_DIGIT cron jobs
    (`auto_close_launching_services`, `auto_lock_reconciliation_snapshots`)
    were removed in the §3.4 restructure pass.
    """
    from app.modules.audit_security.services.audit_chain_verification_cron import (
        register_audit_chain_verification_cron,
    )
    from app.modules.core.services.cron.cron_service import CronService
    from app.modules.core.services.debug.debug_service import DebugService
    from app.db.session import monitor_new_collections

    monitoring_task = asyncio.create_task(monitor_new_collections(db))
    DebugService.app_debug_print("Collection monitoring started", True)

    # Senat-Digit cron jobs — registered before `CronService.start()` so
    # they're picked up on the first tick of the loop.
    # Per `_planning/_followup_batch.md` F7: walk the audit chain on a
    # fixed cadence and persist verification snapshots to
    # `OpsOrganizationLogModel`, so tampering is detected within one
    # interval instead of "next on-demand /verify call".
    register_audit_chain_verification_cron()

    cron_task = asyncio.create_task(CronService.start())
    DebugService.app_debug_print("Cron service started", True)

    return monitoring_task, cron_task
