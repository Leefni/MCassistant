from __future__ import annotations

from dataclasses import asdict

from .command_runtime import CommandRuntime
from .models import BiomeLocation, SeedKnowledge, StructureLocation
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
        return self.nearest_structure(
            structure="village",
            x=x,
            z=z,
            dimension=dimension,
            seed=seed,
            seed_status=seed_status,
        )

    def nearest_structure(
        self,
        *,
        structure: str,
        x: int,
        z: int,
        dimension: str,
        seed: int | None,
        seed_status: SeedKnowledge | None = None,
    ) -> tuple[StructureLocation | None, list[str]]:
        seed_missing = self._seed_missing(seed=seed, seed_status=seed_status)
        if seed_missing:
            return None, seed_missing

        location = self.locator.nearest_structure(
            seed=seed,
            structure=structure,
            x=x,
            z=z,
            dimension=dimension,
        )
        if location is None:
            return None, [
                "No structure locator backend returned data",
                "Configure a cubiomes-compatible CLI and MC_ASSISTANT_LOCATOR_CUBIOMES_BIN",
            ]
        return location, []

    def nearest_biome(
        self,
        *,
        biome: str,
        x: int,
        z: int,
        dimension: str,
        seed: int | None,
        seed_status: SeedKnowledge | None = None,
    ) -> tuple[BiomeLocation | None, list[str]]:
        seed_missing = self._seed_missing(seed=seed, seed_status=seed_status)
        if seed_missing:
            return None, seed_missing

        location = self.locator.nearest_biome(seed=seed, biome=biome, x=x, z=z, dimension=dimension)
        if location is None:
            return None, [
                "No biome locator backend returned data",
                "Configure a cubiomes-compatible CLI and MC_ASSISTANT_LOCATOR_CUBIOMES_BIN",
            ]
        return location, []

    @staticmethod
    def _seed_missing(*, seed: int | None, seed_status: SeedKnowledge | None) -> list[str]:
        if seed is not None:
            return []
        if seed_status and seed_status.requirements_missing:
            return seed_status.requirements_missing
        return ["A cracked seed is required"]

    @staticmethod
    def format_location(location: StructureLocation | BiomeLocation) -> dict:
        return asdict(location)
