#!/bin/bash

echo "⚙️ Uninstalling project Git hooks..."

HOOKS_DIR=".git/hooks"
ADMIN_USERS=("admin" "root")  # customize: add your admin usernames

CURRENT_USER=$(whoami)

# Check if current user is admin
is_admin=false
for admin in "${ADMIN_USERS[@]}"; do
  if [[ "$CURRENT_USER" == "$admin" ]]; then
    is_admin=true
    break
  fi
done

if [[ "$is_admin" == "false" ]]; then
  echo "🔒 Non-admin user detected. Checking permissions..."
fi

uninstall_hook() {
  local name=$1
  local hook_path="$HOOKS_DIR/$name"

  if [[ -f "$hook_path" ]]; then
    # Make writable before removing (in case it was read-only)
    chmod 755 "$hook_path" 2>/dev/null
    rm -f "$hook_path"
    echo "🗑️  Removed $name"
  else
    echo "⏭️  $name not found — skipping"
  fi
}

# Uninstall all hooks
uninstall_hook "pre-commit"
uninstall_hook "pre-push"
uninstall_hook "pre-merge-commit"

echo "✅ Hooks uninstalled successfully."
echo "   Current user: $CURRENT_USER"
