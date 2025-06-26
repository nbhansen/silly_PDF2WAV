# domain/text/chunking_strategy.py - Text Chunking Strategies
"""
Text chunking strategies for optimal TTS processing.
Extracted from AudioEngine to follow Single Responsibility Principle.
"""

from abc import ABC, abstractmethod
from typing import List
from enum import Enum


class ChunkingMode(Enum):
    """Available chunking strategies"""
    SENTENCE_BASED = "sentence"     # Split on sentences first
    WORD_BASED = "word"            # Split on words if sentences too large
    HYBRID = "hybrid"              # Smart combination of both


class IChunkingStrategy(ABC):
    """Interface for text chunking strategies"""
    
    @abstractmethod
    def chunk_text(self, text_chunks: List[str], max_chunk_size: int) -> List[str]:
        """Split text chunks into optimal sizes for TTS processing"""
        pass


class SentenceBasedChunking(IChunkingStrategy):
    """Sentence-aware chunking that preserves natural speech boundaries"""
    
    def chunk_text(self, text_chunks: List[str], max_chunk_size: int) -> List[str]:
        """Split text on sentence boundaries, then words if needed"""
        processed_chunks = []
        
        for chunk in text_chunks:
            if len(chunk) <= max_chunk_size:
                processed_chunks.append(chunk)
                continue
            
            # Split large chunks on sentence boundaries
            sentences = self._split_sentences(chunk)
            current_subchunk = ""
            
            for sentence in sentences:
                # If single sentence is too large, split by words
                if len(sentence) > max_chunk_size:
                    word_chunks = self._split_by_words(sentence, max_chunk_size)
                    # Add current subchunk if it exists
                    if current_subchunk.strip():
                        processed_chunks.append(current_subchunk.strip())
                        current_subchunk = ""
                    # Add word chunks
                    processed_chunks.extend(word_chunks)
                elif len(current_subchunk) + len(sentence) > max_chunk_size and current_subchunk:
                    # Current sentence would exceed limit, save current subchunk
                    processed_chunks.append(current_subchunk.strip())
                    current_subchunk = sentence
                else:
                    # Add sentence to current subchunk
                    current_subchunk += (" " + sentence if current_subchunk else sentence)
            
            # Add final subchunk if it exists
            if current_subchunk.strip():
                processed_chunks.append(current_subchunk.strip())
        
        return processed_chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using common punctuation"""
        # Simple sentence splitting - can be enhanced with NLP libraries
        sentences = text.replace('. ', '.|').replace('! ', '!|').replace('? ', '?|').split('|')
        return [s.strip() for s in sentences if s.strip()]
    
    def _split_by_words(self, text: str, max_size: int) -> List[str]:
        """Split text by words when sentences are too large"""
        words = text.split()
        chunks = []
        current_chunk = ""
        
        for word in words:
            if len(current_chunk) + len(word) + 1 > max_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = word
            else:
                current_chunk += (" " + word if current_chunk else word)
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks


class WordBasedChunking(IChunkingStrategy):
    """Simple word-based chunking for basic splitting"""
    
    def chunk_text(self, text_chunks: List[str], max_chunk_size: int) -> List[str]:
        """Split text chunks by words only"""
        processed_chunks = []
        
        for chunk in text_chunks:
            if len(chunk) <= max_chunk_size:
                processed_chunks.append(chunk)
                continue
            
            # Split by words
            words = chunk.split()
            current_chunk = ""
            
            for word in words:
                if len(current_chunk) + len(word) + 1 > max_chunk_size and current_chunk:
                    processed_chunks.append(current_chunk.strip())
                    current_chunk = word
                else:
                    current_chunk += (" " + word if current_chunk else word)
            
            if current_chunk.strip():
                processed_chunks.append(current_chunk.strip())
        
        return processed_chunks


class ChunkingService:
    """
    Service for text chunking with configurable strategies.
    High cohesion: All chunking logic in one place.
    Low coupling: Strategy pattern allows different implementations.
    """
    
    def __init__(self, strategy: IChunkingStrategy = None):
        self.strategy = strategy or SentenceBasedChunking()
    
    def process_chunks(self, text_chunks: List[str], max_chunk_size: int) -> List[str]:
        """Process text chunks using the configured strategy"""
        if not text_chunks:
            return []
        
        return self.strategy.chunk_text(text_chunks, max_chunk_size)
    
    def set_strategy(self, strategy: IChunkingStrategy):
        """Change chunking strategy"""
        self.strategy = strategy


def create_chunking_service(mode: ChunkingMode = ChunkingMode.SENTENCE_BASED) -> ChunkingService:
    """Factory function for creating chunking services"""
    if mode == ChunkingMode.SENTENCE_BASED:
        return ChunkingService(SentenceBasedChunking())
    elif mode == ChunkingMode.WORD_BASED:
        return ChunkingService(WordBasedChunking())
    else:  # HYBRID - for future implementation
        return ChunkingService(SentenceBasedChunking())  # Default to sentence-based for now
