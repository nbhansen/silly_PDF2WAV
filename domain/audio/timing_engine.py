# domain/audio/timing_engine.py - Timing Engine with Result[T] pattern
"""Timing engine using Result[T] pattern for type-safe error handling.

No exceptions thrown - all errors returned as Result[T].
"""

from abc import ABC, abstractmethod
from contextlib import suppress
import dataclasses
from enum import Enum
from pathlib import Path
import time
from typing import TYPE_CHECKING, Optional

from ..errors import ErrorCode, Result, audio_generation_error
from ..interfaces import IFileManager, ITTSEngine
from ..models import TextSegment, TimedAudioResult, TimingMetadata

if TYPE_CHECKING:
    from ..text.text_pipeline import ITextPipeline


@dataclasses.dataclass(frozen=True)
class ChunkProcessingResult:
    """Result of processing a single text chunk."""

    temp_files: list[str]
    text_segments: list[TextSegment]
    final_cumulative_time: float


@dataclasses.dataclass(frozen=True)
class BatchProcessingResult:
    """Result of processing a batch of sentences."""

    temp_file: Optional[str]
    text_segments: list[TextSegment]
    final_cumulative_time: float


class TimingMode(Enum):
    """Available timing modes."""

    ESTIMATION = "estimation"  # Fast mathematical calculation (for engines without native timestamps)
    MEASUREMENT = "measurement"  # Precise timing from actual audio (for engines with timestamp support)


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
        text_pipeline: Optional["ITextPipeline"] = None,
        mode: TimingMode = TimingMode.ESTIMATION,
        measurement_interval: float = 0.8,
    ):
        self.tts_engine = tts_engine
        self.file_manager = file_manager
        self.text_pipeline = text_pipeline
        self.mode = mode
        self.measurement_interval = measurement_interval
        self.last_api_call = 0.0

        # Optimize timing mode for engine capabilities
        if mode == TimingMode.ESTIMATION and not hasattr(tts_engine, "generate_audio_with_timestamps"):
            print(f"✅ {tts_engine.__class__.__name__}: Using measurement mode for precise timestamps")
            self.mode = TimingMode.MEASUREMENT

    def generate_with_timing(self, text_chunks: list[str], output_filename: str) -> Result[TimedAudioResult]:
        """Main entry point - routes to appropriate timing strategy.

        Returns Result with timing data or error.
        """
        try:
            if self.mode == TimingMode.ESTIMATION:
                return self._generate_with_estimation(text_chunks, output_filename)
            else:  # self.mode == TimingMode.MEASUREMENT
                return self._generate_with_measurement(text_chunks, output_filename)
        except Exception as e:
            return Result.from_exception(e, ErrorCode.AUDIO_GENERATION_FAILED, retryable=True)

    def _generate_with_estimation(self, text_chunks: list[str], output_filename: str) -> Result[TimedAudioResult]:
        """Fast timing using mathematical calculations.

        Returns Result with timing data or error.
        """
        if not hasattr(self.tts_engine, "generate_audio_with_timestamps"):
            # Engine doesn't support native timestamps, use measurement mode instead
            return self._generate_with_measurement(text_chunks, output_filename)

        print("TimingEngine: Using estimation mode with native engine timestamps")

        try:
            # Process chunks individually to respect size limits
            all_audio_files = []
            all_text_segments = []
            cumulative_time = 0.0

            print(f"🔍 TimingEngine: Processing {len(text_chunks)} chunks individually")

            for i, chunk in enumerate(text_chunks):
                # Enhance text with natural formatting if available
                if self.text_pipeline:
                    enhance_result = self.text_pipeline.enhance_with_natural_formatting(chunk)
                    if enhance_result.is_failure:
                        print(f"TimingEngine: Enhancement failed for chunk {i + 1}, using original")
                        enhanced_chunk = chunk
                    elif enhance_result.value is not None:
                        enhanced_chunk = enhance_result.value
                    else:
                        enhanced_chunk = chunk
                else:
                    enhanced_chunk = chunk

                print(f"🔍 TimingEngine: Processing chunk {i + 1}/{len(text_chunks)} ({len(enhanced_chunk)} chars)")

                # Check chunk size
                if len(enhanced_chunk) > 3000:
                    print(
                        f"🚨 TimingEngine: Chunk {i + 1} too large ({len(enhanced_chunk)} chars), "
                        f"falling back to measurement mode"
                    )
                    return self._generate_with_measurement(text_chunks, output_filename)

                if not enhanced_chunk.strip():
                    continue

                # Use engine's native timestamping for this chunk
                result = self.tts_engine.generate_audio_with_timestamps(enhanced_chunk)

                if result.is_failure:
                    print(f"TimingEngine: Engine failed for chunk {i + 1}: {result.error}")
                    continue

                audio_data, text_segments = result.value

                if not audio_data:
                    continue

                # Save audio file for this chunk
                audio_filename = f"{output_filename}_chunk_{i}.mp3"
                audio_path = self.file_manager.save_output_file(audio_data, audio_filename)

                if audio_path:
                    all_audio_files.append(audio_filename)

                    # Adjust timestamps for this chunk relative to previous chunks (immutable)
                    if text_segments:
                        adjusted_segments = [
                            dataclasses.replace(segment, start_time=segment.start_time + cumulative_time)
                            for segment in text_segments
                        ]
                        all_text_segments.extend(adjusted_segments)

                        # Update cumulative time
                        last_segment = text_segments[-1]
                        cumulative_time += last_segment.end_time

            if not all_audio_files:
                return Result.failure(audio_generation_error("No audio files generated in estimation mode"))

            # Create combined MP3
            combined_filename = f"{output_filename}_timed.mp3"
            combined_path = self._combine_audio_chunks(all_audio_files, combined_filename)

            if not combined_path:
                return Result.failure(audio_generation_error("Failed to combine audio chunks"))

            # Create timing metadata
            timing_metadata = TimingMetadata(
                total_duration=cumulative_time,
                text_segments=all_text_segments,
                audio_files=all_audio_files,
            )

            return Result.success(
                TimedAudioResult(
                    audio_files=all_audio_files,
                    combined_mp3=combined_filename,
                    timing_data=timing_metadata,
                )
            )

        except Exception as e:
            return Result.from_exception(e, ErrorCode.AUDIO_GENERATION_FAILED, retryable=True)

    def _generate_with_measurement(self, text_chunks: list[str], output_filename: str) -> Result[TimedAudioResult]:
        """Precise timing through actual audio measurement.

        Returns Result with timing data or error.
        """
        print("TimingEngine: Using measurement mode for accurate timing extraction")

        try:
            all_temp_files = []
            all_text_segments = []
            cumulative_time = 0.0

            # Process each chunk
            for i, chunk in enumerate(text_chunks):
                chunk_result = self._process_chunk_with_measurement(chunk, i, cumulative_time)

                if chunk_result is None:
                    continue

                all_temp_files.extend(chunk_result.temp_files)
                all_text_segments.extend(chunk_result.text_segments)
                cumulative_time = chunk_result.final_cumulative_time

            if not all_temp_files:
                return Result.failure(audio_generation_error("No audio files generated in measurement mode"))

            # Create final combined audio file
            combined_filename = f"{output_filename}_timed.mp3"
            combined_path = self._combine_audio_chunks(all_temp_files, combined_filename)

            # Clean up temporary files
            for temp_file in all_temp_files:
                with suppress(OSError, FileNotFoundError):
                    temp_path = Path(self.file_manager.get_output_dir()) / temp_file
                    if temp_path.exists():
                        temp_path.unlink()

            if not combined_path:
                return Result.failure(audio_generation_error("Failed to combine audio files"))

            # Create timing metadata
            timing_metadata = TimingMetadata(
                total_duration=cumulative_time,
                text_segments=all_text_segments,
                audio_files=[combined_filename],
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

    def _process_chunk_with_measurement(
        self, chunk: str, chunk_index: int, cumulative_time: float
    ) -> Optional[ChunkProcessingResult]:
        """Process a single chunk with measurement mode.

        Returns ChunkProcessingResult or None on failure.
        """
        try:
            # Enhance text if pipeline is available
            if self.text_pipeline:
                enhance_result = self.text_pipeline.enhance_with_natural_formatting(chunk)
                if enhance_result.is_success and enhance_result.value is not None:
                    enhanced_chunk = enhance_result.value
                else:
                    enhanced_chunk = chunk

                # Split into sentences
                sentences_result = self.text_pipeline.split_into_sentences(enhanced_chunk)
                if sentences_result.is_success and sentences_result.value is not None:
                    sentences = sentences_result.value
                else:
                    sentences = [enhanced_chunk]
            else:
                enhanced_chunk = chunk
                sentences = [chunk]

            print(f"TimingEngine: Chunk {chunk_index + 1} has {len(sentences)} sentences")

            # Process in batches for efficiency
            batch_size = 5
            temp_files = []
            text_segments = []

            for batch_start in range(0, len(sentences), batch_size):
                batch_end = min(batch_start + batch_size, len(sentences))
                batch = sentences[batch_start:batch_end]

                print(f"  Processing batch {batch_start // batch_size + 1} (sentences {batch_start + 1}-{batch_end})")

                batch_result = self._process_sentence_batch(batch, chunk_index, batch_start, cumulative_time)

                if batch_result and batch_result.temp_file:
                    temp_files.append(batch_result.temp_file)
                    text_segments.extend(batch_result.text_segments)
                    cumulative_time = batch_result.final_cumulative_time

            return ChunkProcessingResult(
                temp_files=temp_files,
                text_segments=text_segments,
                final_cumulative_time=cumulative_time,
            )

        except Exception as e:
            print(f"TimingEngine: Error processing chunk {chunk_index}: {e}")
            return None

    def _process_sentence_batch(
        self, sentences: list[str], chunk_index: int, batch_start: int, cumulative_time: float
    ) -> Optional[BatchProcessingResult]:
        """Process a batch of sentences for timing.

        Returns BatchProcessingResult or None on failure.
        """
        try:
            batch_text = " ".join(sentences)

            # Rate limiting
            self._apply_rate_limiting()

            # Generate audio for batch
            audio_result = self.tts_engine.generate_audio_data(batch_text)
            if audio_result.is_failure or not audio_result.value:
                print("    Failed to generate audio for batch")
                return None

            # Save temporary audio file
            temp_filename = f"temp_chunk_{chunk_index}_batch_{batch_start}.wav"
            temp_path = self.file_manager.save_output_file(audio_result.value, temp_filename)

            if not temp_path:
                return None

            # Measure audio duration
            from ..audio.audio_engine import AudioEngine

            # Create a temporary minimal AudioEngine instance for processing
            temp_audio_engine = AudioEngine(self.tts_engine, self.file_manager, self)
            duration_result = temp_audio_engine.process_audio_file(temp_path)

            if duration_result.is_failure or duration_result.value is None:
                # Estimate duration fallback
                duration = len(batch_text) * 0.06  # Rough estimate
            else:
                duration = duration_result.value

            print(f"    Audio duration: {duration:.2f}s")

            # Create timing segments for each sentence
            text_segments = []
            sentence_duration = duration / len(sentences) if sentences else 0

            for i, sentence in enumerate(sentences):
                segment = TextSegment(
                    text=sentence,
                    start_time=cumulative_time + (i * sentence_duration),
                    duration=sentence_duration,
                    segment_type="sentence",
                    chunk_index=chunk_index,
                    sentence_index=batch_start + i,
                )
                text_segments.append(segment)

            return BatchProcessingResult(
                temp_file=temp_filename,
                text_segments=text_segments,
                final_cumulative_time=cumulative_time + duration,
            )

        except Exception as e:
            print(f"    Error processing batch: {e}")
            return None

    def _apply_rate_limiting(self) -> None:
        """Apply rate limiting between API calls.

        Pure function - no exceptions thrown.
        """
        current_time = time.time()
        time_since_last = current_time - self.last_api_call

        if time_since_last < self.measurement_interval:
            sleep_time = self.measurement_interval - time_since_last
            print(f"    Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_api_call = time.time()

    def _combine_audio_chunks(self, audio_files: list[str], output_filename: str) -> Optional[str]:
        """Combine multiple audio files into one.

        Returns output path or None on failure.
        """
        try:
            if not audio_files:
                return None

            # Get full paths
            full_paths = []
            for audio_file in audio_files:
                full_path = Path(self.file_manager.get_output_dir()) / audio_file
                if full_path.exists():
                    full_paths.append(str(full_path))

            if not full_paths:
                return None

            # Use audio engine's combine function
            output_path = Path(self.file_manager.get_output_dir()) / output_filename

            # Create a minimal audio engine just for combining
            # This is a bit of a hack but avoids circular dependencies
            import subprocess  # nosec B404

            if len(full_paths) == 1:
                # Just copy the single file
                import shutil

                shutil.copy2(full_paths[0], str(output_path))
                return output_filename

            # Use ffmpeg directly for combining
            list_file = str(output_path) + ".list"
            with Path(list_file).open("w") as f:
                for path in full_paths:
                    f.write(f"file '{path}'\n")

            cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", str(output_path), "-y"]
            result = subprocess.run(cmd, capture_output=True, timeout=300)

            # Clean up list file
            with suppress(OSError, FileNotFoundError):
                Path(list_file).unlink()

            if result.returncode == 0:
                return output_filename
            else:
                print(f"ffmpeg combine failed: {result.stderr.decode()}")
                return None

        except Exception as e:
            print(f"TimingEngine: Error combining audio files: {e}")
            return None
