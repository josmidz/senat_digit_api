"""
CronService — lightweight async scheduler.

Register jobs via ``CronService.register_job()`` then call
``await CronService.start()`` inside the FastAPI lifespan startup.
The loop ticks every second and fires registered callbacks once
their interval elapses.
"""

import asyncio
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

from app.modules.core.services.debug.debug_service import DebugService

logger = logging.getLogger(__name__)


class _Job:
    __slots__ = ("name", "interval_seconds", "callback", "enabled", "last_run")

    def __init__(
        self,
        name: str,
        interval_seconds: int,
        callback: Callable[[], Awaitable[Dict[str, Any]]],
        enabled: bool = True,
    ):
        self.name = name
        self.interval_seconds = interval_seconds
        self.callback = callback
        self.enabled = enabled
        self.last_run: Optional[datetime] = None


class CronService:
    """Singleton-style async cron scheduler (class-level state)."""

    _jobs: Dict[str, _Job] = {}
    _running: bool = False
    _task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    @classmethod
    def register_job(
        cls,
        name: str,
        interval_seconds: int,
        callback: Callable[[], Awaitable[Dict[str, Any]]],
        enabled: bool = True,
    ) -> None:
        """Register (or replace) a named job."""
        cls._jobs[name] = _Job(
            name=name,
            interval_seconds=interval_seconds,
            callback=callback,
            enabled=enabled,
        )
        DebugService.app_debug_print(
            f"[CronService] Registered job '{name}' every {interval_seconds}s (enabled={enabled})",
            True,
        )

    @classmethod
    async def start(cls) -> None:
        """Run the scheduler loop until ``stop()`` is called."""
        if cls._running:
            return
        cls._running = True
        DebugService.app_debug_print("[CronService] Starting scheduler loop …", True)
        try:
            while cls._running:
                now = datetime.now(timezone.utc)
                for job in list(cls._jobs.values()):
                    if not job.enabled:
                        continue
                    if job.last_run is None or (now - job.last_run).total_seconds() >= job.interval_seconds:
                        job.last_run = now
                        try:
                            result = await job.callback()
                            DebugService.app_debug_print(
                                f"[CronService] Job '{job.name}' completed: {result}",
                                True,
                            )
                        except Exception as exc:
                            logger.error(f"[CronService] Job '{job.name}' failed: {exc}")
                            DebugService.app_debug_print(
                                f"[CronService] Job '{job.name}' error: {traceback.format_exc()}",
                                True,
                            )
                await asyncio.sleep(1)
        finally:
            cls._running = False
            DebugService.app_debug_print("[CronService] Scheduler loop stopped", True)

    @classmethod
    def stop(cls) -> None:
        """Signal the scheduler loop to exit."""
        cls._running = False
        DebugService.app_debug_print("[CronService] Stop requested", True)
