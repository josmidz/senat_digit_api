#!/bin/bash
# =============================================================================
# Docker helper script for SenatDigit Apps API
#
# Usage:
#   ./docker/docker-run.sh <command> <env>
#
# Commands:
#   build   [env]   — Build the Docker image for the given environment
#   up      [env]   — Start services (detached)
#   down    [env]   — Stop and remove services
#   restart [env]   — Restart services
#   logs    [env]   — Tail logs
#   seed    [env]   — Run database seeds inside the running container
#   shell   [env]   — Open a bash shell in the running container
#   status          — Show status of all containers
#   fix     [env]   — Full rebuild: down → cleanup → build → up
#   cleanup         — Standard Docker cleanup (safe)
#   cleanup-deep    — Aggressive cleanup (reclaim max space)
#   disk            — Show Docker disk usage
#   cron-install    — Install weekly auto-cleanup cron job
#   cron-uninstall  — Remove auto-cleanup cron job
#   ps              — Alias for status
#
# Environments:
#   local   — Local dev (MongoDB + Redis included)
#   dev     — Development (VPS — external DB)
#   prod    — Production (VPS — external DB)
#
# Examples:
#   ./docker/docker-run.sh up local
#   ./docker/docker-run.sh seed dev
#   ./docker/docker-run.sh fix prod
#   ./docker/docker-run.sh logs local
#   ./docker/docker-run.sh cleanup
#   ./docker/docker-run.sh cleanup-deep
# =============================================================================
set -eo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Navigate to project root (parent of docker/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# ---------------------------------------------------------------- helpers ---
show_help() {
    head -30 "$0" | grep -E "^#" | sed 's/^# *//'
}

resolve_profile() {
    case "${1:-local}" in
        local)                  echo "local" ;;
        dev|development)        echo "dev" ;;
        prod|production)        echo "prod" ;;
        *)
            echo -e "${RED}❌ Unknown environment: $1${NC}" >&2
            echo -e "${YELLOW}Valid options: local, dev, prod${NC}" >&2
            exit 1
            ;;
    esac
}

container_name() {
    case "${1}" in
        local) echo "senat_digit_api_local" ;;
        dev)   echo "senat_digit_api_dev" ;;
        prod)  echo "senat_digit_api_prod" ;;
    esac
}

# ---------------------------------------------------------------- commands ---
CMD="${1:-help}"
ENV_ARG="${2:-local}"
PROFILE=$(resolve_profile "${ENV_ARG}")
CONTAINER=$(container_name "${PROFILE}")

# Map profile → env file (used for both YAML substitution and container env)
case "${PROFILE}" in
    local) ENV_FILE=".env.local" ;;
    dev)   ENV_FILE=".env.development" ;;
    prod)  ENV_FILE=".env.production" ;;
esac
[[ ! -f "${ENV_FILE}" ]] && echo -e "${RED}❌ Missing ${ENV_FILE} — create it before running.${NC}" && exit 1

COMPOSE="docker compose --profile ${PROFILE} --env-file ${ENV_FILE}"

case "${CMD}" in
    build)
        echo -e "${BLUE}🔨 Building image for profile=${PROFILE}...${NC}"
        ${COMPOSE} build
        echo -e "${GREEN}✅ Build completed${NC}"
        ;;

    up|start)
        echo -e "${BLUE}🚀 Starting services for profile=${PROFILE}...${NC}"
        ${COMPOSE} up -d --build
        echo -e "${GREEN}✅ Services started${NC}"
        echo -e "${YELLOW}📋 Container status:${NC}"
        docker compose ps
        ;;

    down|stop)
        echo -e "${BLUE}🛑 Stopping services for profile=${PROFILE}...${NC}"
        ${COMPOSE} down
        echo -e "${GREEN}✅ Services stopped${NC}"
        ;;

    restart)
        echo -e "${BLUE}🔄 Restarting services for profile=${PROFILE}...${NC}"
        ${COMPOSE} restart
        echo -e "${GREEN}✅ Restarted${NC}"
        docker compose ps
        ;;

    logs)
        echo -e "${BLUE}📝 Tailing logs for ${CONTAINER}...${NC}"
        docker logs -f "${CONTAINER}" --tail 100
        ;;

    seed|seeds)
        SEED_ENV="${3:-${ENV_ARG}}"
        echo -e "${BLUE}🌱 Running seeds (env=${SEED_ENV}) in ${CONTAINER}...${NC}"
        docker exec -it "${CONTAINER}" /entrypoint.sh seed "${SEED_ENV}"
        echo -e "${GREEN}✅ Seeds completed${NC}"
        ;;

    shell|bash)
        echo -e "${BLUE}🐚 Opening shell in ${CONTAINER}...${NC}"
        docker exec -it "${CONTAINER}" /bin/bash
        ;;

    status|ps)
        echo -e "${BLUE}📋 Container status:${NC}"
        docker compose ps -a
        ;;

    fix)
        echo -e "${BLUE}🔧 Full rebuild for profile=${PROFILE}...${NC}"
        ${COMPOSE} down --remove-orphans 2>/dev/null || true
        echo -e "${YELLOW}🗑️  Cleaning up before rebuild...${NC}"
        # Remove dangling images, stopped containers, build cache
        docker container prune -f 2>/dev/null || true
        docker image prune -f 2>/dev/null || true
        docker builder prune -f --filter "until=24h" 2>/dev/null || true
        # Remove project-specific old images
        docker images --filter "reference=*senat_digit_api*" -q 2>/dev/null | xargs -r docker rmi -f 2>/dev/null || true
        echo -e "${YELLOW}🔨 Rebuilding...${NC}"
        ${COMPOSE} up -d --build
        echo -e "${GREEN}✅ Fix completed${NC}"
        sleep 3
        docker compose ps
        ;;

    cleanup|clean)
        echo -e "${BLUE}🧹 Running standard Docker cleanup...${NC}"
        bash "${SCRIPT_DIR}/docker-cleanup.sh" --standard
        ;;

    cleanup-deep|clean-deep|purge)
        echo -e "${BLUE}🧹 Running aggressive Docker cleanup...${NC}"
        bash "${SCRIPT_DIR}/docker-cleanup.sh" --aggressive
        ;;

    disk|df|usage)
        bash "${SCRIPT_DIR}/docker-cleanup.sh" --status
        ;;

    cron-install)
        bash "${SCRIPT_DIR}/docker-cleanup.sh" --install-cron
        ;;

    cron-uninstall)
        bash "${SCRIPT_DIR}/docker-cleanup.sh" --uninstall-cron
        ;;

    help|-h|--help)
        show_help
        ;;

    *)
        echo -e "${RED}❌ Unknown command: ${CMD}${NC}"
        show_help
        exit 1
        ;;
esac
