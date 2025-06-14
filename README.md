# PDF to Audio App

A PDF to audio conversion application that extracts text from PDFs and converts it to speech using multiple TTS engines. Supports both text-based and image-based PDFs with intelligent text cleaning and SSML enhancement for academic content.

## Current Features

### Core Functionality
- **PDF Text Extraction**: Direct text extraction via pdfplumber with OCR fallback using Tesseract
- **Text Processing**: LLM-based text cleaning removes headers, footers, citations, and adds natural pauses
- **Audio Generation**: Support for multiple TTS engines with async processing
- **Page Range Selection**: Convert specific page ranges instead of entire documents
- **Format Support**: Outputs individual WAV files with combined MP3 creation via FFmpeg

### TTS Engine Support
- **Piper TTS**: Local engine with basic SSML support, no API costs
- **Gemini TTS**: Cloud-based engine with full SSML support, requires Google AI API key

### Advanced Features
- **SSML Enhancement**: Academic-focused speech markup for better pronunciation of numbers, statistics, and technical terms
- **Async Processing**: Concurrent audio generation with intelligent rate limiting
- **File Management**: Automatic cleanup of generated files based on age and disk usage
- **Error Handling**: Structured error system with retryable failures and user-friendly messages

### Web Interface
- Flask-based web application with C64-themed design
- File upload with validation (100MB limit)
- Real-time PDF info display
- Audio playback and download
- Admin endpoints for file management statistics

## Architecture

```
pdf_to_audio_app/
├── application/           # Application orchestration and configuration
│   ├── config/           # SystemConfig and TTS factory
│   └── services/         # PDF processing service
├── domain/               # Core business logic and interfaces
│   ├── services/         # Text cleaning, audio generation, SSML
│   ├── interfaces.py     # Core abstractions
│   ├── models.py         # Domain models
│   └── errors.py         # Structured error handling
├── infrastructure/       # External integrations
│   ├── tts/             # Piper and Gemini TTS providers
│   ├── llm/             # Gemini LLM provider
│   ├── ocr/             # Tesseract OCR provider
│   └── file/            # File lifecycle management
└── templates/           # Web interface templates
```

The project follows clean architecture principles with clear separation between domain logic, application orchestration, and infrastructure concerns.

## Requirements

### System Dependencies
- **Python 3.9-3.11**
- **Tesseract OCR**: Required for image-based PDF processing
- **Poppler**: PDF rendering utilities for pdf2image
- **FFmpeg**: Audio processing and MP3 compression (optional but recommended)
- **espeak/espeak-ng**: Required by some TTS models

### Python Dependencies
See `requirements.txt` for complete list. Key dependencies:
- `Flask` - Web interface
- `google-genai` - Gemini LLM and TTS integration
- `pdfplumber` - PDF text extraction
- `pytesseract` - OCR processing
- `pdf2image` - PDF to image conversion
- `aiofiles` - Async file operations

## Installation

1. **Clone repository**:
   ```bash
   git clone https://github.com/nbhansen/silly_PDF2WAV
   cd silly_PDF2WAV
   ```

2. **Install system dependencies**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr poppler-utils espeak-ng ffmpeg
   
   # macOS (Homebrew)
   brew install tesseract poppler espeak ffmpeg
   ```

3. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

4. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment**:
   Create `.env` file with configuration:
   ```bash
   TTS_ENGINE=piper                    # or 'gemini'
   GOOGLE_AI_API_KEY=your_api_key     # required for Gemini TTS/LLM
   ENABLE_TEXT_CLEANING=True
   ENABLE_SSML=True
   DOCUMENT_TYPE=research_paper
   ```

## Configuration

The application uses environment variables for configuration. Key settings:

### Core Settings
- `TTS_ENGINE`: `piper` (local) or `gemini` (cloud)
- `ENABLE_TEXT_CLEANING`: Use LLM for text enhancement (default: True)
- `ENABLE_SSML`: Apply SSML markup for better speech (default: True)
- `DOCUMENT_TYPE`: `research_paper`, `literature_review`, or `general`

### File Management
- `ENABLE_FILE_CLEANUP`: Automatic file cleanup (default: True)
- `MAX_FILE_AGE_HOURS`: File retention period (default: 24)
- `MAX_DISK_USAGE_MB`: Disk usage limit before forced cleanup (default: 1000)

### TTS Engine Specific
- `GOOGLE_AI_API_KEY`: Required for Gemini TTS and LLM features
- `PIPER_MODEL_NAME`: Piper voice model (default: en_US-lessac-medium)
- `MAX_CONCURRENT_TTS_REQUESTS`: Async processing limit (default: 4)

See `application/config/system_config.py` for complete configuration options.

## Usage

1. **Start application**:
   ```bash
   python app.py
   ```

2. **Access web interface**: http://127.0.0.1:5000

3. **Convert PDF**:
   - Upload PDF file (max 100MB)
   - Optionally specify page range
   - Download generated audio files

### Admin Endpoints
- `/admin/file_stats` - File management statistics
- `/admin/cleanup` - Manual cleanup trigger
- `/admin/test` - System status information

## Performance Characteristics

### Processing Speed
- **Local TTS (Piper)**: Fast, no network dependencies
- **Cloud TTS (Gemini)**: Slower due to API calls, rate limited
- **Text Cleaning**: Depends on LLM response time when enabled
- **Large Documents**: Automatically chunked and processed concurrently

### Resource Usage
- **CPU**: Moderate for local TTS, minimal for cloud TTS
- **Memory**: Scales with document size and concurrent chunks
- **Disk**: Temporary files auto-cleaned based on configuration
- **Network**: Only required for Gemini TTS/LLM features

## Testing

Run test suite:
```bash
./run_tests.py              # All tests
./run_tests.py integration  # Integration tests only
./run_tests.py unit         # Unit tests only
./run_tests.py quick        # Single fast test
```

Or directly with pytest:
```bash
pytest tests/ -v --cov=. --cov-report=html
```

## Limitations

- **File Size**: 100MB PDF limit (configurable)
- **TTS Quality**: Varies between engines and models
- **Processing Time**: Large documents can take several minutes
- **API Costs**: Gemini TTS usage incurs charges
- **Language Support**: Currently optimized for English content
- **SSML Support**: Limited by TTS engine capabilities

## Error Handling

The application includes structured error handling with:
- Retryable vs permanent error classification
- User-friendly error messages
- Automatic fallbacks (OCR when direct extraction fails)
- Rate limit handling for cloud APIs

Common error scenarios are handled gracefully with informative feedback to users.