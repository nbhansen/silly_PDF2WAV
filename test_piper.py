#!/usr/bin/env python3
"""Test script to verify Piper TTS works correctly"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from application.config.system_config import SystemConfig
from domain.factories.service_factory import create_tts_engine
from infrastructure.tts.piper_tts_provider import PIPER_AVAILABLE, PIPER_METHOD

def test_piper():
    print("=== Piper TTS Test ===")
    print(f"PIPER_AVAILABLE: {PIPER_AVAILABLE}")
    print(f"PIPER_METHOD: {PIPER_METHOD}")
    
    if not PIPER_AVAILABLE:
        print("ERROR: Piper is not available!")
        return False
    
    # Load config
    print("\n1. Loading configuration...")
    try:
        config = SystemConfig.from_yaml('config.yaml')
        print(f"   Config loaded. TTS Engine: {config.tts_engine.value}")
    except Exception as e:
        print(f"   ERROR loading config: {e}")
        return False
    
    # Create TTS engine
    print("\n2. Creating TTS engine...")
    try:
        tts_engine = create_tts_engine(config)
        print(f"   TTS engine created: {type(tts_engine).__name__}")
    except Exception as e:
        print(f"   ERROR creating TTS engine: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test text generation
    print("\n3. Testing audio generation...")
    test_text = "Hello, this is a test of the Piper text to speech system."
    
    # Also test with SSML to ensure stripping works
    print("\n4. Testing SSML stripping...")
    ssml_text = 'Hello <break time="2s"/> this is a test with <emphasis level="strong">SSML tags</emphasis>.'
    
    try:
        result = tts_engine.generate_audio_data(test_text)
        if result.is_success:
            audio_data = result.value
            print(f"   SUCCESS! Generated {len(audio_data)} bytes of audio")
            
            # Save test output
            output_path = "test_piper_output.wav"
            with open(output_path, 'wb') as f:
                f.write(audio_data)
            print(f"   Saved test audio to: {output_path}")
            
            # Test SSML text
            print("\n4. Testing SSML stripping...")
            ssml_result = tts_engine.generate_audio_data(ssml_text)
            if ssml_result.is_success:
                print(f"   SUCCESS! SSML text processed correctly")
                ssml_output_path = "test_piper_ssml_output.wav"
                with open(ssml_output_path, 'wb') as f:
                    f.write(ssml_result.value)
                print(f"   Saved SSML test audio to: {ssml_output_path}")
            else:
                print(f"   SSML test FAILED: {ssml_result.error.message}")
                
            return True
        else:
            print(f"   FAILED: {result.error.message}")
            print(f"   Error code: {result.error.code}")
            return False
    except Exception as e:
        print(f"   ERROR during generation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_piper()
    sys.exit(0 if success else 1)