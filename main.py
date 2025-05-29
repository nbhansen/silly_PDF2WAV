from processors import PDFProcessor

def main():
    processor = PDFProcessor(
        google_api_key="your_key",
        tts_engine="coqui",
        tts_config={"model_name": "tts_models/en/vctk/vits"}
    )
    
    result = processor.process_pdf("path/to/file.pdf", "output_name")
    if result.success:
        print(f"Audio saved: {result.audio_path}")
    else:
        print(f"Error: {result.error}")