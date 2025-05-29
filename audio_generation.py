# audio_generation.py
import os
import re
from typing import Optional, List
from tts_utils import get_tts_processor

class TTSGenerator:
    """Handles text-to-speech generation"""
    
    def __init__(self, engine: str, config: dict):
        self.processor = get_tts_processor(engine, **config)
        self.engine_name = engine
        self.chunk_size = 5000  # Characters per audio chunk
    
    def generate(self, text: str, output_name: str, output_dir: str = "audio_outputs") -> Optional[str]:
        """Generate audio from text"""
        if not self.processor or not text.strip():
            print("TTSGenerator: No processor or empty text")
            return None
            
        if text.startswith("Error") or text.startswith("LLM cleaning skipped"):
            print("TTSGenerator: Skipping audio generation due to upstream error")
            return None
            
        os.makedirs(output_dir, exist_ok=True)
        
        # Split text for TTS
        chunks = self._split_for_tts(text)
        print(f"TTSGenerator: Split into {len(chunks)} chunks")
        
        if len(chunks) == 1:
            # Single chunk - direct generation
            return self.processor.generate_audio_file(text, output_name, output_dir)
        
        # Multiple chunks - generate and combine
        return self._generate_and_combine(chunks, output_name, output_dir)
    
    def _split_for_tts(self, text: str) -> List[str]:
        """Split text optimally for TTS"""
        if len(text) <= self.chunk_size:
            return [text]
            
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = ""
        
        for sentence in sentences:
            if len(current) + len(sentence) > self.chunk_size:
                if current:
                    chunks.append(current.strip())
                current = sentence
            else:
                current += " " + sentence if current else sentence
                
        if current:
            chunks.append(current.strip())
            
        return chunks
    
    def _generate_and_combine(self, chunks: List[str], output_name: str, output_dir: str) -> Optional[str]:
        """Generate audio for each chunk and combine"""
        try:
            from pydub import AudioSegment
        except ImportError:
            print("TTSGenerator: pydub not available, cannot combine chunks")
            return None
            
        temp_files = []
        try:
            # Generate individual chunks
            for i, chunk in enumerate(chunks):
                print(f"TTSGenerator: Processing chunk {i+1}/{len(chunks)}")
                temp_name = f"{output_name}_chunk_{i}"
                temp_file = self.processor.generate_audio_file(chunk, temp_name, output_dir)
                if temp_file:
                    temp_files.append(os.path.join(output_dir, temp_file))
            
            if not temp_files:
                print("TTSGenerator: No audio chunks generated")
                return None
            
            # Combine audio files
            print("TTSGenerator: Combining audio chunks")
            combined = AudioSegment.empty()
            for temp_file in temp_files:
                combined += AudioSegment.from_file(temp_file)
            
            # Save combined file
            ext = self.processor.get_output_extension()
            final_file = f"{output_name}.{ext}"
            final_path = os.path.join(output_dir, final_file)
            combined.export(final_path, format=ext)
            
            # Cleanup temp files
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass
                    
            print(f"TTSGenerator: Combined audio saved as {final_file}")
            return final_file
            
        except Exception as e:
            print(f"TTSGenerator: Error combining audio: {e}")
            return None