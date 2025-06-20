# domain/services/academic_ssml_service.py - Advanced SSML for Academic Content
import re
import json
import os
from typing import List, Dict, Any
from domain.interfaces import ITTSEngine, SSMLCapability


class AcademicSSMLService:
    """
    Single service for generating advanced SSML markup for academic content.

    Replaces the complex pipeline system with one focused, maintainable service.
    """

    def __init__(self, tts_engine: ITTSEngine, document_type: str = "research_paper", academic_terms_config: str = "config/academic_terms_en.json"):
        self.tts_engine = tts_engine
        self.document_type = document_type
        self.capability = self._detect_engine_capability()
        self.academic_terms = self._load_academic_terms(academic_terms_config)

        # Default academic terminology (fallback)
        self.default_academic_terms = {
            'significance': ['significant', 'significantly', 'important', 'crucial', 'essential', 'key', 'primary', 'major'],
            'findings': ['found', 'discovered', 'revealed', 'demonstrated', 'showed', 'indicated', 'concluded', 'established'],
            'methodology': ['analyzed', 'examined', 'investigated', 'measured', 'calculated', 'assessed', 'evaluated', 'tested'],
            'transition': ['however', 'therefore', 'furthermore', 'moreover', 'consequently', 'nevertheless', 'nonetheless']
        }

    def _load_academic_terms(self, config_path: str) -> Dict:
        """Load academic terms from configuration file"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    terms = json.load(f)
                print(f"Loaded academic terms from {config_path}")
                return terms
            else:
                print(f"Warning: Academic terms config not found at {config_path}, using defaults")
                return {}
        except Exception as e:
            print(f"Warning: Failed to load academic terms from {config_path}: {e}")
            return {}

        print(f"AcademicSSMLService: Initialized for {self.document_type} with {self.capability.value} SSML support")

    def enhance_text_chunks(self, text_chunks: List[str]) -> List[str]:
        """
        Main entry point: enhance text chunks with advanced SSML

        Args:
            text_chunks: List of cleaned text chunks

        Returns:
            List of SSML-enhanced text chunks
        """
        if self.capability == SSMLCapability.NONE:
            # No SSML support - add simple pause markers
            return [self._add_pause_markers(chunk) for chunk in text_chunks]

        enhanced_chunks = []
        for i, chunk in enumerate(text_chunks):
            if chunk.strip() and not chunk.startswith("Error"):
                enhanced = self._enhance_single_chunk(chunk, i + 1, len(text_chunks))
                enhanced_chunks.append(enhanced)
            else:
                enhanced_chunks.append(chunk)

        return enhanced_chunks

    def _enhance_single_chunk(self, text: str, chunk_number: int, total_chunks: int) -> str:
        """Enhance a single text chunk with advanced SSML"""

        # Start with the text
        enhanced_text = text.strip()

        # Apply enhancements based on capability level
        if self.capability in [SSMLCapability.BASIC, SSMLCapability.ADVANCED, SSMLCapability.FULL]:
            enhanced_text = self._enhance_numbers_and_statistics(enhanced_text)
            enhanced_text = self._add_natural_pauses(enhanced_text)
            enhanced_text = self._emphasize_key_terms(enhanced_text)

        if self.capability in [SSMLCapability.ADVANCED, SSMLCapability.FULL]:
            enhanced_text = self._add_advanced_prosody(enhanced_text)
            enhanced_text = self._enhance_document_structure(enhanced_text)

        if self.capability == SSMLCapability.FULL:
            enhanced_text = self._add_full_ssml_features(enhanced_text)

        # Wrap in speak tags and add chunk markers
        if self.capability != SSMLCapability.NONE:
            enhanced_text = self._wrap_in_speak_tags(enhanced_text, chunk_number, total_chunks)

        return enhanced_text

    def _enhance_numbers_and_statistics(self, text: str) -> str:
        """Enhance numbers, percentages, and statistical notation for better speech"""

        # Handle percentages
        text = re.sub(
            r'\b(\d+(?:\.\d+)?)\s*(?:percent|%)\b',
            r'<say-as interpret-as="number">\1</say-as> percent',
            text, flags=re.IGNORECASE
        )

        # Handle statistical significance (p-values)
        text = re.sub(
            r'\bp\s*[<>=≤≥]\s*(\d+(?:\.\d+)?)',
            r'<break time="200ms"/>p value <say-as interpret-as="number">\1</say-as>',
            text, flags=re.IGNORECASE
        )

        # Handle F-statistics and similar
        text = re.sub(
            r'\bF\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*=\s*(\d+(?:\.\d+)?)',
            r'<prosody rate="90%">F statistic, <say-as interpret-as="number">\1</say-as> comma <say-as interpret-as="number">\2</say-as> degrees of freedom, equals <say-as interpret-as="number">\3</say-as></prosody>',
            text
        )

        # Handle years
        text = re.sub(
            r'\b(19\d{2}|20\d{2})\b',
            r'<say-as interpret-as="date" format="y">\1</say-as>',
            text
        )

        # Handle large numbers with better pronunciation
        text = re.sub(
            r'\b(\d{1,3}(?:,\d{3})+(?:\.\d+)?)\b',
            r'<say-as interpret-as="number">\1</say-as>',
            text
        )

        # Handle ordinal numbers in academic contexts
        text = re.sub(
            r'\b(\d+)(?:st|nd|rd|th)\s+(century|chapter|section|study|experiment|hypothesis)\b',
            r'<say-as interpret-as="ordinal">\1</say-as> \2',
            text, flags=re.IGNORECASE
        )

        return text

    def _add_natural_pauses(self, text: str) -> str:
        """Add natural pauses for better speech flow"""

        # Transition words with different pause lengths
        major_transitions = ['however', 'nevertheless', 'nonetheless', 'consequently', 'therefore']
        minor_transitions = ['furthermore', 'moreover', 'additionally', 'similarly', 'likewise']
        conclusion_words = ['in conclusion', 'to summarize', 'in summary', 'finally', 'ultimately']

        # Major transitions - longer pauses
        for word in major_transitions:
            pattern = f'\\b{word}\\b,?\\s*'
            replacement = f'<break time="400ms"/><prosody rate="95%">{word}</prosody>,<break time="600ms"/>'
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Minor transitions - shorter pauses
        for word in minor_transitions:
            pattern = f'\\b{word}\\b,?\\s*'
            replacement = f'<break time="300ms"/>{word},<break time="400ms"/>'
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Conclusion words - dramatic pauses
        for phrase in conclusion_words:
            pattern = f'\\b{phrase}\\b,?\\s*'
            replacement = f'<break time="600ms"/><prosody pitch="+3%" rate="90%">{phrase}</prosody>,<break time="800ms"/>'
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Pauses around parenthetical information
        text = re.sub(
            r'\s*\(([^)]{15,})\)\s*',
            r' <break time="250ms"/>(<prosody rate="110%">\1</prosody>)<break time="350ms"/> ',
            text
        )

        # Pauses after enumeration
        text = re.sub(
            r'\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b,?\s*',
            r'<break time="200ms"/>\1,<break time="350ms"/>',
            text, flags=re.IGNORECASE
        )

        return text

    def _emphasize_key_terms(self, text: str) -> str:
        """Add emphasis to important academic terms"""

        # Emphasize significance words
        for word in self.academic_terms['significance']:
            pattern = f'\\b{word}\\b'
            if f'<emphasis' not in text or word not in text:  # Avoid double emphasis
                replacement = f'<emphasis level="moderate">{word}</emphasis>'
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Emphasize findings words
        for word in self.academic_terms['findings']:
            pattern = f'\\b{word}\\b'
            if f'<emphasis' not in text or word not in text:
                replacement = f'<emphasis level="moderate">{word}</emphasis>'
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Special emphasis for results and conclusions
        text = re.sub(
            r'\b(results?|findings?|conclusions?)\s+(show|indicate|suggest|demonstrate)\b',
            r'<emphasis level="strong">\1 \2</emphasis>',
            text, flags=re.IGNORECASE
        )

        return text

    def _add_advanced_prosody(self, text: str) -> str:
        """Add advanced prosody features for better academic delivery"""

        # Slow down technical terms and acronyms
        text = re.sub(
            r'\b([A-Z]{2,6})\b',
            r'<prosody rate="80%" pitch="-2%">\1</prosody>',
            text
        )

        # Adjust pitch for emphasis on key findings
        text = re.sub(
            r'\b(significant|important|critical)\s+(difference|improvement|increase|decrease|correlation|relationship)\b',
            r'<prosody pitch="+5%" rate="95%">\1 \2</prosody>',
            text, flags=re.IGNORECASE
        )

        # Slow down methodology descriptions
        methodology_terms = ['methodology', 'procedure', 'protocol', 'analysis', 'participants', 'subjects']
        for term in methodology_terms:
            pattern = f'\\b{term}\\b'
            replacement = f'<prosody rate="90%">{term}</prosody>'
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Speed up citations and references (make them less intrusive)
        text = re.sub(
            r'\([^)]*\d{4}[^)]*\)',  # (Author, 2024) style citations
            r'<prosody rate="120%" volume="soft">\g<0></prosody>',
            text
        )

        return text

    def _enhance_document_structure(self, text: str) -> str:
        """Enhance document structure elements"""

        # Enhance section headers
        if self.document_type == "research_paper":
            section_headers = ['abstract', 'introduction', 'methodology',
                               'methods', 'results', 'discussion', 'conclusion']
            for header in section_headers:
                pattern = f'^({header})\\.?\\s*$'
                replacement = f'<break time="1s"/><prosody pitch="+10%" rate="85%"><emphasis level="strong">\\1</emphasis></prosody><break time="1.2s"/>'
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE | re.MULTILINE)

        # Enhance numbered sections
        text = re.sub(
            r'^(\d+\.?\s+[A-Z][^.!?]*[.!?])\s*$',
            r'<break time="800ms"/><prosody pitch="+5%">\1</prosody><break time="1s"/>',
            text, flags=re.MULTILINE
        )

        return text

    def _add_full_ssml_features(self, text: str) -> str:
        """Add full SSML features for engines with complete support"""

        # Add markers for navigation (useful for long documents)
        text = re.sub(
            r'^(Abstract|Introduction|Methods?|Results?|Discussion|Conclusion)\.?\s*$',
            r'<mark name="\1"/>\1.<break time="1s"/>',
            text, flags=re.MULTILINE | re.IGNORECASE
        )

        # Add subtle audio cues for citations (would need actual audio files)
        text = re.sub(
            r'\[(\d+(?:[-,]\d+)*)\]',
            r'<break time="100ms"/>[citation \1]<break time="100ms"/>',
            text
        )

        return text

    def _wrap_in_speak_tags(self, text: str, chunk_number: int, total_chunks: int) -> str:
        """Wrap text in proper SSML speak tags with chunk information"""

        # Add chunk markers for long documents
        if total_chunks > 1:
            chunk_intro = f'<break time="500ms"/><prosody rate="110%" volume="soft">Section {chunk_number}.</prosody><break time="700ms"/>'
            text = chunk_intro + text

        # Wrap in speak tags
        text = f'<speak>{text}</speak>'

        return text

    def _add_pause_markers(self, text: str) -> str:
        """Fallback: Add simple pause markers for engines without SSML"""

        # Add pauses after transition words
        for word in self.academic_terms['transition']:
            text = re.sub(f'\\b{word}\\b', f'... {word} ...', text, flags=re.IGNORECASE)

        # Add pauses around parenthetical content
        text = re.sub(r'\s*\(([^)]+)\)\s*', r' ... (\1) ... ', text)

        return text

    def _detect_engine_capability(self) -> SSMLCapability:
        """Detect SSML capability of the TTS engine"""

        engine_name = self.tts_engine.__class__.__name__.lower()

        if 'gemini' in engine_name:
            return SSMLCapability.FULL
        elif 'piper' in engine_name:
            return SSMLCapability.ADVANCED
        elif 'coqui' in engine_name:
            return SSMLCapability.BASIC
        else:
            return SSMLCapability.NONE

    def get_capability_info(self) -> Dict[str, Any]:
        """Get information about SSML capabilities"""
        return {
            'engine': self.tts_engine.__class__.__name__,
            'capability': self.capability.value,
            'document_type': self.document_type,
            'features_enabled': {
                'number_enhancement': self.capability != SSMLCapability.NONE,
                'natural_pauses': self.capability != SSMLCapability.NONE,
                'emphasis': self.capability != SSMLCapability.NONE,
                'advanced_prosody': self.capability in [SSMLCapability.ADVANCED, SSMLCapability.FULL],
                'document_structure': self.capability in [SSMLCapability.ADVANCED, SSMLCapability.FULL],
                'full_features': self.capability == SSMLCapability.FULL
            }
        }
