# PDF to Audio Converter

A robust, enterprise-ready application that converts PDF documents to high-quality audio files using advanced text extraction and TTS engines. Built with clean architecture principles and comprehensive test coverage.

## ✨ Features

- **Advanced PDF Processing**: Text extraction with intelligent OCR fallback
- **AI-Powered Text Enhancement**: LLM-based text cleaning for optimal audio quality
- **Dual TTS Engine Support**: Piper TTS (local, fast) and Gemini TTS (cloud, high-quality)
- **Academic Document Optimization**: SSML enhancement for research papers and technical content
- **Intelligent Text Chunking**: Configurable chunking strategies for optimal processing
- **Modern Web Interface**: Clean UI for file upload, processing, and download
- **Flexible Page Selection**: Process entire documents or specific page ranges
- **Robust Error Handling**: Comprehensive error management with retry logic

## 🏗️ Architecture

The application follows **Clean Architecture** principles with clear separation of concerns:

### Domain Layer (`domain/`)
- **Core Business Logic**: Models, interfaces, and domain services
- **Modular Factories**: Focused service creation (`audio_factory.py`, `text_factory.py`, `tts_factory.py`)
- **Strategy Pattern**: Pluggable text chunking strategies (`chunking_strategy.py`)
- **Robust Validation**: Domain models with built-in validation
- **Error Management**: Structured error handling with typed results

### Application Layer (`application/`)
- **Configuration Management**: YAML-based system configuration
- **Service Orchestration**: High-level application workflows

### Infrastructure Layer (`infrastructure/`)
- **External Services**: TTS engines, LLM providers, OCR, file management
- **Service Adapters**: Clean interfaces to external dependencies

### Web Layer
- **Flask Interface**: RESTful API and web UI
- **Request Handling**: File uploads, processing status, downloads

## 🚀 Installation

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr poppler-utils espeak-ng ffmpeg

# macOS
brew install tesseract poppler espeak ffmpeg
```

### Application Setup
```bash
git clone https://github.com/nbhansen/silly_PDF2WAV
cd silly_PDF2WAV
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration

**YAML Configuration (Required)**
```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
```

Key settings in `config.yaml`:
```yaml
tts:
  engine: "gemini"              # or "piper" for local TTS
  gemini:
    voice_name: "Kore"          # Options: Kore, Charon, Aoede, Leda
    model_name: "gemini-2.5-pro-preview-tts"  # Gemini TTS model

llm:
  model_name: "gemini-2.5-pro-preview"       # For text cleaning

secrets:
  google_ai_api_key: ""         # Your API key here (required for Gemini)

text_processing:
  document_type: "research_paper"  # or "literature_review", "general"
  enable_text_cleaning: true
  enable_ssml: true
  
audio:
  target_chunk_size: 2000       # Characters per audio chunk
  max_chunk_size: 3000          # Maximum chunk size
```

### Run
```bash
python app.py
```
Access at http://127.0.0.1:5000

## 🎯 TTS Engines

| Engine | Speed | Cost | API Required | Voice Configuration |
|--------|-------|------|--------------|--------------------|
| **Piper** | Fast | Free | No | Model-based (e.g., en_US-lessac-high) |
| **Gemini** | Slower | Paid | Yes | Single voice with content-aware styling |

### Engine Selection
- **Development/Testing**: Use Piper for fast, free processing
- **Production/Quality**: Use Gemini for superior voice quality and SSML support
- **Hybrid**: Configure both and switch based on requirements

## ⚙️ Configuration Architecture

The application uses a robust YAML-based configuration system with validation:

### Service Configuration
- **Modular Factories**: Each service type has its own focused factory
- **Dependency Injection**: Clean service creation with proper dependencies
- **Configuration Validation**: Built-in validation for all settings

### Core Settings
- `tts.engine`: `piper` or `gemini`
- `secrets.google_ai_api_key`: For Gemini features
- `llm.model_name`: Separate LLM model for text cleaning
- `tts.gemini.model_name`: Dedicated TTS model (distinct from LLM)
- `text_processing.document_type`: Content-aware styling
- `audio.target_chunk_size`: Optimal chunk size for processing

## 🧪 Testing

Our application has comprehensive test coverage with multiple test runners:

```bash
./run_tests.py              # All tests (205 tests)
./run_tests.py unit         # Unit tests only
./run_tests.py quick        # Fast test subset
python -m pytest tests/    # Direct pytest execution
```

### Test Architecture
- **Unit Tests**: Domain models, services, factories
- **Integration Tests**: Service factory integration, end-to-end workflows
- **TDD Coverage**: Comprehensive test-driven development approach
- **Mocked Dependencies**: Isolated testing without external services

### Test Categories
- **Domain Models**: Validation, business logic, error handling
- **Service Factories**: Modular service creation and dependency injection
- **Text Processing**: Chunking strategies, pipeline operations
- **Error Handling**: Comprehensive error scenarios and recovery

## 📋 Requirements

### Runtime Requirements
- **Python**: 3.9-3.11
- **System Libraries**: Tesseract, Poppler, FFmpeg, espeak
- **API Access**: Google AI API key (optional, for Gemini features)

### Development Requirements
- **Testing**: pytest, pytest-cov, pytest-asyncio
- **Quality**: All tests passing (205/205)
- **Architecture**: Clean architecture with SOLID principles
- **Documentation**: Comprehensive inline and markdown documentation

## 🏛️ Detailed Architecture

### Domain Layer Structure
```
domain/
├── models.py              # Core domain models with validation
├── interfaces.py          # Service interfaces and contracts
├── errors.py             # Structured error handling
├── audio/                # Audio processing services
│   ├── audio_engine.py   # Main audio generation engine
│   └── timing_engine.py  # Audio timing and synchronization
├── text/                 # Text processing services
│   ├── text_pipeline.py  # Text cleaning and enhancement
│   └── chunking_strategy.py  # Pluggable chunking strategies
├── document/            # Document processing
│   └── document_engine.py  # PDF text extraction
├── factories/           # Service creation (Dependency Injection)
│   ├── service_factory.py   # Main service orchestration
│   ├── audio_factory.py     # Audio service creation
│   ├── text_factory.py      # Text service creation
│   └── tts_factory.py       # TTS engine creation
├── config/              # Domain configuration
│   └── tts_config.py    # TTS-specific configuration
└── container/           # Service container
    └── service_container.py  # Dependency injection container
```

### Key Architectural Improvements
- **Modular Factories**: Each service type has focused factory
- **Strategy Pattern**: Pluggable text chunking algorithms
- **Clean Dependencies**: No circular imports, proper TYPE_CHECKING
- **Robust Validation**: Domain models validate themselves
- **Separation of Concerns**: Clear distinction between TTS and LLM models

## Admin Endpoints

- `/admin/file_stats` - Storage statistics
- `/admin/cleanup` - Manual file cleanup
- `/admin/test` - System status

## Notes

- Files stored in `.local/` directory (git-ignored)
- 100MB file size limit
- Automatic cleanup after 24 hours