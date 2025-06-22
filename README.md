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
Create `.env` file:
```bash
TTS_ENGINE=piper
GOOGLE_AI_API_KEY=your_key_here    # Required for Gemini TTS
ENABLE_TEXT_CLEANING=True
```

### Run
```bash
python app.py
```
Access at http://127.0.0.1:5000

## TTS Engines

| Engine | Speed | Cost | API Required |
|--------|-------|------|--------------|
| Piper | Fast | Free | No |
| Gemini | Slower | Paid | Yes |

## Configuration

Environment variables:
- `TTS_ENGINE`: `piper` or `gemini`
- `GOOGLE_AI_API_KEY`: For Gemini features
- `ENABLE_TEXT_CLEANING`: AI text enhancement (default: True)
- `ENABLE_SSML`: Speech markup (default: True)
- `DOCUMENT_TYPE`: `research_paper`, `literature_review`, or `general`

See `application/config/system_config.py` for complete options.

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