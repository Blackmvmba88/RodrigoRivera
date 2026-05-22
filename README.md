# RodrigoRivera

`El Toro V3 - Predator Intelligence Edition` is a thermodynamic predator
runtime for liquidity warfare, reflex execution, Nash-context analysis,
institutional behavior detection, and synthetic market cognition.

Observe silently. React instantly. Attack precisely.

This repository starts clean-room and paper-trading-first with the intelligence
layer for fast market reflexes.

The first increment implements the Shark Reflex Intelligence Layer:

```text
Telemetry -> Thermodynamic PID -> Nash Engine
                 |
                 v
         Shark Intelligence Layer
                 |
                 v
        Reflex Router / Execution Guard
```

This layer does not predict a candle direction. It evaluates microstructure
stress and returns visible reflex decisions before any broker integration
exists.

## Included now

- `Shark Attention` scores unusual volatility, volume, spread, orderflow, and
  regime movement.
- `Reflex Engine` applies guard-style actions such as cancel, reduce size,
  passive switching, and emergency exits.
- `Predator Memory` records suspicious trap patterns with evidence and
  severity.
- `Shark Reflex Score` turns attention, confidence, urgency, and entropy into
  an interpreted execution posture.
- `Reflex Router` exposes the final guarded decision for downstream execution.
- `Upstream Context Adapter` converts telemetry, thermodynamic PID stress, and
  Nash context into the normalized Shark route input with a visible trace.
- `First Breath` runs one paper heartbeat with a non-blocking regime Hydra,
  dynamic threat threshold, paper account, SQLite journal, and selective
  situation memory.

## Run

```bash
PYTHONPATH=src python3 -m el_toro_v3.demo
PYTHONPATH=src python3 -m el_toro_v3.first_breath
python3 -m unittest discover -s tests -v
```

## Boundary

This version is a deterministic local core fed by synthetic snapshots and a
paper heartbeat feed. It does not connect to exchanges, place orders, or claim
live execution safety yet.
