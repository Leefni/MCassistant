"""Speech-to-text backend powered by ``speech_recognition``."""

from __future__ import annotations

from dataclasses import dataclass

from .input import MicrophoneSource
from .interfaces import SpeechRecognizer


@dataclass(slots=True)
class SpeechRecognitionRecognizer(SpeechRecognizer):
    """Convert PCM/WAV-like audio bytes into transcripts using speech_recognition."""

    language: str = "en-US"
    sample_rate: int = 16_000
    sample_width: int = 2

    def __post_init__(self) -> None:
        try:
            import speech_recognition as sr
        except ImportError as exc:  # pragma: no cover - import guard
            raise RuntimeError(
                "Voice STT backend unavailable. Install extras with: pip install 'mc-assistant[voice]'"
            ) from exc
        self._sr = sr
        self._recognizer = sr.Recognizer()

    def transcribe(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return ""
        audio = self._sr.AudioData(audio_bytes, sample_rate=self.sample_rate, sample_width=self.sample_width)
        try:
            return self._recognizer.recognize_google(audio, language=self.language)
        except self._sr.UnknownValueError:
            return ""
        except self._sr.RequestError as exc:
            raise RuntimeError(
                "Speech recognition service request failed. Check internet access or switch STT backend."
            ) from exc


class SpeechRecognitionMicrophoneSource(MicrophoneSource):
    """Capture microphone utterances as wav bytes via speech_recognition."""

    def __init__(
        self,
        *,
        phrase_time_limit: float = 5.0,
        timeout: float | None = None,
        sample_rate: int = 16_000,
        chunk_size: int = 1024,
        adjust_noise_seconds: float = 0.2,
    ) -> None:
        try:
            import speech_recognition as sr
        except ImportError as exc:  # pragma: no cover - import guard
            raise RuntimeError(
                "Microphone backend unavailable. Install extras with: pip install 'mc-assistant[voice]'"
            ) from exc
        self._sr = sr
        self._recognizer = sr.Recognizer()
        self._microphone = sr.Microphone(sample_rate=sample_rate, chunk_size=chunk_size)
        self._phrase_time_limit = phrase_time_limit
        self._timeout = timeout
        self._adjust_noise_seconds = max(0.0, adjust_noise_seconds)

    def read_chunk(self) -> bytes:
        try:
            with self._microphone as source:
                if self._adjust_noise_seconds > 0:
                    self._recognizer.adjust_for_ambient_noise(source, duration=self._adjust_noise_seconds)
                audio = self._recognizer.listen(
                    source,
                    timeout=self._timeout,
                    phrase_time_limit=self._phrase_time_limit,
                )
            return audio.get_wav_data()
        except self._sr.WaitTimeoutError:
            return b""
