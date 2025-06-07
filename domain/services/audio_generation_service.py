# domain/services/audio_generation_service.py
import os
import re
import subprocess
from typing import Optional, List, Tuple
from domain.models import AudioGenerator, ITTSEngine

class AudioGenerationService(AudioGenerator):
    """Pure business logic for generating audio from text chunks."""
    
    def __init__(self, tts_engine: ITTSEngine):
        self.tts_engine = tts_engine
        self.chunk_size = 20000  # Characters per audio chunk
        self.ffmpeg_available = self._check_ffmpeg()
        print(f"AudioGenerationService: FFmpeg available: {self.ffmpeg_available}")
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available on the system"""
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def generate_audio(self, text_chunks: List[str], output_name: str, output_dir: str, tts_engine: Optional[ITTSEngine] = None) -> Tuple[List[str], Optional[str]]:
        """
        Generate separate audio files from text chunks with optional MP3 combination
        
        Returns:
            Tuple of (individual_audio_files, combined_mp3_file)
        """
        # Use the passed engine or fall back to the instance one
        engine_to_use = tts_engine or self.tts_engine
        
        if not engine_to_use:
            print("AudioGenerationService: No TTS engine available")
            return [], None
            
        os.makedirs(output_dir, exist_ok=True)
        generated_files = []
        
        # Generate individual audio files
        for i, text_chunk in enumerate(text_chunks):
            if not text_chunk.strip():
                print(f"AudioGenerationService: Skipping empty chunk {i+1}")
                continue
                
            if text_chunk.startswith("Error") or text_chunk.startswith("LLM cleaning skipped"):
                print(f"AudioGenerationService: Skipping error chunk {i+1}")
                continue
            
            # Generate filename for this chunk
            chunk_output_name = f"{output_name}_part{i+1:02d}"
            print(f"AudioGenerationService: Generating audio for chunk {i+1}/{len(text_chunks)}: {chunk_output_name}")
            
            try:
                audio_data = engine_to_use.generate_audio_data(text_chunk)
                if audio_data:
                    ext = engine_to_use.get_output_format()
                    audio_filename = f"{chunk_output_name}.{ext}"
                    audio_filepath = os.path.join(output_dir, audio_filename)
                    
                    with open(audio_filepath, "wb") as f:
                        f.write(audio_data)
                    
                    generated_files.append(audio_filename)
                    print(f"AudioGenerationService: Generated {audio_filename}")
                else:
                    print(f"AudioGenerationService: Failed to generate audio data for chunk {i+1}")
            except Exception as e:
                print(f"AudioGenerationService: Error generating audio for chunk {i+1}: {e}")
        
        print(f"AudioGenerationService: Generated {len(generated_files)} individual audio files")
        
        # Create combined MP3 if requested
        combined_mp3 = None
        if len(generated_files) >= 1:
            if len(generated_files) == 1:
                # Single file - convert to MP3
                combined_mp3 = self._convert_single_to_mp3(generated_files[0], output_name, output_dir)
            else:
                # Multiple files - combine to MP3
                combined_mp3 = self._create_combined_mp3(generated_files, output_name, output_dir)
        
        return generated_files, combined_mp3
    
    def _convert_single_to_mp3(self, audio_file: str, base_name: str, output_dir: str) -> Optional[str]:
        """Convert a single audio file to MP3 format"""
        if not self.ffmpeg_available:
            print("AudioGenerationService: FFmpeg not available, cannot convert to MP3")
            return None
        
        try:
            # Prepare file paths
            input_file = os.path.abspath(os.path.join(output_dir, audio_file))
            mp3_filename = f"{base_name}_combined.mp3"
            mp3_path = os.path.abspath(os.path.join(output_dir, mp3_filename))
            
            print(f"AudioGenerationService: Converting single file to MP3: {mp3_filename}")
            
            # Check that input file exists
            if not os.path.exists(input_file):
                print(f"AudioGenerationService: Input file does not exist: {input_file}")
                return None
            
            # FFmpeg command to convert to MP3
            cmd = [
                'ffmpeg', '-y',  # -y to overwrite output file
                '-i', input_file,
                '-c:a', 'libmp3lame',  # MP3 codec
                '-b:a', '128k',        # 128 kbps bitrate
                '-ar', '22050',        # 22.05 kHz sample rate (good for speech)
                mp3_path
            ]
            
            # Run FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(mp3_path):
                file_size = os.path.getsize(mp3_path) / (1024 * 1024)  # MB
                print(f"AudioGenerationService: Successfully converted to MP3: {mp3_filename} ({file_size:.1f} MB)")
                return mp3_filename
            else:
                print(f"AudioGenerationService: Failed to convert to MP3: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"AudioGenerationService: Error converting single file to MP3: {e}")
            return None
        
    def _create_combined_mp3(self, audio_files: List[str], base_name: str, output_dir: str) -> Optional[str]:
        """Combine multiple audio files into a single compressed MP3"""
        if not self.ffmpeg_available:
            print("AudioGenerationService: FFmpeg not available, cannot create combined MP3")
            return None
        
        if len(audio_files) < 2:
            print("AudioGenerationService: Less than 2 files, no need to combine")
            return None
        
        try:
            # Prepare file paths - FIX: Use absolute paths to avoid path confusion
            input_files = []
            for f in audio_files:
                # Convert to absolute path to avoid path issues
                if os.path.isabs(f):
                    input_files.append(f)
                else:
                    input_files.append(os.path.abspath(os.path.join(output_dir, f)))
            
            combined_filename = f"{base_name}_combined.mp3"
            combined_path = os.path.abspath(os.path.join(output_dir, combined_filename))
            
            print(f"AudioGenerationService: Combining {len(input_files)} files into {combined_filename}")
            
            # Check that all input files exist
            missing_files = [f for f in input_files if not os.path.exists(f)]
            if missing_files:
                print(f"AudioGenerationService: Missing input files: {missing_files}")
                return None
            
            # Method 1: Try concat demuxer (fastest, works if all files have same format)
            success = self._combine_with_concat_demuxer(input_files, combined_path)
            
            if not success:
                print("AudioGenerationService: Concat demuxer failed, trying concat filter")
                # Method 2: Use concat filter (slower but more compatible)
                success = self._combine_with_concat_filter(input_files, combined_path)
            
            if success and os.path.exists(combined_path):
                file_size = os.path.getsize(combined_path) / (1024 * 1024)  # MB
                print(f"AudioGenerationService: Successfully created combined MP3: {combined_filename} ({file_size:.1f} MB)")
                return combined_filename
            else:
                print("AudioGenerationService: Failed to create combined MP3")
                return None
                
        except Exception as e:
            print(f"AudioGenerationService: Error creating combined MP3: {e}")
            return None
    
    def _combine_with_concat_demuxer(self, input_files: List[str], output_path: str) -> bool:
        """Combine files using FFmpeg concat demuxer (fast method)"""
        try:
            # Create a temporary file list for FFmpeg
            concat_file = output_path + ".concat.txt"
            
            with open(concat_file, 'w', encoding='utf-8') as f:
                for input_file in input_files:
                    # Use absolute paths and proper escaping
                    abs_path = os.path.abspath(input_file)
                    # For Windows compatibility, use forward slashes and escape properly
                    escaped_path = abs_path.replace('\\', '/').replace("'", "'\"'\"'")
                    f.write(f"file '{escaped_path}'\n")
            
            # FFmpeg command for concat demuxer
            cmd = [
                'ffmpeg', '-y',  # -y to overwrite output file
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:a', 'libmp3lame',  # MP3 codec
                '-b:a', '128k',        # 128 kbps bitrate
                '-ar', '22050',        # 22.05 kHz sample rate (good for speech)
                output_path
            ]
            
            # Run FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Clean up temp file
            try:
                os.remove(concat_file)
            except:
                pass
            
            if result.returncode == 0:
                return True
            else:
                print(f"AudioGenerationService: Concat demuxer error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"AudioGenerationService: Concat demuxer exception: {e}")
            return False
    
    def _combine_with_concat_filter(self, input_files: List[str], output_path: str) -> bool:
        """Combine files using FFmpeg concat filter (compatible method)"""
        try:
            # Build FFmpeg command with concat filter
            cmd = ['ffmpeg', '-y']
            
            # Add input files with absolute paths
            for input_file in input_files:
                abs_path = os.path.abspath(input_file)
                cmd.extend(['-i', abs_path])
            
            # Add filter complex for concatenation
            filter_inputs = ''.join([f'[{i}:0]' for i in range(len(input_files))])
            filter_concat = f'{filter_inputs}concat=n={len(input_files)}:v=0:a=1[out]'
            
            cmd.extend([
                '-filter_complex', filter_concat,
                '-map', '[out]',
                '-c:a', 'libmp3lame',  # MP3 codec
                '-b:a', '128k',        # 128 kbps bitrate
                '-ar', '22050',        # 22.05 kHz sample rate
                output_path
            ])
            
            # Run FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return True
            else:
                print(f"AudioGenerationService: Concat filter error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"AudioGenerationService: Concat filter exception: {e}")
            return False