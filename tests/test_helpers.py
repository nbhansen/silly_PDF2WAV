# tests/test_helpers.py
from domain.models import (
    ITTSEngine, ILLMProvider, TextExtractor, PageRangeValidator, 
    PDFInfo, PageRange, ProcessingRequest
)
from typing import Dict, Any, List

class FakeTTSEngine(ITTSEngine):
    def __init__(self, should_fail=False, output_format="wav"):
        self.should_fail = should_fail
        self.output_format = output_format
        self.generated_texts = []
        
    def generate_audio_data(self, text_to_speak: str) -> bytes:
        self.generated_texts.append(text_to_speak)
        if self.should_fail:
            raise Exception("TTS generation failed")
        return f"audio_data_for_{len(text_to_speak)}_chars".encode()
    
    def get_output_format(self) -> str:
        return self.output_format

class FakeLLMProvider(ILLMProvider):
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.prompts = []
        
    def generate_content(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.should_fail:
            raise Exception("LLM generation failed")
        return f"Cleaned: {prompt[:50]}... with pauses"

class FakeTextExtractor(TextExtractor, PageRangeValidator):
    def __init__(self, text_to_return="Default extracted text", pdf_info=None):
        self.text_to_return = text_to_return
        self.pdf_info = pdf_info or PDFInfo(total_pages=1, title="Test PDF", author="Test Author")
        self.extraction_calls = []
        
    def extract_text(self, pdf_path: str, page_range: PageRange) -> str:
        self.extraction_calls.append((pdf_path, page_range))
        return self.text_to_return
    
    def get_pdf_info(self, pdf_path: str) -> PDFInfo:
        return self.pdf_info
        
    def validate_range(self, pdf_path: str, page_range: PageRange) -> Dict[str, Any]:
        return {'valid': True, 'total_pages': self.pdf_info.total_pages}

def create_test_request(pdf_path="test.pdf", output_name="test_output", page_range=None):
    return ProcessingRequest(
        pdf_path=pdf_path,
        output_name=output_name,
        page_range=page_range or PageRange()
    )