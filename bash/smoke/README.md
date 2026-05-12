# Live RBAC smokes

End-to-end HTTP regression tests for the senat-digit RBAC matrix. Each
script logs in as a real demo user (with HMAC signing + MFA fork +
device pre-pair) and exercises a curated allow/deny URL set against the
running API.

The smokes are the runtime counterpart to the in-process Mongo
aggregation checks in earlier seed work: aggregation proves the seed is
correct; smokes prove `permission_check_middleware` actually enforces it
when wired with the real auth controller.

## Layout

```
bash/smoke/
  _smoke_lib.py                       # shared HMAC + auth + assert helpers
  system_admin_bootstrap_smoke.py     # admindpsenat / system_profil_super_admin
  senateur_role_smoke.py              # senateur1 / senateur
  greffier_role_smoke.py              # greffier1 / greffier
  run_all.py                          # chains all 3, exit-codes for CI
  run_full_check.sh                   # one-command sanity: seeds → wait /health
                                      # → run_all.py. Suitable for CI or the
                                      # post-touch "did I break something?" check.
  pair_recent_device.py               # dev shortcut: pair the freshest cfg_user_device
                                      # for a username (mirrors the admin-mediated
                                      # /auth/validate-device-activation step locally
                                      # without needing the Angular admin web).
```

## One-command check

```sh
# in one terminal — boot the API
bash/runner/run.local.sh

# in another — seed + smoke + verdict
bash/smoke/run_full_check.sh             # full chain
bash/smoke/run_full_check.sh --skip-seed # only run the smokes (faster)
```

Exit code is 0 only if every step passes — drop into CI verbatim.

## Pre-reqs

1. **API running** on `$APP_PORT` (default 8088).
   ```sh
   bash/runner/run.local.sh
   ```
2. **MongoDB seeded** — apps + RBAC + dummy data:
   ```sh
   bash/seeds/run.apps-seed.sh local
   bash/seeds/run.dummy-seed.local.sh
   ```
   The dummy seed bumps `cfg_user_config.allowed_device_count = 5` for
   every demo user. Without that, the legacy auth pipeline locks every
   login with "périphériques autorisés".

## Run

```sh
cd senat_digit_api
source .venv/bin/activate
set -a; source .env.local; set +a
python bash/smoke/run_all.py
```

Each smoke takes < 1s; the runner totals < 3s end-to-end.

## What gets validated

| Smoke | Allowed (sample) | Denied (sample) |
|---|---|---|
| **system-admin** | `/list/sys_user_for_organization`, `/organizations/add/org` | `/list/session` (feature URL) |
| **senateur** | `/static/data/get-applications`, `/list/session`, `/list/notification_self` | `/open/vote`, `/close/session`, `/dispatch/parole_request`, `/list/sys_user_for_organization` |
| **greffier** | `/open/vote`, `/close/session`, `/dispatch/parole_request`, `/create/agenda_item` | `/create/vote_ballot` (sénateur), `/create/parole_request`, `/list/sys_user_for_organization` |

The matrix mirrors `app/modules/core/seeds/senat_digit_role_matrix.py`.
A failing assertion means either the seed catalogue drifted from reality
or `permission_check_middleware` aggregated wrong.

## How a smoke is parameterised

`Smoke(consumer_flag, username, password, device_id, label)` —
everything else (HMAC signing, MFA OTP fork, device pre-pair) is shared.
Adding a new role smoke is ~80 lines: one `await sm.login()` plus the
allow/deny URL list.

## Device pre-pairing — dev-only shortcut

The smokes write `cfg_user_device` directly into Mongo with
`status='allowed'` + `is_authenticated=True` so login bypasses the
legacy `/auth/initiate-device-activation` OTP ceremony. **Stage and prod
must use the real activation flow** — this shortcut is gated behind
local dev only by virtue of the `MONGO_URI` env var.

## MFA — read OTP from Mongo

In dev there's no SMS/email delivery to intercept, so the smoke reads
the freshly-written OTP straight from `ops_user_login_history.otp` after
calling `/auth/get-specific-otp`. Same dev-only shortcut.

## RBAC vs business outcome

A `403` from any of the URLs in the "allowed" set is a hard fail (RBAC
broken). Anything else (200, 4xx-business, 5xx-controller-crash) is
treated as RBAC-OK because the middleware let the request reach the
controller. If a controller crashes downstream it surfaces as an FYI in
the smoke output but doesn't fail the run — that's a separate
investigation.


# Live Flutter test runbook

Once the API + smokes are green, here's how to bring the Flutter app
through to the rendered bottom-nav for a real demo user.

## 1 · Boot the API

```sh
cd senat_digit_api
bash/seeds/run.apps-seed.sh local         # idempotent
bash/seeds/run.dummy-seed.local.sh        # seeds demo users + apps cache
bash/runner/run.local.sh                  # uvicorn :8088 with --reload
```

In a second terminal, confirm the smokes are green:

```sh
cd senat_digit_api
source .venv/bin/activate
set -a; source .env.local; set +a
python bash/smoke/run_all.py              # ✓ ALL ROLE SMOKES PASSED
```

## 2 · Boot the Flutter app

The runner auto-detects your LAN IP, fetches the `senat_digit_mobile`
consumer secret from Mongo, and dart-defines everything:

```sh
cd senat_digit_app
bash/run.dev.sh                           # auto-detects everything
# or with a specific device:
bash/run.dev.sh -d <device-id>
```

The banner will show the resolved `API_BASE_URL`, `CONSUMER_FLAG`, and a
masked secret prefix. If the secret is empty, the API must run with
`STRICT_CONSUMER_VALIDATION=False` for unsigned requests — fine for
local dev.

## 3 · First login — device pairing

The auth pipeline pairs each device on first use. The Flutter app
correctly **calls** `/auth/initiate-device-activation` (which dispatches
the SMS via Lisoloo — confirmed working) but doesn't yet have the
**OTP-entry screen** to call `/auth/validate-device-activation`. So the
cold-boot flow stops after the SMS arrives.

For dev, use the dev shortcut:

```sh
# 1. From the Flutter app, attempt login as senateur1.
#    It bounces with "device not allowed". A device row appears in
#    cfg_user_device with status='pending_validation'.
#
# 2. From the API repo, promote the freshest device for that user:
cd senat_digit_api
source .venv/bin/activate
set -a; source .env.local; set +a
python bash/smoke/pair_recent_device.py senateur1
#    ✓ paired: hash=… → status=allowed, is_authenticated=True
#
# 3. Retry login from the Flutter app — succeeds.
```

Demo creds (printed by `dummy_seed`):

| Role | Username | Password | Consumer | MFA |
|---|---|---|---|---|
| sénateur | `senateur1` … `senateur5` | `Senat2026!` | mobile | email |
| greffier | `greffier1` | `Greffier2026!` | admin web | email |
| sys admin | `admindpsenat` | `12345@Qwerty` | admin web | email |

## 4 · MFA OTP

After password login the app forwards to the MFA verification screen.
The OTP is dispatched via Lisoloo SMS (and email when the user has an
`email` MFA configured). For dev where the inbox is hard to reach, the
OTP is also persisted to `ops_user_login_history.otp` for the matching
session — `pair_recent_device.py` doesn't pull it but you can:

```sh
mongosh "$MONGO_URI/$MONGO_DB_NAME" --quiet --eval '
  db.ops_user_login_history.find(
    {sys_user_id: db.sys_user.findOne({username:"senateur1"})._id, otp:{$exists:true}}
  ).sort({updated_at:-1}).limit(1).forEach(r => print(r.otp));
'
```

## 5 · Bottom-nav rendered

After OTP validation, the Flutter shell calls
`GET /static/data/get-applications`. With the role + RBAC seeds shipped
this turn, the response should contain 5 apps for sénateurs:

  - `apps_senat_home_app`        → /home
  - `apps_senat_session_app`     → /session
  - `apps_senat_documents_app`   → /documents
  - `apps_senat_votes_app`       → /votes
  - `apps_senat_more_app`        → /more

`_ShellScaffold` filters them through `RbacScreenRegistry` and renders
the bottom nav. System admins on the same mobile binary see no tabs —
their app catalogue is admin-web-scoped — so the shell renders an empty
body (no nav bar). That's expected behavior, not a bug.

## 6 · What to check

- Inbox tab populates with the 7 demo notifications targeting senateur1.
- Session tab shows the demo session (`Séance plénière du 30 avril 2026`).
- Vote tab shows the closed scrutin with decision ADOPTÉ.
- Documents tab lists 3 documents (texte de loi / résolution / rapport).

If any of these fail with a 403, the role grant matrix drifted —
`run_all.py` would have already caught that. If they fail with a 500 /
401, that's a controller-level bug analogous to the two we hunted in the
session/notification controllers earlier.

