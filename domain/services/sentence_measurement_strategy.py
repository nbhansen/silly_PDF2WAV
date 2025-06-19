"""
Implements the 'Pragmatic Path' timing strategy.

This strategy generates audio for each sentence individually, measures the
duration of each resulting audio file, and then combines them. It is accurate
but slower due to multiple TTS calls and file operations. It works for any
TTS engine.
"""

import os
import wave
import subprocess
from typing import List, Optional

from domain.interfaces import ITimingStrategy, ITTSEngine
from domain.models import TimedAudioResult, TextSegment, TimingMetadata
from domain.services.academic_ssml_service import AcademicSSMLService
from domain.services.text_cleaning_service import TextCleaningService

# --- Fix: Import the module, not the class, to avoid circular dependency ---
from infrastructure.file import file_manager


class SentenceMeasurementStrategy(ITimingStrategy):
    """
    A timing strategy that manually measures the duration of each sentence's audio.
    """

    def __init__(
        self,
        tts_engine: ITTSEngine,
        ssml_service: AcademicSSMLService,
        file_manager, # Type hint removed to simplify import resolution
        text_cleaning_service: TextCleaningService,
    ):
        self.tts_engine = tts_engine
        self.ssml_service = ssml_service
        self.file_manager = file_manager
        self.text_cleaning_service = text_cleaning_service
        self.ffmpeg_available = self._check_ffmpeg()

    def generate_with_timing(self, text_chunks: list[str], output_filename: str) -> TimedAudioResult:
        """
        Executes the sentence-by-sentence audio generation and measurement process.
        """
        # FIXED: Use the correct method name and approach
        print(f"SentenceMeasurementStrategy: Enhancing {len(text_chunks)} text chunks with SSML...")
        enhanced_chunks = self.ssml_service.enhance_text_chunks(text_chunks)
        
        # Combine enhanced chunks into full text for sentence splitting
        full_enhanced_text = " ".join(enhanced_chunks)
        sentences = self.text_cleaning_service.split_into_sentences(full_enhanced_text)
        
        if not sentences:
            print("SentenceMeasurementStrategy: No sentences found after processing")
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

        print(f"SentenceMeasurementStrategy: Processing {len(sentences)} sentences.")

        temp_audio_files = []
        text_segments = []
        cumulative_time = 0.0

        for i, sentence_text in enumerate(sentences):
            try:
                # Generate audio for this sentence
                audio_data = self.tts_engine.generate_audio_data(sentence_text)
                
                if audio_data:
                    # Save temporary audio file
                    temp_wav_path = self.file_manager.save_temp_file(audio_data, suffix=".wav")
                    temp_audio_files.append(temp_wav_path)
                    
                    # Measure actual duration from audio file
                    duration = self._get_audio_duration(temp_wav_path)
                    if duration is None:
                        # Fall back to estimation based on word count
                        clean_text = self.text_cleaning_service.strip_ssml(sentence_text)
                        word_count = len(clean_text.split())
                        duration = max(word_count / 2.5, 0.5)  # ~2.5 words per second

                    # Create text segment with timing info
                    clean_display_text = self.text_cleaning_service.strip_ssml(sentence_text)
                    segment = TextSegment(
                        text=clean_display_text,
                        start_time=cumulative_time,
                        duration=duration,
                        segment_type="sentence",
                        chunk_index=i // 10,  # Group roughly 10 sentences per chunk
                        sentence_index=i
                    )
                    text_segments.append(segment)
                    cumulative_time += duration
                    print(f"  - Generated segment {i+1}: '{segment.text[:50]}...' ({duration:.2f}s)")
                else:
                    print(f"  - Failed to generate audio for sentence {i+1}")

            except Exception as e:
                print(f"SentenceMeasurementStrategy: Error processing sentence {i+1}: {e}")

        # Create combined audio file if we have audio files and ffmpeg
        final_audio_path = None
        final_audio_files = []
        
        if temp_audio_files:
            if self.ffmpeg_available and len(temp_audio_files) > 1:
                # Create combined MP3
                final_audio_path = self._create_combined_mp3(temp_audio_files, output_filename)
                if final_audio_path:
                    final_audio_files = [os.path.basename(final_audio_path)]
            elif len(temp_audio_files) == 1:
                # Single file - convert to output directory
                try:
                    single_output_path = os.path.join(self.file_manager.get_output_dir(), f"{output_filename}.wav")
                    with open(temp_audio_files[0], 'rb') as src, open(single_output_path, 'wb') as dst:
                        dst.write(src.read())
                    final_audio_files = [os.path.basename(single_output_path)]
                except Exception as e:
                    print(f"Failed to copy single audio file: {e}")
            else:
                # Multiple files but no ffmpeg - copy all individual files
                for i, temp_file in enumerate(temp_audio_files):
                    try:
                        output_path = os.path.join(self.file_manager.get_output_dir(), f"{output_filename}_part{i+1:02d}.wav")
                        with open(temp_file, 'rb') as src, open(output_path, 'wb') as dst:
                            dst.write(src.read())
                        final_audio_files.append(os.path.basename(output_path))
                    except Exception as e:
                        print(f"Failed to copy audio file {i+1}: {e}")

        # Clean up temporary files
        for temp_file in temp_audio_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"Failed to clean up temp file {temp_file}: {e}")

        # Create timing metadata
        timing_metadata = None
        if text_segments:
            timing_metadata = TimingMetadata(
                total_duration=cumulative_time,
                text_segments=text_segments,
                audio_files=final_audio_files
            )

        print(f"SentenceMeasurementStrategy: Finished. Total duration: {cumulative_time:.2f}s, Generated {len(final_audio_files)} audio files")
        
        return TimedAudioResult(
            audio_files=final_audio_files,
            combined_mp3=final_audio_files[0] if final_audio_files else None,
            timing_data=timing_metadata
        )

    def _get_audio_duration(self, audio_filepath: str) -> Optional[float]:
        """Get duration of audio file in seconds"""
        try:
            with wave.open(audio_filepath, 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                return frames / float(rate) if rate > 0 else 0.0
        except Exception as e:
            print(f"Warning: Could not read audio duration for {audio_filepath}: {e}")
            return None

    def _create_combined_mp3(self, audio_files: List[str], base_name: str) -> Optional[str]:
        """Create combined MP3 from individual audio files"""
        output_path = os.path.join(self.file_manager.get_output_dir(), f"{base_name}_combined.mp3")
        concat_list_path = os.path.join(self.file_manager.get_output_dir(), "concat_list.txt")

        try:
            # Create FFmpeg concat file list
            with open(concat_list_path, 'w') as f:
                for path in audio_files:
                    # Use absolute paths and escape properly for FFmpeg
                    abs_path = os.path.abspath(path)
                    f.write(f"file '{abs_path}'\n")

            # Run FFmpeg to combine files
            cmd = [
                'ffmpeg', '-y', 
                '-f', 'concat', 
                '-safe', '0', 
                '-i', concat_list_path,
                '-c:a', 'libmp3lame', 
                '-b:a', '128k',
                '-ar', '22050',
                output_path
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"Successfully created combined MP3: {output_path}")
                return output_path
            else:
                print("FFmpeg completed but output file is empty or missing")
                return None
                
        except subprocess.TimeoutExpired:
            print("FFmpeg timed out during audio combination")
            return None
        except subprocess.CalledProcessError as e:
            print(f"Error creating combined MP3: {e}")
            if e.stderr:
                print(f"FFmpeg stderr: {e.stderr}")
            return None
        except Exception as e:
            print(f"Unexpected error creating combined MP3: {e}")
            return None
        finally:
            # Clean up concat list file
            try:
                if os.path.exists(concat_list_path):
                    os.remove(concat_list_path)
            except:
                pass

    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            print("Warning: FFmpeg is not installed or not in PATH. Combined MP3 generation will be disabled.")
            return False