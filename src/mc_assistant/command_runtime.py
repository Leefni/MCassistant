"""Asynchronous command execution runtime with retry and history support."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Protocol

from mc_assistant.adapters.game_command import GameCommandAdapter, MinescriptCommand


class CommandJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


@dataclass(slots=True)
class CommandJob:
    id: str
    command: str
    status: CommandJobStatus
    submitted_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    stdout: str | None = None
    error: str | None = None
    attempts: int = 0


class HistoryStore(Protocol):
    def append(self, job: CommandJob) -> None:
        ...


class JsonlHistoryStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, job: CommandJob) -> None:
        payload = asdict(job)
        payload["submitted_at"] = job.submitted_at.isoformat()
        payload["started_at"] = job.started_at.isoformat() if job.started_at else None
        payload["finished_at"] = job.finished_at.isoformat() if job.finished_at else None
        payload["status"] = job.status.value
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")


class EchoGameCommandAdapter:
    """Simple test adapter: returns executed command text."""

    def send(self, payload: MinescriptCommand) -> str:
        return f"executed: {payload.command}"


class CommandRuntime:
    def __init__(
        self,
        adapter: GameCommandAdapter,
        *,
        history_store: HistoryStore | None = None,
        command_timeout_seconds: float = 5.0,
        max_retries: int = 1,
        retry_delay_seconds: float = 0.25,
    ) -> None:
        self._adapter = adapter
        self._history_store = history_store
        self._timeout = command_timeout_seconds
        self._max_retries = max_retries
        self._retry_delay = retry_delay_seconds

        self._jobs: dict[str, CommandJob] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    def submit_command(self, command: str) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = CommandJob(
            id=job_id,
            command=command,
            status=CommandJobStatus.QUEUED,
            submitted_at=datetime.now(timezone.utc),
        )
        self._queue.put_nowait(job_id)
        return job_id

    def get_job(self, job_id: str) -> CommandJob:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise KeyError(f"Job not found: {job_id}") from exc

    def list_recent_jobs(self, limit: int = 20) -> list[CommandJob]:
        return sorted(self._jobs.values(), key=lambda job: job.submitted_at, reverse=True)[:limit]

    async def _worker(self) -> None:
        while True:
            job_id = await self._queue.get()
            job = self._jobs[job_id]
            await self._run_job(job)
            self._queue.task_done()

    async def _run_job(self, job: CommandJob) -> None:
        job.status = CommandJobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)

        for attempt in range(self._max_retries + 1):
            job.attempts = attempt + 1
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(self._adapter.send, MinescriptCommand(command=job.command)),
                    timeout=self._timeout,
                )
                job.stdout = response
                job.status = CommandJobStatus.SUCCEEDED
                break
            except asyncio.TimeoutError:
                job.error = f"Command timed out after {self._timeout} seconds"
                job.status = CommandJobStatus.TIMED_OUT
                break
            except Exception as exc:  # noqa: BLE001
                job.error = f"{type(exc).__name__}: {exc}"
                job.status = CommandJobStatus.FAILED
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_delay)
                    continue
                break

        job.finished_at = datetime.now(timezone.utc)
        if self._history_store is not None:
            self._history_store.append(job)
