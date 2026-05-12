

from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field, field_validator, validator
import enum
 
class CurrencyExchangeSetupScope(str, enum.Enum):
  SYSTEM="system"
  ORGANIZATION = "organization"
  ENTITY = "entity"
 
class ESaasConfigPurpose(str, enum.Enum):
  CUSTOMER_SUPPORT="customer_support"
  VENDOR_SUPPORT = "vendor_support"
  CONTACT_SALE = "contact_sale"
  GLOBAL = "global"
 
class ESaasConfigInfoKind(str, enum.Enum):
  EMAIL_ADDRESS="email_address"
  PHONE_NUMBER = "phone_number"
  ADDRESS = "address"

class SaasConfigContactInfo(BaseModel):
    id: str = Field(
        default_factory=lambda: str(ObjectId()),
        description="Unique identifier for contact info"
    )
    contact_info: str
    is_activated: bool
    purpose: ESaasConfigPurpose
    info_kind: ESaasConfigInfoKind
    ref_entity_id: Optional[str]

    @field_validator("purpose", mode="before")
    def convert_purpose_to_enum(cls, value):
        if isinstance(value, str):
            return ESaasConfigPurpose(value).value  # Convert string back to enum
        return value

    @field_validator("info_kind", mode="before")
    def convert_info_kind_to_enum(cls, value):
        if isinstance(value, str):
            return ESaasConfigInfoKind(value).value  # Convert string back to enum
        return value
       