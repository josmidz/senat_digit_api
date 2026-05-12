#!/bin/bash
# bash/seeds/run.seed.sh
# Exit on error
set -e

# Function to display usage information
show_help() {
    echo "Usage: ./run.seed.sh [environment]"
    echo ""
    echo "Runs the database seed script for the specified environment."
    echo ""
    echo "Environments:"
    echo "  dev       - Development environment (default)"
    echo "  prod      - Production environment"
    echo "  local     - Local environment"
    echo "  stage     - Staging environment"
    echo "  test      - Testing environment"
    echo ""
    echo "Examples:"
    echo "  ./run.seed.sh dev     # Run seed for development environment"
    echo "  ./run.seed.sh prod    # Run seed for production environment"
    echo "  ./run.seed.sh local   # Run seed for local environment"
    echo "  ./run.seed.sh stage   # Run seed for staging environment"
    echo "  ./run.seed.sh test    # Run seed for testing environment"
}

# Get the environment from the command line argument
ENV=${1:-dev}

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Validate the environment
case "$ENV" in
    "dev"|"development")
        SCRIPT="$SCRIPT_DIR/run.seed.dev.sh"
        ;;
    "prod"|"production")
        SCRIPT="$SCRIPT_DIR/run.seed.prod.sh"
        ;;
    "local")
        SCRIPT="$SCRIPT_DIR/run.seed.local.sh"
        ;;
    "stage"|"staging")
        SCRIPT="$SCRIPT_DIR/run.seed.stage.sh"
        ;;
    "test"|"testing")
        SCRIPT="$SCRIPT_DIR/run.seed.test.sh"
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
echo "Running database seed script for $ENV environment..."
$SCRIPT

# Check the exit status
if [ $? -eq 0 ]; then
    echo "Database seed completed successfully for $ENV environment."
else
    echo "Database seed failed for $ENV environment."
    exit 1
fi
