# domain/models.py - Pure Domain Models Only
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

# --- Core Domain Models ---

@dataclass
class PageRange:
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    
    def is_full_document(self) -> bool:
        return self.start_page is None and self.end_page is None

@dataclass
class ProcessingRequest:
    pdf_path: str
    output_name: str
    page_range: PageRange
    
@dataclass
class PDFInfo:
    total_pages: int
    title: str
    author: str

@dataclass
class ProcessingResult:
    success: bool
    audio_files: Optional[List[str]] = None
    combined_mp3_file: Optional[str] = None
    error: Optional[str] = None
    debug_info: Optional[Dict[str, Any]] = None