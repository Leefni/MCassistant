"""CLI-side handler wrappers and utility commands."""

from __future__ import annotations

from mc_assistant.command_runtime import CommandJob, CommandRuntime


class CliCommandHandler:
    """Simple sync-friendly facade over the async command runtime."""

    def __init__(self, runtime: CommandRuntime) -> None:
        self._runtime = runtime

    def submit_command(self, command: str) -> str:
        return self._runtime.submit_command(command)

    def get_job(self, job_id: str) -> CommandJob:
        return self._runtime.get_job(job_id)

    def list_recent_jobs(self, limit: int = 20) -> list[CommandJob]:
        return self._runtime.list_recent_jobs(limit=limit)
