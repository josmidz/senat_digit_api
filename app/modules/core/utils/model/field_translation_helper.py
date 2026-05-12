import re
from typing import Dict, Iterable, Mapping

from app.modules.core.models.field_translation_keys import (
    FALLBACK_LANGUAGE,
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGE_CODES,
)


class FieldTranslationHelper:
    """
    Helper for declaring per-model field translation keys using a clean
    keyword-argument syntax (one kwarg per language code).

    Usage inside a model class:

        FIELD_TRANSLATION_KEYS = FieldTranslationHelper.create_keys(
            fr={"numero_parc": "Numéro de parc", "immatriculation": "Immatriculation"},
            en={"numero_parc": "Fleet number", "immatriculation": "Registration plate"},
            ln={"numero_parc": "Numéro ya parc", "immatriculation": "Immatriculation"},
        )

    Returns:
        Dict[str, Dict[str, str]] — field-keyed dict:
        {
            "numero_parc": {"fr": "Numéro de parc", "en": "Fleet number", "ln": "Numéro ya parc", ...},
            "immatriculation": {"fr": "Immatriculation", "en": "Registration plate", ...},
        }

    Missing languages are auto-filled from FALLBACK_LANGUAGE → DEFAULT_LANGUAGE → first provided.
    """

    _FIELD_LABEL_OVERRIDES = {
        "abreviation": "Abbreviation",
        "account_label": "Account label",
        "account_number": "Account number",
        "admin_user_id": "Administrator",
        "application_group_flag": "Application group",
        "auth_email": "Authentication email",
        "auth_phone_number": "Authentication phone number",
        "base_currency_id": "Base currency",
        "cfg_system_country_id": "System country",
        "cfg_system_organization_id": "System organization",
        "cfg_system_town_entity_id": "System town entity",
        "created_by_id": "Created by",
        "default_transactional_currency_id": "Default transactional currency",
        "description_html": "HTML description",
        "description_str": "Description",
        "device_info": "Device information",
        "ending_bus_stop_id": "Ending bus stop",
        "ewallet_amount": "Wallet balance",
        "ewallet_number": "Wallet number",
        "ewallet_placeholder_name": "Wallet name",
        "first_name": "First name",
        "id": "ID",
        "identifier": "Identifier",
        "init_amount": "Initial amount",
        "ip_adress": "IP address",
        "is_active": "Active",
        "is_default": "Default",
        "last_name": "Last name",
        "operation_origin_id": "Operation origin",
        "order_by": "Display order",
        "others": "Other data",
        "phone_number": "Phone number",
        "pricing_type": "Pricing type",
        "ref_bank_id": "Bank",
        "ref_bank_type_id": "Bank type",
        "ref_children_display_type_id": "Children display type",
        "ref_country_id": "Country",
        "ref_currency_id": "Currency",
        "ref_document_template_id": "Document template",
        "ref_document_template_type_id": "Document template type",
        "ref_entity_id": "Entity",
        "ref_icon_id": "Icon",
        "ref_language_id": "Language",
        "ref_notification_channel_id": "Notification channel",
        "ref_notification_tunnel_id": "Notification tunnel",
        "ref_organization_id": "Organization",
        "ref_payment_method_id": "Payment method",
        "ref_person_id": "Person",
        "ref_phone_prefix_id": "Phone prefix",
        "ref_profile_id": "Profile",
        "ref_religion_id": "Religion",
        "ref_role_id": "Role",
        "ref_school_level_id": "School level",
        "ref_bus_stop_id": "Bus stop",
        "ref_system_country_id": "System country",
        "ref_township_entity_id": "Township",
        "ref_user_id": "User",
        "starting_bus_stop_id": "Starting bus stop",
        "status_lbl": "Status label",
        "status_color": "Status color",
        "sys_application_id": "Application",
        "sys_currency_id": "System currency",
        "sys_organization_id": "Organization",
        "sys_user_id": "User",
        "targeted_currency_id": "Target currency",
        "targeted_id": "Target",
        "temporary_usage_code": "Temporary usage code",
        "update_secret_attempt_fail_count": "Secret update failure count",
        "update_secret_attempt_locked_until": "Secret update locked until",
        "updated_by_id": "Updated by",
        "wallet_type": "Wallet type",
    }

    _PREFIXES_TO_DROP = {"ref", "cfg", "sys", "ops", "rbac", "ntf"}
    _TOKENS_TO_DROP = {"id"}
    _TOKEN_OVERRIDES = {
        "api": "API",
        "crud": "CRUD",
        "fcm": "FCM",
        "html": "HTML",
        "ip": "IP",
        "otp": "OTP",
        "saas": "SaaS",
        "totp": "TOTP",
        "ui": "UI",
        "url": "URL",
    }
    _DEFAULT_EXCLUDED_FIELDS = {"id", "identifier"}

    @classmethod
    def humanize_field_name(cls, field_name: str) -> str:
        """
        Generate a stable human-readable label from a model field name.
        """
        if field_name in cls._FIELD_LABEL_OVERRIDES:
            return cls._FIELD_LABEL_OVERRIDES[field_name]

        normalized = field_name
        if normalized.startswith("is_"):
            normalized = normalized[3:]
        if normalized.endswith("_id"):
            normalized = normalized[:-3]
        if normalized.endswith("_str"):
            normalized = normalized[:-4]

        parts = [part for part in normalized.split("_") if part]
        while len(parts) > 1 and parts[0] in cls._PREFIXES_TO_DROP:
            parts = parts[1:]

        words = []
        for part in parts:
            if part in cls._TOKENS_TO_DROP:
                continue
            token = cls._TOKEN_OVERRIDES.get(part)
            if token is None:
                token = re.sub(r"(?<=.)([A-Z])", r" \1", part).replace("-", " ").strip()
                token = token.upper() if token.isupper() else token.capitalize()
            words.append(token)

        if not words:
            return field_name.replace("_", " ").title()

        return " ".join(words)

    @staticmethod
    def create_keys(**lang_maps: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """
        Transpose language-keyed dicts into field-keyed dicts.

        Args:
            **lang_maps: keyword args where each key is a language code (fr, en, ln, ...)
                         and each value is a dict of {field_name: label}.
        """
        # Collect all field names across all provided languages
        all_fields: set[str] = set()
        for field_map in lang_maps.values():
            all_fields.update(field_map.keys())

        # Determine base language for fallback
        base_lang = (
            FALLBACK_LANGUAGE if FALLBACK_LANGUAGE in lang_maps
            else (DEFAULT_LANGUAGE if DEFAULT_LANGUAGE in lang_maps
                  else next(iter(lang_maps)))
        )

        # Build field-keyed result
        result: Dict[str, Dict[str, str]] = {}
        for field_name in sorted(all_fields):
            lang_dict: Dict[str, str] = {}
            for lang_code in SUPPORTED_LANGUAGE_CODES:
                if lang_code in lang_maps and field_name in lang_maps[lang_code]:
                    lang_dict[lang_code] = lang_maps[lang_code][field_name]
                else:
                    # Fallback: use base language label
                    lang_dict[lang_code] = lang_maps.get(base_lang, {}).get(
                        field_name,
                        field_name.replace("_", " ").title(),
                    )
            result[field_name] = lang_dict

        return result

    @classmethod
    def create_keys_from_fields(
        cls,
        *field_names: str,
        exclude: Iterable[str] | None = None,
    ) -> Dict[str, Dict[str, str]]:
        """
        Build generic field labels from field names and register them via create_keys().
        """
        excluded = set(cls._DEFAULT_EXCLUDED_FIELDS)
        if exclude:
            excluded.update(exclude)

        labels = {
            field_name: cls.humanize_field_name(field_name)
            for field_name in field_names
            if field_name not in excluded
        }
        return cls.create_keys(en=labels)

    @classmethod
    def create_keys_from_annotations(
        cls,
        class_namespace: Mapping[str, object],
        exclude: Iterable[str] | None = None,
    ) -> Dict[str, Dict[str, str]]:
        """
        Build generic field labels from the current class namespace annotations.
        """
        annotations = class_namespace.get("__annotations__", {})
        if not isinstance(annotations, Mapping):
            return {}
        return cls.create_keys_from_fields(*annotations.keys(), exclude=exclude)
