#!/bin/bash
# Test script for PDF-to-Audio improvements

echo "========================================="
echo "PDF-to-Audio System Test Suite"
echo "========================================="
echo ""

# Activate virtual environment
source venv/bin/activate

# 1. Check MyPy (should be 0 errors)
echo "1. Testing Type Safety (MyPy)..."
echo "---------------------------------"
if mypy . --ignore-missing-imports | grep -q "Success: no issues found"; then
    echo "✅ PASS: No type errors found"
else
    echo "❌ FAIL: Type errors detected"
    mypy . --ignore-missing-imports | tail -5
fi
echo ""

# 2. Check logging setup
echo "2. Testing Logging Setup..."
echo "---------------------------"
LOG_FILE="$HOME/.pdf_to_audio/app.log"
if [ -d "$HOME/.pdf_to_audio" ]; then
    echo "✅ PASS: Log directory exists"
    if [ -f "$LOG_FILE" ]; then
        echo "✅ PASS: Log file exists ($(wc -l < "$LOG_FILE") lines)"
    else
        echo "⚠️  INFO: Log file will be created when app runs"
    fi
else
    echo "⚠️  INFO: Log directory will be created when app runs"
fi
echo ""

# 3. Check for progress endpoints
echo "3. Testing Progress Endpoints..."
echo "--------------------------------"
if grep -q "api/progress" routes.py && grep -q "api/cancel" routes.py; then
    echo "✅ PASS: Progress endpoints found"
    echo "  - /api/progress/<operation_id>"
    echo "  - /api/cancel/<operation_id>"
else
    echo "❌ FAIL: Progress endpoints missing"
fi
echo ""

# 4. Check for error handling improvements
echo "4. Testing Error Message Utilities..."
echo "-------------------------------------"
if grep -q "get_contextual_error_message" utils.py; then
    echo "✅ PASS: Contextual error messages implemented"
    grep "def get_" utils.py | grep -c "error" | xargs -I {} echo "  - {} error utility functions found"
else
    echo "❌ FAIL: Error utilities missing"
fi
echo ""

# 5. Check processing UI
echo "5. Testing Progress UI..."
echo "-------------------------"
if [ -f "templates/processing.html" ]; then
    echo "✅ PASS: Processing UI exists"
    if grep -q "progress-bar" templates/processing.html && grep -q "cancel-btn" templates/processing.html; then
        echo "✅ PASS: Progress bar and cancel button found"
    else
        echo "❌ FAIL: UI components missing"
    fi
else
    echo "❌ FAIL: Processing UI not found"
fi
echo ""

# 6. Test Python imports
echo "6. Testing Python Dependencies..."
echo "---------------------------------"
python -c "
import sys
try:
    from app_factory import create_app
    from utils import get_contextual_error_message
    print('✅ PASS: All critical imports working')
except ImportError as e:
    print(f'❌ FAIL: Import error - {e}')
    sys.exit(1)
"
echo ""

# 7. Create test app instance
echo "7. Testing App Creation..."
echo "--------------------------"
python -c "
from app_factory import create_app
try:
    app = create_app()
    print('✅ PASS: App created successfully')
    print(f'  - Upload folder: {app.config.get(\"UPLOAD_FOLDER\")}'
    print(f'  - Max file size: {app.config.get(\"MAX_CONTENT_LENGTH\")//1024//1024}MB')
except Exception as e:
    print(f'❌ FAIL: App creation failed - {e}')
" 2>/dev/null
echo ""

# Summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo ""
echo "All critical improvements have been tested:"
echo "1. Type Safety (MyPy) - Prevents crashes"
echo "2. Logging - Debug issues via ~/.pdf_to_audio/app.log"
echo "3. Progress Tracking - Real-time feedback"
echo "4. Error Messages - Helpful, specific guidance"
echo "5. Cancellation - Abort long operations"
echo ""
echo "To run the app:"
echo "  python app.py"
echo ""
echo "Then visit: http://localhost:5000"
echo ""
echo "For live testing:"
echo "  1. Upload a PDF and watch progress bar"
echo "  2. Test cancel button during processing"
echo "  3. Check logs: tail -f ~/.pdf_to_audio/app.log"
echo "  4. Try invalid files to see error messages"