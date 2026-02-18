from __future__ import annotations

import asyncio
from pathlib import Path

from mc_assistant.cli import CliCommandHandler
from mc_assistant.command_runtime import (
    CommandJobStatus,
    CommandRuntime,
    EchoGameCommandAdapter,
    JsonlHistoryStore,
)
from mc_assistant.voice import VoiceCommandHandler


class FailingAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def send(self, payload):
        self.calls += 1
        raise RuntimeError("boom")


class SlowAdapter:
    def send(self, payload):
        import time

        time.sleep(0.1)
        return "late"


def test_runtime_executes_command_successfully() -> None:
    async def _run() -> tuple[CommandJobStatus, str | None]:
        runtime = CommandRuntime(adapter=EchoGameCommandAdapter())
        await runtime.start()
        job_id = runtime.submit_command("/time set day")
        await asyncio.wait_for(runtime._queue.join(), timeout=1)
        job = runtime.get_job(job_id)
        await runtime.stop()
        return job.status, job.stdout

    status, stdout = asyncio.run(_run())
    assert status == CommandJobStatus.SUCCEEDED
    assert stdout == "executed: /time set day"


def test_runtime_retries_and_marks_failed() -> None:
    async def _run() -> tuple[int, CommandJobStatus, str | None]:
        adapter = FailingAdapter()
        runtime = CommandRuntime(adapter=adapter, max_retries=2, retry_delay_seconds=0)
        await runtime.start()
        job_id = runtime.submit_command("/say hi")
        await asyncio.wait_for(runtime._queue.join(), timeout=1)
        job = runtime.get_job(job_id)
        await runtime.stop()
        return adapter.calls, job.status, job.error

    calls, status, error = asyncio.run(_run())
    assert calls == 3
    assert status == CommandJobStatus.FAILED
    assert "RuntimeError" in (error or "")


def test_runtime_timeout() -> None:
    async def _run() -> tuple[CommandJobStatus, str | None]:
        runtime = CommandRuntime(
            adapter=SlowAdapter(),
            command_timeout_seconds=0.01,
            max_retries=0,
        )
        await runtime.start()
        job_id = runtime.submit_command("/say wait")
        await asyncio.wait_for(runtime._queue.join(), timeout=1)
        job = runtime.get_job(job_id)
        await runtime.stop()
        return job.status, job.error

    status, error = asyncio.run(_run())
    assert status == CommandJobStatus.TIMED_OUT
    assert "timed out" in (error or "")


def test_json_history_store_roundtrip(tmp_path: Path) -> None:
    store = JsonlHistoryStore(tmp_path / "history" / "commands.jsonl")
    runtime = CommandRuntime(adapter=EchoGameCommandAdapter(), history_store=store)
    cli = CliCommandHandler(runtime)
    voice = VoiceCommandHandler(runtime)

    job_id = cli.submit_command("/say cli")
    assert voice.get_job(job_id).command == "/say cli"
    recent = voice.list_recent_jobs(limit=5)

    assert recent[0].id == job_id
