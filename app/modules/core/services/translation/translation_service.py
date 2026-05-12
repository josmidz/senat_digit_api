from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.models.field_translation_keys import (
    DEFAULT_LANGUAGE, FIELD_ERROR_TRANSLATED,
    STATIC_HEADING_TITLE_KEYS, TRANSLATION_KEYS,
    TRANSLATIONS
)
import time
from googletrans import Translator
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.enums.type_enum import ECollectionCrudInfoFlag, OutputDataType



class TranslationService(DebugService,):
    # Class-level registry for additional enum modules
    _additional_enum_modules = []
    # Cache for discovered enum modules to avoid repeated file system scans
    _discovered_modules_cache = None

    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.core.services.generic.generic_services import GenericService
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        super().__init__(accept_language)

    @classmethod
    def register_enum_module(cls, module_path: str):
        """
        Register an additional enum module to be searched.
        This allows dynamic registration of new enum modules without modifying the core code.

        Args:
            module_path (str): The full module path (e.g., 'app.modules.custom.enums.custom_enum')
        """
        if module_path not in cls._additional_enum_modules:
            cls._additional_enum_modules.append(module_path)
            DebugService.app_debug_print(f"📝 Registered additional enum module: {module_path}")

    @classmethod
    def discover_enum_modules(cls):
        """
        Dynamically discover all enum modules in the application.
        This scans the app.modules directory structure to find enum modules.
        Uses caching to avoid repeated file system scans.
        """
        # Return cached result if available
        if cls._discovered_modules_cache is not None:
            return cls._discovered_modules_cache

        import os

        discovered_modules = []
        app_modules_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')

        try:
            DebugService.app_debug_print(f"🔍 Discovering enum modules in: {app_modules_path}")

            # Walk through the app/modules directory
            for root, dirs, files in os.walk(app_modules_path):
                # Skip __pycache__ and other non-relevant directories
                dirs[:] = [d for d in dirs if not d.startswith('__') and not d.startswith('.')]

                for file in files:
                    if file.endswith('.py') and 'enum' in file.lower():
                        # Construct the module path
                        relative_path = os.path.relpath(os.path.join(root, file), app_modules_path)
                        module_parts = relative_path.replace(os.sep, '.').replace('.py', '')

                        # Only include modules that start with 'modules.'
                        if module_parts.startswith('modules.'):
                            full_module_path = f'app.{module_parts}'
                            discovered_modules.append(full_module_path)

            # Sort by priority (core first, then alphabetically)
            priority_order = ['core', 'postal_services', 'auth', 'expensechain']

            def sort_key(module_path):
                for i, priority in enumerate(priority_order):
                    if f'.{priority}.' in module_path:
                        return (i, module_path)
                return (len(priority_order), module_path)

            discovered_modules.sort(key=sort_key)

            DebugService.app_debug_print(f"📋 Discovered {len(discovered_modules)} enum modules: {discovered_modules}")

        except Exception as e:
            DebugService.app_debug_print(f"⚠️ Error during enum module discovery: {e}")
            # Fallback to essential modules if discovery fails
            discovered_modules = [
                'app.modules.core.enums.type_enum',
                'app.modules.postal_services.enums.postal_service_enum',
            ]

        # Cache the result
        cls._discovered_modules_cache = discovered_modules
        return discovered_modules

    @classmethod
    def clear_discovery_cache(cls):
        """
        Clear the discovered modules cache. Useful when new modules are added at runtime.
        """
        cls._discovered_modules_cache = None
        DebugService.app_debug_print("🗑️ Cleared enum module discovery cache")

    @classmethod
    def discover_loaded_enum_modules(cls):
        """
        Alternative discovery method that scans already loaded modules.
        This is faster and more reliable than file system scanning.
        """
        import sys
        from enum import Enum

        discovered_modules = []

        try:
            for module_name, module in sys.modules.items():
                if (module and
                    module_name.startswith('app.modules') and
                    ('enum' in module_name.lower() or 'type' in module_name.lower())):

                    # Check if the module actually contains Enum classes
                    has_enums = False
                    try:
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (isinstance(attr, type) and
                                issubclass(attr, Enum) and
                                attr != Enum):
                                has_enums = True
                                break
                    except (TypeError, AttributeError):
                        continue

                    if has_enums and module_name not in discovered_modules:
                        discovered_modules.append(module_name)

            # Sort by priority
            priority_order = ['core', 'postal_services', 'auth', 'expensechain']

            def sort_key(module_path):
                for i, priority in enumerate(priority_order):
                    if f'.{priority}.' in module_path:
                        return (i, module_path)
                return (len(priority_order), module_path)

            discovered_modules.sort(key=sort_key)

        except Exception as e:
            DebugService.app_debug_print(f"⚠️ Error during loaded module discovery: {e}")

        return discovered_modules

    @classmethod
    def get_all_enum_modules(cls):
        """
        Get all enum modules to search, including discovered and registered additional modules.
        Uses both file system discovery and loaded module discovery for maximum coverage.
        """
        # Try loaded modules first (faster and more reliable)
        loaded_modules = cls.discover_loaded_enum_modules()

        # Fall back to file system discovery if needed
        if not loaded_modules:
            discovered_modules = cls.discover_enum_modules()
        else:
            discovered_modules = loaded_modules

        # Combine with manually registered modules
        all_modules = discovered_modules + cls._additional_enum_modules

        # Remove duplicates while preserving order
        seen = set()
        unique_modules = []
        for module in all_modules:
            if module not in seen:
                seen.add(module)
                unique_modules.append(module)

        return unique_modules

    @staticmethod
    def get_translated_value(enum_instance, accept_language="fr"):
        """
        Returns the translated value for the given enum instance based on the language.
        """
        if accept_language not in TRANSLATIONS:
            accept_language = "en"  # Default to English if language is not supported

        enum_type = type(enum_instance)
        if enum_type in TRANSLATIONS[accept_language]:
            return TRANSLATIONS[accept_language][enum_type].get(enum_instance, "Unknown")
        return "Unknown"



    @staticmethod
    def get_enum_class_from_string(enum_class_str: str):
        """
        Converts a string (e.g., "EGender") to the corresponding enum class.
        Uses a dynamic approach to search through common enum modules.
        """
        try:
            # First, try to get the enum from globals
            if enum_class_str in globals():
                enum_class = globals()[enum_class_str]
                if issubclass(enum_class, Enum):
                    return enum_class

            # Get all enum modules to search (including dynamically registered ones)
            enum_modules = TranslationService.get_all_enum_modules()

            # Search through each module
            for module_path in enum_modules:
                try:
                    module = __import__(module_path, fromlist=[enum_class_str])
                    if hasattr(module, enum_class_str):
                        enum_class = getattr(module, enum_class_str)
                        if issubclass(enum_class, Enum):
                            DebugService.app_debug_print(f"✅ Found enum {enum_class_str} in module {module_path}")
                            return enum_class
                except ImportError as import_error:
                    # Silently continue to next module - this is expected for optional modules
                    continue
                except Exception as e:
                    DebugService.app_debug_print(f"⚠️ Error checking module {module_path} for enum {enum_class_str}: {e}")
                    continue

            # If we get here, try a more advanced discovery approach
            # This can help find enums in modules that might be added in the future
            DebugService.app_debug_print(f"🔍 Enum {enum_class_str} not found in common modules, attempting advanced discovery...")

            # Try to find the enum in any loaded modules that contain 'enum' in their name
            import sys
            for module_name, module in sys.modules.items():
                if (module and
                    'enum' in module_name.lower() and
                    module_name.startswith('app.modules') and
                    hasattr(module, enum_class_str)):
                    try:
                        enum_class = getattr(module, enum_class_str)
                        if issubclass(enum_class, Enum):
                            DebugService.app_debug_print(f"🎯 Found enum {enum_class_str} in discovered module {module_name}")
                            return enum_class
                    except (TypeError, AttributeError):
                        continue

            # If we get here, the enum wasn't found anywhere
            DebugService.app_debug_print(f"❌ Enum {enum_class_str} not found in any known or discovered modules.")
            raise ValueError(f"Enum class {enum_class_str} not found in any available modules.")

        except (KeyError, AttributeError, ImportError) as e:
            DebugService.app_debug_print(f"❌ Error fetching enum {enum_class_str}: {e}")
            raise ValueError(f"Enum class {enum_class_str} not found: {e}")

    @staticmethod
    def get_enum_translated_data_list(enum_class, property_name_str, accept_language="fr"):
        """
        Returns a list of dictionaries containing enum properties with translated display names.

        Each dictionary has:
        - "id": The enum member's value (e.g., "google", "m", "active"),
        - "property_name": The provided property name,
        - "display_value": The translated display name.

        If enum_class is provided as a string, it converts it to the corresponding enum class.
        """
        DebugService.app_debug_print(f" > enum_class > '{enum_class}'",False)
        # If a string is provided, convert it to the actual enum class.
        if isinstance(enum_class, str):
            enum_class = TranslationService.get_enum_class_from_string(enum_class)
        DebugService.app_debug_print(f" > enum_class >>> '{enum_class}'",False)
        result = []
        for member in enum_class:
            DebugService.app_debug_print(f"member for '{member}'",False)
            result.append({
                "id": member.value,
                "property_name": property_name_str,
                "display_value": TranslationService.get_translated_value(member, accept_language),
            })
        return result

    # Helper function to get translated message
    @staticmethod
    def get_field_error_translated_message(language: str, key: str, **kwargs) -> str:
        """
        Get a translated message for the given language and key.
        """
        if language not in FIELD_ERROR_TRANSLATED:
            language = DEFAULT_LANGUAGE  # Fallback to English if language is not supported
        return FIELD_ERROR_TRANSLATED[language].get(key, key).format(**kwargs)

    @staticmethod
    async def get_static_fields_translation(property_name: str, accept_language: str) -> str:
        """
        Retrieve the translation for a given property name and language.

        Lookup order:
        1. Model-level registry (FIELD_TRANSLATION_KEYS declared on each model)
        2. Core TRANSLATION_KEYS (centralized fallback)
        3. Auto-titlecased property name

        :param property_name: The property name to translate.
        :param accept_language: The preferred language for translation.
        :return: The translated string or fallback to default language.
        """
        from app.modules.core.utils.model.base_document import BaseDocument
        # Check model-level registry first
        translations = BaseDocument._field_translation_registry.get(property_name, {})
        if not translations:
            # Fallback to core TRANSLATION_KEYS
            translations = TRANSLATION_KEYS.get(property_name, {})

        # Return the translation for the preferred language, or fallback to default language, or the property_name
        return translations.get(accept_language, translations.get(DEFAULT_LANGUAGE, property_name.replace("_", " ").title() ))
    @staticmethod
    async def get_static_heading_title_translation(heading_title: str, accept_language: str) -> str:
        """
        Retrieve the translation for a given property name and language.

        :param property_name: The property name to translate.
        :param accept_language: The preferred language for translation.
        :return: The translated string or fallback to default language.
        """
        # Fetch property translations, fallback to empty dictionary if not found
        translations = STATIC_HEADING_TITLE_KEYS.get(heading_title, {})

        # Return the translation for the preferred language, or fallback to default language, or the property_name
        return translations.get(accept_language, translations.get(DEFAULT_LANGUAGE, heading_title.replace("_", " ").title() ))

    async def get_translation(
        self, targeted_id: str, property_name: str, short_code: str, property_value: Any
    ) -> str:
        """
        Fetches (or creates) the translation for the given property using the provided short_code,
        and stores the translation in the document's own `translations` field.
        Each entry in `translations` is structured as:
            {
                "<property_name>": {
                    "<language_code>": "<translated_text>"
                }
            }
        """
        self.app_debug_print(f"step 1 : {short_code}", True)

        # Default language or missing required data: no translation needed.
        if short_code is None or short_code == DEFAULT_LANGUAGE or targeted_id is None or property_name is None or property_value is None:
            return property_value

        self.app_debug_print("step 2", True)
        # Convert datetime to string if necessary cls.
        if isinstance(property_value, datetime):
            property_value = property_value.isoformat()

        self.app_debug_print("step 3", True)
        # Retrieve translations from the instance. If none exists, initialize as an empty dict.
        translations: Dict[str, Dict[str, str]] = self.translations or {}

        self.app_debug_print(f"step 4 : {translations}", True)
        # Ensure there is a TranslationInfo for the given property.
        if property_name not in translations:
            translations[property_name] = {}

        self.app_debug_print(f"\n\n --> translations: {translations} \n\n", True)
        self.app_debug_print(f" short_code: {short_code} in translations: {short_code in translations[property_name]}", True)

        # Check if a translation for the given language already exists.
        if short_code in translations[property_name]:
            return translations[property_name][short_code]

        # Otherwise, obtain the translation using Google Translate.
        translated = await self.google_translate_text(text=property_value, target_language=short_code)
        self.app_debug_print(f"Auto translated value: {translated}", True)

        # Update the translations structure. We update the inner dictionary on the TranslationInfo instance.
        translations[property_name][short_code] = translated

        # Update the instance attribute before persisting the change.
        self.translations = translations

        # Determine the collection key using the model's Settings name.
        model_name = getattr(self.Settings, "name", self.__class__.__name__.lower())
        collection_key = self.generic_service.get_collection_key_from_model_name(model_name)

        # Persist the updated translations field to the database.
        await self.generic_service.update_data_in_collection(
            collection_key=CollectionKey(collection_key).value,
            item_id=targeted_id,
            data={"translations": translations}
        )

        return translated



    async def get_translationXXX(self, targeted_id: str, property_name: str, short_code: str, property_value: Any) -> str:
        """
        Fetches the translation for the given property using the provided `short_code`.
        """
        self.app_debug_print(f" short_code : {short_code} | targeted_id : {targeted_id} | property_name : {property_name} | property_value : {property_value}",False)
        if short_code == None or short_code == DEFAULT_LANGUAGE or targeted_id == None or property_name == None or property_value == None:
            return property_value  # Default language, no translation needed

        try:
            # Convert datetime to string before JSON serialization
            if isinstance(property_value, datetime):
                property_value = property_value.isoformat()

            lang_query = {
                    f"filter__short_code":short_code
            }
            self.app_debug_print(f" lang_query : {lang_query}",False)
            language_doc = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_LANGUAGE,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=short_code,
                query={
                   **lang_query
                }
            )
            self.app_debug_print(f" language_doc : {language_doc}",False)

            if not language_doc:
                return property_value  # No translation if language not found

            ref_language_id = language_doc['id']
            self.app_debug_print(f" ref_language_id : {ref_language_id}",False)
            translation_entry_query = {
                "filter__targeted_id": str(targeted_id),
                "filter__mixed_id_str": f"{str(targeted_id)}:{property_name}",
                "filter__ref_language_id": str(ref_language_id)
            }
            self.app_debug_print(f" translation_entry_query : {translation_entry_query}",False)
            translation_entry  = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_TRANSLATION,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language='fr',
                query={
                        **translation_entry_query
                    }
            )
            self.app_debug_print(f"\n\n translation_entry FOUNDED : {True if translation_entry else False}",False)
            if translation_entry:
                return translation_entry['translation']
            else:
                # save auto translation and save
                translated = await self.google_translate_text(text=property_value,target_language=short_code)
                self.app_debug_print(f"\n auto translated : {translated}",False)
                data = {
                    "targeted_id": str(targeted_id),
                    "ref_language_id":ref_language_id,
                    "mixed_id_str":f"{targeted_id}:{property_name}",
                    "translation":translated
                }
                translation_saved = await self.generic_service.add_data_to_collection(CollectionKey.CFG_TRANSLATION, data)
                # app_debug_print(f"\n\n translation_saved : {translation_saved}",True)
                return translated
        except Exception as e:
            self.app_debug_print(f"Error during translation fetch: {e}",False)
            return property_value

    async def google_translate_text(self, text: str, target_language='fr'):
        translator = Translator()
        if not text:
            return text
        try:
            translated = await translator.translate(text=text, dest=target_language)
            return translated.text
        except Exception as e:
            self.app_debug_print(f"Auto Translation error: {e} text: {text}")
            raise ValueError(f"Auto Translation error: {e}")
