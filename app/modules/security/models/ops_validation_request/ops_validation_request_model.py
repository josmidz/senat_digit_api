from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from beanie import PydanticObjectId
from pydantic import BaseModel, Field
from app.modules.core.utils.model.field_decorator import translation_meta
import uuid
from app.modules.core.enums.type_enum import EMultipleValidationStatus, EMultipleValidationType, EGLOBAL_DATA_TYPE, EGLOBAL_DATA_TYPE_CONSTRAINTS, EGLOBAL_EXTRA_METAS, FormatedOutPut
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.status_color_helper import StatusColorHelper
from app.modules.security.enums.security_enum import EConfigSudoActionTypeFlag
from app.modules.security.schemas.validation_schams import SudoActionChildrenSchema
from app.modules.security.models.ops_validation_request import ValidatorDecisionRecord
from app.modules.security.types.security_type import ValidatorUser
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper


class OpsValidationRequestModel(BaseDocument):
    """Model for validation requests"""
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        description="MongoDB ObjectId",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    )

    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the folder",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    )

    next_validator_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Next validator ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        )
    )

    sys_organization_id: PydanticObjectId = Field(
        ...,
        description="System organization ID",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        )
    )

    endpoint_path: str = Field(
        ...,
        description="Path of the endpoint that triggered validation",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    endpoint_method: str = Field(
        ...,
        description="HTTP method of the endpoint",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    collection_name: str = Field(
        ...,
        description="Name of the collection being modified",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    operation_type: EMultipleValidationType = Field(
        default=EMultipleValidationType.CREATE,
        description="Gender of the person",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}": "EMultipleValidationType",
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True,
            }
        )
    )
    
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Data to be validated",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )


    upsert_query: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Upsert query for Data to be validated",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}
        )
    )

    target_document_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the document (for creation/ updates/deletes",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}": True},
            extra_metas={}
        )
    )

    cascade_children: Optional[List[SudoActionChildrenSchema]] = Field(
        default=[],
        description="Deprecated legacy field (replaced by recursive child requests linked via ops_validation_request_id)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ARRAY.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    )

    validation_is_completed: Optional[bool] = Field(
        default=False,
        description="if validation_is_completed == true, validation is completed",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}
        )
    )

    description_str: Optional[str] = Field(
        default="aucune description fournie",
        description="Plain-text description of the validation request",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=True,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    )

    download_requested_user_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="User ID who requested the download (for DOWNLOAD operations)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}": True},
            overview_data_type={f"{EGLOBAL_DATA_TYPE.IS_SELECT.value}": True, f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_OPTIONAL.value}": True},
            extra_metas={}
        )
    )

    validation_request_type: Optional[EConfigSudoActionTypeFlag] = Field(
        default=EConfigSudoActionTypeFlag.NONE,
        description="Type of validation request",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}": f"{EConfigSudoActionTypeFlag.__name__}",
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True,
                f"{EGLOBAL_EXTRA_METAS.STATUS_COLORS.value}": StatusColorHelper.generate_status_colors(
                    EConfigSudoActionTypeFlag,
                    StatusColorHelper.create_mapping(
                        green=[EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value,],
                        orange=[EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value,],
                        blue=[EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION.value,],
                        purple=[EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION.value,],
                        teal=[EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION.value,],
                        gray=[EConfigSudoActionTypeFlag.NONE.value,],
                    )
                )
            }
        )
    )

    status: Optional[EMultipleValidationStatus] = Field(
        default=EMultipleValidationStatus.PENDING,
        description="Status of the validation request",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.ENUM_DATA_SOURCE.value}": "EMultipleValidationStatus",
                f"{EGLOBAL_EXTRA_METAS.DISPLAY_ON_OVERVIEW.value}": True
            }
        )
    ) 

    download_url: Optional[str] = Field(
        default=None,
        description="Generated encrypted download URL after validation approval",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            exclude_from_head=True,
        )
    )

    download_email: Optional[str] = Field(
        default=None,
        description="Email to receive Generated URL after validation approval",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            exclude_from_head=True,
        )
    )

    ops_validation_request_id : Optional[PydanticObjectId] = Field(
        default=None,
        description="ID of the parent validation request (for sudo group actions)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            exclude_from_head=True,
        )
    )

    # -------------------------------------------------------------------------
    # Per-model field translations (auto-registered into BaseDocument registry)
    # -------------------------------------------------------------------------
    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "next_validator_id": "ID prochain validateur",
            "sys_organization_id": "ID organisation",
            "endpoint_path": "Chemin du endpoint",
            "endpoint_method": "Méthode HTTP",
            "collection_name": "Nom de la collection",
            "operation_type": "Type d'opération",
            "data": "Données",
            "upsert_query": "Requête upsert",
            "target_document_id": "ID document cible",
            "cascade_children": "Enfants en cascade",
            "validation_is_completed": "Validation terminée",
            "description_str": "Description",
            "download_requested_user_id": "ID utilisateur demandeur de téléchargement",
            "validation_request_type": "Type de demande de validation",
            "status": "Statut",
            "download_url": "URL de téléchargement",
            "download_email": "Email de téléchargement",
            "ops_validation_request_id": "ID demande de validation parente",
        },
        en={
            "next_validator_id": "Next Validator ID",
            "sys_organization_id": "Organization ID",
            "endpoint_path": "Endpoint Path",
            "endpoint_method": "HTTP Method",
            "collection_name": "Collection Name",
            "operation_type": "Operation Type",
            "data": "Data",
            "upsert_query": "Upsert Query",
            "target_document_id": "Target Document ID",
            "cascade_children": "Cascade Children",
            "validation_is_completed": "Validation Completed",
            "description_str": "Description",
            "download_requested_user_id": "Download Requested User ID",
            "validation_request_type": "Validation Request Type",
            "status": "Status",
            "download_url": "Download URL",
            "download_email": "Download Email",
            "ops_validation_request_id": "Parent Validation Request ID",
        },
        ln={
            "next_validator_id": "ID ya movalideur oyo alandi",
            "sys_organization_id": "ID ya organisation",
            "endpoint_path": "Nzela ya endpoint",
            "endpoint_method": "Méthode HTTP",
            "collection_name": "Nkombo ya collection",
            "operation_type": "Lolenge ya opération",
            "data": "Ba données",
            "upsert_query": "Requête ya upsert",
            "target_document_id": "ID ya mokanda ya cible",
            "cascade_children": "Bana ya cascade",
            "validation_is_completed": "Validation esilaki",
            "description_str": "Ndimbola",
            "download_requested_user_id": "ID ya mosaleli asengaki téléchargement",
            "validation_request_type": "Lolenge ya essengo ya validation",
            "status": "Eloko ezali",
            "download_url": "URL ya téléchargement",
            "download_email": "Email ya téléchargement",
            "ops_validation_request_id": "ID ya essengo ya validation ya moboti",
        },
    )

    class Settings:
        name = f"{CollectionKey.OPS_VALIDATION_REQUEST.model_name}"
        validate_on_save = True


    async def get_formated_data(self, accept_language: str, output_data_type: FormatedOutPut = FormatedOutPut.FULL) -> Dict[str, Any]:
        """
        Format validation request data with PARALLEL fetching of related entities.

        OPTIMIZATION: Fetches organization, next validator, download requester,
        validation-request-user rows, target document and child requests in parallel
        using asyncio.gather to reduce latency.
        """
        import asyncio
        from app.modules.core.services.generic.generic_services import GenericService
        from app.modules.core.services.model.model_service import ModelService
        from app.modules.core.models.sys_organization.sys_organization_model import SysOrganizationModel
        from app.modules.core.models.sys_user.sys_user_model import SysUserModel
        from app.modules.security.models.ops_validation_request_user.ops_validation_request_user_model import OpsValidationRequestUserModel
        try:
            # Helper functions for parallel fetching
            async def fetch_organization():
                if self.sys_organization_id:
                    instance = await SysOrganizationModel.get(self.sys_organization_id)
                    if instance:
                        return await instance.get_formated_data(accept_language, FormatedOutPut.MINIMAL)
                return None

            async def fetch_next_validator():
                if self.next_validator_id:
                    instance = await SysUserModel.get(self.next_validator_id)
                    if instance:
                        return await instance.get_formated_data(accept_language, FormatedOutPut.MINIMAL)
                return None

            async def fetch_download_requested_user():
                if self.download_requested_user_id:
                    instance = await SysUserModel.get(self.download_requested_user_id)
                    if instance:
                        return await instance.get_formated_data(accept_language, FormatedOutPut.MINIMAL)
                return None

            async def fetch_target_document():
                if self.target_document_id and self.collection_name:
                    try:
                        collection_key = ModelService.get_collection_key_from_model_name(self.collection_name)
                        model_class = ModelService.get_model_class_from_collection_key(collection_key)
                        instance = await model_class.get(self.target_document_id)
                        if instance and hasattr(instance, 'get_formated_data'):
                            return await instance.get_formated_data(accept_language, FormatedOutPut.FULL)
                    except Exception:
                        pass
                return None
            
            async def fetch_child_validation_requests():
                if self.id:
                    try:
                        child_docs = await OpsValidationRequestModel.find(
                            OpsValidationRequestModel.ops_validation_request_id == self.id
                        ).to_list()
                        if child_docs:
                            results = []
                            for doc in child_docs:
                                try:
                                    formatted = await doc.get_formated_data(accept_language, FormatedOutPut.FULL)
                                    results.append(formatted)
                                except Exception:
                                    pass
                            return results
                    except Exception:
                        pass
                return []

            async def fetch_validation_request_users():
                """Fetch OpsValidationRequestUserModel rows linked to this request."""
                if self.id:
                    try:
                        user_rows = await OpsValidationRequestUserModel.find(
                            OpsValidationRequestUserModel.ops_validation_request_id == self.id
                        ).sort("+order_by").to_list()
                        formatted_rows = []
                        for row in user_rows:
                            try:
                                formatted = await row.get_formated_data(
                                    lang=accept_language,
                                    output=FormatedOutPut.FULL,
                                )
                                formatted_rows.append(formatted)
                            except Exception:
                                pass
                        return formatted_rows
                    except Exception:
                        pass
                return []

            async def fetch_permission_info():
                """
                Resolve permission metadata from the stored endpoint_path.

                Flow:
                  1. Find RbacEndpointModel by url == endpoint_path.
                  2. Find first RbacPermissionTarget where targeted_id == endpoint.id.
                  3. Return endpoint label + associated permission label / flag / description.
                """
                if not self.endpoint_path:
                    return None
                try:
                    from app.modules.core.models.rbac_endpoint.rbac_endpoint_model import RbacEndpointModel
                    from app.modules.core.models.rbac_permission_target.rbac_permission_target_model import RbacPermissionTargetModel
                    from app.modules.core.models.rbac_permission.rbac_permission_model import RbacPermissionModel

                    endpoint = await RbacEndpointModel.find_one(
                        RbacEndpointModel.url == self.endpoint_path
                    )
                    if not endpoint:
                        return {
                            "endpoint_label": None,
                            "endpoint_url": self.endpoint_path,
                            "endpoint_method": self.endpoint_method,
                        }

                    info: dict = {
                        "endpoint_id": str(endpoint.id),
                        "endpoint_label": str(getattr(endpoint, "label", "") or ""),
                        "endpoint_url": str(getattr(endpoint, "url", None) or self.endpoint_path),
                        "endpoint_method": str(self.endpoint_method or ""),
                    }

                    perm_target = await RbacPermissionTargetModel.find_one(
                        RbacPermissionTargetModel.targeted_id == endpoint.id
                    )
                    if perm_target and getattr(perm_target, "rbac_permission_id", None):
                        perm = await RbacPermissionModel.get(perm_target.rbac_permission_id)
                        if perm:
                            info["permission_id"] = str(perm.id)
                            info["permission_label"] = str(getattr(perm, "label", "") or "")
                            info["permission_flag"] = str(getattr(perm, "flag", "") or "")
                            info["permission_description"] = str(getattr(perm, "description_str", "") or "")

                    return info
                except Exception:
                    return None

            # ⚡ PARALLEL FETCH: All related entities fetched simultaneously
            (
                sys_organization,
                next_validator,
                download_requested_user,
                target_document_info,
                child_validation_requests,
                validation_request_users,
                permission_info,
            ) = await asyncio.gather(
                fetch_organization(),
                fetch_next_validator(),
                fetch_download_requested_user(),
                fetch_target_document(),
                fetch_child_validation_requests(),
                fetch_validation_request_users(),
                fetch_permission_info(),
                return_exceptions=True  # Don't let one failure break others
            )

            # Handle any exceptions from gather
            if isinstance(sys_organization, Exception):
                sys_organization = None
            if isinstance(next_validator, Exception):
                next_validator = None
            if isinstance(download_requested_user, Exception):
                download_requested_user = None
            if isinstance(target_document_info, Exception):
                target_document_info = None
            if isinstance(child_validation_requests, Exception):
                child_validation_requests = []
            if isinstance(validation_request_users, Exception):
                validation_request_users = []
            if isinstance(permission_info, Exception):
                permission_info = None

            # Translate enum statuses
            operation_type_lbl = self.handle_translation_status(self.operation_type, EMultipleValidationType, accept_language)
            status_lbl = self.handle_translation_status(self.status, EMultipleValidationStatus, accept_language)
            status_color = StatusColorHelper.get_status_color(self.status)
            validation_request_type_lbl = self.handle_translation_status(self.validation_request_type, EConfigSudoActionTypeFlag, accept_language)
            validation_request_type_color = StatusColorHelper.get_status_color(self.validation_request_type)

            ops_validation_request = {
                "id": str(self.id),
                "identifier": self.identifier,
                "endpoint_path": self.endpoint_path,
                "endpoint_method": self.endpoint_method,
                "collection_name": self.collection_name,

                "operation_type": self.operation_type.value if hasattr(self.operation_type, 'value') else self.operation_type,
                "operation_type_lbl": operation_type_lbl,

                "status": self.status.value if hasattr(self.status, 'value') else self.status,
                "status_lbl": status_lbl,
                "status_color": status_color,

                "validation_request_type": self.validation_request_type.value if hasattr(self.validation_request_type, 'value') else self.validation_request_type,
                "validation_request_type_lbl": validation_request_type_lbl,
                "validation_request_type_color": validation_request_type_color,

                "validation_is_completed": self.validation_is_completed,
                "description_str": self.description_str,

                "data": self.data,
                "upsert_query": self.upsert_query,
                "target_document_id": str(self.target_document_id) if self.target_document_id else None,
                "target_document_info": target_document_info,

                "cascade_children": [child.model_dump(by_alias=True) for child in self.cascade_children] if self.cascade_children else [],

                "next_validator": next_validator,
                "sys_organization": sys_organization,
                "download_requested_user": download_requested_user,
                "download_url": self.download_url,
                "download_email": self.download_email,
                "ops_validation_request_id": str(self.ops_validation_request_id) if self.ops_validation_request_id else None,

                # Fetched from OpsValidationRequestUserModel collection
                "validation_request_users": validation_request_users,

                # Recursive linkage source.
                "child_validation_requests": child_validation_requests,

                # Permission / endpoint metadata resolved from endpoint_path.
                # Includes endpoint_label, permission_label, permission_flag,
                # permission_description for display in validators' UIs.
                "permission_info": permission_info,

                "created_at": self.created_at.isoformat() if hasattr(self, 'created_at') and self.created_at else None,
                "updated_at": self.updated_at.isoformat() if hasattr(self, 'updated_at') and self.updated_at else None,
            }

            return ops_validation_request

        except Exception as e:
            print(f"Error in OpsValidationRequestModel.get_formated_data: {e}")
            ops_validation_request = {
                "id": str(self.id),
                "identifier": self.identifier,
                "endpoint_path": self.endpoint_path,
                "endpoint_method": self.endpoint_method,
                "collection_name": self.collection_name,
                "operation_type": self.operation_type.value if hasattr(self.operation_type, 'value') else self.operation_type,
                "status": self.status.value if hasattr(self.status, 'value') else self.status,
                "validation_request_type": self.validation_request_type.value if hasattr(self.validation_request_type, 'value') else self.validation_request_type,
                "validation_is_completed": self.validation_is_completed,
                "description_str": self.description_str,
                "target_document_id": str(self.target_document_id) if self.target_document_id else None,
                "download_url": self.download_url,
                "download_email": self.download_email,
                "ops_validation_request_id": str(self.ops_validation_request_id) if self.ops_validation_request_id else None,
            }
            return ops_validation_request
        
    
