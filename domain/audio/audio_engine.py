# domain/audio/audio_engine.py - Unified Audio Processing Engine
"""
Consolidated audio engine that unifies audio generation, processing, and coordination.
Replaces: AudioGenerationService, AudioGenerationCoordinator, AudioProcessor, AudioFileProcessor
"""

import os
import time
import asyncio
from typing import List, Optional, Tuple
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

from ..interfaces import ITTSEngine, IFileManager
from ..models import TimedAudioResult, TextSegment, TimingMetadata
from ..errors import Result, audio_generation_error


class IAudioEngine(ABC):
    """Unified interface for all audio operations"""
    
    @abstractmethod
    def generate_with_timing(self, text_chunks: List[str], output_filename: str) -> TimedAudioResult:
        """Generate audio with timing data from text chunks"""
        pass
    
    @abstractmethod
    def generate_audio_async(self, text_chunks: List[str], output_name: str, output_dir: str) -> Tuple[List[str], Optional[str]]:
        """Generate audio files concurrently with coordination"""
        pass
    
    @abstractmethod
    def process_audio_file(self, file_path: str) -> Result[float]:
        """Process audio file and return duration"""
        pass
    
    @abstractmethod
    def combine_audio_files(self, file_paths: List[str], output_path: str) -> Result[str]:
        """Combine multiple audio files into one"""
        pass


class AudioEngine(IAudioEngine):
    """
    Unified audio engine that consolidates all audio-related operations.
    High cohesion: All audio operations in one place.
    Low coupling: Depends only on abstractions (ITTSEngine, IFileManager).
    """
    
    def __init__(
        self,
        tts_engine: ITTSEngine,
        file_manager: IFileManager,
        timing_engine: 'ITimingEngine',
        max_concurrent: int = 4
    ):
        self.tts_engine = tts_engine
        self.file_manager = file_manager
        self.timing_engine = timing_engine
        self.max_concurrent = max_concurrent
        self.base_delay = self._get_base_delay_for_engine()
    
    def generate_with_timing(self, text_chunks: List[str], output_filename: str) -> TimedAudioResult:
        """
        Main entry point for audio generation with timing.
        Delegates to timing engine for strategy-specific processing.
        """
        return self.timing_engine.generate_with_timing(text_chunks, output_filename)
    
    def process_audio_file(self, file_path: str) -> Result[float]:
        """Get audio file duration using ffprobe or fallback"""
        try:
            import subprocess
            
            # Try ffprobe first (most accurate)
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                duration = float(result.stdout.strip())
                return Result.success(duration)
            
            # Fallback to file size estimation
            file_size = os.path.getsize(file_path)
            # Rough estimation: 1 second per 44KB for 22kHz audio
            estimated_duration = file_size / (22050 * 2)  # 22kHz * 2 bytes per sample
            return Result.success(estimated_duration)
            
        except Exception as e:
            return Result.failure(f"Failed to get audio duration: {e}")
    
    def combine_audio_files(self, file_paths: List[str], output_path: str) -> Result[str]:
        """Combine multiple audio files using ffmpeg"""
        if not file_paths:
            return Result.failure("No audio files to combine")
        
        if len(file_paths) == 1:
            # Single file - just copy
            try:
                import shutil
                shutil.copy2(file_paths[0], output_path)
                return Result.success(output_path)
            except Exception as e:
                return Result.failure(f"Failed to copy single audio file: {e}")
        
        try:
            import subprocess
            
            # Create temporary file list for ffmpeg
            list_file = output_path + '.list'
            with open(list_file, 'w') as f:
                for file_path in file_paths:
                    f.write(f"file '{file_path}'\n")
            
            # Use ffmpeg to concatenate
            cmd = [
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_file,
                '-c', 'copy', output_path, '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            
            # Clean up list file
            try:
                os.remove(list_file)
            except:
                pass
            
            if result.returncode == 0:
                return Result.success(output_path)
            else:
                return Result.failure(f"ffmpeg failed: {result.stderr.decode()}")
                
        except Exception as e:
                return Result.failure(f"Failed to combine audio files: {e}")
    
    async def generate_audio_async(self, text_chunks: List[str], output_name: str, output_dir: str) -> Tuple[List[str], Optional[str]]:
        """Generate audio files concurrently with intelligent coordination"""
        if not self.tts_engine:
            print("AudioEngine: No TTS engine available")
            return [], None
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Filter and validate chunks
        valid_chunks = self._filter_valid_chunks(text_chunks)
        
        if not valid_chunks:
            print("AudioEngine: No valid chunks to process")
            return [], None
        
        print(f"AudioEngine: Processing {len(valid_chunks)} valid chunks concurrently")
        
        # Generate audio files concurrently
        audio_files = await self._generate_audio_files_concurrent(valid_chunks, output_name, output_dir)
        
        # Create combined MP3 if we have files
        combined_mp3 = None
        if audio_files:
            combined_path = os.path.join(output_dir, f"{output_name}_combined.mp3")
            result = self.combine_audio_files(audio_files, combined_path)
            if result.is_success:
                combined_mp3 = os.path.basename(result.value)
            else:
                print(f"AudioEngine: Failed to create combined MP3: {result.error}")
        
        return [os.path.basename(f) for f in audio_files], combined_mp3
    
    def sync_generate_audio(self, text_chunks: List[str], output_name: str, output_dir: str) -> Tuple[List[str], Optional[str]]:
        """Synchronous wrapper for backward compatibility"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                self.generate_audio_async(text_chunks, output_name, output_dir)
            )
        finally:
            loop.close()
    
    def check_ffmpeg_availability(self) -> bool:
        """Check if ffmpeg is available"""
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _filter_valid_chunks(self, text_chunks: List[str]) -> List[Tuple[int, str]]:
        """Filter out invalid or empty text chunks"""
        valid_chunks = []
        for i, text_chunk in enumerate(text_chunks):
            if (text_chunk.strip() and 
                not text_chunk.startswith("Error") and 
                not text_chunk.startswith("LLM cleaning skipped")):
                valid_chunks.append((i, text_chunk))
        return valid_chunks
    
    async def _generate_audio_files_concurrent(self, valid_chunks: List[Tuple[int, str]], output_name: str, output_dir: str) -> List[str]:
        """Generate audio files for all valid chunks concurrently"""
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Create tasks for each chunk
        tasks = []
        for i, (original_index, text_chunk) in enumerate(valid_chunks):
            filename = f"{output_name}_part{i + 1:02d}.wav"
            task = self._generate_single_audio_file(semaphore, text_chunk, filename, output_dir, i + 1)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful results
        audio_files = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"AudioEngine: Task {i + 1} failed: {result}")
            elif result and os.path.exists(result):
                audio_files.append(result)
        
        return audio_files
    
    async def _generate_single_audio_file(self, semaphore: asyncio.Semaphore, text_chunk: str, filename: str, output_dir: str, chunk_number: int) -> Optional[str]:
        """Generate a single audio file with rate limiting"""
        async with semaphore:
            try:
                # Apply rate limiting
                if self.base_delay > 0:
                    await asyncio.sleep(self.base_delay)
                
                # Use thread pool for blocking TTS operations
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(self._call_tts_engine, text_chunk)
                    audio_result = await loop.run_in_executor(None, lambda: future.result())
                
                if audio_result.is_failure:
                    print(f"AudioEngine: TTS failed for chunk {chunk_number}: {audio_result.error}")
                    return None
                
                # Save the audio file
                output_path = os.path.join(output_dir, filename)
                save_path = self.file_manager.save_output_file(audio_result.value, filename)
                
                if save_path:
                    print(f"AudioEngine: Generated chunk {chunk_number}: {filename}")
                    return save_path
                else:
                    print(f"AudioEngine: Failed to save chunk {chunk_number}")
                    return None
                
            except Exception as e:
                print(f"AudioEngine: Failed to generate chunk {chunk_number}: {e}")
                return None
    
    def _call_tts_engine(self, text: str) -> Result[bytes]:
        """Call TTS engine (blocking operation)"""
        try:
            return self.tts_engine.generate_audio_data(text)
        except Exception as e:
            return Result.failure(audio_generation_error(f"TTS engine call failed: {str(e)}"))
    
    def _get_base_delay_for_engine(self) -> float:
        """Get base delay for rate limiting based on TTS engine"""
        engine_name = self.tts_engine.__class__.__name__.lower()
        
        if 'gemini' in engine_name:
            return 0.8  # Gemini has stricter rate limits
        elif 'piper' in engine_name:
            return 0.1  # Piper is local, minimal delay
        else:
            return 0.5  # Default for unknown engines