# domain/audio/timing_engine.py - Unified Timing Engine
"""Consolidated timing engine that unifies all timing strategies.
Replaces: GeminiTimestampStrategy, SentenceMeasurementStrategy, EnhancedTimingStrategy, TimingCalculator.
"""

from abc import ABC, abstractmethod
import dataclasses
from enum import Enum
from pathlib import Path
import time
from typing import TYPE_CHECKING, Optional

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
    """Unified interface for timing generation."""

    @abstractmethod
    def generate_with_timing(self, text_chunks: list[str], output_filename: str) -> TimedAudioResult:
        """Generate audio with timing information."""


class TimingEngine(ITimingEngine):
    """Unified timing engine that consolidates all timing strategies.
    Uses strategy pattern internally but presents unified interface.
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

    def generate_with_timing(self, text_chunks: list[str], output_filename: str) -> TimedAudioResult:
        """Main entry point - routes to appropriate timing strategy."""
        if self.mode == TimingMode.ESTIMATION:
            return self._generate_with_estimation(text_chunks, output_filename)
        elif self.mode == TimingMode.MEASUREMENT:
            return self._generate_with_measurement(text_chunks, output_filename)

        # This should never be reached with current enum values
        raise ValueError(f"Unsupported timing mode: {self.mode}")

    def _generate_with_estimation(self, text_chunks: list[str], output_filename: str) -> TimedAudioResult:
        """Fast timing using mathematical calculations (for engines without native timestamps)."""
        if not hasattr(self.tts_engine, "generate_audio_with_timestamps"):
            # Engine doesn't support native timestamps, use measurement mode instead
            return self._generate_with_measurement(text_chunks, output_filename)

        print("TimingEngine: Using estimation mode with native engine timestamps")

        # Process chunks individually to respect size limits
        all_audio_files = []
        all_text_segments = []
        cumulative_time = 0.0

        print(f"🔍 TimingEngine: Processing {len(text_chunks)} chunks individually")

        for i, chunk in enumerate(text_chunks):
            # Enhance text with SSML if available
            enhanced_chunk = self.text_pipeline.enhance_with_ssml(chunk) if self.text_pipeline else chunk

            print(f"🔍 TimingEngine: Processing chunk {i+1}/{len(text_chunks)} ({len(enhanced_chunk)} chars)")

            # Check chunk size
            if len(enhanced_chunk) > 3000:
                print(
                    f"🚨 TimingEngine: Chunk {i+1} too large ({len(enhanced_chunk)} chars), falling back to measurement mode"
                )
                return self._generate_with_measurement(text_chunks, output_filename)

            if not enhanced_chunk.strip():
                continue

            try:
                # Use engine's native timestamping for this chunk
                result = self.tts_engine.generate_audio_with_timestamps(enhanced_chunk)

                if result.is_failure:
                    print(f"TimingEngine: Engine failed for chunk {i+1}: {result.error}")
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

                        # Update cumulative time (using adjusted segments)
                        chunk_duration = max(
                            seg.start_time + seg.duration - cumulative_time for seg in adjusted_segments
                        )
                        cumulative_time += chunk_duration

            except Exception as e:
                print(f"TimingEngine: Failed to process chunk {i+1}: {e}")
                continue

        if not all_audio_files:
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

        # Combine audio files if multiple chunks
        combined_mp3 = None
        if len(all_audio_files) > 1:
            combined_mp3 = f"{output_filename}_combined.mp3"
            # Note: Audio combination logic would go here
            # For now, we'll just use the first file as combined
            combined_mp3 = all_audio_files[0]
        else:
            combined_mp3 = all_audio_files[0]

        # Create timing metadata
        timing_metadata = None
        if all_text_segments:
            total_duration = (
                max(seg.start_time + seg.duration for seg in all_text_segments) if all_text_segments else 0.0
            )
            timing_metadata = TimingMetadata(
                total_duration=total_duration, text_segments=all_text_segments, audio_files=all_audio_files
            )

        return TimedAudioResult(audio_files=all_audio_files, combined_mp3=combined_mp3, timing_data=timing_metadata)

    def _generate_with_measurement(self, text_chunks: list[str], output_filename: str) -> TimedAudioResult:
        """Precise timing by measuring actual audio duration (optimal for engines with timestamp support)."""
        print("TimingEngine: Using measurement mode for precise audio timing")

        if not self.text_pipeline:
            print("Warning: No text pipeline available for measurement mode")
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

        print(f"🔍 TimingEngine: Processing {len(text_chunks)} chunks in measurement mode")

        all_temp_audio_files = []
        all_text_segments = []
        cumulative_time = 0.0

        # Process each text chunk to create audio and timing data
        for chunk_idx, chunk in enumerate(text_chunks):
            chunk_result = self._process_text_chunk(chunk, chunk_idx, cumulative_time)

            all_temp_audio_files.extend(chunk_result.temp_files)
            all_text_segments.extend(chunk_result.text_segments)
            cumulative_time = chunk_result.final_cumulative_time

        # Finalize audio output and create timing metadata
        return self._finalize_audio_output(all_temp_audio_files, all_text_segments, cumulative_time, output_filename)

    def _process_text_chunk(self, chunk: str, chunk_idx: int, cumulative_time: float) -> ChunkProcessingResult:
        """Process a single text chunk into audio and timing segments."""
        print(f"🔍 TimingEngine: Processing chunk {chunk_idx+1} ({len(chunk)} chars)")

        # Enhance chunk and split into sentences
        if self.text_pipeline:
            enhanced_chunk = self.text_pipeline.enhance_with_ssml(chunk)
            chunk_sentences = self.text_pipeline.split_into_sentences(enhanced_chunk)
        else:
            chunk_sentences = [chunk]

        sentences = chunk_sentences
        print(f"🔍 TimingEngine: Chunk has {len(sentences)} sentences")

        if not sentences:
            return ChunkProcessingResult(temp_files=[], text_segments=[], final_cumulative_time=cumulative_time)

        # Smart batching for performance within this chunk
        batch_size = min(15, max(5, len(sentences) // 10))
        sentence_batches = [sentences[i : i + batch_size] for i in range(0, len(sentences), batch_size)]

        print(f"  Processing {len(sentences)} sentences in {len(sentence_batches)} batches")

        temp_audio_files = []
        text_segments = []
        current_cumulative_time = cumulative_time

        # Process each batch of sentences
        for batch_idx, sentence_batch in enumerate(sentence_batches):
            batch_result = self._process_sentence_batch(
                sentence_batch, batch_idx, batch_size, chunk_idx, current_cumulative_time
            )

            if batch_result.temp_file:
                temp_audio_files.append(batch_result.temp_file)

            text_segments.extend(batch_result.text_segments)
            current_cumulative_time = batch_result.final_cumulative_time

        return ChunkProcessingResult(
            temp_files=temp_audio_files, text_segments=text_segments, final_cumulative_time=current_cumulative_time
        )

    def _process_sentence_batch(
        self, sentence_batch: list[str], batch_idx: int, batch_size: int, chunk_idx: int, cumulative_time: float
    ) -> BatchProcessingResult:
        """Process a batch of sentences into audio and create timing segments."""
        try:
            # Apply rate limiting
            self._apply_rate_limit()

            # Generate audio for batch
            batch_text = " ".join(sentence_batch)
            result = self.tts_engine.generate_audio_data(batch_text)

            if result.is_success and result.value:
                audio_data = result.value
                temp_file = self.file_manager.save_temp_file(audio_data, suffix=".wav")

                # Measure batch duration and distribute across sentences
                batch_duration = self._measure_audio_duration(temp_file)
                text_segments = self._distribute_batch_duration(
                    sentence_batch, batch_duration, cumulative_time, chunk_idx, batch_idx, batch_size
                )

                final_cumulative_time = (
                    text_segments[-1].start_time + text_segments[-1].duration if text_segments else cumulative_time
                )

                return BatchProcessingResult(
                    temp_file=temp_file, text_segments=text_segments, final_cumulative_time=final_cumulative_time
                )

        except Exception as e:
            print(f"  Error processing batch {batch_idx + 1}: {e}")

        return BatchProcessingResult(temp_file=None, text_segments=[], final_cumulative_time=cumulative_time)

    def _distribute_batch_duration(
        self,
        sentence_batch: list[str],
        batch_duration: float,
        cumulative_time: float,
        chunk_idx: int,
        batch_idx: int,
        batch_size: int,
    ) -> list["TextSegment"]:
        """Distribute batch duration across individual sentences based on word count."""
        # Calculate total words in batch for proportional distribution
        total_words = sum(len(self._strip_ssml(sent).split()) for sent in sentence_batch)

        text_segments = []
        current_time = cumulative_time

        for i, sentence_text in enumerate(sentence_batch):
            clean_text = self._strip_ssml(sentence_text)
            word_count = len(clean_text.split())

            # Calculate proportional duration based on word count
            if total_words > 0:
                sentence_duration = (word_count / total_words) * batch_duration
            else:
                sentence_duration = batch_duration / len(sentence_batch)

            sentence_duration = max(sentence_duration, 0.3)  # Minimum duration

            segment = TextSegment(
                text=clean_text,
                start_time=current_time,
                duration=sentence_duration,
                segment_type="sentence",
                chunk_index=chunk_idx,
                sentence_index=batch_idx * batch_size + i,
            )
            text_segments.append(segment)
            current_time += sentence_duration

        return text_segments

    def _finalize_audio_output(
        self,
        all_temp_audio_files: list[str],
        all_text_segments: list["TextSegment"],
        cumulative_time: float,
        output_filename: str,
    ) -> "TimedAudioResult":
        """Combine audio files and create final timing metadata."""
        import shutil

        final_audio_files = []
        print(f"🔍 DEBUG: all_temp_audio_files count: {len(all_temp_audio_files)}")

        if all_temp_audio_files:
            if len(all_temp_audio_files) > 1:
                print(f"🔍 DEBUG: Combining {len(all_temp_audio_files)} audio files")
                combined_path = Path(self.file_manager.get_output_dir()) / f"{output_filename}_combined.mp3"
                if self._combine_audio_files(all_temp_audio_files, combined_path):
                    final_audio_files = [Path(combined_path).name]
                    print(f"🔍 DEBUG: Audio combination successful: {final_audio_files}")
                else:
                    print("🔍 DEBUG: Audio combination FAILED")
            else:
                print(f"🔍 DEBUG: Single file copy: {all_temp_audio_files[0]}")
                output_path = Path(self.file_manager.get_output_dir()) / f"{output_filename}.wav"
                try:
                    shutil.copy2(all_temp_audio_files[0], output_path)
                    final_audio_files = [Path(output_path).name]
                    print(f"🔍 DEBUG: Single file copy successful: {final_audio_files}")
                except Exception as e:
                    print(f"🔍 DEBUG: Failed to copy audio file: {e}")
        else:
            print("🔍 DEBUG: No temp audio files to process!")

        # Clean up temporary files
        for temp_file in all_temp_audio_files:
            try:
                if Path(temp_file).exists():
                    Path(temp_file).unlink()
            except (OSError, FileNotFoundError):
                pass

        # Create timing metadata for read-along functionality
        timing_metadata = None
        if all_text_segments:
            timing_metadata = TimingMetadata(
                total_duration=cumulative_time, text_segments=all_text_segments, audio_files=final_audio_files
            )

        return TimedAudioResult(
            audio_files=final_audio_files,
            combined_mp3=final_audio_files[0] if final_audio_files else None,
            timing_data=timing_metadata,
        )

    def _generate_with_hybrid(self, text_chunks: list[str], output_filename: str) -> TimedAudioResult:
        """Smart combination of estimation and measurement."""
        # Try estimation first, fall back to measurement if needed
        result = self._generate_with_estimation(text_chunks, output_filename)

        # If estimation failed or no timing data, use measurement
        if not result.timing_data or not result.audio_files:
            print("TimingEngine: Estimation failed, falling back to measurement")
            return self._generate_with_measurement(text_chunks, output_filename)

        return result

    def _apply_rate_limit(self) -> None:
        """Apply rate limiting between API calls."""
        if self.measurement_interval <= 0:
            return

        current_time = time.time()
        time_since_last = current_time - self.last_api_call

        if time_since_last < self.measurement_interval:
            sleep_duration = self.measurement_interval - time_since_last
            time.sleep(sleep_duration)

        self.last_api_call = time.time()

    def _measure_audio_duration(self, file_path: str) -> float:
        """Measure audio file duration."""
        try:
            import subprocess

            # Validate file path for security
            if not Path(file_path).is_file() or Path(file_path).is_symlink():
                return 1.0  # Default fallback for invalid paths

            cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError, ValueError, FileNotFoundError):
            # FFprobe failed or output parsing error
            pass

        # Fallback to file size estimation
        try:
            file_size = Path(file_path).stat().st_size
            return file_size / (22050 * 2)  # Rough estimation
        except (OSError, FileNotFoundError):
            return 1.0  # Default fallback

    def _strip_ssml(self, text: str) -> str:
        """Remove SSML tags from text for word counting."""
        import re

        # Remove all SSML tags like <speak>, <break>, <prosody>, etc.
        clean_text = re.sub(r"<[^>]+>", "", text)
        # Clean up extra whitespace
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        return clean_text

    def _combine_audio_files(self, file_paths: list[str], output_path: str) -> bool:
        """Combine audio files using ffmpeg."""
        try:
            import subprocess

            print(f"🔍 DEBUG: Combining {len(file_paths)} files to {output_path}")
            print(f"🔍 DEBUG: Input files: {file_paths}")

            list_file = output_path + ".list"
            with Path(list_file).open("w") as f:
                for file_path in file_paths:
                    f.write(f"file '{file_path}'\n")

            # Convert from WAV to MP3 since we can't use -c copy with format change
            cmd = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_file,
                "-c:a",
                "libmp3lame",
                "-b:a",
                "128k",
                output_path,
                "-y",
            ]
            print(f"🔍 DEBUG: Running ffmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, timeout=300)

            print(f"🔍 DEBUG: ffmpeg return code: {result.returncode}")
            if result.stderr:
                print(f"🔍 DEBUG: ffmpeg stderr: {result.stderr.decode()}")

            try:
                Path(list_file).unlink()
            except (OSError, FileNotFoundError):
                # Ignore file cleanup errors - temporary files may already be removed
                pass

            return result.returncode == 0
        except Exception as e:
            print(f"🔍 DEBUG: Audio combination exception: {e}")
            return False
