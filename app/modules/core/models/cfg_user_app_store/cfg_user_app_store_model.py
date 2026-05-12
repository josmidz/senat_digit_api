"""Persistent per-user cache of the aggregated application list.

Backs ``/data/get-applications``. Two row shapes:

  - **Dynamic**: keyed by ``(sys_user_id, ref_api_consumer_id, endpoint_flag,
    application_group_flag, accept_language, output_data_type, all_data_flag)``.
    One row per user — used for admin/agent profiles where the RBAC tree
    differs per tenant.
  - **Static**: ``sys_user_id is None``, keyed by ``rbac_profile_flag``
    instead. One row shared by every user with that profile — used for
    visitor / customer profiles where the menu set is identical.

Ported from bloonio_apps_api. See ``user_app_store_service.py`` for the
read/write API and ``user_app_store_guard.py`` for the bulk-op guard.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from pydantic import Field
import pymongo

from app.modules.core.enums.type_enum import (
    EGLOBAL_DATA_TYPE,
    EGLOBAL_EXTRA_METAS,
)
from app.modules.core.enums.user_app_store_enum import (
    EUserAppStoreEndpointFlag,
    EUserAppStoreProfileTypeFlag,
)
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import FieldTranslationHelper


class CfgUserAppStoreModel(BaseDocument):
    """Per-user (dynamic) or per-profile (static) cache of /data/get-applications."""

    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.EXCLUDED_FIELDS.value}": "id",
            },
        ),
    )

    sys_user_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Owning user. None for static (shared) rows.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    ref_api_consumer_id: PydanticObjectId = Field(
        ...,
        description="API consumer this cache row belongs to.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    rbac_profile_id: Optional[PydanticObjectId] = Field(
        default=None,
        description="Profile the cached app list was computed for.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    rbac_profile_flag: Optional[str] = Field(
        default=None,
        description="Profile flag for fast static-row lookup.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    profile_type_flag: EUserAppStoreProfileTypeFlag = Field(
        ...,
        description="Static (shared across users) or dynamic (cloned per user).",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
        ),
    )

    endpoint_flag: EUserAppStoreEndpointFlag = Field(
        ...,
        description="Which application-fetch endpoint this row caches.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}": True},
        ),
    )

    application_group_flag: Optional[str] = Field(
        default=None,
        description="Application group filter used for this cached payload.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    accept_language: Optional[str] = Field(
        default=None,
        description="Language this cached payload was formatted for.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    output_data_type: Optional[str] = Field(
        default="default",
        description=(
            "Formatter variant the payload was built with "
            "('default', 'data_table', 'tree'). Matches OutputDataType.value."
        ),
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    all_data_flag: Optional[bool] = Field(
        default=False,
        description=(
            "Whether the cached payload was built with ?all_data=true. "
            "Paginated (False) and unpaginated (True) entries kept separate."
        ),
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
        ),
    )

    app_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cached response payload of the application-fetch endpoint.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_LONG_STRING.value}": True},
        ),
    )

    data_version: Optional[str] = Field(
        default=None,
        description="Hash of the source data used to detect staleness.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    last_built_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this cache row was last rebuilt.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True},
        ),
    )

    is_stale: bool = Field(
        default=False,
        description="Marks the row for refresh on next read.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
        ),
    )

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "sys_user_id": "Utilisateur",
            "ref_api_consumer_id": "Consommateur d'API",
            "rbac_profile_id": "Profil",
            "rbac_profile_flag": "Flag du profil",
            "profile_type_flag": "Type de profil",
            "endpoint_flag": "Endpoint",
            "application_group_flag": "Groupe d'applications",
            "accept_language": "Langue",
            "app_data": "Donnees applications",
            "data_version": "Version des donnees",
            "last_built_at": "Dernier rafraichissement",
            "is_stale": "Perime",
        },
        en={
            "sys_user_id": "User",
            "ref_api_consumer_id": "API consumer",
            "rbac_profile_id": "Profile",
            "rbac_profile_flag": "Profile flag",
            "profile_type_flag": "Profile type",
            "endpoint_flag": "Endpoint",
            "application_group_flag": "Application group",
            "accept_language": "Language",
            "app_data": "Applications payload",
            "data_version": "Data version",
            "last_built_at": "Last built at",
            "is_stale": "Stale",
        },
        ln={
            "sys_user_id": "Mosaleli",
            "ref_api_consumer_id": "API consumer",
            "rbac_profile_id": "Profil",
            "rbac_profile_flag": "Flag ya profil",
            "profile_type_flag": "Lolenge ya profil",
            "endpoint_flag": "Endpoint",
            "application_group_flag": "Etuluku ya ba applications",
            "accept_language": "Monoko",
            "app_data": "Ba applications",
            "data_version": "Version",
            "last_built_at": "Mbala ya suka",
            "is_stale": "Ya kala",
        },
    )

    class Settings:
        name = f"{CollectionKey.CFG_USER_APP_STORE.model_name}"
        validate_on_save = True
        indexes = [
            # Fast lookup for dynamic (per-user) rows.
            pymongo.IndexModel(
                [
                    ("sys_user_id", pymongo.ASCENDING),
                    ("ref_api_consumer_id", pymongo.ASCENDING),
                    ("endpoint_flag", pymongo.ASCENDING),
                    ("application_group_flag", pymongo.ASCENDING),
                    ("accept_language", pymongo.ASCENDING),
                    ("output_data_type", pymongo.ASCENDING),
                    ("all_data_flag", pymongo.ASCENDING),
                ],
                name="uas_dynamic_lookup_idx",
            ),
            # Fast lookup for static (per-profile-flag) rows.
            pymongo.IndexModel(
                [
                    ("rbac_profile_flag", pymongo.ASCENDING),
                    ("ref_api_consumer_id", pymongo.ASCENDING),
                    ("endpoint_flag", pymongo.ASCENDING),
                    ("application_group_flag", pymongo.ASCENDING),
                    ("accept_language", pymongo.ASCENDING),
                    ("output_data_type", pymongo.ASCENDING),
                    ("all_data_flag", pymongo.ASCENDING),
                ],
                name="uas_static_lookup_idx",
            ),
            # Bulk-invalidate by user — used by mark_user_stale on RBAC change.
            pymongo.IndexModel(
                [("sys_user_id", pymongo.ASCENDING)],
                name="uas_user_invalidate_idx",
            ),
        ]
