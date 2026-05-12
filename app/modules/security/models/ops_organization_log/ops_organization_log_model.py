from typing import Optional, Dict, Any
from enum import Enum
import uuid
from datetime import datetime, timezone, timedelta
from pydantic import Field
from beanie import PydanticObjectId
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper


class ECrudType(str, Enum):
    """CRUD operation types tracked in organization logs."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


class OpsOrganizationLogModel(BaseDocument):
    """
    Organization-level CRUD operation log entry.
    Tracks create, read, update, and delete operations across collections
    scoped to a specific organization.
    """

    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    sys_organization_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Organization this log belongs to (optional for system-level ops)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    sys_user_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="User who performed the operation",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    crud_type: ECrudType = Field(
        ...,
        description="Type of CRUD operation",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    collection_name: str = Field(
        ...,
        description="MongoDB collection name that was operated on",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    collection_key: Optional[str] = Field(
        default=None,
        description="CollectionKey value if available",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    document_id: Optional[str] = Field(
        default=None,
        description="The _id of the target document (as string)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    description_str: Optional[str] = Field(
        default=None,
        description="Human-readable description of the operation",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    performed_at_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when the operation was performed",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    expires_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when this log entry expires",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    # ── Field Translations ──

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "sys_organization_id": "ID organisation",
            "sys_user_id": "ID utilisateur",
            "crud_type": "Type d'op\u00e9ration",
            "collection_name": "Nom de la collection",
            "collection_key": "Cl\u00e9 de la collection",
            "document_id": "ID du document",
            "description_str": "Description",
            "performed_at_utc": "Effectu\u00e9 le",
            "expires_at": "Expire le",
        },
        en={
            "sys_organization_id": "Organization ID",
            "sys_user_id": "User ID",
            "crud_type": "Operation Type",
            "collection_name": "Collection Name",
            "collection_key": "Collection Key",
            "document_id": "Document ID",
            "description_str": "Description",
            "performed_at_utc": "Performed At",
            "expires_at": "Expires At",
        },
        ln={
            "sys_organization_id": "ID ya organisation",
            "sys_user_id": "ID ya mosaleli",
            "crud_type": "Lolenge ya op\u00e9ration",
            "collection_name": "Nkombo ya collection",
            "collection_key": "Fungola ya collection",
            "document_id": "ID ya mokanda",
            "description_str": "Maloba",
            "performed_at_utc": "Esalemaki na",
            "expires_at": "Ekosila na",
        },
    )

    class Settings:
        name = f"{CollectionKey.OPS_ORGANIZATION_LOG.model_name}"
        validate_on_save = True

    async def get_formated_data(self, lang: str = "fr", output: FormatedOutPut = FormatedOutPut.MINIMAL) -> dict:
        return {
            "id": str(self.id),
            "identifier": self.identifier,
            "sys_organization_id": str(self.sys_organization_id) if self.sys_organization_id else None,
            "sys_user_id": str(self.sys_user_id) if self.sys_user_id else None,
            "crud_type": self.crud_type.value if isinstance(self.crud_type, ECrudType) else self.crud_type,
            "collection_name": self.collection_name,
            "collection_key": self.collection_key,
            "document_id": self.document_id,
            "description_str": self.description_str,
            "performed_at_utc": self.performed_at_utc.isoformat() if self.performed_at_utc else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
