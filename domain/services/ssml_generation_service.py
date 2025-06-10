# domain/services/ssml_generation_service.py - Complete SSML Generation for Academic Content
import re
from typing import Dict, List, Optional
from domain.interfaces import ISSMLGenerator, SSMLCapability

class SSMLGenerationService(ISSMLGenerator):
    """
    Service for generating SSML markup optimized for academic content
    """
    
    def __init__(self, target_capability: SSMLCapability = SSMLCapability.ADVANCED):
        self.target_capability = target_capability
        self.academic_terms = self._load_academic_terms()
        self.emphasis_words = self._load_emphasis_words()
        self.technical_patterns = self._load_technical_patterns()
    
    def generate_ssml_for_academic_content(self, text: str, target_capability: SSMLCapability) -> str:
        """
        Generate SSML markup optimized for academic content
        """
        if target_capability == SSMLCapability.NONE:
            return text
        
        # Start with the input text
        ssml_text = text.strip()
        
        # Apply transformations based on capability level
        if target_capability in [SSMLCapability.BASIC, SSMLCapability.ADVANCED, SSMLCapability.FULL]:
            ssml_text = self.add_natural_pauses(ssml_text)
            ssml_text = self.emphasize_key_terms(ssml_text)
        
        if target_capability in [SSMLCapability.ADVANCED, SSMLCapability.FULL]:
            ssml_text = self.enhance_numbers_and_dates(ssml_text)
            ssml_text = self._add_prosody_for_technical_terms(ssml_text)
        
        if target_capability == SSMLCapability.FULL:
            ssml_text = self._add_advanced_features(ssml_text)
        
        # Structure the content
        ssml_text = self._structure_content(ssml_text, target_capability)
        
        # Wrap in speak tags
        if not ssml_text.strip().startswith('<speak>'):
            ssml_text = f'<speak>\n{ssml_text}\n</speak>'
        
        return ssml_text
    
    def enhance_numbers_and_dates(self, text: str) -> str:
        """Add SSML markup for better number and date pronunciation"""
        # Handle percentages
        text = re.sub(
            r'\b(\d+(?:\.\d+)?)\s*percent\b',
            r'<say-as interpret-as="number">\1</say-as> percent',
            text,
            flags=re.IGNORECASE
        )
        
        # Handle large numbers with decimals
        text = re.sub(
            r'\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\b',
            r'<say-as interpret-as="number">\1</say-as>',
            text
        )
        
        # Handle years (4-digit numbers that likely represent years)
        text = re.sub(
            r'\b(19\d{2}|20\d{2})\b',
            r'<say-as interpret-as="date" format="y">\1</say-as>',
            text
        )
        
        # Handle statistical significance (p-values)
        text = re.sub(
            r'\bp\s*[<>=]\s*(\d+(?:\.\d+)?)',
            r'p <say-as interpret-as="number">\1</say-as>',
            text,
            flags=re.IGNORECASE
        )
        
        # Handle ordinal numbers in academic contexts
        text = re.sub(
            r'\b(\d+)(?:st|nd|rd|th)\s+(century|chapter|section|study|experiment)\b',
            r'<say-as interpret-as="ordinal">\1</say-as> \2',
            text,
            flags=re.IGNORECASE
        )
        
        return text
    
    def add_natural_pauses(self, text: str) -> str:
        """Add appropriate pause markup for natural speech flow"""
        
        # Replace existing pause markers with SSML breaks
        text = re.sub(r'\.{3}\s*\.{3}', '<break time="1s"/>', text)
        text = re.sub(r'\.{3}', '<break time="500ms"/>', text)
        
        # Add pauses after transition words (more specific patterns)
        transition_patterns = [
            # However, Nevertheless, etc.
            (r'\b(However|Nevertheless|Nonetheless|Furthermore|Moreover|Additionally)\b,?\s*',
            r'<break time="300ms"/>\1,<break time="500ms"/>'),
            # Therefore, Consequently, etc.  
            (r'\b(Therefore|Consequently|Thus|Hence|As a result)\b,?\s*',
            r'<break time="300ms"/>\1,<break time="400ms"/>'),
            # In contrast, On the other hand, etc.
            (r'\b(In contrast|On the other hand|Conversely)\b,?\s*',
            r'<break time="400ms"/>\1,<break time="600ms"/>'),
            # Conclusion words
            (r'\b(In conclusion|To summarize|In summary|Finally)\b,?\s*',
            r'<break time="500ms"/>\1,<break time="700ms"/>')
        ]
        
        for pattern, replacement in transition_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Add pauses around parenthetical information (longer than 10 chars)
        text = re.sub(
            r'\s*\(([^)]{10,})\)\s*',
            r' <break time="200ms"/>(\1)<break time="300ms"/> ',
            text
        )
        
        # Add pauses after section headers
        text = re.sub(
            r'^(\d+\.?\s+[A-Z][^.!?]*[.!?])\s*',
            r'\1<break time="800ms"/>',
            text,
            flags=re.MULTILINE
        )
        
        # Add pauses before enumeration
        text = re.sub(
            r'\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b,?\s*',
            r'<break time="200ms"/>\1,<break time="300ms"/>',
            text,
            flags=re.IGNORECASE
        )
        
        return text
    
    def emphasize_key_terms(self, text: str) -> str:
        """Add emphasis markup for important academic terms"""
        
        # Avoid double-processing already emphasized text
        def add_emphasis_if_not_present(word, text_content):
            # Check if word is already in emphasis tags
            if f'<emphasis level="moderate">{word}</emphasis>' not in text_content:
                pattern = f'\\b{word}\\b'
                replacement = f'<emphasis level="moderate">{word}</emphasis>'
                return re.sub(pattern, replacement, text_content, flags=re.IGNORECASE)
            return text_content
        
        # Apply emphasis to significance words
        for word in self.emphasis_words['significance']:
            text = add_emphasis_if_not_present(word, text)
        
        # Apply emphasis to finding words  
        for word in self.emphasis_words['findings']:
            text = add_emphasis_if_not_present(word, text)
        
        # Apply emphasis to methodology words
        for word in self.emphasis_words['methodology']:
            text = add_emphasis_if_not_present(word, text)
        
        return text
    
    def _add_prosody_for_technical_terms(self, text: str) -> str:
        """Add prosody markup for technical terms and acronyms"""
        # Slow down acronyms and technical abbreviations
        text = re.sub(
            r'\b([A-Z]{2,6})\b',
            r'<prosody rate="slow">\1</prosody>',
            text
        )
        
        # Slow down technical terms that might be hard to pronounce
        for term in self.academic_terms['technical']:
            pattern = f'\\b{term}\\b'
            replacement = f'<prosody rate="90%">{term}</prosody>'
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Adjust pitch for emphasis on key findings
        text = re.sub(
            r'\b(significant|important|critical|essential|fundamental)\s+(difference|improvement|increase|decrease|correlation|relationship)\b',
            r'<prosody pitch="+5%" rate="95%">\1 \2</prosody>',
            text,
            flags=re.IGNORECASE
        )
        
        return text
    
    def _add_advanced_features(self, text: str) -> str:
        """Add advanced SSML features for engines with full support"""
        # Add markers for navigation (useful for long documents)
        text = re.sub(
            r'^(Abstract|Introduction|Methods?|Results?|Discussion|Conclusion)\.?\s*$',
            r'<mark name="\1"/>\1.<break time="1s"/>',
            text,
            flags=re.MULTILINE | re.IGNORECASE
        )
        
        # Add audio cues for citations (placeholder - would need actual audio files)
        text = re.sub(
            r'\[(\d+(?:[-,]\d+)*)\]',
            r'<break time="100ms"/>[citation \1]<break time="100ms"/>',
            text
        )
        
        return text
    
    def _structure_content(self, text: str, capability: SSMLCapability) -> str:
        """Structure content with appropriate paragraph and sentence markup"""
        # Split into paragraphs and add structure
        paragraphs = text.split('\n\n')
        structured_paragraphs = []
        
        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue
            
            # Add paragraph breaks between sections
            if i > 0:
                structured_paragraphs.append('<break time="800ms"/>')
            
            # Process the paragraph
            structured_paragraph = self._process_paragraph(paragraph.strip(), capability)
            structured_paragraphs.append(f'<p>{structured_paragraph}</p>')
        
        return '\n'.join(structured_paragraphs)
    
    def _process_paragraph(self, paragraph: str, capability: SSMLCapability) -> str:
        """Process individual paragraph with sentence-level markup"""
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        processed_sentences = []
        
        for sentence in sentences:
            if sentence.strip():
                # Add sentence markup if supported
                if capability in [SSMLCapability.ADVANCED, SSMLCapability.FULL]:
                    processed_sentences.append(f'<s>{sentence.strip()}</s>')
                else:
                    processed_sentences.append(sentence.strip())
        
        return ' '.join(processed_sentences)
    
    def _load_academic_terms(self) -> Dict[str, List[str]]:
        """Load academic terms that benefit from special pronunciation"""
        return {
            'technical': [
                'methodology', 'hypothesis', 'algorithm', 'statistical',
                'quantitative', 'qualitative', 'correlation', 'regression',
                'multivariate', 'heterogeneous', 'homogeneous', 'paradigm',
                'phenomenon', 'empirical', 'theoretical', 'epistemological'
            ]
        }
    
    def _load_emphasis_words(self) -> Dict[str, List[str]]:
        """Load words that should be emphasized in academic content"""
        return {
            'significance': [
                'significant', 'significantly', 'important', 'importantly',
                'critical', 'crucial', 'essential', 'fundamental', 'key',
                'primary', 'main', 'principal', 'major', 'substantial'
            ],
            'findings': [
                'found', 'discovered', 'revealed', 'demonstrated', 'showed',
                'indicated', 'suggested', 'concluded', 'determined',
                'established', 'confirmed', 'validated'
            ],
            'methodology': [
                'analyzed', 'examined', 'investigated', 'measured',
                'calculated', 'computed', 'assessed', 'evaluated',
                'tested', 'compared', 'contrasted'
            ]
        }
    
    def _load_technical_patterns(self) -> Dict[str, str]:
        """Load patterns for technical content recognition"""
        return {
            'statistical': r'\b(p\s*[<>=]\s*\d+(?:\.\d+)?|r\s*=\s*\d+(?:\.\d+)?|t\s*=\s*\d+(?:\.\d+)?)\b',
            'mathematical': r'\b(equation|formula|theorem|proof|lemma|corollary)\b',
            'citations': r'\[(\d+(?:[-,]\d+)*)\]|\(([^)]+,\s*\d{4})\)'
        }


class AcademicSSMLEnhancer(SSMLGenerationService):
    """
    Enhanced SSML generator specifically tuned for academic papers
    
    This class provides advanced SSML generation tailored to different
    types of academic content (research papers, reviews, dissertations, etc.)
    """
    
    def __init__(self, document_type: str = "research_paper"):
        super().__init__(SSMLCapability.ADVANCED)
        self.document_type = document_type
    
    def generate_ssml_for_academic_content(self, text: str, target_capability: SSMLCapability) -> str:
        """Override to provide academic-specific enhancement"""
        if self.document_type == "research_paper":
            return self.enhance_research_paper(text, target_capability)
        elif self.document_type == "literature_review":
            return self.enhance_literature_review(text, target_capability)
        else:
            # Fall back to parent implementation
            return super().generate_ssml_for_academic_content(text, target_capability)
    
    def enhance_research_paper(self, text: str, target_capability: SSMLCapability) -> str:
        """Generate SSML specifically optimized for research papers"""
        ssml_text = text
        
        # Add specific enhancements for research papers
        ssml_text = self._enhance_abstract(ssml_text, target_capability)
        ssml_text = self._enhance_methodology(ssml_text, target_capability)
        ssml_text = self._enhance_results(ssml_text, target_capability)
        ssml_text = self._enhance_discussion(ssml_text, target_capability)
        
        # Apply general academic enhancements
        return super().generate_ssml_for_academic_content(ssml_text, target_capability)
    
    def enhance_literature_review(self, text: str, target_capability: SSMLCapability) -> str:
        """Generate SSML optimized for literature reviews"""
        ssml_text = text
        
        # Add specific enhancements for literature reviews
        ssml_text = self._enhance_citations_heavy_content(ssml_text, target_capability)
        ssml_text = self._enhance_comparative_language(ssml_text, target_capability)
        
        return super().generate_ssml_for_academic_content(ssml_text, target_capability)
    
    def _enhance_abstract(self, text: str, capability: SSMLCapability) -> str:
        """Add specific enhancements for abstract sections"""
        # Abstracts are dense, add more pauses
        text = re.sub(
            r'\.\s+([A-Z][^.]*(?:found|showed|demonstrated|revealed)[^.]*\.)',
            r'.<break time="600ms"/>\1',
            text
        )
        return text
    
    def _enhance_methodology(self, text: str, capability: SSMLCapability) -> str:
        """Add specific enhancements for methodology sections"""
        # Slow down procedural descriptions
        if capability in [SSMLCapability.ADVANCED, SSMLCapability.FULL]:
            text = re.sub(
                r'\b(participants?|subjects?|procedure|protocol|instrument)\b',
                r'<prosody rate="95%">\1</prosody>',
                text,
                flags=re.IGNORECASE
            )
        return text
    
    def _enhance_results(self, text: str, capability: SSMLCapability) -> str:
        """Add specific enhancements for results sections"""
        # Emphasize statistical findings
        text = re.sub(
            r'\b(F\(\d+,\s*\d+\)\s*=\s*\d+(?:\.\d+)?)',
            r'<emphasis level="moderate">\1</emphasis>',
            text
        )
        return text
    
    def _enhance_discussion(self, text: str, capability: SSMLCapability) -> str:
        """Add specific enhancements for discussion sections"""
        # Add pauses around limitation statements
        text = re.sub(
            r'\b(limitation|weakness|constraint)\b',
            r'<break time="300ms"/>\1<break time="200ms"/>',
            text,
            flags=re.IGNORECASE
        )
        return text
    
    def _enhance_citations_heavy_content(self, text: str, capability: SSMLCapability) -> str:
        """Enhance content with many citations"""
        # Reduce citation noise in literature reviews
        if capability != SSMLCapability.NONE:
            text = re.sub(
                r'\s*\([^)]+,?\s*\d{4}[^)]*\)\s*',
                r' <break time="100ms"/>',
                text
            )
        return text
    
    def _enhance_comparative_language(self, text: str, capability: SSMLCapability) -> str:
        """Enhance comparative language common in literature reviews"""
        comparative_terms = [
            'similarly', 'likewise', 'in contrast', 'conversely',
            'on the other hand', 'alternatively', 'whereas'
        ]
        
        for term in comparative_terms:
            if capability != SSMLCapability.NONE:
                pattern = f'\\b{term}\\b'
                replacement = f'<break time="300ms"/><emphasis level="moderate">{term}</emphasis><break time="400ms"/>'
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text


# Testing functions
def test_ssml_generation():
    """Test SSML generation with sample academic content"""
    
    sample_text = """
    Introduction. This study investigates the correlation between machine learning 
    algorithms and computational efficiency. However, previous research has 
    shown mixed results. Furthermore, the methodology used in earlier studies 
    was limited.
    
    Results. We found a 73.2 percent increase in efficiency during 2024. 
    The statistical analysis revealed F(2, 47) = 15.3, p < 0.001. 
    Therefore, the null hypothesis was rejected.
    """
    
    generator = SSMLGenerationService()
    
    # Test different capability levels
    for capability in SSMLCapability:
        print(f"\n=== {capability.value.upper()} SSML ===")
        result = generator.generate_ssml_for_academic_content(sample_text, capability)
        print(result[:300] + "..." if len(result) > 300 else result)

if __name__ == "__main__":
    test_ssml_generation()