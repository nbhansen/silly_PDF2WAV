# domain/models.py
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

# --- Core Domain Models ---

@dataclass
class PageRange:
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    
    def is_full_document(self) -> bool:
        return self.start_page is None and self.end_page is None

@dataclass
class ProcessingRequest:
    pdf_path: str
    output_name: str
    page_range: PageRange
    
@dataclass
class PDFInfo:
    total_pages: int
    title: str
    author: str

@dataclass
class ProcessingResult:
    success: bool
    audio_files: Optional[List[str]] = None
    combined_mp3_file: Optional[str] = None
    error: Optional[str] = None
    debug_info: Optional[Dict[str, Any]] = None

# --- Domain Interfaces ---

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
    def clean_text(self, raw_text: str) -> List[str]:
        """Clean text and return chunks optimized for TTS"""
        pass

class AudioGenerator(ABC):
    """Interface for generating audio from text"""
    
    @abstractmethod
    def generate_audio(self, text_chunks: List[str], output_name: str, output_dir: str) -> tuple[List[str], Optional[str]]:
        """Generate audio files from text chunks. Returns (individual_files, combined_mp3)"""
        pass

class PageRangeValidator(ABC):
    """Interface for validating page ranges"""
    
    @abstractmethod
    def validate_range(self, pdf_path: str, page_range: PageRange) -> Dict[str, Any]:
        """Validate page range against PDF. Returns validation result"""
        pass

# --- Domain Services Interface ---

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