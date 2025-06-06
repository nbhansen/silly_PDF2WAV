# infrastructure/tts/audio_generator_adapter.py
from typing import List, Optional, Tuple
from domain.models import AudioGenerator
from audio_generation import TTSGenerator
from tts_utils import TTSConfig

class AudioGeneratorAdapter(AudioGenerator):
    """Adapter for existing TTSGenerator to implement domain interface"""
    
    def __init__(self, engine: str, config: TTSConfig):
        self._generator = TTSGenerator(engine, config)
    
    def generate_audio(self, text_chunks: List[str], output_name: str, output_dir: str) -> Tuple[List[str], Optional[str]]:
        return self._generator.generate_from_chunks(
            text_chunks, 
            output_name, 
            output_dir,
            create_combined_mp3=True
        )