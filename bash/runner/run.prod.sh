#!/bin/bash
set -eo pipefail

# Environment setup
export ENV="production"
export APP_PORT=${APP_PORT:-8000}
export GUNICORN_PRELOAD="true"

# Path configuration
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"
cd "$PROJECT_ROOT" || { echo "❌ Failed to navigate to project root"; exit 1; }

# Virtual environment setup
VENV_DIR="$PROJECT_ROOT/.venv"
REQUIREMENTS_INSTALLED_FLAG="$VENV_DIR/.requirements_installed"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "🛠 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate" || {
    echo "❌ Virtual environment activation failed" >&2
    exit 1
}

# Install dependencies if not already installed
if [ ! -f "$REQUIREMENTS_INSTALLED_FLAG" ]; then
    echo "📦 Upgrading pip..."
    pip install --upgrade pip

    echo "📦 Installing dependencies from requirements.txt..."
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        pip install -r "$PROJECT_ROOT/requirements.txt"
        # Create flag file to indicate dependencies are installed
        touch "$REQUIREMENTS_INSTALLED_FLAG"
        echo "✅ Dependencies installed successfully!"
    else
        echo "⚠️ Warning: requirements.txt not found, installing from pyproject.toml..."
        pip install -e .
        touch "$REQUIREMENTS_INSTALLED_FLAG"
    fi
else
    echo "📦 Dependencies already installed, skipping..."
fi

# Load environment
[ -f .env.production ] && source .env.production

# Environment validation
if [ -z "$MONGO_URI" ]; then
    echo "❌ MONGO_URI environment variable is required" >&2
    exit 1
fi

# Check WeasyPrint dependencies
echo "🔍 Checking WeasyPrint dependencies..."
python3 -c "
try:
    from weasyprint import HTML
    print('✅ WeasyPrint is available')
except ImportError as e:
    if 'libpango' in str(e) or 'pango' in str(e):
        print('❌ WeasyPrint system dependencies missing!')
        print('Run this command to install them:')
        print('sudo apt install -y libpango-1.0-0 libpangoft2-1.0-0 libfontconfig1 libcairo2 libgdk-pixbuf2.0-0')
        exit(1)
    else:
        print(f'❌ WeasyPrint import error: {e}')
        exit(1)
except Exception as e:
    print(f'⚠️ WeasyPrint warning: {e}')
    print('Continuing anyway...')
"

# Database connection test (optional)
if [ -f "$PROJECT_ROOT/app/db/session.py" ]; then
    echo "🔌 Testing database connection..."
    python3 -c "
import asyncio
import os
from app.db.session import init_db
from motor.motor_asyncio import AsyncIOMotorClient
from app.modules.core.configs.config import settings

async def test_connection():
    try:
        client = AsyncIOMotorClient(settings.MONGO_URI)
        # Test the connection
        await client.admin.command('ping')
        print('✅ Database connection successful')
        return True
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        return False
    finally:
        client.close()

if not asyncio.run(test_connection()):
    raise RuntimeError('Database connection failed')
" || {
        echo "❌ Database connection test failed" >&2
        echo "⚠️ Continuing anyway - database will be initialized when the app starts"
    }
fi

# Start server
echo "🚀 Starting production server on port ${APP_PORT}..."
exec gunicorn -c "$PROJECT_ROOT/configs/gunicorn.conf.py" app.main:app