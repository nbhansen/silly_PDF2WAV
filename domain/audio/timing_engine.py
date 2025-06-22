# domain/audio/timing_engine.py - Unified Timing Engine
"""
Consolidated timing engine that unifies all timing strategies.
Replaces: GeminiTimestampStrategy, SentenceMeasurementStrategy, EnhancedTimingStrategy, TimingCalculator
"""

import os
import time
from typing import List, Optional
from abc import ABC, abstractmethod
from enum import Enum

from ..interfaces import ITTSEngine, ITimestampedTTSEngine, IFileManager
from ..text.text_pipeline import ITextPipeline
from ..models import TimedAudioResult, TextSegment, TimingMetadata
from ..errors import Result


class TimingMode(Enum):
    """Available timing modes"""
    ESTIMATION = "estimation"      # Fast, uses engine timestamps
    MEASUREMENT = "measurement"    # Accurate, measures actual duration
    HYBRID = "hybrid"             # Smart combination of both


class ITimingEngine(ABC):
    """Unified interface for timing generation"""
    
    @abstractmethod
    def generate_with_timing(self, text_chunks: List[str], output_filename: str) -> TimedAudioResult:
        """Generate audio with timing information"""
        pass


class TimingEngine(ITimingEngine):
    """
    Unified timing engine that consolidates all timing strategies.
    Uses strategy pattern internally but presents unified interface.
    """
    
    def __init__(
        self,
        tts_engine: ITTSEngine,
        file_manager: IFileManager,
        text_pipeline: Optional[ITextPipeline] = None,
        mode: TimingMode = TimingMode.ESTIMATION,
        measurement_interval: float = 0.8
    ):
        self.tts_engine = tts_engine
        self.file_manager = file_manager
        self.text_pipeline = text_pipeline
        self.mode = mode
        self.measurement_interval = measurement_interval
        self.last_api_call = 0.0
        
        # Validate mode compatibility
        if mode == TimingMode.ESTIMATION and not hasattr(tts_engine, 'generate_audio_with_timestamps'):
            print(f"Warning: {tts_engine.__class__.__name__} doesn't support estimation mode. Falling back to measurement.")
            self.mode = TimingMode.MEASUREMENT
    
    def generate_with_timing(self, text_chunks: List[str], output_filename: str) -> TimedAudioResult:
        """Main entry point - routes to appropriate timing strategy"""
        
        if self.mode == TimingMode.ESTIMATION:
            return self._generate_with_estimation(text_chunks, output_filename)
        elif self.mode == TimingMode.MEASUREMENT:
            return self._generate_with_measurement(text_chunks, output_filename)
        else:  # HYBRID
            return self._generate_with_hybrid(text_chunks, output_filename)
    
    def _generate_with_estimation(self, text_chunks: List[str], output_filename: str) -> TimedAudioResult:
        """Fast timing using engine-provided timestamps"""
        if not hasattr(self.tts_engine, 'generate_audio_with_timestamps'):
            return self._generate_with_measurement(text_chunks, output_filename)
        
        print("TimingEngine: Using estimation mode (fast)")
        
        # Enhance text with SSML if available
        if self.text_pipeline:
            enhanced_chunks = [self.text_pipeline.enhance_with_ssml(chunk) for chunk in text_chunks]
            full_text = " ".join(enhanced_chunks)
        else:
            full_text = " ".join(text_chunks)
        
        if not full_text.strip():
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)
        
        try:
            # Use engine's native timestamping
            result = self.tts_engine.generate_audio_with_timestamps(full_text)
            
            if result.is_failure:
                print(f"TimingEngine: Engine failed: {result.error}")
                return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)
            
            audio_data, text_segments = result.value
            
            if not audio_data:
                return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)
            
            # Save audio file
            audio_filename = f"{output_filename}_combined.mp3"
            audio_path = self.file_manager.save_output_file(audio_data, audio_filename)
            
            if not audio_path:
                return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)
            
            # Create timing metadata
            timing_metadata = None
            if text_segments:
                total_duration = max(seg.start_time + seg.duration for seg in text_segments) if text_segments else 0.0
                timing_metadata = TimingMetadata(
                    total_duration=total_duration,
                    text_segments=text_segments,
                    audio_files=[audio_filename]
                )
            
            return TimedAudioResult(
                audio_files=[audio_filename],
                combined_mp3=audio_filename,
                timing_data=timing_metadata
            )
            
        except Exception as e:
            print(f"TimingEngine: Estimation failed: {e}")
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)
    
    def _generate_with_measurement(self, text_chunks: List[str], output_filename: str) -> TimedAudioResult:
        """Accurate timing by measuring actual audio duration"""
        print("TimingEngine: Using measurement mode (accurate)")
        
        if not self.text_pipeline:
            print("Warning: No text pipeline available for measurement mode")
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)
        
        # Enhance text with SSML if available
        if self.text_pipeline:
            enhanced_chunks = [self.text_pipeline.enhance_with_ssml(chunk) for chunk in text_chunks]
            full_text = " ".join(enhanced_chunks)
        else:
            full_text = " ".join(text_chunks)
        
        # Split into sentences for individual processing
        sentences = self.text_pipeline.split_into_sentences(full_text)
        
        if not sentences:
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)
        
        # Smart batching for performance
        batch_size = min(15, max(5, len(sentences) // 10))
        sentence_batches = [sentences[i:i+batch_size] for i in range(0, len(sentences), batch_size)]
        
        print(f"TimingEngine: Processing {len(sentences)} sentences in {len(sentence_batches)} batches")
        
        temp_audio_files = []
        text_segments = []
        cumulative_time = 0.0
        
        for batch_idx, sentence_batch in enumerate(sentence_batches):
            try:
                # Apply rate limiting
                self._apply_rate_limit()
                
                # Generate audio for batch
                batch_text = " ".join(sentence_batch)
                result = self.tts_engine.generate_audio_data(batch_text)
                
                if result.is_success:
                    audio_data = result.value
                    temp_file = self.file_manager.save_temp_file(audio_data, suffix=".wav")
                    temp_audio_files.append(temp_file)
                    
                    # Measure batch duration
                    batch_duration = self._measure_audio_duration(temp_file)
                    
                    # Distribute duration across sentences by word count
                    total_words = sum(len(self.text_cleaning_service.strip_ssml(sent).split()) 
                                    for sent in sentence_batch)
                    
                    for i, sentence_text in enumerate(sentence_batch):
                        clean_text = self.text_cleaning_service.strip_ssml(sentence_text)
                        word_count = len(clean_text.split())
                        
                        if total_words > 0:
                            sentence_duration = (word_count / total_words) * batch_duration
                        else:
                            sentence_duration = batch_duration / len(sentence_batch)
                        
                        sentence_duration = max(sentence_duration, 0.3)  # Minimum duration
                        
                        segment = TextSegment(
                            text=clean_text,
                            start_time=cumulative_time,
                            duration=sentence_duration,
                            segment_type="sentence",
                            chunk_index=(batch_idx * batch_size + i) // 10,
                            sentence_index=batch_idx * batch_size + i
                        )
                        text_segments.append(segment)
                        cumulative_time += sentence_duration
                        
            except Exception as e:
                print(f"TimingEngine: Error processing batch {batch_idx + 1}: {e}")
        
        # Combine audio files
        final_audio_files = []
        if temp_audio_files:
            if len(temp_audio_files) > 1:
                combined_path = os.path.join(self.file_manager.get_output_dir(), f"{output_filename}_combined.mp3")
                if self._combine_audio_files(temp_audio_files, combined_path):
                    final_audio_files = [os.path.basename(combined_path)]
            else:
                # Single file
                output_path = os.path.join(self.file_manager.get_output_dir(), f"{output_filename}.wav")
                try:
                    import shutil
                    shutil.copy2(temp_audio_files[0], output_path)
                    final_audio_files = [os.path.basename(output_path)]
                except Exception as e:
                    print(f"Failed to copy audio file: {e}")
        
        # Clean up temp files
        for temp_file in temp_audio_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        
        # Create timing metadata
        timing_metadata = None
        if text_segments:
            timing_metadata = TimingMetadata(
                total_duration=cumulative_time,
                text_segments=text_segments,
                audio_files=final_audio_files
            )
        
        return TimedAudioResult(
            audio_files=final_audio_files,
            combined_mp3=final_audio_files[0] if final_audio_files else None,
            timing_data=timing_metadata
        )
    
    def _generate_with_hybrid(self, text_chunks: List[str], output_filename: str) -> TimedAudioResult:
        """Smart combination of estimation and measurement"""
        # Try estimation first, fall back to measurement if needed
        result = self._generate_with_estimation(text_chunks, output_filename)
        
        # If estimation failed or no timing data, use measurement
        if not result.timing_data or not result.audio_files:
            print("TimingEngine: Estimation failed, falling back to measurement")
            return self._generate_with_measurement(text_chunks, output_filename)
        
        return result
    
    def _apply_rate_limit(self):
        """Apply rate limiting between API calls"""
        if self.measurement_interval <= 0:
            return
        
        current_time = time.time()
        time_since_last = current_time - self.last_api_call
        
        if time_since_last < self.measurement_interval:
            sleep_duration = self.measurement_interval - time_since_last
            time.sleep(sleep_duration)
        
        self.last_api_call = time.time()
    
    def _measure_audio_duration(self, file_path: str) -> float:
        """Measure audio file duration"""
        try:
            import subprocess
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except:
            pass
        
        # Fallback to file size estimation
        try:
            file_size = os.path.getsize(file_path)
            return file_size / (22050 * 2)  # Rough estimation
        except:
            return 1.0  # Default fallback
    
    def _combine_audio_files(self, file_paths: List[str], output_path: str) -> bool:
        """Combine audio files using ffmpeg"""
        try:
            import subprocess
            
            list_file = output_path + '.list'
            with open(list_file, 'w') as f:
                for file_path in file_paths:
                    f.write(f"file '{file_path}'\n")
            
            cmd = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_file, '-c', 'copy', output_path, '-y']
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            
            try:
                os.remove(list_file)
            except:
                pass
            
            return result.returncode == 0
        except:
            return False