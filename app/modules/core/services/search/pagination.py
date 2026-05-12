from typing import List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginationResponse(BaseModel):
    """
    Standard response model for paginated data.
    
    Attributes:
        data: The paginated data
        total: Total number of items (before pagination)
        skip: Number of items skipped
        limit: Maximum number of items per page
    """
    
    data: List[Dict[str, Any]] = Field(
        ...,
        description="The paginated data"
    )
    
    total: int = Field(
        ...,
        description="Total number of items (before pagination)"
    )
    
    skip: int = Field(
        ...,
        description="Number of items skipped"
    )
    
    limit: int = Field(
        ...,
        description="Maximum number of items per page"
    )