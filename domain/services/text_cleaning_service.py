# domain/services/text_cleaning_service.py - Updated with SSML Integration
import time
import re
from typing import Optional, List, Dict, Any

from domain.interfaces import TextCleaner, ILLMProvider, ISSMLGenerator, SSMLCapability

class TextCleaningService(TextCleaner):
    """Enhanced text cleaning service with SSML generation support"""
    
    def __init__(self, 
                 llm_provider: Optional[ILLMProvider] = None, 
                 max_chunk_size: int = 100000,
                 ssml_generator: Optional[ISSMLGenerator] = None):
        self.llm_provider = llm_provider
        self.max_chunk_size = max_chunk_size
        self.ssml_generator = ssml_generator
        
        print(f"TextCleaningService: Initialized with SSML support: {ssml_generator is not None}")

    def clean_text(self, raw_text: str, 
                  llm_provider: Optional[ILLMProvider] = None,
                  target_ssml_capability: SSMLCapability = SSMLCapability.NONE) -> List[str]:
        """
        Clean text and optionally generate SSML markup
        
        Args:
            raw_text: Raw extracted text from PDF
            llm_provider: Optional LLM for advanced cleaning  
            target_ssml_capability: Target SSML support level
            
        Returns:
            List of cleaned text chunks, potentially with SSML markup
        """
        # Use the passed provider or fall back to the instance one
        provider_to_use = llm_provider or self.llm_provider
        
        if not raw_text.strip():
            print("TextCleaningService: Empty text provided")
            return [""]
            
        if raw_text.startswith("Error") or raw_text.startswith("Could not convert"):
            print("TextCleaningService: Skipping cleaning due to upstream error")
            return [raw_text]
        
        print(f"TextCleaningService: Processing text with target SSML capability: {target_ssml_capability.value}")
        
        if not provider_to_use:
            print("TextCleaningService: No LLM provider available, using basic TTS enhancement")
            cleaned_chunks = self._basic_tts_fallback(raw_text)
        else:
            # Use LLM for cleaning with SSML awareness
            if len(raw_text) <= self.max_chunk_size:
                cleaned_text = self._clean_chunk_for_tts_with_ssml(raw_text, provider_to_use, target_ssml_capability)
                cleaned_chunks = self._chunk_for_audio_optimized(cleaned_text)
            else:
                print(f"TextCleaningService: Large text ({len(raw_text):,} chars), processing in chunks")
                cleaned_chunks = self._process_large_text_with_ssml(raw_text, provider_to_use, target_ssml_capability)
        
        # Apply SSML generation if requested and available
        if (target_ssml_capability != SSMLCapability.NONE and 
            self.ssml_generator and 
            not self._already_contains_ssml(cleaned_chunks)):
            
            print(f"TextCleaningService: Applying SSML generation with capability: {target_ssml_capability.value}")
            ssml_chunks = self._apply_ssml_generation(cleaned_chunks, target_ssml_capability)
            return ssml_chunks
        
        return cleaned_chunks
    
    def supports_ssml_generation(self) -> bool:
        """Check if this cleaner can generate SSML markup"""
        return self.ssml_generator is not None
    
    def get_optimal_chunk_size(self, tts_engine = None) -> int:
        """Get optimal chunk size based on TTS engine SSML capabilities"""
        if tts_engine and hasattr(tts_engine, 'supports_ssml') and tts_engine.supports_ssml():
            # SSML engines often prefer smaller chunks for better processing
            return min(self.max_chunk_size, 15000)
        return self.max_chunk_size

    # === SSML-Enhanced Processing Methods ===
    
    def _process_large_text_with_ssml(self, raw_text: str, 
                                     llm_provider: ILLMProvider, 
                                     target_capability: SSMLCapability) -> List[str]:
        """Process large text with SSML awareness"""
        initial_chunks = self._smart_split(raw_text, self.max_chunk_size)
        cleaned_chunks = []
        
        for i, chunk in enumerate(initial_chunks):
            print(f"TextCleaningService: Cleaning and optimizing chunk {i+1}/{len(initial_chunks)} for SSML")
            if i > 0:
                time.sleep(1)  # Rate limiting
            
            cleaned_chunk = self._clean_chunk_for_tts_with_ssml(chunk, llm_provider, target_capability)
            cleaned_chunks.append(cleaned_chunk)
            
            # Write debug files for SSML development
            try:
                debug_path = f"llm_ssml_cleaned_chunk_{i+1}_debug.txt"
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(cleaned_chunk)
                print(f"TextCleaningService: Wrote SSML-optimized chunk {i+1} to {debug_path}")
            except Exception as e:
                print(f"TextCleaningService: Failed to write debug file: {e}")
        
        # Combine cleaned chunks with SSML-aware separators
        if target_capability != SSMLCapability.NONE:
            combined_text = "\n\n<break time=\"1s\"/>\n\n".join(cleaned_chunks)
        else:
            combined_text = "\n\n... ...\n\n".join(cleaned_chunks)
        
        return self._chunk_for_audio_optimized(combined_text)

    def _clean_chunk_for_tts_with_ssml(self, text_chunk: str, 
                                      llm_provider: ILLMProvider, 
                                      target_capability: SSMLCapability) -> str:
        """Clean a single chunk with SSML-aware prompt"""
        if not text_chunk.strip():
            return text_chunk
            
        prompt = self._get_ssml_optimized_prompt(text_chunk, target_capability)
        
        try:
            cleaned_text = llm_provider.generate_content(prompt)
            print(f"TextCleaningService: Successfully cleaned and SSML-optimized chunk ({len(cleaned_text):,} chars)")
            return cleaned_text
        except Exception as e:
            print(f"TextCleaningService: Error during SSML optimization with LLM: {e}")
            return self._basic_tts_fallback(text_chunk)[0]

    def _get_ssml_optimized_prompt(self, text_chunk: str, capability: SSMLCapability) -> str:
        """Generate SSML-optimized cleaning prompt based on capability level"""
        
        if capability == SSMLCapability.NONE:
            return self._get_tts_optimized_prompt(text_chunk)  # Use existing prompt
        
        # Base instructions that apply to all SSML levels
        base_instructions = """**Core Cleaning Tasks:**
- Remove headers, footers, page numbers, running titles, journal names
- Remove line numbers, marginalia, watermarks, scanning artifacts  
- Skip in-text citations (e.g., [1], (Author, 2023))
- Skip mathematical formulas and equations
- Clean URLs to just domain names
- Create grammatically correct, well-formed English suitable for academic narration"""

        # SSML-specific instructions based on capability level
        ssml_instructions = {
            SSMLCapability.BASIC: """
**SSML Enhancement (Basic Level):**
- Add <break time="500ms"/> for natural pauses between sentences
- Add <break time="1s"/> for major topic transitions  
- Use <emphasis level="moderate">important terms</emphasis> for key concepts
- Wrap content in <speak></speak> tags
- Use <p></p> tags for paragraph structure

Example transformations:
"However, the results show" → "<break time=\"300ms\"/>However, the <emphasis level=\"moderate\">results</emphasis> show"
"... ..." → "<break time=\"1s\"/>"
""",
            SSMLCapability.ADVANCED: """
**SSML Enhancement (Advanced Level):**
- All basic features plus:
- Format numbers: <say-as interpret-as="number">73.2</say-as>
- Format percentages: <say-as interpret-as="number">25</say-as> percent
- Format years: <say-as interpret-as="date" format="y">2024</say-as>
- Slow technical terms: <prosody rate="slow">methodology</prosody>
- Add pitch variation: <prosody pitch="+5%" rate="95%">significant findings</prosody>
- Use <s></s> tags for sentence structure

Example transformations:
"73.2 percent increase in 2024" → "<say-as interpret-as=\"number\">73.2</say-as> percent increase in <say-as interpret-as=\"date\" format=\"y\">2024</say-as>"
"However" → "<break time=\"300ms\"/><emphasis level=\"moderate\">However</emphasis><break time=\"400ms\"/>"
""",
            SSMLCapability.FULL: """
**SSML Enhancement (Full Specification):**
- All advanced features plus:
- Section markers: <mark name="section_name"/>
- Alternative voices for quotes: <voice name="alternative">quoted text</voice>
- Audio cues: <break time="100ms"/>[citation]<break time="100ms"/>
- Complex prosody: <prosody pitch="high" rate="slow">emphasis</prosody>
- Phonetic guidance for difficult terms
- Advanced say-as types (ordinal, cardinal, digits, time, etc.)

Example transformations:
"Abstract" → "<mark name=\"Abstract\"/>Abstract<break time=\"1s\"/>"
"[15]" → "<break time=\"100ms\"/>[citation 15]<break time=\"100ms\"/>"
"""
        }
        
        selected_instructions = ssml_instructions.get(capability, ssml_instructions[SSMLCapability.BASIC])
        
        return f"""Transform the following academic text into clean, SSML-enhanced content optimized for text-to-speech.

{base_instructions}

{selected_instructions}

**Academic Content Guidelines:**
- Maintain all scientific accuracy and technical precision
- Preserve the logical flow and academic structure
- Enhance readability while respecting the original meaning
- Optimize for audio comprehension of complex academic concepts

**Output Format:** Provide clean, SSML-enhanced text ready for academic text-to-speech synthesis.

Input text:
---
{text_chunk}
---

SSML-enhanced academic text:"""

    def _apply_ssml_generation(self, cleaned_chunks: List[str], 
                              target_capability: SSMLCapability) -> List[str]:
        """Apply SSML generation to cleaned text chunks"""
        if not self.ssml_generator:
            print("TextCleaningService: No SSML generator available")
            return cleaned_chunks
        
        ssml_chunks = []
        for i, chunk in enumerate(cleaned_chunks):
            if not chunk.strip() or chunk.startswith("Error"):
                ssml_chunks.append(chunk)
                continue
            
            try:
                ssml_chunk = self.ssml_generator.generate_ssml_for_academic_content(
                    chunk, target_capability
                )
                ssml_chunks.append(ssml_chunk)
                print(f"TextCleaningService: Generated SSML for chunk {i+1}")
            except Exception as e:
                print(f"TextCleaningService: SSML generation failed for chunk {i+1}: {e}")
                ssml_chunks.append(chunk)  # Fallback to original chunk
        
        return ssml_chunks

    def _already_contains_ssml(self, chunks: List[str]) -> bool:
        """Check if chunks already contain SSML markup"""
        return any('<speak>' in chunk or '<break' in chunk or '<emphasis' in chunk 
                  for chunk in chunks)

    # === Enhanced Chunking for SSML ===
    
    def _chunk_for_audio_optimized(self, text: str) -> List[str]:
        """Split SSML-optimized text into chunks suitable for TTS processing"""
        # For SSML content, we need to be more careful about chunk boundaries
        if '<speak>' in text or '<break' in text:
            return self._chunk_ssml_aware(text)
        else:
            return self._chunk_for_audio_original(text)
    
    def _chunk_ssml_aware(self, ssml_text: str) -> List[str]:
        """Split SSML content while preserving markup integrity"""
        target_size = 4000  # Smaller chunks for SSML content
        max_chunk_size = 6000  # Strict limit for SSML
        
        if len(ssml_text) <= target_size:
            print("TextCleaningService: SSML content fits in single chunk")
            return [ssml_text]
        
        print(f"TextCleaningService: Splitting SSML content ({len(ssml_text):,} chars) into TTS-friendly chunks")
        
        # Try to split on major SSML breaks first
        if '<break time="1s"' in ssml_text:
            chunks = ssml_text.split('<break time="1s"/>')
            processed_chunks = []
            
            for chunk in chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue
                
                # Ensure each chunk is properly wrapped
                if not chunk.startswith('<speak>'):
                    chunk = f'<speak>{chunk}</speak>'
                
                if len(chunk) <= max_chunk_size:
                    processed_chunks.append(chunk)
                else:
                    # Chunk is still too large, split more aggressively
                    sub_chunks = self._force_split_ssml_content(chunk, target_size, max_chunk_size)
                    processed_chunks.extend(sub_chunks)
            
            print(f"TextCleaningService: Split SSML into {len(processed_chunks)} chunks")
            return processed_chunks
        
        # Fallback to paragraph-based splitting for SSML
        return self._split_ssml_by_paragraphs(ssml_text, target_size, max_chunk_size)
    
    def _force_split_ssml_content(self, ssml_content: str, target_size: int, max_size: int) -> List[str]:
        """Force split SSML content while preserving markup"""
        # Remove outer speak tags temporarily
        content = ssml_content
        if content.startswith('<speak>') and content.endswith('</speak>'):
            content = content[7:-8].strip()
        
        # Split on paragraph tags
        if '<p>' in content:
            p_chunks = re.split(r'</p>\s*<p>', content)
            chunks = []
            current_chunk = ""
            
            for p_chunk in p_chunks:
                # Clean up paragraph markers
                p_chunk = p_chunk.replace('<p>', '').replace('</p>', '').strip()
                
                potential = current_chunk + f"<p>{p_chunk}</p>" if current_chunk else f"<p>{p_chunk}</p>"
                
                if len(potential) <= max_size:
                    current_chunk = potential
                else:
                    if current_chunk:
                        chunks.append(f'<speak>{current_chunk}</speak>')
                    current_chunk = f"<p>{p_chunk}</p>"
            
            if current_chunk:
                chunks.append(f'<speak>{current_chunk}</speak>')
            
            return chunks
        
        # Last resort: split by sentences while preserving SSML
        return self._split_ssml_by_sentences(content, target_size, max_size)
    
    def _split_ssml_by_paragraphs(self, ssml_text: str, target_size: int, max_size: int) -> List[str]:
        """Split SSML by paragraph boundaries"""
        # Find paragraph breaks in SSML
        paragraphs = re.split(r'</p>\s*<break[^>]*/?>\s*<p>', ssml_text)
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk + paragraph) <= max_size:
                current_chunk += paragraph
            else:
                if current_chunk:
                    chunks.append(self._ensure_proper_ssml_wrapper(current_chunk))
                current_chunk = paragraph
        
        if current_chunk:
            chunks.append(self._ensure_proper_ssml_wrapper(current_chunk))
        
        return chunks
    
    def _split_ssml_by_sentences(self, content: str, target_size: int, max_size: int) -> List[str]:
        """Split SSML content by sentence boundaries while preserving markup"""
        # Split on sentence boundaries that don't break SSML tags
        sentences = re.split(r'</s>\s*(?=<s>|<break|[A-Z])', content)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            potential = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential) <= max_size:
                current_chunk = potential
            else:
                if current_chunk:
                    chunks.append(f'<speak>{current_chunk}</speak>')
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(f'<speak>{current_chunk}</speak>')
        
        return chunks
    
    def _ensure_proper_ssml_wrapper(self, content: str) -> str:
        """Ensure content is properly wrapped in SSML speak tags - FIXED VERSION"""
        content = content.strip()
        
        # Remove any incomplete or malformed tags
        content = re.sub(r'<[^>]*$', '', content)  # Remove unclosed tags at end
        content = re.sub(r'^[^<]*>', '', content)  # Remove orphaned closing tags at start
        
        # Ensure proper speak wrapper
        if not content.startswith('<speak>'):
            # Add opening speak tag
            if content.startswith('<'):
                content = f'<speak>{content}'
            else:
                content = f'<speak>{content}'
        
        if not content.endswith('</speak>'):
            # Add closing speak tag  
            if content.endswith('>'):
                content = f'{content}</speak>'
            else:
                content = f'{content}</speak>'
        
        # Validate the structure is sensible
        if content.count('<speak>') != content.count('</speak>'):
            # Fix mismatched tags
            content = re.sub(r'<speak>', '', content)
            content = re.sub(r'</speak>', '', content)
            content = f'<speak>{content}</speak>'
        
        return content

    # === Fallback Methods (Enhanced) ===
    
    def _basic_tts_fallback(self, text: str) -> List[str]:
        """Enhanced fallback TTS processing when LLM is not available"""
        print("TextCleaningService: Using enhanced basic TTS fallback (no LLM)")
        
        # Add more sophisticated pause markers
        text = re.sub(r'\n\s*\n', '\n\n... ', text)
        
        # Add pauses around common transition words
        transition_words = ['however', 'therefore', 'furthermore', 'moreover', 'consequently']
        for word in transition_words:
            text = re.sub(f'\\b{word}\\b', f'... {word} ...', text, flags=re.IGNORECASE)
        
        return self._chunk_for_audio_original(text)
    
    def _chunk_for_audio_original(self, text: str) -> List[str]:
        """Original chunking method for non-SSML content"""
        target_size = 3000    # Target chunk size for TTS
        max_chunk_size = 5000   # Hard limit
        
        if len(text) <= target_size:
            print("TextCleaningService: Text fits in single audio chunk")
            return [text]
        
        print(f"TextCleaningService: Splitting text ({len(text):,} chars) into TTS-friendly chunks")
        
        # Split on major section breaks first
        sections = text.split('\n\n... ...\n\n')
        all_chunks = []
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            if len(section) <= max_chunk_size:
                all_chunks.append(section)
            else:
                forced_chunks = self._force_split_large_text(section, target_size, max_chunk_size)
                all_chunks.extend(forced_chunks)
        
        print(f"TextCleaningService: Split into {len(all_chunks)} TTS-friendly chunks")
        return all_chunks
    
    def _force_split_large_text(self, text: str, target_size: int, max_size: int) -> List[str]:
        """Force split large text into manageable chunks"""
        chunks = []
        
        # Try splitting on pause markers first
        pause_parts = text.split('... ...')
        current_chunk = ""
        
        for part in pause_parts:
            part = part.strip()
            if not part:
                continue
            
            potential = current_chunk + "... ..." + part if current_chunk else part
            
            if len(potential) <= max_size:
                current_chunk = potential
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                if len(part) > max_size:
                    sentence_chunks = self._force_split_by_sentences(part, target_size, max_size)
                    chunks.extend(sentence_chunks)
                    current_chunk = ""
                else:
                    current_chunk = part
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _force_split_by_sentences(self, text: str, target_size: int, max_size: int) -> List[str]:
        """Force split by sentences with size limits"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            potential = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential) <= max_size:
                current_chunk = potential
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                if len(sentence) > max_size:
                    word_chunks = self._force_split_by_words(sentence, target_size, max_size)
                    chunks.extend(word_chunks)
                    current_chunk = ""
                else:
                    current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _force_split_by_words(self, text: str, target_size: int, max_size: int) -> List[str]:
        """Last resort: force split by words with strict size limits"""
        words = text.split()
        chunks = []
        current_chunk = ""
        
        for word in words:
            potential = current_chunk + " " + word if current_chunk else word
            
            if len(potential) <= max_size:
                current_chunk = potential
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = word
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

    # === Legacy Method Compatibility ===
    
    def _get_tts_optimized_prompt(self, text_chunk: str) -> str:
        """Original TTS optimization prompt for backward compatibility"""
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

Here is the text to clean and optimize for TTS:
---
{text_chunk}
---

Cleaned and TTS-optimized text:"""