import numpy as np
import sounddevice as sd
import torch
from faster_whisper import WhisperModel
import logging # Import the logging module

class STTEngine:
    """
    Optimized blocking mic capture for the Speech-Regulator.
    It now uses a shorter recording duration for better responsiveness and
    leverages Faster-Whisper's VAD filter for efficiency.
    Start with enabled=False for manual tests.
    Flip to True via 'Start/Stop Mic' to use Whisper.
    """
    def __init__(self, model_size="tiny", enabled=False, sample_rate=16000, duration=1.5): # Removed app_logger
        self.enabled = enabled
        self.sample_rate = sample_rate
        self.duration = duration
        self._model = None
        self._model_size = model_size
        self._audio_buffer = np.array([], dtype=np.float32) # For potential future non-blocking capture
        self.logger = logging.getLogger("SpeechRegulator") # Use the globally configured logger

    def _ensure_model(self):
        """Ensures the Whisper model is loaded only once."""
        if self._model is None:
            # Determine the device (CUDA for GPU if available, otherwise CPU)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Set compute_type for optimal performance:
            # "int8" for CPU (quantized for speed on CPU)
            # "float16" for GPU (half-precision for speed on GPU)
            compute_type = "int8" if device == "cpu" else "float16"
            
            self.logger.info(f"[STT] Loading Whisper model '{self._model_size}' on '{device}' with compute_type='{compute_type}'")
            self._model = WhisperModel(self._model_size, device=device, compute_type=compute_type)

    def listen(self):
        """
        Records a short audio chunk and transcribes it with Faster-Whisper.
        Now uses VAD filter for better performance by ignoring silent segments.
        """
        try:
            self._ensure_model()
            
            # Record audio for the specified duration
            # sd.rec is blocking, meaning it waits until the recording is complete.
            audio = sd.rec(int(self.duration * self.sample_rate), samplerate=self.sample_rate,
                           channels=1, dtype="float32")
            sd.wait() # Wait until the recording is finished

            # Remove single-dimensional entries from the shape of an array (e.g., (N, 1) -> (N,))
            audio = np.squeeze(audio)

            # Transcribe the audio using Faster-Whisper.
            # vad_filter=True helps to filter out non-speech segments, improving efficiency
            # by not wasting computation on silence.
            segments, _ = self._model.transcribe(
                audio,
                language="en",
                vad_filter=True, # Enable Voice Activity Detection filter
                # Optional: You can fine-tune VAD parameters if needed
                # vad_parameters={"min_silence_duration_ms": 500, "threshold": 0.5}
            )
            
            # Join the transcribed segments into a single string
            text = " ".join(seg.text for seg in segments).strip()
            return text if text else None
        except Exception as e:
            # Log any errors during transcription
            self.logger.error(f"[STT ERROR] Error during transcription: {e}")
            return None
