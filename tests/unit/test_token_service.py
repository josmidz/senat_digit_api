"""`TokenService` — JWT lifecycle (create + decode + verify).

Two methods carry the entire JWT semantics for the auth layer:

  - `create_access_token(data, token_type, expires_delta)` — builds
    a signed JWT with `exp`, `iat`, `type`, `aud` claims plus the
    user-supplied payload.

  - `decode_and_verify_token(token, expected_type, by_pass_exception)`
    — verifies signature, audience, expiry, and the `type` claim.
    Raises `HTTPException(401|403)` on failure; the
    `by_pass_exception=True` flag returns None instead (used by the
    permission-check middleware to fall through to MFA token type).

Six contracts locked:

  1. **Round-trip** — a token created with type T decodes cleanly
     when verified with the same expected_type.

  2. **Audience binding** — a token created as LOGIN cannot be
     verified as MFA_VERIFICATION (or any other type). This is the
     critical defence-in-depth: prevents replay across token
     contexts.

  3. **Expiry** — a token whose `exp` is in the past raises
     ExpiredSignatureError → 401.

  4. **`type` claim cross-check** — even when the audience matches,
     a mismatched `type` claim triggers a 403 (defends against an
     attacker who could control aud but not the body).

  5. **`by_pass_exception=True`** — every error path that would
     raise instead returns None. Locks the contract the permission
     middleware relies on.

  6. **Tampered token** — a flipped byte in the signature → JWTError
     → 401. The integrity guarantee.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import jwt as jose_jwt

from app.modules.auth.services.token.token_service import TokenService
from app.modules.core.configs.config import settings
from app.modules.core.enums.type_enum import EJWTTokenType


def _decode_unverified(token: str) -> dict:
    """Read claims without signature/expiry/audience checks. Used by
    create-side tests to assert exact payload shape."""
    return jose_jwt.get_unverified_claims(token)


# ── create_access_token ────────────────────────────────────────────


def test_create_access_token_returns_string() -> None:
    """JWT encoding output must be a string (callers concatenate
    into `Authorization: Bearer <token>` headers)."""
    out = TokenService.create_access_token(
        data={"sub": "user1"},
        token_type=EJWTTokenType.LOGIN,
    )
    assert isinstance(out, str)
    assert len(out) > 0


def test_create_access_token_embeds_user_payload() -> None:
    """Caller-supplied `data` is preserved in the encoded token."""
    out = TokenService.create_access_token(
        data={"sub": "user1", "rbac_role_id": "role-greffier"},
        token_type=EJWTTokenType.LOGIN,
    )
    claims = _decode_unverified(out)
    assert claims["sub"] == "user1"
    assert claims["rbac_role_id"] == "role-greffier"


def test_create_access_token_sets_type_and_audience_claims() -> None:
    """`type` and `aud` are derived from `token_type`. The
    permission middleware uses both — if the audience doesn't match
    `<type>_token`, jose's `decode` raises before our type check
    even runs."""
    out = TokenService.create_access_token(
        data={"sub": "user1"},
        token_type=EJWTTokenType.LOGIN,
    )
    claims = _decode_unverified(out)
    assert claims["type"] == "login"
    assert claims["aud"] == "login_token"


def test_create_access_token_uses_correct_audience_per_type() -> None:
    """Each token type produces a distinct audience — defends against
    the audience-binding cross-replay attack."""
    expected = {
        EJWTTokenType.LOGIN: "login_token",
        EJWTTokenType.REFRESH_TOKEN: "refresh_token_token",
        EJWTTokenType.MFA_VERIFICATION: "mfa_verification_token",
        EJWTTokenType.PASSWORD_RESET_PROCESS: "reset_password_process_token",
    }
    for t, aud in expected.items():
        out = TokenService.create_access_token(
            data={"sub": "u"},
            token_type=t,
        )
        assert _decode_unverified(out)["aud"] == aud


def test_create_access_token_default_expiry_is_fifteen_minutes() -> None:
    """No `expires_delta` → 15-minute window. Locks the spec so
    a refactor changing the default forces an explicit decision."""
    before = datetime.now(timezone.utc)
    out = TokenService.create_access_token(
        data={"sub": "u"},
        token_type=EJWTTokenType.LOGIN,
    )
    after = datetime.now(timezone.utc)
    claims = _decode_unverified(out)
    exp = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
    # Expiry should be within [before+15min, after+15min] — a few
    # ms of slop accommodates the single test wall-clock window.
    assert before + timedelta(minutes=14, seconds=59) <= exp <= after + timedelta(minutes=15, seconds=1)


def test_create_access_token_honors_custom_expires_delta() -> None:
    """Login tokens use a long delta (8h typical); MFA tokens use 5
    min. The caller provides the value — the service must honor it."""
    custom = timedelta(hours=8)
    before = datetime.now(timezone.utc)
    out = TokenService.create_access_token(
        data={"sub": "u"},
        token_type=EJWTTokenType.LOGIN,
        expires_delta=custom,
    )
    after = datetime.now(timezone.utc)
    exp = datetime.fromtimestamp(_decode_unverified(out)["exp"], tz=timezone.utc)
    assert before + custom - timedelta(seconds=1) <= exp <= after + custom + timedelta(seconds=1)


def test_create_access_token_propagates_device_id_str() -> None:
    """The `device_id_str` from the data dict is hoisted into the
    token claims. The audit chain uses this to attribute calls to a
    specific tablet."""
    out = TokenService.create_access_token(
        data={"sub": "u", "device_id_str": "tablet-greffier-01"},
        token_type=EJWTTokenType.LOGIN,
    )
    assert _decode_unverified(out)["device_id_str"] == "tablet-greffier-01"


def test_create_access_token_device_id_defaults_to_none() -> None:
    """Missing `device_id_str` in the data → `device_id_str: null`
    in the claims, NOT absent. Defends against KeyError when readers
    do `claims["device_id_str"]` rather than `.get(...)`."""
    out = TokenService.create_access_token(
        data={"sub": "u"},  # no device_id_str
        token_type=EJWTTokenType.LOGIN,
    )
    claims = _decode_unverified(out)
    assert "device_id_str" in claims
    assert claims["device_id_str"] is None


def test_create_access_token_iat_is_close_to_now() -> None:
    """`iat` (issued-at) must be roughly 'now' so token-age checks
    on the verifier side stay accurate."""
    before = datetime.now(timezone.utc).timestamp()
    out = TokenService.create_access_token(
        data={"sub": "u"},
        token_type=EJWTTokenType.LOGIN,
    )
    after = datetime.now(timezone.utc).timestamp()
    iat = _decode_unverified(out)["iat"]
    assert before - 1 <= iat <= after + 1


# ── decode_and_verify_token — round-trip ──────────────────────────


def test_decode_and_verify_round_trip() -> None:
    """A token created as LOGIN decodes cleanly when verified as LOGIN.
    The single most consequential property: tokens we issue are tokens
    we accept."""
    token = TokenService.create_access_token(
        data={"sub": "user1", "rbac_role_id": "role-greffier"},
        token_type=EJWTTokenType.LOGIN,
    )
    svc = TokenService()
    out = svc.decode_and_verify_token(
        token=token, expected_type=EJWTTokenType.LOGIN,
    )
    assert out["sub"] == "user1"
    assert out["rbac_role_id"] == "role-greffier"
    assert out["type"] == "login"


def test_decode_and_verify_returns_full_claims() -> None:
    """Every claim present in `data` plus the lifecycle claims (`exp`,
    `iat`, `type`, `aud`) is returned to the caller."""
    token = TokenService.create_access_token(
        data={"sub": "u", "extra": "value"},
        token_type=EJWTTokenType.LOGIN,
    )
    svc = TokenService()
    claims = svc.decode_and_verify_token(token, EJWTTokenType.LOGIN)
    assert claims["sub"] == "u"
    assert claims["extra"] == "value"
    assert "exp" in claims
    assert "iat" in claims
    assert "aud" in claims


# ── decode_and_verify_token — audience binding ────────────────────


def test_decode_rejects_wrong_audience() -> None:
    """A LOGIN token (aud=login_token) cannot be verified as
    MFA_VERIFICATION (aud=mfa_verification_token). jose raises
    JWTError for audience mismatch → 401.

    Critical defence-in-depth: prevents an attacker from replaying
    a login token where an MFA token is expected (or vice versa)."""
    login_token = TokenService.create_access_token(
        data={"sub": "u"},
        token_type=EJWTTokenType.LOGIN,
    )
    svc = TokenService()
    with pytest.raises(HTTPException) as exc:
        svc.decode_and_verify_token(
            login_token, expected_type=EJWTTokenType.MFA_VERIFICATION,
        )
    assert exc.value.status_code == 401


def test_decode_with_bypass_returns_none_on_wrong_audience() -> None:
    """`by_pass_exception=True` is what the permission middleware
    uses to try LOGIN, then fall back to MFA_VERIFICATION without
    a 401 cascade. Returns None instead of raising."""
    login_token = TokenService.create_access_token(
        data={"sub": "u"},
        token_type=EJWTTokenType.LOGIN,
    )
    svc = TokenService()
    out = svc.decode_and_verify_token(
        login_token,
        expected_type=EJWTTokenType.MFA_VERIFICATION,
        by_pass_exception=True,
    )
    assert out is None


# ── decode_and_verify_token — expiry ──────────────────────────────


def test_decode_rejects_expired_token() -> None:
    """A token whose `exp` is in the past → 401 (jose raises
    ExpiredSignatureError). The session-day workflow assumes
    sénateur tokens are 8h-bound; expired tokens force re-login."""
    expired_token = TokenService.create_access_token(
        data={"sub": "u"},
        token_type=EJWTTokenType.LOGIN,
        expires_delta=timedelta(seconds=-10),  # already expired
    )
    svc = TokenService()
    with pytest.raises(HTTPException) as exc:
        svc.decode_and_verify_token(expired_token, EJWTTokenType.LOGIN)
    assert exc.value.status_code == 401


def test_decode_with_bypass_returns_none_on_expired_token() -> None:
    expired_token = TokenService.create_access_token(
        data={"sub": "u"},
        token_type=EJWTTokenType.LOGIN,
        expires_delta=timedelta(seconds=-10),
    )
    svc = TokenService()
    out = svc.decode_and_verify_token(
        expired_token,
        EJWTTokenType.LOGIN,
        by_pass_exception=True,
    )
    assert out is None


# ── decode_and_verify_token — tampered token ──────────────────────


def test_decode_rejects_tampered_signature() -> None:
    """One flipped char in the signature segment → JWTError → 401.
    The integrity guarantee — without it, anyone could mint tokens."""
    token = TokenService.create_access_token(
        data={"sub": "u"},
        token_type=EJWTTokenType.LOGIN,
    )
    # JWT is `<header>.<payload>.<signature>`; flip a char in the
    # signature.
    parts = token.split(".")
    sig = parts[2]
    tampered_sig = ("Z" if sig[0] != "Z" else "Y") + sig[1:]
    tampered_token = ".".join([parts[0], parts[1], tampered_sig])

    svc = TokenService()
    with pytest.raises(HTTPException) as exc:
        svc.decode_and_verify_token(tampered_token, EJWTTokenType.LOGIN)
    assert exc.value.status_code == 401


def test_decode_rejects_garbage_string() -> None:
    """A non-JWT-shaped string raises JWTError immediately — not a
    cryptic decoder error."""
    svc = TokenService()
    with pytest.raises(HTTPException) as exc:
        svc.decode_and_verify_token(
            "definitely-not-a-jwt-token",
            EJWTTokenType.LOGIN,
        )
    assert exc.value.status_code == 401


def test_decode_with_bypass_returns_none_on_garbage() -> None:
    svc = TokenService()
    out = svc.decode_and_verify_token(
        "definitely-not-a-jwt-token",
        EJWTTokenType.LOGIN,
        by_pass_exception=True,
    )
    assert out is None


# ── decode_and_verify_token — type-claim cross-check ──────────────


def test_decode_rejects_mismatched_type_claim() -> None:
    """Defence-in-depth: even when the audience is right, a
    mismatched `type` claim triggers 403. Defends against the
    scenario where an attacker controls the audience binding (e.g.
    via a misconfigured kid header) but can't write to the body.

    Build a hand-crafted token with the right aud but wrong type
    using a direct jose encode."""
    payload = {
        "sub": "u",
        "type": "mfa_verification",  # wrong type
        "aud": f"{EJWTTokenType.LOGIN.value}_token",  # right audience
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jose_jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
    )
    svc = TokenService()
    with pytest.raises(HTTPException) as exc:
        svc.decode_and_verify_token(token, EJWTTokenType.LOGIN)
    assert exc.value.status_code == 403


def test_decode_with_bypass_returns_none_on_type_mismatch() -> None:
    payload = {
        "sub": "u",
        "type": "mfa_verification",
        "aud": f"{EJWTTokenType.LOGIN.value}_token",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jose_jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
    )
    svc = TokenService()
    out = svc.decode_and_verify_token(
        token, EJWTTokenType.LOGIN, by_pass_exception=True,
    )
    assert out is None


# ── decode_and_verify_token — wrong signing key ───────────────────


def test_decode_rejects_token_signed_with_different_key() -> None:
    """A token signed with a key OTHER than `settings.JWT_SECRET_KEY`
    fails signature verification → 401. The "minted by who" check —
    only tokens we created can be accepted."""
    payload = {
        "sub": "u",
        "type": EJWTTokenType.LOGIN.value,
        "aud": f"{EJWTTokenType.LOGIN.value}_token",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    foreign_token = jose_jwt.encode(
        payload, "definitely-not-our-key", algorithm=settings.JWT_ALGORITHM,
    )
    svc = TokenService()
    with pytest.raises(HTTPException) as exc:
        svc.decode_and_verify_token(foreign_token, EJWTTokenType.LOGIN)
    assert exc.value.status_code == 401
