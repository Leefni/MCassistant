from mc_assistant.voice.input import VoiceActivationConfig, VoiceInputService, VoiceListeningMode


class StubRecognizer:
    def __init__(self, transcript: str) -> None:
        self.transcript = transcript

    def transcribe(self, audio_bytes: bytes) -> str:
        return self.transcript


def test_push_to_talk_requires_button_press() -> None:
    service = VoiceInputService(
        recognizer=StubRecognizer("run /say hi"),
        config=VoiceActivationConfig(mode=VoiceListeningMode.PUSH_TO_TALK, sensitivity_threshold=0.0),
    )

    not_pressed = service.process_audio_chunk(b"\x80\x80\xff", push_to_talk_pressed=False)
    pressed = service.process_audio_chunk(b"\x80\x80\xff", push_to_talk_pressed=True)

    assert not_pressed is None
    assert pressed is not None
    assert pressed.transcript == "run /say hi"


def test_always_listening_requires_wake_word() -> None:
    service = VoiceInputService(
        recognizer=StubRecognizer("assistant load schematic base.schem"),
        config=VoiceActivationConfig(
            mode=VoiceListeningMode.ALWAYS_LISTENING,
            wake_word="assistant",
            sensitivity_threshold=0.0,
        ),
    )

    event = service.process_audio_chunk(b"\x90\x90\x90")

    assert event is not None
    assert event.wake_word_detected is True
    assert event.transcript == "load schematic base.schem"
