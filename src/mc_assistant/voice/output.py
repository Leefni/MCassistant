"""Text-to-speech orchestration for spoken assistant responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .interfaces import SpeechSynthesizer


class AudioOutputDevice(Protocol):
    """Interface for a speaker/audio sink."""

    def play(self, audio_bytes: bytes) -> None:
        """Play synthesized audio bytes."""


@dataclass(slots=True)
class VoiceOutputConfig:
    """Configurable controls for response speech."""

    enabled: bool = True
    max_chars: int = 500


class VoiceOutputService:
    """Synthesizes text responses and sends them to an audio device."""

    def __init__(
        self,
        synthesizer: SpeechSynthesizer,
        output_device: AudioOutputDevice,
        config: VoiceOutputConfig | None = None,
    ) -> None:
        self._synthesizer = synthesizer
        self._output_device = output_device
        self._config = config or VoiceOutputConfig()

    def speak(self, text: str) -> bytes | None:
        """Synthesize and play assistant speech when output is enabled."""
        if not self._config.enabled:
            return None

        normalized = " ".join(text.split())
        if not normalized:
            return None

        limited = normalized[: self._config.max_chars]
        audio = self._synthesizer.synthesize(limited)
        self._output_device.play(audio)
        return audio
