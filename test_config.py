#!/usr/bin/env python3
"""
Configuration System Test Script

Run this to verify your configuration is working correctly.
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_configuration():
    """Test the new configuration system"""
    print("Testing PDF to Audio Converter Configuration")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    try:
        from application.config.system_config import SystemConfig
        
        # Test 1: Load configuration
        print("1. Loading configuration from environment...")
        config = SystemConfig.from_env()
        print("   ✅ Configuration loaded successfully")
        
        # Test 2: Print configuration summary
        print("\n2. Configuration summary:")
        config.print_summary()
        
        # Test 3: Test validation
        print("\n3. Testing validation...")
        config.validate()
        print("   ✅ Configuration validation passed")
        
        # Test 4: Test TTS engine creation
        print("\n4. Testing TTS engine creation...")
        from application.composition_root import _create_tts_engine
        tts_engine = _create_tts_engine(config)
        print(f"   ✅ TTS engine created: {tts_engine.__class__.__name__}")
        
        # Test 5: Test LLM provider creation
        print("\n5. Testing LLM provider creation...")
        from application.composition_root import _create_llm_provider
        llm_provider = _create_llm_provider(config)
        if llm_provider:
            print(f"   ✅ LLM provider created: {llm_provider.__class__.__name__}")
        else:
            print("   ⚠️  LLM provider not available (no API key)")
        
        # Test 6: Test complete service creation
        print("\n6. Testing complete service creation...")
        from application.composition_root import create_pdf_service_from_env
        pdf_service = create_pdf_service_from_env()
        print(f"   ✅ PDF service created successfully")
        
        # Test 7: Test SSML service if enabled
        print("\n7. Testing SSML service...")
        if hasattr(pdf_service, 'ssml_service') and pdf_service.ssml_service:
            ssml_info = pdf_service.ssml_service.get_capability_info()
            print(f"   ✅ SSML service active: {ssml_info['capability']} capability")
            print(f"      Document type: {ssml_info['document_type']}")
            print(f"      Number enhancement: {ssml_info['features_enabled']['number_enhancement']}")
            print(f"      Advanced prosody: {ssml_info['features_enabled']['advanced_prosody']}")
        else:
            print("   ⚠️  SSML service not available (disabled or no TTS engine)")
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("Your advanced SSML configuration system is working correctly.")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\nPlease check your configuration and try again.")
        return False

def show_environment_guide():
    """Show guide for setting up environment variables"""
    print("\n📋 Environment Variables Guide")
    print("=" * 40)
    print("Required variables:")
    print("  TTS_ENGINE=piper              # or 'gemini'")
    print("")
    print("Optional variables:")
    print("  UPLOAD_FOLDER=uploads")
    print("  AUDIO_FOLDER=audio_outputs")
    print("  MAX_FILE_SIZE_MB=100")
    print("  ENABLE_TEXT_CLEANING=True")
    print("  ENABLE_SSML=True")
    print("  DOCUMENT_TYPE=research_paper      # research_paper, literature_review, general")
    print("  ENABLE_ASYNC_AUDIO=True")
    print("  MAX_CONCURRENT_TTS_REQUESTS=4")
    print("")
    print("For Gemini TTS:")
    print("  GOOGLE_AI_API_KEY=your_api_key")
    print("  GEMINI_VOICE_NAME=Kore")
    print("")
    print("For Piper TTS:")
    print("  PIPER_MODEL_NAME=en_US-lessac-medium")
    print("  PIPER_MODELS_DIR=piper_models")
    print("")
    print("Create a .env file with these variables or set them in your shell.")

if __name__ == "__main__":
    print("PDF to Audio Converter - Configuration Test")
    print()
    
    success = test_configuration()
    
    if not success:
        show_environment_guide()
        sys.exit(1)
    
    print("\n🚀 Ready to start the application with: python app.py")