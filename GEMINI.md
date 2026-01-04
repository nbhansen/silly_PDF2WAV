# PDF2WAV (PDF to Audio Converter)

## Project Overview

**pdf2wav** is a Flask-based web application designed to convert PDF academic papers and documents into high-quality, listenable audio (MP3). It utilizes a Hexagonal Architecture (Ports and Adapters) to ensure separation of concerns between the core domain logic and external services.

### Key Features
*   **OCR:** Tesseract-based text extraction from PDFs.
*   **Text Cleaning:** Uses Google Gemini LLM to clean and format text for better speech synthesis.
*   **TTS:** Local neural Text-to-Speech using **Piper TTS**.
*   **Interface:** Web UI for uploading, processing, and "read-along" playback.

## Architecture

The project follows **Hexagonal Architecture**:

*   **`domain/`**: Contains the core business logic, entities, and interfaces. This layer has **no external dependencies**.
    *   `interfaces.py`: Defines contracts (`ITTSEngine`, `ILLMProvider`, `IOCRProvider`).
    *   `audio/`, `text/`, `document/`: Core processing engines.
    *   `errors.py`: Implements the `Result[T]` pattern for functional error handling.
*   **`infrastructure/`**: Implementations of domain interfaces.
    *   `ocr/`: Tesseract wrapper.
    *   `llm/`: Google Gemini API client.
    *   `tts/`: Piper TTS wrapper (production) and Gemini TTS (placeholder).
*   **`application/`**: Application wiring, configuration, and context.
    *   `context/`: `ApplicationContext` (Dependency Injection).
    *   `config/`: `SystemConfig` loading from YAML.
    *   `services/`: Application services (e.g., `DocumentProcessingService`) that orchestrate domain logic.
*   **`tests/`**: Comprehensive test suite mirroring the architecture (`unit`, `integration`, `benchmarks`).

## Setup & Development

### Prerequisites
*   Python 3.9+
*   System dependencies: `tesseract-ocr`, `ffmpeg`

### Installation
1.  Create and activate a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Configure the application:
    ```bash
    cp config.example.yaml config.yaml
    # Edit config.yaml to add your Google AI API key (for text cleaning)
    ```

### Running the Application
```bash
python app.py
```
*   Access the UI at `http://localhost:5000`

### Testing
*   **Run all tests:** `python -m pytest`
*   **Unit tests only:** `python -m pytest tests/unit/`
*   **Integration tests:** `python -m pytest tests/integration/`
*   **Benchmarks:** `python -m pytest tests/benchmarks/`

### Code Quality Commands
*   **Lint & Fix:** `ruff check . --fix`
*   **Format:** `ruff format .`
*   **Type Check:** `mypy .`
*   **Security Scan:** `bandit -c pyproject.toml -r .`

## Development Conventions

*   **Error Handling:** Use the `Result[T]` pattern (from `domain.errors`) instead of raising exceptions for business logic failures. Return `Result.success(val)` or `Result.failure(error)`.
*   **Dependency Injection:** All services are registered in `ServiceContainer` and accessed via `ApplicationContext`. Do not instantiate service classes directly in routes.
*   **Configuration:** Access configuration via `context.config`. Do not read environment variables or files directly in business logic.
*   **Docstrings:** Google style docstrings are required.
*   **Type Hints:** Strict typing is enforced (`mypy --strict`).
*   **Imports:** Sorted using `isort` (enforced by `ruff`).

## Directory Structure
```
/
├── application/       # Config, Logging, Context
├── domain/            # Interfaces, Models, Core Engines (Pure Python)
├── infrastructure/    # External adapters (Piper, Gemini, Tesseract)
├── static/            # JS/CSS assets
├── templates/         # HTML templates
├── tests/             # Unit, Integration, and Benchmark tests
├── app.py             # Entry point
├── config.yaml        # Main configuration
└── pyproject.toml     # Build & Tool configuration
```
