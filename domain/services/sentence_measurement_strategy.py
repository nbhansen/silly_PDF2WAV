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
from domain.models import TimedAudioResult, TextSegment
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
        full_ssml_text = " ".join(self.ssml_service.add_ssml(chunk) for chunk in text_chunks)
        sentences = self.text_cleaning_service.split_into_sentences(full_ssml_text)
        
        if not sentences:
            return TimedAudioResult(audio_path=None, segments=[])

        print(f"SentenceMeasurementStrategy: Processing {len(sentences)} sentences.")

        temp_audio_files = []
        text_segments = []
        cumulative_time = 0.0

        for i, sentence_ssml in enumerate(sentences):
            try:
                audio_data = self.tts_engine.generate_audio_data(sentence_ssml)
                
                if audio_data:
                    temp_wav_path = self.file_manager.save_temp_file(audio_data, suffix=".wav")
                    temp_audio_files.append(temp_wav_path)
                    
                    duration = self._get_audio_duration(temp_wav_path)
                    if duration is None:
                        word_count = len(self.text_cleaning_service.strip_ssml(sentence_ssml).split())
                        duration = max(word_count / 2.5, 0.5)

                    segment = TextSegment(
                        text=self.text_cleaning_service.strip_ssml(sentence_ssml),
                        start_time=cumulative_time,
                        duration=duration,
                    )
                    text_segments.append(segment)
                    cumulative_time += duration
                    print(f"  - Generated segment {i+1}: '{segment.text[:30]}...' ({duration:.2f}s)")

            except Exception as e:
                print(f"SentenceMeasurementStrategy: Error processing sentence {i}: {e}")

        final_audio_path = None
        if temp_audio_files and self.ffmpeg_available:
            final_audio_path = self._create_combined_mp3(temp_audio_files, output_filename)
        
        for temp_file in temp_audio_files:
            self.file_manager.delete_file(os.path.basename(temp_file))

        print(f"SentenceMeasurementStrategy: Finished. Total duration: {cumulative_time:.2f}s")
        return TimedAudioResult(audio_path=final_audio_path, segments=text_segments)

    def _get_audio_duration(self, audio_filepath: str) -> Optional[float]:
        try:
            with wave.open(audio_filepath, 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                return frames / float(rate) if rate > 0 else 0.0
        except Exception as e:
            print(f"Warning: Could not read audio duration for {audio_filepath}: {e}")
            return None

    def _create_combined_mp3(self, audio_files: List[str], base_name: str) -> Optional[str]:
        output_path = os.path.join(self.file_manager.get_output_dir(), f"{base_name}.mp3")
        concat_list_path = os.path.join(self.file_manager.get_output_dir(), "concat_list.txt")

        try:
            with open(concat_list_path, 'w') as f:
                for path in audio_files:
                    f.write(f"file '{os.path.abspath(path)}'\n")

            cmd = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_list_path,
                '-c:a', 'libmp3lame', '-b:a', '192k', output_path
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"Successfully created combined MP3: {output_path}")
            return output_path
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Error creating combined MP3: {e}")
            if hasattr(e, 'stderr'):
                print(f"FFmpeg stderr: {e.stderr}")
            return None
        finally:
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)

    def _check_ffmpeg(self) -> bool:
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("Warning: FFmpeg is not installed or not in PATH. Combined MP3 generation will be disabled.")
            return False
