"""Asynchronous command runtime for dispatching Minescript commands."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from mc_assistant.adapters import GameCommandAdapter, MinescriptCommand


class CommandJobStatus(str, Enum):
    """Lifecycle states for submitted command jobs."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


@dataclass(slots=True)
class CommandJob:
    """Represents command execution state and final output."""

    id: str
    command: str
    submitted_at: datetime
    status: CommandJobStatus
    stdout: str | None = None
    error: str | None = None


class CommandHistoryStore(Protocol):
    """Persistence contract for storing command history."""

    def append(self, job: CommandJob) -> None:
        """Persist a finished job record."""

    def list_recent(self, limit: int) -> list[CommandJob]:
        """Return up to ``limit`` newest jobs."""


class InMemoryHistoryStore:
    """Bounded in-memory history store."""

    def __init__(self, max_jobs: int = 1_000) -> None:
        self._jobs: deque[CommandJob] = deque(maxlen=max_jobs)

    def append(self, job: CommandJob) -> None:
        self._jobs.appendleft(job)

    def list_recent(self, limit: int) -> list[CommandJob]:
        return list(self._jobs)[:limit]


class JsonlHistoryStore:
    """Simple JSONL-backed command history persistence."""

    def __init__(self, file_path: str | Path) -> None:
        self._path = Path(file_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, job: CommandJob) -> None:
        payload = asdict(job)
        payload["status"] = str(job.status)
        payload["submitted_at"] = job.submitted_at.isoformat()
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def list_recent(self, limit: int) -> list[CommandJob]:
        if not self._path.exists():
            return []

        jobs: list[CommandJob] = []
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                payload = json.loads(line)
                jobs.append(
                    CommandJob(
                        id=payload["id"],
                        command=payload["command"],
                        submitted_at=datetime.fromisoformat(payload["submitted_at"]),
                        status=CommandJobStatus(payload["status"]),
                        stdout=payload.get("stdout"),
                        error=payload.get("error"),
                    )
                )

        jobs.reverse()
        return jobs[:limit]


class CommandRuntime:
    """Queue-backed async runtime that executes game commands with retries."""

    def __init__(
        self,
        adapter: GameCommandAdapter,
        *,
        history_store: CommandHistoryStore | None = None,
        command_timeout_seconds: float = 5.0,
        max_retries: int = 1,
        retry_delay_seconds: float = 0.2,
        max_queue_size: int = 1_000,
        logger: logging.Logger | None = None,
    ) -> None:
        self._adapter = adapter
        self._history_store = history_store or InMemoryHistoryStore(max_jobs=max_queue_size)
        self._command_timeout_seconds = command_timeout_seconds
        self._max_retries = max_retries
        self._retry_delay_seconds = retry_delay_seconds
        self._logger = logger or logging.getLogger("mc_assistant.command_runtime")

        self._jobs: dict[str, CommandJob] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=max_queue_size)
        self._worker_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the worker loop once for this runtime."""
        if self._worker_task and not self._worker_task.done():
            return

        self._worker_task = asyncio.create_task(self._worker_loop(), name="command-runtime-worker")
        self._logger.info("command_runtime_started", extra={"queue_maxsize": self._queue.maxsize})

    async def stop(self) -> None:
        """Stop worker loop and wait for graceful cancellation."""
        if not self._worker_task:
            return

        self._worker_task.cancel()
        try:
            await self._worker_task
        except asyncio.CancelledError:
            pass
        finally:
            self._worker_task = None

        self._logger.info("command_runtime_stopped")

    def submit_command(self, command: str) -> str:
        """Submit a command and return the associated job id."""
        job_id = uuid4().hex
        job = CommandJob(
            id=job_id,
            command=command,
            submitted_at=datetime.now(timezone.utc),
            status=CommandJobStatus.QUEUED,
        )
        self._jobs[job_id] = job
        self._queue.put_nowait(job_id)
        self._logger.info(
            "command_submitted",
            extra={"job_id": job_id, "command": command, "queue_size": self._queue.qsize()},
        )
        return job_id

    def get_job(self, job_id: str) -> CommandJob:
        """Return job state for the given id."""
        if job_id not in self._jobs:
            raise KeyError(f"Unknown command job id: {job_id}")
        return self._jobs[job_id]

    def list_recent_jobs(self, limit: int = 20) -> list[CommandJob]:
        """Return most recent in-memory jobs and persisted history entries."""
        in_memory = sorted(self._jobs.values(), key=lambda job: job.submitted_at, reverse=True)
        if len(in_memory) >= limit:
            return in_memory[:limit]

        persisted = self._history_store.list_recent(limit)
        merged: list[CommandJob] = []
        seen: set[str] = set()
        for job in [*in_memory, *persisted]:
            if job.id in seen:
                continue
            seen.add(job.id)
            merged.append(job)
            if len(merged) >= limit:
                break
        return merged

    async def _worker_loop(self) -> None:
        while True:
            job_id = await self._queue.get()
            try:
                await self._execute_job(job_id)
            finally:
                self._queue.task_done()

    async def _execute_job(self, job_id: str) -> None:
        job = self._jobs[job_id]
        job.status = CommandJobStatus.RUNNING
        self._logger.info("command_started", extra={"job_id": job.id, "command": job.command})

        last_error: str | None = None
        for attempt in range(1, self._max_retries + 2):
            try:
                output = await asyncio.wait_for(
                    asyncio.to_thread(self._adapter.send, MinescriptCommand(command=job.command)),
                    timeout=self._command_timeout_seconds,
                )
                job.stdout = str(output) if output is not None else None
                job.status = CommandJobStatus.SUCCEEDED
                job.error = None
                self._logger.info(
                    "command_succeeded",
                    extra={"job_id": job.id, "attempt": attempt, "stdout": job.stdout},
                )
                break
            except asyncio.TimeoutError:
                last_error = (
                    f"Command timed out after {self._command_timeout_seconds}s "
                    f"(attempt {attempt}/{self._max_retries + 1})"
                )
                job.status = CommandJobStatus.TIMED_OUT
                self._logger.warning(
                    "command_timeout",
                    extra={"job_id": job.id, "attempt": attempt, "command": job.command},
                )
            except Exception as exc:  # noqa: BLE001 - runtime should capture execution failures.
                last_error = f"{type(exc).__name__}: {exc}"
                job.status = CommandJobStatus.FAILED
                self._logger.exception(
                    "command_failed",
                    extra={"job_id": job.id, "attempt": attempt, "command": job.command},
                )

            if attempt <= self._max_retries:
                await asyncio.sleep(self._retry_delay_seconds)

        if job.status != CommandJobStatus.SUCCEEDED:
            job.error = last_error or "Unknown command execution failure"
        self._history_store.append(job)


class EchoGameCommandAdapter:
    """Fallback adapter used for local CLI/voice demos and tests."""

    def send(self, payload: MinescriptCommand) -> str:
        return f"executed: {payload.command}"
