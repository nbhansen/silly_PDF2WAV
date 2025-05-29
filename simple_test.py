#!/usr/bin/env python3
print("Starting simple test...")

# Test 1: Can we import the TTS utils?
try:
    from tts_utils import get_tts_processor
    print("✅ tts_utils import successful")
except Exception as e:
    print(f"❌ tts_utils import failed: {e}")

# Test 2: Can we create a simple TTS processor?
try:
    processor = get_tts_processor("gtts", lang="en")
    if processor:
        print("✅ gTTS processor created successfully")
    else:
        print("❌ gTTS processor creation returned None")
except Exception as e:
    print(f"❌ gTTS processor creation failed: {e}")

# Test 3: Can we import our new modules?
try:
    from text_processing import TextCleaner
    cleaner = TextCleaner("dummy")
    print("✅ TextCleaner import and creation successful")
except Exception as e:
    print(f"❌ TextCleaner failed: {e}")

try:
    from audio_generation import TTSGenerator
    tts_gen = TTSGenerator("gtts", {"lang": "en"})
    print("✅ TTSGenerator import and creation successful")
except Exception as e:
    print(f"❌ TTSGenerator failed: {e}")

try:
    from processors import PDFProcessor
    print("✅ PDFProcessor import successful")
except Exception as e:
    print(f"❌ PDFProcessor import failed: {e}")

print("Simple test completed.")