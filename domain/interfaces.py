# domain/interfaces.py - Simplified interfaces with SSML support
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
from enum import Enum
from .models import PDFInfo, PageRange, ProcessingRequest, ProcessingResult

# === SSML Support Enums ===

class SSMLCapability(Enum):
    """SSML support levels for TTS engines"""
    NONE = "none"           # No SSML support, strips all tags
    BASIC = "basic"         # Basic tags: break, emphasis, prosody, say-as
    ADVANCED = "advanced"   # Basic + voice, audio (some advanced features)
    FULL = "full"          # Complete SSML specification support

# === Core TTS Interface ===

class ITTSEngine(ABC):
    """Simple interface for text-to-speech engines with optional SSML support"""
    
    @abstractmethod
    def generate_audio_data(self, text_to_speak: str) -> bytes:
        """
        Generate raw audio data from text
        
        Args:
            text_to_speak: Input text (may contain SSML markup)
            
        Returns:
            Raw audio bytes in the engine's native format
        """
        pass

    @abstractmethod
    def get_output_format(self) -> str:
        """
        Returns the output format (e.g., 'wav', 'mp3')
        
        Returns:
            File extension of the output format
        """
        pass
    
    def prefers_sync_processing(self) -> bool:
        """
        Whether this engine works better with synchronous processing
        
        Returns:
            True for local engines (Piper), False for cloud engines (Gemini)
        """
        return True  # Safe default
    
    def supports_ssml(self) -> bool:
        """
        Check if engine supports SSML markup (optional implementation)
        
        Returns:
            True if SSML is supported, False otherwise
        """
        return False  # Safe default

# === External Service Interfaces ===

class ILLMProvider(ABC):
    """Interface for Large Language Model providers"""
    
    @abstractmethod
    def generate_content(self, prompt: str) -> str:
        """
        Generate content based on a prompt
        
        Args:
            prompt: Input prompt for the LLM
            
        Returns:
            Generated text content
        """
        pass

# === Domain Service Interfaces ===

class TextExtractor(ABC):
    """Interface for extracting text from PDFs"""
    
    @abstractmethod
    def extract_text(self, pdf_path: str, page_range: PageRange) -> str:
        """
        Extract text from PDF with optional page range
        
        Args:
            pdf_path: Path to the PDF file
            page_range: Range of pages to extract (PageRange object)
            
        Returns:
            Extracted text content
        """
        pass
    
    @abstractmethod
    def get_pdf_info(self, pdf_path: str) -> PDFInfo:
        """
        Get basic PDF information
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            PDFInfo object with metadata
        """
        pass

class TextCleaner(ABC):
    """Interface for cleaning and optimizing text"""
    
    @abstractmethod
    def clean_text(self, raw_text: str, llm_provider: Optional[ILLMProvider] = None) -> List[str]:
        """
        Clean text and return chunks optimized for TTS
        
        Args:
            raw_text: Raw extracted text from PDF
            llm_provider: Optional LLM for advanced cleaning
            
        Returns:
            List of cleaned text chunks ready for TTS
        """
        pass

class AudioGenerator(ABC):
    """Interface for generating audio from text"""
    
    @abstractmethod
    def generate_audio(self, text_chunks: List[str], output_name: str, output_dir: str, 
                      tts_engine: Optional[ITTSEngine] = None) -> Tuple[List[str], Optional[str]]:
        """
        Generate audio files from text chunks
        
        Args:
            text_chunks: List of text chunks to convert
            output_name: Base name for output files
            output_dir: Directory to save audio files
            tts_engine: Optional TTS engine to use
            
        Returns:
            Tuple of (individual_files, combined_mp3_file_or_None)
        """
        pass

class PageRangeValidator(ABC):
    """Interface for validating page ranges"""
    
    @abstractmethod
    def validate_range(self, pdf_path: str, page_range: PageRange) -> Dict[str, Any]:
        """
        Validate page range against PDF
        
        Args:
            pdf_path: Path to the PDF file
            page_range: PageRange object to validate
            
        Returns:
            Dictionary with validation results:
            - 'valid': bool
            - 'error': str (if invalid)
            - 'total_pages': int
        """
        pass

# === Application Service Interface ===

class PDFProcessingService(ABC):
    """Core business logic for PDF to audio conversion"""
    
    @abstractmethod
    def process_pdf(self, request: ProcessingRequest) -> ProcessingResult:
        """
        Process PDF through complete pipeline
        
        Args:
            request: ProcessingRequest with PDF path, output name, and page range
            
        Returns:
            ProcessingResult with success status and generated files
        """
        pass
    
    @abstractmethod
    def get_pdf_info(self, pdf_path: str) -> PDFInfo:
        """
        Get PDF information for UI
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            PDFInfo object for display in user interface
        """
        pass
    
    @abstractmethod
    def validate_page_range(self, pdf_path: str, page_range: PageRange) -> Dict[str, Any]:
        """
        Validate page range
        
        Args:
            pdf_path: Path to the PDF file
            page_range: PageRange object to validate
            
        Returns:
            Validation result dictionary
        """
        pass