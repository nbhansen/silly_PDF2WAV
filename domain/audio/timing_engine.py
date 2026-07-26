# domain/audio/timing_engine.py - Timing Engine with Result[T] pattern
"""Timing engine using Result[T] pattern for type-safe error handling.

No exceptions thrown - all errors returned as Result[T].

Timing Algorithm
================

Word-level timestamps for read-along synchronization come from the segments the
TTS engine returns, not from estimation.

1. Synthesize each text chunk, which yields one segment per sentence carrying
   both the sentence text and its audio.
2. Lay the segments out on a timeline using their measured durations, plus the
   inter-sentence gap the assembler will write between them.
3. Assemble all segments into one audio file.

Because the same AudioAssembler decides both the gap in the timeline and the gap
in the audio, the two cannot drift apart.

Engines with no internal structure (Gemini) return a single segment per chunk, so
timing is chunk-granular rather than sentence-granular. That is a real limitation
of the engine, and it is visible in the data rather than hidden behind an
estimate that looks precise.
"""

from abc import ABC, abstractmethod
from contextlib import suppress
import logging
from pathlib import Path
import subprocess  # nosec B404
import time

from ..errors import ErrorCode, Result, audio_generation_error
from ..interfaces import IFileManager, ITTSEngine
from ..models import SynthesizedSegment, TextSegment, TimedAudioResult, TimingMetadata
from .audio_assembler import AudioAssembler

logger = logging.getLogger(__name__)


class ITimingEngine(ABC):
    """Interface for timing generation using Result[T] pattern."""

    @abstractmethod
    def generate_with_timing(self, text_chunks: list[str], output_filename: str) -> Result[TimedAudioResult]:
        """Generate audio with timing information."""


class TimingEngine(ITimingEngine):
    """Timing engine using Result[T] pattern for all operations.

    Pure functions with no exceptions - all errors returned as Result[T].
    """

    def __init__(
        self,
        tts_engine: ITTSEngine,
        file_manager: IFileManager,
        assembler: AudioAssembler | None = None,
        request_interval: float = 0.0,
    ):
        """Initialize the timing engine.

        Args:
            tts_engine: Engine that turns text into segments.
            file_manager: Sink for the generated audio.
            assembler: Owns gap policy and container writing. Must be the same policy
                used for the audio itself, or the timeline and the audio disagree.
            request_interval: Minimum seconds between synthesis calls. Only matters
                for rate-limited cloud engines; leave at 0 for local ones.
        """
        self.tts_engine = tts_engine
        self.file_manager = file_manager
        self.assembler = assembler or AudioAssembler()
        self.request_interval = request_interval
        self.last_api_call = 0.0

    def generate_with_timing(self, text_chunks: list[str], output_filename: str) -> Result[TimedAudioResult]:
        """Synthesize all chunks and lay them out on a measured timeline."""
        try:
            all_segments: list[SynthesizedSegment] = []
            timed_segments: list[TextSegment] = []
            cursor = 0.0

            for chunk_index, chunk in enumerate(text_chunks):
                if not chunk.strip():
                    continue

                self._apply_rate_limiting()

                result = self.tts_engine.synthesize(chunk)
                if result.is_failure or not result.value:
                    logger.warning("TimingEngine: Chunk %d failed: %s", chunk_index + 1, result.error)
                    continue

                segments = list(result.value)
                logger.debug("TimingEngine: Chunk %d produced %d segments", chunk_index + 1, len(segments))

                chunk_timed, cursor = self.assembler.to_timed_segments(
                    segments, chunk_index=chunk_index, start_time=cursor
                )
                all_segments.extend(segments)
                timed_segments.extend(chunk_timed)

            if not all_segments:
                return Result.failure(audio_generation_error("No audio generated for any chunk"))

            assembled = self.assembler.to_wav(all_segments)
            if assembled.is_failure or not assembled.value:
                return Result.failure(assembled.error or audio_generation_error("Failed to assemble audio"))

            combined_filename = f"{output_filename}_timed.mp3"
            write_result = self._write_mp3(assembled.value, output_filename, combined_filename)
            if write_result.is_failure:
                return Result.failure(write_result.error)  # type: ignore[arg-type]

            timing_metadata = TimingMetadata(
                total_duration=cursor,
                text_segments=timed_segments,
                audio_files=[combined_filename],
            )

            logger.info(
                "TimingEngine: %d segments over %.2fs from %d chunks",
                len(timed_segments),
                cursor,
                len(text_chunks),
            )

            return Result.success(
                TimedAudioResult(
                    audio_files=[combined_filename],
                    combined_mp3=combined_filename,
                    timing_data=timing_metadata,
                )
            )

        except Exception as e:
            return Result.from_exception(e, ErrorCode.AUDIO_GENERATION_FAILED, retryable=True)

    def _apply_rate_limiting(self) -> None:
        """Space out synthesis calls for rate-limited engines."""
        if self.request_interval <= 0:
            return

        elapsed = time.time() - self.last_api_call
        if elapsed < self.request_interval:
            sleep_time = self.request_interval - elapsed
            logger.debug("TimingEngine: Rate limiting, sleeping %.2fs", sleep_time)
            time.sleep(sleep_time)

        self.last_api_call = time.time()

    def _write_mp3(self, wav_bytes: bytes, output_filename: str, mp3_filename: str) -> Result[str]:
        """Save assembled audio and transcode it to MP3."""
        temp_wav_name = f"{output_filename}_timed_temp.wav"
        temp_wav_path = self.file_manager.save_output_file(wav_bytes, temp_wav_name)
        if not temp_wav_path:
            return Result.failure(audio_generation_error("Failed to save assembled audio"))

        mp3_path = Path(self.file_manager.get_output_dir()) / mp3_filename

        try:
            cmd = [
                "ffmpeg",
                "-i",
                temp_wav_path,
                "-codec:a",
                "libmp3lame",
                "-b:a",
                "192k",
                "-ar",
                "44100",
                str(mp3_path),
                "-y",
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=300)

            if result.returncode != 0:
                return Result.failure(audio_generation_error(f"ffmpeg conversion failed: {result.stderr.decode()}"))

            return Result.success(str(mp3_path))

        except Exception as e:
            return Result.failure(audio_generation_error(f"MP3 conversion failed: {e}"))

        finally:
            with suppress(OSError, FileNotFoundError):
                Path(temp_wav_path).unlink()
