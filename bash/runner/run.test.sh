#!/bin/bash
set -eo pipefail

# Environment setup
export ENV="local"
export APP_PORT=${APP_PORT:-4516}
export GUNICORN_RELOAD="true"

# Path configuration
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"
cd "$PROJECT_ROOT" || { echo "❌ Failed to navigate to project root"; exit 1; }

# Export PYTHONPATH to ensure Python can find the app module
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

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
        # Install local dependencies if available
        if [ -f "$PROJECT_ROOT/requirements-dev.txt" ]; then
            echo "📦 Installing local dependencies..."
            pip install -r "$PROJECT_ROOT/requirements-dev.txt"
        fi
        # Create flag file to indicate dependencies are installed
        touch "$REQUIREMENTS_INSTALLED_FLAG"
        echo "✅ Dependencies installed successfully!"
    else
        echo "⚠️ Warning: requirements.txt not found, installing from pyproject.toml..."
        pip install -e .[dev]
        touch "$REQUIREMENTS_INSTALLED_FLAG"
    fi
else
    echo "📦 Dependencies already installed, skipping..."
fi

# Load environment
[ -f .env.local ] && source .env.local

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

# Test basic imports
echo "🔍 Testing critical imports..."
python3 -c "
try:
    # Test basic app imports
    from app.modules.core.configs.config import settings
    print('✅ Core config import successful')

    # Test database imports
    from app.db.session import init_db
    print('✅ Database imports successful')

    # Test logging imports
    try:
        from app.modules.core.utils.logs.log import LogRequestHeadersMiddleware
        print('✅ Logging middleware import successful')
    except ImportError as e:
        print(f'⚠️ Logging middleware import failed: {e}')
        print('You may need to create the missing logs module')

except ImportError as e:
    print(f'❌ Critical import failed: {e}')
    exit(1)
except Exception as e:
    print(f'❌ Import test failed: {e}')
    exit(1)
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
echo "🚀 Starting local server on port ${APP_PORT}..."
exec gunicorn -c "$PROJECT_ROOT/configs/gunicorn.conf.py" app.main:app