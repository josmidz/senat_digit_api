#!/bin/bash
# =============================================================================
# One-shot setup: Create .venv, install all deps, export to requirements files
#
# Usage:
#   ./setup-venv.sh              # Full setup (create venv + install + export)
#   ./setup-venv.sh --install    # Only install deps into existing .venv
#   ./setup-venv.sh --export     # Only export deps to requirements.in/txt
#   ./setup-venv.sh --clean      # Remove .venv and start fresh
#
# This script:
#   1. Creates a Python 3.11 virtual environment (.venv)
#   2. Upgrades pip, setuptools, wheel
#   3. Installs pip-tools
#   4. Compiles requirements.in → requirements.txt (if requirements.in exists)
#   5. Installs all deps from requirements.txt
#   6. Exports currently installed packages to requirements.txt
#   7. Sets macOS library paths for WeasyPrint/Pango (if on macOS)
# =============================================================================
set -eo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"
cd "${PROJECT_ROOT}"

VENV_DIR="${PROJECT_ROOT}/.venv"
PYTHON_VERSION="3.11"

# ================================================================ helpers ===
detect_python() {
    # Try exact version first, then fallback
    for cmd in "python${PYTHON_VERSION}" "python3.11" "python3" "python"; do
        if command -v "${cmd}" &>/dev/null; then
            local ver
            ver=$("${cmd}" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
            if [[ "${ver}" == "${PYTHON_VERSION}" ]]; then
                echo "${cmd}"
                return 0
            fi
        fi
    done
    # Fallback: any python3
    for cmd in "python3" "python"; do
        if command -v "${cmd}" &>/dev/null; then
            echo -e "${YELLOW}⚠️  Python ${PYTHON_VERSION} not found, using $(${cmd} --version)${NC}" >&2
            echo "${cmd}"
            return 0
        fi
    done
    echo -e "${RED}❌ No Python interpreter found. Install Python ${PYTHON_VERSION}+${NC}" >&2
    exit 1
}

setup_macos_libs() {
    if [[ "$(uname)" == "Darwin" ]]; then
        echo -e "${YELLOW}🍎 Setting macOS library paths for WeasyPrint/Pango...${NC}"
        export DYLD_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_LIBRARY_PATH}"
        export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:/opt/homebrew/opt/libffi/lib/pkgconfig:${PKG_CONFIG_PATH}"
        export FONTCONFIG_PATH="/opt/homebrew/etc/fonts"
        export LDFLAGS="-L/opt/homebrew/opt/libffi/lib"
        export CPPFLAGS="-I/opt/homebrew/opt/libffi/include"
    fi
}

create_venv() {
    local py_cmd="$1"
    echo -e "${BLUE}🛠️  Creating virtual environment with ${py_cmd}...${NC}"
    "${py_cmd}" -m venv "${VENV_DIR}"
    echo -e "${GREEN}✅ Virtual environment created at ${VENV_DIR}${NC}"
}

activate_venv() {
    if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
        echo -e "${RED}❌ No .venv found at ${VENV_DIR}${NC}" >&2
        exit 1
    fi
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
    echo -e "${GREEN}✅ Virtual environment activated ($(python --version))${NC}"
}

install_deps() {
    echo -e "${BLUE}📦 Upgrading pip, setuptools, wheel...${NC}"
    pip install --upgrade pip setuptools wheel

    echo -e "${BLUE}📦 Installing pip-tools...${NC}"
    pip install --upgrade pip-tools

    # Compile requirements.in → requirements.txt if requirements.in exists
    if [[ -f "${PROJECT_ROOT}/requirements.in" ]]; then
        echo -e "${BLUE}📦 Compiling requirements.in → requirements.txt...${NC}"
        pip-compile --strip-extras --output-file=requirements.txt requirements.in
        echo -e "${GREEN}✅ requirements.txt compiled from requirements.in${NC}"
    fi

    # Install from requirements.txt
    if [[ -f "${PROJECT_ROOT}/requirements.txt" ]]; then
        echo -e "${BLUE}📦 Installing dependencies from requirements.txt...${NC}"
        pip install --use-pep517 -r requirements.txt
        echo -e "${BLUE}📦 Installing Uvicorn/WebSocket extras with requirements.txt constraints...${NC}"
        pip install --upgrade -c requirements.txt 'uvicorn[standard]' websockets wsproto
        echo -e "${GREEN}✅ All dependencies installed${NC}"
    else
        echo -e "${RED}❌ No requirements.txt found${NC}" >&2
        exit 1
    fi
}

export_deps() {
    echo -e "${BLUE}📤 Exporting installed packages...${NC}"

    # Export full freeze (for exact reproducibility)
    pip freeze | grep -v "^\-e" > requirements.txt
    echo -e "${GREEN}✅ requirements.txt updated ($(wc -l < requirements.txt | tr -d ' ') packages)${NC}"

    # Also update requirements.in with top-level packages (non-transitive)
    if command -v pip-compile &>/dev/null && [[ -f requirements.in ]]; then
        echo -e "${BLUE}📤 Re-compiling requirements.in → requirements.txt (pinned)...${NC}"
        pip-compile --strip-extras --output-file=requirements.txt requirements.in
        echo -e "${GREEN}✅ requirements.txt re-compiled from requirements.in${NC}"
    fi

    echo -e "${GREEN}📄 requirements.txt ready${NC}"
}

verify_install() {
    echo -e "${BLUE}🔍 Verifying critical imports...${NC}"
    python -c "
try:
    from fastapi import FastAPI
    print('  ✅ FastAPI')
except ImportError as e:
    print(f'  ❌ FastAPI: {e}')

try:
    import motor
    print('  ✅ Motor (MongoDB async)')
except ImportError as e:
    print(f'  ❌ Motor: {e}')

try:
    import beanie
    print('  ✅ Beanie (ODM)')
except ImportError as e:
    print(f'  ❌ Beanie: {e}')

try:
    import redis
    print('  ✅ Redis')
except ImportError as e:
    print(f'  ❌ Redis: {e}')

try:
    from weasyprint import HTML
    print('  ✅ WeasyPrint')
except Exception as e:
    print(f'  ⚠️  WeasyPrint: {e}')

try:
    import uvicorn
    print('  ✅ Uvicorn')
except ImportError as e:
    print(f'  ❌ Uvicorn: {e}')

try:
    import gunicorn
    print('  ✅ Gunicorn')
except ImportError as e:
    print(f'  ❌ Gunicorn: {e}')
"
    echo -e "${BLUE}🔍 Verifying dependency graph...${NC}"
    pip check
    echo -e "${GREEN}✅ Verification complete${NC}"
}

# ================================================================== main ===
main() {
    local mode="${1:-full}"

    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  SenatDigit Apps API — Virtual Environment Setup${NC}"
    echo -e "${BLUE}============================================${NC}"

    setup_macos_libs

    case "${mode}" in
        --install|-i)
            activate_venv
            install_deps
            verify_install
            ;;
        --export|-e)
            activate_venv
            export_deps
            ;;
        --clean|-c)
            echo -e "${YELLOW}🗑️  Removing existing .venv...${NC}"
            rm -rf "${VENV_DIR}"
            echo -e "${GREEN}✅ Cleaned. Run again without flags for full setup.${NC}"
            ;;
        --verify|-v)
            activate_venv
            verify_install
            ;;
        full|--full|"")
            local py_cmd
            py_cmd=$(detect_python)

            # Remove old venv if broken
            if [[ -d "${VENV_DIR}" ]] && [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
                echo -e "${YELLOW}⚠️  Broken .venv detected, removing...${NC}"
                rm -rf "${VENV_DIR}"
            fi

            # Create venv if not exists
            if [[ ! -d "${VENV_DIR}" ]]; then
                create_venv "${py_cmd}"
            else
                echo -e "${GREEN}✅ Virtual environment already exists${NC}"
            fi

            activate_venv
            install_deps
            export_deps
            verify_install

            echo ""
            echo -e "${GREEN}============================================${NC}"
            echo -e "${GREEN}  🎉 Setup complete!${NC}"
            echo -e "${GREEN}============================================${NC}"
            echo -e "${YELLOW}To activate:  source .venv/bin/activate${NC}"
            echo -e "${YELLOW}To run local: ./bash/runner/run.local.sh${NC}"
            echo -e "${YELLOW}To run seeds: ./bash/seeds/run.seed-all.sh local${NC}"
            ;;
        *)
            echo "Usage: $0 [--full|--install|--export|--clean|--verify]"
            exit 1
            ;;
    esac
}

main "$@"
