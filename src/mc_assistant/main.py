"""CLI startup entrypoint for MC Assistant."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich import print

from mc_assistant.adapters import MinescriptGameCommandAdapter, MinescriptUnavailableError, SeedCrackerLogReader
from mc_assistant.assistant import MCAssistant
from mc_assistant.cli import CliCommandHandler
from mc_assistant.command_runtime import CommandJob, CommandJobStatus, CommandRuntime, EchoGameCommandAdapter
from mc_assistant.config import settings
from mc_assistant.game_state import GameStateCollector
from mc_assistant.seed_analysis import analyze_seedcracker_text
from mc_assistant.world_locator import CubiomesCliLocator, DemoVillageLocator, StubWorldLocator
from mc_assistant.adapters.game_command import MinescriptCommand
from mc_assistant.planning import Recommendation
from mc_assistant.world import WorldFacts
from datetime import datetime, timezone

app = typer.Typer(help="MC Assistant service entrypoint")


class _SnapshotWorldIntelligence:
    """Simple world intelligence from one-shot game-state snapshots."""

    def __init__(self, collector: GameStateCollector) -> None:
        self._collector = collector

    def inspect(self) -> WorldFacts:
        snapshot = self._collector.snapshot()
        return WorldFacts(
            seed=snapshot.seed,
            biome=snapshot.biome,
            nearest_structure=snapshot.nearest_structure,
        )


class _BasicRecommendationEngine:
    """Fallback recommendation strategy for voice chat."""

    def suggest(self, facts: WorldFacts, objective: str | None = None) -> list[Recommendation]:
        if objective:
            return [Recommendation(title=objective, rationale="Continuing with your stated objective.", priority=10)]

        if facts.nearest_structure:
            return [
                Recommendation(
                    title="Investigate nearby structure",
                    rationale=f"A nearby {facts.nearest_structure} may provide useful loot.",
                    priority=6,
                )
            ]
        return [Recommendation(title="Gather resources", rationale="Collect wood, food, and stone tools.", priority=5)]


class _FilesystemSchematicLoader:
    """Minimal schematic loader metadata provider for voice feedback."""

    def load(self, path: str) -> dict:
        target = Path(path).expanduser()
        if not target.exists():
            raise FileNotFoundError(f"Schematic not found: {target}")
        return {"path": str(target), "block_count": None}


class _SyncVoiceCommandHandler:
    """Synchronous command handler for interactive voice mode."""

    def __init__(self, adapter) -> None:
        self._adapter = adapter
        self._jobs: list[CommandJob] = []

    def submit_command(self, command: str) -> str:
        job = CommandJob(
            id=f"voice-{len(self._jobs)+1}",
            command=command,
            status=CommandJobStatus.RUNNING,
            submitted_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
        )
        try:
            response = self._adapter.send(MinescriptCommand(command=command))
            job.stdout = response
            job.status = CommandJobStatus.SUCCEEDED
        except Exception as exc:  # noqa: BLE001
            job.error = f"{type(exc).__name__}: {exc}"
            job.status = CommandJobStatus.FAILED
        job.finished_at = datetime.now(timezone.utc)
        self._jobs.insert(0, job)
        return job.id

    def list_recent_jobs(self, limit: int = 20) -> list[CommandJob]:
        return self._jobs[:limit]


def _build_game_adapter():
    backend = settings.minecraft_adapter.lower()
    if backend == "minescript":
        try:
            return MinescriptGameCommandAdapter(command_prefix=settings.minescript_command_prefix)
        except MinescriptUnavailableError:
            return EchoGameCommandAdapter()
    return EchoGameCommandAdapter()


def _build_runtime() -> CommandRuntime:
    return CommandRuntime(adapter=_build_game_adapter())


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


@app.command("voice-chat")
def voice_chat(
    wake_word: str = typer.Option("assistant", help="Wake word in always-listening mode"),
    always_listening: bool = typer.Option(False, help="Require wake word instead of push-to-talk"),
    phrase_time_limit: float = typer.Option(5.0, help="Per-utterance capture limit in seconds"),
) -> None:
    """Run an interactive voice loop with local STT/TTS backends."""
    from mc_assistant.voice import (
        ConversationState,
        VoiceActivationConfig,
        VoiceInputService,
        VoiceIntentParser,
        VoiceIntentRouter,
    )
    from mc_assistant.voice.input import VoiceListeningMode
    from mc_assistant.voice.output import VoiceOutputService

    try:
        from mc_assistant.voice.stt_speechrecognition import (
            SpeechRecognitionMicrophoneSource,
            SpeechRecognitionRecognizer,
        )
        from mc_assistant.voice.tts_pyttsx3 import Pyttsx3AudioOutputDevice, Pyttsx3SpeechSynthesizer
    except RuntimeError as exc:
        print({"error": str(exc)})
        raise typer.Exit(code=1)
    except ImportError:
        print({"error": "Voice extras are missing. Install with: pip install 'mc-assistant[voice]'"})
        raise typer.Exit(code=1)

    try:
        recognizer = SpeechRecognitionRecognizer()
        microphone = SpeechRecognitionMicrophoneSource(phrase_time_limit=phrase_time_limit)
        tts = Pyttsx3SpeechSynthesizer()
        output = Pyttsx3AudioOutputDevice()
    except RuntimeError as exc:
        print({"error": str(exc)})
        raise typer.Exit(code=1)

    mode = VoiceListeningMode.ALWAYS_LISTENING if always_listening else VoiceListeningMode.PUSH_TO_TALK
    input_service = VoiceInputService(
        recognizer=recognizer,
        config=VoiceActivationConfig(mode=mode, wake_word=wake_word, sensitivity_threshold=0.0),
    )
    output_service = VoiceOutputService(synthesizer=tts, output_device=output)

    collector = GameStateCollector(_build_game_adapter())
    router = VoiceIntentRouter(
        command_handler=_SyncVoiceCommandHandler(_build_game_adapter()),
        world_intelligence=_SnapshotWorldIntelligence(collector),
        recommendation_engine=_BasicRecommendationEngine(),
        schematic_loader=_FilesystemSchematicLoader(),
    )
    parser = VoiceIntentParser()
    conversation_state = ConversationState()

    print(
        {
            "voice_chat": "started",
            "mode": mode.value,
            "hint": "Say 'stop listening' to exit."
            if always_listening
            else "Press Enter to capture each utterance; say 'stop listening' to exit.",
        }
    )

    while True:
        if not always_listening:
            input("Press Enter to capture voice (Ctrl+C to quit) ...")

        event = input_service.capture_once(microphone, push_to_talk_pressed=not always_listening)
        if event is None:
            continue

        transcript = event.transcript.strip()
        if not transcript:
            continue
        if "stop listening" in transcript.lower():
            output_service.speak("Okay, stopping voice chat.")
            print({"voice_chat": "stopped"})
            break

        intent = parser.parse(transcript)
        response = router.handle(intent, utterance=transcript, conversation_state=conversation_state)
        print({"heard": transcript, "intent": intent.type.value, "response": response})
        output_service.speak(response)


if __name__ == "__main__":
    app()
