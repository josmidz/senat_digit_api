# """
# Base Document Abstract Class

# This module provides a clean abstract base class for all document models.
# It replaces the complex BaseModelMixin with a simpler, more maintainable approach.

# Features:
# - Pre-save and post-save hooks
# - Flexible formatting method with multiple output types
# - Tree data support with depth, limit, and pagination
# - Can be easily overridden in subclasses
# """

# from abc import ABC, abstractmethod
# from typing import Any, Dict, Optional, List
# from datetime import datetime, timezone
# from zoneinfo import ZoneInfo
# from pydantic import BaseModel, Field
# from beanie import Document

# from app.modules.core.enums.type_enum import EGLOBAL_DATA_TYPE, EGLOBAL_EXTRA_METAS, OutputDataType, EGlobalFormatingFlag
# from app.modules.core.utils.model.timestamp_mixin import TimestampMixin
# from app.modules.core.utils.common.async_runner import AsyncExecutor
# from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
# from app.modules.core.configs.config import settings as app_settings
# from app.modules.core.models.mapping_keys import CollectionKey
# from app.modules.core.utils.model.base_model_utils import BaseModelUtils
# from app.modules.core.services.encryption.db_encryption_service import DBEncryptionService
# from app.modules.core.services.encryption.encryption_service import CURRENT_KEY_VERSION
# from app.modules.core.services.debug.debug_service import DebugService
# from app.modules.core.models.field_translation_keys import TRANSLATIONS


# class BaseDocument(Document, BaseModel, TimestampMixin, ABC):
#     """
#     Abstract base class for all document models.

#     Provides lifecycle hooks (pre_save, post_save) and flexible formatting capabilities.
#     All models should inherit from this class instead of BaseModelMixin.
#     """

#     # ==================== Timezone Helpers ====================

#     @staticmethod
#     def utc_to_local(dt: datetime, tz_name: Optional[str] = None) -> datetime:
#         """
#         Convert a UTC datetime to local timezone.

#         Args:
#             dt: The datetime to convert (can be timezone-aware or naive)
#             tz_name: Target timezone name (e.g., 'Europe/Paris'). 
#                      Defaults to settings.DEFAULT_TIMEZONE

#         Returns:
#             datetime in the local timezone
#         """
#         if tz_name is None:
#             tz_name = app_settings.DEFAULT_TIMEZONE
        
#         local_tz = ZoneInfo(tz_name)
        
#         if dt.tzinfo is not None:
#             # If datetime is timezone-aware, convert directly
#             return dt.astimezone(local_tz)
#         else:
#             # If datetime is naive, assume it's UTC and convert
#             utc_datetime = dt.replace(tzinfo=timezone.utc)
#             return utc_datetime.astimezone(local_tz)

#     @staticmethod
#     def format_datetime_for_display(dt: datetime, tz_name: Optional[str] = None) -> str:
#         """
#         Format a datetime for display, converting from UTC to local timezone.

#         Args:
#             dt: The datetime to format (assumed to be in UTC)
#             tz_name: Target timezone name. Defaults to settings.DEFAULT_TIMEZONE

#         Returns:
#             ISO formatted string in local timezone
#         """
#         local_dt = BaseDocument.utc_to_local(dt, tz_name)
#         return local_dt.isoformat()

#     def handle_translation_status(self, status_value, enum_cls, accept_language: str = DEFAULT_LANGUAGE) -> str:
#         """
#         Returns a localized label for a given enum status using the TRANSLATIONS map.

#         Args:
#             status_value: The enum value to translate. May be an Enum member, its value, or name.
#             enum_cls: The Enum class (e.g., EGlobalStatus).
#             accept_language: Target language code (defaults to DEFAULT_LANGUAGE).

#         Fallbacks:
#             - If language not found, fallback to DEFAULT_LANGUAGE.
#             - If translation missing, return the enum name (or str(value)).
#         """
#         try:
#             # Normalize language
#             lang = (accept_language or DEFAULT_LANGUAGE).lower()
#             if lang not in TRANSLATIONS:
#                 lang = DEFAULT_LANGUAGE

#             # Normalize to an enum member
#             enum_member = None
#             if isinstance(status_value, enum_cls):
#                 enum_member = status_value
#             else:
#                 # Try value-based construction
#                 try:
#                     enum_member = enum_cls(status_value)
#                 except Exception:
#                     # Try by name if a string was provided
#                     if isinstance(status_value, str):
#                         try:
#                             enum_member = enum_cls[status_value]
#                         except Exception:
#                             enum_member = None

#             # Build fallback label from what we have
#             fallback_label = (
#                 enum_member.name.replace("_", " ").title() if getattr(enum_member, "name", None)
#                 else str(getattr(status_value, "name", status_value)).replace("_", " ").title()
#             )

#             # Resolve translation mapping
#             lang_map = TRANSLATIONS.get(lang, {})
#             enum_map = lang_map.get(enum_cls, {})

#             if enum_member is not None and enum_member in enum_map:
#                 return enum_map[enum_member]

#             # No exact match; attempt lenient lookup by name/value
#             if enum_map and status_value is not None:
#                 target_key = str(getattr(status_value, "name", status_value)).upper()
#                 for k, v in enum_map.items():
#                     try:
#                         key_name = getattr(k, "name", str(k)).upper()
#                         key_value = str(getattr(k, "value", k)).upper()
#                     except Exception:
#                         key_name = str(k).upper()
#                         key_value = key_name
#                     if target_key in (key_name, key_value):
#                         return v

#             return fallback_label
#         except Exception:
#             # Last resort
#             return str(status_value)


#     # ==================== Lifecycle Hooks ====================

#     async def pre_save(self, **kwargs) -> None:
#         """
#         Hook called before saving the document.

#         Override this method in subclasses to add custom logic before save.
#         Examples: validation, field transformation, encryption, etc.

#         Handles automatic translation:
#         - If accept_language is provided and != "fr" (default language)
#         - Checks all fields with may_have_translation=True
#         - Saves the French value in the field
#         - Stores other language translations in the translations dict

#         Handles automatic encryption:
#         - Checks all fields with can_be_encrypted=True
#         - Encrypts field values using DBEncryptionService
#         - Handles version tracking and re-encryption

#         Args:
#             **kwargs: Additional context data that might be needed
#                 accept_language: Language code for the input data (default: "fr")
#         """
#         # Update timestamp
#         self.updated_at = datetime.now(timezone.utc)

#         # If this is a new document, set created_at
#         if not hasattr(self, 'id') or self.id is None:
#             self.created_at = datetime.now(timezone.utc)

#         # Handle translations
#         accept_language = kwargs.get('accept_language', DEFAULT_LANGUAGE)

#         # Initialize translations dict if not exists
#         if not hasattr(self, 'translations') or self.translations is None:
#             self.translations = {}

#         # Get all fields from the model class
#         for field_name, field_info in self.__class__.model_fields.items():
#             # Check if field has translation metadata
#             json_schema_extra = field_info.json_schema_extra

#             if json_schema_extra and isinstance(json_schema_extra, dict):
#                 may_have_translation = json_schema_extra.get('may_have_translation', False)

#                 # If field can be translated and has a value
#                 if may_have_translation and hasattr(self, field_name):
#                     field_value = getattr(self, field_name)

#                     # Only process non-empty string values
#                     if field_value and isinstance(field_value, str):
#                         # Initialize translations for this field if not exists
#                         if field_name not in self.translations:
#                             self.translations[field_name] = {}

#                         # Check if this is a default value (from field definition)
#                         field_default = field_info.default if hasattr(field_info, 'default') else None
#                         is_default_value = (field_default is not None and field_value == field_default)

#                         if accept_language != DEFAULT_LANGUAGE:
#                             # User is providing data in non-French language

#                             if is_default_value:
#                                 # This is a default French value, translate it to accept_language
#                                 translated_value = await BaseModelUtils.google_translate_text(
#                                     text=field_value,
#                                     target_language=accept_language
#                                 )
#                                 # Store French default in translations
#                                 self.translations[field_name][DEFAULT_LANGUAGE] = field_value
#                                 # Store translated value in translations
#                                 self.translations[field_name][accept_language] = translated_value
#                                 # Keep French as the primary field value
#                                 # (field_value is already French, no need to change)
#                             else:
#                                 # User provided a custom value in accept_language
#                                 # Store the current value as a translation for accept_language
#                                 self.translations[field_name][accept_language] = field_value

#                                 # Check if we already have a French translation
#                                 if DEFAULT_LANGUAGE in self.translations.get(field_name, {}):
#                                     # Use existing French translation as the field value
#                                     setattr(self, field_name, self.translations[field_name][DEFAULT_LANGUAGE])
#                                 else:
#                                     # Translate to French using Google Translate
#                                     french_value = await BaseModelUtils.google_translate_text(
#                                         text=field_value,
#                                         target_language=DEFAULT_LANGUAGE
#                                     )
#                                     # Store French as the primary field value
#                                     setattr(self, field_name, french_value)
#                                     # Store it in translations as well
#                                     self.translations[field_name][DEFAULT_LANGUAGE] = french_value

#                         elif accept_language == DEFAULT_LANGUAGE:
#                             # User is providing data in French (or using defaults)
#                             # Store French value in translations for consistency
#                             self.translations[field_name][DEFAULT_LANGUAGE] = field_value

#         # Handle encryption
#         await self._encrypt_sensitive_fields()

#     async def _encrypt_sensitive_fields(self) -> None:
#         """
#         Encrypt fields that have can_be_encrypted=True in their metadata.

#         This method handles:
#         - Encrypting unencrypted values
#         - Re-encrypting values with old key versions
#         - Fixing malformed encrypted values
#         - Encrypting translation values for encrypted fields
#         """
#         db_encryption = DBEncryptionService()

#         # Iterate through all fields to find those that can be encrypted
#         for field_name, field_info in self.__class__.model_fields.items():
#             meta = field_info.json_schema_extra or {}
#             can_be_encrypted = meta.get("can_be_encrypted", False)

#             if can_be_encrypted:
#                 # Encrypt the primary field value
#                 field_value = getattr(self, field_name, None)
#                 if field_value is not None:
#                     # Convert to string if it's a number
#                     if isinstance(field_value, (int, float)):
#                         field_value = str(field_value)

#                     if isinstance(field_value, str):
#                         # Handle different encryption formats
#                         if not field_value.lower().startswith(db_encryption.VERSION_PREFIX):
#                             # Not encrypted yet - encrypt it
#                             try:
#                                 # db_encryption.encrypt() already returns value with "db_enc:v1:" prefix
#                                 encrypted_value = db_encryption.encrypt(field_value)
#                                 setattr(self, field_name, encrypted_value)
#                                 DebugService.app_debug_print(f"Encrypted field {field_name}", False)
#                             except Exception as e:
#                                 DebugService.app_debug_print(f"Error encrypting field {field_name}: {e}", True)

#                         # Handle double-versioned encrypted value (db_enc:db_enc:v1: or db_enc:v1:v1:)
#                         elif field_value.lower().startswith(f"{db_encryption.VERSION_PREFIX}{db_encryption.VERSION_PREFIX}") or \
#                              field_value.lower().startswith(f"{db_encryption.VERSION_PREFIX}v1:v1:"):
#                             try:
#                                 # Remove the double prefix
#                                 if field_value.lower().startswith(f"{db_encryption.VERSION_PREFIX}{db_encryption.VERSION_PREFIX}"):
#                                     # db_enc:db_enc:v1:... -> keep from second db_enc onwards
#                                     actual_encrypted_text = field_value[len(db_encryption.VERSION_PREFIX):]
#                                 else:
#                                     # db_enc:v1:v1:... -> remove "db_enc:v1:v1:" prefix
#                                     actual_encrypted_text = field_value[10:]

#                                 DebugService.app_debug_print(f"Fixing double-versioned field {field_name}", False)

#                                 try:
#                                     decrypted_value = db_encryption.decrypt(actual_encrypted_text)

#                                     if decrypted_value != actual_encrypted_text:
#                                         # Re-encrypt properly (encrypt() already adds prefix)
#                                         new_encrypted_value = db_encryption.encrypt(decrypted_value)
#                                         setattr(self, field_name, new_encrypted_value)
#                                         DebugService.app_debug_print(f"Re-encrypted double-versioned field {field_name}", False)
#                                     else:
#                                         setattr(self, field_name, f"{db_encryption.VERSION_PREFIX}{CURRENT_KEY_VERSION}:{actual_encrypted_text}")
#                                         DebugService.app_debug_print(f"Fixed format of double-versioned field {field_name}", False)
#                                 except Exception as e:
#                                     DebugService.app_debug_print(f"Error decrypting double-versioned field {field_name}: {e}", True)
#                                     setattr(self, field_name, f"{db_encryption.VERSION_PREFIX}{CURRENT_KEY_VERSION}:{actual_encrypted_text}")
#                             except Exception as e:
#                                 DebugService.app_debug_print(f"Error fixing double-versioned field {field_name}: {e}", True)

#                         # Handle old-style encrypted value without version (enc:gAAAAA...)
#                         elif ":" not in field_value[7:]:
#                             try:
#                                 old_encrypted_value = field_value[7:]  # Remove "enc:" or "ENC:" prefix
#                                 DebugService.app_debug_print(f"Adding version to old-style encrypted field {field_name}", False)

#                                 try:
#                                     decrypted_value = db_encryption.decrypt(old_encrypted_value)

#                                     if decrypted_value != old_encrypted_value:
#                                         # Re-encrypt properly (encrypt() already adds prefix)
#                                         new_encrypted_value = db_encryption.encrypt(decrypted_value)
#                                         setattr(self, field_name, new_encrypted_value)
#                                         DebugService.app_debug_print(f"Re-encrypted old-style field {field_name}", False)
#                                     else:
#                                         setattr(self, field_name, f"{db_encryption.VERSION_PREFIX}{CURRENT_KEY_VERSION}:{old_encrypted_value}")
#                                         DebugService.app_debug_print(f"Added version to old-style field {field_name}", False)
#                                 except Exception as e:
#                                     DebugService.app_debug_print(f"Error decrypting old-style field {field_name}: {e}", True)
#                                     setattr(self, field_name, f"{db_encryption.VERSION_PREFIX}{CURRENT_KEY_VERSION}:{old_encrypted_value}")
#                             except Exception as e:
#                                 DebugService.app_debug_print(f"Error processing old-style field {field_name}: {e}", True)

#                         # Handle already properly encrypted value (db_enc:v1:gAAAAA...)
#                         elif field_value.lower().startswith(db_encryption.VERSION_PREFIX + "v"):
#                             try:
#                                 parts = field_value[7:].split(":", 1)
#                                 if len(parts) == 2:
#                                     version, encrypted_text = parts

#                                     # If not using current key version, try to re-encrypt
#                                     if version != CURRENT_KEY_VERSION:
#                                         DebugService.app_debug_print(f"Field {field_name} uses old key version {version}, current is {CURRENT_KEY_VERSION}", False)

#                                         try:
#                                             decrypted_value = db_encryption.decrypt(f"{version}:{encrypted_text}")

#                                             if decrypted_value != f"{version}:{encrypted_text}":
#                                                 # Re-encrypt properly (encrypt() already adds prefix)
#                                                 new_encrypted_value = db_encryption.encrypt(decrypted_value)
#                                                 setattr(self, field_name, new_encrypted_value)
#                                                 DebugService.app_debug_print(f"Re-encrypted field {field_name} with current key version", False)
#                                         except Exception as e:
#                                             DebugService.app_debug_print(f"Error re-encrypting field {field_name} with old version: {e}", True)
#                             except Exception as e:
#                                 DebugService.app_debug_print(f"Error processing versioned field {field_name}: {e}", True)

#                 # Also encrypt translation values for this field
#                 if hasattr(self, 'translations') and self.translations and field_name in self.translations:
#                     for lang_code, translation_value in self.translations[field_name].items():
#                         if translation_value and isinstance(translation_value, str):
#                             # Only encrypt if not already encrypted
#                             if not translation_value.lower().startswith(db_encryption.VERSION_PREFIX):
#                                 try:
#                                     encrypted_translation = db_encryption.encrypt(translation_value)
#                                     self.translations[field_name][lang_code] = encrypted_translation
#                                     DebugService.app_debug_print(f"Encrypted translation {field_name}[{lang_code}]", False)
#                                 except Exception as e:
#                                     DebugService.app_debug_print(f"Error encrypting translation {field_name}[{lang_code}]: {e}", True)

#     async def post_save(self, **kwargs) -> None:
#         """
#         Hook called after saving the document.

#         Override this method in subclasses to add custom logic after save.
#         Examples: logging, notifications, cache updates, etc.

#         Args:
#             **kwargs: Additional context data that might be needed
#         """
#         pass

#     # ==================== Formatting Methods ====================
#     # ==================== Decryption Helpers ====================

#     def _decrypt_output_payload(self, payload: Any, accept_language: str = DEFAULT_LANGUAGE) -> Any:
#         """Decrypt fields marked as ``can_be_encrypted`` on this model.

#         Instead of blindly decrypting every string that *looks* encrypted, we
#         introspect the model's field metadata and only decrypt:

#         * Fields whose ``json_schema_extra`` has ``can_be_encrypted=True``
#         * Their corresponding entries inside the ``translations`` map
#         * Common derived values such as ``display_value`` that simply mirror
#           an encrypted field (e.g. for input selects)

#         The function is still safe to call multiple times because
#         :meth:`DBEncryptionService.is_encrypted` ensures plain text is left
#         untouched.
#         """
#         db_encryption = DBEncryptionService()

#         # Discover which fields are declared as encryptable on this model.
#         encrypted_fields = set()
#         try:
#             for field_name, field_info in self.__class__.model_fields.items():  # type: ignore[attr-defined]
#                 meta = field_info.json_schema_extra or {}
#                 if isinstance(meta, dict) and meta.get("can_be_encrypted", False):
#                     encrypted_fields.add(field_name)
#         except Exception as e:
#             DebugService.app_debug_print(
#                 f"Error introspecting encrypted fields metadata: {e}", True
#             )

#         def _decrypt_str(value: Any) -> tuple[Any, bool]:
#             """Decrypt a single string value if it is encrypted.

#             Returns a tuple of (result_value, decrypted_flag).
#             """
#             if isinstance(value, str) and db_encryption.is_encrypted(value):
#                 try:
#                     return db_encryption.decrypt(value), True
#                 except Exception as e:
#                     DebugService.app_debug_print(
#                         f"Error decrypting output value: {e}", True
#                     )
#                     # Return the original value but mark that decryption failed
#                     return value, False
#             return value, False

#         def _walk(value: Any) -> Any:
#             # Handle bare strings so standalone payloads are also decrypted
#             if isinstance(value, str):
#                 decrypted, _ = _decrypt_str(value)
#                 return decrypted

#             # Lists / tuples: walk each element
#             if isinstance(value, list):
#                 return [_walk(v) for v in value]

#             # Non-mapping, non-collection values are returned as-is
#             if not isinstance(value, dict):
#                 return value

#             # Work on a shallow copy so callers' data isn't mutated in-place
#             result: Dict[str, Any] = dict(value)

#             # Cache translations dict if present
#             translations = result.get("translations")
#             if not isinstance(translations, dict):
#                 translations = None

#             # 1) Decrypt primary fields declared as encryptable
#             for field_name in encrypted_fields:
#                 if field_name in result:
#                     original_value = result[field_name]
#                     decrypted_value, ok = _decrypt_str(original_value)

#                     # If still encrypted after a decrypt attempt, try to fall back
#                     # to the translated value (either requested language or
#                     # default language) so callers never see raw tokens.
#                     if (
#                         isinstance(decrypted_value, str)
#                         and db_encryption.is_encrypted(decrypted_value)
#                         and translations is not None
#                     ):
#                         field_translations = translations.get(field_name)
#                         if isinstance(field_translations, dict):
#                             fallback = (
#                                 field_translations.get(accept_language)
#                                 or field_translations.get(DEFAULT_LANGUAGE)
#                             )
#                             if fallback is None and field_translations:
#                                 # Take any available translation as last resort
#                                 fallback = next(iter(field_translations.values()))
#                             if fallback is not None:
#                                 decrypted_value = fallback

#                     result[field_name] = decrypted_value

#             # 2) Decrypt translations for those fields
#             if translations is not None:
#                 for field_name in encrypted_fields:
#                     field_translations = translations.get(field_name)
#                     if isinstance(field_translations, dict):
#                         for lang_code, lang_value in list(field_translations.items()):
#                             decrypted_lang, _ = _decrypt_str(lang_value)
#                             field_translations[lang_code] = decrypted_lang

#             # 3) Common derived values (e.g. input-select display)
#             if "display_value" in result:
#                 display_val = result["display_value"]
#                 decrypted_display, ok = _decrypt_str(display_val)

#                 if (
#                     isinstance(decrypted_display, str)
#                     and db_encryption.is_encrypted(decrypted_display)
#                     and translations is not None
#                 ):
#                     # Try to derive display_value from translations of any
#                     # encryptable field (typically "name").
#                     for field_name in encrypted_fields:
#                         field_translations = translations.get(field_name)
#                         if isinstance(field_translations, dict):
#                             fallback = (
#                                 field_translations.get(accept_language)
#                                 or field_translations.get(DEFAULT_LANGUAGE)
#                             )
#                             if fallback is None and field_translations:
#                                 fallback = next(iter(field_translations.values()))
#                             if fallback is not None:
#                                 decrypted_display = fallback
#                                 break

#                 result["display_value"] = decrypted_display

#             # 4) Recurse into nested structures (children, unwind parts, etc.)
#             for key, child in list(result.items()):
#                 # Skip fields we've already handled explicitly above
#                 if key in encrypted_fields:
#                     continue

#                 if key == "translations":
#                     # We already decrypted the relevant entries for
#                     # encryptable fields, but there may still be nested
#                     # structures under other keys.
#                     result[key] = _walk(child)
#                     continue

#                 if isinstance(child, (dict, list)):
#                     result[key] = _walk(child)
#                 else:
#                     # Fallback: decrypt any remaining encrypted strings that
#                     # weren't covered by explicit metadata (helps if field
#                     # metas drift).
#                     decrypted_child, _ = _decrypt_str(child)
#                     result[key] = decrypted_child

#             return result

#         return _walk(payload)

#     # ==================== Formatting Methods ====================


#     async def _format_unwind_document(
#         self,
#         output_enum: OutputDataType,
#         accept_language: str,
#         collection_key: Optional[CollectionKey],
#         doc: Dict[str, Any],
#         force_include_fields: Optional[List[str]],
#         force_exclude_fields: Optional[List[str]],
#         hidde_on_view_values: Optional[Dict[str, Any]],
#         sort: Optional[Dict[str, int]],
#         formatting_flag: EGlobalFormatingFlag,
#     ) -> Any:
#         """Handle documents coming from native aggregate pipelines with
#         ``unwind__`` keys.

#         For new-style models based on ``BaseDocument`` this mirrors the behaviour
#         implemented for ``BaseModelMixin`` while delegating all formatting to the
#         unified ``format()`` API (both for the base document and any nested
#         documents).
#         """
#         from bson import ObjectId
        
#         # Split base fields and nested unwind parts
#         base_doc: Dict[str, Any] = {}
#         unwind_parts: Dict[str, Any] = {}

#         for key, value in doc.items():
#             if isinstance(key, str) and key.startswith("unwind__"):
#                 unwind_parts[key[len("unwind__") :]] = value
#             else:
#                 base_doc[key] = value

#         # Format the base document using the regular format() pipeline
#         base_formatted = await self.format(
#             output_data_type=output_enum,
#             formatting_flag=formatting_flag,
#             accept_language=accept_language,
#             collection_key=collection_key,
#             doc=base_doc,
#             force_include_fields=force_include_fields,
#             force_exclude_fields=force_exclude_fields,
#             hidde_on_view_values=hidde_on_view_values,
#             sort=sort,
#         )

#         # Import here to avoid circular dependencies at import time
#         try:
#             from app.modules.core.services.model.model_service import ModelService  # type: ignore
#         except Exception:
#             ModelService = None  # type: ignore

#         nested_formatted: Dict[str, Any] = {}

#         def _build_required_fields(model_class: type, item: Dict[str, Any]) -> Dict[str, Any]:
#             """Build required fields dict for model instantiation, similar to NativeFormatHelper."""
#             required_fields: Dict[str, Any] = {}
            
#             for field_name, field in model_class.model_fields.items():
#                 if field.is_required():
#                     # If field is in item, use that value
#                     if field_name in item:
#                         required_fields[field_name] = item.get(field_name)
#                     # Otherwise provide a default value based on field type
#                     else:
#                         # For string fields, generate a temporary value
#                         if field.annotation == str:
#                             required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
#                         # For other types, we might need different defaults
#                         elif field.annotation == int:
#                             required_fields[field_name] = 0
#                         elif field.annotation == float:
#                             required_fields[field_name] = 0.0
#                         elif field.annotation == bool:
#                             required_fields[field_name] = False
#                         elif field.annotation == list or (hasattr(field.annotation, '__origin__') and field.annotation.__origin__ == list):
#                             required_fields[field_name] = []
#                         elif field.annotation == dict or (hasattr(field.annotation, '__origin__') and field.annotation.__origin__ == dict):
#                             required_fields[field_name] = {}
            
#             # Always include ID field if available
#             if "_id" in item:
#                 required_fields["id"] = str(item["_id"])
#             elif "id" in item:
#                 required_fields["id"] = str(item["id"]) if not isinstance(item["id"], str) else item["id"]
#             else:
#                 required_fields["id"] = str(ObjectId())
            
#             return required_fields

#         async def _format_nested(model_name: str, value: Any) -> Any:
#             if ModelService is None:
#                 return value

#             try:
#                 nested_collection_key = ModelService.get_collection_key_from_model_name(
#                     model_name
#                 )
#                 nested_model_class = ModelService.get_model_class_from_collection_key(
#                     nested_collection_key
#                 )
#             except Exception:
#                 # If model not recognized, return value as-is
#                 return value

#             async def _format_single_item(item: Dict[str, Any]) -> Any:
#                 try:
#                     # Build required fields like NativeFormatHelper does
#                     required_fields = _build_required_fields(nested_model_class, item)
#                     nested_instance = nested_model_class(**required_fields)
#                 except Exception as e:
#                     DebugService.app_debug_print(f"Error instantiating nested model {model_name}: {e}", False)
#                     # Fallback: return item with ID normalized
#                     if "_id" in item and "id" not in item:
#                         item["id"] = str(item["_id"])
#                         item.pop("_id", None)
#                     return item

#                 return await nested_instance.format(
#                     output_data_type=output_enum,
#                     formatting_flag=formatting_flag,
#                     accept_language=accept_language,
#                     collection_key=nested_collection_key,
#                     doc=item,
#                     force_include_fields=force_include_fields,
#                     force_exclude_fields=force_exclude_fields,
#                     hidde_on_view_values=hidde_on_view_values,
#                     sort=sort,
#                 )

#             if isinstance(value, dict):
#                 return await _format_single_item(value)
#             if isinstance(value, list):
#                 # Use AsyncExecutor.gather for parallel formatting of list items
#                 dict_items = [(i, elem) for i, elem in enumerate(value) if isinstance(elem, dict)]
#                 non_dict_items = [(i, elem) for i, elem in enumerate(value) if not isinstance(elem, dict)]
                
#                 if dict_items:
#                     dict_tasks = [_format_single_item(elem) for _, elem in dict_items]
#                     formatted_dicts = await AsyncExecutor.gather(dict_tasks)
                    
#                     # Reconstruct list in original order
#                     formatted_list: List[Any] = [None] * len(value)
#                     for (i, _), formatted in zip(dict_items, formatted_dicts):
#                         formatted_list[i] = formatted
#                     for i, elem in non_dict_items:
#                         formatted_list[i] = elem
#                     return formatted_list
#                 else:
#                     return value
#             return value

#         # Use AsyncExecutor.gather for parallel nested formatting
#         nested_keys = list(unwind_parts.keys())
#         nested_values = list(unwind_parts.values())
        
#         if nested_keys:
#             nested_tasks = [_format_nested(model_name=key, value=val) for key, val in zip(nested_keys, nested_values)]
#             nested_results = await AsyncExecutor.gather(nested_tasks)
#             for key, result in zip(nested_keys, nested_results):
#                 nested_formatted[key] = result

#         # Merge base and nested parts
#         combined: Dict[str, Any] = {}
#         if isinstance(base_formatted, dict):
#             combined.update(base_formatted)
#         else:
#             combined["base"] = base_formatted

#         combined.update(nested_formatted)

#         # Hide sensitive fields for non-default representations
#         if output_enum != OutputDataType.DEFAULT:
#             for field in ["password", "user_account_hash", "user_account_socket_hash"]:
#                 combined.pop(field, None)

#         return combined

#     async def format(
#         self,
#         output_data_type: OutputDataType = OutputDataType.DEFAULT,
#         formatting_flag: EGlobalFormatingFlag = EGlobalFormatingFlag.DEFAULT,
#         accept_language: str = DEFAULT_LANGUAGE,
#         depth: Optional[int] = None,
#         limit: Optional[int] = None,
#         page: Optional[int] = None,
#         **kwargs,
#     ) -> Any:
#         """Format the document for output.

#         For ``BaseDocument`` this method is the single entry point used by all
#         higher-level helpers. It routes to specialised helpers (tree,
#         data-table, etc.) and also knows how to consume native aggregate
#         documents with ``unwind__`` keys.
#         """
#         # print('\n\n\n\n format output_data_type : ', output_data_type, '\n\n\n')
#         # Normalise to enum
#         output_enum = (
#             output_data_type
#             if isinstance(output_data_type, OutputDataType)
#             else OutputDataType(output_data_type)
#         )
#         # print('\n\n\n\n format output_enum : ', output_enum, '\n\n\n')
#         doc: Optional[Dict[str, Any]] = kwargs.get("doc")
#         collection_key: Optional[CollectionKey] = kwargs.get("collection_key")
#         force_include_fields: Optional[List[str]] = kwargs.get("force_include_fields")
#         force_exclude_fields: Optional[List[str]] = kwargs.get("force_exclude_fields")
#         hidde_on_view_values: Optional[Dict[str, Any]] = kwargs.get(
#             "hidde_on_view_values"
#         )
#         sort: Optional[Dict[str, int]] = kwargs.get("sort")

#         # Native aggregate documents with ``unwind__`` parts
#         if isinstance(doc, dict) and any(
#             isinstance(key, str) and key.startswith("unwind__") for key in doc.keys()
#         ):
#             aggregate_result = await self._format_unwind_document(
#                 output_enum=output_enum,
#                 accept_language=accept_language,
#                 collection_key=collection_key,
#                 doc=doc,
#                 force_include_fields=force_include_fields,
#                 force_exclude_fields=force_exclude_fields,
#                 hidde_on_view_values=hidde_on_view_values,
#                 sort=sort,
#                 formatting_flag=formatting_flag,
#             )
#             return self._decrypt_output_payload(aggregate_result, accept_language=accept_language)

#         # Route to dedicated helpers for structured representations
#         # print('\n\n\n\n format output_enum in DATA_TABLE: ', output_enum in (OutputDataType.DATA_TABLE,), '\n\n\n')
#         if output_enum in (OutputDataType.DATA_TABLE,):
#             result = await self.format_for_data_table(
#                 accept_language=accept_language,
#                 **kwargs,
#             )
#             return self._decrypt_output_payload(result, accept_language=accept_language)

#         if output_enum in (OutputDataType.INPUT_SELECT,):
#             result = await self.format_for_input_select(
#                 accept_language=accept_language,
#                 **kwargs,
#             )
#             return self._decrypt_output_payload(result, accept_language=accept_language)

#         if output_enum in (OutputDataType.TREE, OutputDataType.TREE_DATA_TABLE):
#             result = await self.format_for_tree(
#                 depth=depth or 1,
#                 limit=limit,
#                 page=page,
#                 accept_language=accept_language,
#                 **kwargs,
#             )
#             return self._decrypt_output_payload(result, accept_language=accept_language)

#         if output_enum in (OutputDataType.CASCADE, OutputDataType.CASCADE_ALL):
#             result = await self.format_for_cascade(
#                 accept_language=accept_language,
#                 **kwargs,
#             )
#             return self._decrypt_output_payload(result, accept_language=accept_language)

#         # Default: return a decrypted dict representation of the document
#         raw_dict = self.to_dict()
#         return self._decrypt_output_payload(raw_dict, accept_language=accept_language)

#     async def format_for_tree(
#         self,
#         depth: int = 1,
#         limit: Optional[int] = None,
#         page: Optional[int] = None,
#         accept_language: str = DEFAULT_LANGUAGE,
#         collection_key: Optional[CollectionKey] = None,
#         force_include_fields: Optional[List[str]] = None,
#         force_exclude_fields: Optional[List[str]] = None,
#         sort: Optional[Dict[str, int]] = None,
#         doc: Optional[Dict[str, Any]] = None,
#         **kwargs,
#     ) -> Dict[str, Any]:
#         """
#         Format the document for tree display.
        
#         Mirrors formatted_properties_for_tree from BaseModelMixin.
#         Only includes fields with display_value_on_tree=True in extra_metas.
#         Recursively fetches children based on parent_field relationship.

#         Args:
#             depth: Maximum depth of tree traversal (default: 1)
#             limit: Maximum number of children to fetch
#             page: Page number for paginated children
#             accept_language: Language code for translations
#             collection_key: Collection key for fetching children
#             force_include_fields: Fields to include even if not marked for tree
#             force_exclude_fields: Fields to exclude from output
#             sort: Sort order for children (default: {"created_at": -1})
#             doc: Optional document dict to format instead of self
#             **kwargs: Additional options

#         Returns:
#             Dict with id, tree display fields, and children array
#         """
#         from bson import ObjectId
        
#         # Initialize default values
#         if force_include_fields is None:
#             force_include_fields = []
#         if force_exclude_fields is None:
#             force_exclude_fields = []
#         if sort is None:
#             sort = {"created_at": -1}
        
#         db_encryption = DBEncryptionService()
        
#         # Determine the source data (provided doc or self)
#         if doc is not None:
#             source_data = doc
#             formatted_data: Dict[str, Any] = {}
            
#             # Ensure we have an ID field
#             if "_id" in doc:
#                 formatted_data["id"] = str(doc["_id"])
#             elif "id" in doc:
#                 formatted_data["id"] = str(doc["id"]) if not isinstance(doc["id"], str) else doc["id"]
#             elif hasattr(self, "id") and self.id:
#                 formatted_data["id"] = str(self.id)
#             else:
#                 formatted_data["id"] = str(ObjectId())
            
#             # Ensure translations dictionary exists
#             if "translations" not in source_data and hasattr(self, "translations"):
#                 source_data["translations"] = getattr(self, "translations", None) or {}
#         else:
#             # Build source_data from self
#             source_data = {}
#             formatted_data = {}
            
#             if hasattr(self, "id") and self.id:
#                 formatted_data["id"] = str(self.id)
#                 source_data["id"] = str(self.id)
#             else:
#                 formatted_data["id"] = str(ObjectId())
#                 source_data["id"] = formatted_data["id"]
            
#             # Extract field values from self
#             for field_name in self.model_fields.keys():
#                 if hasattr(self, field_name):
#                     value = getattr(self, field_name)
#                     if value is not None:
#                         source_data[field_name] = value
            
#             # Add translations
#             if hasattr(self, "translations"):
#                 source_data["translations"] = getattr(self, "translations", None) or {}
        
#         # If force_include_fields is provided and not empty, ensure 'id' is included
#         if force_include_fields and 'id' not in force_include_fields:
#             force_include_fields.append('id')
        
#         # Get model name for translation context and parent field
#         settings = getattr(self, 'Settings', None)
#         if settings and hasattr(settings, 'name'):
#             model_name = settings.name
#         else:
#             model_name = self.__class__.__name__.lower()
#         parent_field = f"{model_name}_id"
        
#         # Collect fields to translate in parallel
#         fields_to_translate: List[tuple] = []
#         fields_direct: Dict[str, Any] = {}
        
#         # Process fields with display_value_on_tree=True
#         for field_name, field in self.model_fields.items():
#             # Skip fields not in force_include_fields if provided
#             if force_include_fields and field_name not in force_include_fields and field_name != 'id':
#                 continue
            
#             # Skip fields in force_exclude_fields
#             if field_name in force_exclude_fields:
#                 continue
            
#             # Skip fields not in source_data
#             if field_name not in source_data:
#                 continue
            
#             meta = field.json_schema_extra or {}
#             extra_metas = meta.get("extra_metas", {})
            
#             # Only include fields marked for tree display
#             if extra_metas.get("display_value_on_tree", False):
#                 field_value = source_data.get(field_name)
                
#                 # Handle ObjectId conversion
#                 if isinstance(field_value, ObjectId):
#                     field_value = str(field_value)
                
#                 # Handle encrypted fields
#                 can_be_encrypted = meta.get("can_be_encrypted", False)
#                 if can_be_encrypted and isinstance(field_value, str) and db_encryption.is_encrypted(field_value):
#                     try:
#                         field_value = db_encryption.decrypt(field_value)
#                     except Exception:
#                         pass
                
#                 # Collect for parallel translation or direct assignment
#                 if meta.get("may_have_translation", False) and accept_language != DEFAULT_LANGUAGE:
#                     fields_to_translate.append((field_name, field_value))
#                 else:
#                     fields_direct[field_name] = field_value
        
#         # Process translations in parallel
#         if fields_to_translate:
#             translate_tasks = [
#                 BaseModelUtils.get_innter_translation(
#                     targeted_id=formatted_data["id"],
#                     property_name=fname,
#                     short_code=accept_language,
#                     property_value=fval,
#                     model_name=model_name
#                 )
#                 for fname, fval in fields_to_translate
#             ]
#             translated_values = await AsyncExecutor.gather(translate_tasks)
            
#             for (field_name, _), translated_value in zip(fields_to_translate, translated_values):
#                 formatted_data[field_name] = translated_value
        
#         # Add non-translated fields
#         formatted_data.update(fields_direct)
        
#         # Fetch children if collection_key is provided
#         if collection_key:
#             try:
#                 from app.modules.core.services.generic.generic_services import GenericService
#                 generic_service = GenericService(accept_language)
                
#                 # Fetch all children in a single query
#                 children_data = await generic_service.fetch_native_query_data_from_collection(
#                     collection_key=collection_key if isinstance(collection_key, str) else collection_key.value if hasattr(collection_key, 'value') else str(collection_key),
#                     all_data=True,
#                     output_data_type=OutputDataType.TREE,
#                     accept_language=accept_language,
#                     native_query={parent_field: ObjectId(formatted_data["id"])},
#                     sort=sort,
#                 )
                
#                 formatted_data["children"] = children_data if children_data else []
#             except RecursionError:
#                 DebugService.app_debug_print("Recursion error detected in tree formatting. Limiting depth.", False)
#                 formatted_data["children"] = []
#             except Exception as e:
#                 DebugService.app_debug_print(f"Error fetching children: {str(e)}", False)
#                 formatted_data["children"] = []
#         else:
#             formatted_data["children"] = []
        
#         return formatted_data

#     async def format_for_data_table(
#         self,
#         accept_language: str = DEFAULT_LANGUAGE,
#         **kwargs
#     ) -> Dict[str, Any]:
#         """
#         Format the document for data table display.

#         This method formats the model properties for data table output with full
#         metadata support, translations, and field processing.

#         Args:
#             accept_language: Language code for translations
#             **kwargs: Additional options including:
#                 - collection_key: The collection key for the model
#                 - force_include_fields: List of fields to include even if they are None
#                 - force_exclude_fields: List of fields to exclude from output
#                 - hidde_on_view_values: Dictionary of fields to hide from view
#                 - sort: Sort order for the data
#                 - doc: Optional document data to use instead of model instance fields

#         Returns:
#             Dict containing the formatted properties with structure:
#             {
#                 "field_name": {
#                     "display_title": str,
#                     "display_value": Any,
#                     "real_value": Any,
#                     "data_type": Dict,
#                     "meta": {
#                         "to_be_translated_in_front": bool,
#                         "may_have_translation": bool,
#                         "missing_translation": bool,
#                         ...
#                     }
#                 }
#             }
#         """
#         try:
#             # Extract kwargs
#             collection_key: Optional[CollectionKey] = kwargs.get("collection_key")
#             force_include_fields: Optional[List[str]] = kwargs.get("force_include_fields") or []
#             force_exclude_fields: Optional[List[str]] = kwargs.get("force_exclude_fields") or []
#             hidde_on_view_values: Optional[Dict[str, Any]] = kwargs.get("hidde_on_view_values") or {}
#             sort: Optional[Dict[str, int]] = kwargs.get("sort") or {"created_at": -1}
#             doc: Optional[Dict[str, Any]] = kwargs.get("doc")

#             # Default excluded fields
#             default_excludes = [
#                 'multiple_validation_status',
#                 'multiple_validated_at',
#                 'soft_deleted',
#                 'soft_deleted_at',
#                 'soft_deleted_by_id',
#                 'translations',
#                 'encryptions',
#                 'revision_id'
#             ]
#             force_exclude_fields.extend(default_excludes)

#             properties = {}

#             # Determine the source data (doc or self)
#             if doc is not None:
#                 # Ensure we have an ID field
#                 if "_id" in doc and "id" not in doc:
#                     doc["id"] = str(doc["_id"])
#                 elif "id" not in doc and "_id" not in doc and hasattr(self, "id"):
#                     doc["id"] = str(self.id)

#                 # Ensure translations dictionary exists
#                 if "translations" not in doc and hasattr(self, "translations"):
#                     doc["translations"] = self.translations or {}

#                 source_data = doc
#             else:
#                 source_data = self.model_dump()
#                 if hasattr(self, "id") and self.id:
#                     source_data["id"] = str(self.id)

#             # Collect fields to process (filter first, then process in parallel)
#             fields_to_process: List[tuple] = []
            
#             for field_name, field_value in source_data.items():
#                 # Skip internal fields and excluded fields
#                 if (field_name.startswith('_') or
#                     field_name in force_exclude_fields or
#                     field_name in ('translations', 'encryptions')):
#                     continue

#                 # Get field metadata if available
#                 field_meta = {}
#                 if field_name in self.__class__.model_fields:
#                     field_info = self.__class__.model_fields[field_name]
#                     field_meta = field_info.json_schema_extra or {}

#                     # Safety check for field_meta
#                     if not isinstance(field_meta, dict):
#                         field_meta = {}

#                     # Check exclude_at_all - only backend exclusion constraint
#                     extra_metas = field_meta.get("extra_metas", {})
#                     if extra_metas.get("exclude_at_all", False) and field_name not in force_include_fields:
#                         continue

#                     # Check filter_based_on_key_value condition
#                     filter_condition = extra_metas.get("filter_based_on_key_value")
#                     if filter_condition and isinstance(filter_condition, str):
#                         try:
#                             condition_parts = filter_condition.split(",", 1)
#                             if len(condition_parts) == 2:
#                                 condition_field, expected_value = condition_parts
#                                 condition_field = condition_field.strip()
#                                 expected_value = expected_value.strip()

#                                 actual_value = source_data.get(condition_field)
#                                 if hasattr(actual_value, 'value'):
#                                     actual_value_str = str(actual_value.value)
#                                 elif actual_value is not None:
#                                     actual_value_str = str(actual_value)
#                                 else:
#                                     actual_value_str = ""

#                                 if actual_value_str != expected_value:
#                                     continue
#                         except Exception:
#                             pass

#                 # Add to list for parallel processing
#                 fields_to_process.append((field_name, field_value, field_meta))

#             # Process all fields in parallel using AsyncExecutor.gather
#             if fields_to_process:
#                 process_tasks = [
#                     self._process_field_for_data_table(
#                         field_name=fname,
#                         field_value=fvalue,
#                         field_meta=fmeta,
#                         accept_language=accept_language,
#                         source_data=source_data,
#                         hidde_on_view_values=hidde_on_view_values
#                     )
#                     for fname, fvalue, fmeta in fields_to_process
#                 ]
                
#                 processed_results = await AsyncExecutor.gather(process_tasks)
                
#                 for (field_name, _, _), processed_field in zip(fields_to_process, processed_results):
#                     if processed_field is not None:
#                         properties[field_name] = processed_field

#             # Sort properties
#             if properties:
#                 priority_fields = ["id", "identifier", "name"]
#                 trailing_fields = ["created_at", "updated_at", "deleted_at"]

#                 sorted_properties = {
#                     field_name: properties[field_name]
#                     for field_name in sorted(
#                         properties.keys(),
#                         key=lambda x: (
#                             0 if x in priority_fields else (2 if x in trailing_fields else 1),
#                             priority_fields.index(x) if x in priority_fields else float("inf"),
#                             x
#                         )
#                     )
#                 }

#                 # Filter properties based on exclusion rules
#                 filtered_props = {
#                     k: v
#                     for k, v in sorted_properties.items()
#                     if k not in force_exclude_fields
#                 }

#                 # Ensure all fields have proper meta structure
#                 for field_val in filtered_props.values():
#                     if isinstance(field_val, dict):
#                         field_val.setdefault('meta', {})
#                         field_val['meta'].setdefault('may_have_translation', False)

#                 return filtered_props

#             return properties

#         except Exception as e:
#             DebugService.app_debug_print(f"[ERROR] Error in format_for_data_table: {e}", True)
#             import traceback
#             DebugService.app_debug_print(f"[ERROR] Traceback: {traceback.format_exc()}", True)
#             raise e

#     async def _process_field_for_data_table(
#         self,
#         field_name: str,
#         field_value: Any,
#         field_meta: Dict[str, Any],
#         accept_language: str,
#         source_data: Dict[str, Any],
#         hidde_on_view_values: Optional[Dict[str, Any]] = None
#     ) -> Optional[Dict[str, Any]]:
#         """
#         Process a single field for data table output.

#         Args:
#             field_name: The name of the field
#             field_value: The value of the field
#             field_meta: The field's metadata (json_schema_extra)
#             accept_language: The language code for translations
#             source_data: The full source data dictionary
#             hidde_on_view_values: Dictionary of fields to hide from view

#         Returns:
#             Dict with the processed field data or None if field should be skipped
#         """
#         from app.modules.core.services.translation.translation_service import TranslationService

#         hidde_on_view_values = hidde_on_view_values or {}
#         db_encryption = DBEncryptionService()

#         # Extract metadata
#         data_type = field_meta.get("data_type", {})
#         extra_metas = field_meta.get("extra_metas", {})
#         may_have_translation = field_meta.get("may_have_translation", False)
#         to_be_translated_in_front = field_meta.get("to_be_translated_in_front", False)
#         can_be_encrypted = field_meta.get("can_be_encrypted", False)

#         # Handle encrypted fields
#         if can_be_encrypted and isinstance(field_value, str) and db_encryption.is_encrypted(field_value):
#             try:
#                 field_value = db_encryption.decrypt(field_value)
#             except Exception:
#                 pass

#         # Get display title
#         try:
#             display_title = await TranslationService.get_static_fields_translation(
#                 property_name=field_name,
#                 accept_language=accept_language
#             )
#         except Exception:
#             display_title = field_name.replace('_', ' ').title()

#         # Handle different data types
#         display_value = field_value
#         real_value = field_value

#         # Handle select - fetch display value from related collection
#         if f'{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}' in extra_metas and field_value:
#             try:
#                 from app.modules.core.services.generic.generic_services import GenericService
#                 generic_service = GenericService(accept_language)
#                 data_source = extra_metas.get(f'{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}')
#                 query = {"filter___id": str(field_value)}
                
#                 # Direct call - no semaphore here to avoid nested deadlock
#                 input_select = await generic_service.fetch_one_from_collection(
#                     collection_key=CollectionKey(data_source),
#                     output_data_type=OutputDataType.INPUT_SELECT.value,
#                     query=query,
#                     accept_language=accept_language
#                 )
#                 if input_select:
#                     display_value = input_select.get("display_value", field_value)
#                     extra_metas["data_source_value"] = input_select
#             except Exception as e:
#                 DebugService.app_debug_print(f"[DEBUG] Error fetching {EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value} for {field_name}: {e}", False)

#         # Handle cascade
#         elif f'{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}' in extra_metas and field_value:
#             try:
#                 from app.modules.core.services.generic.generic_services import GenericService
#                 generic_service = GenericService(accept_language)
#                 cascade_data_source = extra_metas.get(f'{EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value}')
#                 query = {"filter___id": str(field_value)}

#                 input_select = await generic_service.fetch_one_from_collection(
#                     collection_key=CollectionKey(cascade_data_source),
#                     output_data_type=OutputDataType.INPUT_SELECT.value,
#                     query=query,
#                     accept_language=accept_language
#                 )
#                 if input_select:
#                     display_value = input_select.get("display_value", field_value)
#                     extra_metas["data_source_value"] = input_select
#             except Exception as e:
#                 DebugService.app_debug_print(f"[DEBUG] Error fetching {EGLOBAL_EXTRA_METAS.MODEL_REFERENCE.value} for {field_name}: {e}", False)

#         # Handle is_enum with enum_data_source
#         elif data_type.get(f"{EGLOBAL_DATA_TYPE.IS_ENUM.value}", False) and 'enum_data_source' in extra_metas:
#             try:
#                 enum_class_name = extra_metas.get('enum_data_source')
#                 if enum_class_name:
#                     enum_class = TranslationService.get_enum_class_from_string(enum_class_name)
#                     enum_values = TranslationService.get_enum_translated_data_list(
#                         enum_class=enum_class,
#                         property_name_str=field_name,
#                         accept_language=accept_language
#                     )

#                     # Find the translated display value for the current enum value
#                     for enum_item in enum_values:
#                         if enum_item.get("id") == field_value:
#                             display_value = enum_item.get("display_value", field_value)
#                             break

#                     extra_metas["data_source_value"] = enum_values
#                     extra_metas["translated_display_value"] = display_value
#             except Exception as e:
#                 DebugService.app_debug_print(f"[DEBUG] Error processing enum for {field_name}: {e}", False)

#         # Handle is_amount with currency_props
#         elif data_type.get(f"{EGLOBAL_DATA_TYPE.IS_AMOUNT.value}", False) and 'currency_props' in extra_metas:
#             try:
#                 from app.modules.core.services.generic.generic_services import GenericService
#                 generic_service = GenericService(accept_language)
                
#                 currency_prop = extra_metas.get('currency_props')
#                 currency_data_source = extra_metas.get('currency_data_source')
#                 currency_id = source_data.get(currency_prop)

#                 if currency_id and currency_data_source:
#                     query = {"filter___id": str(currency_id)}
#                     # Direct call - no semaphore here to avoid nested deadlock
#                     currency_data = await generic_service.fetch_one_from_collection(
#                         collection_key=CollectionKey(currency_data_source),
#                         output_data_type=OutputDataType.INPUT_SELECT.value,
#                         query=query,
#                         accept_language=accept_language
#                     )
#                     if currency_data:
#                         extra_metas["data_source_value"] = currency_data
#             except Exception as e:
#                 DebugService.app_debug_print(f"[DEBUG] Error processing amount for {field_name}: {e}", False)

#         # Handle is_array_of_object
#         elif data_type.get(f"{EGLOBAL_DATA_TYPE.IS_ARRAY_OF_OBJECT.value}", False) and isinstance(field_value, list):
#             try:
#                 processed_items = []
#                 for item in field_value:
#                     if isinstance(item, dict):
#                         processed_item = {}
#                         for sub_key, sub_val in item.items():
#                             # Get sub-field metadata if available
#                             sub_field_meta = {}
#                             if sub_key in self.__class__.model_fields:
#                                 sub_field_info = self.__class__.model_fields[sub_key]
#                                 sub_field_meta = sub_field_info.json_schema_extra or {}

#                             # Get sub-field display title
#                             try:
#                                 sub_display_title = await TranslationService.get_static_fields_translation(
#                                     property_name=sub_key,
#                                     accept_language=accept_language
#                                 )
#                             except Exception:
#                                 sub_display_title = sub_key.replace('_', ' ').title()

#                             processed_item[sub_key] = {
#                                 "display_title": sub_display_title,
#                                 "display_value": sub_val,
#                                 "real_value": sub_val,
#                                 "data_type": sub_field_meta.get("data_type", {f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True}),
#                                 "meta": {
#                                     "to_be_translated_in_front": sub_field_meta.get("to_be_translated_in_front", False),
#                                     "may_have_translation": sub_field_meta.get("may_have_translation", False),
#                                     "missing_translation": False,
#                                     **sub_field_meta.get("extra_metas", {})
#                                 }
#                             }
#                         processed_items.append(processed_item)
#                     else:
#                         processed_items.append(item)

#                 display_value = processed_items
#                 real_value = field_value
#             except Exception as e:
#                 DebugService.app_debug_print(f"[DEBUG] Error processing array for {field_name}: {e}", False)

#         # Handle boolean
#         elif isinstance(field_value, bool):
#             data_type = {f"{EGLOBAL_DATA_TYPE.IS_BOOLEAN.value}": True}

#         # Handle ObjectId
#         elif hasattr(field_value, '__str__') and str(type(field_value).__name__) == 'ObjectId':
#             display_value = str(field_value)
#             real_value = str(field_value)

#         # Handle datetime - convert UTC to local timezone for display
#         elif isinstance(field_value, datetime):
#             # Convert to local timezone for display
#             local_tz = ZoneInfo(app_settings.DEFAULT_TIMEZONE)
#             if field_value.tzinfo is not None:
#                 # If datetime is timezone-aware (UTC), convert to local
#                 local_datetime = field_value.astimezone(local_tz)
#             else:
#                 # If datetime is naive, assume it's UTC and convert
#                 utc_datetime = field_value.replace(tzinfo=timezone.utc)
#                 local_datetime = utc_datetime.astimezone(local_tz)
            
#             display_value = local_datetime.isoformat()
#             # Keep real_value as UTC ISO string for consistency
#             real_value = field_value.isoformat() if field_value.tzinfo else field_value.replace(tzinfo=timezone.utc).isoformat()
#             data_type = data_type or {f"{EGLOBAL_DATA_TYPE.IS_DATE.value}": True}

#         # Handle translations if needed
#         missing_translation = False
#         if may_have_translation and accept_language != DEFAULT_LANGUAGE:
#             translations = source_data.get("translations", {})
#             if translations and field_name in translations:
#                 lang_translations = translations.get(field_name, {})
#                 if accept_language in lang_translations:
#                     display_value = lang_translations[accept_language]
#                 else:
#                     missing_translation = True
#             else:
#                 missing_translation = True

#         # Build the result
#         result = {
#             "display_title": display_title,
#             "display_value": display_value,
#             "real_value": real_value,
#             "data_type": data_type or {f"{EGLOBAL_DATA_TYPE.IS_STRING.value}": True},
#             "meta": {
#                 "to_be_translated_in_front": to_be_translated_in_front,
#                 "may_have_translation": may_have_translation,
#                 "missing_translation": missing_translation,
#                 **extra_metas
#             }
#         }

#         return result

#     async def format_for_input_select(
#         self,
#         accept_language: str = DEFAULT_LANGUAGE,
#         collection_key: Optional[CollectionKey] = None,
#         force_include_fields: Optional[List[str]] = None,
#         force_exclude_fields: Optional[List[str]] = None,
#         sort: Optional[Dict[str, int]] = None,
#         doc: Optional[Dict[str, Any]] = None,
#         **kwargs
#     ) -> Dict[str, Any]:
#         """
#         Format the document for input select/dropdown display.
        
#         Mirrors formatted_properties_for_input_select from BaseModelMixin.
#         Handles:
#         - Primary display value from extra_metas.display_value_on_input_select
#         - Secondary display values from extra_metas.secondary_display_value_on_input_select
#         - Filter conditions via filter_based_on_key_value
#         - Translations for translatable fields
#         - Fallback to 'name' field

#         Args:
#             accept_language: Language code for translations
#             collection_key: Optional collection key for context
#             force_include_fields: Fields to include in output
#             force_exclude_fields: Fields to exclude from output
#             sort: Sort configuration (not used in input_select but kept for API consistency)
#             doc: Optional document dict to format instead of self
#             **kwargs: Additional options

#         Returns:
#             Dict with id, property_name, display_value, and optional secondary fields
#         """
#         from bson import ObjectId
#         from app.modules.core.utils.model.base_model_utils import BaseModelUtils
#         from app.modules.core.services.debug.debug_service import DebugService
        
#         # Initialize default values
#         if force_include_fields is None:
#             force_include_fields = []
#         if force_exclude_fields is None:
#             force_exclude_fields = []
#         if sort is None:
#             sort = {"created_at": -1}
        
#         # Sensitive fields to always exclude
#         sensitive_fields = ['password', 'user_account_hash', 'user_account_socket_hash']
        
#         # Determine the source data (provided doc or self)
#         if doc is not None:
#             source_data = doc
#             # Ensure we have an ID field
#             if "_id" in doc and "id" not in doc:
#                 source_data["id"] = str(doc["_id"])
#             elif "id" not in doc and "_id" not in doc and hasattr(self, "id"):
#                 source_data["id"] = str(self.id)
            
#             # Ensure translations dictionary exists
#             if "translations" not in source_data and hasattr(self, "translations"):
#                 source_data["translations"] = getattr(self, "translations", None) or {}
#         else:
#             # Build source_data from self
#             source_data = {}
#             if hasattr(self, "id") and self.id:
#                 source_data["id"] = str(self.id)
            
#             # Extract field values from self
#             for field_name in self.model_fields.keys():
#                 if hasattr(self, field_name):
#                     value = getattr(self, field_name)
#                     if value is not None:
#                         source_data[field_name] = value
            
#             # Add translations
#             if hasattr(self, "translations"):
#                 source_data["translations"] = getattr(self, "translations", None) or {}
        
#         # Derive property_name as <model_name>_id
#         settings = getattr(self, 'Settings', None)
#         if settings and hasattr(settings, 'name'):
#             model_name = settings.name
#         else:
#             model_name = self.__class__.__name__.lower()
#         property_name = f"{model_name}_id"
        
#         # Find primary display value
#         primary_display_value = None
#         display_field_name = None
        
#         for field_name, field in self.model_fields.items():
#             if field_name == 'revision_id':
#                 continue
            
#             meta = field.json_schema_extra or {}
#             extra_metas = meta.get("extra_metas", {})
            
#             # Check filter_based_on_key_value condition
#             filter_condition = extra_metas.get("filter_based_on_key_value")
#             if filter_condition and isinstance(filter_condition, str):
#                 try:
#                     condition_parts = filter_condition.split(",", 1)
#                     if len(condition_parts) == 2:
#                         condition_field, expected_value = condition_parts
#                         condition_field = condition_field.strip()
#                         expected_value = expected_value.strip()
                        
#                         # Validate that the condition field exists in the model
#                         if condition_field not in self.model_fields:
#                             continue
                        
#                         # Get the actual value of the condition field from source_data
#                         actual_value = source_data.get(condition_field)
                        
#                         # Handle enum values
#                         if hasattr(actual_value, 'value'):
#                             actual_value_str = str(actual_value.value)
#                         elif actual_value is not None:
#                             actual_value_str = str(actual_value)
#                         else:
#                             actual_value_str = None
                        
#                         # Skip field if condition doesn't match
#                         if actual_value_str != expected_value:
#                             continue
#                 except Exception as e:
#                     DebugService.app_debug_print(
#                         f"[ERROR] Error processing filter condition for field {field_name}: {e}", 
#                         True
#                     )
            
#             # Check for primary display field
#             if meta.get("no_uuid_field_priority", -1) == 0:
#             # if extra_metas.get("display_value_on_input_select", False):
#                 display_field_name = field_name
#                 can_be_translated = meta.get("may_have_translation", False)
                
#                 if display_field_name in source_data:
#                     value = source_data[display_field_name]
                    
#                     # Convert ObjectId to string
#                     if isinstance(value, ObjectId):
#                         value = str(value)
#                     elif field_name.endswith("_id") and isinstance(value, str) and ObjectId.is_valid(value):
#                         value = str(value)
                    
#                     # Handle translation
#                     if can_be_translated and accept_language != DEFAULT_LANGUAGE:
#                         primary_display_value = await BaseModelUtils.get_innter_translation(
#                             targeted_id=source_data.get("id"),
#                             property_name=field_name,
#                             short_code=accept_language,
#                             property_value=value,
#                             model_name=model_name
#                         )
#                     else:
#                         primary_display_value = value
#                 break
        
#         # Fallback to 'name' field if no primary display value found
#         if primary_display_value is None:
#             fallback_field = "name"
#             if fallback_field in source_data:
#                 fallback_value = source_data[fallback_field]
                
#                 # Convert ObjectId to string
#                 if isinstance(fallback_value, ObjectId):
#                     fallback_value = str(fallback_value)
                
#                 # Check if fallback field is translatable
#                 field = self.model_fields.get(fallback_field)
#                 if field:
#                     meta = field.json_schema_extra or {}
#                     can_be_translated = meta.get("may_have_translation", False)
                    
#                     if can_be_translated and accept_language != DEFAULT_LANGUAGE:
#                         primary_display_value = await BaseModelUtils.get_innter_translation(
#                             targeted_id=source_data.get("id"),
#                             property_name=fallback_field,
#                             short_code=accept_language,
#                             property_value=fallback_value,
#                             model_name=model_name
#                         )
#                     else:
#                         primary_display_value = fallback_value
#                 else:
#                     primary_display_value = fallback_value
        
#         # Build base properties
#         properties: Dict[str, Any] = {
#             "id": source_data.get("id"),
#             "property_name": property_name,
#             "display_value": primary_display_value,
#         }
        
#         # Collect secondary display fields for parallel processing
#         secondary_fields_to_translate: List[tuple] = []
#         secondary_fields_direct: Dict[str, Any] = {}
        
#         for field_name, field in self.model_fields.items():
#             # Skip if not in force_include_fields (when specified)
#             if force_include_fields and field_name not in force_include_fields:
#                 continue
            
#             # Skip if in force_exclude_fields
#             if field_name in force_exclude_fields:
#                 continue
            
#             # Skip if not in source_data
#             if field_name not in source_data:
#                 continue
            
#             meta = field.json_schema_extra or {}
#             extra_metas = meta.get("extra_metas", {})
            
#             # Check for secondary display field
#             if meta.get("no_uuid_field_priority", -1) > 0:
#             # if extra_metas.get("secondary_display_value_on_input_select", False):
#                 can_be_translated = meta.get("may_have_translation", False)
#                 value = source_data[field_name]
                
#                 # Convert ObjectId to string
#                 if isinstance(value, ObjectId):
#                     value = str(value)
#                 elif field_name.endswith("_id") and isinstance(value, str) and ObjectId.is_valid(value):
#                     value = str(value)
                
#                 # Collect for parallel translation or direct assignment
#                 if can_be_translated and accept_language != DEFAULT_LANGUAGE:
#                     secondary_fields_to_translate.append((field_name, value))
#                 else:
#                     secondary_fields_direct[field_name] = value
        
#         # Process translations in parallel
#         if secondary_fields_to_translate:
#             translate_tasks = [
#                 BaseModelUtils.get_innter_translation(
#                     targeted_id=source_data.get("id"),
#                     property_name=fname,
#                     short_code=accept_language,
#                     property_value=val,
#                     model_name=model_name
#                 )
#                 for fname, val in secondary_fields_to_translate
#             ]
#             translated_values = await AsyncExecutor.gather(translate_tasks)
            
#             for (field_name, _), translated_value in zip(secondary_fields_to_translate, translated_values):
#                 properties[field_name] = translated_value
        
#         # Add non-translated secondary fields
#         properties.update(secondary_fields_direct)
        
#         # Remove sensitive fields
#         for field in sensitive_fields:
#             properties.pop(field, None)
        
#         return properties

#     async def format_for_cascade(
#         self,
#         accept_language: str = DEFAULT_LANGUAGE,
#         collection_key: Optional[CollectionKey] = None,
#         force_include_fields: Optional[List[str]] = None,
#         force_exclude_fields: Optional[List[str]] = None,
#         sort: Optional[Dict[str, int]] = None,
#         doc: Optional[Dict[str, Any]] = None,
#         **kwargs
#     ) -> Dict[str, Any]:
#         """
#         Format the document for cascade select display.
        
#         Mirrors formatted_properties_for_cascade from BaseModelMixin.
#         Recursively fetches children based on parent_field relationship.

#         Args:
#             accept_language: Language code for translations
#             collection_key: Collection key for fetching children
#             force_include_fields: Fields to include in output
#             force_exclude_fields: Fields to exclude from output
#             sort: Sort order for children (default: {"created_at": -1})
#             doc: Optional document dict to format instead of self
#             **kwargs: Additional options

#         Returns:
#             Dict with cascade structure: {id, property_name, is_leaf, children, display_value}
#         """
#         from bson import ObjectId
#         from pydantic import ValidationError
        
#         # Initialize default values
#         if force_include_fields is None:
#             force_include_fields = []
#         if force_exclude_fields is None:
#             force_exclude_fields = []
#         if sort is None:
#             sort = {"created_at": -1}
        
#         db_encryption = DBEncryptionService()
        
#         # Determine the source data (provided doc or self)
#         if doc is not None:
#             source_data = doc
#             # Ensure we have an ID field
#             if "_id" in doc and "id" not in doc:
#                 source_data["id"] = str(doc["_id"])
#             elif "id" not in doc and "_id" not in doc and hasattr(self, "id"):
#                 source_data["id"] = str(self.id)
            
#             # Ensure translations dictionary exists
#             if "translations" not in source_data and hasattr(self, "translations"):
#                 source_data["translations"] = getattr(self, "translations", None) or {}
#         else:
#             # Build source_data from self
#             source_data = {}
#             if hasattr(self, "id") and self.id:
#                 source_data["id"] = str(self.id)
            
#             # Extract field values from self
#             for field_name in self.model_fields.keys():
#                 if hasattr(self, field_name):
#                     value = getattr(self, field_name)
#                     if value is not None:
#                         source_data[field_name] = value
            
#             # Add translations
#             if hasattr(self, "translations"):
#                 source_data["translations"] = getattr(self, "translations", None) or {}
        
#         # Get model name for context
#         settings = getattr(self, 'Settings', None)
#         if settings and hasattr(settings, 'name'):
#             model_name = settings.name
#         else:
#             model_name = self.__class__.__name__.lower()
#         property_name = f"{model_name}_id"
#         parent_field = f"{model_name}_id"
        
#         # Determine which field to use for display value on cascade
#         display_value_field = "name"  # default fallback
#         can_be_translated = False
        
#         for field_name, field in self.model_fields.items():
#             if field_name == 'revision_id':
#                 continue
            
#             meta = field.json_schema_extra or {}
#             extra_metas = meta.get("extra_metas", {})
            
#             # Check filter_based_on_key_value condition
#             filter_condition = extra_metas.get("filter_based_on_key_value")
#             if filter_condition and isinstance(filter_condition, str):
#                 try:
#                     condition_parts = filter_condition.split(",", 1)
#                     if len(condition_parts) == 2:
#                         condition_field, expected_value = condition_parts
#                         condition_field = condition_field.strip()
#                         expected_value = expected_value.strip()
                        
#                         if condition_field not in self.model_fields:
#                             continue
                        
#                         actual_value = source_data.get(condition_field)
#                         if hasattr(actual_value, 'value'):
#                             actual_value_str = str(actual_value.value)
#                         elif actual_value is not None:
#                             actual_value_str = str(actual_value)
#                         else:
#                             actual_value_str = None
                        
#                         if actual_value_str != expected_value:
#                             continue
#                 except Exception:
#                     pass
            
#             # Check for display_value_on_cascade
#             if meta.get("no_uuid_field_priority", -1) == 0:
#                 display_value_field = field_name
#                 can_be_translated = meta.get("may_have_translation", False)
#                 break
        
#         # Get the display value
#         display_value = source_data.get(display_value_field)
        
#         # Handle encrypted display value
#         if display_value is not None and display_value_field in self.model_fields:
#             field_meta = self.model_fields[display_value_field].json_schema_extra or {}
#             can_be_encrypted = field_meta.get("can_be_encrypted", False)
#             if can_be_encrypted and isinstance(display_value, str) and db_encryption.is_encrypted(display_value):
#                 try:
#                     display_value = db_encryption.decrypt(display_value)
#                 except Exception:
#                     pass
        
#         # Convert ObjectId to string
#         if isinstance(display_value, ObjectId):
#             display_value = str(display_value)
        
#         # Fetch children if collection_key is provided
#         cascade_children: List[Dict[str, Any]] = []
        
#         if collection_key:
#             try:
#                 from app.modules.core.services.generic.generic_services import GenericService
#                 generic_service = GenericService(accept_language)
                
#                 # Query for children using parent field
#                 query_params = {f"filter__{parent_field}": source_data.get("id")}
                
#                 children_data = await generic_service.fetch_data_from_collection(
#                     collection_key=collection_key if isinstance(collection_key, str) else collection_key.value if hasattr(collection_key, 'value') else str(collection_key),
#                     all_data=True,
#                     output_data_type=OutputDataType.DEFAULT.value,
#                     accept_language=accept_language,
#                     query=query_params,
#                     sort=sort
#                 )
                
#                 # Clean and process children data
#                 valid_fields = set(self.__class__.model_fields.keys())
#                 cleaned_children_data = []
                
#                 for child in children_data:
#                     cleaned_child = {}
#                     if "translations" not in child:
#                         child["translations"] = {}
                    
#                     for k, v in child.items():
#                         if k not in valid_fields or k in force_exclude_fields:
#                             continue
                        
#                         # Handle encrypted fields
#                         if k in self.model_fields:
#                             field_meta = self.model_fields[k].json_schema_extra or {}
#                             can_be_encrypted = field_meta.get("can_be_encrypted", False)
#                             if can_be_encrypted and isinstance(v, str) and db_encryption.is_encrypted(v):
#                                 try:
#                                     v = db_encryption.decrypt(v)
#                                 except Exception:
#                                     pass
                        
#                         # Handle display values in dicts
#                         if isinstance(v, dict) and "display_value" in v:
#                             cleaned_child[k] = v["display_value"]
#                         else:
#                             cleaned_child[k] = v
                    
#                     cleaned_children_data.append(cleaned_child)
                
#                 # Instantiate children and recursively get cascade properties
#                 for child_data in cleaned_children_data:
#                     try:
#                         # Build required fields for model instantiation
#                         required_fields = self._build_required_fields_for_cascade(child_data)
#                         child_instance = self.__class__(**required_fields)
                        
#                         cascade_child = await child_instance.format_for_cascade(
#                             accept_language=accept_language,
#                             collection_key=collection_key,
#                             force_include_fields=force_include_fields,
#                             force_exclude_fields=force_exclude_fields,
#                             sort=sort,
#                             doc=child_data
#                         )
#                         cascade_children.append(cascade_child)
#                     except (ValidationError, Exception) as e:
#                         DebugService.app_debug_print(f"Error processing cascade child: {e}", False)
#                         # Fallback: create a simple cascade entry
#                         cascade_children.append({
#                             "id": child_data.get("id", str(ObjectId())),
#                             "property_name": property_name,
#                             "is_leaf": True,
#                             "children": [],
#                             "display_value": child_data.get(display_value_field, child_data.get("name", ""))
#                         })
                        
#             except Exception as e:
#                 DebugService.app_debug_print(f"Error fetching cascade children: {e}", False)
        
#         # Mark as leaf if no children
#         is_leaf = not bool(cascade_children)
        
#         # Get final display value with translation if needed
#         final_display_value = display_value
#         if can_be_translated and display_value is not None and isinstance(display_value, str) and accept_language != DEFAULT_LANGUAGE:
#             final_display_value = await BaseModelUtils.get_innter_translation(
#                 targeted_id=source_data.get("id"),
#                 short_code=accept_language,
#                 property_value=display_value,
#                 property_name=display_value_field,
#                 model_name=model_name
#             )
        
#         # Build response
#         response = {
#             "id": source_data.get("id"),
#             "property_name": property_name,
#             "is_leaf": is_leaf,
#             "children": cascade_children,
#             "display_value": final_display_value,
#         }
        
#         return response
    
#     def _build_required_fields_for_cascade(self, item: Dict[str, Any]) -> Dict[str, Any]:
#         """Build required fields dict for model instantiation in cascade."""
#         from bson import ObjectId
        
#         required_fields: Dict[str, Any] = {}
        
#         for field_name, field in self.model_fields.items():
#             if field.is_required():
#                 if field_name in item:
#                     required_fields[field_name] = item.get(field_name)
#                 else:
#                     # Provide default values for missing required fields
#                     if field.annotation == str:
#                         required_fields[field_name] = f"temp_{field_name}_{str(ObjectId())[-6:]}"
#                     elif field.annotation == int:
#                         required_fields[field_name] = 0
#                     elif field.annotation == float:
#                         required_fields[field_name] = 0.0
#                     elif field.annotation == bool:
#                         required_fields[field_name] = False
#                     elif field.annotation == list or (hasattr(field.annotation, '__origin__') and field.annotation.__origin__ == list):
#                         required_fields[field_name] = []
#                     elif field.annotation == dict or (hasattr(field.annotation, '__origin__') and field.annotation.__origin__ == dict):
#                         required_fields[field_name] = {}
        
#         # Always include ID field
#         if "_id" in item:
#             required_fields["id"] = str(item["_id"])
#         elif "id" in item:
#             required_fields["id"] = str(item["id"]) if not isinstance(item["id"], str) else item["id"]
#         else:
#             required_fields["id"] = str(ObjectId())
        
#         return required_fields

#     # ==================== Utility Methods ====================

#     @staticmethod
#     def _convert_id_fields_to_str(data):
#         """
#         Recursively convert all fields ending with '_id' to strings.

#         This ensures that ObjectId fields are properly serialized to strings
#         when serializing a document.

#         Only converts simple values (ObjectId, int, etc.) to strings, not dicts or lists
#         which may be formatted output structures.

#         Args:
#             data: The data to convert (dict, list, or other)

#         Returns:
#             The data with all _id fields converted to strings
#         """
#         if isinstance(data, dict):
#             result = {}
#             for k, v in data.items():
#                 if k.endswith('_id') and v is not None and not isinstance(v, (str, dict, list)):
#                     # Only convert simple values (ObjectId, int, etc.) to strings
#                     result[k] = str(v)
#                 elif isinstance(v, (dict, list)):
#                     # Recursively process nested structures
#                     result[k] = BaseDocument._convert_id_fields_to_str(v)
#                 else:
#                     result[k] = v
#             return result
#         elif isinstance(data, list):
#             return [BaseDocument._convert_id_fields_to_str(item) for item in data]
#         return data

#     def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
#         """
#         Convert document to dictionary.

#         Args:
#             exclude: List of field names to exclude

#         Returns:
#             Dict representation of the document
#         """
#         exclude = exclude or []
#         data = self.model_dump(exclude=set(exclude))

#         # Convert ObjectId to string
#         if "id" in data and data["id"]:
#             data["id"] = str(data["id"])
#         if "_id" in data and data["_id"]:
#             data["_id"] = str(data["_id"])

#         # Convert all _id fields to strings
#         data = self._convert_id_fields_to_str(data)

#         # Ensure decrypted values in the exported dict (use default language)
#         return self._decrypt_output_payload(data, accept_language=DEFAULT_LANGUAGE)

#     async def save_with_hooks(self, **kwargs) -> "BaseDocument":
#         """
#         Save the document with pre_save and post_save hooks.

#         This method should be used instead of the regular save() method
#         to ensure lifecycle hooks are called.

#         Args:
#             **kwargs: Additional context data

#         Returns:
#             The saved document instance
#         """
#         # Call pre_save hook
#         await self.pre_save(**kwargs)

#         # Save the document
#         await self.save()

#         # Call post_save hook
#         await self.post_save(**kwargs)

#         return self

#     # ==================== Class Methods ====================

#     @classmethod
#     async def format_list(
#         cls,
#         documents: List["BaseDocument"],
#         output_data_type: OutputDataType = OutputDataType.DEFAULT,
#         formatting_flag: EGlobalFormatingFlag = EGlobalFormatingFlag.DEFAULT,
#         accept_language: str = DEFAULT_LANGUAGE,
#         **kwargs
#     ) -> List[Any]:
#         """
#         Format a list of documents.

#         Args:
#             documents: List of document instances
#             output_data_type: Type of output
#             formatting_flag: Formatting style
#             accept_language: Language code for translations
#             **kwargs: Additional formatting options

#         Returns:
#             List of formatted documents
#         """
#         if not documents:
#             return []
        
#         # Use AsyncExecutor.gather for parallel formatting
#         format_tasks = [
#             doc.format(
#                 output_data_type=output_data_type,
#                 formatting_flag=formatting_flag,
#                 accept_language=accept_language,
#                 **kwargs
#             )
#             for doc in documents
#         ]
        
#         formatted_docs = await AsyncExecutor.gather(format_tasks)
#         return list(formatted_docs)
