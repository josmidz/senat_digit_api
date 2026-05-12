"""Agenda request/response schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class AgendaItemCreateRequest(BaseModel):
    session_id: str = Field(..., min_length=12)
    title: str = Field(..., min_length=3, max_length=300)
    description_str: Optional[str] = Field(None, max_length=4000)
    order_index: int = Field(..., ge=0, le=10000)
    linked_document_ids: List[str] = Field(default_factory=list)


class AgendaItemPatchRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=300)
    description_str: Optional[str] = Field(None, max_length=4000)
    order_index: Optional[int] = Field(None, ge=0, le=10000)
    linked_document_ids: Optional[List[str]] = None


class _ReorderEntry(BaseModel):
    id: str = Field(..., min_length=12)
    order_index: int = Field(..., ge=0, le=10000)


class AgendaReorderRequest(BaseModel):
    session_id: str = Field(..., min_length=12)
    items: List[_ReorderEntry] = Field(..., min_length=1)

    @field_validator("items")
    def _unique_ids(cls, v: List[_ReorderEntry]) -> List[_ReorderEntry]:
        ids = [e.id for e in v]
        if len(set(ids)) != len(ids):
            raise ValueError("items contient des id en double")
        return v


class AgendaActivateRequest(BaseModel):
    """Activate one item — service deactivates the rest of the session's items in the same call."""
    item_id: str = Field(..., min_length=12)


class AgendaPublishRequest(BaseModel):
    """Publish (or unpublish) the entire agenda for a session."""
    session_id: str = Field(..., min_length=12)
    is_published: bool = True
