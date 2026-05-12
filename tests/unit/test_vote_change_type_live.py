"""`VoteService.change_type_live` invariants.

PPTX slide 15 (memory: senat_pptx_requirements §3) allows changing the
ballot type / secrecy / majority of a scrutin "en direct pendant
l'assemblée" — but only BEFORE the first ballot is cast. Once a single
voter has consented under the published rule, the rule is frozen.

These tests lock that invariant down. If a refactor accidentally lets
the gate slip — for instance, by re-ordering the precondition checks
so the `ballots_cast_count` check runs after `cfg.save()` — pytest
fails immediately rather than waiting for a regression in the wild.
"""
from __future__ import annotations

import pytest

from app.modules.vote.enums.vote_enum import (
    EVoteBallotType,
    EVoteMajorityType,
    EVoteStatus,
)
from .conftest import make_config


# ── ballots-cast gate (the critical invariant) ──────────────────────


@pytest.mark.parametrize(
    "status",
    [EVoteStatus.PROJET, EVoteStatus.OUVERT, EVoteStatus.SUSPENDU],
    ids=["PROJET", "OUVERT", "SUSPENDU"],
)
@pytest.mark.asyncio
async def test_change_type_rejected_after_first_ballot(
    service_with_loaded, status: EVoteStatus,
) -> None:
    """Even in an otherwise eligible status, ONE ballot freezes the rules."""
    cfg = make_config(status=status, ballots_cast_count=1)
    svc, _, save_mock = service_with_loaded(cfg)

    with pytest.raises(ValueError, match="bulletin"):
        await svc.change_type_live(
            vote_config_id="ignored",
            new_ballot_type=EVoteBallotType.UNINOMINAL,
            new_is_secret=None,
            new_majority_type=None,
            new_majority_custom_threshold=None,
        )
    save_mock.assert_not_called()


# ── status-gate (terminal states are off-limits) ────────────────────


@pytest.mark.parametrize(
    "status",
    [EVoteStatus.CLOS, EVoteStatus.VALIDE, EVoteStatus.ANNULE],
    ids=["CLOS", "VALIDE", "ANNULE"],
)
@pytest.mark.asyncio
async def test_change_type_rejected_in_terminal_or_post_close(
    service_with_loaded, status: EVoteStatus,
) -> None:
    """The "live" in change_type_live ends at CLOS. Past that, results
    have been computed (or are about to be) and the type is frozen."""
    cfg = make_config(status=status, ballots_cast_count=0)
    svc, _, save_mock = service_with_loaded(cfg)

    with pytest.raises(ValueError, match="état"):
        await svc.change_type_live(
            vote_config_id="ignored",
            new_ballot_type=EVoteBallotType.UNINOMINAL,
            new_is_secret=None,
            new_majority_type=None,
            new_majority_custom_threshold=None,
        )
    save_mock.assert_not_called()


# ── happy paths ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "status",
    [EVoteStatus.PROJET, EVoteStatus.OUVERT, EVoteStatus.SUSPENDU],
    ids=["PROJET", "OUVERT", "SUSPENDU"],
)
@pytest.mark.asyncio
async def test_change_ballot_type_succeeds_when_no_ballots(
    service_with_loaded, status: EVoteStatus,
) -> None:
    cfg = make_config(
        status=status,
        ballots_cast_count=0,
        ballot_type=EVoteBallotType.OUI_NON,
    )
    svc, _, save_mock = service_with_loaded(cfg)

    out = await svc.change_type_live(
        vote_config_id="ignored",
        new_ballot_type=EVoteBallotType.UNINOMINAL,
        new_is_secret=None,
        new_majority_type=None,
        new_majority_custom_threshold=None,
    )
    assert out.ballot_type == EVoteBallotType.UNINOMINAL
    save_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_majority_type_succeeds(service_with_loaded) -> None:
    cfg = make_config(
        status=EVoteStatus.PROJET,
        ballots_cast_count=0,
        majority_type=EVoteMajorityType.RELATIVE,
    )
    svc, _, save_mock = service_with_loaded(cfg)

    out = await svc.change_type_live(
        vote_config_id="ignored",
        new_ballot_type=None,
        new_is_secret=None,
        new_majority_type=EVoteMajorityType.DEUX_TIERS,
        new_majority_custom_threshold=None,
    )
    assert out.majority_type == EVoteMajorityType.DEUX_TIERS
    save_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_to_custom_majority_with_threshold(
    service_with_loaded,
) -> None:
    cfg = make_config(status=EVoteStatus.PROJET, ballots_cast_count=0)
    svc, _, save_mock = service_with_loaded(cfg)

    out = await svc.change_type_live(
        vote_config_id="ignored",
        new_ballot_type=None,
        new_is_secret=None,
        new_majority_type=EVoteMajorityType.CUSTOM,
        new_majority_custom_threshold=0.6,
    )
    assert out.majority_type == EVoteMajorityType.CUSTOM
    assert out.majority_custom_threshold == pytest.approx(0.6)
    save_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_partial_change_only_touches_provided_fields(
    service_with_loaded,
) -> None:
    """Sparse payload semantics: untouched fields keep their value."""
    cfg = make_config(
        status=EVoteStatus.PROJET,
        ballots_cast_count=0,
        ballot_type=EVoteBallotType.LISTE,
        majority_type=EVoteMajorityType.ABSOLUE,
    )
    svc, _, _ = service_with_loaded(cfg)

    out = await svc.change_type_live(
        vote_config_id="ignored",
        new_ballot_type=EVoteBallotType.OUI_NON,  # only this changes
        new_is_secret=None,
        new_majority_type=None,
        new_majority_custom_threshold=None,
    )
    assert out.ballot_type == EVoteBallotType.OUI_NON
    assert out.majority_type == EVoteMajorityType.ABSOLUE
    assert out.is_secret is False  # default from make_config


# ── secret-vote crypto handling ─────────────────────────────────────


@pytest.mark.asyncio
async def test_toggle_off_secret_drops_sealed_dek(
    service_with_loaded, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """is_secret True → False: sealed_dek_b64 is cleared.

    Defence-in-depth — even if the DEK leaks later from elsewhere,
    a config that no longer claims `is_secret=True` shouldn't carry
    the sealed key around."""
    cfg = make_config(
        status=EVoteStatus.PROJET,
        ballots_cast_count=0,
        is_secret=True,
        sealed_dek_b64="prev-sealed-key-base64",
    )
    svc, _, _ = service_with_loaded(cfg)

    out = await svc.change_type_live(
        vote_config_id="ignored",
        new_ballot_type=None,
        new_is_secret=False,
        new_majority_type=None,
        new_majority_custom_threshold=None,
    )
    assert out.is_secret is False
    assert out.sealed_dek_b64 is None


@pytest.mark.asyncio
async def test_toggle_on_secret_seals_a_fresh_dek(
    service_with_loaded, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """is_secret False → True: a new sealed DEK is generated.

    We mock the per-org crypto resolver because building a real one
    needs `CfgStorageModel` lookups; the contract under test is "the
    service calls the crypto layer and stores the result", not the
    crypto layer itself (separate test target)."""
    from unittest.mock import AsyncMock, MagicMock

    # Mock VoteCryptoService.for_org → returns a service that yields
    # deterministic dek + sealed bytes.
    fake_crypto = MagicMock()
    fake_crypto.generate_dek = MagicMock(return_value=b"dek-32-bytes")
    fake_crypto.seal_dek = MagicMock(return_value="sealed-base64-str")
    fake_for_org = AsyncMock(return_value=fake_crypto)
    monkeypatch.setattr(
        "app.modules.vote.services.vote_service.VoteCryptoService.for_org",
        fake_for_org,
    )

    cfg = make_config(
        status=EVoteStatus.PROJET,
        ballots_cast_count=0,
        is_secret=False,
        sealed_dek_b64=None,
    )
    svc, _, _ = service_with_loaded(cfg)

    out = await svc.change_type_live(
        vote_config_id="ignored",
        new_ballot_type=None,
        new_is_secret=True,
        new_majority_type=None,
        new_majority_custom_threshold=None,
    )
    assert out.is_secret is True
    assert out.sealed_dek_b64 == "sealed-base64-str"
    fake_crypto.generate_dek.assert_called_once()
    fake_crypto.seal_dek.assert_called_once_with(b"dek-32-bytes")
