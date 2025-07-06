# tests/unit/test_text_pipeline_tdd.py
"""TDD tests for TextPipeline - comprehensive coverage following red-green-refactor cycle.
Tests pure text processing logic without external dependencies.
"""
from unittest.mock import Mock

from domain.errors import Result
from domain.text.text_pipeline import ITextPipeline, TextPipeline


class TestTextPipelineBasicFunctionality:
    """TDD tests for basic TextPipeline functionality."""

    def test_text_pipeline_creation_with_defaults(self):
        """Should create text pipeline with sensible defaults."""
        pipeline = TextPipeline()

        assert pipeline.llm_provider is None
        assert pipeline.enable_cleaning is True
        assert pipeline.enable_ssml is True

    def test_text_pipeline_creation_with_custom_settings(self):
        """Should create text pipeline with custom configuration."""
        mock_llm = Mock()
        pipeline = TextPipeline(llm_provider=mock_llm, enable_cleaning=False, enable_ssml=False)

        assert pipeline.llm_provider == mock_llm
        assert pipeline.enable_cleaning is False
        assert pipeline.enable_ssml is False

    def test_text_pipeline_implements_interface(self):
        """Should properly implement ITextPipeline interface."""
        pipeline = TextPipeline()
        assert isinstance(pipeline, ITextPipeline)

        # Check all interface methods are implemented
        assert hasattr(pipeline, "clean_text")
        assert hasattr(pipeline, "enhance_with_ssml")
        assert hasattr(pipeline, "split_into_sentences")
        assert hasattr(pipeline, "strip_ssml")


class TestTextCleaningTDD:
    """TDD tests for text cleaning functionality."""

    def test_basic_text_cleanup_removes_excessive_whitespace(self):
        """Should normalize whitespace in text."""
        pipeline = TextPipeline(enable_cleaning=False)  # Disable LLM cleaning

        messy_text = "This  is    text   with\n\n\nexcessive     whitespace."
        result = pipeline.clean_text(messy_text)

        assert result == "This is text with excessive whitespace."

    def test_basic_text_cleanup_removes_pdf_artifacts(self):
        """Should remove common PDF extraction artifacts."""
        pipeline = TextPipeline(enable_cleaning=False)

        text_with_artifacts = "Text with\fform feed and non-ASCII: café résumé"
        result = pipeline.clean_text(text_with_artifacts)

        # Should remove form feeds and non-ASCII
        assert "\f" not in result
        assert "café" not in result
        assert "résumé" not in result
        assert "Text with" in result

    def test_basic_text_cleanup_normalizes_punctuation(self):
        """Should normalize excessive punctuation."""
        pipeline = TextPipeline(enable_cleaning=False)

        text = "Excessive dots.... and dashes---- in text."
        result = pipeline.clean_text(text)

        assert "..." in result  # Normalized to three dots
        assert "...." not in result
        assert "--" in result  # Normalized to two dashes
        assert "----" not in result

    def test_llm_cleaning_with_successful_provider(self):
        """Should use LLM for cleaning when available and successful."""
        mock_llm = Mock()
        mock_llm.generate_content.return_value = Result.success("Cleaned text with proper formatting.")

        pipeline = TextPipeline(llm_provider=mock_llm, enable_cleaning=True)

        raw_text = "Raw   messy    text needs cleaning."
        result = pipeline.clean_text(raw_text)

        # Should call LLM provider
        mock_llm.generate_content.assert_called_once()

        # Should use LLM result
        assert "Cleaned text with proper formatting." in result

    def test_llm_cleaning_falls_back_on_failure(self):
        """Should fall back to basic cleaning when LLM fails."""
        mock_llm = Mock()
        mock_llm.generate_content.return_value = Result.failure(Mock())

        pipeline = TextPipeline(llm_provider=mock_llm, enable_cleaning=True)

        raw_text = "Raw   messy    text needs cleaning."
        result = pipeline.clean_text(raw_text)

        # Should still return cleaned text using basic method
        assert result == "Raw messy text needs cleaning."

    def test_llm_cleaning_falls_back_on_short_response(self):
        """Should fall back when LLM response is too short."""
        mock_llm = Mock()
        mock_llm.generate_content.return_value = Result.success("Short")  # Less than 30% of original

        pipeline = TextPipeline(llm_provider=mock_llm, enable_cleaning=True)

        raw_text = "This is a much longer text that should not result in a very short response."
        result = pipeline.clean_text(raw_text)

        # Should fall back to basic cleaning
        assert len(result) > len("Short")
        assert "This is a much longer text" in result

    def test_llm_cleaning_exception_handling(self):
        """Should handle LLM exceptions gracefully."""
        mock_llm = Mock()
        mock_llm.generate_content.side_effect = Exception("LLM service error")

        pipeline = TextPipeline(llm_provider=mock_llm, enable_cleaning=True)

        raw_text = "Text   with   spacing issues."
        result = pipeline.clean_text(raw_text)

        # Should still return cleaned text
        assert result == "Text with spacing issues."

    def test_cleaning_disabled_uses_basic_cleanup(self):
        """Should use basic cleanup when cleaning is disabled."""
        mock_llm = Mock()
        pipeline = TextPipeline(llm_provider=mock_llm, enable_cleaning=False)

        raw_text = "Text   with   spacing."
        result = pipeline.clean_text(raw_text)

        # Should not call LLM
        mock_llm.generate_content.assert_not_called()

        # Should use basic cleanup
        assert result == "Text with spacing."


class TestSSMLEnhancementTDD:
    """TDD tests for SSML enhancement functionality."""

    def test_ssml_enhancement_disabled_returns_original(self):
        """Should return original text when SSML is disabled."""
        pipeline = TextPipeline(enable_ssml=False)

        text = "This is plain text."
        result = pipeline.enhance_with_ssml(text)

        assert result == text

    def test_ssml_enhancement_adds_academic_pauses(self):
        """Should add pauses for academic document structure."""
        pipeline = TextPipeline(enable_ssml=True)

        text = "Abstract This is the abstract. Introduction This is the intro."
        result = pipeline.enhance_with_ssml(text)

        assert '<break time="1s"/>' in result
        assert "Abstract" in result
        assert "Introduction" in result

    def test_ssml_enhancement_adds_numbered_section_pauses(self):
        """Should add pauses after numbered sections."""
        pipeline = TextPipeline(enable_ssml=True)

        text = "1. First section content here. 2. Second section follows."
        result = pipeline.enhance_with_ssml(text)

        assert '<break time="0.5s"/>' in result

    def test_ssml_enhancement_emphasizes_technical_terms(self):
        """Should add emphasis to important technical terms."""
        pipeline = TextPipeline(enable_ssml=True)

        text = "The algorithm shows significant results. However, the method needs improvement."
        result = pipeline.enhance_with_ssml(text)

        assert '<emphasis level="moderate">algorithm</emphasis>' in result
        assert '<emphasis level="moderate">significant</emphasis>' in result
        assert '<emphasis level="moderate">However</emphasis>' in result

    def test_ssml_enhancement_emphasizes_quoted_text(self):
        """Should emphasize text in quotation marks."""
        pipeline = TextPipeline(enable_ssml=True)

        text = 'The author states "this is simple" in the conclusion.'
        result = pipeline.enhance_with_ssml(text)

        assert '<emphasis level="moderate">"this is simple"</emphasis>' in result

    def test_ssml_enhancement_adds_punctuation_breaks(self):
        """Should add appropriate breaks for punctuation."""
        pipeline = TextPipeline(enable_ssml=True)

        text = "First sentence, with comma; and semicolon. Final sentence!"
        result = pipeline.enhance_with_ssml(text)

        assert ',<break time="0.2s"/>' in result  # Comma break
        assert ';<break time="0.3s"/>' in result  # Semicolon break
        assert '.<break time="0.5s"/>' in result  # Period break
        assert '!<break time="0.5s"/>' in result  # Exclamation break

    def test_ssml_enhancement_handles_empty_text(self):
        """Should handle empty or whitespace-only text."""
        pipeline = TextPipeline(enable_ssml=True)

        assert pipeline.enhance_with_ssml("") == ""
        assert pipeline.enhance_with_ssml("   ") == "   "

    def test_ssml_enhancement_universal_academic_approach(self):
        """Should apply universal academic enhancements to all content."""
        pipeline = TextPipeline(enable_ssml=True)

        text = "Abstract This is general content."
        result = pipeline.enhance_with_ssml(text)

        # Should add academic enhancements universally
        assert "Abstract" in result
        # Should add academic pauses for all documents (universal approach)
        assert '<break time="1s"/>' in result


class TestSentenceSplittingTDD:
    """TDD tests for sentence splitting functionality."""

    def test_split_into_sentences_basic_splitting(self):
        """Should split text into individual sentences."""
        pipeline = TextPipeline()

        text = "First sentence. Second sentence! Third sentence?"
        result = pipeline.split_into_sentences(text)

        assert len(result) == 3
        assert "First sentence." in result
        assert "Second sentence!" in result
        assert "Third sentence?" in result

    def test_split_into_sentences_filters_short_sentences(self):
        """Should filter out very short sentences."""
        pipeline = TextPipeline()

        text = "Normal sentence here. Yes. Another normal sentence."
        result = pipeline.split_into_sentences(text)

        # Should filter out "Yes." as it's too short
        assert len(result) == 2
        assert "Normal sentence here." in result
        assert "Another normal sentence." in result
        assert "Yes." not in result

    def test_split_into_sentences_handles_abbreviations(self):
        """Should handle common abbreviations correctly."""
        pipeline = TextPipeline()

        text = "Dr. Smith conducted the study. Mr. Jones reviewed it."
        result = pipeline.split_into_sentences(text)

        # Should not split on "Dr." or "Mr."
        assert len(result) == 2
        assert "Dr. Smith conducted the study." in result
        assert "Mr. Jones reviewed it." in result

    def test_split_into_sentences_strips_ssml_first(self):
        """Should remove SSML tags before splitting."""
        pipeline = TextPipeline()

        text = 'First <emphasis>sentence</emphasis>. <break time="1s"/>Second sentence.'
        result = pipeline.split_into_sentences(text)

        # Should not contain SSML tags in results
        for sentence in result:
            assert "<emphasis>" not in sentence
            assert "<break" not in sentence

    def test_split_into_sentences_handles_empty_text(self):
        """Should handle empty or whitespace text."""
        pipeline = TextPipeline()

        assert pipeline.split_into_sentences("") == []
        assert pipeline.split_into_sentences("   ") == []

    def test_split_into_sentences_trims_whitespace(self):
        """Should trim whitespace from individual sentences."""
        pipeline = TextPipeline()

        text = "  First sentence.   Second sentence.  "
        result = pipeline.split_into_sentences(text)

        for sentence in result:
            assert sentence == sentence.strip()

    def test_split_into_sentences_handles_numbers_and_decimals(self):
        """Should not split on decimal numbers."""
        pipeline = TextPipeline()

        text = "The value is 3.14159 in this calculation. Next sentence follows."
        result = pipeline.split_into_sentences(text)

        assert len(result) == 2
        assert "3.14159" in result[0]


class TestSSMLStrippingTDD:
    """TDD tests for SSML tag removal functionality."""

    def test_strip_ssml_removes_all_tags(self):
        """Should remove all SSML tags from text."""
        pipeline = TextPipeline()

        text = 'Text with <emphasis level="moderate">emphasis</emphasis> and <break time="1s"/> breaks.'
        result = pipeline.strip_ssml(text)

        assert result == "Text with emphasis and breaks."
        assert "<" not in result
        assert ">" not in result

    def test_strip_ssml_removes_complex_tags(self):
        """Should remove complex SSML tags with attributes."""
        pipeline = TextPipeline()

        text = '<speak><prosody rate="slow" pitch="low">Slow speech</prosody><mark name="bookmark"/>End</speak>'
        result = pipeline.strip_ssml(text)

        assert result == "Slow speech End"

    def test_strip_ssml_normalizes_whitespace(self):
        """Should normalize whitespace after tag removal."""
        pipeline = TextPipeline()

        text = 'Text   <break time="1s"/>   with    excessive    spacing.'
        result = pipeline.strip_ssml(text)

        assert result == "Text with excessive spacing."

    def test_strip_ssml_handles_nested_tags(self):
        """Should handle nested SSML tags correctly."""
        pipeline = TextPipeline()

        text = '<emphasis><prosody rate="fast">Nested content</prosody></emphasis>'
        result = pipeline.strip_ssml(text)

        assert result == "Nested content"

    def test_strip_ssml_handles_self_closing_tags(self):
        """Should handle self-closing SSML tags."""
        pipeline = TextPipeline()

        text = 'Before<break time="1s"/>after the break.'
        result = pipeline.strip_ssml(text)

        assert result == "Before after the break."

    def test_strip_ssml_handles_malformed_tags(self):
        """Should handle malformed or incomplete tags gracefully."""
        pipeline = TextPipeline()

        text = "Text with <incomplete and <break> normal content."
        result = pipeline.strip_ssml(text)

        # Should still process and clean up reasonably
        assert "Text with" in result
        assert "normal content" in result

    def test_strip_ssml_handles_empty_text(self):
        """Should handle empty text gracefully."""
        pipeline = TextPipeline()

        assert pipeline.strip_ssml("") == ""
        assert pipeline.strip_ssml("   ") == ""

    def test_strip_ssml_preserves_non_ssml_content(self):
        """Should preserve all non-SSML content exactly."""
        pipeline = TextPipeline()

        text = 'Regular text with "quotes" and numbers 123.45 preserved.'
        result = pipeline.strip_ssml(text)

        assert result == text


class TestTextPipelineIntegrationTDD:
    """TDD tests for TextPipeline component integration."""

    def test_full_pipeline_processing_workflow(self):
        """Should handle complete text processing workflow."""
        mock_llm = Mock()
        mock_llm.generate_content.return_value = Result.success(
            "Cleaned academic text about the algorithm methodology."
        )

        pipeline = TextPipeline(llm_provider=mock_llm, enable_cleaning=True, enable_ssml=True)

        raw_text = "Raw   academic   text about algorithms."

        # Clean text
        cleaned = pipeline.clean_text(raw_text)
        assert "algorithm" in cleaned

        # Enhance with SSML
        enhanced = pipeline.enhance_with_ssml(cleaned)
        assert '<emphasis level="moderate">algorithm</emphasis>' in enhanced

        # Split into sentences
        sentences = pipeline.split_into_sentences(enhanced)
        assert len(sentences) >= 1

        # Strip SSML
        stripped = pipeline.strip_ssml(enhanced)
        assert "<emphasis>" not in stripped
        assert "algorithm" in stripped

    def test_pipeline_consistency_across_operations(self):
        """Should maintain text consistency through all operations."""
        pipeline = TextPipeline(enable_cleaning=False, enable_ssml=True)

        original_text = "Test sentence one. Test sentence two."

        # Process through pipeline
        cleaned = pipeline.clean_text(original_text)
        enhanced = pipeline.enhance_with_ssml(cleaned)
        sentences = pipeline.split_into_sentences(enhanced)

        # Recombine and strip
        recombined = " ".join(sentences)
        final = pipeline.strip_ssml(recombined)

        # Should preserve core content
        assert "Test sentence one" in final
        assert "Test sentence two" in final

    def test_pipeline_handles_large_text_efficiently(self):
        """Should handle larger text blocks without issues."""
        pipeline = TextPipeline(enable_cleaning=False, enable_ssml=True)

        # Create larger text block
        large_text = " ".join([f"Sentence number {i} with content." for i in range(100)])

        # Should process without errors
        result = pipeline.enhance_with_ssml(large_text)
        assert len(result) > len(large_text)  # Should have added SSML

        sentences = pipeline.split_into_sentences(result)
        assert len(sentences) == 100  # Should split correctly

    def test_pipeline_with_all_features_disabled(self):
        """Should work correctly with all enhancement features disabled."""
        pipeline = TextPipeline(enable_cleaning=False, enable_ssml=False)

        text = "Simple   text   with   spacing."

        cleaned = pipeline.clean_text(text)
        enhanced = pipeline.enhance_with_ssml(cleaned)

        # Should still do basic cleanup but no SSML
        assert enhanced == "Simple text with spacing."

    def test_pipeline_error_resilience(self):
        """Should be resilient to various error conditions."""
        # Test with None values
        pipeline = TextPipeline()

        # Should handle None gracefully (this might need implementation)
        # For now, testing with empty strings which should work
        assert pipeline.clean_text("") == ""
        assert pipeline.enhance_with_ssml("") == ""
        assert pipeline.split_into_sentences("") == []
        assert pipeline.strip_ssml("") == ""


class TestTextPipelinePromptGenerationTDD:
    """TDD tests for LLM prompt generation logic."""

    def test_cleaning_prompt_generation_uses_universal_approach(self):
        """Should use universal academic text processing approach in prompts."""
        pipeline = TextPipeline()

        text = "Sample text for cleaning."
        prompt = pipeline._generate_cleaning_prompt(text)

        assert "universal academic text processing approach" in prompt
        assert "Sample text for cleaning." in prompt

    def test_cleaning_prompt_generation_limits_text_size(self):
        """Should limit text size in prompts to prevent token overflow."""
        pipeline = TextPipeline()

        # Create very long text
        long_text = "Sample text. " * 1000  # Much longer than 5000 chars
        prompt = pipeline._generate_cleaning_prompt(long_text)

        # Should be truncated
        assert len(prompt) < len(long_text) + 200  # Account for prompt template

    def test_cleaning_prompt_generation_includes_instructions(self):
        """Should include proper cleaning instructions."""
        pipeline = TextPipeline()

        text = "Sample text"
        prompt = pipeline._generate_cleaning_prompt(text)

        assert "Clean the following text" in prompt
        assert "Remove headers" in prompt
        assert "Add appropriate pauses" in prompt


class TestTextPipelineEdgeCasesTDD:
    """TDD tests for edge cases and error conditions."""

    def test_handles_unicode_content_correctly(self):
        """Should handle unicode content appropriately."""
        pipeline = TextPipeline(enable_cleaning=False)

        # Unicode text should be handled by basic cleanup (removed in current implementation)
        unicode_text = "English text with unicode: café résumé naïve"
        result = pipeline.clean_text(unicode_text)

        # Current implementation removes non-ASCII
        assert "English text with unicode:" in result
        assert "café" not in result

    def test_handles_very_long_sentences(self):
        """Should handle extremely long sentences."""
        pipeline = TextPipeline()

        # Create very long sentence
        long_sentence = "This is a very long sentence " * 100 + "."
        result = pipeline.split_into_sentences(long_sentence)

        # Should still process correctly
        assert len(result) >= 1
        assert len(result[0]) > 1000

    def test_handles_text_with_no_punctuation(self):
        """Should handle text without sentence-ending punctuation."""
        pipeline = TextPipeline()

        text = "Text without any punctuation marks just words"
        result = pipeline.split_into_sentences(text)

        # Should return the whole text as one sentence if over minimum length
        assert len(result) == 1
        assert result[0] == text

    def test_handles_text_with_only_punctuation(self):
        """Should handle text with only punctuation marks."""
        pipeline = TextPipeline()

        text = "!!! ??? ."  # Shorter punctuation sequence
        result = pipeline.split_into_sentences(text)

        # Should filter out as too short (less than 10 chars)
        assert len(result) == 0

    def test_handles_mixed_case_section_headers(self):
        """Should handle section headers in various cases."""
        pipeline = TextPipeline(enable_ssml=True)

        text = "ABSTRACT This is content. abstract This too. Abstract: Also this."
        result = pipeline.enhance_with_ssml(text)

        # Should handle different cases of section headers
        assert '<break time="1s"/>' in result
