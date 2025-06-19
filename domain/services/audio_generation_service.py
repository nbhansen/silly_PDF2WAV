"""
This service orchestrates the process of generating audio from text chunks
by using smart routing between async (cloud) and sync (local) TTS engines.
"""

import os
import time
from typing import List, Tuple, Optional
from ..interfaces import ITimingStrategy, ITTSEngine
from ..models import TimedAudioResult, TextSegment, TimingMetadata


class AudioGenerationService:
    """
    A service that generates audio with timing information by intelligently
    choosing between async (cloud TTS) and sync (local TTS) processing.
    """

    def __init__(self, timing_strategy: ITimingStrategy):
        """
        Initializes the AudioGenerationService with a specific timing strategy.

        Args:
            timing_strategy (ITimingStrategy): An object that implements the
                                               ITimingStrategy interface. This
                                               strategy will be used for sync
                                               processing and timing generation.
        """
        if not isinstance(timing_strategy, ITimingStrategy):
            raise TypeError("timing_strategy must be an instance of ITimingStrategy")
        self.timing_strategy = timing_strategy

    def should_use_async(self, tts_engine: ITTSEngine) -> bool:
        """
        Determine if we should use async generation based on TTS engine type.
        
        Args:
            tts_engine: The TTS engine instance
            
        Returns:
            bool: True if async should be used (cloud services), False for sync (local)
        """
        engine_name = tts_engine.__class__.__name__.lower()
        
        # Cloud services that benefit from async processing (rate limits, network delays)
        cloud_engines = [
            'gemini',      # Google Gemini TTS
            'openai',      # OpenAI TTS
            'elevenlabs',  # ElevenLabs TTS
            'azure',       # Azure Cognitive Services
            'aws',         # AWS Polly
            'google'       # Google Cloud TTS
        ]
        
        # Check if this is a cloud service
        is_cloud_service = any(cloud in engine_name for cloud in cloud_engines)
        
        if is_cloud_service:
            print(f"🌐 Detected cloud TTS service: {engine_name}")
        else:
            print(f"💻 Detected local TTS service: {engine_name}")
            
        return is_cloud_service

    def generate_audio_with_timing(self, text_chunks: List[str], output_filename: str, 
                                 output_dir: str, tts_engine: ITTSEngine) -> TimedAudioResult:
        """
        Generates an audio file with corresponding timing data for text chunks.
        
        Smart routing: Uses async for cloud services, sync for local services.

        Args:
            text_chunks (List[str]): The list of text chunks to convert to speech.
            output_filename (str): The desired base name for the output audio files.
            output_dir (str): Directory where audio files should be saved.
            tts_engine (ITTSEngine): The TTS engine to use for generation.

        Returns:
            TimedAudioResult: An object containing the paths to generated
                              audio files and timing data.
        """
        if not text_chunks:
            print("AudioGenerationService: No text chunks provided")
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

        # Smart routing based on TTS engine type
        if self.should_use_async(tts_engine):
            return self._generate_with_async_service(text_chunks, output_filename, output_dir, tts_engine)
        else:
            return self._generate_with_sync_strategy(text_chunks, output_filename, output_dir, tts_engine)

    def _generate_with_async_service(self, text_chunks: List[str], output_filename: str, 
                                   output_dir: str, tts_engine: ITTSEngine) -> TimedAudioResult:
        """
        Generate audio using the async service (for cloud TTS engines).
        
        Args:
            text_chunks: Text chunks to process
            output_filename: Base filename for output
            output_dir: Output directory
            tts_engine: TTS engine instance
            
        Returns:
            TimedAudioResult with audio files and timing data
        """
        print(f"🌐 Using ASYNC generation for cloud TTS: {tts_engine.__class__.__name__}")
        
        try:
            # Use the async audio generation service
            from .async_audio_generation_service import run_async_audio_generation
            
            # Generate audio files asynchronously (handles rate limits, concurrency)
            audio_files, combined_mp3 = run_async_audio_generation(
                text_chunks=text_chunks,
                output_name=output_filename,
                output_dir=output_dir,
                tts_engine=tts_engine,
                max_concurrent=4  # Reasonable concurrency for cloud APIs
            )
            
            if not audio_files:
                print("AudioGenerationService: Async generation produced no audio files")
                return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)
            
            # Generate timing data by analyzing the created audio files
            timing_data = self._create_timing_data_from_audio_files(
                audio_files, text_chunks, output_dir
            )
            
            # Convert file paths to just filenames for storage
            audio_filenames = [os.path.basename(f) for f in audio_files]
            combined_filename = os.path.basename(combined_mp3) if combined_mp3 else None
            
            print(f"AudioGenerationService: Async generation completed - {len(audio_filenames)} files, timing: {timing_data is not None}")
            
            return TimedAudioResult(
                audio_files=audio_filenames,
                combined_mp3=combined_filename,
                timing_data=timing_data
            )
            
        except Exception as e:
            print(f"AudioGenerationService: Async generation failed: {e}")
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

    def _generate_with_sync_strategy(self, text_chunks: List[str], output_filename: str, 
                                   output_dir: str, tts_engine: ITTSEngine) -> TimedAudioResult:
        """
        Generate audio using the sync timing strategy (for local TTS engines).
        
        Args:
            text_chunks: Text chunks to process
            output_filename: Base filename for output
            output_dir: Output directory (not used by strategy)
            tts_engine: TTS engine instance (not used by strategy)
            
        Returns:
            TimedAudioResult with audio files and timing data
        """
        print(f"💻 Using SYNC generation for local TTS: {tts_engine.__class__.__name__}")
        
        try:
            # Delegate to the existing timing strategy (which handles everything)
            result = self.timing_strategy.generate_with_timing(text_chunks, output_filename)
            
            print(f"AudioGenerationService: Sync generation completed - {len(result.audio_files) if result.audio_files else 0} files, timing: {result.timing_data is not None}")
            
            return result
            
        except Exception as e:
            print(f"AudioGenerationService: Sync generation failed: {e}")
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

    def _create_timing_data_from_audio_files(self, audio_files: List[str], text_chunks: List[str], 
                                           output_dir: str) -> Optional[TimingMetadata]:
        """
        Create timing data by analyzing generated audio files.
        
        This is used for async-generated audio where we need to extract timing info
        after the files are created.
        
        Args:
            audio_files: List of audio file paths
            text_chunks: Original text chunks
            output_dir: Directory containing audio files
            
        Returns:
            TimingMetadata with timing information, or None if extraction fails
        """
        try:
            import wave
            from .text_cleaning_service import TextCleaningService
            
            # Initialize text cleaner for sentence splitting
            text_cleaner = TextCleaningService()
            
            # Split text chunks into sentences
            all_sentences = []
            for chunk in text_chunks:
                sentences = text_cleaner.split_into_sentences(chunk)
                all_sentences.extend(sentences)
            
            if len(audio_files) != len(all_sentences):
                print(f"AudioGenerationService: Audio file count ({len(audio_files)}) doesn't match sentence count ({len(all_sentences)})")
                # Fall back to basic estimation
                return self._create_estimated_timing_data(text_chunks)
            
            # Extract actual durations from audio files
            timing_segments = []
            cumulative_time = 0.0
            
            for i, (audio_file, sentence) in enumerate(zip(audio_files, all_sentences)):
                audio_path = os.path.join(output_dir, os.path.basename(audio_file))
                
                # Try to get actual duration from audio file
                duration = self._get_audio_duration(audio_path)
                if duration is None:
                    # Fall back to estimation
                    duration = self._estimate_sentence_duration(sentence)
                
                # Clean sentence text for display
                clean_text = text_cleaner.strip_ssml(sentence) if hasattr(text_cleaner, 'strip_ssml') else sentence
                
                segment = TextSegment(
                    text=clean_text,
                    start_time=cumulative_time,
                    duration=duration,
                    segment_type="sentence",
                    chunk_index=i // 10,  # Rough grouping - 10 sentences per chunk
                    sentence_index=i
                )
                
                timing_segments.append(segment)
                cumulative_time += duration
            
            # Create timing metadata
            timing_metadata = TimingMetadata(
                total_duration=cumulative_time,
                text_segments=timing_segments,
                audio_files=[os.path.basename(f) for f in audio_files]
            )
            
            print(f"AudioGenerationService: Created timing data with {len(timing_segments)} segments, total duration: {cumulative_time:.2f}s")
            return timing_metadata
            
        except Exception as e:
            print(f"AudioGenerationService: Failed to create timing data: {e}")
            return self._create_estimated_timing_data(text_chunks)

    def _create_estimated_timing_data(self, text_chunks: List[str]) -> Optional[TimingMetadata]:
        """
        Create estimated timing data when exact measurement fails.
        
        Args:
            text_chunks: Original text chunks
            
        Returns:
            TimingMetadata with estimated timing, or None if estimation fails
        """
        try:
            from .text_cleaning_service import TextCleaningService
            
            text_cleaner = TextCleaningService()
            timing_segments = []
            cumulative_time = 0.0
            
            for chunk_idx, chunk in enumerate(text_chunks):
                sentences = text_cleaner.split_into_sentences(chunk)
                
                for sent_idx, sentence in enumerate(sentences):
                    duration = self._estimate_sentence_duration(sentence)
                    clean_text = text_cleaner.strip_ssml(sentence) if hasattr(text_cleaner, 'strip_ssml') else sentence
                    
                    segment = TextSegment(
                        text=clean_text,
                        start_time=cumulative_time,
                        duration=duration,
                        segment_type="sentence",
                        chunk_index=chunk_idx,
                        sentence_index=sent_idx
                    )
                    
                    timing_segments.append(segment)
                    cumulative_time += duration
            
            timing_metadata = TimingMetadata(
                total_duration=cumulative_time,
                text_segments=timing_segments,
                audio_files=[]  # No specific audio file mapping available
            )
            
            print(f"AudioGenerationService: Created estimated timing data with {len(timing_segments)} segments")
            return timing_metadata
            
        except Exception as e:
            print(f"AudioGenerationService: Failed to create estimated timing data: {e}")
            return None

    def _get_audio_duration(self, audio_file_path: str) -> Optional[float]:
        """
        Get the duration of an audio file in seconds.
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            Duration in seconds, or None if extraction fails
        """
        try:
            import wave
            
            if not os.path.exists(audio_file_path):
                return None
                
            with wave.open(audio_file_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                
                if rate > 0:
                    duration = frames / float(rate)
                    return duration
                    
        except Exception as e:
            print(f"AudioGenerationService: Failed to get duration for {audio_file_path}: {e}")
            
        return None

    def _estimate_sentence_duration(self, sentence: str) -> float:
        """
        Estimate the duration of a sentence based on word count and complexity.
        
        Args:
            sentence: The sentence text
            
        Returns:
            Estimated duration in seconds
        """
        # Remove SSML tags for word counting
        import re
        clean_sentence = re.sub(r'<[^>]+>', '', sentence)
        
        # Count words
        word_count = len(clean_sentence.split())
        
        # Base rate: ~2.5 words per second for normal speech
        base_duration = word_count / 2.5
        
        # Add minimum duration
        min_duration = 0.5
        
        # Add pauses for punctuation
        pause_time = 0.0
        pause_time += sentence.count(',') * 0.2    # Comma pauses
        pause_time += sentence.count(';') * 0.3    # Semicolon pauses
        pause_time += sentence.count('.') * 0.4    # Period pauses
        pause_time += sentence.count('!') * 0.4    # Exclamation pauses
        pause_time += sentence.count('?') * 0.4    # Question pauses
        
        total_duration = max(base_duration + pause_time, min_duration)
        
        return total_duration

    # Legacy method for backward compatibility
    def generate_audio(self, text_chunks: List[str], output_name: str, output_dir: str) -> Tuple[List[str], Optional[str]]:
        """
        Legacy method for backward compatibility.
        Returns just audio files without timing data.
        
        Args:
            text_chunks: Text chunks to process
            output_name: Base name for output files
            output_dir: Output directory
            
        Returns:
            Tuple of (audio_files, combined_mp3_file)
        """
        # This would need a TTS engine, but legacy callers don't provide one
        # For now, delegate to timing strategy if it has this method
        if hasattr(self.timing_strategy, 'generate_audio'):
            return self.timing_strategy.generate_audio(text_chunks, output_name, output_dir)
        else:
            print("AudioGenerationService: Legacy generate_audio method not supported by timing strategy")
            return [], None