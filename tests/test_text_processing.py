# tests/test_text_processing.py
from domain.services.text_cleaning_service import TextCleaningService
from tests.test_helpers import FakeLLMProvider

def test_text_cleaning_no_llm():
    cleaner = TextCleaningService(llm_provider=None)
    result = cleaner.clean_text("Test text.\n\nSecond paragraph.")
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert "..." in result[0]  # Should add pause markers

def test_text_cleaning_with_llm():
    fake_llm = FakeLLMProvider()
    cleaner = TextCleaningService(llm_provider=fake_llm)
    
    result = cleaner.clean_text("Raw text to clean.", llm_provider=fake_llm)
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert "Cleaned:" in result[0]
    assert len(fake_llm.prompts) == 1

def test_text_cleaning_handles_empty_text():
    cleaner = TextCleaningService(llm_provider=None)
    result = cleaner.clean_text("")
    assert result == [""]

def test_text_cleaning_handles_error_text():
    cleaner = TextCleaningService(llm_provider=None)
    result = cleaner.clean_text("Error: Something failed")
    assert result == ["Error: Something failed"]

def test_page_range_logic():
    from domain.models import PageRange
    
    full_range = PageRange()
    assert full_range.is_full_document()
    
    partial_range = PageRange(start_page=1, end_page=5)
    assert not partial_range.is_full_document()