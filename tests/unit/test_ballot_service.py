"""`BallotService.cast` — security-critical invariants.

The cast endpoint is the single most security-sensitive path in the
vote module. Three guarantees we lock down here:

  1. **Status gate** — `cfg.status` must be OUVERT. PROJET, CLOS,
     VALIDE, ANNULE, SUSPENDU all reject. Defends against the most
     likely race: a sénateur taps "Pour" right as the greffier
     suspends or closes the scrutin.

  2. **No double voting** — public scrutins reject on a
     (vote_config_id, voter_user_id) lookup; secret scrutins decrypt
     each existing ballot's `voter_user_id_enc` and reject on match.
     The secret path is O(N) by design (small N for plenary scale).

  3. **Secret-vote anonymity** — when `cfg.is_secret`, the persisted
     ballot has `voter_user_id == None` and `voter_user_id_enc != None`.
     The audit chain row for VOTE_CAST has `actor_user_id == None`
     (PPTX slide 15 invariant: "the chain proves a ballot was cast,
     not who cast it").

Plus the proxy-weight rule: `weight = 1 + len(active_proxies_held)`
when `allow_proxies`, else 1.

Mocking strategy follows `test_audit_chain_verify.py`: monkeypatch
the Beanie classmethods (`get`, `find_one`, `find`, `insert`) and the
class-level expression descriptors that the service's query DSL
evaluates at runtime.
"""
from __future__ import annotations

from typing import List
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.modules.vote.enums.vote_enum import (
    EVoteBallotType,
    EVoteChoice,
    EVoteMajorityType,
    EVoteStatus,
)
from app.modules.vote.models.vote_ballot.vote_ballot_model import (
    VoteBallotModel,
)
from app.modules.vote.models.vote_config.vote_config_model import (
    VoteConfigModel,
)
from app.modules.vote.services.ballot_service import BallotService

from .conftest import make_ballot, make_config


# ── Harness ────────────────────────────────────────────────────────


class _ExprStub:
    """Same shape as the audit-chain test stub. Beanie's class-level
    field descriptors aren't initialized without `init_beanie`, so any
    `Model.field == value` expression in production code would
    AttributeError. We swap the field for an instance that returns
    itself from every comparison — the patched `find` / `find_one`
    ignore the resulting expression."""
    def __eq__(self, other): return self
    def __ne__(self, other): return self
    def __ge__(self, other): return self
    def __le__(self, other): return self
    def __gt__(self, other): return self
    def __lt__(self, other): return self
    def __pos__(self): return self
    def __neg__(self): return self
    def __hash__(self): return 0


@pytest.fixture
def cast_harness(monkeypatch: pytest.MonkeyPatch):
    """One-stop fixture for `BallotService.cast` tests.

    Returns a callable that wires up:
      - `VoteConfigModel.get` → returns the supplied cfg
      - `VoteBallotModel.find_one` → returns supplied existing ballot or None
      - `VoteBallotModel.find().to_list` → returns supplied list (secret-scan path)
      - Each constructed VoteBallotModel's `.insert` → AsyncMock no-op
      - `cfg.save` → AsyncMock no-op
      - `ProxyService.active_for_holder` → returns supplied proxy list
      - `VoteCryptoService.for_org` → returns a deterministic stub
        (`encrypt_voter_id` returns f"enc:<voter_id>", decrypt is the
        reverse, unseal_dek returns a fixed bytes value)

    Returns a SimpleNamespace-like dict with handles to the mocks so
    tests can assert call-arity + arguments.
    """
    from types import SimpleNamespace

    # Stub class-level descriptors used in query expressions
    for field in ("vote_config_id", "voter_user_id"):
        monkeypatch.setattr(VoteBallotModel, field, _ExprStub(), raising=False)

    # `BallotService.cast` constructs `VoteBallotModel(...)` directly,
    # which hits Beanie's `Document.__init__` → `get_motor_collection()`.
    # Without `init_beanie` that raises `CollectionWasNotInitialized`.
    # Stub the lookup to a MagicMock — Beanie's __init__ uses it as a
    # presence check, never actually inserts via the returned object
    # (we patch `.insert` separately below).
    monkeypatch.setattr(
        VoteBallotModel,
        "get_motor_collection",
        classmethod(lambda cls: MagicMock(name="motor_collection_stub")),
    )

    def _factory(
        *,
        cfg: VoteConfigModel,
        existing_public_ballot: VoteBallotModel | None = None,
        existing_secret_ballots: List[VoteBallotModel] | None = None,
        active_proxies: List | None = None,
    ):
        # ---- VoteConfigModel.get ---------------------------------
        get_mock = AsyncMock(return_value=cfg)
        monkeypatch.setattr(VoteConfigModel, "get", get_mock)

        # ---- VoteConfigModel.save (instance method) --------------
        cfg_save = AsyncMock()
        object.__setattr__(cfg, "save", cfg_save)

        # ---- VoteBallotModel.find_one (public-vote dup) ----------
        find_one_mock = AsyncMock(return_value=existing_public_ballot)
        monkeypatch.setattr(VoteBallotModel, "find_one", find_one_mock)

        # ---- VoteBallotModel.find().to_list (secret-vote scan) ---
        find_stub = MagicMock()
        find_stub.find.return_value = find_stub

        async def fake_to_list():
            return existing_secret_ballots or []
        find_stub.to_list = fake_to_list
        monkeypatch.setattr(VoteBallotModel, "find", lambda *a, **kw: find_stub)

        # ---- VoteBallotModel.insert (instance method on whichever
        #      ballot the service constructs). We can't reach the
        #      instance from outside, so patch at the class:
        # ----  every instance shares this AsyncMock. -------------
        insert_mock = AsyncMock()
        monkeypatch.setattr(VoteBallotModel, "insert", insert_mock)

        # ---- ProxyService.active_for_holder ----------------------
        from app.modules.vote.services.proxy_service import ProxyService
        active_mock = AsyncMock(return_value=active_proxies or [])
        monkeypatch.setattr(ProxyService, "active_for_holder", active_mock)

        # ---- VoteCryptoService.for_org + crypto methods ----------
        crypto = MagicMock(name="VoteCryptoServiceStub")
        crypto.unseal_dek = MagicMock(return_value=b"dek-32-bytes-deterministic")

        # encrypt_voter_id(dek, voter_str) → "enc:<voter>" (round-trippable)
        crypto.encrypt_voter_id = MagicMock(side_effect=lambda dek, vid: f"enc:{vid}")
        # decrypt mirrors that stripping the "enc:" prefix.
        def _decrypt(dek, ct):
            if not ct.startswith("enc:"):
                raise ValueError("tampered")
            return ct[len("enc:"):]
        crypto.decrypt_voter_id = MagicMock(side_effect=_decrypt)

        from app.modules.vote.services.vote_crypto_service import (
            VoteCryptoService,
        )
        for_org_mock = AsyncMock(return_value=crypto)
        monkeypatch.setattr(VoteCryptoService, "for_org", for_org_mock)

        # Audit chain emit — already neutered by the autouse
        # `freeze_audit_and_notify` fixture in conftest, but we capture
        # a handle to assert on what would have been emitted.
        audit_calls: list[dict] = []
        import app.modules.audit_security.services.audit_chain_service as ac

        class _CapturingAudit:
            def __init__(self, *_a, **_kw): ...
            async def emit(self, **kwargs):
                audit_calls.append(kwargs)
                return None

        monkeypatch.setattr(ac, "AuditChainService", _CapturingAudit)

        return SimpleNamespace(
            get_mock=get_mock,
            cfg_save=cfg_save,
            find_one_mock=find_one_mock,
            insert_mock=insert_mock,
            active_proxies_mock=active_mock,
            crypto=crypto,
            for_org_mock=for_org_mock,
            audit_calls=audit_calls,
        )

    return _factory


# ── Status gate ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "status",
    [
        EVoteStatus.PROJET,
        EVoteStatus.SUSPENDU,
        EVoteStatus.CLOS,
        EVoteStatus.VALIDE,
        EVoteStatus.ANNULE,
    ],
    ids=["PROJET", "SUSPENDU", "CLOS", "VALIDE", "ANNULE"],
)
@pytest.mark.asyncio
async def test_cast_rejects_when_scrutin_not_ouvert(
    cast_harness, status: EVoteStatus,
) -> None:
    cfg = make_config(status=status)
    h = cast_harness(cfg=cfg)
    svc = BallotService("fr")

    with pytest.raises(ValueError, match="non ouvert"):
        await svc.cast(
            vote_config_id="000000000000000000000001",
            voter_user_id=PydanticObjectId(),
            choice=EVoteChoice.POUR,
        )
    h.insert_mock.assert_not_called()
    h.cfg_save.assert_not_called()


@pytest.mark.asyncio
async def test_cast_rejects_when_scrutin_not_found(cast_harness) -> None:
    """Defensive: a vanished cfg row should surface a clear error,
    not a None-deref on `cfg.status`."""
    cfg = make_config(status=EVoteStatus.OUVERT)
    h = cast_harness(cfg=cfg)
    h.get_mock.return_value = None  # override
    svc = BallotService("fr")

    with pytest.raises(ValueError, match="introuvable"):
        await svc.cast(
            vote_config_id="000000000000000000000001",
            voter_user_id=PydanticObjectId(),
            choice=EVoteChoice.POUR,
        )


# ── Public-vote dup detection ──────────────────────────────────────


@pytest.mark.asyncio
async def test_cast_public_vote_succeeds_no_duplicate(cast_harness) -> None:
    cfg = make_config(status=EVoteStatus.OUVERT, is_secret=False)
    voter = PydanticObjectId()
    h = cast_harness(cfg=cfg)
    svc = BallotService("fr")

    ballot = await svc.cast(
        vote_config_id="000000000000000000000001",
        voter_user_id=voter,
        choice=EVoteChoice.POUR,
    )
    assert ballot.voter_user_id == voter
    assert ballot.voter_user_id_enc is None
    assert ballot.choice == EVoteChoice.POUR
    h.insert_mock.assert_awaited_once()
    h.cfg_save.assert_awaited_once()
    assert cfg.ballots_cast_count == 1


@pytest.mark.asyncio
async def test_cast_public_vote_rejects_duplicate(cast_harness) -> None:
    """Same voter, same scrutin, second cast → reject. Defends against
    the screen's most-likely bug: a "submit" button double-tap.

    The notifier swallows the second 409 and refreshes; the cast count
    on the cfg stays at whatever the first call set it to."""
    cfg = make_config(status=EVoteStatus.OUVERT, is_secret=False)
    voter = PydanticObjectId()
    existing = make_ballot(
        vote_config_id=cfg.id, voter_user_id=voter, choice="POUR",
    )
    h = cast_harness(cfg=cfg, existing_public_ballot=existing)
    svc = BallotService("fr")

    with pytest.raises(ValueError, match="déjà voté"):
        await svc.cast(
            vote_config_id="000000000000000000000001",
            voter_user_id=voter,
            choice=EVoteChoice.CONTRE,
        )
    h.insert_mock.assert_not_called()
    h.cfg_save.assert_not_called()


# ── Secret-vote dup detection ──────────────────────────────────────


@pytest.mark.asyncio
async def test_cast_secret_vote_succeeds_no_duplicate(cast_harness) -> None:
    """SECRET path: dup-detection scans existing ballots' encrypted
    voter ids. With no existing ballots, the cast proceeds.

    The persisted ballot must have `voter_user_id_enc` set and
    `voter_user_id` left as None — the secrecy guarantee."""
    cfg = make_config(
        status=EVoteStatus.OUVERT,
        is_secret=True,
        sealed_dek_b64="sealed-key",
    )
    voter = PydanticObjectId()
    h = cast_harness(cfg=cfg, existing_secret_ballots=[])
    svc = BallotService("fr")

    ballot = await svc.cast(
        vote_config_id="000000000000000000000001",
        voter_user_id=voter,
        choice=EVoteChoice.POUR,
    )
    assert ballot.voter_user_id is None
    assert ballot.voter_user_id_enc == f"enc:{voter}"
    h.insert_mock.assert_awaited_once()
    h.cfg_save.assert_awaited_once()
    h.crypto.unseal_dek.assert_called()
    h.crypto.encrypt_voter_id.assert_called()


@pytest.mark.asyncio
async def test_cast_secret_vote_rejects_duplicate(cast_harness) -> None:
    """Existing ciphertext decrypts to this voter → reject. The scan
    is what enforces uniqueness in the secret-vote case (the model
    has no unique index on voter_user_id since it's null for secret)."""
    cfg = make_config(
        status=EVoteStatus.OUVERT,
        is_secret=True,
        sealed_dek_b64="sealed-key",
    )
    voter = PydanticObjectId()
    # Deterministic crypto stub: encrypt = "enc:<voter>". Construct an
    # existing ballot whose voter_user_id_enc decrypts to the same id.
    existing = make_ballot(
        vote_config_id=cfg.id,
        voter_user_id=None,
        voter_user_id_enc=f"enc:{voter}",
        choice="CONTRE",
    )
    h = cast_harness(cfg=cfg, existing_secret_ballots=[existing])
    svc = BallotService("fr")

    with pytest.raises(ValueError, match="déjà voté"):
        await svc.cast(
            vote_config_id="000000000000000000000001",
            voter_user_id=voter,
            choice=EVoteChoice.POUR,
        )
    h.insert_mock.assert_not_called()


@pytest.mark.asyncio
async def test_cast_secret_vote_skips_tampered_ciphertexts(cast_harness) -> None:
    """A row whose `voter_user_id_enc` doesn't decrypt cleanly (tamper /
    DEK rotation gone wrong) is skipped during the dup scan rather
    than blocking honest voters. The tally service surfaces the
    inconsistency separately."""
    cfg = make_config(
        status=EVoteStatus.OUVERT,
        is_secret=True,
        sealed_dek_b64="sealed-key",
    )
    voter = PydanticObjectId()
    # First ballot is tampered (no "enc:" prefix → decrypt raises).
    # Second is for a different voter — also decrypts but doesn't match.
    tampered = make_ballot(
        vote_config_id=cfg.id,
        voter_user_id_enc="garbled-bytes",
    )
    other = make_ballot(
        vote_config_id=cfg.id,
        voter_user_id_enc=f"enc:{PydanticObjectId()}",
    )
    h = cast_harness(
        cfg=cfg, existing_secret_ballots=[tampered, other],
    )
    svc = BallotService("fr")

    # Should succeed — neither row blocks the cast.
    ballot = await svc.cast(
        vote_config_id="000000000000000000000001",
        voter_user_id=voter,
        choice=EVoteChoice.POUR,
    )
    assert ballot.voter_user_id_enc == f"enc:{voter}"
    h.insert_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_cast_secret_vote_rejects_when_dek_missing(cast_harness) -> None:
    """`sealed_dek_b64=None` on a secret-vote cfg is incoherent state.
    Surface a clear error rather than crashing — the audit chain will
    capture the issue at the next verify pass."""
    cfg = make_config(
        status=EVoteStatus.OUVERT,
        is_secret=True,
        sealed_dek_b64=None,  # incoherent
    )
    h = cast_harness(cfg=cfg, existing_secret_ballots=[])
    svc = BallotService("fr")

    with pytest.raises(ValueError, match="DEK manquante"):
        await svc.cast(
            vote_config_id="000000000000000000000001",
            voter_user_id=PydanticObjectId(),
            choice=EVoteChoice.POUR,
        )
    h.insert_mock.assert_not_called()


# ── Proxy weight ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cast_weight_is_one_when_no_proxies(cast_harness) -> None:
    cfg = make_config(status=EVoteStatus.OUVERT, is_secret=False)
    h = cast_harness(cfg=cfg, active_proxies=[])
    svc = BallotService("fr")

    ballot = await svc.cast(
        vote_config_id="000000000000000000000001",
        voter_user_id=PydanticObjectId(),
        choice=EVoteChoice.POUR,
    )
    assert ballot.weight == 1
    assert ballot.proxy_grantor_user_ids == []


@pytest.mark.asyncio
async def test_cast_weight_includes_active_proxies(cast_harness) -> None:
    """One sénateur holds three proxies → weight 4 (self + 3)."""
    cfg = make_config(status=EVoteStatus.OUVERT, is_secret=False)
    granters = [PydanticObjectId() for _ in range(3)]
    proxies = [
        MagicMock(granter_user_id=g) for g in granters
    ]
    h = cast_harness(cfg=cfg, active_proxies=proxies)
    svc = BallotService("fr")

    ballot = await svc.cast(
        vote_config_id="000000000000000000000001",
        voter_user_id=PydanticObjectId(),
        choice=EVoteChoice.POUR,
    )
    assert ballot.weight == 4
    assert ballot.proxy_grantor_user_ids == granters


@pytest.mark.asyncio
async def test_cast_ignores_proxies_when_allow_proxies_false(cast_harness) -> None:
    """When the scrutin's `allow_proxies=False`, the proxy service is
    NOT consulted at all — weight stays 1 even if the voter holds
    active proxies for the séance.

    Defends against a config drift where proxies-disallowed scrutins
    accidentally count proxy weight."""
    cfg = make_config(status=EVoteStatus.OUVERT, is_secret=False)
    cfg.allow_proxies = False
    h = cast_harness(
        cfg=cfg,
        # The proxy list would yield weight=3 IF consulted. We expect it isn't.
        active_proxies=[MagicMock(granter_user_id=PydanticObjectId())] * 2,
    )
    svc = BallotService("fr")

    ballot = await svc.cast(
        vote_config_id="000000000000000000000001",
        voter_user_id=PydanticObjectId(),
        choice=EVoteChoice.POUR,
    )
    assert ballot.weight == 1
    h.active_proxies_mock.assert_not_called()


# ── ballots_cast_count increment ───────────────────────────────────


@pytest.mark.asyncio
async def test_cast_increments_ballots_cast_count(cast_harness) -> None:
    """The counter is what locks `change_type_live` after the first
    ballot. A regression that skips this increment would let the
    greffier silently change the rules mid-scrutin."""
    cfg = make_config(status=EVoteStatus.OUVERT, ballots_cast_count=0)
    h = cast_harness(cfg=cfg)
    svc = BallotService("fr")

    await svc.cast(
        vote_config_id="000000000000000000000001",
        voter_user_id=PydanticObjectId(),
        choice=EVoteChoice.POUR,
    )
    assert cfg.ballots_cast_count == 1
    h.cfg_save.assert_awaited_once()


# ── Audit chain emission ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_cast_audit_omits_voter_id_for_secret_vote(cast_harness) -> None:
    """PPTX slide 15 invariant: a secret-vote cast appears in the
    audit chain WITHOUT the voter's identity. The chain proves "a
    ballot was cast" without binding it to a sénateur.

    This is the most consequential audit-side property in the system
    — a regression here would silently break the secret-vote
    guarantee (a tamper-evident chain that lets you reverse-engineer
    who voted what is, by definition, NOT secret)."""
    cfg = make_config(
        status=EVoteStatus.OUVERT,
        is_secret=True,
        sealed_dek_b64="sealed-key",
    )
    voter = PydanticObjectId()
    h = cast_harness(cfg=cfg, existing_secret_ballots=[])
    svc = BallotService("fr")

    await svc.cast(
        vote_config_id="000000000000000000000001",
        voter_user_id=voter,
        choice=EVoteChoice.POUR,
    )
    assert len(h.audit_calls) == 1
    call = h.audit_calls[0]
    assert call["actor_user_id"] is None  # the critical invariant
    assert call["details"]["is_secret"] is True
    assert call["details"]["choice"] == "POUR"


@pytest.mark.asyncio
async def test_cast_audit_logs_voter_id_for_public_vote(cast_harness) -> None:
    """Public-vote inverse: the audit chain DOES log the voter id, so
    a public scrutin's chain is a complete trail of who voted what."""
    cfg = make_config(status=EVoteStatus.OUVERT, is_secret=False)
    voter = PydanticObjectId()
    h = cast_harness(cfg=cfg)
    svc = BallotService("fr")

    await svc.cast(
        vote_config_id="000000000000000000000001",
        voter_user_id=voter,
        choice=EVoteChoice.CONTRE,
    )
    assert len(h.audit_calls) == 1
    call = h.audit_calls[0]
    assert call["actor_user_id"] == voter
    assert call["details"]["is_secret"] is False
    assert call["details"]["choice"] == "CONTRE"


@pytest.mark.asyncio
async def test_cast_audit_includes_device_id(cast_harness) -> None:
    """The cast endpoint forwards the caller's device_id_str into the
    audit chain so the trail can correlate "ballot from this tablet".
    Useful for the post-incident "which device cast this?" question."""
    cfg = make_config(status=EVoteStatus.OUVERT, is_secret=False)
    h = cast_harness(cfg=cfg)
    svc = BallotService("fr")

    await svc.cast(
        vote_config_id="000000000000000000000001",
        voter_user_id=PydanticObjectId(),
        choice=EVoteChoice.POUR,
        device_id_str="tablet-greffier-01",
    )
    assert h.audit_calls[0]["actor_device_id_str"] == "tablet-greffier-01"


# ── Choice mapping is verbatim (no silent transforms) ─────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "choice",
    list(EVoteChoice),
    ids=[c.value for c in EVoteChoice],
)
async def test_cast_persists_each_choice_verbatim(
    cast_harness, choice: EVoteChoice,
) -> None:
    cfg = make_config(status=EVoteStatus.OUVERT, is_secret=False)
    h = cast_harness(cfg=cfg)
    svc = BallotService("fr")

    ballot = await svc.cast(
        vote_config_id="000000000000000000000001",
        voter_user_id=PydanticObjectId(),
        choice=choice,
    )
    assert ballot.choice == choice
