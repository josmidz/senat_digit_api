#!/bin/bash
# Exit on error
set -e

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Navigate to the main project directory (two levels up from bash/runner)
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

# Set ENV to local explicitly
export ENV=local
echo "Setting ENV=local"

# Set library paths for WeasyPrint/Pango support
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:/opt/homebrew/opt/libffi/lib/pkgconfig:$PKG_CONFIG_PATH"
export FONTCONFIG_PATH="/opt/homebrew/etc/fonts"
export LDFLAGS="-L/opt/homebrew/opt/libffi/lib"
export CPPFLAGS="-I/opt/homebrew/opt/libffi/include"
echo "Library paths configured for WeasyPrint/Pango support"

# Load environment variables from the .env.local file
if [ -f .env.local ]; then
  echo "Loading local environment variables from .env.local..."
  set -a
  source .env.local
  set +a
else
  echo "Error: .env.local file not found. Please create one."
  exit 1
fi

# Start the FastAPI app with Uvicorn
echo "Starting FastAPI app with Uvicorn..."
echo "Using port: ${APP_PORT:-4516}"
echo "Using environment: $ENV"
echo "Using database: $MONGO_DB_NAME"
ENV=local uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT:-4516} --loop asyncio --reload
