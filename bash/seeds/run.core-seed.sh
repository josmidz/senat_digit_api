#!/bin/bash
# bash/seeds/run.core-seed.sh
# Exit on error
set -e

# Function to display usage information
show_help() {
    echo "Usage: ./run.core-seed.sh [environment]"
    echo ""
    echo "Runs the core seed script for the specified environment."
    echo ""
    echo "Environments:"
    echo "  dev       - Development environment (default)"
    echo "  prod      - Production environment"
    echo "  local     - Local environment"
    echo "  stage     - Staging environment"
    echo "  test      - Testing environment"
    echo ""
    echo "Examples:"
    echo "  ./run.core-seed.sh dev     # Run app seed for development environment"
    echo "  ./run.core-seed.sh prod    # Run app seed for production environment"
    echo "  ./run.core-seed.sh local   # Run app seed for local environment"
    echo "  ./run.core-seed.sh stage   # Run app seed for staging environment"
    echo "  ./run.core-seed.sh test    # Run app seed for testing environment"
}

# Get the environment from the command line argument
ENV=${1:-dev}

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Validate the environment
case "$ENV" in
    "dev"|"development")
        SCRIPT="$SCRIPT_DIR/run.seed.dev.core.sh"
        ;;
    "prod"|"production")
        SCRIPT="$SCRIPT_DIR/run.seed.prod.core.sh"
        ;;
    "local")
        SCRIPT="$SCRIPT_DIR/run.seed.local.core.sh"
        ;;
    "stage"|"staging")
        SCRIPT="$SCRIPT_DIR/run.seed.stage.core.sh"
        ;;
    "test"|"testing")
        SCRIPT="$SCRIPT_DIR/run.seed.test.core.sh"
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
echo "Running core seed script for $ENV environment..."
$SCRIPT

# Check the exit status
if [ $? -eq 0 ]; then
    echo "Core seed completed successfully for $ENV environment."
else
    echo "Core seed failed for $ENV environment."
    exit 1
fi
