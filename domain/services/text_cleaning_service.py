# domain/services/text_cleaning_service.py
import time
import re
from typing import Optional, List, Dict, Any

from domain.models import TextCleaner, ILLMProvider

class TextCleaningService(TextCleaner):
    """Pure business logic for cleaning and optimizing text for TTS."""
    
    def __init__(self, llm_provider: Optional[ILLMProvider] = None, max_chunk_size: int = 100000):
        self.llm_provider = llm_provider
        self.max_chunk_size = max_chunk_size

    def clean_text(self, raw_text: str, llm_provider: Optional[ILLMProvider] = None) -> List[str]:
        """
        Clean text with LLM and optimize for TTS in one step.
        """
        # Use the passed provider or fall back to the instance one
        provider_to_use = llm_provider or self.llm_provider
        
        if not raw_text.strip():
            print("TextCleaningService: Empty text provided")
            return [""]
            
        if raw_text.startswith("Error") or raw_text.startswith("Could not convert"):
            print("TextCleaningService: Skipping cleaning due to upstream error")
            return [raw_text]
        
        if not provider_to_use:
            print("TextCleaningService: No LLM provider available, using basic TTS enhancement")
            return self._basic_tts_fallback(raw_text)
        
        # For large texts, clean in chunks with TTS optimization
        if len(raw_text) <= self.max_chunk_size:
            cleaned_text = self._clean_chunk_for_tts(raw_text, provider_to_use)
            return self._chunk_for_audio(cleaned_text)
        else:
            print(f"TextCleaningService: Large text ({len(raw_text):,} chars), processing in chunks")
            initial_chunks = self._smart_split(raw_text, self.max_chunk_size)
            cleaned_chunks = []
            
            for i, chunk in enumerate(initial_chunks):
                print(f"TextCleaningService: Cleaning and TTS-optimizing chunk {i+1}/{len(initial_chunks)}")
                if i > 0:
                    time.sleep(1)  # Rate limiting
                cleaned_chunk = self._clean_chunk_for_tts(chunk, provider_to_use)
                cleaned_chunks.append(cleaned_chunk)
                
                # Write individual debug files (consider if this belongs in domain or infrastructure)
                # For now, keep it as it's part of the original TextCleaner's behavior
                try:
                    debug_path = f"llm_tts_cleaned_chunk_{i+1}_debug.txt"
                    with open(debug_path, "w", encoding="utf-8") as f:
                        f.write(cleaned_chunk)
                    print(f"TextCleaningService: Wrote TTS-optimized chunk {i+1} to {debug_path}")
                except Exception as e:
                    print(f"TextCleaningService: Failed to write debug file: {e}")
            
            # Combine cleaned chunks with section pauses
            combined_text = "\n\n... ...\n\n".join(cleaned_chunks)  # Add pauses between major sections
            return self._chunk_for_audio(combined_text)

    def _clean_chunk_for_tts(self, text_chunk: str, llm_provider: ILLMProvider) -> str:
        """Clean a single chunk with TTS optimization using the LLM provider"""
        if not text_chunk.strip():
            return text_chunk
            
        prompt = self._get_tts_optimized_prompt(text_chunk)
        
        try:
            cleaned_text = llm_provider.generate_content(prompt)
            print(f"TextCleaningService: Successfully cleaned and TTS-optimized chunk ({len(cleaned_text):,} chars)")
            return cleaned_text
        except Exception as e:
            print(f"TextCleaningService: Error during TTS optimization with LLM: {e}")
            return self._basic_tts_fallback(text_chunk)[0]

    def _get_tts_optimized_prompt(self, text_chunk: str) -> str:
        """Generate TTS-optimized cleaning prompt"""
        
        return f"""Your primary goal is to clean the following text from an academic research paper and optimize it for text-to-speech (TTS) conversion.

**Key Cleaning Tasks:**
- Remove headers, footers, page numbers, running titles, journal names
- Remove line numbers, marginalia, watermarks, scanning artifacts  
- Skip in-text citations (e.g., [1], (Author, 2023))
- Skip mathematical formulas and equations
- Clean URLs to just domain names (e.g., "example.com" instead of full URLs)

**TTS Optimization - Critical for Natural Speech:**
- Add natural pause markers using ellipses (...) where a speaker would naturally pause
- Before major topic transitions, add "... ... ..." for longer pause
- After section-ending sentences, add "... ... ..." before starting new concepts
- When introducing lists or examples, add brief pauses: "The following examples... first, second, third"
- For transition words (however, therefore, moreover), add preceding pause: "... However, the results show"
- Keep sentences shorter when possible - break overly long academic sentences at natural points
- Ensure smooth reading flow by adding brief pauses around parenthetical information

**Text Structure for Speech:**
- Maintain clear paragraph breaks for natural speech pacing
- Join hyphenated words split across lines (e.g., "effec-\\ntive" → "effective")  
- Create grammatically correct, well-formed English suitable for reading aloud
- When listing items, use speech-friendly format: "First... Second... Third..." instead of bullet points
- Replace bullet points or dashes with "Next point:" or similar speech-friendly transitions

**Example of good TTS formatting:**
Instead of: "The results (see Table 1) show significant improvement. However, further research is needed."
Output: "The results... show significant improvement. ... However, further research is needed."

Instead of: "Key findings include: • Point one • Point two • Point three"
Output: "Key findings include... First, point one. ... Second, point two. ... Third, point three."

Here is the text to clean and optimize for TTS:
---
{text_chunk}
---

Cleaned and TTS-optimized text:"""

    def _basic_tts_fallback(self, text: str) -> List[str]:
        """Fallback TTS enhancement when LLM is not available"""
        print("TextCleaningService: Using basic TTS fallback (no LLM)")
        # Just do basic paragraph enhancement
        text = re.sub(r'\n\s*\n', '\n\n... ', text)
        return self._chunk_for_audio(text)
    
    def _chunk_for_audio(self, text: str) -> List[str]:
        """Split TTS-optimized text into audio-appropriate chunks"""
        # The text is already TTS-optimized, so we can be more aggressive about preserving structure
        target_size = 80000  # Larger chunks since they're already optimized
        
        if len(text) <= target_size:
            print("TextCleaningService: Text fits in single audio chunk")
            return [text]
        
        print(f"TextCleaningService: Splitting TTS-optimized text ({len(text):,} chars) for audio")
        
        # Split on major pause markers first (section breaks)
        major_sections = text.split('\n\n... ...\n\n')
        
        chunks = []
        current_chunk = ""
        
        for i, section in enumerate(major_sections):
            section = section.strip()
            if not section:
                continue
                
            if len(current_chunk) + len(section) > target_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # If single section is still too large, split it further
                if len(section) > target_size:
                    sub_chunks = self._split_large_section(section, target_size)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = section
            else:
                if current_chunk:
                    current_chunk += "\n\n... ...\n\n" + section
                else:
                    current_chunk = section
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        print(f"TextCleaningService: Split TTS-optimized text into {len(chunks)} audio chunks")
        return chunks
    
    def _split_large_section(self, section: str, max_size: int) -> List[str]:
        """Split a large section while preserving TTS markers"""
        # Try to split on existing pause markers first
        pause_splits = section.split('... ...')
        
        chunks = []
        current_chunk = ""
        
        for part in pause_splits:
            part = part.strip()
            if not part:
                continue
                
            potential = current_chunk + "... ..." + part if current_chunk else part
            
            if len(potential) > max_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = part
            else:
                current_chunk = potential
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _smart_split(self, text: str, max_size: int) -> List[str]:
        """Split text at sentence boundaries for initial processing"""
        # First try to split at sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # If adding this sentence would exceed max size
            if len(current_chunk) + len(sentence) > max_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # If we still have chunks that are too large, split them more aggressively
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= max_size:
                final_chunks.append(chunk)
            else:
                # Split at paragraph boundaries
                paragraphs = chunk.split('\n\n')
                sub_chunk = ""
                for para in paragraphs:
                    if len(sub_chunk) + len(para) > max_size:
                        if sub_chunk:
                            final_chunks.append(sub_chunk.strip())
                        sub_chunk = para
                    else:
                        sub_chunk += "\n\n" + para if sub_chunk else para
                
                if sub_chunk:
                    final_chunks.append(sub_chunk.strip())
        
        print(f"TextCleaningService: Split {len(text):,} chars into {len(final_chunks)} chunks")
        return final_chunks