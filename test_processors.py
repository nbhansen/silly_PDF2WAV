# test_processors.py (add debug prints)
#!/usr/bin/env python3
"""
Simple test script to verify the new processor classes work correctly
before integrating into the Flask app.
"""

import os
import sys

print("DEBUG: Script starting...")
print("DEBUG: About to import processors...")

try:
    from processors import PDFProcessor
    print("DEBUG: Successfully imported PDFProcessor")
except Exception as e:
    print(f"DEBUG: Failed to import PDFProcessor: {e}")
    sys.exit(1)

print("DEBUG: Defining test functions...")

def test_basic_processing():
    """Test the basic PDF processing pipeline"""
    print("=== Testing PDF Processing Pipeline ===")
    
    # Configuration - use lighter settings for testing
    GOOGLE_API_KEY = "your_actual_api_key_here"  # Replace with your key
    TEST_PDF_PATH = "test_files/sample.pdf"  # Put a test PDF here
    OUTPUT_NAME = "test_output"
    
    # Check if test file exists
    if not os.path.exists(TEST_PDF_PATH):
        print(f"❌ Test PDF not found: {TEST_PDF_PATH}")
        print("Please create a 'test_files' folder and add a sample PDF")
        return False
    
    try:
        # Initialize processor with lighter TTS for testing
        print("🔧 Initializing PDFProcessor...")
        processor = PDFProcessor(
            google_api_key=GOOGLE_API_KEY,
            tts_engine="gtts",  # Use gtts for lighter testing
            tts_config={"lang": "en", "tld": "com"}
        )
        print("✅ Processor initialized")
        
        # Process the PDF
        print(f"📄 Processing PDF: {TEST_PDF_PATH}")
        result = processor.process_pdf(TEST_PDF_PATH, OUTPUT_NAME)
        
        # Check results
        if result.success:
            print("✅ Processing successful!")
            print(f"🎵 Audio saved to: {result.audio_path}")
            if result.debug_info:
                print("📊 Debug info:")
                for key, value in result.debug_info.items():
                    print(f"   {key}: {value}")
            return True
        else:
            print(f"❌ Processing failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_components():
    """Test components with minimal setup"""
    print("\n=== Testing Simple Components ===")
    
    # Test just the imports and basic instantiation
    print("🔍 Testing component imports...")
    
    try:
        from text_processing import OCRExtractor, TextCleaner
        print("✅ text_processing imports successful")
        
        ocr = OCRExtractor()
        print("✅ OCRExtractor created")
        
        cleaner = TextCleaner("dummy_key")  # Will work without real key
        print("✅ TextCleaner created")
        
    except Exception as e:
        print(f"❌ Component test failed: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        from audio_generation import TTSGenerator
        print("✅ audio_generation import successful")
        
        tts = TTSGenerator("gtts", {"lang": "en"})
        print("✅ TTSGenerator created")
        
    except Exception as e:
        print(f"❌ TTS component test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all tests"""
    print("🚀 Starting processor tests...\n")
    
    # Create test directories
    os.makedirs("test_files", exist_ok=True)
    os.makedirs("audio_outputs", exist_ok=True)
    
    # Run simple tests first
    test_simple_components()
    
    # Only run full test if we have a PDF
    if os.path.exists("test_files/sample.pdf"):
        success = test_basic_processing()
        print(f"\n{'='*50}")
        if success:
            print("🎉 Full processing test PASSED")
        else:
            print("❌ Full processing test FAILED")
        print("="*50)
    else:
        print("\n⚠️  No test PDF found. Create 'test_files/sample.pdf' to run full test.")

print("DEBUG: About to run main...")

if __name__ == "__main__":
    print("DEBUG: In main block...")
    main()
    print("DEBUG: Script completed.")