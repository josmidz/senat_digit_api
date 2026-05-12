"""Shared HMAC + auth + RBAC primitives for Senat-Digit live smokes.

The same handshake (HMAC-SHA256 sign, device pairing, MFA fork) is needed
by every per-role smoke. This module factors it out so a smoke script
becomes a one-page "what URLs should this role hit and how" file.

A smoke is parameterised by:

  - `consumer_flag`        — admin_web for greffier/sys_admin, mobile for senateur.
  - `username` + `password` — the demo user from dummy_seed.
  - `device_id`            — stable string; smoke pre-pairs it into Mongo.

Public surface (this is the entire API):

    smoke = Smoke(consumer_flag="senat_digit_mobile",
                  username="senateur1", password="Senat2026!",
                  device_id="smoke-test-senateur1")
    await smoke.bootstrap()            # consumer secret + device pre-pair
    await smoke.login()                # handles MFA fork; sets smoke.access_token
    status, body = smoke.call("GET", "/api/v1/list/session")
    smoke.assert_status((200,), "list session granted to sénateur")

Each smoke should fail-fast on the FIRST hard error so the failing step is
obvious in CI logs. Soft errors (one of N RBAC-cut assertions) tally up
into `smoke.fails` and are printed at the end.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Any
from urllib import error, request

from motor.motor_asyncio import AsyncIOMotorClient


API_HOST = os.environ.get("SMOKE_API_HOST", "http://localhost:8088")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("MONGO_DB_NAME", "senatDigitLocalDB")


def _server_device_hash(device_identifier: str) -> str:
    """Mirror `HashService.generate_base64_hash` — sha256(lowered+stripped)
    → urlsafe_b64encode → first 32 chars. Identical to the server-side
    hashing in `core/services/device/device_service.py::get_hashed_device_id`.
    """
    normalized = device_identifier.lower().strip()
    digest = hashlib.sha256(normalized.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode()[:32]


class Smoke:
    """One per-role smoke. Reusable across login + N RBAC assertions."""

    def __init__(
        self,
        *,
        consumer_flag: str,
        username: str,
        password: str,
        device_id: str,
        label: str | None = None,
    ):
        self.consumer_flag = consumer_flag
        self.username = username
        self.password = password
        self.device_id = device_id
        self.device_hash = _server_device_hash(device_id)
        self.label = label or username
        self.access_token: str | None = None
        self.consumer_secret: str | None = None
        self.user_id: str | None = None
        self.fails: int = 0
        self._db = AsyncIOMotorClient(MONGO_URI)[MONGO_DB]

    # ── HMAC sign ─────────────────────────────────────────────────
    def _sign(self, method: str, path_with_query: str, body: bytes) -> dict[str, str]:
        ts = str(int(time.time()))
        nonce = base64.urlsafe_b64encode(secrets.token_bytes(16)).rstrip(b"=").decode()
        body_sha = hashlib.sha256(body).hexdigest()
        canonical = "\n".join([
            self.consumer_flag, ts, nonce,
            method.upper(), path_with_query, body_sha,
        ])
        sig = hmac.new(
            (self.consumer_secret or "").encode(),
            canonical.encode(),
            hashlib.sha256,
        ).hexdigest()
        return {
            "X-Api-Consumer-Flag": self.consumer_flag,
            "X-Api-Timestamp": ts,
            "X-Api-Nonce": nonce,
            "X-Api-Signature": sig,
            # Server hashes `device_id` header when User-Agent == "Mobile"
            # (case-insensitive). Sending both makes the resulting hash
            # deterministic across runs.
            "device_id": self.device_id,
            "User-Agent": "Mobile",
        }

    def call(
        self, method: str, path_with_query: str, *,
        body: dict | None = None, with_auth: bool = True,
    ) -> tuple[int, Any]:
        """Make a signed HTTP call. Returns (status, body_obj)."""
        raw = b"" if body is None else json.dumps(body).encode()
        headers = self._sign(method, path_with_query, raw)
        headers["Content-Type"] = "application/json"
        headers["Accept-Language"] = "fr"
        if with_auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        req = request.Request(
            url=f"{API_HOST}{path_with_query}",
            data=raw if raw else None,
            method=method.upper(),
            headers=headers,
        )
        try:
            with request.urlopen(req, timeout=15) as resp:
                return resp.status, json.loads(resp.read() or b"null")
        except error.HTTPError as e:
            try:
                body_obj = json.loads(e.read() or b"null")
            except Exception:
                body_obj = {"raw": "<non-json>"}
            return e.code, body_obj

    # ── pre-flight: secret + device pre-pair ──────────────────────
    async def bootstrap(self) -> None:
        cons = await self._db["ref_api_consumer"].find_one({"flag": self.consumer_flag})
        if not cons or not cons.get("consumer_secret"):
            raise RuntimeError(
                f"consumer {self.consumer_flag!r} has no consumer_secret — "
                "re-run `bash/seeds/run.dummy-seed.local.sh`."
            )
        self.consumer_secret = cons["consumer_secret"]

        user = await self._db["sys_user"].find_one({"username": self.username})
        if not user:
            raise RuntimeError(
                f"user {self.username!r} missing — run dummy_seed first."
            )
        self.user_id = str(user["_id"])

        # Sweep stale rows from earlier (now-fixed) variants of this script
        # that pre-paired with the raw device_id instead of the hash.
        await self._db["cfg_user_device"].delete_many(
            {"sys_user_id": user["_id"], "device_id_str": self.device_id}
        )
        # Pre-pair the smoke device with status='allowed' (a valid
        # EUserDeviceStatus enum). Bypasses the legacy
        # /auth/initiate-device-activation OTP ceremony for dev-local.
        now = datetime.now(timezone.utc)
        await self._db["cfg_user_device"].update_one(
            {"sys_user_id": user["_id"], "device_id_str": self.device_hash},
            {
                "$set": {
                    "sys_user_id": user["_id"],
                    "device_id_str": self.device_hash,
                    "is_authenticated": True,
                    "is_activated": True,
                    "status": "allowed",
                    "sys_organization_id": user.get("sys_organization_id"),
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "soft_deleted": False,
                    "created_at": now,
                    "translations": {},
                    "multiple_validation_status": "APPROVED",
                    "multiple_validated_at": now,
                    "device_info": {"device_name": f"smoke-{self.label}", "platform": "smoke"},
                },
            },
            upsert=True,
        )

    # ── login + MFA fork ──────────────────────────────────────────
    async def login(self) -> None:
        status, body = self.call(
            "POST", "/api/v1/login/auth",
            body={"username": self.username, "password": self.password},
            with_auth=False,
        )
        if status != 200:
            raise RuntimeError(f"login {self.username} → HTTP {status}: {body}")

        token = body.get("access_token") if isinstance(body, dict) else None
        if not token:
            raise RuntimeError(f"login response missing access_token: {body}")

        if bool(body.get("redirect_to_mfa")):
            mfas = body.get("mfas") or []
            mfa_type = _flag(mfas[0]) if mfas else None
            if not mfa_type:
                mfa_type = _flag(body.get("default_mfa") or {})
            if not mfa_type:
                raise RuntimeError(f"MFA fork but no flag in mfas/default_mfa: {body}")
            self.access_token = token  # MFA_VERIFICATION token for MFA endpoints
            real_token = await self._resolve_mfa(mfa_type=mfa_type)
            if not real_token:
                raise RuntimeError("MFA resolution failed")
            self.access_token = real_token
        else:
            self.access_token = token

    async def _resolve_mfa(self, *, mfa_type: str) -> str | None:
        # 1. trigger OTP (GET, mfa_type as query param)
        status, body = self.call(
            "GET", f"/api/v1/auth/get-specific-otp?mfa_type={mfa_type}",
        )
        if status not in (200, 201):
            print(f"     ✗ get-specific-otp → {status}: {body}")
            return None

        # 2. read OTP from ops_user_login_history (no SMS/email in dev)
        otp = await self._read_otp()
        if not otp:
            print(f"     ✗ no OTP in ops_user_login_history for user_id={self.user_id}")
            return None

        # 3. validate OTP (POST, mfa_type query, body {otp})
        status, body = self.call(
            "POST", f"/api/v1/auth/validate-otp?mfa_type={mfa_type}",
            body={"otp": otp},
        )
        if status != 200:
            print(f"     ✗ validate-otp → {status}: {body}")
            return None
        return body.get("access_token") if isinstance(body, dict) else None

    async def _read_otp(self) -> str | None:
        from bson import ObjectId
        cur = self._db["ops_user_login_history"].find(
            {"sys_user_id": ObjectId(self.user_id), "otp": {"$ne": None, "$exists": True}}
        ).sort("updated_at", -1).limit(1)
        rows = await cur.to_list(length=1)
        if rows:
            return rows[0].get("otp")
        # fall back to string-id form (some seeds store as str)
        cur = self._db["ops_user_login_history"].find(
            {"sys_user_id": self.user_id, "otp": {"$ne": None, "$exists": True}}
        ).sort("updated_at", -1).limit(1)
        rows = await cur.to_list(length=1)
        return rows[0].get("otp") if rows else None

    # ── assertion helper ──────────────────────────────────────────
    def assert_status(
        self,
        actual: int,
        allowed: tuple[int, ...],
        desc: str,
    ) -> bool:
        ok = actual in allowed
        marker = "✓" if ok else "✗"
        print(f"  {marker} {desc}: HTTP {actual} (expected {allowed})")
        if not ok:
            self.fails += 1
        return ok


def _flag(entry: Any) -> str | None:
    """Extract the canonical MFA flag string from a `mfas[i]` entry.

    Backend wraps it in a display-value envelope; the real value lives at
    `entry["flag"]["real_value"]` (e.g. "email", "phone_number").
    """
    if isinstance(entry, dict):
        f = entry.get("flag")
        if isinstance(f, dict):
            return f.get("real_value")
        if isinstance(f, str):
            return f
    return None
