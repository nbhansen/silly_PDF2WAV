# domain/interfaces.py - Complete Business Logic Interfaces with SSML Support
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
from enum import Enum
from .models import PDFInfo, PageRange, ProcessingRequest, ProcessingResult

# === SSML Support Enums and Types ===

class SSMLCapability(Enum):
    """SSML support levels for TTS engines"""
    NONE = "none"           # No SSML support, strips all tags
    BASIC = "basic"         # Basic tags: break, emphasis, prosody, say-as
    ADVANCED = "advanced"   # Basic + voice, audio (some advanced features)
    FULL = "full"          # Complete SSML specification support

class SSMLTagSupport(Enum):
    """Individual SSML tag support"""
    SPEAK = "speak"
    BREAK = "break" 
    EMPHASIS = "emphasis"
    PROSODY = "prosody"
    SAY_AS = "say-as"
    VOICE = "voice"
    AUDIO = "audio"
    MARK = "mark"
    PARAGRAPH = "p"
    SENTENCE = "s"
    SUBSTITUTE = "sub"
    PHONEME = "phoneme"

# === SSML Processing Interfaces ===

class ISSMLProcessor(ABC):
    """Interface for SSML processing capabilities"""
    
    @abstractmethod
    def get_ssml_capability(self) -> SSMLCapability:
        """Get the SSML support level of this engine"""
        pass
    
    @abstractmethod
    def process_ssml(self, ssml_text: str) -> str:
        """
        Process SSML for this engine (convert, validate, or strip as needed)
        
        Args:
            ssml_text: Input text that may contain SSML markup
            
        Returns:
            Processed text suitable for this engine
        """
        pass
    
    @abstractmethod
    def get_supported_tags(self) -> List[str]:
        """
        Get list of supported SSML tag names
        
        Returns:
            List of tag names this engine supports (e.g., ['break', 'emphasis'])
        """
        pass
    
    def validate_ssml(self, ssml_text: str) -> Dict[str, Any]:
        """
        Validate SSML markup for this engine (optional implementation)
        
        Returns:
            Dictionary with 'valid' bool and optional 'errors' list
        """
        return {'valid': True, 'errors': []}

class ISSMLGenerator(ABC):
    """Interface for generating SSML markup"""
    
    @abstractmethod
    def generate_ssml_for_academic_content(self, text: str, target_capability: SSMLCapability) -> str:
        """
        Generate SSML markup optimized for academic content
        
        Args:
            text: Clean academic text
            target_capability: Target SSML support level
            
        Returns:
            Text with appropriate SSML markup
        """
        pass
    
    @abstractmethod
    def enhance_numbers_and_dates(self, text: str) -> str:
        """Add SSML markup for better number and date pronunciation"""
        pass
    
    @abstractmethod
    def add_natural_pauses(self, text: str) -> str:
        """Add appropriate pause markup for natural speech flow"""
        pass
    
    @abstractmethod
    def emphasize_key_terms(self, text: str) -> str:
        """Add emphasis markup for important academic terms"""
        pass

# === External Service Interfaces ===

class ILLMProvider(ABC):
    """Interface for Large Language Model providers"""
    
    @abstractmethod
    def generate_content(self, prompt: str) -> str:
        """
        Generates content based on a prompt
        
        Args:
            prompt: Input prompt for the LLM
            
        Returns:
            Generated text content
        """
        pass
    
    def supports_ssml_generation(self) -> bool:
        """Check if this LLM can generate SSML markup (optional)"""
        return False
    
    def get_max_input_length(self) -> int:
        """Get maximum input length for this LLM (optional)"""
        return 100000  # Default reasonable limit

class ITTSEngine(ABC):
    """Enhanced interface for Text-to-Speech engines with SSML support"""
    
    @abstractmethod
    def generate_audio_data(self, text_to_speak: str) -> bytes:
        """
        Generates raw audio data from text
        
        Args:
            text_to_speak: Input text (may contain SSML if supported)
            
        Returns:
            Raw audio bytes in the engine's native format
        """
        pass

    @abstractmethod
    def get_output_format(self) -> str:
        """
        Returns the output format (e.g., 'wav', 'mp3', 'ogg')
        
        Returns:
            File extension of the output format
        """
        pass
    
    # === SSML Support Methods ===
    
    def supports_ssml(self) -> bool:
        """
        Check if engine supports SSML markup
        
        Returns:
            True if SSML is supported, False otherwise
        """
        if isinstance(self, ISSMLProcessor):
            return self.get_ssml_capability() != SSMLCapability.NONE
        return False
    
    def process_text_for_engine(self, text: str) -> str:
        """
        Process text (SSML or plain) for this specific engine
        
        Args:
            text: Input text that may contain SSML
            
        Returns:
            Text processed appropriately for this engine
        """
        if isinstance(self, ISSMLProcessor):
            return self.process_ssml(text)
        return text
    
    def get_engine_capabilities(self) -> Dict[str, Any]:
        """
        Get comprehensive engine capabilities (optional)
        
        Returns:
            Dictionary describing engine features
        """
        capabilities = {
            'output_format': self.get_output_format(),
            'ssml_support': self.supports_ssml()
        }
        
        if isinstance(self, ISSMLProcessor):
            capabilities.update({
                'ssml_capability': self.get_ssml_capability().value,
                'supported_ssml_tags': self.get_supported_tags()
            })
        
        return capabilities

# === Audio Processing Interfaces ===

class IAudioProcessor(ABC):
    """Interface for audio post-processing operations"""
    
    @abstractmethod
    def combine_audio_files(self, audio_files: List[str], output_path: str) -> bool:
        """Combine multiple audio files into one"""
        pass
    
    @abstractmethod
    def convert_audio_format(self, input_path: str, output_path: str, target_format: str) -> bool:
        """Convert audio from one format to another"""
        pass
    
    @abstractmethod
    def normalize_audio_volume(self, audio_path: str) -> bool:
        """Normalize audio volume levels"""
        pass

class IAsyncAudioGenerator(ABC):
    """Interface for asynchronous audio generation"""
    
    @abstractmethod
    async def generate_audio_async(self, text_chunks: List[str], output_name: str, 
                                 output_dir: str) -> Tuple[List[str], Optional[str]]:
        """Generate audio files asynchronously with concurrency control"""
        pass
    
    @abstractmethod
    def get_max_concurrent_requests(self) -> int:
        """Get maximum number of concurrent TTS requests supported"""
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
    
    def supports_ocr(self) -> bool:
        """Check if this extractor supports OCR for image-based PDFs"""
        return False
    
    def get_extraction_method(self, pdf_path: str) -> str:
        """Get the extraction method that will be used (optional)"""
        return "direct"  # or "ocr"

class TextCleaner(ABC):
    """Interface for cleaning and optimizing text"""
    
    @abstractmethod
    def clean_text(self, raw_text: str, llm_provider: Optional[ILLMProvider] = None,
                  target_ssml_capability: SSMLCapability = SSMLCapability.NONE) -> List[str]:
        """
        Clean text and return chunks optimized for TTS, optionally with SSML
        
        Args:
            raw_text: Raw extracted text from PDF
            llm_provider: Optional LLM for advanced cleaning
            target_ssml_capability: Target SSML support level for output
            
        Returns:
            List of cleaned text chunks, potentially with SSML markup
        """
        pass
    
    def supports_ssml_generation(self) -> bool:
        """Check if this cleaner can generate SSML markup"""
        return False
    
    def get_optimal_chunk_size(self, tts_engine: Optional[ITTSEngine] = None) -> int:
        """Get optimal chunk size for the target TTS engine"""
        return 20000  # Default chunk size

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
    
    def supports_async_generation(self) -> bool:
        """Check if this generator supports asynchronous processing"""
        return False
    
    def supports_audio_combining(self) -> bool:
        """Check if this generator can combine multiple audio files"""
        return False
    
    def get_recommended_chunk_count(self, total_text_length: int, 
                                  tts_engine: Optional[ITTSEngine] = None) -> int:
        """Get recommended number of chunks for optimal processing"""
        if tts_engine and hasattr(tts_engine, 'supports_ssml') and tts_engine.supports_ssml():
            # SSML engines might prefer smaller chunks
            return max(1, total_text_length // 15000)
        return max(1, total_text_length // 20000)

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
            - Additional metadata
        """
        pass

# === Application Service Interfaces ===

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
    
    def get_processing_capabilities(self) -> Dict[str, Any]:
        """Get comprehensive processing capabilities (optional)"""
        return {
            'supports_page_ranges': True,
            'supports_ssml': False,
            'supports_async_audio': False,
            'max_file_size_mb': 100
        }
    
    def estimate_processing_time(self, pdf_path: str, page_range: PageRange) -> Dict[str, Any]:
        """Estimate processing time for a PDF (optional)"""
        return {
            'estimated_minutes': 5,
            'factors': ['file_size', 'page_count', 'tts_engine']
        }

# === Configuration and Factory Interfaces ===

class ITTSEngineFactory(ABC):
    """Factory interface for creating TTS engines"""
    
    @abstractmethod
    def create_engine(self, engine_name: str, config: Dict[str, Any]) -> ITTSEngine:
        """Create TTS engine by name and configuration"""
        pass
    
    @abstractmethod
    def get_available_engines(self) -> List[str]:
        """Get list of available TTS engine names"""
        pass
    
    @abstractmethod
    def get_engine_info(self, engine_name: str) -> Dict[str, Any]:
        """Get information about a specific engine"""
        pass

class IConfigurationProvider(ABC):
    """Interface for configuration management"""
    
    @abstractmethod
    def get_tts_config(self, engine_name: str) -> Dict[str, Any]:
        """Get configuration for TTS engine"""
        pass
    
    @abstractmethod
    def get_processing_config(self) -> Dict[str, Any]:
        """Get general processing configuration"""
        pass
    
    @abstractmethod
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration"""
        pass

# === Error Handling Interfaces ===

class IErrorHandler(ABC):
    """Interface for error handling and recovery"""
    
    @abstractmethod
    def handle_extraction_error(self, error: Exception, pdf_path: str) -> str:
        """Handle text extraction errors"""
        pass
    
    @abstractmethod
    def handle_tts_error(self, error: Exception, text_chunk: str) -> bytes:
        """Handle TTS generation errors"""
        pass
    
    @abstractmethod
    def should_retry(self, error: Exception, attempt_count: int) -> bool:
        """Determine if operation should be retried"""
        pass

# === Monitoring and Logging Interfaces ===

class IProcessingMonitor(ABC):
    """Interface for monitoring processing progress"""
    
    @abstractmethod
    def log_processing_start(self, request: ProcessingRequest) -> None:
        """Log start of processing"""
        pass
    
    @abstractmethod
    def log_processing_step(self, step: str, details: Dict[str, Any]) -> None:
        """Log individual processing step"""
        pass
    
    @abstractmethod
    def log_processing_complete(self, result: ProcessingResult) -> None:
        """Log completion of processing"""
        pass
    
    @abstractmethod
    def get_processing_metrics(self) -> Dict[str, Any]:
        """Get processing performance metrics"""
        pass

# === Quality and Validation Interfaces ===

class IAudioQualityAnalyzer(ABC):
    """Interface for analyzing generated audio quality"""
    
    @abstractmethod
    def analyze_audio_quality(self, audio_path: str) -> Dict[str, Any]:
        """Analyze quality of generated audio"""
        pass
    
    @abstractmethod
    def validate_audio_duration(self, audio_path: str, expected_text_length: int) -> bool:
        """Validate that audio duration matches expected length"""
        pass

class ITextQualityValidator(ABC):
    """Interface for validating cleaned text quality"""
    
    @abstractmethod
    def validate_cleaned_text(self, original_text: str, cleaned_text: str) -> Dict[str, Any]:
        """Validate that text cleaning preserved important content"""
        pass
    
    @abstractmethod
    def check_ssml_validity(self, ssml_text: str, target_capability: SSMLCapability) -> Dict[str, Any]:
        """Validate SSML markup for target capability level"""
        pass

# === Plugin and Extension Interfaces ===

class ITTSPlugin(ABC):
    """Interface for TTS engine plugins"""
    
    @abstractmethod
    def get_plugin_name(self) -> str:
        """Get plugin name"""
        pass
    
    @abstractmethod
    def get_supported_engines(self) -> List[str]:
        """Get list of TTS engines this plugin supports"""
        pass
    
    @abstractmethod
    def enhance_engine(self, engine: ITTSEngine) -> ITTSEngine:
        """Enhance TTS engine with additional capabilities"""
        pass

class ITextProcessingPlugin(ABC):
    """Interface for text processing plugins"""
    
    @abstractmethod
    def get_plugin_name(self) -> str:
        """Get plugin name"""
        pass
    
    @abstractmethod
    def process_text_chunk(self, text: str, context: Dict[str, Any]) -> str:
        """Process individual text chunk"""
        pass
    
    @abstractmethod
    def get_processing_priority(self) -> int:
        """Get processing priority (lower = higher priority)"""
        pass