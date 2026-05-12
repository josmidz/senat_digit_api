#!/bin/bash
# =============================================================================
# Docker Entrypoint for SenatDigit Apps API
# Commands: serve (default), seed, shell
# =============================================================================
set -eo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Resolve ENV name to .env filename suffix
resolve_env_suffix() {
    case "${ENV:-local}" in
        local)        echo "local" ;;
        development)  echo "development" ;;
        production)   echo "production" ;;
        dev)          export ENV=development; echo "development" ;;
        prod)         export ENV=production;  echo "production" ;;
        *)            echo "${ENV}" ;;
    esac
}

ENV_SUFFIX=$(resolve_env_suffix)
echo -e "${BLUE}🐳 SenatDigit Apps API — ENV=${ENV} (suffix=${ENV_SUFFIX})${NC}"

# Determine port
APP_PORT="${APP_PORT:-9888}"

# ------------------------------------------------------------------ serve ---
start_server() {
    echo -e "${GREEN}🚀 Starting server on port ${APP_PORT}...${NC}"

    case "${ENV}" in
        local)
            # Uvicorn with reload for local dev
            # --loop asyncio avoids uvloop/anyio BaseHTTPMiddleware incompatibility
            exec uvicorn app.main:app \
                --host 0.0.0.0 \
                --port "${APP_PORT}" \
                --loop asyncio \
                --reload
            ;;
        development)
            # Gunicorn for development (on VPS)
            exec gunicorn -c configs/gunicorn.conf.py app.main:app
            ;;
        production)
            # Gunicorn for production
            exec gunicorn -c configs/gunicorn.conf.py app.main:app
            ;;
        *)
            echo -e "${YELLOW}⚠️  Unknown ENV=${ENV}, falling back to uvicorn${NC}"
            exec uvicorn app.main:app \
                --host 0.0.0.0 \
                --port "${APP_PORT}" \
                --loop asyncio
            ;;
    esac
}

# ------------------------------------------------------------------- seed ---
run_seeds() {
    local seed_env="${1:-${ENV}}"
    # Map docker ENV values to seed script env names
    case "${seed_env}" in
        development) seed_env="dev" ;;
        production)  seed_env="prod" ;;
    esac

    echo -e "${BLUE}🌱 Running ALL seeds for env=${seed_env}...${NC}"

    # Create logs directory
    mkdir -p bash/seeds/logs

    # Step 1: Database seed
    echo -e "${YELLOW}Step 1: Running database seed...${NC}"
    python3 -m app.modules.core.seeds.seed 2>&1 | tee bash/seeds/logs/${seed_env}_seed_out.log
    echo -e "${GREEN}✅ Database seed done${NC}"

    # Step 2: Application seed
    if [ -f "bash/seeds/run.seed.${seed_env}.app.sh" ]; then
        echo -e "${YELLOW}Step 2: Running application seed...${NC}"
        bash "bash/seeds/run.seed.${seed_env}.app.sh" 2>&1 | tee bash/seeds/logs/${seed_env}_app_seed_out.log
        echo -e "${GREEN}✅ Application seed done${NC}"
    else
        echo -e "${YELLOW}⚠️  No app seed script for env=${seed_env}, skipping${NC}"
    fi

    # Step 3: Core seed
    if [ -f "bash/seeds/run.seed.${seed_env}.core.sh" ]; then
        echo -e "${YELLOW}Step 3: Running core seed...${NC}"
        bash "bash/seeds/run.seed.${seed_env}.core.sh" 2>&1 | tee bash/seeds/logs/${seed_env}_core_seed_out.log
        echo -e "${GREEN}✅ Core seed done${NC}"
    else
        echo -e "${YELLOW}⚠️  No core seed script for env=${seed_env}, skipping${NC}"
    fi

    echo -e "${GREEN}🌱 All seeds completed for env=${seed_env}${NC}"
}

# ---------------------------------------------------------------- dispatch ---
CMD="${1:-serve}"
shift 2>/dev/null || true

case "${CMD}" in
    serve|start|run)
        start_server
        ;;
    seed|seeds)
        run_seeds "$@"
        ;;
    shell|bash)
        exec /bin/bash "$@"
        ;;
    *)
        # Pass through any other command
        exec "$@"
        ;;
esac
