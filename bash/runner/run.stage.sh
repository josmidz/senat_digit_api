#!/bin/bash
# Exit on error
set -e

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Navigate to the main project directory (two levels up from bash/runner)
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

# Load environment variables from the .env file
if [ "$ENV" == "stage" ] && [ -f .env.stage ]; then
  echo "Loading stage environment variables from .env.stage..."
  set -a
  source .env.stage
  set +a
elif [ -f .env ]; then
  echo "Loading environment variables from .env..."
  set -a
  source .env
  set +a
else
  echo "No .env file found. Please create one."
  exit 1
fi

# Start the FastAPI app with Uvicorn
echo "Starting FastAPI app with Uvicorn..."
echo "Using port: ${APP_PORT:-4715}"
ENV=staging uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT:-4498} --loop asyncio --reload
