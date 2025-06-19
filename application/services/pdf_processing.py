"""
This module contains the primary application service for orchestrating the
PDF-to-audio conversion process.
"""

import io
from typing import List, Optional

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
from domain.models import TimedAudioResult

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
            return TimedAudioResult(audio_path=None, segments=[])

        # 2. Generate audio
        # The audio_generation_service now handles all the complexity of
        # selecting the right timing strategy.
        print(f"Extracted {len(text_chunks)} chunks of text. Proceeding to audio generation.")
        timed_audio_result = self.audio_generation_service.generate_audio_with_timing(
            text_chunks=text_chunks,
            output_filename=output_name
        )

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
                        cleaned_text = self.text_cleaner.strip_ssml(text)
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
