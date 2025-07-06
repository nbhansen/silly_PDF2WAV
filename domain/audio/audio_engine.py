# domain/audio/audio_engine.py - Unified Audio Processing Engine
"""Consolidated audio engine that unifies audio generation, processing, and coordination.
Replaces: AudioGenerationService, AudioGenerationCoordinator, AudioProcessor, AudioFileProcessor.
"""

from abc import ABC, abstractmethod
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from ..errors import Result, audio_generation_error
from ..interfaces import IFileManager, ITTSEngine
from ..models import TimedAudioResult
from ..text.chunking_strategy import ChunkingMode, ChunkingService, create_chunking_service

if TYPE_CHECKING:
    from .timing_engine import ITimingEngine


class IAudioEngine(ABC):
    """Unified interface for all audio operations."""

    @abstractmethod
    def generate_with_timing(self, text_chunks: list[str], output_filename: str) -> TimedAudioResult:
        """Generate audio with timing data from text chunks."""

    @abstractmethod
    def generate_simple_audio(self, text_chunks: list[str], output_filename: str) -> TimedAudioResult:
        """Generate audio without timing complexity - for regular uploads."""

    @abstractmethod
    async def generate_audio_async(
        self, text_chunks: list[str], output_name: str, output_dir: str
    ) -> tuple[list[str], Optional[str]]:
        """Generate audio files concurrently with coordination."""

    @abstractmethod
    def process_audio_file(self, file_path: str) -> Result[float]:
        """Process audio file and return duration."""

    @abstractmethod
    def combine_audio_files(self, file_paths: list[str], output_path: str) -> Result[str]:
        """Combine multiple audio files into one."""


class AudioEngine(IAudioEngine):
    """Unified audio engine that consolidates all audio-related operations.
    High cohesion: All audio operations in one place.
    Low coupling: Depends only on abstractions (ITTSEngine, IFileManager).
    """

    def __init__(
        self,
        tts_engine: ITTSEngine,
        file_manager: IFileManager,
        timing_engine: "ITimingEngine",
        max_concurrent: int = 4,
        audio_target_chunk_size: int = 2000,
        audio_max_chunk_size: int = 3000,
        chunking_service: Optional[ChunkingService] = None,
    ):
        self.tts_engine = tts_engine
        self.file_manager = file_manager
        self.timing_engine = timing_engine
        self.max_concurrent = max_concurrent
        self.audio_target_chunk_size = audio_target_chunk_size
        self.audio_max_chunk_size = audio_max_chunk_size
        self.chunking_service = chunking_service or create_chunking_service(ChunkingMode.SENTENCE_BASED)
        self.base_delay = self._get_base_delay_for_engine()

        print("🔍 AudioEngine: Initialized with chunk sizes:")
        print(f"  - audio_target_chunk_size: {self.audio_target_chunk_size}")
        print(f"  - audio_max_chunk_size: {self.audio_max_chunk_size}")

    def generate_with_timing(self, text_chunks: list[str], output_filename: str) -> TimedAudioResult:
        """Main entry point for audio generation with timing.
        Delegates to timing engine for strategy-specific processing.
        """
        return self.timing_engine.generate_with_timing(text_chunks, output_filename)

    def generate_simple_audio(self, text_chunks: list[str], output_filename: str) -> TimedAudioResult:
        """Simple audio generation without timing complexity - bypasses TimingEngine.
        Perfect for regular uploads that don't need timing data.
        """
        print(f"AudioEngine: Generating simple audio for {len(text_chunks)} chunks")
        print(f"🔍 AudioEngine: Chunk sizes: {[len(chunk) for chunk in text_chunks]}")

        if not text_chunks:
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

        # Use chunking service for optimal text splitting
        max_chunk_size = self.audio_target_chunk_size
        print(f"🔍 AudioEngine: Using max_chunk_size = {max_chunk_size} (from self.audio_target_chunk_size)")

        processed_chunks = self.chunking_service.process_chunks(text_chunks, max_chunk_size)
        print(f"AudioEngine: Processing {len(processed_chunks)} chunks (max size: {max_chunk_size} chars)")
        print(f"🔍 AudioEngine: After rechunking, chunk sizes: {[len(chunk) for chunk in processed_chunks]}")

        # Generate audio using new async interface
        print("AudioEngine: Using async processing for simple audio generation")
        audio_chunks = self._generate_chunks_with_new_async_interface(processed_chunks)

        if not audio_chunks:
            print("AudioEngine: No successful audio chunks generated")
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

        try:
            # Combine audio chunks
            combined_audio = self._combine_wav_chunks(audio_chunks)
            audio_data = combined_audio

            if not audio_data:
                return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

            # Save audio file as WAV first (since TTS engines typically generate WAV)
            temp_wav_filename = f"{output_filename}_temp.wav"
            temp_wav_path = self.file_manager.save_output_file(audio_data, temp_wav_filename)

            if not temp_wav_path:
                return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

            # Convert WAV to MP3 using ffmpeg
            mp3_filename = f"{output_filename}_simple.mp3"
            mp3_path = Path(self.file_manager.get_output_dir()) / mp3_filename

            conversion_result = self._convert_wav_to_mp3(temp_wav_path, str(mp3_path))

            # Clean up temporary WAV file
            try:
                Path(temp_wav_path).unlink()
            except (OSError, FileNotFoundError):
                # Ignore file cleanup errors - temporary files may already be removed
                pass

            if conversion_result.is_success:
                print(f"AudioEngine: Simple audio generated and converted to MP3: {mp3_filename}")
                return TimedAudioResult(
                    audio_files=[mp3_filename],
                    combined_mp3=mp3_filename,
                    timing_data=None,  # No timing data needed for simple generation
                )
            else:
                print(f"AudioEngine: MP3 conversion failed: {conversion_result.error}")
                return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

        except Exception as e:
            print(f"AudioEngine: Simple audio generation failed: {e}")
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

    def _generate_chunks_with_new_async_interface(self, processed_chunks: list[str]) -> list[bytes]:
        """Generate audio chunks using the new async interface with true parallelism."""
        import asyncio

        # Create and run async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            audio_chunks = loop.run_until_complete(self._process_chunks_async(processed_chunks))
            return audio_chunks
        finally:
            loop.close()

    async def _process_chunks_async(self, processed_chunks: list[str]) -> list[bytes]:
        """Actually async method that processes chunks in parallel."""
        print(f"AudioEngine: Starting parallel processing of {len(processed_chunks)} chunks")

        # Create tasks for parallel execution
        tasks = []
        for i, chunk in enumerate(processed_chunks):
            if not chunk.strip():
                continue
            task = self._process_single_chunk_async(chunk, i + 1, len(processed_chunks))
            tasks.append(task)

        # Execute all tasks concurrently with rate limiting
        semaphore = asyncio.Semaphore(self.max_concurrent)  # Use existing max_concurrent setting
        limited_tasks = [self._limited_chunk_processing(semaphore, task) for task in tasks]

        results = await asyncio.gather(*limited_tasks, return_exceptions=True)

        # Filter successful results (immutable) - cast is safe because we filter out non-bytes
        audio_chunks: list[bytes] = [
            result
            for result in results
            if not isinstance(result, Exception) and result is not None and isinstance(result, bytes)
        ]

        # Handle failed chunks logging
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"AudioEngine: Chunk {i+1} failed with exception: {result}")

        print(f"AudioEngine: Successfully processed {len(audio_chunks)} chunks in parallel")
        return audio_chunks

    async def _limited_chunk_processing(self, semaphore: asyncio.Semaphore, task: Any) -> Optional[bytes]:
        """Apply semaphore limiting to chunk processing."""
        async with semaphore:
            result = await task
            # Add small delay for rate limiting
            await asyncio.sleep(self.base_delay)
            return result  # type: ignore[no-any-return]

    async def _process_single_chunk_async(self, chunk: str, chunk_num: int, total_chunks: int) -> Optional[bytes]:
        """Process a single chunk asynchronously."""
        print(f"AudioEngine: Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} chars) - TRUE ASYNC")

        try:
            # Use the new async interface
            result = await self.tts_engine.generate_audio_data_async(chunk)
            if result.is_success and result.value:
                return result.value
            else:
                print(
                    f"AudioEngine: Chunk {chunk_num} failed: {result.error if result.is_failure else 'No audio data'}"
                )
                return None
        except Exception as e:
            print(f"AudioEngine: Exception processing chunk {chunk_num}: {e}")
            return None

    def process_audio_file(self, file_path: str) -> Result[float]:
        """Get audio file duration using ffprobe or fallback."""
        try:
            import subprocess

            # Validate file path for security
            path_obj = Path(file_path)
            if not path_obj.is_file() or path_obj.is_symlink():
                return Result.failure(audio_generation_error(f"Invalid or unsafe file path: {file_path}"))

            # Try ffprobe first (most accurate)
            cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", file_path]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                duration = float(result.stdout.strip())
                return Result.success(duration)

            # Fallback to file size estimation
            file_size = Path(file_path).stat().st_size
            # Rough estimation: 1 second per 44KB for 22kHz audio
            estimated_duration = file_size / (22050 * 2)  # 22kHz * 2 bytes per sample
            return Result.success(estimated_duration)

        except Exception as e:
            return Result.failure(audio_generation_error(f"Failed to get audio duration: {e}"))

    def _combine_wav_chunks(self, audio_chunks: list[bytes]) -> bytes:
        """Combine multiple WAV audio chunks into a single WAV file."""
        try:
            import io
            import wave

            if not audio_chunks:
                return b""

            if len(audio_chunks) == 1:
                return audio_chunks[0]

            # Read the first chunk to get audio parameters
            first_chunk = io.BytesIO(audio_chunks[0])
            with wave.open(first_chunk, "rb") as first_wav:
                params = first_wav.getparams()

            # Create output buffer
            output_buffer = io.BytesIO()

            # Write combined WAV file
            with wave.open(output_buffer, "wb") as output_wav:
                output_wav.setparams(params)

                # Append audio data from each chunk
                for chunk_data in audio_chunks:
                    chunk_buffer = io.BytesIO(chunk_data)
                    with wave.open(chunk_buffer, "rb") as chunk_wav:
                        frames = chunk_wav.readframes(chunk_wav.getnframes())
                        output_wav.writeframes(frames)

            return output_buffer.getvalue()

        except Exception as e:
            print(f"AudioEngine: Error combining audio chunks: {e}")
            # Fallback: return the first chunk if combination fails
            return audio_chunks[0] if audio_chunks else b""

    def combine_audio_files(self, file_paths: list[str], output_path: str) -> Result[str]:
        """Combine multiple audio files using ffmpeg."""
        if not file_paths:
            return Result.failure(audio_generation_error("No audio files to combine"))

        if len(file_paths) == 1:
            return self._handle_single_file_copy(file_paths[0], output_path)

        validation_result = self._validate_input_files(file_paths)
        if validation_result.is_failure:
            assert validation_result.error is not None
            return Result.failure(validation_result.error)

        return self._execute_ffmpeg_combination(file_paths, output_path)

    def _handle_single_file_copy(self, file_path: str, output_path: str) -> Result[str]:
        """Handle the special case of combining a single file by copying it."""
        try:
            import shutil

            shutil.copy2(file_path, output_path)
            return Result.success(output_path)
        except Exception as e:
            return Result.failure(audio_generation_error(f"Failed to copy single audio file: {e}"))

    def _validate_input_files(self, file_paths: list[str]) -> Result[None]:
        """Validate all input file paths for security and existence."""
        for file_path in file_paths:
            path_obj = Path(file_path)
            if not path_obj.is_file() or path_obj.is_symlink():
                return Result.failure(audio_generation_error(f"Invalid or unsafe file path: {file_path}"))
        return Result.success(None)

    def _execute_ffmpeg_combination(self, file_paths: list[str], output_path: str) -> Result[str]:
        """Execute ffmpeg command to combine multiple audio files."""
        try:
            import subprocess

            list_file_result = self._prepare_ffmpeg_command(file_paths, output_path)
            if list_file_result.is_failure:
                assert list_file_result.error is not None
                return Result.failure(list_file_result.error)

            list_file = list_file_result.value
            assert list_file is not None  # Should not be None after success check

            cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path, "-y"]

            result = subprocess.run(cmd, capture_output=True, timeout=300)

            # Clean up list file
            try:
                Path(list_file).unlink()
            except (OSError, FileNotFoundError):
                # Ignore file cleanup errors - temporary files may already be removed
                pass

            if result.returncode == 0:
                return Result.success(output_path)
            else:
                return Result.failure(audio_generation_error(f"ffmpeg failed: {result.stderr.decode()}"))

        except Exception as e:
            return Result.failure(audio_generation_error(f"Failed to combine audio files: {e}"))

    def _prepare_ffmpeg_command(self, file_paths: list[str], output_path: str) -> Result[str]:
        """Create temporary file list for ffmpeg concatenation."""
        try:
            list_file = output_path + ".list"
            with Path(list_file).open("w") as f:
                for file_path in file_paths:
                    f.write(f"file '{file_path}'\n")
            return Result.success(list_file)
        except Exception as e:
            return Result.failure(audio_generation_error(f"Failed to create file list: {e}"))

    async def generate_audio_async(
        self, text_chunks: list[str], output_name: str, output_dir: str
    ) -> tuple[list[str], Optional[str]]:
        """Generate audio files concurrently with intelligent coordination."""
        if not self.tts_engine:
            print("AudioEngine: No TTS engine available")
            return [], None

        Path(output_dir).mkdir(parents=True, exist_ok=True)

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
            combined_path = Path(output_dir) / f"{output_name}_combined.mp3"
            result = self.combine_audio_files(audio_files, combined_path)
            if result.is_success and result.value:
                combined_mp3 = Path(result.value).name
            else:
                print(f"AudioEngine: Failed to create combined MP3: {result.error}")

        return [Path(f).name for f in audio_files], combined_mp3

    def _filter_valid_chunks(self, text_chunks: list[str]) -> list[tuple[int, str]]:
        """Filter out invalid or empty text chunks."""
        valid_chunks = []
        for i, text_chunk in enumerate(text_chunks):
            if (
                text_chunk.strip()
                and not text_chunk.startswith("Error")
                and not text_chunk.startswith("LLM cleaning skipped")
            ):
                valid_chunks.append((i, text_chunk))
        return valid_chunks

    async def _generate_audio_files_concurrent(
        self, valid_chunks: list[tuple[int, str]], output_name: str, output_dir: str
    ) -> list[str]:
        """Generate audio files for all valid chunks concurrently."""
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)

        # Create tasks for each chunk
        tasks = []
        for i, (_, text_chunk) in enumerate(valid_chunks):
            filename = f"{output_name}_part{i + 1:02d}.wav"
            task = self._generate_single_audio_file(semaphore, text_chunk, filename, output_dir, i + 1)
            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results
        audio_files: list[str] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"AudioEngine: Task {i + 1} failed: {result}")
            elif isinstance(result, str) and result and Path(result).exists():
                audio_files.append(result)

        return audio_files

    async def _generate_single_audio_file(
        self, semaphore: asyncio.Semaphore, text_chunk: str, filename: str, output_dir: str, chunk_number: int
    ) -> Optional[str]:
        """Generate a single audio file with rate limiting."""
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

                # Validate audio data before saving
                if not audio_result.value:
                    print(f"AudioEngine: No audio data for chunk {chunk_number}")
                    return None

                # Save the audio file
                Path(output_dir) / filename
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
        """Call TTS engine (blocking operation)."""
        try:
            return self.tts_engine.generate_audio_data(text)
        except Exception as e:
            return Result.failure(audio_generation_error(f"TTS engine call failed: {e!s}"))

    def _get_base_delay_for_engine(self) -> float:
        """Get base delay for rate limiting based on TTS engine."""
        engine_name = self.tts_engine.__class__.__name__.lower()

        if "gemini" in engine_name:
            return 0.8  # Gemini has stricter rate limits
        elif "piper" in engine_name:
            return 0.1  # Piper is local, minimal delay
        else:
            return 0.5  # Default for unknown engines

    def _convert_wav_to_mp3(self, wav_path: str, mp3_path: str) -> Result[str]:
        """Convert WAV file to MP3 using ffmpeg."""
        try:
            import os
            import subprocess

            # Validate input file path for security
            if not Path(wav_path).is_file() or Path(wav_path).is_symlink():
                return Result.failure(audio_generation_error(f"Invalid or unsafe input file path: {wav_path}"))

            # Use ffmpeg to convert WAV to MP3 with good quality
            cmd = [
                "ffmpeg",
                "-i",
                wav_path,
                "-codec:a",
                "libmp3lame",
                "-b:a",
                "128k",  # Good quality bitrate
                "-ar",
                "22050",  # Sample rate
                mp3_path,
                "-y",  # Overwrite if exists
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                return Result.success(mp3_path)
            else:
                return Result.failure(audio_generation_error(f"ffmpeg conversion failed: {result.stderr}"))

        except Exception as e:
            return Result.failure(audio_generation_error(f"MP3 conversion failed: {e}"))
