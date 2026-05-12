# app/api/v1/endpoints/generic.py

from app.modules.core.api.controller.generic_controller import GenericController
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.enums.type_enum import OutputDataType
from fastapi import Body, APIRouter, Query, Request
from typing import Dict, Any, List, Optional

router = APIRouter()


@router.post("/validate-user-info")
async def validate_user_info(request: Request, body: dict = Body(...)):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.validate_user_infos(request=request, body=body)


@router.post("/verify-user-validation-code") 
async def verify_user_validation_code(request: Request, body: dict = Body(...)):
    accept_language = request.headers.get(
        "accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.verify_user_validation_code(request=request, body=body)



@router.post("/add/{collection_name}")
async def add_data(request: Request,collection_name: str, data: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.add_data(request=request, collection_name=collection_name, data=data)

@router.patch("/upsert/{collection_name}")
async def add_data(request: Request,collection_name: str, data: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.upsert_data(request=request, collection_name=collection_name, data=data)

@router.post("/create-role")
async def role_add_data(request: Request, data: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.role_add_data(request=request, data=data)


@router.post("/org/add/{collection_name}")
async def org_add_data(request: Request,collection_name: str, data: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.org_add_data(request=request, collection_name=collection_name, data=data)

@router.patch("/org/upsert/{collection_name}")
async def org_upsert_data(request: Request,collection_name: str, data: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.org_upsert_data(request=request, collection_name=collection_name, data=data)

@router.delete("/soft-delete/{collection_name}")
async def soft_delete_data(request: Request,collection_name: str):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.soft_delete_data(request=request, collection_name=collection_name)

@router.delete("/hard-delete/{collection_name}")
async def hard_delete_data(request: Request,collection_name: str):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.hard_delete_data(request=request, collection_name=collection_name)


@router.delete("/org/hard-delete/{collection_name}")
async def org_hard_delete_data(request: Request,collection_name: str):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.hard_delete_data(request=request, collection_name=collection_name)

@router.put("/update/{collection_name}") #deprecated
async def update_data(request: Request,collection_name: str, data: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.on_update_data(request=request, collection_name=collection_name,data=data)


@router.put("/org/update/{collection_name}") #deprecated
async def org_update_data(request: Request,collection_name: str, body: dict = Body(...)):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.org_on_update_data(request=request, collection_name=collection_name,body=body)


@router.put("/put/{collection_name}")
async def update_data(request: Request,collection_name: str, data: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.on_update_data(request=request, collection_name=collection_name,data=data)


@router.put("/org/put/{collection_name}")
async def org_update_data(request: Request,collection_name: str, body: dict = Body(...)):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.org_on_update_data(request=request, collection_name=collection_name,body=body)


@router.patch("/patch/{collection_name}")
async def path_data(request: Request,collection_name: str, data: Dict[str, Any]):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.on_update_data(request=request, collection_name=collection_name,data=data)


@router.patch("/org/patch/{collection_name}")
async def org_patch_data(request: Request,collection_name: str, body: dict = Body(...)):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.org_on_update_data(request=request, collection_name=collection_name,body=body)


@router.patch("/org/ordering-update/{collection_name}")
async def update_to_ordering_data(request: Request,collection_name: str, body: List = Body(...)):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.update_to_ordering_data(request=request, collection_name=collection_name,body=body)

@router.get("/fetch/{collection_name}")
async def fetch_data(
    request: Request,
    collection_name: str,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.on_data_fetch(request=request, collection_name=collection_name,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@router.get("/fetch-one/{collection_name}")
async def fetch_one_data(
    request: Request,
    collection_name: str,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.fetch_one_data(request=request, collection_name=collection_name,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)


@router.get("/org/fetch-one/{collection_name}")
async def fetch_org_one_data(
    request: Request,
    collection_name: str,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.fetch_org_one_data(request=request, collection_name=collection_name,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@router.get("/org/fetch/{collection_name}")
async def fetch_org_data(
    request: Request,
    collection_name: str,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page"),
    sort: Optional[Dict[str, int]] = {'created_at': -1},
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.on_org_fetch_data(request=request, collection_name=collection_name,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit,sort=sort)


@router.get("/head/{collection_name}")
async def get_collection_head(
    collection_name: str,
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.get_collection_head(request=request, collection_name=collection_name)


@router.get("/org/head/{collection_name}")
async def get_org_collection_head(
    collection_name: str,
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.get_org_collection_head(request=request, collection_name=collection_name)



@router.get("/child-head/{collection_name}")
async def get_child_collection_head(
    collection_name: str,
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.get_child_collection_head(request=request, collection_name=collection_name)


@router.get("/org/child-head/{collection_name}")
async def get_org_child_collection_head(
    collection_name: str,
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.get_org_child_collection_head(request=request, collection_name=collection_name)


@router.get("/update-head/{collection_name}")
async def get_collection_update_head(
    collection_name: str,
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.get_collection_update_head(request=request, collection_name=collection_name)

@router.get("/child-update-head/{collection_name}")
async def get_collection_child_update_head(
    collection_name: str,
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.get_collection_child_update_head(request=request, collection_name=collection_name)


@router.get("/org/child-update-head/{collection_name}")
async def get_org_collection_child_update_head(
    collection_name: str,
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.get_org_collection_child_update_head(request=request, collection_name=collection_name)

@router.get("/org/update-head/{collection_name}")
async def get_org_collection_update_head(
    collection_name: str,
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.get_org_collection_update_head(request=request, collection_name=collection_name)


@router.get("/org/data-overview/{collection_name}")
async def ge_org_data_overview(
    collection_name: str,
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.ge_org_data_overview(request=request, collection_name=collection_name)

@router.get("/data-overview/{collection_name}")
async def get_data_overview(
    collection_name: str,
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.get_data_overview(request=request, collection_name=collection_name)


@router.post("/token-data-overview/{collection_name}")
async def get_token_data_overview(
    collection_name: str,
    request: Request,
    body: dict = Body(...)
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.get_token_data_overview(request=request, collection_name=collection_name,body=body)


# Add the new data integrity endpoint
@router.get("/integrity/{collection_name}/{item_id}")
async def check_data_integrity(
    request: Request,
    collection_name: str,
    item_id: str
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.check_data_integrity(request=request, collection_name=collection_name,item_id=item_id)


@router.patch("/translate-field/{collection_name}/{item_id}/{field_name}")
async def translate_field(
    request: Request,
    collection_name: str,
    item_id: str,
    field_name: str,
    translation_data: Dict[str, Any] = Body(...),
    translation_strategy: Optional[str] = Query("default", description="Translation strategy: default, preserve, or cascade")
):

    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.translate_field(request=request, collection_name=collection_name,item_id=item_id,field_name=field_name,translation_data=translation_data,translation_strategy=translation_strategy)


@router.get("/translation-head/{collection_name}/{item_id}/{field_name}")
async def get_translation_field_head(
    collection_name: str,
    item_id: str,
    field_name: str,
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.get_translation_field_head(request=request, collection_name=collection_name,item_id=item_id,field_name=field_name)

@router.get("/count/{collection_name}")
async def count_data(
    request: Request,
    collection_name: str,
):
    """
    Endpoint to count documents in a collection with support for filtering.

    Parameters:
        request (Request): The FastAPI request object.
        collection_name (str): The name of the collection to count documents from.

    Returns:
        int: The count of documents matching the query criteria.
    """
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)

    # Extract query parameters from the request
    query_params = dict(request.query_params)

    # Remove special parameters that shouldn't be part of the MongoDB query
    query_params.pop("collection_name", None)

    return await genericController.count_data_from_collection(
        request=request,
        collection_name=collection_name,
        query=query_params
    )

@router.post("/aggregate-count/{collection_name}")
async def aggregate_count_data(
    request: Request,
    collection_name: str,
    pipeline: List[Dict[str, Any]] = Body(..., description="MongoDB aggregation pipeline stages"),
):
    """
    Endpoint to count documents in a collection using an aggregation pipeline.

    Parameters:
        request (Request): The FastAPI request object.
        collection_name (str): The name of the collection to count documents from.
        pipeline (List[Dict[str, Any]]): A list of MongoDB aggregation pipeline stages.

    Returns:
        int: The count of documents matching the aggregation criteria.
    """
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)

    return await genericController.aggregate_count_data_from_collection(
        request=request,
        collection_name=collection_name,
        pipeline=pipeline
    )


@router.get("/fetch-ref/all-countries")
async def fetch_all_countries(
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    genericController = GenericController(accept_language)
    return await genericController.fetch_all_countries_info(request=request)
