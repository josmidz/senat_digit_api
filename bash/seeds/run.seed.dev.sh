#!/bin/bash
# bash/seeds/run.seed.dev.sh
# Exit on error
set -e

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Navigate to the main project directory (two levels up from bash/seeds)
PROJECT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Navigate to the main project directory (two levels up from bash/seeds)
PROJECT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
echo "Navigating to project directory: $PROJECT_DIR"
cd "$PROJECT_DIR" || { echo "Failed to navigate to project directory"; exit 1; }

# Activate the virtual environment
echo "Looking for virtual environment in: $PROJECT_DIR/.venv"
echo "Looking for virtual environment in: $PROJECT_DIR/.venv"
if [ -f .venv/bin/activate ]; then
  echo "Activating virtual environment..."
  source .venv/bin/activate
  echo "Virtual environment activated successfully."
  echo "Virtual environment activated successfully."
else
  echo "Virtual environment not found at: $PROJECT_DIR/.venv"
  echo "Please create one with: cd $PROJECT_DIR && python3 -m venv .venv"
  exit 1
fi

# Validate and load environment variables from the .env.development file
if [ -f .env.development ]; then
  echo "Validating .env.development file..."
  # Check if the file contains only valid KEY=VALUE pairs
  if grep -q -E "^\s*[^#=]+=" .env.development; then
    echo "Loading development environment variables from .env.development..."
    set -a  # Automatically export all variables in the script (temporary)
    source .env.development
    set +a  # Stop automatically exporting
  else
    echo "Error: .env.development file contains invalid lines. Ensure all lines are valid KEY=VALUE pairs."
    exit 1
  fi
else
  echo "Error: .env.development file not found!"
  exit 1
fi

# Debug: Print environment variables to verify they're loaded correctly
echo "MONGO_URI=$MONGO_URI"
echo "MONGO_DB_NAME=$MONGO_DB_NAME"

# Create logs directory if it doesn't exist (in the script directory)
# Create logs directory if it doesn't exist (in the script directory)
LOGS_DIR="$SCRIPT_DIR/logs"
echo "Creating logs directory if it doesn't exist: $LOGS_DIR"
mkdir -p "$LOGS_DIR"

# Execute the seed script and log output. See `run.seed.local.sh` for
# the full rationale — TRANSCO-domain modules (configuration,
# urban_transportation, trans_agent_flutter_app) were dropped in §3.4
# and their python entry points no longer exist. Removed those calls
# so the run completes cleanly under `set -e`.
SEED_OUT_LOG="$LOGS_DIR/dev_seed_out.log"
SEED_ERR_LOG="$LOGS_DIR/dev_seed_err.log"
echo "Running seed script..."
echo "Output will be logged to: $SEED_OUT_LOG"
echo "Errors will be logged to: $SEED_ERR_LOG"

python3 -m app.modules.core.seeds.seed > "$SEED_OUT_LOG" 2> "$SEED_ERR_LOG"

# user_app_store static seed — must run LAST: depends on RBAC profiles +
# sys_application + rbac_restricted_* junctions all being in place. Pre-
# warms the L2 cache for static profiles (visitor / customer). Non-fatal:
# the cache also populates on-demand on first request.
USER_APP_STORE_SEED_OUT_LOG="$LOGS_DIR/dev_user_app_store_seed_out.log"
USER_APP_STORE_SEED_ERR_LOG="$LOGS_DIR/dev_user_app_store_seed_err.log"
echo "Running user_app_store static seed..."
echo "Output will be logged to: $USER_APP_STORE_SEED_OUT_LOG"
set +e
python3 -m app.modules.core.services.user_app_store.user_app_store_seed_service > "$USER_APP_STORE_SEED_OUT_LOG" 2> "$USER_APP_STORE_SEED_ERR_LOG"
USER_APP_STORE_RC=$?
set -e
if [ $USER_APP_STORE_RC -eq 0 ]; then
  echo "user_app_store static seeding completed successfully."
else
  echo "user_app_store static seeding failed (non-fatal). Check $USER_APP_STORE_SEED_ERR_LOG."
fi

# user_app_store DYNAMIC seed — pre-populates per-user rows for admin /
# agent profiles using StaticController.run_formated_applications_core.
USER_APP_STORE_DYN_OUT_LOG="$LOGS_DIR/dev_user_app_store_dynamic_seed_out.log"
USER_APP_STORE_DYN_ERR_LOG="$LOGS_DIR/dev_user_app_store_dynamic_seed_err.log"
echo "Running user_app_store dynamic seed..."
echo "Output will be logged to: $USER_APP_STORE_DYN_OUT_LOG"
set +e
python3 -m app.modules.core.services.user_app_store.user_app_store_dynamic_seed_service > "$USER_APP_STORE_DYN_OUT_LOG" 2> "$USER_APP_STORE_DYN_ERR_LOG"
USER_APP_STORE_DYN_RC=$?
set -e
if [ $USER_APP_STORE_DYN_RC -eq 0 ]; then
  echo "user_app_store dynamic seeding completed successfully."
else
  echo "user_app_store dynamic seeding failed (non-fatal). Check $USER_APP_STORE_DYN_ERR_LOG."
fi

# Check the exit status of the script
if [ $? -eq 0 ]; then
  echo "Seeding completed successfully. Check $SEED_OUT_LOG, $CONFIGURATION_SEED_OUT_LOG, and $URBAN_TRANSPORT_SEED_OUT_LOG for details."
else
  echo "Seeding failed. Check $SEED_ERR_LOG, $CONFIGURATION_SEED_ERR_LOG, and $URBAN_TRANSPORT_SEED_ERR_LOG for error details."
  exit 1  # Exit with a non-zero status to indicate failure
fi
