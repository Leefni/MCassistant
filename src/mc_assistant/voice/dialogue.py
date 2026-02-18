"""Conversation-state helpers for multi-turn voice intent clarification."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

INTENT_SLOT_SCHEMA: dict[str, tuple[str, ...]] = {
    "run_minecraft_command": ("command",),
    "nearest_biome_or_structure": ("target",),
    "load_schematic": ("path",),
}


_SLOT_QUESTIONS: dict[str, str] = {
    "command": "What Minecraft command should I run?",
    "target": "What should I locate? For example: nearest village or nearest biome cherry_grove.",
    "path": "What schematic file path should I load?",
}


@dataclass(slots=True)
class ConversationState:
    """Tracks multi-turn clarification state for voice intent fulfillment."""

    pending_intent: str | None = None
    required_slots: list[str] = field(default_factory=list)
    collected_slots: dict[str, str] = field(default_factory=dict)
    last_question: str | None = None

    def begin(self, intent: str, required_slots: tuple[str, ...]) -> None:
        self.pending_intent = intent
        self.required_slots = list(required_slots)
        self.collected_slots = {}
        self.last_question = None

    def missing_slots(self) -> list[str]:
        return [slot for slot in self.required_slots if slot not in self.collected_slots]

    def complete(self) -> bool:
        return bool(self.pending_intent) and not self.missing_slots()

    def clear(self) -> None:
        self.pending_intent = None
        self.required_slots = []
        self.collected_slots = {}
        self.last_question = None


_STRUCTURE_HINTS = {
    "village",
    "stronghold",
    "temple",
    "desert_temple",
    "jungle_temple",
    "shipwreck",
    "ocean_monument",
    "trial_chambers",
    "ancient_city",
    "fortress",
    "bastion_remnant",
    "outpost",
    "mansion",
}


def question_for_slot(slot: str) -> str:
    return _SLOT_QUESTIONS.get(slot, f"Please provide {slot}.")


def extract_slots(intent_type: str, text: str) -> dict[str, str]:
    """Extract slot values from free-form utterances using lightweight regex rules."""
    normalized = " ".join(text.strip().split())
    slots: dict[str, str] = {}

    if intent_type == "run_minecraft_command":
        command = _extract_command(normalized)
        if command:
            slots["command"] = command

    if intent_type == "load_schematic":
        path = _extract_path(normalized)
        if path:
            slots["path"] = path

    if intent_type == "nearest_biome_or_structure":
        target = _extract_target(normalized)
        if target:
            slots["target"] = target

    return slots


def _extract_target(text: str) -> str | None:
    lowered = text.lower()
    explicit = re.search(r"(?:nearest|closest)\s+(biome|structure)\s+([a-zA-Z0-9_:-]+)", text, re.IGNORECASE)
    if explicit:
        return f"{explicit.group(1).lower()}:{explicit.group(2).lower()}"

    biome_match = re.search(r"(?:nearest|closest|where(?:\s+is)?\s+the\s+nearest)\s+biome\s+([a-zA-Z0-9_:-]+)", text, re.IGNORECASE)
    if biome_match:
        return f"biome:{biome_match.group(1).lower()}"

    for structure in sorted(_STRUCTURE_HINTS, key=len, reverse=True):
        if structure.replace("_", " ") in lowered or structure in lowered:
            return f"structure:{structure}"

    structure_match = re.search(r"(?:nearest|closest|where(?:\s+is)?\s+the\s+nearest)\s+([a-zA-Z0-9_:-]+)", text, re.IGNORECASE)
    if structure_match:
        candidate = structure_match.group(1).lower()
        if candidate not in {"biome", "structure"}:
            return f"structure:{candidate}"

    if "biome" in lowered:
        return "biome:unknown"
    if "structure" in lowered:
        return "structure:unknown"
    return None


def _extract_command(text: str) -> str | None:
    for pattern in (
        re.compile(r"^(?:run|execute|do)\s+(?:minecraft\s+)?command\s+(.+)$", re.IGNORECASE),
        re.compile(r"^(?:run|execute)\s+(.+)$", re.IGNORECASE),
    ):
        match = pattern.match(text)
        if match:
            return match.group(1).strip()
    return text.strip() or None


def _extract_path(text: str) -> str | None:
    path_match = re.search(r"(?:load|open|import)\s+(?:schematic\s+)?(.+)$", text, re.IGNORECASE)
    if path_match:
        return path_match.group(1).strip().strip('"\'')
    if "/" in text or text.endswith((".schem", ".schematic", ".litematic")):
        return text.strip().strip('"\'')
    return None
