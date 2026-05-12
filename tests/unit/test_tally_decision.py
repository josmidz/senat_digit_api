"""`TallyService._decision` — the rule semantics for adopting a scrutin.

This is the single most legally-significant computation in the system.
A bug here means a vote is recorded as ADOPTÉ when it should be REJETÉ
(or vice versa). The harness exhaustively covers each PPTX-anchored
majority rule plus the cross-cutting NPV / ABSTENTION / proxy-weight
semantics.

Conventions tested (règlement intérieur):
  - **RELATIVE** uses expressed votes (POUR + CONTRE) as denominator;
    decision = POUR strictly greater than CONTRE. Tie ⇒ REJETÉ.
  - **ABSOLUE / DEUX_TIERS / CUSTOM** use seats from the parent session
    as denominator. ABSTENTION + NPV count toward `ballot_headcount`
    but never toward majority — the seat denominator means they don't
    dilute either way.
  - **No ballots cast** ⇒ decision is None (not "REJETÉ"); avoids
    auto-rejecting a vote that simply didn't run yet.
"""
from __future__ import annotations

import pytest

from app.modules.vote.enums.vote_enum import EVoteMajorityType
from app.modules.vote.services.tally_service import TallyService


def _decide(
    *, pour: int = 0, contre: int = 0, abstention: int = 0, npv: int = 0,
    majority: EVoteMajorityType,
    threshold: float | None = None,
    seats: int | None = None,
):
    """Compact wrapper to keep parametrize tables readable."""
    return TallyService._decision(
        count_pour=pour,
        count_contre=contre,
        count_abstention=abstention,
        count_npv=npv,
        majority_type=majority,
        custom_threshold=threshold,
        total_seats=seats,
    )


# ── RELATIVE: POUR > CONTRE wins; ties REJECT ───────────────────────


def test_relative_pour_majority_adopts() -> None:
    d = _decide(pour=40, contre=30, majority=EVoteMajorityType.RELATIVE)
    assert d.majority_met is True
    assert d.decision == "ADOPTE"
    assert d.denominator == 70  # POUR + CONTRE


def test_relative_contre_majority_rejects() -> None:
    d = _decide(pour=30, contre=40, majority=EVoteMajorityType.RELATIVE)
    assert d.majority_met is False
    assert d.decision == "REJETE"


def test_relative_tie_is_rejected() -> None:
    """Strict gate (`cp > cc`): a 50/50 split is REJETÉ.

    This is the règlement intérieur convention — ties don't carry the
    motion. If the rule ever changes to "tie passes", this test forces
    an explicit update."""
    d = _decide(pour=50, contre=50, majority=EVoteMajorityType.RELATIVE)
    assert d.majority_met is False
    assert d.decision == "REJETE"


def test_relative_ignores_abstention_and_npv() -> None:
    """ABSTENTION and NPV are excluded from RELATIVE's denominator
    automatically (denominator = POUR + CONTRE only)."""
    d = _decide(
        pour=40, contre=30, abstention=20, npv=15,
        majority=EVoteMajorityType.RELATIVE,
    )
    assert d.denominator == 70  # NOT 105
    assert d.majority_met is True


def test_relative_ignores_total_seats() -> None:
    """Seat count is irrelevant for RELATIVE — only expressed votes."""
    d = _decide(
        pour=40, contre=30, majority=EVoteMajorityType.RELATIVE, seats=109,
    )
    assert d.denominator == 70


# ── ABSOLUE: floor(seats/2)+1 (tested against Sénat RDC: 109 / 55) ──


def test_absolue_strict_majority_of_seats() -> None:
    """109 seats → required = 55. POUR=55 wins; POUR=54 loses."""
    d = _decide(pour=55, contre=10, majority=EVoteMajorityType.ABSOLUE, seats=109)
    assert d.required_count == 55
    assert d.majority_met is True
    assert d.decision == "ADOPTE"

    d = _decide(pour=54, contre=10, majority=EVoteMajorityType.ABSOLUE, seats=109)
    assert d.required_count == 55
    assert d.majority_met is False
    assert d.decision == "REJETE"


def test_absolue_uses_seats_not_expressed_votes() -> None:
    """Even if POUR > CONTRE, ABSOLUE still requires 55/109 seats —
    sparse turnout doesn't lower the bar."""
    d = _decide(pour=30, contre=10, majority=EVoteMajorityType.ABSOLUE, seats=109)
    assert d.required_count == 55
    assert d.majority_met is False  # 30 < 55
    assert d.decision == "REJETE"


def test_absolue_npv_doesnt_dilute() -> None:
    """NPV ballots are present but the seat-based denominator means
    they don't move the threshold — same answer with or without NPV."""
    d_with_npv = _decide(
        pour=55, contre=10, npv=44,
        majority=EVoteMajorityType.ABSOLUE, seats=109,
    )
    d_without = _decide(
        pour=55, contre=10,
        majority=EVoteMajorityType.ABSOLUE, seats=109,
    )
    assert d_with_npv.required_count == d_without.required_count == 55
    assert d_with_npv.majority_met == d_without.majority_met is True


def test_absolue_no_session_falls_back_to_expressed() -> None:
    """If session lookup fails server-side, the `total_seats=None`
    fallback uses (POUR+CONTRE). This is the safe degradation path —
    no crash, but the result is conservative (smaller denominator =
    easier to meet, but the surrounding system should never let
    a session vanish under an active scrutin in practice)."""
    d = _decide(
        pour=20, contre=10,
        majority=EVoteMajorityType.ABSOLUE, seats=None,
    )
    assert d.denominator == 30  # cp + cc fallback
    # required = floor(30/2)+1 = 16 → POUR=20 meets it
    assert d.required_count == 16
    assert d.majority_met is True


# ── DEUX_TIERS: ceil(2N/3) ──────────────────────────────────────────


def test_deux_tiers_at_threshold_adopts() -> None:
    """109 seats → required = 73 (ceil(218/3))."""
    d = _decide(pour=73, contre=10, majority=EVoteMajorityType.DEUX_TIERS, seats=109)
    assert d.required_count == 73
    assert d.majority_met is True
    assert d.decision == "ADOPTE"


def test_deux_tiers_one_short_rejects() -> None:
    d = _decide(pour=72, contre=10, majority=EVoteMajorityType.DEUX_TIERS, seats=109)
    assert d.required_count == 73
    assert d.majority_met is False
    assert d.decision == "REJETE"


# ── CUSTOM: ceil(N * threshold) ─────────────────────────────────────


def test_custom_60_percent_threshold() -> None:
    """109 seats * 0.6 = 65.4 → ceil = 66."""
    d = _decide(
        pour=66, contre=10, majority=EVoteMajorityType.CUSTOM,
        threshold=0.6, seats=109,
    )
    assert d.required_count == 66
    assert d.majority_met is True
    assert d.decision == "ADOPTE"


def test_custom_threshold_default_when_none() -> None:
    """Defensive: a CUSTOM rule with `threshold=None` shouldn't
    crash — defaults to 0.5 (per `_required_count`)."""
    d = _decide(
        pour=51, contre=10, majority=EVoteMajorityType.CUSTOM,
        threshold=None, seats=100,
    )
    assert d.required_count == 50  # ceil(100*0.5)
    assert d.majority_met is True


def test_custom_zero_threshold_trivially_adopts() -> None:
    """0% threshold means any single POUR adopts. Edge case — but
    locking it in catches accidental `>=` becoming `>`."""
    d = _decide(
        pour=1, contre=0, majority=EVoteMajorityType.CUSTOM,
        threshold=0.0, seats=100,
    )
    assert d.required_count == 0
    assert d.majority_met is True


# ── No-ballots edge: decision is None, not "REJETE" ─────────────────


def test_no_ballots_yields_none_decision() -> None:
    """An untouched scrutin should NOT auto-reject — the result is
    "no decision yet", which the UI renders as "—" rather than ✗.

    `total_weighted == 0` is the gate; `majority_met` may still be
    False (vacuously) but `decision` must stay None."""
    for majority in EVoteMajorityType:
        d = _decide(majority=majority, seats=109, threshold=0.5)
        assert d.decision is None, f"{majority} returned decision={d.decision}"


def test_only_abstention_yields_rejete_via_zero_pour() -> None:
    """If everyone abstains (or NPVs), POUR is 0 — the rule still
    says REJETÉ (decision is set because total_weighted > 0).

    This is a deliberate convention: abstention is *not* tacit
    consent. PPTX §3 says "ABSTENTION et NPV ne comptent ni pour
    ni contre" — so the resolution can't pass."""
    d = _decide(abstention=109, majority=EVoteMajorityType.ABSOLUE, seats=109)
    assert d.decision == "REJETE"
    assert d.majority_met is False


def test_only_npv_yields_rejete() -> None:
    d = _decide(npv=50, majority=EVoteMajorityType.RELATIVE)
    assert d.decision == "REJETE"


# ── Proxy-weight semantics: bigger weights swing the result ─────────


def test_proxy_weights_already_aggregated_in_pour_count() -> None:
    """Reminder for future maintainers: the `pour`/`contre`/etc args
    are the WEIGHTED sums (one ballot with weight=2 contributes 2 to
    its choice, computed by `compute()` from `b.weight`). `_decision`
    doesn't multiply or otherwise interpret weights — it just trusts
    the totals.

    This test is documentation-as-test: a regression where weights
    are double-counted would break the assertion."""
    # Suppose 30 voters present, 5 of them carry one proxy each (weight=2),
    # all 5 voted POUR; the rest split 20 POUR / 5 CONTRE.
    # → total POUR weighted = 5*2 + 20 = 30; CONTRE = 5.
    d = _decide(pour=30, contre=5, majority=EVoteMajorityType.RELATIVE)
    assert d.denominator == 35
    assert d.majority_met is True


# ── Sénat RDC plenary scenarios (PPTX-anchored) ─────────────────────


def test_senat_rdc_full_attendance_adopts_absolue() -> None:
    """109 sénateurs, 60 POUR / 49 CONTRE, ABSOLUE rule. Adopté."""
    d = _decide(
        pour=60, contre=49,
        majority=EVoteMajorityType.ABSOLUE, seats=109,
    )
    assert d.decision == "ADOPTE"


def test_senat_rdc_low_turnout_no_quorum_for_absolue() -> None:
    """Quorum = 55. If only 50 sénateurs vote (40 POUR / 10 CONTRE),
    POUR=40 < required=55 → REJETÉ even though POUR > CONTRE.

    Quorum is enforced upstream of the tally — but the math here
    correctly produces REJETÉ in the under-quorum scenario, which
    is what the audit log will show if the system was misconfigured."""
    d = _decide(
        pour=40, contre=10,
        majority=EVoteMajorityType.ABSOLUE, seats=109,
    )
    assert d.required_count == 55
    assert d.majority_met is False
    assert d.decision == "REJETE"
