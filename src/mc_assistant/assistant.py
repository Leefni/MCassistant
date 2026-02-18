from __future__ import annotations

from dataclasses import asdict

from .command_runtime import CommandRuntime
from .models import SeedKnowledge, StructureLocation
from .seed_analysis import analyze_seedcracker_file
from .world_locator import WorldLocator


class MCAssistant:
    def __init__(self, runtime: CommandRuntime, locator: WorldLocator):
        self.runtime = runtime
        self.locator = locator

    def get_seed_status(self, seedcracker_log_path: str | None) -> SeedKnowledge:
        if not seedcracker_log_path:
            return SeedKnowledge(
                seed=None,
                confidence=0.0,
                source="none",
                requirements_missing=["SeedCrackerX log path is not configured"],
            )
        return analyze_seedcracker_file(seedcracker_log_path)

    def nearest_village(
        self,
        *,
        x: int,
        z: int,
        dimension: str,
        seed: int | None,
        seed_status: SeedKnowledge | None = None,
    ) -> tuple[StructureLocation | None, list[str]]:
        missing: list[str] = []
        if seed is None:
            if seed_status and seed_status.requirements_missing:
                missing.extend(seed_status.requirements_missing)
            else:
                missing.append("A cracked seed is required")
            return None, missing

        location = self.locator.nearest_structure(
            seed=seed,
            structure="village",
            x=x,
            z=z,
            dimension=dimension,
        )
        if location is None:
            return None, [
                "No structure locator backend returned data",
                "Configure a real seed-based biome/structure locator implementation",
            ]
        return location, []

    @staticmethod
    def format_location(location: StructureLocation) -> dict:
        return asdict(location)
