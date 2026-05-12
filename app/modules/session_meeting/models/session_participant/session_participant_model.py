"""SessionParticipantModel — links a sys_user to a séance with role + voting rights."""

import uuid
from typing import Annotated, Any, Dict, Optional

from beanie import Indexed, PydanticObjectId
from pydantic import Field

from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, FormatedOutPut
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.utils.model.base_document import BaseDocument
from app.modules.core.utils.model.field_decorator import translation_meta
from app.modules.session_meeting.enums.session_enum import ESessionParticipantRole


class SessionParticipantModel(BaseDocument):
    id: Optional[PydanticObjectId] = Field(
        default_factory=PydanticObjectId,
        alias="_id",
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

    session_meeting_id: Annotated[
        PydanticObjectId,
        Indexed(name="session_participant_session_index"),
        Field(
            ...,
            json_schema_extra=translation_meta(
                may_have_translation=False,
                to_be_translated_in_front=False,
                data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            ),
        ),
    ]

    sys_user_id: Annotated[
        PydanticObjectId,
        Indexed(name="session_participant_user_index"),
        Field(
            ...,
            json_schema_extra=translation_meta(
                may_have_translation=False,
                to_be_translated_in_front=False,
                data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            ),
        ),
    ]

    sys_organization_id: Annotated[
        PydanticObjectId,
        Indexed(name="session_participant_org_index"),
        Field(
            ...,
            description="Mirrors session.sys_organization_id for direct RLS scoping",
            json_schema_extra=translation_meta(
                may_have_translation=False,
                to_be_translated_in_front=False,
                data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
            ),
        ),
    ]

    role: ESessionParticipantRole = Field(
        ...,
        description="SENATEUR | GREFFIER | INVITE",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
        ),
    )

    can_vote: bool = Field(
        default=True,
        description="False for INVITE (observers/experts) and any role explicitly "
        "stripped of voting rights for this séance",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True},
        ),
    )

    async def get_formated_data(
        self,
        accept_language: str = "fr",
        output: FormatedOutPut = FormatedOutPut.MINIMAL,
    ) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "identifier": self.identifier,
            "session_meeting_id": str(self.session_meeting_id),
            "sys_user_id": str(self.sys_user_id),
            "sys_organization_id": str(self.sys_organization_id),
            "role": self.role.value,
            "can_vote": self.can_vote,
        }

    class Settings:
        name = CollectionKey.SESSION_PARTICIPANT.model_name
        validate_on_save = True
