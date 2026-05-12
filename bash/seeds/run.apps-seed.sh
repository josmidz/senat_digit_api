#!/bin/bash
# bash/seeds/run.apps-seed.sh
# Exit on error
set -e

# Function to display usage information
show_help() {
    echo "Usage: ./run.apps-seed.sh [environment]"
    echo ""
    echo "Runs the application seed script for the specified environment."
    echo ""
    echo "Environments:"
    echo "  dev       - Development environment (default)"
    echo "  prod      - Production environment"
    echo "  local     - Local environment"
    echo "  stage     - Staging environment"
    echo "  test      - Testing environment"
    echo ""
    echo "Examples:"
    echo "  ./run.apps-seed.sh dev     # Run app seed for development environment"
    echo "  ./run.apps-seed.sh prod    # Run app seed for production environment"
    echo "  ./run.apps-seed.sh local   # Run app seed for local environment"
    echo "  ./run.apps-seed.sh stage   # Run app seed for staging environment"
    echo "  ./run.apps-seed.sh test    # Run app seed for testing environment"
}

# Get the environment from the command line argument
ENV=${1:-dev}

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Validate the environment
case "$ENV" in
    "dev"|"development")
        SCRIPT="$SCRIPT_DIR/run.seed.dev.app.sh"
        ;;
    "prod"|"production")
        SCRIPT="$SCRIPT_DIR/run.seed.prod.app.sh"
        ;;
    "local")
        SCRIPT="$SCRIPT_DIR/run.seed.local.app.sh"
        ;;
    "stage"|"staging")
        SCRIPT="$SCRIPT_DIR/run.seed.stage.app.sh"
        ;;
    "test"|"testing")
        SCRIPT="$SCRIPT_DIR/run.seed.test.app.sh"
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

# Check if the script exists
if [ ! -f "$SCRIPT" ]; then
    echo "Error: Script '$SCRIPT' not found!"
    exit 1
fi

# Run the appropriate script
echo "Running application seed script for $ENV environment..."
$SCRIPT

# Check the exit status
if [ $? -eq 0 ]; then
    echo "Application seed completed successfully for $ENV environment."
else
    echo "Application seed failed for $ENV environment."
    exit 1
fi
