#!/bin/bash

# PDF to Audio App - Test Runner
# Run this script to execute the full test suite

echo "🧪 Running PDF to Audio App Tests..."
echo "======================================"

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "   Consider running: source venv/bin/activate"
    echo ""
fi

# Run tests with verbose output and coverage
echo "📋 Running all tests with coverage..."
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

# Check if tests passed
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo "📊 Coverage report generated in htmlcov/"
    echo "   Open htmlcov/index.html in browser for detailed view"
else
    echo ""
    echo "❌ Some tests failed!"
    exit 1
fi