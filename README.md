# MC Assistant

Baseline scaffold for a Minecraft-focused assistant with explicit boundaries for game integration, reasoning, and interaction channels.

## Project Layout

```text
.
├── pyproject.toml
└── src/mc_assistant/
    ├── __init__.py
    ├── main.py
    ├── config.py
    ├── adapters/      # game command adapter (minescript integration)
    ├── voice/         # voice input/output contracts
    ├── world/         # seed/biome/structure intelligence
    ├── planning/      # recommendation engine contracts
    ├── schematics/    # schematic loading boundaries
    └── telemetry/     # telemetry and logging contracts
```

## Quickstart

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -e .
```

### 3) Run the assistant entrypoint

```bash
mc-assistant start
```

## Configuration

Runtime configuration is defined in `src/mc_assistant/config.py` and can be overridden via environment variables prefixed with `MC_ASSISTANT_`.

Examples:

```bash
export MC_ASSISTANT_LOG_LEVEL=DEBUG
export MC_ASSISTANT_MINESCRIPT_SOCKET=127.0.0.1:19132
```

## Module Boundaries

- **`mc_assistant.adapters`**: `GameCommandAdapter` contract for minescript/game command transport.
- **`mc_assistant.voice`**: `SpeechRecognizer` and `SpeechSynthesizer` contracts for audio I/O.
- **`mc_assistant.world`**: `WorldIntelligence` and `WorldFacts` model for seed/biome/structure logic.
- **`mc_assistant.planning`**: `RecommendationEngine` and `Recommendation` for task planning.
- **`mc_assistant.schematics`**: `SchematicLoader` interface for reading build schematics.
- **`mc_assistant.telemetry`**: `Telemetry` interface for structured logging/observability.

Each module currently defines interfaces and data models so implementations can be developed independently without tight coupling.
