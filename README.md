# MC Assistant (Base Project)

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
