#!/usr/bin/env python3
"""
Simple test runner for PDF to Audio Converter.
Just runs tests without complexity.
"""

import subprocess
import sys


def run_tests(test_type="all"):
    """Run tests with simple options"""
    
    commands = {
        "all": ["python", "-m", "pytest", "tests/", "-v"],
        "integration": ["python", "-m", "pytest", "tests/test_integration_fresh.py", "-v"],
        "unit": ["python", "-m", "pytest", "tests/", "-v", "-m", "unit"],
        "quick": ["python", "-m", "pytest", "tests/test_integration_fresh.py::test_can_create_processing_request", "-v"],
        "collect": ["python", "-m", "pytest", "tests/", "--collect-only"]
    }
    
    if test_type not in commands:
        print(f"Unknown test type: {test_type}")
        print(f"Available: {list(commands.keys())}")
        return False
    
    cmd = commands[test_type]
    print(f"Running: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\nTests interrupted")
        return False


if __name__ == "__main__":
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    success = run_tests(test_type)
    sys.exit(0 if success else 1)