# processors.py
from dataclasses import dataclass
from typing import Optional, Dict, Any, List  # Add List import
import os

from text_processing import OCRExtractor, TextCleaner
from audio_generation import TTSGenerator

@dataclass
class ProcessingResult:
    success: bool
    audio_files: Optional[List[str]] = None  # List of audio files
    audio_path: Optional[str] = None  # Keep for backward compatibility
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
            raw_text = self.ocr._extract_direct(pdf_path)  # Use correct method name
            if not raw_text or raw_text.startswith("Error"):
                return ProcessingResult(success=False, error=f"OCR failed: {raw_text}")
            
            # Step 2: Clean text (now returns list of chunks)
            print("PDFProcessor: Step 2 - Cleaning text")
            clean_text_chunks = self.cleaner.clean(raw_text)  # This should return List[str]
            if not clean_text_chunks:
                return ProcessingResult(success=False, error="Text cleaning failed")
            
            # Step 3: Generate audio files (one per chunk)
            print("PDFProcessor: Step 3 - Generating audio files")
            if len(clean_text_chunks) == 1:
                # Single chunk - use original method
                audio_file = self.tts.generate(clean_text_chunks[0], output_name)
                audio_files = [audio_file] if audio_file else []
            else:
                # Multiple chunks - generate separate files
                audio_files = self.tts.generate_from_chunks(clean_text_chunks, output_name)
            
            if not audio_files:
                return ProcessingResult(success=False, error="TTS generation failed")
                
            print(f"PDFProcessor: Processing complete! Generated {len(audio_files)} audio files")
            return ProcessingResult(
                success=True, 
                audio_files=audio_files,
                audio_path=audio_files[0] if audio_files else None,  # First file for compatibility
                debug_info={
                    "raw_text_length": len(raw_text),
                    "text_chunks_count": len(clean_text_chunks),
                    "audio_files_count": len(audio_files),
                    "tts_engine": self.tts.engine_name
                }
            )
            
        except Exception as e:
            print(f"PDFProcessor: Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return ProcessingResult(success=False, error=str(e))