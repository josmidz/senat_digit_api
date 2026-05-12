#!/bin/bash
# check-venv.sh - Virtual Environment Diagnostic Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo -e "${BLUE}🔍 Virtual Environment Diagnostic for senat_digit_api${NC}"
echo -e "${YELLOW}Project Root: $PROJECT_ROOT${NC}"
echo ""

# Check 1: Virtual environment directory
echo -e "${YELLOW}📁 Checking virtual environment directory...${NC}"
VENV_DIR="$PROJECT_ROOT/.venv"
if [ -d "$VENV_DIR" ]; then
    echo -e "${GREEN}✅ Virtual environment directory exists: $VENV_DIR${NC}"
    echo -e "  Size: $(du -sh "$VENV_DIR" | cut -f1)"
    echo -e "  Created: $(stat -c '%y' "$VENV_DIR" 2>/dev/null || stat -f '%Sm' "$VENV_DIR")"
else
    echo -e "${RED}❌ Virtual environment directory not found: $VENV_DIR${NC}"
    echo -e "${YELLOW}💡 Create it with: cd $PROJECT_ROOT && python3 -m venv .venv${NC}"
fi
echo ""

# Check 2: Activation script
echo -e "${YELLOW}🔧 Checking activation script...${NC}"
ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
if [ -f "$ACTIVATE_SCRIPT" ]; then
    echo -e "${GREEN}✅ Activation script exists: $ACTIVATE_SCRIPT${NC}"
    echo -e "  Permissions: $(stat -c '%a' "$ACTIVATE_SCRIPT" 2>/dev/null || stat -f '%A' "$ACTIVATE_SCRIPT")"
else
    echo -e "${RED}❌ Activation script not found: $ACTIVATE_SCRIPT${NC}"
fi
echo ""

# Check 3: Python executable
echo -e "${YELLOW}🐍 Checking Python executable...${NC}"
PYTHON_EXEC="$VENV_DIR/bin/python3"
if [ -f "$PYTHON_EXEC" ]; then
    echo -e "${GREEN}✅ Python executable exists: $PYTHON_EXEC${NC}"
    
    # Test activation and get Python version
    if source "$ACTIVATE_SCRIPT" 2>/dev/null; then
        PYTHON_VERSION=$(python3 --version 2>/dev/null || echo "Unknown")
        echo -e "  Version: $PYTHON_VERSION"
        
        # Check pip
        if command -v pip >/dev/null 2>&1; then
            PIP_VERSION=$(pip --version 2>/dev/null || echo "Unknown")
            echo -e "  Pip: $PIP_VERSION"
        else
            echo -e "${RED}❌ Pip not found in virtual environment${NC}"
        fi
        
        deactivate 2>/dev/null || true
    else
        echo -e "${RED}❌ Failed to activate virtual environment${NC}"
    fi
else
    echo -e "${RED}❌ Python executable not found: $PYTHON_EXEC${NC}"
fi
echo ""

# Check 4: Requirements file
echo -e "${YELLOW}📦 Checking requirements file...${NC}"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo -e "${GREEN}✅ Requirements file exists: $REQUIREMENTS_FILE${NC}"
    PACKAGE_COUNT=$(wc -l < "$REQUIREMENTS_FILE")
    echo -e "  Packages listed: $PACKAGE_COUNT"
    echo -e "  Size: $(du -h "$REQUIREMENTS_FILE" | cut -f1)"
else
    echo -e "${RED}❌ Requirements file not found: $REQUIREMENTS_FILE${NC}"
fi
echo ""

# Check 5: Key dependencies (if venv exists)
if [ -f "$ACTIVATE_SCRIPT" ]; then
    echo -e "${YELLOW}🔍 Checking key dependencies...${NC}"
    
    # Activate virtual environment for testing
    source "$ACTIVATE_SCRIPT" 2>/dev/null || {
        echo -e "${RED}❌ Cannot activate virtual environment for dependency check${NC}"
        exit 1
    }
    
    # Test key dependencies
    DEPENDENCIES=("fastapi" "uvicorn" "motor" "pymongo" "pydantic")
    
    for dep in "${DEPENDENCIES[@]}"; do
        if python3 -c "import $dep" 2>/dev/null; then
            VERSION=$(python3 -c "import $dep; print(getattr($dep, '__version__', 'Unknown'))" 2>/dev/null || echo "Unknown")
            echo -e "${GREEN}✅ $dep: $VERSION${NC}"
        else
            echo -e "${RED}❌ $dep: Not installed${NC}"
        fi
    done
    
    deactivate 2>/dev/null || true
    echo ""
fi

# Check 6: Environment files
echo -e "${YELLOW}📄 Checking environment files...${NC}"
ENV_FILES=(".env.dev" ".env.development" ".env.local" ".env.prod" ".env.production" ".env.test" ".env.testing")

for env_file in "${ENV_FILES[@]}"; do
    ENV_PATH="$PROJECT_ROOT/$env_file"
    if [ -f "$ENV_PATH" ]; then
        echo -e "${GREEN}✅ $env_file exists${NC}"
    else
        echo -e "${YELLOW}⚠️ $env_file not found${NC}"
    fi
done
echo ""

# Check 7: Seed script
echo -e "${YELLOW}🌱 Checking seed script...${NC}"
SEED_SCRIPT="$PROJECT_ROOT/app/modules/core/seeds/specific_seed_all.py"
if [ -f "$SEED_SCRIPT" ]; then
    echo -e "${GREEN}✅ Seed script exists: $SEED_SCRIPT${NC}"
    echo -e "  Size: $(du -h "$SEED_SCRIPT" | cut -f1)"
else
    echo -e "${RED}❌ Seed script not found: $SEED_SCRIPT${NC}"
fi
echo ""

# Summary and recommendations
echo -e "${BLUE}📋 Summary and Recommendations:${NC}"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}🚨 Critical: Virtual environment missing${NC}"
    echo -e "${YELLOW}   Run: cd $PROJECT_ROOT && python3 -m venv .venv${NC}"
fi

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo -e "${RED}🚨 Critical: Requirements file missing${NC}"
    echo -e "${YELLOW}   Ensure requirements.txt exists in project root${NC}"
fi

if [ -f "$ACTIVATE_SCRIPT" ] && [ -f "$REQUIREMENTS_FILE" ]; then
    echo -e "${GREEN}✅ Basic setup looks good${NC}"
    echo -e "${YELLOW}💡 To install/update dependencies:${NC}"
    echo -e "   cd $PROJECT_ROOT"
    echo -e "   source .venv/bin/activate"
    echo -e "   pip install --upgrade pip"
    echo -e "   pip install -r requirements.txt"
fi

echo -e "${YELLOW}💡 To run the seed script:${NC}"
echo -e "   cd $PROJECT_ROOT/bash/seeds"
echo -e "   ./run.specific-seed.sh dev"

echo ""
echo -e "${GREEN}🎉 Diagnostic completed!${NC}"
