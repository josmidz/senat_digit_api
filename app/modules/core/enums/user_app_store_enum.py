"""Enums for the user_app_store cache layer.

Ported from bloonio_apps_api with senat_digit-flavored profile whitelist
(see ``app.modules.core.constants.common.USER_APP_STORE_STATIC_PROFILES``).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class EUserAppStoreProfileTypeFlag(str, Enum):
    """Whether a profile is cloned per-user (dynamic) or shared across users (static)."""
    STATIC = "static"
    DYNAMIC = "dynamic"


class EUserAppStoreEndpointFlag(str, Enum):
    """Which application-fetch endpoint a cache row represents.

    Single endpoint flag for now — senat_digit only has one ``/data/get-applications``
    surface. Add more when additional fetch flows materialize.
    """
    APPLICATIONS = "applications"


def _static_profile_flags() -> frozenset:
    """Lazy-read USER_APP_STORE_STATIC_PROFILES to avoid circular imports."""
    from app.modules.core.constants.common import USER_APP_STORE_STATIC_PROFILES
    return frozenset(USER_APP_STORE_STATIC_PROFILES)


# Module-level snapshot kept for back-compat with code that imports the
# constant directly. New code should call ``_static_profile_flags()`` or
# the helper in ``user_app_store_helpers``.
STATIC_PROFILE_FLAGS = _static_profile_flags()


def resolve_profile_type_flag(
    profile_flag: Optional[str],
) -> EUserAppStoreProfileTypeFlag:
    """Map a profile flag to its cache type.

    STATIC when the flag is in the static whitelist, DYNAMIC otherwise.
    Unknown / None flags fall through to DYNAMIC (safe default — one row
    per user, no cache poisoning across tenants).
    """
    if profile_flag and profile_flag in _static_profile_flags():
        return EUserAppStoreProfileTypeFlag.STATIC
    return EUserAppStoreProfileTypeFlag.DYNAMIC
