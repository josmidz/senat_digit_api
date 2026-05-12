async def cancel_monitoring_task(resources):
    """Cancel monitoring task"""
    from app.modules.core.services.debug.debug_service import DebugService
    
    try:
        if resources.get("monitoring_task"):
            resources["monitoring_task"].cancel()
        DebugService.app_debug_print("Monitoring task cancelled", True)
    except Exception as e:
        DebugService.app_debug_print(f"Error cancelling monitoring task: {e}", True)