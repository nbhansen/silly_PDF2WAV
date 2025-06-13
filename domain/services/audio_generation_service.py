# domain/services/audio_generation_service.py 
import os
import subprocess
from typing import Optional, List, Tuple
from domain.interfaces import AudioGenerator, ITTSEngine, FileManager

class AudioGenerationService(AudioGenerator):
    """Domain service for audio generation with file lifecycle management."""
    
    def __init__(self, tts_engine: ITTSEngine, file_manager: Optional[FileManager] = None):
        self.tts_engine = tts_engine
        self.file_manager = file_manager  # Domain interface dependency ✅
        self.ffmpeg_available = self._check_ffmpeg()
        
        # Simple configuration from environment
        self.use_async = os.getenv('ENABLE_ASYNC_AUDIO', 'True').lower() == 'true'
        self.max_concurrent = int(os.getenv('MAX_CONCURRENT_TTS_REQUESTS', '4'))
        
        # File management settings (domain concerns)
        self.auto_schedule_cleanup = os.getenv('AUTO_SCHEDULE_FILE_CLEANUP', 'True').lower() == 'true'
        self.file_cleanup_delay_hours = float(os.getenv('FILE_CLEANUP_DELAY_HOURS', '2.0'))
        
        print(f"AudioGenerationService: File management: {'Enabled' if file_manager else 'Disabled'}")
        if file_manager and self.auto_schedule_cleanup:
            print(f"AudioGenerationService: Auto-scheduling files for cleanup in {self.file_cleanup_delay_hours}h")
    
    def generate_audio(self, text_chunks: List[str], output_name: str, output_dir: str, 
                      tts_engine: Optional[ITTSEngine] = None) -> Tuple[List[str], Optional[str]]:
        """Generate audio with integrated file lifecycle management"""
        
        engine = tts_engine or self.tts_engine
        if not engine:
            print("AudioGenerationService: No TTS engine available")
            return [], None
        
        # Filter valid chunks
        valid_chunks = [c for c in text_chunks if c.strip() and not c.startswith("Error")]
        
        if not valid_chunks:
            print("AudioGenerationService: No valid chunks to process")
            return [], None
        
        print(f"AudioGenerationService: Processing {len(valid_chunks)} chunks")
        
        # Generate audio files
        if self._should_use_async(engine, len(valid_chunks)):
            generated_files, combined_mp3 = self._generate_async(valid_chunks, output_name, output_dir, engine)
        else:
            generated_files, combined_mp3 = self._generate_sync(valid_chunks, output_name, output_dir, engine)
        
        # Register files with file manager (Domain service → Domain interface)
        if self.file_manager and generated_files:
            self._register_generated_files(generated_files, combined_mp3)
        
        return generated_files, combined_mp3
    
    def _register_generated_files(self, audio_files: List[str], combined_mp3: Optional[str]):
        """Register generated files with file manager for lifecycle tracking"""
        if not self.file_manager:
            return
        
        files_to_register = audio_files.copy()
        if combined_mp3:
            files_to_register.append(combined_mp3)
        
        for filename in files_to_register:
            try:
                # Verify file exists and get info
                file_info = self.file_manager.get_file_info(filename)
                if file_info:
                    print(f"AudioGenerationService: Registered {filename} ({file_info.size_mb:.1f} MB)")
                    
                    # Schedule cleanup if enabled
                    if self.auto_schedule_cleanup:
                        success = self.file_manager.schedule_cleanup(filename, self.file_cleanup_delay_hours)
                        if success:
                            print(f"AudioGenerationService: Scheduled {filename} for cleanup in {self.file_cleanup_delay_hours}h")
                        
            except Exception as e:
                print(f"AudioGenerationService: Failed to register {filename}: {e}")
    
    def get_file_stats(self) -> Optional[dict]:
        """Get file management statistics"""
        if not self.file_manager:
            return None
        
        try:
            return self.file_manager.get_stats()
        except Exception as e:
            print(f"AudioGenerationService: Failed to get file stats: {e}")
            return None
    
    def _should_use_async(self, engine: ITTSEngine, chunk_count: int) -> bool:
        """SIMPLIFIED: Only basic rules for async decision"""
        
        # Rule 1: User disabled async
        if not self.use_async:
            return False
        
        # Rule 2: Respect engine preference
        if hasattr(engine, 'prefers_sync_processing') and engine.prefers_sync_processing():
            return False
        
        # Rule 3: Use async for multiple chunks with async-friendly engines
        return chunk_count > 1
    
    def _generate_sync(self, text_chunks: List[str], output_name: str, output_dir: str, 
                      engine: ITTSEngine) -> Tuple[List[str], Optional[str]]:
        """Synchronous generation - simple and reliable"""
        
        os.makedirs(output_dir, exist_ok=True)
        generated_files = []
        
        print(f"AudioGenerationService: Using sync processing")
        
        for i, text_chunk in enumerate(text_chunks):
            chunk_name = f"{output_name}_part{i+1:02d}"
            
            try:
                audio_data = engine.generate_audio_data(text_chunk)
                if audio_data:
                    ext = engine.get_output_format()
                    filename = f"{chunk_name}.{ext}"
                    filepath = os.path.join(output_dir, filename)
                    
                    with open(filepath, "wb") as f:
                        f.write(audio_data)
                    
                    generated_files.append(filename)
                    print(f"AudioGenerationService: Generated {filename}")
                
            except Exception as e:
                print(f"AudioGenerationService: Error generating chunk {i+1}: {e}")
        
        return self._finalize_files(generated_files, output_name, output_dir)
    
    def _generate_async(self, text_chunks: List[str], output_name: str, output_dir: str, 
                       engine: ITTSEngine) -> Tuple[List[str], Optional[str]]:
        """Async generation with fallback to sync"""
        
        print(f"AudioGenerationService: Attempting async processing")
        
        try:
            from .async_audio_generation_service import run_async_audio_generation
            return run_async_audio_generation(
                text_chunks, output_name, output_dir, engine, self.max_concurrent
            )
        except ImportError:
            print("AudioGenerationService: Async not available, falling back to sync")
            return self._generate_sync(text_chunks, output_name, output_dir, engine)
        except Exception as e:
            print(f"AudioGenerationService: Async failed ({e}), falling back to sync")
            return self._generate_sync(text_chunks, output_name, output_dir, engine)
    
    def _finalize_files(self, generated_files: List[str], output_name: str, 
                       output_dir: str) -> Tuple[List[str], Optional[str]]:
        """Create combined MP3 if possible"""
        
        if not generated_files:
            return [], None
        
        print(f"AudioGenerationService: Generated {len(generated_files)} files")
        
        # Create combined MP3
        combined_mp3 = None
        if len(generated_files) == 1:
            combined_mp3 = self._convert_single_to_mp3(generated_files[0], output_name, output_dir)
        elif len(generated_files) > 1:
            combined_mp3 = self._create_combined_mp3(generated_files, output_name, output_dir)
        
        return generated_files, combined_mp3
    
    def _convert_single_to_mp3(self, audio_file: str, base_name: str, output_dir: str) -> Optional[str]:
        """Convert single file to MP3"""
        
        if not self.ffmpeg_available:
            return None
        
        try:
            input_path = os.path.join(output_dir, audio_file)
            mp3_filename = f"{base_name}_combined.mp3"
            mp3_path = os.path.join(output_dir, mp3_filename)
            
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-c:a', 'libmp3lame',
                '-b:a', '128k',
                '-ar', '22050',
                mp3_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(mp3_path):
                print(f"AudioGenerationService: Created MP3: {mp3_filename}")
                return mp3_filename
            
        except Exception as e:
            print(f"AudioGenerationService: MP3 conversion failed: {e}")
        
        return None
    
    def _create_combined_mp3(self, audio_files: List[str], base_name: str, output_dir: str) -> Optional[str]:
        """Combine multiple files into MP3"""
        
        if not self.ffmpeg_available or len(audio_files) < 2:
            return None
        
        try:
            combined_filename = f"{base_name}_combined.mp3"
            combined_path = os.path.join(output_dir, combined_filename)
            concat_file = combined_path + ".txt"
            
            # Create concat file
            with open(concat_file, 'w') as f:
                for audio_file in audio_files:
                    abs_path = os.path.abspath(os.path.join(output_dir, audio_file))
                    escaped_path = abs_path.replace('\\', '/').replace("'", "'\"'\"'")
                    f.write(f"file '{escaped_path}'\n")
            
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:a', 'libmp3lame',
                '-b:a', '128k',
                '-ar', '22050',
                combined_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            
            # Cleanup
            try:
                os.remove(concat_file)
            except:
                pass
            
            if result.returncode == 0 and os.path.exists(combined_path):
                print(f"AudioGenerationService: Created combined MP3: {combined_filename}")
                return combined_filename
            
        except Exception as e:
            print(f"AudioGenerationService: Combined MP3 creation failed: {e}")
        
        return None
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False