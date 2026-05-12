
#app/api/v1/endpoints/cores.py

from typing import Any, Dict, Optional
from app.modules.core.api.controller.core_controller import CoreController
from app.modules.core.api.controller.system_profil_controller import SystemProfilController
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from fastapi import APIRouter,  Query, Request
from app.modules.core.enums.type_enum import OutputDataType

router = APIRouter()

# Endpoint with user details access
@router.get("/check-core-access")
async def check_core_access(
    request: Request,
    
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.check_core_access(request=request) 
    

@router.get("/update-all-default-access-roles")
async def update_all_default_access_roles(
    request: Request,
    
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.update_all_default_access_roles(request=request) 
  
    
@router.get("/get-config-roles")
async def fetch_config_roles(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_config_roles(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
    
    
@router.get("/get-config-rbac-single-action")
async def fetch_config_single_rbac_actions(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_config_single_rbac_actions(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@router.get("/get-config-rbac-actions")
async def fetch_config_rbac_actions(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_config_rbac_actions(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
    
    
@router.get("/get-config-data-display-type")
async def fetch_config_data_display_types(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_config_data_display_types(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 

@router.get("/get-custom-config-data-display-type")
async def fetch_custom_config_data_display_types(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_custom_config_data_display_types(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
    

@router.get("/get-custom-config-children-display-type")
async def fetch_custom_config_children_display_types(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_custom_config_children_display_types(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
    
@router.get("/get-config-collection-meta-data")
async def fetch_config_collection_meta_datas(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_config_collection_meta_datas(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
    
@router.get("/get-config-children-display-type")
async def fetch_config_children_display_types(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_config_children_display_types(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
    
@router.get("/get-config-rbac-components")
async def fetch_config_rbac_components(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_config_rbac_components(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
    
# @router.get("/get-config-permissions")
# async def fetch_config_permissions(
#     request: Request,
#     output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
#     all_data: Optional[bool] = Query(False, description="Fetch all data"),
#     page: Optional[int] = Query(0, description="Page number for pagination"),
#     limit: Optional[int] = Query(10, description="Number of items per page")
# ):
#     accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
#     core_controller = CoreController(accept_language)
#     return await core_controller.fetch_config_permissions(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
@router.get("/get-simplified-config-sub-endpoints")
async def fetch_simplified_config_rbac_title_sub_endpoints(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_simplified_config_rbac_title_sub_endpoints(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
@router.get("/get-simplified-config-single-endpoint")
async def fetch_simplified_config_rbac_title_single_endpoint(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_simplified_config_rbac_title_single_endpoint(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
 
@router.get("/get-simplified-config-single-permission")
async def fetch_simplified_config_rbac_title_single_permission(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_simplified_config_rbac_title_single_permission(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@router.get("/get-simplified-config-sub-permissions")
async def fetch_simplified_config_rbac_title_sub_permissions(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_simplified_config_rbac_title_sub_permissions(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
 
@router.get("/get-simplified-config-permissions")
async def fetch_simplified_config_rbac_titles(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_simplified_config_rbac_titles(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
 
@router.get("/get-config-path-guards")
async def fetch_config_path_guards(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_config_path_guards(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
  

# @router.get("/get-config-applications")
# async def fetch_config_applications(
#     request: Request,
#     output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
#     all_data: Optional[bool] = Query(False, description="Fetch all data"),
#     page: Optional[int] = Query(0, description="Page number for pagination"),
#     limit: Optional[int] = Query(10, description="Number of items per page")
# ):
#     accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
#     core_controller = CoreController(accept_language)
    # return await core_controller.fetch_config_applications(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@router.get("/get-simplified-config-applications")
async def fetch_simplified_config_applications(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_simplified_config_applications(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@router.get("/get-simplified-config-application-menus")
async def fetch_simplified_config_application_menus(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_simplified_config_application_menus(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@router.get("/get-config-single-application")
async def fetch_config_single_application(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_config_single_application(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
   
@router.get("/get-config-sub-menu")
async def fetch_config_sub_menus(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_config_sub_menus(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
 
   
@router.get("/get-config-standalone-menu")
async def fetch_config_sub_menu_for_configs(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.fetch_standalone_menu_for_configs(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
  
 

@router.patch("/patch/{collection_name}/apiconsumer")
async def update_apiconsumer_data(request: Request,collection_name: str, datas: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.update_apiconsumer_data(request=request,collection_name=collection_name,datas=datas)
   

@router.patch("/patch/{collection_name}/apiconsumertarget")
async def update_apiconsumer_target_data(request: Request,collection_name: str, datas: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.update_apiconsumer_target_data(request=request,collection_name=collection_name,datas=datas)
   
#permission target only
@router.patch("/patch/{collection_name}/systemprofil")
async def update_sysprofil_data(request: Request,collection_name: str, datas: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.update_sysprofil_data(request=request,collection_name=collection_name,datas=datas)

@router.patch("/patch/{collection_name}/systemprofiltarget")
async def update_sysprofil_target_data(request: Request,collection_name: str, datas: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.update_sysprofil_target_data(request=request,collection_name=collection_name,datas=datas)

#update app or menu on path guard
@router.patch("/patch/{collection_name}/targeted")
async def update_targeted_data(request: Request,collection_name: str, datas: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.update_targeted_data(request=request,collection_name=collection_name,datas=datas)
 

@router.patch("/patch/{collection_name}/permissiontarget")
async def update_permission_target_data(request: Request,collection_name: str, datas: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.update_permission_target_data(request=request,collection_name=collection_name,datas=datas)

@router.patch("/patch/{collection_name}/cfgpermissionrole")
async def update_permission_role_data(request: Request,collection_name: str, datas: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    core_controller = CoreController(accept_language)
    return await core_controller.update_permission_role_data(request=request,collection_name=collection_name,datas=datas)
    


# START SYSTEM PROFIL ENDPOINTS
@router.put("/upsert-profile-permissions")
async def core_upsert_profile_permissions(request: Request, body: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_profil_controller = SystemProfilController(accept_language)
    return await system_profil_controller.core_upsert_profile_permissions(request=request, body=body)

@router.put("/upsert-extended-profile-permissions")
async def core_upsert_extended_profile_permissions(request: Request, body: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_profil_controller = SystemProfilController(accept_language)
    return await system_profil_controller.core_upsert_extended_profile_permissions(request=request, body=body)

@router.get("/get-profile-permissions")
async def core_get_profile_permissions(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_profil_controller = SystemProfilController(accept_language)
    return await system_profil_controller.core_get_profile_permissions(request=request,output_data_type=output_data_type)

@router.get("/get-extended-profile-permissions")
async def core_get_extended_profile_permissions(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_profil_controller = SystemProfilController(accept_language)
    return await system_profil_controller.core_get_extended_profile_permissions(request=request,output_data_type=output_data_type)

@router.post("/create-profile")
async def core_add_profile_data(request: Request, data: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_profil_controller = SystemProfilController(accept_language)
    return await system_profil_controller.core_add_profile_data(request=request, data=data)

@router.delete("/delete-profile")
async def core_delete_profile_data(request: Request,):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_profil_controller = SystemProfilController(accept_language)
    return await system_profil_controller.core_delete_profile_data(request=request)


