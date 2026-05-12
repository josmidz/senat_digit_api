from datetime import timedelta
import hashlib
import json
import time
from bson import ObjectId
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.model.model_service import ModelService
from typing import Any, Optional, Dict
from fastapi import BackgroundTasks, Body, HTTPException, Query, Request,status
from app.modules.core.enums.type_enum import EAppGroupFlag, EJWTTokenType, FormatedOutPut, OutputDataType
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.types.response import CustomJSONResponse
from app.modules.auth.enums.common import MessageCategory
from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.utils.common.helpers import extract_field_on_output_data_element
from app.modules.core.utils.helpers.line_helper import exception_line_info, line_info, format_exception
from app.modules.core.schemas.core_schema import SystemCountryCreate
from app.modules.core.services.redis.redis_service import AppRedisService
from app.modules.core.enums.profiles_enum import ESysProfileFlag
from app.modules.core.models.ref_currency.ref_currency_model import RefCurrencyModel
from app.modules.core.services.system_country.system_country_service import SystemCountryService
class SystemCountryController(
    DebugService,
    ResponseService,
    ConverterService,
    AuthenticatedService,
    ModelService,):
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.core.services.generator.generator_service import GeneratorService
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.auth.services.token.token_service import TokenService
        
        self.accept_language = accept_language
        self.generator_service = GeneratorService(accept_language)
        self.generic_service = GenericService(accept_language)
        self.token_service = TokenService(accept_language)
        super().__init__(accept_language)

    


    def _generate_cache_key(self, user_id: str, method_name: str, **params) -> str:
        """
        Generate a unique cache key based on user ID, method name, and parameters
        """
        # Create a string representation of all parameters
        param_str = json.dumps(params, sort_keys=True, default=str)

        # Create a hash of the parameters to keep key length manageable
        param_hash = hashlib.md5(param_str.encode()).hexdigest()

        # Format: static_cache:{user_id}:{method_name}:{param_hash}
        return f"static_cache:{user_id}:{method_name}:{param_hash}"

    async def _get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from cache with timing
        """
        start_time = time.time()
        try:
            cached_data = await AppRedisService.get_str_redis_value(cache_key, use_env_prefix=True)
            fetch_time = round((time.time() - start_time) * 1000, 2)  # Convert to milliseconds

            if cached_data:
                self.app_debug_print(f"🎯 Cache HIT for key: {cache_key} | Fetch time: {fetch_time}ms", True)
                return json.loads(cached_data)
            else:
                self.app_debug_print(f"❌ Cache MISS for key: {cache_key} | Check time: {fetch_time}ms", True)
                return None
        except Exception as e:
            fetch_time = round((time.time() - start_time) * 1000, 2)
            self.app_debug_print(f"⚠️ Cache retrieval error: {str(e)} | Time: {fetch_time}ms", True)
            return None

    async def _set_cached_data(self, cache_key: str, data: Dict[str, Any], ttl: int = 300) -> None:
        """
        Store data in cache with TTL and timing (default 5 minutes)
        """
        start_time = time.time()
        try:
            serialized_data = json.dumps(data, default=str)
            await AppRedisService.set_redis_value(cache_key, serialized_data, expiry=ttl, use_env_prefix=True)
            store_time = round((time.time() - start_time) * 1000, 2)
            data_size = len(serialized_data)
            self.app_debug_print(f"💾 Cache SET for key: {cache_key} | TTL: {ttl}s | Store time: {store_time}ms | Size: {data_size} bytes", True)
        except Exception as e:
            store_time = round((time.time() - start_time) * 1000, 2)
            self.app_debug_print(f"⚠️ Cache storage error: {str(e)} | Time: {store_time}ms", True)




    async def fetch_system_countries(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Convert query parameters to dictionary
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)

            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            sort = request.query_params.get("sort", {'created_at':-1})
            self.app_debug_print(f"Query Parameters (SORT): {sort}",True)
            # Fetch data from the collection using CollectionKey
            data =  await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_SYSTEM_COUNTRY,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    **query_params
                },
                user=user_details,
                sort=sort
            )
            self.app_debug_print(f"Query system coutry: {len(data)}",True)
            formatted_data = []
            for element in data:
                # extract id
                ref_entity_id = element.get('ref_entity_id',{}).get('real_value',None) #  extract_field_on_output_data_element(element,'id',output_data_type)
                ref_entity = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_ENTITY,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    query={
                        "filter___id":ref_entity_id
                    },
                    user=user_details,
                    sort=sort
                )
                if not ref_entity:
                    continue
                formated_currencies = []
                list_of_availlable_currencies = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_CURRENCY,
                    all_data=True,
                    page=0,
                    limit=100000,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    query={
                        "filter__cfg_system_country_id":ref_entity_id
                    },
                    user=user_details,
                    sort=sort
                )
                for currency in list_of_availlable_currencies:
                    ref_currency_id = currency.get('ref_currency_id',{}).get('real_value',None) # extract_field_on_output_data_element(currency,'ref_currency_id',output_data_type)
                    currency_data = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_CURRENCY,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language=self.accept_language,
                        query={
                            "filter___id":ref_currency_id
                        },
                        user=user_details,
                        sort=sort
                    )
                    if not currency_data:
                        continue
                    formated_currencies.append({
                        **currency,
                        "ref_currency":currency_data
                    })

                country_codes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                    all_data=True,
                    page=0,
                    limit=100000,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    query={
                        "filter__cfg_system_country_id":ref_entity_id
                    },
                    user=user_details,
                    sort=sort
                )
                phone_number_prefixes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                    all_data=True,
                    page=0,
                    limit=100000,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    query={
                        "filter__cfg_system_country_id":ref_entity_id
                    },
                    user=user_details,
                    sort=sort
                )
                
                formatted_data.append({
                    **element,
                    "ref_country":{
                        "id":ref_entity['id'],
                        "name":ref_entity['name'],
                        "country_flag":ref_entity['country_flag'],
                    },
                    "availlable_currencies":formated_currencies,
                    "country_codes":country_codes,
                    "phone_number_prefixes":phone_number_prefixes,
                })
                
            extra_data = {}
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.CFG_SYSTEM_COUNTRY,
                    accept_language=self.accept_language,
                    query={
                        **query_params
                    },
                    user=user_details
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": formatted_data,
                    **extra_data
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes 
        except Exception as e:
            # add line of where exception comes from
            self.app_debug_print(f"Error in fetch_data: > 1 {str(e)} {exception_line_info(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    

    async def fetch_entities(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            output_data_type = OutputDataType.DEFAULT.value
            # Convert query parameters to dictionary
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)

            country_named_entity = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__named_entity_flag": "country"},
                all_data=True,
                user=user_details
            )
            if not country_named_entity:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_COUNTRY_NAMED_ENTITY_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            sort = request.query_params.get("sort", {'created_at':-1})
            self.app_debug_print(f"Query Parameters (SORT): {sort}",True)
            query_params = {
                **query_params,
                "filter__ref_named_entity_id": country_named_entity['id']
            }

            # Fetch data from the collection using CollectionKey
            data =  await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_SYSTEM_COUNTRY,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    **query_params
                },
                user=user_details,
                sort=sort
            )
            self.app_debug_print(f"Query system coutry: {len(data)}",True)
            formatted_data = []
            for element in data:
                # extract id
                ref_entity_id = extract_field_on_output_data_element(element,'id',output_data_type)
                ref_entity = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_ENTITY,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    query={
                        "filter___id":ref_entity_id
                    },
                    user=user_details,
                    sort=sort
                )
                if not ref_entity:
                    continue 
                
                formatted_data.append({
                    **element,
                    "ref_country":{
                        "id":ref_entity['id'],
                        "name":ref_entity['name'],
                        "country_flag":ref_entity['country_flag'],
                    },
                })
                
            extra_data = {}
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.CFG_SYSTEM_COUNTRY,
                    accept_language=self.accept_language,
                    query={
                        **query_params
                    },
                    user=user_details
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": formatted_data,
                    **extra_data
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes 
        except Exception as e:
            # add line of where exception comes from
            self.app_debug_print(f"Error in fetch_data: > 1 {str(e)} {exception_line_info(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    

    async def fetch_app_system_countries(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Convert query parameters to dictionary
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)

            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            sort = request.query_params.get("sort", {'created_at':-1})
            application_group_flag = request.query_params.get("filter__application_group_flag",None)
            self.app_debug_print(f"Query Parameters (SORT): {sort}",True)

            if not application_group_flag:
                raise HTTPException(status_code=400, detail="application_group_flag is required")
            
            application_group_flag = application_group_flag.strip().lower()

            if EAppGroupFlag(application_group_flag) == EAppGroupFlag.COMMON:
                raise HTTPException(status_code=400, detail="application_group_flag cannot be common")
            DebugService.app_debug_print(f"application_group_flag : {application_group_flag} : {EAppGroupFlag.__members__}",False)
            
            
            # Get all valid values
            valid_flags = [flag.value for flag in EAppGroupFlag]

            if application_group_flag not in valid_flags:
                raise HTTPException(
                    status_code=400, 
                    detail=f"application_group_flag must be one of: {', '.join(valid_flags)}"
                )

            # Fetch data from the collection using CollectionKey
            data =  await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_SYSTEM_COUNTRY,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                   "filter__application_group_flag":application_group_flag
                },
                user=user_details,
                sort=sort
            ) 
            self.app_debug_print(f"Query system related coutry: {len(data)}",True)
            formatted_data = []
            for cfg_country in data:
                self.app_debug_print(f"\n\n\n cfg_country : {cfg_country}",False)
                cfg_system_country_id = cfg_country.get('ref_entity_id',{}).get('real_value',None) # extract_field_on_output_data_element(cfg_country,'ref_entity_id',output_data_type)
                if cfg_system_country_id:
                    cfg_system_country_id = str(cfg_system_country_id)
                self.app_debug_print(f"\n\n\n cfg_system_country_id : {cfg_system_country_id}",True)
                element = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_ENTITY,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    query={
                        "filter___id":cfg_system_country_id
                    },
                    user=user_details,
                    sort=sort
                )
                self.app_debug_print(f"\n\n\n system country : {element}",False)
                if not element:
                    continue
                formated_currencies = []
                list_of_availlable_currencies = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_CURRENCY,
                    all_data=True,
                    page=0,
                    limit=100000,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    query={
                        "filter__cfg_system_country_id":cfg_system_country_id
                    },
                    user=user_details,
                    sort=sort
                )
                for currency in list_of_availlable_currencies:
                    ref_currency_id = currency.get('ref_currency_id',{}).get('real_value',None) # extract_field_on_output_data_element(currency,'ref_currency_id',output_data_type)
                    currency_data = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_CURRENCY,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language=self.accept_language,
                        query={
                            "filter___id":ref_currency_id
                        },
                        user=user_details,
                        sort=sort
                    )
                    if not currency_data:
                        continue
                    formated_currencies.append({
                        **currency,
                        "ref_currency":currency_data
                    })
                    
               

                country_codes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                    all_data=True,
                    page=0,
                    limit=100000,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    query={
                        "filter__cfg_system_country_id":cfg_system_country_id
                    },
                    user=user_details,
                    sort=sort
                )
                phone_number_prefixes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                    all_data=True,
                    page=0,
                    limit=100000,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    query={
                        "filter__cfg_system_country_id":cfg_system_country_id
                    },
                    user=user_details,
                    sort=sort
                )
                country_code = "" 
                if country_codes:
                    country_code = country_codes[0]['country_code']
                
                formatted_data.append({
                    "id":cfg_country['id'],
                    "name":element['name'],
                    "country_flag":element['country_flag'],
                    "cfg_system_country_id":element['id'],
                    "ref_country":{
                        "id":element['id'],
                        "name":element['name'],
                        "flag":element['country_flag'],
                        "identifier":element['identifier'],
                        "code":country_code
                    },
                    "availlable_currencies":formated_currencies,
                    "country_codes":country_codes,
                    "phone_number_prefixes":phone_number_prefixes,
                })
                
            extra_data = {}
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.CFG_SYSTEM_COUNTRY,
                    accept_language=self.accept_language,
                    query={
                        **query_params
                    },
                    user=user_details
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": formatted_data,
                    **extra_data
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes 
        except Exception as e:
            # add line of where exception comes from
            self.app_debug_print(f"Error in fetch_data: > 1 {str(e)} {exception_line_info(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
        

    async def fetch_app_no_existing_system_countries(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Convert query parameters to dictionary
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)

            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            sort = request.query_params.get("sort", {'created_at':-1})
            application_group_flag = request.query_params.get("filter__application_group_flag",None)
            self.app_debug_print(f"Query Parameters (SORT): {sort}",True)

            if not application_group_flag:
                raise HTTPException(status_code=400, detail="application_group_flag is required")

            application_group_flag = application_group_flag.strip().lower()

            if EAppGroupFlag(application_group_flag) == EAppGroupFlag.COMMON:
                raise HTTPException(status_code=400, detail="application_group_flag cannot be common")
            DebugService.app_debug_print(f"application_group_flag : {application_group_flag} : {EAppGroupFlag.__members__}",False)
            
            
            # Get all valid values
            valid_flags = [flag.value for flag in EAppGroupFlag]

            if application_group_flag not in valid_flags:
                raise HTTPException(
                    status_code=400, 
                    detail=f"application_group_flag must be one of: {', '.join(valid_flags)}"
                )
            country_pipeline = [
                {
                    "$lookup": {
                        "from": f"{CollectionKey.CFG_SYSTEM_COUNTRY.model_name}",
                        "let": {"country_id": "$_id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$and": [
                                            {"$eq": ["$ref_entity_id", "$$country_id"]},
                                            # {"$eq": ["$cfg_system_country_id", "$$country_id"]},
                                            {"$eq": ["$application_group_flag", application_group_flag]}
                                        ]
                                    }
                                }
                            }
                        ],
                        "as": "matching_groups"
                    }
                },
                # lookup named entity
                {
                    "$lookup": {
                        "from": f"{CollectionKey.REF_NAMED_ENTITY.model_name}",
                        "localField": "ref_named_entity_id",
                        "foreignField": "_id",
                        "as": "named_entity"
                    }

                },
                # unwind named entity
                {
                    "$unwind": {
                        "path": "$named_entity",
                        "preserveNullAndEmptyArrays": True
                    }
                },
                {
                    "$match": {
                        "matching_groups": {"$size": 0},
                        # match with named entity flag = country
                        "named_entity.named_entity_flag": "country"
                    }
                },
                {
                    "$project": {
                        "matching_groups": 0
                    }
                },
                {
                    "$skip": limit * page
                },
                {
                    "$limit": limit
                }
            ]
             
            data = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType(output_data_type).value,
                all_data=all_data,
                page=page,
                limit=limit,
                accept_language=self.accept_language,
                pipeline=country_pipeline, 
                sort=sort
            )  
            self.app_debug_print(f"Query no existing system coutry by apps: {len(data)}",True)
            formatted_data = []
            for element in data:
                cfg_system_country_id = extract_field_on_output_data_element(element,'id',output_data_type)
                formated_currencies = []
                list_of_availlable_currencies = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_CURRENCY,
                    all_data=True,
                    page=0,
                    limit=100000,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    query={
                        "filter__cfg_system_country_id":cfg_system_country_id
                    },
                    user=user_details,
                    sort=sort
                )
                for currency in list_of_availlable_currencies:
                    ref_currency_id = currency.get('ref_currency_id',{}).get('real_value',None) # extract_field_on_output_data_element(currency,'ref_currency_id',output_data_type)
                    currency_data = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_CURRENCY,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language=self.accept_language,
                        query={
                            "filter___id":ref_currency_id
                        },
                        user=user_details,
                        sort=sort
                    )
                    if not currency_data:
                        continue
                    formated_currencies.append({
                        **currency,
                        "ref_currency":currency_data
                    })
                    
                

                country_codes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                    all_data=True,
                    page=0,
                    limit=100000,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    query={
                        "filter__cfg_system_country_id":cfg_system_country_id
                    },
                    user=user_details,
                    sort=sort
                )
                phone_number_prefixes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                    all_data=True,
                    page=0,
                    limit=100000,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    query={
                        "filter__cfg_system_country_id":cfg_system_country_id
                    },
                    user=user_details,
                    sort=sort
                ) 
                country_code = ""
                country_related_codes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    all_data=True,
                    query={
                        "filter__cfg_system_country_id":cfg_system_country_id
                    },
                    user=user_details,
                    sort=sort
                )
                if country_related_codes:
                    country_code = country_related_codes[0]['country_code']
                formatted_data.append({
                    "id":element['id'],
                    "name":element['name'],
                    "country_flag":element['country_flag'],
                    "ref_country":{
                        "id":element['id'],
                        "name":element['name'],
                        "flag":element['country_flag'],
                        "identifier":element['identifier'],
                        "code":country_code
                    },
                    "availlable_currencies":formated_currencies,
                    "country_codes":country_codes,
                    "phone_number_prefixes":phone_number_prefixes,
                })
                
            extra_data = {}
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                # get max
                country_pipeline_count = [
                {
                    "$lookup": {
                        "from": f"{CollectionKey.CFG_SYSTEM_COUNTRY.model_name}",
                        "let": {"country_id": "$_id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$and": [
                                            {"$eq": ["$ref_entity_id", "$$country_id"]},
                                            # {"$eq": ["$cfg_system_country_id", "$$country_id"]},
                                            {"$eq": ["$application_group_flag", application_group_flag]}
                                        ]
                                    }
                                }
                            }
                        ],
                        "as": "matching_groups"
                    }
                },
                # lookup named entity
                {
                    "$lookup": {
                        "from": f"{CollectionKey.REF_NAMED_ENTITY.model_name}",
                        "localField": "ref_named_entity_id",
                        "foreignField": "_id",
                        "as": "named_entity"
                    }

                },
                # unwind named entity
                {
                    "$unwind": {
                        "path": "$named_entity",
                        "preserveNullAndEmptyArrays": True
                    }
                },
                {
                    "$match": {
                        "matching_groups": {"$size": 0},
                        # match with named entity flag = country
                        "named_entity.named_entity_flag": "country"
                    }
                },
                {
                    "$project": {
                        "matching_groups": 0
                    }
                },
                 
            ]
               
                # get max
                max_data = await self.generic_service.fetch_native_aggregate_count_from_collection(
                    collection_key=CollectionKey.REF_ENTITY,
                    accept_language=self.accept_language,
                    pipeline=country_pipeline_count
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": formatted_data,
                    **extra_data
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes 
        except Exception as e:
            # add line of where exception comes from
            self.app_debug_print(f"Error in fetch_data: > 1 {str(e)} {exception_line_info(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
  
    async def fetch_system_country_availlable_currencies(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Convert query parameters to dictionary
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params)

            item_id = query_params.get('item_id', None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            sort = request.query_params.get("sort", {'created_at':-1})
            self.app_debug_print(f"Query Parameters (SORT): {sort}",False)
            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    "filter___id":item_id
                },
                user=user_details,
                sort=sort
            )
            if not data:
                message = self.get_response_message(MessageCategory.COMMON, "NO_SUCH_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            self.app_debug_print(f"Query data: {len(data)}",False)
            cfg_system_country_id = extract_field_on_output_data_element(data,'id',output_data_type)
            formatted_data = []
            list_of_availlable_currencies = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_CURRENCY,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    "filter__cfg_system_country_id":cfg_system_country_id
                },
                user=user_details,
                sort=sort
            )

            self.app_debug_print(f"Query list_of_availlable_currencies: {len(list_of_availlable_currencies)}",True)
            all_currencies = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_CURRENCY,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={},
                user=user_details,
                sort=sort
            )
        
            for element in all_currencies:
                ref_currency_id = extract_field_on_output_data_element(element,'id',output_data_type)

                # check if currency is in list_of_availlable_currencies
                is_currency_availlable = False
                for currency in list_of_availlable_currencies:
                    ref_currency_id_availlable = extract_field_on_output_data_element(currency,'ref_currency_id',output_data_type)
                    if ref_currency_id_availlable == ref_currency_id:
                        is_currency_availlable = True
                        break 
                if is_currency_availlable:
                    continue 

                formatted_data.append({
                    **element,
                }) 
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": formatted_data,
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            # add line of where exception comes from
            self.app_debug_print(f"Error in fetch_data: > 1 {str(e)} {exception_line_info(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    async def fetch_no_existing_countries(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Convert query parameters to dictionary
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)

            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            sort = request.query_params.get("sort", {'created_at':-1})
            self.app_debug_print(f"Query Parameters (SORT): {sort}",True)
            # Fetch data from the collection using CollectionKey
            sort = self.process_sort(sort)
            self.app_debug_print(f"PROCESSED (SORT): {sort}",True)
            country_pipeline = [
                {
                    "$lookup": {
                        "from": f"{CollectionKey.REF_ENTITY.model_name}",
                        "localField": "_id",
                        "foreignField": "ref_country_id",
                        "as": "unwind__ref_entity"
                    }
                },
                {
                    "$match": {
                        "unwind__ref_entity": {
                            "$size": 0
                        }
                    }
                },
                {
                    "$skip":limit * page
                },
                {
                    "$limit":limit
                },
                {
                    "$sort":sort
                }
            ]
            data = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.REF_COUNTRY,
                output_data_type=OutputDataType(output_data_type).value,
                all_data=all_data,
                page=page,
                limit=limit,
                accept_language=self.accept_language,
                pipeline=country_pipeline, 
                # sort=sort
            )
            self.app_debug_print(f"Query data: {len(data)}",False)
            extra_data = {}
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                country_pipeline_count = [
                    {
                        "$lookup": {
                            "from": f"{CollectionKey.REF_ENTITY.model_name}",
                            "localField": "_id",
                            "foreignField": "ref_country_id",
                            "as": "unwind__ref_entity"
                        }
                    },
                    {
                        "$match": {
                            "unwind__ref_entity": {
                                "$size": 0
                            }
                        }
                    }, 
                ]
                # get max
                max_data = await self.generic_service.fetch_native_aggregate_count_from_collection(
                    collection_key=CollectionKey.REF_COUNTRY,
                    accept_language=self.accept_language,
                    pipeline=country_pipeline_count
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": data,
                    **extra_data
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch_data: > 1 {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
        
    async def fetch_all_existing_countries(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Convert query parameters to dictionary
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)

            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            sort = request.query_params.get("sort", {'created_at':-1})
            self.app_debug_print(f"Query Parameters (SORT): {sort}",True)
            # Fetch data from the collection using CollectionKey
            sort = self.process_sort(sort)
            self.app_debug_print(f"PROCESSED (SORT): {sort}",True)
            country_pipeline = [
                # {
                #     "$lookup": {
                #         "from": "ref_entity",
                #         "localField": "_id",
                #         "foreignField": "ref_country_id",
                #         "as": "unwind__ref_entity"
                #     }
                # },
                # {
                #     "$match": {
                #         "unwind__ref_entity": {
                #             "$size": 0
                #         }
                #     }
                # },
                {
                    "$skip":limit * page
                },
                {
                    "$limit":limit
                },
                {
                    "$sort":sort
                }
            ]
            data = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.REF_COUNTRY,
                output_data_type=OutputDataType(output_data_type).value,
                all_data=all_data,
                page=page,
                limit=limit,
                accept_language=self.accept_language,
                pipeline=country_pipeline, 
                # sort=sort
            )
            self.app_debug_print(f"Query data: {len(data)}",False)
            extra_data = {}
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                country_pipeline_count = [
                    # {
                    #     "$lookup": {
                    #         "from": "ref_entity",
                    #         "localField": "_id",
                    #         "foreignField": "ref_country_id",
                    #         "as": "unwind__ref_entity"
                    #     }
                    # },
                    # {
                    #     "$match": {
                    #         "unwind__ref_entity": {
                    #             "$size": 0
                    #         }
                    #     }
                    # }, 
                ]
                # get max
                max_data = await self.generic_service.fetch_native_aggregate_count_from_collection(
                    collection_key=CollectionKey.REF_COUNTRY,
                    accept_language=self.accept_language,
                    pipeline=country_pipeline_count
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": data,
                    **extra_data
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch_data: > 1 {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    async def patch_system_country_to_add_remove_country_code_process(
        self,
        request: Request,
        body: dict = Body(...)
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            self.app_debug_print(f"\n\nbody : {body}\n\n",True)

            # get item_id from params
            raw_query_params: Dict[str, str] = dict(request.query_params)
            item_id = raw_query_params.get('item_id', None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            flag = body.get('flag', None)
            if not flag:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_FLAG_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            country_codes = body.get('country_codes', [])
            if not len(country_codes):
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_COUNTRY_CODES_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            system_country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                accept_language=self.accept_language,
                query={
                    "filter___id":item_id
                },
                user=user_details
            )
            if not system_country:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_SYSTEM_COUNTRY_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            if flag == 'add':
                for country_code in country_codes:
                    await self.add_country_code_to_system_country(
                        country_code=country_code,
                        item_id=item_id
                    )
            else:
                # Keep only those entries whose code is not in country_codes
                for country_code in country_codes:
                    # delete from cfg_country_related_country_code
                    await self.generic_service.hard_delete_with_query_data_from_collection(
                        collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                        query={
                            "country_code":country_code,
                            "cfg_system_country_id":ObjectId(item_id)
                        }
                    ) 
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=error_detail)
        

    async def patch_system_country_to_add_remove_country_phone_prefix_process(
        self,
        request: Request,
        body: dict = Body(...)
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # get item_id from params
            raw_query_params: Dict[str, str] = dict(request.query_params)
            item_id = raw_query_params.get('item_id', None)
            ref_telephone_network_id = raw_query_params.get('ref_telephone_network_id', None)
            if not item_id or not ref_telephone_network_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            flag = body.get('flag', None)
            # ref_currency_id = body.get('ref_currency_id', None)
            # if not flag:
            #     message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_FLAG_PROVIDED", self.accept_language)
            #     raise HTTPException(status_code=400, detail=message)
        
            # if not ref_currency_id:
            #     message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_REF_CURRENCY_ID_PROVIDED", self.accept_language)
            #     raise HTTPException(status_code=400, detail=message)
            

            phone_number_prefixes = body.get('phone_number_prefixes', [])
            if not len(phone_number_prefixes):
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_PHONE_NUMBER_PREFIXES_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            system_country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                accept_language=self.accept_language,
                query={
                    "filter___id":item_id
                },
                user=user_details
            )
            if not system_country:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_SYSTEM_COUNTRY_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            if flag == 'add':

                for phone_number_prefix in phone_number_prefixes:
                    await self.add_phone_number_prefix_to_system_country(
                        phone_number_prefix=phone_number_prefix,
                        item_id=item_id,
                        ref_telephone_network_id=ref_telephone_network_id
                    )
                # formated_phone_number_prefixes = system_country.get('phone_number_prefixes', [])
                # for phone_number_prefix in phone_number_prefixes:
                #     if phone_number_prefix not in [entry.get("prefix") for entry in formated_phone_number_prefixes]:
                #         formated_phone_number_prefixes.append({
                #             "prefix": phone_number_prefix
                #         })
                # system_country['phone_number_prefixes'] = formated_phone_number_prefixes.copy()
            else:
                for phone_number_prefix in phone_number_prefixes:
                    # delete from cfg_country_related_phone_number_prefix
                    await self.generic_service.hard_delete_with_query_data_from_collection(
                        collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                        query={
                            "prefix":phone_number_prefix,
                            "cfg_system_country_id":ObjectId(item_id),
                            "ref_telephone_network_id":ObjectId(ref_telephone_network_id)
                        }
                    )  
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=error_detail)
    
 
    async def patch_system_country_to_add_remove_currency_process(
        self,
        request: Request,
        body: dict = Body(...)
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # get item_id from params
            raw_query_params: Dict[str, str] = dict(request.query_params)
            item_id = raw_query_params.get('item_id', None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            flag = body.get('flag', None)
            if not flag:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_FLAG_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            currency_id = body.get('currency_id', None)
            if not currency_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_CURRENCY_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            system_country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter___id":item_id
                }
            )
            if not system_country:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_SYSTEM_COUNTRY_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            if flag == 'add':
                await self.add_currency_to_system_country(
                    ref_currency_id=currency_id,
                    item_id=item_id
                )
            else:
                await self.remove_currency_from_system_country(
                    ref_currency_id=currency_id,
                    item_id=item_id
                )
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=error_detail)

    async def add_system_country(
        self,
        request: Request,
        body: dict = Body(...)
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            formated_body = SystemCountryCreate.model_validate(body, context={"language": self.accept_language})


            named_entity = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__named_entity_flag": 'country',
                }
            )
            if not named_entity:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_NAMED_ENTITY_FOR_COUNTRY_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)


            # get country details
            country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_COUNTRY,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id": formated_body.country_id,
                }
            )
            if not country:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_COUNTRY_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # check if country already exist by name
            existing_country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__ref_named_entity_id": named_entity['id'],
                    "filter__name": str(country.get('name','')).strip().lower(),
                }
            )

            self.app_debug_print(f"\n\n existing_country data : {existing_country}\n\n",True)

            if existing_country:
                result = existing_country['id']
                update_data = {
                    "ref_entity_id":None,
                    "ref_country_id":formated_body.country_id,
                }
                self.app_debug_print(f"\n\n update_data : {update_data}\n\n",True)
                await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.REF_ENTITY,
                    item_id=existing_country['id'],
                    update_data=update_data,
                    user=user_details,
                    accept_language=self.accept_language
                )
            else:
                # Add data to the collection
                data = {
                        # "min_phone_number_chars":formated_body.min_phone_number_chars,
                        # "max_phone_number_chars":formated_body.max_phone_number_chars,
                        "name": str(existing_country['name']).strip().lower(),
                        "ref_entity_id":None,
                        "ref_country_id":formated_body.country_id,
                        "ref_named_entity_id": named_entity['id']
                }
                self.app_debug_print(f"\n\n new country data : {data}\n\n",True)
                result = await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.REF_ENTITY,
                    data=data,
                    user=user_details,
                    accept_language=self.accept_language
                )
            self.app_debug_print(f"\n\n result : {result}\n\n",True)

            # save related min max
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_RELATED_MIN_MAX,
                filter_data={
                    "targeted_id": result
                },
                update_data={
                    "targeted_id": result,
                    "min":formated_body.min_phone_number_chars,
                    "max":formated_body.max_phone_number_chars,
                },
                user=user_details,
            )

            # save country reloated data
            for currency in formated_body.currencies:
                await self.add_currency_to_system_country(
                    ref_currency_id=currency,
                    item_id=result
                )
            for country_code in formated_body.country_codes:
                await self.add_country_code_to_system_country(
                    country_code=country_code,
                    item_id=result
                )
             

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=error_detail)
        

    async def delete_system_country(
        self,
        request: Request,
    ):
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # get item_id from params
            raw_query_params: Dict[str, str] = dict(request.query_params)
            item_id = raw_query_params.get('item_id', None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            # check if system country exist
            system_country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id": item_id
                }
            )
            if not system_country:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # delete from cfg_system_country
            await self.generic_service.hard_delete_data_from_collection(
                collection_key=CollectionKey.CFG_SYSTEM_COUNTRY,
                item_id=item_id
            )
            # delete from cfg_country_related_currency
            await self.generic_service.hard_delete_many_query_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_CURRENCY,
                delete_query={
                    "cfg_system_country_id":ObjectId(item_id)
                }
            )
            # delete from cfg_country_related_country_code
            await self.generic_service.hard_delete_many_query_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                delete_query={
                    "cfg_system_country_id":ObjectId(item_id)
                }
            )
            # delete from cfg_country_related_phone_prefix
            await self.generic_service.hard_delete_many_query_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                delete_query={
                    "cfg_system_country_id":ObjectId(item_id)
                }
            )
            

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)  
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "data": None,
                }
            )
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=error_detail)

    async def add_currency_to_system_country(
        self,
        ref_currency_id: str,
        item_id: str
    ):
        try:

            data = {
                "ref_currency_id":ref_currency_id,
                "cfg_system_country_id":item_id
            }
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_CURRENCY,
                filter_data=data,
                update_data=data,
            )
            return True
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=error_detail)

    async def remove_currency_from_system_country(
        self,
        ref_currency_id: str,
        item_id: str
    ):
        try:
            # Delete the currency relationship from cfg_country_related_currency
            deletion = await self.generic_service.hard_delete_with_query_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_CURRENCY,
                query={
                    "ref_currency_id": ObjectId(ref_currency_id),
                    "cfg_system_country_id": ObjectId(item_id)
                }
            )
            self.app_debug_print(f"\n\n deletion : {deletion}\n\n", True)
            return True
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=error_detail)

    async def add_country_code_to_system_country(
        self,
        country_code: str,
        item_id: str
    ):
        try: 
            # Fetch data from the collection using CollectionKey
            system_country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter___id": item_id
                }
            )
            if not system_country:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language)
                message = line_info(message)
                raise HTTPException(status_code=400, detail=message)
            if not system_country.get('ref_country_id'):
                ref_country = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_COUNTRY,
                    output_data_type=OutputDataType.DEFAULT,
                    accept_language= self.accept_language,
                    query={
                        "filter__code":country_code
                    }
                )
                if ref_country:
                    await self.generic_service.update_data_in_collection(
                        collection_key=CollectionKey.REF_ENTITY,
                        item_id=item_id,
                        data={
                            "ref_country_id":ref_country['id']
                        }
                    )
            
            data = {
                "country_code":country_code,
                "cfg_system_country_id":item_id
            }
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                filter_data=data,
                update_data=data,
            )
            return True 
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=error_detail)
        

    async def add_phone_number_prefix_to_system_country(
        self,
        phone_number_prefix: str,
        item_id: str,
        ref_telephone_network_id: str
    ):
        try: # Check if collection is exposed
            system_country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter___id": item_id
                }
            )
            if not system_country:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language)
                message = line_info(message)
                raise HTTPException(status_code=400, detail=message)
            
            data = {
                "prefix":phone_number_prefix,
                "cfg_system_country_id":item_id,
                "ref_telephone_network_id":ref_telephone_network_id
            }
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                filter_data=data,
                update_data=data,
            )
            return True 
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=error_detail)

   
    async def fetch_telephone_networks(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Convert query parameters to dictionary
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            sort = request.query_params.get("sort", {'created_at':-1})
            self.app_debug_print(f"Query Parameters (SORT): {sort}",True)
            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_TELEPHONE_NETWORK,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    **query_params
                },
                user=user_details,
                sort=sort
            )
            self.app_debug_print(f"Query data: {len(data)}", False)
            extra_data = {}
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.REF_TELEPHONE_NETWORK,
                    accept_language=self.accept_language,
                    query={
                        **query_params
                    },
                    user=user_details
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": data,
                    **extra_data
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch_data: > 1 {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
        
 
    async def fetch_telephone_network_prefixes(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: # Check if collection is exposed
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # Convert query parameters to dictionary
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            sort = request.query_params.get("sort", {'created_at':-1})
            self.app_debug_print(f"Query Parameters (SORT): {sort}",True)
            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    **query_params
                },
                user=user_details,
                sort=sort
            )
            self.app_debug_print(f"Query data: {len(data)}",True)
            extra_data = {}
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                    accept_language=self.accept_language,
                    query={
                        **query_params
                    },
                    user=user_details
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": data,
                    **extra_data
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch_data: > 1 {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    async def delete_telephone_network(
        self,
        request: Request,
        body: dict = Body(...)
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: # Check if collection is exposed
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # get item_id from params
            raw_query_params: Dict[str, str] = dict(request.query_params)
            item_id = raw_query_params.get('item_id', None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            # check if telephone network exist
            telnet = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_TELEPHONE_NETWORK,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id": item_id
                }
            )
            if not telnet:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            
            # delete from cfg_telephone_network
            await self.generic_service.hard_delete_data_from_collection(
                collection_key=CollectionKey.REF_TELEPHONE_NETWORK,
                item_id=item_id
            )

            # delete from cfg_country_related_phone_prefix
            await self.generic_service.hard_delete_many_query_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                delete_query={
                    "ref_telephone_network_id":ObjectId(item_id)
                }
            )

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)  
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "data": None,
                }
            )
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=error_detail)
        

    async def fetch_registration_system_country(self,request:Request):
        """
        Fetch all cfg_system_country, build a tree from country to town using ref_named_entity, and return the tree array ending at town.
        """
        try:
            # Fetch all cfg_system_country
            # First, get all named entities with flag 'country'
            country_named_entities = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__named_entity_flag": "country"},
                all_data=True
            )
            
            # Extract IDs of country named entities
            country_named_entity_ids = [str(entity.get("id")) for entity in country_named_entities if entity.get("id")]
            self.app_debug_print(f"Found {len(country_named_entity_ids)} country named entities", True)
            
            # Now fetch entities with ref_named_entity_id in the list of country named entity IDs
            if country_named_entity_ids:
                system_countries = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.REF_ENTITY,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__ref_named_entity_id__in": country_named_entity_ids},
                    all_data=True
                )
            else:
                system_countries = []
            self.app_debug_print(f"System Countries: {len(system_countries)}", True)

            # Fetch all named entities to use for flag filtering
            all_named_entities = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={},
                all_data=True
            )
            
            # Build a lookup for named_entity by id
            named_entity_lookup = {str(ent.get("id")): ent for ent in all_named_entities}
            # Function to build a tree for a specific node level
            async def build_tree_level(entity_id, level_flag, next_level_flag=None):
                # Fetch direct children of this entity
                self.app_debug_print(f"Fetching children for entity_id: {entity_id}", True)
                # Try multiple query approaches to find all children
                try:
                    # First, try with filter___ref_entity_id (3 underscores)
                    self.app_debug_print(f"Querying for children with ref_entity_id: {entity_id}", True)

                    children = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.REF_ENTITY,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___ref_entity_id": entity_id},
                        all_data=True
                    )
                    
                    # If that didn't work and ID is a string that can be an ObjectId, try that
                    if (not children or len(children) == 0) and isinstance(entity_id, str) and ObjectId.is_valid(entity_id):
                        self.app_debug_print(f"Trying ObjectId format for ref_entity_id: {entity_id}", True)
                        children = await self.generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.REF_ENTITY,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={"filter___ref_entity_id": ObjectId(entity_id)},
                            all_data=True
                        )
                    
                    # If we still have no children, try using the full entity object approach
                    if not children or len(children) == 0:
                        self.app_debug_print(f"Trying alternate approach to find children", True)
                        all_entities = await self.generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.REF_ENTITY,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={},
                            all_data=True
                        )
                        
                        # Filter entities manually
                        children = []
                        for e in all_entities:
                            ref_id = e.get("ref_entity_id")
                            if ref_id and (str(ref_id) == str(entity_id)):
                                children.append(e)
                                self.app_debug_print(f"Found child through manual filtering: {e.get('name')}", True)
                                
                    self.app_debug_print(f"Found {len(children) if children else 0} children for entity_id: {entity_id}", True)
                except Exception as e:
                    self.app_debug_print(f"Error fetching children: {str(e)}", True)
                    children = []
                
                self.app_debug_print(f"Found {len(children) if children else 0} children for entity_id: {entity_id}", True)
                
                result_children = []
                
                # Process each child
                for child in children:
                    named_entity_id = child.get("ref_named_entity_id")
                    if not named_entity_id:
                        continue
                        
                    named_entity = named_entity_lookup.get(str(named_entity_id))
                    if not named_entity:
                        continue
                    
                    # Get the named entity flag or use a default value    
                    child_flag = named_entity.get("named_entity_flag", "")
                    
                    # Log the child entity and its flag
                    self.app_debug_print(f"Child entity: {child.get('name')}, flag: {child_flag}, expected: {level_flag}", True)
                    
                    # Always include children regardless of flag match
                    # We'll assign the expected flag based on level
                    if level_flag == "province" and child_flag != "province":
                        child_flag = "province"
                        self.app_debug_print(f"Assigning province flag to entity {child.get('name')}", True)
                    elif level_flag == "town" and child_flag != "town":
                        child_flag = "town"
                        self.app_debug_print(f"Assigning town flag to entity {child.get('name')}", True)
                    
                    child_node = {
                        "id": str(child.get("id")),
                        "name": child.get("name"),
                        "named_entity_flag": child_flag,
                        "children": []
                    }
                    
                    # If we need to fetch the next level
                    if next_level_flag:
                        next_level_children = await build_tree_level(child.get("id"), next_level_flag)
                        if next_level_children and len(next_level_children) > 0:
                            child_node["children"] = next_level_children
                            self.app_debug_print(f"Added {len(next_level_children)} {next_level_flag} children to {child.get('name')}", True)
                        else:
                            # If no children found through normal means, try manual lookup for towns
                            self.app_debug_print(f"No {next_level_flag} found for {child.get('name')}, trying manual lookup", True)
                            
                            # Look for entities that have this entity as parent
                            all_potential_children = await self.generic_service.fetch_data_from_collection(
                                collection_key=CollectionKey.REF_ENTITY,
                                output_data_type=OutputDataType.DEFAULT.value,
                                query={},
                                all_data=True
                            )
                            
                            child_id = child.get("id")
                            town_nodes = []
                            
                            for potential_child in all_potential_children:
                                parent_entity_id = potential_child.get("parent_entity_id")
                                if parent_entity_id and (str(parent_entity_id) == str(child_id)):
                                    town_node = {
                                        "id": str(potential_child.get("id")),
                                        "name": potential_child.get("name"),
                                        "named_entity_flag": next_level_flag,
                                        "children": []
                                    }
                                    town_nodes.append(town_node)
                                    self.app_debug_print(f"Manually added {next_level_flag} {potential_child.get('name')} to {child.get('name')}", True)
                            
                            child_node["children"] = town_nodes
                    
                    result_children.append(child_node)
                
                return result_children
            

            # Result array for trees
            result_trees = []
            for country in system_countries:
                entity_id = country.get("id")

                named_entity_info = [str(entity.get("named_entity_flag")) for entity in country_named_entities if str(entity.get("id")) == str(country.get("ref_named_entity_id"))]
                self.app_debug_print(f"System Countries named_entity_info: {named_entity_info}", True)
                if named_entity_info:
                    named_entity_flag = named_entity_info[0]
                # Create the country node
                country_codes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__cfg_system_country_id": entity_id},
                    all_data=True
                )

                telephone_prefixes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__cfg_system_country_id": entity_id},
                    all_data=True
                )

                map_country_codes = [{"id": c["id"], "country_code": c["country_code"]} for c in country_codes]
                map_telephone_prefixes =  [{"id": t["id"], "prefix": t["prefix"]} for t in telephone_prefixes]

                # Get provinces (children of country) named_entity_lookup
                province_children = await build_tree_level(entity_id, "province", "town")

                country_node = {
                    "id": entity_id,
                    "name": country.get("name"),
                    "named_entity_flag":named_entity_flag,
                    "country_codes":map_country_codes,
                    "telephone_prefixes":map_telephone_prefixes,
                    "country_flag": country.get("country_flag"), #  
                    "system_country_id":entity_id,
                    "children": []
                }
                country_node["children"] = province_children

                # Add to results
                result_trees.append(country_node) 
            self.app_debug_print(f"Final filtered trees: {len(result_trees)}", True)
            
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "System country registration tree fetched successfully",
                    "data": result_trees
                }
            )
        except Exception as e:
            formated_error = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"Error in fetch_registration_system_country: {formated_error}", True)
            raise HTTPException(status_code=500, detail=str(e))

    async def fetch_registration_system_countryXXXXx(self,request:Request):
        """
        Fetch all cfg_system_country, build a tree from country to town using ref_named_entity, and return the tree array ending at town.
        """
        try:
            # Fetch all cfg_system_country
            # First, get all named entities with flag 'country'
            country_named_entities = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__named_entity_flag": "country"},
                all_data=True
            )
            
            # Extract IDs of country named entities
            country_named_entity_ids = [str(entity.get("id")) for entity in country_named_entities if entity.get("id")]
            self.app_debug_print(f"Found {len(country_named_entity_ids)} country named entities", True)
            
            # Now fetch entities with ref_named_entity_id in the list of country named entity IDs
            if country_named_entity_ids:
                system_countries = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.REF_ENTITY,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__ref_named_entity_id__in": country_named_entity_ids},
                    all_data=True
                )
            else:
                system_countries = []
            self.app_debug_print(f"System Countries: {len(system_countries)}", True)

            # Get unique entity IDs from system_countries
            entity_ids = []
            country_entity_map = {}  # Maps entity_id to system_country_id
            
            for country in system_countries:
                entity_id = country.get("id")
                if entity_id:
                    entity_id_str = str(entity_id)
                    if entity_id_str not in entity_ids:
                        entity_ids.append(entity_id_str)
                        ref_country = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.REF_COUNTRY,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={"filter___id": country.get("ref_country_id")}
                        )
                        if ref_country:
                            # add flag to country_entity_map
                            key = f"{entity_id_str}__flag"
                            country_entity_map[key] = ref_country.get("flag")
                        country_entity_map[entity_id_str] = str(country.get("id"))
                    self.app_debug_print(f"System country: {country.get('id')}, ref_entity_id: {entity_id}", True)

            self.app_debug_print(f"Unique Entity IDs: {entity_ids}", True)
            
            # Fetch all named entities to use for flag filtering
            all_named_entities = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={},
                all_data=True
            )
            
            # Build a lookup for named_entity by id
            named_entity_lookup = {str(ent.get("id")): ent for ent in all_named_entities}
            self.app_debug_print(f"Named Entity Lookup created with {len(named_entity_lookup)} entries", True)
            
            # Fetch parent country entities directly
            country_entities = []
            for entity_id in entity_ids:
                # The issue may be with filter___id vs filter___id (3 underscores)
                # Try both formats for ID filtering to ensure we find the entity
                entity = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_ENTITY,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id": entity_id}  # Using filter with 3 underscores
                )
                
                if not entity and ObjectId.is_valid(entity_id):
                    # Try with ObjectId
                    entity = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_ENTITY,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___id": ObjectId(entity_id)}
                    )
                
                self.app_debug_print(f"Fetched entity for ID {entity_id}: {entity is not None}", True)
                
                if entity:
                    # Add this entity as a country regardless of its named_entity_flag
                    # since it's referenced in cfg_system_country
                    country_entities.append(entity)
                    self.app_debug_print(f"Added entity {entity.get('name')} to country entities", True)
            
            self.app_debug_print(f"Found {len(country_entities)} country entities", True)
            
            # Function to build a tree for a specific node level
            async def build_tree_level(entity_id, level_flag, next_level_flag=None):
                # Fetch direct children of this entity
                self.app_debug_print(f"Fetching children for entity_id: {entity_id}", True)
                # Try multiple query approaches to find all children
                try:
                    # First, try with filter___ref_entity_id (3 underscores)
                    self.app_debug_print(f"Querying for children with ref_entity_id: {entity_id}", True)

                    children = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.REF_ENTITY,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___ref_entity_id": entity_id},
                        all_data=True
                    )
                    
                    # If that didn't work and ID is a string that can be an ObjectId, try that
                    if (not children or len(children) == 0) and isinstance(entity_id, str) and ObjectId.is_valid(entity_id):
                        self.app_debug_print(f"Trying ObjectId format for ref_entity_id: {entity_id}", True)
                        children = await self.generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.REF_ENTITY,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={"filter___ref_entity_id": ObjectId(entity_id)},
                            all_data=True
                        )
                    
                    # If we still have no children, try using the full entity object approach
                    if not children or len(children) == 0:
                        self.app_debug_print(f"Trying alternate approach to find children", True)
                        all_entities = await self.generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.REF_ENTITY,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={},
                            all_data=True
                        )
                        
                        # Filter entities manually
                        children = []
                        for e in all_entities:
                            ref_id = e.get("ref_entity_id")
                            if ref_id and (str(ref_id) == str(entity_id)):
                                children.append(e)
                                self.app_debug_print(f"Found child through manual filtering: {e.get('name')}", True)
                                
                    self.app_debug_print(f"Found {len(children) if children else 0} children for entity_id: {entity_id}", True)
                except Exception as e:
                    self.app_debug_print(f"Error fetching children: {str(e)}", True)
                    children = []
                
                self.app_debug_print(f"Found {len(children) if children else 0} children for entity_id: {entity_id}", True)
                
                result_children = []
                
                # Process each child
                for child in children:
                    named_entity_id = child.get("ref_named_entity_id")
                    if not named_entity_id:
                        continue
                        
                    named_entity = named_entity_lookup.get(str(named_entity_id))
                    if not named_entity:
                        continue
                    
                    # Get the named entity flag or use a default value    
                    child_flag = named_entity.get("named_entity_flag", "")
                    
                    # Log the child entity and its flag
                    self.app_debug_print(f"Child entity: {child.get('name')}, flag: {child_flag}, expected: {level_flag}", True)
                    
                    # Always include children regardless of flag match
                    # We'll assign the expected flag based on level
                    if level_flag == "province" and child_flag != "province":
                        child_flag = "province"
                        self.app_debug_print(f"Assigning province flag to entity {child.get('name')}", True)
                    elif level_flag == "town" and child_flag != "town":
                        child_flag = "town"
                        self.app_debug_print(f"Assigning town flag to entity {child.get('name')}", True)
                    
                    child_node = {
                        "id": str(child.get("id")),
                        "name": child.get("name"),
                        "named_entity_flag": child_flag,
                        "children": []
                    }
                    
                    # If we need to fetch the next level
                    if next_level_flag:
                        next_level_children = await build_tree_level(child.get("id"), next_level_flag)
                        if next_level_children and len(next_level_children) > 0:
                            child_node["children"] = next_level_children
                            self.app_debug_print(f"Added {len(next_level_children)} {next_level_flag} children to {child.get('name')}", True)
                        else:
                            # If no children found through normal means, try manual lookup for towns
                            self.app_debug_print(f"No {next_level_flag} found for {child.get('name')}, trying manual lookup", True)
                            
                            # Look for entities that have this entity as parent
                            all_potential_children = await self.generic_service.fetch_data_from_collection(
                                collection_key=CollectionKey.REF_ENTITY,
                                output_data_type=OutputDataType.DEFAULT.value,
                                query={},
                                all_data=True
                            )
                            
                            child_id = child.get("id")
                            town_nodes = []
                            
                            for potential_child in all_potential_children:
                                parent_entity_id = potential_child.get("parent_entity_id")
                                if parent_entity_id and (str(parent_entity_id) == str(child_id)):
                                    town_node = {
                                        "id": str(potential_child.get("id")),
                                        "name": potential_child.get("name"),
                                        "named_entity_flag": next_level_flag,
                                        "children": []
                                    }
                                    town_nodes.append(town_node)
                                    self.app_debug_print(f"Manually added {next_level_flag} {potential_child.get('name')} to {child.get('name')}", True)
                            
                            child_node["children"] = town_nodes
                    
                    result_children.append(child_node)
                
                return result_children
            
            # Result array for trees
            result_trees = []
            
            # For each country entity, build a complete tree
            for country in country_entities:
                country_id = country.get("id")
                entity_id = str(country_id)
                
                # Get the named entity information
                named_entity_id = country.get("ref_named_entity_id")
                named_entity = named_entity_lookup.get(str(named_entity_id)) if named_entity_id else None
                
                # Log entity info for debugging
                self.app_debug_print(f"Processing country entity: {country.get('name')}, named_entity_id: {named_entity_id}", True)
                
                # Include the country even if named_entity_flag doesn't match
                # since it's referenced in cfg_system_country
                
                # Create the country node
                country_codes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__cfg_system_country_id": country_entity_map.get(entity_id, "")},
                    all_data=True
                )

                telephone_prefixes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__cfg_system_country_id": country_entity_map.get(entity_id, "")},
                    all_data=True
                )

                self.app_debug_print(f"Country {country.get('name')} has {len(country_codes)} country codes and {len(telephone_prefixes)} telephone prefixes", True)

                map_country_codes = [{"id": c["id"], "country_code": c["country_code"]} for c in country_codes]
                map_telephone_prefixes =  [{"id": t["id"], "prefix": t["prefix"]} for t in telephone_prefixes]

                key = f"{entity_id}__flag"
                country_node = {
                    "id": entity_id,
                    "name": country.get("name"),
                    "named_entity_flag": "country",
                    "country_codes":map_country_codes,
                    "telephone_prefixes":map_telephone_prefixes,
                    "country_flag": country.get("country_flag"), # country_entity_map.get(key, ""),
                    "system_country_id": country_entity_map.get(entity_id, ""),
                    "children": []
                }
                
                self.app_debug_print(f"Building tree for country: {country.get('name')} with ID: {country_id}", True)
                
                # Get provinces (children of country)
                province_children = await build_tree_level(country_id, "province", "town")
                
                if province_children and len(province_children) > 0:
                    country_node["children"] = province_children
                    self.app_debug_print(f"Added {len(province_children)} province children to country {country.get('name')}", True)
                else:
                    # If no provinces found, try a different query approach
                    self.app_debug_print(f"No provinces found, trying different query approaches", True)
                    
                    # Try with different filter formats
                    alternative_children1 = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.REF_ENTITY,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter__parent_ref_entity_id": country_id},  # Try different field name
                        all_data=True
                    )
                    
                    if alternative_children1 and len(alternative_children1) > 0:
                        self.app_debug_print(f"Found {len(alternative_children1)} children using parent_ref_entity_id", True)
                        direct_children = alternative_children1
                    else:
                        # If still nothing, try a generic query and filter manually
                        self.app_debug_print(f"Trying full collection scan", True)
                        direct_children = await self.generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.REF_ENTITY,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={},
                            all_data=True
                        )
                    
                    # Find any entities that reference this country as parent
                    province_nodes = []
                    for child in direct_children:
                        parent_id = child.get("parent_entity_id")
                        if parent_id and str(parent_id) == entity_id:
                            child_node = {
                                "id": str(child.get("id")),
                                "name": child.get("name"),
                                "named_entity_flag": "province",  # Assign province flag by default
                                "children": []
                            }
                            province_nodes.append(child_node)
                            self.app_debug_print(f"Added province {child.get('name')} to country {country.get('name')}", True)
                    
                    country_node["children"] = province_nodes
                
                # Add to results
                result_trees.append(country_node)
            
            self.app_debug_print(f"Final filtered trees: {len(result_trees)}", True)
            
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "System country registration tree fetched successfully",
                    "data": result_trees
                }
            )
        except Exception as e:
            formated_error = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"Error in fetch_registration_system_country: {formated_error}", True)
            raise HTTPException(status_code=500, detail=str(e))


    async def fetch_check_system_country_configuration(self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
        ):
        """
        Fetch all cfg_system_country, build a tree from country to town using ref_named_entity, and return the tree array ending at town.
        """
        try:
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            self.app_debug_print(f"\n\n\nRequest Path Params >>>: {request.query_params}", True)
            # get item_id from paramsss
            item_id = request.query_params.get("item_id")
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            # Fetch all cfg_system_country
            system_country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id":item_id
                },
            )
            if not system_country:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            # return CustomJSONResponse(
            #     status_code=status.HTTP_200_OK,
            #     content={
            #         "status_code": status.HTTP_200_OK,
            #         "message": "System country configuration checked successfully",
            #         "data": True
            #     }
            # )
            self.app_debug_print(f"\n\n\n Request system_country >>>: {system_country}", True)
            if 'ref_country_id' not in system_country:
                country = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_COUNTRY,
                    output_data_type=OutputDataType.DEFAULT.value,
                    user=user_details,
                    query={
                        "filter__name":str(system_country['name']).lower()
                    }
                )
                if country: 
                    update_data = {
                        "ref_entity_id": None,
                        "ref_country_id": country['id'],
                    }
                    self.app_debug_print(f"\n\n update_data : {update_data}\n\n",True)
                    await self.generic_service.update_data_in_collection(
                        collection_key=CollectionKey.REF_ENTITY,
                        item_id=system_country['id'],
                        data=update_data,
                        accept_language=self.accept_language
                    )
                    
            
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "System country configuration checked successfully",
                    "data": True
                }
            )
        except PermissionError:
            self.app_debug_print(f"Error in fetch_check_system_country_configuration: Access denied", True)
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            formated_error = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"Error in fetch_check_system_country_configuration: > 1 {formated_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")



    async def init_customer_registration(self, request: Request, background_tasks: BackgroundTasks):
        try:
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_activated": True
                }
            )
            
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG",self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            support_email = await self.get_system_support_email(saas_config_info,self.accept_language) 

            # DEVICE CHECKING   
            device_hashed_id = getattr(request.state, "deviceHashedId", None)
            if not device_hashed_id:
                message = self.get_response_message(MessageCategory.COMMON, "NO_EXISTING_USER_DEVICE",self.accept_language,email=support_email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            
            # GENERATE UNIQUE REGISTRATION KEY TO SAVE IN REDIS
            registration_key = self.generator_service.generate_encryption_key()

            # SAVE IN REDIS
            cache_key = self._generate_cache_key(
                user_id=f"{registration_key}",
                method_name='registration_process',
            )

            # Prepare response data
            response_data = {
                "data": registration_key,
                "device_id_str":device_hashed_id,
                "api_consumer":api_Consumer['id']
            }
            print(f"\n\n\n\n\n\n registration_key response_data : {response_data}")

            # 2. Cache the response data (with verification)
            minutes = 60 * 1
            await self._set_cached_data(cache_key, response_data, ttl=minutes) 

            system_country = await SystemCountryService(self.accept_language).get_registration_system_country()
            print(f">> system_country : {system_country}")
            registration_token = self.token_service.create_access_token(
                data={"sub": f"{cache_key}", "device_id_str":device_hashed_id, "type":EJWTTokenType.REGISTRATION_PROCESS},
                token_type=EJWTTokenType.REGISTRATION_PROCESS,
                expires_delta=timedelta(minutes=minutes)  # Expires after 40 minutes 400
            )
            formated_data = {
                "countries":system_country,
                "token":registration_token
            }
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "success":True,
                        "status_code":status.HTTP_200_OK, 
                        "data":formated_data
                    }
                )
        except Exception as e:
            self.app_debug_print(f"{e}",True)
            # Get translated message
            message = self.get_response_message(MessageCategory.EXCEPTIONS, "INTERNAL_ERROR", self.accept_language)
            # Check if the exception is an HTTPException
            if isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=e.status_code,
                    detail=e.detail or message
                )
            else:
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )



    async def fetch_current_entity_default_currency(self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
        ):
        """
        Fetch current entity default currency
        """
        try:
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            self.app_debug_print(f"\n\n\nRequest Path Params >>>: {request.query_params}", True)
            # get item_id from paramsss
            item_id = request.query_params.get("item_id")
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            # Fetch system_country
            system_country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id":item_id
                },
            )
            if not system_country:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # check if ref_country_id is in system_country
            default_currency = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_DEFAULT_RELATED_CURRENCY,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__targeted_id":system_country['id']
                },
            )
            self.app_debug_print(f"\n\n\n Request system_country >>>: {default_currency}", True)
            currency = None
            if default_currency:
                currency = {
                    "ref_currency_id":str(default_currency['ref_currency_id']),
                    "id":default_currency['id'],
                    "targeted_id":str(default_currency['targeted_id'])
                }
            
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "System country default currency fetched successfully",
                    "data": currency
                }
            )
        except PermissionError:
            self.app_debug_print(f"Error in fetch_current_entity_default_currency: Access denied", True)
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            formated_error = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"Error in fetch_current_entity_default_currency: > 1 {formated_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    async def fetch_current_entity_info(self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
        ):
        """
        Fetch current entity info
        """
        try:
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            self.app_debug_print(f"\n\n\nRequest Path Params >>>: {request.query_params}", True)
            # get item_id from paramsss
            item_id = request.query_params.get("item_id")
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            # Fetch system_country
            system_country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id":item_id
                },
            )
            if not system_country:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            ref_named_entity = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id":system_country['ref_named_entity_id']
                },
            )
            formated_info = {
                "id":system_country['id'],
                "name":system_country['name'],
                "country_flag":system_country['country_flag'],
                "min_phone_number_chars":system_country['min_phone_number_chars'],
                "max_phone_number_chars":system_country['max_phone_number_chars'],
                "min_ewallet_number_chars":system_country['min_ewallet_number_chars'],
                "max_ewallet_number_chars":system_country['max_ewallet_number_chars'],
                "ref_named_entity":{
                    "id":ref_named_entity['id'],
                    "name":ref_named_entity['name'],
                    "identifier":ref_named_entity['identifier']
                }
            }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "System country info fetched successfully",
                    "data": formated_info
                }
            )
        except PermissionError:
            self.app_debug_print(f"Error in fetch_current_entity_info: Access denied", True)
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            format_error = format_exception("HTTPException occurred", e)
            self.app_debug_print(f"Error in fetch_current_entity_info: HTTPException {format_error}", True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    async def update_current_entity_default_currency(
        self,
        request: Request,
        body: dict = Body(...)
    ):
        """
        Update current entity default currency
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # get item_id from params
            raw_query_params: Dict[str, str] = dict(request.query_params)
            item_id = raw_query_params.get('item_id', None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            currency_id = body.get('currency_id', None)
            if not currency_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_CURRENCY_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # check if system country exist
            system_country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id": item_id
                }
            )
            if not system_country:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # check if currency exist
            currency = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_CURRENCY,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id": currency_id
                }
            )
            if not currency:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # update default currency
            update_data = {
                "targeted_id": system_country['id'],
                "ref_currency_id": currency['id']
            }
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_DEFAULT_RELATED_CURRENCY,
                filter_data={"targeted_id": system_country['id']},
                update_data=update_data,
                user=user_details,
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Current entity default currency updated successfully",
                    "data": True
                }
            )
        except PermissionError:
            self.app_debug_print(f"Error in update_current_entity_default_currency: Access denied", True)
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            formated_error = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"Error in update_current_entity_default_currency: > 1 {formated_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
    async def patch_current_entity_flag(
        self,
        request: Request,
        body: dict = Body(...)
    ):
        """
        Update current entity default currency
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            self.app_debug_print(f"\n\n\nRequest Path Params >>>: {request.query_params}", True)
            self.app_debug_print(f"\n\n\nRequest body >>>: {body}", True)
            ref_country_id = body.get('ref_country_id', None)
            ref_entity_id = body.get('ref_entity_id', None)
            if not ref_country_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_COUNTRY_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            if not ref_entity_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ENTITY_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            # get item_id from params
            raw_query_params: Dict[str, str] = dict(request.query_params)
            item_id = raw_query_params.get('item_id', None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            

            # check if system country exist
            ref_country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id": item_id
                }
            )
            system_country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_COUNTRY,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id": ref_country_id
                }
            )
            if not system_country or not ref_country:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.REF_ENTITY,
                item_id=ref_entity_id,
                data={
                    "ref_country_id": ref_country_id,
                    "country_flag": system_country.get("flag")
                }
            ) 

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                    "data": True
                }
            )
        except PermissionError:
            self.app_debug_print(f"Error in update_current_entity_default_currency: Access denied", True)
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            formated_error = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"Error in update_current_entity_default_currency: > 1 {formated_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    async def fetch_system_country_currencies(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Fetch currencies associated with a specific country.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Convert query parameters to dictionary
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            sort = request.query_params.get("sort", {'created_at':-1})
            self.app_debug_print(f"Query Parameters (SORT): {sort}",True)
            item_id = request.query_params.get('filter__cfg_system_country_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            ref_entity = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id": item_id
                }
            )
            if not ref_entity:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # Fetch data from the collection using CollectionKey
            query_params = {
                **query_params,
                # "filter__cfg_system_country_id": str(ref_entity.get("id"))
            }
            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_CURRENCY,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType.DATA_TABLE.value,
                accept_language=self.accept_language,
                query={
                    **query_params
                },
                user=user_details,
                sort=sort
            )
            formated_currency = []
            for currency in data:
                ref_currency_id = currency.get('ref_currency_id',{}).get('real_value',None) # extract_field_on_output_data_element(currency,"ref_currency_id",OutputDataType.DATA_TABLE.value)
                self.app_debug_print(f"Query ref_currency_id: {ref_currency_id}", False)
                currency_info = {}
                if ref_currency_id:
                    currency_info = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_CURRENCY,
                        output_data_type=OutputDataType.DATA_TABLE.value,
                        accept_language=self.accept_language,
                        user=user_details,
                        query={"filter___id": ref_currency_id}
                    )
                formated_currency.append({
                    **currency,
                    "ref_currency":currency_info,
                })
            self.app_debug_print(f"Query data currencies : {len(formated_currency)}", False)
            extra_data = {}
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_CURRENCY,
                    accept_language=self.accept_language,
                    query={
                        **query_params
                    },
                    user=user_details
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": formated_currency,
                    **extra_data
                }
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            formated_error = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"Error in fetch_system_country_currencies: > 1 {formated_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
  
    async def fetch_system_country_codes(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Fetch country codes associated with a specific country.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # Convert query parameters to dictionary
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            sort = request.query_params.get("sort", {'created_at':-1})
            self.app_debug_print(f"Query Parameters (SORT): {sort}",True)
            item_id = request.query_params.get('filter__cfg_system_country_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            ref_entity = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id": item_id
                }
            )
            if not ref_entity:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)


            # Fetch data from the collection using CollectionKey
            query_params = {
                **query_params,
                # "filter__cfg_system_country_id": str(ref_entity.get("id"))
            }
            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType.DATA_TABLE.value,
                accept_language=self.accept_language,
                query={
                    **query_params
                },
                user=user_details,
                sort=sort
            )
            self.app_debug_print(f"Query data: {len(data)}", False)
            extra_data = {}
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                    accept_language=self.accept_language,
                    query={
                        **query_params
                    },
                    user=user_details
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": data,
                    **extra_data
                }
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            formated_error = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"Error in fetch_system_country_codes: > 1 {formated_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")    


    async def patch_system_country_to_add_remove_wallet_prefix_process(
        self,
        request: Request,
        body: dict = Body(...)
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # get item_id from params
            raw_query_params: Dict[str, str] = dict(request.query_params)
            item_id = raw_query_params.get('item_id', None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            flag = body.get('flag', None)
            if not flag:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_FLAG_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            ewallet_number_prefixes = body.get('ewallet_number_prefixes', [])
            if not len(ewallet_number_prefixes):
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_EWALLET_NUMBER_PREFIXES_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            system_country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter___id":item_id
                }
            )
            if not system_country:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_SYSTEM_COUNTRY_FOUND", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            if flag == 'add':
                for ewallet_number_prefix in ewallet_number_prefixes:
                    await self.add_ewallet_number_prefix_to_system_country(
                        ewallet_number_prefix=ewallet_number_prefix,
                        item_id=item_id,
                        ref_currency_id=body.get('ref_currency_id')
                    ) 
            else:
                for ewallet_number_prefix in ewallet_number_prefixes:
                    # delete from cfg_country_related_ewallet_prefix
                    await self.generic_service.hard_delete_with_query_data_from_collection(
                        collection_key=CollectionKey.CFG_COUNTRY_RELATED_EWALLET_PREFIX,
                        query={
                            "prefix":ewallet_number_prefix,
                            "cfg_system_country_id":ObjectId(item_id)
                        }
                    ) 
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=error_detail)
        
    
    async def add_ewallet_number_prefix_to_system_country(
        self,
        ewallet_number_prefix: str,
        item_id: str,
        ref_currency_id:Optional[str] = None
    ):
        try: # Check if collection is exposed
            system_country = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter___id": item_id
                }
            )
            if not system_country:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language)
                message = line_info(message)
                raise HTTPException(status_code=400, detail=message)
            
            data = {
                "prefix":ewallet_number_prefix,
                "cfg_system_country_id":item_id,
                "ref_currency_id":ref_currency_id
            }   
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_EWALLET_PREFIX,
                filter_data=data,
                update_data=data,
            )
            return True 
        except PermissionError as e:
            error_detail = format_exception("Permission denied", e)
            raise HTTPException(status_code=403, detail=error_detail)
        except Exception as e:
            error_detail = format_exception("Unexpected error occurred", e)
            self.app_debug_print(f"\n\n{error_detail}\n\n", True)
            raise HTTPException(status_code=500, detail=error_detail)

    async def fetch_ewallet_prefixes(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)

            query_params = self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            sort = request.query_params.get("sort", {'created_at':-1})
            self.app_debug_print(f"Query Parameters (SORT): {sort}",True)
            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_EWALLET_PREFIX,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={
                    **query_params
                },
                user=user_details,
                sort=sort
            )
            self.app_debug_print(f"Query data: {len(data)}", False)
            extra_data = {}
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_EWALLET_PREFIX,
                    accept_language=self.accept_language,
                    query={
                        **query_params
                    },
                    user=user_details
                )
                extra_data = {
                    "max":max_data,
                    "limit":limit
                }

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": data,
                    **extra_data
                }
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            format_error = format_exception("HTTPException occurred", e)
            self.app_debug_print(f"Error in fetch_ewallet_prefixes: HTTPException {format_error}", True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
            




