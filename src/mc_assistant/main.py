"""CLI startup entrypoint for MC Assistant."""

from __future__ import annotations

import asyncio

import typer
from rich import print

from mc_assistant.cli import CliCommandHandler
from mc_assistant.command_runtime import CommandRuntime, EchoGameCommandAdapter
from mc_assistant.config import settings

app = typer.Typer(help="MC Assistant service entrypoint")

_runtime = CommandRuntime(adapter=EchoGameCommandAdapter())
_cli_handler = CliCommandHandler(runtime=_runtime)


@app.command()
def start() -> None:
    """Start the assistant runtime."""
    print(f"[green]{settings.app_name}[/green] starting with log level {settings.log_level}")
    print(f"Minescript adapter endpoint: {settings.minescript_socket}")


@app.command("submit-command")
def submit_command(command: str) -> None:
    """Submit a game command and wait briefly for async execution."""

    async def _run() -> str:
        await _runtime.start()
        job_id = _cli_handler.submit_command(command)
        await asyncio.sleep(0.01)
        await _runtime.stop()
        return job_id

    job_id = asyncio.run(_run())
    print(f"Submitted job: [cyan]{job_id}[/cyan]")


@app.command("get-job")
def get_job(job_id: str) -> None:
    """Show status for an existing command job."""
    try:
        job = _cli_handler.get_job(job_id)
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc

    print(
        {
            "id": job.id,
            "command": job.command,
            "submitted_at": job.submitted_at.isoformat(),
            "status": str(job.status),
            "stdout": job.stdout,
            "error": job.error,
        }
    )


@app.command("list-jobs")
def list_jobs(limit: int = 20) -> None:
    """List recent command jobs."""
    jobs = _cli_handler.list_recent_jobs(limit=limit)
    print(
        [
            {
                "id": job.id,
                "command": job.command,
                "submitted_at": job.submitted_at.isoformat(),
                "status": str(job.status),
                "stdout": job.stdout,
                "error": job.error,
            }
            for job in jobs
        ]
    )


if __name__ == "__main__":
    app()
