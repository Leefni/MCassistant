from __future__ import annotations

import re
from pathlib import Path

from .models import SeedKnowledge

SEED_PATTERNS = [
    re.compile(r"(?:Cracked\s+seed|Seed)\s*[:=]\s*(-?\d+)", re.IGNORECASE),
    re.compile(r"seed\s+found\s*[:=]\s*(-?\d+)", re.IGNORECASE),
]
MISSING_PATTERNS = [
    re.compile(r"missing\s*[:=]\s*(.+)", re.IGNORECASE),
    re.compile(r"still\s+need\s*[:=]\s*(.+)", re.IGNORECASE),
    re.compile(r"not\s+enough\s+data\s*[:=]\s*(.+)", re.IGNORECASE),
]
CANDIDATE_PAT = re.compile(r"(?:candidates?|possible seeds?)\s*[:=]\s*(\d+)", re.IGNORECASE)
OBS_PAT = re.compile(r"(?:observations?|pillars?|structures?)\s*[:=]\s*(\d+)", re.IGNORECASE)


def _parse_missing_requirements(text: str) -> list[str]:
    missing: list[str] = []
    for line in text.splitlines():
        for pattern in MISSING_PATTERNS:
            match = pattern.search(line)
            if match:
                missing.extend(item.strip(" .") for item in match.group(1).split(",") if item.strip())

    if missing:
        return sorted(set(missing))

    return [
        "Capture additional structure observations in SeedCrackerX",
        "Let SeedCrackerX run longer while exploring distinct chunks",
    ]


def analyze_seedcracker_text(text: str) -> SeedKnowledge:
    for pattern in SEED_PATTERNS:
        seed_match = pattern.search(text)
        if seed_match:
            details: dict[str, int] = {}
            if (candidate_match := CANDIDATE_PAT.search(text)):
                details["candidate_count"] = int(candidate_match.group(1))
            if (obs_match := OBS_PAT.search(text)):
                details["observation_count"] = int(obs_match.group(1))
            return SeedKnowledge(
                seed=int(seed_match.group(1)),
                confidence=1.0,
                source="seedcrackerx",
                requirements_missing=[],
                details=details,
            )

    missing = _parse_missing_requirements(text)
    details = {}
    if (candidate_match := CANDIDATE_PAT.search(text)):
        details["candidate_count"] = int(candidate_match.group(1))
    if (obs_match := OBS_PAT.search(text)):
        details["observation_count"] = int(obs_match.group(1))

    return SeedKnowledge(
        seed=None,
        confidence=0.0,
        source="seedcrackerx",
        requirements_missing=missing,
        details=details,
    )


def analyze_seedcracker_file(path: str | Path) -> SeedKnowledge:
    text = Path(path).read_text(encoding="utf-8")
    return analyze_seedcracker_text(text)
