# domain/text/chunking_strategy.py - Text Chunking Strategies with Result[T] pattern
"""Text chunking strategies using Result[T] pattern for error handling.

No exceptions thrown - all errors returned as Result[T].
"""

from abc import ABC, abstractmethod
from enum import Enum

from ..errors import ApplicationError, ErrorCode, Result


class ChunkingMode(Enum):
    """Available chunking strategies."""

    SENTENCE_BASED = "sentence"  # Split on sentences first
    WORD_BASED = "word"  # Split on words if sentences too large


class IChunkingStrategy(ABC):
    """Interface for text chunking strategies using Result[T] pattern."""

    @abstractmethod
    def chunk_text(self, text_chunks: list[str], max_chunk_size: int) -> Result[list[str]]:
        """Split text chunks into optimal sizes for TTS processing."""


class SentenceBasedChunking(IChunkingStrategy):
    """Sentence-aware chunking that preserves natural speech boundaries.

    Pure functions with Result[T] pattern - no exceptions thrown.
    """

    def chunk_text(self, text_chunks: list[str], max_chunk_size: int) -> Result[list[str]]:
        """Split text on sentence boundaries, then words if needed.

        Returns Result with chunked text or error.
        """
        if max_chunk_size <= 0:
            return Result.failure(
                ApplicationError(
                    code=ErrorCode.CONFIGURATION_ERROR,
                    message="Invalid chunk size",
                    details=f"max_chunk_size must be positive, got {max_chunk_size}",
                    retryable=False,
                )
            )

        if not text_chunks:
            return Result.success([])

        try:
            # Process each chunk and flatten results (immutable)
            result_chunks: list[str] = []
            for chunk in text_chunks:
                chunk_result = self._process_single_chunk(chunk, max_chunk_size)
                if chunk_result.is_failure:
                    return chunk_result
                chunk_value = chunk_result.value
                if chunk_value is not None:
                    result_chunks.extend(chunk_value)

            return Result.success(result_chunks)

        except Exception as e:
            return Result.from_exception(e, ErrorCode.TEXT_EXTRACTION_FAILED, retryable=False)

    def _process_single_chunk(self, chunk: str, max_chunk_size: int) -> Result[list[str]]:
        """Process a single chunk and return Result with sub-chunks."""
        if not chunk:
            return Result.success([])

        if len(chunk) <= max_chunk_size:
            return Result.success([chunk])

        try:
            # Split large chunks on sentence boundaries
            sentences = self._split_sentences(chunk)
            result_chunks = []
            current_subchunk = ""

            for sentence in sentences:
                # If single sentence is too large, split by words
                if len(sentence) > max_chunk_size:
                    word_result = self._split_by_words(sentence, max_chunk_size)
                    if word_result.is_failure:
                        return word_result
                    word_chunks = word_result.value
                    if word_chunks is not None:
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

            return Result.success(result_chunks)

        except Exception as e:
            return Result.from_exception(e, ErrorCode.TEXT_EXTRACTION_FAILED, retryable=False)

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences using common punctuation.

        Pure function - no exceptions thrown.
        """
        # Simple sentence splitting - can be enhanced with NLP libraries
        sentences = text.replace(". ", ".|").replace("! ", "!|").replace("? ", "?|").split("|")
        return [s.strip() for s in sentences if s.strip()]

    def _split_by_words(self, text: str, max_size: int) -> Result[list[str]]:
        """Split text by words when sentences are too large.

        Returns Result with word-based chunks.
        """
        if not text:
            return Result.success([])

        try:
            words = text.split()
            chunks = []
            current_chunk = ""

            for word in words:
                # Handle edge case where single word exceeds max size
                if len(word) > max_size:
                    # Add current chunk if exists
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                        current_chunk = ""
                    # Split oversized word by characters
                    for i in range(0, len(word), max_size):
                        chunks.append(word[i : i + max_size])
                elif len(current_chunk) + len(word) + 1 > max_size:
                    # Would exceed limit, save current chunk and start new
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = word
                else:
                    # Add word to current chunk
                    current_chunk += " " + word if current_chunk else word

            # Add final chunk if exists
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            return Result.success(chunks)

        except Exception as e:
            return Result.from_exception(e, ErrorCode.TEXT_EXTRACTION_FAILED, retryable=False)


class WordBasedChunking(IChunkingStrategy):
    """Simple word-based chunking strategy.

    Pure functions with Result[T] pattern - no exceptions thrown.
    """

    def chunk_text(self, text_chunks: list[str], max_chunk_size: int) -> Result[list[str]]:
        """Split text on word boundaries only.

        Returns Result with chunked text or error.
        """
        if max_chunk_size <= 0:
            return Result.failure(
                ApplicationError(
                    code=ErrorCode.CONFIGURATION_ERROR,
                    message="Invalid chunk size",
                    details=f"max_chunk_size must be positive, got {max_chunk_size}",
                    retryable=False,
                )
            )

        if not text_chunks:
            return Result.success([])

        try:
            # Combine all chunks first
            combined_text = " ".join(text_chunks)
            words = combined_text.split()

            chunks = []
            current_chunk = ""

            for word in words:
                # Handle edge case where single word exceeds max size
                if len(word) > max_chunk_size:
                    # Add current chunk if exists
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                        current_chunk = ""
                    # Split oversized word by characters
                    for i in range(0, len(word), max_chunk_size):
                        chunks.append(word[i : i + max_chunk_size])
                elif len(current_chunk) + len(word) + 1 > max_chunk_size:
                    # Would exceed limit, save current chunk and start new
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = word
                else:
                    # Add word to current chunk
                    current_chunk += " " + word if current_chunk else word

            # Add final chunk if exists
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            return Result.success(chunks)

        except Exception as e:
            return Result.from_exception(e, ErrorCode.TEXT_EXTRACTION_FAILED, retryable=False)


def create_chunking_strategy(mode: ChunkingMode = ChunkingMode.SENTENCE_BASED) -> IChunkingStrategy:
    """Factory function to create appropriate chunking strategy.

    Pure function - always returns a valid strategy.
    """
    if mode == ChunkingMode.SENTENCE_BASED:
        return SentenceBasedChunking()
    else:
        return WordBasedChunking()
