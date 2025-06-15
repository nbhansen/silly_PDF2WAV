# domain/interfaces.py - Simplified interfaces with SSML support
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
from enum import Enum
from .models import PDFInfo, PageRange, ProcessingRequest, ProcessingResult, FileInfo, CleanupResult, TimedAudioResult
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
        Generate audio files from text chunks (existing method)
        
        Args:
            text_chunks: List of text chunks to convert
            output_name: Base name for output files
            output_dir: Directory to save audio files
            tts_engine: Optional TTS engine to use
            
        Returns:
            Tuple of (individual_files, combined_mp3_file_or_None)
        """
        pass
    
    def generate_audio_with_timing(self, text_chunks: List[str], output_name: str, output_dir: str, 
                                  tts_engine: Optional[ITTSEngine] = None) -> 'TimedAudioResult':
        """
        Generate audio with timing metadata (optional implementation)
        
        Args:
            text_chunks: List of text chunks to convert
            output_name: Base name for output files  
            output_dir: Directory to save audio files
            tts_engine: Optional TTS engine to use
            
        Returns:
            TimedAudioResult with audio files and timing data
        """
        # Default implementation: call existing method and wrap result
        audio_files, combined_mp3 = self.generate_audio(text_chunks, output_name, output_dir, tts_engine)
        
        from .models import TimedAudioResult
        return TimedAudioResult(
            audio_files=audio_files,
            combined_mp3=combined_mp3,
            timing_data=None
        )
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

    ## Additional methods for cleanup and file management can be added here

class FileManager(ABC):
    """Domain interface for file lifecycle management"""
    
    @abstractmethod
    def cleanup_old_files(self, max_age_hours: float) -> CleanupResult:
        """Remove files older than max_age_hours"""
        pass
    
    @abstractmethod
    def get_file_info(self, filename: str) -> Optional[FileInfo]:
        """Get information about a specific file"""
        pass
    
    @abstractmethod
    def list_managed_files(self) -> List[FileInfo]:
        """List all files under management"""
        pass
    
    @abstractmethod
    def schedule_cleanup(self, filename: str, delay_hours: float) -> bool:
        """Schedule a file for deletion after delay_hours"""
        pass
    
    @abstractmethod
    def get_total_disk_usage(self) -> int:
        """Get total bytes used by managed files"""
        pass