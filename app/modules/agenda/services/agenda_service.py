"""AgendaService — single source of truth for agenda invariants:

  1. At most one `is_active=True` item per session at a time.
  2. `reorder` rewrites `order_index` atomically across a session's items.
  3. `publish(session_id, is_published=True/False)` flips the flag for ALL
     items belonging to that session in one batch.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from beanie import PydanticObjectId
from beanie.operators import In

from app.modules.agenda.models.agenda_item.agenda_item_model import AgendaItemModel


class AgendaService:
    def __init__(self, accept_language: str = "fr"):
        self.accept_language = accept_language

    async def _load(self, item_id: str | PydanticObjectId) -> AgendaItemModel:
        oid = item_id if isinstance(item_id, PydanticObjectId) else PydanticObjectId(item_id)
        item = await AgendaItemModel.get(oid)
        if item is None:
            raise ValueError(f"Point d'ordre du jour introuvable: {item_id}")
        return item

    async def activate(self, item_id: str) -> AgendaItemModel:
        """Set `is_active=True` on the target item and `False` on all siblings.

        Performed as two queries (set-others-false → set-target-true) rather
        than one transaction. Race condition is benign: even if a parallel call
        flips a sibling, the next read still sees a consistent single-active
        view because both calls converge to one winner.
        """
        target = await self._load(item_id)
        was_active = target.is_active
        now = datetime.now(timezone.utc)

        # Deactivate all siblings (cheap — usually a handful of items per session)
        await AgendaItemModel.find(
            AgendaItemModel.session_meeting_id == target.session_meeting_id,
            AgendaItemModel.id != target.id,
            AgendaItemModel.is_active == True,  # noqa: E712
        ).update({"$set": {"is_active": False}})

        target.is_active = True
        target.activated_at = now
        await target.save()
        # ---- notifications (in-app inbox) ----
        # Idempotency guard: if the same point was already active we don't
        # re-emit (prevents inbox spam from accidental double-clicks).
        if not was_active:
            try:
                from app.modules.notification.enums.notification_enum import (
                    ENotificationEventType,
                )
                from app.modules.notification.services.notification_service import (
                    NotificationService,
                )
                await NotificationService(self.accept_language).emit_to_session_participants(
                    session_meeting_id=target.session_meeting_id,
                    event_type=ENotificationEventType.AGENDA_ITEM_ACTIVATED,
                    body=f"Point activé : « {target.title} ».",
                    snapshot_id=str(target.id),
                )
            except Exception:
                pass
        return target

    async def reorder(self, session_id: str, items: Iterable[tuple[str, int]]) -> int:
        """Apply (id, order_index) tuples in one batch. Returns count updated.

        Service-layer guard: every `id` must already belong to `session_id`.
        Items not listed are left untouched.
        """
        session_oid = PydanticObjectId(session_id)
        items_list = list(items)
        ids = [PydanticObjectId(i[0]) for i in items_list]
        order_map = {PydanticObjectId(i[0]): i[1] for i in items_list}

        existing = await AgendaItemModel.find(
            AgendaItemModel.session_meeting_id == session_oid,
            In(AgendaItemModel.id, ids),
        ).to_list()
        existing_ids = {item.id for item in existing}

        if existing_ids != set(ids):
            missing = set(ids) - existing_ids
            raise ValueError(
                f"Des points ne sont pas rattachés à la séance: "
                f"{[str(m) for m in missing]}"
            )

        n = 0
        for item in existing:
            new_idx = order_map[item.id]
            if item.order_index != new_idx:
                item.order_index = new_idx
                await item.save()
                n += 1
        return n

    async def publish(self, session_id: str, is_published: bool = True) -> int:
        """Flip `is_published` on every item of the session. Returns count updated."""
        session_oid = PydanticObjectId(session_id)
        now = datetime.now(timezone.utc)
        update_fields = {"is_published": is_published}
        if is_published:
            update_fields["published_at"] = now
        result = await AgendaItemModel.find(
            AgendaItemModel.session_meeting_id == session_oid,
        ).update({"$set": update_fields})
        # Beanie returns an UpdateResult; expose modified count uniformly
        modified = getattr(result, "modified_count", 0) or 0
        # ---- notifications (in-app inbox) ----
        # Only fan out when going unpublished → published AND something
        # actually changed. The mobile inbox deep-links AGENDA_PUBLISHED to
        # `/session/agenda` (no snapshot_id needed).
        if is_published and modified > 0:
            try:
                from app.modules.notification.enums.notification_enum import (
                    ENotificationEventType,
                )
                from app.modules.notification.services.notification_service import (
                    NotificationService,
                )
                await NotificationService(self.accept_language).emit_to_session_participants(
                    session_meeting_id=session_oid,
                    event_type=ENotificationEventType.AGENDA_PUBLISHED,
                    body=f"L'ordre du jour de la séance est publié ({modified} point{'s' if modified > 1 else ''}).",
                    snapshot_id=str(session_oid),
                )
            except Exception:
                pass
        return modified
