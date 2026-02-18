"""Core planning contracts for generating actionable recommendations."""

from dataclasses import dataclass
from typing import Protocol

from mc_assistant.world import WorldFacts


@dataclass(slots=True)
class Recommendation:
    """A prioritized task or action for the player."""

    title: str
    rationale: str
    priority: int = 0


class RecommendationEngine(Protocol):
    """Transforms world facts and goals into recommended next actions."""

    def suggest(self, facts: WorldFacts, objective: str | None = None) -> list[Recommendation]:
        """Return ordered recommendations for the current state."""
