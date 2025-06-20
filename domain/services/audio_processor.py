# domain/services/audio_processor.py
import os
import subprocess
import tempfile
import wave
from typing import List

from domain.interfaces import IAudioProcessor
from domain.errors import Result, audio_generation_error


class AudioProcessor(IAudioProcessor):
    """Concrete implementation of audio processing operations"""

    def __init__(self, config=None):
        self._ffmpeg_available = None  # Cache the result

        # Use provided config or get default values
        if config:
            self.audio_bitrate = config.audio_bitrate
            self.audio_sample_rate = str(config.audio_sample_rate)
            self.mp3_codec = config.mp3_codec
            self.ffmpeg_timeout = config.ffmpeg_timeout_seconds
        else:
            # Fallback to hardcoded defaults for backward compatibility
            self.audio_bitrate = "128k"
            self.audio_sample_rate = "22050"
            self.mp3_codec = "libmp3lame"
            self.ffmpeg_timeout = 300

    def check_ffmpeg_availability(self) -> bool:
        """Check if FFmpeg is available on the system."""
        if self._ffmpeg_available is None:
            try:
                result = subprocess.run(['ffmpeg', '-version'],
                                        capture_output=True, check=True, timeout=5)
                self._ffmpeg_available = result.returncode == 0
            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                self._ffmpeg_available = False

        return self._ffmpeg_available

    def combine_audio_files(self, audio_files: List[str], output_path: str) -> Result[str]:
        """Combine multiple audio files into a single file."""
        if not audio_files:
            return Result.failure(audio_generation_error("No audio files to combine"))

        if not self.check_ffmpeg_availability():
            return Result.failure(audio_generation_error("FFmpeg not available for audio combination"))

        if len(audio_files) == 1:
            # Single file - just copy/convert
            return self._convert_single_file(audio_files[0], output_path)

        return self._combine_multiple_files(audio_files, output_path)

    def convert_audio_format(self, input_path: str, output_path: str, format: str) -> Result[str]:
        """Convert audio file to specified format."""
        if not self.check_ffmpeg_availability():
            return Result.failure(audio_generation_error("FFmpeg not available for format conversion"))

        if not os.path.exists(input_path):
            return Result.failure(audio_generation_error(f"Input file not found: {input_path}"))

        try:
            cmd = [
                'ffmpeg', '-y', '-i', input_path,
                '-c:a', self.mp3_codec if format.lower() == 'mp3' else 'copy',
                '-b:a', self.audio_bitrate,
                '-ar', self.audio_sample_rate,
                output_path
            ]

            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=self.ffmpeg_timeout)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return Result.success(output_path)
            else:
                return Result.failure(audio_generation_error("FFmpeg completed but output file is empty"))

        except subprocess.TimeoutExpired:
            return Result.failure(audio_generation_error("FFmpeg timed out during conversion"))
        except subprocess.CalledProcessError as e:
            return Result.failure(audio_generation_error(f"FFmpeg conversion failed: {e.stderr}"))
        except Exception as e:
            return Result.failure(audio_generation_error(f"Unexpected error during conversion: {str(e)}"))

    def get_audio_duration(self, audio_path: str) -> Result[float]:
        """Get duration of audio file in seconds."""
        if not os.path.exists(audio_path):
            return Result.failure(audio_generation_error(f"Audio file not found: {audio_path}"))

        # Try with wave library first (for WAV files)
        try:
            with wave.open(audio_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                if rate > 0:
                    return Result.success(frames / float(rate))
        except Exception:
            pass  # Not a WAV file or corrupted, try FFmpeg

        # Fallback to FFmpeg for other formats
        if self.check_ffmpeg_availability():
            try:
                cmd = [
                    'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                    '-of', 'csv=p=0', audio_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0 and result.stdout.strip():
                    duration = float(result.stdout.strip())
                    return Result.success(duration)

            except (subprocess.TimeoutExpired, ValueError, subprocess.CalledProcessError):
                pass

        return Result.failure(audio_generation_error(f"Could not determine duration of {audio_path}"))

    def _convert_single_file(self, input_path: str, output_path: str) -> Result[str]:
        """Convert a single file to the output format"""
        try:
            # Determine output format from extension
            output_format = 'mp3' if output_path.endswith('.mp3') else 'wav'
            return self.convert_audio_format(input_path, output_path, output_format)

        except Exception as e:
            return Result.failure(audio_generation_error(f"Failed to convert single file: {str(e)}"))

    def _combine_multiple_files(self, audio_files: List[str], output_path: str) -> Result[str]:
        """Combine multiple audio files using FFmpeg"""
        concat_list_path = None

        try:
            # Create temporary concat file list
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                concat_list_path = f.name
                for audio_file in audio_files:
                    abs_path = os.path.abspath(audio_file)
                    # Escape single quotes for FFmpeg
                    escaped_path = abs_path.replace("'", "'\"'\"'")
                    f.write(f"file '{escaped_path}'\n")

            # Run FFmpeg to combine files
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_list_path,
                '-c:a', self.mp3_codec,
                '-b:a', self.audio_bitrate,
                '-ar', self.audio_sample_rate,
                output_path
            ]
            
            print(f"AudioProcessor: Running FFmpeg command: {' '.join(cmd)}")
            print(f"AudioProcessor: Concat file path: {concat_list_path}")
            
            # Show concat file contents for debugging
            try:
                with open(concat_list_path, 'r') as f:
                    concat_contents = f.read()
                    print(f"AudioProcessor: Concat file contents:")
                    for line in concat_contents.strip().split('\n'):
                        print(f"  {line}")
            except Exception as e:
                print(f"AudioProcessor: Could not read concat file: {e}")

            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=self.ffmpeg_timeout)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return Result.success(output_path)
            else:
                return Result.failure(audio_generation_error("FFmpeg completed but output file is empty"))

        except subprocess.TimeoutExpired:
            return Result.failure(audio_generation_error("FFmpeg timed out during combination"))
        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg combination failed: {e.stderr}"
            print(f"AudioProcessor: {error_msg}")
            print(f"AudioProcessor: FFmpeg stdout: {e.stdout}")
            print(f"AudioProcessor: FFmpeg return code: {e.returncode}")
            return Result.failure(audio_generation_error(error_msg))
        except Exception as e:
            error_msg = f"Unexpected error during combination: {str(e)}"
            print(f"AudioProcessor: {error_msg}")
            return Result.failure(audio_generation_error(error_msg))
        finally:
            # Clean up concat list file
            if concat_list_path and os.path.exists(concat_list_path):
                try:
                    os.remove(concat_list_path)
                except:
                    pass  # Ignore cleanup errors
