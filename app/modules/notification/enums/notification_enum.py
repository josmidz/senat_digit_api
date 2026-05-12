"""Notification event taxonomy — Senat-Digit specific.

These values land in `NtfNotificationModel.alert_type`. Each event also
populates `snapshot_id` with the related entity ID (vote_config, document,
parole_request, session_meeting) so the mobile app can deep-link.

In-app inbox only at MVP. FCM/APNs push fan-out is a v1.1 enhancement —
the service layer is structured so adding a push side-channel is a single
override on `NotificationService.emit_one`.
"""

from enum import Enum


class ENotificationEventType(str, Enum):
    """Senat-Digit notification taxonomy. Stored in `alert_type`."""
    VOTE_OPENED = "vote_opened"
    VOTE_CLOSED = "vote_closed"
    DOCUMENT_PUBLISHED = "document_published"
    AGENDA_PUBLISHED = "agenda_published"
    AGENDA_ITEM_ACTIVATED = "agenda_item_activated"
    PAROLE_GRANTED = "parole_granted"
    PAROLE_REFUSED = "parole_refused"
    SESSION_OPENED = "session_opened"
    SESSION_CLOSED = "session_closed"
    BROADCAST = "broadcast"  # greffier-initiated free-form announcement


# Default French labels used when the emitter doesn't override `title`.
DEFAULT_TITLES_FR: dict[ENotificationEventType, str] = {
    ENotificationEventType.VOTE_OPENED: "Scrutin ouvert",
    ENotificationEventType.VOTE_CLOSED: "Scrutin clos",
    ENotificationEventType.DOCUMENT_PUBLISHED: "Document publié",
    ENotificationEventType.AGENDA_PUBLISHED: "Ordre du jour publié",
    ENotificationEventType.AGENDA_ITEM_ACTIVATED: "Point activé",
    ENotificationEventType.PAROLE_GRANTED: "Parole accordée",
    ENotificationEventType.PAROLE_REFUSED: "Parole refusée",
    ENotificationEventType.SESSION_OPENED: "Séance ouverte",
    ENotificationEventType.SESSION_CLOSED: "Séance clôturée",
    ENotificationEventType.BROADCAST: "Annonce du greffier",
}
