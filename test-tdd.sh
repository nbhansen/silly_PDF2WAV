#!/bin/bash
# Quick TDD test runner - runs all 187 TDD tests
# Usage: ./test-tdd.sh [fast|quiet|coverage]

set -e

# Ensure virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
fi

# Parse optional argument
MODE="${1:-normal}"

case "$MODE" in
    "fast")
        echo "🚀 Running TDD tests with fast failure..."
        python run_tests.py tdd-fast
        ;;
    "quiet")
        echo "🤫 Running TDD tests quietly..."
        python run_tests.py tdd-quiet
        ;;
    "coverage")
        echo "📊 Running TDD tests with coverage..."
        python run_tests.py tdd-coverage
        ;;
    *)
        echo "📋 Running all TDD tests..."
        python run_tests.py tdd
        ;;
esac

echo ""
echo "💡 Tip: Use './test-tdd.sh fast' for quick feedback during development"