# tests/unit/test_error_handling_tdd.py
"""TDD tests for Error Handling System - comprehensive coverage following red-green-refactor cycle.
Tests error creation, result types, error classification, and error factory functions.
"""

from domain.errors import (
    ApplicationError,
    ErrorCode,
    Result,
    audio_generation_error,
    configuration_error,
    file_size_error,
    invalid_page_range_error,
    llm_provider_error,
    text_extraction_error,
    tts_engine_error,
    unsupported_file_type_error,
)


class TestErrorCodeEnum:
    """TDD tests for ErrorCode enumeration."""

    def test_error_code_enum_contains_all_expected_codes(self):
        """Should define all necessary error codes for the application."""
        expected_codes = {
            "FILE_NOT_FOUND",
            "TEXT_EXTRACTION_FAILED",
            "TEXT_CLEANING_FAILED",
            "AUDIO_GENERATION_FAILED",
            "INVALID_PAGE_RANGE",
            "CONFIGURATION_ERROR",
            "TTS_ENGINE_ERROR",
            "LLM_PROVIDER_ERROR",
            "SSML_PROCESSING_ERROR",
            "FILE_SIZE_ERROR",
            "UNSUPPORTED_FILE_TYPE",
            "UNKNOWN_ERROR",
        }

        actual_codes = {code.name for code in ErrorCode}
        assert actual_codes == expected_codes

    def test_error_code_enum_values_are_kebab_case(self):
        """Should use consistent kebab-case for error code values."""
        for code in ErrorCode:
            # All values should be lowercase with underscores (kebab-case style)
            assert code.value.islower(), f"Error code {code.name} value should be lowercase"
            assert " " not in code.value, f"Error code {code.name} should not contain spaces"

    def test_error_code_enum_string_representation(self):
        """Should have meaningful string representations."""
        assert ErrorCode.FILE_NOT_FOUND.value == "file_not_found"
        assert ErrorCode.AUDIO_GENERATION_FAILED.value == "audio_generation_failed"
        assert ErrorCode.CONFIGURATION_ERROR.value == "configuration_error"

    def test_error_code_enum_uniqueness(self):
        """Should have unique values for all error codes."""
        values = [code.value for code in ErrorCode]
        assert len(values) == len(set(values)), "All error code values should be unique"


class TestApplicationError:
    """TDD tests for ApplicationError class."""

    def test_application_error_creation_with_minimal_args(self):
        """Should create error with minimal required arguments."""
        error = ApplicationError(code=ErrorCode.UNKNOWN_ERROR, message="Something went wrong")

        assert error.code == ErrorCode.UNKNOWN_ERROR
        assert error.message == "Something went wrong"
        assert error.details is None
        assert error.retryable is False  # Default value

    def test_application_error_creation_with_all_args(self):
        """Should create error with all arguments."""
        error = ApplicationError(
            code=ErrorCode.TTS_ENGINE_ERROR,
            message="TTS service unavailable",
            details="Rate limit exceeded",
            retryable=True,
        )

        assert error.code == ErrorCode.TTS_ENGINE_ERROR
        assert error.message == "TTS service unavailable"
        assert error.details == "Rate limit exceeded"
        assert error.retryable is True

    def test_application_error_string_representation(self):
        """Should have meaningful string representation."""
        error = ApplicationError(
            code=ErrorCode.AUDIO_GENERATION_FAILED, message="Failed to generate audio", details="Model not found"
        )

        expected = "audio_generation_failed: Failed to generate audio"
        assert str(error) == expected

    def test_application_error_repr_representation(self):
        """Should have detailed repr representation for debugging."""
        error = ApplicationError(code=ErrorCode.FILE_SIZE_ERROR, message="File too large", retryable=False)

        repr_str = repr(error)
        assert "ApplicationError" in repr_str
        assert "file_size_error" in repr_str
        assert "File too large" in repr_str
        assert "retryable=False" in repr_str

    def test_application_error_equality(self):
        """Should support equality comparison."""
        error1 = ApplicationError(code=ErrorCode.CONFIGURATION_ERROR, message="Invalid config", retryable=False)
        error2 = ApplicationError(code=ErrorCode.CONFIGURATION_ERROR, message="Invalid config", retryable=False)
        error3 = ApplicationError(code=ErrorCode.CONFIGURATION_ERROR, message="Different message", retryable=False)

        assert error1 == error2
        assert error1 != error3

    def test_application_error_with_empty_message(self):
        """Should handle empty message gracefully."""
        error = ApplicationError(code=ErrorCode.UNKNOWN_ERROR, message="")

        assert error.message == ""
        assert str(error) == "unknown_error: "

    def test_application_error_with_unicode_content(self):
        """Should handle unicode content in messages and details."""
        error = ApplicationError(
            code=ErrorCode.TEXT_EXTRACTION_FAILED,
            message="Échec de l'extraction: 文本提取失败",
            details="File contains unsupported characters: ñáéíóú",
        )

        assert "Échec" in error.message
        assert "文本提取失败" in error.message
        assert "ñáéíóú" in error.details if error.details else False


class TestResultType:
    """TDD tests for Result[T] generic type."""

    def test_result_success_creation(self):
        """Should create successful result with value."""
        result = Result.success("test_value")

        assert result.value == "test_value"
        assert result.error is None
        assert result.is_success is True
        assert result.is_failure is False

    def test_result_failure_creation(self):
        """Should create failed result with error."""
        error = ApplicationError(ErrorCode.UNKNOWN_ERROR, "Test error")
        result: Result[None] = Result.failure(error)

        assert result.value is None
        assert result.error == error
        assert result.is_success is False
        assert result.is_failure is True

    def test_result_success_with_different_types(self):
        """Should support different value types."""
        # String result
        str_result = Result.success("hello")
        assert str_result.value == "hello"
        assert isinstance(str_result.value, str)

        # Integer result
        int_result = Result.success(42)
        assert int_result.value == 42
        assert isinstance(int_result.value, int)

        # List result
        list_result = Result.success([1, 2, 3])
        assert list_result.value == [1, 2, 3]
        assert isinstance(str_result.value, str)

        # None result (valid case)
        none_result = Result.success(None)
        assert none_result.value is None
        assert none_result.is_success is True

    def test_result_from_exception_with_defaults(self):
        """Should create result from exception with default error code."""
        exception = ValueError("Invalid input")
        result: Result[None] = Result.from_exception(exception)

        assert result.is_failure is True
        assert result.error is not None
        assert result.error.code == ErrorCode.UNKNOWN_ERROR
        assert result.error.message == "Invalid input"
        assert result.error.details == "ValueError"
        assert result.error.retryable is False

    def test_result_from_exception_with_custom_args(self):
        """Should create result from exception with custom error code and retryable flag."""
        exception = ConnectionError("Network timeout")
        result: Result[None] = Result.from_exception(exception, code=ErrorCode.TTS_ENGINE_ERROR, retryable=True)

        assert result.is_failure is True
        assert result.error is not None
        assert result.error.code == ErrorCode.TTS_ENGINE_ERROR
        assert result.error.message == "Network timeout"
        assert result.error.details == "ConnectionError"
        assert result.error.retryable is True

    def test_result_from_exception_with_complex_exception(self):
        """Should handle complex exception types."""

        class CustomException(Exception):
            def __init__(self, message: str, error_code: int) -> None:
                super().__init__(message)
                self.error_code = error_code

        exception = CustomException("Custom error occurred", 500)
        result: Result[None] = Result.from_exception(exception, ErrorCode.CONFIGURATION_ERROR)

        assert result.error is not None
        assert result.error.message == "Custom error occurred"
        assert result.error.details == "CustomException"
        assert result.error.code == ErrorCode.CONFIGURATION_ERROR

    def test_result_mutually_exclusive_success_failure(self):
        """Should ensure success and failure are mutually exclusive."""
        success_result = Result.success("value")
        failure_result: Result[None] = Result.failure(ApplicationError(ErrorCode.UNKNOWN_ERROR, "error"))

        # Success result
        assert success_result.is_success
        assert not success_result.is_failure

        # Failure result
        assert failure_result.is_failure
        assert not failure_result.is_success

    def test_result_type_hints_work_correctly(self):
        """Should work correctly with type annotations."""

        # This test documents that the generic typing works
        def process_data() -> Result[str]:
            return Result.success("processed")

        def process_number() -> Result[int]:
            return Result.success(42)

        str_result = process_data()
        int_result = process_number()

        assert isinstance(str_result.value, str)
        assert isinstance(int_result.value, int)


class TestErrorFactoryFunctions:
    """TDD tests for error factory functions."""

    def test_text_extraction_error_factory(self):
        """Should create text extraction error with correct properties."""
        error = text_extraction_error("PDF is corrupted")

        assert error.code == ErrorCode.TEXT_EXTRACTION_FAILED
        assert error.message == "Failed to extract text from PDF"
        assert error.details == "PDF is corrupted"
        assert error.retryable is True  # Text extraction errors should be retryable

    def test_audio_generation_error_factory_with_details(self):
        """Should create audio generation error with details."""
        error = audio_generation_error("Model not available")

        assert error.code == ErrorCode.AUDIO_GENERATION_FAILED
        assert error.message == "Audio generation failed"
        assert error.details == "Model not available"
        assert error.retryable is True

    def test_audio_generation_error_factory_without_details(self):
        """Should create audio generation error without details."""
        error = audio_generation_error()

        assert error.code == ErrorCode.AUDIO_GENERATION_FAILED
        assert error.message == "Audio generation failed"
        assert error.details is None
        assert error.retryable is True

    def test_tts_engine_error_factory(self):
        """Should create TTS engine error with correct properties."""
        error = tts_engine_error("Rate limit exceeded")

        assert error.code == ErrorCode.TTS_ENGINE_ERROR
        assert error.message == "TTS engine error"
        assert error.details == "Rate limit exceeded"
        assert error.retryable is True  # TTS errors are typically transient

    def test_llm_provider_error_factory(self):
        """Should create LLM provider error with correct properties."""
        error = llm_provider_error("API quota exceeded")

        assert error.code == ErrorCode.LLM_PROVIDER_ERROR
        assert error.message == "LLM provider error"
        assert error.details == "API quota exceeded"
        assert error.retryable is True  # LLM errors are typically transient

    def test_invalid_page_range_error_factory(self):
        """Should create page range error with correct properties."""
        error = invalid_page_range_error("Page 15 does not exist in 10-page document")

        assert error.code == ErrorCode.INVALID_PAGE_RANGE
        assert error.message == "Invalid page range"
        assert error.details == "Page 15 does not exist in 10-page document"
        assert error.retryable is False  # User input errors are not retryable

    def test_configuration_error_factory(self):
        """Should create configuration error with correct properties."""
        error = configuration_error("GOOGLE_AI_API_KEY is required")

        assert error.code == ErrorCode.CONFIGURATION_ERROR
        assert error.message == "Configuration error"
        assert error.details == "GOOGLE_AI_API_KEY is required"
        assert error.retryable is False  # Configuration errors are not retryable

    def test_file_size_error_factory(self):
        """Should create file size error with formatted message."""
        error = file_size_error(150.5, 100)

        assert error.code == ErrorCode.FILE_SIZE_ERROR
        assert "150.5MB exceeds maximum 100MB" in error.message
        assert error.retryable is False  # File size errors are not retryable

    def test_file_size_error_factory_with_different_values(self):
        """Should handle different file size values correctly."""
        # Test with small decimal
        error1 = file_size_error(0.5, 1)
        assert "0.5MB exceeds maximum 1MB" in error1.message

        # Test with large numbers
        error2 = file_size_error(2048.7, 1000)
        assert "2048.7MB exceeds maximum 1000MB" in error2.message

        # Test with exact boundary
        error3 = file_size_error(100.1, 100)
        assert "100.1MB exceeds maximum 100MB" in error3.message

    def test_unsupported_file_type_error_factory(self):
        """Should create unsupported file type error with file type."""
        error = unsupported_file_type_error("docx")

        assert error.code == ErrorCode.UNSUPPORTED_FILE_TYPE
        assert "Unsupported file type: docx" in error.message
        assert error.details == "Only PDF files are supported"
        assert error.retryable is False  # File type errors are not retryable

    def test_unsupported_file_type_error_with_different_types(self):
        """Should handle different file types correctly."""
        test_cases = ["txt", "doc", "rtf", "html", ".pdf", "PDF"]

        for file_type in test_cases:
            error = unsupported_file_type_error(file_type)
            assert f"Unsupported file type: {file_type}" in error.message
            assert error.details == "Only PDF files are supported"


class TestErrorClassification:
    """TDD tests for error classification and retryability logic."""

    def test_retryable_errors_are_correctly_classified(self):
        """Should correctly identify retryable errors."""
        retryable_errors = [
            text_extraction_error("OCR failed"),
            audio_generation_error("TTS service down"),
            tts_engine_error("Rate limited"),
            llm_provider_error("API timeout"),
        ]

        for error in retryable_errors:
            assert error.retryable is True, f"{error.code} should be retryable"

    def test_non_retryable_errors_are_correctly_classified(self):
        """Should correctly identify non-retryable errors."""
        non_retryable_errors = [
            invalid_page_range_error("Invalid page"),
            configuration_error("Missing API key"),
            file_size_error(200, 100),
            unsupported_file_type_error("txt"),
        ]

        for error in non_retryable_errors:
            assert error.retryable is False, f"{error.code} should not be retryable"

    def test_error_classification_consistency(self):
        """Should maintain consistent error classification logic."""
        # Define expected classifications

        # Test factory functions produce consistent classifications
        factory_tests = [
            (text_extraction_error("test"), True),
            (audio_generation_error("test"), True),
            (tts_engine_error("test"), True),
            (llm_provider_error("test"), True),
            (invalid_page_range_error("test"), False),
            (configuration_error("test"), False),
            (file_size_error(1, 0), False),
            (unsupported_file_type_error("test"), False),
        ]

        for error, should_be_retryable in factory_tests:
            assert error.retryable == should_be_retryable

    def test_custom_error_retryability(self):
        """Should support custom retryability settings."""
        # Create custom retryable error
        custom_retryable = ApplicationError(
            code=ErrorCode.CONFIGURATION_ERROR,  # Normally not retryable
            message="Temporary config issue",
            retryable=True,  # Override default
        )
        assert custom_retryable.retryable is True

        # Create custom non-retryable error
        custom_non_retryable = ApplicationError(
            code=ErrorCode.TTS_ENGINE_ERROR,  # Normally retryable
            message="Permanent TTS issue",
            retryable=False,  # Override default
        )
        assert custom_non_retryable.retryable is False


class TestErrorHandlingPatterns:
    """TDD tests for common error handling patterns."""

    def test_result_chaining_pattern(self):
        """Should support result chaining for error propagation."""

        def operation_that_fails() -> Result[str]:
            return Result.failure(text_extraction_error("PDF corrupted"))

        def operation_that_succeeds() -> Result[str]:
            return Result.success("success")

        # Test failure propagation
        failed_result = operation_that_fails()
        assert failed_result.is_failure
        assert failed_result.error is not None
        assert failed_result.error.code == ErrorCode.TEXT_EXTRACTION_FAILED

        # Test success
        success_result = operation_that_succeeds()
        assert success_result.is_success
        assert success_result.value == "success"

    def test_error_context_preservation(self):
        """Should preserve error context through function calls."""

        def low_level_operation() -> Result[str]:
            try:
                raise ConnectionError("Network unreachable")
            except Exception as e:
                return Result.from_exception(e, ErrorCode.TTS_ENGINE_ERROR, retryable=True)

        def high_level_operation() -> Result[str]:
            result = low_level_operation()
            if result.is_failure:
                # Error context is preserved
                return result
            return Result.success("processed")

        final_result = high_level_operation()
        assert final_result.is_failure
        assert final_result.error is not None
        assert final_result.error.code == ErrorCode.TTS_ENGINE_ERROR
        assert final_result.error.message == "Network unreachable"
        assert final_result.error.details == "ConnectionError"
        assert final_result.error.retryable is True

    def test_error_aggregation_pattern(self):
        """Should support collecting multiple errors."""
        errors = [
            text_extraction_error("Page 1 failed"),
            text_extraction_error("Page 3 failed"),
            audio_generation_error("TTS unavailable"),
        ]

        # Test that we can collect and analyze multiple errors
        assert len(errors) == 3

        extraction_errors = [e for e in errors if e.code == ErrorCode.TEXT_EXTRACTION_FAILED]
        audio_errors = [e for e in errors if e.code == ErrorCode.AUDIO_GENERATION_FAILED]

        assert len(extraction_errors) == 2
        assert len(audio_errors) == 1
        assert all(e.retryable for e in errors)  # All these errors are retryable

    def test_error_recovery_pattern(self):
        """Should support error recovery patterns."""

        def operation_with_fallback() -> Result[str]:
            # Primary operation fails
            primary_result: Result[str] = Result.failure(tts_engine_error("Gemini unavailable"))

            if primary_result.is_failure and primary_result.error is not None and primary_result.error.retryable:
                # Fallback operation succeeds
                return Result.success("fallback_result")

            return primary_result

        result = operation_with_fallback()
        assert result.is_success
        assert result.value == "fallback_result"

    def test_error_filtering_by_type(self):
        """Should support filtering errors by type and retryability."""
        all_errors = [
            text_extraction_error("OCR failed"),
            configuration_error("Missing API key"),
            tts_engine_error("Rate limited"),
            file_size_error(200, 100),
            llm_provider_error("Quota exceeded"),
        ]

        # Filter retryable errors
        retryable_errors = [e for e in all_errors if e.retryable]
        assert len(retryable_errors) == 3

        # Filter configuration errors
        config_errors = [e for e in all_errors if e.code == ErrorCode.CONFIGURATION_ERROR]
        assert len(config_errors) == 1

        # Filter by multiple criteria
        retryable_service_errors = [
            e
            for e in all_errors
            if e.retryable and e.code in {ErrorCode.TTS_ENGINE_ERROR, ErrorCode.LLM_PROVIDER_ERROR}
        ]
        assert len(retryable_service_errors) == 2


class TestErrorHandlingEdgeCases:
    """TDD tests for edge cases and unusual scenarios."""

    def test_error_with_very_long_messages(self):
        """Should handle very long error messages gracefully."""
        long_message = "x" * 10000  # 10k character message
        long_details = "y" * 5000  # 5k character details

        error = ApplicationError(code=ErrorCode.UNKNOWN_ERROR, message=long_message, details=long_details)

        assert len(error.message) == 10000
        assert error.details is not None
        assert len(error.details) == 5000
        assert str(error).startswith("unknown_error: " + "x" * 100)  # Should not crash

    def test_error_with_special_characters(self):
        """Should handle special characters in error messages."""
        special_chars = "!@#$%^&*()[]{}|;:,.<>?/~`"

        error = ApplicationError(
            code=ErrorCode.TEXT_EXTRACTION_FAILED,
            message=f"Error with special chars: {special_chars}",
            details=f"Details: {special_chars}",
        )

        assert special_chars in error.message
        assert error.details is not None
        assert special_chars in error.details
        assert special_chars in str(error)

    def test_result_with_complex_value_types(self):
        """Should handle complex value types in Result."""
        # Test with dictionary
        from typing import Any

        test_dict: dict[str, Any] = {"key": "value", "nested": {"inner": 42}}
        dict_result: Result[dict[str, Any]] = Result.success(test_dict)
        assert dict_result.is_success
        assert dict_result.value is not None
        assert dict_result.value["key"] == "value"
        assert dict_result.value["nested"]["inner"] == 42

        # Test with custom object
        class CustomObject:
            def __init__(self, name: str) -> None:
                self.name = name

        obj = CustomObject("test")
        obj_result = Result.success(obj)
        assert obj_result.is_success
        assert obj_result.value is not None
        assert obj_result.value.name == "test"

    def test_error_immutability_characteristics(self):
        """Should test error object characteristics."""
        error = ApplicationError(code=ErrorCode.CONFIGURATION_ERROR, message="Test error", retryable=False)

        # Document current behavior (dataclass is mutable by default)
        error.message = "Modified message"
        assert error.message == "Modified message"

        # This documents that errors are mutable (design decision)
        # If immutability is desired, this test should be updated

    def test_exception_to_result_with_none_exception(self):
        """Should handle edge cases in exception conversion."""

        # Test with exception that has None message
        class EmptyException(Exception):
            def __str__(self):
                return ""

        exception = EmptyException()
        result: Result[None] = Result.from_exception(exception)

        assert result.is_failure
        assert result.error is not None
        assert result.error.message == ""
        assert result.error.details == "EmptyException"
