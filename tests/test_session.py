from pathlib import Path

from mc_assistant.adapters.game_command import MinescriptCommand
from mc_assistant.session import SessionCoordinator


class StubAdapter:
    def __init__(self, responses: dict[str, str] | None = None, fail: bool = False) -> None:
        self.responses = responses or {}
        self.fail = fail

    def send(self, payload: MinescriptCommand) -> str | None:
        if self.fail:
            raise RuntimeError("no game")
        return self.responses.get(payload.command)


def test_session_detects_instance_and_world_loaded(tmp_path: Path) -> None:
    log_path = tmp_path / "seed.log"
    log_path.write_text("Seed: 42\n", encoding="utf-8")
    adapter = StubAdapter({"data get entity @p Pos": "[0.0d, 64.0d, 0.0d]"})
    session = SessionCoordinator(adapter=adapter, seedcracker_log_path=str(log_path), configured_version="1.20.1")

    state = session.refresh()
    assert state.instance_running is True
    assert state.world_loaded is True

    session.grant_permission()
    assert session.state.cracked_seed == 42


def test_session_reports_missing_seed_log(tmp_path: Path) -> None:
    adapter = StubAdapter({"data get entity @p Pos": "[0.0d, 64.0d, 0.0d]"})
    missing = tmp_path / "missing.log"
    session = SessionCoordinator(adapter=adapter, seedcracker_log_path=str(missing), configured_version="1.20.1")
    session.grant_permission()

    assert session.state.cracked_seed is None
    assert "does not exist" in session.state.seed_requirements_missing[0]
