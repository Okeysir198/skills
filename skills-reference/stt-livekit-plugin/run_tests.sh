#!/bin/bash

# Test runner script for STT LiveKit Plugin
# This script starts the API, runs tests, and cleans up

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "STT LiveKit Plugin - Test Runner"
echo "================================"

# Check if API is already running
echo -e "\n${YELLOW}Checking if API is running...${NC}"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is already running${NC}"
    API_WAS_RUNNING=true
else
    echo -e "${YELLOW}Starting API with Docker Compose...${NC}"
    docker-compose up -d
    API_WAS_RUNNING=false

    # Wait for API to be ready
    echo "Waiting for API to start..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ API is ready${NC}"
            break
        fi
        sleep 1
        echo -n "."
    done

    if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${RED}✗ API failed to start${NC}"
        docker-compose logs stt-api
        exit 1
    fi
fi

# Check if plugin is installed
echo -e "\n${YELLOW}Checking plugin installation...${NC}"
if python -c "from livekit.plugins import custom_stt" 2>/dev/null; then
    echo -e "${GREEN}✓ Plugin is installed${NC}"
else
    echo -e "${YELLOW}Installing plugin...${NC}"
    cd livekit-plugin-custom-stt
    pip install -e . > /dev/null
    cd ..
    echo -e "${GREEN}✓ Plugin installed${NC}"
fi

# Install test dependencies
echo -e "\n${YELLOW}Installing test dependencies...${NC}"
pip install -r tests/requirements.txt > /dev/null
echo -e "${GREEN}✓ Test dependencies installed${NC}"

# Run tests
echo -e "\n${YELLOW}Running integration tests...${NC}"
echo "================================"

cd tests

if [ "$1" == "--manual" ]; then
    # Run tests manually without pytest
    python test_integration.py
else
    # Run with pytest
    pytest test_integration.py -v "$@"
fi

TEST_EXIT_CODE=$?

cd ..

# Cleanup
if [ "$API_WAS_RUNNING" = false ]; then
    echo -e "\n${YELLOW}Stopping API (started by this script)...${NC}"
    docker-compose down
    echo -e "${GREEN}✓ API stopped${NC}"
fi

# Summary
echo ""
echo "================================"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
fi
echo "================================"

exit $TEST_EXIT_CODE
