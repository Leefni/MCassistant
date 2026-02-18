"""Voice-oriented command submission handler."""

from mc_assistant.command_runtime import CommandJob, CommandRuntime


class VoiceCommandHandler:
    """Bridges recognized speech text into command runtime jobs."""

    def __init__(self, runtime: CommandRuntime) -> None:
        self._runtime = runtime

    def submit_command(self, command: str) -> str:
        """Submit a spoken command string for execution."""
        return self._runtime.submit_command(command)

    def get_job(self, job_id: str) -> CommandJob:
        """Get latest status for a previously submitted voice command."""
        return self._runtime.get_job(job_id)

    def list_recent_jobs(self, limit: int = 20) -> list[CommandJob]:
        """List the most recent command jobs submitted via any channel."""
        return self._runtime.list_recent_jobs(limit=limit)
