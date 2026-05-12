
from fastapi import APIRouter, Body, Request
from typing import Dict, Any
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.security.api.controller.security_websocket_service_controller import SecurityWebsocketServiceController

router = APIRouter()

@router.post("/send-event/{user_account_socket_hash}")
async def send_event_to_client(
    request:Request,
    user_account_socket_hash: str, 
    data: Dict[str, Any],
    
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    websocket_service_controller = SecurityWebsocketServiceController(accept_language)
    return await websocket_service_controller.send_event_to_client(request=request,user_account_socket_hash=user_account_socket_hash,data=data)
 
@router.post("/send-unlock-screen")
async def send_unlock_event_to_client(
    request: Request,
    data: dict = Body(...),
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    websocket_service_controller = SecurityWebsocketServiceController(accept_language)
    return await websocket_service_controller.send_unlock_event_to_client(request=request,data=data)
 
 
@router.post("/get-unlock-screen-result")
async def get_unlock_event_result(
    request: Request,
    data: dict = Body(...),
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    websocket_service_controller = SecurityWebsocketServiceController(accept_language)
    return await websocket_service_controller.get_unlock_event_result(request=request,data=data)
 
 
@router.get("/reload-sudo-action")
async def reload_sudo_action_result(
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    websocket_service_controller = SecurityWebsocketServiceController(accept_language)
    return await websocket_service_controller.reload_sudo_action_result(request=request)
 

@router.get("/connection-status/{user_account_socket_hash}")
async def get_connection_status(
    request: Request,
    user_account_socket_hash: str,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    websocket_service_controller = SecurityWebsocketServiceController(accept_language)
    return await websocket_service_controller.get_connection_status(request=request,user_account_socket_hash=user_account_socket_hash)
 