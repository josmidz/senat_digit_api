# app/schemas/access/access_schema.py

from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class AccessBase(BaseModel):
    access_name: str
    access_level: int
    access_method: str 

class AccessCreate(AccessBase):
    pass

class AccessUpdate(BaseModel):
    access_name: Optional[str] = None
    access_level: Optional[int] = None
    access_method: Optional[str] = None

class AccessResponse(AccessBase):
    id: UUID

    class Config:
        from_attributes = True


        
