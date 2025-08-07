# Development Partnership - Python Immutable Design

We're building production-quality code together. Your role is to create maintainable, efficient solutions while catching potential issues early.

When you seem stuck or overly complex, I'll redirect you - my guidance helps you stay on track.

🚨 **AUTOMATED CHECKS ARE MANDATORY**
ALL hook issues are BLOCKING - EVERYTHING must be ✅ GREEN!
No errors. No formatting issues. No linting problems. Zero tolerance.
These are not suggestions. Fix ALL issues before continuing.

## CRITICAL WORKFLOW - ALWAYS FOLLOW THIS!
Research → Plan → Implement
NEVER JUMP STRAIGHT TO CODING! Always follow this sequence:

- **Research**: Explore the codebase, understand existing patterns
- **Plan**: Create a detailed implementation plan and verify it with me
- **Implement**: Execute the plan with validation checkpoints

When asked to implement any feature, you'll first say: "Let me research the codebase and create a plan before implementing."

For complex architectural decisions or challenging problems, use "ultrathink" to engage maximum reasoning capacity.

## USE MULTIPLE AGENTS!
Leverage subagents aggressively for better results:
- Spawn agents to explore different parts of the codebase in parallel
- Use one agent to write tests while another implements features
- Delegate research tasks
- For complex refactors: One agent identifies changes, another implements them

## Reality Checkpoints
Stop and validate at these moments:
- After implementing a complete feature
- Before starting a new major component
- When something feels wrong
- Before declaring "done"

🚨 **CRITICAL: Hook Failures Are BLOCKING**
When hooks report ANY issues, you MUST:
1. **STOP IMMEDIATELY** - Do not continue with other tasks
2. **FIX ALL ISSUES** - Address every ❌ issue until everything is ✅ GREEN
3. **VERIFY THE FIX** - Re-run the failed command to confirm it's fixed
4. **CONTINUE ORIGINAL TASK** - Return to what you were doing before the interrupt

## Python Immutable Design Rules

### FORBIDDEN - NEVER DO THESE:
- NO mutating existing objects - always return new instances
- NO in-place list/dict modifications (`.append()`, `.update()`, etc.)
- NO global mutable state
- NO keeping old and new code together
- NO migration functions or compatibility layers
- NO TODOs in final code

### Required Standards:
- Use `dataclasses(frozen=True)` or `NamedTuple` for data structures
- Return new instances: `return dataclasses.replace(obj, field=new_value)`
- Use immutable collections: `tuple()`, `frozenset()`, `types.MappingProxyType()`
- Functional transformations: `map()`, `filter()`, list comprehensions
- Delete old code when replacing it
- Type hints on all functions and methods
- Meaningful names: `user_id` not `id`

## Implementation Standards
Our code is complete when:
- All linters pass (black, flake8, mypy)
- All tests pass
- Feature works end-to-end
- Old code is deleted
- Docstrings on all public functions/classes

## Testing Strategy
- Complex business logic → Write tests first
- Simple transformations → Write tests after
- Hot paths → Add benchmarks with pytest-benchmark
- Skip tests for simple CLI parsing

## Project Structure
```
pdf_to_audio_app/
├── application/           # Application orchestration layer
│   └── config/           # SystemConfig - single source of truth
├── domain/               # Core business logic (no external dependencies)
│   ├── audio/           # Audio processing engines
│   ├── config/          # TTS and domain configuration models
│   ├── container/       # Service container for dependency injection
│   ├── document/        # Document processing engine
│   ├── factories/       # Modular service factories
│   ├── text/            # Text processing pipeline and chunking
│   ├── interfaces.py    # Abstract interfaces for dependencies
│   ├── models.py        # Domain models with validation
│   └── errors.py        # Structured error handling
├── infrastructure/      # External service implementations
│   ├── tts/             # TTS providers (Gemini, Piper)
│   ├── llm/             # Gemini LLM provider
│   ├── ocr/             # Tesseract OCR provider
│   └── file/            # File management and cleanup
├── templates/           # Flask web interface templates
├── tests/               # Test files (204 tests total)
└── static/              # Web assets
```

## Hexagonal Architecture Enforcement

**CRITICAL: Follow MEMORY.md architectural patterns strictly!**

### 🚨 ARCHITECTURE VIOLATIONS TO AVOID:

1. **NO GLOBAL STATE** - EVER!
   - ❌ NEVER create global variables like `_global_config`
   - ❌ NEVER use singleton patterns for configuration
   - ✅ ALWAYS pass dependencies explicitly through constructors
   - ✅ ALWAYS use dependency injection for all services

2. **NO HARDCODED DEPENDENCIES**
   - ❌ NEVER hardcode provider selection in CLI commands
   - ❌ NEVER directly access environment variables in domain/business logic
   - ✅ ALWAYS use dependency injection container
   - ✅ ALWAYS abstract external dependencies behind interfaces

3. **NO MUTABLE DEFAULT FACTORIES**
   - ❌ NEVER use `field(default_factory=dict)` in dataclasses
   - ❌ NEVER use `field(default_factory=list)` in dataclasses
   - ✅ ALWAYS use immutable defaults: `field(default_factory=lambda: types.MappingProxyType({}))`
   - ✅ ALWAYS validate immutability in tests

4. **NO BUSINESS LOGIC IN INFRASTRUCTURE**
   - ❌ NEVER put business logic in provider classes
   - ❌ NEVER mix domain logic with API calls
   - ✅ ALWAYS separate domain logic from infrastructure concerns
   - ✅ ALWAYS use ports/adapters pattern

5. **NO DIRECT ENVIRONMENT ACCESS**
   - ❌ NEVER call `os.environ` directly in business logic
   - ❌ NEVER hardcode environment variable names
   - ✅ ALWAYS use configuration objects passed via DI
   - ✅ ALWAYS centralize environment access in configuration layer

### Architecture Checklist Before Implementation:
- [ ] Does this create any global state? (If yes, redesign)
- [ ] Does this access environment variables directly? (If yes, use config)
- [ ] Does this hardcode any dependencies? (If yes, use DI)
- [ ] Does this mix domain logic with infrastructure? (If yes, separate)
- [ ] Are all dataclass fields truly immutable? (If no, fix defaults)
- [ ] Can this be tested without external dependencies? (If no, add abstractions)

### Required Architecture Pattern:
```python
# ✅ CORRECT - Dependency Injection
class PDFProcessor:
    def __init__(self, llm_provider: LLMProvider, config: Config):
        self._llm_provider = llm_provider
        self._config = config

# ❌ WRONG - Global State
_global_config = {}
class PDFProcessor:
    def process(self):
        config = _global_config  # NEVER DO THIS!
```

### Configuration Pattern:
```python
# ✅ CORRECT - Immutable Configuration
@dataclass(frozen=True)
class Config:
    api_key: str
    timeout: float
    max_retries: int = 3

# ❌ WRONG - Mutable Defaults
@dataclass
class Config:
    settings: Dict = field(default_factory=dict)  # NEVER DO THIS!
```

**BEFORE WRITING ANY CODE:**
1. Check if it follows hexagonal architecture
2. Verify no global state is created
3. Ensure all dependencies are injected
4. Confirm domain logic is separated from infrastructure
5. Validate all objects are immutable

## Problem-Solving Together
When you're stuck:
1. **Stop** - Don't spiral into complex solutions
2. **Delegate** - Consider spawning agents
3. **Ultrathink** - For complex problems
4. **Step back** - Re-read requirements
5. **Simplify** - The simple solution is usually correct
6. **Ask** - Present clear alternatives

## Performance & Security
- Measure first - no premature optimization
- Validate all inputs
- Use `secrets` module for randomness
- Parameterized queries for SQL

## Communication Protocol
Progress Updates:
- ✓ Implemented authentication (all tests passing)
- ✗ Found issue with token validation - investigating

## Working Together
This is always a feature branch - no backwards compatibility needed.
When in doubt, we choose clarity over cleverness.

**REMINDER: If this file hasn't been referenced in 30+ minutes, RE-READ IT!**

## Development Best Practices

🚨 **CRITICAL: VIRTUAL ENVIRONMENT MANDATORY - BLOCKING**
- EVERY SINGLE COMMAND must start with: `source venv/bin/activate &&`
- NO EXCEPTIONS - Never run python/pip/pytest/mypy/black without venv
- If you see "ModuleNotFoundError", you forgot the venv!
- ALL bash commands must use this pattern: `source venv/bin/activate && [actual command]`
- This is MANDATORY and BLOCKING - failure to do this breaks everything

## Maintainability Improvement Plan

### Current State Assessment
The codebase demonstrates excellent architectural discipline with clean hexagonal architecture and consistent immutability patterns. However, specific maintainability issues need immediate attention.

### 🚨 CRITICAL ISSUES - MUST FIX IMMEDIATELY

#### 1. Type Safety Failures (BLOCKING)
**Location:** `application/config/system_config.py:135-138`
**Issue:** Multiple mypy errors in YAML parsing preventing type checking
**Fix Required:**
```python
# Current (BROKEN):
def from_yaml(cls, config_path: Path) -> "SystemConfig":
    parsed = cls._parse_yaml(config_path)
    return cls(**parsed)  # Type error: dict incompatible with constructor

# Fix:
def from_yaml(cls, config_path: Path) -> "SystemConfig":
    parsed = cls._parse_yaml(config_path)
    # Explicit field mapping with type validation
    return cls(
        output_dir=Path(parsed["output_dir"]),
        temp_dir=Path(parsed["temp_dir"]),
        # ... explicit field assignments
    )
```

#### 2. Code Duplication in Routes (HIGH PRIORITY)
**Location:** `routes.py` - `upload_file()` and `upload_file_with_timing()`
**Issue:** Nearly identical 100+ line functions
**Fix Required:**
```python
# Extract common logic:
def _process_upload_common(file: FileStorage, form_data: dict, enable_timing: bool) -> tuple[Response, int]:
    """Unified upload processing logic"""
    # All shared processing code here
    pass

@app.route("/upload", methods=["POST"])
def upload_file() -> tuple[Response, int]:
    return _process_upload_common(request.files["pdf_file"], request.form, False)

@app.route("/upload-with-timing", methods=["POST"])
def upload_file_with_timing() -> tuple[Response, int]:
    return _process_upload_common(request.files["pdf_file"], request.form, True)
```

### 📋 HIGH PRIORITY IMPROVEMENTS

#### 3. Configuration Complexity
**Location:** `application/config/system_config.py`
**Issue:** 40+ fields in single class violating SRP
**Fix Required:**
- Break into specialized configs: `TTSConfig`, `LLMConfig`, `OCRConfig`, `FileConfig`
- Use composition pattern in SystemConfig
- Separate YAML parsing into dedicated parser class

#### 4. Error Handling Inconsistency
**Issue:** Mixed patterns - some use `Result[T]`, others raise exceptions
**Standard to Adopt:**
```python
# Domain layer: Always use Result[T]
def process_document(doc: Document) -> Result[ProcessedDocument]:
    pass

# Infrastructure layer: Catch exceptions, return Result[T]
def call_external_api() -> Result[APIResponse]:
    try:
        response = external_api.call()
        return Success(response)
    except Exception as e:
        return Failure(InfrastructureError(str(e)))
```

### 📊 MEDIUM PRIORITY IMPROVEMENTS

#### 5. Missing Type Hints
**Locations:** `utils.py`, route handlers
**Fix Required:**
- Add complete type hints to all functions
- Use TypeVar for generic functions
- Add return type annotations to all route handlers

#### 6. Service Container Immutability
**Location:** `domain/container/service_container.py`
**Issue:** Mutable `_singletons` dict
**Fix Required:**
```python
@dataclass(frozen=True)
class ServiceContainer:
    _factories: types.MappingProxyType[ServiceKey, ServiceFactory]
    _singletons: types.MappingProxyType[ServiceKey, object] = field(
        default_factory=lambda: types.MappingProxyType({})
    )

    def with_singleton(self, key: ServiceKey, instance: object) -> "ServiceContainer":
        """Return new container with added singleton"""
        new_singletons = dict(self._singletons)
        new_singletons[key] = instance
        return dataclasses.replace(
            self,
            _singletons=types.MappingProxyType(new_singletons)
        )
```

#### 7. Extract Rate Limiting
**Current:** Embedded in individual providers
**Fix Required:**
- Create `RateLimiter` abstraction in domain layer
- Inject into providers via dependency injection
- Centralize retry logic with exponential backoff

### ✅ IMPROVEMENT TRACKING CHECKLIST

#### Completed (2025-01-07):
- [x] Fix SystemConfig.from_yaml() type errors - DONE: Explicit field assignment with type casting
- [x] Consolidate duplicate upload route handlers - DONE: Extracted _validate_upload_request()
- [x] Fix remaining 44 mypy errors in parsing helper methods - DONE: Added ConfigAccessor type
- [x] Add missing type hints to utils.py functions - DONE: Added FormData type alias
- [x] Fix get_config callable type issues - DONE: Properly typed as ConfigAccessor
- [x] Remove redundant type casts in SystemConfig - DONE: Cleaned up unnecessary casts

#### High Priority - Type Safety & Code Quality:
- [x] Fix remaining mypy errors in domain/audio modules - DONE: Added proper async type hints
- [ ] Add complete type coverage to all modules (54 errors remaining in tests and infrastructure)

#### Medium Priority - Architecture Improvements:
- [x] Break down SystemConfig into specialized configs - DONE: Created 10 specialized configs with composition
- [ ] Standardize error handling to Result[T] pattern - IN PROGRESS: Domain models converted
- [ ] Extract rate limiting to shared abstraction layer
- [ ] Implement complete service container immutability

#### Low Priority - Testing & Documentation:
- [ ] Add property-based testing for domain models
- [ ] Create architecture decision records (ADRs)
- [ ] Fix failing file_manager tests (6 path-related failures)
- [ ] Add integration tests for refactored upload endpoints

### 🎯 SUCCESS METRICS

**Code Quality Gates (MUST PASS):**
- mypy: 0 errors
- black: formatted
- flake8: 0 violations
- pytest: 204/204 tests passing
- coverage: >85%

**Architecture Health Checks:**
- No global state usage
- All dataclasses frozen
- No mutable default factories
- Clear layer separation maintained
- All dependencies injected

### 📈 EXPECTED OUTCOMES

After implementing these improvements:
1. **Type Safety**: Full mypy compliance enabling early error detection
2. **Maintainability**: Reduced code duplication from ~500 to <100 lines
3. **Clarity**: Single responsibility for all classes
4. **Consistency**: Unified error handling patterns
5. **Testability**: Easier to test with proper abstractions

### 🚦 VALIDATION STEPS

Before considering any improvement complete:
1. Run full test suite: `source venv/bin/activate && pytest`
2. Check type safety: `source venv/bin/activate && mypy .`
3. Verify formatting: `source venv/bin/activate && black --check .`
4. Lint check: `source venv/bin/activate && flake8`
5. Security scan: `source venv/bin/activate && bandit -r .`

**Remember:** Every change must maintain or improve the current architecture. No shortcuts, no global state, no mutable defaults.
