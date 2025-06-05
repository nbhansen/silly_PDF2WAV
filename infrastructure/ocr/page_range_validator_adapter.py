# infrastructure/ocr/page_range_validator_adapter.py
from typing import Dict, Any
from domain.models import PageRangeValidator, PageRange
from text_processing import OCRExtractor

class PageRangeValidatorAdapter(PageRangeValidator):
    """Adapter for page range validation using OCRExtractor"""
    
    def __init__(self, ocr_extractor: OCRExtractor):
        self._extractor = ocr_extractor
    
    def validate_range(self, pdf_path: str, page_range: PageRange) -> Dict[str, Any]:
        try:
            pdf_info = self._extractor.get_pdf_info(pdf_path)
            total_pages = pdf_info.get('total_pages', 0)
            
            if total_pages == 0:
                return {
                    'valid': False,
                    'error': 'Could not determine PDF page count',
                    'total_pages': 0
                }
            
            # Validate start page
            if page_range.start_page is not None:
                if page_range.start_page < 1:
                    return self._error_result('Start page must be 1 or greater', total_pages)
                if page_range.start_page > total_pages:
                    return self._error_result(f'Start page {page_range.start_page} exceeds total pages ({total_pages})', total_pages)
            
            # Validate end page
            if page_range.end_page is not None:
                if page_range.end_page < 1:
                    return self._error_result('End page must be 1 or greater', total_pages)
                if page_range.end_page > total_pages:
                    return self._error_result(f'End page {page_range.end_page} exceeds total pages ({total_pages})', total_pages)
            
            # Validate range consistency
            if page_range.start_page is not None and page_range.end_page is not None:
                if page_range.start_page > page_range.end_page:
                    return self._error_result(f'Start page ({page_range.start_page}) cannot be greater than end page ({page_range.end_page})', total_pages)
            
            # All validations passed
            actual_start = page_range.start_page if page_range.start_page is not None else 1
            actual_end = page_range.end_page if page_range.end_page is not None else total_pages
            
            return {
                'valid': True,
                'total_pages': total_pages,
                'actual_start': actual_start,
                'actual_end': actual_end,
                'pages_to_process': actual_end - actual_start + 1,
                'percentage_of_document': ((actual_end - actual_start + 1) / total_pages) * 100
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Page range validation failed: {str(e)}',
                'total_pages': 0
            }
    
    def _error_result(self, error: str, total_pages: int) -> Dict[str, Any]:
        return {
            'valid': False,
            'error': error,
            'total_pages': total_pages
        }