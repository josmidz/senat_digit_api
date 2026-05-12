from bson import ObjectId
from typing import Any
from pydantic.errors import PydanticUserError

class ObjectIdFormatError(PydanticUserError):
    code = 'objectid.invalid_format'
    msg_template = 'Field {}: Invalid ObjectId format: {}'
    def __init__(self, field: str, wrong_value: Any) -> None:
        super().__init__(field, wrong_value, code=self.code)

class ObjectIdTypeError(PydanticUserError):
    code = 'objectid.invalid_type'
    msg_template = 'Field {}: Expected ObjectId or string, got {}'
    def __init__(self, field: str, wrong_type: str) -> None:
        super().__init__(field, wrong_type, code=self.code)

class CustomPydanticObjectId(ObjectId):
    """
    Custom ObjectId type for Pydantic with JSON Schema support.
    """
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: Any, handler: Any) -> dict:
        return {"type": "string", "pattern": "^[0-9a-fA-F]{24}$"}

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: Any, info: Any) -> "CustomPydanticObjectId":
        # Retrieve field name dynamically (defaulting to 'value' if not provided)
        field = getattr(info, 'field_name', 'value')
        if isinstance(value, ObjectId):
            return cls(value)
        if isinstance(value, str):
            try:
                return cls(ObjectId(value))
            except Exception:
                raise ObjectIdFormatError(field, value)
        raise ObjectIdTypeError(field, type(value).__name__)

    def __str__(self) -> str:
        return super().__str__()
