# app/middleware/ip_whitelist.py

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List

class IPWhitelistMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, whitelist: List[str]):
        super().__init__(app)
        self.whitelist = whitelist

    async def dispatch(self, request: Request, call_next):
        if request.client.host not in self.whitelist:
            raise HTTPException(status_code=403, detail="Access forbidden: IP not in whitelist")
        return await call_next(request)
