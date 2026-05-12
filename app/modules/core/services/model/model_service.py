

from typing import Any, Dict, Optional, Tuple, Type, Union
from bson import ObjectId
from fastapi import HTTPException
from pydantic import BaseModel 
from typing import Type, Dict, Any, Optional, Union, get_origin, get_args
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
import json

class ModelService:
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
    @staticmethod
    def convert_to_model_instance(model_class: Type[BaseModel], data: Dict[str, Any]) -> BaseModel:
        try:
            model_fields = model_class.model_fields
            processed_data = {}

            for field_name, field_info in model_fields.items():
                value = data.get(field_name)

                # Handle missing required fields
                if value is None:
                    if field_info.default is not None:
                        value = field_info.default
                    elif field_info.default_factory is not None:
                        value = field_info.default_factory()
                    elif get_origin(field_info.annotation) is Union:
                        # Check if Optional (Union[SomeType, None])
                        args = get_args(field_info.annotation)
                        if type(None) in args:
                            value = None  # Allow None for optional fields
                        else:
                            raise ValueError(f"Field '{field_name}' is required but missing in data: {data}")
                    else:
                        raise ValueError(f"Field '{field_name}' is required but missing in data: {data}")

                # Process fields like ObjectId, Enums, etc.
                if field_info.annotation == str and isinstance(value, ObjectId):
                    processed_data[field_name] = str(value)
                elif hasattr(field_info.annotation, "__members__") and isinstance(value, str):
                    # Handle Enum types
                    enum_class = field_info.annotation
                    processed_data[field_name] = enum_class(value)
                elif field_info.annotation == str and isinstance(value, dict):
                    processed_data[field_name] = json.dumps(value)
                else:
                    processed_data[field_name] = value

            return model_class(**processed_data)
        except ValueError as e:
            print(f"Error in convert_to_model_instance: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid collection converter {e}")
        except Exception as e:  # Catch other potential errors
            print(f"Error in convert_to_model_instance: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid data format: {e}")
    
    @staticmethod
    def convert_to_model_instanceXXXX(model_class: Type[BaseModel], data: Dict[str, Any]) -> BaseModel:
        try:
            model_fields = model_class.model_fields
            processed_data = {}

            for field_name, field_info in model_fields.items():
                value = data.get(field_name)

                # Handle missing required fields
                if value is None:
                    if field_info.default is not None:
                        value = field_info.default
                    elif field_info.default_factory is not None:
                        value = field_info.default_factory()
                    elif field_info.annotation.__name__ == "Optional":
                        value = None  # Allow None for optional fields
                    else:
                        raise ValueError(f"Field '{field_name}' is required but missing in data: {data}")

                # Process fields like ObjectId, Enums, etc.
                if field_info.annotation == str and isinstance(value, ObjectId):
                    processed_data[field_name] = str(value)
                elif hasattr(field_info.annotation, "__members__") and isinstance(value, str):
                    enum_class = field_info.annotation
                    processed_data[field_name] = enum_class(value)
                elif field_info.annotation == str and isinstance(value, dict):
                    processed_data[field_name] = json.dumps(value)
                else:
                    processed_data[field_name] = value

            return model_class(**processed_data)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid collection converter {e}")
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
    
    @staticmethod
    def get_collection_key_from_model_name(model_name: str) -> CollectionKey:
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        for collection_key, metadata in COLLECTION_MODEL_MAPPING.items():
            if metadata.collection_name == model_name:
                return collection_key
        raise ValueError(f"No CollectionKey found for model name: {model_name}")
    
    @staticmethod
    def get_model_class_from_collection_key(collection_key: CollectionKey) -> Type:
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"[get_model_class_from_collection_key] Invalid collection key: {CollectionKey.SYS_MENU.value}")
        return metadata.model_class

    @staticmethod
    def get_collection_name_from_collection_key(collection_key: CollectionKey) -> Type:
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"[get_collection_name_from_collection_key] Invalid collection key: {CollectionKey.SYS_MENU.value}")
        return metadata.collection_name
    
    @staticmethod
    def get_model_from_collection_key(
        collection_key: CollectionKey,
        endpoint_call: Optional[bool] = False
    ) -> Tuple[BaseModel, str]:
        """
        Fetch model class and collection name from CollectionKey.

        Args:
            collection_key (CollectionKey): Key representing the collection.
            endpoint_call (Optional[bool]): If True, enforce API exposure control.

        Returns:
            tuple: (model_class, collection_name).

        Raises:
            ValueError: If the collection key is invalid.
            PermissionError: If the collection is not exposed for API access.
        """
        from app.modules.core.models.mapping import COLLECTION_MODEL_MAPPING
        metadata = COLLECTION_MODEL_MAPPING.get(collection_key)
        if not metadata:
            raise ValueError(f"Invalid collection key: {collection_key}")
        
        if endpoint_call and not metadata.is_exposed:
            raise PermissionError(f"Access to collection '{collection_key.value}' is not allowed.")
        
        return metadata.model_class, metadata.collection_name