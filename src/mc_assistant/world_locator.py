from __future__ import annotations

import math
from typing import Protocol

from .models import StructureLocation


class WorldLocator(Protocol):
    def nearest_structure(self, *, seed: int, structure: str, x: int, z: int, dimension: str) -> StructureLocation | None:
        ...


class StubWorldLocator:
    """Base placeholder until a real seed-backed structure locator is integrated."""

    def nearest_structure(self, *, seed: int, structure: str, x: int, z: int, dimension: str) -> StructureLocation | None:
        return None


class DemoVillageLocator:
    """Deterministic demo locator (not accurate to Minecraft generation)."""

    def nearest_structure(self, *, seed: int, structure: str, x: int, z: int, dimension: str) -> StructureLocation | None:
        if structure.lower() != "village" or dimension != "overworld":
            return None

        target_x = int((seed % 4000) - 2000)
        target_z = int(((seed // 7) % 4000) - 2000)
        distance = math.dist((x, z), (target_x, target_z))
        return StructureLocation(
            structure="village",
            dimension=dimension,
            x=target_x,
            z=target_z,
            distance_blocks=distance,
            source="demo-locator",
            details={"warning": "Demo locator only; integrate real structure backend next."},
        )
