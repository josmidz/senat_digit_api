"""Senat-Digit auth_device controller.

Thin wrapper around the existing `AuthController` that exposes only the four
MVP auth endpoints with clean Senat-shaped request/response contracts:

  POST /login/auth        — `senat_login`
  POST /refresh/auth      — `senat_refresh`
  PATCH /patch/password   — `senat_patch_password`
  POST /verify/device     — `senat_verify_device`

The underlying services (token issuance, password verification, device pairing,
audit logging, RLS) are reused from the system core. We do not reimplement them.

Audit hooks (per `_planning/_followup_batch.md` F3): LOGIN, LOGIN_FAIL and
PASSWORD_CHANGE are emitted at the wrapper level so the chain captures every
sénateur-side authentication event without touching the legacy 6k-line
auth_controller.
"""

from typing import Any, Optional

from fastapi import HTTPException, Request

from app.modules.auth.api.controller.auth_controller import AuthController
from app.modules.auth.schemas.auth_schema import LoginRequest
from app.modules.auth.schemas.senat_auth_schema import (
    SenatChangePinRequest,
    SenatFcmTokenRegisterRequest,
    SenatForgotPasswordCompleteRequest,
    SenatForgotPasswordStartRequest,
    SenatForgotPasswordVerifyRequest,
    SenatLoginRequest,
    SenatPatchPasswordRequest,
    SenatSetPinRequest,
    SenatSetSecurityQuestionsRequest,
    SenatVerifyDeviceRequest,
    SenatVerifyPinRequest,
)
from app.modules.auth.services.password.password_service import PasswordService
from app.modules.auth.services.pin.pin_service import (
    PinAlreadySetException,
    PinInvalidException,
    PinLockedException,
    PinNotSetException,
    PinService,
)
from app.modules.auth.services.security_questions.security_questions_service import (
    SecurityQuestionsMismatchException,
    SecurityQuestionsNotSetException,
    SecurityQuestionsService,
)
from app.modules.auth.services.token.token_service import TokenService
from app.modules.core.enums.type_enum import (
    EJWTTokenType,
    EUserDeviceStatus,
    OutputDataType,
)
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.generic.generic_services import GenericService


class SenatAuthController:
    """Senat-Digit-shaped auth handlers. Delegates to AuthController for core flows."""

    def __init__(self, accept_language: Optional[str] = None):
        self.accept_language = accept_language or DEFAULT_LANGUAGE
        self._auth = AuthController(self.accept_language)
        self._generic = GenericService(self.accept_language)

    # ---- internal helpers (audit) ----
    async def _resolve_user_for_audit(self, username: str) -> Optional[dict]:
        """Look up the SysUser row for a username so we can emit audit events
        with `actor_user_id` + `sys_organization_id` populated. Returns None
        if the username does not match any user — in that case LOGIN_FAIL is
        emitted without an actor_user_id (and the audit chain skips the row,
        since `sys_organization_id` is required)."""
        try:
            row = await self._generic.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__username": str(username).lower().strip()},
                _skip_rls=True,
            )
            return row if isinstance(row, dict) else None
        except Exception:
            return None

    @staticmethod
    def _response_status_code(result: Any) -> int:
        """Extract a status code from a controller response that may be a
        FastAPI `Response` subclass (CustomJSONResponse) or a plain dict."""
        sc = getattr(result, "status_code", None)
        if sc is None and isinstance(result, dict):
            sc = result.get("status_code")
        return int(sc) if isinstance(sc, (int, str)) and str(sc).isdigit() else 200

    async def _emit_login_audit(
        self,
        request: Request,
        username: str,
        event_type_name: str,
        details: Optional[dict] = None,
    ) -> None:
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )

            user_row = await self._resolve_user_for_audit(username)
            if user_row is None or not user_row.get("sys_organization_id"):
                # Cannot emit without an org — silently skip (e.g. wrong
                # username on first attempt). The IP/UA can still be picked
                # up by the rate-limiter middleware logs.
                return
            consumer_flag = request.headers.get("X-Api-Consumer-Flag")
            device_id = request.headers.get("X-Device-Id")
            await AuditChainService(self.accept_language).emit(
                sys_organization_id=user_row["sys_organization_id"],
                event_type=getattr(EAuditEventType, event_type_name),
                actor_user_id=user_row.get("id"),
                actor_api_consumer_flag=consumer_flag,
                actor_device_id_str=device_id,
                details={"username": username.lower().strip(), **(details or {})},
            )
        except Exception:
            pass

    async def _emit_password_change_audit(self, request: Request) -> None:
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )

            user_id = getattr(request.state, "user_id", None)
            if user_id is None:
                return
            user_row = await self._generic.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__id": str(user_id)},
                _skip_rls=True,
            )
            if not isinstance(user_row, dict) or not user_row.get("sys_organization_id"):
                return
            consumer_flag = request.headers.get("X-Api-Consumer-Flag")
            device_id = request.headers.get("X-Device-Id")
            await AuditChainService(self.accept_language).emit(
                sys_organization_id=user_row["sys_organization_id"],
                event_type=EAuditEventType.PASSWORD_CHANGE,
                actor_user_id=user_id,
                actor_api_consumer_flag=consumer_flag,
                actor_device_id_str=device_id,
                details={"forced_flow": bool(getattr(request.state, "must_update_password", False))},
            )
        except Exception:
            pass

    # ---- POST /login/auth ----
    async def senat_login(self, request: Request, payload: SenatLoginRequest):
        """Authenticate a sénateur (or any user) by username + password.

        Returns the same structure as `AuthController.login` (access_token,
        refresh_token, user, role, profil) so the Flutter login screen can
        consume it without translation. The `should_update_password` flag on
        the user payload drives the forced first-login flow on the client.

        Emits a LOGIN audit row on success or LOGIN_FAIL on any HTTPException
        / 4xx response. Audit emit failures are silent (best-effort).
        """
        legacy_payload = LoginRequest(username=payload.username, password=payload.password)
        try:
            result = await self._auth.login(request=request, payload=legacy_payload)
        except HTTPException as e:
            await self._emit_login_audit(
                request,
                payload.username,
                "LOGIN_FAIL",
                details={"status_code": e.status_code},
            )
            raise
        # The legacy controller may surface non-2xx via `CustomJSONResponse`
        # (e.g. device-not-allowed at 401) without raising. Treat those as
        # failures for the audit chain.
        sc = self._response_status_code(result)
        if sc >= 400:
            await self._emit_login_audit(
                request,
                payload.username,
                "LOGIN_FAIL",
                details={"status_code": sc},
            )
        else:
            await self._emit_login_audit(request, payload.username, "LOGIN")
        return result

    # ---- POST /refresh/auth ----
    async def senat_refresh(self, request: Request):
        """Issue a new access+refresh token pair from a valid refresh token.

        Refresh-token validation, device-binding check, and rotation policy
        are owned by the underlying `refreshToken` flow.
        """
        return await self._auth.refreshToken(request=request)

    # ---- PATCH /patch/password ----
    async def senat_patch_password(
        self,
        request: Request,
        payload: SenatPatchPasswordRequest,
    ):
        """Change the authenticated user's password.

        Two flows converge here:
          - Forced first-login change (JWT carries `must_update_password`):
            `current_password` is optional; the underlying service skips the
            current-password check and clears the `should_update_password` flag.
          - On-demand change: `current_password` required; verified before the
            new password is hashed and persisted.

        The wrapper packages the payload into the shape expected by the
        existing `force_update_password` controller method.
        """
        body = {
            "old_password": payload.current_password,
            "new_password": payload.new_password,
            "confirm_new_password": payload.confirm_new_password,
        }
        result = await self._auth.force_update_password(request=request, body=body)
        # Audit hook (F3): only emit when the underlying response signals
        # success. The controller surfaces 4xx via CustomJSONResponse on
        # validation errors (mismatch, wrong current password, etc.).
        if self._response_status_code(result) < 400:
            await self._emit_password_change_audit(request)
        return result

    # ---- POST /verify/device ----
    async def senat_verify_device(
        self,
        request: Request,
        payload: SenatVerifyDeviceRequest,
    ):
        """Look up a device by its hashed fingerprint and report trust status.

        MVP stub: does NOT create a device record. The login flow handles
        creation. This endpoint is read-only — the Flutter app calls it during
        startup to decide whether to show the device-pairing screen.

        Returns:
          200 + {is_authenticated, device_status} when the device is known.
          200 + {is_authenticated: false, device_status: "PENDING_VALIDATION"}
            as a stub when unknown — keeps the flow non-blocking at MVP.
        """
        device_record = await self._generic.fetch_one_from_collection(
            collection_key=CollectionKey.CFG_USER_DEVICE,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter__device_id_str": payload.device_id_str},
            _skip_rls=True,
        )
        if not device_record:
            return {
                "status_code": 200,
                "is_authenticated": False,
                "device_status": EUserDeviceStatus.PENDING_VALIDATION.value,
            }
        return {
            "status_code": 200,
            "is_authenticated": bool(device_record.get("is_authenticated", False)),
            "device_status": device_record.get(
                "status", EUserDeviceStatus.PENDING_VALIDATION.value
            ),
        }

    async def senat_register_fcm_token(
        self,
        request: Request,
        payload: SenatFcmTokenRegisterRequest,
    ):
        """Persist the caller's FCM registration token onto their
        cfg_user_device row. Resolves the device from the JWT claim
        `cfg_user_device_id` (already populated by
        `verify_logged_in_user` middleware).

        Idempotent: re-registering the same token is a no-op write.
        Token rotation: the client calls this on every
        `onTokenRefresh` event so the latest token always wins.
        """
        from datetime import datetime, timezone
        from fastapi import HTTPException, status

        # Pulled from request.state by the auth middleware. The user
        # dict has the full caller record — the device is referenced
        # via the JWT claim. We don't trust client-supplied device_id;
        # we trust the JWT (server-issued).
        user = getattr(request.state, "user", None)
        decoded = getattr(request.state, "decoded_token", None) or {}
        device_id = decoded.get("cfg_user_device_id")
        if not device_id:
            # Fallback: look up via the device hash header — happens
            # if the JWT was issued before we added the claim.
            device_info = getattr(request.state, "userDeviceInfo", None)
            if isinstance(device_info, dict):
                device_id = device_info.get("id") or device_info.get("_id")

        if not device_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Appareil introuvable dans le contexte d'authentification. "
                    "Reconnectez-vous puis réessayez."
                ),
            )

        await self._generic.update_data_in_collection(
            collection_key=CollectionKey.CFG_USER_DEVICE,
            item_id=str(device_id),
            data={
                "fcm_token": payload.fcm_token,
                "updated_at": datetime.now(timezone.utc),
            },
        )

        # Mask the token in the response — log-safe + still useful for
        # the operator to verify which token registered.
        token_preview = (
            f"{payload.fcm_token[:12]}…" if len(payload.fcm_token) > 12 else "…"
        )
        return {
            "status_code": 200,
            "message": "Jeton FCM enregistré.",
            "data": {
                "device_id": str(device_id),
                "fcm_token_preview": token_preview,
            },
        }

    # ── PIN flow ─────────────────────────────────────────────────────
    # 4 endpoints: status / set / change / verify. All require an
    # authenticated user; the controller pulls `sys_user_id` from
    # `request.state.user` (populated by `verify_logged_in_user`).
    #
    # PIN is a SECOND factor — used at the gate of sensitive actions
    # (vote cast, signature). Stored as an Argon2 hash; never returned.
    # Lockout policy (5 fails / 15 min) is enforced by [PinService].

    @staticmethod
    def _caller_user_id(request):
        """Pull the authenticated caller's PydanticObjectId from
        request.state. Surfaces 401 if the middleware didn't populate
        it (shouldn't happen given middleware order)."""
        from beanie import PydanticObjectId
        from fastapi import HTTPException, status
        user = getattr(request.state, "user", None)
        if not isinstance(user, dict) or not user.get("id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contexte utilisateur absent.",
            )
        return PydanticObjectId(str(user["id"]))

    async def senat_pin_status(self, request):
        """GET /auth/pin/status — does the user have a PIN configured?"""
        user_id = self._caller_user_id(request)
        return {
            "status_code": 200,
            "data": await PinService().get_status(sys_user_id=user_id),
        }

    async def senat_set_pin(
        self, request, payload: SenatSetPinRequest,
    ):
        """POST /auth/pin/set — initial PIN setup."""
        from fastapi import HTTPException, status
        user_id = self._caller_user_id(request)
        try:
            await PinService().set_pin(
                sys_user_id=user_id, pin=payload.pin,
            )
        except PinAlreadySetException as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        return {"status_code": 201, "message": "PIN défini."}

    async def senat_change_pin(
        self, request, payload: SenatChangePinRequest,
    ):
        """POST /auth/pin/change — replace PIN (requires current)."""
        from fastapi import HTTPException, status
        user_id = self._caller_user_id(request)
        try:
            await PinService().change_pin(
                sys_user_id=user_id,
                current_pin=payload.current_pin,
                new_pin=payload.new_pin,
            )
        except PinNotSetException as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PinLockedException as e:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=str(e),
                headers={"X-Locked-Until": e.locked_until.isoformat()},
            )
        except PinInvalidException as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"X-Attempts-Left": str(e.attempts_left)},
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        return {"status_code": 200, "message": "PIN modifié."}

    async def senat_verify_pin(
        self, request, payload: SenatVerifyPinRequest,
    ):
        """POST /auth/pin/verify — sensitive-action gate."""
        from fastapi import HTTPException, status
        user_id = self._caller_user_id(request)
        try:
            await PinService().verify_pin(
                sys_user_id=user_id, pin=payload.pin,
            )
        except PinNotSetException as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PinLockedException as e:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=str(e),
                headers={"X-Locked-Until": e.locked_until.isoformat()},
            )
        except PinInvalidException as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"X-Attempts-Left": str(e.attempts_left)},
            )
        return {"status_code": 200, "message": "PIN vérifié."}

    # ── Security questions (authenticated) ──────────────────────────
    # Three reads + one write:
    #   GET  /auth/security-questions          — full catalog
    #   GET  /auth/security-questions/mine     — which questions THIS user picked
    #   POST /auth/security-questions/set      — replace user's answers
    #
    # The set call replaces (not appends); the client always submits
    # the FULL chosen set. The plaintext answer is normalised + Argon2-
    # hashed by [SecurityQuestionsService]; the plaintext never lands
    # in any column.

    async def senat_list_security_questions(self, request: Request):
        """GET /auth/security-questions — public catalog of available
        questions grouped by category. Required at enrolment time so
        the user can pick N questions covering distinct categories."""
        categories = await self._generic.fetch_data_from_collection(
            collection_key=CollectionKey.REF_AUTH_QUESTION_CATEGORY,
            all_data=True,
            output_data_type=OutputDataType.DEFAULT.value,
            query={},
            _skip_rls=True,
        )
        questions = await self._generic.fetch_data_from_collection(
            collection_key=CollectionKey.REF_AUTH_QUESTION,
            all_data=True,
            output_data_type=OutputDataType.DEFAULT.value,
            query={},
            _skip_rls=True,
        )

        # Group questions under their category. Keep response shape
        # flat-friendly so the Flutter side can render a sectioned
        # list with one pass.
        cat_index: dict[str, dict] = {}
        for c in (categories or []):
            cat_index[str(c.get("id"))] = {
                "id": str(c.get("id")),
                "name": c.get("name"),
                "flag": c.get("flag"),
                "questions": [],
            }
        for q in (questions or []):
            cid = str(q.get("ref_auth_question_category_id"))
            bucket = cat_index.get(cid)
            if bucket is None:
                continue
            bucket["questions"].append({
                "id": str(q.get("id")),
                "name": q.get("name"),
                "flag": q.get("flag"),
            })
        return {
            "status_code": 200,
            "data": list(cat_index.values()),
        }

    async def senat_get_my_security_questions(self, request: Request):
        """GET /auth/security-questions/mine — return the questions
        (without answers) THIS user has enrolled. Used by the Sécurité
        screen to render "Vous avez configuré 3 questions" and let the
        user re-enrol."""
        user_id = self._caller_user_id(request)
        question_ids = await SecurityQuestionsService().list_user_question_ids(
            sys_user_id=user_id,
        )
        if not question_ids:
            return {
                "status_code": 200,
                "data": {
                    "has_enrolled": False,
                    "questions": [],
                },
            }
        rows = await self._generic.fetch_data_from_collection(
            collection_key=CollectionKey.REF_AUTH_QUESTION,
            all_data=True,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter__id__in": [str(q) for q in question_ids]},
            _skip_rls=True,
        ) or []
        return {
            "status_code": 200,
            "data": {
                "has_enrolled": True,
                "questions": [
                    {
                        "id": str(r.get("id")),
                        "name": r.get("name"),
                        "flag": r.get("flag"),
                    }
                    for r in rows
                ],
            },
        }

    async def senat_set_security_questions(
        self,
        request: Request,
        payload: SenatSetSecurityQuestionsRequest,
    ):
        """POST /auth/security-questions/set — enrol or re-enrol.
        Wipes any prior answers + writes the new set with hashed answers.
        Returns 201 on first enrolment, 200 on replacement (same body
        either way; the client doesn't branch on it)."""
        from fastapi import HTTPException, status

        # Reject duplicate question_ids client-side bug -> server enforced.
        qids = [a.cfg_user_question_id for a in payload.answers]
        if len(set(qids)) != len(qids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chaque question ne peut être choisie qu'une seule fois.",
            )

        user_id = self._caller_user_id(request)
        had_previous = await SecurityQuestionsService().has_enrolled_questions(
            sys_user_id=user_id,
        )
        await SecurityQuestionsService().replace_user_answers(
            sys_user_id=user_id,
            answers=[(a.cfg_user_question_id, a.response) for a in payload.answers],
        )
        return {
            "status_code": 200 if had_previous else 201,
            "message": (
                "Questions de sécurité mises à jour."
                if had_previous
                else "Questions de sécurité enregistrées."
            ),
        }

    # ── Forgot-password flow (UNAUTHENTICATED, 3 steps) ─────────────
    # Step 1 — /auth/forgot-password/start
    #   Body: { username }
    #   Returns: { questions[], reset_session_token } — short-lived JWT
    #            scoped to this user_id; no other auth proof yet.
    #
    # Step 2 — /auth/forgot-password/verify
    #   Body: { reset_session_token, answers[] }
    #   Verifies each answer against `response_hash`. On success
    #   returns: { reset_token } (longer-lived JWT spendable by /complete).
    #
    # Step 3 — /auth/forgot-password/complete
    #   Body: { reset_token, new_password, confirm_new_password }
    #   Rotates the password; clears should_update_password +
    #   any account lockout side-effects from the failed-login chain.
    #
    # On every step we DO NOT reveal whether the username exists or
    # whether the answers were partially correct — generic messages,
    # opaque timings. Brute-force protection happens upstream
    # (rate-limit middleware) and at the JWT layer (token TTL).

    # Token TTLs — tuned to be short enough that a stolen token
    # window is small, long enough to survive a slow connection on
    # the client.
    _RESET_SESSION_TTL_MIN = 5
    _RESET_TOKEN_TTL_MIN = 10

    async def senat_forgot_password_start(
        self,
        request: Request,
        payload: SenatForgotPasswordStartRequest,
    ):
        """Step 1 — username → questions + scope token.

        Always returns 200 with the same shape, EVEN IF the username
        is unknown or the user has no enrolled questions. That way an
        attacker can't enumerate valid usernames by probing this
        endpoint. The frontend treats an empty `questions` array as
        "contactez votre administrateur."
        """
        from datetime import timedelta

        user_row = await self._generic.fetch_one_from_collection(
            collection_key=CollectionKey.SYS_USER,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter__username": payload.username},
            _skip_rls=True,
        )

        # Build the "as if it worked" response shape first.
        empty_response = {
            "status_code": 200,
            "data": {
                "questions": [],
                "reset_session_token": "",
            },
        }

        if not isinstance(user_row, dict) or not user_row.get("id"):
            return empty_response

        user_id = str(user_row["id"])
        question_ids = await SecurityQuestionsService().list_user_question_ids(
            sys_user_id=user_row["id"],
        )
        if not question_ids:
            return empty_response

        # Hydrate the questions (names only — no hashes ever leave).
        rows = await self._generic.fetch_data_from_collection(
            collection_key=CollectionKey.REF_AUTH_QUESTION,
            all_data=True,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter__id__in": [str(q) for q in question_ids]},
            _skip_rls=True,
        ) or []

        session_token = TokenService.create_access_token(
            data={"sub": user_id, "username": payload.username},
            token_type=EJWTTokenType.PASSWORD_RESET_SESSION,
            expires_delta=timedelta(minutes=self._RESET_SESSION_TTL_MIN),
        )
        return {
            "status_code": 200,
            "data": {
                "questions": [
                    {
                        "id": str(r.get("id")),
                        "name": r.get("name"),
                        "flag": r.get("flag"),
                    }
                    for r in rows
                ],
                "reset_session_token": session_token,
                "expires_in_seconds": self._RESET_SESSION_TTL_MIN * 60,
            },
        }

    async def senat_forgot_password_verify(
        self,
        request: Request,
        payload: SenatForgotPasswordVerifyRequest,
    ):
        """Step 2 — answers must all match → issue reset_token.

        On mismatch we return a generic 401 with the same message
        regardless of how many answers were wrong. We DO NOT echo
        back per-question correctness — the audit log can record
        the per-question miss count internally, but the wire stays
        opaque.
        """
        from datetime import timedelta
        from fastapi import HTTPException, status

        # Decode the session token. Surfaces 401 on expiry / tampering.
        decoded = TokenService(self.accept_language).decode_and_verify_token(
            token=payload.reset_session_token,
            expected_type=EJWTTokenType.PASSWORD_RESET_SESSION,
            by_pass_exception=True,
        )
        if not decoded or not decoded.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session de réinitialisation expirée. Recommencez.",
            )

        from beanie import PydanticObjectId
        user_id = PydanticObjectId(str(decoded["sub"]))

        try:
            await SecurityQuestionsService().verify_user_answers(
                sys_user_id=user_id,
                answers=[(a.cfg_user_question_id, a.response) for a in payload.answers],
            )
        except SecurityQuestionsNotSetException:
            # Edge case: between /start and /verify the user wiped
            # their questions. Treat as a generic failure.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Réponses incorrectes.",
            )
        except SecurityQuestionsMismatchException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Réponses incorrectes.",
            )

        # Success — mint the reset_token. The token's `sub` is the
        # user_id; /complete trusts it as proof-of-identity.
        reset_token = TokenService.create_access_token(
            data={"sub": str(user_id)},
            token_type=EJWTTokenType.PASSWORD_RESET,
            expires_delta=timedelta(minutes=self._RESET_TOKEN_TTL_MIN),
        )
        return {
            "status_code": 200,
            "data": {
                "reset_token": reset_token,
                "expires_in_seconds": self._RESET_TOKEN_TTL_MIN * 60,
            },
        }

    async def senat_forgot_password_complete(
        self,
        request: Request,
        payload: SenatForgotPasswordCompleteRequest,
    ):
        """Step 3 — spend reset_token + new_password to rotate."""
        from fastapi import HTTPException, status

        decoded = TokenService(self.accept_language).decode_and_verify_token(
            token=payload.reset_token,
            expected_type=EJWTTokenType.PASSWORD_RESET,
            by_pass_exception=True,
        )
        if not decoded or not decoded.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Lien de réinitialisation invalide ou expiré.",
            )

        user_id = str(decoded["sub"])

        # Schema-level guard already enforces min_length=8 / max=200 and
        # `confirm == new`. We deliberately DON'T also call the legacy
        # validate_password_strength helper — it never existed on the
        # mixin chain — so any extra rules (digit + special-char etc.)
        # will land here when the policy is finalised.

        await self._generic.update_data_in_collection(
            collection_key=CollectionKey.SYS_USER,
            item_id=user_id,
            data={
                "password": PasswordService.hash_password(payload.new_password),
                # Forced-update flag clear: the user has just chosen
                # their own password through a verified channel.
                "should_update_password": False,
                # Account lockout side-effects cleared too — the user
                # proved identity via Q&A (login + reset counters both).
                "login_fail_attempt_count": 0,
                "login_locked_until": None,
                "reset_password_fail_attempt_count": 0,
                "reset_password_locked_until": None,
            },
        )

        # Best-effort audit emit so security forensics see the rotation.
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )
            user_row = await self._generic.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__id": user_id},
                _skip_rls=True,
            )
            if isinstance(user_row, dict) and user_row.get("sys_organization_id"):
                await AuditChainService(self.accept_language).emit(
                    sys_organization_id=user_row["sys_organization_id"],
                    event_type=EAuditEventType.PASSWORD_CHANGE,
                    actor_user_id=user_id,
                    actor_device_id_str=request.headers.get("X-Device-Id"),
                    details={"flow": "forgot_password_qa"},
                )
        except Exception:
            pass

        return {
            "status_code": 200,
            "message": "Mot de passe réinitialisé. Vous pouvez vous connecter.",
        }
