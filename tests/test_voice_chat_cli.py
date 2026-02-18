from __future__ import annotations

import sys
import types

import pytest


def test_voice_chat_reports_actionable_error_when_voice_backends_missing(monkeypatch) -> None:
    typer_testing = pytest.importorskip("typer.testing")
    from mc_assistant.main import app

    fake_stt = types.ModuleType("mc_assistant.voice.stt_speechrecognition")
    fake_tts = types.ModuleType("mc_assistant.voice.tts_pyttsx3")

    class _MissingBackend:
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("Voice backend missing. Install with: pip install 'mc-assistant[voice]'")

    fake_stt.SpeechRecognitionRecognizer = _MissingBackend
    fake_stt.SpeechRecognitionMicrophoneSource = _MissingBackend
    fake_tts.Pyttsx3SpeechSynthesizer = _MissingBackend
    fake_tts.Pyttsx3AudioOutputDevice = _MissingBackend

    monkeypatch.setitem(sys.modules, "mc_assistant.voice.stt_speechrecognition", fake_stt)
    monkeypatch.setitem(sys.modules, "mc_assistant.voice.tts_pyttsx3", fake_tts)

    result = typer_testing.CliRunner().invoke(app, ["voice-chat", "--always-listening"], catch_exceptions=False)

    assert result.exit_code == 1
    assert "Install with: pip install 'mc-assistant[voice]'" in result.stdout
