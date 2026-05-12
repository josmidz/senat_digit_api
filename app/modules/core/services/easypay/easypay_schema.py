from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EasypayBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class EasypayAuthData(EasypayBaseModel):
    token: str = Field(..., min_length=1)


class EasypayCollectionRequest(EasypayBaseModel):
    reference_id: str = Field(..., alias="referenceId", min_length=1)
    phone: str = Field(..., min_length=1)
    currency: str = Field(..., min_length=3, max_length=3)
    amount: float = Field(..., gt=0)

    @field_validator("reference_id", "phone", mode="before")
    @classmethod
    def strip_required_string(cls, value: Any) -> str:
        value = str(value or "").strip()
        if not value:
            raise ValueError("value is required")
        return value

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: Any) -> str:
        return str(value or "").strip().upper()


class EasypayStatusRequest(EasypayBaseModel):
    reference_id: str = Field(..., alias="referenceId", min_length=1)

    @field_validator("reference_id", mode="before")
    @classmethod
    def strip_reference_id(cls, value: Any) -> str:
        value = str(value or "").strip()
        if not value:
            raise ValueError("referenceId is required")
        return value


class EasypayErrorData(EasypayBaseModel):
    message: Optional[str] = None
    code: Optional[int] = None


class EasypayResponseEnvelope(EasypayBaseModel):
    success: Union[int, bool, str]
    data: Optional[Any] = None
    error: Optional[EasypayErrorData] = None


class EasypayCollectionData(EasypayBaseModel):
    transaction_id: Optional[str] = Field(None, alias="transactionId")
    reference_id: str = Field(..., alias="referenceId")
    status: Literal["Success", "Failed", "Pending"]
    phone: Optional[str] = None
    amount: Optional[Union[float, str]] = None
    currency: Optional[str] = None
    date: Optional[str] = None
    provider: Optional[str] = None


class EasypayStatusData(EasypayCollectionData):
    telecom_id: Optional[str] = Field(None, alias="telecomId")
    type: Optional[str] = None
    reason: Optional[str] = None


class EasypayBalanceData(EasypayBaseModel):
    local: Optional[float] = None
    usd: Optional[float] = None


class EasypayCallbackPayload(EasypayBaseModel):
    reference_id: str = Field(..., alias="referenceId", min_length=1)
    status: str = Field(..., min_length=1)
    transaction_id: Optional[str] = Field(None, alias="transactionId")
    amount: Optional[Union[float, str]] = None
    currency: Optional[str] = None
    date: Optional[str] = None
    provider: Optional[str] = None
    errormsg: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.status.lower() == "success"

    @property
    def is_failed(self) -> bool:
        return self.status.lower() == "failed"
