#!/bin/bash
# =============================================================================
# Docker Cleanup Script for SenatDigit Apps API
# Prevents disk from filling up (40GB VPS protection)
#
# Usage:
#   ./docker/docker-cleanup.sh              # Standard cleanup (safe)
#   ./docker/docker-cleanup.sh --aggressive # Deep cleanup (reclaim max space)
#   ./docker/docker-cleanup.sh --cron       # Silent mode for cron jobs
#   ./docker/docker-cleanup.sh --status     # Show Docker disk usage only
#   ./docker/docker-cleanup.sh --install-cron  # Install weekly cron job
#   ./docker/docker-cleanup.sh --uninstall-cron # Remove cron job
#
# What gets cleaned:
#   Standard:    stopped containers, dangling images, unused networks, build cache
#   Aggressive:  + ALL unused images, ALL unused volumes (except named ones)
#
# Recommended: run weekly via cron to keep VPS healthy
# =============================================================================
set -eo pipefail

# Colors (disabled in cron mode)
if [[ "${1}" == "--cron" ]]; then
    RED='' GREEN='' YELLOW='' BLUE='' NC=''
else
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
CLEANUP_LOG="${LOG_DIR}/docker-cleanup.log"

mkdir -p "${LOG_DIR}"

# ================================================================= helpers ===
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "$msg" | tee -a "${CLEANUP_LOG}"
}

bytes_to_human() {
    local bytes=$1
    if (( bytes >= 1073741824 )); then
        echo "$(( bytes / 1073741824 ))GB"
    elif (( bytes >= 1048576 )); then
        echo "$(( bytes / 1048576 ))MB"
    elif (( bytes >= 1024 )); then
        echo "$(( bytes / 1024 ))KB"
    else
        echo "${bytes}B"
    fi
}

show_disk_usage() {
    log "${BLUE}=== Disk Usage ===${NC}"

    # System disk
    log "${YELLOW}System disk:${NC}"
    df -h / | tail -1 | awk '{printf "  Total: %s | Used: %s (%s) | Available: %s\n", $2, $3, $5, $4}'

    # Docker disk usage
    log "${YELLOW}Docker disk usage:${NC}"
    docker system df 2>/dev/null || log "  (Docker not running)"

    # Count items
    local containers=$(docker ps -aq 2>/dev/null | wc -l | tr -d ' ')
    local images=$(docker images -q 2>/dev/null | wc -l | tr -d ' ')
    local volumes=$(docker volume ls -q 2>/dev/null | wc -l | tr -d ' ')
    local networks=$(docker network ls -q 2>/dev/null | wc -l | tr -d ' ')
    local dangling=$(docker images -f "dangling=true" -q 2>/dev/null | wc -l | tr -d ' ')

    log "  Containers: ${containers} | Images: ${images} | Volumes: ${volumes} | Networks: ${networks} | Dangling images: ${dangling}"
}

# ============================================================ Standard cleanup
standard_cleanup() {
    log "${BLUE}=== Standard Docker Cleanup ===${NC}"

    # 1. Remove stopped containers
    local stopped=$(docker ps -aq --filter "status=exited" 2>/dev/null | wc -l | tr -d ' ')
    if [[ "${stopped}" -gt 0 ]]; then
        log "${YELLOW}Removing ${stopped} stopped containers...${NC}"
        docker container prune -f 2>/dev/null
        log "${GREEN}  Done${NC}"
    else
        log "  No stopped containers"
    fi

    # 2. Remove dangling images (untagged)
    local dangling=$(docker images -f "dangling=true" -q 2>/dev/null | wc -l | tr -d ' ')
    if [[ "${dangling}" -gt 0 ]]; then
        log "${YELLOW}Removing ${dangling} dangling images...${NC}"
        docker image prune -f 2>/dev/null
        log "${GREEN}  Done${NC}"
    else
        log "  No dangling images"
    fi

    # 3. Remove unused networks
    log "${YELLOW}Removing unused networks...${NC}"
    docker network prune -f 2>/dev/null
    log "${GREEN}  Done${NC}"

    # 4. Remove build cache older than 7 days
    log "${YELLOW}Removing build cache older than 7 days...${NC}"
    docker builder prune -f --filter "until=168h" 2>/dev/null
    log "${GREEN}  Done${NC}"

    # 5. Remove old log files (container JSON logs > 50MB)
    log "${YELLOW}Truncating large container logs...${NC}"
    local log_dir="/var/lib/docker/containers"
    if [[ -d "${log_dir}" ]]; then
        find "${log_dir}" -name "*-json.log" -size +50M -exec truncate -s 0 {} \; 2>/dev/null || true
        log "${GREEN}  Done${NC}"
    else
        log "  Skipped (no root access or different Docker root)"
    fi

    # 6. Clean project-specific logs
    log "${YELLOW}Cleaning project logs older than 30 days...${NC}"
    find "${PROJECT_ROOT}/logs" -name "*.log" -mtime +30 -delete 2>/dev/null || true
    find "${PROJECT_ROOT}/bash/seeds/logs" -name "*.log" -mtime +30 -delete 2>/dev/null || true
    log "${GREEN}  Done${NC}"
}

# ========================================================= Aggressive cleanup
aggressive_cleanup() {
    log "${BLUE}=== Aggressive Docker Cleanup ===${NC}"
    log "${RED}WARNING: This removes ALL unused images and build cache!${NC}"

    # Run standard cleanup first
    standard_cleanup

    # 7. Remove ALL unused images (not just dangling)
    log "${YELLOW}Removing ALL unused images...${NC}"
    docker image prune -a -f 2>/dev/null
    log "${GREEN}  Done${NC}"

    # 8. Remove ALL build cache
    log "${YELLOW}Removing ALL build cache...${NC}"
    docker builder prune -a -f 2>/dev/null
    log "${GREEN}  Done${NC}"

    # 9. Remove unused volumes (EXCEPT named project volumes)
    log "${YELLOW}Removing dangling volumes (keeping named ones)...${NC}"
    docker volume ls -qf "dangling=true" 2>/dev/null | while read -r vol; do
        # Keep named project volumes
        if [[ "${vol}" != senat_digit_* ]]; then
            docker volume rm "${vol}" 2>/dev/null || true
        fi
    done
    log "${GREEN}  Done${NC}"

    # 10. Full system prune (nuclear option)
    log "${YELLOW}Running docker system prune...${NC}"
    docker system prune -f --filter "until=24h" 2>/dev/null
    log "${GREEN}  Done${NC}"
}

# ============================================================== Install cron
install_cron() {
    local cron_script="${SCRIPT_DIR}/docker-cleanup.sh"
    local cron_entry="0 3 * * 0 ${cron_script} --cron >> ${CLEANUP_LOG} 2>&1"

    # Check if already installed
    if crontab -l 2>/dev/null | grep -q "docker-cleanup.sh"; then
        log "${YELLOW}Cron job already installed. Updating...${NC}"
        # Remove old entry
        crontab -l 2>/dev/null | grep -v "docker-cleanup.sh" | crontab -
    fi

    # Add new entry
    (crontab -l 2>/dev/null; echo "${cron_entry}") | crontab -
    log "${GREEN}Cron job installed: runs every Sunday at 3:00 AM${NC}"
    log "  Entry: ${cron_entry}"
    log "  Logs:  ${CLEANUP_LOG}"
}

uninstall_cron() {
    if crontab -l 2>/dev/null | grep -q "docker-cleanup.sh"; then
        crontab -l 2>/dev/null | grep -v "docker-cleanup.sh" | crontab -
        log "${GREEN}Cron job removed${NC}"
    else
        log "${YELLOW}No cron job found${NC}"
    fi
}

# =================================================================== main ===
main() {
    local mode="${1:---standard}"

    log ""
    log "=========================================="
    log "  Docker Cleanup — $(date '+%Y-%m-%d %H:%M:%S')"
    log "=========================================="

    show_disk_usage

    case "${mode}" in
        --standard|-s|"")
            standard_cleanup
            ;;
        --aggressive|-a|--deep)
            aggressive_cleanup
            ;;
        --cron)
            # Cron mode: standard cleanup + silent
            standard_cleanup
            ;;
        --status|--df)
            # Already shown above
            ;;
        --install-cron)
            install_cron
            ;;
        --uninstall-cron)
            uninstall_cron
            ;;
        --help|-h)
            head -18 "$0" | grep -E "^#" | sed 's/^# *//'
            exit 0
            ;;
        *)
            echo "Unknown option: ${mode}"
            echo "Usage: $0 [--standard|--aggressive|--cron|--status|--install-cron|--uninstall-cron]"
            exit 1
            ;;
    esac

    log ""
    log "${BLUE}=== After Cleanup ===${NC}"
    show_disk_usage
    log "${GREEN}Cleanup complete${NC}"
}

main "$@"
