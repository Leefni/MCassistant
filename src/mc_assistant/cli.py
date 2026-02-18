"""CLI-facing command submission handler."""

from mc_assistant.command_runtime import CommandJob, CommandRuntime


class CliCommandHandler:
    """Provides command runtime APIs for CLI commands."""

    def __init__(self, runtime: CommandRuntime) -> None:
        self._runtime = runtime

    def submit_command(self, command: str) -> str:
        """Submit a command through CLI."""
        return self._runtime.submit_command(command)

    def get_job(self, job_id: str) -> CommandJob:
        """Get details for a submitted CLI command job."""
        return self._runtime.get_job(job_id)

    def list_recent_jobs(self, limit: int = 20) -> list[CommandJob]:
        """List recent command jobs for CLI usage."""
        return self._runtime.list_recent_jobs(limit=limit)
