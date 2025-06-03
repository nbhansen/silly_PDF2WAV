# text_processing.py - Complete rewrite with page range support
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
    """Handles text cleaning using Google's Gemini"""
    
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
            print("TextCleaner: Gemini initialized successfully")
            return model
        except Exception as e:
            print(f"TextCleaner: Failed to initialize Gemini: {e}")
            return None

    def clean(self, text: str) -> List[str]:
        """Clean the extracted text, returns list of cleaned chunks"""
        if not text.strip():
            print("TextCleaner: Empty text provided")
            return [""]
            
        if text.startswith("Error") or text.startswith("Could not convert"):
            print("TextCleaner: Skipping cleaning due to upstream error")
            return [text]
        
        if not self.model:
            print("TextCleaner: No LLM model available, returning text as-is")
            return [text]
            
        # Simple chunking for large texts
        if len(text) <= self.max_chunk_size:
            cleaned = self._clean_chunk(text)
            return [cleaned]
        
        print(f"TextCleaner: Text is large ({len(text):,} chars), splitting into chunks")
        chunks = self._smart_split(text, self.max_chunk_size)
        cleaned_chunks = []
        
        for i, chunk in enumerate(chunks):
            print(f"TextCleaner: Processing chunk {i+1}/{len(chunks)} ({len(chunk):,} chars)")
            if i > 0:
                time.sleep(1)  # Rate limiting for API
            
            cleaned_chunk = self._clean_chunk(chunk)
            cleaned_chunks.append(cleaned_chunk)
            
            # Write individual debug files
            try:
                debug_path = f"llm_cleaned_chunk_{i+1}_debug.txt"
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(cleaned_chunk)
                print(f"TextCleaner: Wrote chunk {i+1} to {debug_path}")
            except Exception as e:
                print(f"TextCleaner: Failed to write debug file: {e}")
        
        print(f"TextCleaner: Processed {len(cleaned_chunks)} chunks successfully")
        return cleaned_chunks

    def _clean_chunk(self, text_chunk: str) -> str:
        """Clean a single chunk of text using Gemini"""
        if not text_chunk.strip():
            return text_chunk
            
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
- **Maintain or Reconstruct Natural Spacing:** Ensure there is a single proper space between all words. Ensure appropriate single spacing follows all punctuation marks.
- **Handle Hyphenated Words:** If words are hyphenated across line breaks in the input (e.g., "effec-\\ntive"), correctly join them into single words (e.g., "effective") in the output.
- **Avoid Run-on Words:** The final output must be composed of clearly separated words and sentences. Do not merge words that should be distinct.
- The output must be **grammatically correct**, well-formed English text, structured into natural paragraphs suitable for reading aloud.
- **URLs**: If URLs are present they should be cleaned to just say for instance "example.com" instead of "https://example.com/this/is/a/very/long/url/that/should/not/be/read/aloud".

Here is the text to clean:
---
{text_chunk}
---
Cleaned text:"""

        try:
            response = self.model.generate_content(prompt)
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                cleaned_text = response.candidates[0].content.parts[0].text
                print(f"TextCleaner: Successfully cleaned chunk ({len(cleaned_text):,} chars output)")
                return cleaned_text
            else:
                print("TextCleaner: LLM response was empty or malformed")
                return text_chunk
        except Exception as e:
            print(f"TextCleaner: Error during cleaning: {e}")
            return text_chunk

    def _smart_split(self, text: str, max_size: int) -> List[str]:
        """Split text at sentence boundaries for better cleaning"""
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

