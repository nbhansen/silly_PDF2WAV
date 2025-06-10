# domain/services/ssml_pipeline.py - Centralized SSML Processing
from dataclasses import dataclass
from typing import Optional, List
from domain.interfaces import ITTSEngine, ISSMLProcessor, SSMLCapability
from domain.services.ssml_generation_service import SSMLGenerationService, AcademicSSMLEnhancer

@dataclass
class SSMLConfig:
    """Configuration for SSML processing"""
    enabled: bool = True
    document_type: str = "research_paper"  # research_paper, literature_review, etc.
    force_capability: Optional[SSMLCapability] = None  # Override auto-detection

class SSMLPipeline:
    """
    Centralized SSML processing pipeline
    
    Encapsulates all SSML concerns:
    - Capability detection
    - Text enhancement
    - Engine-specific processing
    - Configuration management
    """
    
    def __init__(self, tts_engine: ITTSEngine, config: SSMLConfig):
        self.tts_engine = tts_engine
        self.config = config
        self.capability = self._detect_capability()
        self.generator = self._create_generator()
        self.processor = self._create_processor()
        
        print(f"SSMLPipeline: Initialized with capability={self.capability.value}, enabled={config.enabled}")
    
    def process_text(self, text: str) -> str:
        """
        Main entry point - processes text through complete SSML pipeline
        
        Args:
            text: Input text (cleaned academic content)
            
        Returns:
            SSML-enhanced text ready for TTS engine
        """
        if not self.config.enabled or self.capability == SSMLCapability.NONE:
            return text
        
        # Generate SSML markup
        enhanced_text = self.generator.generate_ssml_for_academic_content(text, self.capability)
        
        # Process for specific TTS engine
        if self.processor:
            return self.processor.process_ssml(enhanced_text)
        
        return enhanced_text
    
    def process_text_chunks(self, text_chunks: List[str]) -> List[str]:
        """Process multiple text chunks through SSML pipeline"""
        return [self.process_text(chunk) for chunk in text_chunks]
    
    def get_capability(self) -> SSMLCapability:
        """Get the detected SSML capability"""
        return self.capability
    
    def is_enabled(self) -> bool:
        """Check if SSML processing is enabled"""
        return self.config.enabled and self.capability != SSMLCapability.NONE
    
    def get_optimal_chunk_size(self) -> int:
        """Get optimal chunk size for SSML processing"""
        if self.capability == SSMLCapability.NONE:
            return 20000
        else:
            return 15000  # Smaller chunks for SSML
    
    # === Private Implementation ===
    
    def _detect_capability(self) -> SSMLCapability:
        """Detect SSML capability of TTS engine"""
        # Override if forced in config
        if self.config.force_capability:
            return self.config.force_capability
        
        # Detect from engine
        if isinstance(self.tts_engine, ISSMLProcessor):
            return self.tts_engine.get_ssml_capability()
        
        # Check basic support
        if hasattr(self.tts_engine, 'supports_ssml') and self.tts_engine.supports_ssml():
            return SSMLCapability.BASIC
        
        return SSMLCapability.NONE
    
    def _create_generator(self) -> Optional[SSMLGenerationService]:
        """Create appropriate SSML generator"""
        if self.capability == SSMLCapability.NONE:
            return None
        
        # Use academic enhancer for academic documents
        if self.config.document_type in ['research_paper', 'literature_review', 'dissertation']:
            return AcademicSSMLEnhancer(self.config.document_type)
        else:
            return SSMLGenerationService(self.capability)
    
    def _create_processor(self) -> Optional[ISSMLProcessor]:
        """Create SSML processor for TTS engine"""
        if isinstance(self.tts_engine, ISSMLProcessor):
            return self.tts_engine
        return None


class NullSSMLPipeline(SSMLPipeline):
    """Null object pattern - no SSML processing"""
    
    def __init__(self):
        self.capability = SSMLCapability.NONE
        self.config = SSMLConfig(enabled=False)
        
    def process_text(self, text: str) -> str:
        return text
    
    def process_text_chunks(self, text_chunks: List[str]) -> List[str]:
        return text_chunks
    
    def is_enabled(self) -> bool:
        return False


def create_ssml_pipeline(tts_engine: ITTSEngine, config: SSMLConfig) -> SSMLPipeline:
    """Factory function to create SSML pipeline"""
    if not config.enabled:
        return NullSSMLPipeline()
    
    return SSMLPipeline(tts_engine, config)