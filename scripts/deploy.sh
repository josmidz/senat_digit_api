#!/bin/bash
# /home/cobilgo_adm_vps025/BASH/FINANCE_SH/deploy.sh

# Configuration
LOG_FILE="/var/log/deployments/$(date +%Y%m%d_%H%M%S)_${BRANCH}.log"
DEPLOY_USER="deploy_user"  # Consider using a dedicated deployment user

# Initialize logging
exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== Deployment started at $(date) ==="
echo "Branch: $BRANCH"
echo "Commit: ${GIT_COMMIT:-unknown}"

# Validate inputs
if [[ ! "$BRANCH" =~ ^(dev|main)$ ]]; then
  echo "❌ FATAL: Invalid branch specified: '$BRANCH'"
  exit 1
fi

# Environment setup
case "$BRANCH" in
  dev)
    APP_DIR="/var/www/expensechain/DEV/dev_min_finance_api"
    SERVICE_NAME="minfinance_api_dev"
    ;;
  main)
    APP_DIR="/var/www/expensechain/PROD/prod_min_finance_api"
    SERVICE_NAME="minfinance_api_prod"
    ;;
esac

# Verify directory exists
if [ ! -d "$APP_DIR" ]; then
  echo "❌ FATAL: App directory not found: $APP_DIR"
  exit 1
fi

cd "$APP_DIR" || exit 1

# Git operations
echo "🔄 Syncing with origin/$BRANCH"
git fetch origin "$BRANCH" || { echo "❌ Git fetch failed"; exit 1; }

# Verify we're on the right branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
  echo "⚠️ Switching to branch $BRANCH (was on $CURRENT_BRANCH)"
  git checkout -f "$BRANCH" || { echo "❌ Git checkout failed"; exit 1; }
fi

# Reset to remote state
echo "♻️ Resetting to origin/$BRANCH"
git reset --hard "origin/$BRANCH" || { echo "❌ Git reset failed"; exit 1; }
git clean -fd || { echo "❌ Git clean failed"; exit 1; }

# Optional: Install dependencies if using Python
if [ -f "requirements.txt" ]; then
  echo "📦 Installing Python dependencies"
  python -m pip install -r requirements.txt || { echo "❌ Dependency installation failed"; exit 1; }
fi

# Service management
echo "🔄 Restarting $SERVICE_NAME"
sudo supervisorctl status "$SERVICE_NAME" >/dev/null || { 
  echo "❌ Service $SERVICE_NAME not found in supervisor";
  exit 1;
}

sudo supervisorctl restart "$SERVICE_NAME" || {
  echo "❌ Service restart failed";
  sudo supervisorctl status "$SERVICE_NAME";
  exit 1;
}

# Verification
sleep 3  # Give service time to start
SERVICE_STATUS=$(sudo supervisorctl status "$SERVICE_NAME")
echo "✅ Final service status: $SERVICE_STATUS"

echo "🏁 Deployment completed successfully at $(date)"
echo "Log saved to: $LOG_FILE"