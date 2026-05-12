

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from bson import ObjectId
from app.modules.core.utils.common.async_runner import AsyncExecutor
from pydantic import BaseModel, ValidationError, model_validator
from beanie import Document
import uuid
import re
import asyncio
from app.modules.core.models.mapping_keys import CollectionKey
from googletrans import Translator

from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.encryption.encryption_service import CURRENT_KEY_VERSION
from app.modules.core.services.encryption.db_encryption_service import DBEncryptionService
from app.modules.core.services.model.model_service import ModelService
from app.modules.core.enums.type_enum import AppGeneratorType, OutputDataType
from app.modules.core.utils.model.timestamp_mixin import TimestampMixin


class BaseModelUtils:

    # Cache for translations to avoid repeated DB updates
    _translation_cache = {}
    _translation_update_queue = {}
    _translation_update_lock = None
    _google_translation_cache = {}
    # Semaphore to limit concurrent translation operations
    _semaphore = asyncio.Semaphore(10)

    @classmethod
    def get_translation_update_lock(cls):
        """Get or create the translation update lock."""
        if cls._translation_update_lock is None:
            cls._translation_update_lock = asyncio.Lock()
        return cls._translation_update_lock

    @staticmethod
    def generate_uuid() -> str:
        """
        Generates a UUID.
        """
        return str(uuid.uuid4())

    @staticmethod
    def generate_hash_from_name(name: Optional[str]) -> str:
        """
        Generates a hash value based on the provided name.
        """
        if not name:
            raise ValueError("Name is required for hash generation.")
        sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
        return f"{sanitized_name}_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def extract_display(value):
        """
        Recursively extract the inner 'display_value' from wrapped fields.

        If the value is a dict with both "display_title" and "display_value" keys,
        then it is considered a wrapped field and the inner "display_value" is returned
        (processed recursively). Otherwise, if it's a dict without these keys,
        each key is processed recursively. Lists are handled similarly.
        """
        if isinstance(value, dict):
            # If this dict represents a wrapped field, return its inner display_value.
            if "display_title" in value and "display_value" in value:
                return BaseModelUtils.extract_display(value["display_value"])
            else:
                # Otherwise, process each key/value pair recursively.
                return {k: BaseModelUtils.extract_display(v) for k, v in value.items()}
        elif isinstance(value, list):
            # Process each element of the list.
            return [BaseModelUtils.extract_display(item) for item in value]
        else:
            # For primitive types, return the value as is.
            return value

    @staticmethod
    async def get_fields_translation(
        targeted_id: str,
        short_code: str,
        properties: Dict[str, Any],
        add_timestamps: bool = False,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve translations for multiple fields and recursively convert special types.
        Optimized for performance.
        """
        # Import TranslationService lazily to avoid circular imports.
        from app.modules.core.services.translation.translation_service import TranslationService
        translation_service = TranslationService()
        translated_properties = {}

        # Cache for static field translations to avoid repeated DB queries
        static_translation_cache = {}

        async def get_cached_static_translation(property_name):
            """Get static translation from cache or fetch it if not cached"""
            if property_name not in static_translation_cache:
                static_translation_cache[property_name] = await translation_service.get_static_fields_translation(
                    property_name=property_name,
                    accept_language=short_code
                )
            return static_translation_cache[property_name]

        async def format_child(value, property_item, key: str = "") -> Any:
            """
            Recursively format child elements so that the structure matches the top-level field.
            For primitive values, wrap them in a dict containing:
            - display_value: the key (or empty string if not provided)
            - display_value: the (already recursively converted) value
            - real_value: the original value
            - data_type: inherited from the parent property_item
            - meta: inherited meta flags (with missing_translation set to False for children)
            """
            if isinstance(value, list):
                # Process each element in the list recursively.
                return [await format_child(item, property_item, key="") for item in value]
            elif isinstance(value, dict):
                # Process each key/value pair in the dict.
                formatted_dict = {}
                for k, v in value.items():
                    formatted_dict[k] = await format_child(v, property_item, key=k)
                return formatted_dict
            else:
                # For a primitive value, translate if needed.
                child_translated = (
                    await BaseModelUtils.get_innter_translation(
                        targeted_id=targeted_id,
                        property_name=key,
                        short_code=short_code,
                        property_value=value,
                        model_name=model_name
                    )
                    if property_item.may_have_translation
                    else value
                )
                child_translated = ConverterService.recursive_convert(child_translated)
                # Obtain a static display name for this child field.
                child_display_value = await get_cached_static_translation(key)

                return {
                    "display_tltle": child_display_value,
                    "display_value": child_translated,
                    "real_value": value,
                    "data_type": property_item.data_type,
                    "meta": {
                        "to_be_translated_in_front": property_item.to_be_translated_in_front,
                        "missing_translation": False,
                        **property_item.extra_metas
                    }
                }

        # Process all fields in parallel for better performance
        async def process_field(field_name, property_item):
            # Retrieve translation if necessary; otherwise use the original value.
            translated = (
                await BaseModelUtils.get_innter_translation(
                    targeted_id=targeted_id,
                    property_name=property_item.property_name,
                    short_code=short_code,
                    property_value=property_item.property_value,
                    model_name=model_name
                )
                if property_item.may_have_translation
                else property_item.property_value
            )

            # Obtain a static display name for the field.
            display_value = await get_cached_static_translation(field_name)

            # Recursively convert the translated value.
            translated = ConverterService.recursive_convert(translated)

            # If the original property value is a composite type, format its children recursively.
            if isinstance(property_item.property_value, (list, dict)):
                translated = await format_child(translated, property_item, key=field_name)
                # For composite types, we override the missing_translation flag.
                missing_translation = False
            else:
                # For primitive types, check if translation is needed and if it was successful
                # Handle boolean values specially - they don't need translation
                if isinstance(property_item.property_value, bool):
                    missing_translation = False
                else:
                    missing_translation = property_item.may_have_translation and translated == property_item.property_value

            return field_name, {
                "display_title": display_value,
                "display_value": translated,
                "real_value": property_item.property_value,
                "data_type": property_item.data_type,
                "meta": {
                    "to_be_translated_in_front": property_item.to_be_translated_in_front,
                    "missing_translation": missing_translation,
                    **property_item.extra_metas
                }
            }

        # Process fields in batches to avoid overwhelming the system
        batch_size = 10
        field_items = list(properties.items())

        for i in range(0, len(field_items), batch_size):
            batch = field_items[i:i+batch_size]
            # Process batch in parallel
            results = await AsyncExecutor.gather([process_field(field_name, property_item)
                                           for field_name, property_item in batch])

            # Add results to translated_properties
            for field_name, result in results:
                translated_properties[field_name] = result

        # if add_timestamps:
        #     display_value = await get_cached_static_translation("created_at")
        #     translated_properties["created_at"] = {
        #         "display_title": display_value,
        #         "display_value": ConverterService.recursive_convert(self.created_at),
        #         "data_type": {
        #             "is_date": True,
        #         },
        #         "meta": {
        #             "can_be_translated": False,
        #         }
        #     }
        return translated_properties

    @staticmethod
    async def google_translate_text(text: str, target_language='fr'):
        """
        Translate text using Google Translate without blocking the event loop.
        Uses caching for performance.
        """

        if not text:
            return text

        # Cache key
        cache_key = f"{text}:{target_language}"
        if cache_key in BaseModelUtils._google_translation_cache:
            return BaseModelUtils._google_translation_cache[cache_key]

        try:
            # Run the blocking translate call in a thread
            def blocking_translate():
                translator = Translator()
                translated = translator.translate(text=text, dest=target_language)
                return translated.text

            result = await AsyncExecutor.run_in_thread(blocking_translate)

            # Cache the result
            BaseModelUtils._google_translation_cache[cache_key] = result

            return result

        except Exception as e:
            # Only log short texts to avoid log spam
            if len(text) < 100:
                DebugService.app_debug_print(f"Auto Translation error: {e} text: {text}", True)
            return text
    
    @staticmethod
    async def get_innter_translation(
        targeted_id: str,
        property_name: str,
        short_code: str,
        property_value: Any,
        model_name: Optional[str] = None
    ) -> Any:
        """
        Fully non-blocking translation retrieval, with recursive support for lists/dicts,
        caching, and batched updates.
        """

        # Process lists recursively in parallel with semaphore
        if isinstance(property_value, list):
            async def translate_item(item):
                async with BaseModelUtils._semaphore:
                    return await BaseModelUtils.get_innter_translation(
                        targeted_id, property_name, short_code, item, model_name
                    )

            tasks = [translate_item(item) for item in property_value]
            return await AsyncExecutor.gather(tasks)

        # Process dicts recursively
        if isinstance(property_value, dict):
            translated_dict = {}
            tasks = []
            keys = []

            async def translate_value(value):
                async with BaseModelUtils._semaphore:
                    return await BaseModelUtils.get_innter_translation(
                        targeted_id, property_name, short_code, value, model_name
                    )

            for key, value in property_value.items():
                keys.append(key)
                tasks.append(translate_value(value))

            results = await AsyncExecutor.gather(tasks)
            for i, key in enumerate(keys):
                translated_dict[key] = results[i]

            return translated_dict

        # For simple values
        if short_code is None or short_code == DEFAULT_LANGUAGE \
            or targeted_id is None or property_name is None or property_value is None:
            return property_value

        # Convert datetime to string
        if isinstance(property_value, datetime):
            property_value = property_value.isoformat()

        # Cache key
        cache_key = f"{targeted_id}:{property_name}:{short_code}:{property_value}"
        if cache_key in BaseModelUtils._translation_cache:
            return BaseModelUtils._translation_cache[cache_key]

        # Retrieve or create translations structure
        translations = BaseModelUtils._translation_cache or {}
        if property_name not in translations:
            translations[property_name] = {}
        if short_code in translations[property_name]:
            translation_value = translations[property_name][short_code]
            BaseModelUtils._translation_cache[cache_key] = translation_value
            return translation_value

        # Perform non-blocking translation
        translated = await BaseModelUtils.google_translate_text(
            text=property_value,
            target_language=short_code
        )

        # Cache the result
        BaseModelUtils._translation_cache[cache_key] = translated
        translations[property_name][short_code] = translated
        BaseModelUtils._translation_cache = translations

        # Queue updates safely
        async with BaseModelUtils.get_translation_update_lock():
            if targeted_id not in BaseModelUtils._translation_update_queue:
                BaseModelUtils._translation_update_queue[targeted_id] = {
                    "model_name": model_name or "base_model_utils",
                    "translations": translations.copy()
                }
            else:
                # Merge with existing queued translations
                for prop_name, trans_dict in translations.items():
                    if prop_name not in BaseModelUtils._translation_update_queue[targeted_id]["translations"]:
                        BaseModelUtils._translation_update_queue[targeted_id]["translations"][prop_name] = {}
                    for lang, trans_value in trans_dict.items():
                        BaseModelUtils._translation_update_queue[targeted_id]["translations"][prop_name][lang] = trans_value

            # Schedule background update task
            if not getattr(BaseModelUtils, "_update_task_scheduled", False):
                BaseModelUtils._update_task_scheduled = True
                asyncio.create_task(BaseModelUtils._process_translation_updates())

        return translated
    # @staticmethod
    # async def get_innter_translation(
    #         targeted_id: str, property_name: str, short_code: str, property_value: any, model_name: Optional[str] = None
    # ) -> any:
    #     """
    #     Retrieve a translation for a given property value. If property_value is a list or dict,
    #     translate each element recursively.

    #     Optimized for performance with caching and batched updates.
    #     """
    #     # Process lists recursively.
    #     if isinstance(property_value, list):
    #         # Process list items in parallel
    #         tasks = [BaseModelUtils.get_innter_translation(
    #             targeted_id, property_name, short_code, item, model_name
    #         ) for item in property_value]
    #         return await asyncio.gather(*tasks)

    #     # Process dicts recursively.
    #     if isinstance(property_value, dict):
    #         # Process dict items in parallel
    #         translated_dict = {}
    #         tasks = []
    #         keys = []

    #         for key, value in property_value.items():
    #             keys.append(key)
    #             tasks.append(BaseModelUtils.get_innter_translation(
    #                 targeted_id, property_name, short_code, value, model_name
    #             ))

    #         results = await asyncio.gather(*tasks)
    #         for i, key in enumerate(keys):
    #             translated_dict[key] = results[i]

    #         return translated_dict

    #     # For simple values:
    #     if short_code is None or short_code == DEFAULT_LANGUAGE or targeted_id is None or property_name is None or property_value is None:
    #         return property_value

    #     # Convert datetime to string if necessary.
    #     if isinstance(property_value, datetime):
    #         property_value = property_value.isoformat()

    #     # Create a cache key for this translation
    #     cache_key = f"{targeted_id}:{property_name}:{short_code}:{property_value}"

    #     # Check if we have this translation in cache
    #     if cache_key in BaseModelUtils._translation_cache:
    #         return BaseModelUtils._translation_cache[cache_key]

    #     # Retrieve translations from the instance.
    #     translations = BaseModelUtils._translation_cache or {}

    #     # Ensure there's a TranslationInfo for the given property.
    #     if property_name not in translations:
    #         translations[property_name] = {}

    #     # Check if a translation for the given language already exists.
    #     if short_code in translations[property_name]:
    #         translation_value = translations[property_name][short_code]
    #         # Cache the result
    #         BaseModelUtils._translation_cache[cache_key] = translation_value
    #         return translation_value

    #     # Otherwise, obtain the translation using Google Translate.
    #     translated = await BaseModelUtils.google_translate_text(text=property_value, target_language=short_code)

    #     # Cache the result
    #     BaseModelUtils._translation_cache[cache_key] = translated

    #     # Update the translations structure.
    #     translations[property_name][short_code] = translated

    #     # Update the instance attribute
    #     BaseModelUtils._translation_cache = translations

    #     # Queue the update instead of doing it immediately
    #     # This allows us to batch updates for better performance
    #     async with BaseModelUtils.get_translation_update_lock():
    #         if targeted_id not in BaseModelUtils._translation_update_queue:
    #             BaseModelUtils._translation_update_queue[targeted_id] = {
    #                 "model_name": model_name or "base_model_utils",  # Use provided model_name or fallback
    #                 "translations": translations.copy()
    #             }
    #         else:
    #             # Merge with existing queued translations
    #             for prop_name, trans_dict in translations.items():
    #                 if prop_name not in BaseModelUtils._translation_update_queue[targeted_id]["translations"]:
    #                     BaseModelUtils._translation_update_queue[targeted_id]["translations"][prop_name] = {}

    #                 for lang, trans_value in trans_dict.items():
    #                     BaseModelUtils._translation_update_queue[targeted_id]["translations"][prop_name][lang] = trans_value

    #         # Schedule a background task to process the queue if not already scheduled
    #         if not hasattr(BaseModelUtils, "_update_task_scheduled") or not BaseModelUtils._update_task_scheduled:
    #             BaseModelUtils._update_task_scheduled = True
    #             asyncio.create_task(BaseModelUtils._process_translation_updates())

    #     return translated

    @staticmethod
    async def _process_translation_updates():
        """Process queued translation updates in batches"""
        try:
            # Wait a short time to allow more translations to be queued
            await asyncio.sleep(0.5)

            # Get all queued updates
            async with BaseModelUtils.get_translation_update_lock():
                updates = BaseModelUtils._translation_update_queue.copy()
                BaseModelUtils._translation_update_queue.clear()
                BaseModelUtils._update_task_scheduled = False

            if not updates:
                return

            # Process updates
            from app.modules.core.services.generic.generic_services import GenericService

            for targeted_id, update_info in updates.items():
                try:
                    model_name = update_info["model_name"]
                    translations = update_info["translations"]

                    # Get the collection key
                    collection_key = ModelService.get_collection_key_from_model_name(model_name)

                    # Update the database (use DEFAULT_LANGUAGE for the service since we're just updating)
                    generic_service = GenericService(DEFAULT_LANGUAGE)
                    await generic_service.update_data_in_collection(
                        collection_key=CollectionKey(collection_key).value,
                        item_id=targeted_id,
                        data={"translations": translations}
                    )
                except Exception as e:
                    # Log error but don't fail the entire batch
                    DebugService.app_debug_print(f"Error updating translations for {targeted_id}: {e}", False)
        except Exception as e:
            DebugService.app_debug_print(f"Error in _process_translation_updates: {e}", False)


            