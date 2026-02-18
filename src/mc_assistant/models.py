from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

@dataclass(slots=True)
class StructureLocation:
    structure: str
    dimension: str
    x: int
    z: int
    distance_blocks: float
    source: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BiomeLocation:
    biome: str
    dimension: str
    x: int
    z: int
    distance_blocks: float
    source: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SeedKnowledge:
    seed: int | None
    confidence: float
    source: str
    requirements_missing: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
