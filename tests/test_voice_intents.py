from datetime import datetime, timezone

from mc_assistant.command_runtime import CommandJob, CommandJobStatus
from mc_assistant.planning import Recommendation
from mc_assistant.voice.dialogue import ConversationState
from mc_assistant.voice.intents import VoiceIntent, VoiceIntentParser, VoiceIntentRouter, VoiceIntentType
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


def test_parser_maps_required_intents() -> None:
    parser = VoiceIntentParser()

    assert parser.parse("run minecraft command /time set day").type == VoiceIntentType.RUN_COMMAND
    assert parser.parse("what is the latest command result").type == VoiceIntentType.LATEST_COMMAND_RESULT
    assert parser.parse("nearest biome please").type == VoiceIntentType.NEAREST_BIOME_OR_STRUCTURE
    assert parser.parse("what is my current objective").type == VoiceIntentType.CURRENT_OBJECTIVE
    load_intent = parser.parse("load schematic starter.schem")
    assert load_intent.type == VoiceIntentType.LOAD_SCHEMATIC
    assert load_intent.argument == "starter.schem"


def test_router_handles_required_intents() -> None:
    router = VoiceIntentRouter(
        command_handler=StubCommandHandler(),
        world_intelligence=StubWorldIntelligence(),
        recommendation_engine=StubRecommendationEngine(),
        schematic_loader=StubSchematicLoader(),
    )
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
    command_handler = StubCommandHandler()
    router = VoiceIntentRouter(
        command_handler=command_handler,
        world_intelligence=StubWorldIntelligence(),
        recommendation_engine=StubRecommendationEngine(),
        schematic_loader=StubSchematicLoader(),
    )
    parser = VoiceIntentParser()
    state = ConversationState()

    first = router.handle(
        parser.parse("nearest biome"),
        utterance="nearest biome",
        conversation_state=state,
    )
    second = router.handle(
        parser.parse("biome desert x 100 z -250 in overworld use cracked seed"),
        utterance="biome desert x 100 z -250 in overworld use cracked seed",
        conversation_state=state,
    )

    assert "X coordinate" in first
    assert "Nearest biome appears to be plains" in second
    assert state.pending_intent is None
    assert command_handler.commands == []


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
