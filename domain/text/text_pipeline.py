# domain/text/text_pipeline.py - Unified Text Processing Pipeline
"""
Consolidated text processing pipeline that unifies text cleaning and SSML enhancement.
Replaces: TextCleaningService, AcademicSSMLService (as separate concerns)
"""

import re
from typing import List, Optional
from abc import ABC, abstractmethod

from ..errors import Result


class ITextPipeline(ABC):
    """Unified interface for text processing operations"""
    
    @abstractmethod
    def clean_text(self, raw_text: str) -> str:
        """Clean and prepare text for TTS"""
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
        document_type: str = "research_paper"
    ):
        self.llm_provider = llm_provider
        self.enable_cleaning = enable_cleaning
        self.enable_ssml = enable_ssml
        self.document_type = document_type
    
    def clean_text(self, raw_text: str) -> str:
        """Clean and prepare text for TTS processing"""
        if not self.enable_cleaning or not self.llm_provider:
            return self._basic_text_cleanup(raw_text)
        
        try:
            # Use LLM for advanced cleaning
            cleaning_prompt = self._generate_cleaning_prompt(raw_text)
            result = self.llm_provider.generate_text(cleaning_prompt)
            
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
    
    def enhance_with_ssml(self, text: str) -> str:
        """Add SSML enhancements for better speech synthesis"""
        if not self.enable_ssml:
            return text
        
        enhanced = text
        
        # Add pauses for academic reading
        if self.document_type == "research_paper":
            enhanced = self._add_academic_pauses(enhanced)
            enhanced = self._enhance_technical_terms(enhanced)
        
        # Add emphasis for important terms
        enhanced = self._add_emphasis_markup(enhanced)
        
        # Add breaks for punctuation
        enhanced = self._add_punctuation_breaks(enhanced)
        
        return enhanced
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for individual processing"""
        # Clean SSML first if present
        clean_text = self.strip_ssml(text)
        
        # Basic sentence splitting with common edge cases
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', clean_text)
        
        # Filter out very short sentences and clean up
        filtered_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Minimum length filter
                filtered_sentences.append(sentence)
        
        return filtered_sentences
    
    def strip_ssml(self, text: str) -> str:
        """Remove SSML tags from text"""
        # Remove all SSML tags
        clean = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace
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
        return f"""Clean the following text for text-to-speech conversion. 
Remove headers, footers, page numbers, and artifacts. 
Add appropriate pauses with "..." between major sections.
Preserve the main content and structure.
Document type: {self.document_type}

Text to clean:
{text[:5000]}"""  # Limit prompt size
    
    def _add_academic_pauses(self, text: str) -> str:
        """Add pauses for academic content"""
        # Add pauses after section headers
        text = re.sub(r'(Abstract|Introduction|Conclusion|References)(\s*[:\.]?\s*)', 
                      r'\1\2<break time="1s"/>', text)
        
        # Add pauses after numbered sections
        text = re.sub(r'(\d+\.\s*[A-Z][^.]*\.)', r'\1<break time="0.5s"/>', text)
        
        return text
    
    def _enhance_technical_terms(self, text: str) -> str:
        """Add emphasis to technical terms"""
        # Common technical terms that benefit from emphasis
        technical_patterns = [
            r'\b(algorithm|method|approach|technique|system)\b',
            r'\b(significant|important|critical|essential)\b',
            r'\b(however|therefore|furthermore|moreover)\b'
        ]
        
        for pattern in technical_patterns:
            text = re.sub(pattern, r'<emphasis level="moderate">\1</emphasis>', text, flags=re.IGNORECASE)
        
        return text
    
    def _add_emphasis_markup(self, text: str) -> str:
        """Add emphasis for naturally emphasized text"""
        # Emphasize text in quotes
        text = re.sub(r'"([^"]+)"', r'<emphasis level="moderate">"\1"</emphasis>', text)
        
        # Emphasize capitalized words (but not all caps)
        text = re.sub(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', r'<emphasis level="reduced">\1</emphasis>', text)
        
        return text
    
    def _add_punctuation_breaks(self, text: str) -> str:
        """Add appropriate breaks for punctuation"""
        # Short pause after commas
        text = re.sub(r',(\s+)', r',<break time="0.2s"/>\1', text)
        
        # Medium pause after semicolons
        text = re.sub(r';(\s+)', r';<break time="0.3s"/>\1', text)
        
        # Longer pause after periods, exclamations, questions
        text = re.sub(r'([.!?])(\s+)', r'\1<break time="0.5s"/>\2', text)
        
        return text