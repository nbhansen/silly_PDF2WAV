"""Tests for DocumentEngine's text-processing stage.

Focused on the guarantee that a document which yields no usable text fails
loudly rather than reporting success with no audio.
"""

from unittest.mock import Mock

from domain.document.document_engine import DocumentEngine
from domain.errors import ErrorCode, Result


def _engine() -> DocumentEngine:
    """DocumentEngine with stubbed collaborators - none are used by this stage."""
    return DocumentEngine(ocr_provider=Mock(), file_manager=Mock(), pdf_extractor=Mock())


def _pipeline(cleaned: str) -> Mock:
    """Text pipeline whose cleaning stage returns the given text."""
    pipeline = Mock()
    pipeline.clean_text.return_value = Result.success(cleaned)
    return pipeline


class TestEmptyTextIsRejected:
    """An image-only PDF extracts as whitespace and cleans down to nothing.

    Without an explicit guard, _split_for_tts("") returns [] and process_document
    only rejects None, so the run reports success having produced no audio at all.
    """

    def test_empty_cleaned_text_fails(self) -> None:
        """Cleaning down to an empty string must be a failure, not an empty chunk list."""
        result = _engine()._process_text_pipeline(["   "], _pipeline(""), llm_chunk_size=50000)

        assert result.is_failure
        assert result.error is not None
        assert result.error.code == ErrorCode.TEXT_EXTRACTION_FAILED

    def test_whitespace_only_cleaned_text_fails(self) -> None:
        """Whitespace is not usable text either."""
        result = _engine()._process_text_pipeline(["   "], _pipeline("  \n\t "), llm_chunk_size=50000)

        assert result.is_failure
        assert result.error is not None
        assert result.error.code == ErrorCode.TEXT_EXTRACTION_FAILED

    def test_usable_text_still_produces_chunks(self) -> None:
        """The guard must not reject documents that do have content."""
        result = _engine()._process_text_pipeline(
            ["raw"], _pipeline("This document has real content in it."), llm_chunk_size=50000
        )

        assert result.is_success
        assert result.value is not None
        assert len(result.value) >= 1
        assert "real content" in " ".join(result.value)
