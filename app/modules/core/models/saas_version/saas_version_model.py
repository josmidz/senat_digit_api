from typing import Annotated, List, Optional
import uuid
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS
from pydantic import Field
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from beanie import  Indexed, PydanticObjectId
 
class SaasVersionModel(BaseDocument):
    """
    This collection defines the SaaS versions and their metadata.
    """
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
        description="Unique identifier for the SaaS version",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    version_name: Annotated[str, Indexed(unique=True, name="ssaver_name_index")] = Field(
        ...,
        description="Name of the SaaS version (e.g., 1.0.0-alpha)",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    minor: str = Field(
        ...,
        description="Minor version of the SaaS (e.g., 1 in 1.x.x)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    major: str = Field(
        ...,
        description="Major version of the SaaS (e.g., 2 in 2.x.x)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    patch: str = Field(
        ...,
        description="Patch version of the SaaS (e.g., 3 in x.x.3)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    url_segment: str = Field(
        ...,
        description="URL segment representing the API version (e.g., /v1)",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    is_current: bool = Field(
        default=False,
        description="Indicates whether this version is the current active version",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )

    is_validated: bool = Field(
        default=False,
        description="Indicates whether this version has been validated",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True})
    )

    developers: List[str] = Field(
        ...,
        description="List of developer names involved in the version",
        json_schema_extra=translation_meta(may_have_translation=False, to_be_translated_in_front=False, data_type={"is_array_of_strings": True})
    )

    release_notes_str: str = Field(
        default="Aucune note fournie.",
        description="Release notes in plain text",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )

    release_notes_html: str = Field(
        default="<p>Aucune note fournie.</p>",
        description="Release notes in HTML format",
        json_schema_extra=translation_meta(may_have_translation=True, to_be_translated_in_front=True, data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True})
    )
     
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "version_name": "Nom de la version",
            "minor": "Version mineure",
            "major": "Version majeure",
            "patch": "Correctif",
            "url_segment": "Segment URL",
            "is_current": "Version actuelle",
            "is_validated": "Validée",
            "developers": "Développeurs",
            "release_notes_str": "Notes de version (texte)",
            "release_notes_html": "Notes de version (HTML)",
        },
        en={
            "version_name": "Version Name",
            "minor": "Minor Version",
            "major": "Major Version",
            "patch": "Patch",
            "url_segment": "URL Segment",
            "is_current": "Current Version",
            "is_validated": "Validated",
            "developers": "Developers",
            "release_notes_str": "Release Notes (Text)",
            "release_notes_html": "Release Notes (HTML)",
        },
        ln={
            "version_name": "Nkombo ya version",
            "minor": "Version ya moke",
            "major": "Version ya monene",
            "patch": "Correctif",
            "url_segment": "Eteni ya URL",
            "is_current": "Version ya sikawa",
            "is_validated": "Endimamaki",
            "developers": "Ba développeurs",
            "release_notes_str": "Makambo ya version (texte)",
            "release_notes_html": "Makambo ya version (HTML)",
        },
    )

    class Settings:
        name = f"{CollectionKey.SAAS_VERSION.model_name}"
        validate_on_save = True 
