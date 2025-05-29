import google.generativeai as genai
import time

class LLMProcessor:
    """
    Handles text cleaning using Google's Generative AI (Gemini).
    """
    def __init__(self, api_key):
        """
        Initializes the LLMProcessor and configures the Google AI client.

        Args:
            api_key (str): The Google AI API key for Gemini.
        """
        self.api_key = api_key
        self.model = None
        
        if self.api_key and self.api_key != "YOUR_GOOGLE_AI_API_KEY" and self.api_key.strip() != "":
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash') 
                print("LLMProcessor: Google AI API (Gemini) configured successfully.")
            except Exception as e:
                print(f"LLMProcessor: Error configuring Google AI API: {e}")
                print("LLM cleaning will likely fail. Ensure your API key is correct and the API is enabled.")
        else:
            print("LLMProcessor: Google AI API Key not provided or is placeholder. LLM cleaning will be skipped.")

    def clean_text(self, text_to_clean):
        """
        Sends text to the Gemini model for cleaning, processing in chunks if necessary.

        Args:
            text_to_clean (str): The raw text string to be cleaned.

        Returns:
            str: The cleaned text from the LLM, or the original text/error message if cleaning fails or is skipped.
        """
        if not self.model:
            print("LLMProcessor: Model not initialized (check API Key). Skipping cleaning.")
            return "LLM cleaning skipped: Model not initialized."
        
        if not text_to_clean or text_to_clean.strip() == "" or \
           text_to_clean.startswith("Could not convert") or \
           text_to_clean.startswith("No text could be extracted") or \
           text_to_clean.startswith("Error during OCR") or \
           text_to_clean.startswith("Tesseract OCR engine not found"):
            print("LLMProcessor: Skipping cleaning due to empty or error text from upstream process.")
            return text_to_clean

        # Process in chunks if text is very long
        CHUNK_SIZE = 100000   # Conservative chunk size for Gemini
        OVERLAP_SIZE = 2000   # Larger overlap to maintain context at boundaries
        
        if len(text_to_clean) <= CHUNK_SIZE:
            # Process normally for shorter texts
            print(f"LLMProcessor: Processing single chunk ({len(text_to_clean)} chars)")
            return self._clean_single_chunk(text_to_clean)
        else:
            # Process in chunks for longer texts
            print(f"LLMProcessor: Text is long ({len(text_to_clean)} chars). Processing in chunks.")
            return self._clean_text_chunked(text_to_clean, CHUNK_SIZE, OVERLAP_SIZE)

    def _clean_single_chunk(self, text_chunk):
        """Process a single chunk of text through Gemini."""
        print(f"LLMProcessor: Sending text (length: {len(text_chunk)} chars) to Gemini for cleaning.")
        
        # Revised prompt with more emphasis on spacing and natural language output
        prompt = f"""Your primary goal is to clean the following text, extracted from an academic research paper. The cleaned text should be highly readable and well-suited for text-to-speech (TTS) conversion.

**Key Cleaning Tasks (Remove these elements):**
- Headers and Footers: This includes page numbers, running titles, journal names, conference names, and dates that appear consistently at the top or bottom of pages.
- Line Numbers: If present in the margins.
- Marginalia or Side Notes: Any comments or notes found in the margins.
- Watermarks or Stamps: Text like "Draft," "Confidential," or institutional logos/stamps.
- Artifacts from Scanning: Random specks, stray lines, or heavily distorted characters that are clearly not part of the intended text.
- Repeated Copyright or Licensing Information: Especially if it appears on every page or in a boilerplate manner.
- Extraneous Punctuation or Symbols: Symbols or punctuation that are likely errors from the OCR process and do not contribute to the meaning.

**Core Content Preservation (Focus on these):**
- Preserve all text that would be read aloud in an ebook, including all paragraphs and their intended structure.
- Skip in-text citations (e.g., [1], (Author, 2023)).
- Skip mathematical formulas and equations if present.

**Crucial for Readability and TTS (Pay close attention to these):**
- **Maintain or Reconstruct Natural Spacing:** Ensure there is a single proper space between all words. Ensure appropriate single spacing follows all punctuation marks (e.g., a period, comma, colon, semicolon should be followed by a space, unless it's part of a standard abbreviation like "e.g.").
- **Handle Hyphenated Words:** If words are hyphenated across line breaks in the input (e.g., "effec-\\ntive"), correctly join them into single words (e.g., "effective") in the output. This single word should then be followed by appropriate spacing.
- **Avoid Run-on Words:** The final output must be composed of clearly separated words and sentences. Do not merge words that should be distinct.
- The output must be grammatically correct, well-formed English text, structured into natural paragraphs suitable for reading aloud.

**Cautious Removal (Use best judgment to maintain readability of primary content):**
- Figure Captions and Table Titles: If these are interspersed in a way that breaks the flow of the main narrative, try to remove them. However, if they are embedded and provide crucial context, it might be better to keep them.
- Footnote/Endnote Markers: Keep markers like [1] or ^2 within the text if they are part of the original flow. However, remove the full text of footnotes or endnotes if they have been erroneously pulled into the main text flow by OCR.

Here is the text to clean:
---
{text_chunk}
---
Cleaned text:"""
        
        try:
            response = self.model.generate_content(prompt)
            print("LLMProcessor: LLM (Gemini) response received.")
            
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                cleaned_text = response.candidates[0].content.parts[0].text
                return cleaned_text
            else:
                feedback_info = ""
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    feedback_info += f" Prompt Feedback: {response.prompt_feedback}."
                if hasattr(response, 'candidates') and response.candidates and hasattr(response.candidates[0], 'finish_reason'):
                     feedback_info += f" Finish Reason: {response.candidates[0].finish_reason}."
                     if hasattr(response.candidates[0], 'safety_ratings'):
                         feedback_info += f" Safety Ratings: {response.candidates[0].safety_ratings}."
                print(f"LLMProcessor: LLM response issue.{feedback_info if feedback_info else ' Unexpected structure or content possibly blocked.'}")
                return f"Error: LLM response issue.{feedback_info if feedback_info else ' Unexpected structure or content possibly blocked.'}"
        except Exception as e:
            print(f"LLMProcessor: Error during LLM cleaning with Gemini: {e}")
            return f"Error during LLM cleaning with Gemini: {str(e)}"

    def _clean_text_chunked(self, text_to_clean, chunk_size, overlap_size):
        """Process text in overlapping chunks and reassemble."""
        chunks = []
        
        cleaned_chunks = []

        text_len = len(text_to_clean)
        start = 0

        print(f"LLMProcessor: Splitting text into chunks of size {chunk_size} with overlap of {overlap_size}...")
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk = text_to_clean[start:end]

            # Try to break at a sentence boundary near the end (look for punctuation + whitespace)
            if end < text_len:
                # Look for good break points in the last 20% of the chunk
                search_start = max(start + int(chunk_size * 0.8), start + chunk_size // 2)
                search_region = chunk[search_start - start:]
                
                best_break = -1
                # Look for sentence endings
                for punct in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
                    idx = search_region.rfind(punct)
                    if idx > best_break:
                        best_break = idx
                
                if best_break > 0:
                    # Adjust end to the sentence boundary
                    end = search_start + best_break + 1  # +1 to include the punctuation
                    chunk = text_to_clean[start:end]

            chunks.append(chunk)
            print(f"LLMProcessor: Created chunk {len(chunks)} - chars {start} to {end} (length: {len(chunk)})")
            
            if end >= text_len:
                break
            
            # FIXED: Advance by chunk_size minus overlap, but ensure we don't go backwards
            next_start = max(end - overlap_size, start + 1)
            start = next_start

        print(f"LLMProcessor: Split into {len(chunks)} chunks for processing.")

        # Process each chunk with rate limiting
        for i, chunk in enumerate(chunks):
            print(f"LLMProcessor: Processing chunk {i+1}/{len(chunks)} (length: {len(chunk)} chars)...")
            if i > 0:
                time.sleep(1)
            cleaned_chunk = self._clean_single_chunk(chunk)
            if cleaned_chunk.startswith("Error"):
                print(f"LLMProcessor: Error in chunk {i+1}, using original chunk.")
                cleaned_chunk = chunk
            print(f"LLMProcessor: Cleaned chunk {i+1} length: {len(cleaned_chunk)} chars")
            cleaned_chunks.append(cleaned_chunk)

        print("LLMProcessor: Reassembling cleaned chunks...")

        # FIXED: Improved chunk reassembly logic
        if not cleaned_chunks:
            return ""
        
        result = cleaned_chunks[0]
        
        for i in range(1, len(cleaned_chunks)):
            current_chunk = cleaned_chunks[i]
            
            # Try to find and remove overlap between consecutive chunks
            if overlap_size > 0 and len(result) > overlap_size:
                # Get the last part of result for overlap detection
                overlap_search_text = result[-overlap_size:].strip()
                
                # Look for this text at the beginning of the current chunk
                current_chunk_start = current_chunk[:overlap_size*2].strip()  # Search in first part of current chunk
                
                # Find the best overlap match
                best_overlap = 0
                # Try different overlap lengths
                for test_len in range(min(len(overlap_search_text), len(current_chunk_start)), 50, -10):
                    if test_len <= 0:
                        break
                    test_overlap = overlap_search_text[-test_len:]
                    if current_chunk_start.startswith(test_overlap):
                        best_overlap = test_len
                        print(f"LLMProcessor: Found overlap of {best_overlap} chars between chunks {i} and {i+1}")
                        break
                
                if best_overlap > 0:
                    # Remove the overlapping part from the current chunk
                    overlap_text = overlap_search_text[-best_overlap:]
                    if current_chunk.startswith(overlap_text):
                        current_chunk = current_chunk[best_overlap:]
                    else:
                        # Try to find it within the first part and remove
                        overlap_pos = current_chunk.find(overlap_text)
                        if 0 <= overlap_pos <= 100:  # Only if found near the beginning
                            current_chunk = current_chunk[overlap_pos + best_overlap:]
            
            # Add appropriate spacing between chunks if needed
            if result and current_chunk:
                if not result.endswith(' ') and not current_chunk.startswith(' '):
                    result += ' '
            
            result += current_chunk

        print(f"LLMProcessor: Chunked processing complete. Final length: {len(result)} chars")

        # --- DEBUG: Write cleaned result to file ---
        try:
            debug_path = "llm_cleaned_debug.txt"
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"LLMProcessor: Wrote cleaned text to {debug_path} for debugging.")
        except Exception as e:
            print(f"LLMProcessor: Failed to write debug file: {e}")

        return result