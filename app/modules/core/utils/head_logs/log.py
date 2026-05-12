from fastapi import FastAPI, Request
import os
from starlette.types import ASGIApp, Receive, Scope, Send


class LogRequestHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        # Log the headers in local env
        if os.getenv("ENV") == "local" or os.getenv("ENV") == "testing" or os.getenv("ENV") == "stage":
            print(f"Headers: {request.headers}")
        # Pass the request to the next middleware or route
        await self.app(scope, receive, send)
