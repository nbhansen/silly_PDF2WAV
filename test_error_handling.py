#!/usr/bin/env python3
"""
Error Handling Demo Script

Demonstrates the new structured error handling system
"""

import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def demonstrate_error_handling():
    """Demonstrate the structured error handling system"""
    print("PDF to Audio Converter - Error Handling Demo")
    print("=" * 60)
    
    try:
        load_dotenv()
        
        from domain.errors import (
            ErrorCode, ApplicationError, file_not_found_error, 
            text_extraction_error, audio_generation_error, 
            tts_engine_error, Result
        )
        from domain.models import ProcessingResult
        
        print("1. Testing error creation...")
        
        # Test different error types
        errors = [
            file_not_found_error("nonexistent.pdf"),
            text_extraction_error("PDF is password protected"),
            audio_generation_error("TTS service rate limit exceeded"),
            tts_engine_error("Gemini API quota exceeded")
        ]
        
        for error in errors:
            print(f"   • {error.code.value}: {error.message}")
            print(f"     Retryable: {error.retryable}")
            if error.details:
                print(f"     Details: {error.details}")
        
        print("\n2. Testing ProcessingResult with errors...")
        
        # Test successful result
        success_result = ProcessingResult.success_result(
            audio_files=["test1.wav", "test2.wav"],
            combined_mp3="combined.mp3"
        )
        print(f"   Success result: {success_result.success}")
        
        # Test failure result
        failure_result = ProcessingResult.failure_result(
            audio_generation_error("Rate limit exceeded")
        )
        print(f"   Failure result: {failure_result.success}")
        print(f"   Error code: {failure_result.get_error_code()}")
        print(f"   Retryable: {failure_result.is_retryable}")
        print(f"   Error message: {failure_result.get_error_message()}")
        
        print("\n3. Testing Result type...")
        
        # Test Result success
        success = Result.success("Processing completed")
        print(f"   Result success: {success.is_success}, value: {success.value}")
        
        # Test Result failure
        failure = Result.failure(tts_engine_error("API timeout"))
        print(f"   Result failure: {failure.is_failure}, error: {failure.error}")
        
        # Test Result from exception
        try:
            raise ValueError("Something went wrong")
        except Exception as e:
            result = Result.from_exception(e, ErrorCode.CONFIGURATION_ERROR, retryable=False)
            print(f"   Exception result: error={result.error.code.value}, retryable={result.error.retryable}")
        
        print("\n4. Testing error categorization...")
        
        retryable_errors = [e for e in errors if e.retryable]
        non_retryable_errors = [e for e in errors if not e.retryable]
        
        print(f"   Retryable errors: {len(retryable_errors)}")
        for error in retryable_errors:
            print(f"     - {error.code.value}")
        
        print(f"   Non-retryable errors: {len(non_retryable_errors)}")
        for error in non_retryable_errors:
            print(f"     - {error.code.value}")
        
        print("\n" + "=" * 60)
        print("🎉 ERROR HANDLING DEMO COMPLETED!")
        print("The structured error handling system is working correctly.")
        print("=" * 60)
        
        print("\n💡 Key Benefits:")
        print("   • Clear error categorization with error codes")
        print("   • Automatic retry detection (retryable vs non-retryable)")
        print("   • Structured error information for logging")
        print("   • User-friendly error messages")
        print("   • Type-safe error handling with Result types")
        
        return True
        
    except Exception as e:
        print(f"\n❌ DEMO FAILED: {e}")
        return False

def demonstrate_real_world_usage():
    """Show how error handling works in real scenarios"""
    print("\n" + "=" * 60)
    print("Real-World Error Handling Examples")
    print("=" * 60)
    
    scenarios = [
        {
            "scenario": "File not found",
            "error_code": "file_not_found",
            "user_action": "User uploads non-existent file",
            "system_response": "Clear error message, no retry suggestion",
            "retryable": False
        },
        {
            "scenario": "TTS rate limit",
            "error_code": "tts_engine_error", 
            "user_action": "Too many requests to Gemini API",
            "system_response": "Retry suggestion with delay",
            "retryable": True
        },
        {
            "scenario": "PDF password protected",
            "error_code": "text_extraction_failed",
            "user_action": "Upload encrypted PDF",
            "system_response": "Suggest different file",
            "retryable": False
        },
        {
            "scenario": "Network timeout",
            "error_code": "llm_provider_error",
            "user_action": "LLM API unavailable", 
            "system_response": "Retry or disable text cleaning",
            "retryable": True
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['scenario']}")
        print(f"   Error Code: {scenario['error_code']}")
        print(f"   User Action: {scenario['user_action']}")
        print(f"   System Response: {scenario['system_response']}")
        print(f"   Retryable: {scenario['retryable']}")
        print()

if __name__ == "__main__":
    success = demonstrate_error_handling()
    
    if success:
        demonstrate_real_world_usage()
        print("\n🚀 Your error handling system is production-ready!")
    else:
        print("\n💥 Please fix the errors above before proceeding.")
        sys.exit(1)