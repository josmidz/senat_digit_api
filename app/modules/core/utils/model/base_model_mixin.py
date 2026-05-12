#app/utls/base_model_mixin.py
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional, Type, List
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE, FALLBACK_LANGUAGE, SUPPORTED_LANGUAGE_CODES, TRANSLATIONS
from bson import ObjectId
from pydantic import BaseModel, ValidationError, model_validator
from beanie import Document
import uuid
import re
import asyncio
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.encryption.encryption_service import CURRENT_KEY_VERSION
from app.modules.core.services.encryption.db_encryption_service import DBEncryptionService
from app.modules.core.enums.type_enum import AppGeneratorType, OutputDataType
from app.modules.core.utils.model.timestamp_mixin import TimestampMixin
from app.modules.auth.enums.common import FieldTranslation
from app.modules.core.utils.model.base_model_utils import BaseModelUtils
from app.modules.core.utils.common.async_runner import AsyncExecutor



class BaseModelMixin(Document,BaseModel, TimestampMixin):
    """
    Centralized base model class:
    - Handles dynamic field generation based on metadata.
    - Automatically converts fields ending in '_id' to ObjectId.
    - Provides utilities for field translations.
    """
    # Define generic_service as a class variable to exclude it from validation

    # Class-level caches for performance optimization
    FIELD_TRANSLATION_KEYS: ClassVar[Dict[str, Dict[str, str]]] = {}
    _field_data_cache = {}
    _translation_batch_cache = {}
    _cache_lock = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        field_keys = cls.__dict__.get("FIELD_TRANSLATION_KEYS", {})
        if field_keys:
            for _field_name, lang_map in field_keys.items():
                if isinstance(lang_map, dict) and lang_map:
                    base_lang = FALLBACK_LANGUAGE if FALLBACK_LANGUAGE in lang_map else (
                        DEFAULT_LANGUAGE if DEFAULT_LANGUAGE in lang_map else next(iter(lang_map))
                    )
                    for lang in SUPPORTED_LANGUAGE_CODES:
                        lang_map.setdefault(lang, lang_map[base_lang])

            from app.modules.core.utils.model.base_document import BaseDocument

            BaseDocument._field_translation_registry.update(field_keys)

    @classmethod
    def get_cache_lock(cls):
        """Get or create the cache lock."""
        if cls._cache_lock is None:
            cls._cache_lock = asyncio.Lock()
        return cls._cache_lock
    
    def handle_translation_status(self, status_value, enum_cls, accept_language: str = DEFAULT_LANGUAGE) -> str:
        """
        Returns a localized label for a given enum status using the TRANSLATIONS map.

        Args:
            status_value: The enum value to translate. May be an Enum member, its value, or name.
            enum_cls: The Enum class (e.g., EGlobalStatus).
            accept_language: Target language code (defaults to DEFAULT_LANGUAGE).

        Fallbacks:
            - If language not found, fallback to DEFAULT_LANGUAGE.
            - If translation missing, return the enum name (or str(value)).
        """
        try:
            # Normalize language
            lang = (accept_language or DEFAULT_LANGUAGE).lower()
            if lang not in TRANSLATIONS:
                lang = DEFAULT_LANGUAGE

            # Normalize to an enum member
            enum_member = None
            if isinstance(status_value, enum_cls):
                enum_member = status_value
            else:
                # Try value-based construction
                try:
                    enum_member = enum_cls(status_value)
                except Exception:
                    # Try by name if a string was provided
                    if isinstance(status_value, str):
                        try:
                            enum_member = enum_cls[status_value]
                        except Exception:
                            enum_member = None

            # Build fallback label from what we have
            fallback_label = (
                enum_member.name.replace("_", " ").title() if getattr(enum_member, "name", None)
                else str(getattr(status_value, "name", status_value)).replace("_", " ").title()
            )

            # Resolve translation mapping
            lang_map = TRANSLATIONS.get(lang, {})
            enum_map = lang_map.get(enum_cls, {})

            if enum_member is not None and enum_member in enum_map:
                return enum_map[enum_member]

            # No exact match; attempt lenient lookup by name/value
            if enum_map and status_value is not None:
                target_key = str(getattr(status_value, "name", status_value)).upper()
                for k, v in enum_map.items():
                    try:
                        key_name = getattr(k, "name", str(k)).upper()
                        key_value = str(getattr(k, "value", k)).upper()
                    except Exception:
                        key_name = str(k).upper()
                        key_value = key_name
                    if target_key in (key_name, key_value):
                        return v

            return fallback_label
        except Exception:
            # Last resort
            return str(status_value)

    @classmethod
    async def batch_fetch_field_data(cls, data_requests: List[Dict], accept_language: str = DEFAULT_LANGUAGE):
        """
        Batch fetch field data to reduce database calls.
        data_requests: List of {"data_source": str, "field_id": str, "query": dict}
        Returns: Dict mapping "data_source:field_id" to result
        """
        if not data_requests:
            return {}

        # Group requests by data_source
        grouped_requests = {}
        for request in data_requests:
            data_source = request["data_source"]
            if data_source not in grouped_requests:
                grouped_requests[data_source] = []
            grouped_requests[data_source].append(request)

        # Batch fetch for each data_source
        results = {}
        fetch_tasks = []

        for data_source, requests in grouped_requests.items():
            # Collect all IDs for this data_source
            field_ids = [req["field_id"] for req in requests if req["field_id"]]

            if field_ids:
                # Create batch query
                batch_query = {"filter___id": {"$in": field_ids}}

                # Create fetch task
                async def fetch_batch(ds, query, lang):
                    try:
                        from app.modules.core.services.generic.generic_services import GenericService
                        generic_service = GenericService(lang)

                        # Fetch multiple records at once
                        batch_results = await generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey(ds),
                            output_data_type=OutputDataType.INPUT_SELECT,
                            query=query,
                            accept_language=lang,
                            all_data=True
                        )

                        # Convert to lookup dict
                        lookup = {}
                        if batch_results:
                            for result in batch_results:
                                result_id = str(result.get("id", ""))
                                lookup[f"{ds}:{result_id}"] = result

                        return lookup
                    except Exception as e:
                        DebugService.app_debug_print(f"[ERROR] Batch fetch failed for {ds}: {e}", True)
                        return {}

                fetch_tasks.append(fetch_batch(data_source, batch_query, accept_language))

        # Execute all batch fetches concurrently
        if fetch_tasks:
            batch_results = await AsyncExecutor.gather(fetch_tasks, return_exceptions=True)

            # Merge results
            for batch_result in batch_results:
                if isinstance(batch_result, dict):
                    results.update(batch_result)

        return results

    @classmethod
    async def batch_get_translations(cls, translation_requests: List[Dict], accept_language: str = DEFAULT_LANGUAGE):
        """
        Batch get translations to reduce sequential calls.
        translation_requests: List of {"targeted_id": str, "property_name": str, "property_value": str, "model_name": str}
        Returns: Dict mapping request_key to translation result
        """
        if not translation_requests or accept_language == DEFAULT_LANGUAGE:
            # Return original values if no translation needed
            return {f"{req['targeted_id']}:{req['property_name']}": req['property_value']
                   for req in translation_requests}

        # Create concurrent translation tasks
        translation_tasks = []
        request_keys = []

        for req in translation_requests:
            request_key = f"{req['targeted_id']}:{req['property_name']}"
            request_keys.append(request_key)

            # Create translation task
            task = BaseModelUtils.get_innter_translation(
                targeted_id=req['targeted_id'],
                property_name=req['property_name'],
                short_code=accept_language,
                property_value=req['property_value'],
                model_name=req['model_name']
            )
            translation_tasks.append(task)

        # Execute all translations concurrently
        try:
            translation_results = await AsyncExecutor.gather(translation_tasks, return_exceptions=True)

            # Map results back to request keys
            results = {}
            for i, result in enumerate(translation_results):
                request_key = request_keys[i]
                if isinstance(result, Exception):
                    # Use original value if translation failed
                    results[request_key] = translation_requests[i]['property_value']
                    DebugService.app_debug_print(f"[ERROR] Translation failed for {request_key}: {result}", True)
                else:
                    results[request_key] = result

            return results

        except Exception as e:
            DebugService.app_debug_print(f"[ERROR] Batch translation failed: {e}", True)
            # Return original values as fallback
            return {f"{req['targeted_id']}:{req['property_name']}": req['property_value']
                   for req in translation_requests}

    def __init__(self, **data):
        # Initialize parent classes first
        super().__init__(**data)


    # Modified method to directly encrypt field values with version tracking
    async def encrypt_sensitive_fields(self):
        """Encrypt fields that have can_be_encrypted=True in their metadata."""
        # Import CURRENT_KEY_VERSION once at the beginning
        # from app.modules.core.services.encryption.encryption_service import CURRENT_KEY_VERSION
        pass
        db_encryption = DBEncryptionService()
        # Iterate through all fields to find those that can be encrypted
        for field_name, field in self.model_fields.items():
            meta = field.json_schema_extra or {}
            can_be_encrypted = meta.get("can_be_encrypted", False)

            if can_be_encrypted:
                field_value = getattr(self, field_name, None)
                if field_value is not None:
                    # Convert to string if it's a number
                    if isinstance(field_value, (int, float)):
                        field_value = str(field_value)

                    if isinstance(field_value, str):
                        # For debugging
                        DebugService.app_debug_print(f"Processing field {field_name} for encryption: {field_value[:20]}...", False)

                        # Handle different encryption formats
                        if not field_value.lower().startswith(db_encryption.VERSION_PREFIX):
                            # Not encrypted yet - encrypt it
                            try:
                                encrypted_value = db_encryption.encrypt(field_value)
                                # Set the encrypted value directly on the field
                                setattr(self, field_name, f"{db_encryption.VERSION_PREFIX}{encrypted_value}")
                                DebugService.app_debug_print(f"Encrypted field {field_name}", False)
                            except Exception as e:
                                DebugService.app_debug_print(f"Error encrypting field {field_name}: {e}", True)

                        # Handle double-versioned encrypted value (db_enc:v1:v1:)
                        elif field_value.lower().startswith(f"{db_encryption.VERSION_PREFIX}v1:v1:"):
                            try:
                                # Extract the actual encrypted text (after the double version prefix)
                                actual_encrypted_text = field_value[10:]  # Remove "db_enc:v1:v1:" prefix
                                DebugService.app_debug_print(f"Fixing double-versioned field {field_name}", False)

                                # Try to decrypt directly
                                try:
                                    decrypted_value = db_encryption.decrypt(actual_encrypted_text)


                                    # If decryption was successful, re-encrypt with proper versioning
                                    if decrypted_value != actual_encrypted_text:
                                        new_encrypted_value = db_encryption.encrypt(decrypted_value)
                                        setattr(self, field_name, f"{db_encryption.VERSION_PREFIX}{new_encrypted_value}")
                                        DebugService.app_debug_print(f"Re-encrypted double-versioned field {field_name}", False)
                                    else:
                                        # Fix the format without decrypting
                                        setattr(self, field_name, f"{db_encryption.VERSION_PREFIX}{CURRENT_KEY_VERSION}:{actual_encrypted_text}")
                                        DebugService.app_debug_print(f"Fixed format of double-versioned field {field_name}", False)
                                except Exception as e:
                                    DebugService.app_debug_print(f"Error decrypting double-versioned field {field_name}: {e}", True)
                                    # Fix the format without decrypting
                                    setattr(self, field_name, f"{db_encryption.VERSION_PREFIX}{CURRENT_KEY_VERSION}:{actual_encrypted_text}")
                            except Exception as e:
                                DebugService.app_debug_print(f"Error fixing double-versioned field {field_name}: {e}", True)

                        # Handle old-style encrypted value without version (enc:gAAAAA...)
                        elif ":" not in field_value[7:]:
                            try:
                                # Old-style encrypted value without version - add version
                                old_encrypted_value = field_value[7:]  # Remove "enc:" or "ENC:" prefix
                                DebugService.app_debug_print(f"Adding version to old-style encrypted field {field_name}", False)

                                # Try to decrypt with current key
                                try:
                                    decrypted_value = db_encryption.decrypt(old_encrypted_value)

                                    # If decryption was successful, re-encrypt with version tracking
                                    if decrypted_value != old_encrypted_value:
                                        new_encrypted_value = db_encryption.encrypt(decrypted_value)
                                        setattr(self, field_name, f"{db_encryption.VERSION_PREFIX}{new_encrypted_value}")
                                        DebugService.app_debug_print(f"Re-encrypted old-style field {field_name}", False)
                                    else:
                                        # Failed to decrypt - just add version
                                        setattr(self, field_name, f"{db_encryption.VERSION_PREFIX}{CURRENT_KEY_VERSION}:{old_encrypted_value}")
                                        DebugService.app_debug_print(f"Added version to old-style field {field_name}", False)
                                except Exception as e:
                                    DebugService.app_debug_print(f"Error decrypting old-style field {field_name}: {e}", True)
                                    # Add version without decrypting
                                    setattr(self, field_name, f"{db_encryption.VERSION_PREFIX}{CURRENT_KEY_VERSION}:{old_encrypted_value}")
                            except Exception as e:
                                DebugService.app_debug_print(f"Error processing old-style field {field_name}: {e}", True)

                        # Handle already properly encrypted value (enc:v1:gAAAAA...)
                        elif field_value.lower().startswith(db_encryption.VERSION_PREFIX + "v"):
                            # Already properly encrypted with version - check if it needs re-encryption
                            try:
                                # Extract version and encrypted text
                                parts = field_value[7:].split(":", 1)
                                if len(parts) == 2:
                                    version, encrypted_text = parts

                                    # If not using current key version, try to re-encrypt
                                    if version != CURRENT_KEY_VERSION:
                                        DebugService.app_debug_print(f"Field {field_name} uses old key version {version}, current is {CURRENT_KEY_VERSION}", False)

                                        try:
                                            # Try to decrypt with the old version
                                            decrypted_value = db_encryption.decrypt(f"{version}:{encrypted_text}")

                                            # If decryption was successful, re-encrypt with current version
                                            if decrypted_value != f"{version}:{encrypted_text}":
                                                new_encrypted_value = db_encryption.encrypt(decrypted_value)
                                                setattr(self, field_name, f"{db_encryption.VERSION_PREFIX}{new_encrypted_value}")
                                                DebugService.app_debug_print(f"Re-encrypted field {field_name} with current key version", False)
                                        except Exception as e:
                                            DebugService.app_debug_print(f"Error re-encrypting field {field_name} with old version: {e}", True)
                            except Exception as e:
                                DebugService.app_debug_print(f"Error processing versioned field {field_name}: {e}", True)

    @model_validator(mode="before")
    def ensure_auto_generated_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically generate values for fields marked with 'auto_generate' in their metadata.
        """
        for field_name, field in cls.model_fields.items():
            # Retrieve metadata for the field
            meta = field.json_schema_extra or {}
            if meta.get("auto_generate") and not values.get(field_name):
                generator_type = meta.get("generator_type")

                # Validate generator_type against GeneratorType Enum
                if generator_type not in AppGeneratorType.__members__.values():
                    raise ValueError(f"Invalid generator_type: {generator_type} for field {field_name}")

                # Apply the appropriate generator
                if generator_type == AppGeneratorType.HASH_FROM_NAME:
                    values[field_name] = BaseModelUtils.generate_hash_from_name(values.get("name"))
                elif generator_type == AppGeneratorType.UUID:
                    values[field_name] = BaseModelUtils.generate_uuid()
                elif generator_type == AppGeneratorType.CUSTOM:
                    custom_generator = meta.get("custom_generator")
                    if callable(custom_generator):
                        values[field_name] = custom_generator(values)
                    else:
                        raise ValueError(f"Invalid custom_generator for field {field_name}")

        return values



    @model_validator(mode="before")
    def convert_id_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically convert all fields ending with '_id' to ObjectId.
        Handles cases where translated fields store ObjectIds as dictionaries.
        """
        for key, value in values.items():
            if key.endswith("_id"):
                # Handle None values for parent entities
                if value is None:
                    continue

                # If the value is a dictionary (translated format), extract the display_value
                if isinstance(value, dict) and "display_value" in value:
                    value = value["display_value"]

                # Convert to ObjectId if it's still a string
                if isinstance(value, str):
                    try:
                        values[key] = ObjectId(value)
                    except Exception as e:
                        raise ValueError(f"Invalid ObjectId format for field '{key}': {value}") from e

        return values

    @staticmethod
    def _convert_id_fields_to_str(data):
        """
        Recursively convert all fields ending with '_id' to strings.

        This ensures that ObjectId fields are properly serialized to strings
        when serializing a model.

        Only converts simple values (ObjectId, int, etc.) to strings, not dicts or lists
        which may be formatted output structures.

        Args:
            data: The data to convert (dict, list, or other)

        Returns:
            The data with all _id fields converted to strings
        """
        if isinstance(data, dict):
            result = {}
            for k, v in data.items():
                if k.endswith('_id') and v is not None and not isinstance(v, (str, dict, list)):
                    # Only convert simple values (ObjectId, int, etc.) to strings
                    result[k] = str(v)
                elif isinstance(v, (dict, list)):
                    # Recursively process nested structures
                    result[k] = BaseModelMixin._convert_id_fields_to_str(v)
                else:
                    result[k] = v
            return result
        elif isinstance(data, list):
            return [BaseModelMixin._convert_id_fields_to_str(item) for item in data]
        return data

    # Note: Removed model_serializer decorator as it was interfering with internal model operations
    # The _id to string conversion is handled at the GenericService fetch method return points instead

    async def process_field_for_properties(
        self,
        field_name: str,
        field: Any,
        field_value: Any,
        accept_language: str = DEFAULT_LANGUAGE,
        generic_service = None
    ) -> FieldTranslation:
        """
        Process a single field for the formatted_properties method.
        This helper function handles all the field processing logic and can be used
        for both regular fields and array elements.

        Args:
            field_name: The name of the field
            field: The field object with metadata
            field_value: The value of the field
            accept_language: The language code for translations
            generic_service: The GenericService instance to use for data fetching

        Returns:
            FieldTranslation object for the field
        """
        # Handle special cases for primitive types that don't need complex processing
        if isinstance(field_value, bool):
            # For boolean values, create a simple FieldTranslation with default values
            return FieldTranslation(
                property_name=field_name,
                property_value=field_value,
                may_have_translation=False,
                data_type={"is_boolean": True},
                to_be_translated_in_front=False
            )

        # Extract metadata for the field
        meta = field.json_schema_extra or {}
        # field
        DebugService.app_debug_print(f"field >. {field}")
        # For debugging
        DebugService.app_debug_print(f"Processing field {field_name} for properties: {field_value}", False)
        db_encryption = DBEncryptionService()
        # Handle encrypted fields
        can_be_encrypted = meta.get("can_be_encrypted", False)
        if can_be_encrypted and isinstance(field_value, str) and field_value.lower().startswith(db_encryption.VERSION_PREFIX):
            # Try to get the decrypted value
            decrypted_value =  db_encryption.decrypt(field_value)
            field_value = decrypted_value

        # Handle select_source_model
        if 'select_source_model' in meta.get("extra_metas", {}):
            data_source_value = {}
            try:
                data_source = meta.get("extra_metas", {}).get('select_source_model', None)
                query = {
                    "filter___id": field_value
                }
                # Fetch data from the data_source collection
                input_select = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey(data_source),
                    output_data_type=OutputDataType.INPUT_SELECT.value,
                    query=query,
                    accept_language=accept_language
                )
                DebugService.app_debug_print(f"fetching in formater data for {field_name} : '{input_select}'", False)
                data_source_value = input_select
            except Exception as e:
                DebugService.app_debug_print(f"Error fetching data for >'{field_name}': {e}", False)

            return FieldTranslation(
                property_name=field_name,
                property_value=field_value,
                may_have_translation=meta.get("may_have_translation", False),
                data_type=meta.get("data_type", {"is_string": True}),  # Default to string
                to_be_translated_in_front=meta.get("to_be_translated_in_front", False),
                extra_metas={
                    **meta.get("extra_metas", {}),
                    "data_source_value": data_source_value,
                }
            )

        # Handle cascade_source_model
        elif 'cascade_source_model' in meta.get("extra_metas", {}):
            data_source_value = {}
            try:
                cascade_data_source = meta.get("extra_metas", {}).get('cascade_source_model', None)
                query = {
                    "filter___id": field_value
                }
                # Fetch data from the cascade_source_model collection
                input_select = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey(cascade_data_source),
                    output_data_type=OutputDataType.INPUT_SELECT.value,
                    query=query,
                    accept_language=accept_language
                )
                DebugService.app_debug_print(f"fetching cascade data for {field_name} : '{input_select}'", False)
                data_source_value = input_select
            except Exception as e:
                DebugService.app_debug_print(f"Error fetching cascade data for >'{field_name}': {e}", False)

            return FieldTranslation(
                property_name=field_name,
                property_value=field_value,
                may_have_translation=meta.get("may_have_translation", False),
                data_type=meta.get("data_type", {"is_string": True}),  # Default to string
                to_be_translated_in_front=meta.get("to_be_translated_in_front", False),
                extra_metas={
                    **meta.get("extra_metas", {}),
                    "data_source_value": data_source_value,
                }
            )

        # Handle is_amount data type with currency properties
        elif meta.get("data_type", {}).get("is_amount", False) and 'currency_props' in meta.get("extra_metas", {}) and 'currency_data_source' in meta.get("extra_metas", {}):
            data_source_value = {}
            try:
                currency_prop = meta.get("extra_metas", {}).get('currency_props', None)
                data_source = meta.get("extra_metas", {}).get('currency_data_source', None)

                # Get the currency ID from the specified property
                currency_id = getattr(self, currency_prop, None)

                if currency_id:
                    query = {
                        "filter___id": currency_id
                    }
                    # Fetch currency data from the data_source collection
                    currency_data = await generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey(data_source),
                        output_data_type=OutputDataType.INPUT_SELECT.value,
                        query=query,
                        accept_language=accept_language
                    )
                    DebugService.app_debug_print(f"Fetching currency data for {field_name} with {currency_prop}={currency_id}: '{currency_data}'", False)
                    data_source_value = currency_data
            except Exception as e:
                DebugService.app_debug_print(f"Error fetching currency data for >'{field_name}': {e}", False)

            return FieldTranslation(
                property_name=field_name,
                property_value=field_value,
                may_have_translation=meta.get("may_have_translation", False),
                data_type=meta.get("data_type", {"is_amount": True}),
                to_be_translated_in_front=meta.get("to_be_translated_in_front", False),
                extra_metas={
                    **meta.get("extra_metas", {}),
                    "data_source_value": data_source_value,
                }
            )

        # Handle is_enum data type with enum_data_source
        elif meta.get("data_type", {}).get("is_enum", False) and 'enum_data_source' in meta.get("extra_metas", {}):
            data_source_value = []
            current_enum_value = field_value
            translated_display_value = None

            try:
                from app.modules.core.services.translation.translation_service import TranslationService

                # Get the enum class name from the metadata
                enum_class_name = meta.get("extra_metas", {}).get('enum_data_source', None)
                DebugService.app_debug_print(f" fetching enum enum_class_name for >'{field_name}': {enum_class_name}", False)
                if enum_class_name:
                    # Get the enum class from the string
                    enum_class = TranslationService.get_enum_class_from_string(enum_class_name)
                    DebugService.app_debug_print(f" fetching enum enum_class for >'{field_name}': {enum_class}", False)
                    # Get the translated values for the enum
                    enum_values = TranslationService.get_enum_translated_data_list(
                        enum_class=enum_class,
                        property_name_str=field_name,
                        accept_language=accept_language
                    )
                    DebugService.app_debug_print(f" fetching enum enum_values for >'{field_name}': {enum_values}", False)
                    # Find the translated display value for the current enum value
                    for enum_item in enum_values:
                        if enum_item["id"] == current_enum_value:
                            translated_display_value = enum_item["display_value"]
                            break

                    DebugService.app_debug_print(f"Fetching enum data for {field_name} with enum_data_source={enum_class_name}: '{enum_values}'", False)
                    DebugService.app_debug_print(f"Current enum value: {current_enum_value}, Translated display value: {translated_display_value}", False)

                    data_source_value = enum_values
            except Exception as e:
                DebugService.app_debug_print(f"Error fetching enum data for >'{field_name}': {e}", False)

            return FieldTranslation(
                property_name=field_name,
                property_value=field_value,
                may_have_translation=meta.get("may_have_translation", False),
                data_type=meta.get("data_type", {"is_enum": True}),
                to_be_translated_in_front=meta.get("to_be_translated_in_front", False),
                extra_metas={
                    **meta.get("extra_metas", {}),
                    "data_source_value": data_source_value,
                    "translated_display_value": translated_display_value
                }
            )

        # Handle is_array_of_object data type
        elif meta.get("data_type", {}).get("is_array_of_object", False) and isinstance(field_value, list):
            DebugService.app_debug_print(f"[DEBUG] process_field_for_properties: Processing {field_name} as array_of_object", False)
            DebugService.app_debug_print(f"[DEBUG] process_field_for_properties: meta.get('data_type'): {meta.get('data_type', {})}", False)
            DebugService.app_debug_print(f"[DEBUG] process_field_for_properties: isinstance(field_value, list): {isinstance(field_value, list)}", False)
            processed_array = []
            for item in field_value:
                if isinstance(item, dict):
                    processed_item = {}
                    for item_field_name, item_field_value in item.items():
                        # Find the field definition in the model
                        if item_field_name in self.model_fields:
                            item_field = self.model_fields[item_field_name]
                            # Process this field using the same helper function
                            processed_field = await self.process_field_for_properties(
                                item_field_name,
                                item_field,
                                item_field_value,
                                accept_language,
                                generic_service
                            )
                            processed_item[item_field_name] = processed_field
                    processed_array.append(processed_item)

            return FieldTranslation(
                property_name=field_name,
                property_value=processed_array,
                may_have_translation=meta.get("may_have_translation", False),
                data_type=meta.get("data_type", {"is_array_of_object": True}),
                to_be_translated_in_front=meta.get("to_be_translated_in_front", False),
                extra_metas=meta.get("extra_metas", {})
            )

        # Handle other fields with metadata
        elif meta:
            DebugService.app_debug_print(f"[DEBUG] process_field_for_properties: Processing {field_name} as regular field with metadata", False)
            DebugService.app_debug_print(f"[DEBUG] process_field_for_properties: meta.get('data_type'): {meta.get('data_type', {})}", False)
            return FieldTranslation(
                property_name=field_name,
                property_value=field_value,
                may_have_translation=meta.get("may_have_translation", False),
                data_type=meta.get("data_type", {"is_string": True}),  # Default to string
                to_be_translated_in_front=meta.get("to_be_translated_in_front", False),
                extra_metas=meta.get("extra_metas", {})
            )

        # Handle fields without metadata
        else:
            return FieldTranslation(
                property_name=field_name,
                property_value=field_value,
                may_have_translation=False,
                data_type={"is_string": True},  # Default to string
                to_be_translated_in_front=False
            )

    async def formatted_properties(self, accept_language: str = DEFAULT_LANGUAGE,collection_key:Optional[CollectionKey] = CollectionKey.REF_MFAS,force_exclude_fields: Optional[list] = None) -> Dict[str, Any]:
        """
        Automatically generates translated fields using metadata, with sorted priority fields.
        """
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(accept_language)
        properties = {}
        priority_fields = ["id", "identifier", "name"]  # Fields to prioritize at the start
        trailing_fields = ["created_at", "updated_at", "deleted_at"]  # Fields to prioritize at the end

        if force_exclude_fields is None:
            force_exclude_fields = []

        for field_name, field in self.model_fields.items():
            # Skip certain fields
            if field_name == 'revision_id' or field_name == 'translations' or field_name == 'encryptions' or field_name in force_exclude_fields:
                continue

            # Extract metadata for the field
            meta = field.json_schema_extra or {}

            # Check filter_based_on_key_value condition
            filter_condition = meta.get("extra_metas", {}).get("filter_based_on_key_value")
            if filter_condition and isinstance(filter_condition, str):
                DebugService.app_debug_print(f"[DEBUG] Field {field_name} has filter condition: {filter_condition}", False)
                try:
                    # Parse the filter condition (format: "field_name,expected_value")
                    condition_parts = filter_condition.split(",", 1)
                    if len(condition_parts) == 2:
                        condition_field, expected_value = condition_parts
                        condition_field = condition_field.strip()
                        expected_value = expected_value.strip()

                        # Validate that the condition field exists in the model
                        if condition_field not in self.model_fields:
                            DebugService.app_debug_print(f"[WARNING] Filter condition field '{condition_field}' not found in model for field {field_name}", True)
                            continue

                        # Get the actual value of the condition field from the model instance
                        actual_value = getattr(self, condition_field, None)

                        # Handle enum values - convert to string representation
                        if hasattr(actual_value, 'value'):
                            actual_value_str = str(actual_value.value)
                        elif actual_value is not None:
                            actual_value_str = str(actual_value)
                        else:
                            actual_value_str = None

                        DebugService.app_debug_print(f"[DEBUG] Filter condition check for {field_name}: {condition_field}='{actual_value_str}' should equal '{expected_value}'", False)

                        # Skip field if condition doesn't match
                        if actual_value_str != expected_value:
                            DebugService.app_debug_print(f"[DEBUG] Skipping field {field_name} due to filter condition mismatch: {actual_value_str} != {expected_value}", False)
                            continue
                        else:
                            DebugService.app_debug_print(f"[DEBUG] Field {field_name} passes filter condition: {actual_value_str} == {expected_value}", False)
                    else:
                        DebugService.app_debug_print(f"[WARNING] Invalid filter_based_on_key_value format for field {field_name}: {filter_condition}", True)
                except Exception as e:
                    DebugService.app_debug_print(f"[ERROR] Error processing filter condition for field {field_name}: {e}", True)
                    # Continue processing the field if there's an error in the filter condition

            # Skip fields marked with `exclude_from_data_table` or `exclude_at_all`
            if meta.get("exclude_from_data_table", False) or meta.get("exclude_at_all", False):
                continue

            # Get the field value
            field_value = getattr(self, field_name)

            # Process the field using the helper function
            properties[field_name] = await self.process_field_for_properties(
                field_name,
                field,
                field_value,
                accept_language,
                generic_service
            )

        # Sort properties: Priority fields first, then others alphabetically, trailing fields last
        sorted_properties = {field_name: properties[field_name] for field_name in sorted(
            properties.keys(),
            key=lambda x: (
                0 if x in priority_fields else (2 if x in trailing_fields else 1),  # Priority: 0 (first), 1 (middle), 2 (last)
                priority_fields.index(x) if x in priority_fields else float("inf"),  # Priority field order
                x  # Alphabetical order for middle fields
            )
        )}

        # Get model name for translation context
        settings = getattr(self, 'Settings', None)
        if settings and hasattr(settings, 'name'):
            model_name = settings.name
        else:
            model_name = self.__class__.__name__.lower()

        # Return the formatted properties
        return await BaseModelUtils.get_fields_translation(
            targeted_id=self.id,
            short_code=accept_language,
            add_timestamps=True,
            properties=sorted_properties,
            model_name=model_name
        )

    # Cache for translations to avoid repeated API calls
    _google_translation_cache = {}

    async def transform_overview_data(self, field_name: str, field: Any, field_value: Any, accept_language: str = DEFAULT_LANGUAGE) -> Dict[str, Any]:
        """
        Transform a field for overview data display.

        This method processes a field based on its overview_data_type metadata.
        It handles special cases like is_array_of_object by recursively processing each element.

        Args:
            field_name: The name of the field
            field: The field object with metadata
            field_value: The value of the field
            accept_language: The language code for translations

        Returns:
            Dict containing the transformed field data
        """
        # Extract metadata for the field
        meta = field.json_schema_extra or {}
        overview_data_type = meta.get("overview_data_type", {})
        db_encryption = DBEncryptionService()

        # Skip fields without overview_data_type
        if not overview_data_type:
            return None

        # Handle encrypted fields
        can_be_encrypted = meta.get("can_be_encrypted", False)
        if can_be_encrypted and isinstance(field_value, str) and field_value.lower().startswith(db_encryption.VERSION_PREFIX):
            # Decrypt the field value
            decrypted_value = db_encryption.decrypt(field_value)
            # Use the decrypted value for further processing
            field_value = decrypted_value

        # Handle is_array_of_object data type
        if overview_data_type.get("is_array_of_object", False) and isinstance(field_value, list):
            transformed_array = []
            for item in field_value:
                # For each item in the array, process all its fields
                if isinstance(item, dict):
                    transformed_item = {}
                    for item_field_name, item_field_value in item.items():
                        # Find the field definition in the model
                        if item_field_name in self.model_fields:
                            item_field = self.model_fields[item_field_name]
                            # Get the item field's metadata
                            item_meta = item_field.json_schema_extra or {}
                            item_overview_data_type = item_meta.get("overview_data_type", {})

                            # Check if this field is encrypted
                            item_can_be_encrypted = item_meta.get("can_be_encrypted", False)
                            if item_can_be_encrypted and isinstance(item_field_value, str) and item_field_value.lower().startswith(db_encryption.VERSION_PREFIX):
                                # For array items, we need to decrypt manually since we don't have a direct field access

                                decrypted_value =  db_encryption.decrypt(item_field_value)
                                # Only use decrypted value if decryption was successful
                                item_field_value = decrypted_value

                            # Only process fields with overview_data_type
                            if item_overview_data_type:
                                # Recursively transform this field
                                transformed_field = await self.transform_overview_data(
                                    item_field_name,
                                    item_field,
                                    item_field_value,
                                    accept_language
                                )
                                if transformed_field:
                                    transformed_item[item_field_name] = transformed_field

                    # Only add non-empty items
                    if transformed_item:
                        transformed_array.append(transformed_item)

            return {
                "display_title": field_name,
                "display_value": transformed_array,
                "data_type": overview_data_type,
                "extra_metas": meta.get("extra_metas", {})
            }

        # Handle other data types
        return {
            "display_title": field_name,
            "display_value": field_value,
            "data_type": overview_data_type,
            "extra_metas": meta.get("extra_metas", {})
        }

    async def process_overview_data(self, accept_language: str = DEFAULT_LANGUAGE, force_include_fields: Optional[list] = []) -> Dict[str, Any]:
        """
        Process fields with overview_data_type.

        This method extracts fields with overview_data_type metadata and transforms them
        for overview display. It handles special cases like is_array_of_object by recursively
        processing each element.

        Args:
            accept_language: The language code for translations
            force_include_fields: List of fields to include even if they are None

        Returns:
            Dict containing the transformed overview data
        """
        overview_data = {}
        for field_name, field in self.model_fields.items():
            # Skip fields that should be excluded
            meta = field.json_schema_extra or {}
            if meta.get("exclude_from_data_table", False) or meta.get("exclude_at_all", False):
                continue

            # Get the field value
            field_value = getattr(self, field_name, None)

            # Skip None values unless forced to include
            if field_value is None and field_name not in force_include_fields:
                continue

            # Transform the field for overview data
            transformed_field = await self.transform_overview_data(field_name, field, field_value, accept_language)
            if transformed_field:
                overview_data[field_name] = transformed_field

        return overview_data 

    async def formatted_properties_for_default(self, accept_language: str = DEFAULT_LANGUAGE, base_model_class: Optional[Type] = None, collection_key: Optional[CollectionKey] = CollectionKey.REF_MFAS, force_include_fields: Optional[list] = None,
        sort: Optional[Dict[str, int]] = None, doc: Optional[Dict[str, Any]] = None, force_exclude_fields: Optional[list] = None) -> Dict[str, Any]:
        """
        Format properties for default output.

        This method formats the model properties for default output.
        Optimized for performance.

        Args:
            accept_language: The language code for translations
            base_model_class: Optional base model class to use for formatting
            collection_key: The collection key for the model
            force_include_fields: List of fields to include even if they are None
            sort: Sort order for the data
            doc: Optional document data to use instead of model instance fields.
                 If provided, only the fields in the document will be formatted.
            force_exclude_fields: List of fields to exclude from the output

        Returns:
            Dict containing the formatted properties rbac_profile_id
        """
        try:
            DebugService.app_debug_print(f"[DEBUG] formatted_properties_for_default START with doc: {doc}", False)
            DebugService.app_debug_print(f"[DEBUG] formatted_properties_for_default START with doc: {type(doc)}", False)
            DebugService.app_debug_print(f"[DEBUG] self class: {self.__class__.__name__}", False)
            DebugService.app_debug_print(f"[DEBUG] accept_language: {accept_language}", False)
            DebugService.app_debug_print(f"[DEBUG] force_include_fields: {force_include_fields}", False)
            DebugService.app_debug_print(f"[DEBUG] force_exclude_fields: {force_exclude_fields}", False)

            # CRITICAL: Check doc parameter type immediately
            if doc is not None and not isinstance(doc, dict):
                DebugService.app_debug_print(f"[CRITICAL ERROR] doc parameter is not a dictionary! Type: {type(doc)}, Value: {doc}", False)
                # Convert to dict if it's a string that looks like JSON
                if isinstance(doc, str):
                    try:
                        import json
                        doc = json.loads(doc)
                        DebugService.app_debug_print(f"[DEBUG] Successfully parsed doc as JSON: {doc}", False)
                    except Exception as e:
                        DebugService.app_debug_print(f"[ERROR] Failed to parse doc as JSON: {e}", True)
                        # Return empty result if we can't parse the doc
                        return {}
                else:
                    DebugService.app_debug_print(f"[ERROR] doc is not a string or dict, cannot process", False)
                    return {}

            # Use default values if not provided append
            if force_include_fields is None:
                force_include_fields = []
                DebugService.app_debug_print("[DEBUG] Initialized force_include_fields to empty list", False)
            if force_exclude_fields is None:
                force_exclude_fields = []
                DebugService.app_debug_print("[DEBUG] Initialized force_exclude_fields to empty list", False)
            if sort is None:
                sort = {"created_at": -1}
                DebugService.app_debug_print("[DEBUG] Initialized sort to default", False)

            # Initialize properties variable to avoid UnboundLocalError
            properties = {}

            # If a document is provided, use it instead of the model instance fields
            if doc is not None:
                DebugService.app_debug_print(f"[DEBUG] Processing with provided document. Type: {type(doc)}, Value: {doc}", False)

                # Ensure we have an ID field
                DebugService.app_debug_print(f"[DEBUG] Checking ID field in doc: _id in doc: {'_id' in doc}, id in doc: {'id' in doc}", False)
                if "_id" in doc and "id" not in doc:
                    doc["id"] = str(doc["_id"])
                    DebugService.app_debug_print(f"[DEBUG] Added id field from _id: {doc['id']}", False)
                elif "id" not in doc and "_id" not in doc and hasattr(self, "id"):
                    doc["id"] = str(self.id)
                DebugService.app_debug_print(f"[DEBUG] Added id field from self.id: {doc['id']}", False)

            # Ensure translations dictionary exists
            if doc is not None:
                DebugService.app_debug_print(f"[DEBUG] Checking translations: translations in doc: {'translations' in doc}, hasattr(self, 'translations'): {hasattr(self, 'translations')}", False)
                if "translations" not in doc and hasattr(self, "translations"):
                    doc["translations"] = self.translations or {}
                    DebugService.app_debug_print("[DEBUG] Added translations from self.translations", False)
            else:
                DebugService.app_debug_print("[DEBUG] doc is None, skipping translations check", False)

            # Process only the fields that exist in the document
            if doc is not None:
                DebugService.app_debug_print(f"[DEBUG] Processing fields in document. Total fields: {len(doc)}", False)
                for field_name, field_value in doc.items():
                    DebugService.app_debug_print(f"[DEBUG] Processing field: {field_name}, value type: {type(field_value)}", False)

                    # Skip internal fields and excluded fields
                    if field_name.startswith('_') or field_name == 'translations' or field_name == 'encryptions' or field_name in force_exclude_fields:
                        DebugService.app_debug_print(f"[DEBUG] Skipping field {field_name} (internal or excluded)", False)
                        continue

                    # Get field metadata if available
                    field_meta = None
                    if field_name in self.model_fields:
                        DebugService.app_debug_print(f"[DEBUG] Field {field_name} exists in model_fields", False)
                        field = self.model_fields[field_name]
                        field_meta = field.json_schema_extra or {}
                        DebugService.app_debug_print(f"[DEBUG] Field {field_name} metadata: {field_meta}", False)

                        # Check filter_based_on_key_value condition
                        filter_condition = field_meta.get("extra_metas", {}).get("filter_based_on_key_value")
                        if filter_condition and isinstance(filter_condition, str):
                            DebugService.app_debug_print(f"[DEBUG] Field {field_name} has filter condition: {filter_condition}", False)
                            try:
                                # Parse the filter condition (format: "field_name,expected_value")
                                condition_parts = filter_condition.split(",", 1)
                                if len(condition_parts) == 2:
                                    condition_field, expected_value = condition_parts
                                    condition_field = condition_field.strip()
                                    expected_value = expected_value.strip()

                                    # Validate that the condition field exists in the model
                                    if condition_field not in self.model_fields:
                                        DebugService.app_debug_print(f"[WARNING] Filter condition field '{condition_field}' not found in model for field {field_name}", True)
                                        continue

                                    # Get the actual value of the condition field from the document
                                    actual_value = doc.get(condition_field) if doc else getattr(self, condition_field, None)

                                    # Handle enum values - convert to string representation
                                    if hasattr(actual_value, 'value'):
                                        actual_value_str = str(actual_value.value)
                                    elif actual_value is not None:
                                        actual_value_str = str(actual_value)
                                    else:
                                        actual_value_str = None

                                    DebugService.app_debug_print(f"[DEBUG] Filter condition check for {field_name}: {condition_field}='{actual_value_str}' should equal '{expected_value}'", False)

                                    # Skip field if condition doesn't match
                                    if actual_value_str != expected_value:
                                        DebugService.app_debug_print(f"[DEBUG] Skipping field {field_name} due to filter condition mismatch: {actual_value_str} != {expected_value}", False)
                                        continue
                                    else:
                                        DebugService.app_debug_print(f"[DEBUG] Field {field_name} passes filter condition: {actual_value_str} == {expected_value}", False)
                                else:
                                    DebugService.app_debug_print(f"[WARNING] Invalid filter_based_on_key_value format for field {field_name}: {filter_condition}", True)
                            except Exception as e:
                                DebugService.app_debug_print(f"[ERROR] Error processing filter condition for field {field_name}: {e}", True)
                                # Continue processing the field if there's an error in the filter condition

                        # Skip fields marked with `exclude_from_default` or `exclude_at_all`,
                        # but always include fields marked as essential_field
                        is_essential = field_meta.get("extra_metas", {}).get("essential_field", False) or field_name == "id"
                        if (field_meta.get("exclude_from_default", False) or field_meta.get("exclude_at_all", False)) and not is_essential:
                            DebugService.app_debug_print(f"[DEBUG] Skipping field {field_name} (excluded by metadata)", False)
                            continue
                        elif (field_meta.get("exclude_from_default", False) or field_meta.get("exclude_at_all", False)) and is_essential:
                            DebugService.app_debug_print(f"[DEBUG] Including essential field {field_name} despite exclusion metadata", False)
                    else:
                        # Field exists in document but not in model - skip it to avoid errors
                        DebugService.app_debug_print(f"[DEBUG] Field {field_name} exists in document but not in model - skipping", False)
                        continue

                    # Handle encrypted fields
                    can_be_encrypted = field_meta.get("can_be_encrypted", False) if field_meta else False
                    if can_be_encrypted:
                        DebugService.app_debug_print(f"\n\n\n can_be_encrypted {can_be_encrypted} : {field_value}",False)
                        db_encryption = DBEncryptionService()
                        # Check if the field value is encrypted
                        if isinstance(field_value, str) and field_value.lower().startswith(db_encryption.VERSION_PREFIX):
                            # Try to get the decrypted value
                            DebugService.app_debug_print(f"\n\n\n START WITH {field_name} : {field_value}",False)
                            try:
                                decrypted_value = db_encryption.decrypt(field_value)
                                DebugService.app_debug_print(f"\n\n\n decrypted {field_name} : {decrypted_value}",False)
                                field_value = decrypted_value
                            except Exception as e:
                                DebugService.app_debug_print(f"Error decrypting field {field_name}: {e}", True)
                        else:
                            DebugService.app_debug_print(f"\n\n\n NOT START WITH {field_name} : {field_value}",False)

                    # Handle translatable fields
                    # Add safety check for field_meta type
                    if field_meta and not isinstance(field_meta, dict):
                        DebugService.app_debug_print(f"[ERROR] field_meta is not a dict for field {field_name}. Type: {type(field_meta)}, Value: {field_meta}", True)
                        field_meta = {}  # Reset to empty dict to avoid errors

                    may_have_translation = field_meta.get("may_have_translation", False) if field_meta else False
                    if may_have_translation and field_value is not None and isinstance(field_value, str):
                        # If the language is not French, try to get the translation
                        if accept_language != DEFAULT_LANGUAGE:
                            # Ensure field exists in translations dictionary
                            if "translations" in doc and field_name in doc["translations"]:
                                # Check if translation exists for this language
                                if accept_language in doc["translations"][field_name]:
                                    # Use existing translation
                                    translation_value = doc["translations"][field_name][accept_language]

                                    # Check if the translation is encrypted
                                    db_encryption = DBEncryptionService()
                                    if isinstance(translation_value, str) and translation_value.lower().startswith(db_encryption.VERSION_PREFIX):
                                        DebugService.app_debug_print(f"\n\n\n START WITH TRANSLATION {field_name} : {translation_value}",False)
                                        # Try to decrypt the translation
                                        try:
                                            decrypted_value = db_encryption.decrypt(translation_value)
                                            DebugService.app_debug_print(f"\n\n\n decrypted TRANSLATION {field_name} : {decrypted_value}",False)
                                            field_value = decrypted_value
                                        except Exception as e:
                                            DebugService.app_debug_print(f"Error decrypting translation for field {field_name}: {e}", True)
                                    else:
                                        DebugService.app_debug_print(f"\n\n\n NO START WITH TRANSLATION {field_name} : {translation_value}",False)
                                        field_value = translation_value

                    # Process the field if it exists in the model
                    if field_name in self.model_fields:
                        DebugService.app_debug_print(f"[DEBUG] Adding field {field_name} to properties (from model)", False)
                        try:
                            properties[field_name] = field_value
                            DebugService.app_debug_print(f"[DEBUG] Successfully added field {field_name}", False)
                        except Exception as e:
                            # If there's an error processing the field, log it and use the raw value
                            DebugService.app_debug_print(f"[ERROR] Error processing field {field_name}: {e}", True)
                            properties[field_name] = field_value
                    else:
                        # For fields not in the model, add them directly if they're not excluded
                        if field_name not in force_exclude_fields:
                            DebugService.app_debug_print(f"[DEBUG] Adding field {field_name} to properties (not in model)", False)
                            properties[field_name] = field_value
                # Sort properties if needed
                DebugService.app_debug_print(f"[DEBUG] Sorting properties. Properties count: {len(properties)}", False)
                if properties:
                    priority_fields = ["id", "identifier", "name"]
                    trailing_fields = ["created_at", "updated_at", "deleted_at"]
                    DebugService.app_debug_print(f"[DEBUG] Property keys before sorting: {list(properties.keys())}", False)

                    try:
                        sorted_properties = {field_name: properties[field_name] for field_name in sorted(
                            properties.keys(),
                            key=lambda x: (
                                0 if x in priority_fields else (2 if x in trailing_fields else 1),
                                priority_fields.index(x) if x in priority_fields else float("inf"),
                                x
                            )
                        )}
                        DebugService.app_debug_print(f"[DEBUG] Properties sorted successfully. Sorted keys: {list(sorted_properties.keys())}", False)
                    except Exception as e:
                        DebugService.app_debug_print(f"[ERROR] Error sorting properties: {e}", True)
                        sorted_properties = properties

                    # Print all properties before filtering
                    DebugService.app_debug_print(f"[DEBUG] All properties before filtering: {list(sorted_properties.keys())}", False)

                    # Apply force_include_fields filter if provided hidde_on_view_values
                    if force_include_fields:
                        DebugService.app_debug_print(f"[DEBUG] Applying force_include_fields: {force_include_fields}", False)

                        # Check if force_include_fields is a dictionary (like a sort parameter) instead of a list
                        if isinstance(force_include_fields, dict):
                            DebugService.app_debug_print("[DEBUG] force_include_fields is a dictionary, converting to list of keys", False)
                            force_include_fields = list(force_include_fields.keys())

                        # Ensure force_include_fields is a list
                        if not isinstance(force_include_fields, list):
                            DebugService.app_debug_print(f"[DEBUG] force_include_fields is not a list, converting from {type(force_include_fields)}", False)
                            try:
                                force_include_fields = list(force_include_fields)
                            except Exception as e:
                                DebugService.app_debug_print(f"[ERROR] Could not convert force_include_fields to list: {e}", True)
                                force_include_fields = []

                        # Always include 'id' field
                        if force_include_fields and 'id' not in force_include_fields:
                            force_include_fields.append('id')
                            DebugService.app_debug_print("[DEBUG] Added 'id' to force_include_fields", False)

                        DebugService.app_debug_print(f"[DEBUG] Final force_include_fields: {force_include_fields}", False)

                        # Check if we're only returning 'id' and 'created_at'
                        if set(force_include_fields) == {'id', 'created_at'}:
                            DebugService.app_debug_print("[DEBUG] WARNING: Only returning 'id' and 'created_at'", False)
                            DebugService.app_debug_print("[DEBUG] This is likely due to the sort parameter being passed as force_include_fields", False)
                            DebugService.app_debug_print("[DEBUG] Adding all properties to force_include_fields", False)
                            force_include_fields = list(sorted_properties.keys())

                        if force_include_fields:
                            # Print properties that will be included
                            included_props = [k for k in sorted_properties.keys() if k in force_include_fields]
                            DebugService.app_debug_print(f"[DEBUG] Properties that will be included: {included_props}", False)

                            # Print properties that will be excluded
                            excluded_props = [k for k in sorted_properties.keys() if k not in force_include_fields]
                            DebugService.app_debug_print(f"[DEBUG] Properties that will be excluded: {excluded_props}", False)

                            sorted_properties = {k: v for k, v in sorted_properties.items() if k in force_include_fields}
                            DebugService.app_debug_print(f"[DEBUG] Properties after force_include_fields: {list(sorted_properties.keys())}", False)

                    # Apply force_exclude_fields filter if provided
                    if force_exclude_fields:
                        DebugService.app_debug_print(f"[DEBUG] Applying force_exclude_fields: {force_exclude_fields}", False)
                        sorted_properties = {k: v for k, v in sorted_properties.items() if k not in force_exclude_fields}
                        DebugService.app_debug_print(f"[DEBUG] Properties after force_exclude_fields: {list(sorted_properties.keys())}", False)

                    DebugService.app_debug_print(f"[DEBUG] Returning sorted properties. Final count: {len(sorted_properties)}", False)

                    # If all fields were excluded and we have an empty result, include essential fields
                    if len(sorted_properties) == 0 or (len(sorted_properties) == 1 and 'id' in sorted_properties):
                        DebugService.app_debug_print("[DEBUG] All fields were excluded, including essential fields", False)

                        # Add id field if it exists in the document
                        if 'id' in doc and 'id' not in sorted_properties:
                            sorted_properties['id'] = doc['id']

                        # Add essential fields from the document
                        for field_name, field in self.model_fields.items():
                            field_meta = field.json_schema_extra or {}
                            is_essential = field_meta.get("extra_metas", {}).get("essential_field", False)
                            if is_essential and field_name in doc and field_name not in sorted_properties:
                                sorted_properties[field_name] = doc[field_name]
                                DebugService.app_debug_print(f"[DEBUG] Added essential field {field_name}: {doc[field_name]}", False)

                    return sorted_properties

                DebugService.app_debug_print("[DEBUG] No properties to sort, returning empty properties", False)

                # If all fields were excluded, include essential fields
                if len(properties) == 0:
                    DebugService.app_debug_print("[DEBUG] All fields were excluded, including essential fields", False)

                    # Add id field if it exists in the document
                    if doc and 'id' in doc:
                        properties['id'] = doc['id']

                    # Add essential fields from the document
                    if doc:
                        for field_name, field in self.model_fields.items():
                            field_meta = field.json_schema_extra or {}
                            is_essential = field_meta.get("extra_metas", {}).get("essential_field", False)
                            if is_essential and field_name in doc and field_name not in properties:
                                properties[field_name] = doc[field_name]
                                DebugService.app_debug_print(f"[DEBUG] Added essential field {field_name}: {doc[field_name]}", False)

                return properties
            else:
                # If no document is provided, use the model instance fields
                # This branch is currently not used but kept for compatibility
                DebugService.app_debug_print("[DEBUG] No document provided, using model instance fields", False)
                formatted_props = {}

                # Add id field
                DebugService.app_debug_print(f"[DEBUG] Checking for id field: hasattr(self, 'id'): {hasattr(self, 'id')}", False)
                if hasattr(self, "id") and self.id:
                    formatted_props["id"] = str(self.id)
                    DebugService.app_debug_print(f"[DEBUG] Added id field: {formatted_props['id']}", False)

                # Process each field in the model
                for field_name, field in self.model_fields.items():
                    # Skip internal fields and excluded fields
                    if field_name.startswith('_') or field_name == 'translations' or field_name == 'encryptions' or field_name in force_exclude_fields:
                        continue

                    # Get field metadata
                    field_meta = field.json_schema_extra or {}

                    # Check filter_based_on_key_value condition
                    filter_condition = field_meta.get("extra_metas", {}).get("filter_based_on_key_value")
                    if filter_condition and isinstance(filter_condition, str):
                        DebugService.app_debug_print(f"[DEBUG] Field {field_name} has filter condition: {filter_condition}", False)
                        try:
                            # Parse the filter condition (format: "field_name,expected_value")
                            condition_parts = filter_condition.split(",", 1)
                            if len(condition_parts) == 2:
                                condition_field, expected_value = condition_parts
                                condition_field = condition_field.strip()
                                expected_value = expected_value.strip()

                                # Validate that the condition field exists in the model
                                if condition_field not in self.model_fields:
                                    DebugService.app_debug_print(f"[WARNING] Filter condition field '{condition_field}' not found in model for field {field_name}", True)
                                    continue

                                # Get the actual value of the condition field from the model instance
                                actual_value = getattr(self, condition_field, None)

                                # Handle enum values - convert to string representation
                                if hasattr(actual_value, 'value'):
                                    actual_value_str = str(actual_value.value)
                                elif actual_value is not None:
                                    actual_value_str = str(actual_value)
                                else:
                                    actual_value_str = None

                                DebugService.app_debug_print(f"[DEBUG] Filter condition check for {field_name}: {condition_field}='{actual_value_str}' should equal '{expected_value}'", False)

                                # Skip field if condition doesn't match
                                if actual_value_str != expected_value:
                                    DebugService.app_debug_print(f"[DEBUG] Skipping field {field_name} due to filter condition mismatch: {actual_value_str} != {expected_value}", False)
                                    continue
                                else:
                                    DebugService.app_debug_print(f"[DEBUG] Field {field_name} passes filter condition: {actual_value_str} == {expected_value}", False)
                            else:
                                DebugService.app_debug_print(f"[WARNING] Invalid filter_based_on_key_value format for field {field_name}: {filter_condition}", True)
                        except Exception as e:
                            DebugService.app_debug_print(f"[ERROR] Error processing filter condition for field {field_name}: {e}", True)
                            # Continue processing the field if there's an error in the filter condition

                    # Skip fields marked with `exclude_from_default` or `exclude_at_all`,
                    # but always include fields marked as essential_field
                    is_essential = field_meta.get("extra_metas", {}).get("essential_field", False) or field_name == "id"
                    if (field_meta.get("exclude_from_default", False) or field_meta.get("exclude_at_all", False)) and not is_essential:
                        DebugService.app_debug_print(f"[DEBUG] Skipping field {field_name} (excluded by metadata)", True)
                        continue
                    elif (field_meta.get("exclude_from_default", False) or field_meta.get("exclude_at_all", False)) and is_essential:
                        DebugService.app_debug_print(f"[DEBUG] Including essential field {field_name} despite exclusion metadata", False)

                    # Get field value
                    field_value = getattr(self, field_name, None)

                    # Skip None values unless forced to include
                    if field_value is None and field_name not in force_include_fields:
                        continue

                    # Convert ObjectId to string
                    if isinstance(field_value, ObjectId) or field_name.endswith("_id") and ObjectId.is_valid(field_value):
                        field_value = str(field_value)

                    # Handle encrypted fields
                    can_be_encrypted = field_meta.get("can_be_encrypted", False)
                    if can_be_encrypted:
                        DebugService.app_debug_print(f"\n\n\n can_be_encrypted {can_be_encrypted} : {field_value}",True)
                        db_encryption = DBEncryptionService()
                        # Check if the field value is encrypted
                        if isinstance(field_value, str) and field_value.lower().startswith(db_encryption.VERSION_PREFIX):
                            # Try to get the decrypted value
                            DebugService.app_debug_print(f"\n\n\n START WITH {field_name} : {field_value}",True)
                            try:
                                decrypted_value = db_encryption.decrypt(field_value)
                                DebugService.app_debug_print(f"\n\n\n decrypted {field_name} : {decrypted_value}",True)
                                field_value = decrypted_value
                            except Exception as e:
                                DebugService.app_debug_print(f"Error decrypting field {field_name}: {e}", True)
                        else:
                            DebugService.app_debug_print(f"\n\n\n NOT START WITH {field_name} : {field_value}",True)

                    # Handle translatable fields
                    # Add safety check for field_meta type
                    if not isinstance(field_meta, dict):
                        DebugService.app_debug_print(f"[ERROR] field_meta is not a dict for field {field_name}. Type: {type(field_meta)}, Value: {field_meta}", True)
                        field_meta = {}  # Reset to empty dict to avoid errors

                    may_have_translation = field_meta.get("may_have_translation", False)
                    if may_have_translation and field_value is not None and isinstance(field_value, str):
                        # If the language is not French, try to get the translation
                        if accept_language != DEFAULT_LANGUAGE:
                            # Ensure field exists in translations dictionary
                            if hasattr(self, "translations") and self.translations and field_name in self.translations:
                                # Check if translation exists for this language
                                if accept_language in self.translations[field_name]:
                                    # Use existing translation
                                    translation_value = self.translations[field_name][accept_language]

                                    # Check if the translation is encrypted
                                    db_encryption = DBEncryptionService()
                                    if isinstance(translation_value, str) and translation_value.lower().startswith(db_encryption.VERSION_PREFIX):
                                        DebugService.app_debug_print(f"\n\n\n START WITH TRANSLATION {field_name} : {translation_value}",False)
                                        # Try to decrypt the translation
                                        try:
                                            decrypted_value = db_encryption.decrypt(translation_value)
                                            DebugService.app_debug_print(f"\n\n\n decrypted TRANSLATION {field_name} : {decrypted_value}",False)
                                            field_value = decrypted_value
                                        except Exception as e:
                                            DebugService.app_debug_print(f"Error decrypting translation for field {field_name}: {e}", True)
                                    else:
                                        DebugService.app_debug_print(f"\n\n\n NO START WITH TRANSLATION {field_name} : {translation_value}",False)
                                        field_value = translation_value

                    # Add field to formatted properties
                    formatted_props[field_name] = field_value

                # Apply force_include_fields filter if provided
                if force_include_fields:
                    DebugService.app_debug_print(f"[DEBUG] Applying force_include_fields in else branch: {force_include_fields}", False)

                    # Check if force_include_fields is a dictionary (like a sort parameter) instead of a list
                    if isinstance(force_include_fields, dict):
                        DebugService.app_debug_print("[DEBUG] force_include_fields is a dictionary, converting to list of keys", False)
                        force_include_fields = list(force_include_fields.keys())

                    # Ensure force_include_fields is a list
                    if not isinstance(force_include_fields, list):
                        DebugService.app_debug_print(f"[DEBUG] force_include_fields is not a list, converting from {type(force_include_fields)}", False)
                        try:
                            force_include_fields = list(force_include_fields)
                        except Exception as e:
                            DebugService.app_debug_print(f"[ERROR] Could not convert force_include_fields to list: {e}", False)
                            force_include_fields = []

                    # Always include 'id' field
                    if force_include_fields and 'id' not in force_include_fields:
                        force_include_fields.append('id')
                        DebugService.app_debug_print("[DEBUG] Added 'id' to force_include_fields", False)

                    DebugService.app_debug_print(f"[DEBUG] Final force_include_fields: {force_include_fields}", False)

                    if force_include_fields:
                        formatted_props = {k: v for k, v in formatted_props.items() if k in force_include_fields}
                        DebugService.app_debug_print(f"[DEBUG] Properties after force_include_fields: {list(formatted_props.keys())}", False)

                # Apply force_exclude_fields filter if provided
                if force_exclude_fields:
                    formatted_props = {k: v for k, v in formatted_props.items() if k not in force_exclude_fields}

                # If all fields were excluded and we have an empty result, include essential fields
                if len(formatted_props) == 0 or (len(formatted_props) == 1 and 'id' in formatted_props):
                    DebugService.app_debug_print("[DEBUG] All fields were excluded, including essential fields", False)

                    # Add id field if it exists in the model
                    if hasattr(self, 'id') and self.id and 'id' not in formatted_props:
                        formatted_props['id'] = str(self.id)

                    # Add essential fields from the model
                    for field_name, field in self.model_fields.items():
                        field_meta = field.json_schema_extra or {}
                        is_essential = field_meta.get("extra_metas", {}).get("essential_field", False)
                        if is_essential and hasattr(self, field_name) and getattr(self, field_name) is not None and field_name not in formatted_props:
                            field_value = getattr(self, field_name)
                            if isinstance(field_value, ObjectId):
                                field_value = str(field_value)
                            formatted_props[field_name] = field_value
                            DebugService.app_debug_print(f"[DEBUG] Added essential field {field_name}: {field_value}", False)

                return formatted_props
        except Exception as e:
            import traceback
            DebugService.app_debug_print(f"[CRITICAL ERROR] Exception in formatted_properties_for_default: {e}", True)
            DebugService.app_debug_print(f"[CRITICAL ERROR] Traceback: {traceback.format_exc()}", False )
            DebugService.app_debug_print(f"[CRITICAL ERROR] doc type: {type(doc)}, doc value: {doc}", False)
            DebugService.app_debug_print(f"[CRITICAL ERROR] force_include_fields type: {type(force_include_fields)}, value: {force_include_fields}", False)
            DebugService.app_debug_print(f"[CRITICAL ERROR] force_exclude_fields type: {type(force_exclude_fields)}, value: {force_exclude_fields}", False)
            return {}


    async def formatted_properties_for_data_table(
        self,
        accept_language: str = DEFAULT_LANGUAGE,
        collection_key: Optional[CollectionKey] = CollectionKey.REF_MFAS,
        force_include_fields: Optional[list] = None,
        sort: Optional[Dict[str, int]] = None,
        doc: Optional[Dict[str, Any]] = None,
        force_exclude_fields: Optional[list] = None,
        hidde_on_view_values: Optional[dict] = None
    ) -> Dict[str, Any]:
        """
        Format properties for data_table output. 

        This method formats the model properties for data table output.
        Optimized for performance.

        Args:
            accept_language: The language code for translations
            collection_key: The collection key for the model
            force_include_fields: List of fields to include even if they are None
            sort: Sort order for the data
            doc: Optional document data to use instead of model instance fields.
                If provided, only the fields in the document will be formatted.
            force_exclude_fields: List of fields to exclude from output
            hidde_on_view_values: Dictionary of fields to hide from view

        Returns:
            Dict containing the formatted properties with structure:
            {
                "field_name": {
                    "display_title": str,
                    "display_value": Any,
                    "real_value": Any,
                    "data_type": Dict,
                    "meta": {
                        "to_be_translated_in_front": bool,
                        "may_have_translation": bool,
                        "missing_translation": bool,
                        ...
                    }
                }
            }
        """
        try:
            DebugService.app_debug_print(f"[DEBUG] ===== FORMATTED_PROPERTIES_FOR_DATA_TABLE START =====", False)
            DebugService.app_debug_print(f"[DEBUG] Method called with doc type: {type(doc)}", False)
            DebugService.app_debug_print(f"[DEBUG] Doc is None: {doc is None}", False)

            # Initialize default values
            force_include_fields = force_include_fields or []
            force_exclude_fields = force_exclude_fields or []
            sort = sort or {"created_at": -1}
            hidde_on_view_values = hidde_on_view_values or {}

            # Default excluded fields
            excludes = [
                'multiple_validation_status',
                'multiple_validated_at',
                'soft_deleted',
                'soft_deleted_at',
                'soft_deleted_by_id'
            ]
            force_exclude_fields.extend(excludes)

            DebugService.app_debug_print(f"[DEBUG] hidde_on_view_values field {hidde_on_view_values} (hidden on view)", False)

            # If a document is provided, use it instead of the model instance fields
            if doc is not None:
                DebugService.app_debug_print("[DEBUG] Processing with provided document", False)
                from app.modules.core.services.generic.generic_services import GenericService
                generic_service = GenericService(accept_language)
                properties = {}

                # Ensure we have an ID field is_select
                DebugService.app_debug_print(
                    f"[DEBUG] Checking ID field in doc: _id in doc: {'_id' in doc}, id in doc: {'id' in doc}", 
                    False
                )
                
                if "_id" in doc and "id" not in doc:
                    doc["id"] = str(doc["_id"])
                    DebugService.app_debug_print(f"[DEBUG] Added id field from _id: {doc['id']}", False)
                elif "id" not in doc and "_id" not in doc and hasattr(self, "id"):
                    doc["id"] = str(self.id)
                    DebugService.app_debug_print(f"[DEBUG] Added id field from self.id: {doc['id']}", False)

                # Ensure translations dictionary exists
                if "translations" not in doc and hasattr(self, "translations"):
                    doc["translations"] = self.translations or {}
                    DebugService.app_debug_print("[DEBUG] Added translations from model instance", False)

                # Process only the fields that exist in the document
                DebugService.app_debug_print(f"[DEBUG] Processing fields in document. Total fields: {len(doc)}", False)
                DebugService.app_debug_print(f"[DEBUG] All fields in document: {list(doc.keys())}", False)

                for field_name, field_value in doc.items():
                    try:
                        DebugService.app_debug_print(f"[DEBUG] Processing field: {field_name}, value type: {type(field_value)}", False)
                        DebugService.app_debug_print(f"[DEBUG] Field value sample: {str(field_value)[:100]}...", False)

                        # Skip internal fields and excluded fields
                        if (field_name.startswith('_') or
                            field_name in ('translations', 'encryptions') or
                            field_name in force_exclude_fields):
                            DebugService.app_debug_print(f"[DEBUG] Skipping field {field_name} (internal or excluded)", False)
                            continue

                        # Get field metadata if available
                        field_meta = None
                        if field_name in self.model_fields:
                            DebugService.app_debug_print(f"[DEBUG] Field {field_name} exists in model_fields", False)
                            field = self.model_fields[field_name]
                            field_meta = field.json_schema_extra or {}
                            DebugService.app_debug_print(f"[DEBUG] Field {field_name} metadata type: {type(field_meta)}", False)
                            DebugService.app_debug_print(f"[DEBUG] Field {field_name} metadata: {field_meta}", False)

                            # Safety check for field_meta
                            if not isinstance(field_meta, dict):
                                DebugService.app_debug_print(f"[ERROR] field_meta is not a dict for field {field_name}. Type: {type(field_meta)}", False)
                                field_meta = {}

                            # Check filter_based_on_key_value condition
                            filter_condition = field_meta.get("extra_metas", {}).get("filter_based_on_key_value")
                            if filter_condition and isinstance(filter_condition, str):
                                DebugService.app_debug_print(f"[DEBUG] Field {field_name} has filter condition: {filter_condition}", False)
                                try:
                                    # Parse the filter condition (format: "field_name,expected_value")
                                    condition_parts = filter_condition.split(",", 1)
                                    if len(condition_parts) == 2:
                                        condition_field, expected_value = condition_parts
                                        condition_field = condition_field.strip()
                                        expected_value = expected_value.strip()

                                        # Validate that the condition field exists in the model
                                        if condition_field not in self.model_fields:
                                            DebugService.app_debug_print(f"[WARNING] Filter condition field '{condition_field}' not found in model for field {field_name}", False)
                                            continue

                                        # Get the actual value of the condition field from the document
                                        actual_value = doc.get(condition_field)

                                        # Handle enum values - convert to string representation
                                        if hasattr(actual_value, 'value'):
                                            actual_value_str = str(actual_value.value)
                                        elif actual_value is not None:
                                            actual_value_str = str(actual_value)
                                        else:
                                            actual_value_str = None

                                        DebugService.app_debug_print(f"[DEBUG] Filter condition check for {field_name}: {condition_field}='{actual_value_str}' should equal '{expected_value}'", False)

                                        # Skip field if condition doesn't match
                                        if actual_value_str != expected_value:
                                            DebugService.app_debug_print(f"[DEBUG] Skipping field {field_name} due to filter condition mismatch: {actual_value_str} != {expected_value}", False)
                                            continue
                                        else:
                                            DebugService.app_debug_print(f"[DEBUG] Field {field_name} passes filter condition: {actual_value_str} == {expected_value}", False)
                                    else:
                                        DebugService.app_debug_print(f"[WARNING] Invalid filter_based_on_key_value format for field {field_name}: {filter_condition}", False)
                                except Exception as e:
                                    DebugService.app_debug_print(f"[ERROR] Error processing filter condition for field {field_name}: {e}", False)
                                    # Continue processing the field if there's an error in the filter condition

                        DebugService.app_debug_print(f"[DEBUG] Field {field_name} passed initial checks, proceeding to is_array_of_object check", False)
                    except Exception as field_error:
                        DebugService.app_debug_print(f"[ERROR] Error processing field {field_name}: {field_error}", True)
                        DebugService.app_debug_print(f"[ERROR] Field value type: {type(field_value)}", True)
                        DebugService.app_debug_print(f"[ERROR] Field value: {field_value}", True)
                        continue

                    # Special handling for is_cascade data type
                    if (field_meta and
                        field_meta.get("data_type", {}).get("is_cascade", False) and
                        field_value is not None):
                        try:
                            DebugService.app_debug_print(f"[DEBUG] Processing is_cascade field: {field_name}", False)
                            DebugService.app_debug_print(f"[DEBUG] Field metadata: {field_meta}", False)

                            # TEMPORARY: Skip cascade processing to debug the issue
                            DebugService.app_debug_print(f"[DEBUG] SKIPPING cascade processing for {field_name} to debug issue", False)
                            # Fall through to regular processing

                            # # Get cascade configuration from metadata
                            # extra_metas = field_meta.get("extra_metas", {})
                            # cascade_config = extra_metas.get("cascade_config", {})

                            # # Get the cascade data using the cascade method
                            # cascade_data = await self.formatted_properties_for_cascade(
                            #     accept_language=accept_language,
                            #     collection_key=collection_key,
                            #     force_include_fields=force_include_fields,
                            #     sort=sort,
                            #     force_exclude_fields=force_exclude_fields
                            # )

                            # # Get display title for the cascade field
                            # try:
                            #     from app.modules.core.services.translation.translation_service import TranslationService
                            #     display_title = await TranslationService.get_static_fields_translation(
                            #         property_name=field_name,
                            #         accept_language=accept_language
                            #     )
                            # except Exception:
                            #     display_title = field_name.replace('_', ' ').title()

                            # # Prepare the cascade field structure
                            # properties[field_name] = {
                            #     "display_title": display_title,
                            #     "display_value": cascade_data,
                            #     "real_value": cascade_data,
                            #     "data_type": {"is_cascade": True},
                            #     "meta": {
                            #         "to_be_translated_in_front": False,
                            #         "may_have_translation": False,
                            #         "missing_translation": False,
                            #         "cascade_config": cascade_config,
                            #         **extra_metas
                            #     }
                            # }

                            # DebugService.app_debug_print(f"[DEBUG] Successfully processed cascade field {field_name}", True)
                            # continue

                        except Exception as cascade_error:
                            DebugService.app_debug_print(f"[ERROR] Error processing is_cascade field {field_name}: {cascade_error}", True)
                            import traceback
                            DebugService.app_debug_print(f"[ERROR] Cascade traceback: {traceback.format_exc()}", True)
                            # Fall through to regular processing

                    # Special handling for is_array_of_object data type
                    DebugService.app_debug_print(f"[DEBUG] Checking is_array_of_object for field {field_name}", False)
                    DebugService.app_debug_print(f"[DEBUG] - isinstance(field_value, list): {isinstance(field_value, list)}", False)
                    DebugService.app_debug_print(f"[DEBUG] - field_meta: {field_meta}", False)
                    data_type_info = field_meta.get('data_type', {}) if field_meta else None
                    is_array_info = field_meta.get('data_type', {}).get('is_array_of_object', False) if field_meta else None
                    DebugService.app_debug_print(f"[DEBUG] - field_meta.get('data_type'): {data_type_info}", False)
                    DebugService.app_debug_print(f"[DEBUG] - is_array_of_object: {is_array_info}", False)

                    if isinstance(field_value, list) and field_meta and field_meta.get("data_type", {}).get("is_array_of_object", False):
                        try:
                            DebugService.app_debug_print(f"[DEBUG] Processing is_array_of_object field: {field_name}", False)

                            # OPTIMIZATION: Collect all database requests first, then batch them
                            data_requests = []
                            translation_requests = []

                            # First pass: collect all data requests
                            for item_index, item in enumerate(field_value):
                                if isinstance(item, dict):
                                    for sub_key, sub_val in item.items():
                                        # Skip excluded fields
                                        if sub_key in ['multiple_validation_status', 'multiple_validated_at', 'soft_deleted', 'soft_deleted_at', 'soft_deleted_by_id', 'translations', '_id']:
                                            continue

                                        # Check if this field needs data lookup
                                        if sub_key.endswith('_id') and sub_val is not None:
                                            # Get field metadata to determine data source
                                            array_object_model_name = field_meta.get('extra_metas', {}).get('array_of_object_model')
                                            if array_object_model_name:
                                                try:
                                                    # Get the model class
                                                    nested_model_class = BaseModelUtils.get_model_class_by_name(array_object_model_name)

                                                    if nested_model_class and hasattr(nested_model_class, 'model_fields') and sub_key in nested_model_class.model_fields:
                                                        nested_field = nested_model_class.model_fields[sub_key]
                                                        field_metadata = nested_field.json_schema_extra or {}
                                                        overview_data_type = field_metadata.get('overview_data_type', {})
                                                        extra_metas = field_metadata.get('extra_metas', {})
                                                        data_source = extra_metas.get('select_source_model')
                                                        cascade_data_source = extra_metas.get('cascade_source_model')

                                                        if overview_data_type and overview_data_type.get('is_select', False) and data_source:
                                                            # Add to batch request
                                                            data_requests.append({
                                                                "data_source": data_source,
                                                                "field_id": str(sub_val),
                                                                "query": {"filter___id": sub_val},
                                                                "item_index": item_index,
                                                                "sub_key": sub_key
                                                            })
                                                        elif overview_data_type and overview_data_type.get('is_cascade', False) and cascade_data_source:
                                                            # Add to batch request for cascade
                                                            data_requests.append({
                                                                "data_source": cascade_data_source,
                                                                "field_id": str(sub_val),
                                                                "query": {"filter___id": sub_val},
                                                                "item_index": item_index,
                                                                "sub_key": sub_key
                                                            })
                                                except Exception as e:
                                                    DebugService.app_debug_print(f"[ERROR] Error processing field metadata for {sub_key}: {e}", True)

                                        # Collect translation requests
                                        translation_requests.append({
                                            "property_name": sub_key,
                                            "item_index": item_index,
                                            "sub_key": sub_key
                                        })

                            # OPTIMIZATION: Batch fetch all data at once
                            batch_data_results = await self.batch_fetch_field_data(data_requests, accept_language) if data_requests else {}

                            # OPTIMIZATION: Batch fetch all translations at once
                            translation_tasks = []
                            for req in translation_requests:
                                try:
                                    from app.modules.core.services.translation.translation_service import TranslationService
                                    task = TranslationService.get_static_fields_translation(
                                        property_name=req["property_name"],
                                        accept_language=accept_language
                                    )
                                    translation_tasks.append(task)
                                except Exception:
                                    translation_tasks.append(asyncio.create_task(asyncio.coroutine(lambda: req["property_name"].replace('_', ' ').title())()))

                            # Execute all translation tasks concurrently
                            translation_results = await AsyncExecutor.gather(translation_tasks, return_exceptions=True) if translation_tasks else []

                            # Create translation lookup
                            translation_lookup = {}
                            for i, req in enumerate(translation_requests):
                                key = f"{req['item_index']}:{req['sub_key']}"
                                if i < len(translation_results) and not isinstance(translation_results[i], Exception):
                                    translation_lookup[key] = translation_results[i]
                                else:
                                    translation_lookup[key] = req["property_name"].replace('_', ' ').title()

                            # Second pass: process items with batched data
                            processed_items = []
                            for item_index, item in enumerate(field_value):
                                DebugService.app_debug_print(f"[DEBUG] Processing array item {item_index} for field {field_name}", True)
                                if isinstance(item, dict):
                                    processed_item = {}

                                    # Process each field in the array item
                                    for sub_key, sub_val in item.items():
                                        # Skip excluded fields
                                        if sub_key in ['multiple_validation_status', 'multiple_validated_at', 'soft_deleted', 'soft_deleted_at', 'soft_deleted_by_id', 'translations', '_id']:
                                            continue

                                        # Infer data type from the actual value
                                        inferred_data_type = {"is_string": True}  # default
                                        if isinstance(sub_val, bool):
                                            inferred_data_type = {"is_boolean": True}
                                        elif isinstance(sub_val, int):
                                            inferred_data_type = {"is_int": True}
                                        elif isinstance(sub_val, float):
                                            inferred_data_type = {"is_float": True}
                                        elif sub_key.endswith('_id') and sub_val is not None:
                                            inferred_data_type = {"is_select": True}
                                        elif isinstance(sub_val, str) and sub_key in ['status', 'state', 'type']:
                                            inferred_data_type = {"is_enum": True}
                                        elif sub_key.endswith('_at') and sub_val is not None:
                                            inferred_data_type = {"is_date": True}

                                        # Get translated field name from batched results
                                        translation_key = f"{item_index}:{sub_key}"
                                        display_title = translation_lookup.get(translation_key, sub_key.replace('_', ' ').title())

                                        # Prepare meta object
                                        meta_obj = {
                                            "to_be_translated_in_front": False,
                                            "may_have_translation": False,
                                            "missing_translation": False
                                        }

                                        DebugService.app_debug_print(f"[DEBUG] - inferred_data_type >> : {inferred_data_type}", True)

                                        # Handle is_select fields with data source lookup using batched results
                                        if inferred_data_type.get('is_select', False) and sub_val is not None:
                                            DebugService.app_debug_print(f"[DEBUG] Processing is_select field {sub_key} with value {sub_val}", True)

                                            # Try to get field metadata from the array_of_object_model
                                            overview_data_type = None
                                            extra_metas = {}
                                            data_source = None
                                            cascade_data_source = None

                                            # Get the array_of_object_model from the main field's extra_metas
                                            array_object_model_name = field_meta.get('extra_metas', {}).get('array_of_object_model')
                                            DebugService.app_debug_print(f"[DEBUG] Array object model name: {array_object_model_name}", True)

                                            if array_object_model_name:
                                                try:
                                                    # Try to import the schema class directly
                                                    # Schema classes are typically in schema modules, not in COLLECTION_MODEL_MAPPING
                                                    nested_model_class = None

                                                    # Import schema modules list from mapping
                                                    import importlib
                                                    from app.modules.core.models.mapping import SCHEMA_MODULES

                                                    for module_path in SCHEMA_MODULES:
                                                        try:
                                                            module = importlib.import_module(module_path)
                                                            if hasattr(module, array_object_model_name):
                                                                nested_model_class = getattr(module, array_object_model_name)
                                                                DebugService.app_debug_print(f"[DEBUG] ✅ Found schema class {array_object_model_name} in {module_path}", True)
                                                                break
                                                        except ImportError:
                                                            continue

                                                    if nested_model_class and hasattr(nested_model_class, 'model_fields') and sub_key in nested_model_class.model_fields:
                                                        nested_field = nested_model_class.model_fields[sub_key]
                                                        field_metadata = nested_field.json_schema_extra or {}
                                                        overview_data_type = field_metadata.get('overview_data_type', {})
                                                        extra_metas = field_metadata.get('extra_metas', {})
                                                        data_source = extra_metas.get('select_source_model')
                                                        cascade_data_source = extra_metas.get('cascade_source_model')
                                                        DebugService.app_debug_print(f"[DEBUG] Found field metadata for {sub_key} in {array_object_model_name}: overview_data_type={overview_data_type}, data_source={data_source}, cascade_data_source={cascade_data_source}", True)
                                                    else:
                                                        if not nested_model_class:
                                                            DebugService.app_debug_print(f"[DEBUG] Could not find schema class {array_object_model_name} in any module", True)
                                                        else:
                                                            DebugService.app_debug_print(f"[DEBUG] Could not find field {sub_key} in schema {array_object_model_name}", True)

                                                except Exception as e:
                                                    DebugService.app_debug_print(f"[DEBUG] Could not import schema class {array_object_model_name}: {e}", True)
                                            else:
                                                DebugService.app_debug_print(f"[DEBUG] No array_of_object_model specified in field metadata", True)

                                            # Use the exact same pattern as regular field processing
                                            DebugService.app_debug_print(f"[DEBUG] Checking conditions: overview_data_type={overview_data_type}, data_source={data_source}, cascade_data_source={cascade_data_source}", True)
                                            DebugService.app_debug_print(f"[DEBUG] overview_data_type.get('is_select', False)={overview_data_type.get('is_select', False) if overview_data_type else 'None'}", True)
                                            DebugService.app_debug_print(f"[DEBUG] overview_data_type.get('is_cascade', False)={overview_data_type.get('is_cascade', False) if overview_data_type else 'None'}", True)

                                            if overview_data_type and overview_data_type.get('is_select', False) and data_source:
                                                DebugService.app_debug_print(f"[DEBUG] ✅ Conditions met! Using batched data for: {data_source} for {sub_key}", True)

                                                # OPTIMIZATION: Use batched results instead of individual database call
                                                batch_key = f"{data_source}:{str(sub_val)}"
                                                input_select_list = batch_data_results.get(batch_key)

                                                if input_select_list:
                                                    # Add to extra_metas first, then merge into meta_obj
                                                    extra_metas['data_source_value'] = input_select_list
                                                    DebugService.app_debug_print(f"[DEBUG] ✅ Successfully used batched data_source_value: {input_select_list}", True)
                                                else:
                                                    DebugService.app_debug_print(f"[DEBUG] ❌ No batched data found for key: {batch_key}", True)
                                            elif overview_data_type and overview_data_type.get('is_cascade', False) and cascade_data_source:
                                                DebugService.app_debug_print(f"[DEBUG] ✅ Cascade conditions met! Using batched data for: {cascade_data_source} for {sub_key}", True)

                                                # OPTIMIZATION: Use batched results instead of individual database call
                                                batch_key = f"{cascade_data_source}:{str(sub_val)}"
                                                input_select_list = batch_data_results.get(batch_key)

                                                if input_select_list:
                                                    # Add to extra_metas first, then merge into meta_obj
                                                    extra_metas['data_source_value'] = input_select_list
                                                    DebugService.app_debug_print(f"[DEBUG] ✅ Successfully used batched cascade data_source_value: {input_select_list}", True)
                                                else:
                                                    DebugService.app_debug_print(f"[DEBUG] ❌ No batched cascade data found for key: {batch_key}", True)
                                            else:
                                                DebugService.app_debug_print(f"[DEBUG] ❌ Conditions not met for {sub_key}", True)
                                                if not overview_data_type:
                                                    DebugService.app_debug_print(f"[DEBUG] - overview_data_type is None", True)
                                                elif not overview_data_type.get('is_select', False) and not overview_data_type.get('is_cascade', False):
                                                    DebugService.app_debug_print(f"[DEBUG] - overview_data_type.is_select and is_cascade are both False", True)
                                                elif not data_source and not cascade_data_source:
                                                    DebugService.app_debug_print(f"[DEBUG] - both data_source and cascade_data_source are None", True)

                                            # Add select_source_model and any extra_metas to meta_obj
                                            if data_source:
                                                meta_obj['select_source_model'] = data_source
                                                DebugService.app_debug_print(f"[DEBUG] Added select_source_model to meta: {data_source}", True)

                                            # Merge extra_metas into meta_obj
                                            DebugService.app_debug_print(f"[DEBUG] extra_metas before merge: {extra_metas}", True)
                                            meta_obj.update(extra_metas)
                                            DebugService.app_debug_print(f"[DEBUG] meta_obj after merge: {meta_obj}", True)

                                        # Determine display and real values based on field type
                                        display_value = sub_val
                                        real_value = sub_val

                                        # For cascade fields, use the fetched display_value if available
                                        if overview_data_type and overview_data_type.get('is_cascade', False) and 'data_source_value' in extra_metas:
                                            cascade_data = extra_metas['data_source_value']
                                            if cascade_data and isinstance(cascade_data, dict) and 'display_value' in cascade_data:
                                                display_value = cascade_data['display_value']
                                                DebugService.app_debug_print(f"[DEBUG] Using cascade display_value for {sub_key}: {display_value}", True)
                                        # For select fields, use the fetched display_value if available
                                        elif overview_data_type and overview_data_type.get('is_select', False) and 'data_source_value' in extra_metas:
                                            select_data = extra_metas['data_source_value']
                                            if select_data and isinstance(select_data, dict) and 'display_value' in select_data:
                                                display_value = select_data['display_value']
                                                DebugService.app_debug_print(f"[DEBUG] Using select display_value for {sub_key}: {display_value}", True)

                                        processed_item[sub_key] = {
                                            "display_title": display_title,
                                            "display_value": display_value,
                                            "real_value": real_value,
                                            "data_type": inferred_data_type,
                                            "meta": meta_obj
                                        }

                                    processed_items.append(processed_item)
                                else:
                                    processed_items.append(item)

                            properties[field_name] = {
                                "display_title": field_meta.get("display_title", field_name.replace('_', ' ').title()),
                                "display_value": processed_items,
                                "real_value": processed_items,
                                "data_type": field_meta.get("data_type", {"is_array_of_object": True}),
                                "meta": {
                                    "to_be_translated_in_front": field_meta.get("to_be_translated_in_front", False),
                                    "may_have_translation": field_meta.get("may_have_translation", False),
                                    "missing_translation": False,
                                    **field_meta.get("extra_metas", {})
                                }
                            }
                            continue
                        except Exception as array_error:
                            DebugService.app_debug_print(f"[ERROR] Error processing is_array_of_object field {field_name}: {array_error}", True)
                            # Fallback to simple processing
                            properties[field_name] = {
                                "display_title": field_name.replace('_', ' ').title(),
                                "display_value": field_value,
                                "real_value": field_value,
                                "data_type": {"is_array_of_object": True},
                                "meta": {
                                    "to_be_translated_in_front": False,
                                    "may_have_translation": False,
                                    "missing_translation": False
                                }
                            }
                            continue

                    # Skip fields marked with exclusions unless they're essential
                    if field_meta:
                        is_essential = field_meta.get("extra_metas", {}).get("essential_field", False) or field_name == "id"
                        if (field_meta.get("exclude_from_default", False) or
                            field_meta.get("exclude_at_all", False)) and not is_essential:
                            DebugService.app_debug_print(f"[DEBUG] Skipping field {field_name} (excluded by metadata)", True)
                            continue
                        elif (field_meta.get("exclude_from_default", False) or
                            field_meta.get("exclude_at_all", False)) and is_essential:
                            DebugService.app_debug_print(f"[DEBUG] Including essential field {field_name} despite exclusion metadata", True)
                    else:
                        DebugService.app_debug_print(f"[DEBUG] Field {field_name} exists in document but not in model - skipping", False)
                        continue

                    # Process the field if it exists in the model
                    if field_name in self.model_fields:
                        try:
                            field = self.model_fields[field_name]
                            
                            # Special handling for id field with hidden values
                            if field_name == "id" and hidde_on_view_values:
                                meta = field.json_schema_extra or {}
                                extra_metas = meta.get("extra_metas", {})
                                
                                # Merge hidden fields into excluded_fields
                                existing_excluded_fields = extra_metas.get("excluded_fields", "")
                                hidden_field_names = list(hidde_on_view_values.keys())
                                
                                excluded_fields_set = set()
                                if existing_excluded_fields:
                                    excluded_fields_set = set(
                                        field.strip() 
                                        for field in existing_excluded_fields.split(',') 
                                        if field.strip()
                                    )
                                
                                excluded_fields_set.update(hidden_field_names)
                                merged_excluded_fields = ','.join(sorted(excluded_fields_set))
                                
                                # Create modified field metadata
                                modified_extra_metas = {**extra_metas, "excluded_fields": merged_excluded_fields}
                                modified_meta = {**meta, "extra_metas": modified_extra_metas}
                                
                                # Create temporary field with modified metadata
                                modified_field = type('Field', (), {
                                    'json_schema_extra': modified_meta
                                })()
                                
                                properties[field_name] = await self.process_field_for_properties(
                                    field_name,
                                    modified_field,
                                    field_value,
                                    accept_language,
                                    generic_service
                                )
                            else:
                                properties[field_name] = await self.process_field_for_properties(
                                    field_name,
                                    field,
                                    field_value,
                                    accept_language,
                                    generic_service
                                )
                                
                            # Ensure may_have_translation exists in meta
                            if (isinstance(properties[field_name], dict) and 
                                'meta' in properties[field_name] and 
                                'may_have_translation' not in properties[field_name]['meta']):
                                properties[field_name]['meta']['may_have_translation'] = False
                                
                        except Exception as e:
                            DebugService.app_debug_print(f"Error processing field {field_name}: {e}", False)
                            properties[field_name] = {
                                "display_title": field_name.replace('_', ' ').title(),
                                "display_value": field_value,
                                "real_value": field_value,
                                "data_type": {"is_string": True},
                                "meta": {
                                    "to_be_translated_in_front": False,
                                    "may_have_translation": False,
                                    "missing_translation": False
                                }
                            }

                # Sort properties
                if properties:
                    priority_fields = ["id", "identifier", "name"]
                    trailing_fields = ["created_at", "updated_at", "deleted_at"]

                    sorted_properties = {
                        field_name: properties[field_name] 
                        for field_name in sorted(
                            properties.keys(),
                            key=lambda x: (
                                0 if x in priority_fields else (2 if x in trailing_fields else 1),
                                priority_fields.index(x) if x in priority_fields else float("inf"),
                                x
                            )
                        )
                    }

                    # Filter properties based on exclusion rules
                    filtered_props = {
                        k: v 
                        for k, v in sorted_properties.items() 
                        if k not in force_exclude_fields
                    }

                    # Ensure all fields have proper meta structure
                    for field_value in filtered_props.values():
                        if isinstance(field_value, dict):
                            field_value.setdefault('meta', {})
                            field_value['meta'].setdefault('may_have_translation', False)

                    # Separate FieldTranslation objects from dictionaries
                    field_translation_props = {}
                    dictionary_props = {}

                    for key, value in filtered_props.items():
                        if hasattr(value, 'may_have_translation'):
                            # This is a FieldTranslation object
                            field_translation_props[key] = value
                        else:
                            # This is already a dictionary with the final format
                            dictionary_props[key] = value

                    # Process FieldTranslation objects if any exist
                    if field_translation_props:
                        translated_props = await BaseModelUtils.get_fields_translation(
                            targeted_id=doc.get("id", str(self.id)) if hasattr(self, "id") else None,
                            short_code=accept_language,
                            add_timestamps=True,
                            properties=field_translation_props
                        )
                        # Merge with dictionary props
                        return {**translated_props, **dictionary_props}
                    else:
                        # Only dictionaries, return them directly
                        return dictionary_props

                return properties
            else:
                # Get the formatted properties using the base method
                formatted_props = await self.formatted_properties(accept_language, collection_key)

                # Filter properties based on inclusion/exclusion rules
                filtered_props = formatted_props
                if force_include_fields:
                    if 'id' not in force_include_fields:
                        force_include_fields.append('id')
                    filtered_props = {k: v for k, v in formatted_props.items() if k in force_include_fields}
                
                if force_exclude_fields:
                    filtered_props = {k: v for k, v in filtered_props.items() if k not in force_exclude_fields}

                # Ensure all fields have proper meta structure
                for field_value in filtered_props.values():
                    if isinstance(field_value, dict):
                        field_value.setdefault('meta', {})
                        field_value['meta'].setdefault('may_have_translation', False)

                return filtered_props
        except Exception as e:
            import traceback
            DebugService.app_debug_print(f"[DEBUG] Error in formatted_properties_for_data_table: {e}", True)
            DebugService.app_debug_print(f"[DEBUG] Full traceback: {traceback.format_exc()}", True)
            DebugService.app_debug_print(f"[DEBUG] Error type: {type(e)}", True)
            DebugService.app_debug_print(f"[DEBUG] Error args: {e.args}", True)
            raise e
    
    async def formatted_properties_for_input_select(
        self,
        accept_language: str = DEFAULT_LANGUAGE,
        collection_key: Optional[CollectionKey] = None,
        force_include_fields: Optional[list] = None,
        sort: Optional[Dict[str, int]] = None,
        doc: Optional[Dict[str, Any]] = None,force_exclude_fields: Optional[list] = None
        ) -> Dict[str, Any]:
        """
        Format properties for input_select output.
        Optimized for performance with batched database updates.
        """
        # Use default values if not provided
        if force_include_fields is None:
            force_include_fields = []
        if force_exclude_fields is None:
            force_exclude_fields = []
        if sort is None:
            sort = {"created_at": -1}

        # If a document is provided, use it instead of the model instance fields
        if doc is not None:
            DebugService.app_debug_print("[DEBUG] Processing input_select with provided document", False)
            # Create a temporary instance with only the fields from the document
            from app.modules.core.services.generic.generic_services import GenericService
            generic_service = GenericService(accept_language)
            properties = {}

            # Ensure we have an ID field
            DebugService.app_debug_print(f"[DEBUG] Checking ID field in doc: _id in doc: {'_id' in doc}, id in doc: {'id' in doc}", False)
            if "_id" in doc and "id" not in doc:
                doc["id"] = str(doc["_id"])
                DebugService.app_debug_print(f"[DEBUG] Added id field from _id: {doc['id']}", False)
            elif "id" not in doc and "_id" not in doc and hasattr(self, "id"):
                doc["id"] = str(self.id)
                DebugService.app_debug_print(f"[DEBUG] Added id field from self.id: {doc['id']}", False)

            # Ensure translations dictionary exists
            if "translations" not in doc and hasattr(self, "translations"):
                doc["translations"] = self.translations or {}
                DebugService.app_debug_print("[DEBUG] Added translations from model instance", False)

            # Derive property_name as <model_name>_id
            model_name = getattr(self, 'Settings', None)
            if model_name and hasattr(model_name, 'name'):
                model_name = model_name.name
            else:
                model_name = self.__class__.__name__.lower()
            property_name = f"{model_name}_id"

            # Determine primary display value based on extra_metas.display_value_on_input_select.
            primary_display_value = None
            display_field_name = None

            # Find the field to use for display value
            for field_name, field in self.model_fields.items():
                if field_name == 'revision_id':
                    continue
                meta = field.json_schema_extra or {}

                # Check filter_based_on_key_value condition
                filter_condition = meta.get("extra_metas", {}).get("filter_based_on_key_value")
                if filter_condition and isinstance(filter_condition, str):
                    DebugService.app_debug_print(f"[DEBUG] Field {field_name} has filter condition: {filter_condition}", False)
                    try:
                        # Parse the filter condition (format: "field_name,expected_value")
                        condition_parts = filter_condition.split(",", 1)
                        if len(condition_parts) == 2:
                            condition_field, expected_value = condition_parts
                            condition_field = condition_field.strip()
                            expected_value = expected_value.strip()

                            # Validate that the condition field exists in the model
                            if condition_field not in self.model_fields:
                                DebugService.app_debug_print(f"[WARNING] Filter condition field '{condition_field}' not found in model for field {field_name}", True)
                                continue

                            # Get the actual value of the condition field from the document
                            actual_value = doc.get(condition_field)

                            # Handle enum values - convert to string representation
                            if hasattr(actual_value, 'value'):
                                actual_value_str = str(actual_value.value)
                            elif actual_value is not None:
                                actual_value_str = str(actual_value)
                            else:
                                actual_value_str = None

                            DebugService.app_debug_print(f"[DEBUG] Filter condition check for {field_name}: {condition_field}='{actual_value_str}' should equal '{expected_value}'", False)

                            # Skip field if condition doesn't match
                            if actual_value_str != expected_value:
                                DebugService.app_debug_print(f"[DEBUG] Skipping field {field_name} due to filter condition mismatch: {actual_value_str} != {expected_value}", False)
                                continue
                            else:
                                DebugService.app_debug_print(f"[DEBUG] Field {field_name} passes filter condition: {actual_value_str} == {expected_value}", False)
                        else:
                            DebugService.app_debug_print(f"[WARNING] Invalid filter_based_on_key_value format for field {field_name}: {filter_condition}", True)
                    except Exception as e:
                        DebugService.app_debug_print(f"[ERROR] Error processing filter condition for field {field_name}: {e}", True)
                        # Continue processing the field if there's an error in the filter condition

                if meta.get("extra_metas", {}).get("display_value_on_input_select", False):
                    display_field_name = field_name
                    can_be_translated = meta.get("may_have_translation", False)

                    # Check if the field exists in the document
                    if display_field_name in doc:
                        value = doc[display_field_name]
                        if isinstance(value, ObjectId) or field_name.endswith("_id") and ObjectId.is_valid(value):
                            value = str(value)

                        # If translatable and not default language, handle translation
                        if can_be_translated and accept_language != DEFAULT_LANGUAGE:
                            # Get model name for translation context
                            settings = getattr(self, 'Settings', None)
                            if settings and hasattr(settings, 'name'):
                                model_name = settings.name
                            else:
                                model_name = self.__class__.__name__.lower()
                            # Use get_innter_translation which now has caching and batched updates
                            primary_display_value = await BaseModelUtils.get_innter_translation(
                                targeted_id=doc.get("id", str(self.id)) if hasattr(self, "id") else None,
                                property_name=field_name,
                                short_code=accept_language,
                                property_value=value,
                                model_name=model_name
                            )
                        else:
                            # For default language or non-translatable fields, use the original value
                            primary_display_value = value
                    break

            # Use fallback if no primary display value found.
            if primary_display_value is None:
                fallback_field = "name"
                if fallback_field in doc:
                    fallback_value = doc[fallback_field]
                    if isinstance(fallback_value, ObjectId):
                        fallback_value = str(fallback_value)

                    # Check if fallback field is translatable
                    field = self.model_fields.get(fallback_field)
                    if field:
                        meta = field.json_schema_extra or {}
                        can_be_translated = meta.get("may_have_translation", False)

                        # Handle translation for fallback field
                        if can_be_translated and accept_language != DEFAULT_LANGUAGE:
                            # Get model name for translation context
                            settings = getattr(self, 'Settings', None)
                            if settings and hasattr(settings, 'name'):
                                model_name = settings.name
                            else:
                                model_name = self.__class__.__name__.lower()
                            # Use get_innter_translation which now has caching and batched updates
                            primary_display_value = await BaseModelUtils.get_innter_translation(
                                targeted_id=doc.get("id", str(self.id)) if hasattr(self, "id") else None,
                                property_name=fallback_field,
                                short_code=accept_language,
                                property_value=fallback_value,
                                model_name=model_name
                            )
                        else:
                            primary_display_value = fallback_value

            # Construct the base properties dictionary with the primary display value.
            properties = {
                "id": doc.get("id", str(self.id)) if hasattr(self, "id") else None,
                "property_name": property_name,
                "display_value": primary_display_value,
            }

            # Process secondary fields
            for field_name, field in self.model_fields.items():
                # Skip fields not in force_include_fields if it's provided
                if force_include_fields and field_name not in force_include_fields:
                    continue

                # Skip fields not in the document
                if field_name not in doc:
                    continue

                meta = field.json_schema_extra or {}
                if meta.get("extra_metas", {}).get("secondary_display_value_on_input_select", False):
                    can_be_translated = meta.get("may_have_translation", False)
                    value = doc[field_name]
                    if isinstance(value, ObjectId) or field_name.endswith("_id") and ObjectId.is_valid(value):
                        value = str(value)

                    # Handle translation for secondary fields
                    if can_be_translated and accept_language != DEFAULT_LANGUAGE:
                        # Get model name for translation context
                        settings = getattr(self, 'Settings', None)
                        if settings and hasattr(settings, 'name'):
                            model_name = settings.name
                        else:
                            model_name = self.__class__.__name__.lower()
                        # Use get_innter_translation which now has caching and batched updates
                        secondary_display_value = await BaseModelUtils.get_innter_translation(
                            targeted_id=doc.get("id", str(self.id)) if hasattr(self, "id") else None,
                            property_name=field_name,
                            short_code=accept_language,
                            property_value=value,
                            model_name=model_name
                        )
                    else:
                        secondary_display_value = value

                    properties[field_name] = secondary_display_value

            # Remove sensitive fields
            sensitive_fields = ['password', 'user_account_hash', 'user_account_socket_hash']
            for field in sensitive_fields:
                properties.pop(field, None)

            return properties
        else:
            # Initialize translations dictionary if it doesn't exist
            if self.translations is None:
                self.translations = {}

    # Cache for translations to avoid repeated DB updates
    _translation_cache = {}
    _translation_update_queue = {}
    _translation_update_lock = None

    @classmethod
    def get_translation_update_lock(cls):
        """Get or create the translation update lock."""
        if cls._translation_update_lock is None:
            cls._translation_update_lock = asyncio.Lock()
        return cls._translation_update_lock

    async def formatted_properties_for_cascade(
            self, accept_language: str = DEFAULT_LANGUAGE, base_model_class: Optional[Type] = None, collection_key: Optional[CollectionKey] = CollectionKey.REF_MFAS, force_include_fields: Optional[list] = None,
        sort: Optional[Dict[str, int]] = None, doc: Optional[Dict[str, Any]] = None, force_exclude_fields: Optional[list] = None,
        hidde_on_view_values: Optional[dict] = None
    ) -> Dict[str, Any]:
        """
        Format properties for cascade output combining tree and input_select functionalities.
        """
        try:
            DebugService.app_debug_print(f"formatted_properties_for_cascade: accept_language: {accept_language}", True)
            DebugService.app_debug_print(f"formatted_properties_for_cascade: collection_key: {collection_key}", True)
            
            # Initialize force_exclude_fields if not provided
            if force_exclude_fields is None:
                force_exclude_fields = []
                DebugService.app_debug_print("[DEBUG] Initialized force_exclude_fields to empty list", False)
            
            from app.modules.core.services.generic.generic_services import GenericService
            generic_service = GenericService(accept_language)
            
            # Determine model name and property name.
            settings = getattr(self, 'Settings', None)
            if settings and hasattr(settings, 'name'):
                model_name = settings.name
            else:
                model_name = self.__class__.__name__.lower()
            property_name = f"{model_name}_id"
            parent_field = f"{model_name}_id"

            # Determine which field to use for display value on cascade.
            display_value_field = "name"  # default fallback
            can_be_translated = False
            for field_name, field in self.model_fields.items():
                if field_name == 'revision_id':
                    continue
                meta = field.json_schema_extra or {}

                # Check filter_based_on_key_value condition
                filter_condition = meta.get("extra_metas", {}).get("filter_based_on_key_value")
                if filter_condition and isinstance(filter_condition, str):
                    DebugService.app_debug_print(f"[DEBUG] Field {field_name} has filter condition: {filter_condition}", False)
                    try:
                        # Parse the filter condition (format: "field_name,expected_value")
                        condition_parts = filter_condition.split(",", 1)
                        if len(condition_parts) == 2:
                            condition_field, expected_value = condition_parts
                            condition_field = condition_field.strip()
                            expected_value = expected_value.strip()

                            # Validate that the condition field exists in the model
                            if condition_field not in self.model_fields:
                                DebugService.app_debug_print(f"[WARNING] Filter condition field '{condition_field}' not found in model for field {field_name}", True)
                                continue

                            # Get the actual value of the condition field from the model instance
                            actual_value = getattr(self, condition_field, None)

                            # Handle enum values - convert to string representation
                            if hasattr(actual_value, 'value'):
                                actual_value_str = str(actual_value.value)
                            elif actual_value is not None:
                                actual_value_str = str(actual_value)
                            else:
                                actual_value_str = None

                            DebugService.app_debug_print(f"[DEBUG] Filter condition check for {field_name}: {condition_field}='{actual_value_str}' should equal '{expected_value}'", False)

                            # Skip field if condition doesn't match
                            if actual_value_str != expected_value:
                                DebugService.app_debug_print(f"[DEBUG] Skipping field {field_name} due to filter condition mismatch: {actual_value_str} != {expected_value}", False)
                                continue
                            else:
                                DebugService.app_debug_print(f"[DEBUG] Field {field_name} passes filter condition: {actual_value_str} == {expected_value}", False)
                        else:
                            DebugService.app_debug_print(f"[WARNING] Invalid filter_based_on_key_value format for field {field_name}: {filter_condition}", True)
                    except Exception as e:
                        DebugService.app_debug_print(f"[ERROR] Error processing filter condition for field {field_name}: {e}", True)
                        # Continue processing the field if there's an error in the filter condition

                if meta.get("extra_metas", {}).get("display_value_on_cascade", False):
                    display_value_field = field_name
                    can_be_translated = meta.get("may_have_translation", False)
                    break
            DebugService.app_debug_print(
                f"formatted_properties_for_cascade: can_be_translated: {can_be_translated}, display_value_field: {display_value_field}",
                False
            )

            # Get the display value and handle encryption if needed
            display_value = getattr(self, display_value_field, None)
            
            # Handle encrypted display value
            if display_value is not None:
                for field_name, field in self.model_fields.items():
                    if field_name == display_value_field:
                        field_meta = field.json_schema_extra or {}
                        can_be_encrypted = field_meta.get("can_be_encrypted", False)
                        if can_be_encrypted:
                            db_encryption = DBEncryptionService()
                            # Check if the field value is encrypted
                            if isinstance(display_value, str) and display_value.lower().startswith(db_encryption.VERSION_PREFIX):
                                try:
                                    decrypted_value = db_encryption.decrypt(display_value)
                                    display_value = decrypted_value
                                except Exception as e:
                                    DebugService.app_debug_print(f"Error decrypting display field {display_value_field}: {e}", True)
                        break
            
            if isinstance(display_value, ObjectId):
                display_value = str(display_value)

            # Query for children using the same parent field.
            query_params = {f"filter__{parent_field}": str(self.id)}
            # query_params = {f"filter__{parent_field}": str(self.id)}
            DebugService.app_debug_print(f"formatted_properties_for_cascade: query_params: {query_params}", False)

            children_data = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey(collection_key).value,
                all_data=True,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=accept_language,
                query=query_params,
                sort=sort
            )
            DebugService.app_debug_print(f"formatted_properties_for_cascade: children_data: {children_data}", False)

            # Clean the children data based on valid model fields and handle encryption/translation
            valid_fields = set(self.__class__.model_fields.keys())
            cleaned_children_data = []
            for child in children_data:
                cleaned_child = {}
                # Ensure translations key is present
                if "translations" not in child:
                    child["translations"] = {}
                
                for k, v in child.items():
                    if k not in valid_fields or k in force_exclude_fields:
                        continue
                    
                    # Handle encrypted fields
                    if k in self.model_fields:
                        field_meta = self.model_fields[k].json_schema_extra or {}
                        can_be_encrypted = field_meta.get("can_be_encrypted", False)
                        if can_be_encrypted and isinstance(v, str):
                            db_encryption = DBEncryptionService()
                            if v.lower().startswith(db_encryption.VERSION_PREFIX):
                                try:
                                    decrypted_value = db_encryption.decrypt(v)
                                    v = decrypted_value
                                except Exception as e:
                                    DebugService.app_debug_print(f"Error decrypting field {k}: {e}", True)
                    
                    # Handle translations for display values
                    if isinstance(v, dict) and "display_value" in v:
                        cleaned_child[k] = v["display_value"]
                    else:
                        cleaned_child[k] = v
                
                cleaned_children_data.append(cleaned_child)

            # Instantiate children and catch potential validation errors.
            try:
                children = [self.__class__(**child) for child in cleaned_children_data]
            except ValidationError as e:
                DebugService.app_debug_print(f"Error instantiating BaseModelMixin in cascade: {e}", True)
                DebugService.app_debug_print(f"Problematic data: {cleaned_children_data}", True)
                raise

            # Recursively compute cascade properties for each child.
            cascade_children = []
            if children:
                for child in children:
                    cascade_child = await child.formatted_properties_for_cascade(
                        accept_language=accept_language,
                        collection_key=collection_key,
                        sort=sort,
                        force_include_fields=force_include_fields,
                        force_exclude_fields=force_exclude_fields
                    )
                    cascade_children.append(cascade_child)

            # Mark nodes with no children as leaves.
            is_leaf = not bool(cascade_children)

            # Get the final display value with translation if needed
            final_display_value = display_value
            if can_be_translated and display_value is not None and isinstance(display_value, str):
                final_display_value = await BaseModelUtils.get_innter_translation(
                    targeted_id=str(self.id),
                    short_code=accept_language,
                    property_value=display_value,
                    property_name=display_value_field,
                    model_name=model_name
                )

            # Build and return the cascade properties.
            response = {
                "id": str(self.id),
                "property_name": property_name,
                "is_leaf": is_leaf,
                "children": cascade_children,
                "display_value": final_display_value,
            }

            return response
        except Exception as e:
            DebugService.app_debug_print(f"Error in formatted_properties_for_cascade: {e}", True)
            raise
 
    async def formatted_properties_for_cascade_all(
        self,
        accept_language: str = DEFAULT_LANGUAGE,
        collection_key: Optional[CollectionKey] = CollectionKey.REF_MFAS,
        force_include_fields: list = [],  # Add this parameter to match other methods
        force_exclude_fields: Optional[list] = []
    ) -> Dict[str, Any]:
        """
        Format properties for cascade output combining tree and input_select functionalities.
        """
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(accept_language)
        # Initialize translations dictionary if it doesn't exist
        if self.translations is None:
            self.translations = {}

        # Determine model name and property name.
        settings = getattr(self, 'Settings', None)
        if settings and hasattr(settings, 'name'):
            model_name = settings.name
        else:
            model_name = self.__class__.__name__.lower()
        property_name = f"{model_name}_id"
        parent_field = f"{model_name}_id"

        # Determine which field to use for display value on cascade.
        display_value_field = "name"  # default fallback
        can_be_translated = False
        for field_name, field in self.model_fields.items():
            if field_name == 'revision_id':
                continue
            meta = field.json_schema_extra or {}
            if meta.get("extra_metas", {}).get("display_value_on_cascade", False):
                display_value_field = field_name
                can_be_translated = meta.get("may_have_translation", False)
                break

        # Get the display value and convert ObjectId to string if necessary.
        display_value = getattr(self, display_value_field, None)
        if isinstance(display_value, ObjectId):
            display_value = str(display_value)

        # Handle translation for display value
        if can_be_translated and accept_language != DEFAULT_LANGUAGE:
            # Ensure field exists in translations dictionary
            if display_value_field not in self.translations:
                self.translations[display_value_field] = {}

            db_encryption = DBEncryptionService()
            # Check if translation exists for this language
            if accept_language in self.translations[display_value_field]:
                # Use existing translation
                translation_value = self.translations[display_value_field][accept_language]

                # Check if the translation is encrypted
                if isinstance(translation_value, str) and translation_value.startswith(db_encryption.VERSION_PREFIX):
                    # Try to decrypt the translation
                    encrypted_value = translation_value[4:]  # Remove "ENC:" prefix
                    decrypted_value = db_encryption.decrypt(encrypted_value)

                    # Only use decrypted value if decryption was successful
                    if decrypted_value != encrypted_value:
                        translated_display_value = decrypted_value
                    else:
                        translated_display_value = display_value  # Use original value if decryption fails
                else:
                    translated_display_value = translation_value
            else:
                # Translate the field value
                translated_display_value = await AsyncExecutor.run_in_thread(BaseModelUtils.google_translate_text,
                    text=display_value,
                    target_language=accept_language
                )
                # translated_display_value = await BaseModelUtils.google_translate_text(
                #     text=display_value,
                #     target_language=accept_language
                # )

                # Store the translation for future use
                self.translations[display_value_field][accept_language] = translated_display_value

                # Save the updated translations to the database
                try:
                    # save in background
                    await AsyncExecutor.run_in_thread(
                        generic_service.update_data_in_collection,
                        collection_key=collection_key,
                        item_id=str(self.id),
                        data={"translations": self.translations}
                    )
                    # await generic_service.update_data_in_collection(
                    #     collection_key=collection_key,
                    #     item_id=str(self.id),
                    #     data={"translations": self.translations}
                    # )
                except Exception:
                    pass
        else:
            translated_display_value = display_value

        # Query for children using the same parent field.
        query_params = {f"filter__{parent_field}": str(self.id)}

        children_data = await generic_service.fetch_data_from_collection(
            collection_key= CollectionKey(collection_key).value,
            all_data=False,
            output_data_type=OutputDataType.DEFAULT.value,
            accept_language=accept_language,
            query=query_params,
            force_include_fields=force_include_fields  # Pass the force_include_fields parameter
        )

        # Clean the children data based on valid model fields.
        valid_fields = set(self.__class__.model_fields.keys())
        cleaned_children_data = []
        for child in children_data:
            cleaned_child = {}
            # Ensure translations key is present.
            if "translations" not in cleaned_child:
                cleaned_child["translations"] = {}
            for k, v in child.items():
                if k not in valid_fields:
                    continue
                if isinstance(v, dict) and "display_value" in v:
                    cleaned_child[k] = v["display_value"]
                else:
                    cleaned_child[k] = v
            cleaned_children_data.append(cleaned_child)

        # Instantiate children and catch potential validation errors.
        try:
            children = [self.__class__(**child) for child in cleaned_children_data]
        except ValidationError as e:
            DebugService.app_debug_print(f"Error instantiating BaseModelMixin in cascade: {e}")
            DebugService.app_debug_print(f"Problematic data: {cleaned_children_data}")
            raise

        # Recursively compute cascade properties for each child.
        cascade_children = []
        if children:
            for child in children:
                cascade_child = await child.formatted_properties_for_cascade_all(
                    accept_language,
                    collection_key,
                    force_include_fields  # Pass the force_include_fields parameter
                )
                cascade_children.append(cascade_child)

        # Mark nodes with no children as leaves.
        is_leaf = True

        # Build and return the cascade properties.
        response = {
            "id": str(self.id),
            "property_name": property_name,
            "is_leaf": is_leaf,
            "children": cascade_children,
            "display_value": translated_display_value,
        }

        return response


    async def formatted_properties_for_tree(
        self,
        accept_language: str = DEFAULT_LANGUAGE,
        collection_key: Optional[Any] = None,
        force_include_fields: list = [],
        sort: Optional[Dict[str, int]] = {"created_at": -1},
        has_all_translations: Optional[bool] = False,
        doc: Optional[Dict[str, Any]] = None,
        force_exclude_fields: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Format model properties for tree view with optimized performance.
        Only includes fields with display_value_on_tree=True in extra_metas.
        """
        # Use default values if not provided
        if force_exclude_fields is None:
            force_exclude_fields = []

        # If a document is provided, use it instead of the model instance fields
        if doc is not None:
            DebugService.app_debug_print("[DEBUG] Processing tree with provided document", False)

            # Initialize result dictionary with only essential fields
            formatted_data = {}

            # Ensure we have an ID field
            DebugService.app_debug_print(f"[DEBUG] Checking ID field in doc: _id in doc: {'_id' in doc}, id in doc: {'id' in doc}", False)
            if "_id" in doc:
                formatted_data["id"] = str(doc["_id"])
                DebugService.app_debug_print(f"[DEBUG] Added id field from _id: {formatted_data['id']}", False)
            elif "id" in doc:
                formatted_data["id"] = doc["id"]
                DebugService.app_debug_print(f"[DEBUG] Added id field from doc['id']: {formatted_data['id']}", False)
            elif hasattr(self, "id"):
                formatted_data["id"] = str(self.id)
                DebugService.app_debug_print(f"[DEBUG] Added id field from self.id: {formatted_data['id']}", False)
            else:
                formatted_data["id"] = str(ObjectId())
                DebugService.app_debug_print(f"[DEBUG] Generated new id: {formatted_data['id']}", False)

            # If force_include_fields is provided and not empty, only include those fields (plus 'id')
            if force_include_fields:
                # Always include 'id' field
                if 'id' not in force_include_fields:
                    force_include_fields.append('id')

            db_encryption = DBEncryptionService()
            # Add only fields that have display_value_on_tree=True in extra_metas
            for field_name, field in self.model_fields.items():
                # Skip fields not in force_include_fields if it's provided
                if force_include_fields and field_name not in force_include_fields and field_name != 'id':
                    continue

                # Skip fields in force_exclude_fields
                if field_name in force_exclude_fields:
                    continue

                # Skip fields not in the document
                if field_name not in doc:
                    continue

                meta = field.json_schema_extra or {}
                if meta.get("extra_metas", {}).get("display_value_on_tree", False):
                    field_value = doc.get(field_name)

                    # Handle ObjectId conversion
                    if isinstance(field_value, ObjectId):
                        field_value = str(field_value)

                    # Handle encrypted fields
                    can_be_encrypted = meta.get("can_be_encrypted", False)
                    if can_be_encrypted and isinstance(field_value, str) and field_value.startswith(db_encryption.VERSION_PREFIX):
                        # Decrypt the field value
                        field_value = db_encryption.decrypt(field_value)

                    # Handle translations if needed
                    if meta.get("may_have_translation", False) and accept_language != DEFAULT_LANGUAGE:
                        # Get model name for translation context
                        settings = getattr(self, 'Settings', None)
                        if settings and hasattr(settings, 'name'):
                            model_name = settings.name
                        else:
                            model_name = self.__class__.__name__.lower()
                        field_value = await BaseModelUtils.get_innter_translation(
                            targeted_id=formatted_data["id"],
                            property_name=field_name,
                            short_code=accept_language,
                            property_value=field_value,
                            model_name=model_name
                        )

                    formatted_data[field_name] = field_value

            # Get model name for determining child relationship
            settings = getattr(self, 'Settings', None)
            if settings and hasattr(settings, 'name'):
                model_name = settings.name
            else:
                model_name = self.__class__.__name__.lower()
            parent_field = f"{model_name}_id"

            # Batch fetch children instead of individual queries
            if collection_key:
                from app.modules.core.services.generic.generic_services import GenericService
                generic_service = GenericService(accept_language)

                try:
                    # Fetch all children in a single query with optimized output
                    _native_query = {parent_field: ObjectId(formatted_data["id"])}
                    DebugService.app_debug_print(f"\n\n\n _native_query : {_native_query} TREEE sort 10> : {sort}\n\n\n", True)
                    children_data = []
                    children_data = await generic_service.fetch_native_query_data_from_collection(
                        collection_key=collection_key,
                        all_data=True,
                        output_data_type=OutputDataType.TREE,  # Use TREE format for recursive structure
                        accept_language=accept_language,
                        native_query={parent_field: ObjectId(formatted_data["id"])},
                        sort=sort,
                    )

                    # Add children to the formatted data
                    if children_data:
                        formatted_data["children"] = children_data
                    else:
                        formatted_data["children"] = []
                except RecursionError:
                    DebugService.app_debug_print("Recursion error detected in tree formatting. Limiting depth.", False)
                    formatted_data["children"] = []
                except Exception as e:
                    DebugService.app_debug_print(f"Error fetching children: {str(e)}", False)
                    formatted_data["children"] = []
            else:
                formatted_data["children"] = []

            return formatted_data
        else:
            # Initialize result dictionary with only essential fields
            formatted_data = {
                "id": str(self.id)
            }


    async def formatted_properties_for_tree_data_table(
        self,
        accept_language: str = DEFAULT_LANGUAGE,
        collection_key: Optional[Any] = None,
        force_include_fields: list = [],
        sort: Optional[Dict[str, int]] = {"created_at": -1},
        has_all_translations: Optional[bool] = False,
        doc: Optional[Dict[str, Any]] = None,
        force_exclude_fields: Optional[list] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Format model properties for tree view with optimized performance.
        Only includes fields with display_value_on_tree=True in extra_metas.
        """
        from app.modules.core.services.generic.generic_services import GenericService
        generic_service = GenericService(accept_language)
        # Use default values if not provided
        if force_exclude_fields is None:
            force_exclude_fields = []

        # Extract hidde_on_view_values from kwargs if provided
        hidde_on_view_values = kwargs.get('hidde_on_view_values', {})

        # If a document is provided, use it instead of the model instance fields
        if doc is not None:
            DebugService.app_debug_print("[DEBUG] Processing tree with provided document", False)

            # Initialize result dictionary with only essential fields
            formatted_data = {}

            # Ensure we have an ID field
            DebugService.app_debug_print(f"[DEBUG] Checking ID field in doc: _id in doc: {'_id' in doc}, id in doc: {'id' in doc}", False)
            if "_id" in doc:
                id_value = str(doc["_id"])
                DebugService.app_debug_print(f"[DEBUG] Added id field from _id: {id_value}", False)
            elif "id" in doc:
                id_value = doc["id"]
                DebugService.app_debug_print(f"[DEBUG] Added id field from doc['id']: {id_value}", False)
            elif hasattr(self, "id"):
                id_value = str(self.id)
                DebugService.app_debug_print(f"[DEBUG] Added id field from self.id: {id_value}", False)
            else:
                id_value = str(ObjectId())
                DebugService.app_debug_print(f"[DEBUG] Generated new id: {id_value}", False)

            # Format the ID field in the same style as other fields
            try:
                from app.modules.core.services.translation.translation_service import TranslationService
                id_display_title = await TranslationService.get_static_fields_translation(
                    property_name="id",
                    accept_language=accept_language
                )

                id_field = next(
                    ((name, field) for name, field in self.model_fields.items() if name == "id"),
                    None
                )

                extra_metas = {}
                if id_field:
                    field_name, field = id_field
                    meta = field.json_schema_extra or {}
                    extra_metas = meta.get("extra_metas", {})

                    # Merge hidde_on_view_values into excluded_fields
                    if hidde_on_view_values:
                        existing_excluded_fields = extra_metas.get("excluded_fields", "")
                        hidden_field_names = list(hidde_on_view_values.keys())

                        # Convert existing excluded_fields to a set
                        excluded_fields_set = set()
                        if existing_excluded_fields:
                            excluded_fields_set = set(field.strip() for field in existing_excluded_fields.split(',') if field.strip())

                        # Add hidden fields to the set
                        excluded_fields_set.update(hidden_field_names)

                        # Convert back to comma-separated string
                        merged_excluded_fields = ','.join(sorted(excluded_fields_set))

                        # Update extra_metas with merged excluded_fields
                        extra_metas = {**extra_metas, "excluded_fields": merged_excluded_fields}

                    formatted_data["id"] = {
                        "display_title": id_display_title,
                        "display_value": id_value,
                        "real_value": id_value,
                        "data_type": {"is_str": True},
                        "meta": {
                            "to_be_translated_in_front": False,
                            "missing_translation": False,
                            **extra_metas
                        }
                    }
            except Exception as e:
                DebugService.app_debug_print(f"[ERROR] Failed to format id field: {e}", False)
                formatted_data["id"] = id_value

            # If force_include_fields is provided and not empty, only include those fields (plus 'id')
            # if force_include_fields:
            #     # Always include 'id' field
            #     if 'id' not in force_include_fields:
            #         force_include_fields.append('id')

            db_encryption = DBEncryptionService()
            # Add only fields that have display_value_on_tree=True in extra_metas
            for field_name, field in self.model_fields.items():
                if doc and field_name in doc:
                    field_value = doc[field_name]
                elif hasattr(self, field_name):
                    field_value = getattr(self, field_name)
                # Skip fields not in force_include_fields if it's provided
                if force_include_fields and field_name not in force_include_fields and field_name != 'id':
                    continue

                # Skip fields in force_exclude_fields or field_value
                if field_name in force_exclude_fields or field_value is None:
                    continue

                # Skip fields not in the document
                if field_name not in doc:
                    continue

                meta = field.json_schema_extra or {}
                # if meta.get("extra_metas", {}).get("display_value_on_tree", False):
                # field_value = doc.get(field_name)
                # Skip fields marked with `exclude_from_data_table` or `exclude_at_all`
                if meta.get("exclude_from_data_tree", False) or meta.get("exclude_from_data_table", False) or meta.get("exclude_at_all", False):
                    continue

                # Handle ObjectId conversion
                if isinstance(field_value, ObjectId):
                    field_value = str(field_value)

                # Handle encrypted fields
                can_be_encrypted = meta.get("can_be_encrypted", False)
                if can_be_encrypted and isinstance(field_value, str) and field_value.startswith(db_encryption.VERSION_PREFIX):
                    # Decrypt the field value
                    field_value = db_encryption.decrypt(field_value)

                # Handle translations if needed
                if meta.get("may_have_translation", False) and accept_language != DEFAULT_LANGUAGE:
                    # Get model name for translation context
                    settings = getattr(self, 'Settings', None)
                    if settings and hasattr(settings, 'name'):
                        model_name = settings.name
                    else:
                        model_name = self.__class__.__name__.lower()
                    field_value = await BaseModelUtils.get_innter_translation(
                        targeted_id=formatted_data["id"],
                        property_name=field_name,
                        short_code=accept_language,
                        property_value=field_value,
                        model_name=model_name
                    )
                extra_metas = meta.get("extra_metas", {})
                overview_data_type = meta.get("overview_data_type", None)

                try:
                    # Get the field translation for display title
                    from app.modules.core.services.translation.translation_service import TranslationService
                    display_title = await TranslationService.get_static_fields_translation(
                        property_name=field_name,
                        accept_language=accept_language
                    )

                    # Determine if translation is missing
                    may_have_translation = meta.get("may_have_translation", False)
                    missing_translation = False

                    if may_have_translation and accept_language != DEFAULT_LANGUAGE:
                        # The value in tree_data should already be translated
                        # We just need to check if it's the same as the original
                        original_value = getattr(self, field_name, None)
                        if doc and field_name in doc:
                            original_value = doc[field_name]
                        missing_translation = field_value == original_value
                    data_type = extra_metas.get("data_type", {"is_unknown": True})
                    data_source = extra_metas.get("select_source_model")
                    cascade_data_source = extra_metas.get("cascade_source_model")
                    DebugService.app_debug_print(f"[DEBUG] Processing field {field_name}: data_source={data_source}, cascade_data_source={cascade_data_source}", False)
                    DebugService.app_debug_print(f"[DEBUG] Field {field_name} overview_data_type: {overview_data_type}, field_value: {field_value}", False)
                    if overview_data_type and overview_data_type.get('is_select', False) and data_source and field_value:
                        query = {
                            "filter___id": field_value
                        }
                        # Fetch data from the select_source_model collection
                        try:
                            DebugService.app_debug_print(f"[DEBUG] Fetching select data for {field_name} from {data_source} with query: {query}", False)
                            input_select_list = await generic_service.fetch_one_from_collection(
                                collection_key=CollectionKey(data_source),
                                output_data_type=OutputDataType.INPUT_SELECT,
                                query=query,
                                accept_language=accept_language
                            )
                            if input_select_list:
                                extra_metas['data_source_value'] = input_select_list
                                DebugService.app_debug_print(f"[DEBUG] Successfully fetched select data for {field_name}: {input_select_list}", False)
                            else:
                                DebugService.app_debug_print(f"[DEBUG] No select data found for {field_name}", False)
                        except Exception as e:
                            DebugService.app_debug_print(f"[ERROR] Failed to fetch select data for '{field_name}': {e}", True)

                    if overview_data_type and overview_data_type.get('is_cascade', False) and cascade_data_source and field_value:
                        query = {
                            "filter___id": field_value
                        }
                        # Fetch data from the cascade_source_model collection
                        try:
                            DebugService.app_debug_print(f"[DEBUG] Fetching cascade data for {field_name} from {cascade_data_source} with query: {query}", False)
                            input_select_list = await generic_service.fetch_one_from_collection(
                                collection_key=CollectionKey(cascade_data_source),
                                output_data_type=OutputDataType.INPUT_SELECT,
                                query=query,
                                accept_language=accept_language
                            )
                            if input_select_list:
                                extra_metas['data_source_value'] = input_select_list
                                DebugService.app_debug_print(f"[DEBUG] Successfully fetched cascade data for {field_name}: {input_select_list}", False)
                            else:
                                DebugService.app_debug_print(f"[DEBUG] No cascade data found for {field_name}", False)
                        except Exception as e:
                            DebugService.app_debug_print(f"[ERROR] Failed to fetch cascade data for '{field_name}': {e}", True)
                    #     extra_metas['data_source_value'] = input_select_list
                    # Determine display value based on field type
                    display_value = field_value

                    # For cascade fields, use the fetched display_value if available
                    if overview_data_type and overview_data_type.get('is_cascade', False) and 'data_source_value' in extra_metas:
                        cascade_data = extra_metas['data_source_value']
                        if cascade_data and isinstance(cascade_data, dict) and 'display_value' in cascade_data:
                            display_value = cascade_data['display_value']
                            DebugService.app_debug_print(f"[DEBUG] Using cascade display_value for {field_name}: {display_value}", False)
                    # For select fields, use the fetched display_value if available
                    elif overview_data_type and overview_data_type.get('is_select', False) and 'data_source_value' in extra_metas:
                        select_data = extra_metas['data_source_value']
                        if select_data and isinstance(select_data, dict) and 'display_value' in select_data:
                            display_value = select_data['display_value']
                            DebugService.app_debug_print(f"[DEBUG] Using select display_value for {field_name}: {display_value}", False)

                    # Format the field in data_table style
                    formatted_data[field_name] = {
                        "display_title": display_title,
                        "display_value": display_value,
                        "real_value": getattr(self, field_name, field_value) if hasattr(self, field_name) else field_value,
                        "data_type": overview_data_type  if overview_data_type is not None else data_type,
                        # "data_type": {
                        #     f"is_{field.annotation.__name__.lower()}": True
                        # } if hasattr(field.annotation, "__name__") else {},
                        "meta": {
                            "to_be_translated_in_front": meta.get("to_be_translated_in_front", False),
                            "missing_translation": missing_translation,
                            **extra_metas
                        }
                    }
                except Exception as e:
                    DebugService.app_debug_print(f"[ERROR] Failed to process field {field_name}: {e}", True)
                    # Keep the original value if processing fails
                    formatted_data[field_name] = field_value

            # Get model name for determining child relationship
            settings = getattr(self, 'Settings', None)
            if settings and hasattr(settings, 'name'):
                model_name = settings.name
            else:
                model_name = self.__class__.__name__.lower()
            parent_field = f"{model_name}_id"

            # Batch fetch children instead of individual queries
            if collection_key:


                try:
                    # Fetch all children in a single query with optimized output
                    DebugService.app_debug_print(f"\n\n\n before _native_query : {formatted_data['id']} TREEE sort 10> : {sort}\n\n\n", True)
                    _native_query = {parent_field: ObjectId(formatted_data['id']['display_value'])}
                    DebugService.app_debug_print(f"\n\n\n _native_query : {_native_query} TREEE sort 10> : {sort}\n\n\n", True)
                    children_data = []
                    children_data = await generic_service.fetch_native_query_data_from_collection(
                        collection_key=collection_key,
                        all_data=True,
                        output_data_type=OutputDataType.TREE_DATA_TABLE,  # Use TREE format for recursive structure
                        accept_language=accept_language,
                        # native_query={parent_field: ObjectId(id_value)},
                        native_query=_native_query,
                        sort=sort,
                    )

                    # Add children to the formatted data
                    if children_data:
                        formatted_data["children"] = children_data
                    else:
                        formatted_data["children"] = []
                except RecursionError:
                    DebugService.app_debug_print("Recursion error detected in tree formatting. Limiting depth.", True)
                    formatted_data["children"] = []
                except Exception as e:
                    DebugService.app_debug_print(f"Error fetching children: {str(e)}", True)
                    formatted_data["children"] = []
            else:
                formatted_data["children"] = []

            return formatted_data
        else:
            # Initialize result dictionary with only essential fields
            formatted_data = {
                "id": str(self.id)
            }

            # TODO: Implement non-doc path for tree data table if needed
            # For now, return basic structure
            return formatted_data
