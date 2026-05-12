async def stop_cron_service(resources):
    """Stop cron service"""
    from app.modules.core.services.cron.cron_service import CronService
    from app.modules.core.services.debug.debug_service import DebugService
    
    try:
        CronService.stop()
        if resources.get("cron_task"):
            await resources["cron_task"]
        DebugService.app_debug_print("Cron service stopped", True)
    except Exception as e:
        DebugService.app_debug_print(f"Error stopping cron service: {e}", True)