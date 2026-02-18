# MC Assistant (Base Project)

Python Minecraft assistant scaffold with:

- background command execution,
- SeedCrackerX seed status parsing,
- seed-based nearest structure/biome lookup,
- CLI endpoints that can later be wired to voice.

## What is implemented now

- Async command runtime with retries/timeouts/history.
- SeedCrackerX parsing that returns either a cracked seed or explicit missing requirements.
- Real locator integration via external cubiomes-compatible CLI backend.
- Fallback stub backend and demo backend for local flow checks.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configure

Environment variables:

- `MC_ASSISTANT_LOCATOR_BACKEND=cubiomes`
- `MC_ASSISTANT_LOCATOR_CUBIOMES_BIN=/path/to/cubiomes-cli`
- `MC_ASSISTANT_LOCATOR_MINECRAFT_VERSION=1.20.1`
- `MC_ASSISTANT_SEEDCRACKER_LOG_PATH=/path/to/seedcrackerx.log`

Your cubiomes CLI should support:

- `nearest-structure --seed ... --structure ... --x ... --z ... --dimension ... --version ... --json`
- `nearest-biome --seed ... --biome ... --x ... --z ... --dimension ... --version ... --json`

and return JSON containing at least `x` and `z`.

## Usage

```bash
mc-assistant seed-status --seedcracker-file ./seedcrackerx.log

mc-assistant nearest-structure \
  --structure village --x 120 --z -340 --dimension overworld \
  --seed 123456789

mc-assistant nearest-biome \
  --biome cherry_grove --x 120 --z -340 --dimension overworld \
  --seed 123456789
```

If the seed is not cracked, response includes `missing_requirements` explaining what is still needed.
A Python-first Minecraft assistant scaffold designed to:

- run minecraft commands in the background (via a game adapter such as `minescript`),
- keep command history and return results on request,
- parse SeedCrackerX output and explain seed-cracking progress,
- answer nearest structure/biome queries when a locator backend is configured,
- expose a CLI foundation that can later be connected to voice controls.

## Current status

This is a **base project scaffold** with pluggable backends.

Implemented now:

- asynchronous command runtime abstraction,
- seed intelligence model with "what is still missing" reporting,
- structure-locator abstraction + nearest village query endpoint,
- CLI commands for status and nearest-village flows.

Not yet implemented (next step):

- concrete `minescript` adapter integration with live game transport,
- concrete structure/biome locator using your preferred seed tool,
- voice input/output pipeline.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## CLI usage

```bash
mc-assistant status
mc-assistant seed-status --seedcracker-file ./seedcrackerx.log
mc-assistant nearest-village --x 120 --z -340 --dimension overworld --seed 123456789
```

If nearest-village returns unknown, the output includes what needs to be configured.

## Suggested next integration targets

- Seed source: SeedCrackerX exported logs/events.
- Locator backend: any deterministic seed-based locator that can compute nearest structures/biomes by dimension.
- Game transport: Minescript command bridge.
