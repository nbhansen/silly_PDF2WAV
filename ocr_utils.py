import pytesseract
from pdf2image import convert_from_path
import pdfplumber
# from PIL import Image # Not directly used here, but a dependency of pdf2image/pytesseract

class OCRProcessor:
    """
    Handles text extraction from PDF files, attempting direct text extraction first,
    then falling back to OCR if necessary.
    """
    def __init__(self, tesseract_cmd=None, poppler_path_custom=None):
        """
        Initializes the OCRProcessor.

        Args:
            tesseract_cmd (str, optional): Path to the Tesseract executable.
                                           Defaults to None (Tesseract must be in PATH).
            poppler_path_custom (str, optional): Path to the Poppler bin directory.
                                                 Defaults to None (Poppler must be in PATH).
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self.poppler_path_custom = poppler_path_custom # Store for use in convert_from_path

    def _extract_text_directly(self, pdf_path):
        """
        Attempts to extract text directly from a PDF file using pdfplumber.

        Args:
            pdf_path (str): The path to the PDF file.

        Returns:
            str or None: The extracted text if successful, otherwise None.
        """
        print(f"OCRProcessor: Attempting direct text extraction for {pdf_path}")
        text_content = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + f"\n\n--- Page {page_num+1} End (Direct) ---\n\n"
            if text_content.strip():
                print("OCRProcessor: Direct text extraction successful.")
                return text_content.strip()
            else:
                print("OCRProcessor: Direct text extraction yielded no text.")
                return None
        except Exception as e:
            print(f"OCRProcessor: Error during direct text extraction for '{pdf_path}': {e}")
            return None

    def _extract_text_with_ocr(self, pdf_path):
        """
        Extracts text from a PDF using OCR (pdf2image + Tesseract).
        Includes image preprocessing (grayscale, binarization).

        Args:
            pdf_path (str): The path to the PDF file.

        Returns:
            str: The extracted text, or an error message string if OCR fails.
        """
        print(f"OCRProcessor: Starting OCR (image-based) for {pdf_path}")
        try:
            # Use custom poppler_path if provided during initialization
            images = convert_from_path(pdf_path, dpi=300, grayscale=True, poppler_path=self.poppler_path_custom)
            
            full_text_content = ""
            if not images:
                print("OCRProcessor: Could not convert PDF to images for OCR.")
                return "Could not convert PDF to images for OCR."
            
            for i, image in enumerate(images):
                # Image is already grayscale from convert_from_path.
                # Apply binarization (thresholding)
                processed_image = image.convert('L') 
                threshold_value = 180 # This value might need tuning based on document types.
                processed_image = processed_image.point(lambda p: 0 if p < threshold_value else 255)
                # print(f"OCRProcessor: Applied binarization to page {i+1}") # Can be verbose
                
                page_text_content = pytesseract.image_to_string(processed_image, lang='eng')
                full_text_content += page_text_content + f"\n\n--- Page {i+1} End (OCR) ---\n\n"
            
            if not full_text_content.strip():
                print("OCRProcessor: OCR process yielded no text.")
                return "OCR process yielded no text."
            print("OCRProcessor: OCR (image-based) successful.")
            return full_text_content
        except pytesseract.TesseractNotFoundError:
            print("OCRProcessor: Tesseract OCR engine not found. Ensure it's installed and in PATH, or tesseract_cmd is set.")
            return "Tesseract OCR engine not found. Check installation and PATH."
        except Exception as e: # Catch other potential errors from pdf2image or Pillow
            print(f"OCRProcessor: Error during OCR (image-based) process for '{pdf_path}': {e}")
            return f"Error during OCR (image-based) process: {str(e)}"

    def extract_text_from_pdf(self, pdf_path):
        print(f"OCRProcessor: Starting text extraction pipeline for {pdf_path}")
        
        direct_text_content = self._extract_text_directly(pdf_path)
        
        MIN_CHARS_FOR_DIRECT_TEXT = 100 # Arbitrary threshold
        if direct_text_content and len(direct_text_content) > MIN_CHARS_FOR_DIRECT_TEXT:
            print(f"OCRProcessor: Using directly extracted text (length: {len(direct_text_content)}).")
            extracted_text = direct_text_content
        else:
            if direct_text_content:
                print(f"OCRProcessor: Direct text was minimal (length: {len(direct_text_content)}). Falling back to OCR.")
            else:
                print("OCRProcessor: No direct text found. Falling back to OCR.")
            extracted_text = self._extract_text_with_ocr(pdf_path)
            print(f"OCR extracted text length: {len(extracted_text)}")

        # Always write debug file
        with open("ocr_extracted_debug.txt", "w", encoding="utf-8") as f:
            f.write(extracted_text)
        print(f"OCRProcessor: Wrote extracted text to ocr_extracted_debug.txt for debugging.")

        return extracted_text
