# bash/seeds/run.seed-all.sh
#!/bin/bash
# Exit on error
set -e

# Function to display usage information
show_help() {
    echo "Usage: ./run.seed-all.sh [environment]"
    echo ""
    echo "Runs all seed scripts for the specified environment."
    echo ""
    echo "Environments:"
    echo "  dev       - Development environment (default)"
    echo "  prod      - Production environment"
    echo "  local     - Local environment"
    echo "  stage     - Staging environment"
    echo "  test      - Testing environment"
    echo ""
    echo "Examples:"
    echo "  ./run.seed-all.sh dev     # Run all seeds for development environment"
    echo "  ./run.seed-all.sh prod    # Run all seeds for production environment"
    echo "  ./run.seed-all.sh local   # Run all seeds for local environment"
    echo "  ./run.seed-all.sh stage   # Run all seeds for staging environment"
    echo "  ./run.seed-all.sh test    # Run all seeds for testing environment"
}

# Get the environment from the command line argument
ENV=${1:-dev}

# Validate the environment
case "$ENV" in
    "dev"|"development"|"prod"|"production"|"local"|"stage"|"staging"|"test"|"testing")
        # Valid environment
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

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run the database seed script
echo "Step 1: Running database seed script for $ENV environment..."
$SCRIPT_DIR/run.seed.sh $ENV

# Check the exit status
if [ $? -ne 0 ]; then
    echo "Database seed failed for $ENV environment. Aborting."
    exit 1
fi

# Run the application seed script
echo "Step 2: Running application seed script for $ENV environment..."
$SCRIPT_DIR/run.apps-seed.sh $ENV

# Check the exit status
if [ $? -ne 0 ]; then
    echo "Application seed failed for $ENV environment."
    exit 1
fi

# Run the core seed script
echo "Step 3: Running core seed script for $ENV environment..."
$SCRIPT_DIR/run.core-seed.sh $ENV

# Check the exit status
if [ $? -ne 0 ]; then
    echo "Core seed failed for $ENV environment."
    exit 1
fi

# Check the exit status
if [ $? -ne 0 ]; then
    echo "Core seed failed for $ENV environment."
    exit 1
fi

# Run the specific seed script
echo "Step 4: Running specific seed script for $ENV environment..."
$SCRIPT_DIR/run.specific-seed.sh $ENV

# Check the exit status
if [ $? -ne 0 ]; then
    echo "Specific seed failed for $ENV environment."
    exit 1
fi

# Run the user_app_store static seed — must be LAST: depends on RBAC
# profiles + sys_application + rbac_restricted_* junctions all being in
# place. Populates cfg_user_app_store rows keyed by rbac_profile_flag for
# every (static_profile × api_consumer × language) combo, so the very
# first /data/get-applications call from a visitor or customer is served
# from the L2 cache instead of running the slow aggregation.
echo "Step 5: Running user_app_store static seed for $ENV environment..."
PROJECT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
LOGS_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOGS_DIR"
USER_APP_STORE_SEED_OUT_LOG="$LOGS_DIR/${ENV}_user_app_store_seed_out.log"
USER_APP_STORE_SEED_ERR_LOG="$LOGS_DIR/${ENV}_user_app_store_seed_err.log"

# Activate the venv so the python module resolves. Venv lookup mirrors
# what the per-env scripts do above; we don't fail hard on a missing venv
# since by the time we get here every prior step has already passed.
cd "$PROJECT_DIR" || { echo "Failed to navigate to project directory"; exit 1; }
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

# Non-fatal on failure: the L2 cache also populates on-demand on first
# request, so a failed seed just means the first user pays the slow
# aggregation cost once instead of getting a pre-warmed row.
set +e
python3 -m app.modules.core.services.user_app_store.user_app_store_seed_service \
  > "$USER_APP_STORE_SEED_OUT_LOG" 2> "$USER_APP_STORE_SEED_ERR_LOG"
USER_APP_STORE_RC=$?
set -e

if [ $USER_APP_STORE_RC -eq 0 ]; then
  echo "user_app_store static seeding completed successfully. Check $USER_APP_STORE_SEED_OUT_LOG for details."
else
  echo "user_app_store static seeding failed (non-fatal). Check $USER_APP_STORE_SEED_ERR_LOG."
fi

# Step 6: dynamic user_app_store seed — pre-populates per-user rows for
# admin/agent profiles so their first /data/get-applications call hits
# the L2 cache. Calls StaticController.run_formated_applications_core
# (the same helper the live endpoint uses on cache miss), so payloads
# are byte-identical.
echo "Step 6: Running user_app_store dynamic seed for $ENV environment..."
USER_APP_STORE_DYN_OUT_LOG="$LOGS_DIR/${ENV}_user_app_store_dynamic_seed_out.log"
USER_APP_STORE_DYN_ERR_LOG="$LOGS_DIR/${ENV}_user_app_store_dynamic_seed_err.log"
set +e
python3 -m app.modules.core.services.user_app_store.user_app_store_dynamic_seed_service \
  > "$USER_APP_STORE_DYN_OUT_LOG" 2> "$USER_APP_STORE_DYN_ERR_LOG"
USER_APP_STORE_DYN_RC=$?
set -e

if [ $USER_APP_STORE_DYN_RC -eq 0 ]; then
  echo "user_app_store dynamic seeding completed successfully. Check $USER_APP_STORE_DYN_OUT_LOG for details."
else
  echo "user_app_store dynamic seeding failed (non-fatal). Check $USER_APP_STORE_DYN_ERR_LOG."
fi


echo "All seed operations completed successfully for $ENV environment."
