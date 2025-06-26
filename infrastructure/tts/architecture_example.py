# Example of how the shared TextSegmenter works with different TTS engines

"""
Example showing how TextSegmenter provides universal text processing
while each TTS engine handles its specific capabilities
"""

# === Gemini TTS (Rich SSML Support) ===
class GeminiTTSProvider(ITimestampedTTSEngine):
    def __init__(self, ...):
        self.text_segmenter = TextSegmenter(base_wpm=155)  # Shared utilities
        # Gemini-specific: rate limiting, voice config, etc.
    
    def _generate_audio(self, text: str) -> bytes:
        # Gemini-specific: Could add styling if needed
        # styled_text = f"Say naturally: {text}"  # Gemini supports this
        return self._call_gemini_api(text)


# === Piper TTS (Limited SSML Support) ===
class PiperTTSProvider(ITTSEngine):
    def __init__(self, ...):
        self.text_segmenter = TextSegmenter(base_wpm=155)  # Same shared utilities
        # Piper-specific: model path, voice config, etc.
    
    def _generate_audio(self, text: str) -> bytes:
        # Piper-specific: Direct text-to-speech, no styling
        # clean_text = self.text_segmenter.clean_text_for_tts(text)
        return self._call_piper_model(text)


# === ElevenLabs (Advanced SSML Support) ===
class ElevenLabsTTSProvider(ITimestampedTTSEngine):
    def __init__(self, ...):
        self.text_segmenter = TextSegmenter(base_wpm=155)  # Same shared utilities
        # ElevenLabs-specific: API key, voice ID, emotion controls, etc.
    
    def _generate_audio(self, text: str) -> bytes:
        # ElevenLabs-specific: Could add rich SSML, emotion, etc.
        # ssml_text = self._add_elevenlabs_ssml(text)
        return self._call_elevenlabs_api(text)


# === Usage Example ===
def process_document_with_any_engine(tts_engine, document_text: str):
    """
    This works with any TTS engine because they all use TextSegmenter
    for the universal text processing parts
    """
    
    # All engines can use the shared text processing
    if hasattr(tts_engine, 'text_segmenter'):
        # Split into manageable chunks
        chunks = tts_engine.text_segmenter.chunk_text(document_text, max_chunk_size=800)
        
        for chunk in chunks:
            # Each engine handles audio generation in its own way
            audio_result = tts_engine.generate_audio_data(chunk)
            
            # But duration calculation is universal
            duration = tts_engine.text_segmenter.calculate_duration(chunk)
            
            print(f"Generated {duration:.1f}s of audio")
