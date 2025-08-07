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

### Recently Completed Major Work

#### ✅ SystemConfig Architecture Refactoring (COMPLETED Aug 2025)
**STATUS: 100% COMPLETE** - Successfully migrated from monolithic to composed configuration architecture with ALL tests passing.

**What was accomplished:**
- ✅ **Unified TTS Configuration**: Created single source of truth in `domain/config/tts_config.py`
  - Consolidated TTSEngine enum, GeminiConfig (9 fields), PiperConfig (12 fields)
  - All configs now use `@dataclass(frozen=True)` for immutability
- ✅ **Clean Composition Architecture**: Replaced flat SystemConfig with composed structure
  - `SystemConfig` now uses composition: tts, files, cleanup, text_processing, performance, flask, ocr, llm
  - Removed all backward compatibility properties (clean feature branch approach)
- ✅ **Complete Migration**: Updated 24 files (15 application + 13 tests)
  - All imports migrated from old to new SystemConfig structure
  - All property access updated: `config.tts_engine` → `config.tts.engine`
  - Deleted deprecated files: system_config_refactored.py, tts_configs.py
- ✅ **Test Fixes**: Fixed ALL failing tests from refactoring
  - SystemConfig constructor pattern updates (21 tests)
  - TextPipeline Result[T] pattern compliance (34 tests)
  - End-to-end Flask integration test (5 tests) - validates real PDF processing
  - Architecture integration test updates
  - Mypy type safety fixes with proper decorator annotations

**Final Architecture:**
```
domain/config/tts_config.py          ← Single source of truth
├── TTSEngine enum
├── GeminiConfig (9 fields)
├── PiperConfig (12 fields)
└── TTSConfig (base)

application/config/system_config.py  ← Composed configuration
├── Uses domain TTS configs
├── FileConfig, ProcessingConfig, etc.
└── Clean composition pattern
```

**Validation Results**:
- ✅ All 21 SystemConfig TDD tests passing
- ✅ All 34 TextPipeline TDD tests passing
- ✅ End-to-end Flask integration test passing (25.8s real PDF processing)
- ✅ All pre-commit hooks passing (ruff, mypy, black, bandit)
- ✅ Clean git commit with proper formatting and type safety

**Result**: Clean, immutable, well-structured configuration system following all hexagonal architecture principles with ZERO backward compatibility code and complete test coverage.

### HISTORICAL REFERENCE - Property Mappings (COMPLETED)

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

This refactoring has been successfully completed. All property mappings have been applied across the entire codebase, all SystemConfig constructors updated, and all tests passing.
