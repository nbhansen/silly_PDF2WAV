import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import html

# Import the refactored processors and the factory
from ocr_utils import OCRProcessor
from llm_utils import LLMProcessor 
from tts_utils import get_tts_processor

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = 'audio_outputs'
ALLOWED_EXTENSIONS = {'pdf'}
# !! IMPORTANT !! Replace "YOUR_GOOGLE_AI_API_KEY" with your actual API key STRING (in quotes).
GOOGLE_AI_API_KEY = "AIzaSyC_rDGDvSE6s" 
# This global variable will be set based on TTS_ENGINE_KWARGS or default in __main__
# It's used for display purposes in the HTML template.
SELECTED_TTS_ENGINE = "TTS" # Default placeholder

# --- TTS Engine Configuration ---
# Choose your desired TTS engine: "coqui", "gtts", or "bark" (when implemented)
# This configuration will be used when initializing tts_processor
_SELECTED_TTS_ENGINE_CONFIG = "coqui" # Or "gtts", "coqui"
TTS_ENGINE_KWARGS = {}

if _SELECTED_TTS_ENGINE_CONFIG.lower() == "coqui":
    TTS_ENGINE_KWARGS = {
        "model_name": "tts_models/en/vctk/vits", 
        "use_gpu_if_available": True,
        "speaker_idx_to_use": None 
    }
    SELECTED_TTS_ENGINE = "Coqui TTS" # More descriptive name
elif _SELECTED_TTS_ENGINE_CONFIG.lower() == "gtts":
    TTS_ENGINE_KWARGS = {
        "lang": "en",
        "tld": "co.uk"
    }
    SELECTED_TTS_ENGINE = "gTTS"
elif _SELECTED_TTS_ENGINE_CONFIG.lower() == "bark": 
    TTS_ENGINE_KWARGS = {
        "use_gpu_if_available": True,
        "use_small_models": True, 
        "history_prompt": None    
    }
    SELECTED_TTS_ENGINE = "Bark"
else:
    print(f"Warning: Unknown TTS engine '{_SELECTED_TTS_ENGINE_CONFIG}' configured. TTS might not work as expected.")
    SELECTED_TTS_ENGINE = _SELECTED_TTS_ENGINE_CONFIG.upper() if _SELECTED_TTS_ENGINE_CONFIG else "TTS"


# --- Flask App Setup ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['AUDIO_FOLDER'] = AUDIO_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Initialize Processors
print("Initializing processors...")
ocr_processor = OCRProcessor() 
llm_processor = LLMProcessor(api_key=GOOGLE_AI_API_KEY) 

# Initialize TTSProcessor using the factory
tts_processor = get_tts_processor(engine_name=_SELECTED_TTS_ENGINE_CONFIG, **TTS_ENGINE_KWARGS)

if tts_processor is None:
    print(f"CRITICAL: TTS Processor for '{_SELECTED_TTS_ENGINE_CONFIG}' could not be initialized. Audio generation will fail.")
    # Update SELECTED_TTS_ENGINE to reflect failure for display
    SELECTED_TTS_ENGINE = f"{_SELECTED_TTS_ENGINE_CONFIG.upper()} (Failed to Load)"
else:
    print(f"Successfully initialized TTS Processor: {tts_processor.__class__.__name__}")
    # Update SELECTED_TTS_ENGINE based on the actual class name if it was a fallback or for consistency
    if "CoquiTTSProcessor" in tts_processor.__class__.__name__:
        SELECTED_TTS_ENGINE = "Coqui TTS"
    elif "GTTSProcessor" in tts_processor.__class__.__name__:
        SELECTED_TTS_ENGINE = "gTTS"
    elif "BarkTTSProcessor" in tts_processor.__class__.__name__:
        SELECTED_TTS_ENGINE = "Bark"


print("Processors initialized.")


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/audio_outputs/<filename>')
def serve_audio(filename):
    return send_from_directory(app.config['AUDIO_FOLDER'], filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    # Use the globally set SELECTED_TTS_ENGINE for display purposes
    # The actual tts_processor object handles the functionality
    current_tts_engine_display_name = SELECTED_TTS_ENGINE 

    if tts_processor is None: 
        return f"Error: Text-to-Speech engine ({current_tts_engine_display_name}) is not available. Please check server logs."

    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return "No file part in the request."
        file = request.files['pdf_file']
        if file.filename == '':
            return "No file selected."
        
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            base_filename_no_ext = os.path.splitext(original_filename)[0]
            
            # Save uploaded file
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
            file.save(pdf_path)
            
            # Process PDF: OCR -> LLM -> TTS
            print(f"Processing PDF: {original_filename}")
            
            # Step 1: Extract text using OCR
            extracted_text = ocr_processor.extract_text_from_pdf(pdf_path)
            
            # Step 2: Clean text using LLM
            cleaned_text = llm_processor.clean_text(extracted_text)
            
            # Step 3: Generate audio using TTS
            audio_filename = tts_processor.generate_audio_file(
                cleaned_text, 
                base_filename_no_ext, 
                app.config['AUDIO_FOLDER']
            )
            
            if audio_filename:
                # Clean up uploaded PDF
                try:
                    os.remove(pdf_path)
                except:
                    pass
                
                return render_template('result.html', 
                                     audio_file=audio_filename,
                                     original_filename=original_filename,
                                     tts_engine=current_tts_engine_display_name)
            else:
                return "Error: Failed to generate audio file."
        else:
            return "Invalid file type. Please upload a PDF file."
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    print("Starting Flask development server...")
    app.run(debug=True, host='0.0.0.0', port=5000)