"""Boundary for game command transport integrations."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class MinescriptCommand:
    """Canonical command payload directed to the game integration layer."""

    command: str


class GameCommandAdapter(Protocol):
    """Interface to send commands/events to Minecraft via minescript."""

    def send(self, payload: MinescriptCommand) -> str | None:
        """Dispatch a command payload to the running game instance."""
