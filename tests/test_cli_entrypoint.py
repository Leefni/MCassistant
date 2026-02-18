from __future__ import annotations

import importlib

import pytest


def test_console_entrypoint_exposes_app() -> None:
    pytest.importorskip("typer")

    module = importlib.import_module("mc_assistant.main")

    assert hasattr(module, "app")
    assert module.app is not None
