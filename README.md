# MC Assistant

Minecraft automation assistant in Python with live command execution, SeedCrackerX status parsing, and seed-based locator queries.

## Features

- Run Minecraft commands in the background through command jobs.
- Live integration backend for `minescript` (with safe fallback to echo backend).
- Read SeedCrackerX logs and explain what is still missing if seed is not cracked.
- Resolve nearest structures/biomes through a real seed-based cubiomes-compatible CLI backend.
- CLI flows ready to be connected to voice intents.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

For live in-game command execution:

```bash
pip install minescript
```

## Configuration

Environment variables:

- `MC_ASSISTANT_MINECRAFT_ADAPTER=echo|minescript`
- `MC_ASSISTANT_MINESCRIPT_COMMAND_PREFIX=/`
- `MC_ASSISTANT_SEEDCRACKER_LOG_PATH=/path/to/seedcrackerx.log`
- `MC_ASSISTANT_SEEDCRACKER_START_COMMAND="seedcracker finder"`
- `MC_ASSISTANT_LOCATOR_BACKEND=stub|demo|cubiomes`
- `MC_ASSISTANT_LOCATOR_CUBIOMES_BIN=/path/to/cubiomes-cli`
- `MC_ASSISTANT_LOCATOR_MINECRAFT_VERSION=1.20.1`

## Usage

```bash
# runtime/backends
mc-assistant start

# execute live in-game command (uses selected adapter)
mc-assistant submit-command "time set day"

# collect basic live data from game
mc-assistant live-snapshot

# seedcracker workflows
mc-assistant seedcracker-start
mc-assistant seedcracker-tail --lines 120
mc-assistant seed-status --seedcracker-file ./seedcrackerx.log

# seed-based locating
mc-assistant nearest-structure --structure village --x 120 --z -340 --dimension overworld --seed 123456789
mc-assistant nearest-biome --biome cherry_grove --x 120 --z -340 --dimension overworld --seed 123456789
```

If seed is unknown, `nearest-*` output includes `missing_requirements` derived from SeedCrackerX logs.
