# MC Assistant

Baseline scaffold for a Minecraft-focused assistant with explicit boundaries for game integration, reasoning, and interaction channels.

## Python Version Target

- **Python 3.11+** (`requires-python = ">=3.11"` in `pyproject.toml`).

## Dependency Groups

Dependencies are grouped as optional extras in `pyproject.toml`:

- **Core (`core`)**: minescript adapter dependencies.
- **Voice (`voice`)**: speech-to-text and text-to-speech stack.
- **Async/runtime (`async_runtime`)**: task scheduling and queue helpers.
- **Data/parsing (`data_parsing`)**: world/mod parsing and calculation tools.
- **CLI (`cli`)**: command-line UX and config loading.
- **All (`all`)**: installs all feature groups.

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
python3.11 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

Install only CLI/core for baseline use:

```bash
pip install -e ".[cli,core]"
```

Install the full stack:

```bash
pip install -e ".[all]"
```

Install development tooling:

```bash
pip install -e ".[dev]"
```

### 3) Run the assistant entrypoint

```bash
mc-assistant start
```

Alternative direct module execution:

```bash
python -m mc_assistant.main start
```

## Configuration

Runtime configuration is defined in `src/mc_assistant/config.py` and can be overridden via environment variables prefixed with `MC_ASSISTANT_`.

Examples:

```bash
export MC_ASSISTANT_LOG_LEVEL=DEBUG
export MC_ASSISTANT_MINESCRIPT_SOCKET=127.0.0.1:19132
```


## Command Runtime

`mc_assistant.command_runtime` provides a queue-backed async execution layer for game commands with:

- `CommandJob` tracking (`id`, `command`, `submitted_at`, `status`, `stdout`, `error`)
- retry and timeout handling around the game adapter
- structured logging events for submit/start/success/failure/timeout
- in-memory history plus optional JSONL persistence (`JsonlHistoryStore`)

CLI and voice handlers both expose the same API shape:

- `submit_command(command: str) -> job_id`
- `get_job(job_id) -> CommandJob`
- `list_recent_jobs(limit=...)`

CLI commands:

```bash
mc-assistant submit-command "/say hello"
mc-assistant get-job <job_id>
mc-assistant list-jobs --limit 20
```

## Module Boundaries

- **`mc_assistant.adapters`**: `GameCommandAdapter` contract for minescript/game command transport.
- **`mc_assistant.voice`**: `SpeechRecognizer` and `SpeechSynthesizer` contracts for audio I/O.
- **`mc_assistant.world`**: `WorldIntelligence` and `WorldFacts` model for seed/biome/structure logic.
- **`mc_assistant.planning`**: `RecommendationEngine` and `Recommendation` for task planning.
- **`mc_assistant.schematics`**: `SchematicLoader` interface for reading build schematics.
- **`mc_assistant.telemetry`**: `Telemetry` interface for structured logging/observability.

Each module currently defines interfaces and data models so implementations can be developed independently without tight coupling.
