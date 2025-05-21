import os
from TTS.api import TTS 
import torch # For checking CUDA availability and setting device

class TTSProcessor:
    def __init__(self, model_name="tts_models/en/vctk/vits", use_gpu_if_available=False, speaker_idx_to_use=None): # Changed model_name back to VITS
        """
        Initializes the TTSProcessor with a Coqui TTS model.

        Args:
            model_name (str): The name of the Coqui TTS model to use.
            use_gpu_if_available (bool): Whether to attempt to use GPU for TTS if available.
            speaker_idx_to_use (str, optional): Specific speaker ID to use for multi-speaker models.
                                                If None, the first available speaker will be used.
        """
        self.model_name = model_name
        self.tts_model = None
        self.speaker_to_use = speaker_idx_to_use 
        self.is_multi_speaker = False

        try:
            print(f"TTSProcessor: Initializing Coqui TTS model: {self.model_name}")
            self.tts_model = TTS(model_name=self.model_name) 
            
            if use_gpu_if_available:
                if torch.cuda.is_available():
                    device = "cuda"
                    print("TTSProcessor: CUDA is available. Attempting to use GPU.")
                else:
                    device = "cpu"
                    print("TTSProcessor: CUDA not available. Using CPU.")
            else:
                device = "cpu"
                print("TTSProcessor: GPU usage not requested. Using CPU.")
            
            self.tts_model.to(device) 
            print(f"TTSProcessor: Coqui TTS model initialized successfully on {device.upper()}.")

            if self.tts_model.is_multi_speaker:
                self.is_multi_speaker = True
                print("TTSProcessor: Model is multi-speaker.")
                available_speakers = self.tts_model.speakers
                print("Available speakers:", available_speakers)
                if self.speaker_to_use is None and available_speakers: # If no specific speaker is requested, use the first one
                    self.speaker_to_use = available_speakers[0] 
                    print(f"TTSProcessor: Defaulting to speaker: {self.speaker_to_use}")
                elif self.speaker_to_use and self.speaker_to_use not in available_speakers: # If a speaker is requested but not found
                    print(f"TTSProcessor: WARNING - Specified speaker '{self.speaker_to_use}' not found.")
                    self.speaker_to_use = available_speakers[0] if available_speakers else None # Fallback to first
                    if self.speaker_to_use:
                         print(f"TTSProcessor: Now using speaker (fallback): {self.speaker_to_use}")
                    else:
                        print("TTSProcessor: ERROR - No speakers available in multi-speaker model.")
                elif self.speaker_to_use: # If a valid speaker is requested
                    print(f"TTSProcessor: Using specified speaker: {self.speaker_to_use}")
                # If self.speaker_to_use was None and no available_speakers, it remains None (error handled in generate_audio)
            else:
                print(f"TTSProcessor: Model '{self.model_name}' is single-speaker.")


        except Exception as e:
            print(f"TTSProcessor: Error initializing Coqui TTS model: {e}")
            print("TTS will likely fail. Ensure you have an internet connection for the first run to download models,")
            print("and that any model dependencies (like espeak) are installed.")


    def generate_audio_file(self, text_to_speak, output_filename_no_ext, audio_dir):
        if not self.tts_model:
            print("TTSProcessor: Coqui TTS model not available. Skipping audio generation.")
            return None

        print(f"TTSProcessor: Attempting Coqui TTS audio generation for {output_filename_no_ext}.wav")
        
        if not text_to_speak or \
           text_to_speak.strip() == "" or \
           text_to_speak.startswith("LLM cleaning skipped") or \
           text_to_speak.startswith("Error:") or \
           text_to_speak.startswith("Could not convert") or \
           text_to_speak.startswith("No text could be extracted"):
            print("TTSProcessor: Skipping audio generation due to empty or error text from previous steps.")
            return None
        
        try:
            os.makedirs(audio_dir, exist_ok=True) 
            
            audio_filename = f"{output_filename_no_ext}.wav"
            audio_filepath = os.path.join(audio_dir, audio_filename)
            
            speaker_arg = None 
            if self.is_multi_speaker:
                if self.speaker_to_use:
                    speaker_arg = self.speaker_to_use
                else: # Should not happen if __init__ logic is correct and there are available speakers
                    print("TTSProcessor: ERROR - Model is multi-speaker but no speaker is selected/available for synthesis.")
                    return None
            
            self.tts_model.tts_to_file(text=text_to_speak, speaker=speaker_arg, file_path=audio_filepath)
            
            print(f"TTSProcessor: Audio file saved: {audio_filepath}")
            return audio_filename
        except Exception as e:
            print(f"TTSProcessor: Error generating audio file with Coqui TTS: {e}")
            return None
