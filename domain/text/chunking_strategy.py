# domain/text/chunking_strategy.py - Text Chunking Strategies
"""Text chunking strategies for optimal TTS processing.
Extracted from AudioEngine to follow Single Responsibility Principle.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional


class ChunkingMode(Enum):
    """Available chunking strategies."""

    SENTENCE_BASED = "sentence"  # Split on sentences first
    WORD_BASED = "word"  # Split on words if sentences too large


class IChunkingStrategy(ABC):
    """Interface for text chunking strategies."""

    @abstractmethod
    def chunk_text(self, text_chunks: list[str], max_chunk_size: int) -> list[str]:
        """Split text chunks into optimal sizes for TTS processing."""


class SentenceBasedChunking(IChunkingStrategy):
    """Sentence-aware chunking that preserves natural speech boundaries."""

    def chunk_text(self, text_chunks: list[str], max_chunk_size: int) -> list[str]:
        """Split text on sentence boundaries, then words if needed."""
        # Process each chunk and flatten results (immutable)
        return [
            result_chunk for chunk in text_chunks for result_chunk in self._process_single_chunk(chunk, max_chunk_size)
        ]

    def _process_single_chunk(self, chunk: str, max_chunk_size: int) -> list[str]:
        """Process a single chunk and return list of sub-chunks."""
        if len(chunk) <= max_chunk_size:
            return [chunk]

        # Split large chunks on sentence boundaries
        sentences = self._split_sentences(chunk)
        result_chunks = []
        current_subchunk = ""

        for sentence in sentences:
            # If single sentence is too large, split by words
            if len(sentence) > max_chunk_size:
                word_chunks = self._split_by_words(sentence, max_chunk_size)
                # Add current subchunk if it exists
                if current_subchunk.strip():
                    result_chunks.append(current_subchunk.strip())
                    current_subchunk = ""
                # Add word chunks
                result_chunks.extend(word_chunks)
            elif len(current_subchunk) + len(sentence) > max_chunk_size and current_subchunk:
                # Current sentence would exceed limit, save current subchunk
                result_chunks.append(current_subchunk.strip())
                current_subchunk = sentence
            else:
                # Add sentence to current subchunk
                current_subchunk += " " + sentence if current_subchunk else sentence

        # Add final subchunk if it exists
        if current_subchunk.strip():
            result_chunks.append(current_subchunk.strip())

        return result_chunks

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences using common punctuation."""
        # Simple sentence splitting - can be enhanced with NLP libraries
        sentences = text.replace(". ", ".|").replace("! ", "!|").replace("? ", "?|").split("|")
        return [s.strip() for s in sentences if s.strip()]

    def _split_by_words(self, text: str, max_size: int) -> list[str]:
        """Split text by words when sentences are too large."""
        words = text.split()
        chunks = []
        current_chunk = ""

        for word in words:
            if len(current_chunk) + len(word) + 1 > max_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = word
            else:
                current_chunk += " " + word if current_chunk else word

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks


class WordBasedChunking(IChunkingStrategy):
    """Simple word-based chunking for basic splitting."""

    def chunk_text(self, text_chunks: list[str], max_chunk_size: int) -> list[str]:
        """Split text chunks by words only."""
        # Process each chunk and flatten results (immutable)
        return [
            result_chunk
            for chunk in text_chunks
            for result_chunk in self._process_single_chunk_by_words(chunk, max_chunk_size)
        ]

    def _process_single_chunk_by_words(self, chunk: str, max_chunk_size: int) -> list[str]:
        """Process a single chunk by word splitting."""
        if len(chunk) <= max_chunk_size:
            return [chunk]

        # Split by words
        words = chunk.split()
        result_chunks = []
        current_chunk = ""

        for word in words:
            if len(current_chunk) + len(word) + 1 > max_chunk_size and current_chunk:
                result_chunks.append(current_chunk.strip())
                current_chunk = word
            else:
                current_chunk += " " + word if current_chunk else word

        if current_chunk.strip():
            result_chunks.append(current_chunk.strip())

        return result_chunks


class ChunkingService:
    """Service for text chunking with configurable strategies.
    High cohesion: All chunking logic in one place.
    Low coupling: Strategy pattern allows different implementations.
    """

    def __init__(self, strategy: Optional[IChunkingStrategy] = None):
        self.strategy = strategy or SentenceBasedChunking()

    def process_chunks(self, text_chunks: list[str], max_chunk_size: int) -> list[str]:
        """Process text chunks using the configured strategy."""
        if not text_chunks:
            return []

        return self.strategy.chunk_text(text_chunks, max_chunk_size)

    def set_strategy(self, strategy: IChunkingStrategy) -> None:
        """Change chunking strategy."""
        self.strategy = strategy


def create_chunking_service(mode: ChunkingMode = ChunkingMode.SENTENCE_BASED) -> ChunkingService:
    """Factory function for creating chunking services."""
    if mode == ChunkingMode.SENTENCE_BASED:
        return ChunkingService(SentenceBasedChunking())
    elif mode == ChunkingMode.WORD_BASED:
        return ChunkingService(WordBasedChunking())

    # This should never be reached with current enum values
    raise ValueError(f"Unsupported chunking mode: {mode}")
