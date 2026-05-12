
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE

from app.modules.core.api.controller.system_country_controller import SystemCountryController
from fastapi import APIRouter, Body, Header, Query, Request, BackgroundTasks
from app.modules.auth.schemas.auth_schema import DeviceActivationTokenRequest, LoginRequest,  OtpRequest, PasswordInitRequest, PasswordResetRequest, PasswordResetTokenRequest, TOtpRequest
from typing import Optional
from app.modules.core.enums.type_enum import OutputDataType


system_country_router = APIRouter()


@system_country_router.get("/countries/fetch/system-countries")
async def fetch_system_countries(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_system_countries(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@system_country_router.get("/countries/fetch/entities")
async def fetch_entities(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_entities(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@system_country_router.get("/countries/fetch/app-system-countries")
async def fetch_app_system_countries(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_app_system_countries(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@system_country_router.get("/countries/fetch/app-no-existing-system-countries")
async def fetch_app_no_existing_system_countries(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_app_no_existing_system_countries(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@system_country_router.get("/countries/fetch/no-existing-countries")
async def fetch_no_existing_countries(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_no_existing_countries(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@system_country_router.get("/countries/fetch/all-existing-countries")
async def fetch_all_existing_countries(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_all_existing_countries(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@system_country_router.get("/countries/fetch/all-system-country-and-currencies")
async def fetch_all_system_countries_currencies(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_all_system_country_and_currencies(request=request,output_data_type=output_data_type,page=page,limit=limit)

@system_country_router.get("/countries/fetch/system-country-availlable-currencies")
async def fetch_system_country_availlable_currencies(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_system_country_availlable_currencies(request=request,output_data_type=output_data_type)

@system_country_router.patch("/countries/patch/add-remove-country-code")
async def patch_system_country_to_add_remove_country_code_process(
    request: Request,
    body: dict = Body(...)
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.patch_system_country_to_add_remove_country_code_process(request=request,body=body)

@system_country_router.patch("/countries/patch/add-remove-country-phone-prefix")
async def patch_system_country_to_add_remove_country_phone_prefix_process(
    request: Request,
    body: dict = Body(...)
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.patch_system_country_to_add_remove_country_phone_prefix_process(request=request,body=body)
 
@system_country_router.patch("/countries/patch/add-remove-currency")
async def patch_system_country_to_add_remove_currency_process(
    request: Request,
    body: dict = Body(...)
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.patch_system_country_to_add_remove_currency_process(request=request,body=body)

# @system_country_router.patch("/patch/validate-email-phone-number-transfer-required")
# async def patch_system_country_to_validate_email_phone_number_transfer_required_process(
#     request: Request,
#     body: dict = Body(...)
# ):
#     accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
#     system_country_controller = SystemCountryController(accept_language)
#     return await system_country_controller.patch_system_country_to_validate_email_phone_number_transfer_required_process(request=request,body=body)

# /add/system-country
@system_country_router.post("/countries/add/system-country")
async def add_system_country(
    request: Request,
    body: dict = Body(...)
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.add_system_country(request=request,body=body)

# telephone-networks
@system_country_router.get("/telephone-networks/fetch/telnets")
async def fetch_telephone_networks(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_telephone_networks(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
 
@system_country_router.get("/telephone-networks/fetch/telnet-prefixes")
async def fetch_telephone_network_prefixes(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_telephone_network_prefixes(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)



@system_country_router.delete("/telephone-networks/delete/telephone-network")
async def delete_telephone_network(
    request: Request,
    body: dict = Body(...)
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.delete_telephone_network(request=request,body=body)


# /delete/system-country
@system_country_router.delete("/countries/delete/system-country")
async def delete_system_country(
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.delete_system_country(request=request)


@system_country_router.get("/fetch/registration-system-countries")
async def fetch_registration_system_country(
    request: Request,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_registration_system_country(request=request)

@system_country_router.get("/countries/fetch/check-system-country-configuration")
async def fetch_check_system_country_configuration(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_check_system_country_configuration(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@system_country_router.get("/fetch/init-customer-registration-process")
async def init_customer_registration(
    request: Request,
    background_tasks: BackgroundTasks,
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    controller = SystemCountryController(accept_language)
    return await controller.init_customer_registration(request=request, background_tasks=background_tasks)



@system_country_router.get("/countries/fetch/current-entity-default-currency")
async def fetch_current_entity_default_currency(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_current_entity_default_currency(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@system_country_router.get("/countries/fetch/current-entity-info")
async def fetch_current_entity_info(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_current_entity_info(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)

@system_country_router.put("/countries/update/current-entity-default-currency")
async def update_current_entity_default_currency(
    request: Request,
    body: dict = Body(...)
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.update_current_entity_default_currency(request=request,body=body)


@system_country_router.patch("/countries/patch/current-entity-flag")
async def patch_current_entity_flag(
    request: Request,
    body: dict = Body(...)
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.patch_current_entity_flag(request=request,body=body)

@system_country_router.patch("/countries/update/current-entity-flag")
async def patch_current_entity_flag(
    request: Request,
    body: dict = Body(...)
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.patch_current_entity_flag(request=request,body=body)


@system_country_router.get("/countries/fetch/system-country-currencies")
async def fetch_system_country_currencies(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_system_country_currencies(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)


@system_country_router.get("/countries/fetch/my-system-country-currencies")
async def fetch_my_system_country_currencies(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):  
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_my_system_country_currencies(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)


@system_country_router.get("/countries/fetch/my-system-countries-available")
async def fetch_my_system_countries_available(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):  
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_my_system_countries_available(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)


@system_country_router.get("/countries/fetch/system-country-country-codes")
async def fetch_system_country_codes(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_system_country_codes(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)



@system_country_router.patch("/countries/patch/add-remove-wallet-prefix")
async def patch_system_country_to_add_remove_wallet_prefix_process(
    request: Request,
    body: dict = Body(...)
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    country_controller = SystemCountryController(accept_language)
    return await country_controller.patch_system_country_to_add_remove_wallet_prefix_process(request=request,body=body)

# /ewallet-prefixes/fetch/ewallet-prefixes
@system_country_router.get("/ewallet-prefixes/fetch/ewallet-prefixes")
async def fetch_ewallet_prefixes(
    request: Request,
    output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    all_data: Optional[bool] = Query(False, description="Fetch all data"),
    page: Optional[int] = Query(0, description="Page number for pagination"),
    limit: Optional[int] = Query(10, description="Number of items per page")
):
    accept_language = request.headers.get("accept-language", DEFAULT_LANGUAGE).split(",")[0].strip()
    system_country_controller = SystemCountryController(accept_language)
    return await system_country_controller.fetch_ewallet_prefixes(request=request,output_data_type=output_data_type,all_data=all_data,page=page,limit=limit)
