# domain/document/document_engine.py - Unified Document Processing Engine
"""
Consolidated document engine that unifies PDF processing, text extraction, and coordination.
Replaces: PDFProcessingService, complex text extraction logic
"""

import io
import os
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod

import pdfplumber

from ..interfaces import IOCRProvider, IFileManager
from ..models import TimedAudioResult, ProcessingRequest, ProcessingResult, PDFInfo, PageRange
from ..errors import ApplicationError, text_extraction_error, audio_generation_error


class IDocumentEngine(ABC):
    """Unified interface for document processing operations"""
    
    @abstractmethod
    def get_pdf_info(self, pdf_path: str) -> PDFInfo:
        """Get PDF metadata and information"""
        pass
    
    @abstractmethod
    def validate_page_range(self, pdf_path: str, page_range: PageRange) -> Dict[str, Any]:
        """Validate requested page range"""
        pass
    
    @abstractmethod
    def extract_text(self, pdf_path: str, pages: Optional[List[int]] = None) -> List[str]:
        """Extract text from PDF with OCR fallback"""
        pass
    
    @abstractmethod
    def process_document(self, request: ProcessingRequest, audio_engine: 'IAudioEngine', text_pipeline: 'ITextPipeline', enable_timing: bool = False) -> ProcessingResult:
        """Complete document processing workflow"""
        pass


class DocumentEngine(IDocumentEngine):
    """
    Unified document engine that consolidates PDF processing.
    High cohesion: All document operations in one place.
    Low coupling: Depends only on abstractions (IOCRProvider, IFileManager).
    """
    
    def __init__(
        self,
        ocr_provider: IOCRProvider,
        file_manager: IFileManager,
        min_text_threshold: int = 100
    ):
        self.ocr_provider = ocr_provider
        self.file_manager = file_manager
        self.min_text_threshold = min_text_threshold
        print("DocumentEngine initialized and ready.")
    
    def get_pdf_info(self, pdf_path: str) -> PDFInfo:
        """Get PDF information - delegates to OCR provider"""
        return self.ocr_provider.get_pdf_info(pdf_path)
    
    def validate_page_range(self, pdf_path: str, page_range: PageRange) -> Dict[str, Any]:
        """Validate page range - delegates to OCR provider"""
        return self.ocr_provider.validate_range(pdf_path, page_range)
    
    def extract_text(self, pdf_path: str, pages: Optional[List[int]] = None) -> List[str]:
        """
        Extract text from PDF with intelligent OCR fallback.
        Uses direct text extraction first, falls back to OCR for poor quality pages.
        """
        extracted_text = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page_indices = pages if pages else range(len(pdf.pages))
                
                for i in page_indices:
                    if i >= len(pdf.pages):
                        continue
                    
                    page = pdf.pages[i]
                    text = self._extract_page_text(page, i + 1)
                    
                    if text and text.strip():
                        extracted_text.append(text.strip())
            
            return extracted_text
            
        except Exception as e:
            print(f"DocumentEngine: Error extracting text from {pdf_path}: {e}")
            return []
    
    def process_document(
        self, 
        request: ProcessingRequest, 
        audio_engine: 'IAudioEngine', 
        text_pipeline: 'ITextPipeline',
        enable_timing: bool = False
    ) -> ProcessingResult:
        """
        Complete document processing workflow using new architecture components.
        
        Args:
            request: ProcessingRequest with PDF path, output name, page range
            audio_engine: AudioEngine for audio generation
            text_pipeline: TextPipeline for text cleaning and enhancement
        
        Returns:
            ProcessingResult with success/failure and audio files
        """
        try:
            print(f"DocumentEngine: Starting processing for {request.pdf_path}")
            
            # 1. Convert page range to page list
            pages_list = self._convert_page_range_to_list(request.pdf_path, request.page_range)
            
            # 2. Extract text from PDF
            text_chunks = self.extract_text(request.pdf_path, pages_list)
            
            if not text_chunks:
                print("DocumentEngine: No text extracted from PDF")
                return ProcessingResult.failure_result(
                    text_extraction_error("No text could be extracted from the PDF")
                )
            
            print(f"DocumentEngine: Extracted {len(text_chunks)} text chunks")
            
            # 3. Process text through pipeline (clean + enhance)
            processed_chunks = []
            for chunk in text_chunks:
                # Clean the text
                cleaned = text_pipeline.clean_text(chunk)
                # Enhance with SSML
                enhanced = text_pipeline.enhance_with_ssml(cleaned)
                processed_chunks.append(enhanced)
            
            print(f"DocumentEngine: Processed {len(processed_chunks)} chunks through text pipeline")
            
            # 4. Generate audio - choose appropriate method based on timing requirement
            if enable_timing:
                print("DocumentEngine: Using timing-aware audio generation")
                timed_result = audio_engine.generate_with_timing(processed_chunks, request.output_name)
            else:
                print("DocumentEngine: Using simple audio generation (no timing complexity)")
                timed_result = audio_engine.generate_simple_audio(processed_chunks, request.output_name)
            
            if not timed_result or not timed_result.audio_files:
                return ProcessingResult.failure_result(
                    audio_generation_error("Audio generation failed to produce files")
                )
            
            # 5. Convert to ProcessingResult with timing data
            return ProcessingResult.success_result(
                audio_files=[os.path.basename(f) for f in timed_result.audio_files],
                combined_mp3=os.path.basename(timed_result.combined_mp3) if timed_result.combined_mp3 else None,
                timing_data=timed_result.timing_data,  # Pass through timing data
                debug_info={
                    "text_chunks_count": len(text_chunks),
                    "processed_chunks_count": len(processed_chunks),
                    "audio_files_count": len(timed_result.audio_files),
                    "timing_data_available": timed_result.timing_data is not None
                }
            )
            
        except Exception as e:
            print(f"DocumentEngine: Processing failed: {e}")
            return ProcessingResult.failure_result(
                audio_generation_error(f"Document processing failed: {str(e)}")
            )
    
    def _convert_page_range_to_list(self, pdf_path: str, page_range: PageRange) -> Optional[List[int]]:
        """Convert PageRange to 0-based page list"""
        if page_range.is_full_document():
            return None
        
        start = page_range.start_page or 1
        end = page_range.end_page
        
        if end is None:
            # Get total pages to determine end
            pdf_info = self.get_pdf_info(pdf_path)
            end = pdf_info.total_pages
        
        return list(range(start - 1, end))  # Convert to 0-based indexing
    
    def _extract_page_text(self, page: pdfplumber.page.Page, page_num: int) -> str:
        """Extract text from a single page with OCR fallback"""
        # Try direct text extraction first
        text = page.extract_text()
        
        # If direct extraction is poor, try OCR fallback
        if not text or len(text.strip()) < self.min_text_threshold:
            print(f"DocumentEngine: Page {page_num} has low text quality, using OCR")
            ocr_text = self._ocr_page(page)
            
            # Use whichever text is longer
            if len(ocr_text) > len(text or ""):
                text = ocr_text
        
        return text or ""
    
    def _ocr_page(self, page: pdfplumber.page.Page) -> str:
        """Perform OCR on a single PDF page"""
        temp_image_path = None
        
        try:
            # Convert page to high-resolution image
            img = page.to_image(resolution=300).original
            
            # Save as temporary PNG file
            with io.BytesIO() as temp_buffer:
                img.save(temp_buffer, format="PNG")
                image_bytes = temp_buffer.getvalue()
            
            temp_image_path = self.file_manager.save_temp_file(image_bytes, suffix=".png")
            
            # Perform OCR using the provider
            ocr_text = self.ocr_provider.perform_ocr(temp_image_path)
            return ocr_text
            
        except Exception as e:
            print(f"DocumentEngine: OCR failed for page: {e}")
            return ""
            
        finally:
            # Clean up temporary file
            if temp_image_path:
                try:
                    self.file_manager.delete_file(temp_image_path)
                except:
                    pass