from typing import Any, Dict, List, Optional, Type, Union
from bson import ObjectId

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.utils.model.base_model_mixin import BaseModelMixin
from app.modules.core.utils.model.native_format_helper import NativeFormatHelper
from app.modules.core.services.debug.debug_service import DebugService

async def format_object(
    obj: Union[BaseModelMixin, Dict[str, Any]],
    output_data_type: Union[OutputDataType, str],
    accept_language: str = DEFAULT_LANGUAGE,
    collection_key: Optional[CollectionKey] = None,
    force_include_fields: list = [],
    sort: Optional[Dict[str, int]] = {"created_at": -1},
    doc: Optional[Dict[str, Any]] = None,
    force_exclude_fields: Optional[list] = None,
    base_model_class: Optional[Type] = None
) -> Dict[str, Any]:
    """
    Format an object according to the specified output data type.
    
    This helper function allows you to pass any object (BaseModelMixin instance or dict)
    and format it according to the specified output data type.
    
    Args:
        obj: The object to format (BaseModelMixin instance or dict)
        output_data_type: The output data type to use for formatting
        accept_language: The language code for translations
        collection_key: The collection key for the model
        force_include_fields: List of fields to include even if they are None
        sort: Sort order for the data
        doc: Optional document data to use instead of model instance fields
        force_exclude_fields: List of fields to exclude
        base_model_class: The model class to use for parsing (required if obj is a dict)
        
    Returns:
        Dict containing the formatted properties
    """
    # Convert output_data_type to enum if it's a string
    if isinstance(output_data_type, str):
        try:
            output_data_type = OutputDataType(output_data_type)
        except ValueError:
            # Default to DEFAULT if the string is not a valid OutputDataType
            output_data_type = OutputDataType.DEFAULT
    
    # Handle dict objects using NativeFormatHelper
    if isinstance(obj, dict):
        if base_model_class is None:
            raise ValueError("base_model_class is required when obj is a dict")
        
        # Use the appropriate NativeFormatHelper method based on output_data_type
        if output_data_type == OutputDataType.DATA_TABLE:
            return await NativeFormatHelper.formatted_native_properties_for_data_table(
                doc=obj,
                base_model_class=base_model_class,
                accept_language=accept_language,
                default_collection=collection_key,
                force_include_fields=force_include_fields
            )
        elif output_data_type == OutputDataType.TREE_DATA_TABLE:
            return await NativeFormatHelper.formatted_native_properties_for_tree_data_table(
                doc=obj,
                base_model_class=base_model_class,
                accept_language=accept_language,
                default_collection=collection_key,
                force_include_fields=force_include_fields
            )
        elif output_data_type == OutputDataType.INPUT_SELECT:
            return await NativeFormatHelper.formatted_native_properties_for_input_select(
                doc=obj,
                base_model_class=base_model_class,
                accept_language=accept_language,
                default_collection=collection_key,
                force_include_fields=force_include_fields
            )
        elif output_data_type == OutputDataType.TREE:
            return await NativeFormatHelper.formatted_native_properties_for_tree(
                doc=obj,
                base_model_class=base_model_class,
                accept_language=accept_language,
                default_collection=collection_key,
                force_include_fields=force_include_fields
            )
        else:  # Default
            return await NativeFormatHelper.formatted_native_properties_for_default(
                doc=obj,
                base_model_class=base_model_class,
                accept_language=accept_language,
                default_collection=collection_key,
                force_include_fields=force_include_fields
            )
    
    # Handle BaseModelMixin objects
    elif isinstance(obj, BaseModelMixin):
        # Call the appropriate method based on output_data_type
        if output_data_type == OutputDataType.DATA_TABLE:
            return await obj.formatted_properties_for_data_table(
                accept_language=accept_language,
                collection_key=collection_key,
                force_include_fields=force_include_fields,
                sort=sort,
                doc=doc,
                force_exclude_fields=force_exclude_fields
            )
        elif output_data_type == OutputDataType.INPUT_SELECT:
            return await obj.formatted_properties_for_input_select(
                accept_language=accept_language,
                collection_key=collection_key,
                force_include_fields=force_include_fields,
                sort=sort,
                doc=doc,
                force_exclude_fields=force_exclude_fields
            )
        elif output_data_type == OutputDataType.TREE:
            return await obj.formatted_properties_for_tree(
                accept_language=accept_language,
                collection_key=collection_key,
                force_include_fields=force_include_fields,
                sort=sort,
                doc=doc,
                force_exclude_fields=force_exclude_fields
            )
        elif output_data_type == OutputDataType.CASCADE:
            return await obj.formatted_properties_for_cascade(
                accept_language=accept_language,
                collection_key=collection_key,
                force_include_fields=force_include_fields,
                sort=sort,
                force_exclude_fields=force_exclude_fields
            )
        elif output_data_type == OutputDataType.CASCADE_ALL:
            return await obj.formatted_properties_for_cascade_all(
                accept_language=accept_language,
                collection_key=collection_key,
                force_include_fields=force_include_fields,
                force_exclude_fields=force_exclude_fields
            )
        else:  # Default
            return await obj.formatted_properties_for_default(
                accept_language=accept_language,
                collection_key=collection_key,
                force_include_fields=force_include_fields,
                sort=sort,
                force_exclude_fields=force_exclude_fields
            )
    else:
        raise TypeError(f"Unsupported object type: {type(obj)}. Must be BaseModelMixin or dict.")
