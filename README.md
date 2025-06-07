# Nicolais silly PDF to Audio Converter with OCR and LLM Cleaning
![2e849eb9bba1dafe](https://github.com/user-attachments/assets/46f8cfeb-53b1-408a-9aff-e850794af5b2)

I always wanted to listen to academic papers in my car and now I can, sorta not the best but here we are. Sure I could use a PDF-read-aloud thing, but academic papers are full of weird crud that distracts the everliving mother out of me.

This web application processes PDF documents by:
1. Extracting text using direct methods (for text-based PDFs) or OCR (via Tesseract and Poppler for image-based PDFs)
2. Cleaning the extracted text using Google's Gemini Pro LLM via the Google AI API
3. Generating an audio version of the cleaned text using multiple TTS engines (Coqui TTS, gTTS, Bark, or Gemini TTS)

The application is built with Flask and provides a simple web interface for uploading PDFs and listening to/downloading the generated audio.

## 🏗️ Architecture

This project now follows **Clean Architecture** principles with proper separation of concerns and dependency injection:

### 📁 Project Structure
```
pdf_to_audio_app/
├── app.py                          # Flask web application entry point
├── domain/                         # 🏛️ Pure business logic (no dependencies)
│   ├── models.py                   # Domain models, interfaces, and data classes
│   └── services/                   # Domain services with business rules
│       ├── text_cleaning_service.py
│       └── audio_generation_service.py
├── application/                    # 🔧 Application orchestration layer
│   ├── composition_root.py         # Dependency injection setup
│   └── services/
│       └── pdf_processing.py       # Main PDF processing service
├── infrastructure/                 # 🔌 External integrations and implementations
│   ├── llm/
│   │   └── gemini_llm_provider.py  # Google Gemini LLM integration
│   ├── ocr/
│   │   └── tesseract_ocr_provider.py # OCR implementation
│   └── tts/                        # Text-to-Speech providers
│       ├── coqui_tts_provider.py
│       ├── gtts_provider.py
│       ├── bark_tts_provider.py
│       └── gemini_tts_provider.py
├── templates/                      # 🌐 HTML templates
├── tests/                          # 🧪 Comprehensive test suite
│   ├── domain/                     # Domain logic tests
│   ├── application/                # Application service tests
│   ├── infrastructure/             # Infrastructure tests
│   └── test_integration.py         # End-to-end integration tests
├── uploads/                        # 📁 For uploaded PDFs (auto-created)
├── audio_outputs/                  # 🎵 For generated audio (auto-created)
└── requirements.txt                # Python dependencies
```

### 🎯 Key Architectural Benefits

- **Clean Separation**: Domain logic is independent of infrastructure concerns
- **Testability**: Comprehensive test suite with >90% coverage
- **Modularity**: Easy to swap TTS engines, LLM providers, or OCR implementations
- **Dependency Injection**: All dependencies are properly injected through the composition root
- **SOLID Principles**: Each class has a single responsibility and follows interface segregation

## ✨ Features

### Core Functionality
* **Smart Text Extraction**: Handles both text-based and image-based PDFs with automatic fallback to OCR
* **Advanced Text Cleaning**: Uses Google Gemini Pro to remove academic paper artifacts (headers, footers, citations, etc.)
* **TTS Optimization**: Adds natural pauses and speech-friendly formatting for better listening experience
* **Multiple TTS Engines**: Choose from Coqui TTS (default), gTTS, Bark, or Gemini TTS
* **Page Range Selection**: Process specific pages rather than entire documents
* **MP3 Compression**: Automatically combines and compresses audio files using FFmpeg

### Technical Features
* **Clean Architecture**: Modular, testable, and maintainable codebase
* **Dependency Injection**: Proper IoC container for easy testing and configuration
* **GPU Acceleration**: Supports NVIDIA CUDA for Coqui TTS and Bark TTS
* **Comprehensive Testing**: Unit tests, integration tests, and mocked external dependencies
* **Error Handling**: Graceful degradation and informative error messages
* **Rate Limiting**: Built-in delays for API calls to respect service limits

### User Experience
* **Simple Web Interface**: Drag-and-drop PDF upload with real-time feedback
* **Progress Indicators**: Visual feedback during processing
* **Audio Preview**: Play generated audio directly in the browser
* **Download Options**: Save individual chunks or combined MP3 files
* **Mobile Friendly**: Responsive design for phone and tablet use

## Setup & Installation

### Prerequisites

* **Python 3.9 - 3.11** (Python 3.11 recommended for Coqui TTS compatibility)
* **Tesseract OCR Engine:**
    * Installation instructions: [https://tesseract-ocr.github.io/tessdoc/Installation.html](https://tesseract-ocr.github.io/tessdoc/Installation.html)
    * Ensure Tesseract is added to your system's PATH.
* **Poppler:** (PDF rendering utilities, required by `pdf2image`)
    * **Linux (Debian/Ubuntu):** `sudo apt-get install poppler-utils`
    * **macOS (Homebrew):** `brew install poppler`
    * **Windows:** Download Poppler binaries, extract, and add the `bin/` directory to your system's PATH. (More info: [https://github.com/oschwartz10612/poppler-windows/releases/](https://github.com/oschwartz10612/poppler-windows/releases/))
* **espeak (or espeak-ng):** (Required by some Coqui TTS models for phonemization)
    * **Linux (Debian/Ubuntu):** `sudo apt-get install espeak-ng`
    * **macOS (Homebrew):** `brew install espeak`
    * **Windows:** Download espeak binaries and add to PATH.
* **FFMPeg** (recommended for MP3 compression)

### Installation Steps

1. **Clone the repository:**
    ```bash
    git clone https://github.com/nbhansen/silly_PDF2WAV
    cd silly_PDF2WAV
    ```

2. **Create and activate a Python virtual environment (highly recommended):**
    ```bash
    python3 -m venv venv 
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Create and Configure the `.env` File**

This project uses a `.env` file to manage environment variables and secrets.  
Create a new `.env` file in the project root with the following content:

```properties
# .env - Environment variables for the Silly PDF to Audio App

# Flask settings
FLASK_ENV=development
FLASK_DEBUG=1

# Folders (these can be anything you want)
UPLOAD_FOLDER=uploads
AUDIO_FOLDER=audio_outputs

# Allowed file extensions (comma-separated, won't work with anything but pdf though)
ALLOWED_EXTENSIONS=pdf

# Google Gemini API Key (get from https://aistudio.google.com/)
GOOGLE_AI_API_KEY=your_real_google_api_key_here

# TTS Engine selection: coqui, gtts, bark, or gemini
TTS_ENGINE=coqui

# Coqui TTS config (the default - high quality, local processing)
COQUI_MODEL_NAME=tts_models/en/ljspeech/vits
COQUI_USE_GPU_IF_AVAILABLE=True

# gTTS config (lightweight, cloud-based)
GTTS_LANG=en
GTTS_TLD=co.uk

# Bark config (highest quality, very resource-intensive)
BARK_USE_GPU_IF_AVAILABLE=True
BARK_USE_SMALL_MODELS=True
BARK_HISTORY_PROMPT=

# Gemini TTS config (cloud-based, excellent quality)
GEMINI_VOICE_NAME=Kore
GEMINI_STYLE_PROMPT=
```

**Important:**  
- Replace `your_real_google_api_key_here` with your actual Google Gemini API key
- Do **not** commit your `.env` file to version control

## 🧪 Testing

The project includes a comprehensive test suite covering all architectural layers:

### Run All Tests
```bash
./run_tests.sh
```

Or manually with coverage:
```bash
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html
```

### Test Categories
- **Domain Tests**: Pure business logic (no external dependencies)
- **Application Tests**: Service orchestration and workflow
- **Infrastructure Tests**: External integrations and providers
- **Integration Tests**: End-to-end workflows with mocked dependencies

### Test Coverage
- Text extraction and cleaning pipeline
- Audio generation with multiple TTS engines
- Page range validation and processing
- Error handling and graceful degradation
- Configuration and dependency injection

## 🎛️ Configuration

### TTS Engine Selection

Choose your preferred Text-to-Speech engine in the `.env` file:

* **Coqui TTS** (default): High-quality, local processing, GPU acceleration support
* **gTTS**: Lightweight, cloud-based, good for testing and low-resource systems
* **Bark**: Highest quality, very resource-intensive, requires powerful hardware
* **Gemini TTS**: Cloud-based, excellent quality, requires API key

### Model Configuration

* **Coqui TTS Models**: Use `tts --list-models` to see available options
* **GPU Acceleration**: Automatically detected for NVIDIA CUDA systems
* **Voice Customization**: Configure speakers, styles, and quality settings

## 🚀 Running the Application

1. Ensure your virtual environment is activated
2. Make sure all prerequisites are installed and configured
3. Start the Flask application:
    ```bash
    python app.py
    ```
4. Open your web browser and navigate to `http://127.0.0.1:5000/`

## 🎯 Usage Tips

### For Academic Papers
- Skip title pages (start at page 2-3)
- End before references section (typically last 10-20% of pages)
- Use page range selection to focus on main content

### Performance Optimization
- **Coqui TTS**: Best balance of quality and performance
- **GPU Acceleration**: Significantly faster processing with NVIDIA GPUs
- **Page Ranges**: Process only needed sections for faster results
- **Text Cleaning**: LLM cleaning greatly improves listening experience

### Troubleshooting
- **TTS Model Downloads**: First run downloads models automatically
- **Memory Usage**: Use smaller models or page ranges for large documents
- **Audio Quality**: Higher quality engines produce larger files

## 🔧 Development

### Adding New TTS Engines
1. Create new provider in `infrastructure/tts/`
2. Implement `ITTSEngine` interface
3. Add configuration to `domain/models.py`
4. Register in `composition_root.py`
5. Add tests in `tests/infrastructure/tts/`

### Adding New LLM Providers
1. Create provider in `infrastructure/llm/`
2. Implement `ILLMProvider` interface
3. Update composition root configuration
4. Add comprehensive tests

### Code Quality
- Run tests: `./run_tests.sh`
- Format code: `black .`
- Sort imports: `isort .`
- Type checking: `mypy .`
- Linting: `flake8 .`

## 🚨 Known Issues & Future Enhancements

### Current Limitations
- TTS models may mispronounce technical terms or acronyms
- Large documents require chunking which may affect flow
- Processing time scales with document length and TTS engine choice

### Planned Features
- **LaTeX Input Support**: Direct processing of academic LaTeX files
- **Asynchronous Processing**: Background processing with progress tracking
- **Voice Cloning**: Custom voice training for personalized narration
- **Multiple Language Support**: Extend beyond English
- **Audio Post-Processing**: Noise reduction, normalization, chapters

### Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and contribution instructions.

## 🎉 My Wacky Dream Feature

Turn this thing into a sexy LaTeX→Voice beast, thus bypassing the stupid PDF-extract and also enabling people who write academic papers to provide a buttery-smooth audio version for their vision or neurodivergent friends. Imagine submitting your paper with an accompanying audio version that's actually pleasant to listen to!

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---