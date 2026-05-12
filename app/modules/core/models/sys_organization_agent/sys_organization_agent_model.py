from datetime import  date
import uuid
from pydantic import Field
from typing import  Optional
from beanie import PydanticObjectId
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from app.modules.core.models.mapping_keys import CollectionKey
 
class SysOrganizationAgentModel(BaseDocument):
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
    
    matricule: Optional[str] = Field(
        default=None,
        description="Matricule",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            overview_data_type={
                f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
            }
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
    
    sys_user_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="User Account ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            exclude_from_head=True,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.SYS_USER.value}",
            }
        )
    )
    cfg_function_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the associated fonction",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.CFG_FUNCTION.value}",
                f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
            }
        )
    )
    
    cfg_organism_chart_id:Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the associated organism chart",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.CFG_ORGANISM_CHART.value}",
                f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
            }
        )
    )
    
    cfg_grade_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the associated grade",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":f"{CollectionKey.CFG_GRADE.value}",
                f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}":True,
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
            }
        )
    )
  
    # ref_expense_chain_institution_id: Optional[PydanticObjectId] = Field(
    #     default=None,
    #     description="ID of the associated expense chain institution",
    #     json_schema_extra=translation_meta(
    #         may_have_translation=False,
    #         to_be_translated_in_front=False,
    #         data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
    #         overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
    #         extra_metas={
    #             f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}":"expenseChainInstitutions",
    #             f"{EGLOBAL_EXTRA_METAS.JOIN_ORGANIZATION_QUERY.value}":True
    #         }
    #     )
    # )
  
    sys_person_id: PydanticObjectId = Field(
        ...,
        description="ID of the associated person",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            exclude_from_head=True,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True,
                f"{EGLOBAL_EXTRA_METAS.ADDITIONAL_HEAD.value}":f"{CollectionKey.SYS_PERSON.value}",
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
            }
        )
    )
  

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "matricule": "Matricule",
            "sys_organization_id": "Organisation",
            "sys_user_id": "Compte utilisateur",
            "cfg_function_id": "Fonction",
            "cfg_organism_chart_id": "Organigramme",
            "cfg_grade_id": "Grade",
            "sys_person_id": "Personne",
        },
        en={
            "matricule": "Employee ID",
            "sys_organization_id": "Organization",
            "sys_user_id": "User Account",
            "cfg_function_id": "Function",
            "cfg_organism_chart_id": "Organization Chart",
            "cfg_grade_id": "Grade",
            "sys_person_id": "Person",
        },
        ln={
            "matricule": "Matricule",
            "sys_organization_id": "Organisation",
            "sys_user_id": "Compte ya mosaleli",
            "cfg_function_id": "Mosala",
            "cfg_organism_chart_id": "Organigramme",
            "cfg_grade_id": "Grade",
            "sys_person_id": "Moto",
        },
    )

    class Settings:
        name = f"{CollectionKey.SYS_ORGANIZATION_AGENT.model_name}"
        validate_on_save = True
 
