# processors.py
from dataclasses import dataclass
from typing import Optional, Dict, Any
import os

from text_processing import OCRExtractor, TextCleaner
from audio_generation import TTSGenerator

@dataclass
class ProcessingResult:
    success: bool
    audio_path: Optional[str] = None
    error: Optional[str] = None
    debug_info: Optional[Dict[str, Any]] = None

class PDFProcessor:
    """Main processor that orchestrates PDF to audio conversion"""
    
    def __init__(self, google_api_key: str, tts_engine: str = "coqui", tts_config: Dict = None):
        print("PDFProcessor: Initializing components...")
        self.ocr = OCRExtractor()
        self.cleaner = TextCleaner(google_api_key)
        self.tts = TTSGenerator(tts_engine, tts_config or {})
        print("PDFProcessor: Initialization complete")
        
    def process_pdf(self, pdf_path: str, output_name: str) -> ProcessingResult:
        """Process a PDF file through the complete pipeline"""
        try:
            # Check if file exists
            if not os.path.exists(pdf_path):
                return ProcessingResult(success=False, error=f"File not found: {pdf_path}")
            
            print(f"PDFProcessor: Starting processing of {pdf_path}")
            
            # Step 1: Extract text
            print("PDFProcessor: Step 1 - Extracting text")
            raw_text = self.ocr.extract(pdf_path)
            if not raw_text or raw_text.startswith("Error"):
                return ProcessingResult(success=False, error=f"OCR failed: {raw_text}")
            
            # Step 2: Clean text  
            print("PDFProcessor: Step 2 - Cleaning text")
            clean_text = self.cleaner.clean(raw_text)
            if not clean_text:
                return ProcessingResult(success=False, error="Text cleaning failed")
            
            # Step 3: Generate audio
            print("PDFProcessor: Step 3 - Generating audio")
            audio_path = self.tts.generate(clean_text, output_name)
            if not audio_path:
                return ProcessingResult(success=False, error="TTS generation failed")
                
            print("PDFProcessor: Processing complete!")
            return ProcessingResult(
                success=True, 
                audio_path=audio_path,
                debug_info={
                    "raw_text_length": len(raw_text),
                    "clean_text_length": len(clean_text),
                    "tts_engine": self.tts.engine_name
                }
            )
            
        except Exception as e:
            print(f"PDFProcessor: Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return ProcessingResult(success=False, error=str(e))