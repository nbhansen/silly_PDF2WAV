# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overriding objective
NEVER EVER FOR THE LOVE OF GOD FUCKING INSERT HARDCODES ANYWHERE, NOT EVEN AS FALLBACKS, IT GETS THE INFO FROM THE YAML CONFIG FILE ONLY.

**CRUD REMOVAL COMPLETED**: 
- ✅ Removed unused `config/voice_personas.json` file (legacy multi-voice system)
- ✅ Moved Flask server settings (debug, host, port) to YAML configuration  
- ✅ All hardcoded values now properly configurable via YAML
- ✅ YAML config file is the ONLY place with hardcoded values

## Project Overview

A Flask web application that converts PDF documents to audio files using multiple TTS engines (Text-to-Speech). The application extracts text from PDFs, cleans it using LLM services, applies academic SSML enhancements, and generates synchronized audio with optional read-along functionality.

## Architecture

The project follows Clean Architecture principles with clear separation of concerns:

```
pdf_to_audio_app/
├── application/           # Application orchestration layer
│   ├── config/           # SystemConfig - single source of truth for configuration
│   └── services/         # PDF processing coordination service
├── domain/               # Core business logic (no external dependencies)
│   ├── audio/           # Audio processing engines (generation & timing)
│   ├── config/          # TTS and domain configuration models
│   ├── container/       # Service container for dependency injection
│   ├── document/        # Document processing engine
│   ├── factories/       # Modular service factories (audio, text, TTS)
│   ├── text/            # Text processing pipeline and chunking strategies
│   ├── interfaces.py    # Abstract interfaces for all external dependencies
│   ├── models.py        # Domain models with robust validation
│   └── errors.py        # Structured error handling system
├── infrastructure/       # External service implementations
│   ├── tts/             # TTS providers with shared utilities
│   │   ├── text_segmenter.py      # Shared text processing (152 lines)
│   │   ├── gemini_tts_provider.py # Gemini TTS implementation (352 lines)
│   │   └── piper_tts_provider.py  # Piper TTS implementation
│   ├── llm/             # Gemini LLM provider for text cleaning
│   ├── ocr/             # Tesseract OCR provider
│   └── file/            # File management and cleanup scheduling
└── templates/           # Flask web interface templates
```

## Key Development Commands

### Running the Application
```bash
python app.py                    # Start Flask development server
```

### Testing Strategy

The project uses a **hybrid testing approach** combining comprehensive TDD coverage for domain logic with integration testing for infrastructure components.

#### Quick Commands (Most Common)
```bash
# TDD Development Workflow
./test-tdd.sh                    # All 160 TDD tests
./test-tdd.sh fast               # TDD tests with fast failure
./test-commit.sh                 # Pre-commit validation

# Enhanced Test Runner
python run_tests.py tdd          # All TDD tests (160 tests)
python run_tests.py commit       # Pre-commit validation
python run_tests.py models       # Domain models (57 tests)
python run_tests.py pipeline     # Text processing (47 tests)
python run_tests.py config       # Configuration (35 tests)
python run_tests.py errors       # Error handling (44 tests)
python run_tests.py architecture # New architecture validation tests (16 tests)
```

#### Comprehensive Testing
```bash
python run_tests.py all          # All tests with coverage
python run_tests.py unit         # Unit tests with coverage
python run_tests.py integration  # Integration tests only
python run_tests.py coverage     # Full coverage report
```

#### When to Run Tests

**Required (Must Run):**
- **Before every commit**: `./test-commit.sh`
- **After domain logic changes**: `./test-tdd.sh`
- **Before merging PRs**: `python run_tests.py all`

**During Development:**
- **TDD cycle**: `./test-tdd.sh fast` (quick feedback)
- **Component work**: `python run_tests.py models|pipeline|config|errors`
- **Integration testing**: `python run_tests.py integration`

#### TDD Test Coverage (160 Tests)
- **Domain Models**: 57 tests - Data integrity, validation, and immutability
- **Text Processing Pipeline**: 47 tests - Pure text processing logic with chunking strategies
- **System Configuration**: 35 tests - YAML parsing and validation
- **Error Handling System**: 44 tests - Structured error management
- **Architecture Validation**: 16 tests - Modular factories and service integration

#### Total Test Coverage (205 Tests)
- **Unit Tests**: 201 tests - All TDD tests plus legacy unit tests
- **Integration Tests**: 4 tests - End-to-end workflow validation
- **Coverage**: 51% total coverage with focus on domain logic

### Environment Setup
```bash
python3 -m venv venv
source venv/bin/activate         # Linux/Mac
venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

**IMPORTANT**: Always activate the virtual environment before running any Python commands or tools. Many commands will fail if the venv is not activated.

## Configuration System

All configuration is managed through `application/config/system_config.py` using YAML configuration files ONLY

### Configuration Methods

1. **YAML Configuration (Preferred)**
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml with your settings
   python app.py  # Automatically loads from config.yaml
   ```


### Core Settings
- `tts.engine`: `piper` (local) or `gemini` (cloud)
- `secrets.google_ai_api_key`: Required for Gemini TTS/LLM features
- `tts.gemini.voice_name`: Single voice for all TTS generation (Kore, Charon, Aoede, Leda)
- `text_processing.document_type`: Content-aware styling (`research_paper`, `literature_review`, `general`)
- `text_processing.enable_text_cleaning`: Use LLM for text enhancement (default: true)
- `text_processing.enable_ssml`: Apply SSML markup for better speech (default: true)

### Voice System Logic Separation
- **Content Processing**: `document_type` determines how content is styled and emphasized
- **Voice Selection**: `voice_name` determines which voice speaks (Gemini only)
- **Engine Independence**: Piper uses model-based voices, Gemini uses API voices

### File Management
- `files.cleanup.enabled`: Automatic file cleanup (default: true)
- `files.cleanup.max_file_age_hours`: File retention period (default: 24)
- `files.cleanup.max_disk_usage_mb`: Disk usage limit (default: 500)

### Configuration Loading
- `SystemConfig.from_yaml()`: Loads from YAML file with type validation and validation
- Configuration fails fast with clear error messages if invalid or missing

See `config.example.yaml` for a complete configuration template with all available options.

## Dependency Injection

The modular factory system in `domain/factories/` handles all dependency injection:

### Modular Factory Architecture
- **`service_factory.py`**: Main orchestrator, creates complete PDF processing service
- **`audio_factory.py`**: Creates audio engines (AudioEngine, TimingEngine) and timing strategies
- **`text_factory.py`**: Creates text processing services including chunking strategies
- **`tts_factory.py`**: Creates TTS engines with clear separation of Gemini TTS vs Gemini LLM

### Key Features
- **Clear Separation**: TTS and LLM factories prevent confusion between Gemini services
- **Strategy Pattern**: Text chunking uses configurable strategies (sentence-based, word-based)
- **Validation**: All factories validate configuration before creating services
- **Entry Point**: `create_pdf_service_from_env()` accepts SystemConfig and returns fully configured service

## Core Processing Flow

1. **PDF Upload** → Flask routes (`/upload` or `/upload-with-timing`)
2. **Text Extraction** → Document engine with OCR provider (Tesseract) and PDF info validation
3. **Text Cleaning** → Text pipeline with LLM provider (Gemini) removes headers/footers, adds pauses
4. **Text Chunking** → Strategy-based chunking (sentence or word-based) for optimal processing
5. **SSML Enhancement** → Academic SSML service improves pronunciation
6. **Audio Generation** → Audio engine with TTS provider (Piper/Gemini) and timing strategies
7. **File Management** → Cleanup scheduler manages temporary files

## TTS Engine Support

### Piper TTS (Local)
- Fast, no API costs
- Basic SSML support
- Models stored in `piper_models/`
- Configuration: Uses `tts.piper.model_name` (e.g., en_US-lessac-high)
- Voice: Determined by selected model

### Gemini TTS (Cloud) - Simplified Architecture
- **Consistent Voice Delivery**: Single voice throughout entire document
- **Natural Speech**: Removed artificial persona switching for more natural audio
- **Shared Text Processing**: Uses `TextSegmenter` utility for universal text operations
- **Rate Limiting**: Intelligent retry logic with exponential backoff
- **Format Conversion**: Raw PCM data → WAV format conversion
- **Configuration**: 
  - `tts.gemini.voice_name`: Single voice for all content (e.g., "Kore", "Charon")
  - `tts.gemini.model_name`: Gemini TTS model
  - Rate limiting parameters configurable via YAML

### TTS Architecture - Minimal Shared Services Model

The TTS system uses a **minimal shared services** approach that balances code reuse with engine-specific needs:

#### Shared Components (`infrastructure/tts/text_segmenter.py`)
Universal text processing that works for all TTS engines:
- ✅ **Sentence splitting**: Smart boundary detection with abbreviation handling
- ✅ **Duration calculation**: Word-based timing estimation with punctuation pauses  
- ✅ **Text cleaning**: Removes problematic characters safely
- ✅ **Text chunking**: Splits long documents at natural boundaries

#### Engine-Specific Components
Each TTS engine handles its own specialized requirements:

**Gemini TTS Provider** (`gemini_tts_provider.py` - 352 lines):
- Gemini API integration and authentication
- Rate limiting and retry logic (cloud API specific)
- Raw PCM → WAV conversion (Gemini-specific format) 
- Audio chunk combination (WAV file merging)
- Async orchestration with semaphore control

**Piper TTS Provider** (maintains separate implementation):
- Direct WAV output (no conversion needed)
- Local processing (no rate limiting needed)
- Synchronous operation
- Simple model-based voice selection

#### Benefits of This Architecture
- **Shared utilities** prevent code duplication for universal text processing
- **Engine-specific logic** stays separate (SSML, rate limiting, audio formats)
- **Easy to extend** - new engines like ElevenLabs just need `TextSegmenter` + engine logic
- **Clean dependencies** - engines depend on `TextSegmenter`, not each other
- **Testable** - can mock `TextSegmenter` for all engine tests

### Adding New TTS Engines
When adding engines like ElevenLabs:

```python
class ElevenLabsTTSProvider(ITimestampedTTSEngine):
    def __init__(self, ...):
        self.text_segmenter = TextSegmenter(base_wpm=155)  # Reuse shared utilities
        # ElevenLabs-specific: API key, voice cloning, emotion controls
    
    def _generate_audio(self, text: str) -> bytes:
        # ElevenLabs-specific: Rich SSML, voice switching, emotions
        return self._call_elevenlabs_api(text)
```

## Text Processing Architecture

### Chunking Strategies
The application uses the Strategy pattern for text chunking:

- **`ChunkingService`**: Main service that delegates to strategies
- **`SentenceBasedChunking`**: Splits text by sentences (ideal for natural speech)
- **`WordBasedChunking`**: Splits text by word count (useful for length control)
- **Configurable**: Easy to add new chunking strategies

### Text Pipeline
- **Input Validation**: Robust validation of text segments and processing requests
- **Cleaning**: LLM-based text enhancement with academic focus
- **SSML Enhancement**: Pronunciation and pacing improvements
- **Chunking**: Strategy-based text segmentation for optimal processing

## Audio Processing Architecture

### Audio Engines
- **`AudioEngine`**: Main audio processing service with chunking integration
- **`TimingEngine`**: Handles audio timing with multiple strategies

### Timing Strategies
The application uses different timing strategies based on TTS engine:

- **GeminiTimestampStrategy**: Uses engine-provided timestamps (ideal)
- **SentenceMeasurementStrategy**: Measures timing manually (fallback)

Both implement `ITimingStrategy` interface and return `TimedAudioResult` objects.

### Audio Generation Flow
1. Text is chunked using configurable strategies
2. Each chunk is processed through TTS engine
3. Audio segments are combined with timing information
4. Final audio file is generated with optional timing data

## Error Handling

Structured error system in `domain/errors.py`:
- `ApplicationError` base class with error codes
- Retryable vs permanent error classification
- User-friendly error message generation
- Automatic fallbacks (OCR when direct extraction fails)

## Web Interface Features

- **Standard Upload**: Basic PDF to audio conversion
- **Read-Along Upload**: Generates timing data for synchronized text highlighting
- **Admin Endpoints**: File management statistics and manual cleanup
- **C64-themed UI**: Nostalgic design with modern functionality

## File Management

Automatic cleanup system:
- `FileManager`: Handles file operations and metadata
- `FileCleanupScheduler`: Background cleanup based on age and disk usage
- Configurable retention policies and cleanup intervals

## Development Notes

### When Adding New TTS Engines
1. Implement `ITTSEngine` interface in `infrastructure/tts/`
2. Add configuration to `SystemConfig`
3. Update `tts_factory.py` to create the new engine (NOT service_factory directly)
4. Consider implementing `ITimestampedTTSEngine` for timing support
5. **Voice Configuration**: Decide if engine uses single voice or model-based voices
6. **Factory Separation**: Ensure TTS engines are separate from LLM services

### Voice System Architecture
- **Simplified Design**: Single voice per session, content-aware styling
- **No Voice Personas**: Removed complex multi-voice JSON configuration
- **Domain Separation**: Content processing vs voice selection are independent
- **Engine Flexibility**: Each TTS engine handles voice configuration differently
- **Clear Boundaries**: TTS and LLM services are never confused in factory creation

### When Adding New Text Processing
1. Define interface in `domain/interfaces.py`
2. Implement service in `domain/text/` for text processing
3. Add infrastructure provider in `infrastructure/`
4. Wire in appropriate factory (`text_factory.py` for text services)
5. **Chunking Strategies**: Consider if new chunking strategy is needed

### When Adding New Chunking Strategies
1. Implement `ChunkingStrategy` interface in `domain/text/chunking_strategy.py`
2. Register strategy in `ChunkingService`
3. Add configuration option for strategy selection
4. Write comprehensive TDD tests for strategy behavior

### Testing Strategy
- **TDD Coverage**: Comprehensive 205+ tests with domain-driven development
- **Unit Tests**: Domain services with no external dependencies
- **Integration Tests**: Complete workflows and factory integration
- **Architecture Tests**: Validate modular factory structure and separation of concerns
- **Strategy Tests**: Comprehensive coverage of chunking strategies
- **Validation Tests**: Robust model validation with edge cases
- **Test Configuration**: Managed in `pytest.ini`
- **Coverage Reports**: Generated in `htmlcov/`

## System Dependencies

Required external tools:
- **Tesseract OCR**: Image-based PDF processing
- **Poppler**: PDF rendering utilities
- **FFmpeg**: Audio processing and MP3 compression
- **espeak/espeak-ng**: Required by some TTS models

## Performance Characteristics

- **Local TTS**: Fast, CPU-intensive
- **Cloud TTS**: Slower, network-dependent, rate-limited
- **Large Documents**: Automatically chunked and processed concurrently
- **Memory**: Scales with document size and concurrent processing
- **Storage**: Temporary files auto-cleaned based on configuration

## 🚀 Next Steps - Phase 2 Architecture Cleanup

### Phase 1 Complete ✅
**TTS Engine Simplification (Completed)**
- ✅ Removed over-engineered persona switching from Gemini TTS provider
- ✅ Simplified from 529 → 352 lines (-33% complexity reduction)
- ✅ Implemented minimal shared services architecture with TextSegmenter
- ✅ Single consistent voice delivery throughout documents
- ✅ Maintained engine-specific optimizations (rate limiting, audio formats)
- ✅ Updated documentation (README.md, CLAUDE.md) and YAML configurations

### Phase 2 - System-Wide Complexity Removal ✅ **COMPLETED**

**Objective**: Complete the architectural simplification by removing document_type complexity throughout the entire system.

#### ✅ **All Files Successfully Cleaned:**

**1. Configuration System** ✅
- `application/config/system_config.py` - Removed document_type validation logic, field, and print statements
- Simplified configuration creation and validation
- Removed document_type from TextProcessingConfig class

**2. Text Processing Pipeline** ✅
- `domain/text/text_pipeline.py` - Made "research_paper" logic universal (no behavioral changes)
- Universal academic text processing approach now applies to ALL document types
- Simplified constructor - removed document_type parameter
- Updated LLM prompt generation to use "universal academic text processing approach"

**3. Service Factories** ✅
- `domain/factories/text_factory.py` - Removed document_type parameter passing ✅ 
- `domain/factories/tts_factory.py` - Already completed ✅ 
- `domain/container/service_container.py` - Removed document_type passing from TextPipeline and GeminiTTSProvider creation

**4. Configuration Files** ✅
- `config.yaml` & `config.example.yaml` - Removed document_type setting and comments
- Cleaned up YAML structure 

**5. Test Updates** ✅
- Updated all 204 tests to reflect document_type removal
- Fixed configuration tests, text pipeline tests, integration tests, and YAML loading tests
- All tests passing: **204/204** ✅

#### ✅ **Implementation Results:**

**Safe Incremental Approach** ✅
- ✅ Pre-cleanup testing: All 160 TDD tests + 204 total tests passed
- ✅ File-by-file cleanup: Completed configuration → text pipeline → service factories → config files
- ✅ Default behavior preservation: Current "research_paper" logic is now universal
- ✅ Test-driven cleanup: Validated after each component modification

#### ✅ **Success Criteria Met:**
- ✅ All tests continue to pass (204/204) 
- ✅ Configuration simplified (no document_type references)
- ✅ Text processing uses universal academic approach
- ✅ Service creation simplified (fewer parameters)
- ✅ Backward compatibility maintained during transition
- ✅ Documentation updated to reflect simplified architecture

### ✅ **Phase 2 Benefits Achieved:**

- **Consistent Simplification**: Uniform architecture across entire system (not just TTS)
- **Reduced Cognitive Load**: Fewer configuration options and code paths to understand  
- **Lower Maintenance**: Fewer conditional branches to test and debug
- **Cleaner Dependencies**: Simplified service creation and injection
- **Universal Text Processing**: Single approach that works well for all document types

**Timeline**: Completed in ~2 hours with comprehensive testing
**Risk Level**: Low (incremental approach with comprehensive testing validated)
**Test Coverage**: 204/204 tests passing (100% success rate)

## 🧹 Phase 3 - Codebase Cleanup and Dead Code Removal

### Objective
Remove accumulated legacy code, duplicate files, and unused infrastructure to reduce maintenance burden and improve developer experience.

### Priority 1: Remove Legacy/Duplicate Test Files ⭐ **HIGH IMPACT, LOW EFFORT**

**Immediate Actions:**
1. **Remove `tests/unit/test_domain_models.py`** (183 lines)
   - Keep `tests/unit/test_domain_models_tdd.py` (615 lines) - comprehensive TDD version
   - Legacy file contains basic tests that are fully covered by TDD version
   - **Benefits**: Reduces test maintenance overhead, eliminates confusion about which tests to update

2. **Remove `test_piper.py`** (root-level standalone test file)
   - Move any unique functionality into proper test structure under `tests/`
   - **Benefits**: Cleaner root directory, proper test organization

**Validation Steps:**
- ✅ Verify TDD test file covers all functionality from legacy file
- ✅ Update test runners/documentation that reference removed files
- ✅ Run full test suite to ensure no functionality lost

### Priority 2: Remove Dead Code and Infrastructure ⭐ **MEDIUM IMPACT, LOW EFFORT**

**Target Files for Removal:**
1. **`infrastructure/tts/architecture_example.py`**
   - Documentation/example code not used in production
   - Remove to reduce codebase clutter

2. **Review and clean `app_factory.py`**
   - Check if still needed after architectural simplification
   - May be redundant with current service factory structure

**Process:**
- ✅ Confirm files are not referenced in production code
- ✅ Check for any imports or dependencies
- ✅ Remove and test full application functionality

### Priority 3: File Structure Optimization ⭐ **MEDIUM IMPACT, MEDIUM EFFORT**

**Consolidation Opportunities:**
1. **Remove empty `__init__.py` files** where not needed for package structure
2. **Review configuration redundancy:**
   - `config/academic_terms_en.json` - verify usage
   - `config/rate_limits.json` - check if all parameters are used
3. **Clean up any remaining configuration artifacts** from document_type removal

**Documentation Updates:**
- Update file structure diagrams in README.md and CLAUDE.md
- Remove references to deleted files
- Simplify development setup instructions

### Priority 4: Code Quality Improvements ⭐ **LOW IMPACT, HIGH EFFORT**

**Advanced Cleanup (Future):**
1. **Remove commented-out code** throughout codebase
2. **Simplify over-complex abstractions** where Phase 2 revealed opportunities
3. **Optimize imports and dependencies** - remove unused imports
4. **Consider consolidating similar utility functions**

### Expected Outcomes

**Immediate Benefits (Priority 1-2):**
- **Faster test execution**: Eliminate duplicate test coverage
- **Reduced cognitive load**: Fewer files to understand and maintain
- **Cleaner development experience**: Clear separation between production and legacy code
- **Lower maintenance burden**: Single source of truth for domain model tests

**Medium-term Benefits (Priority 3-4):**
- **Simplified onboarding**: New developers see only relevant, active code
- **Reduced build/test times**: Fewer files to process
- **Better code organization**: Clear structure without legacy artifacts
- **Improved code quality metrics**: Higher signal-to-noise ratio in codebase

### Implementation Strategy

**Phase 3A: Quick Wins (Priority 1-2)**
- Target completion: 1-2 hours
- Focus on file removal and immediate cleanup
- Validate with full test suite after each removal

**Phase 3B: Structural Cleanup (Priority 3)**  
- Target completion: 2-4 hours
- Systematic review of file structure and configuration
- Update documentation to reflect changes

**Phase 3C: Code Quality (Priority 4)**
- Target completion: As time permits
- Lower priority, higher effort items
- Can be done incrementally over time

### Risk Assessment
- **Low Risk**: File removal with proper validation
- **Medium Risk**: Structural changes require careful testing
- **Validation Strategy**: Comprehensive test suite (204 tests) provides safety net
- **Rollback Plan**: Git history allows easy reversion if issues discovered