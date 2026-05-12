
from datetime import datetime
import uuid
from pydantic import Field,field_validator
from typing import Optional
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.schemas.organization import format_date_of_birth_datetime
from app.modules.core.enums.type_enum import EGender
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE_CONSTRAINTS
from app.modules.core.enums.type_enum import EGLOBAL_EXTRA_METAS
 
class SysPersonModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING}": True}
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the person",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING}": True}
        )
    )
    # cfg_photo_id: Optional[PydanticObjectId] = Field(
    #     default=None,
    #     description="Photo URL for profile picture",
    #     json_schema_extra=translation_meta(
    #         may_have_translation=False, 
    #         to_be_translated_in_front=False, 
    #         data_type={"is_profile_file": True}
    #     )
    # )

    # Personal Information
    first_name: str = Field(
        ...,
        description="First name of the person",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}":True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}":3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}":255,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
            }
        )
    )

    last_name: str = Field(
        ...,
        description="Last name of the person",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}":True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}":3,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}":255,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
            }
        )
    )

    sur_name: Optional[str] = Field(
        default=None,
        description="Middle or surname of the person",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
            }
        )
    )

    gender: EGender = Field(
        default=EGender.MALE,
        description="Gender of the person",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":f"{EGender.__name__}", 
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
            }
        )
    )

    birth_date: Optional[datetime] = Field(
        default=None,
        description="date",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED}":True,
                "only_future_date":False,
                "only_past_date":False,
                "only_future_date_and_today":False,
                "only_past_date_and_today":False,
                "only_today_date":False,
                "only_minor_age":False,
                "only_major_age":True,
            }
        )
    )

    birth_city: Optional[str] = Field(
        default=None,
        description="City of birth",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True},
             extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
            }
        )
    )

    ref_birth_country_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Country of birth",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_COUNTRY.value}",
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
                # f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}":True
            }
            
        )
    )

    ref_nationality_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Nationality of the person",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_COUNTRY.value}",
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
                # f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}":True
            }
        )
    )

    ref_marital_status_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Marital status of the person",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_MARITAL_STATUS.value}",
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
                # f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}":True
            }
        )
    )

    number_of_children: Optional[int] = Field(
        default=0,
        description="Number of children",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_INT.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
            }
        )
    )

    ref_religion_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Religion of the person",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_RELIGION.value}",
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
                # f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}":True
            }, 
        )
    )

    # Address Information
    address_line1: Optional[str] = Field(
        default=None,
        description="Address line 1",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
            }, 
        )
    )

    address_line2: Optional[str] = Field(
        default=None,
        description="Address line 2",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
            }, 
        )
    ) 
    
    sys_organization_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="System organization ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True
            },
            overview_data_type={
                f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True,
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.SYS_ORGANIZATION.value}",
            }
        )
    )

    postal_code: Optional[str] = Field(
        default=None,
        description="Postal code",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=True,
            to_be_translated_in_front=False, 
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE}": True}
        )
    )

    home_town: Optional[str] = Field(
        default=None,
        description="City of residence",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    ref_home_country_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Country of residence",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_COUNTRY.value}",
                # f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}":True
            }
        )
    )

    # Contact Information
    phone_number: Optional[str] = Field(
        default=None,
        description="Phone number in international format",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True}
        )
    )

    # email: Optional[EmailStr] = Field(
    email: Optional[str] = Field(
        default=None,
        description="Email address",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True}
        )
    )

    # Identification
    national_id_number: Optional[str] = Field(
        default=None,
        description="National ID number",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True}
        )
    )

    passport_number: Optional[str] = Field(
        default=None,
        description="Passport number",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True}
        )
    )

    driving_license_number: Optional[str] = Field(
        default=None,
        description="Driving license number",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True}
        )
    )

    # Employment Information
    # occupation: Optional[str] = Field(
    #     default=None,
    #     description="Occupation or job title",
    #     json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    # )

    # employer_name: Optional[str] = Field(
    #     default=None,
    #     description="Employer name",
    #     json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    # )

    # employment_status: Optional[str] = Field(
    #     default=None,
    #     description="Employment status (e.g., employed, self-employed, unemployed)",
    #     json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    # )

    # Biometric Information
    ref_eye_color_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Reference ID for eye color",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_EYE_COLOR.value}",
            }
        )
    )

    ref_blood_type_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Blood type of the person",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True,f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}":True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.REF_BLOOD_TYPE.value}",
            }
        )
    )

    height_in_cm: Optional[float] = Field(
        default=None,
        description="Height in centimeters",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={"is_float": True}
        )
    )

    weight_in_kg: Optional[float] = Field(
        default=None,
        description="Weight in kilograms",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={"is_float": True}
        )
    )

    # Digital Identity
    # ip_address: Optional[IPvAnyAddress] = Field(
    #     default=None,
    #     description="IP address of the person for registration purposes",
    #     json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    # )

    

    # Relationships
    # spouse_id: Optional[PydanticObjectId] = Field(
    #     default=None,
    #     description="Reference ID of the spouse",
    #     json_schema_extra=translation_meta(
    #         may_have_translation=False, 
    #         to_be_translated_in_front=False, 
    #         data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
    #     )
    # )

    # dependents_ids: Optional[List[PydanticObjectId]] = Field(
    #     default_factory=list,
    #     description="List of reference IDs for dependents",
    #     json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={"is_array": True})
    # ) 
    # Field Validators
    @field_validator("first_name")
    def validate_and_lowercase_first_name(cls, value: str) -> str:
        return value.lower()

    @field_validator("last_name")
    def validate_and_lowercase_last_name(cls, value: str) -> str:
        return value.lower()
    
    @field_validator('birth_date', mode='before')
    def validate_birth_date(cls, v):
        """
        If a datetime string is provided for birth_date,
        convert it to a date (with zero time).
        """
        if v is None:
            return v
        # if isinstance(v, str):
        try:
            v =  format_date_of_birth_datetime(str(v))
            print(f'\n\n\n date : {v}\n\n\n')
        except Exception as e:
            raise ValueError(f"Invalid date format: {v} error : {e}") from e
        return v
     

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "first_name": "Prénom",
            "last_name": "Nom de famille",
            "sur_name": "Post-nom",
            "gender": "Genre",
            "birth_date": "Date de naissance",
            "birth_city": "Ville de naissance",
            "ref_birth_country_id": "Pays de naissance",
            "ref_nationality_id": "Nationalité",
            "ref_marital_status_id": "État civil",
            "number_of_children": "Nombre d'enfants",
            "ref_religion_id": "Religion",
            "address_line1": "Adresse ligne 1",
            "address_line2": "Adresse ligne 2",
            "sys_organization_id": "Organisation",
            "postal_code": "Code postal",
            "home_town": "Ville de résidence",
            "ref_home_country_id": "Pays de résidence",
            "phone_number": "Numéro de téléphone",
            "email": "Email",
            "national_id_number": "Numéro de carte d'identité",
            "passport_number": "Numéro de passeport",
            "driving_license_number": "Numéro de permis de conduire",
            "ref_eye_color_id": "Couleur des yeux",
            "ref_blood_type_id": "Groupe sanguin",
            "height_in_cm": "Taille (cm)",
            "weight_in_kg": "Poids (kg)",
        },
        en={
            "first_name": "First Name",
            "last_name": "Last Name",
            "sur_name": "Surname",
            "gender": "Gender",
            "birth_date": "Date of Birth",
            "birth_city": "City of Birth",
            "ref_birth_country_id": "Country of Birth",
            "ref_nationality_id": "Nationality",
            "ref_marital_status_id": "Marital Status",
            "number_of_children": "Number of Children",
            "ref_religion_id": "Religion",
            "address_line1": "Address Line 1",
            "address_line2": "Address Line 2",
            "sys_organization_id": "Organization",
            "postal_code": "Postal Code",
            "home_town": "City of Residence",
            "ref_home_country_id": "Country of Residence",
            "phone_number": "Phone Number",
            "email": "Email",
            "national_id_number": "National ID Number",
            "passport_number": "Passport Number",
            "driving_license_number": "Driving License Number",
            "ref_eye_color_id": "Eye Color",
            "ref_blood_type_id": "Blood Type",
            "height_in_cm": "Height (cm)",
            "weight_in_kg": "Weight (kg)",
        },
        ln={
            "first_name": "Nkombo ya liboso",
            "last_name": "Nkombo ya libota",
            "sur_name": "Nkombo ya nsima",
            "gender": "Mwasi to Mobali",
            "birth_date": "Mokolo ya mbotama",
            "birth_city": "Engumba ya mbotama",
            "ref_birth_country_id": "Ekolo ya mbotama",
            "ref_nationality_id": "Nationalité",
            "ref_marital_status_id": "Lolenge ya libala",
            "number_of_children": "Motango ya bana",
            "ref_religion_id": "Lingomba",
            "address_line1": "Adresse molongo 1",
            "address_line2": "Adresse molongo 2",
            "sys_organization_id": "Organisation",
            "postal_code": "Code postal",
            "home_town": "Engumba ya kofanda",
            "ref_home_country_id": "Ekolo ya kofanda",
            "phone_number": "Nimero ya telefone",
            "email": "Email",
            "national_id_number": "Nimero ya karti ya moto",
            "passport_number": "Nimero ya passeport",
            "driving_license_number": "Nimero ya permis ya kotambwisa",
            "ref_eye_color_id": "Langi ya miso",
            "ref_blood_type_id": "Groupe ya makila",
            "height_in_cm": "Molayi (cm)",
            "weight_in_kg": "Kilo (kg)",
        },
    )

    class Settings:
        name = f"{CollectionKey.SYS_PERSON.model_name}"
        validate_on_save = True
 
