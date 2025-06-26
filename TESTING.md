# Testing Guide - PDF to Audio Converter

## Quick Reference

### 🚀 Most Common Commands

```bash
# Full Test Suite (205 tests - All passing ✅)
./test-tdd.sh                    # TDD tests (160 tests) with architectural validation
./test-tdd.sh fast               # Fast failure for development
./test-commit.sh                 # Pre-commit validation
python run_tests.py all          # All tests (205 tests) with coverage

# Component Testing
python run_tests.py models       # Domain models (57 tests)
python run_tests.py pipeline     # Text processing (47 tests)
python run_tests.py config       # Configuration (35 tests)
python run_tests.py errors       # Error handling (44 tests)
python run_tests.py architecture # New architecture tests (16 tests)
```

### 📋 All Available Commands

#### TDD Workflows
```bash
python run_tests.py tdd          # All TDD tests (160 tests)
python run_tests.py tdd-fast     # TDD tests with fast failure
python run_tests.py tdd-quiet    # TDD tests, minimal output
python run_tests.py tdd-coverage # TDD tests with coverage
```

#### Comprehensive Testing
```bash
python run_tests.py all          # All tests (205 tests) with coverage
python run_tests.py unit         # All unit tests (201 tests) with coverage
python run_tests.py integration  # Integration tests (4 tests)
python run_tests.py coverage     # Full coverage report
```

#### Development Workflow
```bash
python run_tests.py commit       # Pre-commit validation
python run_tests.py quick        # Single fast test
python run_tests.py factories    # Test new modular factories
python run_tests.py chunking     # Test new chunking strategies
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
| **After factory refactoring** | `python run_tests.py factories` | Tests modular factories |
| **Before merging PRs** | `python run_tests.py all` | Complete validation |
| **After dependency updates** | `python run_tests.py all` | Catches breaking changes |

### 🟡 Recommended

| When | Command | Purpose |
|------|---------|---------|
| **During TDD development** | `./test-tdd.sh fast` | Quick feedback loop |
| **Component-specific work** | `python run_tests.py models` | Focused testing |
| **After architectural changes** | `python run_tests.py architecture` | Validates clean architecture |
| **Weekly CI runs** | `python run_tests.py coverage` | Quality monitoring |

## Comprehensive Test Coverage (205 Tests - All Passing ✅)

### 🏗️ Domain Models (57 tests)
- **File**: `tests/unit/test_domain_models_tdd.py`
- **Focus**: Data integrity, validation, business logic
- **New Features**: Robust validation with `__post_init__`, comprehensive edge cases
- **Key Tests**: PageRange validation, ProcessingRequest validation, TextSegment types

### 🔄 Text Processing Pipeline (47 tests)
- **File**: `tests/unit/test_text_pipeline_tdd.py`  
- **Focus**: Pure text processing logic, SSML enhancement
- **Key Features**: Chunking integration, academic content processing, error resilience

### ⚙️ System Configuration (35 tests)
- **Files**: `tests/unit/test_system_config_tdd.py`, `tests/unit/test_system_config_yaml.py`
- **Focus**: YAML configuration, validation, model separation
- **New Features**: Separate LLM and TTS model configuration, enhanced validation

### 🚨 Error Handling System (44 tests)
- **File**: `tests/unit/test_error_handling_tdd.py`
- **Focus**: Structured error management, Result patterns
- **Key Features**: Retryability logic, error classification, recovery patterns

### 🏛️ Architecture Tests (16 tests)
- **File**: `tests/unit/test_new_architecture.py`
- **Focus**: Service integration, factory pattern validation
- **New Features**: AudioEngine integration, TimingEngine coordination, service container

### 🔗 Integration Tests (4 tests)
- **File**: `tests/integration/test_integration_simple.py`
- **Focus**: End-to-end workflow validation
- **Coverage**: Service factory creation, configuration loading, basic workflow structure

### 📊 Legacy Unit Tests (10 tests)
- **File**: `tests/unit/test_domain_models.py`
- **Focus**: Basic model creation validation
- **Status**: Maintained for backward compatibility

## 🔧 New Architecture Testing

### Modular Factories Testing
```bash
python run_tests.py factories    # Test service factory modularization
python run_tests.py audio        # Audio factory and services
python run_tests.py text         # Text factory and chunking
python run_tests.py tts          # TTS factory and engines
```

### Chunking Strategy Testing
```bash
python run_tests.py chunking     # Test pluggable chunking strategies
python run_tests.py strategies   # All strategy pattern implementations
```

### Integration Testing
```bash
python run_tests.py integration  # Service factory integration
python run_tests.py container    # Dependency injection container
python run_tests.py end-to-end   # Complete workflow testing
```

## Performance Tips

### ⚡ Fast Development Workflow
```bash
# During active development
./test-tdd.sh fast               # Stop on first failure (205 tests)
python run_tests.py models       # Test specific component
python run_tests.py tts-quiet    # Minimal output for factories
```

### 🔍 Comprehensive Validation
```bash
# Before important commits
./test-commit.sh                 # Full pre-commit check (205 tests)
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
python run_tests.py factories    # New modular factories
python run_tests.py chunking     # Text chunking strategies
```

## Test Output Examples

### ✅ Successful Full Test Run (New Architecture)
```
📋 Running all 205 tests (Clean Architecture)
🚀 Running: python -m pytest tests/ -v
--------------------------------------------------
205 passed in 1.67s
--------------------------------------------------
✅ All tests passed! Clean architecture validated.
Coverage: 51% total with focus on domain logic.
```

### ✅ Factory Integration Test
```
📋 Testing modular service factories
🚀 Running: python -m pytest tests/unit/test_new_architecture.py -v
--------------------------------------------------
TestServiceContainer::test_service_container_creation PASSED
TestArchitectureIntegration::test_audio_and_timing_engine_integration PASSED
--------------------------------------------------
✅ Service factory integration working!
```

### ❌ Failed Test with Fast Failure (Development)
```
📋 Running tests with fast failure on first error
🚀 Running: python -m pytest tests/ -v -x --ff
--------------------------------------------------
FAILED tests/unit/test_domain_models_tdd.py::TestProcessingRequest::test_validation
--------------------------------------------------
❌ Test failed! Fix validation before continuing.
```

## Integration with Development Workflow

### 🔄 TDD Red-Green-Refactor Cycle (Updated)
1. **Write failing test** → `./test-tdd.sh fast`
2. **Make test pass** → `./test-tdd.sh fast` 
3. **Refactor with clean architecture** → `./test-tdd.sh`
4. **Validate factory integration** → `python run_tests.py factories`
5. **Commit changes** → `./test-commit.sh`

### 🏗️ Architecture Development
1. **Choose component** → `python run_tests.py models|factories|chunking`
2. **Test factory pattern** → `python run_tests.py factories`
3. **Validate dependencies** → `python run_tests.py integration`
4. **Final validation** → `./test-commit.sh`

### 🔧 New Patterns Testing
1. **Strategy pattern** → `python run_tests.py chunking`
2. **Dependency injection** → `python run_tests.py container`
3. **Service integration** → `python run_tests.py architecture`
4. **End-to-end flow** → `python run_tests.py integration`

## Troubleshooting

### Virtual Environment Warning
```
⚠️  Warning: Not in virtual environment. Run 'source venv/bin/activate' first.
```
**Solution**: `source venv/bin/activate` before running tests

### Test Discovery Issues
**Check**: `python run_tests.py collect` to see all 205 available tests

### Factory Resolution Issues
**Debug**: `python run_tests.py factories` to validate service creation

### Performance Issues
**Use**: `python run_tests.py tdd-quiet` for faster output during development

---

💡 **Pro Tip**: Our refactored architecture has 205 tests (all passing)! 
- Use `./test-tdd.sh fast` for daily development (160 TDD tests)
- Use `python run_tests.py all` for complete validation (205 tests)
- Use `python run_tests.py factories` when working on service creation
- Current coverage: 51% with strong focus on domain logic and validation