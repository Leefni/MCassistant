"""Microphone capture and speech-to-text orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .interfaces import SpeechRecognizer


class VoiceListeningMode(str, Enum):
    """Available listening modes for speech capture."""

    PUSH_TO_TALK = "push_to_talk"
    ALWAYS_LISTENING = "always_listening"


@dataclass(slots=True)
class VoiceActivationConfig:
    """Activation parameters for voice listening and wake-word gating."""

    mode: VoiceListeningMode = VoiceListeningMode.PUSH_TO_TALK
    wake_word: str = "assistant"
    sensitivity_threshold: float = 0.1


@dataclass(slots=True)
class VoiceInputEvent:
    """Recognized utterance from microphone audio."""

    transcript: str
    activation_used: VoiceListeningMode
    wake_word_detected: bool


class MicrophoneSource(Protocol):
    """Represents a microphone-backed audio source."""

    def read_chunk(self) -> bytes:
        """Read and return the next audio chunk."""


class VoiceInputService:
    """Converts captured microphone audio chunks into transcripts."""

    def __init__(self, recognizer: SpeechRecognizer, config: VoiceActivationConfig | None = None) -> None:
        self._recognizer = recognizer
        self._config = config or VoiceActivationConfig()

    @property
    def config(self) -> VoiceActivationConfig:
        """Current activation config."""
        return self._config

    def update_config(
        self,
        *,
        mode: VoiceListeningMode | None = None,
        wake_word: str | None = None,
        sensitivity_threshold: float | None = None,
    ) -> None:
        """Update listening mode and activation thresholds at runtime."""
        if mode is not None:
            self._config.mode = mode
        if wake_word is not None:
            self._config.wake_word = wake_word.strip().lower()
        if sensitivity_threshold is not None:
            self._config.sensitivity_threshold = max(0.0, min(1.0, sensitivity_threshold))

    def capture_once(
        self,
        microphone: MicrophoneSource,
        *,
        push_to_talk_pressed: bool = False,
    ) -> VoiceInputEvent | None:
        """Capture a single chunk from microphone and transcribe when activated."""
        audio_bytes = microphone.read_chunk()
        return self.process_audio_chunk(audio_bytes, push_to_talk_pressed=push_to_talk_pressed)

    def process_audio_chunk(
        self,
        audio_bytes: bytes,
        *,
        push_to_talk_pressed: bool = False,
    ) -> VoiceInputEvent | None:
        """Transcribe one audio chunk if mode and sensitivity checks pass."""
        if not self._is_activation_allowed(push_to_talk_pressed=push_to_talk_pressed):
            return None

        if self._estimate_signal_level(audio_bytes) < self._config.sensitivity_threshold:
            return None

        transcript = self._recognizer.transcribe(audio_bytes).strip()
        if not transcript:
            return None

        wake_word_detected = self._contains_wake_word(transcript)
        if self._config.mode == VoiceListeningMode.ALWAYS_LISTENING and not wake_word_detected:
            return None

        return VoiceInputEvent(
            transcript=self._strip_wake_word(transcript) if wake_word_detected else transcript,
            activation_used=self._config.mode,
            wake_word_detected=wake_word_detected,
        )

    def _is_activation_allowed(self, *, push_to_talk_pressed: bool) -> bool:
        if self._config.mode == VoiceListeningMode.PUSH_TO_TALK:
            return push_to_talk_pressed
        return True

    def _contains_wake_word(self, transcript: str) -> bool:
        wake_word = self._config.wake_word.lower().strip()
        return bool(wake_word) and wake_word in transcript.lower()

    def _strip_wake_word(self, transcript: str) -> str:
        wake_word = self._config.wake_word.lower().strip()
        lowered = transcript.lower()
        idx = lowered.find(wake_word)
        if idx < 0:
            return transcript

        stripped = (transcript[:idx] + transcript[idx + len(wake_word) :]).strip(" ,:;.-")
        return stripped or transcript

    @staticmethod
    def _estimate_signal_level(audio_bytes: bytes) -> float:
        """Estimate normalized amplitude from 8-bit PCM-like bytes."""
        if not audio_bytes:
            return 0.0

        centered_total = sum(abs(sample - 128) for sample in audio_bytes)
        return centered_total / (len(audio_bytes) * 128)
