"""Live Minecraft command adapters.

These adapters are designed so command-runtime jobs can execute against a real game
instance (e.g., through minescript), while still being testable in CI where the
mod is not available.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from mc_assistant.adapters.game_command import GameCommandAdapter, MinescriptCommand


class MinescriptUnavailableError(RuntimeError):
    """Raised when minescript is not installed or has no supported command API."""


@dataclass(slots=True)
class MinescriptGameCommandAdapter(GameCommandAdapter):
    """Adapter that dispatches commands through a locally-imported `minescript` module."""

    command_prefix: str = "/"

    def __post_init__(self) -> None:
        self._executor = self._resolve_executor()

    def send(self, payload: MinescriptCommand) -> str | None:
        command = payload.command
        if self.command_prefix and not command.startswith(self.command_prefix):
            command = f"{self.command_prefix}{command}"

        result = self._executor(command)
        return "" if result is None else str(result)

    @staticmethod
    def _resolve_executor() -> Callable[[str], str | None]:
        try:
            module = importlib.import_module("minescript")
        except Exception as exc:  # noqa: BLE001
            raise MinescriptUnavailableError(
                "Unable to import minescript. Install it and ensure Minecraft + the mod are running."
            ) from exc

        for attr in ("execute", "run", "command", "chat_command"):
            fn = getattr(module, attr, None)
            if callable(fn):
                return fn

        raise MinescriptUnavailableError(
            "Imported minescript but found no supported API (expected execute/run/command/chat_command)."
        )


@dataclass(slots=True)
class SeedCrackerLogReader:
    """Utility for reading SeedCrackerX output written to a log file."""

    path: Path

    def read(self) -> str:
        if not self.path.exists():
            return ""
        return self.path.read_text(encoding="utf-8", errors="ignore")

    def tail(self, lines: int = 50) -> str:
        text = self.read()
        return "\n".join(text.splitlines()[-lines:])
