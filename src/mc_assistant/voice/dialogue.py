"""Conversation-state helpers for multi-turn voice intent clarification."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

INTENT_SLOT_SCHEMA: dict[str, tuple[str, ...]] = {
    "run_minecraft_command": ("command",),
    "nearest_biome_or_structure": (
        "target",
        "x",
        "z",
        "dimension",
        "seed_source",
    ),
    "load_schematic": ("path",),
}


_SLOT_QUESTIONS: dict[str, str] = {
    "command": "What Minecraft command should I run?",
    "target": "Do you want the nearest biome or structure, and what name should I search for?",
    "x": "I need your current X coordinate. What is it?",
    "z": "I also need your current Z coordinate. What is it?",
    "dimension": "Which dimension are you in: overworld, nether, or end?",
    "seed_source": "Please provide the world seed, or tell me to use your cracked/current seed.",
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


_COORD_X = re.compile(r"\bx\s*(?:=|is)?\s*(-?\d+)\b", re.IGNORECASE)
_COORD_Z = re.compile(r"\bz\s*(?:=|is)?\s*(-?\d+)\b", re.IGNORECASE)
_COORD_PAIR = re.compile(r"(?:coords?|position)\s*(?:are|is|:)?\s*(-?\d+)\s*[ ,]+\s*(-?\d+)", re.IGNORECASE)
_SEED_NUMERIC = re.compile(r"\bseed\s*(?:=|is)?\s*(-?\d+)\b", re.IGNORECASE)


def question_for_slot(slot: str) -> str:
    return _SLOT_QUESTIONS.get(slot, f"Please provide {slot}.")


def extract_slots(intent_type: str, text: str) -> dict[str, str]:
    """Extract slot values from free-form utterances using lightweight regex rules."""
    normalized = " ".join(text.strip().split())
    lowered = normalized.lower()
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

        x_match = _COORD_X.search(normalized)
        z_match = _COORD_Z.search(normalized)
        if x_match:
            slots["x"] = x_match.group(1)
        if z_match:
            slots["z"] = z_match.group(1)

        pair_match = _COORD_PAIR.search(normalized)
        if pair_match:
            slots.setdefault("x", pair_match.group(1))
            slots.setdefault("z", pair_match.group(2))

        for dimension in ("overworld", "nether", "end"):
            if dimension in lowered:
                slots["dimension"] = dimension
                break

        seed_match = _SEED_NUMERIC.search(normalized)
        if seed_match:
            slots["seed_source"] = seed_match.group(1)
        elif "cracked seed" in lowered:
            slots["seed_source"] = "cracked seed"
        elif "current seed" in lowered or "my seed" in lowered:
            slots["seed_source"] = "current seed"

    return slots


def _extract_target(text: str) -> str | None:
    target_match = re.search(r"(?:nearest|closest)\s+(biome|structure)\s+([a-zA-Z0-9_:-]+)", text, re.IGNORECASE)
    if target_match:
        return f"{target_match.group(1).lower()}:{target_match.group(2)}"

    if "biome" in text.lower():
        return "biome:unknown"
    if "structure" in text.lower():
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
