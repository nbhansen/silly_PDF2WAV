# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
# Run application
python app.py                          # Starts Flask server at localhost:5000

# Testing
python -m pytest                       # All tests
python -m pytest tests/unit/           # Unit tests only
python -m pytest tests/integration/    # Integration tests only
python -m pytest tests/benchmarks/     # Performance benchmarks
python -m pytest -k "test_name"        # Run specific test by name
python -m pytest -m unit               # Run tests by marker

# Linting & Formatting (pre-commit runs all automatically)
pre-commit run --all-files             # Run all checks
ruff check . --fix                     # Lint with auto-fix
ruff format .                          # Format code
mypy .                                 # Type checking
bandit -c pyproject.toml -r .          # Security scanning
```

## Architecture Overview

This is a **hexagonal architecture** PDF-to-audio converter Flask application:

### Layer Structure
- **`application/`** - Configuration, context, and orchestration services (`DocumentProcessingService`)
- **`domain/`** - Pure business logic with no external dependencies
- **`infrastructure/`** - External service implementations (TTS, OCR, LLM, file system)

### Core Processing Pipeline
1. **DocumentProcessingService** (`application/services/`) - Orchestrates the entire flow
2. **DocumentEngine** (`domain/document/`) - PDF text extraction via OCR
3. **TextPipeline** (`domain/text/`) - Text cleaning/enhancement via LLM, chunking strategies
4. **AudioEngine** (`domain/audio/`) - TTS orchestration, audio file combination
5. **TimingEngine** (`domain/audio/`) - Word-level timing for read-along sync

### Dependency Injection
- **`ServiceContainer`** (`domain/container/service_container.py`) - Immutable DI container with lazy initialization
- **`ApplicationContext`** (`application/context/`) - Holds config + services, passed through Flask's `app.config["APP_CONTEXT"]`
- **`ThreadSafeProgressStore`** (`progress_store.py`) - Thread-safe job progress tracking with locking

### Key Interfaces (`domain/interfaces.py`)
- `ITTSEngine` / `IEnhancedTTSEngine` - Text-to-speech abstraction
- `ILLMProvider` - LLM for text cleaning
- `IOCRProvider` - OCR for PDF text extraction
- `IDocumentProcessor`, `ITextProcessor`, `IFileManager`, `IAudioProcessor`

### TTS Providers
- **Piper TTS** (`infrastructure/tts/piper_tts_provider.py`) - Local neural TTS, production-ready
- **Gemini TTS** (`infrastructure/tts/gemini_tts_provider.py`) - Placeholder/experimental only

### Error Handling
Uses `Result[T]` pattern (`domain/errors.py`) for explicit success/failure handling instead of exceptions. Return `Result.success(value)` or `Result.failure(ApplicationError(...))`.

TTS providers use **deferred error handling**: constructor never raises, stores initialization errors internally, returns failure `Result` on first `generate_audio_data()` call.

All providers (TTS, LLM, etc.) must use the `_initialization_error: Optional[str]` pattern for deferred error handling. The constructor stores error messages in `self._initialization_error`, and each public method checks this field first, returning `Result.failure()` with the stored message before attempting any work. The `self.client = None` check is kept as a fallback after the `_initialization_error` check. See `piper_tts_provider.py` for the reference implementation.

## Configuration

Configuration is loaded into `SystemConfig` dataclass from YAML. Key config sections:
- `tts` - Engine selection (piper/gemini), rate limiting
- `piper` - Voice model, auto-download settings
- `gemini` - API key, model name (for LLM text cleaning)
- `text_processing` - Enable/disable cleaning, chunk sizes
- `files` - Upload/output folders, size limits
- `cleanup` - Auto-cleanup scheduler settings

## Test Fixtures (`tests/conftest.py`)

Standard fixtures available: `test_config`, `temp_dir`, `mock_tts_engine`, `mock_llm_provider`, `mock_file_manager`, `mock_ocr_provider`, `sample_text_segments`, `sample_processing_request`

Skip-if-unavailable fixtures for integration tests: `requires_tesseract`, `requires_piper`, `requires_gemini_api`, `requires_network`

Tests auto-mark based on directory (`tests/unit/` -> `@pytest.mark.unit`, etc.)

## Code Style

- **Line length**: 120 characters
- **Type hints**: Required on all functions (strict mypy)
- **Docstrings**: Google style
- **Imports**: Sorted by isort (first-party: `application`, `domain`, `infrastructure`)
