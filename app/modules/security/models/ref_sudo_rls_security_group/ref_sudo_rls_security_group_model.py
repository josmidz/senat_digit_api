
from typing import Optional
import uuid
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.enums.type_enum import FormatedOutPut
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

class RefSudoRlsSecurityGroupModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True,
                f"{EGLOBAL_EXTRA_METAS.FIELD_ORDERING.value}":"id,identifier,name,flag,created_at",
                f"{EGLOBAL_EXTRA_METAS.EXCLUDED_FIELDS.value}":"created_by_id,id,sys_organization_id,created_at,updated_at,flag",
                f"{EGLOBAL_EXTRA_METAS.UPPERCASED_FIELD_VALUES.value}":"identifier"
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    name: str = Field(
        ...,
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    description_str: Optional[str] = Field(
        default="aucune description fournie",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True}
        )
    )

    sys_organization_id: PydanticObjectId = Field(
        ...,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    ) 

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "description_str": "Description",
            "sys_organization_id": "ID organisation",
        },
        en={
            "name": "Name",
            "description_str": "Description",
            "sys_organization_id": "Organization ID",
        },
        ln={
            "name": "Nkombo",
            "description_str": "Ndimbola",
            "sys_organization_id": "ID ya organisation",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP.model_name}"
        validate_on_save = True


    async def get_formated_data(self, accept_language: str, output: FormatedOutPut = FormatedOutPut.MINIMAL) -> dict:
        try:
            from app.modules.core.services.generic.generic_services import GenericService
            from app.modules.security.models.ref_sudo_rls_security_group_user.ref_sudo_rls_security_group_user_model import RefSudoRlsSecurityGroupUserModel
            generic_service = GenericService(accept_language)
            from app.modules.core.models.sys_organization.sys_organization_model import SysOrganizationModel
            users = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
                all_data=True,
                page=0,
                limit=100000,
                accept_language=accept_language,
                query={"filter__ref_sudo_rls_security_group_id": str(self.id)},
            )
            formatted_users = []
            for user in users:
                user_instance = RefSudoRlsSecurityGroupUserModel(**user)
                formatted_user = await user_instance.get_formated_data(accept_language, output)
                formatted_users.append(formatted_user)
            user_count = await generic_service.count_data_from_collection(
                collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
                accept_language=accept_language,
                query={"filter__ref_sudo_rls_security_group_id": str(self.id)},
            )
            base_data = {
                "id": str(self.id),
                "identifier": self.identifier,
                "name": self.name,
                "description_str": self.description_str,
                "sys_organization_id": str(self.sys_organization_id),
                "created_at": self.created_at,
                "user_count": user_count,
                "users": formatted_users
            }
            return base_data
        except Exception as e:
            print(f"Error in get_formated_data: {e}")
            return {
                "id": str(self.id),
                "identifier": self.identifier,
                "name": self.name,
                "description_str": self.description_str,
                "sys_organization_id": str(self.sys_organization_id),
                "created_at": self.created_at,
                "user_count": 0,
                "users": []
            }



