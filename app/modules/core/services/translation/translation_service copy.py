# from datetime import datetime
# from enum import Enum
# from typing import Any, Dict, Optional
# from app.modules.core.models.mapping_keys import CollectionKey
# from app.modules.core.models.field_translation_keys import (
#     DEFAULT_LANGUAGE, FIELD_ERROR_TRANSLATED,
#     STATIC_HEADING_TITLE_KEYS, TRANSLATION_KEYS,
#     TRANSLATIONS
# )
# import time
# from googletrans import Translator
# from app.modules.core.services.debug.debug_service import DebugService
# from app.modules.core.enums.type_enum import ECollectionCrudInfoFlag, OutputDataType



# class TranslationService(DebugService,):

#     def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
#         from app.modules.core.services.generic.generic_services import GenericService
#         self.accept_language = accept_language
#         self.generic_service = GenericService(accept_language)
#         super().__init__(accept_language)


#     @staticmethod
#     def get_translated_value(enum_instance, accept_language="fr"):
#         """
#         Returns the translated value for the given enum instance based on the language.
#         """
#         if accept_language not in TRANSLATIONS:
#             accept_language = "en"  # Default to English if language is not supported

#         enum_type = type(enum_instance)
#         if enum_type in TRANSLATIONS[accept_language]:
#             return TRANSLATIONS[accept_language][enum_type].get(enum_instance, "Unknown")
#         return "Unknown"



#     # Cache for discovered enums to improve performance
#     _enum_cache = {}

#     @staticmethod
#     def _discover_enum_modules():
#         """
#         Dynamically discover all enum modules in the application.
#         Returns a list of module paths that likely contain enums.
#         """
#         import os
#         import glob

#         enum_modules = []

#         # Get the base app directory
#         base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

#         # Search patterns for enum files
#         search_patterns = [
#             "**/enums/*.py",
#             "**/enum/*.py",
#             "**/*_enum.py",
#             "**/*_enums.py"
#         ]

#         for pattern in search_patterns:
#             enum_files = glob.glob(os.path.join(base_dir, pattern), recursive=True)
#             for file_path in enum_files:
#                 if "__pycache__" in file_path or file_path.endswith("__init__.py"):
#                     continue

#                 # Convert file path to module path
#                 rel_path = os.path.relpath(file_path, base_dir)
#                 module_path = rel_path.replace(os.sep, ".").replace(".py", "")

#                 # Skip if it doesn't start with app
#                 if module_path.startswith("app."):
#                     enum_modules.append(module_path)

#         return enum_modules

#     @staticmethod
#     def _load_enum_from_module(module_path: str, enum_class_str: str):
#         """
#         Try to load an enum class from a specific module.
#         """
#         try:
#             import importlib
#             module = importlib.import_module(module_path)

#             if hasattr(module, enum_class_str):
#                 enum_class = getattr(module, enum_class_str)
#                 if hasattr(enum_class, '__bases__') and any(issubclass(base, Enum) for base in enum_class.__bases__ if base != object):
#                     return enum_class
#                 elif issubclass(enum_class, Enum):
#                     return enum_class
#         except (ImportError, AttributeError, TypeError) as e:
#             # Silently ignore import errors for modules that can't be loaded
#             pass

#         return None

#     @classmethod
#     def get_all_enum_modules(cls):
#         """
#         Get all enum modules to search, including registered additional modules.
#         """
#         base_modules = [
#             'app.modules.core.enums.type_enum',                        # Core enums (EGender, etc.)
#             'app.modules.postal_services.enums.postal_service_enum',   # Postal services enums (ECustomerType, etc.)
#             'app.modules.auth.enums.common',                           # Auth common enums
#             'app.modules.auth.enums.auth',                             # Auth specific enums
#             'app.modules.auth.enums.mfa',                              # MFA enums
#             'app.modules.expensechain.modules.basic.enums.basic_enum', # Expense chain enums
#         ]
#         return base_modules + cls._additional_enum_modules
    
#     @staticmethod
#     def get_enum_class_from_string(enum_class_str: str):
#         """
#         Converts a string (e.g., "EGender") to the corresponding enum class.
#         Uses a dynamic approach to search through common enum modules.
#         """
#         try:
#             # First, try to get the enum from globals
#             if enum_class_str in globals():
#                 enum_class = globals()[enum_class_str]
#                 if issubclass(enum_class, Enum):
#                     return enum_class

#             # Get all enum modules to search (including dynamically registered ones)
#             enum_modules = TranslationService.get_all_enum_modules()

#             # Search through each module
#             for module_path in enum_modules:
#                 try:
#                     module = __import__(module_path, fromlist=[enum_class_str])
#                     if hasattr(module, enum_class_str):
#                         enum_class = getattr(module, enum_class_str)
#                         if issubclass(enum_class, Enum):
#                             DebugService.app_debug_print(f"✅ Found enum {enum_class_str} in module {module_path}")
#                             return enum_class
#                 except ImportError as import_error:
#                     # Silently continue to next module - this is expected for optional modules
#                     continue
#                 except Exception as e:
#                     DebugService.app_debug_print(f"⚠️ Error checking module {module_path} for enum {enum_class_str}: {e}")
#                     continue

#             # If we get here, try a more advanced discovery approach
#             # This can help find enums in modules that might be added in the future
#             DebugService.app_debug_print(f"🔍 Enum {enum_class_str} not found in common modules, attempting advanced discovery...")

#             # Try to find the enum in any loaded modules that contain 'enum' in their name
#             import sys
#             for module_name, module in sys.modules.items():
#                 if (module and
#                     'enum' in module_name.lower() and
#                     module_name.startswith('app.modules') and
#                     hasattr(module, enum_class_str)):
#                     try:
#                         enum_class = getattr(module, enum_class_str)
#                         if issubclass(enum_class, Enum):
#                             DebugService.app_debug_print(f"🎯 Found enum {enum_class_str} in discovered module {module_name}")
#                             return enum_class
#                     except (TypeError, AttributeError):
#                         continue

#             # If we get here, the enum wasn't found anywhere
#             DebugService.app_debug_print(f"❌ Enum {enum_class_str} not found in any known or discovered modules.")
#             raise ValueError(f"Enum class {enum_class_str} not found in any available modules.")

#         except (KeyError, AttributeError, ImportError) as e:
#             DebugService.app_debug_print(f"❌ Error fetching enum {enum_class_str}: {e}")
#             raise ValueError(f"Enum class {enum_class_str} not found: {e}")

#     @staticmethod
#     def clear_enum_cache():
#         """
#         Clear the enum cache. Useful during development or when new enums are added.
#         """
#         TranslationService._enum_cache.clear()
#         DebugService.app_debug_print("Enum cache cleared")

#     @staticmethod
#     def get_cached_enums():
#         """
#         Get a list of all cached enum names for debugging purposes.
#         """
#         return list(TranslationService._enum_cache.keys())

#     @staticmethod
#     def get_enum_translated_data_list(enum_class, property_name_str, accept_language="fr"):
#         """
#         Returns a list of dictionaries containing enum properties with translated display names.

#         Each dictionary has:
#         - "id": The enum member's value (e.g., "google", "m", "active"),
#         - "property_name": The provided property name,
#         - "display_value": The translated display name.

#         If enum_class is provided as a string, it converts it to the corresponding enum class.
#         """
#         DebugService.app_debug_print(f" > enum_class > '{enum_class}'",False)
#         # If a string is provided, convert it to the actual enum class.
#         if isinstance(enum_class, str):
#             enum_class = TranslationService.get_enum_class_from_string(enum_class)
#         DebugService.app_debug_print(f" > enum_class >>> '{enum_class}'",False)
#         result = []
#         for member in enum_class:
#             DebugService.app_debug_print(f"member for '{member}'",False)
#             result.append({
#                 "id": member.value,
#                 "property_name": property_name_str,
#                 "display_value": TranslationService.get_translated_value(member, accept_language),
#             })
#         return result

#     # Helper function to get translated message
#     @staticmethod
#     def get_field_error_translated_message(language: str, key: str, **kwargs) -> str:
#         """
#         Get a translated message for the given language and key.
#         """
#         if language not in FIELD_ERROR_TRANSLATED:
#             language = DEFAULT_LANGUAGE  # Fallback to English if language is not supported
#         return FIELD_ERROR_TRANSLATED[language].get(key, key).format(**kwargs)

#     @staticmethod
#     async def get_static_fields_translation(property_name: str, accept_language: str) -> str:
#         """
#         Retrieve the translation for a given property name and language.

#         :param property_name: The property name to translate.
#         :param accept_language: The preferred language for translation.
#         :return: The translated string or fallback to default language.
#         """
#         # Fetch property translations, fallback to empty dictionary if not found
#         translations = TRANSLATION_KEYS.get(property_name, {})

#         # Return the translation for the preferred language, or fallback to default language, or the property_name
#         return translations.get(accept_language, translations.get(DEFAULT_LANGUAGE, property_name.replace("_", " ").title() ))
#     @staticmethod
#     async def get_static_heading_title_translation(heading_title: str, accept_language: str) -> str:
#         """
#         Retrieve the translation for a given property name and language.

#         :param property_name: The property name to translate.
#         :param accept_language: The preferred language for translation.
#         :return: The translated string or fallback to default language.
#         """
#         # Fetch property translations, fallback to empty dictionary if not found
#         translations = STATIC_HEADING_TITLE_KEYS.get(heading_title, {})

#         # Return the translation for the preferred language, or fallback to default language, or the property_name
#         return translations.get(accept_language, translations.get(DEFAULT_LANGUAGE, heading_title.replace("_", " ").title() ))

#     async def get_translation(
#         self, targeted_id: str, property_name: str, short_code: str, property_value: Any
#     ) -> str:
#         """
#         Fetches (or creates) the translation for the given property using the provided short_code,
#         and stores the translation in the document's own `translations` field.
#         Each entry in `translations` is structured as:
#             {
#                 "<property_name>": {
#                     "<language_code>": "<translated_text>"
#                 }
#             }
#         """
#         self.app_debug_print(f"step 1 : {short_code}", True)

#         # Default language or missing required data: no translation needed.
#         if short_code is None or short_code == DEFAULT_LANGUAGE or targeted_id is None or property_name is None or property_value is None:
#             return property_value

#         self.app_debug_print("step 2", True)
#         # Convert datetime to string if necessary cls.
#         if isinstance(property_value, datetime):
#             property_value = property_value.isoformat()

#         self.app_debug_print("step 3", True)
#         # Retrieve translations from the instance. If none exists, initialize as an empty dict.
#         translations: Dict[str, Dict[str, str]] = self.translations or {}

#         self.app_debug_print(f"step 4 : {translations}", True)
#         # Ensure there is a TranslationInfo for the given property.
#         if property_name not in translations:
#             translations[property_name] = {}

#         self.app_debug_print(f"\n\n --> translations: {translations} \n\n", True)
#         self.app_debug_print(f" short_code: {short_code} in translations: {short_code in translations[property_name]}", True)

#         # Check if a translation for the given language already exists.
#         if short_code in translations[property_name]:
#             return translations[property_name][short_code]

#         # Otherwise, obtain the translation using Google Translate.
#         translated = await self.google_translate_text(text=property_value, target_language=short_code)
#         self.app_debug_print(f"Auto translated value: {translated}", True)

#         # Update the translations structure. We update the inner dictionary on the TranslationInfo instance.
#         translations[property_name][short_code] = translated

#         # Update the instance attribute before persisting the change.
#         self.translations = translations

#         # Determine the collection key using the model's Settings name.
#         model_name = getattr(self.Settings, "name", self.__class__.__name__.lower())
#         collection_key = self.generic_service.get_collection_key_from_model_name(model_name)

#         # Persist the updated translations field to the database.
#         await self.generic_service.update_data_in_collection(
#             collection_key=CollectionKey(collection_key).value,
#             item_id=targeted_id,
#             data={"translations": translations}
#         )

#         return translated



#     async def get_translationXXX(self, targeted_id: str, property_name: str, short_code: str, property_value: Any) -> str:
#         """
#         Fetches the translation for the given property using the provided `short_code`.
#         """
#         self.app_debug_print(f" short_code : {short_code} | targeted_id : {targeted_id} | property_name : {property_name} | property_value : {property_value}",False)
#         if short_code == None or short_code == DEFAULT_LANGUAGE or targeted_id == None or property_name == None or property_value == None:
#             return property_value  # Default language, no translation needed

#         try:
#             # Convert datetime to string before JSON serialization
#             if isinstance(property_value, datetime):
#                 property_value = property_value.isoformat()

#             lang_query = {
#                     f"filter__short_code":short_code
#             }
#             self.app_debug_print(f" lang_query : {lang_query}",False)
#             language_doc = await self.generic_service.fetch_one_from_collection(
#                 collection_key=CollectionKey.REF_LANGUAGE,
#                 output_data_type=OutputDataType.DEFAULT.value,
#                 accept_language=short_code,
#                 query={
#                    **lang_query
#                 }
#             )
#             self.app_debug_print(f" language_doc : {language_doc}",False)

#             if not language_doc:
#                 return property_value  # No translation if language not found

#             ref_language_id = language_doc['id']
#             self.app_debug_print(f" ref_language_id : {ref_language_id}",False)
#             translation_entry_query = {
#                 "filter__targeted_id": str(targeted_id),
#                 "filter__mixed_id_str": f"{str(targeted_id)}:{property_name}",
#                 "filter__ref_language_id": str(ref_language_id)
#             }
#             self.app_debug_print(f" translation_entry_query : {translation_entry_query}",False)
#             translation_entry  = await self.generic_service.fetch_one_from_collection(
#                 collection_key=CollectionKey.CFG_TRANSLATION,
#                 output_data_type=OutputDataType.DEFAULT.value,
#                 accept_language='fr',
#                 query={
#                         **translation_entry_query
#                     }
#             )
#             self.app_debug_print(f"\n\n translation_entry FOUNDED : {True if translation_entry else False}",False)
#             if translation_entry:
#                 return translation_entry['translation']
#             else:
#                 # save auto translation and save
#                 translated = await self.google_translate_text(text=property_value,target_language=short_code)
#                 self.app_debug_print(f"\n auto translated : {translated}",False)
#                 data = {
#                     "targeted_id": str(targeted_id),
#                     "ref_language_id":ref_language_id,
#                     "mixed_id_str":f"{targeted_id}:{property_name}",
#                     "translation":translated
#                 }
#                 translation_saved = await self.generic_service.add_data_to_collection(CollectionKey.CFG_TRANSLATION, data)
#                 # app_debug_print(f"\n\n translation_saved : {translation_saved}",True)
#                 return translated
#         except Exception as e:
#             self.app_debug_print(f"Error during translation fetch: {e}",False)
#             return property_value

#     async def google_translate_text(self, text: str, target_language='fr'):
#         translator = Translator()
#         if not text:
#             return text
#         try:
#             translated = await translator.translate(text=text, dest=target_language)
#             return translated.text
#         except Exception as e:
#             self.app_debug_print(f"Auto Translation error: {e} text: {text}")
#             raise ValueError(f"Auto Translation error: {e}")
