from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from typing import Optional, Dict, Any, List
import random
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlparse

from fastapi import Body, HTTPException, Request, status
from pydantic import BaseModel

from app.modules.auth.enums.common import MessageCategory
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.generator.generator_service import GeneratorService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.redis.redis_service import AppRedisService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.services.encryption.encryption_service import EncryptionService
from app.modules.core.enums.type_enum import OutputDataType, EExpectedActionTypeFlag, ESudoActionTypeFlag
from app.modules.core.services.email_sender.email_sender_service import EMailSenderService
from app.modules.core.services.sms.sms_service import SmsService
from app.modules.core.configs.config import settings
from app.modules.core.constants.keys import RedisKeys
from app.modules.core.utils.helpers.line_helper import format_exception
from app.modules.core.types.response import CustomJSONResponse
from app.modules.security.enums.security_enum import (
    EConfigSudoActionTypeFlag,
    ESudoActionAccessTargetedTypeFlag,
    ESudoActionAccessTypeFlag,
)
from app.modules.security.services.security_websocket_service import SecurityWebSocketService


class CheckQrcodeSudoActionRequest(BaseModel):
    instruction_key: str
    user_id: str
    qrcode_enc_key: str


class ValidateQrcodeSudoActionRequest(BaseModel):
    instruction_key: str
    user_id: str
    qrcode_enc_key: str


class SendDelegatedValidationOtpRequest(BaseModel):
    instruction_key: str
    validator_user_id: Optional[str] = None
    channel: Optional[str] = None


class VerifyDelegatedValidationOtpRequest(BaseModel):
    instruction_key: str
    otp_code: str


class SudoActionController(DebugService):
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        self.email_sender_service = EMailSenderService(accept_language=accept_language)
        self.sms_service = SmsService(accept_language=accept_language)
        super().__init__(accept_language)

    # ─── Helper: get mobile consumer hashes (can_receive_totp_validation_push=True) ───
    async def _get_mobile_consumer_hashes(self, user_details: Optional[Dict[str, Any]] = None) -> List[str]:
        """Fetch all API consumers that can receive push events (mobile apps)."""
        consumers = await self.generic_service.fetch_data_from_collection(
            collection_key=CollectionKey.REF_API_CONSUMER,
            output_data_type=OutputDataType.DEFAULT.value,
            all_data=True,
            page=0,
            limit=10,
            query={"filter__can_receive_totp_validation_push": True},
            sort={'created_at': -1},
            user=user_details,
        )
        return [c['consumer_hash'] for c in (consumers or [])]

    # ─── Helper: get the angular (source) consumer hash from the request ───
    async def _get_source_consumer_hash(self, request: Request) -> str:
        """Get the consumer_hash of the API consumer making the request."""
        api_consumer = await AuthenticatedService.get_api_consumer(request, self.accept_language)
        return api_consumer.get('consumer_hash', '')

    # ─── Helper: send event to mobile apps via WebSocket ───
    async def _send_event_to_mobile_apps(
        self,
        user_socket_hash: str,
        event_data: Dict[str, Any],
        redis_data: Optional[Dict[str, Any]] = None,
        source_consumer_hash: Optional[str] = None,
        user_details: Optional[Dict[str, Any]] = None,
    ):
        """Send WebSocket event to all mobile app consumers for a given user."""
        mobile_hashes = await self._get_mobile_consumer_hashes(user_details=user_details)
        if not mobile_hashes:
            self.app_debug_print("No mobile consumers found to send events to", True)
            return
        
        self.app_debug_print(
            f"SUDO_EVENT: Sending to {len(mobile_hashes)} mobile consumers, "
            f"user_socket_hash={user_socket_hash}, source={source_consumer_hash}", True
        )
        
        results = await SecurityWebSocketService.send_event_to_target_consumers(
            user_socket_hash=user_socket_hash,
            consumer_hashes=mobile_hashes,
            event_data=event_data,
            redis_data=redis_data,
            source_consumer_hash=source_consumer_hash,
        )
        self.app_debug_print(f"SUDO_EVENT: Send results: {results}", True)
        return results

    # ─── Helper: send event to angular (web) app via WebSocket ───
    async def _send_event_to_angular_app(
        self,
        user_socket_hash: str,
        angular_consumer_hash: str,
        event_data: Dict[str, Any],
        redis_data: Optional[Dict[str, Any]] = None,
    ):
        """Send WebSocket event back to the Angular web app."""
        target_key = f"{angular_consumer_hash}___{user_socket_hash}"
        self.app_debug_print(
            f"SUDO_EVENT: Sending to Angular app: {target_key}", True
        )
        result = await SecurityWebSocketService.send_event_to_client(target_key, event_data, redis_data)
        self.app_debug_print(f"SUDO_EVENT: Angular send result: {result}", True)
        return result

    def _extract_confirmation_type_debug_data(self, confirmation_types: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize sudo confirmation types for debug responses/logs."""
        return [
            {
                "id": c.get("id"),
                "flag": c.get("flag"),
                "name": c.get("name"),
                "description": c.get("totp_app_description_str"),
                "is_activated": c.get("is_activated"),
            }
            for c in (confirmation_types or [])
        ]

    @staticmethod
    def _normalize_qrcode_enc_key(value: Optional[str]) -> str:
        """
        Normalize qrcode_enc_key for robust comparison across transport variants.
        """
        if value is None:
            return ""
        return str(value).strip().replace(" ", "+").rstrip("=")

    @staticmethod
    def _normalize_target_endpoint_path(sudo_url: str) -> str:
        """
        Normalize X-Sudo-Url to an API path.
        Supports absolute URLs and relative paths.
        """
        if not sudo_url:
            return ""
        parsed = urlparse(str(sudo_url).strip())
        path = parsed.path or str(sudo_url).strip().split("?")[0]
        return path.strip()

    async def _resolve_rbac_endpoint_for_sudo_url(self, target_path: str, user_details: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Fetch RBAC endpoint metadata for the provided sudo target path."""
        if not target_path:
            return None

        candidate_paths = [target_path]
        trimmed_path = target_path.rstrip("/")
        if trimmed_path and trimmed_path != target_path:
            candidate_paths.append(trimmed_path)

        for path in candidate_paths:
            endpoint = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ENDPOINT,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={"filter__url": path},
                user=user_details,
            )
            if endpoint:
                return endpoint
        return None

    @staticmethod
    def _resolve_sudo_action_types(rbac_endpoint: Optional[Dict[str, Any]]) -> List[str]:
        """Map RBAC endpoint sudo flags to EConfigSudoActionTypeFlag values."""
        if not rbac_endpoint:
            return []

        sudo_types: List[str] = []
        if bool(rbac_endpoint.get("is_sudo_action", False)):
            sudo_types.append(EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value)
        if bool(rbac_endpoint.get("is_sudo_group_action", False)):
            sudo_types.append(EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value)
        if bool(rbac_endpoint.get("is_sudo_delegated_action", False)):
            sudo_types.append(EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION.value)
        if bool(rbac_endpoint.get("is_sudo_group_cross_validation_action", False)):
            sudo_types.append(
                EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION.value
            )
        if bool(rbac_endpoint.get("is_sudo_group_inter_organization_validation_action", False)):
            sudo_types.append(
                EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION.value
            )
        return sudo_types

    async def _is_sudo_enabled_for_organization(self, organization_id: str, user_details: Optional[Dict[str, Any]] = None) -> bool:
        """Check organization-level sudo setup switch."""
        sudo_setup = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_SUDO_ACTION_SETUP,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=self.accept_language,
            query={
                "filter__sys_organization_id": organization_id,
                "filter__is_enabled": True,
            },
            user=user_details,
        )
        return bool(sudo_setup)

    async def _is_endpoint_sudo_enabled_for_organization(
        self,
        organization_id: str,
        endpoint_id: str,
        sudo_action_types: List[str],
        user_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Resolve endpoint sudo enablement for organization and return:
        - is_enabled
        - selected_sudo_action_type (priority based)
        - cfg_organization_sudo_action (selected CFG_ORGANIZATION_SUDO_ACTION row)
        """
        result: Dict[str, Any] = {
            "is_enabled": False,
            "selected_sudo_action_type": None,
            "cfg_organization_sudo_action": None,
            "available_sudo_action_types": [],
        }

        if not organization_id or not endpoint_id or not sudo_action_types:
            return result

        ordered_sudo_action_types = self._get_sudo_action_type_priority(
            sudo_action_types
        )
        result["available_sudo_action_types"] = ordered_sudo_action_types

        for sudo_action_type in ordered_sudo_action_types:
            endpoint_config = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_ORGANIZATION_SUDO_ACTION,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={
                    "filter__sys_organization_id": organization_id,
                    "filter__rbac_endpoint_id": endpoint_id,
                    "filter__sudo_action_type": sudo_action_type,
                    "filter__is_enabled": True,
                },
                user=user_details,
            )
            if endpoint_config:
                result["is_enabled"] = True
                result["selected_sudo_action_type"] = sudo_action_type
                result["cfg_organization_sudo_action"] = endpoint_config
                return result
        return result

    @staticmethod
    def _get_sudo_action_type_priority(sudo_action_types: List[str]) -> List[str]:
        """
        Priority order:
        - inter_connected > cross > grouped > delegated > simple sudo
        """
        priority_order = [
            EConfigSudoActionTypeFlag.IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION.value,
            EConfigSudoActionTypeFlag.IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION.value,
            EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value,
            EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION.value,
            EConfigSudoActionTypeFlag.IS_SUDO_ACTION.value,
        ]
        ordered = [item for item in priority_order if item in sudo_action_types]
        remaining = [item for item in sudo_action_types if item not in ordered]
        return ordered + remaining

    async def _fetch_user_group_ids(
        self,
        organization_id: str,
        user_id: str,
        user_details: Optional[Dict[str, Any]] = None,
    ) -> set[str]:
        """Fetch all sudo/rls security groups containing the user."""
        group_memberships = await self.generic_service.fetch_data_from_collection(
            collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
            all_data=True,
            page=0,
            limit=100000,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=self.accept_language,
            query={
                "filter__sys_organization_id": organization_id,
                "filter__sys_user_id": user_id,
                "filter__is_activated": True,
            },
            user=user_details,
        )
        group_ids: set[str] = set()
        for membership in group_memberships or []:
            group_id = membership.get("ref_sudo_rls_security_group_id", None)
            if group_id:
                group_ids.add(str(group_id))
        return group_ids

    @staticmethod
    def _is_access_entry_matching_user(
        access_entry: Dict[str, Any],
        user_id: str,
        user_group_ids: set[str],
    ) -> bool:
        """Check whether a CFG_SUDO_ACTION_ACCESS entry applies to the user."""
        targeted_type = access_entry.get("targeted_type", "")
        targeted_id = str(access_entry.get("targeted_id", ""))
        if not targeted_id:
            return False

        if (
            targeted_type == ESudoActionAccessTargetedTypeFlag.USER.value
            and targeted_id == str(user_id)
        ):
            return True

        if (
            targeted_type
            == ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value
            and targeted_id in user_group_ids
        ):
            return True

        return False

    @staticmethod
    def _is_user_or_group_target(access_entry: Dict[str, Any]) -> bool:
        """Only USER and SUDO_RLS_SECURITY_GROUP targets are eligible validators."""
        targeted_type = access_entry.get("targeted_type", "")
        targeted_id = str(access_entry.get("targeted_id", "")).strip()
        return bool(targeted_id) and targeted_type in {
            ESudoActionAccessTargetedTypeFlag.USER.value,
            ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value,
        }

    async def _fetch_sudo_action_access_records(
        self,
        organization_id: str,
        sudo_action_access_type: str,
        cfg_organization_sudo_action_id: Optional[str] = None,
        user_details: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch CFG_SUDO_ACTION_ACCESS rows by type and optional action binding."""
        query: Dict[str, Any] = {
            "filter__sys_organization_id": organization_id,
            "filter__sudo_action_access_type": sudo_action_access_type,
            "filter__is_activated": True,
        }
        if cfg_organization_sudo_action_id is not None:
            query["filter__cfg_organization_sudo_action_id"] = cfg_organization_sudo_action_id

        data = await self.generic_service.fetch_data_from_collection(
            collection_key=CollectionKey.CFG_SUDO_ACTION_ACCESS,
            all_data=True,
            page=0,
            limit=100000,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=self.accept_language,
            query=query,
            user=user_details,
        )
        return data or []

    async def _is_user_allowed_for_delegated_validation(
        self,
        organization_id: str,
        user_id: str,
        cfg_organization_sudo_action_id: str,
        user_details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Delegated validation permissions:
        - GLOBAL_ACCESS (direct user or group membership)
        - DELEGATED_ACCESS linked to cfg_organization_sudo_action_id
        """
        user_group_ids = await self._fetch_user_group_ids(
            organization_id=organization_id,
            user_id=user_id,
            user_details=user_details,
        )

        global_access_records = await self._fetch_sudo_action_access_records(
            organization_id=organization_id,
            sudo_action_access_type=ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value,
            user_details=user_details,
        )
        delegated_access_records = await self._fetch_sudo_action_access_records(
            organization_id=organization_id,
            sudo_action_access_type=ESudoActionAccessTypeFlag.DELEGATED_ACCESS.value,
            cfg_organization_sudo_action_id=cfg_organization_sudo_action_id,
            user_details=user_details,
        )

        allowed_records = (global_access_records or []) + (delegated_access_records or [])
        return any(
            self._is_access_entry_matching_user(record, user_id, user_group_ids)
            for record in allowed_records
        )

    @staticmethod
    def _extract_organization_id_value(organization_value: Any) -> str:
        """Normalize organization identifier from raw id or nested object."""
        if isinstance(organization_value, dict):
            organization_value = (
                organization_value.get("id", None)
                or organization_value.get("_id", None)
            )
        if organization_value is None:
            return ""
        return str(organization_value).strip()

    @staticmethod
    def _build_user_full_name(user_data: Dict[str, Any]) -> str:
        first_name = str(user_data.get("first_name", "")).strip()
        last_name = str(user_data.get("last_name", "")).strip()
        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            return full_name

        for fallback_key in ("email", "phone_number", "username"):
            fallback_value = str(user_data.get(fallback_key, "")).strip()
            if fallback_value:
                return fallback_value
        return ""

    @staticmethod
    def _sanitize_delegated_validators_for_client(
        validators: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Drop backend-only fields (e.g. socket hash) before returning to frontend."""
        items: List[Dict[str, Any]] = []
        for validator in validators or []:
            items.append(
                {
                    "user_id": str(validator.get("user_id", "")).strip(),
                    "first_name": str(validator.get("first_name", "")).strip(),
                    "last_name": str(validator.get("last_name", "")).strip(),
                    "full_name": str(validator.get("full_name", "")).strip(),
                    "email": str(validator.get("email", "")).strip(),
                    "phone_number": str(validator.get("phone_number", "")).strip(),
                    "access_sources": list(validator.get("access_sources", []) or []),
                }
            )
        return items

    @staticmethod
    def _normalize_otp_channel(
        requested_channel: Optional[str],
        confirmation_flag: Optional[str],
    ) -> str:
        """Resolve OTP channel from explicit payload channel or sudo confirmation flag."""
        normalized_channel = str(requested_channel or "").strip().lower()
        if normalized_channel in {"email"}:
            return "email"
        if normalized_channel in {"phone", "phone_number", "sms"}:
            return "phone"

        normalized_flag = str(confirmation_flag or "").strip().lower()
        if normalized_flag == ESudoActionTypeFlag.EMAIL.value.lower():
            return "email"
        if normalized_flag in {
            ESudoActionTypeFlag.PHONE.value.lower(),
            "phone_number",
            "sms",
        }:
            return "phone"
        return ""

    @staticmethod
    def _mask_contact_value(contact_value: str, channel: str) -> str:
        """Return a partially masked contact value safe for client responses."""
        value = str(contact_value or "").strip()
        if not value:
            return ""

        if channel == "email":
            local_part, separator, domain_part = value.partition("@")
            if not separator:
                return "***"
            if len(local_part) <= 2:
                masked_local = f"{local_part[:1]}***"
            else:
                masked_local = f"{local_part[:2]}***"
            return f"{masked_local}@{domain_part}"

        digits = "".join(character for character in value if character.isdigit())
        if not digits:
            return "***"
        if len(digits) <= 4:
            return "*" * len(digits)
        return f"{'*' * (len(digits) - 4)}{digits[-4:]}"

    @staticmethod
    def _extract_delegated_validation_from_sudo_data(
        sudo_action_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        delegated_validation = (sudo_action_data or {}).get("delegated_validation", {})
        if not isinstance(delegated_validation, dict):
            return {}
        return delegated_validation

    @staticmethod
    def _resolve_sudo_redis_expiry_from_data(
        sudo_action_data: Dict[str, Any],
        default_expiry_seconds: int = 300,
    ) -> int:
        raw_expiry = (sudo_action_data or {}).get("expiration_time", default_expiry_seconds)
        try:
            normalized_expiry = int(raw_expiry)
        except (TypeError, ValueError):
            normalized_expiry = default_expiry_seconds
        return max(normalized_expiry, 60)

    @staticmethod
    def _find_eligible_validator_by_user_id(
        eligible_validators: List[Dict[str, Any]],
        target_user_id: str,
    ) -> Optional[Dict[str, Any]]:
        target_user_id = str(target_user_id or "").strip()
        if not target_user_id:
            return None
        for validator in eligible_validators or []:
            if str(validator.get("user_id", "")).strip() == target_user_id:
                return validator
        return None

    async def _dispatch_sudo_contact_otp(
        self,
        *,
        channel: str,
        otp_code: str,
        recipient_email: str,
        recipient_phone_number: str,
    ) -> Dict[str, Any]:
        """
        Send OTP by email or phone.
        In local/test environments, delivery is skipped but OTP generation remains available.
        """
        normalized_channel = str(channel or "").strip().lower()
        env = str(getattr(settings, "ENV", "local")).strip().lower()
        can_deliver = env in {"production", "development"}

        if normalized_channel == "email":
            if not recipient_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected validator has no email address.",
                )

            if can_deliver:
                mail_title_translated = (
                    ResponseService.get_response_message(
                        MessageCategory.COMMON, "OTP_EMAIL_TITLE", self.accept_language
                    )
                    or "OTP Validation"
                )
                mail_message_translated = (
                    ResponseService.get_response_message(
                        MessageCategory.COMMON,
                        "OTP_EMAIL_BODY",
                        self.accept_language,
                        otp_code=otp_code,
                    )
                    or f"Your validation OTP is: {otp_code}"
                )
                second_mail_message_translated = (
                    ResponseService.get_response_message(
                        MessageCategory.COMMON,
                        "OTP_EMAIL_SECOND_MESSAGE",
                        self.accept_language,
                    )
                    or "Use this code to confirm your operation."
                )
                mail_note_translated = (
                    ResponseService.get_response_message(
                        MessageCategory.COMMON,
                        "OTP_EMAIL_NOTE",
                        self.accept_language,
                    )
                    or "This code expires shortly."
                )
                await self.email_sender_service.sending_translated_email_async(
                    email_to=recipient_email,
                    subject=f"{otp_code} - OTP",
                    mail_title_translated=mail_title_translated,
                    mail_message_translated=mail_message_translated,
                    second_mail_message_translated=second_mail_message_translated,
                    mail_note_translated=mail_note_translated,
                    accept_language=self.accept_language,
                )
            else:
                self.app_debug_print(
                    "SUDO OTP: Skipping email delivery outside production/development environment",
                    True,
                )

            return {
                "channel": "email",
                "masked_destination": self._mask_contact_value(recipient_email, "email"),
                "debug_otp_code": otp_code if not can_deliver else "",
            }

        if normalized_channel == "phone":
            if not recipient_phone_number:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected validator has no phone number.",
                )

            if can_deliver:
                sms_message = (
                    ResponseService.get_response_message(
                        MessageCategory.COMMON,
                        "OTP_SMS_MESSAGE",
                        self.accept_language,
                        otp_code=otp_code,
                    )
                    or f"Your validation OTP is: {otp_code}"
                )
                await self.sms_service.send_sms_httpx_async(
                    phone_number=recipient_phone_number,
                    message=sms_message,
                )
            else:
                self.app_debug_print(
                    "SUDO OTP: Skipping SMS delivery outside production/development environment",
                    True,
                )

            return {
                "channel": "phone",
                "masked_destination": self._mask_contact_value(recipient_phone_number, "phone"),
                "debug_otp_code": otp_code if not can_deliver else "",
            }

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported OTP channel. Allowed values: email, phone.",
        )

    async def _resolve_delegated_eligible_validators(
        self,
        organization_id: str,
        cfg_organization_sudo_action_id: str,
        user_details: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Resolve all eligible validators for delegated validation:
        - GLOBAL_ACCESS (direct user or security-group members)
        - DELEGATED_ACCESS linked to cfg_organization_sudo_action_id
        """
        global_access_records = await self._fetch_sudo_action_access_records(
            organization_id=organization_id,
            sudo_action_access_type=ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value,
            user_details=user_details,
        )
        delegated_access_records = await self._fetch_sudo_action_access_records(
            organization_id=organization_id,
            sudo_action_access_type=ESudoActionAccessTypeFlag.DELEGATED_ACCESS.value,
            cfg_organization_sudo_action_id=cfg_organization_sudo_action_id,
            user_details=user_details,
        )

        all_access_records = (global_access_records or []) + (delegated_access_records or [])
        if not all_access_records:
            return []

        user_access_sources: Dict[str, set[str]] = {}
        group_access_sources: Dict[str, set[str]] = {}

        for access_record in all_access_records:
            if not self._is_user_or_group_target(access_record):
                continue

            access_type = str(access_record.get("sudo_action_access_type", "")).strip()
            targeted_type = access_record.get("targeted_type", "")
            targeted_id = str(access_record.get("targeted_id", "")).strip()
            if not targeted_id:
                continue

            if targeted_type == ESudoActionAccessTargetedTypeFlag.USER.value:
                if targeted_id not in user_access_sources:
                    user_access_sources[targeted_id] = set()
                if access_type:
                    user_access_sources[targeted_id].add(access_type)
                continue

            if targeted_type == ESudoActionAccessTargetedTypeFlag.SUDO_RLS_SECURITY_GROUP.value:
                if targeted_id not in group_access_sources:
                    group_access_sources[targeted_id] = set()
                if access_type:
                    group_access_sources[targeted_id].add(access_type)

        for group_id, group_access_types in group_access_sources.items():
            group_members = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_SUDO_RLS_SECURITY_GROUP_USER,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={
                    "filter__sys_organization_id": organization_id,
                    "filter__ref_sudo_rls_security_group_id": group_id,
                    "filter__is_activated": True,
                },
                user=user_details,
            )
            for group_member in group_members or []:
                member_user_id = str(group_member.get("sys_user_id", "")).strip()
                if not member_user_id:
                    continue
                if member_user_id not in user_access_sources:
                    user_access_sources[member_user_id] = set()
                user_access_sources[member_user_id].update(group_access_types)

        eligible_validators: List[Dict[str, Any]] = []
        for candidate_user_id, access_sources in user_access_sources.items():
            user_info = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={"filter___id": candidate_user_id},
                user=user_details,
            )
            user_info = user_info or {}

            first_name = str(user_info.get("first_name", "")).strip()
            last_name = str(user_info.get("last_name", "")).strip()
            full_name = self._build_user_full_name(user_info)
            email = str(user_info.get("email", "")).strip()
            phone_number = str(user_info.get("phone_number", "")).strip()
            socket_hash = str(user_info.get("user_account_socket_hash", "")).strip()

            eligible_validators.append(
                {
                    "user_id": str(candidate_user_id).strip(),
                    "first_name": first_name,
                    "last_name": last_name,
                    "full_name": full_name,
                    "email": email,
                    "phone_number": phone_number,
                    "user_account_socket_hash": socket_hash,
                    "access_sources": sorted(source for source in access_sources if source),
                }
            )

        eligible_validators.sort(
            key=lambda user_item: (
                str(user_item.get("full_name", "")).lower(),
                str(user_item.get("email", "")).lower(),
                str(user_item.get("user_id", "")).lower(),
            )
        )
        return eligible_validators

    async def _resolve_delegated_validation_context(
        self,
        organization_id: str,
        current_user_id: str,
        cfg_organization_sudo_action_id: str,
        user_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Resolve delegated-validation eligibility context for init flow."""
        all_eligible_validators = await self._resolve_delegated_eligible_validators(
            organization_id=organization_id,
            cfg_organization_sudo_action_id=cfg_organization_sudo_action_id,
            user_details=user_details,
        )

        current_user_id = str(current_user_id or "").strip()
        current_user_can_validate = any(
            str(item.get("user_id", "")).strip() == current_user_id
            for item in all_eligible_validators
        )

        return {
            "is_configured": bool(all_eligible_validators),
            "current_user_can_validate": current_user_can_validate,
            "requires_external_validator": bool(all_eligible_validators) and not current_user_can_validate,
            "all_eligible_validators": all_eligible_validators,
        }

    async def _resolve_sudo_action_organization_id(
        self,
        sudo_action_data: Dict[str, Any],
        sudo_action_owner_user_id: str,
        user_details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Resolve organization id from stored sudo payload (fallback to owner user lookup)."""
        organization_id = self._extract_organization_id_value(
            (sudo_action_data or {}).get("sys_organization_id", "")
        )
        if organization_id:
            return organization_id

        owner_user_id = str(sudo_action_owner_user_id or "").strip()
        if not owner_user_id:
            return ""

        owner_user = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.SYS_USER,
            output_data_type=OutputDataType.DEFAULT,
            accept_language=self.accept_language,
            query={"filter___id": owner_user_id},
            user=user_details,
        )
        if not owner_user:
            return ""

        return self._extract_organization_id_value(
            owner_user.get("sys_organization_id", None)
        )

    async def _enforce_delegated_qrcode_validator_access(
        self,
        request: Request,
        sudo_action_data: Dict[str, Any],
        sudo_action_owner_user_id: str,
        user_details: Optional[Dict[str, Any]] = None,
    ) -> Optional[CustomJSONResponse]:
        """
        For delegated sudo action, only users with GLOBAL_ACCESS or DELEGATED_ACCESS
        (directly or through configured security groups) can validate QR operations.
        """
        resolved_sudo_action_type = str(
            (sudo_action_data or {}).get("resolved_sudo_action_type", "")
        ).strip()
        if (
            resolved_sudo_action_type
            != EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION.value
        ):
            return None

        validator_user = await AuthenticatedService.get_user_info(
            request, self.accept_language
        )
        validator_user_id = str((validator_user or {}).get("id", "")).strip()
        if not validator_user_id:
            invalid_user_message = ResponseService.get_response_message(
                MessageCategory.COMMON, "INVALID_USER_ACCOUNT", self.accept_language
            ) or "Invalid user account"
            return self._build_init_sudo_error_response(
                error_code="INVALID_USER_ACCOUNT",
                detail=invalid_user_message,
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        # Use validator_user as user_details if not provided
        effective_user_details = user_details if user_details is not None else validator_user

        cfg_organization_sudo_action_id = str(
            (sudo_action_data or {}).get("cfg_organization_sudo_action_id", "")
        ).strip()
        if not cfg_organization_sudo_action_id:
            return self._build_init_sudo_error_response(
                error_code="SUDO_DELEGATED_ACTION_MISCONFIGURED",
                detail="Delegated sudo action is misconfigured for this endpoint.",
            )

        organization_id = await self._resolve_sudo_action_organization_id(
            sudo_action_data=sudo_action_data,
            sudo_action_owner_user_id=sudo_action_owner_user_id,
            user_details=effective_user_details,
        )
        if not organization_id:
            return self._build_init_sudo_error_response(
                error_code="SUDO_DELEGATED_ACTION_MISCONFIGURED",
                detail="Unable to resolve organization for delegated sudo validation.",
            )

        can_validate = await self._is_user_allowed_for_delegated_validation(
            organization_id=organization_id,
            user_id=validator_user_id,
            cfg_organization_sudo_action_id=cfg_organization_sudo_action_id,
            user_details=effective_user_details,
        )
        if not can_validate:
            return self._build_init_sudo_error_response(
                error_code="SUDO_DELEGATED_VALIDATION_ACCESS_DENIED",
                detail="You are not allowed to validate this delegated sudo action.",
            )

        return None

    async def _has_group_action_validator_configuration(
        self,
        organization_id: str,
        cfg_organization_sudo_action_id: str,
        user_details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Grouped action can be initiated only when at least one eligible validator exists:
        - GLOBAL_ACCESS (user or security group)
        - GROUPED_ACCESS linked to cfg_organization_sudo_action_id
        """
        global_access_records = await self._fetch_sudo_action_access_records(
            organization_id=organization_id,
            sudo_action_access_type=ESudoActionAccessTypeFlag.GLOBAL_ACCESS.value,
            user_details=user_details,
        )
        grouped_access_records = await self._fetch_sudo_action_access_records(
            organization_id=organization_id,
            sudo_action_access_type=ESudoActionAccessTypeFlag.GROUPED_ACCESS.value,
            cfg_organization_sudo_action_id=cfg_organization_sudo_action_id,
            user_details=user_details,
        )

        return any(
            self._is_user_or_group_target(record)
            for record in (global_access_records or []) + (grouped_access_records or [])
        )

    def _build_skip_sudo_response(self, reason: str, sudo_url: Optional[str] = None) -> CustomJSONResponse:
        """Return a successful response instructing frontend to bypass sudo modal."""
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "message": "Sudo validation is not enabled for this organization endpoint",
                "data": {
                    "skip_sudo_validation": True,
                    "should_submit_directly": True,
                    "reason": reason,
                    "url": sudo_url or "",
                },
            },
        )

    def _build_init_sudo_error_response(
        self,
        *,
        error_code: str,
        detail: str,
        status_code: int = status.HTTP_403_FORBIDDEN,
    ) -> CustomJSONResponse:
        """Return structured init-sudo error response with explicit backend error code."""
        return CustomJSONResponse(
            status_code=status_code,
            content={
                "status_code": status_code,
                "success": False,
                "message": detail,
                "detail": detail,
                "error": error_code,
                "data": None,
            },
        )

    async def debug_sudo_confirmation_types(
        self,
        request: Request,
        include_inactive: bool = False,
    ) -> Dict[str, Any]:
        """Debug endpoint to inspect sudo confirmation types currently available in DB."""
        try:
            user_details = await AuthenticatedService.get_user_info(request, self.accept_language)
            user_id = user_details.get("id", None)

            query: Dict[str, Any] = {}
            if not include_inactive:
                query["filter__is_activated"] = True

            confirmation_types = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_SUDO_ACTION_CONFIRMATION_TYPE,
                all_data=True,
                page=0,
                limit=100,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query=query,
                sort={"created_at": -1},
                user=user_details,
            )

            items = self._extract_confirmation_type_debug_data(confirmation_types or [])
            flags = [item.get("flag") for item in items if item.get("flag")]
            unique_flags = sorted(set(flags))

            self.app_debug_print(
                f"SUDO_DEBUG: confirmation_types count={len(items)} include_inactive={include_inactive} "
                f"flags={unique_flags} requester={user_id}",
                True,
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": "Sudo confirmation types debug data",
                    "data": {
                        "requester_user_id": user_id,
                        "include_inactive": include_inactive,
                        "count": len(items),
                        "flags": unique_flags,
                        "items": items,
                    },
                },
            )
        except Exception as e:
            format_error = format_exception("Error in debug_sudo_confirmation_types: ", e)
            self.app_debug_print(f"Error in debug_sudo_confirmation_types: {format_error}", True)
            raise HTTPException(status_code=500, detail="Unable to fetch sudo confirmation types debug data")

    async def initiate_sudo_action(self, request: Request) -> Dict[str, Any]:
        """
        Initiate a sudo action by:
        1. Reading sudo_url and sudo_instruction_key from headers
        2. Creating Redis storage with key: user_id + instruction_key
        3. Saving data: {url, status: "pending_verification", qrcode_enc_key, expiration_time, instruction_key}
        4. Returning random selected validation from sudo_action_confirmation_types
        """
        try:
            # Get headers
            sudo_url = request.headers.get("X-Sudo-Url", None)
            # sudo_instruction_key = request.headers.get("X-Sudo-Instruction-Key", None)

            if not sudo_url:
                message = ResponseService.get_response_message(MessageCategory.EXCEPTIONS, "MISSING_SUDO_URL", self.accept_language)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message or "Missing sudo URL in headers")

            # if not sudo_instruction_key:
                # Generate instruction key if not provided
            sudo_instruction_key = GeneratorService.generate_encryption_key()

            # Get authenticated user
            user_details = await AuthenticatedService.get_user_info(request, self.accept_language)
            user_id = user_details.get('id', None)
            user_account_socket_hash = user_details.get('user_account_socket_hash', None)

            if not user_id:
                message = ResponseService.get_response_message(MessageCategory.COMMON, "INVALID_USER_ACCOUNT", self.accept_language)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

            # ─── APPLY SAME ORG/ENDPOINT GATING AS SudoActionCheckMiddleware ───
            organization_id = user_details.get("sys_organization_id", None)
            if isinstance(organization_id, dict):
                organization_id = organization_id.get("id", None) or organization_id.get("_id", None)
            if not organization_id:
                self.app_debug_print(
                    "SUDO INIT: Missing sys_organization_id on authenticated user, skipping sudo flow",
                    True,
                )
                return self._build_skip_sudo_response(
                    reason="missing_organization",
                    sudo_url=sudo_url,
                )

            target_path = self._normalize_target_endpoint_path(sudo_url)
            rbac_endpoint = await self._resolve_rbac_endpoint_for_sudo_url(target_path, user_details=user_details)
            endpoint_sudo_types = self._resolve_sudo_action_types(rbac_endpoint)

            # If endpoint has no sudo flags in RBAC, do not start sudo flow.
            if not endpoint_sudo_types:
                self.app_debug_print(
                    f"SUDO INIT: Skipping sudo flow (endpoint not sudo-protected) path={target_path}",
                    True,
                )
                return self._build_skip_sudo_response(
                    reason="endpoint_not_sudo_protected",
                    sudo_url=sudo_url,
                )

            # Organization global sudo setup switch
            org_sudo_enabled = await self._is_sudo_enabled_for_organization(str(organization_id), user_details=user_details)
            if not org_sudo_enabled:
                self.app_debug_print(
                    f"SUDO INIT: Skipping sudo flow (CFG_SUDO_ACTION_SETUP disabled) org={organization_id}",
                    True,
                )
                return self._build_skip_sudo_response(
                    reason="organization_sudo_disabled",
                    sudo_url=sudo_url,
                )

            endpoint_id = str((rbac_endpoint or {}).get("id", ""))
            endpoint_sudo_resolution = await self._is_endpoint_sudo_enabled_for_organization(
                organization_id=str(organization_id),
                endpoint_id=endpoint_id,
                sudo_action_types=endpoint_sudo_types,
                user_details=user_details,
            )
            if not endpoint_sudo_resolution.get("is_enabled", False):
                self.app_debug_print(
                    f"SUDO INIT: Skipping sudo flow (endpoint not enabled for org) org={organization_id} endpoint={endpoint_id} types={endpoint_sudo_types}",
                    True,
                )
                return self._build_skip_sudo_response(
                    reason="endpoint_sudo_disabled_for_organization",
                    sudo_url=sudo_url,
                )

            selected_sudo_action_type = endpoint_sudo_resolution.get(
                "selected_sudo_action_type", ""
            )
            selected_org_sudo_action = endpoint_sudo_resolution.get(
                "cfg_organization_sudo_action", {}
            ) or {}
            selected_org_sudo_action_id_raw = selected_org_sudo_action.get(
                "id", None
            ) or selected_org_sudo_action.get("_id", None)
            selected_org_sudo_action_id = (
                str(selected_org_sudo_action_id_raw).strip()
                if selected_org_sudo_action_id_raw is not None
                else ""
            )

            selected_is_sudo_group_action = (
                selected_sudo_action_type
                == EConfigSudoActionTypeFlag.IS_SUDO_GROUP_ACTION.value
            )
            selected_is_sudo_delegated_action = (
                selected_sudo_action_type
                == EConfigSudoActionTypeFlag.IS_SUDO_DELEGATED_ACTION.value
            )
            delegated_validation_payload: Dict[str, Any] = {
                "is_delegated_action": selected_is_sudo_delegated_action,
                "current_user_can_validate": True,
                "requires_external_validator": False,
                "eligible_validators": [],
            }
            delegated_validator_user_ids: List[str] = []
            delegated_validator_socket_hashes: List[str] = []

            self.app_debug_print(
                "SUDO INIT: Resolved org sudo action "
                f"type={selected_sudo_action_type} "
                f"cfg_organization_sudo_action_id={selected_org_sudo_action_id}",
                True,
            )

            if selected_is_sudo_group_action:
                if not selected_org_sudo_action_id:
                    return self._build_init_sudo_error_response(
                        error_code="SUDO_GROUP_ACTION_MISCONFIGURED",
                        detail="Grouped sudo action is misconfigured for this endpoint.",
                    )

                has_group_validator_configuration = (
                    await self._has_group_action_validator_configuration(
                        organization_id=str(organization_id),
                        cfg_organization_sudo_action_id=selected_org_sudo_action_id,
                        user_details=user_details,
                    )
                )
                if not has_group_validator_configuration:
                    return self._build_init_sudo_error_response(
                        error_code="SUDO_GROUP_VALIDATORS_MISSING",
                        detail="Missing users/groups with global validation access or grouped access for this endpoint.",
                    )

            if selected_is_sudo_delegated_action:
                if not selected_org_sudo_action_id:
                    return self._build_init_sudo_error_response(
                        error_code="SUDO_DELEGATED_ACTION_MISCONFIGURED",
                        detail="Delegated sudo action is misconfigured for this endpoint.",
                    )

                delegated_validation_context = (
                    await self._resolve_delegated_validation_context(
                        organization_id=str(organization_id),
                        current_user_id=str(user_id),
                        cfg_organization_sudo_action_id=selected_org_sudo_action_id,
                        user_details=user_details,
                    )
                )
                if not delegated_validation_context.get("is_configured", False):
                    return self._build_init_sudo_error_response(
                        error_code="SUDO_DELEGATED_ACTION_MISCONFIGURED",
                        detail=(
                            "Missing users/groups with global or delegated access for this endpoint."
                        ),
                    )

                all_eligible_validators = delegated_validation_context.get(
                    "all_eligible_validators", []
                ) or []
                delegated_validator_user_ids = [
                    str(item.get("user_id", "")).strip()
                    for item in all_eligible_validators
                    if str(item.get("user_id", "")).strip()
                ]
                delegated_validator_socket_hashes = [
                    str(item.get("user_account_socket_hash", "")).strip()
                    for item in all_eligible_validators
                    if str(item.get("user_account_socket_hash", "")).strip()
                ]

                requires_external_validator = bool(
                    delegated_validation_context.get("requires_external_validator", False)
                )
                delegated_validation_payload = {
                    "is_delegated_action": True,
                    "current_user_can_validate": bool(
                        delegated_validation_context.get(
                            "current_user_can_validate", False
                        )
                    ),
                    "requires_external_validator": requires_external_validator,
                    "eligible_validators": self._sanitize_delegated_validators_for_client(
                        all_eligible_validators
                    ),
                }

            # Fetch sudo action confirmation types
            sudo_action_confirmation_types = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_SUDO_ACTION_CONFIRMATION_TYPE,
                all_data=True,
                page=0,
                limit=10,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={
                    "filter__is_activated": True,
                },
                user=user_details,
            )

            if not sudo_action_confirmation_types or len(sudo_action_confirmation_types) == 0:
                message = ResponseService.get_response_message(MessageCategory.COMMON, "NO_SUDO_ACTION_CONFIRMATION_TYPES", self.accept_language)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message or "No sudo action confirmation types found")

            loaded_types_debug = self._extract_confirmation_type_debug_data(sudo_action_confirmation_types)
            self.app_debug_print(
                f"SUDO_DEBUG: INIT loaded confirmation types ({len(loaded_types_debug)}): "
                f"{[(x.get('flag'), x.get('name')) for x in loaded_types_debug]}",
                True,
            )

            # Select random confirmation type
            random_confirmation_type = random.choice(sudo_action_confirmation_types)
            self.app_debug_print(
                "SUDO_DEBUG: INIT selected confirmation type "
                f"id={random_confirmation_type.get('id')} "
                f"flag={random_confirmation_type.get('flag')} "
                f"name={random_confirmation_type.get('name')}",
                True,
            )

            # Generate QR code encryption key
            qrcode_enc_key = GeneratorService.generate_encryption_key()

            # Build Redis key: user_id + instruction_key
            sudo_initiation_key = RedisKeys.format_key(
                RedisKeys.SUDO_ACTION,
                instruction_id=f"{user_id}_{sudo_instruction_key}"
            )

            # Expiration time: 20 minutes (in seconds)
            expiration_time_seconds = 20 * 60
            source_consumer_hash = await self._get_source_consumer_hash(request)

            # Data to store in Redis
            redis_data = {
                "url": sudo_url,
                "status": "pending_verification",
                "qrcode_enc_key": qrcode_enc_key,
                "expiration_time": expiration_time_seconds,
                "instruction_key": sudo_instruction_key,
                "user_id": user_id,
                "user_account_socket_hash": user_account_socket_hash,
                "angular_consumer_hash": source_consumer_hash,
                "selected_confirmation_type": {
                    "id": random_confirmation_type.get('id'),
                    "flag": random_confirmation_type.get('flag'),
                    "name": random_confirmation_type.get('name'),
                    "description": random_confirmation_type.get('totp_app_description_str'),
                },
                "resolved_sudo_action_type": selected_sudo_action_type,
                "cfg_organization_sudo_action_id": selected_org_sudo_action_id,
                "sys_organization_id": str(organization_id),
                "delegated_validation": {
                    **delegated_validation_payload,
                    "eligible_validator_user_ids": delegated_validator_user_ids,
                    "eligible_validator_socket_hashes": delegated_validator_socket_hashes,
                },
            }

            # Store in Redis with expiration
            self.app_debug_print(f" SUDO INITIATION: Storing key >> : {sudo_initiation_key} ", True)
            await AppRedisService.set_redis_value(
                sudo_initiation_key,
                json.dumps(redis_data),
                expiration_time_seconds
            )

            self.app_debug_print(f" SUDO INITIATION: Data stored successfully ", True)

            # Build deeplink QR code content for mobile app
            qr_payload = json.dumps({
                "instruction_key": sudo_instruction_key,
                "user_id": user_id,
                "qrcode_enc_key": qrcode_enc_key,
            })
            encrypted_qr_payload = EncryptionService.aes_encrypt_for_mobile(qr_payload)
            qr_deeplink = f"sycamore://sudo/validate?data={quote(encrypted_qr_payload, safe='')}"

            self.app_debug_print(f" SUDO INITIATION: QR deeplink generated ", True)

            # ─── Send WebSocket event to mobile apps ───
            # Build event data based on selected confirmation type flag
            confirmation_flag = random_confirmation_type.get('flag', '')
            
            mobile_event_data = {
                "type": "instruction",
                "custom_type": confirmation_flag,
                "params": {
                    "instruction_key": sudo_instruction_key,
                    "user_id": user_id,
                    "qrcode_enc_key": qrcode_enc_key,
                    "instruction_id": sudo_instruction_key,
                    "expected_action": EExpectedActionTypeFlag.SUDO_ACTION.value,
                    "description": random_confirmation_type.get('totp_app_description_str', ''),
                }
            }

            # Add golden numbers for GOLDEN_NUMBER type
            golden_numbers = []
            selected_golden_number = 0
            if confirmation_flag == ESudoActionTypeFlag.GOLDEN_NUMBER.value:
                golden_numbers = GeneratorService.generate_random_golden_numbers(3)
                random_golden_number = random.choice(golden_numbers)
                selected_golden_number = random_golden_number.get('number', 0) if isinstance(random_golden_number, dict) else random_golden_number
                mobile_event_data["params"]["numbers"] = golden_numbers

                # Also store golden number in Redis
                redis_data["selected_golden_number"] = random_golden_number
                await AppRedisService.set_redis_value(
                    sudo_initiation_key,
                    json.dumps(redis_data),
                    expiration_time_seconds
                )

            # Build Redis data for the mobile event
            merged_redis_info = {
                **redis_data,  # Preserve qrcode_enc_key/status/url and all sudo metadata
                **mobile_event_data,  # Keep websocket instruction payload for listeners
                "api_consumer_key": source_consumer_hash,
                "api_consumer_keys": await self._get_mobile_consumer_hashes(user_details=user_details),
                "instruction_id": sudo_instruction_key,
                "instruction_key": sudo_instruction_key,
                "expected_action": EExpectedActionTypeFlag.SUDO_ACTION.value,
                "custom_type": confirmation_flag,
                "type": "instruction",
                "params": {
                    **mobile_event_data.get("params", {}),
                    "api_consumer_key": source_consumer_hash,
                },
            }
            mobile_redis_data = {
                "redis_data_key": sudo_initiation_key,
                "redis_data_info": merged_redis_info,
                "redis_expire_time": expiration_time_seconds,
            }

            target_socket_hashes: set[str] = set()
            if selected_is_sudo_delegated_action and delegated_validation_payload.get(
                "requires_external_validator", False
            ):
                target_socket_hashes = {
                    str(socket_hash).strip()
                    for socket_hash in delegated_validator_socket_hashes
                    if str(socket_hash).strip()
                }
            else:
                if user_account_socket_hash:
                    target_socket_hashes.add(str(user_account_socket_hash).strip())

            if not target_socket_hashes:
                self.app_debug_print(
                    "SUDO INITIATION: No eligible mobile socket hash found for push notification",
                    True,
                )

            # Send to resolved mobile validator users
            for target_socket_hash in target_socket_hashes:
                try:
                    await self._send_event_to_mobile_apps(
                        user_socket_hash=target_socket_hash,
                        event_data=mobile_event_data,
                        redis_data=mobile_redis_data,
                        source_consumer_hash=source_consumer_hash,
                        user_details=user_details,
                    )
                except Exception as ws_error:
                    self.app_debug_print(
                        f"SUDO INITIATION: WebSocket push to mobile failed for {target_socket_hash}: {ws_error}",
                        True,
                    )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": ResponseService.get_response_message(MessageCategory.SUCCESS, "SUDO_ACTION_INITIATED", self.accept_language) or "Sudo action initiated successfully",
                    "data":{
                        "instruction_key": sudo_instruction_key,
                        "qrcode_enc_key": qrcode_enc_key,
                        "expiration_time": expiration_time_seconds,
                        "qr_deeplink": qr_deeplink,
                        "qrcode_string": qr_deeplink,
                        "golden_numbers": golden_numbers,
                        "selected_golden_number": selected_golden_number,
                        "selected_confirmation_type": {
                            "id": random_confirmation_type.get('id'),
                            "flag": random_confirmation_type.get('flag'),
                            "name": random_confirmation_type.get('name'),
                            "description": random_confirmation_type.get('totp_app_description_str'),
                        },
                        "resolved_sudo_action_type": selected_sudo_action_type,
                        "cfg_organization_sudo_action_id": selected_org_sudo_action_id,
                        "delegated_validation": delegated_validation_payload,
                    }
                }
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            message = ResponseService.get_response_message(MessageCategory.ERRORS, "UNEXPECTED_ERROR", self.accept_language)
            format_error = format_exception("Error in initiate_sudo_action: ", e)
            self.app_debug_print(f"Error in initiate_sudo_action: {format_error}", True)
            raise HTTPException(status_code=500, detail=message)

    async def get_sudo_action_status(self, request: Request, instruction_key: str) -> Dict[str, Any]:
        """
        Get the status of a sudo action by instruction key
        """
        user_details = await AuthenticatedService.get_user_info(request, self.accept_language)
        user_id = user_details.get('id', None)

        if not user_id:
            message = ResponseService.get_response_message(MessageCategory.COMMON, "INVALID_USER_ACCOUNT", self.accept_language)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

        sudo_initiation_key = RedisKeys.format_key(
            RedisKeys.SUDO_ACTION,
            instruction_id=f"{user_id}_{instruction_key}"
        )

        saved_data = await AppRedisService.get_str_redis_value(sudo_initiation_key)

        if not saved_data: 
            return CustomJSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "success": False,
                    "message":ResponseService.get_response_message(MessageCategory.COMMON, "SUDO_ACTION_NOT_FOUND", self.accept_language) or "Sudo action not found or expired",
                    "data":None
                }
            )

        data = json.loads(saved_data)
        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "status": data.get('status'),
                "instruction_key": instruction_key,
                "url": data.get('url'),
                "selected_confirmation_type": data.get('selected_confirmation_type')
            }
        )

    async def validate_sudo_action(self, request: Request, instruction_key: str) -> Dict[str, Any]:
        """
        Validate/confirm a sudo action - marks status as validated
        """
        user_details = await AuthenticatedService.get_user_info(request, self.accept_language)
        user_id = user_details.get('id', None)

        if not user_id:
            message = ResponseService.get_response_message(MessageCategory.COMMON, "INVALID_USER_ACCOUNT", self.accept_language)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

        sudo_initiation_key = RedisKeys.format_key(
            RedisKeys.SUDO_ACTION,
            instruction_id=f"{user_id}_{instruction_key}"
        )

        saved_data = await AppRedisService.get_str_redis_value(sudo_initiation_key)

        if not saved_data:
            return CustomJSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "success": False,
                    "message":ResponseService.get_response_message(MessageCategory.COMMON, "SUDO_ACTION_NOT_FOUND", self.accept_language) or "Sudo action not found or expired",
                    "data":None
                }
            )

        data = json.loads(saved_data)
        data['status'] = 'validated'

        # Update with remaining TTL or set new expiration
        await AppRedisService.set_redis_value(
            sudo_initiation_key,
            json.dumps(data),
            60 * 5  # 5 minutes to complete the action after validation
        )

        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "status": "validated",
                "instruction_key": instruction_key,
                "url": data.get('url'),
                "message": ResponseService.get_response_message(MessageCategory.SUCCESS, "SUDO_ACTION_VALIDATED", self.accept_language) or "Sudo action validated successfully",
                "data":None
            }
        )

    async def cancel_sudo_action(self, request: Request, instruction_key: str) -> Dict[str, Any]:
        """
        Cancel a sudo action - removes from Redis
        """
        user_details = await AuthenticatedService.get_user_info(request, self.accept_language)
        user_id = user_details.get('id', None)

        if not user_id:
            message = ResponseService.get_response_message(MessageCategory.COMMON, "INVALID_USER_ACCOUNT", self.accept_language)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

        sudo_initiation_key = RedisKeys.format_key(
            RedisKeys.SUDO_ACTION,
            instruction_id=f"{user_id}_{instruction_key}"
        )

        await AppRedisService.remove_redis_value(sudo_initiation_key)

        return CustomJSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "message": ResponseService.get_response_message(MessageCategory.SUCCESS, "SUDO_ACTION_CANCELLED", self.accept_language) or "Sudo action cancelled successfully",
                "data":None
            }
        )

    async def check_qrcode_sudo_action(self, request: Request, payload: CheckQrcodeSudoActionRequest) -> Dict[str, Any]:
        """
        Check/validate a QR code for sudo action (called by Flutter app after scanning).
        Validates qrcode_enc_key against Redis, returns sudo action info + confirmation type.
        """
        try:
            instruction_key = payload.instruction_key
            user_id = payload.user_id
            qrcode_enc_key = payload.qrcode_enc_key

            if not instruction_key or not user_id or not qrcode_enc_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required fields: instruction_key, user_id, qrcode_enc_key"
                )

            # Build Redis key
            sudo_initiation_key = RedisKeys.format_key(
                RedisKeys.SUDO_ACTION,
                instruction_id=f"{user_id}_{instruction_key}"
            )

            self.app_debug_print(f" CHECK QRCODE: Looking up key >> : {sudo_initiation_key} ", True)

            # Fetch from Redis
            saved_data = await AppRedisService.get_str_redis_value(sudo_initiation_key)

            if not saved_data:
                return CustomJSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status_code": status.HTTP_404_NOT_FOUND,
                        "success": False,
                        "message": ResponseService.get_response_message(MessageCategory.COMMON, "SUDO_ACTION_NOT_FOUND", self.accept_language) or "Sudo action not found or expired",
                        "data": None
                    }
                )

            data = json.loads(saved_data)

            # Validate qrcode_enc_key matches
            stored_qrcode_enc_key = data.get('qrcode_enc_key', '')
            if self._normalize_qrcode_enc_key(stored_qrcode_enc_key) != self._normalize_qrcode_enc_key(qrcode_enc_key):
                self.app_debug_print(
                    " CHECK QRCODE: qrcode_enc_key mismatch "
                    f"(stored={stored_qrcode_enc_key}, received={qrcode_enc_key})",
                    True
                )
                return CustomJSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "status_code": status.HTTP_403_FORBIDDEN,
                        "success": False,
                        "message": "Invalid QR code validation key",
                        "data": None
                    }
                )

            delegated_access_error = await self._enforce_delegated_qrcode_validator_access(
                request=request,
                sudo_action_data=data,
                sudo_action_owner_user_id=user_id,
            )
            if delegated_access_error is not None:
                return delegated_access_error

            current_status = data.get('status')
            self.app_debug_print(
                f" CHECK QRCODE: current status={current_status} for key={sudo_initiation_key} ",
                True
            )

            # Accept pending-like states and already validated state to avoid
            # false negatives in retry/race scenarios.
            if current_status not in ('pending_verification', 'pending', 'validated'):
                return CustomJSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "status_code": status.HTTP_409_CONFLICT,
                        "success": False,
                        "message": "Sudo action is no longer available for QR verification",
                        "data": {
                            "status": current_status
                        }
                    }
                )

            message = "QR code validated successfully"
            if current_status == 'validated':
                message = "Sudo action already validated"

            self.app_debug_print(
                f" CHECK QRCODE: Valid QR code, returning confirmation type (status={current_status}) ",
                True
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": message,
                    "data": {
                        "instruction_key": instruction_key,
                        "user_id": user_id,
                        "status": current_status,
                        "selected_confirmation_type": data.get('selected_confirmation_type'),
                        "url": data.get('url'),
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            message = ResponseService.get_response_message(MessageCategory.ERRORS, "UNEXPECTED_ERROR", self.accept_language)
            format_error = format_exception("Error in check_qrcode_sudo_action: ", e)
            self.app_debug_print(f"Error in check_qrcode_sudo_action: {format_error}", True)
            raise HTTPException(status_code=500, detail=message)

    async def validate_qrcode_sudo_action(self, request: Request, payload: ValidateQrcodeSudoActionRequest) -> Dict[str, Any]:
        """
        Validate/confirm a sudo action via QR code (called by Flutter app after user confirms).
        Marks status as validated in Redis and sends WebSocket notification.
        """
        try:
            instruction_key = payload.instruction_key
            user_id = payload.user_id
            qrcode_enc_key = payload.qrcode_enc_key

            if not instruction_key or not user_id or not qrcode_enc_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required fields: instruction_key, user_id, qrcode_enc_key"
                )

            # Build Redis key
            sudo_initiation_key = RedisKeys.format_key(
                RedisKeys.SUDO_ACTION,
                instruction_id=f"{user_id}_{instruction_key}"
            )

            self.app_debug_print(f" VALIDATE QRCODE: Looking up key >> : {sudo_initiation_key} ", True)

            # Fetch from Redis
            saved_data = await AppRedisService.get_str_redis_value(sudo_initiation_key)

            if not saved_data:
                return CustomJSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status_code": status.HTTP_404_NOT_FOUND,
                        "success": False,
                        "message": ResponseService.get_response_message(MessageCategory.COMMON, "SUDO_ACTION_NOT_FOUND", self.accept_language) or "Sudo action not found or expired",
                        "data": None
                    }
                )

            data = json.loads(saved_data)

            # Validate qrcode_enc_key matches
            stored_qrcode_enc_key = data.get('qrcode_enc_key', '')
            if self._normalize_qrcode_enc_key(stored_qrcode_enc_key) != self._normalize_qrcode_enc_key(qrcode_enc_key):
                self.app_debug_print(
                    " VALIDATE QRCODE: qrcode_enc_key mismatch "
                    f"(stored={stored_qrcode_enc_key}, received={qrcode_enc_key})",
                    True
                )
                return CustomJSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "status_code": status.HTTP_403_FORBIDDEN,
                        "success": False,
                        "message": "Invalid QR code validation key",
                        "data": None
                    }
                )

            delegated_access_error = await self._enforce_delegated_qrcode_validator_access(
                request=request,
                sudo_action_data=data,
                sudo_action_owner_user_id=user_id,
            )
            if delegated_access_error is not None:
                return delegated_access_error

            # Mark as validated
            data['status'] = 'validated'

            # Update Redis with remaining TTL (5 minutes to complete the action)
            await AppRedisService.set_redis_value(
                sudo_initiation_key,
                json.dumps(data),
                60 * 5
            )

            self.app_debug_print(f" VALIDATE QRCODE: Sudo action validated via QR ", True)

            # Send WebSocket notification to the Angular frontend
            try:
                user_account_socket_hash = data.get('user_account_socket_hash', '')
                angular_consumer_hash = data.get('angular_consumer_hash', '')
                
                if user_account_socket_hash:
                    event_payload = {
                        "type": "instruction_response",
                        "custom_type": "sudoActionValidated",
                        "instruction_id": instruction_key,
                        "instruction_key": instruction_key,
                        "expected_action": EExpectedActionTypeFlag.SUDO_ACTION.value,
                        "success": True,
                        "status": "validated",
                    }
                    
                    if angular_consumer_hash:
                        # Send to the specific Angular app
                        await self._send_event_to_angular_app(
                            user_socket_hash=user_account_socket_hash,
                            angular_consumer_hash=angular_consumer_hash,
                            event_data=event_payload,
                        )
                    else:
                        # Fallback: try sending to all active connections for this user
                        from app.modules import active_connections
                        for conn_key in list(active_connections.keys()):
                            if conn_key.endswith(f"___{user_account_socket_hash}"):
                                await SecurityWebSocketService.send_event_to_client(conn_key, event_payload)
                    
                    self.app_debug_print(f" VALIDATE QRCODE: WebSocket notification sent to Angular ", True)
            except Exception as ws_error:
                self.app_debug_print(f" VALIDATE QRCODE: WebSocket notification failed: {ws_error} ", True)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": ResponseService.get_response_message(MessageCategory.SUCCESS, "SUDO_ACTION_VALIDATED", self.accept_language) or "Sudo action validated successfully via QR code",
                    "data": {
                        "instruction_key": instruction_key,
                        "status": "validated",
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            message = ResponseService.get_response_message(MessageCategory.ERRORS, "UNEXPECTED_ERROR", self.accept_language)
            format_error = format_exception("Error in validate_qrcode_sudo_action: ", e)
            self.app_debug_print(f"Error in validate_qrcode_sudo_action: {format_error}", True)
            raise HTTPException(status_code=500, detail=message)

    async def send_delegated_validation_otp(
        self,
        request: Request,
        payload: SendDelegatedValidationOtpRequest,
    ) -> Dict[str, Any]:
        """
        Send sudo validation OTP to a delegated validator contact (email/phone).
        Supports delegated and non-delegated flows.
        """
        try:
            instruction_key = str(payload.instruction_key or "").strip()
            if not instruction_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="instruction_key is required.",
                )

            user_details = await AuthenticatedService.get_user_info(
                request, self.accept_language
            )
            user_id = str((user_details or {}).get("id", "")).strip()
            if not user_id:
                message = ResponseService.get_response_message(
                    MessageCategory.COMMON, "INVALID_USER_ACCOUNT", self.accept_language
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message or "Invalid user account.",
                )

            sudo_initiation_key = RedisKeys.format_key(
                RedisKeys.SUDO_ACTION,
                instruction_id=f"{user_id}_{instruction_key}",
            )
            saved_data = await AppRedisService.get_str_redis_value(sudo_initiation_key)
            if not saved_data:
                return CustomJSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status_code": status.HTTP_404_NOT_FOUND,
                        "success": False,
                        "message": ResponseService.get_response_message(
                            MessageCategory.COMMON,
                            "SUDO_ACTION_NOT_FOUND",
                            self.accept_language,
                        )
                        or "Sudo action not found or expired",
                        "data": None,
                    },
                )

            sudo_action_data = json.loads(saved_data)
            current_status = str(sudo_action_data.get("status", "")).strip()
            if current_status == "validated":
                return CustomJSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "status_code": status.HTTP_409_CONFLICT,
                        "success": False,
                        "message": "Sudo action is already validated.",
                        "data": {
                            "status": current_status,
                        },
                    },
                )
            if current_status not in {"pending_verification", "pending"}:
                return CustomJSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "status_code": status.HTTP_409_CONFLICT,
                        "success": False,
                        "message": "Sudo action is no longer pending validation.",
                        "data": {
                            "status": current_status,
                        },
                    },
                )

            selected_confirmation_type = sudo_action_data.get(
                "selected_confirmation_type", {}
            ) or {}
            confirmation_flag = str(
                selected_confirmation_type.get("flag", "")
            ).strip()

            otp_channel = self._normalize_otp_channel(
                requested_channel=payload.channel,
                confirmation_flag=confirmation_flag,
            )
            if not otp_channel:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported OTP channel for this sudo action.",
                )

            expected_channel_from_flag = self._normalize_otp_channel(
                requested_channel=None,
                confirmation_flag=confirmation_flag,
            )
            if expected_channel_from_flag and expected_channel_from_flag != otp_channel:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"This sudo action expects '{expected_channel_from_flag}' OTP channel."
                    ),
                )

            delegated_validation = self._extract_delegated_validation_from_sudo_data(
                sudo_action_data
            )
            is_delegated_action = bool(
                delegated_validation.get("is_delegated_action", False)
            )
            requires_external_validator = bool(
                delegated_validation.get("requires_external_validator", False)
            )
            eligible_validators_raw = delegated_validation.get("eligible_validators", [])
            eligible_validators = (
                eligible_validators_raw
                if isinstance(eligible_validators_raw, list)
                else []
            )

            eligible_validator_user_ids = [
                str(user_id_value).strip()
                for user_id_value in (
                    delegated_validation.get("eligible_validator_user_ids", []) or []
                )
                if str(user_id_value).strip()
            ]
            if not eligible_validator_user_ids and eligible_validators:
                eligible_validator_user_ids = [
                    str(item.get("user_id", "")).strip()
                    for item in eligible_validators
                    if str(item.get("user_id", "")).strip()
                ]

            target_validator_user_id = str(
                payload.validator_user_id or ""
            ).strip()
            if is_delegated_action:
                if requires_external_validator and not target_validator_user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "validator_user_id is required for delegated external validation."
                        ),
                    )
                if not target_validator_user_id:
                    target_validator_user_id = user_id
                if eligible_validator_user_ids and target_validator_user_id not in set(
                    eligible_validator_user_ids
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Selected validator is not eligible for this delegated action.",
                    )
            else:
                target_validator_user_id = user_id

            selected_validator_preview = self._find_eligible_validator_by_user_id(
                eligible_validators=eligible_validators,
                target_user_id=target_validator_user_id,
            )
            target_validator_user = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={"filter___id": target_validator_user_id},
                user=user_details,
            )
            if not target_validator_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Selected validator account was not found.",
                )

            recipient_email = str(target_validator_user.get("email", "")).strip()
            recipient_phone_number = str(
                target_validator_user.get("phone_number", "")
            ).strip()

            otp_code = GeneratorService.generate_otp(length=6)
            otp_validity_seconds = 5 * 60
            now_utc = datetime.now(timezone.utc)
            expires_at = now_utc + timedelta(seconds=otp_validity_seconds)

            otp_delivery_result = await self._dispatch_sudo_contact_otp(
                channel=otp_channel,
                otp_code=otp_code,
                recipient_email=recipient_email,
                recipient_phone_number=recipient_phone_number,
            )

            delegated_validation["otp_request"] = {
                "validator_user_id": target_validator_user_id,
                "channel": otp_channel,
                "otp_code": otp_code,
                "attempts": 0,
                "max_attempts": 5,
                "sent_at": now_utc.isoformat(),
                "expires_at": expires_at.isoformat(),
                "otp_sent_to_masked": otp_delivery_result.get("masked_destination", ""),
            }
            delegated_validation["selected_validator_user_id"] = target_validator_user_id
            delegated_validation["selected_validation_channel"] = otp_channel
            delegated_validation["otp_requested"] = True
            delegated_validation["otp_sent_to_masked"] = otp_delivery_result.get(
                "masked_destination", ""
            )
            delegated_validation["otp_sent_at"] = now_utc.isoformat()
            delegated_validation["otp_expires_at"] = expires_at.isoformat()
            if selected_validator_preview:
                sanitized_preview = self._sanitize_delegated_validators_for_client(
                    [selected_validator_preview]
                )
                delegated_validation["selected_validator"] = (
                    sanitized_preview[0] if sanitized_preview else {}
                )

            sudo_action_data["delegated_validation"] = delegated_validation
            redis_expiry = self._resolve_sudo_redis_expiry_from_data(sudo_action_data)
            await AppRedisService.set_redis_value(
                sudo_initiation_key,
                json.dumps(sudo_action_data),
                redis_expiry,
            )

            response_data = {
                "instruction_key": instruction_key,
                "status": current_status,
                "channel": otp_channel,
                "validator_user_id": target_validator_user_id,
                "otp_sent_to_masked": otp_delivery_result.get("masked_destination", ""),
                "otp_expires_in_seconds": otp_validity_seconds,
                "otp_sent_at": now_utc.isoformat(),
                "otp_expires_at": expires_at.isoformat(),
                "delegated_validation": delegated_validation,
            }
            debug_otp_code = str(otp_delivery_result.get("debug_otp_code", "")).strip()
            if debug_otp_code:
                response_data["debug_otp_code"] = debug_otp_code

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": "Validation OTP sent successfully.",
                    "data": response_data,
                },
            )

        except HTTPException:
            raise
        except Exception as e:
            format_error = format_exception("Error in send_delegated_validation_otp: ", e)
            self.app_debug_print(
                f"Error in send_delegated_validation_otp: {format_error}", True
            )
            message = ResponseService.get_response_message(
                MessageCategory.ERRORS, "UNEXPECTED_ERROR", self.accept_language
            ) or "Unexpected error while sending validation OTP."
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)

    async def verify_delegated_validation_otp(
        self,
        request: Request,
        payload: VerifyDelegatedValidationOtpRequest,
    ) -> Dict[str, Any]:
        """Verify delegated OTP and mark sudo action as validated."""
        try:
            instruction_key = str(payload.instruction_key or "").strip()
            submitted_otp = str(payload.otp_code or "").strip()
            if not instruction_key or not submitted_otp:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="instruction_key and otp_code are required.",
                )

            user_details = await AuthenticatedService.get_user_info(
                request, self.accept_language
            )
            user_id = str((user_details or {}).get("id", "")).strip()
            if not user_id:
                message = ResponseService.get_response_message(
                    MessageCategory.COMMON, "INVALID_USER_ACCOUNT", self.accept_language
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message or "Invalid user account.",
                )

            sudo_initiation_key = RedisKeys.format_key(
                RedisKeys.SUDO_ACTION,
                instruction_id=f"{user_id}_{instruction_key}",
            )
            saved_data = await AppRedisService.get_str_redis_value(sudo_initiation_key)
            if not saved_data:
                return CustomJSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status_code": status.HTTP_404_NOT_FOUND,
                        "success": False,
                        "message": ResponseService.get_response_message(
                            MessageCategory.COMMON,
                            "SUDO_ACTION_NOT_FOUND",
                            self.accept_language,
                        )
                        or "Sudo action not found or expired",
                        "data": None,
                    },
                )

            sudo_action_data = json.loads(saved_data)
            current_status = str(sudo_action_data.get("status", "")).strip()
            if current_status == "validated":
                return CustomJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "success": True,
                        "message": "Sudo action already validated.",
                        "data": {
                            "instruction_key": instruction_key,
                            "status": "validated",
                            "delegated_validation": sudo_action_data.get(
                                "delegated_validation", {}
                            ),
                        },
                    },
                )
            if current_status not in {"pending_verification", "pending"}:
                return CustomJSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "status_code": status.HTTP_409_CONFLICT,
                        "success": False,
                        "message": "Sudo action is no longer pending validation.",
                        "data": {
                            "status": current_status,
                        },
                    },
                )

            delegated_validation = self._extract_delegated_validation_from_sudo_data(
                sudo_action_data
            )
            otp_request = delegated_validation.get("otp_request", {})
            if not isinstance(otp_request, dict) or not str(
                otp_request.get("otp_code", "")
            ).strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No active validation OTP request found.",
                )

            now_utc = datetime.now(timezone.utc)
            expires_at_raw = str(otp_request.get("expires_at", "")).strip()
            if expires_at_raw:
                expires_at_str = (
                    expires_at_raw
                    if expires_at_raw.endswith("+00:00")
                    else expires_at_raw.replace("Z", "+00:00")
                )
                expires_at = datetime.fromisoformat(expires_at_str)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if now_utc > expires_at:
                    delegated_validation.pop("otp_request", None)
                    delegated_validation["otp_requested"] = False
                    delegated_validation["otp_error"] = "expired"
                    sudo_action_data["delegated_validation"] = delegated_validation
                    await AppRedisService.set_redis_value(
                        sudo_initiation_key,
                        json.dumps(sudo_action_data),
                        self._resolve_sudo_redis_expiry_from_data(sudo_action_data),
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Validation OTP has expired. Please request a new one.",
                    )

            try:
                attempts = int(otp_request.get("attempts", 0))
            except (TypeError, ValueError):
                attempts = 0
            try:
                max_attempts = int(otp_request.get("max_attempts", 5))
            except (TypeError, ValueError):
                max_attempts = 5

            if attempts >= max_attempts:
                delegated_validation.pop("otp_request", None)
                delegated_validation["otp_requested"] = False
                delegated_validation["otp_error"] = "max_attempts"
                sudo_action_data["delegated_validation"] = delegated_validation
                await AppRedisService.set_redis_value(
                    sudo_initiation_key,
                    json.dumps(sudo_action_data),
                    self._resolve_sudo_redis_expiry_from_data(sudo_action_data),
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Maximum OTP attempts reached. Please request a new code.",
                )

            stored_otp = str(otp_request.get("otp_code", "")).strip()
            if submitted_otp != stored_otp:
                otp_request["attempts"] = attempts + 1
                delegated_validation["otp_request"] = otp_request
                delegated_validation["otp_requested"] = True
                sudo_action_data["delegated_validation"] = delegated_validation
                await AppRedisService.set_redis_value(
                    sudo_initiation_key,
                    json.dumps(sudo_action_data),
                    self._resolve_sudo_redis_expiry_from_data(sudo_action_data),
                )
                remaining_attempts = max(max_attempts - int(otp_request["attempts"]), 0)
                return CustomJSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "status_code": status.HTTP_403_FORBIDDEN,
                        "success": False,
                        "message": "Invalid OTP code.",
                        "data": {
                            "remaining_attempts": remaining_attempts,
                        },
                    },
                )

            # OTP is valid -> mark sudo action as validated
            sudo_action_data["status"] = "validated"
            delegated_validation.pop("otp_request", None)
            delegated_validation["otp_requested"] = False
            delegated_validation["otp_validated_at"] = now_utc.isoformat()
            delegated_validation["validated_by_otp"] = {
                "validator_user_id": str(
                    otp_request.get("validator_user_id", "")
                ).strip(),
                "channel": str(otp_request.get("channel", "")).strip(),
                "validated_at": now_utc.isoformat(),
                "otp_sent_to_masked": str(
                    otp_request.get("otp_sent_to_masked", "")
                ).strip(),
            }
            delegated_validation["otp_sent_to_masked"] = str(
                otp_request.get("otp_sent_to_masked", "")
            ).strip()
            delegated_validation["selected_validation_channel"] = str(
                otp_request.get("channel", "")
            ).strip()
            delegated_validation["selected_validator_user_id"] = str(
                otp_request.get("validator_user_id", "")
            ).strip()

            sudo_action_data["delegated_validation"] = delegated_validation
            await AppRedisService.set_redis_value(
                sudo_initiation_key,
                json.dumps(sudo_action_data),
                60 * 5,
            )

            # Notify Angular (best-effort)
            try:
                user_account_socket_hash = sudo_action_data.get(
                    "user_account_socket_hash", ""
                )
                angular_consumer_hash = sudo_action_data.get(
                    "angular_consumer_hash", ""
                )
                if user_account_socket_hash:
                    event_payload = {
                        "type": "instruction_response",
                        "custom_type": "sudoActionValidated",
                        "instruction_id": instruction_key,
                        "instruction_key": instruction_key,
                        "expected_action": EExpectedActionTypeFlag.SUDO_ACTION.value,
                        "success": True,
                        "status": "validated",
                    }
                    if angular_consumer_hash:
                        await self._send_event_to_angular_app(
                            user_socket_hash=user_account_socket_hash,
                            angular_consumer_hash=angular_consumer_hash,
                            event_data=event_payload,
                        )
            except Exception as ws_error:
                self.app_debug_print(
                    f"SUDO OTP VERIFY: WebSocket notification failed: {ws_error}",
                    True,
                )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "message": ResponseService.get_response_message(
                        MessageCategory.SUCCESS,
                        "SUDO_ACTION_VALIDATED",
                        self.accept_language,
                    )
                    or "Sudo action validated successfully",
                    "data": {
                        "instruction_key": instruction_key,
                        "status": "validated",
                        "delegated_validation": delegated_validation,
                    },
                },
            )

        except HTTPException:
            raise
        except Exception as e:
            format_error = format_exception("Error in verify_delegated_validation_otp: ", e)
            self.app_debug_print(
                f"Error in verify_delegated_validation_otp: {format_error}", True
            )
            message = ResponseService.get_response_message(
                MessageCategory.ERRORS, "UNEXPECTED_ERROR", self.accept_language
            ) or "Unexpected error while verifying delegated OTP."
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)

    # ═══════════════════════════════════════════════════════════════════════════
    # RELOAD SUDO ACTION
    # ═══════════════════════════════════════════════════════════════════════════
    async def reload_sudo_action(self, request: Request) -> Dict[str, Any]:
        """
        Reload/resend a sudo action with a new random confirmation type.
        Generates a new instruction, stores in Redis, sends event to mobile.
        """
        try:
            sent_instruction_id = request.query_params.get("instruction_id", None)
            if not sent_instruction_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="instruction_id query parameter is required"
                )

            user_details = await AuthenticatedService.get_user_info(request, self.accept_language)
            user_id = user_details.get('id', None)
            user_account_socket_hash = user_details.get('user_account_socket_hash', None)
            source_consumer_hash = await self._get_source_consumer_hash(request)

            if not user_id:
                message = ResponseService.get_response_message(MessageCategory.COMMON, "INVALID_USER_ACCOUNT", self.accept_language)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

            # Look up the original sudo action in Redis
            old_redis_key = RedisKeys.format_key(
                RedisKeys.SUDO_ACTION,
                instruction_id=f"{user_id}_{sent_instruction_id}"
            )
            saved_instruction = await AppRedisService.get_str_redis_value(str(old_redis_key).strip())

            if not saved_instruction:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Sudo action not found or expired"
                )

            saved_data = json.loads(saved_instruction)
            if saved_data.get('status') not in ('pending_verification', 'pending'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sudo action is no longer pending"
                )

            saved_delegated_validation = saved_data.get("delegated_validation", {})
            if not isinstance(saved_delegated_validation, dict):
                saved_delegated_validation = {}
            saved_delegated_payload = {
                "is_delegated_action": bool(
                    saved_delegated_validation.get("is_delegated_action", False)
                ),
                "current_user_can_validate": bool(
                    saved_delegated_validation.get("current_user_can_validate", True)
                ),
                "requires_external_validator": bool(
                    saved_delegated_validation.get("requires_external_validator", False)
                ),
                "eligible_validators": (
                    saved_delegated_validation.get("eligible_validators", [])
                    if isinstance(saved_delegated_validation.get("eligible_validators", []), list)
                    else []
                ),
                "selected_validator_user_id": str(
                    saved_delegated_validation.get("selected_validator_user_id", "")
                ).strip(),
                "selected_validation_channel": str(
                    saved_delegated_validation.get("selected_validation_channel", "")
                ).strip(),
                "otp_requested": bool(saved_delegated_validation.get("otp_requested", False)),
                "otp_sent_to_masked": str(
                    saved_delegated_validation.get("otp_sent_to_masked", "")
                ).strip(),
                "otp_sent_at": str(saved_delegated_validation.get("otp_sent_at", "")).strip(),
                "otp_expires_at": str(
                    saved_delegated_validation.get("otp_expires_at", "")
                ).strip(),
                "selected_validator": (
                    saved_delegated_validation.get("selected_validator", {})
                    if isinstance(saved_delegated_validation.get("selected_validator", {}), dict)
                    else {}
                ),
                "validated_by_otp": (
                    saved_delegated_validation.get("validated_by_otp", {})
                    if isinstance(saved_delegated_validation.get("validated_by_otp", {}), dict)
                    else {}
                ),
            }
            saved_delegated_validator_user_ids = [
                str(user_id_value).strip()
                for user_id_value in (
                    saved_delegated_validation.get("eligible_validator_user_ids", []) or []
                )
                if str(user_id_value).strip()
            ]
            saved_delegated_validator_socket_hashes = [
                str(socket_hash).strip()
                for socket_hash in (
                    saved_delegated_validation.get("eligible_validator_socket_hashes", []) or []
                )
                if str(socket_hash).strip()
            ]

            # Pick a new random confirmation type
            sudo_action_confirmation_types = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.RBAC_SUDO_ACTION_CONFIRMATION_TYPE,
                all_data=True,
                page=0,
                limit=10,
                output_data_type=OutputDataType.DEFAULT,
                accept_language=self.accept_language,
                query={"filter__is_activated": True},
                user=user_details,
            )
            if not sudo_action_confirmation_types:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No confirmation types found")

            loaded_types_debug = self._extract_confirmation_type_debug_data(sudo_action_confirmation_types)
            self.app_debug_print(
                f"SUDO_DEBUG: RELOAD loaded confirmation types ({len(loaded_types_debug)}): "
                f"{[(x.get('flag'), x.get('name')) for x in loaded_types_debug]}",
                True,
            )

            random_confirmation_type = random.choice(sudo_action_confirmation_types)
            self.app_debug_print(
                "SUDO_DEBUG: RELOAD selected confirmation type "
                f"id={random_confirmation_type.get('id')} "
                f"flag={random_confirmation_type.get('flag')} "
                f"name={random_confirmation_type.get('name')}",
                True,
            )
            confirmation_flag = random_confirmation_type.get('flag', '')

            # Generate new instruction key
            new_instruction_key = GeneratorService.generate_encryption_key()
            new_qrcode_enc_key = GeneratorService.generate_encryption_key()
            expiration_time_seconds = 2 * 60  # 2 minutes for reload

            new_redis_key = RedisKeys.format_key(
                RedisKeys.SUDO_ACTION,
                instruction_id=f"{user_id}_{new_instruction_key}"
            )

            # Build mobile event
            golden_numbers = []
            selected_golden_number = 0
            selected_golden_payload = None
            mobile_event_data = {
                "type": "instruction",
                "custom_type": confirmation_flag,
                "params": {
                    "instruction_key": new_instruction_key,
                    "instruction_id": new_instruction_key,
                    "expected_action": EExpectedActionTypeFlag.SUDO_ACTION.value,
                    "description": random_confirmation_type.get('totp_app_description_str', ''),
                }
            }

            if confirmation_flag == ESudoActionTypeFlag.GOLDEN_NUMBER.value:
                golden_numbers = GeneratorService.generate_random_golden_numbers(3)
                random_golden = random.choice(golden_numbers)
                selected_golden_number = random_golden.get('number', 0) if isinstance(random_golden, dict) else random_golden
                selected_golden_payload = random_golden if isinstance(random_golden, dict) else {"number": selected_golden_number}
                mobile_event_data["params"]["numbers"] = golden_numbers

            # Store new sudo action in Redis
            new_redis_data = {
                "url": saved_data.get('url', ''),
                "status": "pending_verification",
                "qrcode_enc_key": new_qrcode_enc_key,
                "expiration_time": expiration_time_seconds,
                "instruction_key": new_instruction_key,
                "user_id": user_id,
                "user_account_socket_hash": user_account_socket_hash,
                "angular_consumer_hash": source_consumer_hash,
                "selected_confirmation_type": {
                    "id": random_confirmation_type.get('id'),
                    "flag": confirmation_flag,
                    "name": random_confirmation_type.get('name'),
                    "description": random_confirmation_type.get('totp_app_description_str'),
                },
                "selected_golden_number": selected_golden_payload if confirmation_flag == ESudoActionTypeFlag.GOLDEN_NUMBER.value else 0,
                "resolved_sudo_action_type": saved_data.get("resolved_sudo_action_type", ""),
                "cfg_organization_sudo_action_id": saved_data.get("cfg_organization_sudo_action_id", ""),
                "sys_organization_id": saved_data.get("sys_organization_id", ""),
                "delegated_validation": {
                    **saved_delegated_payload,
                    "eligible_validator_user_ids": saved_delegated_validator_user_ids,
                    "eligible_validator_socket_hashes": saved_delegated_validator_socket_hashes,
                },
            }

            await AppRedisService.set_redis_value(new_redis_key, json.dumps(new_redis_data), expiration_time_seconds)
            # Remove old key
            await AppRedisService.remove_redis_value(old_redis_key)

            # Build QR deeplink
            qr_payload = json.dumps({
                "instruction_key": new_instruction_key,
                "user_id": user_id,
                "qrcode_enc_key": new_qrcode_enc_key,
            })
            encrypted_qr_payload = EncryptionService.aes_encrypt_for_mobile(qr_payload)
            qr_deeplink = f"sycamore://sudo/validate?data={quote(encrypted_qr_payload, safe='')}"

            # Send event to mobile apps
            merged_redis_info = {
                **new_redis_data,  # Preserve qrcode_enc_key/status/url and all sudo metadata
                **mobile_event_data,  # Keep websocket instruction payload for listeners
                "api_consumer_key": source_consumer_hash,
                "api_consumer_keys": await self._get_mobile_consumer_hashes(user_details=user_details),
                "instruction_id": new_instruction_key,
                "instruction_key": new_instruction_key,
                "expected_action": EExpectedActionTypeFlag.SUDO_ACTION.value,
                "custom_type": confirmation_flag,
                "type": "instruction",
                "params": {
                    **mobile_event_data.get("params", {}),
                    "api_consumer_key": source_consumer_hash,
                },
            }
            mobile_redis_data = {
                "redis_data_key": new_redis_key,
                "redis_data_info": merged_redis_info,
                "redis_expire_time": expiration_time_seconds,
            }

            target_socket_hashes: set[str] = set()
            if (
                saved_delegated_payload.get("is_delegated_action", False)
                and saved_delegated_payload.get("requires_external_validator", False)
            ):
                target_socket_hashes = {
                    str(socket_hash).strip()
                    for socket_hash in saved_delegated_validator_socket_hashes
                    if str(socket_hash).strip()
                }
            else:
                if user_account_socket_hash:
                    target_socket_hashes.add(str(user_account_socket_hash).strip())

            if not target_socket_hashes:
                self.app_debug_print(
                    "RELOAD: No eligible mobile socket hash found for push notification",
                    True,
                )

            for target_socket_hash in target_socket_hashes:
                try:
                    await self._send_event_to_mobile_apps(
                        user_socket_hash=target_socket_hash,
                        event_data=mobile_event_data,
                        redis_data=mobile_redis_data,
                        source_consumer_hash=source_consumer_hash,
                        user_details=user_details,
                    )
                except Exception as ws_error:
                    self.app_debug_print(
                        f"RELOAD: WebSocket push failed for {target_socket_hash}: {ws_error}",
                        True,
                    )

            message = ResponseService.get_response_message(MessageCategory.SUCCESS, "EVENT_SENT_SUCCESSFULLY", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "status_code": status.HTTP_201_CREATED,
                    "success": True,
                    "message": message or "Sudo action reloaded",
                    "data": {
                        "instruction_key": new_instruction_key,
                        "qr_deeplink": qr_deeplink,
                        "qrcode_string": qr_deeplink,
                        "expiration_time": expiration_time_seconds,
                        "golden_numbers": golden_numbers,
                        "selected_golden_number": selected_golden_number,
                        "selected_confirmation_type": {
                            "id": random_confirmation_type.get('id'),
                            "flag": confirmation_flag,
                            "name": random_confirmation_type.get('name'),
                            "description": random_confirmation_type.get('totp_app_description_str'),
                        },
                        "resolved_sudo_action_type": new_redis_data.get("resolved_sudo_action_type", ""),
                        "cfg_organization_sudo_action_id": new_redis_data.get("cfg_organization_sudo_action_id", ""),
                        "delegated_validation": saved_delegated_payload,
                    },
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            format_error = format_exception("Error in reload_sudo_action: ", e)
            self.app_debug_print(f"Error in reload_sudo_action: {format_error}", True)
            raise HTTPException(status_code=500, detail=str(e))

    # ═══════════════════════════════════════════════════════════════════════════
    # LOCK / UNLOCK SCREEN EVENTS
    # ═══════════════════════════════════════════════════════════════════════════
    async def send_lock_screen_event(self, request: Request, data: dict = None) -> Dict[str, Any]:
        """
        Send a lock screen event from mobile to Angular app.
        Persist lock status in Redis so a reconnecting web client is forced to lock.
        """
        try:
            user_details = await AuthenticatedService.get_user_info(request, self.accept_language)
            user_id = user_details.get('id', None)
            user_account_socket_hash = user_details.get('user_account_socket_hash', None)
            source_consumer_hash = await self._get_source_consumer_hash(request)
            mobile_consumer_hashes = await self._get_mobile_consumer_hashes(user_details=user_details)

            if not user_id or not user_account_socket_hash:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user account")

            instruction_id = GeneratorService.generate_encryption_key()
            event_data = {
                "type": "instruction",
                "custom_type": EExpectedActionTypeFlag.LOCK_SCREEN.value,
                "params": {
                    "instruction_id": instruction_id,
                    "expected_action": EExpectedActionTypeFlag.LOCK_SCREEN.value,
                    "description": "Lock screen instruction from mobile",
                }
            }

            # Persist lock marker for reconnect scenario.
            lock_status_key = RedisKeys.format_key(
                RedisKeys.PENDING_WEB_SCREEN_LOCK,
                user_socket_hash=user_account_socket_hash,
            )
            lock_status_data = {
                "status": "pending",
                "instruction_id": instruction_id,
                "expected_action": EExpectedActionTypeFlag.LOCK_SCREEN.value,
                "triggered_by_consumer_hash": source_consumer_hash,
                "mobile_consumer_hashes": mobile_consumer_hashes,
                "event_data": event_data,
            }
            await AppRedisService.set_redis_value(
                lock_status_key,
                json.dumps(lock_status_data),
                expiry=86400,  # 24h fallback window
            )

            # Send immediately to currently connected non-mobile consumers (web clients).
            from app.modules import active_connections
            delivered_count = 0
            for conn_key in list(active_connections.keys()):
                try:
                    if "___" not in conn_key:
                        continue

                    connection_consumer_hash, connection_user_hash = conn_key.split("___", 1)
                    if connection_user_hash != user_account_socket_hash:
                        continue

                    # Skip mobile clients to avoid sending lock instructions back to TOTP apps.
                    if connection_consumer_hash in mobile_consumer_hashes:
                        continue

                    await SecurityWebSocketService.send_event_to_client(conn_key, event_data, None)
                    delivered_count += 1
                except Exception as send_error:
                    self.app_debug_print(
                        f"send_lock_screen_event: failed to send to {conn_key}: {send_error}",
                        True
                    )

            # If sent live to at least one web client, clear fallback marker.
            if delivered_count > 0:
                await AppRedisService.remove_redis_value(lock_status_key)

            message = ResponseService.get_response_message(MessageCategory.SUCCESS, "EVENT_SENT_SUCCESSFULLY", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "status_code": status.HTTP_201_CREATED,
                    "success": True,
                    "message": message or "Lock screen event sent",
                    "data": {
                        "instruction_id": instruction_id,
                        "delivered_count": delivered_count,
                        "pending_for_reconnect": delivered_count == 0,
                    },
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"Error in send_lock_screen_event: {str(e)}", True)
            raise HTTPException(status_code=500, detail=str(e))

    async def send_unlock_screen_event(self, request: Request, data: dict = None) -> Dict[str, Any]:
        """
        Send an unlock screen event from Angular to mobile apps.
        Mobile needs to show local auth / biometric prompt, then respond.
        """
        try:
            user_details = await AuthenticatedService.get_user_info(request, self.accept_language)
            user_id = user_details.get('id', None)
            user_account_socket_hash = user_details.get('user_account_socket_hash', None)
            source_consumer_hash = await self._get_source_consumer_hash(request)

            if not user_id or not user_account_socket_hash:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user account")

            instruction_id = GeneratorService.generate_encryption_key()
            event_data = {
                "type": "instruction",
                "custom_type": ESudoActionTypeFlag.LOCAL_AUTH.value,
                "params": {
                    "instruction_id": instruction_id,
                    "expected_action": EExpectedActionTypeFlag.UNLOCK_SCREEN.value,
                    "description": "Unlock screen instructions",
                    "api_consumer_key": source_consumer_hash,
                }
            }

            instruction_key = RedisKeys.format_key(
                RedisKeys.ACTIVE_INSTRUCTION,
                expected_action=EExpectedActionTypeFlag.UNLOCK_SCREEN.value,
                instruction_id=instruction_id
            )
            redis_data = {
                "redis_data_key": instruction_key,
                "redis_data_info": {
                    **event_data,
                    "api_consumer_key": source_consumer_hash,
                    "api_consumer_keys": await self._get_mobile_consumer_hashes(user_details=user_details),
                    "status": "pending",
                    "instruction_id": instruction_id,
                },
                "redis_expire_time": 120,
            }

            # Send to all mobile consumers
            await self._send_event_to_mobile_apps(
                user_socket_hash=user_account_socket_hash,
                event_data=event_data,
                redis_data=redis_data,
                source_consumer_hash=source_consumer_hash,
                user_details=user_details,
            )

            message = ResponseService.get_response_message(MessageCategory.SUCCESS, "EVENT_SENT_SUCCESSFULLY", self.accept_language)
            return CustomJSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "status_code": status.HTTP_201_CREATED,
                    "success": True,
                    "message": message or "Unlock screen event sent",
                    "data": instruction_id,
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            self.app_debug_print(f"Error in send_unlock_screen_event: {str(e)}", True)
            raise HTTPException(status_code=500, detail=str(e))
