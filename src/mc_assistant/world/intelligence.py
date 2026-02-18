"""Domain model for world-state intelligence and lookup logic."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class WorldFacts:
    """Normalized world signals used by planning and recommendations."""

    seed: int | None
    biome: str | None
    nearest_structure: str | None


class WorldIntelligence(Protocol):
    """Service that infers facts about the current world and surroundings."""

    def inspect(self) -> WorldFacts:
        """Collect and return current world facts."""
