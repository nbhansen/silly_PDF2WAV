import time
import re
from typing import Optional, List

from domain.interfaces import TextCleaner, ILLMProvider

class TextCleaningService(TextCleaner):
    """Simplified text cleaning service - SSML logic moved to pipeline"""
    
    def __init__(self, llm_provider: Optional[ILLMProvider] = None, max_chunk_size: int = 100000):
        self.llm_provider = llm_provider
        self.max_chunk_size = max_chunk_size
        print(f"TextCleaningService: Initialized (SSML handling moved to pipeline)")

    def clean_text(self, raw_text: str, llm_provider: Optional[ILLMProvider] = None) -> List[str]:
        """Clean text for TTS - no SSML logic here"""
        provider_to_use = llm_provider or self.llm_provider
        
        if not raw_text.strip():
            return [""]
            
        if raw_text.startswith("Error") or raw_text.startswith("Could not convert"):
            return [raw_text]
        
        if not provider_to_use:
            return self._basic_tts_fallback(raw_text)
        
        if len(raw_text) <= self.max_chunk_size:
            cleaned_text = self._clean_chunk_for_tts(raw_text, provider_to_use)
            return self._chunk_for_audio(cleaned_text)
        else:
            return self._process_large_text(raw_text, provider_to_use)
    
    def _process_large_text(self, raw_text: str, llm_provider: ILLMProvider) -> List[str]:
        """Process large text in chunks"""
        initial_chunks = self._smart_split(raw_text, self.max_chunk_size)
        cleaned_chunks = []
        
        for i, chunk in enumerate(initial_chunks):
            print(f"TextCleaningService: Cleaning chunk {i+1}/{len(initial_chunks)}")
            if i > 0:
                time.sleep(1)
            
            cleaned_chunk = self._clean_chunk_for_tts(chunk, llm_provider)
            cleaned_chunks.append(cleaned_chunk)
        
        combined_text = "\n\n... ...\n\n".join(cleaned_chunks)
        return self._chunk_for_audio(combined_text)
    
    def _clean_chunk_for_tts(self, text_chunk: str, llm_provider: ILLMProvider) -> str:
        """Clean a single chunk - simplified prompt"""
        if not text_chunk.strip():
            return text_chunk
            
        prompt = f"""Clean this academic text for text-to-speech:

**Tasks:**
- Remove headers, footers, page numbers, citations
- Add natural pause markers (...) for speech flow
- Optimize for audio comprehension

Text:
---
{text_chunk}
---

Cleaned text:"""
        
        try:
            cleaned_text = llm_provider.generate_content(prompt)
            return cleaned_text
        except Exception as e:
            print(f"TextCleaningService: LLM cleaning failed: {e}")
            return self._basic_tts_fallback(text_chunk)[0]

    def _smart_split(self, text: str, max_chunk_size: int) -> List[str]:
        """Split text intelligently (same implementation as before)"""
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        remaining_text = text
        
        while len(remaining_text) > max_chunk_size:
            chunk_end = max_chunk_size
            
            # Find good split points
            paragraph_break = remaining_text.rfind('\n\n', 0, chunk_end)
            if paragraph_break > max_chunk_size // 2:
                split_point = paragraph_break + 2
            else:
                sentence_end = max(
                    remaining_text.rfind('. ', 0, chunk_end),
                    remaining_text.rfind('! ', 0, chunk_end),
                    remaining_text.rfind('? ', 0, chunk_end)
                )
                if sentence_end > max_chunk_size // 2:
                    split_point = sentence_end + 2
                else:
                    whitespace = remaining_text.rfind(' ', 0, chunk_end)
                    split_point = whitespace + 1 if whitespace > max_chunk_size // 2 else max_chunk_size
            
            chunk = remaining_text[:split_point].strip()
            if chunk:
                chunks.append(chunk)
            
            remaining_text = remaining_text[split_point:].strip()
            
            # Safety check
            if len(remaining_text) >= len(chunk):
                if len(remaining_text) > max_chunk_size:
                    chunks.append(remaining_text[:max_chunk_size])
                    remaining_text = remaining_text[max_chunk_size:]
                else:
                    break
        
        if remaining_text.strip():
            chunks.append(remaining_text.strip())
        
        return chunks
    
    def _chunk_for_audio(self, text: str) -> List[str]:
        """Split cleaned text into audio-friendly chunks"""
        target_size = 3000
        max_chunk_size = 5000
        
        if len(text) <= target_size:
            return [text]
        
        # Split on major section breaks
        sections = text.split('\n\n... ...\n\n')
        all_chunks = []
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            if len(section) <= max_chunk_size:
                all_chunks.append(section)
            else:
                # Force split large sections
                while len(section) > max_chunk_size:
                    # Find sentence boundary
                    split_point = section.rfind('. ', 0, max_chunk_size)
                    if split_point < max_chunk_size // 2:
                        split_point = max_chunk_size
                    
                    all_chunks.append(section[:split_point].strip())
                    section = section[split_point:].strip()
                
                if section:
                    all_chunks.append(section)
        
        return all_chunks
    
    def _basic_tts_fallback(self, text: str) -> List[str]:
        """Basic TTS enhancement without LLM"""
        # Add pause markers
        text = re.sub(r'\n\s*\n', '\n\n... ', text)
        
        # Add pauses around transition words
        transition_words = ['however', 'therefore', 'furthermore', 'moreover', 'consequently']
        for word in transition_words:
            text = re.sub(f'\\b{word}\\b', f'... {word} ...', text, flags=re.IGNORECASE)
        
        return self._chunk_for_audio(text)