# infrastructure/tts/gemini_tts_provider.py
"""
Enhanced Gemini TTS provider with audiobook-quality features
"""
from typing import List, Tuple, Optional, Dict
import re
import json
import os
import wave
import struct
import asyncio
import concurrent.futures
from google import genai
from google.genai import types

from domain.interfaces import ITTSEngine, ITimestampedTTSEngine
from domain.models import TextSegment
from domain.errors import Result, tts_engine_error


class GeminiTTSProvider(ITimestampedTTSEngine):
    """
    Enhanced Gemini 2.5 TTS with audiobook features:
    - Multiple voice personas for different content types
    - Advanced timing estimation
    - Natural language style control
    """

    # Content-aware styling for different document types
    DOCUMENT_STYLES = {
        "research_paper": {
            "narrator": "clearly and informatively",
            "technical": "precisely and methodically", 
            "emphasis": "with clear emphasis",
            "dialogue": "naturally"
        },
        "literature_review": {
            "narrator": "thoughtfully and analytically",
            "technical": "carefully and systematically",
            "emphasis": "with scholarly emphasis", 
            "dialogue": "conversationally"
        },
        "general": {
            "narrator": "naturally and clearly",
            "technical": "clearly and slowly",
            "emphasis": "with emphasis",
            "dialogue": "conversationally"
        }
    }

    def __init__(
        self, 
        model_name: str, 
        api_key: str,
        voice_name: str,
        document_type: str,
        min_request_interval: float,
        max_concurrent_requests: int,
        requests_per_minute: int
    ):
        if not api_key:
            raise ValueError("API key required for Gemini TTS")

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.configured_voice = voice_name  # Voice from environment config
        self.document_type = document_type  # Content type for styling
        
        # Content-aware style mappings (single voice, different styles)
        self.content_styles = self._get_content_styles_for_document_type(document_type)

        # Advanced timing estimation parameters
        self.base_wpm = 155  # Audiobook standard
        self.punctuation_pauses = {
            '.': 0.4, '!': 0.4, '?': 0.4,
            ',': 0.2, ';': 0.3, ':': 0.3,
            '—': 0.3, '...': 0.6
        }
        
        # Optimized rate limiting parameters
        self.min_request_interval = min_request_interval  # Config-driven rate limiting
        self.max_concurrent_segments = max_concurrent_requests  # Config-driven concurrency
        self.requests_per_minute = requests_per_minute  # Official rate limit
        self.segment_semaphore = asyncio.Semaphore(self.max_concurrent_segments)
        
        print(f"🚀 GeminiTTSProvider: Optimized rate limiting - {requests_per_minute} RPM, {min_request_interval}s intervals, {max_concurrent_requests} concurrent")

    def _get_content_styles_for_document_type(self, document_type: str) -> Dict[str, str]:
        """Get content styles based on document type"""
        styles = self.DOCUMENT_STYLES.get(document_type, self.DOCUMENT_STYLES["general"])
        print(f"✅ Using {document_type} content styles with voice '{self.configured_voice}'")
        return styles

    def generate_audio_data(self, text_to_speak: str) -> Result[bytes]:
        """Generate standard audio"""
        try:
            audio_data = self._generate_with_content_style(text_to_speak, "narrator")
            if not audio_data:
                return Result.failure(tts_engine_error("No audio data generated"))
            return Result.success(audio_data)
        except Exception as e:
            return Result.failure(tts_engine_error(f"Audio generation failed: {str(e)}"))

    async def generate_audio_data_async(self, text_to_speak: str) -> Result[bytes]:
        """Generate audio data asynchronously using internal async infrastructure"""
        try:
            # Use the async segment processing for a single chunk
            # This leverages our existing async infrastructure 
            segments = [{'text': text_to_speak, 'content_type': 'narrator', 'type': 'narrative'}]
            
            # Create a single async task for this text
            async with self.segment_semaphore:
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    audio_data = await loop.run_in_executor(
                        executor,
                        self._generate_with_content_style,
                        text_to_speak,
                        "narrator"
                    )
                
                # Add rate limiting delay based on configuration
                await asyncio.sleep(self.min_request_interval)
                
                if not audio_data:
                    return Result.failure(tts_engine_error("No audio data generated"))
                return Result.success(audio_data)
                
        except Exception as e:
            return Result.failure(tts_engine_error(f"Async audio generation failed: {str(e)}"))

    def generate_audio_with_timestamps(self, text_to_speak: str) -> Result[Tuple[bytes, List[TextSegment]]]:
        """
        Generate audio with intelligent content-aware processing using async segment processing
        """
        try:
            # Analyze content and split into segments with appropriate personas
            segments = self._analyze_and_segment_content(text_to_speak)

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
            
            duration = self._calculate_precise_duration(
                seg_data['text'],
                seg_data['content_type']
            )
            
            audio_chunks.append(audio_data)
            
            timing_segments.append(TextSegment(
                text=self._clean_for_display(seg_data['text']),
                start_time=current_time,
                duration=duration,
                segment_type=seg_data['type'],
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
                    self._generate_with_content_style,
                    seg_data['text'],
                    seg_data['content_type']
                )
            
            # Add rate limiting delay based on configuration  
            await asyncio.sleep(self.min_request_interval)
            
            return audio_data, seg_data

    def _generate_with_content_style(self, text: str, content_type: str) -> bytes:
        """Generate audio with content-aware styling using single voice"""
        style = self.content_styles.get(content_type, self.content_styles["narrator"])
        
        # Enhance text with natural language style using configured voice
        styled_text = f"Say {style}: {text}"
        
        # Use configured voice for all content
        voice_config = {
            "voice": self.configured_voice,
            "style": style,
            "rate": "medium"  # Consistent rate for single voice
        }

        return self._generate_with_retry(styled_text, voice_config)

    def _generate_with_retry(self, styled_text: str, voice_config: dict, max_retries: int = 3) -> bytes:
        """Generate audio with exponential backoff retry logic"""
        import time
        
        for attempt in range(max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=styled_text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=voice_config['voice']
                                )
                            )
                        )
                    )
                )

                if response.candidates and response.candidates[0].content.parts:
                    raw_audio_data = response.candidates[0].content.parts[0].inline_data.data
                    # Convert raw audio to proper WAV format
                    if attempt > 0:
                        print(f"✅ Retry successful after {attempt} attempts")
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
                        
                        print(f"🚀 Rate limited (attempt {attempt + 1}/{max_retries + 1}). Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        print(f"❌ Max retries ({max_retries}) exceeded. Rate limit persists.")
                        
                # For non-rate-limit errors, don't retry
                print(f"Error generating audio: {e}")
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


    def _analyze_and_segment_content(self, text: str) -> List[Dict]:
        """
        Intelligently segment content and assign voice personas
        """
        segments = []

        # Split into sentences first
        sentences = self._split_into_sentences(text)

        for sentence in sentences:
            # Determine content type and appropriate persona
            if self._is_technical_content(sentence):
                content_type = "technical"
                seg_type = "technical"
            elif self._is_emphasis_needed(sentence):
                content_type = "emphasis"
                seg_type = "emphasis"
            elif self._is_dialogue(sentence):
                content_type = "dialogue"
                seg_type = "dialogue"
            else:
                content_type = "narrator"
                seg_type = "narrative"

            segments.append({
                'text': sentence,
                'content_type': content_type,
                'type': seg_type
            })

        return segments

    def _calculate_precise_duration(self, text: str, content_type: str) -> float:
        """
        Calculate duration with content-type adjustments using single voice
        """
        # Clean text for word counting
        clean_text = re.sub(r'<[^>]+>', '', text)
        words = clean_text.split()
        word_count = len(words)

        # Consistent rate for single voice with slight content adjustments
        rate_adjustment = {
            "technical": 1.1,    # Slightly slower for technical content
            "emphasis": 1.05,    # Slightly slower for emphasis
            "dialogue": 1.0,     # Normal rate for dialogue
            "narrator": 1.0      # Normal rate for narrative
        }.get(content_type, 1.0)

        # Calculate base duration
        base_duration = (word_count / self.base_wpm) * 60 * rate_adjustment

        # Add punctuation pauses
        pause_time = 0.0
        for punct, pause in self.punctuation_pauses.items():
            pause_time += text.count(punct) * pause

        # Add complexity adjustments
        complexity_bonus = 0.0

        # Technical terms (words with numbers, capitals, long words)
        technical_pattern = r'\b(?:[A-Z]{2,}|\w*\d\w*|\w{10,})\b'
        technical_matches = re.findall(technical_pattern, clean_text)
        complexity_bonus += len(technical_matches) * 0.2

        # Parenthetical content
        paren_content = re.findall(r'\([^)]+\)', text)
        complexity_bonus += len(paren_content) * 0.3

        total_duration = base_duration + pause_time + complexity_bonus

        # Ensure minimum duration
        return max(total_duration, 0.5)

    def _is_technical_content(self, text: str) -> bool:
        """Detect technical content requiring slower, clearer delivery"""
        technical_indicators = [
            r'\b(?:equation|formula|algorithm|theorem|proof)\b',
            r'\b[A-Z]{3,}\b',  # Acronyms
            r'\b\d+\.?\d*\s*(?:percent|%|Hz|kHz|MHz|GB|MB)\b',
            r'(?:=|<|>|≤|≥|±)',  # Mathematical operators
            r'\bF\(\d+,\s*\d+\)',  # Statistics
        ]

        for pattern in technical_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _is_emphasis_needed(self, text: str) -> bool:
        """Detect content needing emphasis"""
        emphasis_indicators = [
            r'\b(?:significant|important|crucial|essential|key|primary)\b',
            r'\b(?:however|therefore|consequently|nevertheless)\b',
            r'\b(?:conclusion|summary|finding|result)\b',
        ]

        for pattern in emphasis_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _is_dialogue(self, text: str) -> bool:
        """Detect dialogue or quoted content"""
        return bool(re.search(r'[""].*[""]', text))

    def _split_into_sentences(self, text: str) -> List[str]:
        """Smart sentence splitting preserving context"""
        # Don't split on abbreviations
        text = re.sub(r'\b(?:Dr|Mr|Mrs|Ms|Prof|Sr|Jr)\.\s*', r'\g<0>@@@', text)

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

        # Restore abbreviations
        sentences = [s.replace('@@@', '') for s in sentences]

        return [s.strip() for s in sentences if s.strip()]

    def _clean_for_display(self, text: str) -> str:
        """Clean text for display"""
        # Remove SSML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove style instructions
        text = re.sub(r'^Say \w+:\s*', '', text)
        return text.strip()

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
            print(f"Warning: Failed to convert audio to WAV format: {e}")
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
                            else:
                                print(f"Warning: Audio chunk format mismatch, skipping chunk")
                    except Exception as e:
                        print(f"Warning: Failed to read audio chunk: {e}")
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
            print(f"Error combining audio chunks: {e}")
            # Fallback: try simple concatenation for emergency cases
            print("Falling back to simple concatenation")
            return b''.join(chunks)

    def get_output_format(self) -> str:
        return "wav"

    def supports_ssml(self) -> bool:
        return True
