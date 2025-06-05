# text_processing.py - Complete rewrite with TTS optimization
import google.generativeai as genai
import pytesseract
from pdf2image import convert_from_path
import pdfplumber
import time
import re
from typing import Optional, List

class OCRExtractor:
    """Handles text extraction from PDF files with page range support"""
    
    def __init__(self, tesseract_cmd=None, poppler_path_custom=None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self.poppler_path_custom = poppler_path_custom

    def extract(self, pdf_path: str, start_page: int = None, end_page: int = None) -> str:
        """Extract text from PDF with optional page range"""
        print(f"OCRExtractor: Starting extraction for {pdf_path}")
        
        if start_page is not None or end_page is not None:
            print(f"OCRExtractor: Using page range {start_page or 1} to {end_page or 'end'}")
            return self._extract_with_page_range(pdf_path, start_page, end_page)
        else:
            print("OCRExtractor: Processing entire PDF")
            return self._extract_full_pdf(pdf_path)
    
    def _extract_with_page_range(self, pdf_path: str, start_page: int = None, end_page: int = None) -> str:
        """Extract from specified page range"""
        try:
            # Try direct extraction from page range first
            direct_text = self._extract_direct_with_range(pdf_path, start_page, end_page)
            if direct_text and len(direct_text) > 100:
                print(f"OCRExtractor: Using direct extraction from page range ({len(direct_text)} chars)")
                return direct_text
            
            # Fall back to OCR on page range
            print("OCRExtractor: Falling back to OCR on page range")
            ocr_text = self._extract_ocr_with_range(pdf_path, start_page, end_page)
            print(f"OCRExtractor: OCR extracted {len(ocr_text)} chars from page range")
            return ocr_text
                
        except Exception as e:
            print(f"OCRExtractor: Page range extraction failed: {e}")
            # Fall back to full PDF
            return self._extract_full_pdf(pdf_path)
    
    def _extract_full_pdf(self, pdf_path: str) -> str:
        """Extract from entire PDF (original behavior)"""
        # Try direct extraction first
        direct_text = self._extract_direct(pdf_path)
        if direct_text and len(direct_text) > 100:
            print(f"OCRExtractor: Using direct extraction ({len(direct_text)} chars)")
            return direct_text
        
        # Fall back to OCR
        print("OCRExtractor: Falling back to OCR")
        ocr_text = self._extract_ocr(pdf_path)
        print(f"OCRExtractor: OCR extracted {len(ocr_text)} chars")
        return ocr_text

    def _extract_direct_with_range(self, pdf_path: str, start_page: int = None, end_page: int = None) -> Optional[str]:
        """Extract text directly from specified page range"""
        try:
            text_content = ""
            
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                
                # Determine actual page range
                actual_start = (start_page - 1) if start_page else 0
                actual_end = min(end_page, total_pages) if end_page else total_pages
                
                # Validate page range
                if actual_start < 0:
                    actual_start = 0
                if actual_end > total_pages:
                    actual_end = total_pages
                if actual_start >= actual_end:
                    print(f"OCRExtractor: Invalid page range {start_page}-{end_page}")
                    return None
                
                print(f"OCRExtractor: Processing pages {actual_start + 1} to {actual_end} of {total_pages}")
                
                for page_num in range(actual_start, actual_end):
                    page = pdf.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + f"\n\n--- Page {page_num + 1} End ---\n\n"
            
            return text_content.strip() if text_content.strip() else None
        except Exception as e:
            print(f"OCRExtractor: Direct range extraction failed: {e}")
            return None

    def _extract_direct(self, pdf_path: str) -> Optional[str]:
        """Extract text directly using pdfplumber (full PDF)"""
        try:
            text_content = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + f"\n\n--- Page {page_num+1} End ---\n\n"
            return text_content.strip() if text_content.strip() else None
        except Exception as e:
            print(f"OCRExtractor: Direct extraction failed: {e}")
            return None

    def _extract_ocr_with_range(self, pdf_path: str, start_page: int = None, end_page: int = None) -> str:
        """OCR extraction from specified page range"""
        try:
            # Get total pages first for validation
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
            
            # Validate and adjust page range
            actual_start = start_page if start_page else 1
            actual_end = min(end_page, total_pages) if end_page else total_pages
            
            if actual_start < 1:
                actual_start = 1
            if actual_end > total_pages:
                actual_end = total_pages
            if actual_start > actual_end:
                print(f"OCRExtractor: Invalid OCR page range {start_page}-{end_page}")
                return "Error: Invalid page range for OCR"
            
            print(f"OCRExtractor: OCR processing pages {actual_start} to {actual_end}")
            
            # Convert specified page range
            images = convert_from_path(
                pdf_path, 
                dpi=300, 
                grayscale=True,
                first_page=actual_start,
                last_page=actual_end,
                poppler_path=self.poppler_path_custom
            )
            
            full_text = ""
            
            for i, image in enumerate(images):
                processed_image = image.convert('L')
                processed_image = processed_image.point(lambda p: 0 if p < 180 else 255)
                page_text = pytesseract.image_to_string(processed_image, lang='eng')
                actual_page_num = actual_start + i
                full_text += page_text + f"\n\n--- Page {actual_page_num} End (OCR) ---\n\n"
            
            return full_text if full_text.strip() else "OCR process yielded no text."
            
        except Exception as e:
            print(f"OCRExtractor: Range OCR failed: {e}")
            return f"Error during range OCR: {str(e)}"

    def _extract_ocr(self, pdf_path: str) -> str:
        """Extract text using OCR (full PDF)"""
        try:
            images = convert_from_path(pdf_path, dpi=300, grayscale=True, 
                                     poppler_path=self.poppler_path_custom)
            
            full_text = ""
            for i, image in enumerate(images):
                processed_image = image.convert('L')
                processed_image = processed_image.point(lambda p: 0 if p < 180 else 255)
                page_text = pytesseract.image_to_string(processed_image, lang='eng')
                full_text += page_text + f"\n\n--- Page {i+1} End (OCR) ---\n\n"
            
            return full_text if full_text.strip() else "OCR process yielded no text."
            
        except Exception as e:
            print(f"OCRExtractor: OCR failed: {e}")
            return f"Error during OCR: {str(e)}"

    def get_pdf_info(self, pdf_path: str) -> dict:
        """Get basic PDF information for user interface"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return {
                    'total_pages': len(pdf.pages),
                    'title': pdf.metadata.get('Title', 'Unknown') if pdf.metadata else 'Unknown',
                    'author': pdf.metadata.get('Author', 'Unknown') if pdf.metadata else 'Unknown'
                }
        except Exception as e:
            print(f"OCRExtractor: Failed to get PDF info: {e}")
            return {
                'total_pages': 0,
                'title': 'Unknown',
                'author': 'Unknown'
            }

class TextCleaner:
    """Handles text cleaning and TTS optimization using Google's Gemini"""
    
    def __init__(self, api_key: str, max_chunk_size: int = 100000):
        self.api_key = api_key
        self.max_chunk_size = max_chunk_size
        self.model = self._init_model()
    
    def _init_model(self):
        """Initialize the Gemini model"""
        if not self.api_key or self.api_key == "YOUR_GOOGLE_AI_API_KEY" or self.api_key == "crawling in my skin":
            print("TextCleaner: No valid API key provided - skipping LLM cleaning")
            return None
            
        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            print("TextCleaner: Gemini initialized successfully for TTS optimization")
            return model
        except Exception as e:
            print(f"TextCleaner: Failed to initialize Gemini: {e}")
            return None

    def clean(self, text: str) -> List[str]:
        """
        Clean text and optimize for TTS - main entry point for backward compatibility
        """
        return self.clean_for_tts(text)

    def clean_for_tts(self, text: str) -> List[str]:
        """
        Clean text with LLM and optimize for TTS in one step
        """
        
        if not text.strip():
            print("TextCleaner: Empty text provided")
            return [""]
            
        if text.startswith("Error") or text.startswith("Could not convert"):
            print("TextCleaner: Skipping cleaning due to upstream error")
            return [text]
        
        if not self.model:
            print("TextCleaner: No LLM model available, using basic TTS enhancement")
            return self._basic_tts_fallback(text)
        
        # For large texts, clean in chunks with TTS optimization
        if len(text) <= self.max_chunk_size:
            cleaned_text = self._clean_chunk_for_tts(text)
            return self._chunk_for_audio(cleaned_text)
        else:
            print(f"TextCleaner: Large text ({len(text):,} chars), processing in chunks")
            initial_chunks = self._smart_split(text, self.max_chunk_size)
            cleaned_chunks = []
            
            for i, chunk in enumerate(initial_chunks):
                print(f"TextCleaner: Cleaning and TTS-optimizing chunk {i+1}/{len(initial_chunks)}")
                if i > 0:
                    time.sleep(1)  # Rate limiting
                cleaned_chunk = self._clean_chunk_for_tts(chunk)
                cleaned_chunks.append(cleaned_chunk)
                
                # Write individual debug files
                try:
                    debug_path = f"llm_tts_cleaned_chunk_{i+1}_debug.txt"
                    with open(debug_path, "w", encoding="utf-8") as f:
                        f.write(cleaned_chunk)
                    print(f"TextCleaner: Wrote TTS-optimized chunk {i+1} to {debug_path}")
                except Exception as e:
                    print(f"TextCleaner: Failed to write debug file: {e}")
            
            # Combine cleaned chunks with section pauses
            combined_text = "\n\n... ...\n\n".join(cleaned_chunks)  # Add pauses between major sections
            return self._chunk_for_audio(combined_text)

    def _clean_chunk_for_tts(self, text_chunk: str) -> str:
        """Clean a single chunk with TTS optimization"""
        if not text_chunk.strip():
            return text_chunk
            
        prompt = self._get_tts_optimized_prompt(text_chunk)
        
        try:
            response = self.model.generate_content(prompt)
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                cleaned_text = response.candidates[0].content.parts[0].text
                print(f"TextCleaner: Successfully cleaned and TTS-optimized chunk ({len(cleaned_text):,} chars)")
                return cleaned_text
            else:
                print("TextCleaner: LLM response was empty, using fallback")
                return self._basic_tts_fallback(text_chunk)[0]
        except Exception as e:
            print(f"TextCleaner: Error during TTS optimization: {e}")
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
        print("TextCleaner: Using basic TTS fallback (no LLM)")
        # Just do basic paragraph enhancement
        text = re.sub(r'\n\s*\n', '\n\n... ', text)
        return self._chunk_for_audio(text)
    
    def _chunk_for_audio(self, text: str) -> List[str]:
        """Split TTS-optimized text into audio-appropriate chunks"""
        # The text is already TTS-optimized, so we can be more aggressive about preserving structure
        target_size = 80000  # Larger chunks since they're already optimized
        
        if len(text) <= target_size:
            print("TextCleaner: Text fits in single audio chunk")
            return [text]
        
        print(f"TextCleaner: Splitting TTS-optimized text ({len(text):,} chars) for audio")
        
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
        
        print(f"TextCleaner: Split TTS-optimized text into {len(chunks)} audio chunks")
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
        
        print(f"TextCleaner: Split {len(text):,} chars into {len(final_chunks)} chunks")
        return final_chunks