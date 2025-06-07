import pytest
from unittest.mock import MagicMock, patch
from domain.services.text_cleaning_service import TextCleaningService
from domain.models import ILLMProvider

class MockLLMProvider(ILLMProvider):
    def generate_content(self, prompt: str) -> str:
        if "error" in prompt:
            raise Exception("Mock LLM Error")
        # Simulate cleaning: remove "bad_word", replace "citation" with "", simplify URLs
        cleaned_text = prompt.replace("bad_word", "").replace("(citation)", "").replace("https://www.example.com/path", "example.com")
        # Simulate TTS optimization: add some ellipses
        cleaned_text = cleaned_text.replace(". ", "... ")
        return cleaned_text

@pytest.fixture
def mock_llm_provider():
    return MockLLMProvider()

@pytest.fixture
def text_cleaning_service(mock_llm_provider):
    return TextCleaningService(llm_provider=mock_llm_provider, max_chunk_size=100)

@pytest.fixture
def text_cleaning_service_no_llm():
    return TextCleaningService(llm_provider=None, max_chunk_size=100)

class TestTextCleaningService:

    @patch('builtins.open', new_callable=MagicMock)
    @patch('os.path.exists', return_value=True)
    def test_clean_text_with_llm_small_text(self, mock_exists, mock_open, text_cleaning_service):
        raw_text = "This is a test sentence. It has a bad_word and (citation). Also, a URL: https://www.example.com/path."
        cleaned_chunks = text_cleaning_service.clean_text(raw_text)
        
        assert len(cleaned_chunks) == 1
        expected_cleaned_text = "This is a test sentence... It has a and. Also, a URL: example.com."
        assert cleaned_chunks[0].strip() == expected_cleaned_text.strip()
        text_cleaning_service.llm_provider.generate_content.assert_called_once()

    def test_clean_text_no_llm_fallback(self, text_cleaning_service_no_llm):
        raw_text = "This is a test sentence.\n\nAnother paragraph."
        cleaned_chunks = text_cleaning_service_no_llm.clean_text(raw_text)
        
        assert len(cleaned_chunks) == 1
        expected_cleaned_text = "This is a test sentence.\n\n... Another paragraph."
        assert cleaned_chunks[0].strip() == expected_cleaned_text.strip()

    def test_clean_text_empty_input(self, text_cleaning_service):
        raw_text = ""
        cleaned_chunks = text_cleaning_service.clean_text(raw_text)
        assert cleaned_chunks == [""]

    def test_clean_text_upstream_error_input(self, text_cleaning_service):
        raw_text = "Error: PDF conversion failed"
        cleaned_chunks = text_cleaning_service.clean_text(raw_text)
        assert cleaned_chunks == ["Error: PDF conversion failed"]

    @patch('builtins.open', new_callable=MagicMock)
    @patch('os.path.exists', return_value=True)
    @patch('time.sleep', MagicMock())
    def test_clean_text_with_llm_large_text_multiple_chunks(self, mock_exists, mock_open, mock_sleep, text_cleaning_service):
        # Create a text larger than max_chunk_size (100)
        raw_text = "Sentence one. " * 20 + "\n\n... ...\n\n" + "Sentence two. " * 20
        
        cleaned_chunks = text_cleaning_service.clean_text(raw_text)
        
        # Expect multiple calls to generate_content and multiple chunks
        assert text_cleaning_service.llm_provider.generate_content.call_count == 2
        assert len(cleaned_chunks) > 1
        assert all("..." in chunk for chunk in cleaned_chunks) # Check for TTS optimization

    @patch('builtins.open', new_callable=MagicMock)
    @patch('os.path.exists', return_value=True)
    def test_clean_text_llm_error_fallback(self, mock_exists, mock_open, text_cleaning_service):
        raw_text = "This text will cause an error."
        text_cleaning_service.llm_provider.generate_content = MagicMock(side_effect=Exception("LLM API error"))
        
        cleaned_chunks = text_cleaning_service.clean_text(raw_text)
        
        assert len(cleaned_chunks) == 1
        # Should fall back to basic TTS enhancement
        assert "... " in cleaned_chunks[0]
        assert "error" not in cleaned_chunks[0] # The mock LLM would have removed "error" if it succeeded

    def test_chunk_for_audio_small_text(self, text_cleaning_service):
        text = "This is a short text that should fit in one chunk."
        chunks = text_cleaning_service._chunk_for_audio(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_for_audio_large_text_major_sections(self, text_cleaning_service):
        text = "Section 1 content. " * 50 + "\n\n... ...\n\n" + "Section 2 content. " * 50
        chunks = text_cleaning_service._chunk_for_audio(text)
        assert len(chunks) == 2
        assert "Section 1" in chunks[0]
        assert "Section 2" in chunks[1]

    def test_chunk_for_audio_large_section_split(self, text_cleaning_service):
        # Create a section larger than target_size (80000) but smaller than max_chunk_size (100)
        # The _chunk_for_audio uses target_size=80000, while the service is initialized with max_chunk_size=100
        # This test needs to simulate the output of _clean_chunk_for_tts which is then passed to _chunk_for_audio
        long_section = "A very long sentence. " * 5000 # 100000 chars
        
        # Temporarily adjust max_chunk_size for this test to make _chunk_for_audio split it
        original_max_chunk_size = text_cleaning_service.max_chunk_size
        text_cleaning_service.max_chunk_size = 10000 # Make it split into ~10 chunks
        
        chunks = text_cleaning_service._chunk_for_audio(long_section)
        assert len(chunks) > 1
        assert all(len(chunk) <= 80000 for chunk in chunks) # _chunk_for_audio's target_size
        
        text_cleaning_service.max_chunk_size = original_max_chunk_size # Reset

    def test_smart_split_sentence_boundaries(self, text_cleaning_service):
        text = "First sentence. Second sentence! Third sentence?"
        chunks = text_cleaning_service._smart_split(text, max_size=20) # max_chunk_size is 100, but _smart_split uses its own max_size
        assert len(chunks) == 3
        assert chunks[0] == "First sentence."
        assert chunks[1] == "Second sentence!"
        assert chunks[2] == "Third sentence?"

    def test_smart_split_paragraph_boundaries(self, text_cleaning_service):
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = text_cleaning_service._smart_split(text, max_size=20) # max_chunk_size is 100, but _smart_split uses its own max_size
        assert len(chunks) == 3
        assert chunks[0] == "Paragraph one."
        assert chunks[1] == "Paragraph two."
        assert chunks[2] == "Paragraph three."

    def test_smart_split_very_large_chunk(self, text_cleaning_service):
        # A single "sentence" that is larger than max_size
        long_sentence = "A" * 150
        text = long_sentence
        chunks = text_cleaning_service._smart_split(text, max_size=100)
        assert len(chunks) == 2 # Should split into two chunks based on paragraph fallback
        assert chunks[0] == "A" * 100
        assert chunks[1] == "A" * 50

    def test_get_tts_optimized_prompt(self, text_cleaning_service):
        test_chunk = "Some raw text with (citation) and a bad_word."
        prompt = text_cleaning_service._get_tts_optimized_prompt(test_chunk)
        assert "Your primary goal is to clean the following text" in prompt
        assert "{text_chunk}" in prompt
        assert test_chunk in prompt
        assert "Add natural pause markers using ellipses" in prompt