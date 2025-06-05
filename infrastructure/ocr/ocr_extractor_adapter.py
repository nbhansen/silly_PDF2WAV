# infrastructure/ocr/ocr_extractor_adapter.py
from domain.models import TextExtractor, PDFInfo, PageRange
from text_processing import OCRExtractor as LegacyOCRExtractor

class OCRExtractorAdapter(TextExtractor):
    """Adapter for existing OCRExtractor to implement domain interface"""
    
    def __init__(self, tesseract_cmd=None, poppler_path_custom=None):
        self._extractor = LegacyOCRExtractor(tesseract_cmd, poppler_path_custom)
    
    def extract_text(self, pdf_path: str, page_range: PageRange) -> str:
        return self._extractor.extract(
            pdf_path, 
            page_range.start_page, 
            page_range.end_page
        )
    
    def get_pdf_info(self, pdf_path: str) -> PDFInfo:
        info_dict = self._extractor.get_pdf_info(pdf_path)
        return PDFInfo(
            total_pages=info_dict['total_pages'],
            title=info_dict['title'],
            author=info_dict['author']
        )