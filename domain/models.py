# domain/models.py
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
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

# --- Configuration Models (moved from tts_utils.py) ---
@dataclass
class TTSConfig:
    """Unified TTS configuration with common parameters and engine-specific sections"""
    voice_quality: str = "medium"  # low/medium/high
    speaking_style: str = "neutral"  # casual/professional/narrative
    speed: float = 1.0
    
    # Engine-specific configs
    coqui: Optional['CoquiConfig'] = None
    gtts: Optional['GTTSConfig'] = None
    bark: Optional['BarkConfig'] = None
    gemini: Optional['GeminiConfig'] = None

@dataclass
class CoquiConfig:
    model_name: Optional[str] = None
    speaker: Optional[str] = None
    use_gpu: Optional[bool] = None

@dataclass
class GTTSConfig:
    lang: str = "en"
    tld: str = "co.uk"
    slow: bool = False

@dataclass
class BarkConfig:
    use_gpu: Optional[bool] = None
    use_small_models: Optional[bool] = None
    history_prompt: Optional[str] = None

@dataclass
class GeminiConfig:
    voice_name: str = "Kore"
    style_prompt: Optional[str] = None
    api_key: Optional[str] = None

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