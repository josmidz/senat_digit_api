from typing import Any, Dict, List, Optional, Type
from bson import ObjectId

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.model.model_service import ModelService

class NativeFormatHelper:
    @staticmethod
    async def formatted_native_properties_for_default(
        doc: Dict[str, Any],
        base_model_class: Type,
        accept_language: str = DEFAULT_LANGUAGE,
        collection_key: CollectionKey = CollectionKey.SYS_USER,
        force_include_fields: Optional[list] = [],
        force_exclude_fields: Optional[list] = [],
    ) -> Dict[str, Any]:
        """
        Processes a raw document (fetched from aggregation) that contains:
          - Base collection fields
          - Nested collections under keys prefixed with "unwind__"

        For each portion of the document, this method:
          1. Parses the data into its model (using the provided model class for the base or via a helper for nested data)
          2. Calls that instance's formatted_properties_for_default() method to get the translated fields.
          3. Merges the base fields with nested (recursively processed) fields.

        Parameters:
          - doc: The raw document (as a dict) from the database.
          - base_model_class: The model class corresponding to the base document.
          - accept_language: Language code (if you need to translate any fields).
          - collection_key: The CollectionKey corresponding to the base document.
          - force_include_fields: List of fields to forcefully include in the output, overriding exclusions.

        Returns:
          A dict with the fully formatted (and translated) data.
        """
        # 1. Process the base document.
        base_doc = {k: v for k, v in doc.items() if not k.startswith("unwind__")}
        try:
            # Get required fields from model
            required_fields = {}
            for field_name, field in base_model_class.model_fields.items():
                if field.is_required():
                    # If field is in base_doc, use that value
                    if field_name in base_doc:
                        required_fields[field_name] = base_doc.get(field_name)
                    # Otherwise provide a default value based on field type
                    else:
                        # For string fields like 'flag', generate a temporary value
                        if field.annotation == str:
                            required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                        # For other types, you might need different defaults
            
            # Always include ID field if available
            if "_id" in base_doc:
                required_fields["id"] = str(base_doc["_id"])
            elif "id" in base_doc:
                required_fields["id"] = base_doc["id"]
            else:
                required_fields["id"] = str(ObjectId())
                
            base_instance = base_model_class(**required_fields)
            base_formatted = await base_instance.formatted_properties_for_default(
                accept_language=accept_language,
                collection_key=collection_key,
                force_include_fields=force_include_fields,
                force_exclude_fields=force_exclude_fields
            )

            # If formatted_properties_for_default returns None, use the original document
            if base_formatted is None:
                print(f"Warning: formatted_properties_for_default returned None, using original document")
                base_formatted = base_doc
                # Ensure we have an ID field
                if "_id" in base_formatted and "id" not in base_formatted:
                    base_formatted["id"] = str(base_formatted["_id"])
                    base_formatted.pop("_id", None)
        except Exception as e:
            print(f"Error formatting base document: {e}")
            # If there's an error, use the original document
            base_formatted = base_doc
            # Ensure we have an ID field
            if "_id" in base_formatted and "id" not in base_formatted:
                base_formatted["id"] = str(base_formatted["_id"])
                base_formatted.pop("_id", None)

        # 2. Process nested keys (those with prefix "unwind__")
        nested_formatted = {}
        for key, value in doc.items():
            if not key.startswith("unwind__"):
                continue

            # Remove the prefix to get the intended collection name.
            nested_key = key[len("unwind__"):]
            try:
                nested_collection_key = ModelService.get_collection_key_from_model_name(nested_key)
            except ValueError as e:
                # If not recognized, include the value as is.
                nested_formatted[nested_key] = value
                continue

            # Get the model class for the nested collection.
            try:
                nested_model_class = ModelService.get_model_class_from_collection_key(nested_collection_key)
            except Exception as e:
                nested_formatted[nested_key] = value
                continue

            # Process the nested value.
            if isinstance(value, dict):
                # Try to create a model instance with required fields only
                required_fields = {}
                for field_name, field in nested_model_class.model_fields.items():
                    if field.is_required():
                        # If field is in value, use that value
                        if field_name in value:
                            required_fields[field_name] = value.get(field_name)
                        # Otherwise provide a default value based on field type
                        else:
                            # For string fields, generate a temporary value
                            if field.annotation == str:
                                required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                            # For other types, you might need different defaults
                
                # Always include ID field if available
                if "_id" in value:
                    required_fields["id"] = str(value["_id"])
                elif "id" in value:
                    required_fields["id"] = value["id"]
                else:
                    required_fields["id"] = str(ObjectId())
                    
                nested_instance = nested_model_class(**required_fields)
                nested_formatted[nested_key] = await nested_instance.formatted_properties_for_default(
                    accept_language=accept_language,
                    collection_key=nested_collection_key,
                    force_include_fields=force_include_fields,
                    force_exclude_fields=force_exclude_fields
                )
            elif isinstance(value, list):
                formatted_list: List[Any] = []
                for item in value:
                    if isinstance(item, dict):
                        # Try to create a model instance with required fields only
                        required_fields = {}
                        for field_name, field in nested_model_class.model_fields.items():
                            if field.is_required():
                                # If field is in item, use that value
                                if field_name in item:
                                    required_fields[field_name] = item.get(field_name)
                                # Otherwise provide a default value based on field type
                                else:
                                    # For string fields, generate a temporary value
                                    if field.annotation == str:
                                        required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                                    # For other types, you might need different defaults
                        
                        # Always include ID field if available
                        if "_id" in item:
                            required_fields["id"] = str(item["_id"])
                        elif "id" in item:
                            required_fields["id"] = item["id"]
                        else:
                            required_fields["id"] = str(ObjectId())
                            
                        nested_instance = nested_model_class(**required_fields)
                        formatted_item = await nested_instance.formatted_properties_for_default(
                            accept_language=accept_language,
                            collection_key=nested_collection_key,
                            force_include_fields=force_include_fields,
                            force_exclude_fields=force_exclude_fields
                        )
                        formatted_list.append(formatted_item)
                    else:
                        formatted_list.append(item)
                nested_formatted[nested_key] = formatted_list
            else:
                # For any other type, keep the value as is.
                nested_formatted[nested_key] = value

        # 3. Merge the base and nested formatted dictionaries.
        # In case of a key collision, nested keys override the base ones.
        combined = {**base_formatted, **nested_formatted}
        # sensitive_fields = ['password', 'user_account_hash', 'user_account_socket_hash']
        # for field in sensitive_fields:
        #     combined.pop(field, None)
        return combined

    @staticmethod
    async def formatted_native_properties_for_input_select(
        doc: Dict[str, Any],
        base_model_class: Type,
        accept_language: str = DEFAULT_LANGUAGE,
        collection_key: CollectionKey = CollectionKey.SYS_USER,
        force_include_fields: Optional[list] = [],
        force_exclude_fields: Optional[list] = [],
    ) -> Dict[str, Any]:
        """
        Processes a raw document (fetched from aggregation) that contains:
          - Base collection fields
          - Nested collections under keys prefixed with "unwind__"

        For each portion of the document, this method:
          1. Parses the data into its model (using the provided model class for the base or via a helper for nested data)
          2. Calls that instance's formatted_properties_for_input_select() method to get the translated fields.
          3. Merges the base fields with nested (recursively processed) fields.

        Parameters:
          - doc: The raw document (as a dict) from the database.
          - base_model_class: The model class corresponding to the base document.
          - accept_language: Language code (if you need to translate any fields).
          - collection_key: The CollectionKey corresponding to the base document.
          - force_include_fields: List of fields to forcefully include in the output, overriding exclusions.

        Returns:
          A dict with the fully formatted (and translated) data.
        """
        # 1. Process the base document.
        base_doc = {k: v for k, v in doc.items() if not k.startswith("unwind__")}
        try:
            # base_instance = base_model_class.parse_obj(base_doc)
            required_fields = {}
            for field_name, field in base_model_class.model_fields.items():
                if field.is_required():
                    # If field is in base_doc, use that value
                    if field_name in base_doc:
                        required_fields[field_name] = base_doc.get(field_name)
                    # Otherwise provide a default value based on field type
                    else:
                        # For string fields like 'flag', generate a temporary value
                        if field.annotation == str:
                            required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                        # For other types, you might need different defaults
                        else:
                            required_fields[field_name] = None

            # Always include ID field if available
            if "_id" in base_doc:
                required_fields["id"] = str(base_doc["_id"])
            elif "id" in base_doc:
                required_fields["id"] = base_doc["id"]
            else:
                required_fields["id"] = str(ObjectId())

            base_instance = base_model_class(**required_fields)
            base_formatted = await base_instance.formatted_properties_for_input_select(
                accept_language=accept_language,
                collection_key=collection_key,
                force_include_fields=force_include_fields,
                force_exclude_fields=force_exclude_fields
            )

            # If formatted_properties_for_input_select returns None, use the original document
            if base_formatted is None:
                print(f"Warning: formatted_properties_for_input_select returned None, using original document")
                base_formatted = base_doc
                # Ensure we have an ID field
                if "_id" in base_formatted and "id" not in base_formatted:
                    base_formatted["id"] = str(base_formatted["_id"])
                    base_formatted.pop("_id", None)
        except Exception as e:
            print(f"Error formatting base document for input_select: {e}")
            # If there's an error, use the original document
            base_formatted = base_doc
            # Ensure we have an ID field
            if "_id" in base_formatted and "id" not in base_formatted:
                base_formatted["id"] = str(base_formatted["_id"])
                base_formatted.pop("_id", None)

        # 2. Process nested keys (those with prefix "unwind__")
        nested_formatted = {}
        for key, value in doc.items():
            if not key.startswith("unwind__"):
                continue

            # Remove the prefix to get the intended collection name.
            nested_key = key[len("unwind__"):]
            try:
                nested_collection_key = ModelService.get_collection_key_from_model_name(nested_key)
            except ValueError as e:
                # If not recognized, include the value as is.
                nested_formatted[nested_key] = value
                continue

            # Get the model class for the nested collection.
            try:
                nested_model_class = ModelService.get_model_class_from_collection_key(nested_collection_key)
            except Exception as e:
                nested_formatted[nested_key] = value
                continue

            # Process the nested value.
            if isinstance(value, dict):
                # Try to create a model instance with required fields only
                required_fields = {}
                for field_name, field in nested_model_class.model_fields.items():
                    if field.is_required():
                        # If field is in value, use that value
                        if field_name in value:
                            required_fields[field_name] = value.get(field_name)
                        # Otherwise provide a default value based on field type
                        else:
                            # For string fields, generate a temporary value
                            if field.annotation == str:
                                required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                            # For other types, you might need different defaults
                        
                # Always include ID field if available
                if "_id" in value:
                    required_fields["id"] = str(value["_id"])
                elif "id" in value:
                    required_fields["id"] = value["id"]
                else:
                    required_fields["id"] = str(ObjectId())
                    
                nested_instance = nested_model_class(**required_fields)
                nested_formatted[nested_key] = await nested_instance.formatted_properties_for_input_select(
                    accept_language=accept_language,
                    collection_key=nested_collection_key,
                    force_include_fields=force_include_fields,
                    force_exclude_fields=force_exclude_fields
                )
            elif isinstance(value, list):
                formatted_list: List[Any] = []
                for item in value:
                    if isinstance(item, dict):
                        # Try to create a model instance with required fields only
                        required_fields = {}
                        for field_name, field in nested_model_class.model_fields.items():
                            if field.is_required():
                                # If field is in item, use that value
                                if field_name in item:
                                    required_fields[field_name] = item.get(field_name)
                                # Otherwise provide a default value based on field type
                                else:
                                    # For string fields, generate a temporary value
                                    if field.annotation == str:
                                        required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                                    # For other types, you might need different defaults
                        
                        # Always include ID field if available
                        if "_id" in item:
                            required_fields["id"] = str(item["_id"])
                        elif "id" in item:
                            required_fields["id"] = item["id"]
                        else:
                            required_fields["id"] = str(ObjectId())
                            
                        nested_instance = nested_model_class(**required_fields)
                        formatted_item = await nested_instance.formatted_properties_for_input_select(
                            accept_language=accept_language,
                            collection_key=nested_collection_key,
                            force_include_fields=force_include_fields,
                            force_exclude_fields=force_exclude_fields
                        )
                        formatted_list.append(formatted_item)
                    else:
                        formatted_list.append(item)
                nested_formatted[nested_key] = formatted_list
            else:
                # For any other type, keep the value as is.
                nested_formatted[nested_key] = value

        # 3. Merge the base and nested formatted dictionaries.
        # In case of a key collision, nested keys override the base ones.
        combined = {**base_formatted, **nested_formatted}
        # 4. Remove sensitive fields before returning
        sensitive_fields = ['password', 'user_account_hash', 'user_account_socket_hash']
        for field in sensitive_fields:
            combined.pop(field, None)
        return combined

    @staticmethod
    async def formatted_native_properties_for_data_table(
        doc: Dict[str, Any],
        base_model_class: Type,
        accept_language: str = DEFAULT_LANGUAGE,
        collection_key: CollectionKey = CollectionKey.SYS_USER,
        force_include_fields: Optional[list] = [],
        force_exclude_fields: Optional[list] = [],
    ) -> Dict[str, Any]:
        """
        Processes a raw document (fetched from aggregation) that contains:
        - Base collection fields
        - Nested collections under keys prefixed with "unwind__"

        For each portion of the document, this method:
        1. Parses the data into its model (using the provided model class for the base or via a helper for nested data)
        2. Calls that instance's formatted_properties_for_data_table() method to get the translated fields.
        3. Merges the base fields with nested (recursively processed) fields.
        4. Removes sensitive fields like 'password' before returning.

        Parameters:
        - doc: The raw document (as a dict) from the database.
        - base_model_class: The model class corresponding to the base document.
        - accept_language: Language code (if you need to translate any fields).
        - collection_key: The CollectionKey corresponding to the base document.
        - force_include_fields: List of fields to forcefully include in the output, overriding exclusions.

        Returns:
        A dict with the fully formatted (and translated) data, without sensitive fields.
        """

        # print(f"\n\n\n doc >>>> : {doc} \n\n\n")
        # 1. Process the base document.
        base_doc = {k: v for k, v in doc.items() if not k.startswith("unwind__")}
        # print(f"\n\n\n base_doc >>>> : {base_doc} \n\n\n")
        try:
            # Get required fields from model
            required_fields = {}
            for field_name, field in base_model_class.model_fields.items():
                if field.is_required():
                    # If field is in base_doc, use that value
                    if field_name in base_doc:
                        required_fields[field_name] = base_doc.get(field_name)
                    # Otherwise provide a default value based on field type
                    else:
                        # For string fields like 'flag', generate a temporary value
                        if field.annotation == str:
                            required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                        # For other types, you might need different defaults
            
            # Always include ID field if available
            if "_id" in base_doc:
                required_fields["id"] = str(base_doc["_id"])
            elif "id" in base_doc:
                required_fields["id"] = base_doc["id"]
            else:
                required_fields["id"] = str(ObjectId())
                
            base_instance = base_model_class(**required_fields)
            base_formatted = await base_instance.formatted_properties_for_data_table(
                accept_language=accept_language,
                collection_key=collection_key,
                doc=base_doc,  # Pass the document directly to avoid validation errors
                force_include_fields=force_include_fields,
                force_exclude_fields=force_exclude_fields
            )
        except Exception as e:
            print(f"\n\n\n error first parse: {e} \n\n\n")
            # If model creation fails, try to create a minimal valid instance
            try:
                # Get all required fields from model
                required_fields = {}
                for field_name, field in base_model_class.model_fields.items():
                    if field.is_required():
                        # If field is in base_doc, use that value
                        if field_name in base_doc:
                            required_fields[field_name] = base_doc.get(field_name)
                        # Otherwise provide a default value based on field type
                        else:
                            # For string fields like 'flag', generate a temporary value
                            if field.annotation == str:
                                required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                            # For other types, you might need different defaults
                
                # Always include ID field if available
                if "_id" in base_doc:
                    required_fields["id"] = str(base_doc["_id"])
                elif "id" in base_doc:
                    required_fields["id"] = base_doc["id"]
                else:
                    required_fields["id"] = str(ObjectId())
                    
                base_instance = base_model_class(**required_fields)
                base_formatted = await base_instance.formatted_properties_for_data_table(
                    accept_language=accept_language,
                    collection_key=collection_key,
                    doc=base_doc,  # Pass the document directly to avoid validation errors
                    force_include_fields=force_include_fields,
                    force_exclude_fields=force_exclude_fields
                )
            except Exception as inner_e:
                # If all else fails, just return the document as is
                print(f"Error formatting document: {inner_e}")
                base_formatted = base_doc

        # 2. Process nested keys (those with prefix "unwind__")
        nested_formatted = {}
        for key, value in doc.items():
            if not key.startswith("unwind__"):
                continue

            # Remove the prefix to get the intended collection name.
            nested_key = key[len("unwind__"):]
            # print(f"\n\n\n nested_key: {nested_key} \n\n\n")
            try:
                nested_collection_key = ModelService.get_collection_key_from_model_name(nested_key)
            except ValueError as e:
                # If not recognized, include the value as is.
                nested_formatted[nested_key] = value
                continue

            # Get the model class for the nested collection.
            try:
                nested_model_class = ModelService.get_model_class_from_collection_key(nested_collection_key)
            except Exception as e:
                nested_formatted[nested_key] = value
                continue

            # Process the nested value.
            if isinstance(value, dict):
                try:
                    # Try to create a model instance with required fields only
                    required_fields = {}
                    for field_name, field in nested_model_class.model_fields.items():
                        if field.is_required():
                            # If field is in value, use that value
                            if field_name in value:
                                required_fields[field_name] = value.get(field_name)
                            # Otherwise provide a default value based on field type
                            else:
                                # For string fields, generate a temporary value
                                if field.annotation == str:
                                    required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                                # For other types, you might need different defaults
                    
                    # Always include ID field if available
                    if "_id" in value:
                        required_fields["id"] = str(value["_id"])
                    elif "id" in value:
                        required_fields["id"] = value["id"]
                    else:
                        required_fields["id"] = str(ObjectId())
                        
                    nested_instance = nested_model_class(**required_fields)
                    nested_formatted[nested_key] = await nested_instance.formatted_properties_for_data_table(
                        accept_language=accept_language,
                        collection_key=nested_collection_key,
                        doc=value,  # Pass the document directly to avoid validation errors
                        force_include_fields=force_include_fields,
                        force_exclude_fields=force_exclude_fields
                    )
                except Exception as e:
                    try:
                        # Create a minimal instance with just the ID
                        minimal_data = {"id": value.get("_id", None) or value.get("id", None)}
                        if minimal_data["id"] is None:
                            minimal_data["id"] = str(ObjectId())

                        nested_instance = nested_model_class(**minimal_data)
                        nested_formatted[nested_key] = await nested_instance.formatted_properties_for_data_table(
                            accept_language=accept_language,
                            collection_key=nested_collection_key,
                            doc=value,  # Pass the document directly to avoid validation errors
                            force_include_fields=force_include_fields,
                            force_exclude_fields=force_exclude_fields
                        )
                    except Exception as inner_e:
                        # If all else fails, just return the document as is
                        print(f"Error formatting nested document: {inner_e}")
                        nested_formatted[nested_key] = value
            elif isinstance(value, list):
                formatted_list: List[Any] = []
                for item in value:
                    if isinstance(item, dict):
                        try:
                            # Try to create a model instance with required fields only
                            required_fields = {}
                            for field_name, field in nested_model_class.model_fields.items():
                                if field.is_required():
                                    # If field is in item, use that value
                                    if field_name in item:
                                        required_fields[field_name] = item.get(field_name)
                                    # Otherwise provide a default value based on field type
                                    else:
                                        # For string fields, generate a temporary value
                                        if field.annotation == str:
                                            required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                                        # For other types, you might need different defaults
                            
                            # Always include ID field if available
                            if "_id" in item:
                                required_fields["id"] = str(item["_id"])
                            elif "id" in item:
                                required_fields["id"] = item["id"]
                            else:
                                required_fields["id"] = str(ObjectId())
                                
                            nested_instance = nested_model_class(**required_fields)
                            formatted_item = await nested_instance.formatted_properties_for_data_table(
                                accept_language=accept_language,
                                collection_key=nested_collection_key,
                                doc=item,  # Pass the document directly to avoid validation errors
                                force_include_fields=force_include_fields,
                                force_exclude_fields=force_exclude_fields
                            )
                            formatted_list.append(formatted_item)
                        except Exception as e:
                            try:
                                # Create a minimal instance with just the ID
                                minimal_data = {"id": item.get("_id", None) or item.get("id", None)}
                                if minimal_data["id"] is None:
                                    minimal_data["id"] = str(ObjectId())

                                nested_instance = nested_model_class(**minimal_data)
                                formatted_item = await nested_instance.formatted_properties_for_data_table(
                                    accept_language=accept_language,
                                    collection_key=nested_collection_key,
                                    doc=item,  # Pass the document directly to avoid validation errors
                                    force_include_fields=force_include_fields,
                                    force_exclude_fields=force_exclude_fields
                                )
                                formatted_list.append(formatted_item)
                            except Exception as inner_e:
                                # If all else fails, just return the item as is
                                print(f"Error formatting nested list item: {inner_e}")
                                formatted_list.append(item)
                    else:
                        formatted_list.append(item)
                nested_formatted[nested_key] = formatted_list
            else:
                # For any other type, keep the value as is.
                nested_formatted[nested_key] = value

        # 3. Merge the base and nested formatted dictionaries.
        # In case of a key collision, nested keys override the base ones.
        combined = {**base_formatted, **nested_formatted}

        # 4. Remove sensitive fields before returning
        sensitive_fields = ['password', 'user_account_hash', 'user_account_socket_hash']
        for field in sensitive_fields:
            combined.pop(field, None)

        return combined
     

    @staticmethod
    async def formatted_native_properties_for_tree(
        doc: Dict[str, Any],
        base_model_class: Type,
        accept_language: str = DEFAULT_LANGUAGE,
        collection_key: CollectionKey = CollectionKey.SYS_USER,
        force_include_fields: Optional[list] = [],
        force_exclude_fields: Optional[list] = [],
    ) -> Dict[str, Any]:
        """
        Processes a raw document (fetched from aggregation) that contains:
          - Base collection fields
          - Nested collections under keys prefixed with "unwind__"

        For each portion of the document, this method:
          1. Parses the data into its model (using the provided model class for the base or via a helper for nested data)
          2. Calls that instance's formatted_properties_for_tree() method to get the translated fields.
          3. Merges the base fields with nested (recursively processed) fields.

        Parameters:
          - doc: The raw document (as a dict) from the database.
          - base_model_class: The model class corresponding to the base document.
          - accept_language: Language code (if you need to translate any fields).
          - collection_key: The CollectionKey corresponding to the base document.
          - force_include_fields: List of fields to forcefully include in the output, overriding exclusions.

        Returns:
          A dict with the fully formatted (and translated) data.
        """
        # 1. Process the base document.
        base_doc = {k: v for k, v in doc.items() if not k.startswith("unwind__")}
        try:
            # Get required fields from model
            required_fields = {}
            for field_name, field in base_model_class.model_fields.items():
                if field.is_required():
                    # If field is in base_doc, use that value
                    if field_name in base_doc:
                        required_fields[field_name] = base_doc.get(field_name)
                    # Otherwise provide a default value based on field type
                    else:
                        # For string fields like 'flag', generate a temporary value
                        if field.annotation == str:
                            required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                        # For other types, you might need different defaults
            
            # Always include ID field if available
            if "_id" in base_doc:
                required_fields["id"] = str(base_doc["_id"])
            elif "id" in base_doc:
                required_fields["id"] = base_doc["id"]
            else:
                required_fields["id"] = str(ObjectId())
                
            base_instance = base_model_class(**required_fields)
            base_formatted = await base_instance.formatted_properties_for_tree(
                accept_language=accept_language,
                collection_key=collection_key,
                force_include_fields=force_include_fields,
                force_exclude_fields=force_exclude_fields
            )

            # If formatted_properties_for_tree returns None, use the original document
            if base_formatted is None:
                print(f"Warning: formatted_properties_for_tree returned None, using original document")
                base_formatted = base_doc
                # Ensure we have an ID field
                if "_id" in base_formatted and "id" not in base_formatted:
                    base_formatted["id"] = str(base_formatted["_id"])
                    base_formatted.pop("_id", None)
        except Exception as e:
            print(f"Error formatting base document for tree: {e}")
            # If there's an error, use the original document
            base_formatted = base_doc
            # Ensure we have an ID field
            if "_id" in base_formatted and "id" not in base_formatted:
                base_formatted["id"] = str(base_formatted["_id"])
                base_formatted.pop("_id", None)

        # 2. Process nested keys (those with prefix "unwind__")
        nested_formatted = {}
        for key, value in doc.items():
            if not key.startswith("unwind__"):
                continue

            # Remove the prefix to get the intended collection name.
            nested_key = key[len("unwind__"):]
            try:
                nested_collection_key = ModelService.get_collection_key_from_model_name(nested_key)
            except ValueError as e:
                # If not recognized, include the value as is.
                nested_formatted[nested_key] = value
                continue

            # Get the model class for the nested collection.
            try:
                nested_model_class = ModelService.get_model_class_from_collection_key(nested_collection_key)
            except Exception as e:
                nested_formatted[nested_key] = value
                continue

            # Process the nested value.
            if isinstance(value, dict):
                # Try to create a model instance with required fields only
                required_fields = {}
                for field_name, field in nested_model_class.model_fields.items():
                    if field.is_required():
                        # If field is in value, use that value
                        if field_name in value:
                            required_fields[field_name] = value.get(field_name)
                        # Otherwise provide a default value based on field type
                        else:
                            # For string fields, generate a temporary value
                            if field.annotation == str:
                                required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                            # For other types, you might need different defaults
                
                # Always include ID field if available
                if "_id" in value:
                    required_fields["id"] = str(value["_id"])
                elif "id" in value:
                    required_fields["id"] = value["id"]
                else:
                    required_fields["id"] = str(ObjectId())
                    
                nested_instance = nested_model_class(**required_fields)
                nested_formatted[nested_key] = await nested_instance.formatted_properties_for_tree(
                    accept_language=accept_language,
                    collection_key=nested_collection_key
                )
            elif isinstance(value, list):
                formatted_list: List[Any] = []
                for item in value:
                    if isinstance(item, dict):
                        # Try to create a model instance with required fields only
                        required_fields = {}
                        for field_name, field in nested_model_class.model_fields.items():
                            if field.is_required():
                                # If field is in item, use that value
                                if field_name in item:
                                    required_fields[field_name] = item.get(field_name)
                                # Otherwise provide a default value based on field type
                                else:
                                    # For string fields, generate a temporary value
                                    if field.annotation == str:
                                        required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
                                    # For other types, you might need different defaults
                        
                        # Always include ID field if available
                        if "_id" in item:
                            required_fields["id"] = str(item["_id"])
                        elif "id" in item:
                            required_fields["id"] = item["id"]
                        else:
                            required_fields["id"] = str(ObjectId())
                            
                        nested_instance = nested_model_class(**required_fields)
                        formatted_item = await nested_instance.formatted_properties_for_tree(
                            accept_language=accept_language,
                            collection_key=nested_collection_key
                        )
                        formatted_list.append(formatted_item)
                    else:
                        formatted_list.append(item)
                nested_formatted[nested_key] = formatted_list
            else:
                # For any other type, keep the value as is.
                nested_formatted[nested_key] = value

        # 3. Merge the base and nested formatted dictionaries.
        # In case of a key collision, nested keys override the base ones.
        combined = {**base_formatted, **nested_formatted}
        sensitive_fields = ['password', 'user_account_hash', 'user_account_socket_hash']
        for field in sensitive_fields:
            combined.pop(field, None)
        return combined

