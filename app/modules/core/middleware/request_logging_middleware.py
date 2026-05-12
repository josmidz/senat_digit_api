from fastapi import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.modules.core.utils.asgi_utils import (
    build_receive_with_cached_body,
    get_cached_body,
)


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        request_path = request.url.path

        if request_path.startswith("/api/v1/websocket/") or request_path.startswith("/api/v1/ng-websocket/"):
            await self.app(scope, receive, send)
            return

        print(f"\nRequest: {request.method} {request_path}")

        downstream_receive = receive
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                if "multipart/form-data" not in request.headers.get("content-type", ""):
                    body = await get_cached_body(scope, receive)
                    downstream_receive = build_receive_with_cached_body(scope)
                    try:
                        print(f"\n\n\nRequest body: {body.decode()}")
                    except UnicodeDecodeError:
                        print(f"Request contains binary data ({len(body)} bytes)")
            except Exception as exc:
                print(f"Error reading body: {exc}")

        await self.app(scope, downstream_receive, send)
