from typing import Dict, List, Any, Optional, Type
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from pydantic import BaseModel
import copy

from app.modules.core.api.controller.search_controller import SearchController
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.utils.model.base_model_mixin import BaseModelMixin
from app.modules.core.services.encryption.encryption_service import EncryptionService
from app.modules.core.services.search.pagination import PaginationResponse


async def decrypt_document_fields(doc: Dict[str, Any], model_class: Type[BaseModelMixin]) -> Dict[str, Any]:
    """
    Decrypt encrypted fields in a document.

    Args:
        doc: The document to decrypt
        model_class: The model class for the document

    Returns:
        The document with decrypted fields
    """
    # Make a deep copy to avoid modifying the original document
    decrypted_doc = copy.deepcopy(doc)

    # Get encrypted fields for the model class
    encrypted_fields = []
    for field_name, field in model_class.model_fields.items():
        meta = field.json_schema_extra or {}
        can_be_encrypted = meta.get("can_be_encrypted", False)

        if can_be_encrypted:
            encrypted_fields.append(field_name)

    # Decrypt encrypted fields
    for field_name in encrypted_fields:
        if field_name in decrypted_doc and isinstance(decrypted_doc[field_name], str):
            field_value = decrypted_doc[field_name]

            # Check if the field is encrypted
            if field_value.startswith("ENC:"):
                # Extract the encrypted value
                encrypted_value = field_value[4:]

                # Decrypt the value
                try:
                    decrypted_value = EncryptionService.decrypt(encrypted_value)

                    # If decryption was successful (decrypted value is different from encrypted value)
                    if decrypted_value != encrypted_value:
                        decrypted_doc[field_name] = decrypted_value
                except Exception as e:
                    print(f"Error decrypting field {field_name}: {e}")
                    # Keep the original value if decryption fails

    return decrypted_doc

router = APIRouter()


class SearchRequest(BaseModel):
    """Search request model."""

    collection_key: str
    search_criteria: Dict[str, Any]
    skip: int = 0
    limit: int = 100
    sort: Optional[Dict[str, int]] = None



@router.post("/search", response_model=PaginationResponse)
async def search(
    request: SearchRequest = Body(...),
    accept_language: str = Query(DEFAULT_LANGUAGE, description="Language for response")
) -> PaginationResponse:
    """
    Search for documents that match the search criteria.

    This endpoint supports searching across both encrypted and non-encrypted fields.
    It uses a hybrid search strategy:
    1. Use MongoDB to filter by non-encrypted fields
    2. Fetch the filtered results and apply in-memory filtering for encrypted fields

    Example:
    ```json
    {
        "collection_key": "sysUsers",
        "search_criteria": {
            "name": {"$regex": "John"},
            "credit_card_number": "1234"  // This will search in decrypted values
        },
        "skip": 0,
        "limit": 10,
        "sort": {"created_at": -1}
    }
    ```

    Notes:
    - For encrypted fields, only exact matches and regex searches are supported
    - Performance may be impacted when searching on encrypted fields with large datasets
    - Consider using non-encrypted fields for filtering when possible
    """
    try:
        # Create search controller
        search_controller = SearchController(accept_language=accept_language)

        # Perform search
        results, total_count = await search_controller.search(
            collection_key=request.collection_key,
            search_criteria=request.search_criteria,
            skip=request.skip,
            limit=request.limit,
            sort=request.sort
        )

        # Return paginated response
        return PaginationResponse(
            data=results,
            total=total_count,
            skip=request.skip,
            limit=request.limit
        )
    except Exception as e:
        # Log the error with traceback
        print(f"Error in search endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.post("/test", response_model=Dict[str, Any])
async def test_search():
    """
    Test endpoint to verify that the search functionality is working.
    """
    try:
        # Return a simple response
        return {
            "status": "success",
            "message": "Search endpoint is working"
        }
    except Exception as e:
        # Log the error with traceback
        print(f"Error in test endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Test error: {str(e)}")


@router.post("/simple", response_model=PaginationResponse)
async def simple_search(
    collection_key: str = Body(...),
    field: str = Body(...),
    value: str = Body(...),
    skip: int = Body(0),
    limit: int = Body(10)
):
    """
    Simple search endpoint that searches for an exact match in a specific field.

    This endpoint is a simplified version of the search endpoint that doesn't rely on
    the complex search service. It's useful for testing and debugging.

    Example:
    ```json
    {
        "collection_key": "refMfas",
        "field": "flag",
        "value": "email",
        "skip": 0,
        "limit": 10
    }
    ```
    """
    try:
        # Import necessary modules
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        from app.db.base import get_collection

        # Validate collection key
        if collection_key not in COLLECTION_MODEL_MAPPING:
            raise HTTPException(status_code=400, detail=f"Invalid collection key: {collection_key}")

        # Get the model class and collection
        model_class = COLLECTION_MODEL_MAPPING[collection_key].model_class
        collection_name = getattr(model_class.Settings, "name", model_class.__name__.lower())
        collection = get_collection(collection_name)

        # Create a simple query
        query = {field: value}

        # Get total count
        total_count = await collection.count_documents(query)

        # Fetch documents
        cursor = collection.find(query).skip(skip).limit(limit)
        documents = []
        async for doc in cursor:
            documents.append(doc)

        # Format documents and decrypt encrypted fields
        formatted_documents = []
        for doc in documents:
            # Convert ObjectId to string
            if "_id" in doc:
                doc["id"] = str(doc["_id"])

            # Remove _id field
            if "_id" in doc:
                del doc["_id"]

            # Decrypt encrypted fields
            decrypted_doc = await decrypt_document_fields(doc, model_class)

            formatted_documents.append(decrypted_doc)

        # Return paginated response
        return PaginationResponse(
            data=formatted_documents,
            total=total_count,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        # Log the error with traceback
        print(f"Error in simple search endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Simple search error: {str(e)}")


@router.post("/regex", response_model=PaginationResponse)
async def regex_search(
    collection_key: str = Body(...),
    field: str = Body(...),
    pattern: str = Body(...),
    skip: int = Body(0),
    limit: int = Body(10)
):
    """
    Regex search endpoint that searches for a regex pattern in a specific field.

    This endpoint is useful for searching in non-encrypted fields.

    Example:
    ```json
    {
        "collection_key": "mfas",
        "field": "usage_description",
        "pattern": "email",
        "skip": 0,
        "limit": 10
    }
    ```
    """
    try:
        # Import necessary modules
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        from app.db.base import get_collection

        # Validate collection key
        if collection_key not in COLLECTION_MODEL_MAPPING:
            raise HTTPException(status_code=400, detail=f"Invalid collection key: {collection_key}")

        # Get the model class and collection
        model_class = COLLECTION_MODEL_MAPPING[collection_key].model_class
        collection_name = getattr(model_class.Settings, "name", model_class.__name__.lower())
        collection = get_collection(collection_name)

        # Create a regex query
        query = {field: {"$regex": pattern, "$options": "i"}}

        # Get total count
        total_count = await collection.count_documents(query)

        # Fetch documents
        cursor = collection.find(query).skip(skip).limit(limit)
        documents = []
        async for doc in cursor:
            documents.append(doc)

        # Format documents and decrypt encrypted fields
        formatted_documents = []
        for doc in documents:
            # Convert ObjectId to string
            if "_id" in doc:
                doc["id"] = str(doc["_id"])

            # Remove _id field
            if "_id" in doc:
                del doc["_id"]

            # Decrypt encrypted fields
            decrypted_doc = await decrypt_document_fields(doc, model_class)

            formatted_documents.append(decrypted_doc)

        # Return paginated response
        return PaginationResponse(
            data=formatted_documents,
            total=total_count,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        # Log the error with traceback
        print(f"Error in regex search endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Regex search error: {str(e)}")


@router.post("/encrypted-fields", response_model=List[str])
async def get_encrypted_fields(
    collection_key: str = Body(..., embed=True),
    accept_language: str = Query(DEFAULT_LANGUAGE, description="Language for response")
) -> List[str]:
    """
    Get a list of encrypted fields for a collection.

    This endpoint is useful for client applications to know which fields
    are encrypted and may require special handling in search operations.
    """
    # Create search controller
    search_controller = SearchController(accept_language=accept_language)

    # Get encrypted fields
    encrypted_fields = await search_controller.get_encrypted_fields(collection_key)

    return encrypted_fields
