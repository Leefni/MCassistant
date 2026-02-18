from __future__ import annotations

import json
from pathlib import Path

from mc_assistant.seed_analysis import analyze_seedcracker_text
from mc_assistant.world_locator import CubiomesCliLocator


def test_seedcracker_extracts_seed_and_details() -> None:
    text = """
    Seed: 123456
    candidates: 1
    observations: 7
    """
    state = analyze_seedcracker_text(text)

    assert state.seed == 123456
    assert state.requirements_missing == []
    assert state.details["candidate_count"] == 1
    assert state.details["observation_count"] == 7


def test_seedcracker_missing_requirements() -> None:
    text = "still need: desert temple, jungle temple"
    state = analyze_seedcracker_text(text)

    assert state.seed is None
    assert "desert temple" in state.requirements_missing


def test_cubiomes_cli_locator_structure(tmp_path: Path) -> None:
    script = tmp_path / "fake_locator.py"
    script.write_text(
        """
import json
print(json.dumps({"x": 200, "z": -50}))
""".strip(),
        encoding="utf-8",
    )

    locator = CubiomesCliLocator(binary_path="python", minecraft_version="1.20.1")
    # call private helper to validate subprocess/json integration in a portable way
    payload = locator._run_locator(
        mode=str(script),
        target_flag="--structure",
        target="village",
        seed=1,
        x=0,
        z=0,
        dimension="overworld",
    )
    assert payload == {"x": 200, "z": -50}
