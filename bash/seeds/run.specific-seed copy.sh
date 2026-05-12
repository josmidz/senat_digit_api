# # bash/seeds/run.specific-seed.sh
# #!/bin/bash
# # Exit on error
# set -e

# # Function to display usage information
# show_help() {
#     echo "Usage: ./run.specific-seed.sh [environment]"
#     echo ""
#     echo "Runs the specific seed script for the specified environment."
#     echo ""
#     echo "Environments:"
#     echo "  dev       - Development environment (default)"
#     echo "  prod      - Production environment"
#     echo "  local     - Local environment"
#     echo "  stage     - Staging environment"
#     echo "  test      - Testing environment"
#     echo ""
#     echo "Examples:"
#     echo "  ./run.specific-seed.sh dev     # Run specific seed for development environment"
#     echo "  ./run.specific-seed.sh prod    # Run specific seed for production environment"
#     echo "  ./run.specific-seed.sh local   # Run specific seed for local environment"
#     echo "  ./run.specific-seed.sh stage   # Run specific seed for staging environment"
#     echo "  ./run.specific-seed.sh test    # Run specific seed for testing environment"
# }

# # Get the environment from the command line argument
# ENV=${1:-dev}

# # Get the directory where this script is located
# SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# # Validate the environment
# case "$ENV" in
#     "dev"|"development"|"prod"|"production"|"local"|"stage"|"staging"|"test"|"testing")
#         # Valid environment - all environments use the same specific seed script
#         ;;
#     "help"|"-h"|"--help")
#         show_help
#         exit 0
#         ;;
#     *)
#         echo "Error: Unknown environment '$ENV'"
#         show_help
#         exit 1
#         ;;
# esac

# # Get the project root directory (two levels up from the script directory)
# PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# # Create logs directory if it doesn't exist
# LOGS_DIR="$SCRIPT_DIR/logs"
# mkdir -p "$LOGS_DIR"

# # Set up log files
# SPECIFIC_SEED_OUT_LOG="$LOGS_DIR/specific_seed_${ENV}_out.log"
# SPECIFIC_SEED_ERR_LOG="$LOGS_DIR/specific_seed_${ENV}_err.log"

# echo "Running specific seed script for $ENV environment..."
# echo "Output will be logged to: $SPECIFIC_SEED_OUT_LOG"
# echo "Errors will be logged to: $SPECIFIC_SEED_ERR_LOG"

# # Change to project root
# cd "$PROJECT_ROOT"

# # Activate the virtual environment
# echo "Looking for virtual environment in: $PROJECT_ROOT/.venv"
# if [ -f .venv/bin/activate ]; then
#   echo "Activating virtual environment..."
#   source .venv/bin/activate
#   echo "Virtual environment activated successfully."
# else
#   echo "Virtual environment not found at: $PROJECT_ROOT/.venv"
#   echo "Please create one with: cd $PROJECT_ROOT && python3 -m venv .venv"
#   exit 1
# fi

# # Check if FastAPI is installed in the virtual environment
# echo "Checking if required dependencies are installed..."
# if ! python3 -c "import fastapi" 2>/dev/null; then
#     echo "FastAPI not found in virtual environment. Installing dependencies..."
#     if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
#         pip install -r "$PROJECT_ROOT/requirements.txt"
#         echo "Dependencies installed successfully."
#     else
#         echo "Error: requirements.txt not found. Cannot install dependencies."
#         exit 1
#     fi
# else
#     echo "Required dependencies are available."
# fi

# # Load environment variables from the appropriate .env file
# ENV_FILE="$PROJECT_ROOT/.env.$ENV"
# if [ -f "$ENV_FILE" ]; then
#     echo "Loading environment variables from $ENV_FILE..."
#     set -a
#     source "$ENV_FILE"
#     set +a
# else
#     echo "Warning: $ENV_FILE file not found. Using default environment variables."
# fi

# # Run the specific seed script
# python3 -m app.modules.core.seeds.specific_seed_all > "$SPECIFIC_SEED_OUT_LOG" 2> "$SPECIFIC_SEED_ERR_LOG"

# # Check the exit status
# if [ $? -eq 0 ]; then
#     echo "Specific seed completed successfully for $ENV environment."
#     echo "Output log: $SPECIFIC_SEED_OUT_LOG"
#     echo "Error log: $SPECIFIC_SEED_ERR_LOG"
# else
#     echo "Specific seed failed for $ENV environment."
#     echo "Check the error log for details: $SPECIFIC_SEED_ERR_LOG"
#     echo ""
#     echo "Recent errors:"
#     tail -n 10 "$SPECIFIC_SEED_ERR_LOG" 2>/dev/null || echo "No error log found"
#     exit 1
# fi
