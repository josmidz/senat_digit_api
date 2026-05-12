"""Per-user PIN (4-6 digit) for sensitive-action confirmation.

Stored as an Argon2 hash (via `PasswordService`). The PIN is a
secondary factor — it is **never** a replacement for the user's
password (which protects the account) or MFA (which protects the
device pairing). PIN gates flows like:

  - Confirm a vote cast (PPTX scope: "second factor before scrutin")
  - Confirm a signature (présence / amendement)
  - Confirm sensitive admin ops (revoke device, lock user)

Lockout policy: after `_LOCKOUT_THRESHOLD` failed attempts, the
record's `locked_until` is set to `now + _LOCKOUT_DURATION` and any
verify within that window raises. The fail counter resets on a
successful verify or admin override.

One row per (`sys_user_id`). Devices share the same PIN — the PIN
proves "the user authorised this action", not "this device is
trusted" (that's `cfg_user_device.status`).
"""

import uuid
from datetime import datetime
from typing import Annotated, Optional

from beanie import Indexed, PydanticObjectId
from pydantic import Field

from app.modules.core.enums.type_enum import (
    EGLOBAL_DATA_TYPE,
    EGLOBAL_DATA_TYPE_CONSTRAINTS,
    EGLOBAL_EXTRA_METAS,
)
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.core.utils.model.field_translation_helper import (
    FieldTranslationHelper,
)


class CfgUserPinModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
    )
    identifier: str = Field(
        default_factory=lambda: f"{uuid.uuid4().hex[:8]}",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            extra_metas={f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}": True},
        ),
    )

    sys_user_id: Annotated[
        PydanticObjectId,
        Indexed(name="cfg_user_pin_user_unique", unique=True),
        Field(
            ...,
            description="One PIN per user (unique index).",
        ),
    ]

    # Argon2 hash. Never returned to the client; never logged.
    pin_hash: str = Field(
        ...,
        min_length=10,
        max_length=200,
        description="Argon2 hash of the user's PIN (4-6 digits).",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,
            },
            extra_metas={
                f"{EGLOBAL_EXTRA_METAS.SKIP_ON_VIEW.value}": True,
            },
        ),
    )

    # Failed-verify counter. Reset on success.
    fail_attempt_count: int = Field(
        default=0,
        ge=0,
        description="Consecutive failed verify attempts.",
    )

    # When set + in the future, all verify attempts raise.
    locked_until: Optional[datetime] = Field(
        default=None,
        description="If non-null and in the future, verify is blocked.",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={
                f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True,
                f"{EGLOBAL_DATA_TYPE_CONSTRAINTS.IS_NULLABLE.value}": True,
            },
        ),
    )

    # Audit metadata — when the PIN was set and last verified.
    pin_set_at: Optional[datetime] = Field(default=None)
    last_verified_at: Optional[datetime] = Field(default=None)

    FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
        fr={
            "sys_user_id": "Utilisateur",
            "pin_hash": "Hash du PIN",
            "fail_attempt_count": "Tentatives échouées",
            "locked_until": "Verrouillé jusqu'à",
            "pin_set_at": "Défini le",
            "last_verified_at": "Dernière vérification",
        },
        en={
            "sys_user_id": "User",
            "pin_hash": "PIN hash",
            "fail_attempt_count": "Failed attempts",
            "locked_until": "Locked until",
            "pin_set_at": "Set at",
            "last_verified_at": "Last verified at",
        },
        ln={
            "sys_user_id": "Mosaleli",
            "pin_hash": "Hash ya PIN",
            "fail_attempt_count": "Mbala ya kokweya",
            "locked_until": "Ekangamí kino",
            "pin_set_at": "Etiyamí na",
            "last_verified_at": "Eyebanaki na",
        },
    )

    class Settings:
        name = CollectionKey.CFG_USER_PIN.model_name
        validate_on_save = True
