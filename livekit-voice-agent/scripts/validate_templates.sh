#!/bin/bash

# Template Validation Script
# Validates that all Python templates have correct syntax

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$(dirname "$SCRIPT_DIR")/templates"

echo "🔍 Validating LiveKit Voice Agent Templates"
echo "==========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

ERRORS=0

# Function to validate Python file syntax
validate_python() {
    local file=$1
    echo -n "Checking $(basename $file)... "

    if python3 -m py_compile "$file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        python3 -m py_compile "$file"
        return 1
    fi
}

# Validate all Python files in templates
echo "📝 Validating Python syntax:"
echo ""

for pyfile in "$TEMPLATE_DIR"/**/*.py "$TEMPLATE_DIR"/*.py; do
    if [ -f "$pyfile" ]; then
        if ! validate_python "$pyfile"; then
            ERRORS=$((ERRORS + 1))
        fi
    fi
done

echo ""

# Check for required files
echo "📂 Checking required files:"
echo ""

REQUIRED_FILES=(
    "$TEMPLATE_DIR/main_entry_point.py"
    "$TEMPLATE_DIR/agents/intro_agent.py"
    "$TEMPLATE_DIR/agents/specialist_agent.py"
    "$TEMPLATE_DIR/agents/escalation_agent.py"
    "$TEMPLATE_DIR/models/shared_data.py"
    "$TEMPLATE_DIR/pyproject.toml"
    "$TEMPLATE_DIR/.env.example"
    "$TEMPLATE_DIR/Dockerfile"
)

for file in "${REQUIRED_FILES[@]}"; do
    echo -n "Checking $(basename $file)... "
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Missing${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""

# Summary
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All validations passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ $ERRORS error(s) found${NC}"
    exit 1
fi
