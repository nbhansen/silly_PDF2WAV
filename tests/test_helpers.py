# tests/test_helpers.py
from domain.interfaces import (
    ITTSEngine, ILLMProvider, ITextExtractor, IPageRangeValidator,
    IAudioProcessor, ITimingCalculator, IEngineCapabilityDetector, SSMLCapability,
    ITimingStrategy
)
from domain.models import PDFInfo, PageRange, ProcessingRequest, TimedAudioResult, TimingMetadata
from domain.errors import Result, tts_engine_error, llm_provider_error, audio_generation_error
from typing import Dict, Any, List
import tempfile
import os

class FakeTTSEngine(ITTSEngine):
    def __init__(self, should_fail=False, output_format="wav"):
        self.should_fail = should_fail
        self.output_format = output_format
        self.generated_texts = []
        
    def generate_audio_data(self, text_to_speak: str) -> Result[bytes]:
        self.generated_texts.append(text_to_speak)
        if self.should_fail:
            return Result.failure(tts_engine_error("TTS generation failed"))
        return Result.success(f"audio_data_for_{len(text_to_speak)}_chars".encode())
    
    def get_output_format(self) -> str:
        return self.output_format

class FakeLLMProvider(ILLMProvider):
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.prompts = []
        
    def generate_content(self, prompt: str) -> Result[str]:
        self.prompts.append(prompt)
        if self.should_fail:
            return Result.failure(llm_provider_error("LLM generation failed"))
        return Result.success(f"Cleaned: {prompt[:50]}... with pauses")
    
    def process_text(self, text: str) -> Result[str]:
        return self.generate_content(text)

class FakeTextExtractor(ITextExtractor, IPageRangeValidator):
    def __init__(self, text_to_return="Default extracted text", pdf_info=None):
        self.text_to_return = text_to_return
        self.pdf_info = pdf_info or PDFInfo(total_pages=1, title="Test PDF", author="Test Author")
        self.extraction_calls = []
        
    def extract_text(self, pdf_path: str, page_range: PageRange) -> str:
        self.extraction_calls.append((pdf_path, page_range))
        return self.text_to_return
    
    def get_pdf_info(self, pdf_path: str) -> PDFInfo:
        return self.pdf_info
        
    def validate_range(self, pdf_path: str, page_range: PageRange) -> Dict[str, Any]:
        return {'valid': True, 'total_pages': self.pdf_info.total_pages}

def create_test_request(pdf_path="test.pdf", output_name="test_output", page_range=None):
    return ProcessingRequest(
        pdf_path=pdf_path,
        output_name=output_name,
        page_range=page_range or PageRange()
    )


class FakeFileManager:
    """Fake file manager for testing"""
    
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or tempfile.mkdtemp()
        os.makedirs(self.output_dir, exist_ok=True)
        self.saved_files = []
        self.temp_files = []
    
    def save_output_file(self, content: bytes, filename: str) -> str:
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(content)
        self.saved_files.append(filepath)
        return filepath
    
    def save_temp_file(self, content: bytes, suffix: str = ".tmp") -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(content)
            self.temp_files.append(f.name)
            return f.name
    
    def get_output_dir(self) -> str:
        return self.output_dir
    
    def delete_file(self, filepath: str) -> None:
        if os.path.exists(filepath):
            os.remove(filepath)
            if filepath in self.saved_files:
                self.saved_files.remove(filepath)
            if filepath in self.temp_files:
                self.temp_files.remove(filepath)
    
    def cleanup(self):
        """Clean up all created files"""
        for filepath in self.saved_files + self.temp_files:
            if os.path.exists(filepath):
                os.remove(filepath)
        self.saved_files.clear()
        self.temp_files.clear()


class FakeAudioProcessor(IAudioProcessor):
    """Fake audio processor for testing"""
    
    def __init__(self, ffmpeg_available=True):
        self._ffmpeg_available = ffmpeg_available
    
    def check_ffmpeg_availability(self) -> bool:
        return self._ffmpeg_available
    
    def combine_audio_files(self, audio_files: List[str], output_path: str) -> Result[str]:
        if not self._ffmpeg_available:
            return Result.failure(audio_generation_error("FFmpeg not available"))
        if not audio_files:
            return Result.failure(audio_generation_error("No audio files to combine"))
        # Simulate combining files
        return Result.success(output_path)
    
    def convert_audio_format(self, input_path: str, output_path: str, format: str) -> Result[str]:
        if not self._ffmpeg_available:
            return Result.failure(audio_generation_error("FFmpeg not available"))
        return Result.success(output_path)
    
    def get_audio_duration(self, audio_path: str) -> Result[float]:
        # Return a fake duration based on file path
        return Result.success(2.5)


class FakeTimingCalculator(ITimingCalculator):
    """Fake timing calculator for testing"""
    
    def estimate_text_duration(self, text: str, engine_type: str) -> float:
        return len(text.split()) * 0.5  # Half second per word
    
    def calculate_phoneme_duration(self, text: str) -> float:
        return len(text) * 0.1  # 0.1 seconds per character
    
    def add_punctuation_pauses(self, text: str) -> float:
        return text.count('.') * 0.5 + text.count(',') * 0.2
    
    def estimate_sentence_duration(self, sentence: str, engine_type: str) -> float:
        return self.estimate_text_duration(sentence, engine_type)


class FakeEngineCapabilityDetector(IEngineCapabilityDetector):
    """Fake engine capability detector for testing"""
    
    def detect_ssml_capability(self, engine) -> SSMLCapability:
        return SSMLCapability.BASIC
    
    def supports_timestamps(self, engine) -> bool:
        return False
    
    def get_recommended_rate_limit(self, engine) -> float:
        return 1.0
    
    def requires_async_processing(self, engine) -> bool:
        return True
    
    def get_engine_characteristics(self, engine) -> Dict[str, any]:
        return {
            'name': engine.__class__.__name__,
            'ssml_capability': SSMLCapability.BASIC,
            'supports_timestamps': False,
            'recommended_rate_limit': 1.0,
            'requires_async': True,
            'is_cloud_service': True,
            'output_format': 'wav'
        }
    
    def register_engine_capabilities(self, engine_name: str, capabilities: Dict[str, any]) -> None:
        pass


class FakeTimingStrategy(ITimingStrategy):
    """Fake timing strategy for testing"""
    
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
    
    def generate_with_timing(self, text_chunks: List[str], output_filename: str) -> TimedAudioResult:
        """Generate fake timed audio result"""
        if self.should_fail:
            return TimedAudioResult(
                audio_files=[],
                combined_mp3=None,
                timing_data=None
            )
        
        # Create fake audio files and timing data
        audio_files = [f"{output_filename}_part{i+1:02d}.wav" for i in range(len(text_chunks))]
        
        timing_metadata = TimingMetadata(
            total_duration=len(text_chunks) * 2.0,  # 2 seconds per chunk
            text_segments=[],
            audio_files=audio_files
        )
        
        return TimedAudioResult(
            audio_files=audio_files,
            combined_mp3=f"{output_filename}_combined.mp3",
            timing_data=timing_metadata
        )