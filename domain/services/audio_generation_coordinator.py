# domain/services/audio_generation_coordinator.py
import asyncio
import os
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor

from domain.interfaces import ITTSEngine, IFileManager, IAudioProcessor
from domain.services.rate_limiting_service import RateLimitingService
from domain.services.audio_file_processor import AudioFileProcessor
from domain.services.audio_processor import AudioProcessor
from domain.errors import Result, audio_generation_error

class AudioGenerationCoordinator:
    """Coordinates async audio generation with proper separation of concerns"""
    
    def __init__(self, tts_engine: ITTSEngine, file_manager: IFileManager, 
                 audio_processor: IAudioProcessor, max_concurrent_requests: int = 4):
        self.tts_engine = tts_engine
        self.file_manager = file_manager
        self.rate_limiter = RateLimitingService(max_concurrent_requests)
        self.file_processor = AudioFileProcessor(file_manager, audio_processor)
        
        # Get engine-specific settings
        self.base_delay = self.rate_limiter.get_base_delay_for_engine(tts_engine)
        
        print(f"AudioGenerationCoordinator: Initialized with max {max_concurrent_requests} concurrent requests")
        print(f"AudioGenerationCoordinator: Base delay: {self.base_delay}s, FFmpeg: {audio_processor.check_ffmpeg_availability()}")
    
    async def generate_audio_async(self, text_chunks: List[str], output_name: str, 
                                 output_dir: str) -> Tuple[List[str], Optional[str]]:
        """Generate audio files concurrently with intelligent rate limiting"""
        
        if not self.tts_engine:
            print("AudioGenerationCoordinator: No TTS engine available")
            return [], None
            
        os.makedirs(output_dir, exist_ok=True)
        
        # Filter and validate chunks
        valid_chunks = self._filter_valid_chunks(text_chunks)
        
        if not valid_chunks:
            print("AudioGenerationCoordinator: No valid chunks to process")
            return [], None
        
        print(f"AudioGenerationCoordinator: Processing {len(valid_chunks)} valid chunks out of {len(text_chunks)} total")
        
        # Generate audio files concurrently
        audio_files = await self._generate_audio_files(valid_chunks, output_name, output_dir)
        
        # Create combined MP3 if we have files
        combined_mp3 = None
        if audio_files:
            result = self.file_processor.create_combined_mp3(audio_files, output_name, output_dir)
            if result.is_success:
                combined_mp3 = result.value
            else:
                print(f"AudioGenerationCoordinator: Failed to create combined MP3: {result.error}")
        
        return audio_files, combined_mp3
    
    def _filter_valid_chunks(self, text_chunks: List[str]) -> List[Tuple[int, str]]:
        """Filter out invalid or empty text chunks"""
        valid_chunks = []
        for i, text_chunk in enumerate(text_chunks):
            if (text_chunk.strip() and 
                not text_chunk.startswith("Error") and 
                not text_chunk.startswith("LLM cleaning skipped")):
                valid_chunks.append((i, text_chunk))
        return valid_chunks
    
    async def _generate_audio_files(self, valid_chunks: List[Tuple[int, str]], 
                                   output_name: str, output_dir: str) -> List[str]:
        """Generate audio files for all valid chunks concurrently"""
        
        # Create tasks for each chunk
        tasks = []
        for i, (original_index, text_chunk) in enumerate(valid_chunks):
            filename = f"{output_name}_part{i+1:02d}.wav"
            task = self._generate_single_audio_file(text_chunk, filename, output_dir, i+1)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful results
        audio_files = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"AudioGenerationCoordinator: Task {i+1} failed: {result}")
            elif result and os.path.exists(result):
                audio_files.append(result)
        
        return audio_files
    
    async def _generate_single_audio_file(self, text_chunk: str, filename: str, 
                                        output_dir: str, chunk_number: int) -> Optional[str]:
        """Generate a single audio file with rate limiting and retry logic"""
        
        async def generate_operation():
            """The actual audio generation operation"""
            # Use thread pool for blocking TTS operations
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                future = executor.submit(self._call_tts_engine, text_chunk)
                audio_result = await loop.run_in_executor(None, lambda: future.result())
            
            if audio_result.is_failure:
                raise Exception(f"TTS generation failed: {audio_result.error}")
            
            # Save the audio file
            save_result = self.file_processor.save_audio_chunk(
                audio_result.value, output_dir, filename
            )
            
            if save_result.is_failure:
                raise Exception(f"Failed to save audio: {save_result.error}")
            
            return save_result.value
        
        try:
            result = await self.rate_limiter.execute_with_retry(
                generate_operation, 
                max_retries=3, 
                base_delay=self.base_delay
            )
            
            print(f"AudioGenerationCoordinator: Generated chunk {chunk_number}: {filename}")
            return result
            
        except Exception as e:
            print(f"AudioGenerationCoordinator: Failed to generate chunk {chunk_number}: {e}")
            return None
    
    def _call_tts_engine(self, text: str) -> Result[bytes]:
        """Call TTS engine (blocking operation)"""
        try:
            # The TTS engine now returns Result[bytes] directly
            return self.tts_engine.generate_audio_data(text)
        except Exception as e:
            return Result.failure(audio_generation_error(f"TTS engine call failed: {str(e)}"))
    
    def sync_generate_audio(self, text_chunks: List[str], output_name: str, 
                           output_dir: str) -> Tuple[List[str], Optional[str]]:
        """Synchronous wrapper for backward compatibility"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                self.generate_audio_async(text_chunks, output_name, output_dir)
            )
        finally:
            loop.close()