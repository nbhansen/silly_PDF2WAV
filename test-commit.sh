#!/bin/bash
# Pre-commit test validation - ensures code quality before commits
# Usage: ./test-commit.sh

set -e

echo "🔍 Pre-commit validation starting..."
echo "=" * 50

# Ensure virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
fi

# Step 1: Run TDD tests first (fast feedback)
echo "📋 Step 1: Running TDD tests..."
python run_tests.py tdd-fast

# Step 2: Run all unit tests
echo ""
echo "📋 Step 2: Running all unit tests..."
python run_tests.py commit

# Step 3: Quick integration test check
echo ""
echo "📋 Step 3: Running integration tests..."
python run_tests.py integration

echo ""
echo "✅ All pre-commit tests passed!"
echo "🚀 Safe to commit your changes."
echo ""
echo "💡 Next steps:"
echo "   git add ."
echo "   git commit -m 'Your commit message'"