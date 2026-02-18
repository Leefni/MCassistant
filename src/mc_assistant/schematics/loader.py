"""Interface for reading schematic files and exposing build instructions."""

from typing import Protocol


class SchematicLoader(Protocol):
    """Loads schematic artifacts from disk or remote storage."""

    def load(self, path: str) -> dict:
        """Return a normalized schematic payload."""
