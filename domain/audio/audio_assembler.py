# domain/audio/audio_assembler.py - Segment assembly with Result[T] pattern
"""Assembles synthesized segments into playable audio.

This is the one place that decides what silence goes between segments and how
samples become a file. Engines return segments; nothing downstream of them
writes a container or invents a gap.

Keeping it here matters because gaps have to be applied consistently at two
different seams: between the sentences inside one synthesis call, and between
the chunks that get concatenated into the finished document. When those two
decisions lived in different layers, the second one went missing entirely.
"""

from collections.abc import Sequence
import io
import logging
import wave

from ..errors import ErrorCode, Result, audio_generation_error
from ..models import SynthesizedSegment, TextSegment

logger = logging.getLogger(__name__)


class AudioAssembler:
    """Turns synthesized segments into WAV bytes and timing metadata.

    Pure functions with no exceptions - all errors returned as Result[T].
    """

    def __init__(self, sentence_gap: float = 0.2):
        """Initialize the assembler.

        Args:
            sentence_gap: Seconds of silence written after each segment. This is the
                main cadence control; it applies at every segment boundary including
                the last, so concatenated chunks keep a gap at their seam.
        """
        self.sentence_gap = max(0.0, sentence_gap)

    def silence_for(self, segment: SynthesizedSegment) -> bytes:
        """Silent PCM matching a segment's format, sized to the configured gap."""
        frames = int(segment.sample_rate * self.sentence_gap)
        return bytes(frames * segment.frame_size)

    def gap_duration(self) -> float:
        """Seconds of silence written after each segment."""
        return self.sentence_gap

    def to_wav(self, segments: Sequence[SynthesizedSegment]) -> Result[bytes]:
        """Assemble segments into a single WAV, with a gap after each one.

        Returns Result with WAV bytes or error.
        """
        if not segments:
            return Result.failure(audio_generation_error("No segments to assemble"))

        first = segments[0]
        if not first.frame_size or not first.sample_rate:
            return Result.failure(audio_generation_error(f"Segment has invalid audio format: {first.sample_rate}Hz"))

        mismatched = [s for s in segments if not s.matches_format(first)]
        if mismatched:
            return Result.failure(
                audio_generation_error(
                    f"Cannot assemble segments with differing formats "
                    f"({len(mismatched)} of {len(segments)} do not match {first.sample_rate}Hz)"
                )
            )

        try:
            silence = self.silence_for(first)
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wav_file:
                wav_file.setframerate(first.sample_rate)
                wav_file.setsampwidth(first.sample_width)
                wav_file.setnchannels(first.channels)

                for segment in segments:
                    wav_file.writeframes(segment.pcm)
                    if silence:
                        wav_file.writeframes(silence)

            return Result.success(buffer.getvalue())

        except Exception as e:
            return Result.from_exception(e, ErrorCode.AUDIO_GENERATION_FAILED, retryable=False)

    def to_timed_segments(
        self,
        segments: Sequence[SynthesizedSegment],
        chunk_index: int,
        start_time: float,
        first_sentence_index: int = 0,
    ) -> tuple[list[TextSegment], float]:
        """Map segments onto the timeline using their measured durations.

        The gap after each segment is part of the elapsed time but not part of the
        segment's own duration, so highlighting clears at the end of the speech
        rather than lingering through the pause.

        Returns the timed segments and the time immediately after the last gap.
        """
        timed: list[TextSegment] = []
        cursor = start_time

        for offset, segment in enumerate(segments):
            timed.append(
                TextSegment(
                    text=segment.text,
                    start_time=cursor,
                    duration=segment.duration,
                    segment_type="sentence",
                    chunk_index=chunk_index,
                    sentence_index=first_sentence_index + offset,
                )
            )
            cursor += segment.duration + self.sentence_gap

        return timed, cursor
