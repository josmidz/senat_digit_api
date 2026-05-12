# app/middleware/rate_limiter.py

import time
import redis.asyncio as redis  # Use redis.asyncio instead of aioredis
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.modules.core.configs.config import settings
import os

# Connect to Redis with password
redis_url = settings.REDIS_URL.format(REDIS_PASSWORD=os.getenv('REDIS_PASSWORD', ''))
redis_client = redis.Redis.from_url(redis_url)

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate_limit: int, period: int):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.period = period

    async def dispatch(self, request: Request, call_next):
        # Exclude `/openapi.json` from rate limiting
        if request.url.path == "/openapi.json":
            return await call_next(request)
        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"
        current_time = int(time.time())

        # Use Redis to manage rate limiting
        request_count = await redis_client.zcount(key, current_time - self.period, current_time)
        if request_count >= self.rate_limit:
            return JSONResponse({"detail": "Too many requests"}, status_code=429)

        # Record request timestamp and set expiration
        await redis_client.zadd(key, {current_time: current_time})
        await redis_client.expire(key, self.period)

        return await call_next(request)
