


import asyncio
from datetime import datetime, timedelta, timezone
import os
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import BackgroundTasks, Body, File, Form, HTTPException, Query, Request, UploadFile,status
import httpx
from pydantic import ValidationError
from app.db.dao import DAO
from app.modules.auth.enums.auth import ELoginStatus
from app.modules.auth.enums.common import MessageCategory
from app.modules.core.types.response import CustomJSONResponse
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.schemas.organization import EorgApplicationKeyAddPayload, OrganizationBranchCreate, OrganizationCreate, RetroCommissionCreate
from app.modules.core.schemas.person_schema import PersonCreate
from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService

from app.modules.auth.services.password.password_service import PasswordService
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.device.device_service import DeviceService

from app.modules.core.services.generator.generator_service import GeneratorService
from app.modules.core.services.hash.hash_service import HashService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.services.sms.sms_service import SmsService
from app.modules.core.enums.type_enum import AccountStatusFlag, EAccountMovementStatus, EAccountMovementType, EAppGroupFlag, EGlobalStatus, EJWTTokenType, FormatedOutPut, OutputDataType
import math
from app.modules.core.configs.config import settings
from app.modules.core.utils.common.helpers import extract_field_on_output_data_element, mask_email_or_phone_util
from app.modules.core.services.model.model_service import ModelService
from app.modules.core.models.sys_organization.sys_organization_model import SysOrganizationModel
from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.security.middleware.sudo_action_middleware import sudo_action_middleware
from app.modules.core.models.sys_user.sys_user_model import SysUserModel
from app.modules.core.schemas.user_schema import ProfilPermissionCreate, UserPrivilegePermissionCreate
from app.modules.core.enums.access_level import EAccessFlag
from app.modules.core.utils.helpers.line_helper import exception_line_info, format_exception
from app.modules.core.services.wallet.wallet_number_generation_service import generate_ewallet_number_for_country
from app.modules.core.utils.common.async_runner import AsyncExecutor
from app.modules.core.services.encryption.encryption_service import EncryptionService
from app.modules.auth.enums.mfa import MFaFlag
from app.modules.security.enums.security_enum import EConfigSudoActionTypeFlag
from app.modules.core.services.system_country.system_country_service import SystemCountryService




class OrganizationController( 
    AuthenticatedService,
    DebugService,
    PasswordService,
    ResponseService,
    ConverterService,
    ModelService,
    SmsService,
    DeviceService):
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.auth.services.login.login_service import LoginService
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.auth.services.token.token_service import TokenService
        from app.modules.core.services.email_sender.email_sender_service import EMailSenderService
        from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
        
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        self.token_service = TokenService(accept_language)
        self.login_service = LoginService(accept_language)
        self.email_sender_service = EMailSenderService()
        self.rbac_role_service = RbacRoleService(accept_language)
        super().__init__(accept_language)
     
    async def add_new_org_data(self,request: Request,background_tasks: BackgroundTasks, body: dict = Body(...)):
        """
        Endpoint to add a new document to the specified collection.
        """
        saved_profil_id = None
        try: 
            self.app_debug_print(f"\n\n organization body : {body}\n\n",True)
            org_data = OrganizationCreate.model_validate(body, context={"language": self.accept_language})
            # DECODE USER TOKEN  fetch_data_from_collection(
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            # START GETTING SUPPORRT EMAIL ADDRESS
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__is_activated": True
                }
            )

            parent_entity = await SystemCountryService(self.accept_language).get_static_parent_entity_by_flag(
                str(org_data.ref_entity_id), 'country'
            )
            if not parent_entity:
                message = self.get_response_message(MessageCategory.COMMON, "NO_PARENT_ENTITY_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            authenticationService = AuthenticatedService()
            support_email = await authenticationService.get_system_support_email(saas_config_info,self.accept_language)
            # END GETTING SUPPORRT EMAIL ADDRESS

            profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type = OutputDataType.DEFAULT,
                user=user_details,
                query={
                    "filter___id":org_data.rbac_profile_id,
                    # "filter__is_default":True,
                    "filter__system_reserved_actions":True,
                }
            )
            if not profil_info:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_PROFIL_FOUND", self.accept_language,email=support_email)
                raise HTTPException(status_code=401, detail=message)

            # CHECK IF AN ORGANIZATION ALREADY EXIST WITH THAT PROFILE
            org_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type = OutputDataType.DEFAULT,
                user=user_details,
                query={
                    "filter__rbac_profile_id":org_data.rbac_profile_id,
                }
            )
            if org_info:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "ORGANIZATION_ALREADY_EXIST_WITH_THAT_PROFILE", self.accept_language,email=support_email)
                raise HTTPException(status_code=401, detail=message)


            default_role = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__is_default":True,
                    "filter__rbac_profile_id":profil_info['id'],
                    "filter__system_reserved_actions":True,
                },
            )
            if not default_role:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ORG_DEFAULT_ROLE_FOUND", self.accept_language,email=support_email)
                raise HTTPException(status_code=401, detail=message)

            admin_user = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type = OutputDataType.DEFAULT,
                user=user_details,
                query={
                    "filter__username":str(org_data.admin_username).strip()
                }
            ) 
            
            generated_password:str = org_data.admin_password
            if org_data.is_auto_password_selected:
                generated_password = GeneratorService.strong_password_generator(10)
            
            # self.app_debug_print(f"\n\n generated_passwords : {generated_passwords}\n\n",True)
            
            if admin_user:
                # # DELETE CREATED PROFIL
                # await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_PROFIL, new_profil_id)
                # # DELETE CREATED ROLE
                # await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_ROLE, new_role_id)
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "USER_NAME_ALREADY_TAKEN", self.accept_language,username=org_data.admin_username)
                raise HTTPException(status_code=401, detail=message)
            
            #format phone numbers
            phone_numbers = []
            for phone in org_data.telephones:
                phone_numbers.append({
                    'phone_number':phone
                })
            emails = []
            for email in org_data.emails:
                emails.append({
                    "email":email
                })

            
            
            self.app_debug_print(f"\n\n generated_passwords : {generated_password}\n\n",True) 
            org_data_to_save = {
                "ref_entity_id":org_data.ref_entity_id,
                "name":org_data.name,
                "rbac_profile_id":profil_info['id'],
                "sys_organization_id":org_data.sys_organization_id,
                "phone_numbers":phone_numbers,
                "emails":emails,
                "others":org_data.others,
                "parent_reseller_id":user_details['sys_organization_id'],
                "address":org_data.address,
                "contact_person":{
                    "first_name":org_data.contact_first_name,
                    "last_name":org_data.contact_last_name,
                    "gender":org_data.contact_gender,
                    "email":org_data.contact_email,
                    "phone_number":org_data.contact_phone_number,
                }
            }
            self.app_debug_print(f"\n\n\n\n\n\n  org_data_to_save : {org_data_to_save}",False)
            org_saved_item_id = await self.generic_service.add_data_to_collection(CollectionKey.SYS_ORGANIZATION, org_data_to_save, user=user_details, request=request)


            phone_numbers  = []
            phone_numbers.append({'phone_number':org_data.admin_phone_number})
            emails = []
            emails.append({'email':org_data.admin_email})
            self.app_debug_print(f"\n\n\n\n\n\n emails : {emails} | phones {phone_numbers}")

            user_data_to_save = {
                "username":org_data.admin_username,
                "account_status":AccountStatusFlag.ACTIVE.value,
                "password":self.hash_password(generated_password),
                "sys_organization_id":org_saved_item_id,
                "email":org_data.admin_email,
                "phone_number":org_data.admin_phone_number,
                "gender":org_data.admin_gender,
                "ref_entity_id":parent_entity['id'],
                "first_name":org_data.admin_first_name,
                "last_name":org_data.admin_last_name,
                "rbac_role_id":default_role['id'],
                "phone_numbers":phone_numbers,
                "emails":emails,
                "is_default":True,
                "rbac_profile_id":profil_info['id'],
                "others":[],
            }
            self.app_debug_print(f"\n\n\n\n\n\n object : {user_data_to_save}")
            # Add data to the collection
            item_id = await self.generic_service.add_data_to_collection(CollectionKey.SYS_USER, user_data_to_save, user=user_details, request=request)
            self.app_debug_print(f"\n\n\n\n\n\n user saved : {item_id}",True)
            language = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_LANGUAGE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter__short_code": 'fr'
                }
            )

            ref_totp_mfa = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_MFAS,
                output_data_type=OutputDataType.DEFAULT,
                user=user_details,
                query={
                    "filter__flag": MFaFlag.SYCAMORE_2FA_APP.value
                }
            )
            if ref_totp_mfa:
                check_existing_cfg_user_mfa = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    output_data_type=OutputDataType.DEFAULT,
                    user=user_details,
                    query={
                        "filter__sys_user_id": item_id,
                        "filter__ref_mfa_id": ref_totp_mfa['id']
                    }
                )
                if not check_existing_cfg_user_mfa:
                    await self.generic_service.add_data_to_collection(
                        collection_key=CollectionKey.CFG_USER_MFA,
                        user=user_details,
                        request=request,
                        data={
                            "sys_user_id": item_id,
                            "ref_mfa_id": ref_totp_mfa['id'],
                            "is_configured": False,
                            "is_disabled":False,
                            "mfa_configuration_next_setup_at": datetime.now(),
                            "is_activated": True,
                        }
                    )

            # ADD USER CONFIG DEFAULT DATA
            if language:
                await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.CFG_USER_CONFIG,
                    user=user_details,
                    request=request,
                    data={
                        "sys_user_id":item_id,
                        "allowed_device_count":1,
                        "ref_language_id":language['id'],
                    }
                )

            user_account_hash = HashService.generate_hash(f"{item_id}")
            user_account_socket_hash = HashService.generate_hash(f"{item_id}")
            data_update = {
                "user_account_hash":user_account_hash,
                "user_account_socket_hash":user_account_socket_hash
            }
            await self.generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=item_id, data=data_update)

            # SAVE ORGANIZATION PROFILE IN CFG_RELATED_SYSTEM_PROFIL
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
                filter_data={
                    "targeted_id":org_saved_item_id,
                    "rbac_profile_id":org_data.rbac_profile_id
                },
                update_data={
                    "rbac_profile_id":org_data.rbac_profile_id,
                    "targeted_id":org_saved_item_id
                }
            )



            # GET COMMON APP GROUP
            common_app_group = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_APPLICATION_GROUP,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter__flag": EAppGroupFlag.COMMON.value
                }
            )
            if common_app_group:
                # ADD COMMON APP GROUPS
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                    filter_data={
                        "targeted_id":org_saved_item_id,
                        "ref_application_group_id":common_app_group['id'],
                    },
                    update_data={
                        "targeted_id":org_saved_item_id,
                        "ref_application_group_id":common_app_group['id'],
                    }
                )
            org_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter___id":org_saved_item_id
                }
            )
            self.app_debug_print(f"\n\n\n\n\n\n newly created org_info : {True if org_info else False}",True)
            # if org_info:
            #     background_tasks.add_task(
            #         self._complete_org_creation,
            #         profil_info=profil_info,
            #         org_info=org_info,
            #         ref_entity_id=org_data.ref_entity_id,
            #         user_details=user_details,
            #         new_profil_info=new_profil_info
            #     )
            #     # await self._complete_org_creation(profil_info=profil_info,org_info=org_info,ref_entity_id=org_data.ref_entity_id,user_details=user_details,new_profil_info=new_profil_info)

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language,)
            return CustomJSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "status_code": status.HTTP_201_CREATED,
                        "message": message,
                        "data":org_saved_item_id
                    }
                )
            
        except ValidationError as e:
            # DELETE CREATED PROFIL AND ALL RELATED DATA
            if saved_profil_id:
                await self.rbac_role_service.delete_single_sys_profil(saved_profil_id)
            # Extract error messages and format them into a single line
            errors = e.errors()
            error_messages = []
            for error in errors:
                field = ".".join(map(str, error["loc"]))  # Get the field name (e.g., "body.password")
                msg = error.get("msg", "Invalid value")  # Get the error message
                error_messages.append(f"{field}: {msg}")
            
            # Join all error messages into a single line
            self.app_debug_print(f" user err : {e}",True)
            raise HTTPException(status_code=400, detail="; ".join(error_messages))
        except PermissionError as e:
            # DELETE CREATED PROFIL AND ALL RELATED DATA
            if saved_profil_id:
                await self.rbac_role_service.delete_single_sys_profil(saved_profil_id)
            self.app_debug_print(f" user err permission : {e}",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:

            # DELETE CREATED PROFIL AND ALL RELATED DATA
            if saved_profil_id:
                await self.rbac_role_service.delete_single_sys_profil(saved_profil_id)

            self.app_debug_print(f" user err exception : {e}",True)
            raise HTTPException(status_code=500, detail=str(e))
    
    async def add_new_cloned_org_data(self,request: Request,background_tasks: BackgroundTasks, body: dict = Body(...)):
        """
        Endpoint to add a new document to the specified collection.
        """
        saved_profil_id = None
        try: 
            self.app_debug_print(f"\n\n organization body : {body}\n\n",True)
            org_data = OrganizationCreate.model_validate(body, context={"language": self.accept_language})
            # DECODE USER TOKEN  fetch_data_from_collection(
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            # START GETTING SUPPORRT EMAIL ADDRESS
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__is_activated": True
                }
            )

            parent_entity = await SystemCountryService(self.accept_language).get_static_parent_entity_by_flag(
                str(org_data.ref_entity_id), 'country'
            )
            if not parent_entity:
                message = self.get_response_message(MessageCategory.COMMON, "NO_PARENT_ENTITY_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            authenticationService = AuthenticatedService()
            support_email = await authenticationService.get_system_support_email(saas_config_info,self.accept_language)
            # END GETTING SUPPORRT EMAIL ADDRESS

            profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type = OutputDataType.DEFAULT,
                user=user_details,
                query={
                    "filter___id":org_data.rbac_profile_id,
                    # "filter__is_default":True,
                    "filter__system_reserved_actions":True,
                }
            )
            if not profil_info:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_PROFIL_FOUND", self.accept_language,email=support_email)
                raise HTTPException(status_code=401, detail=message)

            # CHECK IF AN ORGANIZATION ALREADY EXIST WITH THAT PROFILE
            org_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type = OutputDataType.DEFAULT,
                user=user_details,
                query={
                    "filter__rbac_profile_id":org_data.rbac_profile_id,
                }
            )
            if org_info:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "ORGANIZATION_ALREADY_EXIST_WITH_THAT_PROFILE", self.accept_language,email=support_email)
                raise HTTPException(status_code=401, detail=message)

            # CREATE ORGANIZATION PROFIL FROM PARENT PROFIL
            new_profil_id = await self.generic_service.add_data_to_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                user=user_details,
                request=request,
                data={
                    "name":f"Profil de l'organisation : {org_data.name}",
                    "description_str":profil_info['description_str'],
                    "sys_organization_id":None,
                    "rbac_profile_id":profil_info['id'],
                    # "flag":profil_info['flag'],
                    "is_default":False,
                    "system_reserved_actions":True,
                }
            )
            self.app_debug_print(f"\n\n\n\n\n\n new_profil_id >>> : {new_profil_id}",True)
            saved_profil_id = new_profil_id
            asyncio.create_task(
                self.rbac_role_service.create_cloned_sys_profil_from_parent(
                    parent_rbac_profile_id=profil_info['id'],
                    rbac_profile_id=new_profil_id
                )
            )
            # await self.rbac_role_service.create_cloned_sys_profil_from_parent(parent_rbac_profile_id=profil_info['id'],rbac_profile_id=new_profil_id)

            default_role = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__is_default":True,
                    "filter__rbac_profile_id":profil_info['id'],
                    "filter__system_reserved_actions":True,
                },
            )
            if not default_role:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ORG_DEFAULT_ROLE_FOUND", self.accept_language,email=support_email)
                raise HTTPException(status_code=401, detail=message)


            new_profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id":new_profil_id,
                },
            )
            self.app_debug_print(f"\n\n\n\n\n\n new_profil_info >>> : {new_profil_info}",True)
            if not new_profil_info:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_PROFIL_FOUND", self.accept_language,email=support_email)
                raise HTTPException(status_code=404, detail=message)


            admin_user = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type = OutputDataType.DEFAULT,
                user=user_details,
                query={
                    "filter__username":str(org_data.admin_username).strip()
                }
            ) 
            
            generated_password:str = org_data.admin_password
            if org_data.is_auto_password_selected:
                generated_password = GeneratorService.strong_password_generator(10)
            
            # self.app_debug_print(f"\n\n generated_passwords : {generated_passwords}\n\n",True)
            
            if admin_user:
                # # DELETE CREATED PROFIL
                # await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_PROFIL, new_profil_id)
                # # DELETE CREATED ROLE
                # await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_ROLE, new_role_id)
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "USER_NAME_ALREADY_TAKEN", self.accept_language,username=org_data.admin_username)
                raise HTTPException(status_code=401, detail=message)
            
            #format phone numbers
            phone_numbers = []
            for phone in org_data.telephones:
                phone_numbers.append({
                    'phone_number':phone
                })
            emails = []
            for email in org_data.emails:
                emails.append({
                    "email":email
                })

            
            
            self.app_debug_print(f"\n\n generated_passwords : {generated_password}\n\n",True) 
            org_data_to_save = {
                "ref_entity_id":org_data.ref_entity_id,
                "name":org_data.name,
                "rbac_profile_id":new_profil_id,
                "sys_organization_id":org_data.sys_organization_id,
                "phone_numbers":phone_numbers,
                "emails":emails,
                "others":org_data.others,
                "parent_reseller_id":user_details['sys_organization_id'],
                "address":org_data.address,
                "contact_person":{
                    "first_name":org_data.contact_first_name,
                    "last_name":org_data.contact_last_name,
                    "gender":org_data.contact_gender,
                    "email":org_data.contact_email,
                    "phone_number":org_data.contact_phone_number,
                }
            }
            self.app_debug_print(f"\n\n\n\n\n\n  org_data_to_save : {org_data_to_save}",False)
            org_saved_item_id = await self.generic_service.add_data_to_collection(CollectionKey.SYS_ORGANIZATION, org_data_to_save, user=user_details, request=request)

            self.app_debug_print(f"\n\n\n\n\n\n saved org_saved_item_id : {org_saved_item_id}",True)

            # CREATE ORGANIZATION DEFAULT ROLE
            new_role_data = {
                    "name":f"Rôle administrateur de l'organisation {org_data.name} ",
                    "description_str":f"Rôle administrateur de l'organisation {org_data.name} ",
                    "sys_organization_id":org_saved_item_id,
                    "rbac_profile_id":new_profil_id,
                    "flag":f"{default_role['flag']}_org_{org_saved_item_id}_super_admin",
                    "is_default":True,
                    "system_reserved_actions":True,
                    "sys_core_role_id":default_role['id']
                }
            self.app_debug_print(f"\n\n\n\n\n\n new_role_data : {new_role_data}",True)
            new_role_id = await self.generic_service.add_data_to_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                user=user_details,
                request=request,
                data=new_role_data
            )
            self.app_debug_print(f"\n\n\n\n new_role_id : {new_role_id}",True)
            asyncio.create_task(
                self.rbac_role_service.create_single_rbac_role_permissions_from_parent(
                    parent_rbac_role_id=default_role['id'],
                    rbac_role_id=new_role_id
                )
            )



            asyncio.create_task(
                self.rbac_role_service.create_roles_from_parent_profile(
                    parent_profil_id=profil_info['id'],
                    new_profil_id=new_profil_id,
                    saved_organization_id=org_saved_item_id
                )
            )
             
            phone_numbers  = []
            phone_numbers.append({'phone_number':org_data.admin_phone_number})
            emails = []
            emails.append({'email':org_data.admin_email})
            self.app_debug_print(f"\n\n\n\n\n\n emails : {emails} | phones {phone_numbers}")
            
            user_data_to_save = {
                "username":org_data.admin_username,
                "account_status":AccountStatusFlag.ACTIVE.value,
                "password":self.hash_password(generated_password),
                "sys_organization_id":org_saved_item_id,
                "email":org_data.admin_email,
                "phone_number":org_data.admin_phone_number,
                "gender":org_data.admin_gender,
                "ref_entity_id":parent_entity['id'],
                "first_name":org_data.admin_first_name,
                "last_name":org_data.admin_last_name,
                "rbac_role_id":new_role_id,
                "phone_numbers":phone_numbers,
                "emails":emails,
                "is_default":True,
                "rbac_profile_id":new_profil_id,
                "others":[],
            }
            self.app_debug_print(f"\n\n\n\n\n\n object : {user_data_to_save}")
            # Add data to the collection
            item_id = await self.generic_service.add_data_to_collection(CollectionKey.SYS_USER, user_data_to_save, user=user_details, request=request)
            self.app_debug_print(f"\n\n\n\n\n\n user saved : {item_id}",True)
            language = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_LANGUAGE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter__short_code": 'fr'
                }
            )

            ref_totp_mfa = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_MFAS,
                output_data_type=OutputDataType.DEFAULT,
                user=user_details,
                query={
                    "filter__flag": MFaFlag.SYCAMORE_2FA_APP.value
                }
            )
            if ref_totp_mfa:
                check_existing_cfg_user_mfa = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    output_data_type=OutputDataType.DEFAULT,
                    user=user_details,
                    query={
                        "filter__sys_user_id": item_id,
                        "filter__ref_mfa_id": ref_totp_mfa['id']
                    }
                )
                if not check_existing_cfg_user_mfa:
                    await self.generic_service.add_data_to_collection(
                        collection_key=CollectionKey.CFG_USER_MFA,
                        user=user_details,
                        request=request,
                        data={
                            "sys_user_id": item_id,
                            "ref_mfa_id": ref_totp_mfa['id'],
                            "is_configured": False,
                            "is_disabled":False,
                            "mfa_configuration_next_setup_at": datetime.now(),
                            "is_activated": True,
                        }
                    )

            # ADD USER CONFIG DEFAULT DATA
            if language:
                await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.CFG_USER_CONFIG,
                    user=user_details,
                    request=request,
                    data={
                        "sys_user_id":item_id,
                        "allowed_device_count":1,
                        "ref_language_id":language['id'],
                    }
                )

            user_account_hash = HashService.generate_hash(f"{item_id}")
            user_account_socket_hash = HashService.generate_hash(f"{item_id}")
            data_update = {
                "user_account_hash":user_account_hash,
                "user_account_socket_hash":user_account_socket_hash
            }
            await self.generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=item_id, data=data_update)

            # SAVE ORGANIZATION PROFILE IN CFG_RELATED_SYSTEM_PROFIL
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
                filter_data={
                    "targeted_id":org_saved_item_id,
                    "rbac_profile_id":org_data.rbac_profile_id
                },
                update_data={
                    "rbac_profile_id":org_data.rbac_profile_id,
                    "targeted_id":org_saved_item_id
                }
            )



            # GET COMMON APP GROUP
            common_app_group = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_APPLICATION_GROUP,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter__flag": EAppGroupFlag.COMMON.value
                }
            )
            if common_app_group:
                # ADD COMMON APP GROUPS
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                    filter_data={
                        "targeted_id":org_saved_item_id,
                        "ref_application_group_id":common_app_group['id'],
                    },
                    update_data={
                        "targeted_id":org_saved_item_id,
                        "ref_application_group_id":common_app_group['id'],
                    }
                )
            org_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter___id":org_saved_item_id
                }
            )
            self.app_debug_print(f"\n\n\n\n\n\n newly created org_info : {True if org_info else False}",True)
            if org_info:
                asyncio.create_task(
                    self._complete_org_creation(
                        profil_info=profil_info,
                        org_info=org_info,
                        ref_entity_id=org_data.ref_entity_id,
                        user_details=user_details,
                        new_profil_info=new_profil_info
                    )
                )
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language,)
            return CustomJSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "status_code": status.HTTP_201_CREATED,
                        "message": message,
                        "data":org_saved_item_id
                    }
                )
            
        except ValidationError as e:
            # DELETE CREATED PROFIL AND ALL RELATED DATA
            if saved_profil_id:
                await self.rbac_role_service.delete_single_sys_profil(saved_profil_id)
            # Extract error messages and format them into a single line
            errors = e.errors()
            error_messages = []
            for error in errors:
                field = ".".join(map(str, error["loc"]))  # Get the field name (e.g., "body.password")
                msg = error.get("msg", "Invalid value")  # Get the error message
                error_messages.append(f"{field}: {msg}")
            
            # Join all error messages into a single line
            self.app_debug_print(f" user err : {e}",True)
            raise HTTPException(status_code=400, detail="; ".join(error_messages))
        except PermissionError as e:
            # DELETE CREATED PROFIL AND ALL RELATED DATA
            if saved_profil_id:
                await self.rbac_role_service.delete_single_sys_profil(saved_profil_id)
            self.app_debug_print(f" user err permission : {e}",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:

            # DELETE CREATED PROFIL AND ALL RELATED DATA
            if saved_profil_id:
                await self.rbac_role_service.delete_single_sys_profil(saved_profil_id)

            self.app_debug_print(f" user err exception : {e}",True)
            raise HTTPException(status_code=500, detail=str(e))
    

    async def add_agent_data(
        self,
        request: Request, 
        body: dict = Body(...)):
        """
        Endpoint to add a new document to the specified collection.
        """
        try:
            # Validate the incoming data with context
            self.app_debug_print(f"\n\n organization agent body : {body}\n\n",True)
            org_person_data = PersonCreate.model_validate(body, context={"language": self.accept_language})
            # org_data = OrganizationCreate.model_validate(body, context={"language": accept_language})
            self.app_debug_print(f"\n\n organization agent body : {org_person_data}\n\n",True)
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            # START GETTING SUPPORRT EMAIL ADDRESS
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__is_activated": True
                }
            )
            # print("saas_config_info:", saas_config_info)

            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            authenticationService = AuthenticatedService()
            support_email = await  authenticationService.get_system_support_email(saas_config_info,self.accept_language) 
            
             
            person_data_to_save = {
                "first_name":org_person_data.first_name,
                "last_name":org_person_data.last_name,
                "sur_name":org_person_data.sur_name,
                "sys_organization_id":org_person_data.sys_organization_id,
                "birth_date":org_person_data.birth_date,
                "gender":org_person_data.gender,
                
                "birth_city":org_person_data.birth_city,
                "ref_birth_country_id":org_person_data.ref_birth_country_id,
                "ref_nationality_id":org_person_data.ref_nationality_id,
                "ref_marital_status_id":org_person_data.ref_marital_status_id,
                "number_of_children":org_person_data.number_of_children,
                "ref_religion_id":org_person_data.ref_religion_id,
                "address_line1":org_person_data.address_line1,
                "address_line2":org_person_data.address_line2,
                "home_town":org_person_data.home_town,
                "ref_home_country_id":org_person_data.ref_home_country_id,
                "phone_number":org_person_data.phone_number,
                "email":org_person_data.email,
                "national_id_number":org_person_data.national_id_number,
                "passport_number":org_person_data.passport_number,
                "driving_license_number":org_person_data.driving_license_number,
                "ref_eye_color_id":org_person_data.ref_eye_color_id,
                "ref_blood_type_id":org_person_data.ref_blood_type_id,
                "height_in_cm":org_person_data.height_in_cm,
                "weight_in_kg":org_person_data.weight_in_kg,
                "weight_in_kg":org_person_data.weight_in_kg,
                
            }
            # if org_person_data.birth_date :
            #     person_data_to_save = {
            #         **person_data_to_save,
            #         "birth_date":org_person_data.birth_date,
            #     }
            self.app_debug_print(f"  person_data_to_save : {person_data_to_save}",True)
            person_saved_item_id = await self.generic_service.add_data_to_collection(CollectionKey.SYS_PERSON, person_data_to_save, user=user_details, request=request)

            self.app_debug_print(f" saved person_saved_item_id : {person_saved_item_id}",True)

            agent_data_to_save = {
                "matricule":org_person_data.matricule,
                "cfg_function_id":org_person_data.cfg_function_id,
                "cfg_organism_chart_id":org_person_data.cfg_organism_chart_id,
                "cfg_grade_id":org_person_data.cfg_grade_id,
                "sys_organization_id":org_person_data.sys_organization_id,
                "sys_person_id":person_saved_item_id,
            }

            agent_saved_item_id = await self.generic_service.add_data_to_collection(CollectionKey.SYS_ORGANIZATION_AGENT, agent_data_to_save, user=user_details, request=request)
            
            self.app_debug_print(f" saved agent_saved_item_id : {agent_saved_item_id}",True) 
            
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language,)
            return CustomJSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "status_code": status.HTTP_201_CREATED,
                        "message": message,
                        "data":agent_saved_item_id
                    }
                )
            
        except ValidationError as e:
            # Extract error messages and format them into a single line
            errors = e.errors()
            error_messages = []
            for error in errors:
                field = ".".join(map(str, error["loc"]))  # Get the field name (e.g., "body.password")
                msg = error.get("msg", "Invalid value")  # Get the error message
                error_messages.append(f"{field}: {msg}")
            
            # Join all error messages into a single line
            self.app_debug_print(f" user err : {e}",True)
            raise HTTPException(status_code=400, detail="; ".join(error_messages))
        except PermissionError as e:
            self.app_debug_print(f" agent err permission : {e}",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f" agent err exception : {e}",True)
            raise HTTPException(status_code=500, detail=str(e))
    

    async def   add_user_data(
        self,
        request: Request, 
        body: dict = Body(...)):
        """
        Endpoint to add a new document to the specified collection.
        """
        try:
            # Validate the incoming data with context
            # org_person_data = PersonCreate.model_validate(body, context={"language": accept_language})
            # org_data = OrganizationCreate.model_validate(body, context={"language": accept_language})
            self.app_debug_print(f"\n\n agent user body : {body}\n\n",True)
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            # START GETTING SUPPORRT EMAIL ADDRESS
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__is_activated": True
                }
            )

            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            authenticationService = AuthenticatedService()
            support_email = await  authenticationService.get_system_support_email(saas_config_info,self.accept_language)
            # END GETTING SUPPORRT EMAIL ADDRESS

            # profil_info = await self.generic_service.fetch_one_from_collection(
            #     collection_key=CollectionKey.RBAC_PROFIL,
            #     output_data_type = OutputDataType.DEFAULT,
            #     query={
            #         "filter__flag":'organization'
            #     }
            # )
            # if not profil_info:
            #     message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_PROFIL_FOUND", self.accept_language,email=support_email)
            #     raise HTTPException(status_code=401, detail=message)

            # Add data to the collection
            password = self.hash_password(body.get('password'))
            rbac_profile_id = body.get('rbac_profile_id',user_profil['id'])
            user_data = {
                **body,
                "rbac_profile_id":rbac_profile_id,
                "account_status":AccountStatusFlag.ACTIVE.value,
                "password": password
            }
            self.app_debug_print(f" BEFORE SAVE user account  : {user_data}",True)
            item_id = await self.generic_service.add_data_to_collection(CollectionKey.SYS_USER, user_data, user=user_details, request=request)
            self.app_debug_print(f" SAVED user account item_id : {item_id}",True)
            cfg_organism_chart_id = body.get('cfg_organism_chart_id',None)
            sys_organization_id = body.get('sys_organization_id',None)
            sys_person_id = body.get('sys_person_id',None)


            user_account_hash = HashService.generate_hash(f"{item_id}")
            user_account_socket_hash = HashService.generate_hash(f"{item_id}")
            data_update = {
                "user_account_hash":user_account_hash,
                "user_account_socket_hash":user_account_socket_hash
            }
            await self.generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=item_id, data=data_update)
            
            agent_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION_AGENT,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__sys_person_id": sys_person_id,
                    "filter__cfg_organism_chart_id": cfg_organism_chart_id,
                }
            )
            self.app_debug_print(f" adding user account  agent : {agent_info}",True)
            if agent_info:
                agent_data = {
                        "sys_user_id":item_id,
                    } 
                # UPDATE USER
                updated = await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.SYS_ORGANIZATION_AGENT,
                    item_id=agent_info['id'],
                    data=agent_data
                )
                self.app_debug_print(f" adding user account  agent  updated : {updated}",True)

            language = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_LANGUAGE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter__short_code": 'fr'
                }
            )

            # ADD USER CONFIG DEFAULT DATA
            if language:
                await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.CFG_USER_CONFIG,
                    user=user_details,
                    request=request,
                    data={
                        "sys_user_id":item_id,
                        "allowed_device_count":1,
                        "ref_language_id":language['id'],
                    }
                )

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
            
        except ValidationError as e:
            # Extract error messages and format them into a single line
            errors = e.errors()
            error_messages = []
            for error in errors:
                field = ".".join(map(str, error["loc"]))  # Get the field name (e.g., "body.password")
                msg = error.get("msg", "Invalid value")  # Get the error message
                error_messages.append(f"{field}: {msg}")
            
            # Join all error messages into a single line
            self.app_debug_print(f" user err : {e}",True)
            raise HTTPException(status_code=400, detail="; ".join(error_messages))
        except PermissionError as e:
            self.app_debug_print(f" user err permission : {e}",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f" user err exception : {e}",True)
            raise HTTPException(status_code=500, detail=str(e))
    

    async def soft_delete_data(
        self,
        request: Request,
        collection_name: str, 
        item_id: str):
        """
        Endpoint to soft delete a document in the specified collection.
        """
        try:
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # Soft delete the document
            success = await self.generic_service.soft_delete_data_from_collection(collection_key, item_id)
            if success:
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": "Data soft-deleted successfully",
                    }
                )
            else:
                raise HTTPException(status_code=404, detail="Item not found or already deleted")
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    async def delete_agent_data(
        self,
        request: Request,):
        """
        Endpoint to soft delete a document in the specified collection.
        """
        try: 

            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            # START GETTING SUPPORRT EMAIL ADDRESS
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__is_activated": True
                }
            )

            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            authenticationService = AuthenticatedService()
            support_email = await  authenticationService.get_system_support_email(saas_config_info,self.accept_language)
            collection_key = CollectionKey.SYS_ORGANIZATION_AGENT

            item_id = request.query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # CHECK ORGANIZATION AGENT EXIST
            agent_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION_AGENT,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id":  item_id,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                }
            )
            if not agent_info:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_AGENT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            # DELETE IN SYS_PERSON
            await self.generic_service.soft_delete_data_from_collection(CollectionKey.SYS_PERSON, agent_info['sys_person_id'])

            # DELETE IN SYS_USER
            if 'sys_user_id' in agent_info:
                await self.generic_service.soft_delete_data_from_collection(CollectionKey.SYS_USER, agent_info['sys_user_id'])
            
            # Soft delete the document
            success = await self.generic_service.hard_delete_data_from_collection(collection_key, item_id)
            if success:
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": "Data soft-deleted successfully",
                    }
                )
            else:
                raise HTTPException(status_code=404, detail="Item not found or already deleted")
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
    async def delete_user_data(
        self,
        request: Request,):
        """
        Endpoint to soft delete a document in the specified collection.
        """
        try: 

            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            # START GETTING SUPPORRT EMAIL ADDRESS
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__is_activated": True
                }
            )

            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            authenticationService = AuthenticatedService()
            support_email = await  authenticationService.get_system_support_email(saas_config_info,self.accept_language)

            item_id = request.query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            # CHECK ORGANIZATION AGENT EXIST
            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id":  item_id,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                }
            )
            if not user_info:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_USER_ACCOUNT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            # DELETE USER LOGIN HISTORIES

            # Soft delete the document
            success = await self.generic_service.hard_delete_data_from_collection(CollectionKey.SYS_USER, item_id)
            if success:
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": "Data soft-deleted successfully",
                    }
                )
            else:
                raise HTTPException(status_code=404, detail="Item not found or already deleted")
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
    async def hard_delete_organization(
        self,
        request: Request,
        background_tasks: BackgroundTasks):
        """
        Endpoint to hard delete a document in the specified collection.
        """
        try: 
            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message',None)
            # sudo_can_proceed = sudo_action.get('can_proceed',True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_400_BAD_REQUEST,
            #             content={
            #                 "status_code": status.HTTP_400_BAD_REQUEST,
            #                 "message": sudo_message,
            #             }
            #         )
            item_id = request.query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            # CHECK ORGANIZATION EXIST
            organization_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter___id":  item_id,
                }
            )
            if not organization_info:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_ORG_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            # DELETE PROFIL
            asyncio.create_task(self._complete_org_deletion(organization_info))
            asyncio.create_task(self.rbac_role_service.delete_single_sys_profil(str(organization_info['rbac_profile_id'])))
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                }
            ) 
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        

    async def generate_reset_password_link(
        self,
        request: Request,
        background_tasks: BackgroundTasks):
        """
        Endpoint to soft delete a document in the specified collection.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            # GET IP ADDRESS
            ip_address = await self.get_optional_api_address(request,self.accept_language)

            raw_query_params: Dict[str, str] = dict(request.query_params)
            item_id = raw_query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ITEM_ID_SENT", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # GET USER INFO
            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id": item_id,
                }
            )
            if not user_info:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # Get current time in UTC 
            now = datetime.now(timezone.utc) 
            end_of_validity = now - timedelta(minutes=30)
            
            # GENERATE OTP
            otp_code = GeneratorService.generate_otp(length=8)
            # self.app_debug_print(f"userInfo :  {user_id}")
            data_history_query = {
                "sys_user_id":user_info['id'],
                "otp":f"{otp_code}",
                "ip_address":ip_address,
                "cfg_user_device_id":None,
                # "cfg_user_device_id":user_device_info.get("id"),
                "status":ELoginStatus.INIT_PASSWORD_PROCESS.value,
            }
            self.app_debug_print(f" RESET PASSWORD data_history_query :  {data_history_query}")
            filter_history_query = {
                "filter__sys_user_id":user_info['id'],
                "filter__status":ELoginStatus.INIT_PASSWORD_PROCESS.value,
                "filter__created_at": {"$gte": end_of_validity}  
            }
            
            resetPasswHistory = await self.login_service.get_or_create_init_with_data_history(data=data_history_query,filter_query=filter_history_query)
            self.app_debug_print(f"RESET PASSWORD History :  {resetPasswHistory}")
            
            if not resetPasswHistory:
                message = self.get_response_message(MessageCategory.PASSWORD_RESET, "MISSING_PASSWORD_RESET_HISTORY",self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            otp_code = resetPasswHistory["otp"]
            if not otp_code:
                # GENERATE OTP
                otp_code = GeneratorService.generate_otp(length=8)
                h_data = {
                    "otp":f"{otp_code}"
                }
                # UPDATE OTP ON LOGIN HISTORY
                await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                    item_id=resetPasswHistory['id'],
                    data=h_data
                )
                
            self.app_debug_print(f"\n\n otp_code : {otp_code} \n\n")
            email = user_info['email']
            
            if not email:
                message = self.get_response_message(MessageCategory.COMMON, "USER_EMAIL_NOT_FOUND",self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            mail_title_translated = self.get_response_message(MessageCategory.PASSWORD_RESET, "SUCCESS_PASSWORD_INIT_PROCESS_TITLE",self.accept_language)

            mail_message_translated = self.get_response_message(MessageCategory.PASSWORD_RESET, "PASSWORD_INIT_EMAIL_BODY",self.accept_language, otp_code=otp_code)

            second_mail_message_translated = self.get_response_message(MessageCategory.PASSWORD_RESET, "PASSWORD_INIT_EMAIL_SECOND_MESSAGE",self.accept_language,minutes=30)

            mail_note_translated = self.get_response_message(MessageCategory.PASSWORD_RESET, "PASSWORD_INIT_EMAIL_NOTE",self.accept_language)

            
            reset_password_redirect_token = self.token_service.create_access_token(
                data={"sub": resetPasswHistory['id'], "type":EJWTTokenType.PASSWORD_RESET_REDIRECTED},
                token_type=EJWTTokenType.PASSWORD_RESET_REDIRECTED,
                expires_delta=timedelta(minutes=30)  # Expires after 30 minutes
            )
            reset_password_redirect_url = f"{settings.FRONT_END_ANGULAR_BASE_URL}/gen-reset/{reset_password_redirect_token}"
            
            update_here_message = self.get_response_message(MessageCategory.PASSWORD_RESET, "CLICK_HERE_TO_UPDATE",self.accept_language)
            
            # Send password reset email in background to avoid blocking the request
            asyncio.create_task(
                self.send_password_reset_email_background(
                    email=email,
                    otp_code=otp_code,
                    mail_title_translated=mail_title_translated,
                    mail_message_translated=mail_message_translated,
                    second_mail_message_translated=second_mail_message_translated,
                    mail_note_translated=mail_note_translated,
                    reset_password_redirect_url=reset_password_redirect_url,
                    update_here_message=update_here_message,
                    accept_language=self.accept_language
                )
            )
            
            # Return the formatted response message
            mask_email = mask_email_or_phone_util(email)
            sms = self.get_response_message(MessageCategory.PASSWORD_RESET, "PASSWORD_INIT_LINK_EMAIL_SENT",self.accept_language, email=mask_email)
            
            # Generate access token
            token = self.token_service.create_access_token(
                data={"sub": str(resetPasswHistory['id']), "type":EJWTTokenType.PASSWORD_INIT_PROCESS},
                token_type=EJWTTokenType.PASSWORD_INIT_PROCESS,
                expires_delta=timedelta(minutes=60)  # Expires after 30 minutes
            )
            
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code":status.HTTP_200_OK,
                    "message":sms,
                    # "access_token":token,
                    "username":user_info['username'],
                }
            )
        except PermissionError as e:
            print(f"\n\n\n ERROR :: {e}")
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            print(f"\n\n\n ERROR auto gen:: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def hard_delete_data(
        self,
        request: Request,
        collection_name: str, 
        item_id: str):
        """
        Endpoint to soft delete a document in the specified collection.
        """
        
        try:
            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # Soft delete the document
            success = await self.generic_service.hard_delete_data_from_collection(collection_key, item_id)
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
            if success:
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
            else:
                raise HTTPException(status_code=404, detail="Item not found or already deleted")
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def update_data(
        self,
        request: Request,
        collection_name: str, item_id: str, data: Dict[str, Any]):
        """
        Endpoint to update a document in the specified collection.
        """
        try:
            # Fetch `Accept-Language` from headers, default to 'fr'
            
            # Convert string to CollectionKey
            try:
                collection_key = CollectionKey(collection_name)
            except ValueError:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "INVALID_COLLECTION_NAME", self.accept_language,collection_name=collection_name)
                raise HTTPException(status_code=400, detail=message)

            # Check if collection is exposed
            metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
            if not metadata:
                raise HTTPException(status_code=400, detail="Invalid collection name")

            # Perform the update
            dao = DAO(metadata.collection_name,metadata.model_class,is_read_only=False)
            result = await dao.update({'_id':item_id}, data)
            if result:
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": "Data updated successfully",
                    }
                )
            else:
                raise HTTPException(status_code=404, detail="Item not found or not updated")
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
 
    
    async def fetch_org_data(
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
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            user_profil = getattr(request.state, "userProfil", None)
            if not user_profil:
                message = self.get_response_message(MessageCategory.COMMON, "USER_PROFIL_MISSING", self.accept_language)
                self.app_debug_print(f" missing user_profil : {message}",)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
            
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params =  self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",False)

            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language= self.accept_language,
                user=user_details,
                query={
                    **query_params
                }
            )
            self.app_debug_print(f"\n returned out formatted_data  >: {len(data)} \n\n", False)
            formatted_data = []
            for element in data:
                self.app_debug_print(f"-> element: {element}",False)
                try:
                    organization_instance = ModelService.convert_to_model_instance(SysOrganizationModel,element)
                    self.app_debug_print(f"-> step 1: ",False)
                    organization = await  organization_instance.get_formated_data(self.accept_language,FormatedOutPut.FULL)
                    self.app_debug_print(f"-> step 2 returned : {organization} ",False)
                    formatted_data.append(organization)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid collection name: {organization_instance}")
                except PermissionError as e:
                    self.app_debug_print(f"Error in fetch_data 4: {str(e)}",False)
                    raise HTTPException(status_code=403, detail=str(e))

            self.app_debug_print(f"Query data: {len(data)}",False)
            extra_data = {}
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.SYS_ORGANIZATION,
                    accept_language= self.accept_language,
                    user=user_details,
                    query={
                        **query_params
                    }
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

        except PermissionError as e:
            self.app_debug_print(f"Error in fetch_data 1: {str(e)}",False)
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            self.app_debug_print(f"ERROR fetch org 2: {e}",True)
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch_data 3: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
    
    async def search_organization_info(
        self,
        request: Request,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            

            if not user_profil:
                message = self.get_response_message(MessageCategory.COMMON, "USER_PROFIL_MISSING", self.accept_language)
                self.app_debug_print(f" missing user_profil : {message}",)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
            
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            search_key= raw_query_params.get('search_key','')
            # ADD STATIC FILTER
            query_params = {
                # **raw_query_params,
                "$or":[
                    {
                        "name": { '$regex': f'{search_key}', '$options': "i" }
                    }, 
                ]
            }
            
            
            # query_params = convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            
            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_native_query_data_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                all_data=all_data,
                page=page,
                limit=limit,
                accept_language= self.accept_language,
                native_query={
                    **query_params
                }
            )
            self.app_debug_print(f"Query data user: {len(data)}",True)
            extra_data = {}
            formatted_data = []
            for element in data:
                user_instance = ModelService.convert_to_model_instance(SysOrganizationModel,element)
                user = await  user_instance.get_formated_data(self.accept_language)
                formatted_data.append(user)

            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.SYS_ORGANIZATION,
                    accept_language= self.accept_language,
                    user=user_details,
                    query={
                        **query_params
                    }
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

        except PermissionError as e:
            self.app_debug_print(f"Error in users 1: {str(e)}",True)
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            self.app_debug_print(f"Error in users 2: {str(e)}",True)
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in users 1: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    

    async def upload_org_logo(
        self,
        request: Request,
        id: str = Form(...), 
        upload_file: UploadFile = File(...),
    ):
        """
        Upload a single file and forward it to another API endpoint with progress updates.
        """
        try:
            self.app_debug_print(f"Received id: {id}", True)
            self.app_debug_print(f"Received file: {upload_file}", True)
            # Read the file content
            org_info = await self.generic_service.fetch_native_query_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                accept_language= self.accept_language,
                native_query={
                    "_id": ObjectId(id),
                }
            )
            if not org_info:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # Read the entire file content first
            file_content = await upload_file.read()

            # Reset file pointer for potential reuse
            await upload_file.seek(0)

            # Use httpx AsyncClient to post the file to the target endpoint
            async with httpx.AsyncClient() as client:
                headers = {
                    "authorization": f"Bearer {settings.SENAT_DIGIT_APPS_FILE_BEARER_TOKEN}"
                }
                # math
                self.app_debug_print(f"\n\n\n headers : {headers} \n\n", False)
                response = await client.post(
                    f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/files/upload?base_dir={settings.SENAT_DIGIT_APPS_FILE_ORGANIZATION_LOGO_BASE_DIR}",
                    files={"upload_file": (upload_file.filename, file_content, upload_file.content_type)},
                    headers=headers
                )
                self.app_debug_print(f"Forwarded file upload response status: {response.status_code}", False)

            self.app_debug_print(f" UPLOADED FILE response : {isinstance(response.status_code, int)}", False)
            self.app_debug_print(f" UPLOADED FILE all response : {response.json()}", False)

            # You may want to validate the response from the target endpoint.
            if response.status_code == 200 or response.status_code == 201:
                # Assuming response.data is a dictionary or an object with attributes
                resp = response.json()
                data = resp.get('data', {})

                # Access the fields from response.data
                # Access the fields from response.data
                id = data.get('id')
                file_name = data.get('file_name')
                file_url = data.get('file_url')
                # created_at = data.get('created_at')
                file_size = data.get('file_size')
                file_type = data.get('file_type')
                file_path = data.get('file_path')
                # identifier = data.get('identifier')
                file_original_name = data.get('file_original_name')
                file_extension = data.get('file_extension')
                file_str_id_composed = data.get('file_str_id_composed')

                # PREPARE ARCH FILE DATA
                # timestamp = get_today_timestamp_int()
                # file_str_id_composed = f"{uuid.uuid4()}_{id}_{timestamp}"
                file_url_composed = f"{settings.MAIN_APP_BASE_URL}/static/files/view-file/{file_str_id_composed}"
                arch_file_data = {
                    "remote_arch_file_id":data.get('id'),
                    "remote_arch_file_url":file_url,
                    "file_name":file_name,
                    "file_str_id_composed":file_str_id_composed,
                    "file_url":file_url_composed,
                    "file_original_name":file_original_name,
                    "file_extension":file_extension,
                    "file_type":file_type,
                    "file_size":file_size,
                    "file_path":file_path,
                }
                # Call the asynchronous function to update the collection
                added_file_id = await self.generic_service.add_data_to_collection(collection_key=CollectionKey.ARCH_FILE, data=arch_file_data)
                self.app_debug_print(f" added_file_id: {added_file_id}", False)

                # SAVE ORG FILE
                # Prepare the update data
                update_data = {
                    "logo_file_id": added_file_id  # Ensure `id` is defined and has the correct value
                }
                self.app_debug_print(f" update_data: {update_data}", False)
                # Call the asynchronous function to update the collection
                updated = await self.generic_service.update_data_in_collection(
                    collection_key=CollectionKey.SYS_ORGANIZATION,
                    item_id=org_info['id'],
                    data=update_data
                )
                self.app_debug_print(f" updated: {updated}", False)
                message = self.get_response_message(MessageCategory.SUCCESS, "FILE_UPLOADED_SUCCESSFULLY", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
            raise HTTPException(status_code=response.status_code, detail="Failed to forward the file to the target API.")

        except Exception as e:
            self.app_debug_print(f"Error during file upload: {e}", True)
            raise HTTPException(status_code=500, detail="An error occurred while processing the file.")
        

    async def fetch_own_org_info(
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
            # query_params = {
            #     # **query_params,
            #     "filter__sys_organization_id": user_details['sys_organization_id']
            # }
            self.app_debug_print(f" org id : {user_details['sys_organization_id']}",True)

            check_data = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter___id": user_details['sys_organization_id']
                },
            )
            self.app_debug_print(f"\n\n\n\n check_data : {check_data}",True)
            if not check_data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            formatted_data_org_info = {}
            try:
                organization_instance = ModelService.convert_to_model_instance(SysOrganizationModel,check_data)
                self.app_debug_print(f"-> step 1: ",False)
                formatted_data_org_info = await  organization_instance.get_formated_data(self.accept_language,FormatedOutPut.FULL)
                self.app_debug_print(f"-> step 2 returned : {formatted_data_org_info} ",False)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid collection name: {organization_instance}")
            except PermissionError as e:
                self.app_debug_print(f"Error in fetch_data 4: {str(e)}",False)
                raise HTTPException(status_code=403, detail=str(e))

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": formatted_data_org_info
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch_data: > 1 {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
    async def fetch_single_user_info(
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

            user_id = query_params.get('user_id', None)
            if not user_id:
                message = self.get_response_message(MessageCategory.COMMON, "USER_ID_MISSING", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            check_data = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter___id": user_details['sys_organization_id']
                },
            )
            self.app_debug_print(f"\n\n\n\n check_data : {check_data}",True)
            if not check_data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter___id": user_id,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                },
            )
            self.app_debug_print(f"\n\n\n\n user_info : {user_info}",True)
            if not user_info:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            formatted_data_user_info = {}
            try:
                user_instance = ModelService.convert_to_model_instance(SysUserModel,user_info)
                self.app_debug_print(f"-> step 1: ",False)
                formatted_data_user_info = await  user_instance.get_formated_data(self.accept_language,FormatedOutPut.FULL)
                self.app_debug_print(f"-> step 2 returned : {formatted_data_user_info} ",False)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid collection name: {user_instance}")
            except PermissionError as e:
                self.app_debug_print(f"Error in fetch_data 4: {str(e)}",False)
                raise HTTPException(status_code=403, detail=str(e))
            
            # FETCH USER INFO 
            self.app_debug_print(f"\n\n\n\n formatted_data_user_info : {formatted_data_user_info}",True)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": formatted_data_user_info
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch_data: > 1 {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    

    # update_user_device_count
    async def update_user_device_count(
        self,
        request: Request,
        body: dict = Body(...)
    ):
        try:
            # DECODE USER TOKEN
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            self.app_debug_print(f"\n\nbody : {body}\n\n",True)

            # CHECK IF USER EXIST
            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id": body['sys_user_id'],
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                }
            )
            if not user_info:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # CHECK IF USER CONFIG EXIST
            user_config_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_USER_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__sys_user_id": body['sys_user_id'],
                }
            )
            if not user_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "USER_CONFIG_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            # UPDATE USER DEVICE COUNT
            updated = await self.generic_service.update_data_in_collection(
                collection_key=CollectionKey.CFG_USER_CONFIG,
                item_id=user_config_info['id'],
                data={
                    "allowed_device_count": body['allowed_device_count'],
                    "reason": body['reason'],
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
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f" \n\n Exception: {e}\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))




    async def fetch_main_profile(
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
            # query_params = {
            #     # **query_params,
            #     "filter__sys_organization_id": user_details['sys_organization_id']
            # }
            self.app_debug_print(f" org id : {user_details['sys_organization_id']}",True)

            check_data = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter___id": user_details['sys_organization_id']
                },
            )
            self.app_debug_print(f"\n\n\n\n check_data : {check_data}",True)
            if not check_data:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            # FETCH MAIN PROFILE
            main_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter___id": check_data['rbac_profile_id']
                },
            )
            self.app_debug_print(f"\n\n\n\n main_profil : {main_profil}",True)
            if not main_profil:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
             
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": main_profil
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch_data: > 1 {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
    
    async def fetch_org_charts(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page"),
        sort: Optional[Dict[str, int]] = {'created_at': -1},
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)


            self.app_debug_print(f"\n\n\n sort : {sort}\n\n\n",True)
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            raw_query_params = {
                **raw_query_params,
                "filter__sys_organization_id": str(user_details['sys_organization_id'])
            }

            query_params = self.convert_query_params(raw_query_params)
            sort = query_params.get('sort', {'created_at': -1})
            # If sort is a string, parse it into a dictionary
            self.app_debug_print(f"\n\n\n sort 0 > : {sort}\n\n\n", False)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",False)
            # If sort is a string, parse it into a dictionary
            self.app_debug_print(f"\n\n\n sort 1 > : {sort}\n\n\n", False)


            self.app_debug_print(f"\n\n\n sort 2> : {sort}\n\n\n", False)

            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_ORGANISM_CHART,
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
            formated_org_charts = []
            # Import the recursive chart processor utility
            from app.modules.core.utils.chart.recursive_chart_processor import RecursiveChartProcessor

            # Define ID extractor function based on output data type
            def extract_chart_id(element):
                """Extract chart ID based on output data type."""
                if output_data_type == OutputDataType.DATA_TABLE.value:
                    return element['id']['display_value']
                elif output_data_type == OutputDataType.DEFAULT.value:
                    return element['id']
                elif output_data_type == OutputDataType.TREE.value:
                    return element['id']
                else:
                    return None

            # Define count callback function
            async def get_counts_for_chart_id(cfg_organism_chart_id):
                """Get all counts for a specific chart ID."""
                if not cfg_organism_chart_id:
                    return {
                        "agent_count": 0,
                        "users_count": 0,
                        "rbac_profile_count": 0,
                        "rbac_role_count": 0
                    }

                # Get all counts concurrently for better performance
                agent_count, users_count, sys_profil_count, rbac_role_count = await AsyncExecutor.gather([
                    self.generic_service.count_data_from_collection(
                        collection_key=CollectionKey.SYS_ORGANIZATION_AGENT,
                        accept_language=self.accept_language,
                        query={
                            "filter__sys_organization_id": str(user_details['sys_organization_id']),
                            "filter__cfg_organism_chart_id": str(cfg_organism_chart_id)
                        },
                        user=user_details
                    ),
                    self.generic_service.count_data_from_collection(
                        collection_key=CollectionKey.SYS_USER,
                        accept_language=self.accept_language,
                        query={
                            "filter__sys_organization_id": str(user_details['sys_organization_id']),
                            "filter__cfg_organism_chart_id": str(cfg_organism_chart_id)
                        },
                        user=user_details
                    ),
                    self.generic_service.count_data_from_collection(
                        collection_key=CollectionKey.RBAC_PROFILE,
                        accept_language=self.accept_language,
                        query={
                            "filter__sys_organization_id": str(user_details['sys_organization_id']),
                            "filter__cfg_organism_chart_id": str(cfg_organism_chart_id)
                        },
                        user=user_details
                    ),
                    self.generic_service.count_data_from_collection(
                        collection_key=CollectionKey.RBAC_ROLE,
                        accept_language=self.accept_language,
                        query={
                            "filter__sys_organization_id": str(user_details['sys_organization_id']),
                            "filter__cfg_organism_chart_id": str(cfg_organism_chart_id)
                        },
                        user=user_details
                    )
                ])

                return {
                    "agent_count": agent_count,
                    "users_count": users_count,
                    "rbac_profile_count": sys_profil_count,
                    "rbac_role_count": rbac_role_count
                }

            # Process all chart data recursively using the utility
            formated_org_charts = await RecursiveChartProcessor.process_chart_with_counts(
                chart_data=data,
                count_callback=get_counts_for_chart_id,
                id_extractor=extract_chart_id
            )
            extra_data = {
                "max":0,
                "limit":limit
            }
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.CFG_ORGANISM_CHART,
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
                    "data": formated_org_charts,
                    **extra_data
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch_data: > 2 {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
        
    # ORGANIZATION BRANCHES
    async def add_branches_data(self,request: Request,background_tasks: BackgroundTasks, body: dict = Body(...)):
        """
        Endpoint to add a new document to the specified collection.
        """
        saved_profil_id = None
        try: 
            self.app_debug_print(f"\n\n organization body : {body}\n\n",True)
            org_data = OrganizationBranchCreate.model_validate(body, context={"language": self.accept_language})
            # DECODE USER TOKEN  fetch_data_from_collection(
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # USER ORGANIZATION
            user_organization = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id": user_details['sys_organization_id'],
                }
            )
            if not user_organization:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ORG_FOUND", self.accept_language)
                raise HTTPException(status_code=401, detail=message)

            # START GETTING SUPPORRT EMAIL ADDRESS
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__is_activated": True
                }
            )

            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            authenticationService = AuthenticatedService()
            support_email = await authenticationService.get_system_support_email(saas_config_info,self.accept_language)
            # END GETTING SUPPORRT EMAIL ADDRESS

            profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type = OutputDataType.DEFAULT,
                user=user_details,
                query={
                    "filter___id": org_data.rbac_profile_id
                }
            )
            self.app_debug_print(f"\n\n profil_info branch : {profil_info}\n\n",True)
            if not profil_info:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_PROFIL_FOUND", self.accept_language,email=support_email)
                raise HTTPException(status_code=401, detail=message)

            default_role = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__is_default":True,
                    "filter__rbac_profile_id":profil_info['id'],
                    "filter__system_reserved_actions":False,
                },
            )
            if not default_role:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ORG_DEFAULT_ROLE_FOUND", self.accept_language,email=support_email)
                raise HTTPException(status_code=401, detail=message)

            admin_user = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type = OutputDataType.DEFAULT,
                user=user_details,
                query={
                    "filter__username":str(org_data.admin_username).strip()
                }
            ) 
            
            generated_password:str = org_data.admin_password
            if org_data.is_auto_password_selected:
                generated_password = GeneratorService.strong_password_generator(10)
            
            # self.app_debug_print(f"\n\n generated_passwords : {generated_passwords}\n\n",True)
            
            if admin_user:
                # # DELETE CREATED PROFIL
                # await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_PROFIL, new_profil_id)
                # # DELETE CREATED ROLE
                # await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_ROLE, new_role_id)
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "USER_NAME_ALREADY_TAKEN", self.accept_language,username=org_data.admin_username)
                raise HTTPException(status_code=401, detail=message)
            
            #format phone numbers
            phone_numbers = []
            for phone in org_data.telephones:
                phone_numbers.append({
                    'phone_number':phone
                })
            emails = []
            for email in org_data.emails:
                emails.append({
                    "email":email
                })

            parent_entity = await SystemCountryService(self.accept_language).get_static_parent_entity_by_flag(
                str(org_data.ref_entity_id), 'country'
            )
            if not parent_entity:
                message = self.get_response_message(MessageCategory.COMMON, "NO_PARENT_ENTITY_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            self.app_debug_print(f"\n\n generated_passwords : {generated_password}\n\n",True) 
            org_data_to_save = {
                "ref_entity_id":org_data.ref_entity_id,
                "name":org_data.name,
                "rbac_profile_id":profil_info['id'],
                "sys_organization_id":user_details['sys_organization_id'],
                "phone_numbers":phone_numbers,
                "emails":emails,
                "others":org_data.others,
                "address":org_data.address,
                "contact_person":{
                    "first_name":org_data.contact_first_name,
                    "last_name":org_data.contact_last_name,
                    "gender":org_data.contact_gender,
                    "email":org_data.contact_email,
                    "phone_number":org_data.contact_phone_number,
                }
            }
            self.app_debug_print(f"\n\n\n\n\n\n  org_data_to_save : {org_data_to_save}",False)
            org_saved_item_id = await self.generic_service.add_data_to_collection(CollectionKey.SYS_ORGANIZATION, org_data_to_save, user=user_details, request=request)

            phone_numbers  = []
            phone_numbers.append({'phone_number':org_data.admin_phone_number})
            emails = []
            emails.append({'email':org_data.admin_email})
            self.app_debug_print(f"\n\n\n\n\n\n emails : {emails} | phones {phone_numbers}")
            user_data_to_save = {
                "username":org_data.admin_username,
                "account_status":AccountStatusFlag.ACTIVE.value,
                "password":self.hash_password(generated_password),
                "sys_organization_id":org_saved_item_id,
                "email":org_data.admin_email,
                "phone_number":org_data.admin_phone_number,
                "gender":org_data.admin_gender,
                "first_name":org_data.admin_first_name,
                "ref_entity_id":parent_entity['id'],
                "last_name":org_data.admin_last_name,
                "rbac_role_id":default_role['id'],
                "phone_numbers":phone_numbers,
                "emails":emails,
                "is_default":True,
                "rbac_profile_id":profil_info['id'],
                "others":[],
            }
            self.app_debug_print(f"\n\n\n\n\n\n object  : {user_data_to_save}")
            # Add data to the collection
            item_id = await self.generic_service.add_data_to_collection(CollectionKey.SYS_USER, user_data_to_save, user=user_details, request=request)
            self.app_debug_print(f"\n\n\n\n\n\n user saved : {item_id}",True)

            language = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_LANGUAGE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter__short_code": 'fr'
                }
            )

            ref_totp_mfa = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_MFAS,
                output_data_type=OutputDataType.DEFAULT,
                user=user_details,
                query={
                    "filter__flag": MFaFlag.SYCAMORE_2FA_APP.value
                }
            )
            if ref_totp_mfa:
                check_existing_cfg_user_mfa = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    output_data_type=OutputDataType.DEFAULT,
                    user=user_details,
                    query={
                        "filter__sys_user_id": item_id,
                        "filter__ref_mfa_id": ref_totp_mfa['id']
                    }
                )
                if not check_existing_cfg_user_mfa:
                    await self.generic_service.add_data_to_collection(
                        collection_key=CollectionKey.CFG_USER_MFA,
                        user=user_details,
                        request=request,
                        data={
                            "sys_user_id": item_id,
                            "ref_mfa_id": ref_totp_mfa['id'],
                            "is_configured": False,
                            "is_disabled":False,
                            "mfa_configuration_next_setup_at": datetime.now(),
                            "is_activated": True,
                        }
                    )

            # ADD USER CONFIG DEFAULT DATA
            if language:
                await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.CFG_USER_CONFIG,
                    user=user_details,
                    request=request,
                    data={
                        "sys_user_id":item_id,
                        "allowed_device_count":1,
                        "ref_language_id":language['id'],
                    }
                )
                self.app_debug_print(f"\n\n\n\n\n\n user config added",True)

            user_account_hash = HashService.generate_hash(f"{item_id}")
            user_account_socket_hash = HashService.generate_hash(f"{item_id}")
            data_update = {
                "user_account_hash":user_account_hash,
                "user_account_socket_hash":user_account_socket_hash
            }
            await self.generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=item_id, data=data_update)
            org_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter___id":org_saved_item_id
                }
            )
            # if org_info:
            asyncio.create_task(
                self._complete_org_creation(
                    profil_info=profil_info,
                    org_info=org_info,
                    ref_entity_id=org_data.ref_entity_id,
                    user_details=user_details,
                    new_profil_info=profil_info
                )
            )

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language,)
            return CustomJSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "status_code": status.HTTP_201_CREATED,
                        "message": message,
                        "data":org_saved_item_id
                    }
                )
            
        except ValidationError as e:
            # DELETE CREATED PROFIL AND ALL RELATED DATA
            if saved_profil_id:
                await self.rbac_role_service.delete_single_sys_profil(saved_profil_id)
            # Extract error messages and format them into a single line
            errors = e.errors()
            error_messages = []
            for error in errors:
                field = ".".join(map(str, error["loc"]))  # Get the field name (e.g., "body.password")
                msg = error.get("msg", "Invalid value")  # Get the error message
                error_messages.append(f"{field}: {msg}")
            
            # Join all error messages into a single line
            self.app_debug_print(f" user err : {e}",True)
            raise HTTPException(status_code=400, detail="; ".join(error_messages))
        except PermissionError as e:
            # DELETE CREATED PROFIL AND ALL RELATED DATA
            if saved_profil_id:
                await self.rbac_role_service.delete_single_sys_profil(saved_profil_id)
            self.app_debug_print(f" user err permission : {e}",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:

            # DELETE CREATED PROFIL AND ALL RELATED DATA
            if saved_profil_id:
                await self.rbac_role_service.delete_single_sys_profil(saved_profil_id)

            self.app_debug_print(f" user err exception : {e}",True)
            raise HTTPException(status_code=500, detail=str(e))
        
    async def add_old_branches_data(self,request: Request,background_tasks: BackgroundTasks, body: dict = Body(...)):
        """
        Endpoint to add a new document to the specified collection.
        """
        saved_profil_id = None
        try: 
            self.app_debug_print(f"\n\n organization body : {body}\n\n",True)
            org_data = OrganizationBranchCreate.model_validate(body, context={"language": self.accept_language})
            # DECODE USER TOKEN  fetch_data_from_collection(
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # USER ORGANIZATION
            user_organization = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id": user_details['sys_organization_id'],
                }
            )
            if not user_organization:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ORG_FOUND", self.accept_language)
                raise HTTPException(status_code=401, detail=message)
            
            # START GETTING SUPPORRT EMAIL ADDRESS
            saas_config_info  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SAAS_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__is_activated": True
                }
            )
            
            if not saas_config_info:
                message = self.get_response_message(MessageCategory.COMMON, "MISSING_SYSTEM_CONFIG", self.accept_language)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
            authenticationService = AuthenticatedService()
            support_email = await authenticationService.get_system_support_email(saas_config_info,self.accept_language) 
            # END GETTING SUPPORRT EMAIL ADDRESS
            
            profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type = OutputDataType.DEFAULT,
                user=user_details,
                query={
                    "filter___id": org_data.rbac_profile_id
                }
            ) 
            self.app_debug_print(f"\n\n profil_info branch : {profil_info}\n\n",True)
            if not profil_info: 
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_PROFIL_FOUND", self.accept_language,email=support_email)
                raise HTTPException(status_code=401, detail=message)
            # if  profil_info: 
            #     message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_PROFIL_FOUND", self.accept_language,email=support_email)
            #     raise HTTPException(status_code=401, detail=message)
            
            # CREATE ORGANIZATION PROFIL FROM PARENT PROFIL
            new_profil_id = await self.generic_service.add_data_to_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                user=user_details,
                request=request,
                data={
                    "name":f"Profil de l'organisation : {org_data.name}",
                    "description_str":profil_info['description_str'],
                    "sys_organization_id":None,
                    "rbac_profile_id":profil_info['id'],
                    # "flag":profil_info['flag'],
                    "is_default":False,
                    "system_reserved_actions":True,
                }
            )
            saved_profil_id = new_profil_id
            await self.rbac_role_service.create_cloned_sys_profil_from_parent(parent_rbac_profile_id=profil_info['id'],rbac_profile_id=new_profil_id)
            
            default_role = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter__is_default":True,
                    "filter__rbac_profile_id":profil_info['id'],
                    "filter__system_reserved_actions":True,
                }, 
            )
            if not default_role:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ORG_DEFAULT_ROLE_FOUND", self.accept_language,email=support_email)
                raise HTTPException(status_code=401, detail=message)
            
            new_profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id":new_profil_id,
                }, 
            )
            self.app_debug_print(f"\n\n\n\n\n\n new_profil_info >>> : {new_profil_info}",True)
            if not new_profil_info:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_PROFIL_FOUND", self.accept_language,email=support_email)
                raise HTTPException(status_code=404, detail=message)
            
        
            admin_user = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type = OutputDataType.DEFAULT,
                user=user_details,
                query={
                    "filter__username":str(org_data.admin_username).strip()
                }
            ) 
            
            generated_password:str = org_data.admin_password
            if org_data.is_auto_password_selected:
                generated_password = GeneratorService.strong_password_generator(10)
            
            # self.app_debug_print(f"\n\n generated_passwords : {generated_passwords}\n\n",True)
            
            if admin_user:
                # # DELETE CREATED PROFIL
                # await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_PROFIL, new_profil_id)
                # # DELETE CREATED ROLE
                # await self.generic_service.hard_delete_data_from_collection(CollectionKey.RBAC_ROLE, new_role_id)
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "USER_NAME_ALREADY_TAKEN", self.accept_language,username=org_data.admin_username)
                raise HTTPException(status_code=401, detail=message)
            
            #format phone numbers
            phone_numbers = []
            for phone in org_data.telephones:
                phone_numbers.append({
                    'phone_number':phone
                })
            emails = []
            for email in org_data.emails:
                emails.append({
                    "email":email
                })

            parent_entity = await SystemCountryService(self.accept_language).get_static_parent_entity_by_flag(
                str(org_data.ref_entity_id), 'country'
            )
            if not parent_entity:
                message = self.get_response_message(MessageCategory.COMMON, "NO_PARENT_ENTITY_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            self.app_debug_print(f"\n\n generated_passwords : {generated_password}\n\n",True) 
            org_data_to_save = {
                "ref_entity_id":org_data.ref_entity_id,
                "name":org_data.name,
                "rbac_profile_id":new_profil_id,
                "sys_organization_id":user_details['sys_organization_id'],
                "phone_numbers":phone_numbers,
                "emails":emails,
                "others":org_data.others,
                "address":org_data.address,
                "contact_person":{
                    "first_name":org_data.contact_first_name,
                    "last_name":org_data.contact_last_name,
                    "gender":org_data.contact_gender,
                    "email":org_data.contact_email,
                    "phone_number":org_data.contact_phone_number,
                }
            }
            self.app_debug_print(f"\n\n\n\n\n\n  org_data_to_save : {org_data_to_save}",False)
            org_saved_item_id = await self.generic_service.add_data_to_collection(CollectionKey.SYS_ORGANIZATION, org_data_to_save, user=user_details, request=request)
            
            self.app_debug_print(f"\n\n\n\n\n\n saved org_saved_item_id : {org_saved_item_id}",True)

            # CREATE ORGANIZATION DEFAULT ROLE
            new_role_data = {
                    "name":f"Rôle administrateur de la succursale {org_data.name} ",
                    "description_str":f"Rôle administrateur de la succursale {org_data.name} ",
                    "sys_organization_id":org_saved_item_id,
                    "rbac_profile_id":new_profil_id,
                    "flag":f"{default_role['flag']}_org_{org_saved_item_id}_super_admin",
                    "is_default":True,
                    "system_reserved_actions":True,
                    "sys_core_role_id":default_role['id']
                }
            self.app_debug_print(f"\n\n\n\n\n\n new_role_data : {new_role_data}",True)
            new_role_id = await self.generic_service.add_data_to_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                user=user_details,
                request=request,
                data=new_role_data
            )
            self.app_debug_print(f"\n\n\n\n new_role_id : {new_role_id}",True)
            asyncio.create_task(
                self.rbac_role_service.create_single_rbac_role_permissions_from_parent(
                    parent_rbac_role_id=default_role['id'],
                    rbac_role_id=new_role_id
                )
            )
            # await self.rbac_role_service.create_single_rbac_role_permissions_from_parent(parent_rbac_role_id=default_role['id'],rbac_role_id=new_role_id)

            # CREATE ALL ROLES
            all_profil_roles = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                user=user_details,
                query={
                    "filter__rbac_profile_id":profil_info['id'],
                    "filter__system_reserved_actions":True,
                    "filter__is_default":False,
                }
            )
            self.app_debug_print(f"\n\n\n\n\n\n all_profil_roles : {all_profil_roles}",True)
            for role in all_profil_roles:
                self.app_debug_print(f"\n\n\n\n\n\n loop role : {role}",True)
                # if role['is_default'] or role['flag'] == ESysProfilSuperUserRoleFlag.SYSTEM_PROFIL_SUPER_ADMIN.value or role['flag'] == ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN.value: continue
                saved_role = await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.RBAC_ROLE,
                    user=user_details,
                    request=request,
                    data={
                        "name":f"{role['name']}", 
                        "sys_organization_id":org_saved_item_id,
                        "rbac_profile_id":new_profil_id,
                        "flag":f"{role['flag']}_org_{org_saved_item_id}",
                        "is_default":False,
                        "system_reserved_actions":True,
                        "sys_core_role_id":role['id']
                    }
                )
                self.app_debug_print(f"\n\n\n\n\n\n saved_role : {saved_role}",True)
                asyncio.create_task(
                    self.rbac_role_service.create_single_rbac_role_permissions_from_parent(
                        parent_rbac_role_id=role['id'],
                        rbac_role_id=saved_role
                    )
                )
                # await self.rbac_role_service.create_single_rbac_role_permissions_from_parent(parent_rbac_role_id=role['id'],rbac_role_id=saved_role)
             
            phone_numbers  = []
            phone_numbers.append({'phone_number':org_data.admin_phone_number})
            emails = []
            emails.append({'email':org_data.admin_email})
            self.app_debug_print(f"\n\n\n\n\n\n emails : {emails} | phones {phone_numbers}")
            user_data_to_save = {
                "username":org_data.admin_username,
                "account_status":AccountStatusFlag.ACTIVE.value,
                "password":self.hash_password(generated_password),
                "sys_organization_id":org_saved_item_id,
                "email":org_data.admin_email,
                "phone_number":org_data.admin_phone_number,
                "gender":org_data.admin_gender,
                "first_name":org_data.admin_first_name,
                "ref_entity_id":parent_entity['id'],
                "last_name":org_data.admin_last_name,
                "rbac_role_id":new_role_id,
                "phone_numbers":phone_numbers,
                "emails":emails,
                "is_default":True,
                "rbac_profile_id":new_profil_id,
                "others":[],
            }
            self.app_debug_print(f"\n\n\n\n\n\n object  : {user_data_to_save}")
            # Add data to the collection
            item_id = await self.generic_service.add_data_to_collection(CollectionKey.SYS_USER, user_data_to_save, user=user_details, request=request)
            self.app_debug_print(f"\n\n\n\n\n\n user saved : {item_id}",True)

            language = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_LANGUAGE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter__short_code": 'fr'
                }
            )

            ref_totp_mfa = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_MFAS,
                output_data_type=OutputDataType.DEFAULT,
                user=user_details,
                query={
                    "filter__flag": MFaFlag.SYCAMORE_2FA_APP.value
                }
            )
            if ref_totp_mfa:
                check_existing_cfg_user_mfa = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    output_data_type=OutputDataType.DEFAULT,
                    user=user_details,
                    query={
                        "filter__sys_user_id": item_id,
                        "filter__ref_mfa_id": ref_totp_mfa['id']
                    }
                )
                if not check_existing_cfg_user_mfa:
                    await self.generic_service.add_data_to_collection(
                        collection_key=CollectionKey.CFG_USER_MFA,
                        user=user_details,
                        request=request,
                        data={
                            "sys_user_id": item_id,
                            "ref_mfa_id": ref_totp_mfa['id'],
                            "is_configured": False,
                            "is_disabled":False,
                            "mfa_configuration_next_setup_at": datetime.now(),
                            "is_activated": True,
                        }
                    )

            # ADD USER CONFIG DEFAULT DATA
            if language:
                await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.CFG_USER_CONFIG,
                    user=user_details,
                    request=request,
                    data={
                        "sys_user_id":item_id,
                        "allowed_device_count":1,
                        "ref_language_id":language['id'],
                    }
                )
                self.app_debug_print(f"\n\n\n\n\n\n user config added",True)

            user_account_hash = HashService.generate_hash(f"{item_id}")
            user_account_socket_hash = HashService.generate_hash(f"{item_id}")
            data_update = {
                "user_account_hash":user_account_hash,
                "user_account_socket_hash":user_account_socket_hash
            }
            await self.generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=item_id, data=data_update) 
            org_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                user=user_details,
                query={
                    "filter___id":org_saved_item_id
                }
            )
            # if org_info:
            asyncio.create_task(
                self._complete_org_creation(
                    profil_info=profil_info,
                    org_info=org_info,
                    ref_entity_id=org_data.ref_entity_id,
                    user_details=user_details,
                    new_profil_info=new_profil_info
                )
            )

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language,)
            return CustomJSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "status_code": status.HTTP_201_CREATED,
                        "message": message,
                        "data":org_saved_item_id
                    }
                )
            
        except ValidationError as e:
            # DELETE CREATED PROFIL AND ALL RELATED DATA
            if saved_profil_id:
                await self.rbac_role_service.delete_single_sys_profil(saved_profil_id)
            # Extract error messages and format them into a single line
            errors = e.errors()
            error_messages = []
            for error in errors:
                field = ".".join(map(str, error["loc"]))  # Get the field name (e.g., "body.password")
                msg = error.get("msg", "Invalid value")  # Get the error message
                error_messages.append(f"{field}: {msg}")
            
            # Join all error messages into a single line
            self.app_debug_print(f" user err : {e}",True)
            raise HTTPException(status_code=400, detail="; ".join(error_messages))
        except PermissionError as e:
            # DELETE CREATED PROFIL AND ALL RELATED DATA
            if saved_profil_id:
                await self.rbac_role_service.delete_single_sys_profil(saved_profil_id)
            self.app_debug_print(f" user err permission : {e}",True)
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:

            # DELETE CREATED PROFIL AND ALL RELATED DATA
            if saved_profil_id:
                await self.rbac_role_service.delete_single_sys_profil(saved_profil_id)

            self.app_debug_print(f" user err exception : {e}",True)
            raise HTTPException(status_code=500, detail=str(e))


    async def fetch_org_branches_data(
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
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            user_profil = getattr(request.state, "userProfil", None)
            if not user_profil:
                message = self.get_response_message(MessageCategory.COMMON, "USER_PROFIL_MISSING", self.accept_language)
                self.app_debug_print(f" missing user_profil : {message}",)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
            
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params =  self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",False)

            query_params = {
                **query_params,
                "filter__sys_organization_id": user_details['sys_organization_id']
            }
            
            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language= self.accept_language,
                user=user_details,
                query={
                    **query_params
                }
            )
            self.app_debug_print(f"\n returned out formatted_data  >: {len(data)} \n\n", False)
            formatted_data = []
            for element in data:
                self.app_debug_print(f"-> element: {element}",False)
                try:
                    organization_instance = ModelService.convert_to_model_instance(SysOrganizationModel,element)
                    self.app_debug_print(f"-> step 1: ",False)
                    organization = await  organization_instance.get_formated_data(self.accept_language,FormatedOutPut.FULL)
                    self.app_debug_print(f"-> step 2 returned : {organization} ",False)
                    formatted_data.append(organization)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid collection name: {organization_instance}")
                except PermissionError as e:
                    self.app_debug_print(f"Error in fetch_data 4: {str(e)}",False)
                    raise HTTPException(status_code=403, detail=str(e))
                
            self.app_debug_print(f"Query data: {len(data)}",False)
            extra_data = {}
            # if OutputDataType(output_data_type).value == OutputDataType.DATA_TABLE:
            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.SYS_ORGANIZATION,
                    accept_language= self.accept_language,
                    user=user_details,
                    query={
                        **query_params
                    }
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

        except PermissionError as e:
            self.app_debug_print(f"Error in fetch_data 1: {str(e)}",False)
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            self.app_debug_print(f"ERROR fetch org 2: {e}",True)
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch_data 3: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


    async def hard_delete_branches_data(
        self,
        request: Request,):
        """
        Endpoint to hard delete a document in the specified collection.
        """
        try: 
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)

            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message',None)
            # sudo_can_proceed = sudo_action.get('can_proceed',True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_400_BAD_REQUEST,
            #             content={
            #                 "status_code": status.HTTP_400_BAD_REQUEST,
            #                 "message": sudo_message,
            #             }
            #         )
            item_id = request.query_params.get('item_id',None)
            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            # CHECK ORGANIZATION EXIST
            organization_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id":  item_id,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                }
            )
            if not organization_info:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_ORG_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            # DELETE ALL ORGANIZATION AGENT
            agents = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION_AGENT,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                user=user_details,
                query={
                    "filter__sys_organization_id": item_id,
                }
            )
            for agent in agents:
                await self.generic_service.hard_delete_data_from_collection(
                    collection_key=CollectionKey.SYS_ORGANIZATION_AGENT,
                    item_id=agent['id']
                )
                self.app_debug_print(f" deleted agent : {agent['id']}",True)

            # DELETE PROFIL
            await self.rbac_role_service.delete_single_sys_profil(organization_info['rbac_profile_id'])

            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_DELETED_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": message,
                }
            ) 
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        

    async def search_branches_data(
        self,
        request: Request,
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            

            if not user_profil:
                message = self.get_response_message(MessageCategory.COMMON, "USER_PROFIL_MISSING", self.accept_language)
                self.app_debug_print(f" missing user_profil : {message}",)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
            
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            search_key= raw_query_params.get('search_key','')
            # ADD STATIC FILTER
            query_params = {
                # **raw_query_params,
                "$or":[
                    {
                        "sys_organization_id": ObjectId(user_details['sys_organization_id']),
                        "name": { '$regex': f'{search_key}', '$options': "i" }
                    }, 
                ]
            }
            
            
            # query_params = convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",True)
            
            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_native_query_data_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                all_data=all_data,
                page=page,
                limit=limit,
                accept_language= self.accept_language,
                native_query={
                    **query_params
                }
            )
            self.app_debug_print(f"Query data user: {len(data)}",True)
            extra_data = {}
            formatted_data = []
            for element in data:
                user_instance = ModelService.convert_to_model_instance(SysOrganizationModel,element)
                user = await  user_instance.get_formated_data(self.accept_language,FormatedOutPut.FULL)
                formatted_data.append(user)

            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.SYS_ORGANIZATION,
                    accept_language= self.accept_language,
                    user=user_details,
                    query={
                        **query_params
                    }
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

        except PermissionError as e:
            self.app_debug_print(f"Error in users 1: {str(e)}",True)
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            self.app_debug_print(f"Error in users 2: {str(e)}",True)
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in users 1: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
        


    # USER PRIVILEGES
    async def fetch_user_privileges_head(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(
            OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        """
        Generic endpoint to fetch data based on collection name.
        """
        try: 
            # DECODE USER TOKEN 
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            if not user_details:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            if not user_profil:
                message = self.get_response_message(MessageCategory.COMMON, "USER_PROFIL_MISSING", self.accept_language)
                self.app_debug_print(f" missing user_profil : {message}",)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
            

            user_id = request.query_params.get('user_id', None)
            if not user_id:
                message = self.get_response_message(MessageCategory.COMMON, "USER_ID_MISSING", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            # GET USER INFO
            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id": user_id,
                    "filter__sys_organization_id": user_details['sys_organization_id'],
                }
            )
            if not user_info:
                message = self.get_response_message(MessageCategory.COMMON, "USER_NOT_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            # GET ORGANIZATION INFO
            organization_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                user=user_details,
                query={
                    "filter___id": user_details['sys_organization_id'],
                }
            )
            if not organization_info:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ORG_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            

            # CHECK IF THE ROLE BELONGS TO THE ORGANIZATION
            role_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language= self.accept_language,
                user=user_details,
                query={
                    "filter___id":user_info['rbac_role_id'],
                }
            )
            if not role_info:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            # PIPELINE TO RBAC_RESTRICTED_PROFIL JOIN PERMISSION WHERE TARGETED_ID IS JOINED TO RBAC_PERMISSION
            role_permissions_pipeline = [
                {
                    '$match': {
                        'rbac_profile_id': ObjectId(user_info['rbac_profile_id'])
                    }
                }, {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION.model_name}", 
                        'localField': 'targeted_id', 
                        'foreignField': '_id', 
                        'as': 'unwind__rbac_permission'
                    }
                }, {
                    '$unwind': {
                        'path': '$unwind__rbac_permission', 
                        'preserveNullAndEmptyArrays': False
                    }
                }, {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_TITLE.model_name}",
                        'localField': 'unwind__rbac_permission.rbac_title_id', 
                        'foreignField': '_id', 
                        'as': 'unwind__rbac_title'
                    }
                }, {
                    '$unwind': {
                        'path': '$unwind__rbac_title', 
                        'preserveNullAndEmptyArrays': False
                    }
                }, {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                        'localField': 'unwind__rbac_permission._id',
                        'foreignField': 'rbac_permission_id',
                        'as': 'unwind__rbac_privilege'
                    }
                }, {
                    '$unwind': {
                        'path': '$unwind__rbac_privilege',
                        'preserveNullAndEmptyArrays': True
                    }
                },
                {
                    '$match': {
                        "unwind__rbac_permission.is_accessible_to_all_profil":False,
                        # Filter for privileges with status 'added' for specific user or allow null/empty privileges
                        '$or': [
                            {
                                '$and': [
                                    {'unwind__rbac_privilege.status': 'added'},
                                    {'unwind__rbac_privilege.sys_user_id': user_id}
                                ]
                            },
                            {'unwind__rbac_privilege': None}
                        ]
                    }
                },
            ]
            role_permissions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL.value,
                output_data_type=OutputDataType.DATA_TABLE.value,
                accept_language= self.accept_language,
                page=0,
                limit=100000,
                pipeline=role_permissions_pipeline,
            )
            # Process your data
            hierarchy = await self.rbac_role_service.build_role_joined_to_permission_rbac_hierarchy(role_permissions,output_data_type,user_info['rbac_role_id'])
            self.app_debug_print(f"\n\n\n role permissions LEN: {len(hierarchy)} \n\n\n",True)
            # ORGANIZATION PROFIL PERMISSIONS
            # PIPELINE TO RBAC_RESTRICTED_PROFIL JOIN PERMISSION WHERE TARGETED_ID IS JOINED TO RBAC_PERMISSION
            profil_permissions_pipeline = [
                {
                    '$match': {
                        'rbac_profile_id': ObjectId(organization_info['rbac_profile_id'])
                    }
                }, {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PERMISSION.model_name}", 
                        'localField': 'targeted_id', 
                        'foreignField': '_id', 
                        'as': 'unwind__rbac_permission'
                    }
                }, {
                    '$unwind': {
                        'path': '$unwind__rbac_permission', 
                        'preserveNullAndEmptyArrays': False
                    }
                }, {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_TITLE.model_name}", 
                        'localField': 'unwind__rbac_permission.rbac_title_id', 
                        'foreignField': '_id', 
                        'as': 'unwind__rbac_title'
                    }
                }, {
                    '$unwind': {
                        'path': '$unwind__rbac_title', 
                        'preserveNullAndEmptyArrays': False
                    }
                }, {
                    '$lookup': {
                        'from': f"{CollectionKey.RBAC_PRIVILEGE.model_name}",
                        'localField': 'unwind__rbac_permission._id',
                        'foreignField': 'rbac_permission_id',
                        'as': 'unwind__rbac_privilege'
                    }
                }, {
                    '$unwind': {
                        'path': '$unwind__rbac_privilege',
                        'preserveNullAndEmptyArrays': True
                    }
                },
                {
                    '$match': {
                        "unwind__rbac_permission.is_accessible_to_all_profil":False,
                        # Filter for privileges with status 'added' for specific user or allow null/empty privileges
                        '$or': [
                            {
                                '$and': [
                                    {'unwind__rbac_privilege.status': 'added'},
                                    {'unwind__rbac_privilege.sys_user_id': user_id}
                                ]
                            },
                            {'unwind__rbac_privilege': None}
                        ]
                    }
                },
            ]
            profil_permissions = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.RBAC_RESTRICTED_PROFIL.value,
                output_data_type=OutputDataType.DATA_TABLE.value,
                accept_language= self.accept_language,
                page=0,
                limit=100000,
                pipeline=profil_permissions_pipeline,
            )
            self.app_debug_print(f"\n\n\n profil initial permissions LEN: {len(profil_permissions)} \n\n\n",True)
            # Process your data
            organization_profil_hierarchy = await self.rbac_role_service.build_profil_not_joined_to_permission_rbac_hierarchy(profil_permissions,output_data_type,organization_info['rbac_profile_id'],user_id)
            self.app_debug_print(f"\n\n\n org profil permissions LEN: {len(organization_profil_hierarchy)} \n\n\n",True)
            # Use intelligent merge instead of simple concatenation
            merged_permissions = self.rbac_role_service.merge_permission_hierarchies(hierarchy, organization_profil_hierarchy)
            self.app_debug_print(f"\n\n\n merged_permissions LEN: {len(merged_permissions)} \n\n\n",True)
            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Data fetched successfully",
                    "data": merged_permissions,
                }
            )

        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            self.app_debug_print(f"Error in fetch_data 2: {str(e)}",True)
            raise e  # Rethrow HTTP exceptions for proper error status codes
        except Exception as e:
            self.app_debug_print(f"Error in fetch user privileges 3: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    async def add_user_privileges_data(
        self,
        request: Request,
        body: Dict[str, Any]
    ):
        try:
            self.app_debug_print(f" \n\n\n add_user_privileges_data : {body} \n\n\n",False)
            # sudo_action = await sudo_action_middleware(request)
            # sudo_message = sudo_action.get('message',None)
            # sudo_can_proceed = sudo_action.get('can_proceed',True)
            # if sudo_message and sudo_can_proceed == False:
            #     return CustomJSONResponse(
            #             status_code=status.HTTP_400_BAD_REQUEST,
            #             content={
            #                 "status_code": status.HTTP_400_BAD_REQUEST,
            #                 "message": sudo_message,
            #             }
            #         )
            
            user_details = await self.get_user_info(request,self.accept_language)
            # user_details = await self.get_user_info(request=request,accept_language=accept_language)
            api_Consumer = await self.get_api_consumer(request=request,accept_language= self.accept_language)
            user_profil = await self.get_user_profil(request=request,accept_language= self.accept_language)

            self.app_debug_print(f" \n\n\n body : {body} \n\n\n",False)
            validator_data = UserPrivilegePermissionCreate.model_validate(body, context={"language": self.accept_language})
            self.app_debug_print(f" \n\n\n validator_data : {validator_data} \n\n\n",False)

            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language= self.accept_language,
                user=user_details,
                query = {
                    "filter___id":validator_data.sys_user_id,
                }
            )
            if not user_info:
                message = self.get_response_message(MessageCategory.NOT_FOUND, "NO_SUCH_DATA_DATA_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            # ADD NEW RBAC PERMISSION ROLES
            for permission_id in validator_data.rbac_permissions:
                new_perm_tar_role_doc = {
                    "sys_user_id": validator_data.sys_user_id,
                    "rbac_permission_id": permission_id,
                    "status":EAccessFlag.ADDED.value,
                    "sys_organization_id":user_details['sys_organization_id'],
                }
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_PRIVILEGE.value,
                    filter_data={
                        "sys_user_id":new_perm_tar_role_doc['sys_user_id'],
                        'rbac_permission_id':new_perm_tar_role_doc['rbac_permission_id']
                    },
                    update_data=new_perm_tar_role_doc)
                
            message = self.get_response_message(MessageCategory.SUCCESS, "DATA_ADD_SUCCESSED", self.accept_language)
            return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": message,
                    }
                )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.app_debug_print(f" \n\n Exception: {e}\n\n",True)
            raise HTTPException(status_code=500, detail=str(e))



    async def fetch_user_login_histories(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = Query(OutputDataType.DEFAULT, description="Format data for selection"),
        all_data: Optional[bool] = Query(False, description="Fetch all data"),
        page: Optional[int] = Query(0, description="Page number for pagination"),
        limit: Optional[int] = Query(10, description="Number of items per page")
    ):
        try:
            user_details = await self.get_user_info(request,self.accept_language)
            api_Consumer = await self.get_api_consumer(request,self.accept_language)
            user_profil = await self.get_user_profil(request,self.accept_language)
            
            # Convert query parameters to dictionary and handle type conversions
            raw_query_params: Dict[str, str] = dict(request.query_params)
            query_params =  self.convert_query_params(raw_query_params)
            self.app_debug_print(f"Query Parameters (converted): {query_params}",False)

            # Fetch data from the collection using CollectionKey
            data = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language= self.accept_language,
                user=user_details,
                query={
                    **query_params
                }
            )
            self.app_debug_print(f"Query data user: {len(data)}",True)
            extra_data = {}
            formatted_data = []
            for element in data:
                # user_instance = ModelService.convert_to_model_instance(OpsUserLoginHistoryModel,element)
                # user = await  user_instance.get_formated_data(self.accept_language)
                user_device_id = extract_field_on_output_data_element(element,'cfg_user_device_id',output_data_type)
                user_device = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_DEVICE,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language= self.accept_language,
                    user=user_details,
                    query = {
                        "filter___id":user_device_id,
                    }
                )
                # Fetch login activities
                login_history_id = extract_field_on_output_data_element(element,'id',output_data_type)
                login_activities = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.OPS_USER_LOGIN_DAILY_ACTIVITY,
                    all_data=True,
                    page=0,
                    limit=100000,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language= self.accept_language,
                    user=user_details,
                    query = {
                        "filter__ops_user_login_history_id":login_history_id,
                    }
                )
                item = {
                    "id":element['id'],
                    "identifier":element['identifier'],
                    "status":element['status'],
                    "session_id_str":element['session_id_str'],
                    # "session_actual_expiration":element['session_actual_expiration'], session_last_activity
                    "session_last_activity":element['session_last_activity'],
                    "ip_address":element['ip_address'],
                    "sys_user_id":element['sys_user_id'],
                    "user_device":{} if not user_device else {
                        "id":user_device['id'],
                        "status":user_device['status'],
                        "device_id_str":user_device['device_id_str'],
                        "device_info":user_device['device_info'],
                    },
                    "login_activities":login_activities
                }
                formatted_data.append(item)

            if not all_data:
                # get max
                max_data = await self.generic_service.count_data_from_collection(
                    collection_key=CollectionKey.OPS_USER_LOGIN_HISTORY,
                    accept_language=self.accept_language,
                    user=user_details,
                    query={
                        **query_params
                    }
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
        except Exception as e:
            self.app_debug_print(f"Error fetching user login histories: {str(e)}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    def send_password_reset_email_background(self, email, otp_code, mail_title_translated,
                                           mail_message_translated, second_mail_message_translated,
                                           mail_note_translated, reset_password_redirect_url,
                                           update_here_message, accept_language):
        """
        Background task method for sending password reset email.
        This runs asynchronously without blocking the main request.
        """
        try:
            self.app_debug_print(f"Starting background password reset email sending to {email}", True)

            self.email_sender_service.sending_translated_email_with_redirect_button(
                email_to=email,
                subject=f"{otp_code} - {mail_title_translated}",
                mail_title_translated=mail_title_translated,
                mail_message_translated=mail_message_translated,
                second_mail_message_translated=second_mail_message_translated,
                mail_note_translated=mail_note_translated,
                accept_language=accept_language,
                action_button_url=reset_password_redirect_url,
                action_button_text=update_here_message,
            )

            self.app_debug_print(f"Background password reset email sent successfully to {email}", True)

        except Exception as e:
            self.app_debug_print(f"Failed to send background password reset email to {email}: {e}", True)

    async def fetch_organization_related_profiles(
        self,
        request: Request,
        raw_query_params: dict,
    ):
        try:
            """Fetch profiles linked to an organization via CFG_RELATED_SYSTEM_PROFIL"""
            query_params = self.convert_query_params(raw_query_params)
            item_id = raw_query_params.get('item_id', None)

            user_details = await self.get_user_info(request,self.accept_language)

            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            sys_org = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter___id": item_id},
                user=user_details,
            )
            if not sys_org:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ORG_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            rbac_profile_id = sys_org['rbac_profile_id']
            sys_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter___id": rbac_profile_id},
                user=user_details,
            )
            if not sys_profil:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ORG_PROFIL_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)

            output_data_type = query_params.get("output_data_type", OutputDataType.DEFAULT.value)
            all_data = query_params.get("all_data", False)
            page = query_params.get("page", 0)
            limit = query_params.get("limit", 100)
            sort = query_params.get("sort", {})

            # Fetch related profiles from junction table
            list_of_related_profiles = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={"filter__targeted_id": item_id},
                user=user_details,
                sort=sort
            )
            self.app_debug_print(f"Query related profiles: {len(list_of_related_profiles)}", True)
            if len(list_of_related_profiles) == 0:

                # update max
                if sys_profil['is_default']:
                    await self.generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
                        accept_language=self.accept_language,
                        update_data={
                            "targeted_id": item_id,
                            "rbac_profile_id":rbac_profile_id
                        },
                        filter_data={
                            "targeted_id": item_id,
                            "rbac_profile_id":rbac_profile_id
                        }
                    )
                elif 'rbac_profile_id' in sys_profil:
                    parent_profil = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.RBAC_PROFILE,
                        output_data_type=OutputDataType.DEFAULT.value,
                        accept_language=self.accept_language,
                        query={"filter___id":sys_profil['rbac_profile_id']},
                        user=user_details,
                    )
                    if parent_profil:
                        await self.generic_service.upsert_data_to_collection(
                            collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
                            accept_language=self.accept_language,
                            update_data={
                                "targeted_id": item_id,
                                "rbac_profile_id":parent_profil['id']
                            },
                            filter_data={
                                "targeted_id": item_id,
                                "rbac_profile_id":parent_profil['id']
                            }
                        )

            formatted_profiles = []
            for related_profile in list_of_related_profiles:
                rbac_profile_id = related_profile.get('rbac_profile_id',{}).get('real_value',None) # extract_field_on_output_data_element(related_profile, 'rbac_profile_id', output_data_type)

                # Fetch profile details
                profile_data = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_PROFILE,
                    output_data_type=OutputDataType(output_data_type).value,
                    accept_language=self.accept_language,
                    query={"filter___id": rbac_profile_id},
                    user=user_details,
                    sort=sort
                )

                if not profile_data:
                    continue

                formatted_profiles.append({
                    **related_profile,
                    "rbac_profil": profile_data
                })

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": formatted_profiles,
                    "max": len(formatted_profiles),
                    "limit": limit,
                    "page": page
                },
            )
        except Exception as e:
            format_error = format_exception("Error in fetch_organization_related_profiles", e)
            self.app_debug_print(f"Error in fetch_organization_related_profiles: {format_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    async def fetch_organization_available_profiles(
        self,
        request: Request,
        raw_query_params: dict,
    ):
        try:
            """Fetch profiles NOT yet linked to the organization"""
            query_params = self.convert_query_params(raw_query_params)
            item_id = raw_query_params.get('item_id', None)

            user_details = await self.get_user_info(request,self.accept_language)

            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            organization_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter___id": item_id},
                user=user_details,
            )
            if not organization_info:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ORG_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            organization_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter___id": organization_info['rbac_profile_id']},
                user=user_details,
            )
            if not organization_profil:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ORG_PROFIL_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            
            is_organization_profil_default = organization_profil['is_default']
            if not is_organization_profil_default:
                organization_profil = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_PROFILE,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={"filter___id": organization_profil['rbac_profile_id']},
                    user=user_details,
                )
                if not organization_profil:
                    message = self.get_response_message(MessageCategory.COMMON, "NO_ORG_PROFIL_FOUND", self.accept_language)
                    raise HTTPException(status_code=404, detail=message)

            output_data_type = query_params.get("output_data_type", OutputDataType.DEFAULT.value)
            sort = query_params.get("sort", {})
            

            customer_profil_flags = [
            ]
            organization_profil_flags = [
            ]
            excluded_profil_flags = [
                ESysProfileFlag.SYSTEM_PROFIL.value,
                ESysProfileFlag.SYSTEM_BRANCH_PROFIL.value,
                ESysProfileFlag.TEST_SYS_PROFIL.value,

                # TODO: REMOVE LATER
                ESysProfileFlag.COMMON_PROFIL.value, 
            ]

            is_organization = organization_profil['flag'] in organization_profil_flags


            # Fetch profiles already linked to this organization
            list_of_related_profiles = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                all_data=True,
                user=user_details,
                query={"filter__targeted_id": item_id}
            )

            # Fetch all profiles
            all_profiles = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                all_data=True,
                user=user_details,
                query={
                    "filter__is_activated": True,
                    "filter__is_default": True,
                    # "filter__flag__not_in": excluded_profil_flags,
                },
            )


            formatted_data = []
            for profile in all_profiles:
                sys_profil_flag = extract_field_on_output_data_element(profile, 'flag', output_data_type)
                if sys_profil_flag in excluded_profil_flags:
                    continue
                if is_organization and sys_profil_flag in customer_profil_flags:
                    continue
                rbac_profile_id = extract_field_on_output_data_element(profile, 'id', output_data_type)
                sys_profil_name = extract_field_on_output_data_element(profile, 'name', output_data_type)
                is_profile_linked = False

                for related_profile in list_of_related_profiles:
                    rbac_profile_id_linked = related_profile.get('rbac_profile_id',{}).get('real_value',None) # extract_field_on_output_data_element(related_profile, 'rbac_profile_id', output_data_type)
                    print(f"\n\n name : {sys_profil_name} rbac_profile_id_linked: {rbac_profile_id_linked} == rbac_profile_id: {rbac_profile_id} = {str(rbac_profile_id_linked) == str(rbac_profile_id)}\n\n")
                    if str(rbac_profile_id_linked) == str(rbac_profile_id):
                        is_profile_linked = True
                        break

                if is_profile_linked:
                    continue

                formatted_data.append({**profile})

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": formatted_data,
                    "max": len(formatted_data),
                },
            )
        except Exception as e:
            format_error = format_exception("Error in fetch_organization_available_profiles", e)
            self.app_debug_print(f"Error in fetch_organization_available_profiles: {format_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
    async def _fetch_default_currency_from_entity(self, entity_id):
        try:
            default_currency = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_DEFAULT_RELATED_CURRENCY,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter__targeted_id": entity_id},
            )
            if not default_currency:
                message = self.get_response_message(MessageCategory.COMMON, "NO_DEFAULT_CURRENCY_FOUND", self.accept_language)
                raise HTTPException(status_code=500, detail=message)
            return default_currency
        except Exception as e:
            format_error = format_exception("Error in _fetch_default_currency_from_entity", e)
            self.app_debug_print(f"Error in _fetch_default_currency_from_entity: {format_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
 

    async def patch_organization_to_add_remove_profile(
        self,
        request: Request,
        raw_query_params: dict,
        body: dict,
    ):
        try:
                """Main PATCH method to add or remove profiles from organization"""
                item_id = raw_query_params.get('item_id', None)

                user_details = await self.get_user_info(request,self.accept_language)

                if not item_id:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                flag = body.get('flag', None)
                if not flag:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_FLAG_PROVIDED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                profile_id = body.get('profile_id', None)
                if not profile_id:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_PROFILE_ID_PROVIDED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                
                org_data = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.SYS_ORGANIZATION,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={"filter___id": item_id},
                    user=user_details,
                )
                if not org_data:
                    message = self.get_response_message(MessageCategory.COMMON, "NO_ORG_FOUND", self.accept_language)
                    raise HTTPException(status_code=404, detail=message)
                
                org_profil = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_PROFILE,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={"filter___id": profile_id},
                    user=user_details,
                )
                if not org_profil:
                    message = self.get_response_message(MessageCategory.COMMON, "NO_PROFIL_FOUND", self.accept_language)
                    raise HTTPException(status_code=404, detail=message)
                
                # we can not add profil to reserverd profil or if profil has not parent
                # if org_profil['system_reserved_actions'] or not org_profil['rbac_profile_id']:
                #     message = self.get_response_message(MessageCategory.EXCEPTIONS, "CANT_ADD_RESERVED_PROFIL", self.accept_language)
                #     raise HTTPException(status_code=400, detail=message)
                
                cfg_organization_related_profil = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
                    output_data_type=OutputDataType.DEFAULT.value,
                    all_data=True,
                    accept_language=self.accept_language,
                    query={"filter__targeted_id": item_id, },
                    # "filter__rbac_profile_id": profile_id
                    user=user_details,
                )
                exist_related_profil = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
                    output_data_type=OutputDataType.DEFAULT.value,
                    all_data=True,
                    accept_language=self.accept_language,
                    query={"filter__targeted_id": item_id, "filter__rbac_profile_id": profile_id},
                    # "filter__rbac_profile_id": profile_id
                    user=user_details,
                )
                if len(exist_related_profil) == 1 and flag == 'add':
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "PROFILE_ALREADY_ADDED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                
                # if len ==1 and flag == 'remove': raise error
                if len(cfg_organization_related_profil) == 1 and flag == 'remove':
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "CANT_REMOVE_LAST_PROFILE", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                if flag == 'add':
                    await self.add_profile_to_organization(rbac_profile_id=profile_id, targeted_id=item_id,current_org_info=org_data)
                else:
                    await self.remove_profile_from_organization(rbac_profile_id=profile_id, targeted_id=item_id,current_org_info=org_data)

                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"status_code": status.HTTP_200_OK, "message": message}
                )
        except Exception as e:
            format_error = format_exception("Error in patch_organization_to_add_remove_profile", e)
            self.app_debug_print(f"Error in patch_organization_to_add_remove_profile: {format_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")



    async def patch_organization_to_add_remove_application_group(
        self,
        request: Request,
        raw_query_params: dict,
        body: dict,
    ):
        try:
                """Main PATCH method to add or remove profiles from organization"""
                sys_organization_id = raw_query_params.get('sys_organization_id', None)

                user_details = await self.get_user_info(request,self.accept_language)

                if not sys_organization_id:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                flag = body.get('flag', None)
                if not flag:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_FLAG_PROVIDED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                ref_application_group_id = body.get('ref_application_group_id', None)
                if not ref_application_group_id:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_APPLICATION_GROUP_ID_PROVIDED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)
                
                cfg_organization_related_profil = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                    output_data_type=OutputDataType.DEFAULT.value,
                    all_data=True,
                    accept_language=self.accept_language,
                    query={"filter__targeted_id": sys_organization_id,},
                    user=user_details,
                    #  "filter__ref_application_group_id": ref_application_group_id
                )
                # if len ==1 and flag == 'remove': raise error
                if len(cfg_organization_related_profil) == 1 and flag == 'remove':
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "CANT_REMOVE_LAST_PROFILE", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                if flag == 'add':
                    await self.add_application_group_to_organization(ref_application_group_id=ref_application_group_id, targeted_id=sys_organization_id)
                else:
                    await self.remove_application_group_from_organization(ref_application_group_id=ref_application_group_id, targeted_id=sys_organization_id)

                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"status_code": status.HTTP_200_OK, "message": message}
                )
        except Exception as e:
            format_error = format_exception("Error in patch_organization_to_add_remove_application_group", e)
            self.app_debug_print(f"Error in patch_organization_to_add_remove_application_group: {format_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")



    async def add_application_group_to_organization(self, ref_application_group_id: str, targeted_id: str):
        """Helper method to add profile to organization"""
        self.app_debug_print(f"\n\n\n\n\n\n [add_application_group_to_organization] : {ref_application_group_id} | {targeted_id}",True)
        try:

            data = {"ref_application_group_id": ref_application_group_id, "targeted_id": targeted_id}
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                filter_data=data,
                update_data=data,
            )
            return True
        except Exception as e:
            format_error = format_exception("Error in add_application_group_to_organization", e)
            self.app_debug_print(f"Error in add_application_group_to_organization: {format_error}",True)
            return False
    
    async def remove_application_group_from_organization(self, ref_application_group_id: str, targeted_id: str):
        """Helper method to remove profile from organization"""
        self.app_debug_print(f"\n\n\n\n\n\n [remove_application_group_from_organization] : {ref_application_group_id} | {targeted_id}",True)
        try:
            deletion = await self.generic_service.hard_delete_with_query_data_from_collection(
                collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                query={"ref_application_group_id": ObjectId(ref_application_group_id), "targeted_id": ObjectId(targeted_id)}
            )
            return True
        except Exception as e:
            format_error = format_exception("Error in remove_application_group_from_organization", e)
            self.app_debug_print(f"Error in remove_application_group_from_organization: {format_error}",True)
            return False
    
    async def add_profile_to_organization(self, rbac_profile_id: str, targeted_id: str,current_org_info: dict):
        """Helper method to add profile to organization"""
        try:
            self.app_debug_print(f"\n\n\n\n\n\n [add_profile_to_organization] : {rbac_profile_id} | {targeted_id}",True)
            data = {"rbac_profile_id": rbac_profile_id, "targeted_id": targeted_id}
            self.app_debug_print(f"\n\n\n\n\n\n data for add_profile_to_organization : {data}",True)
            await self.generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
                filter_data=data,
                update_data=data,
            )

            current_profil_default_role = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__rbac_profile_id":rbac_profile_id,
                    "filter__system_reserved_actions":True,
                    "filter__is_default":True,
                }
            )
            self.app_debug_print(f"\n\n\n\n\n\n current_profil_default_role : {current_profil_default_role}",True)

            org_profil_default_role = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__sys_organization_id":targeted_id,
                    "filter__rbac_profile_id":current_org_info['rbac_profile_id'],
                    "filter__system_reserved_actions":True,
                    "filter__is_default":True,
                }
            )
            self.app_debug_print(f"\n\n\n\n\n\n org_profil_default_role : {org_profil_default_role}",True)

            # MERGE PERMISSION FROM NEW PROFIL DEFAULT ROLE
            await self.rbac_role_service.create_single_rbac_role_permissions_from_parent(parent_rbac_role_id=current_profil_default_role['id'],rbac_role_id=org_profil_default_role['id'])

            all_profil_roles = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={
                    "filter__rbac_profile_id":rbac_profile_id,
                    "filter__system_reserved_actions":True,
                    "filter__is_default":False,
                }
            )
            self.app_debug_print(f"\n\n\n\n\n\n all_profil_roles : {all_profil_roles}",True)
            for role in all_profil_roles:
                self.app_debug_print(f"\n\n\n\n\n\n loop role : {role}",True)
                # if role['is_default'] or role['flag'] == ESysProfilSuperUserRoleFlag.SYSTEM_PROFIL_SUPER_ADMIN.value or role['flag'] == ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN.value: continue
                saved_role = await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.RBAC_ROLE,
                    data={
                        "name":f"{role['name']}", 
                        "sys_organization_id":targeted_id,
                        "rbac_profile_id":current_org_info['rbac_profile_id'],
                        "flag":f"{role['flag']}_org_{targeted_id}",
                        "is_default":False,
                        "system_reserved_actions":True,
                        "sys_core_role_id":role['id']
                    }
                )
                self.app_debug_print(f"\n\n\n\n\n\n saved_role : {saved_role}",True)
                await self.rbac_role_service.create_single_rbac_role_permissions_from_parent(parent_rbac_role_id=role['id'],rbac_role_id=saved_role)


            all_access_app_groups_from_profil = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={
                    "filter__targeted_id":rbac_profile_id,
                }
            )
            self.app_debug_print(f"\n\n\n\n\n\n all_access_app_groups_from_profil : {all_access_app_groups_from_profil}",True)
            for app_group in all_access_app_groups_from_profil:
                self.app_debug_print(f"\n\n\n\n\n\n loop app_group : {app_group}",True)
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                    filter_data={
                        "targeted_id":str(targeted_id),
                        "ref_application_group_id":str(app_group['ref_application_group_id']),
                    },
                    update_data={
                        "targeted_id":targeted_id,
                        "ref_application_group_id":app_group['ref_application_group_id'],
                    }
                )

            return True
        except Exception as e:
            format_error = format_exception("Error in add_profile_to_organization", e)
            self.app_debug_print(f"Error in add_profile_to_organization: {format_error}",True)
            return False
            # raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    async def remove_profile_from_organization(self, rbac_profile_id: str, targeted_id: str,current_org_info: dict):
        """Helper method to remove profile from organization"""
        try:
            self.app_debug_print(f"\n\n\n\n\n\n [remove_profile_from_organization] : {rbac_profile_id} | {targeted_id}",True)
            deletion = await self.generic_service.hard_delete_with_query_data_from_collection(
                collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
                query={"rbac_profile_id": ObjectId(rbac_profile_id), "targeted_id": ObjectId(targeted_id)}
            )
            self.app_debug_print(f"\n\n\n\n\n\n deletion : {deletion}",True)

            all_organization_profiles = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={
                    "filter__targeted_id":targeted_id,
                }
            )
            self.app_debug_print(f"\n\n\n\n\n\n all_organization_profiles : {all_organization_profiles}",True)


            # NO DEFAULT ROLES
            all_profil_roles = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={
                    "filter__rbac_profile_id":rbac_profile_id,
                    "filter__system_reserved_actions":True,
                    "filter__is_default":False,
                }
            )
            self.app_debug_print(f"\n\n\n\n\n\n all_profil_roles : {all_profil_roles}",True)
            for role in all_profil_roles:
                self.app_debug_print(f"\n\n\n\n\n\n loop role : {role}",True) 
                # DELETE CURRENT ROLE CHILD
                saved_role = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.RBAC_ROLE,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={
                        "filter__sys_core_role_id": str(role['id']),
                        "filter__sys_organization_id": str(targeted_id),
                        "filter__rbac_profile_id": str(rbac_profile_id),
                    }
                )
                self.app_debug_print(f"\n\n\n\n\n\n saved_role : {saved_role}",True)
                if saved_role:
                    await self.generic_service.hard_delete_with_query_data_from_collection(
                        collection_key=CollectionKey.RBAC_ROLE,
                        query={
                            "sys_core_role_id": ObjectId(str(role['id'])),
                            "sys_organization_id": ObjectId(targeted_id),
                            "rbac_profile_id": current_org_info['rbac_profile_id'],
                        }
                    )
                    self.app_debug_print(f"\n\n\n\n\n\n role to remove : {saved_role}",True)
                    await self.rbac_role_service.remove_single_rbac_role_permissions_from_parent(parent_rbac_role_id=role['id'],rbac_role_id=saved_role)

            all_access_app_groups_from_profil = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={
                    "filter__targeted_id":rbac_profile_id,
                }
            )
            self.app_debug_print(f"\n\n\n\n\n\n all_access_app_groups_from_profil : {len(all_access_app_groups_from_profil)}",True)
            
            for app_group in all_access_app_groups_from_profil:
                self.app_debug_print(f"\n\n\n\n\n\n loop app_group : {app_group}",True)
                app_group_element = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_APPLICATION_GROUP,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={
                        "filter___id": str(app_group['ref_application_group_id']),
                    }
                )
                self.app_debug_print(f"\n\n\n\n\n\n app_group_element : {app_group_element}",True)
                if not app_group_element:
                    continue
                if app_group_element['flag'] == EAppGroupFlag.COMMON.value:
                    continue

                by_pass_deletion = False
                for profil in all_organization_profiles:
                    self.app_debug_print(f"\n\n\n\n\n\n loop profil : {profil}",True)
                    app_group_for_org = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={
                            "filter__targeted_id":str(profil['id']),
                            "filter__ref_application_group_id":str(app_group['ref_application_group_id']),
                        }
                    )
                    self.app_debug_print(f"\n\n\n\n\n\n app_group_for_org : {app_group_for_org}",True)
                    if app_group_for_org:
                        by_pass_deletion = True
                        break
                
                if by_pass_deletion:
                    continue
                self.app_debug_print(f"\n\n\n\n\n\n by_pass_deletion : {by_pass_deletion}",True)
                await self.generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                    filter_data={
                        "targeted_id":str(targeted_id),
                        "ref_application_group_id":str(app_group['ref_application_group_id']),
                    },
                    update_data={
                        "targeted_id":str(targeted_id),
                        "ref_application_group_id":app_group['ref_application_group_id'],
                    }
                )

            return True
        except Exception as e:
            format_error = format_exception("Error in remove_profile_from_organization", e)
            self.app_debug_print(f"Error in remove_profile_from_organization: {format_error}",True)
            return False

    async def fetch_organization_users(
        self,
        request: Request,
        raw_query_params: dict,
    ):
        try:
            """Fetch users belonging to an organization"""
            query_params = self.convert_query_params(raw_query_params)
            item_id = raw_query_params.get('item_id', None)

            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)

            user_details = await self.get_user_info(request, self.accept_language)

            output_data_type = query_params.get("output_data_type", OutputDataType.DEFAULT.value)
            all_data = query_params.get("all_data", False)
            page = query_params.get("page", 0)
            limit = query_params.get("limit", 100000)
            sort = query_params.get("sort", {})

            # Fetch users from organization
            list_of_users = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.SYS_USER,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={"filter__sys_organization_id": item_id},
                user=user_details,
                sort=sort
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": list_of_users,
                    "max": len(list_of_users),
                    "limit": limit,
                    "page": page
                },
            )
        except Exception as e:
            format_error = format_exception("Error in fetch_organization_users", e)
            self.app_debug_print(f"Error in fetch_organization_users: {format_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    async def fetch_application_groups(
        self,
        request: Request,
        raw_query_params: dict,
    ):
        try:
            """Fetch all application groups"""
            query_params = self.convert_query_params(raw_query_params)

            user_details = await self.get_user_info(request, self.accept_language)

            output_data_type = query_params.get("output_data_type", OutputDataType.DEFAULT.value)
            all_data = query_params.get("all_data", False)
            page = query_params.get("page", 0)
            limit = query_params.get("limit", 100000)
            sort = query_params.get("sort", {})
            organization_id = raw_query_params.get('filter__organization_id', None)

            # Fetch application groups
            list_of_groups = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_APPLICATION_GROUP,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={},
                user=user_details,
                sort=sort
            )
            formated_list_of_groups = []
            for group in list_of_groups:
                cfg_related_org_app_group = []
                group_id = extract_field_on_output_data_element(group, 'id', output_data_type)
                if organization_id:
                    cfg_related_org_app_group = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                        all_data=True,
                        page=0,
                        limit=100000,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language=self.accept_language,
                        query={
                            "filter__ref_application_group_id": group_id,
                            "filter__targeted_id": organization_id
                        },
                        user=user_details,
                        sort=sort
                    )
                formated_list_of_groups.append({
                    "id": group_id,
                    "identifier": group['identifier'],
                    "name": group['name'],
                    "flag": group['flag'],
                    "icon": group['icon'],
                    "is_linked": len(cfg_related_org_app_group) > 0
                })

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": formated_list_of_groups,
                    "max": len(formated_list_of_groups),
                    "limit": limit,
                    "page": page
                },
            )
        except Exception as e:
            format_error = format_exception("Error in fetch_application_groups", e)
            self.app_debug_print(f"Error in fetch_application_groups: {format_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    async def fetch_linked_application_groups(
        self,
        request: Request,
        raw_query_params: dict,
    ):
        try:
            """Fetch all application groups"""
            query_params = self.convert_query_params(raw_query_params)

            user_details = await self.get_user_info(request, self.accept_language)

            output_data_type = query_params.get("output_data_type", OutputDataType.DEFAULT.value)
            all_data = query_params.get("all_data", False)
            page = query_params.get("page", 0)
            limit = query_params.get("limit", 100000)
            sort = query_params.get("sort", {})
            organization_id = raw_query_params.get('filter__organization_id', None)

            # Fetch application groups
            list_of_groups = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_APPLICATION_GROUP,
                all_data=all_data,
                page=page,
                limit=limit,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={},
                user=user_details,
                sort=sort
            )
            formated_list_of_groups = []
            for group in list_of_groups:
                cfg_related_org_app_group = []
                group_id = extract_field_on_output_data_element(group, 'id', output_data_type)
                if organization_id:
                    cfg_related_org_app_group = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language=self.accept_language,
                        query={
                            "filter__ref_application_group_id": group_id,
                            "filter__targeted_id": organization_id
                        },
                        user=user_details,
                        sort=sort
                    )
                    if cfg_related_org_app_group:
                        formated_list_of_groups.append({
                            "id": group_id,
                            "identifier": group['identifier'],
                            "name": group['name'],
                            "flag": group['flag'],
                            "icon": group['icon'],
                            "is_linked": len(cfg_related_org_app_group) > 0
                        })

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": formated_list_of_groups,
                    "max": len(formated_list_of_groups),
                    "limit": limit,
                    "page": page
                },
            )
        except Exception as e:
            format_error = format_exception("Error in fetch_application_groups", e)
            self.app_debug_print(f"Error in fetch_application_groups: {format_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

  
 
    async def fetch_organization_application_groups_access(
        self,
        request: Request,
        raw_query_params: dict,
    ):
        try:
            """Fetch profiles NOT yet linked to the organization"""
            query_params = self.convert_query_params(raw_query_params)
            item_id = raw_query_params.get('item_id', None)

            user_details = await self.get_user_info(request,self.accept_language)

            if not item_id:
                message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                raise HTTPException(status_code=400, detail=message)
            
            profil_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter___id": item_id},
                user=user_details,
            )
            if not profil_info:
                message = self.get_response_message(MessageCategory.COMMON, "NO_ORG_FOUND", self.accept_language)
                raise HTTPException(status_code=404, detail=message)
            

            applications_groups = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_APPLICATION_GROUP,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                accept_language=self.accept_language,
                query={"filter__is_activated": True},
                user=user_details,
            ) 
            formatted_data = []
            for app_group in applications_groups:
                accessible = False
                cfg_access = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=self.accept_language,
                    query={"filter__targeted_id": item_id, "filter__ref_application_group_id": app_group['id']},
                    user=user_details,
                )
                if cfg_access:
                    accessible = True 
                formatted_data.append({
                    **app_group,
                    "accessible":accessible
                })

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "data": formatted_data,
                    "max": len(formatted_data),
                },
            )
        except Exception as e:
            format_error = format_exception("Error in fetch_organization_application_groups_access", e)
            self.app_debug_print(f"Error in fetch_organization_application_groups_access: {format_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    

    async def patch_organization_profile_application_access(
        self,
        request: Request,
        raw_query_params: dict,
        body: dict,
    ):
        try:
                """Main PATCH method to add or remove profiles from organization"""
                item_id = flag = body.get('targeted_id', None) # raw_query_params.get('item_id', None)

                user_details = await self.get_user_info(request,self.accept_language)

                if not item_id:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_ITEM_ID_PROVIDED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                ref_application_group_id = body.get('ref_application_group_id', None)
                if not ref_application_group_id:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_APPLICATION_GROUP_ID_PROVIDED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                flag = body.get('flag', None)
                if not flag:
                    message = self.get_response_message(MessageCategory.EXCEPTIONS, "NO_FLAG_PROVIDED", self.accept_language)
                    raise HTTPException(status_code=400, detail=message)

                if flag == 'add':
                    await self.add_application_group_to_organization(ref_application_group_id=ref_application_group_id, targeted_id=item_id)
                else:
                    await self.remove_application_group_from_organization(ref_application_group_id=ref_application_group_id, targeted_id=item_id)

                message = self.get_response_message(MessageCategory.SUCCESS, "DATA_UPDATED_SUCCESSED", self.accept_language)
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"status_code": status.HTTP_200_OK, "message": message}
                )
        except Exception as e:
            format_error = format_exception("Error in patch_organization_profile_application_access", e)
            self.app_debug_print(f"Error in patch_organization_profile_application_access: {format_error}",True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
        
    async def add_application_group_to_organization(self, ref_application_group_id: str, targeted_id: str):
        """Helper method to add profile to organization"""
        data = {"ref_application_group_id": ref_application_group_id, "targeted_id": targeted_id}
        await self.generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
            filter_data=data,
            update_data=data,
        )
        return True
    
    async def remove_application_group_from_organization(self, ref_application_group_id: str, targeted_id: str):
        """Helper method to remove profile from organization"""
        deletion = await self.generic_service.hard_delete_with_query_data_from_collection(
            collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
            query={"ref_application_group_id": ObjectId(ref_application_group_id), "targeted_id": ObjectId(targeted_id)}
        )
        return True


    async def _complete_org_deletion(self,org_info):
        try:
            self.app_debug_print(f"\n\n\n\n\n\n [TOP] _complete_org_deletion org_info: {org_info['id']}",True)
            sys_organization_id = org_info['id']
            org_profil = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={"filter__sys_organization_id": org_info['rbac_profile_id']},
            )
            if not org_profil:
                return False
            # has profil parent
            # rbac_profile_id =  org_profil.get('rbac_profile_id',org_profil['id'])
            # if str(rbac_profile_id) != str(org_profil['id']):
            #     org_profil = await self.generic_service.fetch_one_from_collection(
            #         collection_key=CollectionKey.RBAC_PROFILE,
            #         output_data_type=OutputDataType.DEFAULT.value,
            #         accept_language=self.accept_language,
            #         query={"filter__sys_organization_id": org_info['id']},
            #     )
            # DELETE ALL ORGANIZATION AGENT
            agents = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION_AGENT,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={
                    "filter__sys_organization_id": sys_organization_id,
                }
            )
            for agent in agents:
                await self.generic_service.hard_delete_data_from_collection(
                    collection_key=CollectionKey.SYS_ORGANIZATION_AGENT,
                    item_id=agent['id']
                )
                self.app_debug_print(f" deleted agent : {agent['id']}",True)

            # DELETE ALL ORGANIZATION WALLETS
            wallets = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.OPS_EWALLET,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={
                    "filter__sys_organization_id": sys_organization_id,
                }
            )
            for wallet in wallets:
                await self.generic_service.hard_delete_data_from_collection(
                    collection_key=CollectionKey.OPS_EWALLET,
                    item_id=wallet['id']
                )
                self.app_debug_print(f" deleted wallet : {wallet['id']}",True)

            # delete CFG_LISOLOO_COUNTRY_COVERAGE
            country_coverages = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_LISOLOO_COUNTRY_COVERAGE,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={
                    "filter__sys_organization_id": sys_organization_id,
                }
            )
            for country_coverage in country_coverages:
                await self.generic_service.hard_delete_data_from_collection(
                    collection_key=CollectionKey.CFG_LISOLOO_COUNTRY_COVERAGE,
                    item_id=country_coverage['id']
                )

            # delete CFG_LISOLOO_ORGANIZATION_CONFIG
            org_config = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_LISOLOO_ORGANIZATION_CONFIG,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                query={
                    "filter__sys_organization_id": sys_organization_id,
                }
            )
            if org_config:
                await self.generic_service.hard_delete_data_from_collection(
                    collection_key=CollectionKey.CFG_LISOLOO_ORGANIZATION_CONFIG,
                    item_id=org_config['id']
                )
            # delete CFG_APPLICATION_KEYS
            application_keys = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_APPLICATION_KEYS,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={
                    "filter__sys_organization_id": sys_organization_id,
                }
            )
            for application_key in application_keys:
                await self.generic_service.hard_delete_data_from_collection(
                    collection_key=CollectionKey.CFG_APPLICATION_KEYS,
                    item_id=application_key['id']
                )

            # delete CFG_APPLICATION_GROUP_ACCESSIBILITY
            application_group_accessibilities = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                query={
                    "filter__targeted_id": sys_organization_id,
                }
            )
            for application_group_accessibility in application_group_accessibilities:
                await self.generic_service.hard_delete_data_from_collection(
                    collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                    item_id=application_group_accessibility['id']
                )

            # delete CFG_RELATED_SYSTEM_PROFIL
            related_system_profiles = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                all_data=True,
                query={
                    "filter__targeted_id": sys_organization_id,
                }
            )
            for related_system_profile in related_system_profiles:
                await self.generic_service.hard_delete_data_from_collection(
                    collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
                    item_id=related_system_profile['id']
                )
                

            return True
        except Exception as e:
            format_error = format_exception("Error in _complete_org_deletion", e)
            self.app_debug_print(f"Error in _complete_org_deletion: {format_error}",True)
            return False
        

    async def _complete_security_setup(self,org_profil,org_info):
        try:
            from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
            rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)
            # if is_sudo_action or is_sudo_group_action or is_sudo_delegated_action or is_sudo_cross_organization_validation_action or is_sudo_inter_connected_organization_validation_action:
            org_perm_endpoints = await rbac_role_service.get_sudo_permissions_and_endpoints(org_info['id'],org_profil['id'])
            for org in org_perm_endpoints['results']:
                # as_access_to_permission = await rbac_role_service.organization_has_permission(org['id'],permission_data['id'])
                permissions = org.get('permissions',[])
                endpoint = org.get('endpoint',None)
                if not endpoint:
                    continue
                is_sudo_action = org.get('endpoint',{}).get('is_sudo_action',False)
                is_sudo_group_action = org.get('endpoint',{}).get('is_sudo_group_action',False)
                is_available_for_rls = org.get('endpoint',{}).get('is_available_for_rls',False)
                is_sudo_delegated_action = org.get('endpoint',{}).get('is_sudo_delegated_action',False)
                is_sudo_cross_organization_validation_action = org.get('endpoint',{}).get('is_sudo_cross_organization_validation_action',False)
                is_sudo_inter_connected_organization_validation_action = org.get('endpoint',{}).get('is_sudo_inter_connected_organization_validation_action',False)
                for permission in permissions:
                    if is_sudo_action:
                        sudo_action_type = EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value
                        cfg_org_sudo_action = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                            output_data_type=OutputDataType.DEFAULT,
                            query={
                                "filter__rbac_endpoint_id": endpoint['id'],
                                "filter__rbac_permission_id": permission['id'],
                                "filter__sys_organization_id": str(org['id']),
                                "filter__sudo_action_type": sudo_action_type,
                            }
                        )
                        if not cfg_org_sudo_action:
                            cfg_org_sudo_action = await self.generic_service.add_data_to_collection(
                                collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                                data={
                                    "rbac_endpoint_id": endpoint['id'],
                                    "rbac_permission_id": permission['id'],
                                    "sys_organization_id": str(org['id']),
                                    "sudo_action_type": sudo_action_type,
                                    "is_enabled": False
                                }
                            )
                    if is_sudo_group_action:
                        sudo_action_type = EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value
                        cfg_org_sudo_action = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                            output_data_type=OutputDataType.DEFAULT,
                            query={
                                "filter__rbac_endpoint_id": endpoint['id'],
                                "filter__rbac_permission_id": permission['id'],
                                "filter__sys_organization_id": str(org['id']),
                                "filter__sudo_action_type": sudo_action_type,
                            }
                        )
                        if not cfg_org_sudo_action:
                            cfg_org_sudo_action = await self.generic_service.add_data_to_collection(
                                collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                                data={
                                    "rbac_endpoint_id": endpoint['id'],
                                    "rbac_permission_id": permission['id'],
                                    "sys_organization_id": str(org['id']),
                                    "sudo_action_type": sudo_action_type,
                                    "is_enabled": False
                                }
                            )
                    
                    if is_sudo_delegated_action:
                        sudo_action_type = EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION.value
                        cfg_org_sudo_action = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                            output_data_type=OutputDataType.DEFAULT,
                            query={
                                "filter__rbac_endpoint_id": endpoint['id'],
                                "filter__rbac_permission_id": permission['id'],
                                "filter__sys_organization_id": str(org['id']),
                                "filter__sudo_action_type": sudo_action_type,
                            }
                        )
                        if not cfg_org_sudo_action:
                            cfg_org_sudo_action = await self.generic_service.add_data_to_collection(
                                collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                                data={
                                    "rbac_endpoint_id": endpoint['id'],
                                    "rbac_permission_id": permission['id'],
                                    "sys_organization_id": str(org['id']),
                                    "sudo_action_type": sudo_action_type,
                                    "is_enabled": False
                                }
                            )
                    
                    if is_sudo_cross_organization_validation_action:
                        sudo_action_type = EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION.value
                        cfg_org_sudo_action = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                            output_data_type=OutputDataType.DEFAULT,
                            query={
                                "filter__rbac_endpoint_id": endpoint['id'],
                                "filter__rbac_permission_id": permission['id'],
                                "filter__sys_organization_id": str(org['id']),
                                "filter__sudo_action_type": sudo_action_type,
                            }
                        )
                        if not cfg_org_sudo_action:
                            cfg_org_sudo_action = await self.generic_service.add_data_to_collection(
                                collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                                data={
                                    "rbac_endpoint_id": endpoint['id'],
                                    "rbac_permission_id": permission['id'],
                                    "sys_organization_id": str(org['id']),
                                    "sudo_action_type": sudo_action_type,
                                    "is_enabled": False
                                }
                            )
                    
                    if is_sudo_inter_connected_organization_validation_action:
                        sudo_action_type = EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION.value
                        cfg_org_sudo_action = await self.generic_service.fetch_one_from_collection(
                            collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                            output_data_type=OutputDataType.DEFAULT,
                            query={
                                "filter__rbac_endpoint_id": endpoint['id'],
                                "filter__rbac_permission_id": permission['id'],
                                "filter__sys_organization_id": str(org['id']),
                                "filter__sudo_action_type": sudo_action_type,
                            }
                        )
                        if not cfg_org_sudo_action:
                            cfg_org_sudo_action = await self.generic_service.add_data_to_collection(
                                collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                                data={
                                    "rbac_endpoint_id": endpoint['id'],
                                    "rbac_permission_id": permission['id'],
                                    "sys_organization_id": str(org['id']),
                                    "sudo_action_type": sudo_action_type,
                                    "is_enabled": False
                                }
                            )

                    cfg_org_rls = await self.generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.CFG_ORGANIZATION_RLS,
                        output_data_type=OutputDataType.DEFAULT,
                        query={
                            "filter__rbac_endpoint_id": endpoint['id'],
                            "filter__rbac_permission_id": permission['id'],
                            "filter__sys_organization_id": str(org['id']),
                        }
                    )
                    if not cfg_org_rls and is_available_for_rls:
                        cfg_org_rls = await self.generic_service.add_data_to_collection(
                            collection_key=CollectionKey.CFG_ORGANIZATION_RLS,
                            data={
                                "rbac_endpoint_id": endpoint['id'],
                                "rbac_permission_id": permission['id'],
                                "sys_organization_id": str(org['id']),
                                "is_enabled": False
                            }
                        )
            cfg_rls_setup  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_RLS_SETUP,
                output_data_type=OutputDataType.DEFAULT,
                query={
                    "filter__sys_organization_id": str(org['id']),
                }
            )
            if not cfg_rls_setup:
                cfg_rls_setup = await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.CFG_RLS_SETUP,
                    data={
                        "sys_organization_id": str(org['id']),
                        "is_enabled": False
                    }
                )
            cfg_sudo_action_setup = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SUDO_ACTION_SETUP,
                output_data_type=OutputDataType.DEFAULT,
                query={
                    "filter__sys_organization_id": str(org['id']),
                }
            )
            if not cfg_sudo_action_setup:
                cfg_sudo_action_setup = await self.generic_service.add_data_to_collection(
                    collection_key=CollectionKey.CFG_SUDO_ACTION_SETUP,
                    data={
                        "sys_organization_id": str(org['id']),
                        "is_enabled": False
                    }
                )
        except Exception as e:
            format_error = format_exception("Error in _complete_security_setup", e)
            self.app_debug_print(f"Error in _complete_security_setup: {format_error}",True)
            return False


    async def _complete_org_creation(self,profil_info,org_info,ref_entity_id,user_details,new_profil_info):
        """Complete organization creation by adding default data"""
        try:
            parent_entity = await SystemCountryService(self.accept_language).get_static_parent_entity_by_flag(
                str(ref_entity_id), 'country'
            )
            self.app_debug_print(f" _complete_org_creation parent_entity: {parent_entity}",True)
            if not parent_entity:
                return False
            
            self.app_debug_print(f"[TOP] _complete_org_creation profil_info['flag']: {profil_info['flag']}",True)
            
            default_currency = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_DEFAULT_RELATED_CURRENCY,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=self.accept_language,
                user=user_details,
                query={"filter__targeted_id": ref_entity_id},
            )

            # debug
            self.app_debug_print(f" _complete_org_creation default_currency: {default_currency}",True)

            await self._complete_security_setup(org_profil=new_profil_info,org_info=org_info)
            
            return True
        except Exception as e:
            format_error = format_exception("Error in _complete_org_creation", e)
            self.app_debug_print(f"Error in _complete_org_creation: {format_error}",True)
            return False
         
