# app/middleware/ip_blocklist.py

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class IPBlocklistMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, blocklist: list):
        super().__init__(app)
        self.blocklist = blocklist

    async def dispatch(self, request: Request, call_next):
        if request.client.host in self.blocklist:
            raise HTTPException(status_code=403, detail="Forbidden")
        return await call_next(request)

# app.add_middleware(IPBlocklistMiddleware, blocklist=["192.168.0.1", "10.0.0.1"])

