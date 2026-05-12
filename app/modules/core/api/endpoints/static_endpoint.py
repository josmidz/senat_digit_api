
#app/api/v1/endpoints/static.py

from typing import Any, Dict, Optional
from app.modules.core.api.controller.static_controller import StaticController
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from fastapi import APIRouter, BackgroundTasks, Query, Request
from app.modules.core.schemas.user_schema import UserConfigPayload
from app.modules.core.enums.type_enum import OutputDataType
 
router = APIRouter()

@router.get("/fetch-consumer-key")
async def fetch_encrypted_consumer_key(request: Request):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_encrypted_consumer_key(request=request)
   
@router.get("/data/get-entity-config")
async def fetch_menu_configs(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_menu_configs(request=request,output_data_type=output_data_type,endpoint_call=endpoint_call)
      
@router.get("/data/get-menus")
async def fetch_menus(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_menus(request=request,output_data_type=output_data_type,endpoint_call=endpoint_call)
 
    
@router.get("/data/get-applications")
async def fetch_formated_applications(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call"),
    sse_key: Optional[str] = Query(None, description="SSE tracking key for real-time progress"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(20, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_formated_applications(request=request,output_data_type=output_data_type,endpoint_call=endpoint_call,sse_key=sse_key,all_data=all_data,page=page,limit=limit)


@router.get("/data/get-applications/sse")
async def stream_formated_applications_sse(
    request: Request,
    sse_key: str = Query(..., description="SSE tracking key shared with applications fetch call"),
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.stream_applications_sse(
        request=request,
        sse_key=sse_key,
    )


@router.get("/data/get-senat-digit-applications")
async def fetch_senat_digit_app_formated_applications(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call"),
    sse_key: Optional[str] = Query(None, description="SSE tracking key for real-time progress"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(20, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_senat_digit_app_formated_applications(request=request,output_data_type=output_data_type,endpoint_call=endpoint_call,sse_key=sse_key,all_data=all_data,page=page,limit=limit)


@router.get("/data/get-senat-digit-applications/sse")
async def stream_senat_digit_app_formated_applications_sse(
    request: Request,
    sse_key: str = Query(..., description="SSE tracking key shared with applications fetch call"),
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.stream_senat_digit_applications_sse(
        request=request,
        sse_key=sse_key,
    )


@router.get("/data/get-agent-applications")
async def fetch_agent_app_formated_applications(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(20, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_agent_app_formated_applications(request=request,output_data_type=output_data_type,endpoint_call=endpoint_call,all_data=all_data,page=page,limit=limit)


@router.get("/data/get-application-groups")
async def fetch_formated_application_groups(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
): 
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_formated_application_groups(request=request,output_data_type=output_data_type,endpoint_call=endpoint_call,all_data=all_data,page=page,limit=limit)
 

@router.get("/data/get-application-user-submenus")
async def fetch_formated_application_user_sub_menus(
    request: Request, 
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(25, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_formated_application_user_sub_menus(request=request,output_data_type=output_data_type,endpoint_call=endpoint_call,all_data=all_data,page=page,limit=limit)
  
 

@router.get("/data/get-menu-user-sub-menus")
async def fetch_formated_menu_user_sub_menus(
    request: Request, 
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(25, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_formated_menu_user_sub_menus(request=request,output_data_type=output_data_type,endpoint_call=endpoint_call,all_data=all_data,page=page,limit=limit)
  
 
    
@router.get("/data/get-roles")
async def fetch_formated_organization_roles(
    request: Request,
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(20, description="Number of items per page"),
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_formated_organization_roles(request=request,all_data=all_data,page=page,limit=limit,output_data_type=output_data_type,endpoint_call=endpoint_call)
 
 
 
@router.get("/data/get-api-consumer-profiles")
async def fetch_api_consumer_profiles(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_api_consumer_profiles(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
 
@router.get("/data/get-standalone-menus")
async def fetch_standalone_menus(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_standalone_menus(request=request,output_data_type=output_data_type,endpoint_call=endpoint_call)
 
@router.get("/data/get-notifications")
async def fetch_notifications(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_notifications(request=request,all_data=all_data,page=page,limit=limit,output_data_type=output_data_type,endpoint_call=endpoint_call)


@router.post("/data/mark-all-notifications-read")
async def mark_all_notifications_read(request: Request):
    """Mark every NTF_NOTIFICATION targeted to the calling user as read.

    Returns ``{ updated: N }`` — the number of rows flipped from
    ``is_read=false`` to ``is_read=true``. Idempotent: a no-op when
    nothing was unread.
    """
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.mark_all_notifications_read(request=request)


@router.post("/data/mark-notification-read")
async def mark_notification_read(
    request: Request,
    notification_id: str = Query(..., alias="id", min_length=1),
):
    """Mark a single notification as read (owner-only).

    Returns ``{ updated: 0|1 }`` — 1 when the notification was unread
    and got flipped, 0 when it was already read or not found / not
    owned by the caller.
    """
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.mark_notification_read(
        request=request, notification_id=notification_id
    )


# ── Validation-request endpoints have been moved to the security module ────────
# Canonical paths:
#   GET  /api/v1/securities/validations/requests/pending
#   GET  /api/v1/securities/validations/requests/single
#   POST /api/v1/securities/validations/requests/validate-or-reject
#   POST /api/v1/securities/validations/requests/validate-all
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/data/get-global-validators")
async def fetch_global_user_validators(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_global_user_validators(request=request,all_data=all_data,page=page,limit=limit,output_data_type=output_data_type,endpoint_call=endpoint_call)

@router.get("/data/get-no-sudo-global-validators")
async def fetch_no_sudo_global_user_validators(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_no_sudo_global_user_validators(request=request,all_data=all_data,page=page,limit=limit,output_data_type=output_data_type,endpoint_call=endpoint_call)
 
 
@router.get("/data/get-no-sudo-per-permission-validators")
async def fetch_no_sudo_per_permission_user_validators(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_no_sudo_per_permission_user_validators(request=request,all_data=all_data,page=page,limit=limit,output_data_type=output_data_type,endpoint_call=endpoint_call)
 
 
@router.post("/data/add-global-validators")
async def add_global_user_validators(
    request: Request,
    body: Dict[str, Any]
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.add_global_user_validators(request=request,body=body)
 
@router.put("/data/update-currency-exchanges")
async def update_currency_exchanges(
    request: Request,
    body: Dict[str, Any]
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.update_currency_exchanges(request=request,body=body)
 
  
 
@router.get("/data/get-permission-validators") 
async def fetch_validator_users_per_permission(
    request: Request,
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_validator_users_per_permission(request=request,all_data=all_data,page=page,limit=limit,output_data_type=output_data_type,endpoint_call=endpoint_call)
 
    

@router.post("/data/add-permission-validators")
async def add_permission_user_validators(
    request: Request,
    body: Dict[str, Any]
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.add_permission_user_validators(request=request,body=body)
 
 
@router.get("/data/get-sudo-permissions")
async def get_sudo_permissions(
    request: Request,
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.get_sudo_permissions(request=request,all_data=all_data,page=page,limit=limit,output_data_type=output_data_type,endpoint_call=endpoint_call)
 
  
    
@router.get("/data/get-exchanges-config")
async def fetch_exchanges_config(
    request: Request,
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_exchanges_config(request=request,all_data=all_data,page=page,limit=limit,output_data_type=output_data_type,endpoint_call=endpoint_call)


# GET ROLE PERMISSIONS
@router.get("/data/org/get-role-permissions")
async def fetch_org_role_permissions(
    request: Request, 
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_org_role_permissions(request=request,output_data_type=output_data_type,endpoint_call=endpoint_call)

# UPDATE ROLE PERMISSIONS
@router.put("/data/org/update-role-permissions")
async def update_org_role_permissions(
    request: Request, 
    background_tasks: BackgroundTasks,
    body: Dict[str, Any],
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.update_org_role_permissions(request=request,background_tasks=background_tasks,body=body)
 
@router.get("/org/data/get-exchanges-config")
async def fetch_org_exchanges_config(
    request: Request,
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    endpoint_call: Optional[bool] = Query(False, description="Endpoint call")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_org_exchanges_config(request=request,all_data=all_data,page=page,limit=limit,output_data_type=output_data_type,endpoint_call=endpoint_call)
 
@router.get("/data/get-user-config")
async def fetch_user_config(
    request: Request, 
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.fetch_user_config(request)
 
 
@router.post("/data/add-user-config")
async def add_exchanges_config(
    request: Request, 
    payload:UserConfigPayload
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.add_exchanges_config(request=request, payload=payload)
 
    
@router.post("/add-translations")
async def add_translation_data(request: Request, data: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.add_translation_data(request=request, data=data)
 
@router.get("/org/agent-user-account-head")
async def get_agent_user_account_head(
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.get_agent_user_account_head(request=request)
 
@router.get("/org/get-agent-user-account")
async def get_agent_user_account(
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.get_agent_user_account(request=request)
 
@router.get("/files/view-file")
async def view_file(request: Request):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.view_file(request=request)

@router.get("/files/view-svg")
async def view_svg_icon(request: Request):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.view_svg_icon(request=request)

@router.get("/files/viewfiles")
async def view_file(request: Request):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.view_file_from_gen_id(request=request)

    
@router.get("/files/download-file")
async def download_file(request: Request):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.download_file(request=request)
 
    
@router.get("/files/local-download-file")
async def download_lodal_file(request: Request):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.download_local_file(request=request)
 
    
@router.get("/data/saas-users")
async def get_saas_users(request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.get_saas_users(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
 

# PROFIL
@router.put("/data/org/upsert-profile-permissions")
async def org_upsert_profile_permissions(request: Request,background_tasks: BackgroundTasks, body: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.org_upsert_profile_permissions(request=request,background_tasks=background_tasks, body=body)

@router.put("/data/org/upsert-extended-profile-permissions")
async def org_upsert_extended_profile_permissions(request: Request,background_tasks: BackgroundTasks, body: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.org_upsert_extended_profile_permissions(request=request,background_tasks=background_tasks, body=body)

@router.get("/data/org/get-profile-permissions")
async def org_get_profile_permissions(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.org_get_profile_permissions(request=request,output_data_type=output_data_type)

@router.get("/data/org/get-extended-profile-permissions")
async def org_get_extended_profile_permissions(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.org_get_extended_profile_permissions(request=request,output_data_type=output_data_type)

@router.post("/data/org/create-profile")
async def org_add_profile_data(request: Request,background_tasks: BackgroundTasks, data: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.org_add_profile_data(request=request,background_tasks=background_tasks, data=data)

@router.delete("/data/org/delete-profile")
async def org_delete_profile_data(request: Request,background_tasks: BackgroundTasks):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.org_delete_profile_data(request=request,background_tasks=background_tasks)


# ROLES
@router.post("/data/org/create-role")
async def org_add_role_data(request: Request,background_tasks: BackgroundTasks, data: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.org_add_role_data(request=request,background_tasks=background_tasks, data=data)

@router.delete("/data/org/delete-role")
async def org_delete_role_data(request: Request,background_tasks: BackgroundTasks):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    static_controller = StaticController(accept_language)
    return await static_controller.org_delete_role_data(request=request,background_tasks=background_tasks)
