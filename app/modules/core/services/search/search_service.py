from typing import Dict, List, Any, Optional, Type, Tuple
import re
from bson import ObjectId
from pydantic import BaseModel

from app.modules.core.utils.model.base_model_mixin import BaseModelMixin
from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
from app.db.base import get_collection
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.encryption.encryption_service import EncryptionService


class SearchService(DebugService):
    """
    Service for handling searches that may involve encrypted fields.

    This service implements a hybrid search strategy:
    1. Use MongoDB to filter by non-encrypted fields
    2. Fetch the filtered results and apply in-memory filtering for encrypted fields
    """

    def __init__(self, accept_language: str = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        super().__init__(accept_language)

    @staticmethod
    async def get_model_class(collection_key: str) -> Type[BaseModelMixin]:
        """Get the model class for a collection key."""
        if collection_key not in COLLECTION_MODEL_MAPPING:
            raise ValueError(f"Collection key '{collection_key}' not found")

        return COLLECTION_MODEL_MAPPING[collection_key].model_class

    @staticmethod
    async def get_encrypted_fields(model_class: Type[BaseModelMixin]) -> List[str]:
        """Get a list of field names that have can_be_encrypted=True."""
        encrypted_fields = []

        for field_name, field in model_class.model_fields.items():
            meta = field.json_schema_extra or {}
            can_be_encrypted = meta.get("can_be_encrypted", False)

            if can_be_encrypted:
                encrypted_fields.append(field_name)

        return encrypted_fields

    @staticmethod
    async def split_search_criteria(
        search_criteria: Dict[str, Any],
        encrypted_fields: List[str]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Split search criteria into database query and in-memory filter.

        Args:
            search_criteria: The search criteria
            encrypted_fields: List of field names that are encrypted

        Returns:
            Tuple containing (database_query, memory_filter)
        """
        database_query = {}
        memory_filter = {}

        for key, value in search_criteria.items():
            # Check if this is a field or a query operator
            if key.startswith("$"):
                # Handle logical operators ($and, $or, etc.)
                if key in ["$and", "$or"]:
                    db_list = []
                    mem_list = []

                    for item in value:
                        db_item, mem_item = await SearchService.split_search_criteria(item, encrypted_fields)
                        if db_item:
                            db_list.append(db_item)
                        if mem_item:
                            mem_list.append(mem_item)

                    if db_list:
                        database_query[key] = db_list
                    if mem_list:
                        memory_filter[key] = mem_list
                else:
                    # Other operators go to database query
                    database_query[key] = value
            else:
                # Check if this is a field with operators
                if isinstance(value, dict) and any(k.startswith("$") for k in value.keys()):
                    # Field with operators
                    field_name = key

                    # Check if this is an encrypted field
                    if field_name in encrypted_fields:
                        memory_filter[field_name] = value
                    else:
                        database_query[field_name] = value
                else:
                    # Simple field=value query
                    field_name = key

                    # Check if this is an encrypted field
                    if field_name in encrypted_fields:
                        memory_filter[field_name] = value
                    else:
                        database_query[field_name] = value

        return database_query, memory_filter

    @staticmethod
    async def apply_memory_filter(
        documents: List[Dict[str, Any]],
        memory_filter: Dict[str, Any],
        model_class: Type[BaseModelMixin]
    ) -> List[Dict[str, Any]]:
        """
        Apply in-memory filtering for encrypted fields.

        Args:
            documents: List of documents to filter
            memory_filter: Filter criteria for in-memory filtering
            model_class: The model class for decrypting fields

        Returns:
            Filtered list of documents
        """
        if not memory_filter:
            return documents

        # Get encrypted fields for the model class
        encrypted_fields = await SearchService.get_encrypted_fields(model_class)
        print(f"Encrypted fields for {model_class.__name__}: {encrypted_fields}")

        filtered_documents = []

        for doc in documents:
            # Create a model instance for decryption
            model_instance = model_class(**doc)

            # Check if the document matches all filter criteria
            if await SearchService._matches_filter(model_instance, memory_filter, encrypted_fields):
                filtered_documents.append(doc)

        return filtered_documents

    @staticmethod
    async def _matches_filter(
        model_instance: BaseModelMixin,
        filter_criteria: Dict[str, Any],
        encrypted_fields: List[str] = None
    ) -> bool:
        """
        Check if a model instance matches the filter criteria.

        Args:
            model_instance: The model instance to check
            filter_criteria: The filter criteria

        Returns:
            True if the model instance matches the filter criteria, False otherwise
        """
        for key, value in filter_criteria.items():
            if key == "$and":
                # All conditions must match
                for condition in value:
                    if not await SearchService._matches_filter(model_instance, condition, encrypted_fields):
                        return False
                return True
            elif key == "$or":
                # At least one condition must match
                for condition in value:
                    if await SearchService._matches_filter(model_instance, condition, encrypted_fields):
                        return True
                return False
            else:
                # Regular field condition
                field_name = key

                # Get the field value (decrypt if needed)
                field_value = getattr(model_instance, field_name, None)

                # Check if this is an encrypted field
                if field_name in encrypted_fields and isinstance(field_value, str):
                    # Handle encrypted field
                    if field_value.startswith("ENC:") or field_value.startswith("enc:"):
                        # Extract the encrypted value
                        if field_value.startswith("ENC:v1:") or field_value.startswith("enc:v1:"):
                            # Format: ENC:v1:encrypted_value
                            encrypted_value = field_value[7:]  # Remove "ENC:v1:" prefix
                            version_prefix = "v1:"
                        else:
                            # Format: ENC:encrypted_value
                            encrypted_value = field_value[4:]  # Remove "ENC:" prefix
                            version_prefix = ""

                        # Directly use the encryption service to decrypt
                        try:
                            decrypted_value = EncryptionService.decrypt(f"{version_prefix}{encrypted_value}")
                            field_value = decrypted_value
                            # Debug output
                            print(f"Decrypted field {field_name}: {field_value}")
                        except Exception as e:
                            print(f"Error decrypting field {field_name}: {e}")
                            # Keep the original value if decryption fails
                    elif field_value.startswith("v1:"):
                        # Format: v1:encrypted_value (missing ENC: prefix)
                        try:
                            decrypted_value = EncryptionService.decrypt(field_value)
                            field_value = decrypted_value
                            # Debug output
                            print(f"Decrypted field {field_name} (v1 format): {field_value}")
                        except Exception as e:
                            print(f"Error decrypting field {field_name} (v1 format): {e}")
                            # Keep the original value if decryption fails
                    elif field_value.startswith("gAAAAAB"):
                        # Format: gAAAAAB... (Fernet token without prefix)
                        try:
                            decrypted_value = EncryptionService.decrypt(field_value)
                            field_value = decrypted_value
                            # Debug output
                            print(f"Decrypted field {field_name} (Fernet token): {field_value}")
                        except Exception as e:
                            print(f"Error decrypting field {field_name} (Fernet token): {e}")
                            # Keep the original value if decryption fails
                    else:
                        # Not encrypted, use as is
                        print(f"Field {field_name} is not encrypted: {field_value}")
                else:
                    # Regular field
                    print(f"Regular field {field_name}: {field_value}")

                # Apply the filter
                if isinstance(value, dict):
                    # Operator-based filter
                    for op, op_value in value.items():
                        result = SearchService._apply_operator(field_value, op, op_value)
                        # Debug output
                        print(f"Operator {op} with value {op_value} on field {field_name} = {result}")
                        if not result:
                            return False
                else:
                    # Simple equality filter
                    result = (field_value == value)
                    # Debug output
                    print(f"Equality check {field_name} == {value} = {result}")
                    if not result:
                        return False

        return True

    @staticmethod
    def _apply_operator(field_value: Any, operator: str, value: Any) -> bool:
        """
        Apply a filter operator to a field value.

        Args:
            field_value: The field value
            operator: The operator (e.g., $eq, $gt, $lt, $regex)
            value: The value to compare against

        Returns:
            True if the field value matches the operator condition, False otherwise
        """
        # Special case for encrypted values that couldn't be decrypted
        if isinstance(field_value, str) and (field_value.startswith("ENC:") or field_value.startswith("enc:") or field_value.startswith("v1:") or field_value.startswith("gAAAAAB")):
            # For encrypted values, we can only do basic string matching
            if operator == "$eq":
                # Can't do exact matching on encrypted values
                return False
            elif operator == "$ne":
                # Always true for not equals, since we can't know the actual value
                return True
            elif operator in ["$gt", "$gte", "$lt", "$lte"]:
                # Can't do comparison on encrypted values
                return False
            elif operator == "$in":
                # Can't do list membership on encrypted values
                return False
            elif operator == "$nin":
                # Always true for not in, since we can't know the actual value
                return True
            elif operator == "$regex":
                # For regex, we'll always return false since we can't search encrypted content
                return False
            elif operator == "$options":
                # This is used with $regex, ignore
                return True
            else:
                # Unsupported operator
                return False

        # Normal case for decrypted or unencrypted values
        if operator == "$eq":
            return field_value == value
        elif operator == "$ne":
            return field_value != value
        elif operator == "$gt":
            return field_value > value
        elif operator == "$gte":
            return field_value >= value
        elif operator == "$lt":
            return field_value < value
        elif operator == "$lte":
            return field_value <= value
        elif operator == "$in":
            return field_value in value
        elif operator == "$nin":
            return field_value not in value
        elif operator == "$regex":
            if not isinstance(field_value, str):
                return False

            # Case-insensitive search if the value is a string
            try:
                if isinstance(value, str):
                    pattern = re.compile(value, re.IGNORECASE)
                else:
                    pattern = re.compile(value)
                return bool(pattern.search(field_value))
            except Exception as e:
                print(f"Error applying regex: {e}")
                return False
        elif operator == "$options":
            # This is used with $regex, ignore
            return True
        else:
            # Unsupported operator
            return False

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
            print(f"Search service - collection_key: {collection_key}, criteria: {search_criteria}")

            # Get the model class and collection
            try:
                model_class = await self.get_model_class(collection_key)
                print(f"Retrieved model class: {model_class.__name__}")

                collection_name = getattr(model_class.Settings, "name", model_class.__name__.lower())
                print(f"Collection name: {collection_name}")

                collection = get_collection(collection_name)
                print(f"Retrieved collection: {collection}")
            except Exception as e:
                print(f"Error getting model class or collection: {e}")
                import traceback
                traceback.print_exc()
                raise

            # Get encrypted fields
            try:
                encrypted_fields = await self.get_encrypted_fields(model_class)
                print(f"Encrypted fields: {encrypted_fields}")
            except Exception as e:
                print(f"Error getting encrypted fields: {e}")
                import traceback
                traceback.print_exc()
                raise

            # Split search criteria
            try:
                database_query, memory_filter = await self.split_search_criteria(search_criteria, encrypted_fields)
                print(f"Database query: {database_query}")
                print(f"Memory filter: {memory_filter}")
            except Exception as e:
                print(f"Error splitting search criteria: {e}")
                import traceback
                traceback.print_exc()
                raise

            # If we have memory filters, we need to fetch more documents
            # to ensure we have enough after in-memory filtering
            fetch_limit = limit * 10 if memory_filter else limit

            # Apply database query
            try:
                cursor = collection.find(database_query)

                # Apply sort if provided
                if sort:
                    cursor = cursor.sort(list(sort.items()))

                # Get total count (before pagination)
                total_count = await collection.count_documents(database_query)
                print(f"Total count (before pagination): {total_count}")

                # Apply pagination
                cursor = cursor.skip(skip).limit(fetch_limit)
            except Exception as e:
                print(f"Error applying database query: {e}")
                import traceback
                traceback.print_exc()
                raise

            # Fetch documents
            try:
                documents = []
                async for doc in cursor:
                    documents.append(doc)

                print(f"Fetched {len(documents)} documents")
            except Exception as e:
                print(f"Error fetching documents: {e}")
                import traceback
                traceback.print_exc()
                raise

            # Apply in-memory filtering for encrypted fields
            if memory_filter:
                try:
                    documents = await self.apply_memory_filter(documents, memory_filter, model_class)

                    # Adjust total count based on in-memory filtering
                    total_count = len(documents)
                    print(f"Total count after in-memory filtering: {total_count}")

                    # Apply pagination again after in-memory filtering
                    documents = documents[skip:skip+limit]
                except Exception as e:
                    print(f"Error applying in-memory filter: {e}")
                    import traceback
                    traceback.print_exc()
                    raise

            # Format documents
            try:
                formatted_documents = []
                for doc in documents:
                    model_instance = model_class(**doc)
                    formatted_doc = await model_instance.formatted_properties(accept_language=self.accept_language)
                    formatted_documents.append(formatted_doc)

                print(f"Formatted {len(formatted_documents)} documents")
            except Exception as e:
                print(f"Error formatting documents: {e}")
                import traceback
                traceback.print_exc()
                raise

            return formatted_documents, total_count
        except Exception as e:
            print(f"Unexpected error in search service: {e}")
            import traceback
            traceback.print_exc()
            raise
