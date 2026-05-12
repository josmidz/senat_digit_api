"""`TallyService._required_count` per-majority-rule arithmetic.

Locks the threshold formulas in:

    RELATIVE   → 1 (sentinel; gate is `cp > cc`, not a count compare)
    ABSOLUE    → floor(N/2) + 1   (strict majority of denominator)
    DEUX_TIERS → ceil(2N/3)       (the "majorité des deux tiers")
    CUSTOM     → ceil(N * threshold), threshold defaults to 0.5

Edge case: denominator <= 0 short-circuits to 0 across all rules
(prevents `(0 // 2) + 1 == 1` quirks for the empty case).
"""
from __future__ import annotations

import pytest

from app.modules.vote.enums.vote_enum import EVoteMajorityType
from app.modules.vote.services.tally_service import TallyService


# ── ABSOLUE: strict majority of seats ────────────────────────────────


@pytest.mark.parametrize(
    "denom,expected",
    [
        (109, 55),  # the actual Sénat RDC seat count → quorum 55
        (100, 51),
        (10,  6),
        (3,   2),
        (2,   2),   # floor(2/2)+1 = 2 (you need both for "absolute")
        (1,   1),
    ],
)
def test_absolue_required_count(denom: int, expected: int) -> None:
    assert TallyService._required_count(
        EVoteMajorityType.ABSOLUE, None, denom
    ) == expected


# ── DEUX_TIERS: ceil(2N/3) ───────────────────────────────────────────


@pytest.mark.parametrize(
    "denom,expected",
    [
        (109, 73),  # ceil(218/3) = ceil(72.67) = 73
        (100, 67),  # ceil(200/3) = ceil(66.67) = 67
        (9,   6),   # exactly 2/3 — no ceiling boost
        (10,  7),   # ceil(20/3) = ceil(6.67) = 7
        (3,   2),
        (1,   1),
    ],
)
def test_deux_tiers_required_count(denom: int, expected: int) -> None:
    assert TallyService._required_count(
        EVoteMajorityType.DEUX_TIERS, None, denom
    ) == expected


# ── CUSTOM: ceil(N * threshold), default 0.5 when threshold None ─────


@pytest.mark.parametrize(
    "denom,threshold,expected",
    [
        (109, 0.6,  66),  # ceil(65.4)
        (109, 0.75, 82),  # ceil(81.75)
        (100, 0.5,  50),  # exact boundary, no ceiling boost
        (100, None, 50),  # default 0.5 path
        (100, 0.51, 51),
        (100, 1.0, 100),
        (1,   0.5,  1),   # ceil(0.5)
        (10,  0.0,  0),   # 0% threshold → trivially met
    ],
)
def test_custom_required_count(
    denom: int, threshold: float | None, expected: int,
) -> None:
    assert TallyService._required_count(
        EVoteMajorityType.CUSTOM, threshold, denom
    ) == expected


# ── RELATIVE: sentinel 1 ────────────────────────────────────────────


@pytest.mark.parametrize("denom", [1, 5, 100, 109, 1000])
def test_relative_returns_sentinel_one(denom: int) -> None:
    """The actual gate for RELATIVE is `cp > cc` in `_decision`;
    `_required_count` returns 1 to signal "anything past parity"."""
    assert TallyService._required_count(
        EVoteMajorityType.RELATIVE, None, denom
    ) == 1


# ── empty / negative denominator short-circuits to 0 ────────────────


@pytest.mark.parametrize(
    "majority_type,threshold",
    [
        (EVoteMajorityType.RELATIVE,   None),
        (EVoteMajorityType.ABSOLUE,    None),
        (EVoteMajorityType.DEUX_TIERS, None),
        (EVoteMajorityType.CUSTOM,     0.5),
    ],
)
@pytest.mark.parametrize("denom", [0, -1])
def test_zero_or_negative_denominator(
    majority_type: EVoteMajorityType, threshold: float | None, denom: int,
) -> None:
    """Empty scrutin should not produce phantom thresholds."""
    assert TallyService._required_count(majority_type, threshold, denom) == 0
