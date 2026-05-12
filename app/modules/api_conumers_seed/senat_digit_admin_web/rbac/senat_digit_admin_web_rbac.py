"""RBAC catalogue for the Senat-Digit Admin (Angular) consumer.

The admin web is the surface for greffier / admin_it / archiviste roles —
session orchestration, vote configuration/supervision, audit chain, etc.
The Angular UI itself is post-MVP, but we wire the RBAC permissions now so
the matrix surface exists end-to-end.

Currently aggregates:
  - audit_security (admin-only audit reads + chain verify/export)
  - session_meeting (greffier orchestration: create/open/suspend/close)
  - vote (greffier configuration + supervision + validate)
  - agenda (greffier ODJ construction)
  - document (greffier document CRUD + amendment validation)
  - parole (greffier dispatch)
  - notification (greffier broadcast)

Sénateur-only mobile permissions (auth_device, presence.sign_self, vote.cast,
parole.request_self) are NOT loaded here — they live on senat_digit_mobile.
The two consumer scopes deliberately don't overlap on those.
"""

from app.modules.audit_security.seeds.audit_seed_loader import (
    load_audit_security_permission_titles,
)
from app.modules.session_meeting.seeds.session_seed_loader import (
    load_session_meeting_permission_titles,
)
from app.modules.vote.seeds.vote_seed_loader import load_vote_permission_titles
from app.modules.agenda.seeds.agenda_seed_loader import load_agenda_permission_titles
from app.modules.document.seeds.document_seed_loader import load_document_permission_titles
from app.modules.parole.seeds.parole_seed_loader import load_parole_permission_titles
from app.modules.notification.seeds.notification_seed_loader import (
    load_notification_permission_titles,
)


CORE_SENAT_DIGIT_ADMIN_WEB_APP_RBAC_TITLE_DB = [
    *load_audit_security_permission_titles(),
    *load_session_meeting_permission_titles(),
    *load_vote_permission_titles(),
    *load_agenda_permission_titles(),
    *load_document_permission_titles(),
    *load_parole_permission_titles(),
    *load_notification_permission_titles(),
]
