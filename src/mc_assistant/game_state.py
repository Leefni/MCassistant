"""Helpers for collecting live world/player signals from a running Minecraft instance."""

from __future__ import annotations

from dataclasses import dataclass

from mc_assistant.adapters.game_command import GameCommandAdapter, MinescriptCommand


@dataclass(slots=True)
class LiveSnapshot:
    position_raw: str | None
    biome_raw: str | None
    daytime_raw: str | None


class GameStateCollector:
    """Collects common world/player details via vanilla commands."""

    def __init__(self, adapter: GameCommandAdapter):
        self._adapter = adapter

    def _safe_command(self, command: str) -> str | None:
        try:
            return self._adapter.send(MinescriptCommand(command=command))
        except Exception:  # noqa: BLE001
            return None

    def snapshot(self) -> LiveSnapshot:
        return LiveSnapshot(
            position_raw=self._safe_command("data get entity @p Pos"),
            biome_raw=self._safe_command("execute positioned as @p run locate biome plains"),
            daytime_raw=self._safe_command("time query daytime"),
        )
