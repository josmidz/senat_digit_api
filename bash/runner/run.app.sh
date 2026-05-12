#!/bin/bash
# Exit on error
set -e

# Function to display usage information
show_help() {
    echo "Usage: ./run.app.sh [environment]"
    echo ""
    echo "Runs the application for the specified environment."
    echo ""
    echo "Environments:"
    echo "  dev       - Development environment (default)"
    echo "  prod      - Production environment"
    echo "  local     - Local environment"
    echo "  stage     - Staging environment"
    echo "  test      - Testing environment"
    echo ""
    echo "Examples:"
    echo "  ./run.app.sh dev     # Run application in development environment"
    echo "  ./run.app.sh prod    # Run application in production environment"
    echo "  ./run.app.sh local   # Run application in local environment"
    echo "  ./run.app.sh stage   # Run application in staging environment"
    echo "  ./run.app.sh test    # Run application in testing environment"
}

# Get the environment from the command line argument
ENV=${1:-dev}

# Validate the environment
case "$ENV" in
    "dev"|"development")
        SCRIPT="./run.dev.sh"
        ;;
    "prod"|"production")
        SCRIPT="./run.prod.sh"
        ;;
    "local")
        SCRIPT="./run.local.sh"
        ;;
    "stage"|"staging")
        SCRIPT="./run.stage.sh"
        ;;
    "test"|"testing")
        SCRIPT="./run.test.sh"
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
echo "Running application for $ENV environment..."
$SCRIPT

# Note: We don't check the exit status here because the application will keep running
# until it's terminated by the user
uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT:-8000} --reload
