# domain/audio/audio_engine.py - Audio Processing Engine with Result[T] pattern
"""Audio engine using Result[T] pattern for type-safe error handling.

No exceptions thrown - all errors returned as Result[T].
"""

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Awaitable, Coroutine
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union

from ..errors import Result, audio_generation_error

logger = logging.getLogger(__name__)
from ..interfaces import IFileManager, ITTSEngine
from ..models import TimedAudioResult
from ..text.chunking_strategy import ChunkingMode, IChunkingStrategy, create_chunking_strategy

if TYPE_CHECKING:
    from .timing_engine import ITimingEngine


class IAudioEngine(ABC):
    """Interface for audio operations using Result[T] pattern."""

    @abstractmethod
    def generate_with_timing(self, text_chunks: list[str], output_filename: str) -> Result[TimedAudioResult]:
        """Generate audio with timing data from text chunks."""

    @abstractmethod
    def generate_simple_audio(self, text_chunks: list[str], output_filename: str) -> Result[TimedAudioResult]:
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
    """Audio engine using Result[T] pattern for all operations.

    Pure functions with no exceptions - all errors returned as Result[T].
    """

    def __init__(
        self,
        tts_engine: ITTSEngine,
        file_manager: IFileManager,
        timing_engine: "ITimingEngine",
        max_concurrent: int = 4,
        audio_target_chunk_size: int = 2000,
        audio_max_chunk_size: int = 3000,
        enable_async: bool = True,
        chunking_strategy: Optional[IChunkingStrategy] = None,
    ):
        self.tts_engine = tts_engine
        self.file_manager = file_manager
        self.timing_engine = timing_engine
        self.max_concurrent = max_concurrent
        self.audio_target_chunk_size = audio_target_chunk_size
        self.audio_max_chunk_size = audio_max_chunk_size
        self.enable_async = enable_async
        self.chunking_strategy = chunking_strategy or create_chunking_strategy(ChunkingMode.SENTENCE_BASED)
        self.base_delay = self._get_base_delay_for_engine()

        logger.debug(
            "AudioEngine initialized with chunk sizes: target=%d, max=%d",
            self.audio_target_chunk_size,
            self.audio_max_chunk_size,
        )

    def generate_with_timing(self, text_chunks: list[str], output_filename: str) -> Result[TimedAudioResult]:
        """Main entry point for audio generation with timing.

        Delegates to timing engine for strategy-specific processing.
        """
        return self.timing_engine.generate_with_timing(text_chunks, output_filename)

    def generate_simple_audio(self, text_chunks: list[str], output_filename: str) -> Result[TimedAudioResult]:
        """Simple audio generation without timing complexity.

        Returns Result with audio result or error - no exceptions thrown.
        """
        logger.info("Generating simple audio for %d chunks", len(text_chunks))
        logger.debug("Chunk sizes: %s", [len(chunk) for chunk in text_chunks])

        if not text_chunks:
            return Result.success(TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None))

        try:
            # Use chunking strategy for optimal text splitting
            max_chunk_size = self.audio_target_chunk_size
            logger.debug("Using max_chunk_size=%d (from audio_target_chunk_size)", max_chunk_size)

            chunks_result = self.chunking_strategy.chunk_text(text_chunks, max_chunk_size)
            if chunks_result.is_failure:
                return Result.failure(chunks_result.error)  # type: ignore[arg-type]

            processed_chunks = chunks_result.value
            if processed_chunks is None:
                return Result.success(TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None))

            logger.info("Processing %d chunks (max size: %d chars)", len(processed_chunks), max_chunk_size)
            logger.debug("After rechunking, chunk sizes: %s", [len(chunk) for chunk in processed_chunks])

            # Generate audio using sync or async based on config
            if self.enable_async:
                logger.debug("Using async processing for simple audio generation")
                audio_chunks = self._generate_chunks_with_new_async_interface(processed_chunks)
            else:
                logger.debug("Using synchronous processing for simple audio generation")
                audio_chunks = self._generate_chunks_sync(processed_chunks)

            if not audio_chunks:
                logger.warning("No successful audio chunks generated")
                return Result.success(TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None))

            # Combine audio chunks
            combined_audio = self._combine_wav_chunks(audio_chunks)

            if not combined_audio:
                return Result.success(TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None))

            # Save audio file as WAV first (since TTS engines typically generate WAV)
            temp_wav_filename = f"{output_filename}_temp.wav"
            temp_wav_path = self.file_manager.save_output_file(combined_audio, temp_wav_filename)

            if not temp_wav_path:
                return Result.success(TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None))

            # Convert WAV to MP3 using ffmpeg
            mp3_filename = f"{output_filename}_simple.mp3"
            mp3_path = Path(self.file_manager.get_output_dir()) / mp3_filename

            conversion_result = self._convert_wav_to_mp3(temp_wav_path, str(mp3_path))

            # Clean up temporary WAV file
            with suppress(OSError, FileNotFoundError):
                Path(temp_wav_path).unlink()

            if conversion_result.is_success:
                logger.info("Simple audio generated and converted to MP3: %s", mp3_filename)
                return Result.success(
                    TimedAudioResult(
                        audio_files=[mp3_filename],
                        combined_mp3=mp3_filename,
                        timing_data=None,
                    )
                )
            else:
                logger.error("MP3 conversion failed: %s", conversion_result.error)
                return Result.success(TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None))

        except Exception as e:
            logger.exception("Simple audio generation failed: %s", e)
            return Result.failure(audio_generation_error(f"Simple audio generation failed: {e}"))

    def _generate_chunks_with_new_async_interface(self, processed_chunks: list[str]) -> list[bytes]:
        """Generate audio chunks using the new async interface with true parallelism.

        Pure function - returns empty list on error.
        """
        import asyncio

        try:
            # Use asyncio.run() for cleaner event loop management (Python 3.7+)
            return asyncio.run(self._process_chunks_async(processed_chunks))
        except Exception as e:
            logger.exception("Async processing failed: %s", e)
            return []

    def _generate_chunks_sync(self, processed_chunks: list[str]) -> list[bytes]:
        """Generate audio chunks synchronously.

        Pure function - returns list of successful chunks.
        """
        audio_chunks = []

        for i, chunk in enumerate(processed_chunks, 1):
            logger.debug("Processing chunk %d/%d (%d chars)", i, len(processed_chunks), len(chunk))

            result = self.tts_engine.generate_audio_data(chunk)
            if result.is_success and result.value is not None:
                audio_chunks.append(result.value)
                logger.debug("Chunk %d completed (%d bytes)", i, len(result.value))
            else:
                logger.warning("Chunk %d failed: %s", i, result.error)

        return audio_chunks

    async def _process_chunks_async(self, processed_chunks: list[str]) -> list[bytes]:
        """Orchestrate parallel chunk processing with proper async coordination.

        Returns list of successful audio chunks.
        """
        # Initialize timing and logging
        timing_context = self._initialize_async_timing()

        # Create async tasks for all valid chunks
        tasks = self._create_chunk_tasks(processed_chunks)

        # Execute tasks with rate limiting
        results = await self._execute_tasks_with_rate_limiting(tasks)

        # Process results and calculate metrics
        return self._process_async_results(results, processed_chunks, timing_context)

    def _initialize_async_timing(self) -> dict[str, float]:
        """Initialize timing and logging for async processing."""
        import time

        start_time = time.time()
        logger.debug("Starting parallel processing at %.2f", start_time)
        return {"start_time": start_time}

    def _create_chunk_tasks(self, processed_chunks: list[str]) -> list[Coroutine[Any, Any, Optional[bytes]]]:
        """Create async tasks for all valid chunks."""
        tasks: list[Coroutine[Any, Any, Optional[bytes]]] = []
        for i, chunk in enumerate(processed_chunks):
            if not chunk.strip():
                continue
            task = self._process_single_chunk_async(chunk, i + 1, len(processed_chunks))
            tasks.append(task)

        logger.debug("Created %d tasks from %d chunks", len(tasks), len(processed_chunks))
        return tasks

    async def _execute_tasks_with_rate_limiting(
        self, tasks: list[Coroutine[Any, Any, Optional[bytes]]]
    ) -> list[Union[Optional[bytes], BaseException]]:
        """Execute tasks with semaphore-based rate limiting."""
        # Apply rate limiting
        semaphore = asyncio.Semaphore(self.max_concurrent)
        limited_tasks = [self._limited_chunk_processing(semaphore, task) for task in tasks]

        # Execute all tasks concurrently
        results: list[Union[Optional[bytes], BaseException]] = await asyncio.gather(
            *limited_tasks, return_exceptions=True
        )
        return results

    def _process_async_results(
        self,
        results: list[Union[Optional[bytes], BaseException]],
        processed_chunks: list[str],
        timing_context: dict[str, float],
    ) -> list[bytes]:
        """Process results, calculate metrics, and filter successful chunks."""
        import time

        end_time = time.time()
        total_time = end_time - timing_context["start_time"]
        logger.info("Parallel processing completed in %.2f seconds", total_time)

        # Filter successful results (immutable) - cast is safe because we filter out non-bytes
        audio_chunks: list[bytes] = [
            result
            for result in results
            if not isinstance(result, Exception) and result is not None and isinstance(result, bytes)
        ]

        # Handle failed chunks logging
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Chunk %d failed with exception: %s", i + 1, result)

        logger.info(
            "Successfully processed %d/%d chunks in %.2fs",
            len(audio_chunks),
            len(processed_chunks),
            total_time,
        )

        # Calculate and log performance metrics
        if len(processed_chunks) > 1:
            avg_time_per_chunk = total_time / len(processed_chunks)
            theoretical_sequential_time = avg_time_per_chunk * len(processed_chunks)
            speedup = theoretical_sequential_time / total_time if total_time > 0 else 1
            logger.debug("Async speedup: %.1fx faster than sequential processing", speedup)

        return audio_chunks

    async def _limited_chunk_processing(
        self, semaphore: asyncio.Semaphore, task: Awaitable[Optional[bytes]]
    ) -> Optional[bytes]:
        """Apply semaphore limiting to chunk processing."""
        async with semaphore:
            result = await task
            # Add small delay for rate limiting
            await asyncio.sleep(self.base_delay)
            return result

    async def _process_single_chunk_async(self, chunk: str, chunk_num: int, total_chunks: int) -> Optional[bytes]:
        """Process a single chunk asynchronously."""
        import time

        chunk_start = time.time()
        logger.debug("Starting chunk %d/%d (%d chars)", chunk_num, total_chunks, len(chunk))

        try:
            # Use the new async interface
            result = await self.tts_engine.generate_audio_data_async(chunk)
            chunk_end = time.time()
            chunk_time = chunk_end - chunk_start

            if result.is_success and result.value:
                logger.debug("Chunk %d completed in %.2fs (%d bytes)", chunk_num, chunk_time, len(result.value))
                return result.value
            else:
                error_msg = result.error if result.is_failure else "No audio data"
                logger.warning("Chunk %d failed in %.2fs: %s", chunk_num, chunk_time, error_msg)
                return None
        except Exception as e:
            chunk_end = time.time()
            chunk_time = chunk_end - chunk_start
            logger.exception("Chunk %d exception in %.2fs: %s", chunk_num, chunk_time, e)
            return None

    def process_audio_file(self, file_path: str) -> Result[float]:
        """Get audio file duration using ffprobe or fallback.

        Returns Result with duration or error.
        """
        try:
            import subprocess  # nosec B404

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
            estimated_duration = file_size / (24000 * 2)  # 24kHz * 2 bytes per sample
            return Result.success(estimated_duration)

        except Exception as e:
            return Result.failure(audio_generation_error(f"Failed to get audio duration: {e}"))

    def _combine_wav_chunks(self, audio_chunks: list[bytes]) -> bytes:
        """Combine multiple audio chunks.

        If WAV (RIFF header), uses wave module to combine properly.
        Otherwise (e.g. MP3), concatenates bytes directly.
        """
        try:
            import io
            import wave

            if not audio_chunks:
                return b""

            if len(audio_chunks) == 1:
                return audio_chunks[0]

            # Check for RIFF header to determine if it's WAV
            if not audio_chunks[0].startswith(b"RIFF"):
                logger.debug("Chunks do not appear to be WAV (no RIFF header), using direct concatenation")
                return b"".join(audio_chunks)

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
                    try:
                        with wave.open(chunk_buffer, "rb") as chunk_wav:
                            frames = chunk_wav.readframes(chunk_wav.getnframes())
                            output_wav.writeframes(frames)
                    except wave.Error:
                        # Fallback for mixed content? Should not happen if first chunk was RIFF
                        logger.warning("Failed to read chunk as WAV during combination")
                        continue

            return output_buffer.getvalue()

        except Exception as e:
            logger.exception("Error combining audio chunks: %s", e)
            # Fallback: return the first chunk or concatenation if combination fails
            return b"".join(audio_chunks) if audio_chunks else b""

    def combine_audio_files(self, file_paths: list[str], output_path: str) -> Result[str]:
        """Combine multiple audio files using ffmpeg.

        Returns Result with output path or error.
        """
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
            import subprocess  # nosec B404

            list_file_result = self._prepare_ffmpeg_command(file_paths, output_path)
            if list_file_result.is_failure:
                assert list_file_result.error is not None
                return Result.failure(list_file_result.error)

            list_file = list_file_result.value
            assert list_file is not None  # Should not be None after success check

            cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path, "-y"]

            result = subprocess.run(cmd, capture_output=True, timeout=300)

            # Clean up list file
            with suppress(OSError, FileNotFoundError):
                Path(list_file).unlink()

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
        """Generate audio files concurrently with intelligent coordination.

        Async function for backward compatibility - returns tuple directly.
        """
        if not self.tts_engine:
            logger.error("No TTS engine available")
            return [], None

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Filter and validate chunks
        valid_chunks = self._filter_valid_chunks(text_chunks)

        if not valid_chunks:
            logger.warning("No valid chunks to process")
            return [], None

        logger.info("Processing %d valid chunks concurrently", len(valid_chunks))

        # Generate audio files concurrently
        audio_files = await self._generate_audio_files_concurrent(valid_chunks, output_name, output_dir)

        # Create combined MP3 if we have files
        combined_mp3 = None
        if audio_files:
            combined_path = Path(output_dir) / f"{output_name}_combined.mp3"
            result = self.combine_audio_files(audio_files, str(combined_path))
            if result.is_success and result.value:
                combined_mp3 = Path(result.value).name
            else:
                logger.error("Failed to create combined MP3: %s", result.error)

        return [Path(f).name for f in audio_files], combined_mp3

    def _filter_valid_chunks(self, text_chunks: list[str]) -> list[tuple[int, str]]:
        """Filter out invalid or empty text chunks.

        Pure function.
        """
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
                logger.warning("Task %d failed: %s", i + 1, result)
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
                    logger.warning("TTS failed for chunk %d: %s", chunk_number, audio_result.error)
                    return None

                # Validate audio data before saving
                if not audio_result.value:
                    logger.warning("No audio data for chunk %d", chunk_number)
                    return None

                # Save the audio file
                save_path = self.file_manager.save_output_file(audio_result.value, filename)

                if save_path:
                    logger.debug("Generated chunk %d: %s", chunk_number, filename)
                    return save_path
                else:
                    logger.warning("Failed to save chunk %d", chunk_number)
                    return None

            except Exception as e:
                logger.exception("Failed to generate chunk %d: %s", chunk_number, e)
                return None

    def _call_tts_engine(self, text: str) -> Result[bytes]:
        """Call TTS engine (blocking operation)."""
        try:
            return self.tts_engine.generate_audio_data(text)
        except Exception as e:
            return Result.failure(audio_generation_error(f"TTS engine call failed: {e!s}"))

    def _get_base_delay_for_engine(self) -> float:
        """Get base delay for rate limiting based on TTS engine.

        Pure function.
        """
        engine_name = self.tts_engine.__class__.__name__.lower()

        if "gemini" in engine_name:
            return 0.8  # Gemini has stricter rate limits
        elif "piper" in engine_name:
            return 0.1  # Piper is local, minimal delay
        else:
            return 0.5  # Default for unknown engines

    def _convert_wav_to_mp3(self, wav_path: str, mp3_path: str) -> Result[str]:
        """Convert WAV file to MP3 using ffmpeg.

        Returns Result with output path or error.
        """
        try:
            import subprocess  # nosec B404

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
                "192k",  # High quality bitrate
                "-ar",
                "44100",  # Standard high quality sample rate
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
