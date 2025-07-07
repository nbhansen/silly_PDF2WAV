# domain/document/document_engine.py - Unified Document Processing Engine
"""Consolidated document engine that unifies PDF processing, text extraction, and coordination.
Replaces: PDFProcessingService, complex text extraction logic.
"""

from abc import ABC, abstractmethod
import io
import os
from typing import TYPE_CHECKING, Any, Optional

import pdfplumber

from ..errors import audio_generation_error, text_extraction_error
from ..interfaces import IFileManager, IOCRProvider
from ..models import PageRange, PDFInfo, ProcessingRequest, ProcessingResult

if TYPE_CHECKING:
    from ..audio.audio_engine import IAudioEngine
    from ..text.text_pipeline import ITextPipeline


class IDocumentEngine(ABC):
    """Unified interface for document processing operations."""

    @abstractmethod
    def get_pdf_info(self, pdf_path: str) -> PDFInfo:
        """Get PDF metadata and information."""

    @abstractmethod
    def validate_page_range(self, pdf_path: str, page_range: PageRange) -> dict[str, Any]:
        """Validate requested page range."""

    @abstractmethod
    def extract_text(self, pdf_path: str, pages: Optional[list[int]] = None) -> list[str]:
        """Extract text from PDF with OCR fallback."""

    @abstractmethod
    def process_document(
        self,
        request: ProcessingRequest,
        audio_engine: "IAudioEngine",
        text_pipeline: "ITextPipeline",
        enable_timing: bool = False,
        llm_chunk_size: int = 50000,
    ) -> ProcessingResult:
        """Complete document processing workflow."""


class DocumentEngine(IDocumentEngine):
    """Unified document engine that consolidates PDF processing.
    High cohesion: All document operations in one place.
    Low coupling: Depends only on abstractions (IOCRProvider, IFileManager).
    """

    def __init__(self, ocr_provider: IOCRProvider, file_manager: IFileManager, min_text_threshold: int = 100):
        self.ocr_provider = ocr_provider
        self.file_manager = file_manager
        self.min_text_threshold = min_text_threshold
        print("DocumentEngine initialized and ready.")

    def get_pdf_info(self, pdf_path: str) -> PDFInfo:
        """Get PDF information - delegates to OCR provider."""
        return self.ocr_provider.get_pdf_info(pdf_path)

    def validate_page_range(self, pdf_path: str, page_range: PageRange) -> dict[str, Any]:
        """Validate page range - delegates to OCR provider."""
        return self.ocr_provider.validate_range(pdf_path, page_range)

    def extract_text(self, pdf_path: str, pages: Optional[list[int]] = None) -> list[str]:
        """Extract text from PDF with intelligent OCR fallback.
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
        audio_engine: "IAudioEngine",
        text_pipeline: "ITextPipeline",
        enable_timing: bool = False,
        llm_chunk_size: int = 50000,
    ) -> ProcessingResult:
        """Complete document processing workflow using new architecture components.

        Args:
            request: ProcessingRequest with PDF path, output name, page range
            audio_engine: AudioEngine for audio generation
            text_pipeline: TextPipeline for text cleaning and enhancement
            enable_timing: Whether to generate timing data
            llm_chunk_size: Optimal chunk size for LLM processing

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
                return ProcessingResult.failure_result(text_extraction_error("No text could be extracted from the PDF"))

            print(f"DocumentEngine: Extracted {len(text_chunks)} text chunks")

            # 3. Process text through pipeline with optimized chunking
            # Combine chunks for efficient LLM processing, then re-chunk for TTS
            print(f"🔬 DocumentEngine: Using optimized chunking strategy (LLM chunk size: {llm_chunk_size})")

            # Step 3a: Combine chunks for LLM processing
            combined_chunks = self._combine_chunks_for_llm(text_chunks, llm_chunk_size)
            print(f"   → Combined {len(text_chunks)} original chunks into {len(combined_chunks)} LLM chunks")

            # Step 3b: Process through LLM cleaning
            cleaned_chunks = []
            for i, combined_chunk in enumerate(combined_chunks, 1):
                print(
                    f"🔬 DocumentEngine: Processing LLM chunk {i}/{len(combined_chunks)} ({len(combined_chunk)} chars)"
                )
                print(f"   Combined text preview: '{combined_chunk[:100]}...'")

                # Clean the text using LLM
                print("   → Calling text_pipeline.clean_text()...")
                cleaned = text_pipeline.clean_text(combined_chunk)
                print(f"   → Cleaned text ({len(cleaned)} chars): '{cleaned[:100]}...'")

                cleaned_chunks.append(cleaned)

            # Step 3c: Re-combine all cleaned text and enhance with natural formatting
            all_cleaned_text = " ".join(cleaned_chunks)
            print(f"   → Combined all cleaned text: {len(all_cleaned_text)} chars total")

            print("   → Calling text_pipeline.enhance_with_natural_formatting() on combined text...")
            enhanced_text = text_pipeline.enhance_with_natural_formatting(all_cleaned_text)
            print(f"   → Enhanced text ({len(enhanced_text)} chars): '{enhanced_text[:100]}...'")

            # Step 3d: Split enhanced text back into optimal chunks for TTS
            processed_chunks = self._split_for_tts(enhanced_text)
            print(f"   → Split enhanced text into {len(processed_chunks)} TTS-optimized chunks")

            print(
                f"DocumentEngine: Processed through optimized pipeline: "
                f"{len(text_chunks)} → {len(combined_chunks)} → {len(processed_chunks)} chunks"
            )

            # 4. Generate audio - choose appropriate method based on timing requirement
            if enable_timing:
                print("DocumentEngine: Using timing-aware audio generation")
                timed_result = audio_engine.generate_with_timing(processed_chunks, request.output_name)
            else:
                print("DocumentEngine: Using simple audio generation (no timing complexity)")
                timed_result = audio_engine.generate_simple_audio(processed_chunks, request.output_name)

            print(f"🔍 DEBUG: timed_result={timed_result}")
            if timed_result:
                print(f"🔍 DEBUG: timed_result.audio_files={timed_result.audio_files}")

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
                    "timing_data_available": timed_result.timing_data is not None,
                },
            )

        except Exception as e:
            print(f"DocumentEngine: Processing failed: {e}")
            return ProcessingResult.failure_result(audio_generation_error(f"Document processing failed: {e!s}"))

    def _convert_page_range_to_list(self, pdf_path: str, page_range: PageRange) -> Optional[list[int]]:
        """Convert PageRange to 0-based page list."""
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
        """Extract text from a single page with OCR fallback."""
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
        """Perform OCR on a single PDF page."""
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
            ocr_result = self.ocr_provider.perform_ocr(temp_image_path)
            if ocr_result.is_success:
                return ocr_result.value or ""
            else:
                print(f"DocumentEngine: OCR provider failed: {ocr_result.error}")
                return ""

        except Exception as e:
            print(f"DocumentEngine: OCR failed for page: {e}")
            return ""

        finally:
            # Clean up temporary file
            if temp_image_path:
                try:
                    self.file_manager.delete_file(temp_image_path)
                except (OSError, FileNotFoundError):
                    # Ignore file cleanup errors - temporary files may already be removed
                    pass

    def _combine_chunks_for_llm(self, text_chunks: list[str], llm_chunk_size: int) -> list[str]:
        """Combine small PDF chunks into larger chunks optimal for LLM processing.

        Args:
            text_chunks: Original PDF text chunks
            llm_chunk_size: Target size for LLM chunks

        Returns:
            List of combined chunks optimized for LLM processing
        """
        if not text_chunks:
            return []

        combined_chunks = []
        current_chunk = ""

        for chunk in text_chunks:
            # Check if adding this chunk would exceed the target size
            if current_chunk and len(current_chunk) + len(chunk) + 1 > llm_chunk_size:
                # Current chunk is full, start a new one
                combined_chunks.append(current_chunk.strip())
                current_chunk = chunk
            else:
                # Add to current chunk
                if current_chunk:
                    current_chunk += " " + chunk
                else:
                    current_chunk = chunk

        # Add the final chunk if it has content
        if current_chunk.strip():
            combined_chunks.append(current_chunk.strip())

        return combined_chunks

    def _split_for_tts(self, text: str, target_chunk_size: int = 4000) -> list[str]:
        """Split enhanced text into chunks optimal for TTS processing.

        Args:
            text: Enhanced text with SSML markup
            target_chunk_size: Target size for TTS chunks

        Returns:
            List of chunks optimized for TTS processing
        """
        if not text:
            return []

        # Simple sentence-based splitting that handles SSML markup
        import re

        # If splitting fails, fall back to simple character-based chunking
        # Split on sentence boundaries, being careful with SSML tags
        sentences = re.split(r"([.!?]+(?:\s*(?:<[^>]*>)?\s*))", text)

        # Rejoin sentences with their delimiters
        sentence_list = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            sentence_list.append(sentence.strip())

        # Combine sentences into chunks of target size
        chunks = []
        current_chunk = ""

        for sentence in sentence_list:
            if not sentence:
                continue

            # Check if adding this sentence would exceed target size
            if current_chunk and len(current_chunk) + len(sentence) + 1 > target_chunk_size:
                # Current chunk is full, start a new one
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                # Add to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence

        # Add the final chunk if it has content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # Fallback: if no chunks created, split by character count
        if not chunks and text.strip():
            print("   → Sentence splitting failed, using character-based fallback")
            for i in range(0, len(text), target_chunk_size):
                chunk = text[i : i + target_chunk_size]
                if chunk.strip():
                    chunks.append(chunk.strip())

        return chunks
