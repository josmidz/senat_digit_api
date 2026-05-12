#!/bin/bash
# Senat-Digit — generate production secret values.
#
# Prints fresh random values for the crypto-backed env keys in
# `.env.production`. Run once when initialising a new env, copy the
# output into `.env.production`, and DO NOT REUSE these values
# across environments.
#
# Usage:
#   bash bash/utils/generate_production_secrets.sh
#   bash bash/utils/generate_production_secrets.sh > /tmp/secrets.txt
#
# Verifying you can re-derive: each value is computed by Python's
# `secrets` module (cryptographically secure). The Fernet key uses
# the cryptography library's recommended generator.

set -euo pipefail

if ! command -v python3 >/dev/null; then
  echo "python3 is required" >&2
  exit 1
fi

# Activate venv if available — `cryptography` ships there. Falls back
# to system python with a hint when missing.
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if ! python3 -c "from cryptography.fernet import Fernet" 2>/dev/null; then
  echo "Missing dependency: 'cryptography'." >&2
  echo "Run: pip install cryptography" >&2
  exit 1
fi

cat <<'EOF'
# ─── Senat-Digit production secrets ────────────────────────────────
# Generated $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# Copy each line below into your `.env.production`. Treat as
# credentials — store in a password manager + rotate per security
# policy.
EOF

python3 - <<'PY'
import secrets
from cryptography.fernet import Fernet

# 64-hex-char (32-byte) JWT signing key
print(f"JWT_SECRET_KEY={secrets.token_hex(32)}")

# General-purpose 64-hex-char secrets
print(f"SECRET_KEY={secrets.token_hex(32)}")
print(f"RECAPTCHA_SECRET={secrets.token_hex(32)}")

# Fernet master keys (32-byte url-safe base64). Used by
# CryptoService for tenant config + secret-vote DEKs.
print(f"ENCRYPTION_KEY='{Fernet.generate_key().decode()}'")
print(f"ENCRYPTION_SECRET_KEY={Fernet.generate_key().decode()}")
print(f"ENCRYPTION_DB_SECRET_KEY={Fernet.generate_key().decode()}")

# Strong default-admin password (32 url-safe chars). The operator
# rotates this via the admin UI once they're logged in.
print(f"ADMIN_PASSWORD={secrets.token_urlsafe(24)}")
PY
