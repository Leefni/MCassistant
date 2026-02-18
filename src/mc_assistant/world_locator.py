from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Protocol

from .models import BiomeLocation, StructureLocation


class WorldLocator(Protocol):
    def nearest_structure(self, *, seed: int, structure: str, x: int, z: int, dimension: str) -> StructureLocation | None:
        ...

    def nearest_biome(self, *, seed: int, biome: str, x: int, z: int, dimension: str) -> BiomeLocation | None:
        ...


class StubWorldLocator:
    """Base placeholder until a real seed-backed structure locator is integrated."""

    def nearest_structure(self, *, seed: int, structure: str, x: int, z: int, dimension: str) -> StructureLocation | None:
        return None

    def nearest_biome(self, *, seed: int, biome: str, x: int, z: int, dimension: str) -> BiomeLocation | None:
        return None


class CubiomesCliLocator:
    """Real seed-based locator using an external cubiomes-compatible CLI.

    The binary must support commands:
      - nearest-structure --seed <seed> --structure <name> --x <x> --z <z> --dimension <dim> --json
      - nearest-biome --seed <seed> --biome <name> --x <x> --z <z> --dimension <dim> --json

    and print JSON with at least keys: x, z.
    """

    def __init__(self, binary_path: str, minecraft_version: str = "1.20.1"):
        self.binary_path = str(Path(binary_path))
        self.minecraft_version = minecraft_version

    def nearest_structure(self, *, seed: int, structure: str, x: int, z: int, dimension: str) -> StructureLocation | None:
        payload = self._run_locator(
            mode="nearest-structure",
            target_flag="--structure",
            target=structure,
            seed=seed,
            x=x,
            z=z,
            dimension=dimension,
        )
        if payload is None:
            return None

        target_x = int(payload["x"])
        target_z = int(payload["z"])
        return StructureLocation(
            structure=structure,
            dimension=dimension,
            x=target_x,
            z=target_z,
            distance_blocks=math.dist((x, z), (target_x, target_z)),
            source="cubiomes-cli",
            details={"version": self.minecraft_version, "raw": payload},
        )

    def nearest_biome(self, *, seed: int, biome: str, x: int, z: int, dimension: str) -> BiomeLocation | None:
        payload = self._run_locator(
            mode="nearest-biome",
            target_flag="--biome",
            target=biome,
            seed=seed,
            x=x,
            z=z,
            dimension=dimension,
        )
        if payload is None:
            return None

        target_x = int(payload["x"])
        target_z = int(payload["z"])
        return BiomeLocation(
            biome=biome,
            dimension=dimension,
            x=target_x,
            z=target_z,
            distance_blocks=math.dist((x, z), (target_x, target_z)),
            source="cubiomes-cli",
            details={"version": self.minecraft_version, "raw": payload},
        )

    def _run_locator(
        self,
        *,
        mode: str,
        target_flag: str,
        target: str,
        seed: int,
        x: int,
        z: int,
        dimension: str,
    ) -> dict | None:
        cmd = [
            self.binary_path,
            mode,
            "--seed",
            str(seed),
            target_flag,
            target,
            "--x",
            str(x),
            "--z",
            str(z),
            "--dimension",
            dimension,
            "--version",
            self.minecraft_version,
            "--json",
        ]

        try:
            result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

        if not isinstance(payload, dict) or "x" not in payload or "z" not in payload:
            return None

        return payload


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

    def nearest_biome(self, *, seed: int, biome: str, x: int, z: int, dimension: str) -> BiomeLocation | None:
        target_x = int((seed % 8000) - 4000)
        target_z = int(((seed // 13) % 8000) - 4000)
        distance = math.dist((x, z), (target_x, target_z))
        return BiomeLocation(
            biome=biome,
            dimension=dimension,
            x=target_x,
            z=target_z,
            distance_blocks=distance,
            source="demo-locator",
            details={"warning": "Demo locator only; integrate real biome backend next."},
        )
