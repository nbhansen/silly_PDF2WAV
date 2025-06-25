# Testing Guide - PDF to Audio Converter

## Quick Reference

### 🚀 Most Common Commands

```bash
# TDD Development (201 tests)
./test-tdd.sh                    # All TDD tests
./test-tdd.sh fast               # TDD with fast failure
./test-commit.sh                 # Pre-commit validation

# Component Testing
python run_tests.py models       # Domain models (47 tests)
python run_tests.py pipeline     # Text processing (47 tests)
python run_tests.py config       # Configuration (63 tests)
python run_tests.py errors       # Error handling (44 tests)
```

### 📋 All Available Commands

#### TDD Workflows
```bash
python run_tests.py tdd          # All TDD tests (201 tests)
python run_tests.py tdd-fast     # TDD tests with fast failure
python run_tests.py tdd-quiet    # TDD tests, minimal output
python run_tests.py tdd-coverage # TDD tests with coverage
```

#### Comprehensive Testing
```bash
python run_tests.py all          # All tests with coverage
python run_tests.py unit         # All unit tests with coverage
python run_tests.py integration  # Integration tests only
python run_tests.py coverage     # Full coverage report
```

#### Development Workflow
```bash
python run_tests.py commit       # Pre-commit validation
python run_tests.py quick        # Single fast test
python run_tests.py watch        # Watch mode (if available)
```

#### Analysis
```bash
python run_tests.py collect      # List all available tests
python run_tests.py help         # Show help and options
```

## When to Run Tests

### 🔴 Required (Must Run)

| When | Command | Purpose |
|------|---------|---------|
| **Before every commit** | `./test-commit.sh` | Ensures no regressions |
| **After domain logic changes** | `./test-tdd.sh` | Validates business rules |
| **Before merging PRs** | `python run_tests.py all` | Complete validation |
| **After dependency updates** | `python run_tests.py all` | Catches breaking changes |

### 🟡 Recommended

| When | Command | Purpose |
|------|---------|---------|
| **During TDD development** | `./test-tdd.sh fast` | Quick feedback loop |
| **Component-specific work** | `python run_tests.py models` | Focused testing |
| **After refactoring** | `python run_tests.py unit` | Behavior preservation |
| **Weekly CI runs** | `python run_tests.py coverage` | Quality monitoring |

## TDD Test Coverage (187 Tests)

### 🏗️ Domain Models (47 tests)
- **File**: `tests/unit/test_domain_models_tdd.py`
- **Focus**: Data integrity, immutability, validation
- **Key Features**: ProcessingResult defensive copying, FileInfo size calculations

### 🔄 Text Processing Pipeline (47 tests)
- **File**: `tests/unit/test_text_pipeline_tdd.py`  
- **Focus**: Pure text processing logic
- **Key Features**: SSML enhancement, sentence splitting, abbreviation handling

### ⚙️ System Configuration (49 tests)
- **File**: `tests/unit/test_system_config_tdd.py`
- **Focus**: Environment parsing and validation
- **Key Features**: Case-insensitive parsing, type validation, error messages

### 🚨 Error Handling System (44 tests)
- **File**: `tests/unit/test_error_handling_tdd.py`
- **Focus**: Structured error management
- **Key Features**: Result[T] patterns, error classification, retryability logic

## Performance Tips

### ⚡ Fast Development Workflow
```bash
# During active development
./test-tdd.sh fast               # Stop on first failure
python run_tests.py models       # Test specific component
python run_tests.py tdd-quiet    # Minimal output
```

### 🔍 Comprehensive Validation
```bash
# Before important commits
./test-commit.sh                 # Full pre-commit check
python run_tests.py all          # Everything with coverage
python run_tests.py coverage     # Detailed coverage report
```

### 🎯 Component-Specific Testing
```bash
# Working on specific areas
python run_tests.py models       # Domain models only
python run_tests.py pipeline     # Text processing only
python run_tests.py config       # Configuration only
python run_tests.py errors       # Error handling only
```

## Test Output Examples

### ✅ Successful TDD Run
```
📋 Running all 187 TDD tests
🚀 Running: python -m pytest tests/unit/ -k tdd -v
--------------------------------------------------
187 passed, 27 deselected in 0.29s
--------------------------------------------------
✅ Tests passed!
```

### ❌ Failed Test with Fast Failure
```
📋 Running TDD tests with fast failure on first error
🚀 Running: python -m pytest tests/unit/ -k tdd -v -x --ff
--------------------------------------------------
FAILED tests/unit/test_domain_models_tdd.py::TestProcessingResult::test_example
--------------------------------------------------
❌ Tests failed!
```

## Integration with Development Workflow

### 🔄 TDD Red-Green-Refactor Cycle
1. **Write failing test** → `./test-tdd.sh fast`
2. **Make test pass** → `./test-tdd.sh fast` 
3. **Refactor code** → `./test-tdd.sh`
4. **Commit changes** → `./test-commit.sh`

### 🔧 Component Development
1. **Choose component** → `python run_tests.py models|pipeline|config|errors`
2. **Develop feature** → Repeat component tests
3. **Integration test** → `python run_tests.py unit`
4. **Final validation** → `./test-commit.sh`

## Troubleshooting

### Virtual Environment Warning
```
⚠️  Warning: Not in virtual environment. Run 'source venv/bin/activate' first.
```
**Solution**: `source venv/bin/activate` before running tests

### Test Discovery Issues
**Check**: `python run_tests.py collect` to see all available tests

### Performance Issues
**Use**: `python run_tests.py tdd-quiet` for faster output during development

---

💡 **Pro Tip**: Bookmark this guide and use `./test-tdd.sh fast` for daily development!