# app/schemas/response.py

from datetime import datetime
from enum import Enum
import json
import typing
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Optional


# Modify the response serialization
def serialize_enum(obj):
    if isinstance(obj, Enum):
        return obj.value  # Convert enum to its string value
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class AppResponse(BaseModel):
    success: bool
    status_code: int
    message: str
    data: Optional[Any] = None
    
class CustomJSONResponse(JSONResponse):
    def render(self, content: typing.Any) -> bytes:
        # Custom default function to handle non-serializable types
        def default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()  # Convert datetime to ISO format string
            if isinstance(obj, Enum):
                return obj.value  # Convert Enum to its value
            if hasattr(obj, "__dict__"):  # Handle objects with attributes
                return obj.__dict__
            return str(obj)  # Convert any other object to a string

        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=default_serializer  # Custom default function
        ).encode("utf-8")
