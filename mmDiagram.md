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

  %% SUBGRAPH COLORS (light backgrounds)
  style UI_LAYER fill:#fff,stroke:#82c0e9,stroke-width:2px,color:#111
  style APP_LAYER fill:#fff,stroke:#ffd966,stroke-width:2px,color:#111
  style DOMAIN_LAYER fill:#fff,stroke:#82e982,stroke-width:2px,color:#111
  style INFRA_LAYER fill:#fff,stroke:#c082e9,stroke-width:2px,color:#111

  %% NODE COLORS (light, with black text)
  style UI fill:#e3f2fd,stroke:#90caf9,stroke-width:2px,color:#111
  style APP fill:#fffde7,stroke:#ffe082,stroke-width:2px,color:#111
  style APP_SERVICE fill:#fffde7,stroke:#ffe082,stroke-width:2px,color:#111
  style DOMAIN_SERVICES fill:#e8f5e9,stroke:#81c784,stroke-width:2px,color:#111
  style MODELS fill:#e8f5e9,stroke:#81c784,stroke-width:2px,color:#111
  style OCR fill:#f3e5f5,stroke:#ba68c8,stroke-width:2px,color:#111
  style PDFPLUMBER fill:#f3e5f5,stroke:#ba68c8,stroke-width:2px,color:#111
  style LLM fill:#f3e5f5,stroke:#ba68c8,stroke-width:2px,color:#111
  style TTS fill:#f3e5f5,stroke:#ba68c8,stroke-width:2px,color:#111
  style AUDIO fill:#f5f5f5,stroke:#bdbdbd,stroke-width:2px,color:#111
  style UPLOADS fill:#f5f5f5,stroke:#bdbdbd,stroke-width:2px,color:#111
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