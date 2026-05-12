
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Body, File, Form, Query, Request, UploadFile
from app.modules.edocs.api.controller.edoc_controller import EdocController
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.enums.type_enum import OutputDataType

router = APIRouter()
 
@router.post("/org/add/archFolders")
async def add_folder_data(request: Request,data: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    edoc_controller = EdocController(accept_language)
    return await edoc_controller.add_folder_data(request=request,data=data) 
    
@router.get("/org/fetch/archFolders")
async def fetch_org_folder_data(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
    sort: Optional[Dict[str, int]] = {'created_at': -1},
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    edoc_controller = EdocController(accept_language)
    return await edoc_controller.fetch_org_folder_data(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit,sort=sort)


@router.delete("/org/hard-delete/archFolders")
async def hard_delete_folder_data(request: Request,):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    edoc_controller = EdocController(accept_language)
    return await edoc_controller.hard_delete_folder_data(request=request,)
 
@router.get("/org/fetch/folders-bin")
async def fetch_org_folder_bin_data(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
    sort: Optional[Dict[str, int]] = {'created_at': -1},
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    edoc_controller = EdocController(accept_language)
    return await edoc_controller.fetch_org_folder_bin_data(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit,sort=sort)
 
 
@router.post("/org/add/archFiles")
async def add_org_file_data(request: Request,data: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    edoc_controller = EdocController(accept_language)
    return await edoc_controller.add_org_file_data(request=request,data=data)

@router.post("/org/files/upload")
async def add_org_file_data(
    request: Request,
    arch_folder_id: str = Form(...),
    upload_file: UploadFile = File(...),
):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    edoc_controller = EdocController(accept_language)
    return await edoc_controller.add_org_file_data(request=request, arch_folder_id=arch_folder_id, upload_file=upload_file)


@router.get("/org/data/stats")
async def fetch_org_edoc_stats(
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    edoc_controller = EdocController(accept_language)
    return await edoc_controller.fetch_org_edoc_stats(request=request)
 
 