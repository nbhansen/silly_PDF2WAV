#!/usr/bin/env python3
# test_migration.py - Quick test to verify the refactoring worked

import os
import sys

def test_imports():
    """Test that all imports work"""
    print("🧪 Testing imports...")
    
    try:
        # Test domain imports
        from domain.models import PageRange, ProcessingRequest, PDFInfo
        from domain.interfaces import ITTSEngine, ILLMProvider
        from domain.config import PiperConfig, CoquiConfig
        print("✅ Domain imports successful")
        
        # Test application imports  
        from application.config import TTSConfigFactory, PiperConfigBuilder
        print("✅ Application config imports successful")
        
        # Test composition root
        from application.composition_root import create_pdf_service_from_env
        print("✅ Composition root imports successful")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_piper_config():
    """Test that Piper configuration works"""
    print("\n🔧 Testing Piper configuration...")
    
    try:
        # Set test environment
        os.environ['PIPER_MODEL_NAME'] = 'en_US-ryan-medium'
        os.environ['PIPER_SPEED'] = '0.9'
        
        from application.config import PiperConfigBuilder
        config = PiperConfigBuilder.from_env()
        
        assert config.model_name == 'en_US-ryan-medium'
        assert config.length_scale == 0.9
        print(f"✅ Piper config working: {config.model_name} at speed {config.length_scale}")
        
        return True
    except Exception as e:
        print(f"❌ Piper config failed: {e}")
        return False

def test_tts_factory():
    """Test TTS factory"""
    print("\n🏭 Testing TTS factory...")
    
    try:
        from application.config import TTSConfigFactory
        
        # Test creating configs for different engines
        engines_to_test = ['piper', 'coqui', 'gtts']
        
        for engine in engines_to_test:
            config = TTSConfigFactory.create_config(engine)
            engine_config = getattr(config, engine, None)
            print(f"✅ {engine}: {type(engine_config).__name__ if engine_config else 'Default config'}")
        
        return True
    except Exception as e:
        print(f"❌ TTS factory failed: {e}")
        return False

def test_service_creation():
    """Test service creation"""
    print("\n🎯 Testing service creation...")
    
    try:
        # Mock environment for testing
        os.environ['TTS_ENGINE'] = 'piper'
        os.environ['GOOGLE_AI_API_KEY'] = 'test_key'
        
        from application.composition_root import create_pdf_service_from_env
        service = create_pdf_service_from_env()
        
        print(f"✅ Service created successfully: {type(service).__name__}")
        return True
    except Exception as e:
        print(f"❌ Service creation failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Clean Configuration Architecture Migration")
    print("=" * 60)
    
    tests = [
        ("Import Tests", test_imports),
        ("Piper Config Tests", test_piper_config), 
        ("TTS Factory Tests", test_tts_factory),
        ("Service Creation Tests", test_service_creation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Migration successful! Your Piper configuration is now working.")
        print("\n💡 You can now change PIPER_MODEL_NAME in your .env file!")
        print("Available models: en_US-ryan-medium, en_GB-alba-medium, etc.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        print("Common issues:")
        print("  - Missing __init__.py files in new directories")
        print("  - Import path typos")
        print("  - Missing .env file")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)