# app/api/v1/endpoints/generic.py

from app.modules.core.api.controller.organization_controller import OrganizationController
from app.modules.core.api.controller.agent_bulk_controller import AgentBulkController
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from fastapi import APIRouter, BackgroundTasks, Body, File, Form, Query, Request, UploadFile
from typing import Dict, Any, Optional
from app.modules.core.enums.type_enum import OutputDataType

router = APIRouter()


@router.post("/add/org")
async def add_data(request: Request,background_tasks: BackgroundTasks, body: dict = Body(...)):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.add_new_org_data(request=request,background_tasks=background_tasks, body=body)


@router.delete("/hard-delete/org")
async def hard_delete_organization(request: Request,background_tasks: BackgroundTasks):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.hard_delete_organization(request=request,background_tasks=background_tasks)


@router.post("/add/agents")
async def add_agent_data(request: Request, body: dict = Body(...)):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.add_agent_data(request=request, body=body)


@router.delete("/hard-delete/agents")
async def delete_agent_data(request: Request):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.delete_agent_data(request=request)


@router.post("/bulk-upload/agents")
async def bulk_upload_agents(request: Request, file: UploadFile = File(...), cfg_organism_chart_id: Optional[str] = Form(None)):
    """Bulk upload agents from an Excel file."""
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = AgentBulkController(accept_language)
    return await controller.bulk_upload_agents(request=request, file=file, cfg_organism_chart_id=cfg_organism_chart_id)


@router.get("/fetch/agents-bulk-template")
async def download_agents_bulk_template(request: Request):
    """Download an Excel template for bulk agent creation."""
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = AgentBulkController(accept_language)
    return await controller.download_bulk_template(request=request)


@router.delete("/hard-delete/user")
async def delete_user_data(request: Request):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.delete_user_data(request=request)


@router.post("/add/sysUsers")
async def add_user_data(request: Request, body: dict = Body(...)):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.add_user_data(request=request, body=body)


@router.delete("/soft-delete/{collection_name}/{item_id}")
async def soft_delete_data(request: Request, collection_name: str, item_id: str):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.soft_delete_data(request=request, collection_name=collection_name, item_id=item_id)


@router.get("/generate-reset-password-link")
async def generate_reset_password_link(request: Request, background_tasks: BackgroundTasks):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.generate_reset_password_link(request=request, background_tasks=background_tasks)


@router.delete("/hard-delete/{collection_name}/{item_id}")
async def hard_delete_data(request: Request, collection_name: str, item_id: str):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.hard_delete_data(request=request, collection_name=collection_name, item_id=item_id)


@router.put("/update/{collection_name}/{item_id}")
async def update_data(request: Request, collection_name: str, item_id: str, data: Dict[str, Any]):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.update_data(request=request, collection_name=collection_name, item_id=item_id, data=data)


@router.get("/fetch/own-info")
async def fetch_own_info(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(
        OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.fetch_own_org_info(request=request, output_data_type=output_data_type, all_data=all_data, page=page, limit=limit)


@router.get("/fetch-single-user-info")
async def fetch_single_user_info(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(
        OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.fetch_single_user_info(request=request, output_data_type=output_data_type, all_data=all_data, page=page, limit=limit)

@router.patch("/update/user-device-count")
async def update_user_device_count(
    request: Request,
    body: dict = Body(...)
):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.update_user_device_count(request=request, body=body)


@router.get("/fetch-main-profile")
async def fetch_main_profile(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(
        OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.fetch_main_profile(request=request, output_data_type=output_data_type, all_data=all_data, page=page, limit=limit)


@router.get("/fetch/organism-charts")
async def fetch_org_charts(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(
        OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
    sort: Optional[Dict[str, int]] = {'created_at': -1},
):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.fetch_org_charts(request=request, output_data_type=output_data_type, all_data=all_data, page=page, limit=limit, sort=sort)


@router.get("/fetch/org")
async def fetch_org_data(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(
        OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.fetch_org_data(request=request, output_data_type=output_data_type, all_data=all_data, page=page, limit=limit)


@router.get("/search-org")
async def search_organization_info(
    request: Request,
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.search_organization_info(request=request, all_data=all_data, page=page, limit=limit)


@router.post("/upload-logo")
async def upload_org_logo(
    request: Request,
    id: str = Form(...),
    upload_file: UploadFile = File(...),
):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.upload_org_logo(request=request, id=id, upload_file=upload_file)


# ORGANIZATION BRANCHES

@router.get("/fetch/org-branches")
async def fetch_org_branches_data(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(
        OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.fetch_org_branches_data(request=request, output_data_type=output_data_type, all_data=all_data, page=page, limit=limit)


@router.post("/add/org-branches")
async def add_branches_data(request: Request,background_tasks: BackgroundTasks, body: dict = Body(...)):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.add_branches_data(request=request,background_tasks=background_tasks, body=body)


@router.delete("/hard-delete/org-branches")
async def hard_delete_branches_data(request: Request):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.hard_delete_branches_data(request=request)


@router.get("/search-branches")
async def search_branches_data(
    request: Request,
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.search_branches_data(request=request, all_data=all_data, page=page, limit=limit)


@router.get("/head/user-privileges")
async def fetch_user_privileges_head(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(
        OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.fetch_user_privileges_head(request=request, output_data_type=output_data_type, all_data=all_data, page=page, limit=limit)

@router.post("/add/user-privileges")
async def add_user_privileges_data(request: Request, body: dict = Body(...)):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.add_user_privileges_data(request=request, body=body)


@router.get("/fetch/user-login-histories")
async def fetch_user_login_histories(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(
        OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.fetch_user_login_histories(request=request, output_data_type=output_data_type, all_data=all_data, page=page, limit=limit)

 
@router.delete("/hard-delete/user-privileges")
async def hard_delete_user_privileges_data(request: Request):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.hard_delete_user_privileges_data(request=request)


@router.get("/search/user-privileges")
async def search_user_privileges_data(
    request: Request,
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.search_user_privileges_data(request=request, all_data=all_data, page=page, limit=limit)

@router.get("/user-login-history")
async def fetch_user_login_history_head(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(
        OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    organization_controller = OrganizationController(accept_language)
    return await organization_controller.fetch_user_login_history_head(request=request, output_data_type=output_data_type, all_data=all_data, page=page, limit=limit)


@router.get("/fetch/organization-related-profiles")
async def fetch_organization_related_profiles(
    request: Request,
):
    organization_controller = OrganizationController(
        accept_language=request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
    )
    return await organization_controller.fetch_organization_related_profiles(
        request=request,
        raw_query_params=dict(request.query_params),
    )


@router.get("/fetch/organization-available-profiles")
async def fetch_organization_available_profiles(
    request: Request,
):
    organization_controller = OrganizationController(
        accept_language=request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
    )
    return await organization_controller.fetch_organization_available_profiles(
        request=request,
        raw_query_params=dict(request.query_params),
    )


@router.patch("/patch/add-remove-organization-profile")
async def patch_organization_to_add_remove_profile(
    request: Request,
    body: dict,
):
    organization_controller = OrganizationController(
        accept_language=request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
    )
    return await organization_controller.patch_organization_to_add_remove_profile(
        request=request,
        raw_query_params=dict(request.query_params),
        body=body,
    )

@router.patch("/patch/add-remove-organization-application-group")
async def patch_organization_to_add_remove_application_group(
    request: Request,
    body: dict,
):
    organization_controller = OrganizationController(
        accept_language=request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
    )
    return await organization_controller.patch_organization_to_add_remove_application_group(
        request=request,
        raw_query_params=dict(request.query_params),
        body=body,
    )

# /patch/add-remove-organization-application-key
@router.patch("/patch/add-remove-organization-application-key")
async def patch_add_remove_organization_application_key(
    request: Request,
    body: dict,
):
    organization_controller = OrganizationController(
        accept_language=request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
    )
    return await organization_controller.patch_add_remove_organization_application_key(
        request=request,
        raw_query_params=dict(request.query_params),
        body=body,
    )


# /fetch/organization-sms-coverage
@router.get("/fetch/organization-sms-coverage")
async def fetch_organization_sms_coverage(
    request: Request,
):
    organization_controller = OrganizationController(
        accept_language=request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
    )
    return await organization_controller.fetch_organization_sms_coverage(
        request=request,
        raw_query_params=dict(request.query_params),
    )


# /patch/add-remove-organization-sms-coverage
@router.patch("/patch/add-remove-organization-sms-coverage")
async def patch_add_remove_organization_sms_coverage(
    request: Request,
    body: dict,
):
    organization_controller = OrganizationController(
        accept_language=request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
    )
    return await organization_controller.patch_add_remove_organization_sms_coverage(
        request=request,
        raw_query_params=dict(request.query_params),
        body=body,
    )


