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
- **TTS Engines**: Gemini TTS (cloud), Piper TTS (local) with shared TextSegmenter utilities
- **LLM Providers**: Gemini for text cleaning and enhancement
- **External Services**: OCR (Tesseract), file management, cleanup scheduling
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
    voice_name: "Kore"          # Single voice: Kore, Charon, Aoede, Leda
    model_name: "gemini-2.5-pro-preview-tts"  # Gemini TTS model

llm:
  model_name: "gemini-2.5-pro-preview"       # For text cleaning

secrets:
  google_ai_api_key: ""         # Your API key here (required for Gemini)

text_processing:
  enable_text_cleaning: true    # LLM-based text enhancement
  enable_ssml: true             # Academic SSML improvements

audio:
  target_chunk_size: 2000       # Characters per audio chunk
  max_chunk_size: 3000          # Maximum chunk size
```

### Run
```bash
python app.py
```
Access at http://127.0.0.1:5000

## 🚀 Getting Started

### Quick Start (5 minutes)

1. **Setup Configuration**
   ```bash
   cp config.example.yaml config.yaml
   ```
   
   For **Piper TTS** (free, local):
   ```yaml
   tts:
     engine: "piper"
   ```
   
   For **Gemini TTS** (requires API key):
   ```yaml
   tts:
     engine: "gemini"
   secrets:
     google_ai_api_key: "your-api-key-here"
   ```

2. **Start the Application**
   ```bash
   source venv/bin/activate
   python app.py
   ```

3. **Upload and Convert**
   - Open http://127.0.0.1:5000 in your browser
   - Upload a PDF file (research papers work great!)
   - Select pages (optional - leave blank for full document)
   - Click "Convert to Audio"
   - Download your MP3 when processing completes

### First Time Setup Tips

- **Test with a small PDF first** (1-2 pages) to verify everything works
- **Piper TTS** downloads models automatically (~100MB) on first use
- **Gemini TTS** requires a [Google AI API key](https://aistudio.google.com/app/apikey) but provides higher quality voices
- Check the **console output** for processing status and any errors

### Example Workflow

```bash
# 1. Quick setup for local processing
cp config.example.yaml config.yaml
# (Use default Piper settings)

# 2. Start the server
python app.py

# 3. Upload a research paper PDF
# 4. Select pages 1-10 (optional)
# 5. Enable text cleaning for better quality
# 6. Download the generated MP3

# Processing typically takes 30 seconds - 2 minutes per page
```

## 🎯 Recent Architecture Improvements

### TTS Engine Simplification (v2.0)
- **Removed over-engineered persona switching**: Eliminated artificial voice style changes for more natural speech
- **Simplified to single voice delivery**: Consistent voice throughout entire document
- **Minimal shared services architecture**: TextSegmenter provides universal text processing while keeping engine-specific logic separate
- **Reduced complexity**: Gemini TTS provider simplified from 529 → 352 lines (-33%)
- **Improved maintainability**: Clear separation between shared utilities and engine-specific features
- **Future-ready**: Easy to add new TTS engines (ElevenLabs) using the same TextSegmenter foundation

## 🎯 TTS Engines

| Engine | Speed | Cost | API Required | Voice Configuration |
|--------|-------|------|--------------|--------------------|
| **Piper** | Fast | Free | No | Model-based (e.g., en_US-lessac-high) |
| **Gemini** | Slower | Paid | Yes | Single consistent voice (e.g., Kore, Charon) |

### Engine Selection
- **Development/Testing**: Use Piper for fast, free processing
- **Production/Quality**: Use Gemini for superior voice quality and natural speech
- **Hybrid**: Configure both and switch based on requirements

### TTS Architecture - Minimal Shared Services

The TTS system uses a **minimal shared services** approach optimized for different engine capabilities:

#### Universal Components
- **TextSegmenter** (`infrastructure/tts/text_segmenter.py`): Shared text processing utilities
  - Sentence splitting with abbreviation handling
  - Duration calculation with punctuation timing
  - Text cleaning and chunking
  - Works with all TTS engines (Piper, Gemini, future ElevenLabs)

#### Engine-Specific Components
- **Gemini TTS**: Cloud API with rate limiting, PCM→WAV conversion, async processing
- **Piper TTS**: Local processing, direct WAV output, synchronous operation
- **Future engines**: Can reuse TextSegmenter + add engine-specific logic

#### Benefits
- **Shared utilities** prevent code duplication for universal text processing
- **Engine-specific logic** stays separate (SSML support, rate limiting, audio formats)
- **Easy to extend** - new engines just need TextSegmenter + their specific requirements

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
- `tts.gemini.voice_name`: Single consistent voice for entire document
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
- **Simplified TTS**: Removed over-engineered persona switching for natural speech
- **Shared Utilities**: TextSegmenter provides universal text processing for all TTS engines
- **Minimal Shared Services**: Balance between code reuse and engine-specific flexibility

## Admin Endpoints

- `/admin/file_stats` - Storage statistics
- `/admin/cleanup` - Manual file cleanup
- `/admin/test` - System status

## Notes

- Files stored in `.local/` directory (git-ignored)
- 100MB file size limit
- Automatic cleanup after 24 hours
