"""`DocumentService` — version chain + amendment FSM + publish.

Three contracts locked:

  1. **Version chain integrity** — `create_version` preserves
     `version_chain_id` from the parent and increments
     `current_version_number` by 1. The new DocumentMeta carries
     `parent_version_id` pointing back; a sibling DocumentVersion
     row records the change-log entry. Locks the linkage that the
     mobile "voir l'historique" tab relies on.

  2. **Amendment FSM** — `validate_amendment` enforces
     PROPOSE → VALIDE | REJETE (and only those). Terminal states
     reject all further transitions. Defends against re-validating
     an already-decided amendment.

  3. **Publish transition-edge gating** — the unpublished→published
     edge fires the audit + notification. Re-publishing
     (published→published, modified=0) is a quiet no-op for
     notifications. Defends inbox-spam scenario where the greffier
     republishes an already-published doc.

Plus the session-bound notification rule: documents WITHOUT a
`linked_session_id` are standalone library entries and don't fan out
on publish — surfaced via the documents list, not via push.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.modules.document.enums.document_enum import (
    AMENDMENT_STATUS_TRANSITIONS,
    EAmendmentStatus,
    EDocumentTypology,
)
from app.modules.document.models.document_amendment.document_amendment_model import (
    DocumentAmendmentModel,
)
from app.modules.document.models.document_meta.document_meta_model import (
    DocumentMetaModel,
)
from app.modules.document.models.document_version.document_version_model import (
    DocumentVersionModel,
)
from app.modules.document.services.document_service import DocumentService

from .conftest import make_document_amendment, make_document_meta


# ── Pure FSM matrix (amendment) ────────────────────────────────────


_ALLOWED: list[tuple[EAmendmentStatus, EAmendmentStatus]] = [
    (EAmendmentStatus.PROPOSE, EAmendmentStatus.VALIDE),
    (EAmendmentStatus.PROPOSE, EAmendmentStatus.REJETE),
]


def _all_disallowed() -> list[tuple[EAmendmentStatus, EAmendmentStatus]]:
    allowed = set(_ALLOWED)
    out: list[tuple[EAmendmentStatus, EAmendmentStatus]] = []
    for src in EAmendmentStatus:
        for dst in EAmendmentStatus:
            if src == dst:
                continue
            if (src, dst) in allowed:
                continue
            out.append((src, dst))
    return out


@pytest.mark.parametrize(
    "src,dst", _ALLOWED,
    ids=[f"{s.value}->{d.value}" for s, d in _ALLOWED],
)
def test_amendment_transition_allowed(src, dst) -> None:
    """`validate_amendment` checks `decision in AMENDMENT_STATUS_TRANSITIONS[
    amendment.status]` directly. Locks the matrix at the table level."""
    assert dst in AMENDMENT_STATUS_TRANSITIONS.get(src, frozenset())


@pytest.mark.parametrize(
    "src,dst", _all_disallowed(),
    ids=[f"{s.value}->{d.value}" for s, d in _all_disallowed()],
)
def test_amendment_transition_rejected(src, dst) -> None:
    assert dst not in AMENDMENT_STATUS_TRANSITIONS.get(src, frozenset())


def test_amendment_terminal_states_have_no_outbound() -> None:
    """VALIDE / REJETE are terminal — no re-validation."""
    assert AMENDMENT_STATUS_TRANSITIONS[EAmendmentStatus.VALIDE] == frozenset()
    assert AMENDMENT_STATUS_TRANSITIONS[EAmendmentStatus.REJETE] == frozenset()


def test_amendment_every_status_in_transition_matrix() -> None:
    keys = set(AMENDMENT_STATUS_TRANSITIONS.keys())
    assert keys == set(EAmendmentStatus)


# ── Test helpers ──────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def stub_motor_collection(monkeypatch: pytest.MonkeyPatch):
    """Bypass Beanie's motor lookup so `DocumentMetaModel(...)` and
    `DocumentVersionModel(...)` constructors work inside the service."""
    for cls in (DocumentMetaModel, DocumentVersionModel):
        monkeypatch.setattr(
            cls,
            "get_motor_collection",
            classmethod(lambda c: MagicMock(name="motor_stub")),
        )


@pytest.fixture
def service_with_meta(monkeypatch: pytest.MonkeyPatch):
    """Wires `_load_meta` to return the supplied DocumentMetaModel +
    replaces save with an AsyncMock."""
    from types import SimpleNamespace

    def _factory(meta: DocumentMetaModel):
        svc = DocumentService("fr")

        async def fake_load(_id):
            return meta
        monkeypatch.setattr(svc, "_load_meta", fake_load)

        save_mock = AsyncMock()
        object.__setattr__(meta, "save", save_mock)
        return SimpleNamespace(svc=svc, meta=meta, save=save_mock)

    return _factory


@pytest.fixture
def captured_audit(monkeypatch: pytest.MonkeyPatch):
    """Capture `AuditChainService.emit` calls (overrides the autouse
    no-op stub from conftest)."""
    calls: List[dict] = []
    import app.modules.audit_security.services.audit_chain_service as ac

    class _Capturing:
        def __init__(self, *_a, **_kw): ...
        async def emit(self, **kwargs):
            calls.append(kwargs)
            return None
    monkeypatch.setattr(ac, "AuditChainService", _Capturing)
    return calls


@pytest.fixture
def captured_notifs(monkeypatch: pytest.MonkeyPatch):
    """Capture `NotificationService.emit_to_session_participants` calls."""
    calls: List[dict] = []
    import app.modules.notification.services.notification_service as ns

    class _Capturing:
        def __init__(self, *_a, **_kw): ...
        async def emit_to_session_participants(self, **kwargs):
            calls.append(kwargs)
            return None
    monkeypatch.setattr(ns, "NotificationService", _Capturing)
    return calls


# ── create_version ────────────────────────────────────────────────


@pytest.fixture
def version_inserts(monkeypatch: pytest.MonkeyPatch):
    """Capture inserts on both DocumentMetaModel and DocumentVersionModel."""
    meta_inserts: List[DocumentMetaModel] = []
    version_inserts_list: List[DocumentVersionModel] = []

    async def fake_meta_insert(self):
        meta_inserts.append(self)
        return self
    monkeypatch.setattr(DocumentMetaModel, "insert", fake_meta_insert)

    async def fake_version_insert(self):
        version_inserts_list.append(self)
        return self
    monkeypatch.setattr(DocumentVersionModel, "insert", fake_version_insert)

    return meta_inserts, version_inserts_list


@pytest.mark.asyncio
async def test_create_version_preserves_chain_id(
    service_with_meta, version_inserts,
) -> None:
    """The single most important versioning invariant: every new
    version on a doc shares the parent's `version_chain_id`. A
    regression that mints a fresh chain id would break every
    "show me all versions of this doc" query downstream."""
    chain = PydanticObjectId()
    parent = make_document_meta(
        version_chain_id=chain,
        current_version_number=2,
    )
    h = service_with_meta(parent)
    metas, _ = version_inserts

    new_meta = await h.svc.create_version(
        parent_document_id=str(parent.id),
        title="V3 — révisions",
        description_str=None,
        arch_file_id=None,
        change_summary="Corrections typo",
    )
    assert new_meta.version_chain_id == chain
    assert new_meta.current_version_number == 3
    assert new_meta.parent_version_id == parent.id
    assert len(metas) == 1
    assert metas[0] is new_meta


@pytest.mark.asyncio
async def test_create_version_inserts_change_log_row(
    service_with_meta, version_inserts,
) -> None:
    """Sibling `DocumentVersionModel` row records the change-log
    entry. The mobile "voir l'historique" tab pulls from this
    collection — a regression that skips the version-row insert
    silently breaks history."""
    parent = make_document_meta(current_version_number=1)
    h = service_with_meta(parent)
    _, version_rows = version_inserts

    actor = PydanticObjectId()
    new_meta = await h.svc.create_version(
        parent_document_id=str(parent.id),
        title="V2 — révision",
        description_str=None,
        arch_file_id=None,
        change_summary="Ajout annexe",
        actor_user_id=actor,
    )
    assert len(version_rows) == 1
    v = version_rows[0]
    assert v.version_chain_id == parent.version_chain_id
    assert v.document_meta_id == new_meta.id
    assert v.parent_version_id == parent.id
    assert v.version_number == 2
    assert v.change_summary == "Ajout annexe"
    assert v.created_by_user_id == actor


@pytest.mark.asyncio
async def test_create_version_starts_unpublished(
    service_with_meta, version_inserts,
) -> None:
    """Even when the parent was published, the new version starts
    unpublished. The greffier explicitly re-publishes after review —
    a regression that auto-published would surface unreviewed
    versions to sénateurs immediately."""
    parent = make_document_meta(is_published=True)
    h = service_with_meta(parent)
    metas, _ = version_inserts

    new_meta = await h.svc.create_version(
        parent_document_id=str(parent.id),
        title="V2 — révision",
        description_str=None,
        arch_file_id=None,
        change_summary=None,
    )
    assert new_meta.is_published is False


@pytest.mark.asyncio
async def test_create_version_propagates_session_and_links(
    service_with_meta, version_inserts,
) -> None:
    """Session + agenda + resolution links are inherited so the new
    version surfaces in the same place. Defends against orphaning
    the new version from its séance context."""
    session_id = PydanticObjectId()
    agenda_id = PydanticObjectId()
    resolution_id = PydanticObjectId()
    parent = make_document_meta(
        linked_session_id=session_id,
        linked_agenda_item_ids=[agenda_id],
        linked_resolution_ids=[resolution_id],
    )
    h = service_with_meta(parent)

    new_meta = await h.svc.create_version(
        parent_document_id=str(parent.id),
        title="V2 — révision",
        description_str=None,
        arch_file_id=None,
        change_summary=None,
    )
    assert new_meta.linked_session_id == session_id
    assert new_meta.linked_agenda_item_ids == [agenda_id]
    assert new_meta.linked_resolution_ids == [resolution_id]


@pytest.mark.asyncio
async def test_create_version_propagates_typology(
    service_with_meta, version_inserts,
) -> None:
    """Typology stays the same across versions — a TEXTE_LOI never
    becomes a RESOLUTION mid-chain."""
    parent = make_document_meta(typology=EDocumentTypology.TEXTE_LOI)
    h = service_with_meta(parent)

    new_meta = await h.svc.create_version(
        parent_document_id=str(parent.id),
        title="V2 — révision",
        description_str=None,
        arch_file_id=None,
        change_summary=None,
    )
    assert new_meta.typology == EDocumentTypology.TEXTE_LOI


@pytest.mark.asyncio
async def test_create_version_unknown_parent_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vanished parent id → "introuvable" rather than a None-deref."""
    monkeypatch.setattr(
        DocumentMetaModel, "get", AsyncMock(return_value=None),
    )
    svc = DocumentService("fr")
    with pytest.raises(ValueError, match="introuvable"):
        await svc.create_version(
            parent_document_id=str(PydanticObjectId()),
            title="V2 — révision",
            description_str=None,
            arch_file_id=None,
            change_summary=None,
        )


# ── validate_amendment ────────────────────────────────────────────


@pytest.fixture
def amendment_harness(monkeypatch: pytest.MonkeyPatch):
    """Wires `DocumentAmendmentModel.get` + `save` for FSM tests."""
    from types import SimpleNamespace

    def _factory(amendment: DocumentAmendmentModel | None):
        monkeypatch.setattr(
            DocumentAmendmentModel, "get",
            AsyncMock(return_value=amendment),
        )
        save_mock = AsyncMock()
        if amendment is not None:
            object.__setattr__(amendment, "save", save_mock)
        return SimpleNamespace(amendment=amendment, save=save_mock)

    return _factory


@pytest.mark.asyncio
async def test_validate_amendment_to_valide(
    amendment_harness, captured_audit,
) -> None:
    amendment = make_document_amendment(status=EAmendmentStatus.PROPOSE)
    h = amendment_harness(amendment)
    svc = DocumentService("fr")

    out = await svc.validate_amendment(
        amendment_id=str(amendment.id),
        decision=EAmendmentStatus.VALIDE,
        reason="Conforme",
        validator_user_id=PydanticObjectId(),
    )
    assert out.status == EAmendmentStatus.VALIDE
    assert out.validation_reason == "Conforme"
    assert out.validated_by_user_id is not None
    h.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_validate_amendment_to_rejete(
    amendment_harness, captured_audit,
) -> None:
    amendment = make_document_amendment(status=EAmendmentStatus.PROPOSE)
    h = amendment_harness(amendment)
    svc = DocumentService("fr")

    out = await svc.validate_amendment(
        amendment_id=str(amendment.id),
        decision=EAmendmentStatus.REJETE,
        reason="Hors sujet",
        validator_user_id=PydanticObjectId(),
    )
    assert out.status == EAmendmentStatus.REJETE
    assert out.validation_reason == "Hors sujet"


@pytest.mark.parametrize(
    "src,dst",
    _all_disallowed(),
    ids=[f"{s.value}->{d.value}" for s, d in _all_disallowed()],
)
@pytest.mark.asyncio
async def test_validate_amendment_disallowed_transitions_rejected(
    amendment_harness, captured_audit, src, dst,
) -> None:
    """Already-VALIDE / REJETE amendments cannot be re-validated.
    Locks the terminal-state guarantee at the public-method level."""
    amendment = make_document_amendment(status=src)
    h = amendment_harness(amendment)
    svc = DocumentService("fr")

    with pytest.raises(ValueError, match="refusée"):
        await svc.validate_amendment(
            amendment_id=str(amendment.id),
            decision=dst,
            reason=None,
            validator_user_id=PydanticObjectId(),
        )
    h.save.assert_not_called()


@pytest.mark.asyncio
async def test_validate_amendment_unknown_id_raises(
    amendment_harness, captured_audit,
) -> None:
    amendment_harness(None)
    svc = DocumentService("fr")
    with pytest.raises(ValueError, match="introuvable"):
        await svc.validate_amendment(
            amendment_id=str(PydanticObjectId()),
            decision=EAmendmentStatus.VALIDE,
            reason=None,
            validator_user_id=PydanticObjectId(),
        )


@pytest.mark.asyncio
async def test_validate_amendment_emits_audit(
    amendment_harness, captured_audit,
) -> None:
    """Audit row carries decision + has_reason flag + actor.
    Documents the exact payload shape the audit chain stores."""
    amendment = make_document_amendment(status=EAmendmentStatus.PROPOSE)
    h = amendment_harness(amendment)
    svc = DocumentService("fr")

    validator = PydanticObjectId()
    await svc.validate_amendment(
        amendment_id=str(amendment.id),
        decision=EAmendmentStatus.VALIDE,
        reason="Conforme au texte de loi",
        validator_user_id=validator,
    )
    assert len(captured_audit) == 1
    call = captured_audit[0]
    assert call["actor_user_id"] == validator
    assert call["document_meta_id"] == amendment.base_document_meta_id
    assert call["details"]["decision"] == "VALIDE"
    assert call["details"]["has_reason"] is True


@pytest.mark.asyncio
async def test_validate_amendment_does_not_block_on_audit_failure(
    monkeypatch: pytest.MonkeyPatch, amendment_harness,
) -> None:
    """A flaky audit chain doesn't block the validation from saving."""
    amendment = make_document_amendment(status=EAmendmentStatus.PROPOSE)
    h = amendment_harness(amendment)

    import app.modules.audit_security.services.audit_chain_service as ac

    class _Exploding:
        def __init__(self, *_a, **_kw): ...
        async def emit(self, *_a, **_kw):
            raise RuntimeError("audit down")
    monkeypatch.setattr(ac, "AuditChainService", _Exploding)

    svc = DocumentService("fr")
    out = await svc.validate_amendment(
        amendment_id=str(amendment.id),
        decision=EAmendmentStatus.VALIDE,
        reason=None,
        validator_user_id=PydanticObjectId(),
    )
    assert out.status == EAmendmentStatus.VALIDE
    h.save.assert_awaited_once()


# ── publish ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_sets_is_published_and_published_at(
    service_with_meta, captured_audit, captured_notifs,
) -> None:
    meta = make_document_meta(is_published=False)
    h = service_with_meta(meta)

    out = await h.svc.publish(str(meta.id), is_published=True)
    assert out.is_published is True
    assert out.published_at is not None
    assert out.published_at.tzinfo == timezone.utc
    h.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_unpublish_clears_published_at(
    service_with_meta, captured_audit, captured_notifs,
) -> None:
    """Going published→unpublished sets `published_at=None` rather
    than keeping the old timestamp. A previous publish that's been
    rolled back shouldn't lie about the publish time."""
    meta = make_document_meta(is_published=True)
    object.__setattr__(meta, "published_at", datetime.now(timezone.utc))
    h = service_with_meta(meta)

    out = await h.svc.publish(str(meta.id), is_published=False)
    assert out.is_published is False
    assert out.published_at is None


@pytest.mark.asyncio
async def test_publish_emits_notification_on_first_publish(
    service_with_meta, captured_audit, captured_notifs,
) -> None:
    """Unpublished → published WITH `linked_session_id` → fan-out."""
    session_id = PydanticObjectId()
    meta = make_document_meta(
        is_published=False, linked_session_id=session_id,
        title="Adoption résolution",
    )
    h = service_with_meta(meta)

    await h.svc.publish(str(meta.id), is_published=True)
    assert len(captured_notifs) == 1
    call = captured_notifs[0]
    assert call["session_meeting_id"] == session_id
    assert call["snapshot_id"] == str(meta.id)
    assert "Adoption résolution" in call["body"]


@pytest.mark.asyncio
async def test_republish_does_not_emit_notification(
    service_with_meta, captured_audit, captured_notifs,
) -> None:
    """Already-published → published is a no-op for notifications.
    Defends inbox-spam scenario where the greffier double-clicks
    Publier."""
    meta = make_document_meta(
        is_published=True,  # already published
        linked_session_id=PydanticObjectId(),
    )
    h = service_with_meta(meta)

    await h.svc.publish(str(meta.id), is_published=True)
    assert captured_notifs == []


@pytest.mark.asyncio
async def test_unpublish_does_not_emit_notification(
    service_with_meta, captured_audit, captured_notifs,
) -> None:
    """Pulling a doc back is a quiet admin action — sénateurs already
    saw it. No reverse-publish ping."""
    meta = make_document_meta(
        is_published=True,
        linked_session_id=PydanticObjectId(),
    )
    h = service_with_meta(meta)

    await h.svc.publish(str(meta.id), is_published=False)
    assert captured_notifs == []


@pytest.mark.asyncio
async def test_publish_without_session_skips_notification(
    service_with_meta, captured_audit, captured_notifs,
) -> None:
    """Standalone library docs (no `linked_session_id`) don't fan out
    on publish — surfaced via the documents list, not via push.
    Audit still fires (the publish edge is auditable regardless)."""
    meta = make_document_meta(
        is_published=False,
        linked_session_id=None,  # standalone
    )
    h = service_with_meta(meta)

    await h.svc.publish(str(meta.id), is_published=True)
    assert captured_notifs == []
    assert len(captured_audit) == 1  # audit still fires


@pytest.mark.asyncio
async def test_publish_audit_includes_was_published_flag(
    service_with_meta, captured_audit, captured_notifs,
) -> None:
    """The audit row records BOTH the prior `was_published` AND the
    new `is_published`. Locks the audit-chain shape so a forensic
    review can distinguish "first publish" from "republish" without
    cross-referencing the chain."""
    meta = make_document_meta(is_published=False)
    h = service_with_meta(meta)

    await h.svc.publish(str(meta.id), is_published=True)
    assert len(captured_audit) == 1
    details = captured_audit[0]["details"]
    assert details["was_published"] is False
    assert details["is_published"] is True
    assert details["title"] == meta.title
    assert details["typology"] == meta.typology.value
    assert details["version_number"] == meta.current_version_number


@pytest.mark.asyncio
async def test_publish_does_not_block_on_audit_failure(
    monkeypatch: pytest.MonkeyPatch, service_with_meta,
) -> None:
    """A flaky audit chain doesn't block the publish save."""
    meta = make_document_meta(is_published=False)
    h = service_with_meta(meta)

    import app.modules.audit_security.services.audit_chain_service as ac

    class _Exploding:
        def __init__(self, *_a, **_kw): ...
        async def emit(self, *_a, **_kw):
            raise RuntimeError("audit down")
    monkeypatch.setattr(ac, "AuditChainService", _Exploding)

    out = await h.svc.publish(str(meta.id), is_published=True)
    assert out.is_published is True
    h.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_does_not_block_on_notification_failure(
    monkeypatch: pytest.MonkeyPatch, service_with_meta, captured_audit,
) -> None:
    """A flaky FCM doesn't block the publish save."""
    meta = make_document_meta(
        is_published=False, linked_session_id=PydanticObjectId(),
    )
    h = service_with_meta(meta)

    import app.modules.notification.services.notification_service as ns

    class _Exploding:
        def __init__(self, *_a, **_kw): ...
        async def emit_to_session_participants(self, *_a, **_kw):
            raise RuntimeError("FCM down")
    monkeypatch.setattr(ns, "NotificationService", _Exploding)

    out = await h.svc.publish(str(meta.id), is_published=True)
    assert out.is_published is True


@pytest.mark.asyncio
async def test_publish_unknown_document_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        DocumentMetaModel, "get", AsyncMock(return_value=None),
    )
    svc = DocumentService("fr")
    with pytest.raises(ValueError, match="introuvable"):
        await svc.publish(str(PydanticObjectId()), is_published=True)
