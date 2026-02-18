"""CLI startup entrypoint for MC Assistant."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich import print

from mc_assistant.adapters import MinescriptGameCommandAdapter, MinescriptUnavailableError, SeedCrackerLogReader
from mc_assistant.assistant import MCAssistant
from mc_assistant.cli import CliCommandHandler
from mc_assistant.command_runtime import CommandRuntime, EchoGameCommandAdapter
from mc_assistant.config import settings
from mc_assistant.game_state import GameStateCollector
from mc_assistant.seed_analysis import analyze_seedcracker_text
from mc_assistant.world_locator import CubiomesCliLocator, DemoVillageLocator, StubWorldLocator

app = typer.Typer(help="MC Assistant service entrypoint")


def _build_game_adapter():
    backend = settings.minecraft_adapter.lower()
    if backend == "minescript":
        try:
            return MinescriptGameCommandAdapter(command_prefix=settings.minescript_command_prefix)
        except MinescriptUnavailableError:
            return EchoGameCommandAdapter()
    return EchoGameCommandAdapter()

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

def _build_runtime() -> CommandRuntime:
    return CommandRuntime(adapter=_build_game_adapter())

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

def _build_locator(use_demo_locator: bool = False):
    if use_demo_locator or settings.locator_backend.lower() == "demo":
        return DemoVillageLocator()
    if settings.locator_backend.lower() == "cubiomes" and settings.locator_cubiomes_bin:
        return CubiomesCliLocator(
            binary_path=settings.locator_cubiomes_bin,
            minecraft_version=settings.locator_minecraft_version,
        )
    return StubWorldLocator()


def _build_assistant(use_demo_locator: bool = False) -> tuple[MCAssistant, CliCommandHandler]:
    runtime = _build_runtime()
    cli_handler = CliCommandHandler(runtime=runtime)
    assistant = MCAssistant(runtime=runtime, locator=_build_locator(use_demo_locator=use_demo_locator))
    return assistant, cli_handler


@app.command()
def start() -> None:
    """Show runtime backend configuration."""
    print(
        {
            "app_name": settings.app_name,
            "minecraft_adapter": settings.minecraft_adapter,
            "locator_backend": settings.locator_backend,
            "seedcracker_log_path": settings.seedcracker_log_path,
        }
    )


@app.command("seed-status")
def seed_status(seedcracker_file: str = typer.Option(None, help="Path to SeedCrackerX log export")) -> None:
    assistant, _ = _build_assistant()
    info = assistant.get_seed_status(seedcracker_file or settings.seedcracker_log_path)
    print(info)


@app.command("seedcracker-tail")
def seedcracker_tail(
    seedcracker_file: str = typer.Option(None, help="Path to SeedCrackerX log export"),
    lines: int = typer.Option(80, help="How many lines to read from the end"),
) -> None:
    path = seedcracker_file or settings.seedcracker_log_path
    if not path:
        raise typer.BadParameter("Provide --seedcracker-file or set MC_ASSISTANT_SEEDCRACKER_LOG_PATH")

    reader = SeedCrackerLogReader(Path(path))
    text = reader.tail(lines=lines)
    status = analyze_seedcracker_text(text)
    print({"tail": text, "parsed_status": status})


@app.command("seedcracker-start")
def seedcracker_start(command: str = typer.Option(None, help="In-game command to start/assist SeedCrackerX")) -> None:
    assistant, cli_handler = _build_assistant()
    cmd = command or settings.seedcracker_start_command

    async def _run() -> str:
        await assistant.runtime.start()
        job_id = cli_handler.submit_command(cmd)
        await asyncio.wait_for(assistant.runtime._queue.join(), timeout=2)
        job = cli_handler.get_job(job_id)
        await assistant.runtime.stop()
        return f"{job.id}: {job.status.value} ({job.stdout or job.error or ''})"

    print({"seedcracker_command_result": asyncio.run(_run())})


@app.command("live-snapshot")
def live_snapshot() -> None:
    collector = GameStateCollector(_build_game_adapter())
    print(collector.snapshot())


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
    assistant, _ = _build_assistant(use_demo_locator=use_demo_locator)
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
    assistant, _ = _build_assistant(use_demo_locator=use_demo_locator)
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
    """Submit an in-game command and wait for completion."""
    assistant, cli_handler = _build_assistant()

    async def _run() -> str:
        await assistant.runtime.start()
        job_id = cli_handler.submit_command(command)
        await asyncio.wait_for(assistant.runtime._queue.join(), timeout=5)
        job = cli_handler.get_job(job_id)
        await assistant.runtime.stop()
        return f"{job.id}: {job.status.value} ({job.stdout or job.error or ''})"

    print({"command_result": asyncio.run(_run())})


if __name__ == "__main__":
    app()
