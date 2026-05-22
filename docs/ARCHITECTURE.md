# Architecture

## V3 seed

The Shark layer sits after upstream context engines and before any execution
surface.

```text
MarketSnapshot
  -> SharkAttention
  -> SharkReflexScorer
  -> ReflexEngine
  -> ReflexRouter
  -> ReflexDecision
```

`PredatorMemory` runs beside the decision path. The current implementation
records explicit trap evidence rather than inferring hidden intent from thin
data.

## Responsibilities

| Module | Responsibility |
| --- | --- |
| `domain.py` | Typed snapshots, positions, memory events, and decisions |
| `attention.py` | Weighted attention score |
| `reflex.py` | Immediate guard action selection |
| `scoring.py` | Shark Reflex Score and posture bands |
| `memory.py` | Trap event recording and recent-pattern lookup |
| `router.py` | Single decision surface for the future execution guard |

## Next integration seam

The next upstream adapter should convert telemetry, PID state, and Nash output
into a normalized `MarketSnapshot`, `confidence`, and `urgency` triple. The
execution side should consume `ReflexDecision` without reaching backward into
market feature calculation.

