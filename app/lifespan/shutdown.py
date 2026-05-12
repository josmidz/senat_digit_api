from .cron_utils import stop_cron_service
from .monitoring_utils import cancel_monitoring_task

async def shutdown_application(resources):
    """Main shutdown function"""
    from app.modules.core.services.debug.debug_service import DebugService
    
    try:
        await stop_cron_service(resources)
        await cancel_monitoring_task(resources)
        await close_database_connection(resources)
        DebugService.app_debug_print("Application shutdown completed", True)
    except Exception as e:
        DebugService.app_debug_print(f"Error during shutdown: {e}", True)


async def close_database_connection(resources):
    """Close database connection"""
    from app.modules.core.services.debug.debug_service import DebugService
    
    try:
        client = resources.get("client")
        
        if client is None:
            DebugService.app_debug_print("No database client to close (client is None)", True)
            return
            
        # Motor's close() method is synchronous, not async
        client.close()
        DebugService.app_debug_print("Database connection closed", True)
            
    except Exception as e:
        DebugService.app_debug_print(f"Error closing database connection: {e}", True)
        import traceback
        DebugService.app_debug_print(f"Traceback: {traceback.format_exc()}", True)