#!/bin/bash
# bash/seeds/run.dummy-seed.test.sh
#
# Demo data seeder targeting the testing DB. Used by reviewers + CI staging
# runs. Mirrors run.dummy-seed.local.sh — only difference is the env file
# (.env.testing). Idempotent: safe to re-run.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "Navigating to project directory: $PROJECT_DIR"
cd "$PROJECT_DIR" || { echo "Failed to navigate to project directory"; exit 1; }

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

if [ -f .env.testing ]; then
  echo "Validating .env.testing file..."
  if grep -q -E "^\s*[^#=]+=" .env.testing; then
    echo "Loading testing environment variables from .env.testing..."
    set -a
    source .env.testing
    set +a
  else
    echo "Error: .env.testing file contains invalid lines. Ensure all lines are valid KEY=VALUE pairs."
    exit 1
  fi
else
  echo "Error: .env.testing file not found!"
  exit 1
fi

echo "MONGO_URI=$MONGO_URI"
echo "MONGO_DB_NAME=$MONGO_DB_NAME"

LOGS_DIR="$SCRIPT_DIR/logs"
echo "Creating logs directory if it doesn't exist: $LOGS_DIR"
mkdir -p "$LOGS_DIR"

SEED_OUT_LOG="$LOGS_DIR/dummy_seed_test_out.log"
SEED_ERR_LOG="$LOGS_DIR/dummy_seed_test_err.log"
echo "Running dummy seed script (test)..."
echo "Output will be logged to: $SEED_OUT_LOG"
echo "Errors will be logged to: $SEED_ERR_LOG"

python3 -m app.modules.core.seeds.dummy_seed > "$SEED_OUT_LOG" 2> "$SEED_ERR_LOG"

if [ $? -eq 0 ]; then
  echo "Dummy seeding completed successfully. Check $SEED_OUT_LOG for details."
  if grep -q "DONE — credentials" "$SEED_OUT_LOG"; then
    echo
    awk '/═══/,/═══$/' "$SEED_OUT_LOG" | tail -n +1
  fi
else
  echo "Dummy seeding failed. Check $SEED_ERR_LOG for error details."
  exit 1
fi
