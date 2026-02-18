"""CLI startup entrypoint for MC Assistant."""

from __future__ import annotations

import asyncio

import typer
from rich import print

from mc_assistant.assistant import MCAssistant
from mc_assistant.cli import CliCommandHandler
from mc_assistant.command_runtime import CommandRuntime, EchoGameCommandAdapter
from mc_assistant.config import settings
from mc_assistant.world_locator import CubiomesCliLocator, DemoVillageLocator, StubWorldLocator

app = typer.Typer(help="MC Assistant service entrypoint")

_runtime = CommandRuntime(adapter=EchoGameCommandAdapter())
_cli_handler = CliCommandHandler(runtime=_runtime)


def _build_locator(use_demo_locator: bool = False):
    if use_demo_locator:
        return DemoVillageLocator()
    if settings.locator_backend.lower() == "cubiomes" and settings.locator_cubiomes_bin:
        return CubiomesCliLocator(
            binary_path=settings.locator_cubiomes_bin,
            minecraft_version=settings.locator_minecraft_version,
        )
    return StubWorldLocator()


def _build_assistant(use_demo_locator: bool = False) -> MCAssistant:
    return MCAssistant(runtime=_runtime, locator=_build_locator(use_demo_locator=use_demo_locator))


@app.command()
def start() -> None:
    """Start the assistant runtime."""
    print(f"[green]{settings.app_name}[/green] starting with log level {settings.log_level}")
    print(f"Minescript adapter endpoint: {settings.minescript_socket}")


@app.command("seed-status")
def seed_status(seedcracker_file: str = typer.Option(None, help="Path to SeedCrackerX log export")) -> None:
    assistant = _build_assistant()
    info = assistant.get_seed_status(seedcracker_file or settings.seedcracker_log_path)
    print(info)


@app.command("nearest-structure")
def nearest_structure(
    structure: str = typer.Option(..., help="Structure type, e.g. village"),
    x: int = typer.Option(..., help="Current X"),
    z: int = typer.Option(..., help="Current Z"),
    dimension: str = typer.Option("overworld", help="overworld/nether/end"),
    seed: int = typer.Option(None, help="Known/cracked world seed"),
    seedcracker_file: str = typer.Option(None, help="Path to SeedCrackerX log export"),
    use_demo_locator: bool = typer.Option(False, help="Use deterministic demo locator"),
) -> None:
    assistant = _build_assistant(use_demo_locator=use_demo_locator)
    seed_state = assistant.get_seed_status(seedcracker_file or settings.seedcracker_log_path)
    effective_seed = seed if seed is not None else seed_state.seed
    location, missing = assistant.nearest_structure(
        structure=structure,
        x=x,
        z=z,
        dimension=dimension,
        seed=effective_seed,
        seed_status=seed_state,
    )
    if location is None:
        print({"nearest_structure": None, "missing_requirements": missing})
        raise typer.Exit(code=1)

    print({"nearest_structure": assistant.format_location(location), "missing_requirements": []})


@app.command("nearest-biome")
def nearest_biome(
    biome: str = typer.Option(..., help="Biome id, e.g. cherry_grove"),
    x: int = typer.Option(..., help="Current X"),
    z: int = typer.Option(..., help="Current Z"),
    dimension: str = typer.Option("overworld", help="overworld/nether/end"),
    seed: int = typer.Option(None, help="Known/cracked world seed"),
    seedcracker_file: str = typer.Option(None, help="Path to SeedCrackerX log export"),
    use_demo_locator: bool = typer.Option(False, help="Use deterministic demo locator"),
) -> None:
    assistant = _build_assistant(use_demo_locator=use_demo_locator)
    seed_state = assistant.get_seed_status(seedcracker_file or settings.seedcracker_log_path)
    effective_seed = seed if seed is not None else seed_state.seed
    location, missing = assistant.nearest_biome(
        biome=biome,
        x=x,
        z=z,
        dimension=dimension,
        seed=effective_seed,
        seed_status=seed_state,
    )
    if location is None:
        print({"nearest_biome": None, "missing_requirements": missing})
        raise typer.Exit(code=1)

    print({"nearest_biome": assistant.format_location(location), "missing_requirements": []})


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
