#!/bin/bash
# Exit on error
set -e

# Function to display usage information
show_help() {
    echo "Usage: ./list_migrations.sh [environment]"
    echo ""
    echo "Lists all migrations and their status for the specified environment."
    echo ""
    echo "Environments:"
    echo "  dev       - Development environment (default)"
    echo "  prod      - Production environment"
    echo "  local     - Local environment"
    echo "  stage     - Staging environment"
    echo "  test      - Testing environment"
    echo ""
    echo "Examples:"
    echo "  ./list_migrations.sh             # List migrations for dev environment"
    echo "  ./list_migrations.sh prod        # List migrations for prod environment"
    echo "  ./list_migrations.sh local       # List migrations for local environment"
}

# Parse command line arguments
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
    exit 0
fi

ENV=${1:-dev}

# Validate the environment
case "$ENV" in
    "dev"|"development")
        ENV="development"
        ENV_FILE=".env.development"
        ;;
    "prod"|"production")
        ENV="production"
        ENV_FILE=".env.production"
        ;;
    "local")
        ENV="local"
        ENV_FILE=".env.local"
        ;;
    "stage"|"staging")
        ENV="staging"
        ENV_FILE=".env.staging"
        ;;
    "test"|"testing")
        ENV="testing"
        ENV_FILE=".env.testing"
        ;;
    "help"|"-h"|"--help")
        show_help
        exit 0
        ;;
    *)
        echo "Error: Unknown environment '$ENV'"
        show_help
        exit 1
        ;;
esac

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Navigate to the main project directory (two levels up from bash/migration)
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

# Load environment variables from the appropriate .env file
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE..."
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "Warning: $ENV_FILE file not found. Using default environment variables."
fi

# Set environment variables
export ENV=$ENV
export MONGO_URI=${MONGO_URI:-"mongodb://localhost:27017"}
export MONGO_DB_NAME=${MONGO_DB_NAME:-"suiviFinceManLocalDB"}

# Debug: Print environment variables
echo "Environment: $ENV"
echo "MongoDB URI: $MONGO_URI"
echo "MongoDB Database: $MONGO_DB_NAME"

# Create logs directory if it doesn't exist
# Create logs directory if it doesn't exist (in the script directory)
LOGS_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOGS_DIR"

# Set log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
MIGRATION_OUT_LOG="$LOGS_DIR/migration_list_${ENV}_${TIMESTAMP}_out.log"
MIGRATION_ERR_LOG="$LOGS_DIR/migration_list_${ENV}_${TIMESTAMP}_err.log"

echo "Logs will be saved to:"
echo "  Output: $MIGRATION_OUT_LOG"
echo "  Errors: $MIGRATION_ERR_LOG"

# Execute the command using the existing list_migrations.py script
echo "Listing migrations for $ENV environment..."
PYTHONPATH="$PROJECT_DIR" python3 bash/migration/list_migrations.py > "$MIGRATION_OUT_LOG" 2> "$MIGRATION_ERR_LOG"

# Check the exit status of the script
if [ $? -eq 0 ]; then
    echo "✅ Migration listing completed successfully. Check $MIGRATION_OUT_LOG for details."
    echo ""
    echo "📋 Summary:"
    echo "   - Environment: $ENV"
    echo "   - Database: $MONGO_DB_NAME"
    echo "   - Output log: $MIGRATION_OUT_LOG"
    echo "   - Error log: $MIGRATION_ERR_LOG"

    # Display the output for immediate viewing
    echo ""
    echo "📄 Migration Status:"
    cat "$MIGRATION_OUT_LOG"
else
    echo "❌ Migration listing failed. Check $MIGRATION_ERR_LOG for error details."
    echo ""
    echo "Error details:"
    cat "$MIGRATION_ERR_LOG"
    exit 1
fi
