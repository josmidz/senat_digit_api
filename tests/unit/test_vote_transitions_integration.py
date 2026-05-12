"""Integration of `VoteService._transition` with the FSM matrix.

`test_vote_fsm_transitions.py` covers `_can_transition` as a pure
function. This file exercises the wired-up `_transition` method —
making sure that:

  1. allowed transitions actually mutate cfg.status and persist;
  2. disallowed transitions raise WITHOUT mutating cfg.status (so a
     failed call leaves the model in a clean, retry-safe state);
  3. timestamp side-fields (`opened_at`, `closed_at`, …) are populated
     when present, so the audit timeline stays accurate.

And the `patch` precondition (PROJET-only) is locked in here too.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.vote.enums.vote_enum import EVoteStatus
from .conftest import make_config


# ── happy-path FSM transitions via the public methods ───────────────


@pytest.mark.asyncio
async def test_open_sets_status_and_opened_at(service_with_loaded) -> None:
    cfg = make_config(status=EVoteStatus.PROJET)
    svc, _, save_mock = service_with_loaded(cfg)

    out = await svc.open("ignored")

    assert out.status == EVoteStatus.OUVERT
    assert out.opened_at is not None
    assert out.opened_at.tzinfo == timezone.utc
    save_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_suspend_sets_status_and_suspended_at(service_with_loaded) -> None:
    cfg = make_config(status=EVoteStatus.OUVERT)
    svc, _, save_mock = service_with_loaded(cfg)

    out = await svc.suspend("ignored")

    assert out.status == EVoteStatus.SUSPENDU
    assert out.suspended_at is not None
    save_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_from_ouvert_sets_status_and_closed_at(
    service_with_loaded,
) -> None:
    cfg = make_config(status=EVoteStatus.OUVERT)
    svc, _, save_mock = service_with_loaded(cfg)

    out = await svc.close("ignored")

    assert out.status == EVoteStatus.CLOS
    assert out.closed_at is not None
    save_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_from_suspendu_works(service_with_loaded) -> None:
    """SUSPENDU → CLOS is the "skip the resume" path: greffier ends
    debate without re-opening the floor."""
    cfg = make_config(status=EVoteStatus.SUSPENDU)
    svc, _, _ = service_with_loaded(cfg)

    out = await svc.close("ignored")
    assert out.status == EVoteStatus.CLOS


@pytest.mark.asyncio
async def test_validate_from_clos(service_with_loaded) -> None:
    cfg = make_config(status=EVoteStatus.CLOS)
    svc, _, save_mock = service_with_loaded(cfg)

    out = await svc.validate("ignored")

    assert out.status == EVoteStatus.VALIDE
    assert out.validated_at is not None
    save_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_annul_from_clos(service_with_loaded) -> None:
    cfg = make_config(status=EVoteStatus.CLOS)
    svc, _, _ = service_with_loaded(cfg)

    out = await svc.annul("ignored")
    assert out.status == EVoteStatus.ANNULE


# ── disallowed transitions raise without mutation ───────────────────


@pytest.mark.asyncio
async def test_open_from_clos_rejected(service_with_loaded) -> None:
    """A closed scrutin can't be re-opened — defends against the most
    likely "oh no" scenario where the greffier double-clicks Ouvrir
    after clôture."""
    cfg = make_config(status=EVoteStatus.CLOS)
    svc, _, save_mock = service_with_loaded(cfg)

    with pytest.raises(ValueError, match="refusée"):
        await svc.open("ignored")
    assert cfg.status == EVoteStatus.CLOS
    save_mock.assert_not_called()


@pytest.mark.asyncio
async def test_validate_from_ouvert_rejected(service_with_loaded) -> None:
    """Validation requires CLOS first — you can't ratify a result for
    a vote that's still accepting ballots."""
    cfg = make_config(status=EVoteStatus.OUVERT)
    svc, _, save_mock = service_with_loaded(cfg)

    with pytest.raises(ValueError, match="refusée"):
        await svc.validate("ignored")
    assert cfg.status == EVoteStatus.OUVERT
    save_mock.assert_not_called()


@pytest.mark.asyncio
async def test_open_from_validated_rejected(service_with_loaded) -> None:
    """VALIDE is terminal — the most important guarantee of the FSM."""
    cfg = make_config(status=EVoteStatus.VALIDE)
    svc, _, save_mock = service_with_loaded(cfg)

    with pytest.raises(ValueError, match="refusée"):
        await svc.open("ignored")
    assert cfg.status == EVoteStatus.VALIDE
    save_mock.assert_not_called()


@pytest.mark.asyncio
async def test_close_from_projet_rejected(service_with_loaded) -> None:
    """PROJET → CLOS is disallowed — the scrutin must be opened first
    so participants have a window to cast (or explicitly NPV)."""
    cfg = make_config(status=EVoteStatus.PROJET)
    svc, _, save_mock = service_with_loaded(cfg)

    with pytest.raises(ValueError, match="refusée"):
        await svc.close("ignored")
    save_mock.assert_not_called()


# ── self-transition short-circuit (no DB write) ─────────────────────


@pytest.mark.asyncio
async def test_open_when_already_ouvert_is_idempotent(
    service_with_loaded,
) -> None:
    """The service short-circuits `target == current` and returns
    early without writing. Important so a noisy retry from the client
    doesn't churn the audit chain or `opened_at` timestamp."""
    cfg = make_config(status=EVoteStatus.OUVERT)
    svc, _, save_mock = service_with_loaded(cfg)

    out = await svc.open("ignored")
    assert out.status == EVoteStatus.OUVERT
    save_mock.assert_not_called()


# ── patch (PROJET-only) ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_succeeds_in_projet(service_with_loaded) -> None:
    cfg = make_config(status=EVoteStatus.PROJET)
    svc, _, save_mock = service_with_loaded(cfg)

    out = await svc.patch(
        "ignored",
        title="Renamed scrutin",
        duration_seconds=120,
        allow_proxies=False,
    )
    assert out.title == "Renamed scrutin"
    assert out.duration_seconds == 120
    assert out.allow_proxies is False
    save_mock.assert_awaited_once()


@pytest.mark.parametrize(
    "status",
    [
        EVoteStatus.OUVERT,
        EVoteStatus.SUSPENDU,
        EVoteStatus.CLOS,
        EVoteStatus.VALIDE,
        EVoteStatus.ANNULE,
    ],
    ids=["OUVERT", "SUSPENDU", "CLOS", "VALIDE", "ANNULE"],
)
@pytest.mark.asyncio
async def test_patch_rejected_outside_projet(
    service_with_loaded, status: EVoteStatus,
) -> None:
    """Soft-field PATCH is forbidden once the scrutin has been
    opened — by then sénateurs have seen the title/duration and we
    must not change it under them."""
    cfg = make_config(status=status)
    svc, _, save_mock = service_with_loaded(cfg)

    with pytest.raises(ValueError, match="PROJET"):
        await svc.patch("ignored", title="late rename")
    save_mock.assert_not_called()
