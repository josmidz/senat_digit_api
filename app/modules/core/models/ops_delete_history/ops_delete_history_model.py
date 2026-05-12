import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from pydantic import Field

from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_EXTRA_METAS, ERestoreStatus, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper
from app.modules.core.utils.model.status_color_helper import StatusColorHelper


class OpsDeleteHistoryModel(BaseDocument):
    """
    Tracks every hard-delete operation performed on any collection.

    Stores the full document data at the moment of deletion so the record
    can be audited or restored later.
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
        description="Unique short identifier for the history entry",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    # --------------- context fields ---------------

    collection_name: str = Field(
        ...,
        description="The MongoDB collection name (snake_case model name) that was deleted from",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    collection_key: Optional[str] = Field(
        default=None,
        description="The CollectionKey value (camelCase) if available",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    document_id: str = Field(
        ...,
        description="The _id of the document that was deleted (as string)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    operation_type: str = Field(
        default="hard_delete",
        description="Type of delete: hard_delete | hard_delete_with_query | delete_many",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    # --------------- full deleted data ---------------

    data_before: Dict[str, Any] = Field(
        ...,
        description="Complete document data at the moment of deletion (full snapshot)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_DICT.value}": True},
            exclude_from_data_table=True,
        ),
    )

    # --------------- actor ---------------

    deleted_by_user_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="The user who performed the deletion",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}": "sysUsers",
            },
        ),
    )

    deleted_at_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when the deletion occurred",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True},
        ),
    )

    # --------------- restore tracking ---------------
    restore_status: ERestoreStatus = Field(
        default=ERestoreStatus.NOT_RESTORED,
        description="Restore status of this history entry",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}": f"{ERestoreStatus.__name__}",
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    ERestoreStatus,
                    StatusColorHelper.create_mapping(
                        green=[ERestoreStatus.RESTORED.value],
                        orange=[ERestoreStatus.PARTIALLY_RESTORED.value],
                        red=[ERestoreStatus.NOT_RESTORED.value],
                    )
                )
            },
        ),
    )

    restore_count: int = Field(
        default=0,
        description="Number of times this history entry has been used to restore data",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_NUMBER.value}": True},
        ),
    )

    async def get_formated_data(self, accept_language: str = 'fr', output: FormatedOutPut = FormatedOutPut.MINIMAL) -> Optional[dict]:
        from app.modules.core.models.field_translation_keys import TRANSLATIONS

        try:
            # Fetch the user who performed the deletion
            from app.modules.core.models.sys_user.sys_user_model import SysUserModel
            deleted_by_user = None
            if self.deleted_by_user_id:
                user_instance = await SysUserModel.get(self.deleted_by_user_id)
                if user_instance:
                    deleted_by_user = await user_instance.get_formated_data(accept_language, FormatedOutPut.MINIMAL)

            # Get translations for enums
            translations = TRANSLATIONS.get(accept_language, TRANSLATIONS.get('en', {}))

            # Restore status translations
            restore_status_lbl = translations.get(ERestoreStatus, {}).get(self.restore_status, self.restore_status.value if self.restore_status else "")
            restore_status_color = StatusColorHelper.get_status_color(
                self.restore_status,
                StatusColorHelper.create_mapping(
                    green=[ERestoreStatus.RESTORED.value],
                    orange=[ERestoreStatus.PARTIALLY_RESTORED.value],
                    red=[ERestoreStatus.NOT_RESTORED.value],
                )
            )

            formatted = {
                "id": str(self.id),
                "identifier": self.identifier,
                "collection_name": self.collection_name,
                "collection_key": self.collection_key,
                "document_id": self.document_id,
                "operation_type": self.operation_type,
                "data_before": self.data_before,
                "deleted_by_user_id": str(self.deleted_by_user_id) if self.deleted_by_user_id else None,
                "deleted_by_user": deleted_by_user,
                "deleted_at_utc": self.format_datetime_for_display(self.deleted_at_utc) if self.deleted_at_utc else None,
                "restore_status": self.restore_status.value if self.restore_status else None,
                "restore_status_lbl": restore_status_lbl,
                "restore_status_color": restore_status_color,
                "restore_count": self.restore_count,
                "created_at": self.format_datetime_for_display(self.created_at) if self.created_at else None,
            }

            if output == FormatedOutPut.MINIMAL:
                return {
                    "id": formatted["id"],
                    "identifier": formatted["identifier"],
                    "collection_name": formatted["collection_name"],
                    "document_id": formatted["document_id"],
                    "operation_type": formatted["operation_type"],
                    "deleted_by_user": formatted["deleted_by_user"],
                    "deleted_at_utc": formatted["deleted_at_utc"],
                    "restore_status": formatted["restore_status"],
                    "restore_status_lbl": formatted["restore_status_lbl"],
                    "restore_status_color": formatted["restore_status_color"],
                    "restore_count": formatted["restore_count"],
                }

            return formatted

        except Exception as e:
            print(f"Error formatting ops delete history data: {e}")
            import traceback
            traceback.print_exc()
            raise

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "collection_name": "Nom de la collection",
            "collection_key": "Clé de la collection",
            "document_id": "ID du document",
            "operation_type": "Type d'opération",
            "data_before": "Données avant suppression",
            "deleted_by_user_id": "Supprimé par",
            "deleted_at_utc": "Date de suppression (UTC)",
            "restore_status": "Statut de restauration",
            "restore_count": "Nombre de restaurations",
        },
        en={
            "collection_name": "Collection Name",
            "collection_key": "Collection Key",
            "document_id": "Document ID",
            "operation_type": "Operation Type",
            "data_before": "Data Before Deletion",
            "deleted_by_user_id": "Deleted By",
            "deleted_at_utc": "Deletion Date (UTC)",
            "restore_status": "Restore Status",
            "restore_count": "Restore Count",
        },
        ln={
            "collection_name": "Nkombo ya collection",
            "collection_key": "Fungola ya collection",
            "document_id": "ID ya mokanda",
            "operation_type": "Lolenge ya opération",
            "data_before": "Données liboso ya kolongola",
            "deleted_by_user_id": "Elongolamá na",
            "deleted_at_utc": "Mokolo ya kolongola (UTC)",
            "restore_status": "Lolenge ya kozongisa",
            "restore_count": "Mbala ya kozongisa",
        },
    )

    class Settings:
        name = f"{CollectionKey.OPS_DELETE_HISTORY.model_name}"
        validate_on_save = True
