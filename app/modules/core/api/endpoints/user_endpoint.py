
#app/api/v1/endpoints/user.py
from typing import Optional
from app.modules.core.api.controller.user_controller import UserController
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.schemas.user_schema import (
    UserConfigPayload, 
    UserConfigsPayload,
)
from fastapi import APIRouter, Body, Query, Request
from fastapi import APIRouter
from app.modules.auth.schemas.auth_schema import NewPasswordResetRequest
from app.modules.core.enums.type_enum import OutputDataType


router = APIRouter()



