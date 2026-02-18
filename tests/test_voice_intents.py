from datetime import datetime, timezone

from mc_assistant.command_runtime import CommandJob, CommandJobStatus
from mc_assistant.models import SeedKnowledge, StructureLocation
from mc_assistant.planning import Recommendation
from mc_assistant.voice.dialogue import ConversationState
from mc_assistant.voice.intents import (
    PlayerContext,
    VoiceIntent,
    VoiceIntentParser,
    VoiceIntentRouter,
    VoiceIntentType,
)
from mc_assistant.world import WorldFacts


class StubCommandHandler:
    def __init__(self) -> None:
        self.commands: list[str] = []

    def submit_command(self, command: str) -> str:
        self.commands.append(command)
        return "job-123"

    def list_recent_jobs(self, limit: int = 20) -> list[CommandJob]:
        return [
            CommandJob(
                id="job-123",
                command="/say hi",
                status=CommandJobStatus.SUCCEEDED,
                submitted_at=datetime.now(timezone.utc),
                stdout="executed",
            )
        ]


class StubWorldIntelligence:
    def inspect(self) -> WorldFacts:
        return WorldFacts(seed=1, biome="plains", nearest_structure="village")


class StubRecommendationEngine:
    def suggest(self, facts: WorldFacts, objective: str | None = None) -> list[Recommendation]:
        return [Recommendation(title=objective or "Gather resources", rationale="Mine iron next.", priority=10)]


class StubSchematicLoader:
    def load(self, path: str) -> dict:
        return {"path": path, "block_count": 42}


class StubLocatorAssistant:
    def nearest_structure(self, **kwargs):
        seed = kwargs["seed"]
        if seed is None:
            return None, ["A cracked seed is required"]
        return (
            StructureLocation(
                structure=kwargs["structure"],
                dimension=kwargs["dimension"],
                x=100,
                z=-50,
                distance_blocks=12.0,
                source="stub",
            ),
            [],
        )

    def nearest_biome(self, **kwargs):
        return None, ["not implemented"]


class StubContextProvider:
    def current_context(self) -> PlayerContext | None:
        return PlayerContext(x=0, z=0, dimension="overworld")


def _build_router(**kwargs):
    return VoiceIntentRouter(
        command_handler=StubCommandHandler(),
        world_intelligence=StubWorldIntelligence(),
        recommendation_engine=StubRecommendationEngine(),
        schematic_loader=StubSchematicLoader(),
        **kwargs,
    )


def test_parser_maps_required_intents() -> None:
    parser = VoiceIntentParser()

    assert parser.parse("run minecraft command /time set day").type == VoiceIntentType.RUN_COMMAND
    assert parser.parse("what is the latest command result").type == VoiceIntentType.LATEST_COMMAND_RESULT
    assert parser.parse("nearest biome please").type == VoiceIntentType.NEAREST_BIOME_OR_STRUCTURE
    assert parser.parse("where is the nearest village").type == VoiceIntentType.NEAREST_BIOME_OR_STRUCTURE
    assert parser.parse("what is my current objective").type == VoiceIntentType.CURRENT_OBJECTIVE
    load_intent = parser.parse("load schematic starter.schem")
    assert load_intent.type == VoiceIntentType.LOAD_SCHEMATIC
    assert load_intent.argument == "starter.schem"


def test_router_handles_required_intents() -> None:
    router = _build_router()
    parser = VoiceIntentParser()

    run_resp = router.handle(parser.parse("run minecraft command /say hi"))
    latest_resp = router.handle(parser.parse("latest command result"))
    world_resp = router.handle(parser.parse("nearest structure"))
    objective_resp = router.handle(parser.parse("next best action"), objective="Find diamonds")
    load_resp = router.handle(parser.parse("load schematic castle.schem"))

    assert "job-123" in run_resp
    assert "Latest command" in latest_resp
    assert "nearest structure" in world_resp
    assert "Find diamonds" in objective_resp
    assert "42 blocks" in load_resp


def test_router_asks_followup_and_completes_pending_intent() -> None:
    router = _build_router(
        locator_assistant=StubLocatorAssistant(),
        player_context_provider=StubContextProvider(),
        seed_status_provider=lambda: SeedKnowledge(seed=1, confidence=1.0, source="test", requirements_missing=[]),
        seed_provider=lambda: 1,
    )
    parser = VoiceIntentParser()
    state = ConversationState()

    first = router.handle(
        parser.parse("nearest"),
        utterance="nearest",
        conversation_state=state,
    )
    second = router.handle(
        parser.parse("nearest village"),
        utterance="nearest village",
        conversation_state=state,
    )

    assert "What should I locate" in first
    assert "Nearest village is at x=100" in second
    assert state.pending_intent is None


def test_router_asks_for_missing_command_then_runs_it() -> None:
    command_handler = StubCommandHandler()
    router = VoiceIntentRouter(
        command_handler=command_handler,
        world_intelligence=StubWorldIntelligence(),
        recommendation_engine=StubRecommendationEngine(),
        schematic_loader=StubSchematicLoader(),
    )
    state = ConversationState()

    first = router.handle(
        intent=VoiceIntent(type=VoiceIntentType.RUN_COMMAND),
        utterance="",
        conversation_state=state,
    )
    second = router.handle(
        intent=VoiceIntentParser().parse("/say hello"),
        utterance="/say hello",
        conversation_state=state,
    )

    assert "What Minecraft command" in first
    assert "Queued command `/say hello` as job" in second
    assert command_handler.commands == ["/say hello"]


def test_router_explains_when_seed_not_cracked() -> None:
    router = _build_router(
        locator_assistant=StubLocatorAssistant(),
        player_context_provider=StubContextProvider(),
        seed_status_provider=lambda: SeedKnowledge(
            seed=None,
            confidence=0.0,
            source="test",
            requirements_missing=["SeedCrackerX still needs more data"],
        ),
        seed_provider=lambda: None,
    )

    response = router.handle(VoiceIntentParser().parse("where is the nearest village"), utterance="where is the nearest village")
    assert "can’t locate" in response
    assert "A cracked seed is required" in response
