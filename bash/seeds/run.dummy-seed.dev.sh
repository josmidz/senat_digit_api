#!/bin/bash
# bash/seeds/run.dummy-seed.dev.sh
#
# Demo data seeder targeting the development DB. Mirrors run.dummy-seed.local.sh
# 1:1 — only difference is the env file (.env.development) and the log
# filename. Idempotent: safe to re-run; helpers in dummy_seed.py upsert
# by stable natural keys.
#
# IMPORTANT: this is dev-only on purpose. There is no run.dummy-seed.prod.sh —
# a parliamentary platform must never have shared demo credentials in prod.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"

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
  if grep -q -E "^\s*[^#=]+=" .env.development; then
    echo "Loading dev environment variables from .env.development..."
    set -a
    source .env.development
    set +a
  else
    echo "Error: .env.development file contains invalid lines. Ensure all lines are valid KEY=VALUE pairs."
    exit 1
  fi
else
  echo "Error: .env.development file not found!"
  exit 1
fi

echo "MONGO_URI=$MONGO_URI"
echo "MONGO_DB_NAME=$MONGO_DB_NAME"

LOGS_DIR="$SCRIPT_DIR/logs"
echo "Creating logs directory if it doesn't exist: $LOGS_DIR"
mkdir -p "$LOGS_DIR"

SEED_OUT_LOG="$LOGS_DIR/dummy_seed_dev_out.log"
SEED_ERR_LOG="$LOGS_DIR/dummy_seed_dev_err.log"
echo "Running dummy seed script (dev)..."
echo "Output will be logged to: $SEED_OUT_LOG"
echo "Errors will be logged to: $SEED_ERR_LOG"

python3 -m app.modules.core.seeds.dummy_seed > "$SEED_OUT_LOG" 2> "$SEED_ERR_LOG"

if [ $? -eq 0 ]; then
  echo "Dummy seeding completed successfully. Check $SEED_OUT_LOG for details."
  # Replay the credential summary block on stdout so the dev sees it
  # without having to open the log file.
  if grep -q "DONE — credentials" "$SEED_OUT_LOG"; then
    echo
    awk '/═══/,/═══$/' "$SEED_OUT_LOG" | tail -n +1
  fi
else
  echo "Dummy seeding failed. Check $SEED_ERR_LOG for error details."
  exit 1
fi
