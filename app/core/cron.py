"""
DEPRECATED: This module is deprecated and will be removed in a future version.
Please use app.modules.core.services.cron.cron_service instead.

This module now forwards all calls to CronService for backward compatibility.
"""

import logging
import asyncio
import functools
import warnings
from datetime import datetime
from typing import Dict, List, Callable, Awaitable, Optional, Any

from app.modules.core.services.cron.cron_service import CronService

logger = logging.getLogger(__name__)

# Show deprecation warning
warnings.warn(
    "CronScheduler is deprecated. Use CronService from app.modules.core.services.cron.cron_service instead.",
    DeprecationWarning,
    stacklevel=2
)

class CronScheduler:
    """
    DEPRECATED: Use CronService instead.
    
    This class now forwards all calls to CronService for backward compatibility.
    """
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
        self.task_loop = None
        self.running = False
        logger.warning("CronScheduler is deprecated. Use CronService instead.")

    async def start(self):
        """Start the scheduler loop (forwards to CronService)."""
        logger.warning("Using deprecated CronScheduler.start(). Use CronService.start() instead.")
        await CronService.start()
        self.running = True

    async def stop(self):
        """Stop the scheduler loop (forwards to CronService)."""
        logger.warning("Using deprecated CronScheduler.stop(). Use CronService.stop() instead.")
        CronService.stop()
        self.running = False

    def schedule_job(self, 
                    name: str, 
                    task_func: Callable[[], Awaitable[None]], 
                    interval_minutes: int = 5, 
                    run_immediately: bool = False):
        """Schedule a job (forwards to CronService)."""
        logger.warning("Using deprecated CronScheduler.schedule_job(). Use CronService.register_job() instead.")
        
        # Wrap the function to return a dict as required by CronService
        @functools.wraps(task_func)
        async def wrapper() -> Dict[str, Any]:
            try:
                result = await task_func()
                return {"status": "success", "result": result}
            except Exception as e:
                logger.error(f"Error in job {name}: {e}", exc_info=True)
                return {"status": "error", "error": str(e)}
        
        CronService.register_job(
            name=name,
            interval_seconds=interval_minutes * 60,
            callback=wrapper,
            enabled=True
        )
        
        self.tasks[name] = {
            "func": task_func,
            "interval_minutes": interval_minutes,
            "last_run": None if run_immediately else datetime.now()
        }

    def remove_job(self, name: str) -> bool:
        """Remove a scheduled job by name."""
        logger.warning("Using deprecated CronScheduler.remove_job(). Use CronService.disable_job() instead.")
        result = CronService.disable_job(name)
        
        if name in self.tasks:
            del self.tasks[name]
            
        return result

# Global scheduler instance that forwards to CronService
scheduler = CronScheduler()

def scheduled_job(name: str, interval_minutes: int = 5, run_immediately: bool = False):
    """
    DEPRECATED: Use CronService.scheduled_job instead.
    
    This decorator now forwards to CronService.scheduled_job for backward compatibility.
    
    Example:
        @scheduled_job(name="process_sms", interval_minutes=5)
        async def process_sms_messages():
            # Process SMS messages
    """
    logger.warning(
        f"Using deprecated @scheduled_job decorator for '{name}'. "
        f"Use @CronService.scheduled_job instead."
    )
    
    def decorator(func):
        if not asyncio.iscoroutinefunction(func):
            raise TypeError("Scheduled jobs must be async functions")
        
        # Forward to CronService
        CronService.scheduled_job(
            name=name, 
            interval_minutes=interval_minutes, 
            enabled=True
        )(func)
        
        # Also register with the legacy scheduler for backward compatibility
        scheduler.schedule_job(name, func, interval_minutes, run_immediately)
        return func
        
    return decorator