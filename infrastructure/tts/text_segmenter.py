# infrastructure/tts/text_segmenter.py
"""Shared text processing utilities for TTS engines
Only includes universal text processing that all TTS engines need.
"""
import re


class TextSegmenter:
    """Universal text processing for TTS engines.

    Handles only basic text segmentation and timing that works for all engines:
    - Piper TTS (limited SSML support)
    - Gemini TTS (rich styling support)
    - ElevenLabs (advanced SSML support)

    Does NOT include engine-specific features like:
    - SSML generation
    - Voice-specific styling
    - Engine-specific markup
    """

    def __init__(self, base_wpm: int = 155):
        """Initialize with configurable words per minute.

        Args:
            base_wpm: Base words per minute for duration calculation (audiobook standard is ~155)
        """
        self.base_wpm = base_wpm
        self.punctuation_pauses = {".": 0.4, "!": 0.4, "?": 0.4, ",": 0.2, ";": 0.3, ":": 0.3, "—": 0.3, "...": 0.6}

    def split_into_sentences(self, text: str) -> list[str]:
        """Smart sentence splitting preserving context.

        Handles common abbreviations and edge cases that shouldn't trigger splits.
        """
        if not text.strip():
            return []

        # Don't split on common abbreviations
        text = re.sub(r"\b(?:Dr|Mr|Mrs|Ms|Prof|Sr|Jr)\.\s*", r"\g<0>@@@", text)

        # Split on sentence boundaries (period, exclamation, question mark followed by space and capital)
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)

        # Restore abbreviations
        sentences = [s.replace("@@@", "") for s in sentences]

        # Clean and filter
        return [s.strip() for s in sentences if s.strip()]

    def calculate_duration(self, text: str) -> float:
        """Calculate estimated duration for text based on word count and punctuation.

        This is a universal calculation that works for any TTS engine.
        """
        if not text.strip():
            return 0.5  # Minimum duration

        # Clean text for word counting (remove HTML/XML tags)
        clean_text = re.sub(r"<[^>]+>", "", text)
        words = clean_text.split()
        word_count = len(words)

        # Calculate base duration (words per minute to seconds)
        base_duration = (word_count / self.base_wpm) * 60

        # Add punctuation pauses
        pause_time = 0.0
        for punct, pause in self.punctuation_pauses.items():
            pause_time += text.count(punct) * pause

        total_duration = base_duration + pause_time

        # Ensure minimum duration
        return max(total_duration, 0.5)

    def split_into_chunks(self, text: str, max_chunk_size: int = 1000) -> list[str]:
        """Split text into manageable chunks for TTS processing.

        Useful for engines that have text length limits or for better concurrency.
        Tries to split on sentence boundaries when possible.
        """
        if len(text) <= max_chunk_size:
            return [text]

        chunks = []
        sentences = self.split_into_sentences(text)
        current_chunk = ""

        for sentence in sentences:
            # If single sentence is too long, we'll have to break it
            if len(sentence) > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                # Split long sentence by words
                words = sentence.split()
                temp_chunk = ""
                for word in words:
                    if len(temp_chunk + " " + word) > max_chunk_size:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                        temp_chunk = word
                    else:
                        temp_chunk = temp_chunk + " " + word if temp_chunk else word

                if temp_chunk:
                    chunks.append(temp_chunk.strip())
                continue

            # If adding this sentence would exceed limit, save current chunk
            if len(current_chunk + " " + sentence) > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk = current_chunk + " " + sentence if current_chunk else sentence

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return [chunk for chunk in chunks if chunk.strip()]

    def clean_text_for_tts(self, text: str) -> str:
        """Clean text for better TTS processing.

        Removes problematic characters and normalizes text.
        """
        # Remove or replace problematic characters
        text = re.sub(r"[^\w\s\.\!\?\,\;\:\—\-\'\"\(\)]", " ", text)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text
