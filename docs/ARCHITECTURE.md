# Architecture

## V3 seed

The Shark layer sits after upstream context engines and before any execution
surface.

```text
TelemetryFrame + ThermodynamicPIDState + NashContext
  -> UpstreamContextAdapter
  -> SharkRouteInput
  -> MarketSnapshot
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
| `upstream.py` | Context adapter from telemetry, PID stress, and Nash state |

## Current upstream seam

`UpstreamContextAdapter` converts telemetry into a normalized `MarketSnapshot`,
derives confidence from Nash edge and conflict, and derives urgency from PID
stress plus opponent pressure. It returns a `SharkRouteInput` with a short trace
so those inputs stay inspectable before routing.

The next live adapter should feed those upstream contracts from paper-trading
telemetry without letting execution code reach backward into market feature
calculation.
