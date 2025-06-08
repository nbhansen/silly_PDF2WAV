# Silly PDF2WAV – Simplified Architecture Diagram

```mermaid
flowchart TD
  %% NODE DEFINITIONS
  UI["Web UI<br/>(Flask Templates)"]
  APP["Flask App<br/>(app.py)"]
  APP_SERVICE["Application Layer<br/>(pdf_processing.py)"]
  OCR["OCR Provider<br/>(Tesseract)"]
  PDFPLUMBER["PDF Text Extraction<br/>(pdfplumber)"]
  LLM["LLM Provider<br/>(Gemini LLM)"]
  TTS["TTS Providers<br/>(Coqui, gTTS, Bark, Gemini TTS)"]
  AUDIO["audio_outputs/<br/>(output files)"]
  UPLOADS["uploads/<br/>(uploaded PDFs)"]
  MODELS["Domain Models &<br/>Data Classes"]
  DOMAIN_SERVICES["Domain Services<br/>(Business Logic)"]

  %% SUBGRAPHS
  subgraph UI_LAYER["UI Layer"]
    UI
  end

  subgraph APP_LAYER["Application Layer"]
    APP
    APP_SERVICE
  end

  subgraph DOMAIN_LAYER["Domain Layer"]
    MODELS
    DOMAIN_SERVICES
  end

  subgraph INFRA_LAYER["Infrastructure Layer"]
    OCR
    PDFPLUMBER
    LLM
    TTS
  end

  %% FLOWS
  UI -->|User uploads PDF| APP
  APP -->|Process PDF| APP_SERVICE

  APP_SERVICE -->|PDF Extraction| OCR
  APP_SERVICE -->|Text Extraction| PDFPLUMBER
  APP_SERVICE -->|Text Cleaning| LLM
  APP_SERVICE -->|Generate Audio| TTS

  APP_SERVICE --> DOMAIN_SERVICES
  DOMAIN_SERVICES --> MODELS

  APP -->|Serve Audio| AUDIO
  APP -->|Store Uploads| UPLOADS

  %% COLORS
  style UI_LAYER fill:#e5f5fd,stroke:#82c0e9,stroke-width:2px
  style APP_LAYER fill:#fff9e5,stroke:#ffd966,stroke-width:2px
  style DOMAIN_LAYER fill:#e6f9e5,stroke:#82e982,stroke-width:2px
  style INFRA_LAYER fill:#f5e5fa,stroke:#c082e9,stroke-width:2px

  style UI fill:#b8daff
  style APP fill:#ffe699
  style APP_SERVICE fill:#ffe699
  style DOMAIN_SERVICES fill:#b6fcd5
  style MODELS fill:#b6fcd5
  style OCR fill:#e0c3fc
  style PDFPLUMBER fill:#e0c3fc
  style LLM fill:#e0c3fc
  style TTS fill:#e0c3fc
  style AUDIO fill:#fff3cd
  style UPLOADS fill:#fff3cd
```

## Key Layers

- **UI:** Web interface for uploading PDFs and playing audio.
- **Application Layer:** Orchestrates PDF processing, calls domain logic and infrastructure.
- **Domain Layer:** Contains pure business rules, models, and service definitions.
- **Infrastructure Layer:** Integrations with external services (Tesseract OCR, LLMs, TTS engines).
- **Uploads/Audio:** File storage for user uploads and generated audio.

## Main Flow

1. User uploads a PDF via the web UI.
2. `app.py` (Flask) receives the upload and hands PDF to the application service.
3. Application layer uses:
    - OCR (Tesseract) or PDF text extraction
    - LLM (Gemini) for text cleaning
    - TTS providers for audio generation
4. The cleaned audio file is saved and made available for download/playback.