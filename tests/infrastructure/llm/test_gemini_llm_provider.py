import pytest
from unittest.mock import MagicMock
from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider

@pytest.fixture
def mock_genai_configure(mocker):
    """Mock genai.configure."""
    return mocker.patch('google.generativeai.configure')

@pytest.fixture
def mock_generative_model(mocker):
    """Mock genai.GenerativeModel."""
    mock_model_class = mocker.patch('google.generativeai.GenerativeModel')
    mock_model_instance = MagicMock()
    mock_model_class.return_value = mock_model_instance
    return mock_model_instance

@pytest.fixture
def llm_provider_with_mock_model(mock_genai_configure, mock_generative_model):
    """Fixture for GeminiLLMProvider with a mocked model."""
    provider = GeminiLLMProvider(api_key="test_api_key")
    yield provider

@pytest.fixture
def llm_provider_no_api_key(mock_genai_configure, mock_generative_model):
    """Fixture for GeminiLLMProvider with no valid API key."""
    provider = GeminiLLMProvider(api_key="YOUR_GOOGLE_AI_API_KEY")
    yield provider

# Tests for _init_model (implicitly tested by provider fixture)
def test_init_model_success(mock_genai_configure, mock_generative_model):
    """Test successful model initialization."""
    provider = GeminiLLMProvider(api_key="valid_api_key")
    mock_genai_configure.assert_called_once_with(api_key="valid_api_key")
    mock_generative_model.assert_called_once_with('gemini-2.0-flash')
    assert provider.model is not None

def test_init_model_no_api_key(mock_genai_configure, mock_generative_model):
    """Test model initialization with no valid API key."""
    provider = GeminiLLMProvider(api_key="YOUR_GOOGLE_AI_API_KEY")
    mock_genai_configure.assert_not_called()
    mock_generative_model.assert_not_called()
    assert provider.model is None

def test_init_model_initialization_error(mock_genai_configure, mock_generative_model):
    """Test model initialization error handling."""
    mock_genai_configure.side_effect = Exception("API key error")
    provider = GeminiLLMProvider(api_key="invalid_api_key")
    mock_genai_configure.assert_called_once_with(api_key="invalid_api_key")
    mock_generative_model.assert_not_called()
    assert provider.model is None

# Tests for generate_content
def test_generate_content_success(llm_provider_with_mock_model, mock_generative_model):
    """Test successful content generation."""
    mock_response = MagicMock()
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content = MagicMock()
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = "Generated test content."
    mock_generative_model.generate_content.return_value = mock_response

    prompt = "Hello, LLM!"
    result = llm_provider_with_mock_model.generate_content(prompt)

    mock_generative_model.generate_content.assert_called_once_with(prompt)
    assert result == "Generated test content."

def test_generate_content_empty_response(llm_provider_with_mock_model, mock_generative_model):
    """Test content generation with an empty LLM response."""
    mock_response = MagicMock()
    mock_response.candidates = [] # No candidates
    mock_generative_model.generate_content.return_value = mock_response

    prompt = "Empty response test."
    result = llm_provider_with_mock_model.generate_content(prompt)

    mock_generative_model.generate_content.assert_called_once_with(prompt)
    assert result == "LLM content generation yielded no response."

def test_generate_content_api_error(llm_provider_with_mock_model, mock_generative_model):
    """Test content generation when an API error occurs."""
    mock_generative_model.generate_content.side_effect = Exception("API rate limit exceeded")

    prompt = "Error test."
    result = llm_provider_with_mock_model.generate_content(prompt)

    mock_generative_model.generate_content.assert_called_once_with(prompt)
    assert "Error during LLM content generation: API rate limit exceeded" in result

def test_generate_content_model_not_available(llm_provider_no_api_key):
    """Test content generation when the LLM model is not available."""
    prompt = "Model not available test."
    result = llm_provider_no_api_key.generate_content(prompt)

    assert result == "LLM content generation skipped due to missing API key or initialization error."