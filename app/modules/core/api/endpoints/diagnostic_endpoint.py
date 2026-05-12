"""
SERVER-SIDE BLOCKING DIAGNOSTIC
================================
This module adds diagnostic endpoints to trace blocking issues.
Add this to your router to debug concurrent request handling.

Usage:
1. Import and include the router in your main app
2. Call /api/v1/diagnostic/concurrent-test to diagnose blocking
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi import status

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.application.application_service import ApplicationService
from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.types.response import CustomJSONResponse
from app.modules.core.utils.common.async_runner import AsyncExecutor


router = APIRouter(prefix="/diagnostic", tags=["Diagnostic"])


class BlockingDiagnosticService:
    """Service to diagnose blocking issues in async code."""

    @staticmethod
    async def timed_operation(name: str, coro) -> Dict[str, Any]:
        """Execute a coroutine and measure its time."""
        start = time.perf_counter()
        try:
            result = await coro
            duration_ms = (time.perf_counter() - start) * 1000
            return {
                "name": name,
                "duration_ms": round(duration_ms, 2),
                "success": True,
                "result_count": len(result) if isinstance(result, list) else 1 if result else 0
            }
        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            return {
                "name": name,
                "duration_ms": round(duration_ms, 2),
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def diagnose_concurrent_requests(
        request: Request,
        accept_language: str = DEFAULT_LANGUAGE
    ) -> Dict[str, Any]:
        """
        Diagnose blocking by running withdrawal-demands and menu fetch concurrently.
        """
        results = {
            "test_time": datetime.now().isoformat(),
            "isolated_tests": [],
            "concurrent_test": {},
            "diagnosis": []
        }

        # Get auth info first
        try:
            user_details = await AuthenticatedService.get_user_info(request, accept_language)
            api_consumer = await AuthenticatedService.get_api_consumer(request, accept_language)
            user_profil = await AuthenticatedService.get_user_profil(request, accept_language)
        except Exception as e:
            return {"error": f"Auth failed: {str(e)}"}

        generic_service = GenericService(accept_language)

        # ========== TEST 1: Isolated withdrawal-demands ==========
        DebugService.app_debug_print("🔬 DIAGNOSTIC: Testing isolated withdrawal-demands...", True)
        
        async def fetch_withdrawal_demands():
            """Simulate the withdrawal demands fetch."""
            data = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.OPS_EWALLET_WIDTHDRAWAL,
                all_data=True,
                page=0,
                limit=50,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=accept_language,
                query={},
                user=user_details,
                sort={'created_at': -1}
            )
            return data

        isolated_withdrawal_result = await BlockingDiagnosticService.timed_operation(
            "withdrawal-demands (isolated)",
            fetch_withdrawal_demands()
        )
        results["isolated_tests"].append(isolated_withdrawal_result)

        # Small delay
        await asyncio.sleep(0.1)

        # ========== TEST 2: Isolated menu-submenus ==========
        DebugService.app_debug_print("🔬 DIAGNOSTIC: Testing isolated menu-submenus...", True)
        
        # Use a test menu ID - you may need to adjust this
        test_menu_id = "692c06feacd2f0a1bada9715"  # From user's example
        
        async def fetch_menu_submenus():
            """Simulate the menu submenus fetch."""
            return await ApplicationService.get_user_menu_submenus(
                sys_menu_id=test_menu_id,
                apiConsumer=api_consumer,
                user=user_details,
                userProfil=user_profil,
                page=0,
                limit=50,
                all_data=True,
                accept_language=accept_language,
                output_data_type=OutputDataType.DATA_TABLE.value,
            )

        isolated_menu_result = await BlockingDiagnosticService.timed_operation(
            "menu-submenus (isolated)",
            fetch_menu_submenus()
        )
        results["isolated_tests"].append(isolated_menu_result)

        # Small delay
        await asyncio.sleep(0.1)

        # ========== TEST 3: CONCURRENT - THE CRITICAL TEST ==========
        DebugService.app_debug_print("🔬 DIAGNOSTIC: Testing CONCURRENT requests...", True)
        
        concurrent_start = time.perf_counter()
        
        # Use AsyncExecutor.gather for truly parallel execution
        concurrent_results = await AsyncExecutor.gather([
            BlockingDiagnosticService.timed_operation(
                "withdrawal-demands (concurrent)",
                fetch_withdrawal_demands()
            ),
            BlockingDiagnosticService.timed_operation(
                "menu-submenus (concurrent)",
                fetch_menu_submenus()
            )
        ])
        
        concurrent_total_time = round((time.perf_counter() - concurrent_start) * 1000, 2)
        
        results["concurrent_test"] = {
            "total_time_ms": concurrent_total_time,
            "individual_results": concurrent_results,
            "max_individual_time_ms": max(r["duration_ms"] for r in concurrent_results if r["success"])
        }

        # ========== DIAGNOSIS ==========
        isolated_withdrawal_time = isolated_withdrawal_result["duration_ms"]
        isolated_menu_time = isolated_menu_result["duration_ms"]
        concurrent_withdrawal = next((r for r in concurrent_results if "withdrawal" in r["name"]), {})
        concurrent_menu = next((r for r in concurrent_results if "menu" in r["name"]), {})

        # Check for blocking patterns
        if concurrent_withdrawal.get("duration_ms", 0) > isolated_withdrawal_time * 2:
            results["diagnosis"].append({
                "issue": "WITHDRAWAL_SLOWDOWN",
                "message": f"Withdrawal demands took {concurrent_withdrawal['duration_ms']}ms concurrent vs {isolated_withdrawal_time}ms isolated - {concurrent_withdrawal['duration_ms']/isolated_withdrawal_time:.1f}x slower",
                "severity": "HIGH"
            })

        if concurrent_menu.get("duration_ms", 0) > isolated_menu_time * 2:
            results["diagnosis"].append({
                "issue": "MENU_SLOWDOWN", 
                "message": f"Menu submenus took {concurrent_menu['duration_ms']}ms concurrent vs {isolated_menu_time}ms isolated - {concurrent_menu['duration_ms']/isolated_menu_time:.1f}x slower",
                "severity": "HIGH"
            })

        expected_parallel_time = max(isolated_withdrawal_time, isolated_menu_time)
        actual_time = concurrent_total_time
        
        if actual_time > expected_parallel_time * 1.5:
            results["diagnosis"].append({
                "issue": "SEQUENTIAL_EXECUTION",
                "message": f"Total time {actual_time}ms is much higher than expected parallel time {expected_parallel_time}ms - suggests sequential execution",
                "severity": "CRITICAL"
            })
        else:
            results["diagnosis"].append({
                "issue": "PARALLEL_OK",
                "message": f"Total time {actual_time}ms is close to expected parallel time {expected_parallel_time}ms - parallel execution working",
                "severity": "INFO"
            })

        return results


@router.get("/concurrent-test")
async def diagnose_concurrent_blocking(
    request: Request,
):
    """
    Diagnose blocking issues when withdrawal-demands and menu-submenus
    are fetched concurrently.
    """
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    
    try:
        results = await BlockingDiagnosticService.diagnose_concurrent_requests(
            request=request,
            accept_language=accept_language
        )
        
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Diagnostic completed",
                "data": results
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db-pool-test")
async def diagnose_db_pool(
    request: Request,
    concurrent_requests: int = Query(10, description="Number of concurrent requests")
):
    """
    Test database connection pool by making multiple concurrent queries.
    """
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    generic_service = GenericService(accept_language)
    
    async def simple_db_query(i: int):
        """Simple DB query to test pool."""
        start = time.perf_counter()
        try:
            result = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.OPS_EWALLET_WIDTHDRAWAL,
                all_data=False,
                page=0,
                limit=1,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=accept_language,
                query={},
            )
            duration = (time.perf_counter() - start) * 1000
            return {"id": i, "duration_ms": round(duration, 2), "success": True}
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return {"id": i, "duration_ms": round(duration, 2), "success": False, "error": str(e)}
    
    start_total = time.perf_counter()
    results = await AsyncExecutor.gather([
        simple_db_query(i) for i in range(concurrent_requests)
    ])
    total_time = round((time.perf_counter() - start_total) * 1000, 2)
    
    times = [r["duration_ms"] for r in results if r["success"]]
    
    return CustomJSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status_code": status.HTTP_200_OK,
            "message": "DB pool test completed",
            "data": {
                "total_time_ms": total_time,
                "concurrent_requests": concurrent_requests,
                "avg_time_ms": round(sum(times) / len(times), 2) if times else 0,
                "min_time_ms": min(times) if times else 0,
                "max_time_ms": max(times) if times else 0,
                "spread_ms": round(max(times) - min(times), 2) if times else 0,
                "individual_results": results,
                "analysis": {
                    "pool_healthy": max(times) < sum(times)/len(times) * 3 if times else False,
                    "note": "High spread indicates connection pool contention" if times and (max(times) - min(times)) > sum(times)/len(times) else "Pool looks healthy"
                }
            }
        }
    )


@router.get("/event-loop-test")
async def diagnose_event_loop(request: Request):
    """
    Test if the event loop is being blocked by CPU-bound work.
    """
    results = []
    
    # Test 1: Pure async tasks
    async def async_sleep_task(i: int, duration: float):
        start = time.perf_counter()
        await asyncio.sleep(duration)
        return {"id": i, "actual_ms": round((time.perf_counter() - start) * 1000, 2), "expected_ms": duration * 1000}
    
    start = time.perf_counter()
    sleep_results = await AsyncExecutor.gather([
        async_sleep_task(i, 0.1) for i in range(10)
    ])
    total_sleep_time = round((time.perf_counter() - start) * 1000, 2)
    
    results.append({
        "test": "async_sleep",
        "expected_total_ms": 100,  # All should run in parallel
        "actual_total_ms": total_sleep_time,
        "blocked": total_sleep_time > 200,  # More than 2x expected = blocked
        "individual_results": sleep_results
    })
    
    # Test 2: Check if event loop is blocked
    async def check_loop_responsiveness():
        """Check how long it takes to yield to event loop."""
        times = []
        for _ in range(100):
            start = time.perf_counter()
            await asyncio.sleep(0)  # Yield to event loop
            times.append((time.perf_counter() - start) * 1000)
        return {
            "avg_yield_ms": round(sum(times) / len(times), 4),
            "max_yield_ms": round(max(times), 4),
            "min_yield_ms": round(min(times), 4)
        }
    
    loop_results = await check_loop_responsiveness()
    results.append({
        "test": "event_loop_responsiveness",
        **loop_results,
        "healthy": loop_results["max_yield_ms"] < 10
    })
    
    return CustomJSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status_code": status.HTTP_200_OK,
            "message": "Event loop test completed",
            "data": results
        }
    )


@router.get("/semaphore-status")
async def get_semaphore_status():
    """
    Get the current status of the GlobalDBSemaphore.
    
    This shows how many concurrent DB operations are allowed,
    how many are currently active, and how many slots are available.
    
    Use this to monitor DB operation contention in real-time.
    """
    from app.modules.core.utils.common.async_runner import GlobalDBSemaphore
    
    stats = GlobalDBSemaphore.get_stats()
    
    return CustomJSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status_code": status.HTTP_200_OK,
            "message": "GlobalDBSemaphore status",
            "data": {
                **stats,
                "utilization_percent": round((stats["active_count"] / stats["max_concurrent"]) * 100, 2) if stats["max_concurrent"] > 0 else 0,
                "is_saturated": stats["available_slots"] == 0
            }
        }
    )
