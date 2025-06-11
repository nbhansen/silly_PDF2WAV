# domain/services/audio_generation_service.py - Fixed to respect engine preferences
import os
import re
import subprocess
from typing import Optional, List, Tuple
from domain.interfaces import AudioGenerator, ITTSEngine

class AudioGenerationService(AudioGenerator):
    """Enhanced audio generation with proper sync/async selection based on engine preferences."""
    
    def __init__(self, tts_engine: ITTSEngine):
        self.tts_engine = tts_engine
        self.chunk_size = 20000  # Characters per audio chunk
        self.ffmpeg_available = self._check_ffmpeg()
        
        # Read performance settings from environment
        self.use_async = self._check_async_support() and self._async_enabled_in_env()
        self.max_concurrent_requests = int(os.getenv('MAX_CONCURRENT_TTS_REQUESTS', '4'))
        
        print(f"AudioGenerationService: FFmpeg available: {self.ffmpeg_available}")
        print(f"AudioGenerationService: Async support: {self.use_async}")
        print(f"AudioGenerationService: Max concurrent: {self.max_concurrent_requests}")
    
    def generate_audio(self, text_chunks: List[str], output_name: str, output_dir: str, 
                      tts_engine: Optional[ITTSEngine] = None) -> Tuple[List[str], Optional[str]]:
        """
        Generate audio with intelligent processing strategy selection
        """
        engine_to_use = tts_engine or self.tts_engine
        
        if not engine_to_use:
            print("AudioGenerationService: No TTS engine available")
            return [], None
        
        # Filter valid chunks
        valid_chunks = [c for c in text_chunks if c.strip() and not c.startswith("Error") and not c.startswith("LLM cleaning skipped")]
        chunk_count = len(valid_chunks)
        
        print(f"AudioGenerationService: Processing {chunk_count} valid chunks from {len(text_chunks)} total")
        
        if chunk_count <= 1:
            print("AudioGenerationService: Using single-chunk processing")
            return self._generate_audio_sync(text_chunks, output_name, output_dir, engine_to_use)
        
        # Decide processing strategy based on engine preference and settings
        if self._should_use_async(engine_to_use, chunk_count):
            return self._generate_audio_async_wrapper(text_chunks, output_name, output_dir, engine_to_use)
        else:
            return self._generate_audio_optimized_sync(text_chunks, output_name, output_dir, engine_to_use)
    
    def _should_use_async(self, engine: ITTSEngine, chunk_count: int) -> bool:
        """Determine if async processing should be used - FIXED to respect engine preferences"""
        if not self.use_async:
            print(f"AudioGenerationService: Async disabled in configuration")
            return False
            
        # Check if user forces async
        if self._force_async():
            print(f"AudioGenerationService: Async processing forced by configuration")
            return True
        
        # Get engine name for logging
        engine_name = engine.__class__.__name__
            
        # RESPECT ENGINE PREFERENCE FIRST - This is the key fix!
        if hasattr(engine, 'prefers_sync_processing') and engine.prefers_sync_processing():
            print(f"AudioGenerationService: {engine_name} prefers sync processing")
            # For sync-preferring engines (like Piper), only use async for very large jobs
            if chunk_count > 10:
                print(f"AudioGenerationService: Large job ({chunk_count} chunks), overriding sync preference")
                return True
            else:
                print(f"AudioGenerationService: Using sync processing as preferred by {engine_name}")
                return False
        
        # For async-preferring engines (like Gemini), use async for multiple chunks
        if chunk_count >= 2:
            print(f"AudioGenerationService: Using async processing for {chunk_count} chunks with {engine_name}")
            return True
        
        print(f"AudioGenerationService: Using sync processing for single chunk with {engine_name}")
        return False
    
    def _async_enabled_in_env(self) -> bool:
        """Check if async is enabled in environment"""
        return os.getenv('ENABLE_ASYNC_AUDIO', 'True').lower() in ('true', '1', 'yes')
    
    def _force_async(self) -> bool:
        """Check if user explicitly forces async mode"""
        return os.getenv('FORCE_ASYNC_AUDIO', 'False').lower() in ('true', '1', 'yes')
    
    def _generate_audio_sync(self, text_chunks: List[str], output_name: str, output_dir: str, 
                            engine_to_use: ITTSEngine) -> Tuple[List[str], Optional[str]]:
        """Synchronous processing - reliable for all engines, especially local ones like Piper"""
        os.makedirs(output_dir, exist_ok=True)
        generated_files = []
        
        print(f"AudioGenerationService: Using synchronous processing with {engine_to_use.__class__.__name__}")
        
        for i, text_chunk in enumerate(text_chunks):
            if not text_chunk.strip():
                print(f"AudioGenerationService: Skipping empty chunk {i+1}")
                continue
                
            if text_chunk.startswith("Error") or text_chunk.startswith("LLM cleaning skipped"):
                print(f"AudioGenerationService: Skipping error chunk {i+1}")
                continue
            
            chunk_output_name = f"{output_name}_part{i+1:02d}"
            print(f"AudioGenerationService: Generating audio for chunk {i+1}/{len(text_chunks)}: {chunk_output_name}")
            
            try:
                audio_data = engine_to_use.generate_audio_data(text_chunk)
                if audio_data:
                    ext = engine_to_use.get_output_format()
                    audio_filename = f"{chunk_output_name}.{ext}"
                    audio_filepath = os.path.join(output_dir, audio_filename)
                    
                    with open(audio_filepath, "wb") as f:
                        f.write(audio_data)
                    
                    generated_files.append(audio_filename)
                    print(f"AudioGenerationService: Generated {audio_filename} ({len(audio_data)} bytes)")
                else:
                    print(f"AudioGenerationService: Failed to generate audio data for chunk {i+1}")
            except Exception as e:
                print(f"AudioGenerationService: Error generating audio for chunk {i+1}: {e}")
        
        return self._finalize_audio_files(generated_files, output_name, output_dir)
    
    def _generate_audio_optimized_sync(self, text_chunks: List[str], output_name: str, output_dir: str, 
                                      engine_to_use: ITTSEngine) -> Tuple[List[str], Optional[str]]:
        """Optimized sync processing with intelligent delays for rate-limited engines"""
        os.makedirs(output_dir, exist_ok=True)
        generated_files = []
        
        # Add intelligent delays for rate-limited engines
        delay_between_requests = self._get_optimal_delay(engine_to_use)
        
        print(f"AudioGenerationService: Using optimized sync processing with {engine_to_use.__class__.__name__}")
        if delay_between_requests > 0:
            print(f"AudioGenerationService: Rate limiting enabled: {delay_between_requests}s between requests")
        
        for i, text_chunk in enumerate(text_chunks):
            if not text_chunk.strip() or text_chunk.startswith("Error") or text_chunk.startswith("LLM cleaning skipped"):
                continue
            
            # Add delay between requests for rate-limited engines
            if i > 0 and delay_between_requests > 0:
                import time
                print(f"AudioGenerationService: Rate limiting delay: {delay_between_requests}s")
                time.sleep(delay_between_requests)
            
            chunk_output_name = f"{output_name}_part{i+1:02d}"
            
            try:
                audio_data = engine_to_use.generate_audio_data(text_chunk)
                if audio_data:
                    ext = engine_to_use.get_output_format()
                    audio_filename = f"{chunk_output_name}.{ext}"
                    audio_filepath = os.path.join(output_dir, audio_filename)
                    
                    with open(audio_filepath, "wb") as f:
                        f.write(audio_data)
                    
                    generated_files.append(audio_filename)
                    print(f"AudioGenerationService: Generated {audio_filename} ({len(audio_data)} bytes)")
                    
            except Exception as e:
                error_str = str(e)
                if self._is_rate_limit_error(error_str):
                    print(f"AudioGenerationService: Rate limit hit, implementing exponential backoff")
                    delay_between_requests = min(delay_between_requests * 2, 30)  # Cap at 30s
                else:
                    print(f"AudioGenerationService: Error generating audio for chunk {i+1}: {e}")
        
        return self._finalize_audio_files(generated_files, output_name, output_dir)
    
    def _generate_audio_async_wrapper(self, text_chunks: List[str], output_name: str, output_dir: str, 
                                     engine_to_use: ITTSEngine) -> Tuple[List[str], Optional[str]]:
        """Wrapper for async processing with fallback to sync"""
        try:
            # Import the async function from the async module
            from .async_audio_generation_service import run_async_audio_generation
            print(f"AudioGenerationService: Using async processing with {self.max_concurrent_requests} concurrent requests")
            return run_async_audio_generation(
                text_chunks, output_name, output_dir, engine_to_use, self.max_concurrent_requests
            )
        except ImportError as e:
            print(f"AudioGenerationService: Async support not available ({e}), falling back to optimized sync")
            return self._generate_audio_optimized_sync(text_chunks, output_name, output_dir, engine_to_use)
        except Exception as e:
            print(f"AudioGenerationService: Async processing failed ({e}), falling back to optimized sync")
            return self._generate_audio_optimized_sync(text_chunks, output_name, output_dir, engine_to_use)
    
    def _finalize_audio_files(self, generated_files: List[str], output_name: str, 
                             output_dir: str) -> Tuple[List[str], Optional[str]]:
        """Common logic for finalizing audio files"""
        print(f"AudioGenerationService: Generated {len(generated_files)} individual audio files")
        
        combined_mp3 = None
        if len(generated_files) >= 1:
            if len(generated_files) == 1:
                combined_mp3 = self._convert_single_to_mp3(generated_files[0], output_name, output_dir)
            else:
                combined_mp3 = self._create_combined_mp3(generated_files, output_name, output_dir)
        
        return generated_files, combined_mp3
    
    def _is_rate_limited_engine(self, engine: ITTSEngine) -> bool:
        """Check if engine is likely to have rate limits"""
        engine_class_name = engine.__class__.__name__.lower()
        rate_limited_engines = ["gemini", "openai", "elevenlabs"]
        return any(name in engine_class_name for name in rate_limited_engines)
    
    def _get_optimal_delay(self, engine: ITTSEngine) -> float:
        """Get optimal delay between requests for engine type"""
        if not self._is_rate_limited_engine(engine):
            return 0.0
        
        engine_class_name = engine.__class__.__name__.lower()
        
        if "gemini" in engine_class_name:
            return 2.0  # Start with 2s for Gemini in sync mode
        elif "openai" in engine_class_name:
            return 1.0
        else:
            return 1.5  # Conservative default
    
    def _is_rate_limit_error(self, error_str: str) -> bool:
        """Check if error indicates rate limiting"""
        rate_limit_indicators = ["429", "RESOURCE_EXHAUSTED", "quota", "rate limit", "too many requests"]
        return any(indicator in error_str.lower() for indicator in rate_limit_indicators)
    
    def _check_async_support(self) -> bool:
        """Check if async dependencies are available"""
        try:
            import asyncio
            import aiofiles
            import nest_asyncio
            return True
        except ImportError:
            return False
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available on the system"""
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def _convert_single_to_mp3(self, audio_file: str, base_name: str, output_dir: str) -> Optional[str]:
        """Convert a single audio file to MP3 format"""
        if not self.ffmpeg_available:
            print("AudioGenerationService: FFmpeg not available, cannot convert to MP3")
            return None
        
        try:
            # Prepare file paths
            input_file = os.path.abspath(os.path.join(output_dir, audio_file))
            mp3_filename = f"{base_name}_combined.mp3"
            mp3_path = os.path.abspath(os.path.join(output_dir, mp3_filename))
            
            print(f"AudioGenerationService: Converting single file to MP3: {mp3_filename}")
            
            # Check that input file exists
            if not os.path.exists(input_file):
                print(f"AudioGenerationService: Input file does not exist: {input_file}")
                return None
            
            # FFmpeg command to convert to MP3
            cmd = [
                'ffmpeg', '-y',  # -y to overwrite output file
                '-i', input_file,
                '-c:a', 'libmp3lame',  # MP3 codec
                '-b:a', '128k',        # 128 kbps bitrate
                '-ar', '22050',        # 22.05 kHz sample rate (good for speech)
                mp3_path
            ]
            
            # Run FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(mp3_path):
                file_size = os.path.getsize(mp3_path) / (1024 * 1024)  # MB
                print(f"AudioGenerationService: Successfully converted to MP3: {mp3_filename} ({file_size:.1f} MB)")
                return mp3_filename
            else:
                print(f"AudioGenerationService: Failed to convert to MP3: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"AudioGenerationService: Error converting single file to MP3: {e}")
            return None
        
    def _create_combined_mp3(self, audio_files: List[str], base_name: str, output_dir: str) -> Optional[str]:
        """Combine multiple audio files into a single compressed MP3"""
        if not self.ffmpeg_available:
            print("AudioGenerationService: FFmpeg not available, cannot create combined MP3")
            return None
        
        if len(audio_files) < 2:
            print("AudioGenerationService: Less than 2 files, no need to combine")
            return None
        
        try:
            # Prepare file paths - Use absolute paths to avoid path confusion
            input_files = []
            for f in audio_files:
                if os.path.isabs(f):
                    input_files.append(f)
                else:
                    input_files.append(os.path.abspath(os.path.join(output_dir, f)))
            
            combined_filename = f"{base_name}_combined.mp3"
            combined_path = os.path.abspath(os.path.join(output_dir, combined_filename))
            
            print(f"AudioGenerationService: Combining {len(input_files)} files into {combined_filename}")
            
            # Check that all input files exist
            missing_files = [f for f in input_files if not os.path.exists(f)]
            if missing_files:
                print(f"AudioGenerationService: Missing input files: {missing_files}")
                return None
            
            # Method 1: Try concat demuxer (fastest, works if all files have same format)
            success = self._combine_with_concat_demuxer(input_files, combined_path)
            
            if not success:
                print("AudioGenerationService: Concat demuxer failed, trying concat filter")
                # Method 2: Use concat filter (slower but more compatible)
                success = self._combine_with_concat_filter(input_files, combined_path)
            
            if success and os.path.exists(combined_path):
                file_size = os.path.getsize(combined_path) / (1024 * 1024)  # MB
                print(f"AudioGenerationService: Successfully created combined MP3: {combined_filename} ({file_size:.1f} MB)")
                return combined_filename
            else:
                print("AudioGenerationService: Failed to create combined MP3")
                return None
                
        except Exception as e:
            print(f"AudioGenerationService: Error creating combined MP3: {e}")
            return None
    
    def _combine_with_concat_demuxer(self, input_files: List[str], output_path: str) -> bool:
        """Combine files using FFmpeg concat demuxer (fast method)"""
        try:
            # Create a temporary file list for FFmpeg
            concat_file = output_path + ".concat.txt"
            
            with open(concat_file, 'w', encoding='utf-8') as f:
                for input_file in input_files:
                    # Ensure input_file is a string, not bytes
                    if isinstance(input_file, bytes):
                        input_file = input_file.decode('utf-8')
                    
                    # Use absolute paths and proper escaping
                    abs_path = os.path.abspath(str(input_file))  # Ensure string
                    # For Windows compatibility, use forward slashes and escape properly
                    escaped_path = abs_path.replace('\\', '/').replace("'", "'\"'\"'")
                    f.write(f"file '{escaped_path}'\n")
            
            # FFmpeg command for concat demuxer
            cmd = [
                'ffmpeg', '-y',  # -y to overwrite output file
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),  # Ensure string
                '-c:a', 'libmp3lame',  # MP3 codec
                '-b:a', '128k',        # 128 kbps bitrate
                '-ar', '22050',        # 22.05 kHz sample rate (good for speech)
                str(output_path)       # Ensure string
            ]
            
            # Run FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Clean up temp file
            try:
                os.remove(concat_file)
            except:
                pass
            
            if result.returncode == 0:
                return True
            else:
                print(f"AudioGenerationService: Concat demuxer error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"AudioGenerationService: Concat demuxer exception: {e}")
            return False
    
    def _combine_with_concat_filter(self, input_files: List[str], output_path: str) -> bool:
        """Combine files using FFmpeg concat filter (compatible method)"""
        try:
            # Build FFmpeg command with concat filter
            cmd = ['ffmpeg', '-y']
            
            # Add input files with absolute paths
            for input_file in input_files:
                abs_path = os.path.abspath(input_file)
                cmd.extend(['-i', abs_path])
            
            # Add filter complex for concatenation
            filter_inputs = ''.join([f'[{i}:0]' for i in range(len(input_files))])
            filter_concat = f'{filter_inputs}concat=n={len(input_files)}:v=0:a=1[out]'
            
            cmd.extend([
                '-filter_complex', filter_concat,
                '-map', '[out]',
                '-c:a', 'libmp3lame',  # MP3 codec
                '-b:a', '128k',        # 128 kbps bitrate
                '-ar', '22050',        # 22.05 kHz sample rate
                output_path
            ])
            
            # Run FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return True
            else:
                print(f"AudioGenerationService: Concat filter error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"AudioGenerationService: Concat filter exception: {e}")
            return False