"""RBAC catalogue for the Senat-Digit Mobile (Flutter) consumer.

Aggregates per-feature permission catalogues as the §3.5 feature modules ship.
Currently includes:

  - auth_device  (login, refresh, password change, device verify, profile.*)

Future additions (one block per module): session_meeting, agenda, document,
vote, presence, parole, notification, audit_security.

Each entry follows the schema documented in
`core/seeds/rbac_title/system_config_permission_title.py`. The list is consumed
by `RbacRoleService.seed_rbac_from_module()` from the consumer's
`data/senat_digit_mobile_data_seed.py`.
"""

from app.modules.auth.seeds.senat_seed_loader import load_auth_device_permission_titles
from app.modules.session_meeting.seeds.session_seed_loader import (
    load_session_meeting_permission_titles,
)
from app.modules.agenda.seeds.agenda_seed_loader import load_agenda_permission_titles
from app.modules.document.seeds.document_seed_loader import load_document_permission_titles
from app.modules.vote.seeds.vote_seed_loader import load_vote_permission_titles
from app.modules.presence.seeds.presence_seed_loader import load_presence_permission_titles
from app.modules.parole.seeds.parole_seed_loader import load_parole_permission_titles
from app.modules.notification.seeds.notification_seed_loader import (
    load_notification_permission_titles,
)

# Home tab tile permissions — one per sub-menu, keyed on path_guard
# flag, with `rbac_roles_list` for per-role server-side filtering
# (sénateur / greffier / mainadmin / sysadmin). See
# `home/senat_digit_mobile_home_all_rbac.py` for the full mapping.
from app.modules.api_conumers_seed.senat_digit_mobile.rbac.home.senat_digit_mobile_home_all_rbac import (
    SENAT_DIGIT_MOBILE_HOME_PERMISSION_RBAC_DB,
)


CORE_SENAT_DIGIT_MOBILE_APP_RBAC_TITLE_DB = [
    *load_auth_device_permission_titles(),
    *load_session_meeting_permission_titles(),
    *load_agenda_permission_titles(),
    *load_document_permission_titles(),
    *load_vote_permission_titles(),
    *load_presence_permission_titles(),
    *load_parole_permission_titles(),
    *load_notification_permission_titles(),
    *SENAT_DIGIT_MOBILE_HOME_PERMISSION_RBAC_DB,
    # *load_document_permission_titles(),              # §3.5 step 4
    # *load_vote_permission_titles(),                  # §3.5 step 5
    # *load_presence_permission_titles(),              # §3.5 step 6
    # *load_parole_permission_titles(),                # §3.5 step 7
    # *load_notification_permission_titles(),          # §3.5 step 8
]
