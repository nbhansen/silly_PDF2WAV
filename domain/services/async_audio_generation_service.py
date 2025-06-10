# domain/services/async_audio_generation_service.py
import asyncio
import aiofiles
import os
import time
import subprocess
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
from domain.interfaces import ITTSEngine

class AsyncAudioGenerationService:
    """Async version of AudioGenerationService for better performance with rate-limited APIs"""
    
    def __init__(self, tts_engine: ITTSEngine, max_concurrent_requests: int = 4):
        self.tts_engine = tts_engine
        self.max_concurrent_requests = max_concurrent_requests
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.ffmpeg_available = self._check_ffmpeg()
        
        # Rate limiting settings based on engine type
        self.base_delay = self._get_base_delay_for_engine(tts_engine)
        
        print(f"AsyncAudioGenerationService: Initialized with max {max_concurrent_requests} concurrent requests")
        print(f"AsyncAudioGenerationService: Base delay: {self.base_delay}s, FFmpeg: {self.ffmpeg_available}")
    
    async def generate_audio_async(self, text_chunks: List[str], output_name: str, 
                                 output_dir: str) -> Tuple[List[str], Optional[str]]:
        """Generate audio files concurrently with intelligent rate limiting"""
        
        if not self.tts_engine:
            print("AsyncAudioGenerationService: No TTS engine available")
            return [], None
            
        os.makedirs(output_dir, exist_ok=True)
        
        # Filter valid chunks and create tasks
        valid_chunks = []
        for i, text_chunk in enumerate(text_chunks):
            if text_chunk.strip() and not text_chunk.startswith("Error") and not text_chunk.startswith("LLM cleaning skipped"):
                valid_chunks.append((i, text_chunk))
        
        if not valid_chunks:
            print("AsyncAudioGenerationService: No valid chunks to process")
            return [], None
        
        print(f"AsyncAudioGenerationService: Processing {len(valid_chunks)} valid chunks out of {len(text_chunks)} total")
        
        # Create tasks for each valid chunk
        tasks = []
        for i, (original_index, text_chunk) in enumerate(valid_chunks):
            chunk_output_name = f"{output_name}_part{original_index+1:02d}"
            task = self._generate_single_audio_with_retry(
                text_chunk, chunk_output_name, output_dir, 
                original_index+1, len(text_chunks), i
            )
            tasks.append(task)
        
        print(f"AsyncAudioGenerationService: Starting {len(tasks)} concurrent audio generation tasks")
        
        # Execute tasks concurrently with rate limiting
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful results
        generated_files = []
        for i, result in enumerate(results):
            if isinstance(result, str) and result:  # Successful filename
                generated_files.append(result)
                print(f"AsyncAudioGenerationService: Task {i+1} completed successfully: {result}")
            elif isinstance(result, Exception):
                print(f"AsyncAudioGenerationService: Task {i+1} failed with error: {result}")
            else:
                print(f"AsyncAudioGenerationService: Task {i+1} returned no result")
        
        print(f"AsyncAudioGenerationService: Generated {len(generated_files)} audio files successfully")
        
        # Create combined MP3
        combined_mp3 = None
        if len(generated_files) >= 1:
            # Sort files to maintain order
            generated_files.sort()
            if len(generated_files) == 1:
                combined_mp3 = await self._convert_single_to_mp3_async(generated_files[0], output_name, output_dir)
            else:
                combined_mp3 = await self._create_combined_mp3_async(generated_files, output_name, output_dir)
        
        return generated_files, combined_mp3
    
    async def _generate_single_audio_with_retry(self, text_chunk: str, chunk_output_name: str, 
                                              output_dir: str, chunk_num: int, total_chunks: int,
                                              task_index: int) -> Optional[str]:
        """Generate audio for a single chunk with retry logic and rate limiting"""
        
        max_retries = 3
        base_retry_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                # Apply rate limiting with jitter based on task index
                async with self.semaphore:
                    # Add staggered delay to prevent thundering herd
                    initial_delay = self.base_delay + (task_index * 0.5)
                    if attempt > 0:
                        # Exponential backoff for retries
                        retry_delay = base_retry_delay * (2 ** (attempt - 1))
                        initial_delay += retry_delay
                        print(f"AsyncAudioGenerationService: Retry {attempt} for chunk {chunk_num}, waiting {retry_delay:.1f}s")
                    
                    if initial_delay > 0:
                        await asyncio.sleep(initial_delay)
                    
                    print(f"AsyncAudioGenerationService: Generating audio for chunk {chunk_num}/{total_chunks}: {chunk_output_name} (attempt {attempt + 1})")
                    
                    # Run TTS generation in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    with ThreadPoolExecutor() as executor:
                        audio_data = await loop.run_in_executor(
                            executor, 
                            self.tts_engine.generate_audio_data, 
                            text_chunk
                        )
                    
                    if audio_data:
                        ext = self.tts_engine.get_output_format()
                        audio_filename = f"{chunk_output_name}.{ext}"
                        audio_filepath = os.path.join(output_dir, audio_filename)
                        
                        # Use async file writing
                        async with aiofiles.open(audio_filepath, "wb") as f:
                            await f.write(audio_data)
                        
                        print(f"AsyncAudioGenerationService: Successfully generated {audio_filename}")
                        return audio_filename
                    else:
                        print(f"AsyncAudioGenerationService: Failed to generate audio data for chunk {chunk_num} (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            continue
                        else:
                            return None
                            
            except Exception as e:
                error_str = str(e)
                print(f"AsyncAudioGenerationService: Error generating audio for chunk {chunk_num} (attempt {attempt + 1}): {e}")
                
                # Check if this is a rate limit error
                if self._is_rate_limit_error(error_str):
                    if attempt < max_retries - 1:
                        # Extract retry delay from error if available
                        suggested_delay = self._extract_retry_delay(error_str)
                        retry_delay = suggested_delay if suggested_delay > 0 else (base_retry_delay * (2 ** attempt))
                        print(f"AsyncAudioGenerationService: Rate limit detected, waiting {retry_delay:.1f}s before retry")
                        await asyncio.sleep(retry_delay)
                        continue
                
                # For non-rate-limit errors, simple exponential backoff
                if attempt < max_retries - 1:
                    retry_delay = base_retry_delay * (2 ** attempt)
                    await asyncio.sleep(retry_delay)
                    continue
        
        print(f"AsyncAudioGenerationService: All {max_retries} attempts failed for chunk {chunk_num}")
        return None
    
    async def _convert_single_to_mp3_async(self, audio_file: str, base_name: str, output_dir: str) -> Optional[str]:
        """Async version of MP3 conversion"""
        if not self.ffmpeg_available:
            print("AsyncAudioGenerationService: FFmpeg not available for MP3 conversion")
            return None
        
        try:
            input_file = os.path.abspath(os.path.join(output_dir, audio_file))
            mp3_filename = f"{base_name}_combined.mp3"
            mp3_path = os.path.abspath(os.path.join(output_dir, mp3_filename))
            
            if not os.path.exists(input_file):
                print(f"AsyncAudioGenerationService: Input file not found: {input_file}")
                return None
            
            cmd = [
                'ffmpeg', '-y',
                '-i', input_file,
                '-c:a', 'libmp3lame',
                '-b:a', '128k',
                '-ar', '22050',
                mp3_path
            ]
            
            print(f"AsyncAudioGenerationService: Converting single file to MP3: {mp3_filename}")
            success = await self._run_subprocess_async(cmd)
            
            if success and os.path.exists(mp3_path):
                # Fix metadata for single files too
                print("AsyncAudioGenerationService: Fixing MP3 metadata for single file...")
                await self._fix_mp3_metadata(mp3_path)
                
                file_size = os.path.getsize(mp3_path) / (1024 * 1024)
                print(f"AsyncAudioGenerationService: Successfully converted to MP3: {mp3_filename} ({file_size:.1f} MB)")
                return mp3_filename
            else:
                print("AsyncAudioGenerationService: MP3 conversion failed")
                return None
                
        except Exception as e:
            print(f"AsyncAudioGenerationService: Error converting single file to MP3: {e}")
            return None
    
    async def _create_combined_mp3_async(self, audio_files: List[str], base_name: str, output_dir: str) -> Optional[str]:
        """Async version of MP3 combination"""
        if not self.ffmpeg_available or len(audio_files) < 2:
            print("AsyncAudioGenerationService: Cannot create combined MP3 (FFmpeg unavailable or insufficient files)")
            return None
        
        try:
            input_files = [os.path.abspath(os.path.join(output_dir, f)) for f in audio_files]
            combined_filename = f"{base_name}_combined.mp3"
            combined_path = os.path.abspath(os.path.join(output_dir, combined_filename))
            
            # Check that all input files exist
            missing_files = [f for f in input_files if not os.path.exists(f)]
            if missing_files:
                print(f"AsyncAudioGenerationService: Missing input files: {missing_files}")
                return None
            
            # Create concat file
            concat_file = combined_path + ".concat.txt"
            async with aiofiles.open(concat_file, 'w', encoding='utf-8') as f:
                for input_file in input_files:
                    # Escape paths properly for FFmpeg
                    escaped_path = input_file.replace('\\', '/').replace("'", "'\"'\"'")
                    await f.write(f"file '{escaped_path}'\n")
            
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:a', 'libmp3lame',
                '-b:a', '128k',
                '-ar', '22050',
                '-movflags', '+faststart',  # Optimize for streaming/web playback
                '-metadata', 'title=Combined Audio',  # Add proper metadata
                combined_path
            ]
            
            print(f"AsyncAudioGenerationService: Combining {len(input_files)} files into MP3: {combined_filename}")
            success = await self._run_subprocess_async(cmd)
            
            # Clean up concat file
            try:
                os.remove(concat_file)
            except:
                pass
            
            if success and os.path.exists(combined_path):
                # Fix metadata duration issue with a second pass
                print("AsyncAudioGenerationService: Fixing MP3 metadata...")
                await self._fix_mp3_metadata(combined_path)
                
                file_size = os.path.getsize(combined_path) / (1024 * 1024)
                print(f"AsyncAudioGenerationService: Successfully created combined MP3: {combined_filename} ({file_size:.1f} MB)")
                return combined_filename
            else:
                print("AsyncAudioGenerationService: Combined MP3 creation failed")
                return None
                
        except Exception as e:
            print(f"AsyncAudioGenerationService: Error creating combined MP3: {e}")
            return None
    
    async def _fix_mp3_metadata(self, mp3_path: str) -> bool:
        """Fix MP3 metadata duration issues by re-encoding with proper headers"""
        try:
            temp_path = mp3_path + ".temp.mp3"
            
            # Re-encode to fix metadata issues
            cmd = [
                'ffmpeg', '-y',
                '-i', mp3_path,
                '-c:a', 'copy',  # Copy audio stream (no re-encoding)
                '-map_metadata', '0',  # Copy all metadata
                '-write_xing', '1',  # Force write proper Xing header
                temp_path
            ]
            
            success = await self._run_subprocess_async(cmd)
            
            if success and os.path.exists(temp_path):
                # Replace original with fixed version
                os.replace(temp_path, mp3_path)
                print("AsyncAudioGenerationService: MP3 metadata fixed successfully")
                return True
            else:
                # Clean up temp file if it exists
                try:
                    os.remove(temp_path)
                except:
                    pass
                print("AsyncAudioGenerationService: MP3 metadata fix failed")
                return False
                
        except Exception as e:
            print(f"AsyncAudioGenerationService: Error fixing MP3 metadata: {e}")
            return False
    
    async def _run_subprocess_async(self, cmd: List[str]) -> bool:
        """Run subprocess asynchronously"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
            
            if process.returncode != 0:
                print(f"AsyncAudioGenerationService: Subprocess failed with return code {process.returncode}")
                if stderr:
                    print(f"AsyncAudioGenerationService: Subprocess stderr: {stderr.decode()[:500]}")
            
            return process.returncode == 0
            
        except asyncio.TimeoutError:
            print("AsyncAudioGenerationService: Subprocess timed out")
            return False
        except Exception as e:
            print(f"AsyncAudioGenerationService: Subprocess error: {e}")
            return False
    
    def _get_base_delay_for_engine(self, engine: ITTSEngine) -> float:
        """Get base delay based on engine type"""
        if not engine:
            return 0.0
        
        engine_class_name = engine.__class__.__name__.lower()
        
        if "gemini" in engine_class_name:
            return 0.5  # Reduced from 1.0 since we're using much smaller chunks
        elif "openai" in engine_class_name:
            return 0.5
        elif "elevenlabs" in engine_class_name:
            return 1.0
        else:
            return 0.1  # Minimal delay for local engines like Coqui, gTTS
    
    def _is_rate_limit_error(self, error_str: str) -> bool:
        """Check if error indicates rate limiting"""
        rate_limit_indicators = ["429", "RESOURCE_EXHAUSTED", "quota", "rate limit", "too many requests"]
        return any(indicator in error_str.lower() for indicator in rate_limit_indicators)
    
    def _extract_retry_delay(self, error_str: str) -> float:
        """Extract suggested retry delay from error message"""
        try:
            import re
            # Look for patterns like 'retryDelay': '16s'
            match = re.search(r"'retryDelay':\s*'(\d+)s'", error_str)
            if match:
                return float(match.group(1))
        except:
            pass
        return 0.0
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False


# Wrapper function to use async service in sync context
def run_async_audio_generation(text_chunks: List[str], output_name: str, 
                              output_dir: str, tts_engine: ITTSEngine,
                              max_concurrent: int = 4) -> Tuple[List[str], Optional[str]]:
    """Wrapper to run async audio generation in sync context"""
    
    async def _async_wrapper():
        service = AsyncAudioGenerationService(tts_engine, max_concurrent)
        return await service.generate_audio_async(text_chunks, output_name, output_dir)
    
    # Handle different event loop scenarios
    try:
        # Check if we're already in an event loop
        loop = asyncio.get_running_loop()
        # If we are, we need nest_asyncio to run another async function
        import nest_asyncio
        nest_asyncio.apply()
        
        # Create a new task in the current loop
        task = loop.create_task(_async_wrapper())
        # This is a bit complex - we need to block until the task completes
        # but we can't use run_until_complete in a running loop
        
        # Alternative approach: use asyncio.run_coroutine_threadsafe
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _async_wrapper())
            return future.result()
            
    except RuntimeError:
        # No event loop running, we can use asyncio.run
        return asyncio.run(_async_wrapper())