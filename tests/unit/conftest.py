"""Shared fixtures for vote-service unit tests.

The unit suite is mock-only — it never touches MongoDB. We stub
`VoteService._load` to return an in-memory `VoteConfigModel`-like
record, and `cfg.save` to a no-op coroutine. That lets us assert FSM +
invariant logic in isolation, without spinning up a Beanie/Mongo
fixture.

Why not test through the live HTTP layer?
  - The bash/smoke harness already covers RBAC + reachability.
  - The PPTX §3 invariant ("no change_type after first ballot cast")
    is a service-level rule; locking it in pure code is faster to run
    in CI and resilient to controller refactors.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest
from beanie import PydanticObjectId

from app.modules.vote.enums.vote_enum import (
    EVoteBallotType,
    EVoteMajorityType,
    EVoteStatus,
)
from app.modules.vote.models.vote_config.vote_config_model import VoteConfigModel
from app.modules.vote.services.vote_service import VoteService


def make_config(
    *,
    status: EVoteStatus = EVoteStatus.PROJET,
    ballots_cast_count: int = 0,
    is_secret: bool = False,
    ballot_type: EVoteBallotType = EVoteBallotType.OUI_NON,
    majority_type: EVoteMajorityType = EVoteMajorityType.RELATIVE,
    majority_custom_threshold: float | None = None,
    sealed_dek_b64: str | None = None,
) -> VoteConfigModel:
    """Build an in-memory VoteConfigModel for unit tests.

    Uses `model_construct` to skip both Pydantic validation and Beanie's
    `Document.__init__`, the latter of which calls `get_motor_collection()`
    — that demands `init_beanie()` was run first, which we explicitly
    don't want in a unit test (no DB round-trip; no warm Mongo).

    Defaults mirror the create endpoint's defaults so tests state
    overrides explicitly.
    """
    return VoteConfigModel.model_construct(
        id=PydanticObjectId(),
        identifier="test-id",
        sys_organization_id=PydanticObjectId(),
        session_meeting_id=PydanticObjectId(),
        resolution_id=PydanticObjectId(),
        title="Test scrutin",
        description_str=None,
        ballot_type=ballot_type,
        is_secret=is_secret,
        majority_type=majority_type,
        majority_custom_threshold=majority_custom_threshold,
        duration_seconds=60,
        allow_proxies=True,
        status=status,
        opened_at=None,
        suspended_at=None,
        closed_at=None,
        validated_at=None,
        ballots_cast_count=ballots_cast_count,
        sealed_dek_b64=sealed_dek_b64,
    )


@pytest.fixture
def service_with_loaded(monkeypatch: pytest.MonkeyPatch):
    """Returns `(svc, cfg, save_mock)` for a freshly-built scrutin.

    `svc._load` returns the in-memory cfg. `cfg.save` is replaced with
    an `AsyncMock` so tests can assert it was/wasn't called and inspect
    the post-mutation state without DB IO. The audit/notification
    side-effects on the real service are best-effort `try/except` so
    unit tests don't need to mock them — failures inside those blocks
    are silently swallowed by design.
    """

    def _factory(cfg: VoteConfigModel | None = None) -> tuple[VoteService, VoteConfigModel, AsyncMock]:
        cfg = cfg or make_config()
        svc = VoteService("fr")

        async def fake_load(vote_config_id: Any) -> VoteConfigModel:
            return cfg

        save_mock = AsyncMock()
        # Patching the *bound method* on the instance — sidesteps Beanie's
        # `.save()` which would otherwise try to round-trip Mongo.
        # Pydantic v2 blocks regular attribute assignment on model
        # instances; `object.__setattr__` bypasses that guard.
        object.__setattr__(cfg, "save", save_mock)

        monkeypatch.setattr(svc, "_load", fake_load)
        return svc, cfg, save_mock

    return _factory


def make_document_meta(
    *,
    typology=None,
    version_chain_id=None,
    current_version_number: int = 1,
    parent_version_id=None,
    title: str = "Document test",
    is_published: bool = False,
    linked_session_id=None,
    linked_agenda_item_ids=None,
    linked_resolution_ids=None,
    arch_file_id=None,
    sys_organization_id=None,
):
    """Build an in-memory DocumentMetaModel for tests."""
    from app.modules.document.enums.document_enum import EDocumentTypology
    from app.modules.document.models.document_meta.document_meta_model import (
        DocumentMetaModel,
    )

    return DocumentMetaModel.model_construct(
        id=PydanticObjectId(),
        identifier="test-doc",
        sys_organization_id=sys_organization_id or PydanticObjectId(),
        title=title,
        description_str=None,
        typology=typology or EDocumentTypology.RESOLUTION,
        version_chain_id=version_chain_id or PydanticObjectId(),
        current_version_number=current_version_number,
        parent_version_id=parent_version_id,
        arch_file_id=arch_file_id,
        linked_session_id=linked_session_id,
        linked_agenda_item_ids=list(linked_agenda_item_ids or []),
        linked_resolution_ids=list(linked_resolution_ids or []),
        is_published=is_published,
        published_at=None,
    )


def make_document_amendment(
    *,
    status=None,
    base_document_meta_id=None,
    validated_by_user_id=None,
    validation_reason: str | None = None,
    sys_organization_id=None,
):
    """Build an in-memory DocumentAmendmentModel for tests."""
    from app.modules.document.enums.document_enum import EAmendmentStatus
    from app.modules.document.models.document_amendment.document_amendment_model import (
        DocumentAmendmentModel,
    )

    return DocumentAmendmentModel.model_construct(
        id=PydanticObjectId(),
        identifier="test-amend",
        sys_organization_id=sys_organization_id or PydanticObjectId(),
        base_document_meta_id=base_document_meta_id or PydanticObjectId(),
        title="Test amendment",
        proposal_text="Test amendment proposal text",
        proposed_by_user_id=PydanticObjectId(),
        status=status or EAmendmentStatus.PROPOSE,
        validated_by_user_id=validated_by_user_id,
        validation_reason=validation_reason,
    )


def make_parole_request(
    *,
    session_meeting_id=None,
    requester_user_id=None,
    status=None,
    motive: str | None = None,
    granted_duration_seconds: int | None = None,
    dispatched_at=None,
    dispatched_by_user_id=None,
    requested_at=None,
):
    """Build an in-memory ParoleRequestModel for tests."""
    from datetime import datetime, timezone
    from app.modules.parole.enums.parole_enum import EParoleStatus
    from app.modules.parole.models.parole_request.parole_request_model import (
        ParoleRequestModel,
    )

    return ParoleRequestModel.model_construct(
        id=PydanticObjectId(),
        identifier="test-parole",
        sys_organization_id=PydanticObjectId(),
        session_meeting_id=session_meeting_id or PydanticObjectId(),
        agenda_item_id=None,
        requester_user_id=requester_user_id or PydanticObjectId(),
        requested_at=requested_at or datetime.now(timezone.utc),
        motive=motive,
        status=status or EParoleStatus.EN_ATTENTE,
        dispatched_by_user_id=dispatched_by_user_id,
        dispatched_at=dispatched_at,
        dispatch_reason=None,
        granted_duration_seconds=granted_duration_seconds,
        terminated_at=None,
    )


def make_presence_signature(
    *,
    session_meeting_id=None,
    sys_user_id=None,
    method=None,
    signed_at=None,
    device_id_str: str | None = None,
):
    """Build an in-memory PresenceSignatureModel for tests."""
    from datetime import datetime, timezone
    from app.modules.presence.enums.presence_enum import EPresenceMethod
    from app.modules.presence.models.presence_signature.presence_signature_model import (
        PresenceSignatureModel,
    )

    return PresenceSignatureModel.model_construct(
        id=PydanticObjectId(),
        identifier="test-sig",
        sys_organization_id=PydanticObjectId(),
        session_meeting_id=session_meeting_id or PydanticObjectId(),
        sys_user_id=sys_user_id or PydanticObjectId(),
        method=method or EPresenceMethod.ESIGN,
        signed_at=signed_at or datetime.now(timezone.utc),
        device_id_str=device_id_str,
        signature_hash=None,
        geolocation_lat=None,
        geolocation_lon=None,
    )


def make_agenda_item(
    *,
    session_meeting_id=None,
    title: str = "Point test",
    order_index: int = 0,
    is_active: bool = False,
    is_published: bool = False,
    activated_at=None,
    published_at=None,
):
    """Build an in-memory AgendaItemModel for tests. Bypass Beanie's
    motor lookup via `model_construct` — see tests/unit/README.md."""
    from app.modules.agenda.models.agenda_item.agenda_item_model import (
        AgendaItemModel,
    )

    return AgendaItemModel.model_construct(
        id=PydanticObjectId(),
        identifier="test-item",
        sys_organization_id=PydanticObjectId(),
        session_meeting_id=session_meeting_id or PydanticObjectId(),
        title=title,
        description_str=None,
        order_index=order_index,
        is_active=is_active,
        is_published=is_published,
        activated_at=activated_at,
        published_at=published_at,
        linked_document_ids=[],
    )


def make_session(
    *,
    status=None,
    mode=None,
    total_seats: int = 109,
    required_quorum_count: int = 55,
    title: str = "Séance test",
    opened_at=None,
    suspended_at=None,
    closed_at=None,
):
    """Build an in-memory SessionMeetingModel for tests.

    Defaults mirror the typical Sénat RDC plenary configuration
    (109 sièges, 55 quorum). Bypass Beanie's motor lookup via
    `model_construct` — see tests/unit/README.md."""
    from app.modules.session_meeting.enums.session_enum import (
        ESessionMode,
        ESessionStatus,
    )
    from app.modules.session_meeting.models.session_meeting.session_meeting_model import (
        SessionMeetingModel,
    )

    return SessionMeetingModel.model_construct(
        id=PydanticObjectId(),
        identifier="test-session",
        sys_organization_id=PydanticObjectId(),
        title=title,
        description_str=None,
        mode=mode or ESessionMode.PRESENTIEL,
        status=status or ESessionStatus.PLANIFIEE,
        opened_at=opened_at,
        suspended_at=suspended_at,
        closed_at=closed_at,
        total_seats=total_seats,
        required_quorum_count=required_quorum_count,
    )


def make_ballot(
    *,
    vote_config_id: PydanticObjectId | None = None,
    voter_user_id: PydanticObjectId | None = None,
    voter_user_id_enc: str | None = None,
    choice: str = "POUR",
    weight: int = 1,
):
    """Build an in-memory VoteBallotModel for the dup-detection scan
    in `BallotService.cast` (secret-vote path).

    Same `model_construct` rationale as `make_config`: bypass Beanie's
    motor-collection lookup and Pydantic validation. The default fields
    mirror what `BallotService` itself would set on a real cast — only
    overrides matter to most tests.
    """
    from app.modules.vote.enums.vote_enum import EVoteChoice
    from app.modules.vote.models.vote_ballot.vote_ballot_model import (
        VoteBallotModel,
    )

    return VoteBallotModel.model_construct(
        id=PydanticObjectId(),
        identifier="test-ballot",
        sys_organization_id=PydanticObjectId(),
        vote_config_id=vote_config_id or PydanticObjectId(),
        voter_user_id=voter_user_id,
        voter_user_id_enc=voter_user_id_enc,
        choice=EVoteChoice(choice),
        weight=weight,
        proxy_grantor_user_ids=[],
        device_id_str=None,
        signature_hash=None,
    )


@pytest.fixture(autouse=True)
def freeze_audit_and_notify(monkeypatch: pytest.MonkeyPatch):
    """Defang audit-chain + notification side-effects.

    The vote service emits these via local imports inside try/except
    blocks. They'd otherwise blow up trying to talk to Mongo / a
    notification queue. Replacing the import targets with no-op classes
    keeps the FSM logic isolated.
    """
    # Audit chain — `await AuditChainService(lang).emit(...)` no-op
    class _NoopAudit:
        def __init__(self, *_a, **_kw): ...
        async def emit(self, *_a, **_kw): return None

    # Notification — `await NotificationService(lang).emit_to_session_participants(...)`
    class _NoopNotif:
        def __init__(self, *_a, **_kw): ...
        async def emit_to_session_participants(self, *_a, **_kw): return None

    import app.modules.audit_security.services.audit_chain_service as ac
    import app.modules.notification.services.notification_service as ns
    monkeypatch.setattr(ac, "AuditChainService", _NoopAudit)
    monkeypatch.setattr(ns, "NotificationService", _NoopNotif)
    yield
