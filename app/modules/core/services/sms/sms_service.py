from typing import Optional
import requests
import asyncio
import httpx
import re

from concurrent.futures import ThreadPoolExecutor
from app.modules.core.configs.config import settings
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.services.debug.debug_service import DebugService

class SmsService:
    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.sms_sender_id = settings.SMS_SENDER_ID
        self.sms_post_url = settings.SMS_POST_URL
        self.headers = {"Authorization": f"Bearer {settings.SMS_TOKEN}"}
        self.accept_language = accept_language
        self.executor = ThreadPoolExecutor(max_workers=3)  # Limit concurrent SMS sending

    def send_sms(self, phone_number: str, message: str):
        payload = {
            "dest_type": "singleton",
            "pending_type": 0,
            "message": message,
            "singleton": phone_number,
            "senderid": self.sms_sender_id,
        }
        try:
            response = requests.post(self.sms_post_url, json=payload, headers=self.headers)
            response.raise_for_status()
            print(f"SMS sent successfully to {phone_number}.")
        except Exception as e:
            print(f"Failed to send SMS: {e}")
            raise

    async def send_sms_async(self, phone_number: str, message: str):
        """Async version of send_sms that runs in a thread pool"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self.send_sms, phone_number, message)
            return True
        except Exception as e:
            DebugService.app_debug_print(f"Failed to send SMS async: {e}")
            raise

    async def send_sms_httpx_async(self, phone_number: str, message: str, sender_id: Optional[str] = "Digi public"):
        """Send SMS using the new Lisoloo LISOLOO implementation (fully async).

        - Uses LISOLOO_API_URL (fallback to lisoloo.com) with APIKEY headers
        - Payload keys: from, to (international without +/00), message, type, dlr
        - Truncates sender_id to 11 characters as per provider constraints
        """
        # Read LISOLOO settings
        lisoloo_api_key = getattr(settings, "LISOLOO_API_KEY", None)
        lisoloo_api_url = getattr(settings, "LISOLOO_API_URL", "https://dev.apps.api.bloonio.com/api/v1/lisoloo/sms-api/send")

        if not lisoloo_api_key or not lisoloo_api_url:
            DebugService.app_debug_print("LISOLOO credentials not configured (LISOLOO_API_KEY/LISOLOO_API_URL)", True)
            raise RuntimeError("LISOLOO credentials not configured")

        # Sanitize and format phone number: digits only, trim leading 00 or +
        original_number = phone_number
        cleaned = re.sub(r"\D", "", original_number or "")
        if cleaned.startswith("00"):
            cleaned = cleaned[2:]
        # Note: we assume caller provides an international number
        if not cleaned:
            raise ValueError("Invalid phone number provided")

        # Sender ID: passed-in or default; truncate to max 11 chars
        sender = (sender_id or self.sms_sender_id or "Digi Public")[:11]

        payload = { 
            "recipients": [f"{cleaned}"],
            "sender_id": sender,
            "message": message
        }
        print(f"Sending SMS to {cleaned} via Lisoloo")
        print(f"Sending SMS payload {payload} via Lisoloo")
        headers = {
            "Content-Type": "application/json",
            "app-key": lisoloo_api_key,
        }
 

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    resp = await client.post(lisoloo_api_url, json=payload, headers=headers)
                except httpx.ConnectError:
                    if not lisoloo_api_url:
                        raise
                    # Try backup URL
                    resp = await client.post(lisoloo_api_url, json=payload, headers=headers)

                # Handle HTTP status
                resp.raise_for_status()

                # Best-effort JSON inspection (not strictly required to succeed)
                try:
                    data = resp.json()
                    DebugService.app_debug_print(f"Lisoloo response: {data}", True)
                except Exception:
                    DebugService.app_debug_print("Lisoloo response not JSON or parsing failed", True)

                DebugService.app_debug_print(f"SMS sent successfully to {original_number} via Lisoloo", True)
                return True
        except Exception as e:
            DebugService.app_debug_print(f"Failed to send SMS via Lisoloo: {e}", True)
            raise

    async def lisoloo_send_sms(self, phone_number: str, message: str, sender_id: Optional[str] = "Digi public"):
        """Send SMS via Lisoloo SMS API (fully async).

        Uses LISOLOO_API_URL with app-key header authentication.
        Payload: {"to": ["+<number>"], "message": "..."}

        Settings required:
          - LISOLOO_API_KEY : your Lisoloo app key
          - LISOLOO_API_URL : API base URL (default: https://dev.apps.api.bloonio.com/api/v1/lisoloo/sms-api)
        """
        lisoloo_api_key = getattr(settings, "LISOLOO_API_KEY", None)
        lisoloo_api_url = getattr(settings, "LISOLOO_API_URL", "https://dev.apps.api.bloonio.com/api/v1/lisoloo/sms-api")

        if not lisoloo_api_key or not lisoloo_api_url:
            DebugService.app_debug_print("LISOLOO credentials not configured (LISOLOO_API_KEY/LISOLOO_API_URL)", True)
            raise RuntimeError("LISOLOO credentials not configured")

        # Sanitize phone number: digits only, trim leading 00 or +
        original_number = phone_number
        cleaned = re.sub(r"\D", "", original_number or "")
        if cleaned.startswith("00"):
            cleaned = cleaned[2:]
        if not cleaned:
            raise ValueError("Invalid phone number provided")

        payload = {
            "to": [f"+{cleaned}"],
            "message": message,
            "sender_id":sender_id,
        }
        headers = {
            "app-key": lisoloo_api_key,
            "Content-Type": "application/json",
        }

        DebugService.app_debug_print(f"Sending SMS to +{cleaned} via Lisoloo", True)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{lisoloo_api_url}/send", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                DebugService.app_debug_print(f"Lisoloo response: {data}", True)
                DebugService.app_debug_print(
                    f"SMS sent to {original_number} via Lisoloo — message_id={data.get('data', {}).get('message_id')}",
                    True,
                )
                return data
        except Exception as e:
            DebugService.app_debug_print(f"Failed to send SMS via Lisoloo: {e}", True)
            raise

    async def send_sms_emess_async(
        self,
        phone_number: str,
        message: str,
        sms_type: str = "standard",
        keep_diacritics: bool = False,
    ):
        """Send SMS via the Emess (emess.cd) provider (fully async).

        Flow:
          1. POST /api/v0/auth/token  →  obtain a short-lived Bearer JWT
          2. POST /api/v0/sms/send   →  deliver the message

        Settings required (config.py / .env):
          - EMESS_APP_ID      : your Emess application ID
          - EMESS_SECRET_KEY  : your Emess secret key
          - EMESS_API_URL     : base URL (default: https://emess.cd)

        Args:
            phone_number:    Recipient phone number (international format recommended).
            message:         SMS body text.
            sms_type:        Message priority — "critical", "standard" (default), or "bulk".
            keep_diacritics: Whether to preserve accent characters (default False).
        """
        app_id = getattr(settings, "EMESS_APP_ID", "")
        secret_key = getattr(settings, "EMESS_SECRET_KEY", "")
        base_url = getattr(settings, "EMESS_API_URL", "https://emess.cd").rstrip("/")

        if not app_id or not secret_key:
            DebugService.app_debug_print(
                "Emess credentials not configured (EMESS_APP_ID / EMESS_SECRET_KEY)", True
            )
            raise RuntimeError("Emess credentials not configured")

        async with httpx.AsyncClient(timeout=60.0) as client:
            # ── Step 1: authenticate ──────────────────────────────────────
            try:
                auth_resp = await client.post(
                    f"{base_url}/api/v0/auth/token",
                    json={"app_id": app_id, "secret_key": secret_key},
                    headers={"Content-Type": "application/json"},
                )
                auth_resp.raise_for_status()
                DebugService.app_debug_print(f"Emess authentication response : {auth_resp}", True)
                token = auth_resp.json().get("token") or auth_resp.json().get("access_token")
                if not token:
                    raise RuntimeError(f"Emess auth response missing token: {auth_resp.text}")
            except Exception as e:
                DebugService.app_debug_print(f"Emess authentication failed: {e}", True)
                raise

            # ── Step 2: send SMS ──────────────────────────────────────────
            try:
                sms_resp = await client.post(
                    f"{base_url}/api/v0/sms/send",
                    json={
                        "number": phone_number,
                        "message": message,
                        "type": sms_type,
                        "keepDiacritics": keep_diacritics,
                    },
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {token}",
                    },
                )
                sms_resp.raise_for_status()
                data = sms_resp.json()
                DebugService.app_debug_print(
                    f"Emess SMS sent to {phone_number} — id={data.get('id')} batch={data.get('batchId')}", True
                )
                return data
            except Exception as e:
                DebugService.app_debug_print(f"Failed to send SMS via Emess: {e}", True)
                raise

    def send_sms_background(self, phone_number: str, message: str):
        """Background task method for sending SMS without blocking the request"""
        try:
            DebugService.app_debug_print(f"Starting background SMS send to {phone_number}", True)
            self.send_sms(phone_number, message)
            DebugService.app_debug_print(f"Background SMS sent successfully to {phone_number}", True)
        except Exception as e:
            DebugService.app_debug_print(f"Failed to send background SMS to {phone_number}: {e}", True)
            # Don't raise here as this is a background task
