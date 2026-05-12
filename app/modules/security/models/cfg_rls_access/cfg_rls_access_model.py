from typing import Optional
import uuid
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.security.enums.security_enum import EConfigSudoActionTypeFlag, ERlsAccessTypeFlag, ESudoActionAccessTargetedTypeFlag, ESudoActionAccessTypeFlag
from app.modules.core.utils.model.status_color_helper import StatusColorHelper
from app.modules.core.utils.helpers.line_helper import exception_line_info, format_exception
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

class CfgRlsAccessModel(BaseDocument):
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
    
    # TARGETED ID CAN BE A USER OR A SUDO/RLS SECURITY GROUP
    targeted_id: PydanticObjectId = Field(
        ...,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    targeted_type: Optional[ESudoActionAccessTargetedTypeFlag] = Field(
        default=ESudoActionAccessTargetedTypeFlag.USER,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":f"{ESudoActionAccessTargetedTypeFlag.__name__}",
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    ESudoActionAccessTargetedTypeFlag,
                    StatusColorHelper.create_mapping(
                        green=[ESudoActionAccessTargetedTypeFlag.USER.value,],
                        orange=[ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value,],
                    )
                )
            }
        )
    )

    rls_access_type: Optional[ERlsAccessTypeFlag] = Field(
        default=ERlsAccessTypeFlag.GLOBAL_ACCESS,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":f"{ERlsAccessTypeFlag.__name__}",
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    ERlsAccessTypeFlag,
                    StatusColorHelper.create_mapping(
                        green=[ERlsAccessTypeFlag.GLOBAL_ACCESS.value,],
                        orange=[ERlsAccessTypeFlag.CUSTOM_ACCESS.value,],
                        red=[ERlsAccessTypeFlag.REVOKED_ACCESS.value,],
                    )
                )
            }
        )
    )

    cfg_organization_rls_id: Optional[PydanticObjectId] = Field(
        None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.CFG_ORGANIZATION_RLS.value}",
            }
        )
    )  

    # IF CUSTOM ACCESS IS SET, WE CAN TARGET A SPECIFIC ROW ( DOCUMENT ID )
    targeted_row_id: Optional[PydanticObjectId] = Field(
        None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    # TODO:: CHECK IF IT'S NECESSARY TO KEEP COLLECTION NAME OF TARGETED ROW ID
    collection_name: Optional[str] = Field(
        None,
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
            "targeted_id": "ID cible",
            "targeted_type": "Type de cible",
            "rls_access_type": "Type d'accès RLS",
            "cfg_organization_rls_id": "ID configuration RLS organisation",
            "targeted_row_id": "ID ligne ciblée",
            "collection_name": "Nom de la collection",
            "sys_organization_id": "ID organisation",
        },
        en={
            "targeted_id": "Target ID",
            "targeted_type": "Target Type",
            "rls_access_type": "RLS Access Type",
            "cfg_organization_rls_id": "Organization RLS Config ID",
            "targeted_row_id": "Targeted Row ID",
            "collection_name": "Collection Name",
            "sys_organization_id": "Organization ID",
        },
        ln={
            "targeted_id": "ID ya cible",
            "targeted_type": "Lolenge ya cible",
            "rls_access_type": "Lolenge ya accès RLS",
            "cfg_organization_rls_id": "ID ya configuration RLS ya organisation",
            "targeted_row_id": "ID ya molongo eciblée",
            "collection_name": "Nkombo ya collection",
            "sys_organization_id": "ID ya organisation",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_RLS_ACCESS.model_name}"
        validate_on_save = True


    async def get_formated_data(self,lang:str="fr",output: FormatedOutPut = FormatedOutPut.MINIMAL) -> dict:
        try:
            from app.modules.security.models.cfg_organization_rls.cfg_organization_rls_model import CfgOrganizationRlsModel
            from app.modules.core.models.sys_user.sys_user_model import SysUserModel
            from app.modules.security.models.ref_sudo_rls_security_group.ref_sudo_rls_security_group_model import RefSudoRlsSecurityGroupModel
            cfg_organization_rls = None
            if self.cfg_organization_rls_id:
                cfg_organization_rls = await CfgOrganizationRlsModel.get(self.cfg_organization_rls_id)
                if cfg_organization_rls:
                    cfg_organization_rls = await cfg_organization_rls.get_formated_data(lang, output)

            targeted_type_lbl = self.handle_translation_status(self.targeted_type,ESudoActionAccessTargetedTypeFlag,lang)
            targeted_type_color= StatusColorHelper.get_status_color(self.targeted_type,StatusColorHelper.create_mapping(
                green=[ESudoActionAccessTargetedTypeFlag.USER.value,],
                orange=[ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value,],
            ))
            user = None
            group = None
            if self.targeted_type == ESudoActionAccessTargetedTypeFlag.USER:
                user = await SysUserModel.get(self.targeted_id)
                if user:
                    user = await user.get_formated_data(lang, FormatedOutPut.MINIMAL)
            elif self.targeted_type == ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP:
                group = await RefSudoRlsSecurityGroupModel.get(self.targeted_id)
                if group:
                    group = await group.get_formated_data(lang, output)

            rls_access_type_lbl = self.handle_translation_status(self.rls_access_type,ERlsAccessTypeFlag,lang)
            rls_access_type_color= StatusColorHelper.get_status_color(self.rls_access_type,StatusColorHelper.create_mapping(
                green=[ERlsAccessTypeFlag.GLOBAL_ACCESS.value,],
                orange=[ERlsAccessTypeFlag.CUSTOM_ACCESS.value,],
                red=[ERlsAccessTypeFlag.REVOKED_ACCESS.value,],
            ))

            if output == FormatedOutPut.MINIMAL:
                return {
                    "id":str(self.id),
                    "identifier":self.identifier,
                    "targeted_id":str(self.targeted_id),
                    "targeted_type":self.targeted_type.value,
                    "collection_name":self.collection_name,
                    "targeted_row_id":str(self.targeted_row_id),
                    "rls_access_type":self.rls_access_type.value,
                    "cfg_organization_rls_id":str(self.cfg_organization_rls_id),
                    "sys_organization_id":str(self.sys_organization_id),
                }
            else:
                return {
                    "id":str(self.id),
                    "identifier":self.identifier,

                    "targeted_id":str(self.targeted_id),
                    "targeted_type":self.targeted_type.value,
                    "targeted_type_lbl":targeted_type_lbl,
                    "targeted_type_color":targeted_type_color,
                    "user":user,
                    "group":group,

                    "collection_name":self.collection_name,
                    "targeted_row_id":str(self.targeted_row_id),

                    "rls_access_type":self.rls_access_type.value,
                    "rls_access_type_lbl":rls_access_type_lbl,
                    "rls_access_type_color":rls_access_type_color,

                    "cfg_organization_rls_id":str(self.cfg_organization_rls_id),
                    "cfg_organization_rls":cfg_organization_rls,
                }

        except Exception as e:
            format_error = format_exception(f"error get_formated_data ",e)
            print(f"\n\n\n error in get_formated_data sudo_action_access_model : {exception_line_info(e)} : {format_error}\n\n")
            return {
                "id":str(self.id),
                "identifier":self.identifier,
                "targeted_id":str(self.targeted_id),
                "targeted_type":self.targeted_type.value,
                "rls_access_type":self.rls_access_type.value,
                "cfg_organization_rls_id":str(self.cfg_organization_rls_id),
                "collection_name":self.collection_name,
                "targeted_row_id":str(self.targeted_row_id),
                "sys_organization_id":str(self.sys_organization_id),
            }



