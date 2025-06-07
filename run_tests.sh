#!/bin/bash
# Test runner script for PDF to Audio Converter

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Running PDF to Audio Converter Test Suite${NC}"
echo "=================================================="

# Default test run with coverage
echo -e "${BLUE}Running all tests with coverage...${NC}"
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

# Check if tests passed
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo -e "${BLUE}Coverage report generated in htmlcov/index.html${NC}"
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi

# Optional: Run specific test categories
# Uncomment as needed:

# Integration tests only
# echo -e "${BLUE}Running integration tests...${NC}"
# pytest tests/test_integration.py -v

# Domain tests only  
# echo -e "${BLUE}Running domain tests...${NC}"
# pytest tests/domain/ -v

# Infrastructure tests only
# echo -e "${BLUE}Running infrastructure tests...${NC}"
# pytest tests/infrastructure/ -v

# Fast tests (exclude slow ones if marked)
# echo -e "${BLUE}Running fast tests only...${NC}"
# pytest tests/ -v -m "not slow"

echo -e "${GREEN}Test run complete!${NC}"