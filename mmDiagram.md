# Silly PDF2WAV – Simplified Architecture Diagram

```mermaid
flowchart TD
    UI[Web UI (Flask Templates)] -->|User uploads PDF| APP[Flask App (app.py)]
    APP -->|Process PDF| APP_SERVICE[Application Layer (pdf_processing.py)]
    APP_SERVICE -->|PDF Extraction| OCR[OCR Provider (Tesseract)]
    APP_SERVICE -->|Text Extraction| PDFPLUMBER[PDFPlumber]
    APP_SERVICE -->|Text Cleaning| LLM[LLM Provider (Gemini LLM)]
    APP_SERVICE -->|Generate Audio| TTS[TTS Providers (Coqui, gTTS, Bark, Gemini TTS)]
    
    subgraph Domain Layer
        MODELS[Models & Data Classes]
        DOMAIN_SERVICES[Business Logic Services]
    end
    APP_SERVICE --> DOMAIN_SERVICES
    DOMAIN_SERVICES --> MODELS

    subgraph Infrastructure Layer
        OCR
        LLM
        TTS
    end

    APP -->|Serve Audio| AUDIO[(audio_outputs/)]
    APP -->|Store Uploads| UPLOADS[(uploads/)]
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