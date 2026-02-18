"""Session orchestration for live Minecraft + SeedCrackerX workflows."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from mc_assistant.adapters.game_command import GameCommandAdapter, MinescriptCommand
from mc_assistant.seed_analysis import analyze_seedcracker_file

_VERSION_RE = re.compile(r"\b(\d+\.\d+(?:\.\d+)?)\b")


@dataclass(slots=True)
class SessionState:
    instance_running: bool = False
    minecraft_version: str | None = None
    world_loaded: bool = False
    data_permission_granted: bool = False
    cracked_seed: int | None = None
    seed_waiting: bool = False
    seed_requirements_missing: list[str] = field(default_factory=list)


class SessionCoordinator:
    """Tracks whether game data can be consumed and whether a cracked seed is available."""

    def __init__(
        self,
        *,
        adapter: GameCommandAdapter,
        seedcracker_log_path: str | None,
        configured_version: str | None = None,
    ) -> None:
        self._adapter = adapter
        self._seedcracker_log_path = seedcracker_log_path
        self._configured_version = configured_version
        self._state = SessionState(minecraft_version=configured_version)

    @property
    def state(self) -> SessionState:
        return self._state

    def refresh(self) -> SessionState:
        position = self._safe_command("data get entity @p Pos")
        self._state.instance_running = position is not None
        self._state.world_loaded = bool(position)

        if self._state.minecraft_version is None:
            self._state.minecraft_version = self._detect_version()

        if self._state.data_permission_granted:
            self._refresh_seed_status()

        return self._state

    def grant_permission(self) -> None:
        self._state.data_permission_granted = True
        self._refresh_seed_status()

    def deny_permission(self) -> None:
        self._state.data_permission_granted = False

    def wait_for_cracked_seed(self, *, timeout_seconds: float = 30.0, poll_interval_seconds: float = 1.0) -> bool:
        if not self._state.data_permission_granted:
            return False

        deadline = time.monotonic() + timeout_seconds
        self._state.seed_waiting = True
        while time.monotonic() <= deadline:
            self._refresh_seed_status()
            if self._state.cracked_seed is not None:
                self._state.seed_waiting = False
                return True
            time.sleep(max(0.05, poll_interval_seconds))

        self._state.seed_waiting = False
        return False

    def _refresh_seed_status(self) -> None:
        if not self._seedcracker_log_path:
            self._state.cracked_seed = None
            self._state.seed_requirements_missing = ["SeedCrackerX log path is not configured"]
            return

        log_path = Path(self._seedcracker_log_path)
        if not log_path.exists():
            self._state.cracked_seed = None
            self._state.seed_requirements_missing = [f"SeedCrackerX log does not exist: {log_path}"]
            return

        knowledge = analyze_seedcracker_file(log_path)
        self._state.cracked_seed = knowledge.seed
        self._state.seed_requirements_missing = knowledge.requirements_missing

    def _safe_command(self, command: str) -> str | None:
        try:
            return self._adapter.send(MinescriptCommand(command=command))
        except Exception:  # noqa: BLE001
            return None

    def _detect_version(self) -> str | None:
        result = self._safe_command("seed")
        if result:
            match = _VERSION_RE.search(result)
            if match:
                return match.group(1)
        return self._configured_version
