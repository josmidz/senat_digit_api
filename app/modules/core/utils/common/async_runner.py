import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Any, Callable, List, Optional, TypeVar, Coroutine

T = TypeVar('T')


class GlobalDBSemaphore:
    """
    Global semaphore to limit concurrent database operations across ALL requests.
    
    This prevents database connection pool exhaustion when multiple endpoints
    are called concurrently, each spawning many parallel DB queries.
    
    Usage:
        async with GlobalDBSemaphore.acquire():
            result = await db_operation()
    """
    _semaphore: Optional[asyncio.Semaphore] = None
    _max_concurrent: int = 50  # Max concurrent DB operations across all requests
    _active_count: int = 0
    _total_requests: int = 0
    _lock: Optional[asyncio.Lock] = None
    
    @classmethod
    def init(cls, max_concurrent: int = 50):
        """Initialize the global semaphore. Call once at app startup."""
        cls._max_concurrent = max_concurrent
        cls._semaphore = asyncio.Semaphore(max_concurrent)
        cls._lock = asyncio.Lock()
        print(f"[GlobalDBSemaphore] Initialized with max_concurrent={max_concurrent}")
    
    @classmethod
    async def acquire(cls):
        """Context manager for acquiring the semaphore."""
        if cls._semaphore is None:
            cls.init()
        return cls._semaphore
    
    @classmethod
    async def execute(cls, coro: Coroutine[Any, Any, T]) -> T:
        """Execute a coroutine with semaphore protection."""
        if cls._semaphore is None:
            cls.init()
        
        async with cls._semaphore:
            cls._active_count += 1
            cls._total_requests += 1
            try:
                return await coro
            finally:
                cls._active_count -= 1
    
    @classmethod
    def get_stats(cls) -> dict:
        """Get current semaphore statistics."""
        return {
            "max_concurrent": cls._max_concurrent,
            "active_count": cls._active_count,
            "total_requests": cls._total_requests,
            "available_slots": cls._max_concurrent - cls._active_count if cls._semaphore else cls._max_concurrent
        }


class AsyncExecutor:
    """
    AsyncExecutor
    =============
    A unified helper to safely run blocking functions in asyncio apps (e.g., FastAPI).

    Provides:
      - run_in_thread(): Run blocking I/O-bound work in a thread pool.
      - run_in_process(): Run CPU-bound heavy work in a process pool.
      - run_fire_and_forget(): Schedule a coroutine as fire-and-forget using asyncio.create_task.
      - gather(): Run multiple coroutines in parallel with error handling.
      - gather_with_limit(): Run coroutines with concurrency limit (semaphore).
      - gather_db(): Run DB coroutines with GLOBAL semaphore protection.

    Initialization (at app startup)
    --------------------------------
    ```python
    from fastapi import FastAPI
    from utils.async_executor import AsyncExecutor

    app = FastAPI()

    @app.on_event("startup")
    async def startup_event():
        AsyncExecutor.init_pools(max_threads=50, max_processes=4)
    ```

    Examples
    --------
    CPU-bound:
    ```python
    hashed = await AsyncExecutor.run_in_process(PasswordService.hash_password, "mypassword")
    ```

    I/O-bound:
    ```python
    result = await AsyncExecutor.run_in_thread(mongo_client.db.users.find_one, {"_id": some_id})
    ```

    Parallel coroutines:
    ```python
    # Simple parallel execution
    results = await AsyncExecutor.gather([
        fetch_user(user_id),
        fetch_orders(user_id),
        fetch_notifications(user_id)
    ])

    # With concurrency limit (max 10 concurrent tasks)
    results = await AsyncExecutor.gather_with_limit(
        [process_item(item) for item in items],
        limit=10
    )

    # Format multiple documents in parallel
    formatted = await AsyncExecutor.gather([
        doc.format(output_type) for doc in documents
    ])
    ```

    Background (fire-and-forget):
    ```python
    @app.post("/send-email")
    async def send_email(email: str):
        AsyncExecutor.run_fire_and_forget(
            email_service.send_simple_email_background,
            email,
            "Hello"
        )
        return {"status": "scheduled"}
    ```
    """

    _thread_pool: Optional[ThreadPoolExecutor] = None
    _process_pool: Optional[ProcessPoolExecutor] = None

    @classmethod
    def init_pools(cls, max_threads: int = 20, max_processes: Optional[int] = None):
        """Initialize thread and process pools. Call once at app startup."""
        if cls._thread_pool is None:
            cls._thread_pool = ThreadPoolExecutor(max_workers=max_threads)
        if cls._process_pool is None:
            cls._process_pool = ProcessPoolExecutor(max_workers=max_processes)

    @classmethod
    async def run_in_thread(cls, func: Callable, *args, **kwargs) -> Any:
        """Run I/O-bound blocking code in a thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            cls._thread_pool, lambda: func(*args, **kwargs)
        )

    @classmethod
    async def run_in_process(cls, func: Callable, *args, **kwargs) -> Any:
        """Run CPU-bound heavy code in a process pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            cls._process_pool, lambda: func(*args, **kwargs)
        )

    @classmethod
    def run_fire_and_forget(cls, func: Callable, *args, **kwargs):
        """
        Schedule a coroutine as fire-and-forget using asyncio.create_task.
        """
        asyncio.create_task(func(*args, **kwargs))

    @classmethod
    async def gather(
        cls,
        coroutines: List[Coroutine[Any, Any, T]],
        return_exceptions: bool = False
    ) -> List[T]:
        """
        Run multiple coroutines in parallel using asyncio.gather.
        
        This is a convenience wrapper that provides:
        - Empty list handling
        - Optional exception capture
        - Type hints for better IDE support
        
        Args:
            coroutines: List of coroutines to execute in parallel
            return_exceptions: If True, exceptions are returned as results instead of raised
            
        Returns:
            List of results in the same order as input coroutines
            
        Example:
            ```python
            # Format multiple documents in parallel
            formatted_docs = await AsyncExecutor.gather([
                doc.get_formated_data(language) for doc in documents
            ])
            
            # Fetch multiple related resources
            user, orders, settings = await AsyncExecutor.gather([
                fetch_user(user_id),
                fetch_orders(user_id),
                fetch_settings(user_id)
            ])
            ```
        """
        if not coroutines:
            return []
        
        return list(await asyncio.gather(*coroutines, return_exceptions=return_exceptions))

    @classmethod
    async def gather_with_limit(
        cls,
        coroutines: List[Coroutine[Any, Any, T]],
        limit: int = 10,
        return_exceptions: bool = False
    ) -> List[T]:
        """
        Run multiple coroutines in parallel with a concurrency limit.
        
        Uses a semaphore to limit the number of concurrent tasks.
        Useful when you have many tasks but want to avoid overwhelming
        the database or external services.
        
        Args:
            coroutines: List of coroutines to execute
            limit: Maximum number of concurrent tasks (default: 10)
            return_exceptions: If True, exceptions are returned as results
            
        Returns:
            List of results in the same order as input coroutines
            
        Example:
            ```python
            # Process 100 items with max 10 concurrent DB calls
            results = await AsyncExecutor.gather_with_limit(
                [process_item(item) for item in items],
                limit=10
            )
            ```
        """
        if not coroutines:
            return []
        
        semaphore = asyncio.Semaphore(limit)
        
        async def limited_coro(coro: Coroutine[Any, Any, T]) -> T:
            async with semaphore:
                return await coro
        
        limited_coroutines = [limited_coro(coro) for coro in coroutines]
        return list(await asyncio.gather(*limited_coroutines, return_exceptions=return_exceptions))

    @classmethod
    async def gather_db(
        cls,
        coroutines: List[Coroutine[Any, Any, T]],
        return_exceptions: bool = False
    ) -> List[T]:
        """
        Run multiple database coroutines with GLOBAL semaphore protection.
        
        This is the KEY method for preventing blocking across concurrent requests.
        It uses a global semaphore that limits total concurrent DB operations
        across ALL requests, not just within a single request.
        
        Use this for ALL database operations that run in parallel.
        
        Args:
            coroutines: List of DB coroutines to execute
            return_exceptions: If True, exceptions are returned as results
            
        Returns:
            List of results in the same order as input coroutines
            
        Example:
            ```python
            # These will be globally rate-limited across all concurrent requests
            results = await AsyncExecutor.gather_db([
                fetch_user(user_id),
                fetch_orders(user_id),
                fetch_settings(user_id)
            ])
            ```
        """
        if not coroutines:
            return []
        
        # Each coroutine acquires the global semaphore
        async def db_coro(coro: Coroutine[Any, Any, T]) -> T:
            return await GlobalDBSemaphore.execute(coro)
        
        protected_coroutines = [db_coro(coro) for coro in coroutines]
        return list(await asyncio.gather(*protected_coroutines, return_exceptions=return_exceptions))

    @classmethod
    async def gather_dict(
        cls,
        coroutines_dict: dict[str, Coroutine[Any, Any, Any]],
        return_exceptions: bool = False
    ) -> dict[str, Any]:
        """
        Run multiple coroutines in parallel and return results as a dictionary.
        
        Useful when you need to fetch multiple named resources.
        
        Args:
            coroutines_dict: Dictionary mapping keys to coroutines
            return_exceptions: If True, exceptions are returned as values
            
        Returns:
            Dictionary with same keys, values are coroutine results
            
        Example:
            ```python
            data = await AsyncExecutor.gather_dict({
                'user': fetch_user(user_id),
                'profile': fetch_profile(user_id),
                'settings': fetch_settings(user_id)
            })
            # Access: data['user'], data['profile'], data['settings']
            ```
        """
        if not coroutines_dict:
            return {}
        
        keys = list(coroutines_dict.keys())
        coroutines = list(coroutines_dict.values())
        
        results = await asyncio.gather(*coroutines, return_exceptions=return_exceptions)
        
        return dict(zip(keys, results))
