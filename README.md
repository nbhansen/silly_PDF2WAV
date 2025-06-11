# PDF to Audio App

This project is a "PDF to Audio App" designed to convert PDF documents into audio, making academic papers and other long-form texts accessible for listening. It handles both text-based and image-based PDFs, cleans the extracted content, and synthesizes high-quality audio using various Text-to-Speech (TTS) providers.

## Features

*   **PDF Processing**: Extracts text from PDFs, supporting both direct text extraction and Optical Character Recognition (OCR) for image-based documents.
*   **Intelligent Text Cleaning**: Utilizes a Large Language Model (LLM) to clean extracted text, removing common artifacts found in academic papers (e.g., headers, footers, citations).
*   **SSML Generation**: Generates Speech Synthesis Markup Language (SSML) to enhance audio quality with natural pauses and speech-friendly formatting.
*   **Audio Synthesis**: Supports multiple Text-to-Speech (TTS) providers, including local (e.g., PiperTTS) and cloud-based (e.g., Gemini TTS) options.
*   **Asynchronous Processing**: Leverages asynchronous and concurrent processing for faster audio generation, especially for large documents.
*   **Page Range Selection**: Allows users to specify a range of pages to process, focusing on relevant content.
*   **MP3 Compression**: Automatically combines and compresses generated audio files into MP3 format.

## Architecture

The project follows a layered or hexagonal architecture, promoting separation of concerns, testability, and modularity.

*   **`domain/`**: This layer contains the core business logic, domain models, interfaces, and pure business services. It is independent of external frameworks and infrastructure details. Examples include `domain/models.py` for data structures and `domain/services/audio_generation_service.py` for core audio logic.
*   **`application/`**: This layer orchestrates the domain services to implement specific use cases and application workflows. It acts as an intermediary between the domain and infrastructure layers, handling dependency injection and application-specific configurations. Key files include `application/composition_root.py` for setting up dependencies and `application/services/pdf_processing.py` for the main PDF processing flow.
*   **`infrastructure/`**: This layer provides implementations for external concerns and integrations. It contains adapters for interacting with external systems such as LLM providers, OCR engines, and TTS services. Examples include `infrastructure/llm/gemini_llm_provider.py` for LLM integration and `infrastructure/tts/gemini_tts_provider.py` for TTS services.

## Project structure

```
pdf_to_audio_app/
├── .gitignore
├── app.py
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── requirements.txt
├── run_tests.sh
├── application/
│   ├── __init__.py
│   ├── composition_root.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── config_builders.py
│   │   └── tts_factory.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── pdf_processing.py
├── domain/
│   ├── __init__.py
│   ├── interfaces.py
│   ├── models.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── tts_config.py
│   ├── services/
│   │   ├── async_audio_generation_service.py
│   │   ├── audio_generation_service.py
│   │   ├── ssml_generation_service.py
│   │   ├── ssml_pipeline.py
│   │   └── text_cleaning_service.py
├── infrastructure/
│   ├── __init__.py
│   ├── llm/
│   │   └── gemini_llm_provider.py
│   ├── ocr/
│   │   ├── __init__.py
│   │   └── tesseract_ocr_provider.py
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── audio_generator_adapter.py
│   │   ├── gemini_tts_provider.py
│   │   └── piper_tts_provider.py
│   └── web/
│       └── __init__.py
├── piper/
├── templates/
│   ├── index.html
│   └── result.html
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_audio_generation.py
    ├── test_config.py
    ├── test_helpers.py
    ├── test_processors.py
    ├── test_ssml_complete.py
    ├── test_text_processing.py
    ├── tests_integration.py
    ├── application/
    │   └── services/
    │       └── test_pdf_processing.py
    ├── domain/
    │   ├── test_models.py
    │   └── services/
    │       ├── test_audio_generation_simple.py
    │       └── test_text_cleaning_simple.py
    └── infrastructure/
        └── tts/
            └── test_gemini_tts_provider.py
```

## Setup and Installation

### Prerequisites

*   **Python 3.9 - 3.11**
*   **Tesseract OCR Engine**: For image-based PDF processing. Refer to [Tesseract Installation Guide](https://tesseract-ocr.github.io/tessdoc/Installation.html).
*   **Poppler**: PDF rendering utilities, required by `pdf2image`.
    *   Linux (Debian/Ubuntu): `sudo apt-get install poppler-utils`
    *   macOS (Homebrew): `brew install poppler`
    *   Windows: Download binaries from [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/) and add to PATH.
*   **espeak (or espeak-ng)**: Required by some TTS models for phonemization.
    *   Linux (Debian/Ubuntu): `sudo apt-get install espeak-ng`
    *   macOS (Homebrew): `brew install espeak`
*   **FFmpeg**: Recommended for MP3 compression and metadata fixing.

### Installation Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/nbhansen/silly_PDF2WAV
    cd silly_PDF2WAV
    ```
2.  **Create and activate a Python virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure Environment Variables**: Create a `.env` file in the project root and populate it with necessary API keys and settings (e.g., `GOOGLE_AI_API_KEY`, `TTS_ENGINE`). A template is usually provided or can be inferred from `application/config/config_builders.py` and `domain/config/tts_config.py`.

## Usage

1.  Ensure your Python virtual environment is activated and all prerequisites are installed.
2.  Start the Flask application:
    ```bash
    python app.py
    ```
3.  Open your web browser and navigate to `http://127.0.0.1:5000/`.
4.  Upload a PDF, select desired options (e.g., page range, TTS engine), and generate audio.

## Testing

The project includes a comprehensive test suite. To run all tests:

```bash
./run_tests.sh
```

Alternatively, you can run tests manually with `pytest`:

```bash
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html
```

## Configuration

The application's behavior can be configured through environment variables, typically loaded from a `.env` file. Key configuration files include:

*   [`domain/config/tts_config.py`](domain/config/tts_config.py): Defines the structure and default values for Text-to-Speech engine configurations, including specific settings for different TTS providers (e.g., PiperTTS, Gemini TTS).
*   [`application/config/config_builders.py`](application/config/config_builders.py): Responsible for building and providing configuration objects to the application, often reading values from environment variables and ensuring proper type conversion and validation.

These files work together to allow flexible configuration of TTS engines, API keys, concurrency settings, and other application parameters.
