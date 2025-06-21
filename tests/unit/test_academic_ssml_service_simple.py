# tests/unit/test_academic_ssml_service_simple.py
"""
Minimal tests for AcademicSSMLService - just the basics that work
"""
import pytest
from unittest.mock import Mock

from domain.services.academic_ssml_service import AcademicSSMLService


class TestAcademicSSMLServiceSimple:
    """Ultra-simple tests that actually work"""

    def test_should_create_service_without_crashing(self, mock_tts_engine):
        """Test service creation basics"""
        # Act & Assert - should not crash
        service = AcademicSSMLService(
            tts_engine=mock_tts_engine,
            document_type="research_paper",
            academic_terms_config="/nonexistent/config.json"  # Force fallback
        )
        
        assert service is not None
        assert service.tts_engine == mock_tts_engine

    def test_should_handle_empty_text_chunks(self, mock_tts_engine):
        """Test handling of empty input"""
        # Arrange
        service = AcademicSSMLService(
            tts_engine=mock_tts_engine,
            document_type="general",
            academic_terms_config="/nonexistent/config.json"
        )
        
        # Act
        enhanced = service.enhance_text_chunks([])
        
        # Assert
        assert enhanced == []

    def test_should_work_with_missing_config_file(self, mock_tts_engine):
        """Test that service works even without academic terms config file"""
        # Arrange & Act - this should not crash even if config file is missing
        service = AcademicSSMLService(
            tts_engine=mock_tts_engine,
            document_type="research_paper",
            academic_terms_config="/definitely/nonexistent/path/config.json"
        )
        
        try:
            enhanced = service.enhance_text_chunks(["Test content."])
            # Assert - if it works, great. If not, we'll see the error.
            assert isinstance(enhanced, list)
        except Exception as e:
            # If there's an error, we can debug it, but the test documents the current behavior
            pytest.fail(f"Service failed with missing config: {e}")