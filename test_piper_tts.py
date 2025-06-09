# test_piper_tts.py - Test script for Piper TTS integration

import os
import tempfile
from pathlib import Path

def test_piper_installation():
    """Test if Piper TTS is properly installed"""
    print("🔍 Testing Piper TTS installation...")
    
    try:
        from infrastructure.tts.piper_tts_provider import PIPER_AVAILABLE, PiperTTSProvider, PiperConfig
        
        if not PIPER_AVAILABLE:
            print("❌ Piper TTS not available")
            print("💡 Install with: pip install piper-tts")
            return False
        
        print("✅ Piper TTS found and available")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_piper_basic_functionality():
    """Test basic Piper TTS functionality"""
    print("\n🎵 Testing basic Piper TTS functionality...")
    
    try:
        from infrastructure.tts.piper_tts_provider import PiperTTSProvider, PiperConfig
        
        # Create provider with test configuration
        config = PiperConfig(
            model_name="en_US-lessac-medium",
            length_scale=1.0,
            noise_scale=0.667,
            download_dir="test_piper_models"
        )
        
        provider = PiperTTSProvider(config)
        
        # Test simple text generation
        test_text = "Hello, this is a test of Piper text-to-speech synthesis."
        print(f"📝 Testing with text: {test_text}")
        
        audio_data = provider.generate_audio_data(test_text)
        
        if audio_data and len(audio_data) > 0:
            print(f"✅ Audio generated successfully ({len(audio_data)} bytes)")
            
            # Save test audio file
            test_output = "test_piper_output.wav"
            with open(test_output, "wb") as f:
                f.write(audio_data)
            print(f"💾 Test audio saved as: {test_output}")
            return True
        else:
            print("❌ No audio data generated")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Piper: {e}")
        return False

def test_piper_ssml_conversion():
    """Test SSML tag stripping and conversion"""
    print("\n🏷️ Testing SSML conversion...")
    
    try:
        from infrastructure.tts.piper_tts_provider import PiperTTSProvider, PiperConfig
        
        config = PiperConfig(download_dir="test_piper_models")
        provider = PiperTTSProvider(config)
        
        # Test SSML input
        ssml_text = """<speak>
        <p>This is a test of <emphasis level="moderate">academic paper synthesis</emphasis>.</p>
        <break time="1s"/>
        <p>We found a <say-as interpret-as="decimal">73.2</say-as> percent increase in efficiency.</p>
        <break time="500ms"/>
        <p><prosody rate="slow">However, further research is needed.</prosody></p>
        </speak>"""
        
        print(f"📝 Testing SSML conversion with: {ssml_text[:100]}...")
        
        # Test the internal SSML stripping method
        clean_text = provider._strip_ssml_tags(ssml_text)
        print(f"🔧 Converted to: {clean_text}")
        
        # Generate audio from converted text
        audio_data = provider.generate_audio_data(ssml_text)
        
        if audio_data and len(audio_data) > 0:
            print(f"✅ SSML conversion and audio generation successful ({len(audio_data)} bytes)")
            
            # Save SSML test audio
            ssml_output = "test_piper_ssml.wav"
            with open(ssml_output, "wb") as f:
                f.write(audio_data)
            print(f"💾 SSML test audio saved as: {ssml_output}")
            return True
        else:
            print("❌ SSML conversion failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing SSML: {e}")
        return False

def test_piper_academic_content():
    """Test with realistic academic paper content"""
    print("\n📚 Testing with academic paper content...")
    
    try:
        from infrastructure.tts.piper_tts_provider import PiperTTSProvider, PiperConfig
        
        # Configure for academic content
        config = PiperConfig(
            model_name="en_US-lessac-medium",
            length_scale=1.1,  # Slightly slower for technical content
            sentence_silence=0.3,  # Longer pauses between sentences
            download_dir="test_piper_models"
        )
        
        provider = PiperTTSProvider(config)
        
        # Realistic academic content
        academic_text = """
        Introduction. This study investigates the correlation between machine learning algorithms 
        and computational efficiency in text-to-speech synthesis. We analyzed data from 1,247 
        research papers published between 2020 and 2024. Results indicate a significant improvement 
        in processing speed of 73.2 percent when using neural network architectures. However, 
        further research is needed to validate these findings across different domains.
        """
        
        print(f"📝 Testing academic content: {academic_text[:100]}...")
        
        audio_data = provider.generate_audio_data(academic_text.strip())
        
        if audio_data and len(audio_data) > 0:
            print(f"✅ Academic content processed successfully ({len(audio_data)} bytes)")
            
            # Save academic test audio
            academic_output = "test_piper_academic.wav"
            with open(academic_output, "wb") as f:
                f.write(audio_data)
            print(f"💾 Academic test audio saved as: {academic_output}")
            return True
        else:
            print("❌ Academic content processing failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing academic content: {e}")
        return False

def test_piper_integration_with_system():
    """Test full integration with your PDF processing system"""
    print("\n🔗 Testing integration with PDF processing system...")
    
    try:
        # Test environment variable configuration
        os.environ['TTS_ENGINE'] = 'piper'
        os.environ['PIPER_MODEL_NAME'] = 'en_US-lessac-medium'
        os.environ['PIPER_SPEED'] = '1.0'
        
        from application.composition_root import create_pdf_service_from_env
        
        print("🏗️ Creating PDF service with Piper TTS...")
        service = create_pdf_service_from_env()
        
        print("✅ PDF service created successfully with Piper TTS")
        
        # Test getting TTS engine info
        if hasattr(service, 'tts_engine'):
            engine_type = type(service.tts_engine).__name__
            print(f"🎵 TTS Engine: {engine_type}")
            
            if "Piper" in engine_type:
                print("✅ Piper TTS successfully integrated")
                return True
            else:
                print(f"⚠️ Expected Piper TTS, got {engine_type}")
                return False
        else:
            print("⚠️ TTS engine not accessible from service")
            return False
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def run_all_tests():
    """Run complete Piper TTS test suite"""
    print("🚀 Starting Piper TTS Test Suite")
    print("=" * 50)
    
    tests = [
        ("Installation Check", test_piper_installation),
        ("Basic Functionality", test_piper_basic_functionality),
        ("SSML Conversion", test_piper_ssml_conversion),
        ("Academic Content", test_piper_academic_content),
        ("System Integration", test_piper_integration_with_system)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Piper TTS is ready to use.")
        print("\n💡 Next steps:")
        print("   1. Update your .env file: TTS_ENGINE=piper")
        print("   2. Try processing a PDF with your application")
        print("   3. Listen to the generated audio files")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        print("\n🔧 Troubleshooting:")
        print("   1. Make sure Piper TTS is installed: pip install piper-tts")
        print("   2. Check that 'piper --version' works in your terminal")
        print("   3. Ensure you have internet connection for model downloads")
    
    return passed == total

if __name__ == "__main__":
    # Allow running individual tests
    import sys
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        
        if test_name == "install":
            test_piper_installation()
        elif test_name == "basic":
            test_piper_basic_functionality()
        elif test_name == "ssml":
            test_piper_ssml_conversion()
        elif test_name == "academic":
            test_piper_academic_content()
        elif test_name == "integration":
            test_piper_integration_with_system()
        else:
            print("Available tests: install, basic, ssml, academic, integration")
    else:
        run_all_tests()