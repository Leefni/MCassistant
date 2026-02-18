from __future__ import annotations

import re
from pathlib import Path

from .models import SeedKnowledge

SEED_RE = re.compile(r"(?:seed\s*[:=]\s*|Cracked seed\s*[:=]\s*)(-?\d+)", re.IGNORECASE)
MISSING_RE = re.compile(r"missing\s*[:=]\s*(.+)", re.IGNORECASE)


def analyze_seedcracker_text(text: str) -> SeedKnowledge:
    seed_match = SEED_RE.search(text)
    if seed_match:
        return SeedKnowledge(
            seed=int(seed_match.group(1)),
            confidence=1.0,
            source="seedcrackerx",
            requirements_missing=[],
        )

    missing: list[str] = []
    for line in text.splitlines():
        m = MISSING_RE.search(line)
        if m:
            missing.extend(item.strip() for item in m.group(1).split(",") if item.strip())

    if not missing:
        missing = [
            "More structure observations from SeedCrackerX",
            "At least one confirmed structure set in overworld",
        ]

    return SeedKnowledge(seed=None, confidence=0.0, source="seedcrackerx", requirements_missing=missing)


def analyze_seedcracker_file(path: str | Path) -> SeedKnowledge:
    text = Path(path).read_text(encoding="utf-8")
    return analyze_seedcracker_text(text)
