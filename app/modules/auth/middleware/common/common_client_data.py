import logging
from fastapi import Request, HTTPException
from starlette.types import ASGIApp, Receive, Scope, Send
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.services.device.device_service import DeviceService
from app.modules.core.services.debug.debug_service import DebugService


class CommonClientDataMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        # Skip processing for WebSocket connections but allow them to pass through
        if request.url.path.startswith("/api/v1/websocket/") or request.url.path.startswith("/api/v1/ng-websocket/"):
            DebugService.app_debug_print(f"CommonClientDataMiddleware: Skipping for WebSocket route: {request.url.path}", True)
            await self.app(scope, receive, send)
            return

        try:
            # Extract headers
            accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
            DebugService.app_debug_print(f"Accept-Language from header: {accept_language}")
            request.state.acceptLanguage = accept_language
            
            # Extract ip address
            ip_address = DeviceService.get_real_ip_address(request)
            request.state.ipAddress = ip_address
            
            
            # Get the hashed device ID from the request
            device_hashed_id = await DeviceService.get_hashed_device_id(request)
            request.state.deviceHashedId = device_hashed_id
            
            
            # USER DEVICE
            if device_hashed_id:
                device_service = DeviceService(accept_language=accept_language)
                user_device_info = await device_service.device_info_from_hashed_id(device_hashed_id=device_hashed_id)
                if user_device_info:
                    request.state.userDeviceInfo = user_device_info

            # USER DEVICES
            if device_hashed_id:
                device_service = DeviceService(accept_language=accept_language)
                request.state.listOfUserDevices = await device_service.devices_list_from_hashed_id(device_hashed_id=device_hashed_id)
            
            # DEVICE INFO
            device_info = await DeviceService.get_device_info(request=request)
            if device_info: 
                request.state.deviceInfo = device_info
            
            # LOCAL INFO
            location_info = await DeviceService.get_location_from_ip_secure(request)
            if location_info:
                request.state.locationInfo = location_info


            
            # Preprocessing
            await self.app(scope, receive, send)
            return
        except HTTPException as http_exception:
            DebugService.app_debug_print(f"\n common client data exception {http_exception}  \n",)
            await self.app(scope, receive, send)
