#!/usr/bin/env python3
"""
Manual testing script for Phase 1 architectural improvements
Run this to manually verify the changes work correctly
"""

import os
import sys
import tempfile
from typing import List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from application.composition_root import create_pdf_service_from_env
from domain.models import ProcessingRequest, PageRange
from domain.errors import Result
from infrastructure.tts.piper_tts_provider import PiperTTSProvider
from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
from domain.config.tts_config import PiperConfig


def test_result_pattern():
    """Test the new Result pattern"""
    print("🧪 Testing Result Pattern...")
    
    # Test success
    success_result = Result.success("test data")
    assert success_result.is_success
    assert success_result.value == "test data"
    print("  ✅ Result.success() works correctly")
    
    # Test failure
    from domain.errors import tts_engine_error
    error = tts_engine_error("Test error")
    failure_result = Result.failure(error)
    assert failure_result.is_failure
    assert failure_result.error.details == "Test error"
    print("  ✅ Result.failure() works correctly")
    
    print("  ✅ Result pattern working correctly!")


def test_tts_error_handling():
    """Test TTS provider error handling"""
    print("\\n🔊 Testing TTS Error Handling...")
    
    try:
        # Test Piper TTS with empty text
        config = PiperConfig(model_name="en_US-lessac-medium", download_dir="piper_models")
        provider = PiperTTSProvider(config)
        
        result = provider.generate_audio_data("")
        assert result.is_failure
        print("  ✅ Empty text properly rejected")
        
        # Test with valid text
        result = provider.generate_audio_data("Hello world")
        if result.is_success:
            print(f"  ✅ Valid text generated {len(result.value)} bytes of audio")
        else:
            print(f"  ⚠️  Audio generation failed: {result.error}")
        
    except Exception as e:
        print(f"  ❌ TTS test failed: {e}")


def test_composition_root():
    """Test the composition root with dependency injection"""
    print("\\n🏗️  Testing Composition Root...")
    
    try:
        # Create service from environment
        service = create_pdf_service_from_env()
        print("  ✅ PDF service created successfully")
        
        # Check that new coordinator is injected
        has_coordinator = hasattr(service.audio_generation_service, 'async_coordinator')
        coordinator = service.audio_generation_service.async_coordinator
        
        if has_coordinator and coordinator:
            print("  ✅ Audio coordinator properly injected")
            print(f"     - Rate limiter: {coordinator.rate_limiter is not None}")
            print(f"     - File processor: {coordinator.file_processor is not None}")
            print(f"     - TTS engine: {coordinator.tts_engine is not None}")
        else:
            print("  ⚠️  Audio coordinator not found")
        
        # Test basic service properties
        print(f"  📊 Service properties:")
        print(f"     - Timing strategy: {type(service.audio_generation_service.timing_strategy).__name__}")
        print(f"     - TTS engine: {type(service.audio_generation_service.timing_strategy.tts_engine).__name__}")
        print(f"     - File manager: {type(service.file_manager).__name__}")
        
    except Exception as e:
        print(f"  ❌ Composition root test failed: {e}")
        import traceback
        traceback.print_exc()


def test_error_propagation():
    """Test error propagation through the system"""
    print("\\n🚨 Testing Error Propagation...")
    
    try:
        # Create a processing request for non-existent file
        request = ProcessingRequest(
            pdf_path="nonexistent.pdf",
            output_name="test_output",
            page_range=PageRange()
        )
        
        service = create_pdf_service_from_env()
        result = service.process_pdf(request)
        
        if not result.success:
            print("  ✅ Error properly handled for non-existent file")
            print(f"     - Error code: {result.get_error_code()}")
            print(f"     - Error message: {result.get_error_message()}")
            print(f"     - Is retryable: {result.is_retryable}")
        else:
            print("  ⚠️  Expected error but processing succeeded")
        
    except Exception as e:
        print(f"  ❌ Error propagation test failed: {e}")


def test_audio_coordinator_directly():
    """Test the audio coordinator directly"""
    print("\\n🎵 Testing Audio Coordinator...")
    
    try:
        from domain.services.audio_generation_coordinator import AudioGenerationCoordinator
        from infrastructure.file.file_manager import FileManager
        from tests.test_helpers import FakeTTSEngine
        
        # Create coordinator with fake TTS
        temp_dir = tempfile.mkdtemp()
        file_manager = FileManager(upload_folder=temp_dir, output_folder=temp_dir)
        tts_engine = FakeTTSEngine()
        
        coordinator = AudioGenerationCoordinator(
            tts_engine=tts_engine,
            file_manager=file_manager,
            max_concurrent_requests=2
        )
        
        # Test audio generation
        chunks = ["Hello world", "This is a test", "Goodbye"]
        audio_files, combined_mp3 = coordinator.sync_generate_audio(
            chunks, "test_output", temp_dir
        )
        
        print(f"  ✅ Generated {len(audio_files)} audio files")
        print(f"  ✅ TTS engine processed {len(tts_engine.generated_texts)} chunks")
        print(f"  ✅ Combined MP3: {combined_mp3 is not None}")
        
        # Test with empty chunks
        empty_result = coordinator.sync_generate_audio([], "empty", temp_dir)
        assert empty_result == ([], None)
        print("  ✅ Empty chunks handled correctly")
        
    except Exception as e:
        print(f"  ❌ Audio coordinator test failed: {e}")
        import traceback
        traceback.print_exc()


def test_rate_limiting():
    """Test rate limiting service"""
    print("\\n⏱️  Testing Rate Limiting...")
    
    try:
        from domain.services.rate_limiting_service import RateLimitingService
        from tests.test_helpers import FakeTTSEngine
        
        rate_limiter = RateLimitingService(max_concurrent_requests=1)
        
        # Test delay calculation
        gemini_engine = FakeTTSEngine()
        gemini_engine.__class__.__name__ = "GeminiTTSProvider"
        
        piper_engine = FakeTTSEngine()
        piper_engine.__class__.__name__ = "PiperTTSProvider"
        
        gemini_delay = rate_limiter.get_base_delay_for_engine(gemini_engine)
        piper_delay = rate_limiter.get_base_delay_for_engine(piper_engine)
        
        print(f"  ✅ Gemini delay: {gemini_delay}s (should be higher)")
        print(f"  ✅ Piper delay: {piper_delay}s (should be lower)")
        
        assert gemini_delay > piper_delay
        print("  ✅ Rate limiting configured correctly for different engines")
        
        # Test retry delay
        retry_delays = [rate_limiter.get_retry_delay(i, 1.0) for i in range(4)]
        print(f"  ✅ Retry delays: {retry_delays} (should increase)")
        
        for i in range(1, len(retry_delays)):
            assert retry_delays[i] >= retry_delays[i-1]
        
        print("  ✅ Exponential backoff working correctly")
        
    except Exception as e:
        print(f"  ❌ Rate limiting test failed: {e}")


def main():
    """Run all manual tests"""
    print("🚀 Phase 1 Manual Testing")
    print("=" * 50)
    
    test_result_pattern()
    test_tts_error_handling()
    test_composition_root()
    test_error_propagation()
    test_audio_coordinator_directly()
    test_rate_limiting()
    
    print("\\n" + "=" * 50)
    print("✅ Phase 1 manual testing complete!")
    print("\\n💡 To run automated tests:")
    print("   python -m pytest tests/test_phase1_services.py -v")
    print("   python -m pytest tests/test_error_handling.py -v")
    print("   python -m pytest tests/test_phase1_integration.py -v")


if __name__ == "__main__":
    main()