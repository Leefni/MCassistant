"""Contracts for speech recognition and synthesis."""

from typing import Protocol


class SpeechRecognizer(Protocol):
    """Converts live or buffered audio into text."""

    def transcribe(self, audio_bytes: bytes) -> str:
        """Return recognized text from raw audio input."""


class SpeechSynthesizer(Protocol):
    """Converts text responses into audio output."""

    def synthesize(self, text: str) -> bytes:
        """Return playable audio bytes for the given text."""
