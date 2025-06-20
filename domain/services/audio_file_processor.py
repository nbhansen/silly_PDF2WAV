# domain/services/audio_file_processor.py
import os
import subprocess
import tempfile
from typing import List, Optional, Tuple
from domain.interfaces import IFileManager, IAudioProcessor
from domain.errors import Result, audio_generation_error


class AudioFileProcessor:
    """Service responsible for audio file operations and FFmpeg processing"""

    def __init__(self, file_manager: IFileManager, audio_processor: IAudioProcessor):
        self.file_manager = file_manager
        self.audio_processor = audio_processor

    def save_audio_chunk(self, audio_data: bytes, output_dir: str,
                         filename: str) -> Result[str]:
        """Save individual audio chunk to file"""
        try:
            if not audio_data:
                return Result.failure(audio_generation_error("No audio data to save"))

            output_path = os.path.join(output_dir, filename)

            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            with open(output_path, 'wb') as f:
                f.write(audio_data)

            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                return Result.failure(audio_generation_error(f"Failed to save audio file: {filename}"))

            return Result.success(output_path)

        except Exception as e:
            return Result.failure(audio_generation_error(f"Failed to save audio chunk: {str(e)}"))

    def create_combined_mp3(self, audio_files: List[str], output_name: str,
                            output_dir: str) -> Result[Optional[str]]:
        """Create combined MP3 from individual audio files using FFmpeg"""
        if not self.audio_processor.check_ffmpeg_availability():
            print("AudioFileProcessor: FFmpeg not available, skipping MP3 combination")
            return Result.success(None)

        if not audio_files:
            return Result.failure(audio_generation_error("No audio files to combine"))

        # Validate audio files before attempting combination
        valid_files, invalid_files = self.validate_audio_files(audio_files)
        
        # Enhanced file debugging - always enabled for now to diagnose MP3 issue
        print(f"AudioFileProcessor: Validating {len(audio_files)} audio files for MP3 combination")
        for i, file_path in enumerate(audio_files):
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  File {i+1}: {file_path} - Size: {size} bytes")
                
                # Try to validate as WAV file
                try:
                    import wave
                    with wave.open(file_path, 'rb') as wav:
                        frames = wav.getnframes()
                        rate = wav.getframerate()
                        channels = wav.getnchannels()
                        duration = frames / rate if rate > 0 else 0
                        print(f"    WAV info: {frames} frames, {rate}Hz, {channels} channels, {duration:.2f}s")
                except Exception as e:
                    print(f"    WAV validation failed: {e}")
                
                # Try to validate with ffprobe if available
                try:
                    import subprocess
                    result = subprocess.run([
                        'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', file_path
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        print(f"    FFprobe: Valid audio file")
                    else:
                        print(f"    FFprobe: Invalid audio file - {result.stderr}")
                except Exception as e:
                    print(f"    FFprobe validation skipped: {e}")
            else:
                print(f"  File {i+1}: {file_path} - MISSING")
        
        if invalid_files:
            print(f"AudioFileProcessor: Found {len(invalid_files)} invalid audio files: {invalid_files}")
        
        if not valid_files:
            return Result.failure(audio_generation_error(f"No valid audio files found. Invalid files: {invalid_files}"))
        
        if len(valid_files) != len(audio_files):
            print(f"AudioFileProcessor: Using {len(valid_files)} valid files out of {len(audio_files)} total")

        output_path = os.path.join(output_dir, f"{output_name}_combined.mp3")
        print(f"AudioFileProcessor: Attempting to create MP3: {output_path}")
        
        result = self.audio_processor.combine_audio_files(valid_files, output_path)
        
        if not result.is_success:
            print(f"AudioFileProcessor: MP3 combination failed with error: {result.error}")
            print(f"AudioFileProcessor: Error details: {result.error.details if hasattr(result.error, 'details') else 'No details available'}")
        
        return result

    def cleanup_temp_files(self, temp_files: List[str]) -> None:
        """Clean up temporary audio files"""
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"AudioFileProcessor: Failed to clean up temp file {temp_file}: {e}")

    def validate_audio_files(self, audio_files: List[str]) -> Tuple[List[str], List[str]]:
        """Validate audio files and return valid/invalid lists"""
        valid_files = []
        invalid_files = []

        for audio_file in audio_files:
            if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
                valid_files.append(audio_file)
            else:
                invalid_files.append(audio_file)

        return valid_files, invalid_files
