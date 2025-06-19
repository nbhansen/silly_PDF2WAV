"""
This module contains the primary application service for orchestrating the
PDF-to-audio conversion process with added wrapper methods for cleaner interface.
"""

import io
import os
from typing import List, Optional, Dict, Any

import pdfplumber
from PIL import Image

# Import the interfaces it depends on and implements
from domain.interfaces import (
    ITextExtractor,
    IOCRProvider,
    IFileManager,
    ITextCleaner,
    ILLMProvider,
)
# Import the concrete services it depends on
from domain.services.audio_generation_service import AudioGenerationService
from domain.services.academic_ssml_service import AcademicSSMLService
from domain.models import TimedAudioResult, ProcessingRequest, ProcessingResult, PDFInfo, PageRange
from domain.errors import ApplicationError, text_extraction_error, audio_generation_error

class PDFProcessingService(ITextExtractor):
    """
    Application service to orchestrate the PDF to audio workflow.
    This service handles text extraction (both text-based and OCR),
    cleaning, enhancement, and audio generation.
    """

    def __init__(
        self,
        ocr_provider: IOCRProvider,
        audio_generation_service: AudioGenerationService,
        file_manager: IFileManager,
        text_cleaner: ITextCleaner,
        ssml_service: AcademicSSMLService,
        llm_provider: Optional[ILLMProvider] = None,
    ):
        self.ocr_provider = ocr_provider
        self.audio_generation_service = audio_generation_service
        self.file_manager = file_manager
        self.text_cleaner = text_cleaner
        self.ssml_service = ssml_service
        self.llm_provider = llm_provider
        print("PDFProcessingService initialized and ready.")

    # NEW: Wrapper methods for cleaner app.py interface
    def get_pdf_info(self, pdf_path: str) -> PDFInfo:
        """Get PDF information - delegates to OCR provider"""
        return self.ocr_provider.get_pdf_info(pdf_path)
    
    def validate_page_range(self, pdf_path: str, page_range: PageRange) -> Dict[str, Any]:
        """Validate page range - delegates to OCR provider"""
        return self.ocr_provider.validate_range(pdf_path, page_range)
    
    def process_pdf(self, request: ProcessingRequest) -> ProcessingResult:
        """
        Process PDF with standard interface - wrapper around process_pdf_and_generate_audio
        
        Args:
            request: ProcessingRequest with pdf_path, output_name, and page_range
            
        Returns:
            ProcessingResult with success/failure and audio files
        """
        try:
            # Convert PageRange to page list
            pages_list = None
            if not request.page_range.is_full_document():
                start = request.page_range.start_page or 1
                end = request.page_range.end_page
                if end is None:
                    # Get total pages to determine end
                    pdf_info = self.get_pdf_info(request.pdf_path)
                    end = pdf_info.total_pages
                pages_list = list(range(start - 1, end))  # Convert to 0-based indexing
            
            # Use the existing method
            timed_result = self.process_pdf_and_generate_audio(
                filepath=request.pdf_path,
                output_name=request.output_name,
                pages=pages_list
            )
            
            if not timed_result or not timed_result.audio_files:
                return ProcessingResult.failure_result(
                    audio_generation_error("No audio files were generated")
                )
            
            # Convert TimedAudioResult to ProcessingResult
            return ProcessingResult.success_result(
                audio_files=[os.path.basename(f) for f in timed_result.audio_files],
                combined_mp3=os.path.basename(timed_result.combined_mp3) if timed_result.combined_mp3 else None,
                debug_info={
                    "audio_files_count": len(timed_result.audio_files),
                    "combined_mp3_created": timed_result.combined_mp3 is not None,
                    "timing_data_available": timed_result.timing_data is not None
                }
            )
            
        except Exception as e:
            print(f"PDFProcessingService.process_pdf error: {e}")
            return ProcessingResult.failure_result(
                audio_generation_error(f"Processing failed: {str(e)}")
            )

    # EXISTING: Core processing method
    def process_pdf_and_generate_audio(
        self,
        filepath: str,
        output_name: str,
        pages: Optional[List[int]] = None
    ) -> TimedAudioResult:
        """
        The main orchestration method.
        1. Extracts text from the PDF.
        2. Generates audio with timing information.
        """
        print(f"Starting PDF processing for: {filepath}")

        # 1. Extract text using the method from this class
        text_chunks = self.extract_text(filepath, pages)

        if not text_chunks:
            print("No text extracted from PDF. Aborting.")
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

        # 2. Clean text using text cleaner
        print(f"Extracted {len(text_chunks)} chunks of text. Cleaning text...")
        try:
            # Combine chunks for cleaning, then re-chunk
            combined_text = "\n\n".join(text_chunks)
            cleaned_chunks = self.text_cleaner.clean_text(combined_text, self.llm_provider)
            
            if not cleaned_chunks:
                print("Text cleaning produced no results, using original text")
                cleaned_chunks = text_chunks
                
        except Exception as e:
            print(f"Text cleaning failed: {e}, using original text")
            cleaned_chunks = text_chunks

        # 3. Enhance with SSML
        print("Enhancing text with SSML...")
        try:
            enhanced_chunks = self.ssml_service.enhance_text_chunks(cleaned_chunks)
        except Exception as e:
            print(f"SSML enhancement failed: {e}, using cleaned text")
            enhanced_chunks = cleaned_chunks

        # 4. Generate audio with timing using the audio generation service
        print(f"Proceeding to audio generation with {len(enhanced_chunks)} enhanced chunks...")
        try:
            # Get the TTS engine from the audio generation service's timing strategy
            tts_engine = None
            if hasattr(self.audio_generation_service, 'timing_strategy'):
                if hasattr(self.audio_generation_service.timing_strategy, 'tts_engine'):
                    tts_engine = self.audio_generation_service.timing_strategy.tts_engine
            
            if tts_engine:
                timed_audio_result = self.audio_generation_service.generate_audio_with_timing(
                    text_chunks=enhanced_chunks,
                    output_filename=output_name,
                    output_dir=self.file_manager.get_output_dir(),
                    tts_engine=tts_engine
                )
            else:
                # Fallback: use timing strategy directly
                timed_audio_result = self.audio_generation_service.timing_strategy.generate_with_timing(
                    text_chunks=enhanced_chunks,
                    output_filename=output_name
                )
                
        except Exception as e:
            print(f"Audio generation failed: {e}")
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

        print("PDF processing and audio generation complete.")
        return timed_audio_result

    def extract_text(self, filepath: str, pages: Optional[List[int]] = None) -> List[str]:
        """
        Extracts text from a PDF file. It attempts to extract text directly,
        and if that fails or yields little text, it falls back to OCR.
        """
        extracted_text = []
        try:
            with pdfplumber.open(filepath) as pdf:
                page_indices = pages if pages else range(len(pdf.pages))
                
                for i in page_indices:
                    if i >= len(pdf.pages):
                        continue
                        
                    page = pdf.pages[i]
                    text = page.extract_text()
                    
                    # If direct text extraction is poor, try OCR as a fallback
                    if not text or len(text.strip()) < 100:
                        print(f"Page {i+1}: Low text quality found. Attempting OCR.")
                        ocr_text = self._ocr_page(page)
                        # Use whichever text is longer
                        if len(ocr_text) > len(text or ""):
                            text = ocr_text

                    if text:
                        # Basic text cleaning
                        cleaned_text = text.strip()
                        if cleaned_text:
                            extracted_text.append(cleaned_text)
            
            return extracted_text
        except Exception as e:
            print(f"Error extracting text from PDF {filepath}: {e}")
            return []

    def _ocr_page(self, page: pdfplumber.page.Page) -> str:
        """Performs OCR on a single PDF page object."""
        temp_image_path = None
        try:
            # Convert page to a high-resolution image
            img = page.to_image(resolution=300).original
            
            with io.BytesIO() as temp_buffer:
                img.save(temp_buffer, format="PNG")
                image_bytes = temp_buffer.getvalue()

            temp_image_path = self.file_manager.save_temp_file(image_bytes, suffix=".png")

            # Perform OCR using the injected provider
            ocr_text = self.ocr_provider.perform_ocr(temp_image_path)
            return ocr_text
        except Exception as e:
            print(f"Failed to perform OCR on page: {e}")
            return ""
        finally:
            # Ensure temporary file is always cleaned up
            if temp_image_path:
                self.file_manager.delete_file(temp_image_path)