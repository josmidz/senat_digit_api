#!/usr/bin/env bash
#
# bash/smoke/run_full_check.sh — one-command sanity check for the
# Senat-Digit backend.
#
# Chains:
#   1. Apps + RBAC seed (idempotent)
#   2. Dummy seed — demo users, demo session, vote, notifications,
#      cfg_user_app_store warm-up (idempotent)
#   3. Wait for the API on $APP_PORT to respond on /health
#   4. Run the live HTTP role smokes (system_admin + sénateur + greffier)
#
# Exit code: 0 only if every step passes. Suitable for CI and for the
# "did I break something?" check after touching seeds, RBAC, or auth.
#
# Pre-reqs:
#   - .env.local exists in the repo root (this script sources it)
#   - .venv exists with all deps installed
#   - The API is already running on $APP_PORT — start it in a separate
#     terminal with `bash/runner/run.local.sh`. We don't auto-start it
#     here because the API is `--reload`-driven and best left in a
#     foreground shell where its logs are visible.
#
# Usage:
#   bash bash/smoke/run_full_check.sh
#   bash bash/smoke/run_full_check.sh --skip-seed   # only run smokes
#
# Override:
#   APP_PORT=9000 bash bash/smoke/run_full_check.sh
#   API_HOST=http://192.168.1.10:8088 bash bash/smoke/run_full_check.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

# ── env ──────────────────────────────────────────────────────────────
if [[ ! -f .env.local ]]; then
  echo "✗ .env.local missing in $PROJECT_DIR — copy from .env.local.template first."
  exit 2
fi

# Activate venv unless already in one
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  if [[ -f .venv/bin/activate ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
  else
    echo "✗ .venv not found in $PROJECT_DIR — run \`python3 -m venv .venv && pip install -r requirements.txt\` first."
    exit 2
  fi
fi

# Load env vars from .env.local (Mongo URI, app port, etc.)
set -a
# shellcheck disable=SC1091
source .env.local
set +a

APP_PORT="${APP_PORT:-8088}"
SMOKE_API_HOST="${SMOKE_API_HOST:-http://localhost:${APP_PORT}}"
export SMOKE_API_HOST

SKIP_SEED=0
for arg in "$@"; do
  case "$arg" in
    --skip-seed) SKIP_SEED=1 ;;
    -h|--help)
      sed -n '1,/^# Usage/p; /^# Usage:/,/^$/p' "$0" | sed 's/^# \?//'
      exit 0 ;;
    *) echo "unknown arg: $arg"; exit 2 ;;
  esac
done

# ── helpers ──────────────────────────────────────────────────────────
# ANSI codes only when stdout is a tty AND --no-color isn't set; the
# bare `printf '\033…'` form depended on the shell's non-portable escape
# interpretation (worked in some shells, leaked literal `[32m` in
# others). Resolving once at startup keeps the output clean.
if [[ -t 1 ]]; then
  C_GREEN=$(printf '\033[32m')
  C_RED=$(printf '\033[31m')
  C_RESET=$(printf '\033[0m')
else
  C_GREEN=''; C_RED=''; C_RESET=''
fi
hr()   { printf '\n%s\n' "════════════════════════════════════════════════════════════════════════"; }
step() { hr; printf '  ▶ %s\n' "$1"; hr; }
ok()   { printf '  %s✓%s %s\n' "$C_GREEN" "$C_RESET" "$1"; }
fail() { printf '  %s✗%s %s\n' "$C_RED"   "$C_RESET" "$1"; }

wait_for_health() {
  local url="${SMOKE_API_HOST}/api/v1/health"
  local tries=0
  local max_tries=30  # 30 × 0.5s = 15s budget
  while (( tries < max_tries )); do
    if curl -s -m 2 -o /dev/null -w '%{http_code}' "$url" 2>/dev/null | grep -q '^200$'; then
      return 0
    fi
    sleep 0.5
    tries=$((tries + 1))
  done
  return 1
}

# ── 1. Seed ──────────────────────────────────────────────────────────
if (( SKIP_SEED )); then
  step "Seeds skipped (--skip-seed)"
else
  step "1 · Apps + RBAC seed"
  if bash bash/seeds/run.apps-seed.sh local >/tmp/senat-apps-seed.log 2>&1; then
    ok "apps seed (rbac_endpoint, rbac_permission, rbac_permission_target, role grants)"
  else
    fail "apps seed crashed — see /tmp/senat-apps-seed.log"
    tail -30 /tmp/senat-apps-seed.log
    exit 1
  fi

  step "2 · Dummy seed"
  if bash bash/seeds/run.dummy-seed.local.sh >/tmp/senat-dummy-seed.log 2>&1; then
    ok "dummy seed (demo users, session, vote, notifications, app-store warm)"
  else
    fail "dummy seed crashed — see /tmp/senat-dummy-seed.log"
    tail -30 /tmp/senat-dummy-seed.log
    exit 1
  fi
fi

# ── 3. Wait for API ──────────────────────────────────────────────────
step "3 · Wait for API at ${SMOKE_API_HOST}"
if wait_for_health; then
  ok "API healthy (GET /api/v1/health → 200)"
else
  fail "API did not become healthy within 15s. Start it with \`bash/runner/run.local.sh\` in another shell."
  exit 1
fi

# ── 4. Live smokes ────────────────────────────────────────────────────
step "4 · Live role smokes (system_admin + sénateur + greffier)"
if python bash/smoke/run_all.py; then
  ok "all role smokes PASSED"
else
  fail "one or more smokes failed (see output above)"
  exit 1
fi

# ── verdict ──────────────────────────────────────────────────────────
hr
ok "FULL CHECK PASSED"
hr
