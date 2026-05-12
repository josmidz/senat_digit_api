
from datetime import datetime
import uuid
from typing import   Optional
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field
from beanie import PydanticObjectId

from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
 
class ArchFolderModel(BaseDocument):
    """
    This collection defines folder structures, including nested subfolders and metadata.
    """
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                "delete_if_not_used_in":"files,folders"
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the folder",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    name: str = Field(
        ...,
        description="Name of the folder",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    description_str: str = Field(
        ...,
        description="Plain-text description of the folder",
        json_schema_extra=translation_meta(
            may_have_translation=True, 
            to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True})
    ) 
    
    moved_to_trash_at: Optional[datetime] = Field(
        default=None,
        description="date",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True,"is_optional":True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}":True
            }
        )
    )

    arch_folder_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the parent folder (if applicable)",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
         )
    )

    sys_organization_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="System organization ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True
            }
        )
    )

    moved_to_trash:Optional[bool]  = Field(
        default=False,
        description="Flag indicating whether the folder has been moved to the bin",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    is_masked: bool = Field(
        default=False,
        description="Flag indicating whether the folder is masked",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            to_be_translated_in_front=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    is_locked: bool = Field(
        default=False,
        description="Flag indicating whether the folder access is locked",
        json_schema_extra=translation_meta(
            may_have_translation=False, 
            exclude_from_head=True,
            exclude_from_update_head=True,
            to_be_translated_in_front=False, 
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )
    
    @classmethod
    async def find_with_subfolders(cls, folder_id: str):
        """
        Fetch a folder along with its subfolders.
        """
        folder = await cls.find_one({"_id": folder_id, "soft_deleted": False})
        if not folder:
            return None
        subfolders = await cls.find({"arch_folder_id": folder_id, "soft_deleted": False}).to_list()
        return {"folder": folder, "subfolders": subfolders}

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "name": "Nom",
            "description_str": "Description",
            "moved_to_trash_at": "Date de mise en corbeille",
            "arch_folder_id": "Dossier parent",
            "sys_organization_id": "Organisation",
            "moved_to_trash": "Mis en corbeille",
            "is_masked": "Masqué",
            "is_locked": "Verrouillé",
        },
        en={
            "name": "Name",
            "description_str": "Description",
            "moved_to_trash_at": "Moved to Trash At",
            "arch_folder_id": "Parent Folder",
            "sys_organization_id": "Organization",
            "moved_to_trash": "Moved to Trash",
            "is_masked": "Masked",
            "is_locked": "Locked",
        },
        ln={
            "name": "Nkombo",
            "description_str": "Ndimbola",
            "moved_to_trash_at": "Mokolo ya kobwaka na poubelle",
            "arch_folder_id": "Dossier ya liboso",
            "sys_organization_id": "Organisasyo",
            "moved_to_trash": "Ebwakamá na poubelle",
            "is_masked": "Ebombamá",
            "is_locked": "Ekangamá",
        },
    )

    class Settings:
        name = f"{CollectionKey.ARCH_FOLDER.model_name}"
        validate_on_save = True
