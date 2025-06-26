# infrastructure/tts/gemini_tts_provider.py
"""
Simplified Gemini TTS provider with consistent voice delivery
"""
from typing import List, Tuple, Optional, Dict
import re
import time
import wave
import struct
import asyncio
import concurrent.futures
from google import genai
from google.genai import types

from domain.interfaces import ITTSEngine, ITimestampedTTSEngine
from domain.models import TextSegment
from domain.errors import Result, tts_engine_error
from .text_segmenter import TextSegmenter


class GeminiTTSProvider(ITimestampedTTSEngine):
    """
    Simplified Gemini 2.5 TTS provider with consistent voice delivery
    """

    def __init__(
        self, 
        model_name: str, 
        api_key: str,
        voice_name: str,
        min_request_interval: float,
        max_concurrent_requests: int,
        requests_per_minute: int
    ):
        if not api_key:
            raise ValueError("API key required for Gemini TTS")

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.configured_voice = voice_name

        # Shared text processing utilities
        self.text_segmenter = TextSegmenter(base_wpm=155)
        
        # Gemini-specific rate limiting parameters
        self.min_request_interval = min_request_interval
        self.max_concurrent_segments = max_concurrent_requests
        self.requests_per_minute = requests_per_minute
        self.segment_semaphore = asyncio.Semaphore(self.max_concurrent_segments)

    def generate_audio_data(self, text_to_speak: str) -> Result[bytes]:
        """Generate standard audio"""
        try:
            audio_data = self._generate_audio(text_to_speak)
            if not audio_data:
                return Result.failure(tts_engine_error("No audio data generated"))
            return Result.success(audio_data)
        except Exception as e:
            return Result.failure(tts_engine_error(f"Audio generation failed: {str(e)}"))

    async def generate_audio_data_async(self, text_to_speak: str) -> Result[bytes]:
        """Generate audio data asynchronously"""
        try:
            async with self.segment_semaphore:
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    audio_data = await loop.run_in_executor(
                        executor,
                        self._generate_audio,
                        text_to_speak
                    )
                
                # Add rate limiting delay
                await asyncio.sleep(self.min_request_interval)
                
                if not audio_data:
                    return Result.failure(tts_engine_error("No audio data generated"))
                return Result.success(audio_data)
                
        except Exception as e:
            return Result.failure(tts_engine_error(f"Async audio generation failed: {str(e)}"))

    def generate_audio_with_timestamps(self, text_to_speak: str) -> Result[Tuple[bytes, List[TextSegment]]]:
        """
        Generate audio with simple sentence-based segmentation
        """
        try:
            # Simple sentence segmentation - no persona switching
            segments = self._split_into_segments(text_to_speak)

            # Generate audio for segments concurrently using asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                audio_chunks, timing_segments = loop.run_until_complete(
                    self._generate_segments_async(segments)
                )
            finally:
                loop.close()

            # Combine audio chunks
            combined_audio = self._combine_audio_chunks(audio_chunks)

            if not combined_audio:
                return Result.failure(tts_engine_error("Failed to combine audio chunks"))

            return Result.success((combined_audio, timing_segments))

        except Exception as e:
            return Result.failure(tts_engine_error(f"Timestamped audio generation failed: {str(e)}"))

    async def _generate_segments_async(self, segments: List[Dict]) -> Tuple[List[bytes], List[TextSegment]]:
        """
        Generate audio for segments concurrently with rate limiting
        """
        # Create tasks for concurrent processing
        tasks = []
        for i, seg_data in enumerate(segments):
            task = self._generate_segment_async(seg_data, i)
            tasks.append(task)
        
        # Execute all tasks concurrently with semaphore control
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results maintaining order
        audio_chunks = []
        timing_segments = []
        current_time = 0.0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                raise result
            
            audio_data, seg_data = result
            
            if not audio_data:
                raise Exception(f"Failed to generate audio for segment: {seg_data['text'][:50]}...")
            
            duration = self.text_segmenter.calculate_duration(seg_data['text'])
            
            audio_chunks.append(audio_data)
            
            timing_segments.append(TextSegment(
                text=seg_data['text'],
                start_time=current_time,
                duration=duration,
                segment_type='narrative',
                chunk_index=0,
                sentence_index=i
            ))
            
            current_time += duration
        
        return audio_chunks, timing_segments

    async def _generate_segment_async(self, seg_data: Dict, index: int) -> Tuple[bytes, Dict]:
        """
        Generate audio for a single segment with async rate limiting
        """
        async with self.segment_semaphore:
            # Use thread pool for blocking API call
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                audio_data = await loop.run_in_executor(
                    executor,
                    self._generate_audio,
                    seg_data['text']
                )
            
            # Add rate limiting delay based on configuration  
            await asyncio.sleep(self.min_request_interval)
            
            return audio_data, seg_data

    def _generate_audio(self, text: str) -> bytes:
        """Generate audio with consistent voice - no style switching"""
        return self._generate_with_retry(text)

    def _generate_with_retry(self, text: str, max_retries: int = 3) -> bytes:
        """Generate audio with exponential backoff retry logic"""
        import time
        
        for attempt in range(max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=self.configured_voice
                                )
                            )
                        )
                    )
                )

                if response.candidates and response.candidates[0].content.parts:
                    raw_audio_data = response.candidates[0].content.parts[0].inline_data.data
                    # Convert raw audio to proper WAV format
                    return self._convert_to_wav(raw_audio_data)

            except Exception as e:
                error_str = str(e)
                
                # Check if this is a rate limit error (429)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < max_retries:
                        # Extract retry delay from error if available
                        retry_delay = self._extract_retry_delay(error_str)
                        if retry_delay is None:
                            # Exponential backoff: 5s, 15s, 45s
                            retry_delay = 5 * (3 ** attempt)
                        
                        time.sleep(retry_delay)
                        continue
                        
                # For non-rate-limit errors, don't retry
                break

        return b""
    
    def _extract_retry_delay(self, error_str: str) -> Optional[int]:
        """Extract retry delay from Gemini error response"""
        import re
        
        # Look for retryDelay in the error message
        match = re.search(r"retryDelay.*?(\d+)s", error_str)
        if match:
            return int(match.group(1))
        return None


    def _split_into_segments(self, text: str) -> List[Dict]:
        """Simple sentence-based segmentation using shared utilities"""
        segments = []
        sentences = self.text_segmenter.split_into_sentences(text)
        
        for sentence in sentences:
            segments.append({
                'text': sentence,
                'content_type': 'narrative',
                'type': 'narrative'
            })
        
        return segments

    def _convert_to_wav(self, raw_audio_data: bytes) -> bytes:
        """Convert raw audio data from Gemini to proper WAV format"""
        if not raw_audio_data:
            return b""
        
        try:
            # Gemini TTS typically returns PCM16 at 22050 Hz, mono
            # These are common parameters, but may need adjustment
            sample_rate = 22050
            channels = 1
            sample_width = 2  # 16-bit = 2 bytes per sample
            
            # Create WAV header manually
            # Calculate sizes
            data_size = len(raw_audio_data)
            file_size = data_size + 36  # 44 - 8 bytes for RIFF header
            
            # Create WAV header
            wav_header = struct.pack('<4sI4s4sIHHIIHH4sI',
                b'RIFF',           # Chunk ID
                file_size,         # Chunk size
                b'WAVE',           # Format
                b'fmt ',           # Subchunk1 ID
                16,                # Subchunk1 size (PCM)
                1,                 # Audio format (PCM)
                channels,          # Number of channels
                sample_rate,       # Sample rate
                sample_rate * channels * sample_width,  # Byte rate
                channels * sample_width,  # Block align
                sample_width * 8,  # Bits per sample
                b'data',           # Subchunk2 ID
                data_size          # Subchunk2 size
            )
            
            return wav_header + raw_audio_data
            
        except Exception as e:
            # Return raw data as fallback
            return raw_audio_data

    def _combine_audio_chunks(self, chunks: List[bytes]) -> bytes:
        """Properly combine WAV audio chunks by merging their data sections"""
        if not chunks:
            return b""
        
        if len(chunks) == 1:
            return chunks[0]
        
        try:
            import io
            import wave
            
            # Parse the first WAV file to get format info
            first_wav = io.BytesIO(chunks[0])
            with wave.open(first_wav, 'rb') as first_wave:
                # Get audio parameters from first file
                channels = first_wave.getnchannels()
                sampwidth = first_wave.getsampwidth()
                framerate = first_wave.getframerate()
                
                # Collect all audio data
                combined_data = b""
                total_frames = 0
                
                # Add data from first file
                first_wav.seek(0)
                with wave.open(first_wav, 'rb') as w:
                    combined_data += w.readframes(w.getnframes())
                    total_frames += w.getnframes()
                
                # Add data from remaining files
                for chunk in chunks[1:]:
                    chunk_io = io.BytesIO(chunk)
                    try:
                        with wave.open(chunk_io, 'rb') as w:
                            # Verify format compatibility
                            if (w.getnchannels() == channels and 
                                w.getsampwidth() == sampwidth and
                                w.getframerate() == framerate):
                                combined_data += w.readframes(w.getnframes())
                                total_frames += w.getnframes()
                    except Exception:
                        continue
                
                # Create combined WAV file
                output_buffer = io.BytesIO()
                with wave.open(output_buffer, 'wb') as combined_wave:
                    combined_wave.setnchannels(channels)
                    combined_wave.setsampwidth(sampwidth)
                    combined_wave.setframerate(framerate)
                    combined_wave.writeframes(combined_data)
                
                return output_buffer.getvalue()
                
        except Exception as e:
            # Fallback: try simple concatenation for emergency cases
            return b''.join(chunks)

    def get_output_format(self) -> str:
        return "wav"

    def supports_ssml(self) -> bool:
        return True
