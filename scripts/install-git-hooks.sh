#!/bin/bash

echo "⚙️ Installing project Git hooks..."

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

mkdir -p "$HOOKS_DIR"

install_hook() {
  local name=$1
  echo "📌 Installing $name ..."
  cp "hooks/$name" "$HOOKS_DIR/$name"
  chmod +x "$HOOKS_DIR/$name"

  if [[ "$is_admin" == "false" ]]; then
    chmod 555 "$HOOKS_DIR/$name"   # read-only for normal users
  else
    chmod 755 "$HOOKS_DIR/$name"   # admins can edit
  fi
}

# Install all hooks
install_hook "pre-commit"
install_hook "pre-push"
install_hook "pre-merge-commit"

echo "✅ Hooks installed successfully."
echo "   Current user: $CURRENT_USER"
if [[ "$is_admin" == "false" ]]; then
  echo "🔒 Hooks are read-only for non-admin users."
else
  echo "🔓 Admin privileges detected — hooks are editable."
fi
