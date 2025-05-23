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
GOOGLE_AI_API_KEY = "YOUR_GOOGLE_AI_API_KEY"  # Set to None if not using LLM features

# --- TTS Engine Configuration ---
# Choose your desired TTS engine: "coqui", "gtts", or "bark"
SELECTED_TTS_ENGINE = "coqui" 
TTS_ENGINE_KWARGS = {}

if SELECTED_TTS_ENGINE.lower() == "coqui":
    TTS_ENGINE_KWARGS = {
        "model_name": "tts_models/en/vctk/vits", 
        "use_gpu_if_available": True,
        "speaker_idx_to_use": None 
    }
elif SELECTED_TTS_ENGINE.lower() == "gtts":
    TTS_ENGINE_KWARGS = {
        "lang": "en",
        "tld": "co.uk"
    }
elif SELECTED_TTS_ENGINE.lower() == "bark": 
    TTS_ENGINE_KWARGS = {
        "use_gpu_if_available": False,
        "use_small_models": True, # <<< CHANGED TO True to address OOM
        "history_prompt": None    
    }


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

tts_processor = get_tts_processor(engine_name=SELECTED_TTS_ENGINE, **TTS_ENGINE_KWARGS)
if tts_processor is None:
    print("CRITICAL: TTS Processor could not be initialized. Audio generation will fail.")
else:
    print(f"Successfully initialized TTS Processor: {tts_processor.__class__.__name__}")

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
    if tts_processor is None: 
        return "Error: Text-to-Speech engine is not available. Please check server logs."

    if request.method == 'POST':
        # ... (file handling logic remains the same) ...
        if 'pdf_file' not in request.files:
            return "No file part in the request."
        file = request.files['pdf_file']
        if file.filename == '':
            return "No file selected."
        
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            base_filename = os.path.splitext(original_filename)[0]
            
            upload_filepath = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
            try:
                file.save(upload_filepath)
                print(f"File saved: {upload_filepath}")
            except Exception as e:
                print(f"Error saving file: {e}")
                return f"Error saving file: {str(e)}"

            extracted_text_ocr = ocr_processor.extract_text_from_pdf(upload_filepath)
            cleaned_text_llm = llm_processor.clean_text(extracted_text_ocr)
            
            audio_filename = None 
            if cleaned_text_llm and \
               not cleaned_text_llm.startswith("Error:") and \
               not cleaned_text_llm.startswith("LLM cleaning skipped") and \
               not cleaned_text_llm.startswith("Could not convert") and \
               not cleaned_text_llm.startswith("No text could be extracted"):
                audio_filename = tts_processor.generate_audio_file(
                    cleaned_text_llm, 
                    base_filename, 
                    app.config['AUDIO_FOLDER']
                )
            
            audio_section_html = ""
            output_extension = tts_processor.get_output_extension() if tts_processor else "unknown"
            audio_mime_type = "audio/wav" if output_extension == "wav" else "audio/mpeg" 

            if audio_filename:
                audio_url = url_for('serve_audio', filename=audio_filename)
                audio_section_html = f"""
                <div class="content-section">
                    <h2>Generated Audio ({SELECTED_TTS_ENGINE.upper()})</h2>
                    <audio controls src="{audio_url}" type="{audio_mime_type}">
                        Your browser does not support the audio element.
                    </audio>
                    <p style="margin-top: 10px; text-align: center;">
                        <a href="{audio_url}" download="{html.escape(audio_filename)}" class="button">Download Audio File (.{output_extension})</a>
                    </p>
                </div>"""
            else:
                audio_section_html = f"""
                <div class="content-section">
                    <h2>Audio Generation ({SELECTED_TTS_ENGINE.upper()})</h2>
                    <p>Audio could not be generated or was skipped (e.g., due to issues in OCR or LLM steps, or empty text).</p>
                </div>"""
            
            # ... (HTML rendering remains the same) ...
            return f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Processing Result for {html.escape(original_filename)}</title>
                <style>
                    body {{ 
                        font-family: Arial, sans-serif; 
                        margin: 0; 
                        padding: 0; 
                        background-color: #222222; 
                        color: #FFFF00; 
                        line-height: 1.6;
                    }}
                    .main-container {{ 
                        display: flex; 
                        flex-direction: column; 
                        align-items: center; 
                        padding: 20px; 
                    }}
                    .content-section {{ 
                        background-color: #333333; 
                        border: 1px solid #FFD700; 
                        color: #FFFF00; 
                        padding: 20px; 
                        border-radius: 8px; 
                        box-shadow: 0 0 15px rgba(255, 255, 0, 0.1); 
                        margin-bottom: 20px; 
                        width: 90%; 
                        max-width: 800px; 
                    }}
                    h1 {{ 
                        color: #FFFF00; 
                        border-bottom: 2px solid #FFD700; 
                        padding-bottom: 10px; 
                        text-align: center; 
                    }}
                    h2 {{ 
                        color: #FFFF00; 
                        margin-top: 0; 
                    }}
                    pre {{ 
                        white-space: pre-wrap; 
                        word-wrap: break-word; 
                        background-color: #1c1c1c; 
                        border: 1px solid #FFD700; 
                        padding: 15px; 
                        border-radius: 5px; 
                        font-size: 0.95em; 
                        max-height: 30vh; 
                        overflow-y: auto;
                        color: #FFFFE0; 
                    }}
                    audio {{ 
                        width: 100%; 
                        margin-top: 15px; 
                        border-radius: 5px; 
                    }}
                    audio::-webkit-media-controls-panel {{
                        background-color: #333333;
                        border-radius: 5px;
                    }}
                    audio::-webkit-media-controls-play-button,
                    audio::-webkit-media-controls-volume-slider,
                    audio::-webkit-media-controls-mute-button,
                    audio::-webkit-media-controls-timeline,
                    audio::-webkit-media-controls-current-time-display,
                    audio::-webkit-media-controls-time-remaining-display {{
                        filter: invert(1) sepia(1) saturate(5) hue-rotate(30deg);
                    }}

                    a.button {{ 
                        display: inline-block; 
                        padding: 10px 15px; 
                        background-color: #FFD700; 
                        color: #222222; 
                        text-decoration: none; 
                        border-radius: 5px; 
                        transition: background-color 0.3s ease; 
                        font-size: 0.9em; 
                        font-weight: bold;
                        border: 1px solid #FFFF00;
                    }}
                    a.button:hover {{ 
                        background-color: #FFFF00; 
                        color: #111111;
                    }}
                </style>
            </head>
            <body>
                <div class="main-container">
                    <h1>Result for {html.escape(original_filename)}</h1>
                    {audio_section_html}
                    <div class="content-section">
                        <h2>Cleaned Text (LLM)</h2>
                        <pre>{html.escape(cleaned_text_llm)}</pre>
                    </div>
                    <div class="content-section">
                        <h2>Original Extracted Text (OCR/Direct)</h2>
                        <pre>{html.escape(extracted_text_ocr)}</pre>
                    </div>
                    <p style="text-align:center;"><a href="{url_for('index')}" class="button">Upload Another File</a></p>
                </div>
            </body>
            </html>
            """
        else:
            return "Invalid file type."
    return redirect(url_for('index'))

# --- Main Execution Point ---
if __name__ == '__main__':
    if GOOGLE_AI_API_KEY == "YOUR_GOOGLE_AI_API_KEY" or GOOGLE_AI_API_KEY.strip() == "":
        print("\n" + "="*50)
        print("WARNING: GOOGLE_AI_API_KEY for Gemini is not set or is empty.")
        print("LLM features will not work.")
        print("="*50 + "\n")

    print("Starting Flask app...")
    app.run(debug=True, host='0.0.0.0', port=5000)
