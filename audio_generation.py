# audio_generation.py - Fixed path handling for FFmpeg
import os
import re
import subprocess
import shutil
from typing import Optional, List, Tuple
from tts_utils import get_tts_processor

class TTSGenerator:
    """Handles text-to-speech generation with MP3 compression support"""
    
    def __init__(self, engine: str, config: dict):
        self.processor = get_tts_processor(engine, **config)
        self.engine_name = engine
        self.chunk_size = 20000  # Characters per audio chunk
        
        # Check for FFmpeg availability
        self.ffmpeg_available = self._check_ffmpeg()
        print(f"TTSGenerator: FFmpeg available: {self.ffmpeg_available}")
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available on the system"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def generate(self, text: str, output_name: str, output_dir: str = "audio_outputs") -> Optional[str]:
        """Generate audio from text (single chunk method)"""
        if not self.processor or not text.strip():
            print("TTSGenerator: No processor or empty text")
            return None
            
        if text.startswith("Error") or text.startswith("LLM cleaning skipped"):
            print("TTSGenerator: Skipping audio generation due to upstream error")
            return None
            
        os.makedirs(output_dir, exist_ok=True)
        
        # Split text for TTS
        chunks = self._split_for_tts(text)
        print(f"TTSGenerator: Split into {len(chunks)} chunks")
        
        if len(chunks) == 1:
            # Single chunk - direct generation
            return self.processor.generate_audio_file(text, output_name, output_dir)
        
        # Multiple chunks - generate and combine
        return self._generate_and_combine(chunks, output_name, output_dir)
    
    def generate_from_chunks(self, text_chunks: List[str], base_output_name: str, 
                           output_dir: str = "audio_outputs", 
                           create_combined_mp3: bool = True) -> Tuple[List[str], Optional[str]]:
        """
        Generate separate audio files from text chunks with optional MP3 combination
        
        Returns:
            Tuple of (individual_audio_files, combined_mp3_file)
        """
        if not self.processor:
            print("TTSGenerator: No processor available")
            return [], None
            
        os.makedirs(output_dir, exist_ok=True)
        generated_files = []
        
        # Generate individual audio files
        for i, text_chunk in enumerate(text_chunks):
            if not text_chunk.strip():
                print(f"TTSGenerator: Skipping empty chunk {i+1}")
                continue
                
            if text_chunk.startswith("Error") or text_chunk.startswith("LLM cleaning skipped"):
                print(f"TTSGenerator: Skipping error chunk {i+1}")
                continue
            
            # Generate filename for this chunk
            chunk_output_name = f"{base_output_name}_part{i+1:02d}"
            print(f"TTSGenerator: Generating audio for chunk {i+1}/{len(text_chunks)}: {chunk_output_name}")
            
            # For individual chunks, we can still split if they're too long
            chunk_audio = self.generate(text_chunk, chunk_output_name, output_dir)
            if chunk_audio:
                generated_files.append(chunk_audio)
                print(f"TTSGenerator: Generated {chunk_audio}")
            else:
                print(f"TTSGenerator: Failed to generate audio for chunk {i+1}")
        
        print(f"TTSGenerator: Generated {len(generated_files)} individual audio files")
        
        # Create combined MP3 if requested - MODIFIED: Now works for single files too
        combined_mp3 = None
        if create_combined_mp3 and len(generated_files) >= 1:  # Changed from > 1 to >= 1
            if len(generated_files) == 1:
                # Single file - convert to MP3
                combined_mp3 = self._convert_single_to_mp3(generated_files[0], base_output_name, output_dir)
            else:
                # Multiple files - combine to MP3
                combined_mp3 = self._create_combined_mp3(generated_files, base_output_name, output_dir)
        
        return generated_files, combined_mp3
    
    def _convert_single_to_mp3(self, audio_file: str, base_name: str, output_dir: str) -> Optional[str]:
        """Convert a single audio file to MP3 format"""
        if not self.ffmpeg_available:
            print("TTSGenerator: FFmpeg not available, cannot convert to MP3")
            return None
        
        try:
            # Prepare file paths
            input_file = os.path.abspath(os.path.join(output_dir, audio_file))
            mp3_filename = f"{base_name}_combined.mp3"
            mp3_path = os.path.abspath(os.path.join(output_dir, mp3_filename))
            
            print(f"TTSGenerator: Converting single file to MP3: {mp3_filename}")
            
            # Check that input file exists
            if not os.path.exists(input_file):
                print(f"TTSGenerator: Input file does not exist: {input_file}")
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
                print(f"TTSGenerator: Successfully converted to MP3: {mp3_filename} ({file_size:.1f} MB)")
                return mp3_filename
            else:
                print(f"TTSGenerator: Failed to convert to MP3: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"TTSGenerator: Error converting single file to MP3: {e}")
            return None
        
    def _create_combined_mp3(self, audio_files: List[str], base_name: str, output_dir: str) -> Optional[str]:
        """Combine multiple audio files into a single compressed MP3"""
        if not self.ffmpeg_available:
            print("TTSGenerator: FFmpeg not available, cannot create combined MP3")
            return None
        
        if len(audio_files) < 2:
            print("TTSGenerator: Less than 2 files, no need to combine")
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
            
            print(f"TTSGenerator: Combining {len(input_files)} files into {combined_filename}")
            
            # Check that all input files exist
            missing_files = [f for f in input_files if not os.path.exists(f)]
            if missing_files:
                print(f"TTSGenerator: Missing input files: {missing_files}")
                return None
            
            # Method 1: Try concat demuxer (fastest, works if all files have same format)
            success = self._combine_with_concat_demuxer(input_files, combined_path)
            
            if not success:
                print("TTSGenerator: Concat demuxer failed, trying concat filter")
                # Method 2: Use concat filter (slower but more compatible)
                success = self._combine_with_concat_filter(input_files, combined_path)
            
            if success and os.path.exists(combined_path):
                file_size = os.path.getsize(combined_path) / (1024 * 1024)  # MB
                print(f"TTSGenerator: Successfully created combined MP3: {combined_filename} ({file_size:.1f} MB)")
                return combined_filename
            else:
                print("TTSGenerator: Failed to create combined MP3")
                return None
                
        except Exception as e:
            print(f"TTSGenerator: Error creating combined MP3: {e}")
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
                print(f"TTSGenerator: Concat demuxer error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"TTSGenerator: Concat demuxer exception: {e}")
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
                print(f"TTSGenerator: Concat filter error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"TTSGenerator: Concat filter exception: {e}")
            return False
    
    def _split_for_tts(self, text: str) -> List[str]:
        """Split text optimally for TTS"""
        if len(text) <= self.chunk_size:
            return [text]
            
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = ""
        
        for sentence in sentences:
            if len(current) + len(sentence) > self.chunk_size:
                if current:
                    chunks.append(current.strip())
                current = sentence
            else:
                current += " " + sentence if current else sentence
                
        if current:
            chunks.append(current.strip())
            
        return chunks
    
    def _generate_and_combine(self, chunks: List[str], output_name: str, output_dir: str) -> Optional[str]:
        """Generate audio for each chunk and combine (KEPT FOR BACKWARD COMPATIBILITY)"""
        try:
            from pydub import AudioSegment
        except ImportError:
            print("TTSGenerator: pydub not available, cannot combine chunks")
            return None
            
        temp_files = []
        try:
            # Generate individual chunks
            for i, chunk in enumerate(chunks):
                print(f"TTSGenerator: Processing chunk {i+1}/{len(chunks)}")
                temp_name = f"{output_name}_chunk_{i}"
                temp_file = self.processor.generate_audio_file(chunk, temp_name, output_dir)
                if temp_file:
                    temp_files.append(os.path.join(output_dir, temp_file))
            
            if not temp_files:
                print("TTSGenerator: No audio chunks generated")
                return None
            
            # Combine audio files
            print("TTSGenerator: Combining audio chunks")
            combined = AudioSegment.empty()
            for temp_file in temp_files:
                combined += AudioSegment.from_file(temp_file)
            
            # Save combined file
            ext = self.processor.get_output_extension()
            final_file = f"{output_name}.{ext}"
            final_path = os.path.join(output_dir, final_file)
            combined.export(final_path, format=ext)
            
            # Cleanup temp files
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass
                    
            print(f"TTSGenerator: Combined audio saved as {final_file}")
            return final_file
            
        except Exception as e:
            print(f"TTSGenerator: Error combining audio: {e}")
            return None

