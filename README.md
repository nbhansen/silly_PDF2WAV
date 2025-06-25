# PDF to Audio Converter

Converts PDF documents to audio files using text extraction and TTS engines.

## Features

- PDF text extraction with OCR fallback
- LLM-based text cleaning
- Piper TTS (local) and Gemini TTS (cloud) support
- SSML enhancement for academic documents
- Web interface for file upload/download
- Page range selection

## Installation

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

#### Option 1: YAML Configuration (Recommended)
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

secrets:
  google_ai_api_key: ""         # Your API key here (required for Gemini)

text_processing:
  document_type: "research_paper"  # or "literature_review", "general"
  enable_text_cleaning: true
  enable_ssml: true
```

#### Option 2: Environment Variables (Fallback)
Create `.env` file:
```bash
# Core settings
TTS_ENGINE=gemini
GOOGLE_AI_API_KEY=your_key_here    # Required for Gemini TTS

# Voice configuration (Gemini only)
GEMINI_VOICE_NAME=Kore             # Single voice for all content
DOCUMENT_TYPE=research_paper       # Content-aware styling

# Text processing
ENABLE_TEXT_CLEANING=True
ENABLE_SSML=True
```

### Run
```bash
python app.py
```
Access at http://127.0.0.1:5000

## TTS Engines

| Engine | Speed | Cost | API Required | Voice Configuration |
|--------|-------|------|--------------|--------------------|
| Piper | Fast | Free | No | Model-based (e.g., en_US-lessac-high) |
| Gemini | Slower | Paid | Yes | Single voice with content-aware styling |

## Configuration Details

The application supports both YAML and environment variable configuration:

### Core Settings
- `tts.engine` / `TTS_ENGINE`: `piper` or `gemini`
- `secrets.google_ai_api_key` / `GOOGLE_AI_API_KEY`: For Gemini features
- `tts.gemini.voice_name` / `GEMINI_VOICE_NAME`: Single voice for all TTS (Kore, Charon, Aoede, Leda)
- `text_processing.document_type` / `DOCUMENT_TYPE`: Content-aware styling (`research_paper`, `literature_review`, `general`)
- `text_processing.enable_text_cleaning` / `ENABLE_TEXT_CLEANING`: AI text enhancement (default: true)
- `text_processing.enable_ssml` / `ENABLE_SSML`: Speech markup (default: true)

### Voice System
- **Gemini TTS**: Uses single voice with intelligent content styling
- **Piper TTS**: Uses model-based voices, ignores Gemini voice config
- **Content Processing**: Document type drives emphasis and technical content handling

See `config.example.yaml` for all available options or `application/config/system_config.py` for defaults.

## Testing

```bash
./run_tests.py              # All tests
./run_tests.py unit         # Unit tests only
./run_tests.py quick        # Fast test
```

## Requirements

- Python 3.9-3.11
- Tesseract, Poppler, FFmpeg, espeak
- Google AI API key (optional, for Gemini features)

## Architecture

- **Domain**: Core business logic
- **Application**: Configuration and orchestration  
- **Infrastructure**: External services (TTS, LLM, OCR, files)
- **Web**: Flask interface

## Admin Endpoints

- `/admin/file_stats` - Storage statistics
- `/admin/cleanup` - Manual file cleanup
- `/admin/test` - System status

## Notes

- Files stored in `.local/` directory (git-ignored)
- 100MB file size limit
- Automatic cleanup after 24 hours