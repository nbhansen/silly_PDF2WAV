# PDF to Audio Converter

Converts PDF documents to audio files using OCR and text-to-speech.

## Features

- PDF text extraction via OCR (Tesseract)
- Text processing with LLM-based cleaning (Gemini API)
- Local text-to-speech synthesis (Piper TTS)
- Web interface for file upload/download
- Batch processing support

## Requirements

- Python 3.8+
- Tesseract OCR
- FFmpeg
- Piper TTS binary
- Google AI API key (for text cleaning)

## Linux Setup

### Install System Dependencies

```bash
# Debian/Ubuntu
sudo apt update
sudo apt install tesseract-ocr ffmpeg python3-venv

# Fedora
sudo dnf install tesseract ffmpeg python3-virtualenv

# Arch
sudo pacman -S tesseract ffmpeg python
```

### Install Application

```bash
# Clone repository
git clone <repository-url>
cd silly_PDF2WAV

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Download Piper TTS binary
mkdir -p piper_models
# Download appropriate binary from: https://github.com/rhasspy/piper/releases
# Extract to project root as 'piper'
chmod +x piper
```

### Configuration

```bash
# Copy example configuration
cp config.example.yaml config.yaml

# Edit config.yaml
# Required: Set google_ai_api_key for text cleaning
# Optional: Adjust other settings as needed
```

## Usage

### Web Interface

```bash
source venv/bin/activate
python app.py
# Access http://localhost:5000
```

### Command Line

```bash
source venv/bin/activate
python app.py --input document.pdf --output audio.mp3
```

## Architecture

```
pdf_to_audio_app/
├── application/       # Configuration and orchestration
├── domain/           # Business logic
│   ├── audio/       # Audio generation
│   ├── text/        # Text processing pipeline
│   └── document/    # PDF processing
├── infrastructure/   # External service implementations
│   ├── tts/         # Piper TTS provider
│   ├── llm/         # Gemini LLM provider
│   └── ocr/         # Tesseract OCR provider
└── tests/           # Test suite
```

## API Endpoints

- `GET /` - Web interface
- `POST /upload` - Upload PDF for processing
- `GET /download/<task_id>` - Download generated audio
- `GET /status/<task_id>` - Check processing status

## Configuration Reference

Key settings in `config.yaml`:

- `secrets.google_ai_api_key` - Required for LLM text cleaning
- `tts.piper.model_name` - TTS voice selection
- `text_processing.chunk_size` - Text chunk size for processing
- `audio.concurrent_chunks` - Parallel audio generation threads
- `files.max_file_size_mb` - Maximum upload size

## Testing

```bash
source venv/bin/activate
python -m pytest                 # Run all tests
python -m pytest tests/unit/     # Unit tests only
python -m pytest tests/integration/  # Integration tests only
```

## Dependencies

Core dependencies:
- Flask - Web framework
- google-generativeai - LLM API client
- Pillow - Image processing
- pydub - Audio processing
- PyYAML - Configuration parsing

See `requirements.txt` for complete list.

## License

See LICENSE file.
