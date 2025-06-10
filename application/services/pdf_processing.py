import os
from typing import Dict, Any, Optional

from domain.models import ProcessingRequest, ProcessingResult, PDFInfo, PageRange
from domain.interfaces import (
    TextExtractor, TextCleaner, AudioGenerator, PageRangeValidator,
    PDFProcessingService as PDFProcessingServiceInterface,
    ILLMProvider, ITTSEngine
)
from domain.services.ssml_pipeline import SSMLPipeline

class PDFProcessingService(PDFProcessingServiceInterface):
    """Simplified PDF processing service using SSML pipeline"""
    
    def __init__(
        self,
        text_extractor: TextExtractor,
        text_cleaner: TextCleaner,
        audio_generator: AudioGenerator,
        page_validator: PageRangeValidator,
        ssml_pipeline: SSMLPipeline,  # NEW: Centralized SSML
        llm_provider: Optional[ILLMProvider] = None,
        tts_engine: Optional[ITTSEngine] = None
    ):
        self.text_extractor = text_extractor
        self.text_cleaner = text_cleaner
        self.audio_generator = audio_generator
        self.page_validator = page_validator
        self.ssml_pipeline = ssml_pipeline  # NEW
        self.llm_provider = llm_provider
        self.tts_engine = tts_engine
    
    def process_pdf(self, request: ProcessingRequest) -> ProcessingResult:
        """Simplified business logic with centralized SSML processing"""
        try:
            if not os.path.exists(request.pdf_path):
                return ProcessingResult(success=False, error=f"File not found: {request.pdf_path}")
            
            self._log_processing_start(request)
            
            # Step 1: Extract text
            raw_text = self.text_extractor.extract_text(request.pdf_path, request.page_range)
            if self._is_extraction_failed(raw_text):
                return ProcessingResult(success=False, error=f"Text extraction failed: {raw_text}")
            
            self._log_extraction_success(raw_text, request.page_range)
            
            # Step 2: Clean text (no SSML logic here)
            clean_text_chunks = self.text_cleaner.clean_text(raw_text, self.llm_provider)
            if not self._is_cleaning_successful(clean_text_chunks):
                return ProcessingResult(success=False, error="Text cleaning failed")
            
            self._log_cleaning_success(clean_text_chunks)
            
            # Step 3: SSML processing (centralized)
            ssml_chunks = self.ssml_pipeline.process_text_chunks(clean_text_chunks)
            
            # Step 4: Generate audio
            audio_files, combined_mp3 = self.audio_generator.generate_audio(
                ssml_chunks,
                request.output_name,
                output_dir="audio_outputs",
                tts_engine=self.tts_engine
            )
            
            if not audio_files:
                return ProcessingResult(success=False, error="Audio generation failed")
            
            self._log_processing_complete(audio_files, combined_mp3)
            
            return ProcessingResult(
                success=True,
                audio_files=audio_files,
                combined_mp3_file=combined_mp3,
                debug_info=self._build_debug_info(
                    raw_text, clean_text_chunks, audio_files, 
                    combined_mp3, request.page_range
                )
            )
            
        except Exception as e:
            self._log_error(f"Unexpected error: {e}")
            return ProcessingResult(success=False, error=f"Processing failed: {str(e)}")
    
    def get_pdf_info(self, pdf_path: str) -> PDFInfo:
        return self.text_extractor.get_pdf_info(pdf_path)
    
    def validate_page_range(self, pdf_path: str, page_range: PageRange) -> Dict[str, Any]:
        return self.page_validator.validate_range(pdf_path, page_range)
    
    # === Helper methods (unchanged logic, simplified debug info) ===
    
    def _is_extraction_failed(self, raw_text: str) -> bool:
        return not raw_text or raw_text.startswith("Error")
    
    def _is_cleaning_successful(self, clean_text_chunks: list) -> bool:
        return clean_text_chunks and any(chunk.strip() for chunk in clean_text_chunks)
    
    def _build_debug_info(self, raw_text: str, clean_text_chunks: list, 
                         audio_files: list, combined_mp3: str, page_range: PageRange) -> Dict[str, Any]:
        debug_info = {
            "raw_text_length": len(raw_text),
            "text_chunks_count": len(clean_text_chunks),
            "audio_files_count": len(audio_files),
            "combined_mp3_created": combined_mp3 is not None,
            "ssml_enabled": self.ssml_pipeline.is_enabled(),
            "ssml_capability": self.ssml_pipeline.get_capability().value
        }
        
        if not page_range.is_full_document():
            debug_info["page_range"] = {
                "start_page": page_range.start_page,
                "end_page": page_range.end_page
            }
        
        return debug_info
    
    def _log_processing_start(self, request: ProcessingRequest):
        page_info = ""
        if not request.page_range.is_full_document():
            page_info = f" (pages {request.page_range.start_page or 1}-{request.page_range.end_page or 'end'})"
        print(f"PDFProcessingService: Starting processing of {request.pdf_path}{page_info}")
    
    def _log_extraction_success(self, raw_text: str, page_range: PageRange):
        page_info = ""
        if not page_range.is_full_document():
            page_info = f" (pages {page_range.start_page or 1}-{page_range.end_page or 'end'})"
        print(f"PDFProcessingService: Extracted {len(raw_text):,} characters from PDF{page_info}")
    
    def _log_cleaning_success(self, clean_text_chunks: list):
        valid_chunks = len([c for c in clean_text_chunks if c.strip() and not c.startswith("Error")])
        print(f"PDFProcessingService: Text cleaning produced {len(clean_text_chunks)} chunks ({valid_chunks} valid)")
    
    def _log_processing_complete(self, audio_files: list, combined_mp3: str):
        print(f"PDFProcessingService: Processing complete! Generated {len(audio_files)} audio files")
        if combined_mp3:
            print(f"PDFProcessingService: Created combined MP3: {combined_mp3}")
    
    def _log_error(self, message: str):
        print(f"PDFProcessingService: {message}")
