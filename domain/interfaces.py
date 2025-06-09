# domain/interfaces.py - All Business Logic Interfaces
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
from .models import PDFInfo, PageRange, ProcessingRequest, ProcessingResult

# --- External Service Interfaces ---

class ILLMProvider(ABC):
    """Interface for Large Language Model providers"""
    @abstractmethod
    def generate_content(self, prompt: str) -> str:
        """Generates content based on a prompt"""
        pass

class ITTSEngine(ABC):
    """Interface for Text-to-Speech engines"""
    @abstractmethod
    def generate_audio_data(self, text_to_speak: str) -> bytes:
        """Generates raw audio data from text"""
        pass

    @abstractmethod
    def get_output_format(self) -> str:
        """Returns the output format (e.g., 'wav', 'mp3')"""
        pass

# --- Domain Service Interfaces ---

class TextExtractor(ABC):
    """Interface for extracting text from PDFs"""
    
    @abstractmethod
    def extract_text(self, pdf_path: str, page_range: PageRange) -> str:
        """Extract text from PDF with optional page range"""
        pass
    
    @abstractmethod
    def get_pdf_info(self, pdf_path: str) -> PDFInfo:
        """Get basic PDF information"""
        pass

class TextCleaner(ABC):
    """Interface for cleaning and optimizing text"""
    
    @abstractmethod
    def clean_text(self, raw_text: str, llm_provider: Optional[ILLMProvider] = None) -> List[str]:
        """Clean text and return chunks optimized for TTS, optionally using an LLM provider"""
        pass

class AudioGenerator(ABC):
    """Interface for generating audio from text"""
    
    @abstractmethod
    def generate_audio(self, text_chunks: List[str], output_name: str, output_dir: str, tts_engine: Optional[ITTSEngine] = None) -> Tuple[List[str], Optional[str]]:
        """Generate audio files from text chunks. Returns (individual_files, combined_mp3)"""
        pass

class PageRangeValidator(ABC):
    """Interface for validating page ranges"""
    
    @abstractmethod
    def validate_range(self, pdf_path: str, page_range: PageRange) -> Dict[str, Any]:
        """Validate page range against PDF. Returns validation result"""
        pass

# --- Application Service Interfaces ---

class PDFProcessingService(ABC):
    """Core business logic for PDF to audio conversion"""
    
    @abstractmethod
    def process_pdf(self, request: ProcessingRequest) -> ProcessingResult:
        """Process PDF through complete pipeline"""
        pass
    
    @abstractmethod
    def get_pdf_info(self, pdf_path: str) -> PDFInfo:
        """Get PDF information for UI"""
        pass
    
    @abstractmethod
    def validate_page_range(self, pdf_path: str, page_range: PageRange) -> Dict[str, Any]:
        """Validate page range"""
        pass