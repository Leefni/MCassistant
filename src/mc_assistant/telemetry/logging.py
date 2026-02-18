"""Contract for runtime telemetry and structured logging sinks."""

from typing import Protocol


class Telemetry(Protocol):
    """Reports operational events, traces, and assistant outcomes."""

    def emit(self, event_name: str, payload: dict) -> None:
        """Publish telemetry event to the configured sink."""
