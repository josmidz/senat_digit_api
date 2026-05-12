from typing import Optional
import uuid
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, FormatedOutPut, OutputDataType
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

class RefSudoRlsSecurityGroupUserModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
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

    ref_sudo_rls_security_group_id: PydanticObjectId = Field(
        ...,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    sys_user_id: PydanticObjectId = Field(
        ...,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
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
            "ref_sudo_rls_security_group_id": "ID groupe de sécurité",
            "sys_user_id": "ID utilisateur",
            "sys_organization_id": "ID organisation",
        },
        en={
            "ref_sudo_rls_security_group_id": "Security Group ID",
            "sys_user_id": "User ID",
            "sys_organization_id": "Organization ID",
        },
        ln={
            "ref_sudo_rls_security_group_id": "ID ya lisanga ya sécurité",
            "sys_user_id": "ID ya mosaleli",
            "sys_organization_id": "ID ya organisation",
        },
    )

    class Settings:
        name = f"{CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER.model_name}"
        validate_on_save = True

    async def get_formated_data(self, accept_language: str, output: FormatedOutPut = FormatedOutPut.MINIMAL) -> dict:
        try:
            from app.modules.core.services.generic.generic_services import GenericService
            generic_service = GenericService(accept_language)
            from app.modules.core.models.sys_user.sys_user_model import SysUserModel
            user = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": str(self.sys_user_id)},
            )
            base_data = {
                "id": str(self.id),
                "identifier": self.identifier,
                "ref_sudo_rls_security_group_id": str(self.ref_sudo_rls_security_group_id),
                "sys_user_id": str(self.sys_user_id),
                "sys_organization_id": str(self.sys_organization_id),
                "user": user
            }
            return base_data
        except Exception as e:
            print(f"Error in get_formated_data: {e}")
            return {
                "id": str(self.id),
                "identifier": self.identifier,
                "ref_sudo_rls_security_group_id": str(self.ref_sudo_rls_security_group_id),
                "sys_user_id": str(self.sys_user_id),
                "sys_organization_id": str(self.sys_organization_id),
                "user": None
            }



