"""Tests for AudioAssembler.

The assembler is the single owner of gap policy and container writing (issue #64).
The property that matters most is that the timeline it reports and the audio it
writes use the same gaps - when those lived in different layers, they disagreed.
"""

import io
import wave

import pytest

from domain.audio.audio_assembler import AudioAssembler
from domain.models import SynthesizedSegment

SAMPLE_RATE = 100  # cheap frame math: 1 frame = 10ms


def _segment(text: str = "A sentence.", frames: int = 100, sample_rate: int = SAMPLE_RATE) -> SynthesizedSegment:
    """16-bit mono segment of a known length."""
    return SynthesizedSegment(
        text=text,
        pcm=b"\x01\x00" * frames,
        sample_rate=sample_rate,
        sample_width=2,
        channels=1,
    )


def _frames_of(wav_bytes: bytes) -> int:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        return wav.getnframes()


class TestSegmentDuration:
    """Duration is measured from the samples, never estimated."""

    def test_duration_from_sample_count(self) -> None:
        """Sample count over sample rate, nothing else."""
        assert _segment(frames=150).duration == pytest.approx(1.5)

    def test_zero_length_segment_has_zero_duration(self) -> None:
        """No samples means no time."""
        assert _segment(frames=0).duration == 0.0

    def test_degenerate_format_does_not_divide_by_zero(self) -> None:
        """A malformed segment must not blow up the timeline."""
        segment = SynthesizedSegment(text="x", pcm=b"", sample_rate=0, sample_width=0, channels=0)

        assert segment.duration == 0.0


class TestWavAssembly:
    """Assembling segments into a container."""

    def test_gap_written_after_every_segment(self) -> None:
        """Including the last, so concatenated chunks keep a gap at their seam."""
        assembler = AudioAssembler(sentence_gap=0.5)  # 50 frames

        wav = assembler.to_wav([_segment(frames=100) for _ in range(3)])

        assert wav.is_success
        assert wav.value is not None
        assert _frames_of(wav.value) == 3 * (100 + 50)

    def test_zero_gap_writes_only_speech(self) -> None:
        """A zero gap means the audio is exactly the speech frames."""
        assembler = AudioAssembler(sentence_gap=0.0)

        wav = assembler.to_wav([_segment(frames=100), _segment(frames=100)])

        assert wav.is_success
        assert wav.value is not None
        assert _frames_of(wav.value) == 200

    def test_negative_gap_is_clamped(self) -> None:
        """A negative gap would otherwise mean negative silence."""
        assembler = AudioAssembler(sentence_gap=-1.0)

        assert assembler.gap_duration() == 0.0

    def test_empty_segments_is_a_failure(self) -> None:
        """There is no meaningful empty WAV to return."""
        assert AudioAssembler().to_wav([]).is_failure

    def test_mismatched_formats_rejected(self) -> None:
        """Concatenating different sample rates would silently change pitch."""
        assembler = AudioAssembler()

        result = assembler.to_wav([_segment(sample_rate=100), _segment(sample_rate=200)])

        assert result.is_failure
        assert result.error is not None
        assert "differing formats" in (result.error.details or "")

    def test_output_preserves_format(self) -> None:
        """The container must describe the samples it holds."""
        assembler = AudioAssembler(sentence_gap=0.1)

        wav = assembler.to_wav([_segment()])

        assert wav.value is not None
        with wave.open(io.BytesIO(wav.value), "rb") as out:
            assert out.getframerate() == SAMPLE_RATE
            assert out.getsampwidth() == 2
            assert out.getnchannels() == 1


class TestTimeline:
    """Mapping segments onto the read-along timeline."""

    def test_segments_are_spaced_by_their_real_durations(self) -> None:
        """A short and a long sentence must not get the same slot."""
        assembler = AudioAssembler(sentence_gap=0.0)

        timed, end = assembler.to_timed_segments(
            [_segment("Short.", frames=20), _segment("A much longer sentence.", frames=200)],
            chunk_index=0,
            start_time=0.0,
        )

        assert timed[0].start_time == pytest.approx(0.0)
        assert timed[0].duration == pytest.approx(0.2)
        assert timed[1].start_time == pytest.approx(0.2)
        assert timed[1].duration == pytest.approx(2.0)
        assert end == pytest.approx(2.2)

    def test_gap_advances_the_clock_but_is_not_part_of_a_segment(self) -> None:
        """Highlighting should clear at the end of speech, not linger through the pause."""
        assembler = AudioAssembler(sentence_gap=0.5)

        timed, end = assembler.to_timed_segments(
            [_segment(frames=100), _segment(frames=100)], chunk_index=0, start_time=0.0
        )

        assert timed[0].duration == pytest.approx(1.0)  # speech only
        assert timed[1].start_time == pytest.approx(1.5)  # speech + gap
        assert end == pytest.approx(3.0)

    def test_timeline_matches_assembled_audio_duration(self) -> None:
        """The whole point: the reported timeline and the real audio agree.

        This is what the old even-split could not guarantee.
        """
        assembler = AudioAssembler(sentence_gap=0.3)
        segments = [_segment("One.", frames=37), _segment("Two.", frames=211), _segment("Three.", frames=94)]

        _, end = assembler.to_timed_segments(segments, chunk_index=0, start_time=0.0)
        wav = assembler.to_wav(segments)

        assert wav.value is not None
        assert _frames_of(wav.value) / SAMPLE_RATE == pytest.approx(end)

    def test_start_time_offsets_continue_across_chunks(self) -> None:
        """Later chunks continue the timeline rather than restarting it."""
        assembler = AudioAssembler(sentence_gap=0.0)

        timed, end = assembler.to_timed_segments([_segment(frames=100)], chunk_index=2, start_time=10.0)

        assert timed[0].start_time == pytest.approx(10.0)
        assert timed[0].chunk_index == 2
        assert end == pytest.approx(11.0)

    def test_sentence_indices_are_sequential(self) -> None:
        """Indices continue from the offset the caller supplies."""
        assembler = AudioAssembler()

        timed, _ = assembler.to_timed_segments(
            [_segment() for _ in range(3)], chunk_index=0, start_time=0.0, first_sentence_index=5
        )

        assert [t.sentence_index for t in timed] == [5, 6, 7]

    def test_segment_text_is_carried_through(self) -> None:
        """Read-along needs the text, and it must be the text that made the audio."""
        assembler = AudioAssembler()

        timed, _ = assembler.to_timed_segments(
            [_segment("The first one."), _segment("The second one.")], chunk_index=0, start_time=0.0
        )

        assert [t.text for t in timed] == ["The first one.", "The second one."]
