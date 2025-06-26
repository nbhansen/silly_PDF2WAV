# domain/text/text_pipeline.py - Unified Text Processing Pipeline
"""
Consolidated text processing pipeline that unifies text cleaning and SSML enhancement.
Replaces: TextCleaningService, AcademicSSMLService (as separate concerns)
"""

import re
from typing import List, Optional, TYPE_CHECKING
from abc import ABC, abstractmethod

from ..errors import Result

if TYPE_CHECKING:
    from ..interfaces import ILLMProvider


class ITextPipeline(ABC):
    """Unified interface for text processing operations"""
    
    @abstractmethod
    def clean_text(self, raw_text: str) -> str:
        """Clean and prepare text for TTS"""
        pass
    
    @abstractmethod
    async def clean_text_async(self, raw_text: str) -> str:
        """Clean and prepare text for TTS asynchronously with rate limiting"""
        pass
    
    @abstractmethod
    def enhance_with_ssml(self, text: str) -> str:
        """Add SSML enhancements to text"""
        pass
    
    @abstractmethod
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for processing"""
        pass
    
    @abstractmethod
    def strip_ssml(self, text: str) -> str:
        """Remove SSML tags from text"""
        pass


class TextPipeline(ITextPipeline):
    """
    Unified text processing pipeline with high cohesion.
    Handles cleaning, SSML enhancement, and sentence splitting in one place.
    """
    
    def __init__(
        self,
        llm_provider: Optional['ILLMProvider'] = None,
        enable_cleaning: bool = True,
        enable_ssml: bool = True,
        document_type: str = "research_paper",
        tts_supports_ssml: bool = True
    ):
        self.llm_provider = llm_provider
        self.enable_cleaning = enable_cleaning
        self.enable_ssml = enable_ssml
        self.document_type = document_type
        self.tts_supports_ssml = tts_supports_ssml
        
        # If TTS doesn't support SSML, disable SSML enhancement
        if not self.tts_supports_ssml:
            self.enable_ssml = False
    
    def clean_text(self, raw_text: str) -> str:
        """Clean and prepare text for TTS processing"""
        if not self.enable_cleaning or not self.llm_provider:
            return self._basic_text_cleanup(raw_text)
        
        try:
            # Use LLM for advanced cleaning
            cleaning_prompt = self._generate_cleaning_prompt(raw_text)
            result = self.llm_provider.generate_content(cleaning_prompt)
            
            if result.is_success:
                cleaned = result.value
                # Basic validation of LLM output
                if cleaned and len(cleaned) > len(raw_text) * 0.3:  # At least 30% of original length
                    return self._basic_text_cleanup(cleaned)
            
            # Fallback to basic cleaning if LLM fails
            return self._basic_text_cleanup(raw_text)
            
        except Exception as e:
            print(f"TextPipeline: LLM cleaning failed: {e}")
            return self._basic_text_cleanup(raw_text)
    
    async def clean_text_async(self, raw_text: str) -> str:
        """Clean and prepare text for TTS processing asynchronously"""
        if not self.enable_cleaning or not self.llm_provider:
            return self._basic_text_cleanup(raw_text)
        
        # Check if async method is available
        if not hasattr(self.llm_provider, 'generate_content_async'):
            print("TextPipeline: Async cleaning not available, using sync method")
            return self.clean_text(raw_text)
        
        try:
            # Use async LLM for advanced cleaning with rate limiting
            cleaning_prompt = self._generate_cleaning_prompt(raw_text)
            result = await self.llm_provider.generate_content_async(cleaning_prompt)
            
            if result.is_success:
                cleaned = result.value
                # Basic validation of LLM output
                if cleaned and len(cleaned) > len(raw_text) * 0.3:  # At least 30% of original length
                    return self._basic_text_cleanup(cleaned)
            
            # Fallback to basic cleaning if LLM fails
            return self._basic_text_cleanup(raw_text)
            
        except Exception as e:
            print(f"TextPipeline: Async LLM cleaning failed: {e}")
            return self._basic_text_cleanup(raw_text)
    
    def enhance_with_ssml(self, text: str) -> str:
        """Add SSML enhancements or natural formatting for better speech synthesis"""
        # If TTS doesn't support SSML, use natural formatting instead
        if not self.tts_supports_ssml:
            return self._enhance_with_natural_formatting(text)
        
        if not self.enable_ssml:
            return text
        
        enhanced = text
        
        # Order matters: do non-interfering enhancements first
        
        # 1. Add emphasis for quotes first (won't interfere with other patterns)
        enhanced = self._add_emphasis_markup(enhanced)
        
        # 2. Add technical term emphasis (works on remaining text)
        if self.document_type == "research_paper":
            enhanced = self._enhance_technical_terms(enhanced)
        
        # 3. Add structural breaks and pauses (work on any text)
        if self.document_type == "research_paper":
            enhanced = self._add_academic_pauses(enhanced)
        
        enhanced = self._add_punctuation_breaks(enhanced)
        
        return enhanced
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for individual processing"""
        # Clean SSML first if present
        clean_text = self.strip_ssml(text)
        
        # Handle abbreviations better - don't split on Dr., Mr., etc.
        # Basic sentence splitting with common edge cases
        sentences = re.split(r'(?<!\bDr\.)(?<!\bMr\.)(?<!\bMs\.)(?<!\bProf\.)(?<=[.!?])\s+(?=[A-Z])', clean_text)
        
        # Filter out very short sentences and clean up
        filtered_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Minimum length filter
                filtered_sentences.append(sentence)
        
        return filtered_sentences
    
    def strip_ssml(self, text: str) -> str:
        """Remove SSML tags from text"""
        # Remove all SSML tags but preserve spacing
        clean = re.sub(r'<[^>]+>', ' ', text)
        
        # Normalize whitespace but preserve single spaces
        clean = re.sub(r'\s+', ' ', clean)
        
        return clean.strip()
    
    def _basic_text_cleanup(self, text: str) -> str:
        """Basic text cleanup without LLM"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common PDF artifacts
        text = re.sub(r'\f', ' ', text)  # Form feed
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Non-ASCII characters
        
        # Clean up punctuation
        text = re.sub(r'\.{3,}', '...', text)  # Multiple dots
        text = re.sub(r'-{2,}', '--', text)  # Multiple dashes
        
        return text.strip()
    
    def _generate_cleaning_prompt(self, text: str) -> str:
        """Generate LLM prompt for text cleaning"""
        if self.tts_supports_ssml:
            pause_instruction = 'Add appropriate pauses with "..." between major sections.'
        else:
            pause_instruction = '''Use natural punctuation for better speech rhythm:
- Use "..." for medium pauses (between paragraphs or sections)
- Use "...." or "....." for longer pauses (after major sections)
- Add extra commas where natural pauses would occur in speech
- Use line breaks to create natural breathing points'''
        
        return f"""Clean the following text for text-to-speech conversion. 
Remove headers, footers, page numbers, and artifacts. 
{pause_instruction}
Preserve the main content and structure.
Document type: {self.document_type}

Text to clean:
{text[:5000]}"""  # Limit prompt size
    
    def _add_academic_pauses(self, text: str) -> str:
        """Add pauses for academic content"""
        # Add pauses after section headers (case insensitive)
        text = re.sub(r'(Abstract|Introduction|Conclusion|References)(\s*[:\.]?\s*)', 
                      r'\1\2<break time="1s"/>', text, flags=re.IGNORECASE)
        
        # Add pauses after numbered sections
        text = re.sub(r'(\d+\.\s*[A-Z][^.]*\.)', r'\1<break time="0.5s"/>', text)
        
        return text
    
    def _enhance_technical_terms(self, text: str) -> str:
        """Add emphasis to technical terms"""
        # Common technical terms that benefit from emphasis
        # Avoid words already inside SSML tags
        technical_patterns = [
            r'\b(algorithm|method|approach|technique|system)\b',
            r'\b(significant|important|critical|essential)\b',
            r'\b(however|therefore|furthermore|moreover)\b'
        ]
        
        for pattern in technical_patterns:
            # Use negative lookbehind/lookahead to avoid words inside SSML tags
            enhanced_pattern = r'(?<!>)' + pattern + r'(?!<)'
            text = re.sub(enhanced_pattern, r'<emphasis level="moderate">\1</emphasis>', text, flags=re.IGNORECASE)
        
        return text
    
    def _add_emphasis_markup(self, text: str) -> str:
        """Add emphasis for naturally emphasized text"""
        # Emphasize text in quotes
        text = re.sub(r'"([^"]+)"', r'<emphasis level="moderate">"\1"</emphasis>', text)
        
        return text
    
    def _add_punctuation_breaks(self, text: str) -> str:
        """Add appropriate breaks for punctuation"""
        # Short pause after commas
        text = re.sub(r',(\s+)', r',<break time="0.2s"/>\1', text)
        
        # Medium pause after semicolons
        text = re.sub(r';(\s+)', r';<break time="0.3s"/>\1', text)
        
        # Longer pause after periods, exclamations, questions (with or without following space)
        text = re.sub(r'([.!?])(\s+|$)', r'\1<break time="0.5s"/>\2', text)
        
        return text
    
    def _enhance_with_natural_formatting(self, text: str) -> str:
        """Apply natural formatting tricks for TTS engines without SSML support"""
        enhanced = text
        
        # 1. Add natural emphasis (order matters)
        enhanced = self._add_natural_emphasis(enhanced)
        
        # 2. Add academic formatting for research papers
        if self.document_type == "research_paper":
            enhanced = self._add_natural_academic_formatting(enhanced)
        
        # 3. Enhance punctuation for better rhythm
        enhanced = self._enhance_punctuation_for_natural_speech(enhanced)
        
        return enhanced
    
    def _add_natural_emphasis(self, text: str) -> str:
        """Add natural emphasis without SSML tags"""
        # Already quoted text gets natural emphasis from quotes
        # No changes needed for quoted text as TTS engines naturally emphasize quotes
        
        # For research papers, we could uppercase key transitional words
        # But this might sound unnatural, so we'll rely on punctuation
        
        return text
    
    def _add_natural_academic_formatting(self, text: str) -> str:
        """Add natural formatting for academic content without SSML"""
        # Add extra dots after section headers for longer pauses
        text = re.sub(r'(Abstract|Introduction|Conclusion|References)(\s*[:\.]?\s*)', 
                      r'\1\2... ', text, flags=re.IGNORECASE)
        
        # Add pause after numbered sections with extra dots
        text = re.sub(r'(\d+\.\s*[A-Z][^.]*\.)', r'\1.. ', text)
        
        # Add line breaks around major transitions for natural pauses
        text = re.sub(r'(However|Therefore|Furthermore|Moreover),', r'\n\1,', text, flags=re.IGNORECASE)
        
        return text
    
    def _enhance_punctuation_for_natural_speech(self, text: str) -> str:
        """Enhance punctuation for better natural speech rhythm"""
        # Add extra comma pauses where beneficial
        # After introductory phrases
        text = re.sub(r'^(In this paper|In this study|We present|We propose|This work),', 
                      r'\1,,', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Convert single dots between sentences to double for slightly longer pauses
        # But preserve ellipsis (...)
        text = re.sub(r'(?<![.])\.(?![.])\s+(?=[A-Z])', r'.. ', text)
        
        # Add commas after "First", "Second", etc. if not already present
        text = re.sub(r'\b(First|Second|Third|Fourth|Fifth|Finally|Additionally|Specifically)(?!,)\s', 
                      r'\1, ', text, flags=re.IGNORECASE)
        
        # Ensure ellipsis has consistent spacing
        text = re.sub(r'\.{3,}', '... ', text)
        
        return text