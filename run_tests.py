#!/usr/bin/env python3
"""
Enhanced test runner for PDF to Audio Converter with TDD support.
Supports comprehensive testing strategies including TDD workflows.
"""

import subprocess
import sys
import os


def run_tests(test_type="all"):
    """Run tests with professional options including coverage and TDD support"""
    
    commands = {
        # Comprehensive test suites
        "all": ["python", "-m", "pytest", "tests/", "-v", "--cov", "--cov-report=term", "--cov-report=html"],
        "unit": ["python", "-m", "pytest", "tests/unit/", "-v", "--cov", "--cov-report=term"],
        "integration": ["python", "-m", "pytest", "tests/integration/", "-v"],
        
        # TDD-specific commands
        "tdd": ["python", "-m", "pytest", "tests/unit/", "-k", "tdd", "-v"],
        "tdd-fast": ["python", "-m", "pytest", "tests/unit/", "-k", "tdd", "-v", "-x", "--ff"],
        "tdd-quiet": ["python", "-m", "pytest", "tests/unit/", "-k", "tdd", "-q"],
        "tdd-coverage": ["python", "-m", "pytest", "tests/unit/", "-k", "tdd", "-v", "--cov", "--cov-report=term"],
        
        # Development workflow commands
        "commit": ["python", "-m", "pytest", "tests/unit/", "-v", "-x"],  # Pre-commit validation
        "quick": ["python", "-m", "pytest", "tests/unit/test_domain_models_tdd.py", "-v"],
        "watch": ["python", "-m", "pytest", "tests/unit/", "-k", "tdd", "-v", "-f"],  # Watch mode (if pytest-watch installed)
        
        # Coverage and analysis
        "coverage": ["python", "-m", "pytest", "tests/", "--cov", "--cov-report=term", "--cov-report=html", "--cov-report=json"],
        "no-cov": ["python", "-m", "pytest", "tests/", "-v"],
        "collect": ["python", "-m", "pytest", "tests/", "--collect-only"],
        
        # Individual TDD components
        "models": ["python", "-m", "pytest", "tests/unit/test_domain_models_tdd.py", "-v"],
        "pipeline": ["python", "-m", "pytest", "tests/unit/test_text_pipeline_tdd.py", "-v"],
        "config": ["python", "-m", "pytest", "tests/unit/test_system_config_tdd.py", "-v"],
        "errors": ["python", "-m", "pytest", "tests/unit/test_error_handling_tdd.py", "-v"]
    }
    
    if test_type not in commands:
        print(f"Unknown test type: {test_type}")
        print("\nAvailable test types:")
        print("\n📋 Comprehensive:")
        print("  all        - All tests with coverage")
        print("  unit       - All unit tests with coverage")
        print("  integration- Integration tests only")
        print("\n🔄 TDD Workflows:")
        print("  tdd        - All TDD tests (187 tests)")
        print("  tdd-fast   - TDD tests with fast failure")
        print("  tdd-quiet  - TDD tests, minimal output")
        print("  tdd-coverage- TDD tests with coverage")
        print("\n⚡ Development:")
        print("  commit     - Pre-commit validation")
        print("  quick      - Single fast test")
        print("  watch      - Watch mode (if available)")
        print("\n🔍 Individual Components:")
        print("  models     - Domain models TDD tests")
        print("  pipeline   - Text pipeline TDD tests")
        print("  config     - System config TDD tests")
        print("  errors     - Error handling TDD tests")
        print("\n📊 Analysis:")
        print("  coverage   - Full coverage report")
        print("  collect    - List all available tests")
        return False
    
    cmd = commands[test_type]
    
    # Add helpful context
    test_descriptions = {
        "tdd": "Running all 187 TDD tests",
        "tdd-fast": "Running TDD tests with fast failure on first error",
        "commit": "Running pre-commit validation tests",
        "models": "Testing domain models (47 tests)",
        "pipeline": "Testing text processing pipeline (47 tests)",
        "config": "Testing system configuration (49 tests)",
        "errors": "Testing error handling (44 tests)"
    }
    
    if test_type in test_descriptions:
        print(f"📋 {test_descriptions[test_type]}")
    
    print(f"🚀 Running: {' '.join(cmd)}")
    print("-" * 50)
    
    # Ensure we're in the virtual environment
    if 'VIRTUAL_ENV' not in os.environ:
        print("⚠️  Warning: Not in virtual environment. Run 'source venv/bin/activate' first.")
        print("   Continuing anyway...")
        print()
    
    try:
        result = subprocess.run(cmd)
        print("-" * 50)
        if result.returncode == 0:
            print("✅ Tests passed!")
        else:
            print("❌ Tests failed!")
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted")
        return False


def main():
    """Main entry point with enhanced help"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        print("📋 PDF to Audio Converter - Test Runner")
        print("=" * 50)
        print("\nUsage: python run_tests.py [test_type]")
        print("\nFor TDD development workflow:")
        print("  python run_tests.py tdd       # All TDD tests")
        print("  python run_tests.py tdd-fast  # Fast feedback")
        print("  python run_tests.py commit    # Pre-commit check")
        print("\nFor component testing:")
        print("  python run_tests.py models    # Domain models")
        print("  python run_tests.py pipeline  # Text processing")
        print("\nRun without arguments to see all options.")
        sys.exit(0)
    
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    success = run_tests(test_type)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()