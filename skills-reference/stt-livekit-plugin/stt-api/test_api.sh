#!/bin/bash

# Test script for STT API
# This script tests the basic functionality of the STT API

set -e

API_URL="${STT_API_URL:-http://localhost:8000}"
echo "Testing STT API at: $API_URL"
echo "================================"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Health check
echo -e "\n1. Testing health endpoint..."
if curl -s -f "$API_URL/health" > /dev/null; then
    echo -e "${GREEN}✓ Health check passed${NC}"
    curl -s "$API_URL/health" | python3 -m json.tool
else
    echo -e "${RED}✗ Health check failed${NC}"
    exit 1
fi

# Test 2: Root endpoint
echo -e "\n2. Testing root endpoint..."
if curl -s -f "$API_URL/" > /dev/null; then
    echo -e "${GREEN}✓ Root endpoint passed${NC}"
    curl -s "$API_URL/" | python3 -m json.tool
else
    echo -e "${RED}✗ Root endpoint failed${NC}"
    exit 1
fi

# Test 3: Transcribe endpoint (if audio file provided)
if [ -n "$1" ]; then
    AUDIO_FILE="$1"
    echo -e "\n3. Testing transcribe endpoint with: $AUDIO_FILE"

    if [ ! -f "$AUDIO_FILE" ]; then
        echo -e "${RED}✗ Audio file not found: $AUDIO_FILE${NC}"
        exit 1
    fi

    RESPONSE=$(curl -s -X POST "$API_URL/transcribe" \
        -F "file=@$AUDIO_FILE" \
        -F "language=en")

    if echo "$RESPONSE" | python3 -c "import sys, json; json.load(sys.stdin)" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Transcribe endpoint passed${NC}"
        echo "$RESPONSE" | python3 -m json.tool
    else
        echo -e "${RED}✗ Transcribe endpoint failed${NC}"
        echo "Response: $RESPONSE"
        exit 1
    fi
else
    echo -e "\n3. Skipping transcribe test (no audio file provided)"
    echo "   Usage: $0 [audio_file.wav]"
fi

echo -e "\n================================"
echo -e "${GREEN}All tests passed!${NC}"
