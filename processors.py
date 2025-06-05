# processors.py - Updated with MP3 combination support
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import os

from text_processing import OCRExtractor, TextCleaner
from audio_generation import TTSGenerator
from tts_config import TTSConfig

@dataclass
class ProcessingResult:
    success: bool
    audio_files: Optional[List[str]] = None  # List of individual audio files
    combined_mp3_file: Optional[str] = None  # Combined MP3 file
    audio_path: Optional[str] = None  # Keep for backward compatibility
    error: Optional[str] = None
    debug_info: Optional[Dict[str, Any]] = None

class PDFProcessor:
    """Main processor that orchestrates PDF to audio conversion with MP3 combination"""
    
    def __init__(self, google_api_key: str, tts_engine: str = "coqui", tts_config: TTSConfig = None):
        print("PDFProcessor: Initializing components...")
        self.ocr = OCRExtractor()
        self.cleaner = TextCleaner(google_api_key)
        self.tts = TTSGenerator(tts_engine, tts_config or TTSConfig())
        print("PDFProcessor: Initialization complete")
        
    def process_pdf(self, pdf_path: str, output_name: str, start_page: int = None, end_page: int = None) -> ProcessingResult:
        """Process a PDF file through the complete pipeline with optional page range"""
        try:
            # Check if file exists
            if not os.path.exists(pdf_path):
                return ProcessingResult(success=False, error=f"File not found: {pdf_path}")
            
            # Build page range info for logging
            if start_page is not None or end_page is not None:
                page_info = f" (pages {start_page or 1}-{end_page or 'end'})"
            else:
                page_info = ""
            
            print(f"PDFProcessor: Starting processing of {pdf_path}{page_info}")
            
            # Step 1: Extract text with page range
            print("PDFProcessor: Step 1 - Extracting text")
            raw_text = self.ocr.extract(pdf_path, start_page, end_page)
            
            if not raw_text or raw_text.startswith("Error"):
                return ProcessingResult(success=False, error=f"Text extraction failed: {raw_text}")
            
            print(f"PDFProcessor: Extracted {len(raw_text):,} characters from PDF{page_info}")
            
            # Step 2: Clean text (now returns list of chunks)
            print("PDFProcessor: Step 2 - Cleaning text")
            clean_text_chunks = self.cleaner.clean(raw_text)
            
            if not clean_text_chunks:
                return ProcessingResult(success=False, error="Text cleaning failed - no output from cleaner")
            
            # Filter out empty chunks
            clean_text_chunks = [chunk for chunk in clean_text_chunks if chunk.strip()]
            
            if not clean_text_chunks:
                return ProcessingResult(success=False, error="Text cleaning resulted in empty content")
            
            print(f"PDFProcessor: Text cleaning produced {len(clean_text_chunks)} chunks")
            
            # Step 3: Generate audio files with MP3 combination
            print("PDFProcessor: Step 3 - Generating audio files")
            
            # ALWAYS try to create MP3, even for single chunks
            audio_files, combined_mp3 = self.tts.generate_from_chunks(
                clean_text_chunks, 
                output_name,
                create_combined_mp3=True  # Always try to create MP3
            )
            
            if not audio_files:
                return ProcessingResult(success=False, error="TTS generation failed - no audio files produced")
                
            print(f"PDFProcessor: Processing complete! Generated {len(audio_files)} audio files")
            if combined_mp3:
                print(f"PDFProcessor: Created combined MP3: {combined_mp3}")
            else:
                print("PDFProcessor: No combined MP3 created (FFmpeg may not be available or single chunk)")
            
            # Build debug info
            debug_info = {
                "raw_text_length": len(raw_text),
                "text_chunks_count": len(clean_text_chunks),
                "audio_files_count": len(audio_files),
                "tts_engine": self.tts.engine_name,
                "ffmpeg_available": self.tts.ffmpeg_available,
                "combined_mp3_created": combined_mp3 is not None
            }
            
            # Add page range info to debug
            if start_page is not None or end_page is not None:
                debug_info["page_range"] = {
                    "start_page": start_page,
                    "end_page": end_page,
                    "range_description": f"{start_page or 1}-{end_page or 'end'}"
                }
            else:
                debug_info["page_range"] = "full_document"
            
            return ProcessingResult(
                success=True, 
                audio_files=audio_files,
                combined_mp3_file=combined_mp3,
                audio_path=audio_files[0] if audio_files else None,  # First file for compatibility
                debug_info=debug_info
            )
            
        except Exception as e:
            print(f"PDFProcessor: Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return ProcessingResult(success=False, error=f"Processing failed: {str(e)}")
        
    def get_pdf_info(self, pdf_path: str) -> Dict[str, Any]:
        """Get PDF information for the UI (page count, etc.)"""
        try:
            return self.ocr.get_pdf_info(pdf_path)
        except Exception as e:
            print(f"PDFProcessor: Failed to get PDF info: {e}")
            return {
                'total_pages': 0,
                'title': 'Unknown',
                'author': 'Unknown',
                'error': str(e)
            }
    
    def validate_page_range(self, pdf_path: str, start_page: int = None, end_page: int = None) -> Dict[str, Any]:
        """Validate page range against actual PDF"""
        try:
            pdf_info = self.get_pdf_info(pdf_path)
            total_pages = pdf_info.get('total_pages', 0)
            
            if total_pages == 0:
                return {
                    'valid': False,
                    'error': 'Could not determine PDF page count',
                    'total_pages': 0
                }
            
            # Validate start page
            if start_page is not None:
                if start_page < 1:
                    return {
                        'valid': False,
                        'error': 'Start page must be 1 or greater',
                        'total_pages': total_pages
                    }
                if start_page > total_pages:
                    return {
                        'valid': False,
                        'error': f'Start page {start_page} exceeds total pages ({total_pages})',
                        'total_pages': total_pages
                    }
            
            # Validate end page
            if end_page is not None:
                if end_page < 1:
                    return {
                        'valid': False,
                        'error': 'End page must be 1 or greater',
                        'total_pages': total_pages
                    }
                if end_page > total_pages:
                    return {
                        'valid': False,
                        'error': f'End page {end_page} exceeds total pages ({total_pages})',
                        'total_pages': total_pages
                    }
            
            # Validate range consistency
            if start_page is not None and end_page is not None:
                if start_page > end_page:
                    return {
                        'valid': False,
                        'error': f'Start page ({start_page}) cannot be greater than end page ({end_page})',
                        'total_pages': total_pages
                    }
            
            # All validations passed
            actual_start = start_page if start_page is not None else 1
            actual_end = end_page if end_page is not None else total_pages
            
            return {
                'valid': True,
                'total_pages': total_pages,
                'actual_start': actual_start,
                'actual_end': actual_end,
                'pages_to_process': actual_end - actual_start + 1,
                'percentage_of_document': ((actual_end - actual_start + 1) / total_pages) * 100
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Page range validation failed: {str(e)}',
                'total_pages': 0
            }

