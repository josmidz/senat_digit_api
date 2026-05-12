from fastapi import APIRouter, WebSocket, Request
from typing import Any, Dict
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.security.api.controller.security_websocket_controller import SecurityWebsocketController

router = APIRouter()


# Debug endpoint to check if HTTP requests are reaching this route
@router.get("/ws")
async def websocket_debug_endpoint(request: Request):
    print(f"HTTP GET request received at WebSocket endpoint - Headers: {dict(request.headers)}")
    print(f"HTTP GET request received at WebSocket endpoint - Query params: {dict(request.query_params)}")
    return {"error": "This is a WebSocket endpoint. Use WebSocket protocol to connect.", "method": "GET", "path": "/ws"}

# get user_account_socket_hash as param
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print(f"WebSocket endpoint called - Headers: {dict(websocket.headers)}")
    print(f"WebSocket endpoint called - Query params: {dict(websocket.query_params)}")
    accept_language = websocket.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    websocket_controller = SecurityWebsocketController(accept_language)
    return await websocket_controller.websocket_endpoint(websocket=websocket)
 
@router.post("/push-notification")
async def push_notification(request:Request,user_id: str, notification: dict):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    websocket_controller = SecurityWebsocketController(accept_language)
    return await websocket_controller.push_notification(request=request,user_id=user_id,notification=notification)
  
  

@router.get("/pending-notifications")
async def get_pending_notifications(request:Request, consume: bool = False):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    websocket_controller = SecurityWebsocketController(accept_language)
    return await websocket_controller.get_pending_notifications(request=request, consume=consume)
 


@router.get("/send-pong")
async def send_pong(request:Request):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    websocket_controller = SecurityWebsocketController(accept_language)
    return await websocket_controller.send_pong(request=request)

@router.post("/send-action")
async def send_action(request:Request,data: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    websocket_controller = SecurityWebsocketController(accept_language)
    return await websocket_controller.send_action(request=request,data=data)
    
    
    
