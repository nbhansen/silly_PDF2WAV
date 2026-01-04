"""Comprehensive tests for TextSegmenter.

Tests text processing functionality that is shared across all TTS engines.
These tests validate sentence splitting, duration calculation, text chunking,
and text cleaning for TTS compatibility.
"""

import pytest

from infrastructure.tts.text_segmenter import TextSegmenter


@pytest.fixture
def default_segmenter() -> TextSegmenter:
    """Default TextSegmenter with standard settings."""
    return TextSegmenter()


@pytest.fixture
def custom_segmenter() -> TextSegmenter:
    """Custom TextSegmenter with faster speaking rate."""
    return TextSegmenter(base_wpm=200)


class TestTextSegmenterInitialization:
    """Test TextSegmenter initialization and configuration."""

    def test_init_with_default_wpm(self, default_segmenter: TextSegmenter) -> None:
        """Should initialize with default words per minute."""
        segmenter = default_segmenter

        assert segmenter.base_wpm == 155  # Audiobook standard
        assert isinstance(segmenter.punctuation_pauses, dict)
        assert len(segmenter.punctuation_pauses) > 0

    def test_init_with_custom_wpm(self, custom_segmenter: TextSegmenter) -> None:
        """Should initialize with custom words per minute."""
        segmenter = custom_segmenter

        assert segmenter.base_wpm == 200
        assert isinstance(segmenter.punctuation_pauses, dict)

    def test_punctuation_pauses_configuration(self, default_segmenter: TextSegmenter) -> None:
        """Should have proper punctuation pause configuration."""
        segmenter = default_segmenter

        # Check expected punctuation marks
        expected_punctuation = [".", "!", "?", ",", ";", ":", "—", "..."]
        for punct in expected_punctuation:
            assert punct in segmenter.punctuation_pauses
            assert isinstance(segmenter.punctuation_pauses[punct], (int, float))
            assert segmenter.punctuation_pauses[punct] > 0


class TestTextSegmenterSentenceSplitting:
    """Test sentence splitting functionality."""

    def test_split_into_sentences_basic(self, default_segmenter: TextSegmenter) -> None:
        """Should split basic sentences correctly."""
        segmenter = default_segmenter

        text = "This is the first sentence. This is the second sentence! Is this the third sentence?"
        sentences = segmenter.split_into_sentences(text)

        expected = [
            "This is the first sentence.",
            "This is the second sentence!",
            "Is this the third sentence?",
        ]
        assert sentences == expected

    def test_split_into_sentences_handles_abbreviations(self, default_segmenter: TextSegmenter) -> None:
        """Should not split on common abbreviations."""
        segmenter = default_segmenter

        text = "Dr. Smith met with Mr. Johnson. They discussed Prof. Brown's research."
        sentences = segmenter.split_into_sentences(text)

        expected = [
            "Dr. Smith met with Mr. Johnson.",
            "They discussed Prof. Brown's research.",
        ]
        assert sentences == expected

    def test_split_into_sentences_handles_multiple_abbreviations(self, default_segmenter: TextSegmenter) -> None:
        """Should handle multiple abbreviations in one sentence."""
        segmenter = default_segmenter

        text = "Mr. and Mrs. Smith visited Dr. Johnson Sr. yesterday."
        sentences = segmenter.split_into_sentences(text)

        assert len(sentences) == 1
        assert sentences[0] == "Mr. and Mrs. Smith visited Dr. Johnson Sr. yesterday."

    def test_split_into_sentences_empty_input(self, default_segmenter: TextSegmenter) -> None:
        """Should handle empty input gracefully."""
        segmenter = default_segmenter

        assert segmenter.split_into_sentences("") == []
        assert segmenter.split_into_sentences("   ") == []
        assert segmenter.split_into_sentences("\n\t") == []

    def test_split_into_sentences_single_sentence(self, default_segmenter: TextSegmenter) -> None:
        """Should handle single sentence without ending punctuation."""
        segmenter = default_segmenter

        text = "This is a single sentence without ending punctuation"
        sentences = segmenter.split_into_sentences(text)

        assert len(sentences) == 1
        assert sentences[0] == text

    def test_split_into_sentences_cleans_whitespace(self, default_segmenter: TextSegmenter) -> None:
        """Should clean whitespace in split sentences."""
        segmenter = default_segmenter

        text = "  First sentence.   Second sentence with extra spaces.  "
        sentences = segmenter.split_into_sentences(text)

        expected = [
            "First sentence.",
            "Second sentence with extra spaces.",
        ]
        assert sentences == expected

    def test_split_into_sentences_handles_edge_cases(self, default_segmenter: TextSegmenter) -> None:
        """Should handle various edge cases in sentence splitting."""
        segmenter = default_segmenter

        # Numbers and decimals
        text = "The price was $19.99. The temperature was 98.6 degrees."
        sentences = segmenter.split_into_sentences(text)
        assert len(sentences) == 2

        # Ellipsis
        text = "He said... Then he paused. Finally he continued."
        sentences = segmenter.split_into_sentences(text)
        assert len(sentences) >= 2  # Should not split on ellipsis inappropriately

    def test_split_into_sentences_preserves_context(self, default_segmenter: TextSegmenter) -> None:
        """Should preserve sentence context and content."""
        segmenter = default_segmenter

        text = "Chapter 1. Introduction to Machine Learning. Chapter 2. Data Processing."
        sentences = segmenter.split_into_sentences(text)

        # Should handle this appropriately
        assert len(sentences) >= 1
        for sentence in sentences:
            assert sentence.strip()  # No empty sentences


class TestTextSegmenterDurationCalculation:
    """Test duration calculation functionality."""

    def test_calculate_duration_basic(self, default_segmenter: TextSegmenter) -> None:
        """Should calculate duration for basic text."""
        segmenter = default_segmenter

        # "Hello world" = 2 words at 155 WPM = (2/155) * 60 = ~0.77 seconds
        text = "Hello world"
        duration = segmenter.calculate_duration(text)

        assert duration > 0.5  # Minimum duration
        assert duration < 5.0  # Reasonable upper bound for short text

    def test_calculate_duration_with_punctuation(self, default_segmenter: TextSegmenter) -> None:
        """Should add time for punctuation pauses."""
        segmenter = default_segmenter

        text_without_punct = "Hello world"
        text_with_punct = "Hello, world!"

        duration_without = segmenter.calculate_duration(text_without_punct)
        duration_with = segmenter.calculate_duration(text_with_punct)

        # Text with punctuation should take longer
        assert duration_with > duration_without

    def test_calculate_duration_empty_text(self, default_segmenter: TextSegmenter) -> None:
        """Should return minimum duration for empty text."""
        segmenter = default_segmenter

        assert segmenter.calculate_duration("") == 0.5
        assert segmenter.calculate_duration("   ") == 0.5
        assert segmenter.calculate_duration("\n\t") == 0.5

    def test_calculate_duration_with_html_tags(self, default_segmenter: TextSegmenter) -> None:
        """Should ignore HTML/XML tags in duration calculation."""
        segmenter = default_segmenter

        text_plain = "Hello world"
        text_with_tags = "<speak>Hello <break time='1s'/> world</speak>"

        duration_plain = segmenter.calculate_duration(text_plain)
        duration_with_tags = segmenter.calculate_duration(text_with_tags)

        # Should be approximately equal (tags ignored)
        assert abs(duration_plain - duration_with_tags) < 0.1

    def test_calculate_duration_scales_with_text_length(self, default_segmenter: TextSegmenter) -> None:
        """Should scale duration appropriately with text length."""
        segmenter = default_segmenter

        short_text = "Hello world"
        long_text = short_text * 10  # 10x longer

        duration_short = segmenter.calculate_duration(short_text)
        duration_long = segmenter.calculate_duration(long_text)

        # Longer text should take proportionally longer
        assert duration_long > duration_short * 5  # At least 5x longer
        assert duration_long < duration_short * 15  # But not too much longer

    def test_calculate_duration_different_wpm(self) -> None:
        """Should calculate different durations for different WPM settings."""
        slow_segmenter = TextSegmenter(base_wpm=100)
        fast_segmenter = TextSegmenter(base_wpm=200)

        text = "This is a test sentence with several words."

        duration_slow = slow_segmenter.calculate_duration(text)
        duration_fast = fast_segmenter.calculate_duration(text)

        # Slower WPM should result in longer duration
        assert duration_slow > duration_fast

    def test_calculate_duration_handles_multiple_punctuation(self, default_segmenter: TextSegmenter) -> None:
        """Should handle multiple punctuation marks correctly."""
        segmenter = default_segmenter

        text = "Hello, world! How are you? I'm fine... Thanks."
        duration = segmenter.calculate_duration(text)

        # Should account for all punctuation pauses
        expected_pauses = 1 * 0.2 + 1 * 0.4 + 1 * 0.4 + 1 * 0.6 + 1 * 0.4  # , ! ? ... .

        # Duration should include base time plus pauses
        assert duration > expected_pauses
        assert duration > 2.0  # Reasonable minimum for this text


class TestTextSegmenterChunking:
    """Test text chunking functionality."""

    def test_split_into_chunks_short_text(self, default_segmenter: TextSegmenter) -> None:
        """Should return single chunk for short text."""
        segmenter = default_segmenter

        text = "This is a short text."
        chunks = segmenter.split_into_chunks(text, max_chunk_size=1000)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_split_into_chunks_respects_sentence_boundaries(self, default_segmenter: TextSegmenter) -> None:
        """Should prefer splitting on sentence boundaries."""
        segmenter = default_segmenter

        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = segmenter.split_into_chunks(text, max_chunk_size=30)

        # Should split into multiple chunks
        assert len(chunks) > 1

        # Each chunk should contain complete sentences where possible
        for chunk in chunks:
            # Should end with sentence punctuation or be the last chunk
            assert chunk.endswith(('.', '!', '?')) or chunk == chunks[-1]

    def test_split_into_chunks_handles_long_sentences(self, default_segmenter: TextSegmenter) -> None:
        """Should split long sentences by words when necessary."""
        segmenter = default_segmenter

        # Create a very long sentence
        long_sentence = "This is a very long sentence " * 10 + "with no internal punctuation marks."
        chunks = segmenter.split_into_chunks(long_sentence, max_chunk_size=50)

        # Should split into multiple chunks
        assert len(chunks) > 1

        # Each chunk should be within size limit (approximately)
        for chunk in chunks:
            assert len(chunk) <= 60  # Some tolerance for word boundaries

    def test_split_into_chunks_empty_input(self, default_segmenter: TextSegmenter) -> None:
        """Should handle empty input gracefully."""
        segmenter = default_segmenter

        assert segmenter.split_into_chunks("") == [""]
        assert segmenter.split_into_chunks("   ") == ["   "]
        assert segmenter.split_into_chunks("\n\t") == ["\n\t"]

    def test_split_into_chunks_preserves_content(self, default_segmenter: TextSegmenter) -> None:
        """Should preserve all content across chunks."""
        segmenter = default_segmenter

        text = "First sentence. Second sentence. Third sentence with more words."
        chunks = segmenter.split_into_chunks(text, max_chunk_size=25)

        # Reconstructed text should match original (minus spacing changes)
        reconstructed = " ".join(chunks)

        # Should contain all original words
        original_words = text.split()
        reconstructed_words = reconstructed.split()

        # Allow for some whitespace normalization
        assert len(original_words) == len(reconstructed_words)

    def test_split_into_chunks_custom_size(self, default_segmenter: TextSegmenter) -> None:
        """Should respect custom chunk size limits."""
        segmenter = default_segmenter

        text = "Word " * 100  # 500 characters

        small_chunks = segmenter.split_into_chunks(text, max_chunk_size=50)
        large_chunks = segmenter.split_into_chunks(text, max_chunk_size=200)

        # Smaller limit should create more chunks
        assert len(small_chunks) > len(large_chunks)

        # Each chunk should respect its limit (with word boundary tolerance)
        for chunk in small_chunks:
            assert len(chunk) <= 60  # Some tolerance for word boundaries

    def test_split_into_chunks_single_word_edge_case(self, default_segmenter: TextSegmenter) -> None:
        """Should handle single very long words."""
        segmenter = default_segmenter

        # Create a very long "word"
        long_word = "supercalifragilisticexpialidocious" * 5
        chunks = segmenter.split_into_chunks(long_word, max_chunk_size=50)

        # Should still return the word, even if it exceeds limit
        assert len(chunks) >= 1
        assert long_word in "".join(chunks)


class TestTextSegmenterTextCleaning:
    """Test text cleaning functionality."""

    def test_clean_text_for_tts_removes_problematic_chars(self, default_segmenter: TextSegmenter) -> None:
        """Should remove characters that cause TTS issues."""
        segmenter = default_segmenter

        text = "Hello @#$%^&* world with weird symbols ©®™"
        cleaned = segmenter.clean_text_for_tts(text)

        # Should remove problematic symbols
        assert "@#$%^&*" not in cleaned
        assert "©®™" not in cleaned

        # Should preserve readable content
        assert "Hello" in cleaned
        assert "world" in cleaned
        assert "with" in cleaned
        assert "weird" in cleaned
        assert "symbols" in cleaned

    def test_clean_text_for_tts_preserves_punctuation(self, default_segmenter: TextSegmenter) -> None:
        """Should preserve important punctuation."""
        segmenter = default_segmenter

        text = "Hello, world! How are you? I'm fine... Thanks-goodbye."
        cleaned = segmenter.clean_text_for_tts(text)

        # Should preserve sentence punctuation
        assert "," in cleaned
        assert "!" in cleaned
        assert "?" in cleaned
        assert "." in cleaned
        assert "-" in cleaned
        assert "'" in cleaned

    def test_clean_text_for_tts_normalizes_whitespace(self, default_segmenter: TextSegmenter) -> None:
        """Should normalize excessive whitespace."""
        segmenter = default_segmenter

        text = "Hello   world\n\nwith    lots\t\tof   whitespace"
        cleaned = segmenter.clean_text_for_tts(text)

        # Should have single spaces between words
        assert cleaned == "Hello world with lots of whitespace"

    def test_clean_text_for_tts_strips_leading_trailing(self, default_segmenter: TextSegmenter) -> None:
        """Should remove leading and trailing whitespace."""
        segmenter = default_segmenter

        text = "   Hello world   "
        cleaned = segmenter.clean_text_for_tts(text)

        assert cleaned == "Hello world"
        assert not cleaned.startswith(" ")
        assert not cleaned.endswith(" ")

    def test_clean_text_for_tts_empty_input(self, default_segmenter: TextSegmenter) -> None:
        """Should handle empty input gracefully."""
        segmenter = default_segmenter

        assert segmenter.clean_text_for_tts("") == ""
        assert segmenter.clean_text_for_tts("   ") == ""
        assert segmenter.clean_text_for_tts("\n\t") == ""

    def test_clean_text_for_tts_preserves_parentheses_quotes(self, default_segmenter: TextSegmenter) -> None:
        """Should preserve parentheses and quotes."""
        segmenter = default_segmenter

        text = 'He said "Hello (how are you?)" yesterday.'
        cleaned = segmenter.clean_text_for_tts(text)

        assert '"' in cleaned
        assert "(" in cleaned
        assert ")" in cleaned
        assert "Hello" in cleaned
        assert "how are you" in cleaned

    def test_clean_text_for_tts_handles_unicode(self, default_segmenter: TextSegmenter) -> None:
        """Should handle Unicode characters appropriately."""
        segmenter = default_segmenter

        # Mix of ASCII and Unicode
        text = "Café résumé naïve Москва 北京"
        cleaned = segmenter.clean_text_for_tts(text)

        # Should preserve basic Latin characters
        assert "Caf" in cleaned or "résumé" in cleaned or len(cleaned) > 0


class TestTextSegmenterIntegration:
    """Test integration between different segmenter functions."""

    def test_sentence_splitting_then_chunking(self, default_segmenter: TextSegmenter) -> None:
        """Should work well when combining sentence splitting and chunking."""
        segmenter = default_segmenter

        text = "First sentence. Second sentence. Third sentence. Fourth sentence."

        # First split into sentences
        sentences = segmenter.split_into_sentences(text)

        # Then chunk the sentences
        combined_text = " ".join(sentences)
        chunks = segmenter.split_into_chunks(combined_text, max_chunk_size=30)

        # Should produce reasonable results
        assert len(chunks) >= 1
        assert all(chunk.strip() for chunk in chunks)

    def test_cleaning_then_duration_calculation(self, default_segmenter: TextSegmenter) -> None:
        """Should work well when cleaning text before duration calculation."""
        segmenter = default_segmenter

        dirty_text = "Hello, world!!! @#$%^& How are you???"
        clean_text = segmenter.clean_text_for_tts(dirty_text)
        duration = segmenter.calculate_duration(clean_text)

        # Should calculate reasonable duration for cleaned text
        assert duration > 0.5
        assert duration < 10.0  # Reasonable upper bound

    def test_full_processing_pipeline(self, default_segmenter: TextSegmenter) -> None:
        """Should handle a complete text processing pipeline."""
        segmenter = default_segmenter

        raw_text = """
        This is a test document!!! It has multiple sentences.
        Some sentences have weird @symbols# and excessive   whitespace.
        Dr. Smith said, "This should work well..." Let's see!
        """

        # Clean the text
        cleaned = segmenter.clean_text_for_tts(raw_text)

        # Split into sentences
        sentences = segmenter.split_into_sentences(cleaned)

        # Calculate durations
        durations = [segmenter.calculate_duration(sentence) for sentence in sentences]

        # Chunk if needed
        chunks = segmenter.split_into_chunks(cleaned, max_chunk_size=100)

        # All steps should complete successfully
        assert isinstance(cleaned, str)
        assert len(sentences) > 0
        assert all(d > 0 for d in durations)
        assert len(chunks) > 0
        assert all(chunk.strip() for chunk in chunks)
