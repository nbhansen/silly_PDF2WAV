# tests/domain/services/test_text_cleaning_simple.py
from domain.services.text_cleaning_service import TextCleaningService
from tests.test_helpers import FakeLLMProvider

def test_text_cleaning_service_creation():
    fake_llm = FakeLLMProvider()
    service = TextCleaningService(llm_provider=fake_llm)
    assert service.llm_provider == fake_llm

def test_text_cleaning_no_llm():
    service = TextCleaningService(llm_provider=None)
    result = service.clean_text("Test text.\n\nSecond paragraph.")
    assert isinstance(result, list)
    assert len(result) > 0

def test_text_cleaning_with_llm():
    fake_llm = FakeLLMProvider()
    service = TextCleaningService(llm_provider=fake_llm)
    result = service.clean_text("Raw text", fake_llm)
    assert isinstance(result, list)
    assert len(result) > 0
    assert len(fake_llm.prompts) >= 1