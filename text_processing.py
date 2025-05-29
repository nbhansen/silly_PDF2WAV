# text_processing.py
import google.generativeai as genai
import pytesseract
from pdf2image import convert_from_path
import pdfplumber
import time
import re
from typing import Optional, List

class OCRExtractor:
    """Handles text extraction from PDF files"""
    
    def __init__(self, tesseract_cmd=None, poppler_path_custom=None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self.poppler_path_custom = poppler_path_custom

    def extract(self, pdf_path: str) -> str:
        """Extract text from PDF, trying direct method first, then OCR"""
        print(f"OCRExtractor: Starting extraction for {pdf_path}")
        
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

    def _extract_direct(self, pdf_path: str) -> Optional[str]:
        """Extract text directly using pdfplumber"""
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

    def _extract_ocr(self, pdf_path: str) -> str:
        """Extract text using OCR"""
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

class TextCleaner:
    """Handles text cleaning using Google's Gemini"""
    
    def __init__(self, api_key: str, max_chunk_size: int = 100000):
        self.api_key = api_key
        self.max_chunk_size = max_chunk_size
        self.model = self._init_model()
    
    def _init_model(self):
        """Initialize the Gemini model"""
        if not self.api_key or self.api_key == "YOUR_GOOGLE_AI_API_KEY":
            print("TextCleaner: No valid API key provided")
            return None
            
        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            print("TextCleaner: Gemini initialized successfully")
            return model
        except Exception as e:
            print(f"TextCleaner: Failed to initialize Gemini: {e}")
            return None

    def clean(self, text: str) -> str:
        """Clean the extracted text"""
        if not self.model or not text.strip():
            print("TextCleaner: Skipping cleaning (no model or empty text)")
            return text
            
        if text.startswith("Error") or text.startswith("Could not convert"):
            print("TextCleaner: Skipping cleaning due to upstream error")
            return text
            
        # Simple chunking for large texts
        if len(text) <= self.max_chunk_size:
            return self._clean_chunk(text)
        
        print(f"TextCleaner: Text is large ({len(text)} chars), splitting into chunks")
        chunks = self._smart_split(text, self.max_chunk_size)
        cleaned_chunks = []
        
        for i, chunk in enumerate(chunks):
            print(f"TextCleaner: Processing chunk {i+1}/{len(chunks)}")
            if i > 0:
                time.sleep(1)  # Rate limiting
            cleaned_chunk = self._clean_chunk(chunk)
            cleaned_chunks.append(cleaned_chunk)
        
        result = " ".join(cleaned_chunks)
        
        # Write debug file
        try:
            with open("llm_cleaned_debug.txt", "w", encoding="utf-8") as f:
                f.write(result)
            print("TextCleaner: Debug file written")
        except Exception as e:
            print(f"TextCleaner: Failed to write debug file: {e}")
            
        return result

    def _clean_chunk(self, text_chunk: str) -> str:
        """Clean a single chunk of text"""
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
- The output must be grammatically correct, well-formed English text, structured into natural paragraphs suitable for reading aloud.

Here is the text to clean:
---
{text_chunk}
---
Cleaned text:"""

        try:
            response = self.model.generate_content(prompt)
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            else:
                print("TextCleaner: LLM response issue")
                return text_chunk
        except Exception as e:
            print(f"TextCleaner: Error during cleaning: {e}")
            return text_chunk

    def _smart_split(self, text: str, max_size: int) -> List[str]:
        """Split text at sentence boundaries"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > max_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
                
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks