
import uuid
from typing import   Optional
from beanie import PydanticObjectId
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper

from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey

class ArchFileModel(BaseDocument):
    """
    This collection defines file metadata and its related properties for storage and management.
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
                # "delete_if_not_used_in":"files,folders"
            }
        )
    )


    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the file",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    file_name: str = Field(
        ...,
        description="file_name of the file",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    file_url: str = Field(
        ...,
        description="URL of the file",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    file_original_name: str = Field(
        ...,
        description="Verbose description of the file",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    file_type: Optional[str] = Field(
        default=None,
        description="Type of the file (e.g., PDF, image)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
    file_extension: Optional[str] = Field(
        default=None,
        description="Type of the file (e.g., .pdf, .jpg, .png)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    file_size: Optional[str] = Field(
        default=None,
        description="Size of the file (e.g., 1.2 MB)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    file_path: Optional[str] = Field(
        default=None,
        description="Path to the file in storage",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    moved_to_trash: bool = Field(
        default=False,
        description="Flag indicating whether the file is moved to the bin",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )

    is_masked: bool = Field(
        default=False,
        description="Flag indicating whether the file is masked",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )

    is_locked: bool = Field(
        default=True,
        description="Flag indicating whether the file is locked",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )
    is_local_file: Optional[bool] = Field(
        default=True,
        description="Flag indicating whether the file is locked",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )
    

    remote_arch_file_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID from",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True
            }
        )
    )
    
    remote_arch_file_url: Optional[str] = Field(
        default=None,
        description="url from remote",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True
            }
        )
    )
    
    file_str_id_composed: Optional[str] = Field(
        default=None,
        description="composed id",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True
            }
        )
    )

    file_generated_uuid: Optional[str] = Field(
        default=None,
        description="generated uuid",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}":True
            }
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
    
    

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "file_name": "Nom du fichier",
            "file_url": "URL du fichier",
            "file_original_name": "Nom original du fichier",
            "file_type": "Type de fichier",
            "file_extension": "Extension du fichier",
            "file_size": "Taille du fichier",
            "file_path": "Chemin du fichier",
            "moved_to_trash": "Mis en corbeille",
            "is_masked": "Masqué",
            "is_locked": "Verrouillé",
            "is_local_file": "Fichier local",
            "remote_arch_file_id": "ID fichier distant",
            "remote_arch_file_url": "URL fichier distant",
            "file_str_id_composed": "ID composé du fichier",
            "file_generated_uuid": "UUID généré du fichier",
            "sys_organization_id": "Organisation",
        },
        en={
            "file_name": "File Name",
            "file_url": "File URL",
            "file_original_name": "Original File Name",
            "file_type": "File Type",
            "file_extension": "File Extension",
            "file_size": "File Size",
            "file_path": "File Path",
            "moved_to_trash": "Moved to Trash",
            "is_masked": "Masked",
            "is_locked": "Locked",
            "is_local_file": "Local File",
            "remote_arch_file_id": "Remote File ID",
            "remote_arch_file_url": "Remote File URL",
            "file_str_id_composed": "Composed File ID",
            "file_generated_uuid": "Generated File UUID",
            "sys_organization_id": "Organization",
        },
        ln={
            "file_name": "Nkombo ya fisyé",
            "file_url": "URL ya fisyé",
            "file_original_name": "Nkombo ya ebandeli ya fisyé",
            "file_type": "Lolenge ya fisyé",
            "file_extension": "Extension ya fisyé",
            "file_size": "Bonene ya fisyé",
            "file_path": "Nzela ya fisyé",
            "moved_to_trash": "Ebwakamá na poubelle",
            "is_masked": "Ebombamá",
            "is_locked": "Ekangamá",
            "is_local_file": "Fisyé ya esika",
            "remote_arch_file_id": "ID ya fisyé ya mosika",
            "remote_arch_file_url": "URL ya fisyé ya mosika",
            "file_str_id_composed": "ID composé ya fisyé",
            "file_generated_uuid": "UUID esalamá ya fisyé",
            "sys_organization_id": "Organisasyo",
        },
    )

    class Settings:
        name = f"{CollectionKey.ARCH_FILE.model_name}"
        validate_on_save = True
