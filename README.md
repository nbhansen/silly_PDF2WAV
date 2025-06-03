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
* **FFMPeg**thats great to have anyway, do it brother 

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

# TTS Engine selection: coqui, gtts, or bark
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
```

**Important:**  
- Replace `your_real_google_api_key_here` with your actual Google Gemini API key.
- Do **not** commit your `.env` file to version control.

## Configuration

1.  **Google AI API Key (for LLM Text Cleaning):**
    * You need an API key from Google AI Studio ([https://aistudio.google.com/](https://aistudio.google.com/)).
    * Enter it into the .env file discussed above

2.  **Coqui TTS Models:**
    * The application uses as default uses Coqui TTS models (e.g., `tts_models/en/vctk/vits`). These models will be downloaded automatically by the `TTS` library on the first run if they are not found in the local cache (`~/.local/share/tts/`). This requires an internet connection for the initial setup. 
    * Use tts --list-models to see and try out different models. 
    * If this is too heavy for you, change it to gtts and if you roll with a GIANT gpu, try changing it to Bark. 

3.  **(Optional and untested dragon territory PATHS ARE STUPID ON WINDOWS) Tesseract OCR Path (Windows):**
    * If Tesseract is not automatically found in your PATH on Windows, you might need to uncomment and set the path in `ocr_utils.py` within the `OCRProcessor` class:
        ```python
        # if tesseract_cmd:
        #     pytesseract.pytesseract.tesseract_cmd = tesseract_cmd 
        ```
        Set `tesseract_cmd` to your Tesseract executable path (e.g., `r'C:\Program Files\Tesseract-OCR\tesseract.exe'`).

## Running the Application

1.  Ensure your virtual environment is activated.
2.  Make sure all prerequisites are installed and configured (see above)
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

* The default Coqui TTS VCTK model might mispronounce certain uncommon words or acronyms. Experimenting with different Coqui TTS models or fine-tuning might be necessary for specific needs. Highly dependent on model but also on the outputted text
* Error handling could be more granular for user feedback in the web UI.
* Implement asynchronous task processing (e.g., with Celery) for long-running OCR/TTS tasks to prevent web request timeouts and improve user experience.
* Status bars and general UX... which would allow me to disable debug mode. I love seeing a good CLI-spam tho. 
* DEFINITELY some architectural changes to more gracefully and less spaghettily handle for instance: Other LLMs than Gemini (local when??), API TTS for that smooth sexy in the cloud voice
* tests which i dont know the first thing about but am very keen to learn about

## My wacky idea that I really wanna do
Turn this thing into a sexy sexy LaTeX-->Voice beast, thus bypassing the stupid PDF-extract and also enabling people who write academic paper to provide a buttery-smooth audio version for their vision or neurodivergent friends. 

