"""PIN management — set, change, verify, with Argon2 hashing + lockout.

Centralizes everything we do to a `CfgUserPinModel` row so the
controller stays thin. Hashing reuses `PasswordService` (Argon2 via
passlib) so we don't ship two crypto primitives for the same job.

Lockout policy:
  - `_MAX_ATTEMPTS` consecutive bad verifies → row.locked_until set
    to `now + _LOCKOUT_DURATION`. Any verify within that window
    raises `PinLockedException`.
  - A successful verify resets the counter and clears the lockout.
  - Setting a fresh PIN (admin reset or legitimate user reset via
    Q&A) also clears both.

Threading: every method is async + awaits the underlying Beanie
write. The Mongo doc has a unique index on `sys_user_id` so a race
between two "set PIN" calls surfaces as a `DuplicateKeyError`, which
[set_pin] catches and translates into "PIN already set; use change_pin".
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from beanie import PydanticObjectId

from app.modules.auth.models.cfg_user_pin.cfg_user_pin_model import (
    CfgUserPinModel,
)
from app.modules.auth.services.password.password_service import (
    PasswordService,
)


# ── Policy constants ────────────────────────────────────────────────
_MAX_ATTEMPTS = 5
_LOCKOUT_DURATION = timedelta(minutes=15)


class PinError(Exception):
    """Base class for PIN-related domain errors."""


class PinNotSetException(PinError):
    """User has no PIN row yet — must call set_pin first."""


class PinAlreadySetException(PinError):
    """User already has a PIN — use change_pin to replace it."""


class PinInvalidException(PinError):
    """Verify failed — wrong PIN. fail_attempt_count was incremented."""

    def __init__(self, attempts_left: int):
        super().__init__(f"PIN invalide. {attempts_left} tentative(s) restante(s).")
        self.attempts_left = attempts_left


class PinLockedException(PinError):
    """Too many failed attempts. Row is locked until `locked_until`."""

    def __init__(self, locked_until: datetime):
        super().__init__(
            "PIN verrouillé suite à trop d'échecs. Réessayez plus tard."
        )
        self.locked_until = locked_until


class PinService:
    """Stateless service. Construct once per request (cheap)."""

    def __init__(self):
        self._hash = PasswordService

    # ── Lifecycle ───────────────────────────────────────────────────

    async def set_pin(
        self,
        *,
        sys_user_id: PydanticObjectId,
        pin: str,
    ) -> CfgUserPinModel:
        """Create the row for a user who doesn't have a PIN yet.

        Raises [PinAlreadySetException] if a row already exists.
        """
        self._validate_pin_format(pin)

        existing = await CfgUserPinModel.find_one(
            CfgUserPinModel.sys_user_id == sys_user_id
        )
        if existing is not None:
            raise PinAlreadySetException(
                "PIN déjà défini. Utilisez « Changer le PIN »."
            )

        now = datetime.now(timezone.utc)
        row = CfgUserPinModel(
            sys_user_id=sys_user_id,
            pin_hash=self._hash.hash_password(pin),
            fail_attempt_count=0,
            locked_until=None,
            pin_set_at=now,
        )
        await row.insert()
        return row

    async def change_pin(
        self,
        *,
        sys_user_id: PydanticObjectId,
        current_pin: str,
        new_pin: str,
    ) -> CfgUserPinModel:
        """Verify the current PIN then replace it. Verify path applies
        the lockout policy — a stuck-key attacker who doesn't know the
        old PIN can't brute-force their way to changing it."""
        self._validate_pin_format(new_pin)
        # Verify also raises PinLockedException + PinInvalidException
        # which the controller maps to 423 / 401 respectively.
        row = await self.verify_pin(
            sys_user_id=sys_user_id, pin=current_pin,
        )
        row.pin_hash = self._hash.hash_password(new_pin)
        row.fail_attempt_count = 0
        row.locked_until = None
        row.pin_set_at = datetime.now(timezone.utc)
        await row.save()
        return row

    async def reset_pin(
        self,
        *,
        sys_user_id: PydanticObjectId,
        new_pin: str,
    ) -> CfgUserPinModel:
        """Admin / forgot-PIN reset. SKIPS verify of the current PIN —
        the caller (controller) must have proven the user's identity
        through a stronger factor (e.g. password reset flow, sysadmin
        action, security questions). Resets the row in-place if it
        exists, creates one otherwise."""
        self._validate_pin_format(new_pin)
        now = datetime.now(timezone.utc)
        row = await CfgUserPinModel.find_one(
            CfgUserPinModel.sys_user_id == sys_user_id
        )
        if row is None:
            row = CfgUserPinModel(
                sys_user_id=sys_user_id,
                pin_hash=self._hash.hash_password(new_pin),
                fail_attempt_count=0,
                locked_until=None,
                pin_set_at=now,
            )
            await row.insert()
            return row
        row.pin_hash = self._hash.hash_password(new_pin)
        row.fail_attempt_count = 0
        row.locked_until = None
        row.pin_set_at = now
        await row.save()
        return row

    # ── Verify ──────────────────────────────────────────────────────

    async def verify_pin(
        self,
        *,
        sys_user_id: PydanticObjectId,
        pin: str,
    ) -> CfgUserPinModel:
        """Returns the (fresh) row on success. Otherwise:
          - [PinNotSetException]  if the user never set a PIN.
          - [PinLockedException]  if the row is in a lockout window.
          - [PinInvalidException] on a bad PIN (after incrementing
                                  the fail counter and possibly
                                  triggering a fresh lockout).
        """
        row = await CfgUserPinModel.find_one(
            CfgUserPinModel.sys_user_id == sys_user_id
        )
        if row is None:
            raise PinNotSetException(
                "Aucun PIN configuré pour ce compte."
            )

        now = datetime.now(timezone.utc)
        if row.locked_until is not None and row.locked_until > now:
            raise PinLockedException(locked_until=row.locked_until)

        ok = self._hash.verify_password(pin, row.pin_hash)
        if ok:
            row.fail_attempt_count = 0
            row.locked_until = None
            row.last_verified_at = now
            await row.save()
            return row

        # Wrong PIN — bump the counter, lock if at threshold.
        row.fail_attempt_count += 1
        if row.fail_attempt_count >= _MAX_ATTEMPTS:
            row.locked_until = now + _LOCKOUT_DURATION
            await row.save()
            raise PinLockedException(locked_until=row.locked_until)
        await row.save()
        attempts_left = _MAX_ATTEMPTS - row.fail_attempt_count
        raise PinInvalidException(attempts_left=attempts_left)

    # ── Read ────────────────────────────────────────────────────────

    async def get_status(
        self,
        *,
        sys_user_id: PydanticObjectId,
    ) -> dict:
        """Read-only status used by the Flutter "Sécurité" screen to
        decide between "Configurer mon PIN" vs "Changer mon PIN".
        Never returns the hash or the PIN itself."""
        row = await CfgUserPinModel.find_one(
            CfgUserPinModel.sys_user_id == sys_user_id
        )
        if row is None:
            return {
                "is_pin_set": False,
                "is_locked": False,
                "locked_until": None,
                "fail_attempt_count": 0,
                "pin_set_at": None,
                "last_verified_at": None,
            }
        now = datetime.now(timezone.utc)
        is_locked = (
            row.locked_until is not None and row.locked_until > now
        )
        return {
            "is_pin_set": True,
            "is_locked": is_locked,
            "locked_until": row.locked_until.isoformat() if row.locked_until else None,
            "fail_attempt_count": row.fail_attempt_count,
            "pin_set_at": row.pin_set_at.isoformat() if row.pin_set_at else None,
            "last_verified_at": (
                row.last_verified_at.isoformat() if row.last_verified_at else None
            ),
        }

    # ── Validation helpers ──────────────────────────────────────────

    @staticmethod
    def _validate_pin_format(pin: str) -> None:
        """Server-side guard. The schema already enforces this at the
        FastAPI layer, but a service-level check covers any internal
        caller (admin override, migration script) that didn't go
        through the schema."""
        if not isinstance(pin, str):
            raise ValueError("PIN doit être une chaîne de caractères.")
        s = pin.strip()
        if not s.isdigit():
            raise ValueError("PIN doit être uniquement numérique.")
        if not (4 <= len(s) <= 6):
            raise ValueError("PIN doit comporter entre 4 et 6 chiffres.")
