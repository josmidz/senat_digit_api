"""Document request/response schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.modules.document.enums.document_enum import EAmendmentStatus, EDocumentTypology


class DocumentCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    description_str: Optional[str] = Field(None, max_length=4000)
    typology: EDocumentTypology
    arch_file_id: Optional[str] = Field(None, min_length=12)
    linked_session_id: Optional[str] = Field(None, min_length=12)
    linked_agenda_item_ids: List[str] = Field(default_factory=list)
    linked_resolution_ids: List[str] = Field(default_factory=list)


class DocumentPatchRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=300)
    description_str: Optional[str] = Field(None, max_length=4000)
    arch_file_id: Optional[str] = Field(None, min_length=12)
    linked_session_id: Optional[str] = Field(None, min_length=12)
    linked_agenda_item_ids: Optional[List[str]] = None
    linked_resolution_ids: Optional[List[str]] = None


class DocumentPublishRequest(BaseModel):
    document_id: str = Field(..., min_length=12)
    is_published: bool = True


class DocumentVersionCreateRequest(BaseModel):
    """Create a new version of an existing document.

    The new version inherits `version_chain_id`, `typology`, links — and
    bumps `current_version_number` by 1.
    """
    parent_document_id: str = Field(..., min_length=12)
    title: str = Field(..., min_length=3, max_length=300)
    description_str: Optional[str] = Field(None, max_length=4000)
    arch_file_id: Optional[str] = Field(None, min_length=12)
    change_summary: Optional[str] = Field(None, max_length=2000)


class DocumentAmendmentCreateRequest(BaseModel):
    base_document_id: str = Field(..., min_length=12)
    title: str = Field(..., min_length=3, max_length=300)
    proposal_text: str = Field(..., min_length=10, max_length=10000)


class DocumentAmendmentValidateRequest(BaseModel):
    amendment_id: str = Field(..., min_length=12)
    decision: EAmendmentStatus  # VALIDE | REJETE
    reason: Optional[str] = Field(None, max_length=2000)


class SignedBlobUrlResponse(BaseModel):
    document_id: str
    arch_file_id: str
    signed_url: str
    expires_at: str
