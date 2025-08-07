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

## Architectural Memory

### Current Major Work In Progress

#### ❌ SystemConfig Architecture Refactoring (INCOMPLETE - CRITICAL)
**STATUS: PARTIALLY COMPLETE** - Migration from monolithic to composed configuration architecture is UNFINISHED.

**BLOCKING ISSUE**: Integration tests and other features cannot be properly committed because the SystemConfig refactoring is incomplete, causing mypy failures across the entire codebase.

**What is done:**
- ✅ `domain/config/tts_config.py` - Unified TTS configuration classes created
- ✅ `application/config/system_config.py` - New composition pattern structure created
- ✅ Some files updated to new property access patterns

**What is MISSING (CRITICAL):**

### PHASE 1: Fix All Property Access Patterns
**Files that MUST be updated to use new composition pattern:**

**REQUIRED PROPERTY MAPPING:**
```
OLD PATTERN                    → NEW PATTERN
config.enable_text_cleaning    → config.text_processing.enable_cleaning
config.max_file_size_mb        → config.files.max_file_size_mb
config.upload_folder           → config.files.upload_folder
config.audio_folder            → config.files.audio_folder
config.gemini_api_key          → config.gemini.api_key (if config.gemini)
config.tts_engine              → config.tts.engine
config.enable_async_audio      → config.performance.enable_async_audio
config.audio_concurrent_chunks → config.performance.audio_concurrent_chunks
config.tts_concurrent_requests → config.tts.concurrent_requests
config.tts_request_delay_seconds → config.tts.request_delay_seconds
config.enable_natural_formatting → config.text_processing.enable_natural_formatting
config.gemini_model_name       → config.gemini.model_name (if config.gemini)
config.gemini_voice_name       → config.gemini.voice_name (if config.gemini)
config.audio_target_chunk_size → config.text_processing.audio_target_chunk_size
config.audio_max_chunk_size    → config.text_processing.audio_max_chunk_size
config.gemini_use_measurement_mode → config.gemini.use_measurement_mode (if config.gemini)
config.gemini_measurement_mode_interval → config.gemini.measurement_mode_interval (if config.gemini)
config.piper_model_repository_url → config.piper.model_repository_url (if config.piper)
```

**FILES REQUIRING UPDATES:**
- `utils.py` - Some property access patterns
- `domain/container/service_container.py` - Multiple property access patterns
- `domain/factories/*.py` - Factory files with old property access
- `tests/unit/*.py` - Test files with old SystemConfig usage
- `tests/benchmarks/*.py` - Benchmark files with old patterns
- `tests/integration/*.py` - Integration tests with old patterns
- `routes.py` - Route handlers with old property access
- Any other files with `config.{old_property}` patterns

### PHASE 2: Update All SystemConfig Constructors
**Every SystemConfig constructor call must use composition pattern:**
```python
# OLD (WRONG):
SystemConfig(tts_engine=TTSEngine.PIPER, upload_folder="/path", ...)

# NEW (CORRECT):
SystemConfig(
    tts=TTSConfig(engine=TTSEngine.PIPER, ...),
    files=FileConfig(upload_folder="/path", ...),
    cleanup=FileCleanupConfig(...),
    text_processing=TextProcessingConfig(...),
    performance=PerformanceConfig(...),
    flask=FlaskConfig(...),
    ocr=OCRConfig(...),
    llm=LLMConfig(...),
    gemini=GeminiConfig(...) if needed,
    piper=PiperConfig(...) if needed,
)
```

### PHASE 3: Clean Up File References
- Remove any imports or references to deleted `system_config_refactored.py`
- Remove any imports or references to deleted `tts_configs.py`

### PHASE 4: Complete Validation
- Run `mypy .` - MUST pass with zero errors on SystemConfig
- Run all tests - MUST pass completely
- Ensure integration tests can be committed without SKIP flags

**CRITICAL**: This refactoring affects ~15-20 files and must be completed systematically. NO SHORTCUTS. Every single SystemConfig property access must be updated to use the composition pattern.

**PRIORITY**: This is BLOCKING work that must be completed before any other features can be properly committed.
