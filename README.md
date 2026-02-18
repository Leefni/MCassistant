# MC Assistant

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
