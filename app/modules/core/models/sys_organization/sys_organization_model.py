
import re
import uuid
from fastapi import HTTPException
from pydantic import Field, field_validator, model_validator
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from bson import ObjectId
from app.modules.core.schemas.user_schema import ContactPersonInfo, EmailInfo, OthersInfo, PhoneNumberInfo
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.model.model_service import ModelService
from app.modules.core.enums.type_enum import FormatedOutPut, OutputDataType
from app.modules.core.utils.model.base_document import BaseDocument
from typing import  List, Optional, Dict, Any
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey

 
 
class SysOrganizationModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DELETE_IF_NOT_USED_IN.value}":f"{CollectionKey.SYS_ORGANIZATION_AGENT.value}"
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    logo_file_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="organization logo",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={"is_logo": True}
        )
    )
    name: str = Field(
        ...,
        description="organization name",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    
    latitude: Optional[str] = Field(
        default=None,
        description="Latitude of the organization location",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    longitude: Optional[str] = Field(
        default=None,
        description="Longitude of the organization location",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    altitude: Optional[str] = Field(
        default=None,
        description="Altitude of the organization location",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    address: Optional[str] = Field(
        default='',
        description="Address",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True})
    )
    
    emails: Optional[List["EmailInfo"]] = Field(
        default_factory=list, 
        description="List of organization others emails",
        json_schema_extra=translation_meta(
            may_have_translation=False,  
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ARRAY_OF_OBJECT.value}": True}
        )
    )  
    phone_numbers: Optional[List["PhoneNumberInfo"]] = Field(
        default_factory=list, 
        description="List of organization others phone numbers",
        json_schema_extra=translation_meta(
            may_have_translation=False,  
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ARRAY_OF_OBJECT.value}": True}
        )
    )  
    others: Optional[List["OthersInfo"]] = Field(
        default_factory=list, 
        description="List of dynamic organization others informations others",
        json_schema_extra=translation_meta(
            may_have_translation=False,  
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ARRAY_OF_OBJECT.value}": True}
        )
    ) 
    contact_person: Optional["ContactPersonInfo"] = Field(
        default_factory=dict, 
        description="Contact person of the organization",
        json_schema_extra=translation_meta(
            may_have_translation=False,  
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ARRAY_OF_OBJECT.value}": True}
        )
    ) 

    sys_organization_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Parent organization ID",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    cfg_system_country_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Country ID",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    rbac_profile_id: PydanticObjectId = Field(
        ...,
        description="System profile ID associated with the organization",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    ref_entity_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Reference entity ID associated with the organization",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    ) 

    parent_reseller_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Parent reseller organization",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.SYS_ORGANIZATION.value}",
            }
        )
    )

    flag: Optional[str] = Field(
        default=None,
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        )
    ) 
    
    # Field Validator
    @field_validator("name")
    def validate_and_lowercase_name(cls, value: str) -> str:
        return value.lower()
    
    
    @model_validator(mode='before')
    def generate_flag_if_not_provided(cls, values):
        """
        Custom validator to generate the 'flag' field if not provided.
        """
        if "flag" not in values or not values["flag"]:
            name = values.get("name")
            if name:
                sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
                values["flag"] = f"{sanitized_name}_{len(name)}"
        return values
    
    def get_org_status_translated(self,accept_language:str = 'fr') -> str:
        is_activated = 'Désactivé' if accept_language == 'fr' else 'Deactive'
        if self.is_activated:
            is_activated = 'Activé' if accept_language == 'fr' else 'Active'
        return is_activated
    
    async def get_formated_data(self,accept_language:str = 'fr',output:FormatedOutPut = FormatedOutPut.MINIMAL) -> dict:
        from app.modules.core.configs.config import settings
        try:
            from app.modules.core.models.sys_user.sys_user_model import SysUserModel
            from app.modules.core.services.generic.generic_services import GenericService
            from app.modules.core.models.ref_entity.ref_entity_model import RefEntityModel
            from app.modules.core.enums.type_enum import EGlobalFormatingFlag
            generic_service = GenericService(accept_language)
            from app.modules.core.models.mapping_keys import CollectionKey
            DebugService.app_debug_print(f"\n step  >< : 1 \n\n", False)
            entity_instance = await RefEntityModel.find_one({"_id": self.ref_entity_id})
            entity_output = EGlobalFormatingFlag.FULL_FORMATING_DATA if output == FormatedOutPut.FULL else EGlobalFormatingFlag.RESUME_FORMATING_DATA
            entity =  await entity_instance.get_default_formated_data(accept_language,entity_output)
            # entity = await generic_service.fetch_one_from_collection(
            #     collection_key=CollectionKey.REF_ENTITY,
            #     output_data_type=OutputDataType.DEFAULT.value,
            #     query={"filter___id":str(self.ref_entity_id).strip()}, 
            # )
            DebugService.app_debug_print(f"\n step entity  > : {entity} : output :{output} \n\n", False)
            if entity and output == FormatedOutPut.FULL:
                named_entity = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_NAMED_ENTITY,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter___id":str(entity['ref_named_entity_id']).strip()}, 
                )
            DebugService.app_debug_print(f"\n step  > : 2 \n\n", False)
            profil = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id":str(self.rbac_profile_id).strip()}, 
            )
            DebugService.app_debug_print(f"\n step  >< {profil}: 2.5 \n\n", False)
            contact_person = self.contact_person
            DebugService.app_debug_print(f"\n step  > : 3 \n\n", False)
            default_role  = await generic_service.fetch_native_query_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                accept_language=accept_language,
                native_query={
                    "rbac_profile_id":self.rbac_profile_id,
                    "is_default":True
                }
            )
            DebugService.app_debug_print(f"\n step  >> : 4 default_role :{default_role} \n\n", False)
            admin_user_info = {}
            if default_role:
                DebugService.app_debug_print(f"\n step  >> : 5 \n\n", False)
                admin_user = await generic_service.fetch_native_query_data_from_collection(
                    collection_key=CollectionKey.SYS_USER,
                    all_data=True,
                    accept_language=accept_language,
                    native_query={
                        "rbac_role_id":ObjectId(str(default_role['id'])),
                    }
                )
                DebugService.app_debug_print(f"\n step  > : 6>> {admin_user} \n\n", False)
                if isinstance(admin_user,list) and len(admin_user) > 0:
                    DebugService.app_debug_print(f"\n step  >> : 7 \n\n", False)
                    user_instance = SysUserModel(**admin_user[0]) #ModelService.convert_to_model_instance(SysUserModel,admin_user[0])
                    DebugService.app_debug_print(f"\n step  > : 8 \n\n", False)
                    admin_user_info = await  user_instance.get_formated_data(accept_language,output)
                    DebugService.app_debug_print(f"\n step  > : 9 \n\n", False)

            # DebugService.app_debug_print(f"\n self.logo  > {self.logo}: 9 \n\n", True)
            org_logo = "empty"
            if self.logo_file_id:
                DebugService.app_debug_print(f"\n step  > : 10 \n\n", False)
                arc_file = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.ARCH_FILE,
                    output_data_type=OutputDataType.DEFAULT.value,
                    accept_language=accept_language,
                    query={
                        "filter___id":str(self.logo_file_id),
                    }
                )
                if arc_file:
                    org_logo =  f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/static/files/view-file?file_id={arc_file['file_str_id_composed']}"
            DebugService.app_debug_print(f"\n\n\n\n\n ALL COMPANY INFO  > : {self} \n\n\n\n\n", False)

            if output == FormatedOutPut.MINIMAL:
                org_info = {
                    "logo": org_logo,
                    "id":str(self.id),
                    "identifier":self.identifier,
                    "name":self.name,
                    "created_at":self.created_at,
                    "emails": EmailInfo.to_dict_list(self.emails),
                    "phone_numbers": PhoneNumberInfo.to_dict_list(self.phone_numbers),
                    "is_activated":self.is_activated,
                    "rbac_profile_id":str(self.rbac_profile_id),
                    "ref_entity_id":str(self.ref_entity_id),
                    "address":self.address,
                    "entity":entity,
                } 
                return org_info
            
            org_info = {
                "logo": org_logo,
                "id":str(self.id),
                "is_activated":self.is_activated,
                "identifier":self.identifier,
                "name":self.name,
                "latitude":self.latitude,
                "longitude":self.longitude,
                "altitude":self.altitude,
                "is_activated":self.is_activated,
                "is_activated_lbl":self.get_org_status_translated(accept_language),
                
                "sys_organization_id":self.sys_organization_id,
                "cfg_system_country_id":self.cfg_system_country_id,
                "rbac_profile_id":str(self.rbac_profile_id),
                "ref_entity_id":str(self.ref_entity_id),
                
                "emails": EmailInfo.to_dict_list(self.emails),
                "phone_numbers": PhoneNumberInfo.to_dict_list(self.phone_numbers),
                "others":self.others,
                "address":self.address,
                "created_at":self.created_at,
                "profil":profil,
                "named_entity":named_entity,
                "entity":entity,
                
                "contact_person":contact_person,
                "admin_user":admin_user_info,
            } 
            DebugService.app_debug_print(f"\n return las  >< : {org_info} \n\n", False)
            return org_info
        except ValueError as e:
            DebugService.app_debug_print(f"\n error formating organization  >< : {e} \n\n", True)
            org_info = {
                "id":str(self.id),
                "is_activated":self.is_activated,
                "identifier":self.identifier,
                "name":self.name,
                "latitude":self.latitude,
                "longitude":self.longitude,
                "altitude":self.altitude,
                "is_activated":self.is_activated,
                "is_activated_lbl":self.get_org_status_translated(accept_language),
                
                "sys_organization_id":self.sys_organization_id,
                "cfg_system_country_id":self.cfg_system_country_id,
                "rbac_profile_id":str(self.rbac_profile_id),
                "ref_entity_id":str(self.ref_entity_id),
                
                "emails": EmailInfo.to_dict_list(self.emails),
                "phone_numbers": PhoneNumberInfo.to_dict_list(self.phone_numbers),
                "others":self.others,
                "address":self.address,
                "created_at":self.created_at, 
            } 
            return org_info
        except PermissionError as e:
            DebugService.app_debug_print(f"\n error formating organization  >< : {e} \n\n", True)
            org_info = {
                "id":str(self.id),
                "is_activated":self.is_activated,
                "identifier":self.identifier,
                "name":self.name,
                "latitude":self.latitude,
                "longitude":self.longitude,
                "altitude":self.altitude,
                "is_activated":self.is_activated,
                "is_activated_lbl":self.get_org_status_translated(accept_language),
                "rbac_profile_id":str(self.rbac_profile_id),
                "ref_entity_id":str(self.ref_entity_id),
                
                "sys_organization_id":self.sys_organization_id,
                "cfg_system_country_id":self.cfg_system_country_id,
                "rbac_profile_id":self.rbac_profile_id,
                "ref_entity_id":self.ref_entity_id,
                
                "emails": EmailInfo.to_dict_list(self.emails),
                "phone_numbers": PhoneNumberInfo.to_dict_list(self.phone_numbers),
                "others":self.others,
                "address":self.address,
                "created_at":self.created_at, 
            } 
            DebugService.app_debug_print(f"\n return las  >< : {org_info} \n\n", False)
            return org_info

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "logo_file_id": "Logo",
            "name": "Nom",
            "latitude": "Latitude",
            "longitude": "Longitude",
            "altitude": "Altitude",
            "address": "Adresse",
            "emails": "Emails",
            "phone_numbers": "Numéros de téléphone",
            "others": "Autres informations",
            "contact_person": "Personne de contact",
            "sys_organization_id": "Organisation parente",
            "cfg_system_country_id": "Pays",
            "rbac_profile_id": "Profil système",
            "ref_entity_id": "Entité de référence",
            "parent_reseller_id": "Revendeur parent",
        },
        en={
            "logo_file_id": "Logo",
            "name": "Name",
            "latitude": "Latitude",
            "longitude": "Longitude",
            "altitude": "Altitude",
            "address": "Address",
            "emails": "Emails",
            "phone_numbers": "Phone Numbers",
            "others": "Other Information",
            "contact_person": "Contact Person",
            "sys_organization_id": "Parent Organization",
            "cfg_system_country_id": "Country",
            "rbac_profile_id": "System Profile",
            "ref_entity_id": "Reference Entity",
            "parent_reseller_id": "Parent Reseller",
        },
        ln={
            "logo_file_id": "Logo",
            "name": "Nkombo",
            "latitude": "Latitude",
            "longitude": "Longitude",
            "altitude": "Altitude",
            "address": "Adresse",
            "emails": "Ba emails",
            "phone_numbers": "Ba nimero ya telefone",
            "others": "Makambo mosusu",
            "contact_person": "Moto ya kobenga",
            "sys_organization_id": "Organisation ya likolo",
            "cfg_system_country_id": "Ekolo",
            "rbac_profile_id": "Profil ya système",
            "ref_entity_id": "Entité ya référence",
            "parent_reseller_id": "Moteki ya likolo",
        },
    )

    class Settings:
        name = f"{CollectionKey.SYS_ORGANIZATION.model_name}"
        validate_on_save = True
 
