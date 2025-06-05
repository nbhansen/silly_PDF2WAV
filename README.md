# Nicolais silly PDF to Audio Converter with OCR and LLM Cleaning
![2e849eb9bba1dafe](https://github.com/user-attachments/assets/46f8cfeb-53b1-408a-9aff-e850794af5b2)

I always wanted to listen to academic papers in my car and now I can, sorta not the best but here we are. Sure I could use a PDF-read-aloud thing, but academic papers are full of weird crud that distracts the everliving mother out of me. 

This web application processes PDF documents by:
1.  Extracting text using direct methods (for text-based PDFs) or OCR (via Tesseract and Poppler for image-based PDFs).
2.  Cleaning the extracted text using Google's Gemini Pro LLM via the Google AI API.
3.  Generating an audio version of the cleaned text using Coqui TTS (as default) for natural-sounding speech (or gTTS if you have a weak system, or Bark if you are rich)

The application is built with Flask and provides a simple web interface for uploading PDFs and listening to/downloading the generated audio. 

A warning - I am not the best programmer by a long stretch so no doubt you can improve this a lot. And probably a lot of alternatives are already out there. I dont care this is what a hobby project should look like BUT some personal caveats:

- only tested this on Fedora Linux (my love <3) and Linux Mint though the instructions for installation below I tried to make as general as possible for windows, mac and debian-brand linuxes as well. If you know your way a system hopefully you can translate that. I used pip and a virtual environment though, so it SHOULD work kinda fine on other platforms but sometimes a package is called something different on windows or Mac compared to Linux. Sorry.
- You will need some sorta google gemini api access. Or you can just rawdog it without entering anything into the field for that in app.py in which case the app will happily proceed and just generate audio including all the horrifying artefacts that are in the pdf format. Writing a new tts_utils.py module that allows you to use different AI apis should be trivial. If you would like that, lemme know. 
- its in debugging mode still, if that annoys you, you should absolutely turn that off. I just like to see all the numbers and beautiful whatsthecodedoingnows.
- its hilarious to think about someone training an AI on this <3
- I tried to make it somewhat modular but there are a few horrifying aspects around still. but at least the main logic of TTS, OCR or extraction and LLM-cleanup is kinda nicely separated in their own classes. Kinda. I mean, there should really be a config file or something but honestly, this is a hobby project

## Features

* Handles both text-based and image-based PDFs.
* Prioritizes direct text extraction for speed; falls back to OCR.
* Utilizes Google Gemini Pro for advanced text cleaning (removal of headers, footers, artifacts, etc.).
* Generates natural-sounding speech using Coqui TTS (VITS model) - if thats too light, it also has support for Bark (requires a beefy gpu/cpu) or gTTS (lightweight but kinda crappy)
* Allows for GPU acceleration for Coqui TTS + Bark TTS if an NVIDIA GPU and CUDA are available. I have not looked into acceleration on AMD or Intel Arc though I would like to.
* Simple web interface for file upload and audio playbook/download.
* **Comprehensive test suite** for reliability and development confidence.

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
* **FFMPeg** thats great to have anyway, do it brother 

### Installation Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/nbhansen/silly_PDF2WAV
    cd silly_PDF2WAV
    ```

2.  **Create and activate a Python virtual environment (recommended a lot):**
    ```bash
    python3 -m venv venv 
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create and Configure the `.env` File**

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

# Allowed file extensions (comma-separated, wont work with anything but pdf tho)
ALLOWED_EXTENSIONS=pdf

# Google Gemini API Key
GOOGLE_AI_API_KEY=your_real_google_api_key_here

# TTS Engine selection: coqui, gtts, bark, or gemini
TTS_ENGINE=coqui

# Coqui TTS config (the default)
COQUI_MODEL_NAME=tts_models/en/ljspeech/vits
COQUI_USE_GPU_IF_AVAILABLE=True

# gTTS config (very slow but works)
GTTS_LANG=en
GTTS_TLD=co.uk

# Bark config (very fancy but very very very heavy)
BARK_USE_GPU_IF_AVAILABLE=True
BARK_USE_SMALL_MODELS=True
BARK_HISTORY_PROMPT=

# Gemini TTS config (cloud-based, high quality)
GEMINI_VOICE_NAME=Kore
GEMINI_STYLE_PROMPT=
```

**Important:**  
- Replace `your_real_google_api_key_here` with your actual Google Gemini API key.
- Do **not** commit your `.env` file to version control.

## Testing

Run the comprehensive test suite:
```bash
./run_tests.sh
```

Or manually:
```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

Tests cover:
- Configuration and TTS engine setup
- PDF text extraction and cleaning
- Audio generation and processing
- Error handling and edge cases
- Integration workflows

## Configuration

1.  **Google AI API Key (for LLM Text Cleaning):**
    * You need an API key from Google AI Studio ([https://aistudio.google.com/](https://aistudio.google.com/)).
    * Enter it into the .env file discussed above

2.  **TTS Engine Selection:**
    * **Coqui TTS** (default): High-quality, local processing. Models download automatically.
    * **gTTS**: Lightweight, cloud-based. Good for testing.
    * **Bark**: Highest quality, very resource-intensive.
    * **Gemini TTS**: Cloud-based, excellent quality, requires API key.

3.  **Coqui TTS Models:**
    * Use `tts --list-models` to see available models
    * Models cache in `~/.local/share/tts/`

## Running the Application

1.  Ensure your virtual environment is activated.
2.  Make sure all prerequisites are installed and configured (see above)
3.  Run the Flask application:
    ```bash
    python app.py
    ```
4.  Open your web browser and navigate to `http://127.0.0.1:5000/`.

## GPU Acceleration

* NVIDIA GPU + CUDA enables acceleration for Coqui TTS and Bark
* Check CUDA availability: `python -c "import torch; print(torch.cuda.is_available())"`
* The application shows GPU/CPU usage in console output

## File Structure
```
your_project_folder/
├── app.py               # Main Flask application
├── processors.py        # Main PDFProcessor orchestrator  
├── text_processing.py   # OCRExtractor and TextCleaner classes
├── audio_generation.py  # TTSGenerator class
├── tts_utils.py         # TTS engine implementations
├── tts_config.py        # Configuration system
├── templates/           # HTML templates
├── tests/               # Test suite
├── run_tests.sh         # Test runner script
├── uploads/             # For uploaded PDFs (auto-created)
├── audio_outputs/       # For generated audio (auto-created)
├── requirements.txt     # Python dependencies
└── .env                 # Environment configuration (create this)
```

## Troubleshooting

* **`TTSProcessor: Error initializing...`**: Check internet connection for model downloads, ensure espeak is installed
* **`OCRProcessor: Tesseract OCR engine not found...`**: Verify Tesseract installation and PATH
* **`pdf2image.exceptions...`**: Ensure Poppler utilities are installed and in PATH
* **Test failures**: Check that all dependencies are installed: `pip install -r requirements.txt`

## Known Issues / Future Enhancements

* TTS models may mispronounce uncommon words or acronyms
* Error handling could be more granular for web UI feedback
* Asynchronous task processing needed for long documents
* Status bars and UX improvements
* Support for other LLMs besides Gemini
* LaTeX input support (my dream feature!)

## My wacky idea that I really wanna do
Turn this thing into a sexy sexy LaTeX-->Voice beast, thus bypassing the stupid PDF-extract and also enabling people who write academic papers to provide a buttery-smooth audio version for their vision or neurodivergent friends.