from typing import Optional
import uuid
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.security.enums.security_enum import EConfigSudoActionTypeFlag, ESudoActionAccessTargetedTypeFlag, ESudoActionAccessTypeFlag
from app.modules.core.utils.model.status_color_helper import StatusColorHelper
from app.modules.core.utils.helpers.line_helper import exception_line_info, format_exception
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

class CfgSudoActionAccessModel(BaseDocument):
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
    
    # TARGETED ID CAN BE A USER OR A SUDO/RLS SECURITY GROUP/ CROSS ORGANIZATION / INTER CONNECTED ORGANIZATION
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
                        teal=[ESudoActionAccessTargetedTypeFlag.CROSS_ORGANIZATION.value,],
                        purple=[ESudoActionAccessTargetedTypeFlag.INTER_CONNECTED_ORGANIZATION.value,],
                    )
                )
            }
        )
    )

    sudo_action_access_type: Optional[ESudoActionAccessTypeFlag] = Field(
        default=ESudoActionAccessTypeFlag.DELEGATED_ACCESS,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}":f"{ESudoActionAccessTypeFlag.__name__}",
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    ESudoActionAccessTypeFlag,
                    StatusColorHelper.create_mapping(
                        green=[ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value,],
                        orange=[ESudoActionAccessTypeFlag.GROUPED_ACCESS.value,],
                        teal=[ESudoActionAccessTypeFlag.DELEGATED_ACCESS.value,],
                        brown=[ESudoActionAccessTypeFlag.GROUPED_CROSS_VALIDATION_ACCESS.value,],
                        purple=[ESudoActionAccessTypeFlag.GROUPED_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACCESS.value,],
                    )
                )
            }
        )
    )


    cfg_organization_sudo_action_id: Optional[PydanticObjectId] = Field(
        None,
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.CFG_ORGANIZATION_SUDO_ACTION.value}",
            }
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
            "sudo_action_access_type": "Type d'accès sudo",
            "cfg_organization_sudo_action_id": "ID configuration sudo organisation",
            "sys_organization_id": "ID organisation",
        },
        en={
            "targeted_id": "Target ID",
            "targeted_type": "Target Type",
            "sudo_action_access_type": "Sudo Action Access Type",
            "cfg_organization_sudo_action_id": "Organization Sudo Action Config ID",
            "sys_organization_id": "Organization ID",
        },
        ln={
            "targeted_id": "ID ya cible",
            "targeted_type": "Lolenge ya cible",
            "sudo_action_access_type": "Lolenge ya accès sudo",
            "cfg_organization_sudo_action_id": "ID ya configuration sudo ya organisation",
            "sys_organization_id": "ID ya organisation",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_SUDO_ACTION_ACCESS.model_name}"
        validate_on_save = True


    async def get_formated_data(self,lang:str="fr",output: FormatedOutPut = FormatedOutPut.MINIMAL) -> dict:
        try:
            from app.modules.security.models.cfg_organization_sudo_action.cfg_organization_sudo_action_model import CfgOrganizationSudoActionModel
            from app.modules.core.models.sys_user.sys_user_model import SysUserModel
            from app.modules.security.models.ref_sudo_rls_security_group.ref_sudo_rls_security_group_model import RefSudoRlsSecurityGroupModel
            from app.modules.core.models.sys_organization.sys_organization_model import SysOrganizationModel
            cfg_organization_sudo_action = None
            if self.cfg_organization_sudo_action_id:
                cfg_organization_sudo_action = await CfgOrganizationSudoActionModel.get(self.cfg_organization_sudo_action_id)
                if cfg_organization_sudo_action:
                    cfg_organization_sudo_action = await cfg_organization_sudo_action.get_formated_data(lang, output)

            targeted_type_lbl = self.handle_translation_status(self.targeted_type,ESudoActionAccessTargetedTypeFlag,lang)
            targeted_type_color= StatusColorHelper.get_status_color(self.targeted_type,StatusColorHelper.create_mapping(
                green=[ESudoActionAccessTargetedTypeFlag.USER.value,],
                orange=[ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value,],
                teal=[ESudoActionAccessTargetedTypeFlag.CROSS_ORGANIZATION.value,],
                purple=[ESudoActionAccessTargetedTypeFlag.INTER_CONNECTED_ORGANIZATION.value,],
            ))
            user = None
            group = None
            organization = None
            if self.targeted_type == ESudoActionAccessTargetedTypeFlag.USER:
                user = await SysUserModel.get(self.targeted_id)
                if user:
                    user = await user.get_formated_data(lang, FormatedOutPut.MINIMAL)

            elif self.targeted_type == ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP:
                group = await RefSudoRlsSecurityGroupModel.get(self.targeted_id)
                if group:
                    group = await group.get_formated_data(lang, output)

            elif self.targeted_type == ESudoActionAccessTargetedTypeFlag.CROSS_ORGANIZATION:
                organization = await SysOrganizationModel.get(self.targeted_id)
                if organization:
                    organization = await organization.get_formated_data(lang, FormatedOutPut.MINIMAL)

            sudo_action_access_type_lbl = self.handle_translation_status(self.sudo_action_access_type,ESudoActionAccessTypeFlag,lang)
            sudo_action_access_type_color= StatusColorHelper.get_status_color(self.sudo_action_access_type,StatusColorHelper.create_mapping(
                green=[ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value,],
                orange=[ESudoActionAccessTypeFlag.GROUPED_ACCESS.value,],
                teal=[ESudoActionAccessTypeFlag.DELEGATED_ACCESS.value,],
                brown=[ESudoActionAccessTypeFlag.GROUPED_CROSS_VALIDATION_ACCESS.value,],
                purple=[ESudoActionAccessTypeFlag.GROUPED_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACCESS.value,],
            ))

            if output == FormatedOutPut.MINIMAL:
                return {
                    "id":str(self.id),
                    "identifier":self.identifier,
                    "targeted_id":str(self.targeted_id),
                    "targeted_type":self.targeted_type.value,
                    "sudo_action_access_type":self.sudo_action_access_type.value,
                    "cfg_organization_sudo_action_id":str(self.cfg_organization_sudo_action_id),
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
                    "organization":organization,

                    "sudo_action_access_type":self.sudo_action_access_type.value,
                    "sudo_action_access_type_lbl":sudo_action_access_type_lbl,
                    "sudo_action_access_type_color":sudo_action_access_type_color,

                    "cfg_organization_sudo_action_id":str(self.cfg_organization_sudo_action_id),
                    "cfg_organization_sudo_action":cfg_organization_sudo_action,
                }

        except Exception as e:
            format_error = format_exception(f"error get_formated_data ",e)
            print(f"\n\n\n error in get_formated_data sudo_action_access_model : {exception_line_info(e)} : {format_error}\n\n")
            return {
                "id":str(self.id),
                "identifier":self.identifier,
                "targeted_id":str(self.targeted_id),
                "targeted_type":self.targeted_type.value,
                "sudo_action_access_type":self.sudo_action_access_type.value,
                "cfg_organization_sudo_action_id":str(self.cfg_organization_sudo_action_id),
                "sys_organization_id":str(self.sys_organization_id),
            }



