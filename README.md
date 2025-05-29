# Nicolais silly PDF to Audio Converter with OCR and LLM Cleaning
![2e849eb9bba1dafe](https://github.com/user-attachments/assets/46f8cfeb-53b1-408a-9aff-e850794af5b2)


I always wanted to listen to academic papers in my car and now I can, sorta shittyly but here we are. 

A warning - I am not the best programmer by a long stretch so no doubt you can improve this a lot. And probably a lot of alternatives are already out there. I dont care this is what a hobby project should look like BUT some personal caveats:

- only tested this on Fedora Linux (my love <3) though the instructions for installation below I tried to make as general as possible for windows, mac and debian-brand linuxes. If you know your way around linux hopefully you can translate that.
- You will need some sorta google gemini api access. Or you can just rawdog it without entering anything into the field for that in app.py in which case the app will happily proceed and just generate audio including all the horrifying artefacts that are in the pdf format. Writing a new tts_utils.py module that allows you to use different AI apis should be trivial. If you would like that, lemme know. 
- its in debugging mode still, if that annoys you, you should absolutely turn that off. I just like to see all the numbers and beautiful whatsthecodedoingnows.
- its hilarious to think about someone training an AI on this <3
- I tried to make it somewhat modular but there are a few horrifying aspects around still. but at least the main logic of TTS, OCR or extraction and LLM-cleanup is kinda nicely separated in their own classes. Kinda. I mean, there should really be a config file or something but honestly, this is a hobby project

This web application processes PDF documents by:
1.  Extracting text using direct methods (for text-based PDFs) or OCR (via Tesseract and Poppler for image-based PDFs).
2.  Cleaning the extracted text using Google's Gemini Pro LLM via the Google AI API.
3.  Generating an audio version of the cleaned text using Coqui TTS (as default) for natural-sounding speech.

The application is built with Flask and provides a simple web interface for uploading PDFs and listening to/downloading the generated audio.

## Features

* Handles both text-based and image-based PDFs.
* Prioritizes direct text extraction for speed; falls back to OCR.
* Utilizes Google Gemini Pro for advanced text cleaning (removal of headers, footers, artifacts, etc.).
* Generates natural-sounding speech using Coqui TTS (VITS model) - if thats too light, it also has support for Bark (requires a beefy gpu/cpu) or gTTS (lightweight but kinda crappy)
* Allows for GPU acceleration for Coqui TTS + Bark TTS if an NVIDIA GPU and CUDA are available. I have not looked into acceleration on AMD or Intel Arc though I would like to.
* Simple web interface for file upload and audio playback/download.

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

### Installation Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/nbhansen/silly_PDF2WAV
    cd silly_PDF2WAV
    ```

2.  **Create and activate a Python virtual environment:**
    ```bash
    python3 -m venv venv 
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Google AI API Key (for LLM Text Cleaning):**
    * You need an API key from Google AI Studio ([https://aistudio.google.com/](https://aistudio.google.com/)).
    * Open the `app.py` file (or `llm_utils.py` if configuration is moved there).
    * Find the line: `GOOGLE_AI_API_KEY = "YOUR_GOOGLE_AI_API_KEY"`
    * Replace `"YOUR_GOOGLE_AI_API_KEY"` with your actual API key (ensure it's a string, enclosed in quotes).
    * **Note:** For production or more secure setups, it's highly recommended to set this key as an environment variable instead of hardcoding it.

2.  **Coqui TTS Models:**
    * The application uses as default uses Coqui TTS models (e.g., `tts_models/en/vctk/vits`). These models will be downloaded automatically by the `TTS` library on the first run if they are not found in the local cache (`~/.local/share/tts/`). This requires an internet connection for the initial setup. If this is too heavy for you, change it to gtts and if you roll with a GIANT gpu, try changing it to Bark. 

3.  **(Optional) Tesseract OCR Path (Windows):**
    * If Tesseract is not automatically found in your PATH on Windows, you might need to uncomment and set the path in `ocr_utils.py` within the `OCRProcessor` class:
        ```python
        # if tesseract_cmd:
        #     pytesseract.pytesseract.tesseract_cmd = tesseract_cmd 
        ```
        Set `tesseract_cmd` to your Tesseract executable path (e.g., `r'C:\Program Files\Tesseract-OCR\tesseract.exe'`).

## Running the Application

1.  Ensure your virtual environment is activated.
2.  Make sure all prerequisites are installed and configured.
3.  Run the Flask application:
    ```bash
    python app.py
    ```
4.  Open your web browser and navigate to `http://127.0.0.1:5000/`.

## GPU Acceleration for Coqui TTS

* If you have an NVIDIA GPU and have correctly installed NVIDIA drivers, CUDA, and a CUDA-enabled version of PyTorch, GPU acceleration for Coqui TTS will be attempted by default.
* You can verify your PyTorch CUDA setup by running:
    ```python
    import torch
    print(torch.cuda.is_available())
    ```
* The application will print messages to the console indicating whether it's using CPU or GPU for TTS.

## File Structure
your_project_folder/
├── app.py               # Main Flask application file
├── processors.py        # Main PDFProcessor orchestrator  
├── text_processing.py   # OCRExtractor and TextCleaner classes
├── audio_generation.py  # TTSGenerator class
├── tts_utils.py         # TTS engine implementations
├── templates/
│   └── index.html
├── uploads/             # For uploaded PDFs (gitignored by default app will create a new one)
├── audio_outputs/       # For generated audio (gitignored by default app will create a new one)
├── requirements.txt     # Python dependencies
├── README.md            # This file
└── .gitignore           # Specifies intentionally untracked files

## Troubleshooting

* **`TTSProcessor: Error initializing Coqui TTS model...`**:
    * Ensure you have an internet connection for the first run to download models.
    * Make sure `espeak` or `espeak-ng` (dependent on your OS) is installed and accessible.
    * Check for any specific error messages related to PyTorch or CUDA if GPU is enabled.
* **`OCRProcessor: Tesseract OCR engine not found...`**:
    * Verify Tesseract is installed and its installation directory is in your system's PATH.
    * On Windows, consider setting `pytesseract.tesseract_cmd` as mentioned in Configuration.
* **`pdf2image.exceptions...` errors**:
    * Ensure Poppler utilities are installed and in your system's PATH.

## Known Issues / Future Enhancements

* The default Coqui TTS VCTK model might mispronounce certain uncommon words or acronyms. Experimenting with different Coqui TTS models or fine-tuning might be necessary for specific needs. 
* Error handling could be more granular for user feedback in the web UI.
* Consider moving API keys and sensitive configurations to environment variables for better security. Please do not throw this on your website or whatever and allow people to jack your google api key.
* Implement asynchronous task processing (e.g., with Celery) for long-running OCR/TTS tasks to prevent web request timeouts and improve user experience.

