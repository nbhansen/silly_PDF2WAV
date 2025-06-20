# domain/services/enhanced_timing_strategy.py
"""
Enhanced timing strategy with ML-inspired duration estimation
"""
import re
import json
from typing import List, Dict, Optional
from domain.interfaces import ITimingStrategy, ITTSEngine, IFileManager
from domain.models import TimedAudioResult, TextSegment, TimingMetadata
from domain.services.academic_ssml_service import AcademicSSMLService

class EnhancedTimingStrategy(ITimingStrategy):
    """
    Advanced timing strategy using linguistic analysis and ML-inspired heuristics
    """
    
    def __init__(self, tts_engine: ITTSEngine, ssml_service: AcademicSSMLService, file_manager: IFileManager):
        self.tts_engine = tts_engine
        self.ssml_service = ssml_service
        self.file_manager = file_manager
        
        # Phoneme-based duration estimates (milliseconds per phoneme)
        self.phoneme_durations = {
            'vowel': 80,
            'consonant': 40,
            'fricative': 60,  # s, f, sh
            'plosive': 30,    # p, t, k
            'liquid': 50,     # l, r
            'nasal': 55,      # m, n
        }
        
        # Word frequency adjustments (common words spoken faster)
        self.common_words = {
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have',
            'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you',
            'do', 'at', 'this', 'but', 'his', 'by', 'from'
        }
        
        # Context-based adjustments
        self.context_patterns = {
            'list_item': (r'^(?:\d+\.|\*|\-)\s+', 0.3),  # Pause before list items
            'heading': (r'^#{1,6}\s+', 0.5),              # Pause for headings
            'quote': (r'^["\']', 0.2),                    # Slight pause for quotes
            'parenthetical': (r'\([^)]+\)', 0.15),        # Speed up parentheticals
        }
        
    def generate_with_timing(self, text_chunks: List[str], output_filename: str) -> TimedAudioResult:
        """
        Generate audio with enhanced timing estimation
        """
        if not text_chunks:
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)
        
        # Process chunks with SSML
        enhanced_chunks = self.ssml_service.enhance_text_chunks(text_chunks)
        
        # Generate audio
        combined_text = ' '.join(enhanced_chunks)
        result = self.tts_engine.generate_audio_data(combined_text)
        
        if result.is_failure:
            print(f"EnhancedTimingStrategy: TTS generation failed: {result.error}")
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)
        
        audio_data = result.value
        if not audio_data:
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)
        
        # Save audio
        audio_filename = f"{output_filename}.wav"
        audio_path = self.file_manager.save_output_file(audio_data, audio_filename)
        
        # Generate enhanced timing data
        timing_segments = self._generate_enhanced_timing(enhanced_chunks)
        
        # Create timing metadata
        total_duration = sum(seg.duration for seg in timing_segments)
        timing_metadata = TimingMetadata(
            total_duration=total_duration,
            text_segments=timing_segments,
            audio_files=[audio_filename]
        )
        
        # Save timing data as JSON
        self._save_timing_json(output_filename, timing_metadata)
        
        return TimedAudioResult(
            audio_files=[audio_filename],
            combined_mp3=audio_filename,
            timing_data=timing_metadata
        )
    
    def _generate_enhanced_timing(self, text_chunks: List[str]) -> List[TextSegment]:
        """
        Generate timing with advanced linguistic analysis
        """
        segments = []
        current_time = 0.0
        
        for chunk_idx, chunk in enumerate(text_chunks):
            sentences = self._split_sentences_with_context(chunk)
            
            for sent_idx, sentence_data in enumerate(sentences):
                sentence = sentence_data['text']
                context = sentence_data['context']
                
                # Calculate duration with multiple factors
                duration = self._calculate_enhanced_duration(sentence, context)
                
                # Clean for display
                clean_text = self._clean_ssml(sentence)
                
                segment = TextSegment(
                    text=clean_text,
                    start_time=current_time,
                    duration=duration,
                    segment_type=context.get('type', 'sentence'),
                    chunk_index=chunk_idx,
                    sentence_index=sent_idx
                )
                
                segments.append(segment)
                current_time += duration
        
        return segments
    
    def _calculate_enhanced_duration(self, text: str, context: Dict) -> float:
        """
        Calculate duration using multiple linguistic factors
        """
        # Base calculation using phoneme estimation
        phoneme_duration = self._estimate_phoneme_duration(text)
        
        # Word frequency adjustment
        frequency_factor = self._calculate_frequency_factor(text)
        
        # Contextual adjustments
        context_adjustment = self._calculate_context_adjustment(text, context)
        
        # Complexity analysis
        complexity_factor = self._analyze_complexity(text)
        
        # Combine all factors
        base_duration = phoneme_duration * frequency_factor * complexity_factor
        total_duration = base_duration + context_adjustment
        
        # Apply voice-specific adjustments
        if context.get('voice_persona') == 'technical':
            total_duration *= 1.15  # Slower for technical
        elif context.get('voice_persona') == 'emphasis':
            total_duration *= 1.1   # Slightly slower for emphasis
        
        # Ensure reasonable bounds
        min_duration = 0.3
        max_duration = min(15.0, len(text.split()) * 0.5)  # Max 0.5s per word
        
        return max(min_duration, min(total_duration, max_duration))
    
    def _estimate_phoneme_duration(self, text: str) -> float:
        """
        Estimate duration based on phoneme analysis
        """
        # Simplified phoneme estimation
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        
        total_ms = 0
        for char in clean_text:
            if char in 'aeiou':
                total_ms += self.phoneme_durations['vowel']
            elif char in 'bdgpqt':
                total_ms += self.phoneme_durations['plosive']
            elif char in 'fsvz':
                total_ms += self.phoneme_durations['fricative']
            elif char in 'lr':
                total_ms += self.phoneme_durations['liquid']
            elif char in 'mn':
                total_ms += self.phoneme_durations['nasal']
            elif char.isalpha():
                total_ms += self.phoneme_durations['consonant']
            elif char.isspace():
                total_ms += 20  # Brief pause between words
        
        return total_ms / 1000.0  # Convert to seconds
    
    def _calculate_frequency_factor(self, text: str) -> float:
        """
        Adjust for word frequency (common words spoken faster)
        """
        words = text.lower().split()
        if not words:
            return 1.0
        
        common_count = sum(1 for word in words if word in self.common_words)
        common_ratio = common_count / len(words)
        
        # More common words = faster speech (0.85 to 1.0)
        return 1.0 - (common_ratio * 0.15)
    
    def _calculate_context_adjustment(self, text: str, context: Dict) -> float:
        """
        Add pauses based on context
        """
        adjustment = 0.0
        
        # Check context patterns
        for pattern_name, (pattern, pause) in self.context_patterns.items():
            if re.search(pattern, text):
                adjustment += pause
        
        # Punctuation pauses
        adjustment += text.count('.') * 0.4
        adjustment += text.count('!') * 0.4
        adjustment += text.count('?') * 0.4
        adjustment += text.count(',') * 0.2
        adjustment += text.count(';') * 0.3
        adjustment += text.count(':') * 0.3
        
        # Paragraph/section boundaries
        if context.get('is_paragraph_start'):
            adjustment += 0.6
        if context.get('is_section_start'):
            adjustment += 0.8
        
        return adjustment
    
    def _analyze_complexity(self, text: str) -> float:
        """
        Analyze text complexity for speed adjustment
        """
        words = text.split()
        if not words:
            return 1.0
        
        # Factors that slow down speech
        complexity_score = 0.0
        
        # Long words (syllables approximation)
        long_words = sum(1 for word in words if len(word) > 8)
        complexity_score += (long_words / len(words)) * 0.3
        
        # Technical terms (numbers, uppercase acronyms)
        technical_pattern = r'\b(?:[A-Z]{2,}|\w*\d\w*)\b'
        technical_matches = re.findall(technical_pattern, text)
        complexity_score += (len(technical_matches) / len(words)) * 0.4
        
        # Nested clauses (commas, parentheses)
        clause_indicators = text.count(',') + text.count('(') + text.count(')')
        complexity_score += (clause_indicators / len(words)) * 0.2
        
        # Convert to factor (1.0 to 1.5)
        return 1.0 + min(complexity_score, 0.5)
    
    def _split_sentences_with_context(self, text: str) -> List[Dict]:
        """
        Split into sentences while preserving context
        """
        # Basic sentence splitting with context preservation
        sentences = []
        
        # Split on sentence boundaries
        raw_sentences = re.split(r'(?<=[.!?])\s+', text)
        
        for i, sentence in enumerate(raw_sentences):
            if not sentence.strip():
                continue
            
            context = {
                'text': sentence,
                'context': {
                    'position': i,
                    'is_first': i == 0,
                    'is_last': i == len(raw_sentences) - 1,
                    'type': self._determine_sentence_type(sentence)
                }
            }
            
            sentences.append(context)
        
        return sentences
    
    def _determine_sentence_type(self, sentence: str) -> str:
        """Determine the type of sentence for timing adjustments"""
        if re.match(r'^#{1,6}\s+', sentence):
            return 'heading'
        elif re.match(r'^(?:\d+\.|\*|\-)\s+', sentence):
            return 'list_item'
        elif sentence.strip().startswith('"') or sentence.strip().startswith("'"):
            return 'quote'
        elif '(' in sentence and ')' in sentence:
            return 'parenthetical'
        else:
            return 'sentence'
    
    def _clean_ssml(self, text: str) -> str:
        """Remove SSML tags for display"""
        return re.sub(r'<[^>]+>', '', text).strip()
    
    def _save_timing_json(self, base_filename: str, timing_metadata: TimingMetadata):
        """Save timing data as JSON for debugging and analysis"""
        timing_data = {
            'total_duration': timing_metadata.total_duration,
            'segment_count': len(timing_metadata.text_segments),
            'segments': [
                {
                    'text': seg.text[:50] + '...' if len(seg.text) > 50 else seg.text,
                    'start': round(seg.start_time, 3),
                    'duration': round(seg.duration, 3),
                    'type': seg.segment_type
                }
                for seg in timing_metadata.text_segments[:10]  # First 10 for debugging
            ]
        }
        
        # Save alongside audio files
        json_path = self.file_manager.save_output_file(
            json.dumps(timing_data, indent=2).encode('utf-8'),
            f"{base_filename}_timing_debug.json"
        )
        
        print(f"Saved timing debug data: {json_path}")