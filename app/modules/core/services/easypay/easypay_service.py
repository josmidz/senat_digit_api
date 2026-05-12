import asyncio
import json
import time
from collections.abc import Mapping
from typing import Any, Dict, Optional

import httpx
from pydantic import ValidationError

from app.modules.core.configs.config import settings
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.redis.redis_service import AppRedisService
from app.modules.core.services.easypay.easypay_schema import (
    EasypayAuthData,
    EasypayBalanceData,
    EasypayCallbackPayload,
    EasypayCollectionData,
    EasypayCollectionRequest,
    EasypayErrorData,
    EasypayResponseEnvelope,
    EasypayStatusData,
    EasypayStatusRequest,
)


class EasypayServiceError(Exception):
    def __init__(
        self,
        message: str,
        code: Optional[int] = None,
        status_code: Optional[int] = None,
        endpoint: Optional[str] = None,
        response: Optional[Mapping[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.endpoint = endpoint
        self.response = response or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "code": self.code,
            "status_code": self.status_code,
            "endpoint": self.endpoint,
            "response": dict(self.response),
        }


class EasypayConfigurationError(EasypayServiceError):
    pass


class EasypayAPIError(EasypayServiceError):
    pass


class EasypayHTTPError(EasypayServiceError):
    pass


class EasypayService(DebugService):
    AUTH_ENDPOINT = "auth"
    COLLECTIONS_ENDPOINT = "collections"
    STATUS_ENDPOINT = "status"
    BALANCE_ENDPOINT = "balance"
    TOKEN_EXPIRED_CODE = 3009
    TOKEN_CACHE_KEY = "easypay:bearer_token"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        token_cache_seconds: Optional[int] = None,
        use_redis_cache: Optional[bool] = None,
        max_retries: Optional[int] = None,
        accept_language: Optional[str] = DEFAULT_LANGUAGE,
    ):
        super().__init__(accept_language)
        self.api_key = (api_key if api_key is not None else settings.EASYPAY_API_KEY).strip()
        self.base_url = self._normalize_base_url(base_url or settings.EASYPAY_BASE_URL)
        self.timeout_seconds = timeout_seconds or settings.EASYPAY_TIMEOUT_SECONDS
        self.token_cache_seconds = int(token_cache_seconds or settings.EASYPAY_TOKEN_CACHE_SECONDS)
        self.use_redis_cache = settings.EASYPAY_USE_REDIS_TOKEN_CACHE if use_redis_cache is None else use_redis_cache
        self.max_retries = max(0, int(max_retries if max_retries is not None else settings.EASYPAY_MAX_RETRIES))
        self._token: Optional[str] = None
        self._token_expires_at = 0.0

    async def authenticate(self, force_refresh: bool = False) -> EasypayAuthData:
        if not force_refresh:
            cached_token = await self.get_cached_token()
            if cached_token:
                return EasypayAuthData(token=cached_token)

        self._ensure_configured()
        response = await self._send_post(
            self.AUTH_ENDPOINT,
            headers={"Authorization": f"Basic {self.api_key}"},
        )
        data = response.get("data") or {}
        token = str(data.get("token") or "").strip()
        if not token:
            raise EasypayAPIError(
                "Easypay authentication response is missing token",
                endpoint=self.AUTH_ENDPOINT,
                response=response,
            )

        await self.cache_token(token)
        return EasypayAuthData(token=token)

    async def get_token(self, force_refresh: bool = False) -> str:
        auth_data = await self.authenticate(force_refresh=force_refresh)
        return auth_data.token

    async def get_cached_token(self) -> Optional[str]:
        if self._token and self._token_expires_at > time.monotonic():
            return self._token

        if not self.use_redis_cache:
            return None

        try:
            cached = await AppRedisService.get_str_redis_value(self.TOKEN_CACHE_KEY, use_env_prefix=True)
            if not cached:
                return None
            token = self._extract_cached_token(cached)
            if token:
                self._set_memory_token(token)
            return token
        except Exception as exc:
            DebugService.app_debug_print(f"Easypay token cache read failed: {exc}", True)
            return None

    async def cache_token(self, token: str) -> None:
        self._set_memory_token(token)

        if not self.use_redis_cache:
            return

        try:
            payload = json.dumps({"token": token}, separators=(",", ":"))
            await AppRedisService.set_redis_value(
                self.TOKEN_CACHE_KEY,
                payload,
                expiry=self.token_cache_seconds,
                use_env_prefix=True,
            )
        except Exception as exc:
            DebugService.app_debug_print(f"Easypay token cache write failed: {exc}", True)

    async def clear_cached_token(self) -> None:
        self._token = None
        self._token_expires_at = 0.0
        if not self.use_redis_cache:
            return
        try:
            await AppRedisService.remove_redis_value(self.TOKEN_CACHE_KEY, use_env_prefix=True)
        except Exception as exc:
            DebugService.app_debug_print(f"Easypay token cache clear failed: {exc}", True)

    async def initiate_collection(
        self,
        reference_id: str,
        phone: str,
        currency: str,
        amount: float,
    ) -> EasypayCollectionData:
        payload = EasypayCollectionRequest(
            referenceId=reference_id,
            phone=phone,
            currency=currency,
            amount=amount,
        ).model_dump(by_alias=True)

        response = await self._send_authenticated_post(self.COLLECTIONS_ENDPOINT, payload=payload)
        return EasypayCollectionData.model_validate(response.get("data") or {})

    async def collect(
        self,
        reference_id: str,
        phone: str,
        currency: str,
        amount: float,
    ) -> EasypayCollectionData:
        return await self.initiate_collection(reference_id, phone, currency, amount)

    async def check_status(self, reference_id: str) -> EasypayStatusData:
        payload = EasypayStatusRequest(referenceId=reference_id).model_dump(by_alias=True)
        response = await self._send_authenticated_post(self.STATUS_ENDPOINT, payload=payload)
        return EasypayStatusData.model_validate(response.get("data") or {})

    async def get_status(self, reference_id: str) -> EasypayStatusData:
        return await self.check_status(reference_id)

    async def check_balance(self) -> EasypayBalanceData:
        response = await self._send_authenticated_post(self.BALANCE_ENDPOINT)
        return EasypayBalanceData.model_validate(response.get("data") or {})

    async def get_balance(self) -> EasypayBalanceData:
        return await self.check_balance()

    def parse_callback_payload(self, payload: Mapping[str, Any]) -> EasypayCallbackPayload:
        try:
            return EasypayCallbackPayload.model_validate(payload)
        except ValidationError as exc:
            raise EasypayServiceError("Invalid Easypay callback payload", response={"errors": exc.errors()}) from exc

    @staticmethod
    def build_callback_success_response(message: str = "Payment processed successfully") -> Dict[str, Any]:
        return {"success": 1, "message": message}

    @staticmethod
    def build_callback_error_response(message: str = "Invalid callback payload") -> Dict[str, Any]:
        return {"success": 0, "errormsg": message}

    async def _send_authenticated_post(
        self,
        endpoint: str,
        payload: Optional[Mapping[str, Any]] = None,
        retry_on_expired_token: bool = True,
    ) -> Dict[str, Any]:
        token = await self.get_token(True)
        try:
            return await self._send_post(endpoint, headers=self._bearer_headers(token), payload=payload)
        except EasypayAPIError as exc:
            if retry_on_expired_token and exc.code == self.TOKEN_EXPIRED_CODE:
                await self.clear_cached_token()
                refreshed_token = await self.get_token(force_refresh=True)
                return await self._send_post(
                    endpoint,
                    headers=self._bearer_headers(refreshed_token),
                    payload=payload,
                )
            raise

    async def _send_post(
        self,
        endpoint: str,
        headers: Mapping[str, str],
        payload: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    request_kwargs: Dict[str, Any] = {"headers": dict(headers)}
                    if payload is not None:
                        request_kwargs["json"] = dict(payload)
                    response = await client.post(url, **request_kwargs)
                    self.app_debug_print(f"[_send_post] easypay : {response} : {response}",True)
                return self._parse_response(endpoint, response)
            except httpx.RequestError as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                await asyncio.sleep(0.25 * (attempt + 1))

        raise EasypayHTTPError(
            f"Easypay request failed: {last_error}",
            endpoint=endpoint,
        )

    def _parse_response(self, endpoint: str, response: httpx.Response) -> Dict[str, Any]:
        body = self._decode_json_response(endpoint, response)
        envelope = self._build_envelope(body)

        if response.status_code >= 400:
            error = envelope.error or EasypayErrorData(message=response.reason_phrase)
            raise EasypayAPIError(
                error.message or response.reason_phrase,
                code=error.code,
                status_code=response.status_code,
                endpoint=endpoint,
                response=body,
            )

        if self._is_unsuccessful(envelope.success):
            error = envelope.error or EasypayErrorData(message="Easypay request failed")
            raise EasypayAPIError(
                error.message or "Easypay request failed",
                code=error.code,
                status_code=response.status_code,
                endpoint=endpoint,
                response=body,
            )

        return body

    def _decode_json_response(self, endpoint: str, response: httpx.Response) -> Dict[str, Any]:
        try:
            body = response.json()
            self.app_debug_print(f"[_decode_json_response] : body : {body}",True)
        except ValueError as exc:
            self.app_debug_print(f"[_decode_json_response] : err : {str(exc)}",True)
            raise EasypayAPIError(
                "Easypay response is not valid JSON",
                status_code=response.status_code,
                endpoint=endpoint,
                response={"text": response.text},
            ) from exc

        if not isinstance(body, dict):
            raise EasypayAPIError(
                "Easypay response must be a JSON object",
                status_code=response.status_code,
                endpoint=endpoint,
                response={"body": body},
            )
        return body

    def _build_envelope(self, body: Mapping[str, Any]) -> EasypayResponseEnvelope:
        try:
            return EasypayResponseEnvelope.model_validate(body)
        except ValidationError:
            error = None
            if isinstance(body.get("error"), Mapping):
                error = EasypayErrorData.model_validate(body.get("error"))
            return EasypayResponseEnvelope(
                success=body.get("success", 1),
                data=body.get("data", body),
                error=error,
            )

    def _build_url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint.strip('/')}"

    def _ensure_configured(self) -> None:
        if not self.api_key:
            raise EasypayConfigurationError("EASYPAY_API_KEY is not configured")
        if not self.base_url:
            raise EasypayConfigurationError("EASYPAY_BASE_URL is not configured")

    def _set_memory_token(self, token: str) -> None:
        self._token = token
        self._token_expires_at = time.monotonic() + max(1, self.token_cache_seconds)

    def _extract_cached_token(self, cached: str) -> Optional[str]:
        try:
            data = json.loads(cached)
            token = data.get("token")
            return str(token).strip() if token else None
        except Exception:
            token = str(cached or "").strip()
            return token or None

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        return str(base_url or "").strip().rstrip("/")

    @staticmethod
    def _bearer_headers(token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _is_unsuccessful(success: Any) -> bool:
        if isinstance(success, str):
            return success.strip().lower() in {"0", "false"}
        return success in (0, False)
