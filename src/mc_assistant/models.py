from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


@dataclass(slots=True)
class CommandJob:
    job_id: str
    command: str
    status: JobStatus = JobStatus.queued
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    result: str | None = None
    error: str | None = None


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
class SeedKnowledge:
    seed: int | None
    confidence: float
    source: str
    requirements_missing: list[str] = field(default_factory=list)
