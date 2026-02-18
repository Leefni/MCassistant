from __future__ import annotations

from typing import Protocol


class MinecraftAdapter(Protocol):
    async def run_command(self, command: str) -> str:
        """Run a minecraft command and return textual result."""


class StubMinecraftAdapter:
    async def run_command(self, command: str) -> str:
        return f"[stub] executed: {command}"


class MinescriptAdapter:
    """Placeholder for concrete minescript integration in next step."""

    async def run_command(self, command: str) -> str:
        raise NotImplementedError(
            "Minescript adapter is not wired yet. Next step: connect to minescript API/event bus."
        )
