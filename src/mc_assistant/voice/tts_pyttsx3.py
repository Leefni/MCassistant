"""Text-to-speech backend powered by ``pyttsx3``."""

from __future__ import annotations

from dataclasses import dataclass

from .interfaces import SpeechSynthesizer
from .output import AudioOutputDevice


@dataclass(slots=True)
class Pyttsx3SpeechSynthesizer(SpeechSynthesizer):
    """Prepare text payload for local pyttsx3 playback."""

    voice_id: str | None = None
    rate: int | None = None
    volume: float | None = None

    def __post_init__(self) -> None:
        try:
            import pyttsx3
        except ImportError as exc:  # pragma: no cover - import guard
            raise RuntimeError(
                "Voice TTS backend unavailable. Install extras with: pip install 'mc-assistant[voice]'"
            ) from exc
        self._pyttsx3 = pyttsx3

    def synthesize(self, text: str) -> bytes:
        return text.encode("utf-8")


class Pyttsx3AudioOutputDevice(AudioOutputDevice):
    """Speaker playback using a local pyttsx3 engine instance."""

    def __init__(self, *, voice_id: str | None = None, rate: int | None = None, volume: float | None = None) -> None:
        try:
            import pyttsx3
        except ImportError as exc:  # pragma: no cover - import guard
            raise RuntimeError(
                "Audio output backend unavailable. Install extras with: pip install 'mc-assistant[voice]'"
            ) from exc

        self._engine = pyttsx3.init()
        if voice_id:
            self._engine.setProperty("voice", voice_id)
        if rate is not None:
            self._engine.setProperty("rate", rate)
        if volume is not None:
            clamped = max(0.0, min(1.0, volume))
            self._engine.setProperty("volume", clamped)

    def play(self, audio_bytes: bytes) -> None:
        text = audio_bytes.decode("utf-8", errors="ignore").strip()
        if not text:
            return
        self._engine.say(text)
        self._engine.runAndWait()
