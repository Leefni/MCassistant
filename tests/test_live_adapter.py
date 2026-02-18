from __future__ import annotations

import sys
import types
from pathlib import Path

from mc_assistant.adapters.live_minecraft import MinescriptGameCommandAdapter, SeedCrackerLogReader


class _FakeMinescriptModule(types.SimpleNamespace):
    def __init__(self):
        super().__init__()
        self.calls: list[str] = []

    def execute(self, command: str) -> str:
        self.calls.append(command)
        return f"ok:{command}"


def test_minescript_adapter_dispatches_command(monkeypatch) -> None:
    fake = _FakeMinescriptModule()
    monkeypatch.setitem(sys.modules, "minescript", fake)

    adapter = MinescriptGameCommandAdapter(command_prefix="/")
    response = adapter.send(types.SimpleNamespace(command="time set day"))

    assert response == "ok:/time set day"
    assert fake.calls == ["/time set day"]


def test_seedcracker_log_reader_tail(tmp_path: Path) -> None:
    log_path = tmp_path / "seedcracker.log"
    log_path.write_text("a\nb\nc\n", encoding="utf-8")

    reader = SeedCrackerLogReader(log_path)
    assert reader.tail(lines=2) == "b\nc"
