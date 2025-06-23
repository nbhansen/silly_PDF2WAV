# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
│   ├── services/         # Text cleaning, audio generation, SSML enhancement
│   ├── interfaces.py     # Abstract interfaces for all external dependencies
│   ├── models.py         # Domain models and data structures
│   └── errors.py         # Structured error handling system
├── infrastructure/       # External service implementations
│   ├── tts/             # Gemini and Piper TTS providers
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
./test-tdd.sh                    # All 187 TDD tests
./test-tdd.sh fast               # TDD tests with fast failure
./test-commit.sh                 # Pre-commit validation

# Enhanced Test Runner
python run_tests.py tdd          # All TDD tests (187 tests)
python run_tests.py commit       # Pre-commit validation
python run_tests.py models       # Domain models (47 tests)
python run_tests.py pipeline     # Text processing (47 tests)
python run_tests.py config       # Configuration (49 tests)
python run_tests.py errors       # Error handling (44 tests)
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

#### TDD Test Coverage (187 Tests)
- **Domain Models**: 47 tests - Data integrity and immutability
- **Text Processing Pipeline**: 47 tests - Pure text processing logic  
- **System Configuration**: 49 tests - Environment parsing and validation
- **Error Handling System**: 44 tests - Structured error management

### Environment Setup
```bash
python3 -m venv venv
source venv/bin/activate         # Linux/Mac
venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

## Configuration System

All configuration is managed through `application/config/system_config.py` using environment variables:

### Core Settings
- `TTS_ENGINE`: `piper` (local) or `gemini` (cloud)
- `GOOGLE_AI_API_KEY`: Required for Gemini TTS/LLM features
- `GEMINI_VOICE_NAME`: Single voice for all TTS generation (Kore, Charon, Aoede, Leda)
- `DOCUMENT_TYPE`: Content-aware styling (`research_paper`, `literature_review`, `general`)
- `ENABLE_TEXT_CLEANING`: Use LLM for text enhancement (default: True)
- `ENABLE_SSML`: Apply SSML markup for better speech (default: True)

### Voice System Logic Separation
- **Content Processing**: `DOCUMENT_TYPE` determines how content is styled and emphasized
- **Voice Selection**: `GEMINI_VOICE_NAME` determines which voice speaks (Gemini only)
- **Engine Independence**: Piper uses model-based voices, Gemini uses API voices

### File Management
- `ENABLE_FILE_CLEANUP`: Automatic file cleanup (default: True)
- `MAX_FILE_AGE_HOURS`: File retention period (default: 24)
- `MAX_DISK_USAGE_MB`: Disk usage limit (default: 1000)

The `SystemConfig.from_env()` method validates all configuration and fails fast with clear error messages.

## Dependency Injection

The `application/composition_root.py` handles all dependency injection:
- Creates and wires all services based on configuration
- Manages the object graph and lifecycle
- Entry point: `create_pdf_service_from_env()` returns fully configured service

## Core Processing Flow

1. **PDF Upload** → Flask routes (`/upload` or `/upload-with-timing`)
2. **Text Extraction** → OCR provider (Tesseract) with PDF info validation
3. **Text Cleaning** → LLM provider (Gemini) removes headers/footers, adds pauses
4. **SSML Enhancement** → Academic SSML service improves pronunciation
5. **Audio Generation** → TTS engine (Piper/Gemini) with timing strategies
6. **File Management** → Cleanup scheduler manages temporary files

## TTS Engine Support

### Piper TTS (Local)
- Fast, no API costs
- Basic SSML support
- Models stored in `piper_models/`
- Configuration: Uses `PIPER_MODEL_NAME` (e.g., en_US-lessac-high)
- Voice: Determined by selected model

### Gemini TTS (Cloud) - Simplified Single Voice System
- Full SSML support with precise timestamps
- Requires Google AI API key
- Rate limiting with intelligent retry logic
- **Single Voice Configuration**: `GEMINI_VOICE_NAME` used for all content
- **Content-Aware Styling**: `DOCUMENT_TYPE` drives speech patterns
  - `research_paper`: "precisely and methodically" for technical content
  - `literature_review`: "thoughtfully and analytically" for narrative
  - `general`: Natural, conversational styles
- **No Multi-Voice Complexity**: Removed voice personas JSON system

## Timing Strategies

The application uses different timing strategies based on TTS engine:

- **GeminiTimestampStrategy**: Uses engine-provided timestamps (ideal)
- **SentenceMeasurementStrategy**: Measures timing manually (fallback)

Both implement `ITimingStrategy` interface and return `TimedAudioResult` objects.

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
3. Update `service_factory.create_tts_engine()`
4. Consider implementing `ITimestampedTTSEngine` for timing support
5. **Voice Configuration**: Decide if engine uses single voice or model-based voices

### Voice System Architecture
- **Simplified Design**: Single voice per session, content-aware styling
- **No Voice Personas**: Removed complex multi-voice JSON configuration
- **Domain Separation**: Content processing vs voice selection are independent
- **Engine Flexibility**: Each TTS engine handles voice configuration differently

### When Adding New Text Processing
1. Define interface in `domain/interfaces.py`
2. Implement service in `domain/services/`
3. Add infrastructure provider in `infrastructure/`
4. Wire in `CompositionRoot`

### Testing Strategy
- Unit tests for domain services (no external dependencies)
- Integration tests for complete workflows
- Test configuration in `pytest.ini`
- Coverage reports in `htmlcov/`

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