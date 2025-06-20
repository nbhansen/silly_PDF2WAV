# domain/services/timing_calculator.py
import re
from typing import Dict

from domain.interfaces import ITimingCalculator


class TimingCalculator(ITimingCalculator):
    """Concrete implementation of timing and duration calculations"""

    def __init__(self):
        # Engine-specific WPM (words per minute) rates
        self.engine_wpm = {
            'GeminiTTSProvider': 180,
            'PiperTTSProvider': 150,
            'OpenAITTSProvider': 175,
            'ElevenLabsTTSProvider': 165,
            'default': 160
        }

        # Punctuation pause durations (seconds)
        self.punctuation_pauses = {
            '.': 0.4, '!': 0.4, '?': 0.4,
            ',': 0.2, ';': 0.3, ':': 0.3,
            '—': 0.3, '–': 0.2, '...': 0.6,
            '(': 0.1, ')': 0.1
        }

        # Phoneme duration estimates (milliseconds)
        self.phoneme_durations = {
            'vowel': 80,
            'consonant': 40,
            'fricative': 60,  # s, f, sh, th
            'plosive': 30,    # p, t, k, b, d, g
            'liquid': 50,     # l, r
            'nasal': 55,      # m, n, ng
            'glide': 45,      # w, y
        }

    def estimate_text_duration(self, text: str, engine_type: str) -> float:
        """Estimate duration for text based on engine characteristics."""
        if not text.strip():
            return 0.0

        # Get base WPM for engine
        wpm = self.engine_wpm.get(engine_type, self.engine_wpm['default'])

        # Clean text and count words
        clean_text = self._clean_text_for_counting(text)
        word_count = len(clean_text.split())

        if word_count == 0:
            return 0.5  # Minimum duration for non-empty text

        # Calculate base duration
        base_duration = (word_count / wpm) * 60  # Convert to seconds

        # Add punctuation pauses
        punctuation_time = self.add_punctuation_pauses(text)

        # Add complexity adjustments
        complexity_factor = self._calculate_complexity_factor(text)

        # Combine all factors
        total_duration = base_duration * complexity_factor + punctuation_time

        # Ensure minimum duration
        return max(total_duration, 0.3)

    def calculate_phoneme_duration(self, text: str) -> float:
        """Calculate duration based on phoneme analysis."""
        clean_text = self._clean_text_for_counting(text).lower()

        total_ms = 0
        for char in clean_text:
            if char in 'aeiou':
                total_ms += self.phoneme_durations['vowel']
            elif char in 'sftθðʃʒ':  # fricatives
                total_ms += self.phoneme_durations['fricative']
            elif char in 'ptkbdg':  # plosives
                total_ms += self.phoneme_durations['plosive']
            elif char in 'lr':  # liquids
                total_ms += self.phoneme_durations['liquid']
            elif char in 'mnŋ':  # nasals
                total_ms += self.phoneme_durations['nasal']
            elif char in 'wy':  # glides
                total_ms += self.phoneme_durations['glide']
            elif char.isalpha():  # other consonants
                total_ms += self.phoneme_durations['consonant']
            elif char.isspace():
                total_ms += 20  # Brief pause between words

        return total_ms / 1000.0  # Convert to seconds

    def add_punctuation_pauses(self, text: str) -> float:
        """Calculate additional time for punctuation pauses."""
        pause_time = 0.0

        for punct, pause_duration in self.punctuation_pauses.items():
            pause_time += text.count(punct) * pause_duration

        # Add extra time for ellipsis
        ellipsis_count = text.count('...')
        pause_time += ellipsis_count * 0.3  # Additional pause for ellipsis

        return pause_time

    def _clean_text_for_counting(self, text: str) -> str:
        """Clean text for word/character counting"""
        # Remove SSML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Remove extra whitespace
        text = re.sub(r'\\s+', ' ', text)

        return text.strip()

    def _calculate_complexity_factor(self, text: str) -> float:
        """Calculate complexity factor that affects speaking speed"""
        clean_text = self._clean_text_for_counting(text)
        words = clean_text.split()

        if not words:
            return 1.0

        complexity_score = 0.0

        # Long words (indicating complex vocabulary)
        long_words = sum(1 for word in words if len(word) > 8)
        complexity_score += (long_words / len(words)) * 0.3

        # Technical terms (numbers, acronyms, specialized vocabulary)
        technical_pattern = r'\\b(?:[A-Z]{2,}|\\w*\\d\\w*|\\w*[%$€£]\\w*)\\b'
        technical_matches = re.findall(technical_pattern, text)
        complexity_score += (len(technical_matches) / len(words)) * 0.4

        # Nested clauses (commas, parentheses, dashes)
        clause_indicators = text.count(',') + text.count('(') + text.count(')') + text.count('—') + text.count('–')
        complexity_score += (clause_indicators / len(words)) * 0.2

        # Foreign words or proper nouns (indicated by capitalization patterns)
        capitalized_words = sum(1 for word in words if word and word[0].isupper() and len(word) > 3)
        complexity_score += (capitalized_words / len(words)) * 0.1

        # Convert to factor (1.0 to 1.5 range)
        complexity_factor = 1.0 + min(complexity_score, 0.5)

        return complexity_factor

    def estimate_sentence_duration(self, sentence: str, engine_type: str) -> float:
        """Estimate duration for a single sentence with enhanced accuracy"""
        if not sentence.strip():
            return 0.0

        # Combine phoneme analysis with engine-specific estimation
        phoneme_duration = self.calculate_phoneme_duration(sentence)
        engine_duration = self.estimate_text_duration(sentence, engine_type)

        # Weight the estimates based on text length
        text_length = len(sentence.split())
        if text_length < 3:
            # For very short text, phoneme analysis is more accurate
            return phoneme_duration * 1.2  # Small adjustment for natural speech
        elif text_length > 20:
            # For longer text, statistical WPM is more reliable
            return engine_duration
        else:
            # For medium text, blend both approaches
            weight = text_length / 20  # 0.15 to 1.0
            return phoneme_duration * (1 - weight) + engine_duration * weight
