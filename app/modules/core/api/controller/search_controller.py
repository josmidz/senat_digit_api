from typing import Dict, List, Any, Optional, Tuple
from fastapi import HTTPException


from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.search.search_service import SearchService


class SearchController:
    """
    Controller for search operations.
    This controller handles search operations across both encrypted and non-encrypted fields.
    It uses a hybrid search strategy:
    1. Use MongoDB to filter by non-encrypted fields
    2. Fetch the filtered results and apply in-memory filtering for encrypted fields
    """

    def __init__(self, accept_language: str = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self.search_service = SearchService(accept_language=accept_language)

    async def search(
        self,
        collection_key: str,
        search_criteria: Dict[str, Any],
        skip: int = 0,
        limit: int = 100,
        sort: Optional[Dict[str, int]] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search for documents that match the search criteria.

        Args:
            collection_key: The collection key
            search_criteria: The search criteria
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort: Sort criteria

        Returns:
            Tuple containing (matching_documents, total_count)
        """
        try:
            # Log input parameters
            print(f"Search request - collection_key: {collection_key}, criteria: {search_criteria}")

            # Validate collection key
            try:
                # Convert to lowercase for case-insensitive matching
                collection_key_lower = collection_key.lower()

                # Try to find a matching collection key
                matching_keys = [k for k in CollectionKey.__members__ if k.lower() == collection_key_lower]

                if matching_keys:
                    # Use the first matching key
                    collection_key_enum = CollectionKey[matching_keys[0]]
                    print(f"Matched collection key: {collection_key} -> {collection_key_enum}")
                else:
                    # Try direct conversion
                    collection_key_enum = CollectionKey(collection_key)
            except ValueError as ve:
                print(f"Invalid collection key: {collection_key}, error: {ve}")
                # List available keys for debugging
                available_keys = list(CollectionKey.__members__.keys())
                print(f"Available collection keys: {available_keys}")
                raise HTTPException(status_code=400, detail=f"Invalid collection key: {collection_key}. Available keys: {available_keys}")
            except Exception as e:
                print(f"Unexpected error validating collection key: {e}")
                raise HTTPException(status_code=400, detail=f"Invalid collection key: {collection_key}")

            # Perform search
            try:
                results, total_count = await self.search_service.search(
                    collection_key=collection_key_enum,
                    search_criteria=search_criteria,
                    skip=skip,
                    limit=limit,
                    sort=sort
                )

                return results, total_count
            except Exception as e:
                print(f"Error in search service: {str(e)}")
                import traceback
                traceback.print_exc()
                raise
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Log the error with traceback
            print(f"Search error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

    async def get_encrypted_fields(self, collection_key: str) -> List[str]:
        """
        Get a list of encrypted fields for a collection.

        Args:
            collection_key: The collection key

        Returns:
            List of field names that are encrypted
        """
        try:
            # Log input parameters
            print(f"Get encrypted fields request - collection_key: {collection_key}")

            # Validate collection key
            try:
                # Convert to lowercase for case-insensitive matching
                collection_key_lower = collection_key.lower()

                # Try to find a matching collection key
                matching_keys = [k for k in CollectionKey.__members__ if k.lower() == collection_key_lower]

                if matching_keys:
                    # Use the first matching key
                    collection_key_enum = CollectionKey[matching_keys[0]]
                    print(f"Matched collection key: {collection_key} -> {collection_key_enum}")
                else:
                    # Try direct conversion
                    collection_key_enum = CollectionKey(collection_key)
            except ValueError as ve:
                print(f"Invalid collection key: {collection_key}, error: {ve}")
                # List available keys for debugging
                available_keys = list(CollectionKey.__members__.keys())
                print(f"Available collection keys: {available_keys}")
                raise HTTPException(status_code=400, detail=f"Invalid collection key: {collection_key}. Available keys: {available_keys}")
            except Exception as e:
                print(f"Unexpected error validating collection key: {e}")
                raise HTTPException(status_code=400, detail=f"Invalid collection key: {collection_key}")

            # Get model class
            try:
                model_class = await self.search_service.get_model_class(collection_key_enum)
                print(f"Retrieved model class: {model_class.__name__}")

                # Get encrypted fields
                encrypted_fields = await self.search_service.get_encrypted_fields(model_class)
                print(f"Encrypted fields for {model_class.__name__}: {encrypted_fields}")

                return encrypted_fields
            except Exception as e:
                print(f"Error getting model class or encrypted fields: {str(e)}")
                import traceback
                traceback.print_exc()
                raise
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Log the error with traceback
            print(f"Error getting encrypted fields: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error getting encrypted fields: {str(e)}")
