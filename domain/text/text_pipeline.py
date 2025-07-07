# domain/text/text_pipeline.py - Unified Text Processing Pipeline
"""Consolidated text processing pipeline that unifies text cleaning and SSML enhancement.
Replaces: TextCleaningService, AcademicSSMLService (as separate concerns).
"""

from abc import ABC, abstractmethod
import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..interfaces import ILLMProvider


class ITextPipeline(ABC):
    """Unified interface for text processing operations."""

    @abstractmethod
    def clean_text(self, raw_text: str) -> str:
        """Clean and prepare text for TTS."""

    @abstractmethod
    async def clean_text_async(self, raw_text: str) -> str:
        """Clean and prepare text for TTS asynchronously with rate limiting."""

    @abstractmethod
    def enhance_with_natural_formatting(self, text: str) -> str:
        """Add natural formatting enhancements to text."""

    @abstractmethod
    def split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences for processing."""


class TextPipeline(ITextPipeline):
    """Unified text processing pipeline with high cohesion.
    Handles cleaning, SSML enhancement, and sentence splitting in one place.
    """

    def __init__(
        self,
        llm_provider: Optional["ILLMProvider"] = None,
        enable_cleaning: bool = True,
        enable_natural_formatting: bool = True,
    ):
        self.llm_provider = llm_provider
        self.enable_cleaning = enable_cleaning
        self.enable_natural_formatting = enable_natural_formatting

    def clean_text(self, raw_text: str) -> str:
        """Clean and prepare text for TTS processing."""
        print(f"🔬 TextPipeline.clean_text(): Input {len(raw_text)} chars")

        if not self.enable_cleaning or not self.llm_provider:
            llm_available = self.llm_provider is not None
            print(f"   → Using basic cleanup (cleaning={self.enable_cleaning}, " f"llm_provider={llm_available})")
            result = self._basic_text_cleanup(raw_text)
            print(f"   → Basic cleanup result: {len(result)} chars")
            return result

        try:
            # Use LLM for advanced cleaning
            print(f"   → Using LLM cleaning (provider: {type(self.llm_provider).__name__})")
            cleaning_prompt = self._generate_cleaning_prompt(raw_text)
            print(f"   → Generated cleaning prompt ({len(cleaning_prompt)} chars)")

            print("   → Calling LLM API...")
            result = self.llm_provider.generate_content(cleaning_prompt)

            if result.is_success:
                cleaned = result.value
                print(f"   → LLM success: {len(cleaned)} chars returned")
                # Basic validation of LLM output
                if (
                    cleaned and len(cleaned) > len(raw_text) * 0.05
                ):  # At least 5% of original length (cleaning should reduce size)
                    print("   → LLM output valid, applying basic cleanup")
                    final_result = self._basic_text_cleanup(cleaned)
                    print(f"   → Final result: {len(final_result)} chars")
                    return final_result
                else:
                    print(f"   → LLM output too short ({len(cleaned) if cleaned else 0} chars), trying smaller chunks")
            else:
                print(f"   → LLM failed: {result.error}")

            # If large chunk failed, try processing in smaller pieces
            if len(raw_text) > 15000:
                print("   → Attempting retry with smaller chunks (15K chars each)")
                chunk_size = 15000
                cleaned_parts = []

                for i in range(0, len(raw_text), chunk_size):
                    chunk = raw_text[i : i + chunk_size]
                    print(f"     → Processing sub-chunk {i//chunk_size + 1} ({len(chunk)} chars)")

                    sub_prompt = self._generate_cleaning_prompt(chunk)
                    sub_result = self.llm_provider.generate_content(sub_prompt)

                    if sub_result.is_success and sub_result.value:
                        cleaned_parts.append(sub_result.value)
                        print(f"     → Sub-chunk success: {len(sub_result.value)} chars")
                    else:
                        # Use basic cleanup for failed sub-chunks
                        cleaned_parts.append(self._basic_text_cleanup(chunk))
                        print("     → Sub-chunk failed, using basic cleanup")

                if cleaned_parts:
                    combined_result = " ".join(cleaned_parts)
                    print(f"   → Combined sub-chunks: {len(combined_result)} chars")
                    return self._basic_text_cleanup(combined_result)

            # Final fallback to basic cleaning if all else fails
            print("   → All attempts failed, using basic cleanup")
            fallback_result = self._basic_text_cleanup(raw_text)
            print(f"   → Fallback result: {len(fallback_result)} chars")
            return fallback_result

        except Exception as e:
            print(f"   → TextPipeline: LLM cleaning exception: {e}")
            fallback_result = self._basic_text_cleanup(raw_text)
            print(f"   → Exception fallback result: {len(fallback_result)} chars")
            return fallback_result

    async def clean_text_async(self, raw_text: str) -> str:
        """Clean and prepare text for TTS processing asynchronously."""
        if not self.enable_cleaning or not self.llm_provider:
            return self._basic_text_cleanup(raw_text)

        # Check if async method is available
        if not hasattr(self.llm_provider, "generate_content_async"):
            print("TextPipeline: Async cleaning not available, using sync method")
            return self.clean_text(raw_text)

        try:
            # Use async LLM for advanced cleaning with rate limiting
            cleaning_prompt = self._generate_cleaning_prompt(raw_text)
            result = await self.llm_provider.generate_content_async(cleaning_prompt)

            if result.is_success:
                cleaned = result.value
                # Basic validation of LLM output
                if cleaned and len(cleaned) > len(raw_text) * 0.3:  # At least 30% of original length
                    return self._basic_text_cleanup(cleaned)

            # Fallback to basic cleaning if LLM fails
            return self._basic_text_cleanup(raw_text)

        except Exception as e:
            print(f"TextPipeline: Async LLM cleaning failed: {e}")
            return self._basic_text_cleanup(raw_text)

    def enhance_with_natural_formatting(self, text: str) -> str:
        """Add natural formatting for better speech synthesis (Piper-optimized)."""
        if not self.enable_natural_formatting:
            return text

        return self._enhance_with_natural_formatting(text)

    def split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences for individual processing."""
        # Use text directly since we only generate natural formatting (no markup)
        clean_text = text

        # Handle abbreviations better - don't split on Dr., Mr., etc.
        # Basic sentence splitting with common edge cases
        sentences = re.split(r"(?<!\bDr\.)(?<!\bMr\.)(?<!\bMs\.)(?<!\bProf\.)(?<=[.!?])\s+(?=[A-Z])", clean_text)

        # Filter out very short sentences and clean up (immutable)
        return [sentence.strip() for sentence in sentences if sentence.strip() and len(sentence.strip()) > 10]

    def _basic_text_cleanup(self, text: str) -> str:
        """Basic text cleanup without LLM."""
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove common PDF artifacts
        text = re.sub(r"\f", " ", text)  # Form feed
        text = re.sub(r"[^\x00-\x7F]+", " ", text)  # Non-ASCII characters

        # Clean up punctuation
        text = re.sub(r"\.{3,}", "...", text)  # Multiple dots
        text = re.sub(r"-{2,}", "--", text)  # Multiple dashes

        return text.strip()

    def _generate_cleaning_prompt(self, text: str) -> str:
        """Generate LLM prompt for text cleaning (optimized for natural speech)."""
        pause_instruction = """Use natural punctuation for better speech rhythm:
- Use "..." for medium pauses (between paragraphs or sections)
- Use "...." or "....." for longer pauses (after major sections)
- Add extra commas where natural pauses would occur in speech
- Use line breaks to create natural breathing points"""

        return f"""Clean this text for text-to-speech by removing ONLY:
- Page numbers, headers, footers
- Reference markers like [1], [2], etc.
- Broken hyphenations across lines
- Excessive whitespace

{pause_instruction}

Return ONLY the cleaned text, nothing else.

Text:
{text}"""

    def _enhance_with_natural_formatting(self, text: str) -> str:
        """Apply natural formatting tricks for TTS engines without SSML support."""
        enhanced = text

        # 1. Add natural emphasis (order matters)
        enhanced = self._add_natural_emphasis(enhanced)

        # 2. Add academic formatting (universal approach)
        enhanced = self._add_natural_academic_formatting(enhanced)

        # 3. Enhance punctuation for better rhythm
        enhanced = self._enhance_punctuation_for_natural_speech(enhanced)

        return enhanced

    def _add_natural_emphasis(self, text: str) -> str:
        """Add natural emphasis without SSML tags."""
        # Already quoted text gets natural emphasis from quotes
        # No changes needed for quoted text as TTS engines naturally emphasize quotes

        # For research papers, we could uppercase key transitional words
        # But this might sound unnatural, so we'll rely on punctuation

        return text

    def _add_natural_academic_formatting(self, text: str) -> str:
        """Add natural formatting for academic content without SSML."""
        # Add extra dots after section headers for longer pauses
        text = re.sub(
            r"(Abstract|Introduction|Conclusion|References)(\s*[:\.]?\s*)", r"\1\2... ", text, flags=re.IGNORECASE
        )

        # Add pause after numbered sections with extra dots
        text = re.sub(r"(\d+\.\s*[A-Z][^.]*\.)", r"\1.. ", text)

        # Add line breaks around major transitions for natural pauses
        text = re.sub(r"(However|Therefore|Furthermore|Moreover),", r"\n\1,", text, flags=re.IGNORECASE)

        return text

    def _enhance_punctuation_for_natural_speech(self, text: str) -> str:
        """Enhance punctuation for better natural speech rhythm."""
        # Add extra comma pauses where beneficial
        # After introductory phrases
        text = re.sub(
            r"^(In this paper|In this study|We present|We propose|This work),",
            r"\1,,",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        # Convert single dots between sentences to double for slightly longer pauses
        # But preserve ellipsis (...)
        text = re.sub(r"(?<![.])\.(?![.])\s+(?=[A-Z])", r".. ", text)

        # Add commas after "First", "Second", etc. if not already present
        text = re.sub(
            r"\b(First|Second|Third|Fourth|Fifth|Finally|Additionally|Specifically)(?!,)\s",
            r"\1, ",
            text,
            flags=re.IGNORECASE,
        )

        # Ensure ellipsis has consistent spacing
        text = re.sub(r"\.{3,}", "... ", text)

        return text
