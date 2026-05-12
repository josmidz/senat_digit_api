#!/bin/bash
# bash/seeds/run.seed.dev.app.sh
# Exit on error
set -e

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Navigate to the main project directory (two levels up from bash/seeds)
PROJECT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Navigate to the project directory
echo "Navigating to project directory: $PROJECT_DIR"
cd "$PROJECT_DIR" || { echo "Failed to navigate to project directory"; exit 1; }

# Activate the virtual environment
echo "Looking for virtual environment in: $PROJECT_DIR/.venv"
if [ -f .venv/bin/activate ]; then
  echo "Activating virtual environment..."
  source .venv/bin/activate
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
    echo "Loading local environment variables from .env.development..."
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

# Create logs directory if it doesn't exist
# Create logs directory if it doesn't exist (in the script directory)
LOGS_DIR="$SCRIPT_DIR/logs"
echo "Creating logs directory if it doesn't exist: $LOGS_DIR"
mkdir -p "$LOGS_DIR"

# Execute the seed script and log output
SEED_OUT_LOG="$LOGS_DIR/app_dev_seed_out.log"
SEED_ERR_LOG="$LOGS_DIR/app_dev_seed_err.log"
echo "Running seed script..."
echo "Output will be logged to: $SEED_OUT_LOG"
echo "Errors will be logged to: $SEED_ERR_LOG"

python3 -m app.modules.core.seeds.seed_apps > "$SEED_OUT_LOG" 2> "$SEED_ERR_LOG"

# §3.4 dropped the TRANSCO `configuration` module — see run.seed.local.app.sh
# for the full rationale. Senat-Digit's app/menu catalog ships through
# `init_data()` via `senat_digit_modules_rbac.py` (F2).

if [ $? -eq 0 ]; then
  echo "Seeding completed successfully. Check $SEED_OUT_LOG for details."
else
  echo "Seeding failed. Check $SEED_ERR_LOG for error details."
  exit 1
fi
