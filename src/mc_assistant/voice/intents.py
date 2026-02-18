"""Spoken-intent parsing and dispatch for common assistant actions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from mc_assistant.planning import RecommendationEngine
from mc_assistant.schematics import SchematicLoader
from mc_assistant.voice.command_handler import VoiceCommandHandler
from mc_assistant.voice.dialogue import (
    INTENT_SLOT_SCHEMA,
    ConversationState,
    extract_slots,
    question_for_slot,
)
from mc_assistant.world import WorldIntelligence


class VoiceIntentType(str, Enum):
    """Supported voice intents for Minecraft helper actions."""

    RUN_COMMAND = "run_minecraft_command"
    LATEST_COMMAND_RESULT = "latest_command_result"
    NEAREST_BIOME_OR_STRUCTURE = "nearest_biome_or_structure"
    CURRENT_OBJECTIVE = "current_objective_or_next_action"
    LOAD_SCHEMATIC = "load_schematic"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class VoiceIntent:
    """Parsed voice intent and optional argument payload."""

    type: VoiceIntentType
    argument: str | None = None


class VoiceIntentParser:
    """Maps spoken phrases to structured intent objects."""

    _RUN_PATTERNS = (
        re.compile(r"^(?:run|execute|do)\s+(?:minecraft\s+)?command\s+(.+)$", re.IGNORECASE),
        re.compile(r"^(?:run|execute)\s+(.+)$", re.IGNORECASE),
    )
    _LOAD_SCHEMATIC_PATTERNS = (
        re.compile(r"^(?:load|open|import)\s+(?:schematic\s+)?(.+)$", re.IGNORECASE),
        re.compile(r"^load\s+schematic\s+(.+)$", re.IGNORECASE),
    )

    def parse(self, utterance: str) -> VoiceIntent:
        """Parse a recognized utterance into one of the known assistant intents."""
        text = " ".join(utterance.strip().split())
        lowered = text.lower()
        if not text:
            return VoiceIntent(type=VoiceIntentType.UNKNOWN)

        for pattern in self._RUN_PATTERNS:
            match = pattern.match(text)
            if match:
                return VoiceIntent(type=VoiceIntentType.RUN_COMMAND, argument=match.group(1).strip())

        if any(
            phrase in lowered
            for phrase in (
                "latest command result",
                "last command result",
                "what happened with my last command",
                "status of last command",
            )
        ):
            return VoiceIntent(type=VoiceIntentType.LATEST_COMMAND_RESULT)

        if any(
            phrase in lowered
            for phrase in (
                "nearest biome",
                "nearest structure",
                "closest biome",
                "closest structure",
            )
        ):
            return VoiceIntent(type=VoiceIntentType.NEAREST_BIOME_OR_STRUCTURE)

        if any(
            phrase in lowered
            for phrase in (
                "current objective",
                "next best action",
                "what should i do next",
                "what is my objective",
            )
        ):
            return VoiceIntent(type=VoiceIntentType.CURRENT_OBJECTIVE)

        for pattern in self._LOAD_SCHEMATIC_PATTERNS:
            match = pattern.match(text)
            if match:
                return VoiceIntent(
                    type=VoiceIntentType.LOAD_SCHEMATIC,
                    argument=match.group(1).strip().strip('"\''),
                )

        return VoiceIntent(type=VoiceIntentType.UNKNOWN)


class VoiceIntentRouter:
    """Executes parsed intents against runtime, world intelligence, and planning services."""

    def __init__(
        self,
        *,
        command_handler: VoiceCommandHandler,
        world_intelligence: WorldIntelligence,
        recommendation_engine: RecommendationEngine,
        schematic_loader: SchematicLoader,
    ) -> None:
        self._command_handler = command_handler
        self._world_intelligence = world_intelligence
        self._recommendation_engine = recommendation_engine
        self._schematic_loader = schematic_loader

    def handle(
        self,
        intent: VoiceIntent,
        *,
        objective: str | None = None,
        utterance: str | None = None,
        conversation_state: ConversationState | None = None,
    ) -> str:
        """Handle a parsed intent and return action output or a follow-up question."""
        state = conversation_state
        text = utterance or intent.argument or ""

        if state is not None:
            if intent.type != VoiceIntentType.UNKNOWN:
                required = INTENT_SLOT_SCHEMA.get(intent.type.value, ())
                if required:
                    state.begin(intent.type.value, required)
                    if intent.argument:
                        key = "command" if intent.type == VoiceIntentType.RUN_COMMAND else "path"
                        state.collected_slots[key] = intent.argument
                    state.collected_slots.update(extract_slots(intent.type.value, text))
                else:
                    state.clear()
            elif state.pending_intent:
                state.collected_slots.update(extract_slots(state.pending_intent, text))

            if state.pending_intent:
                missing = state.missing_slots()
                if missing:
                    question = question_for_slot(missing[0])
                    state.last_question = question
                    return question

                pending_intent = VoiceIntentType(state.pending_intent)
                response = self._execute(
                    pending_intent,
                    argument=state.collected_slots.get("command") or state.collected_slots.get("path"),
                    objective=objective,
                    slots=state.collected_slots,
                )
                state.clear()
                return response

        return self._execute(intent.type, argument=intent.argument, objective=objective, slots={})

    def _execute(
        self,
        intent_type: VoiceIntentType,
        *,
        argument: str | None,
        objective: str | None,
        slots: dict[str, str],
    ) -> str:
        if intent_type == VoiceIntentType.RUN_COMMAND:
            command_text = argument or slots.get("command")
            if not command_text:
                return "I did not catch the Minecraft command to run."
            job_id = self._command_handler.submit_command(command_text)
            return f"Queued command `{command_text}` as job {job_id}."

        if intent_type == VoiceIntentType.LATEST_COMMAND_RESULT:
            jobs = self._command_handler.list_recent_jobs(limit=1)
            if not jobs:
                return "No command results are available yet."
            latest = jobs[0]
            if latest.error:
                return f"Latest command `{latest.command}` is {latest.status.value}: {latest.error}"
            return (
                f"Latest command `{latest.command}` is {latest.status.value}. "
                f"Output: {latest.stdout or 'no output'}"
            )

        if intent_type == VoiceIntentType.NEAREST_BIOME_OR_STRUCTURE:
            facts = self._world_intelligence.inspect()
            biome = facts.biome or "unknown biome"
            structure = facts.nearest_structure or "unknown structure"
            requested = slots.get("target")
            context = ""
            if requested:
                context = (
                    f" Requested target {requested} near x={slots.get('x')}, z={slots.get('z')} "
                    f"in {slots.get('dimension')} using {slots.get('seed_source')}."
                )
            return (
                f"Nearest biome appears to be {biome}; nearest structure appears to be {structure}.{context}"
            )

        if intent_type == VoiceIntentType.CURRENT_OBJECTIVE:
            facts = self._world_intelligence.inspect()
            recommendations = self._recommendation_engine.suggest(facts, objective=objective)
            if not recommendations:
                return "I have no next action recommendation right now."
            best = sorted(recommendations, key=lambda rec: rec.priority, reverse=True)[0]
            return f"Current objective: {best.title}. Next best action: {best.rationale}"

        if intent_type == VoiceIntentType.LOAD_SCHEMATIC:
            schematic_path = argument or slots.get("path")
            if not schematic_path:
                return "Please specify a schematic path to load."
            payload = self._schematic_loader.load(schematic_path)
            block_count = payload.get("block_count")
            if block_count is None:
                return f"Loaded schematic from {schematic_path}."
            return f"Loaded schematic from {schematic_path} with {block_count} blocks."

        return "I could not map that phrase to a known intent."
