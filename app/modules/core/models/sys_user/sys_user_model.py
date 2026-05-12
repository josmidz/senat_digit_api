
import re
from beanie import Indexed, PydanticObjectId, after_event
from beanie.odm.actions import Replace, SaveChanges, Update
from pydantic import Field, field_validator,model_validator
from typing import Annotated, List,Optional
from datetime import datetime, timedelta, timezone
import uuid
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.schemas.user_schema import EmailInfo, OthersInfo, PhoneNumberInfo
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, AccountStatusFlag, EGender, ELoginResetPasswordFailStatus, ERegistrationOrigin, FormatedOutPut, OutputDataType
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.auth.services.password.password_service import PasswordService
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.timestamp_mixin import TimestampMixin
from app.modules.core.utils.model.status_color_helper import StatusColorHelper

class SysUserModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                # "upsert_if_exist_with_props":"sys_user_id,ops_expense_account_id",
                f"{EGLOBAL_EXTRA_METAS.EXCLUDED_FIELDS.value}":"id",
            }
        )
    ) 
    first_name: str = Field(
        ...,
        description="First Name",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
    last_name: str = Field(
        ...,
        description="First Name",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    sur_name: Optional[str] = Field(
        default='',
        description="First Name",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    
    email: Optional[str] = Field(
        None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_EMAIL.value}": True},
            extra_metas={
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}":True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}":8,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}":100,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}":True,
            }
        )
    ) 
    
    
    phone_number: Optional[str] = Field(
        None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_PHONE_NUMBER.value}": True},
            extra_metas={
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}":True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}":8,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}":100,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}":True,
            }
        )
    ) 

    face_image_path_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Face image path ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    id_card_image_path_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID card image path ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
    
    address: Optional[str] = Field(
        default='',
        description="Address",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True,f'{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}':True}
        )
    )
    
    emails: Optional[List["EmailInfo"]] = Field(
        default=[], 
        description="List of user others emails",
        json_schema_extra=translation_meta(
            may_have_translation=False,  
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ARRAY_OF_OBJECT.value}": True}
        )
    )  
    phone_numbers: Optional[List["PhoneNumberInfo"]] = Field(
        default=[], 
        description="List of user others phone numbers",
        json_schema_extra=translation_meta(
            may_have_translation=False,  
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ARRAY_OF_OBJECT.value}": True}
        )
    )
    
    account_status:  Optional[AccountStatusFlag] = Field(
        default=AccountStatusFlag.INACTIVE,
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            exclude_from_overview=True,
            to_be_translated_in_front=False,
            data_type={ f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True}
        )
    )
    
    username: Annotated[
        str,
        Indexed(unique=True, name="usr_unique_index"),  # Indexed for database uniqueness
        Field(  # JSON schema metadata
            json_schema_extra=translation_meta(
                may_have_translation=False,
                to_be_translated_in_front=False,
                data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
                extra_metas={
                    f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}":True,
                    f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}":4,
                    f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}":100,
                    f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}":True,
                    f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}":True,
                    f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}":True,
                }
            )
        )
    ]
    password: Optional[str] = Field(
        default=None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_update_head=True,
            exclude_from_overview=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_PASSWORD.value}": True},
            extra_metas={
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_REQUIRED.value}":True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MIN_LENGTH.value}":4,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.MAX_LENGTH.value}":100,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_INPUT_SELECT.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_TREE.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_VALUE_ON_CASCADE.value}":True,
            }
        )
    ) 
    
    user_account_hash: Optional[str] = Field(
        default=None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            exclude_from_overview=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
             
        )
    ) 
    
    user_account_socket_hash: Optional[str] = Field(
        default=None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            exclude_from_overview=True,
            data_type={ f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
             
        )
    ) 
    
    gender: EGender = Field(
        default=EGender.MALE,
        description="Gender of the person",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={ f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":"EGender", 
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}":StatusColorHelper.generate_status_colors(
                    EGender,
                    StatusColorHelper.create_mapping(
                        green=[EGender.FEMALE.value,],
                        orange=[EGender.MALE.value],
                        blue=[EGender.OTHER.value],
                    )
                ),
            }
        )
    )

    birth_day: Optional[datetime] = Field(
        default=None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
    
    birth_city: Optional[str] = Field(
        default="",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    ref_entity_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Reference entity ID associated with the user",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
    ref_country_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Reference entity ID associated with the user",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )
     
   
    
    sys_organization_id: Annotated[
        Optional[PydanticObjectId],
        Field(
            default=None,
            description="System organization ID",
            json_schema_extra=translation_meta(
                may_have_translation=False,
                exclude_from_head=True,
                exclude_from_update_head=True,
                to_be_translated_in_front=False,
                data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True},
                overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True} 
            )
        )
    ]
    
    rbac_role_id: PydanticObjectId = Field(
        description="Role ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True,
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.RBAC_ROLE.value}",
                f"{EGLOBAL_EXTRA_METAS.JOIN_PROFIL_OR_ORGANIZATION_QUERY.value}":True,
            }
        )
    )
    sys_person_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Role ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            overview_data_type={
                f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True,
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.SYS_PERSON.value}"
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.SYS_PERSON.value}",
            }
        )
    )
    
    
    login_fail_attempt_count: int = Field(
        default=0,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            exclude_from_overview=True,
            data_type={ f"{EGLOBAL_DATA_TYPE.IS_NUMBER.value}": True}
        )
    ) 
    
    login_locked_until: Annotated[
        Optional[datetime],
        Field(
            default=None,
            description="LOcked data",
            json_schema_extra=translation_meta(
                may_have_translation=False,
                to_be_translated_in_front=False,
                exclude_from_head=True,
                exclude_from_update_head=True,
                exclude_from_overview=True,
                data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True}
            )
        )
    ]
    
    login_fail_status:  ELoginResetPasswordFailStatus = Field(
        default=ELoginResetPasswordFailStatus.NORMAL,
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            exclude_from_overview=True,
            data_type={ f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True}
        )
    )
    
    
    reset_password_fail_attempt_count: int = Field(
        default=0,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            exclude_from_overview=True,
            data_type={ f"{EGLOBAL_DATA_TYPE.IS_NUMBER.value}": True}
        )
    )
    
    reset_password_locked_until: Annotated[
        Optional[datetime],
        Field(
            default=None,
            description="Password reset Locked date",
            json_schema_extra=translation_meta(
                may_have_translation=False,
                to_be_translated_in_front=False,
                exclude_from_head=True,
                exclude_from_update_head=True,
                exclude_from_overview=True,
                data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True}
            )
        )
    ]
    reset_password_fail_status:  ELoginResetPasswordFailStatus = Field(
        default=ELoginResetPasswordFailStatus.NORMAL,
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            exclude_from_overview=True,
            data_type={ f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True}
        )
    )

    is_default: Optional[bool] = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_data_table=True,
            exclude_from_head=True,
            exclude_from_update_head=True,
            exclude_from_overview=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    should_update_password: Optional[bool] = Field(
        default=False,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            exclude_from_overview=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
    
    registration_origin: ERegistrationOrigin = Field(
        default=ERegistrationOrigin.REGISTRATION,
        json_schema_extra=translation_meta(
            may_have_translation=False, 
             exclude_from_head=True,
            to_be_translated_in_front=False, 
            data_type={ f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True}
        )
    )

    cfg_organism_chart_id:Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the associated organism chart",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
             extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.CFG_ORGANISM_CHART.value}",
                f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}":True
            }
        )
    )

    rbac_profile_id:Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of user system profil",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            exclude_from_update_head=True,
            exclude_from_overview=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
             extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.RBAC_PROFILE.value}",
            }
        )
    )
   
    
    others: Optional[List["OthersInfo"]] = Field(
        default=[], 
        description="List of dynamic user others informations others",
        json_schema_extra=translation_meta(
            may_have_translation=False,  
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ARRAY_OF_OBJECT.value}": True}
        )
    )

    @field_validator("username")
    def validate_and_lowercase_username(cls, value: str) -> str:
        return value.lower()

    # @field_validator('phone_number',mode='before')
    # def validate_phone_numbers(cls, v):
    #     phone_regex = r"^\+?[1-9]\d{1,14}$"  # E.164 standard
    #     if v:
    #         if not re.match(phone_regex, v):
    #             raise ValueError(f"Invalid phone number: {v}")
    #     return v
    
    # @model_validator(mode="before")
    # def generate_flag(cls, values):
    #     """
    #     Generate the 'flag' field if not provided.
    #     """
    #     values['user_account_socket_hash'] = values
    #     if "flag" not in values or not values["flag"]:
    #         name = values.get("name", "")
    #         sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
    #         values["flag"] = f"{sanitized_name}_{uuid.uuid4().hex[:8]}"
    #     return values   
    @model_validator(mode="before")
    def generate_flag(cls, values):
        """
        Check if birth_day is not a valid date and set it to None.
        """
        birth_day = values.get("birth_day")
        if birth_day is not None:
            if isinstance(birth_day, datetime):
                pass  # already a valid datetime
            elif isinstance(birth_day, str):
                try:
                    datetime.fromisoformat(birth_day)
                except (ValueError, TypeError):
                    values["birth_day"] = None
            else:
                values["birth_day"] = None
        return values

    @after_event(Replace, SaveChanges, Update)
    async def _invalidate_user_app_store_cache(self) -> None:
        """Defensive cache invalidation hook.

        Fires on any save against a SysUser document — covers ``.save()``
        (Replace), ``.save_changes()`` (SaveChanges), and ``.update()``
        (Update). When ANY future endpoint (or admin tool) mutates this
        user's RBAC fields (``rbac_role_id``, ``rbac_profile_id``,
        ``sys_organization_id``, …), the L1 (Redis) and L2 (user_app_store)
        caches for this user are flushed so the next request rebuilds
        against the fresh state.

        This intentionally fires unconditionally rather than tracking
        previous-vs-new field values:
          * The cost is tiny — one Mongo update_many that matches at most
            a handful of cache rows for a single user.
          * It guarantees correctness even when the mutation goes through
            a future code path we haven't predicted.
          * The seed path is suppressed automatically — every mark_*_stale
            call checks ``is_user_app_store_guard_active()`` and no-ops
            during a seed run.

        All errors are swallowed: a failed cache invalidation must never
        break a user save. Lazy imports prevent circular boot issues
        (``user_app_store_service`` itself imports SysUser indirectly).
        """
        if self.id is None:
            return
        try:
            from app.modules.core.services.user_app_store.user_app_store_service import (
                UserAppStoreService,
            )
            from app.modules.core.services.redis.redis_service import (
                AppRedisService,
            )

            user_id = str(self.id)
            await UserAppStoreService.mark_user_stale(user_id)
            try:
                await AppRedisService.delete_keys_by_pattern(
                    f"static_cache:{user_id}:*", use_env_prefix=True,
                )
            except Exception as l1_err:  # noqa: BLE001
                DebugService.app_debug_print(
                    f"SysUser save hook: L1 sweep failed for {user_id}: {l1_err}",
                    True,
                )
        except Exception as exc:  # noqa: BLE001
            # Hook failures must NEVER block a user save. Logged for ops.
            DebugService.app_debug_print(
                f"SysUser._invalidate_user_app_store_cache failed: {exc}", True,
            )

    def set_password(self, password: str) -> None:
        self.password = PasswordService.hash_password(password)

    def verify_password(self, password: str) -> bool:
        return PasswordService.verify_password(password, self.password)
    
    def get_gender_translated(self,accept_language:str = 'fr') -> str:
        gender = 'Masculin' if accept_language == 'fr' else 'Male'
        if self.gender == 'f':
            gender = 'Feminin' if accept_language == 'fr' else 'Female'
        return gender
    
    def handle_account_status(self,accept_language:str = 'fr') -> str:
        status = self.account_status
        if status == AccountStatusFlag.ACTIVE:
            DebugService.app_debug_print("Account is active")
            return 'Actif' if accept_language == 'fr' else 'Active'
        elif status == AccountStatusFlag.INACTIVE:
            DebugService.app_debug_print("Account is inactive")
            return 'Inactif' if accept_language == 'fr' else 'Inactive'
        elif status == AccountStatusFlag.LOCKED:
            DebugService.app_debug_print("Account is locked")
            return 'Bloqué' if accept_language == 'fr' else 'Locked'
        elif status == AccountStatusFlag.SUSPENDED:
            DebugService.app_debug_print("Account is suspended")
            return 'Suspendu' if accept_language == 'fr' else 'Suspended'
        elif status == AccountStatusFlag.REVOQUED:
            DebugService.app_debug_print("Account is revoqued")
            return 'Revoqué' if accept_language == 'fr' else 'Revoqued'
        elif status == AccountStatusFlag.LOCKED_BY_SYSTEM:
            DebugService.app_debug_print("Account is locked by system")
            return 'Bloqué par le système' if accept_language == 'fr' else 'Locked by system'
        else:
            DebugService.app_debug_print("Unknown account status")
            return 'Statut inconnu' if accept_language == 'fr' else 'Unknown account status'
    
    
    def get_account_status_translated(self,accept_language:str = 'fr') -> str:
        return self.handle_account_status(accept_language)
    
    def increment_login_fail(self) -> None:
        self.login_fail_attempt_count += 1
        if self.login_fail_attempt_count >= 5:
            self.login_fail_status = ELoginResetPasswordFailStatus.LOCKED
            self.login_locked_until = datetime.now(timezone.utc) + timedelta(days=3)
    
    async def get_formated_data(self,accept_language:str = 'fr',output:FormatedOutPut = FormatedOutPut.MINIMAL) -> dict:
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(accept_language)
        from app.modules.core.models.mapping_keys import CollectionKey
        from app.modules.core.enums.type_enum import OutputDataType
        from app.modules.core.services.device.device_service import DeviceService
        device_service = DeviceService(accept_language)
        try:
            # default_role  = await fetch_native_query_one_from_collection(
            #     collection_key=CollectionKey.RBAC_ROLE,
            #     accept_language=accept_language,
            #     native_query={
            #         "_id":self.rbac_role_id,
            #         "is_default":True
            #     }
            # )
            default_role = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id":str(self.rbac_role_id).strip()}, 
            )
            is_admin_account = True if default_role.get('is_default',False) else False
            profil_info = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id":str(self.rbac_profile_id).strip()}, 
            )

            user_config_info = await device_service.create_or_get_user_config(
                sys_user_id=self.id,
                accept_language=accept_language
            );
        

            if output == FormatedOutPut.MINIMAL:
                user_info = {
                    "id":str(self.id),
                    "first_name":self.first_name,
                    "last_name":self.last_name,
                    "username":self.username,
                    "email":self.email,
                    "phone_number":self.phone_number,
                    "is_activated":self.is_activated,
                } 
                return user_info
            
            user_info = {
                "photo":'empty',
                "signature":'-',
                "id":str(self.id),
                "first_name":self.first_name,
                "username":self.username,
                "last_name":self.last_name,
                "sur_name":self.sur_name,
                "gender":self.get_gender_translated(accept_language),
                "phone_number":self.phone_number,
                "address":self.address,
                "email":self.email,
                "emails":self.emails,
                "phone_numbers":self.phone_numbers,
                "account_status":self.account_status,
                "others":self.others,
                "account_status_lbl":self.handle_account_status(accept_language),
                "is_admin_account":is_admin_account,
                "role":default_role,
                "rbac_role_id":str(self.rbac_role_id),
                "rbac_profile_id":self.rbac_profile_id,
                "sys_organization_id":self.sys_organization_id,
                "profil_info":profil_info,
                "created_at":self.created_at,
                "updated_at":self.updated_at,
                "allowed_devices":user_config_info.get('allowed_device_count',0)
            } 
            return user_info
        except Exception as e:
            DebugService.app_debug_print(f"\n error formating user  >< : {e} \n\n", True)
            user_info = {
            "photo":'empty',
            "signature":'-',
            "id":str(self.id),
            "first_name":self.first_name,
            "username":self.username,
            "last_name":self.last_name,
            "sur_name":self.sur_name,
            "gender":self.get_gender_translated(accept_language),
            "phone_number":self.phone_number,
            "address":self.address,
            "email":self.email,
            "emails":self.emails,
            "phone_numbers":self.phone_numbers,
            "account_status":self.account_status,
            "others":self.others,
            "account_status_lbl":self.handle_account_status(accept_language),
            "rbac_role_id":str(self.rbac_role_id),
            "rbac_profile_id":self.rbac_profile_id,
            "sys_organization_id":self.sys_organization_id,
            "created_at":self.created_at,
            "updated_at":self.updated_at, 
        } 
        return user_info
 
    
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "first_name": "Prénom",
            "last_name": "Nom de famille",
            "sur_name": "Post-nom",
            "email": "Email",
            "phone_number": "Numéro de téléphone",
            "face_image_path_id": "Photo du visage",
            "id_card_image_path_id": "Photo de la carte d'identité",
            "address": "Adresse",
            "emails": "Emails",
            "phone_numbers": "Numéros de téléphone",
            "account_status": "Statut du compte",
            "username": "Nom d'utilisateur",
            "password": "Mot de passe",
            "user_account_hash": "Hash du compte",
            "user_account_socket_hash": "Hash socket du compte",
            "gender": "Genre",
            "birth_day": "Date de naissance",
            "birth_city": "Ville de naissance",
            "ref_entity_id": "Entité de référence",
            "ref_country_id": "Pays",
            "sys_organization_id": "Organisation",
            "rbac_role_id": "Rôle",
            "sys_person_id": "Personne",
            "login_fail_attempt_count": "Tentatives de connexion échouées",
            "login_locked_until": "Connexion bloquée jusqu'au",
            "login_fail_status": "Statut d'échec de connexion",
            "reset_password_fail_attempt_count": "Tentatives de réinitialisation échouées",
            "reset_password_locked_until": "Réinitialisation bloquée jusqu'au",
            "reset_password_fail_status": "Statut d'échec de réinitialisation",
            "is_default": "Compte par défaut",
            "should_update_password": "Doit changer le mot de passe",
            "registration_origin": "Origine de l'inscription",
            "cfg_organism_chart_id": "Organigramme",
            "rbac_profile_id": "Profil système",
            "others": "Autres informations",
        },
        en={
            "first_name": "First Name",
            "last_name": "Last Name",
            "sur_name": "Surname",
            "email": "Email",
            "phone_number": "Phone Number",
            "face_image_path_id": "Face Image",
            "id_card_image_path_id": "ID Card Image",
            "address": "Address",
            "emails": "Emails",
            "phone_numbers": "Phone Numbers",
            "account_status": "Account Status",
            "username": "Username",
            "password": "Password",
            "user_account_hash": "Account Hash",
            "user_account_socket_hash": "Account Socket Hash",
            "gender": "Gender",
            "birth_day": "Date of Birth",
            "birth_city": "City of Birth",
            "ref_entity_id": "Reference Entity",
            "ref_country_id": "Country",
            "sys_organization_id": "Organization",
            "rbac_role_id": "Role",
            "sys_person_id": "Person",
            "login_fail_attempt_count": "Login Fail Attempts",
            "login_locked_until": "Login Locked Until",
            "login_fail_status": "Login Fail Status",
            "reset_password_fail_attempt_count": "Reset Password Fail Attempts",
            "reset_password_locked_until": "Reset Password Locked Until",
            "reset_password_fail_status": "Reset Password Fail Status",
            "is_default": "Default Account",
            "should_update_password": "Must Change Password",
            "registration_origin": "Registration Origin",
            "cfg_organism_chart_id": "Organization Chart",
            "rbac_profile_id": "System Profile",
            "others": "Other Information",
        },
        ln={
            "first_name": "Nkombo ya liboso",
            "last_name": "Nkombo ya libota",
            "sur_name": "Nkombo ya nsima",
            "email": "Email",
            "phone_number": "Nimero ya telefone",
            "face_image_path_id": "Foto ya elongi",
            "id_card_image_path_id": "Foto ya karti ya moto",
            "address": "Adresse",
            "emails": "Ba emails",
            "phone_numbers": "Ba nimero ya telefone",
            "account_status": "Lolenge ya compte",
            "username": "Nkombo ya mosaleli",
            "password": "Mot de passe",
            "user_account_hash": "Hash ya compte",
            "user_account_socket_hash": "Hash socket ya compte",
            "gender": "Mwasi to Mobali",
            "birth_day": "Mokolo ya mbotama",
            "birth_city": "Engumba ya mbotama",
            "ref_entity_id": "Entité ya référence",
            "ref_country_id": "Ekolo",
            "sys_organization_id": "Organisation",
            "rbac_role_id": "Mosala",
            "sys_person_id": "Moto",
            "login_fail_attempt_count": "Bomeki ya connexion elondi te",
            "login_locked_until": "Connexion ekangami tii na",
            "login_fail_status": "Lolenge ya kolonga te ya connexion",
            "reset_password_fail_attempt_count": "Bomeki ya kobongola mot de passe elondi te",
            "reset_password_locked_until": "Kobongola mot de passe ekangami tii na",
            "reset_password_fail_status": "Lolenge ya kolonga te ya kobongola mot de passe",
            "is_default": "Compte ya ebandeli",
            "should_update_password": "Asengeli kobongola mot de passe",
            "registration_origin": "Esika ya bokomi",
            "cfg_organism_chart_id": "Organigramme",
            "rbac_profile_id": "Profil ya système",
            "others": "Makambo mosusu",
        },
    )

    class Settings:
        name = f"{CollectionKey.SYS_USER.model_name}"
        validate_on_save = True
