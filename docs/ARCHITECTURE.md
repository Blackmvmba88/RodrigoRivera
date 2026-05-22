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

## First Breath

`first_breath.py` adds the first paper loop around that seam:

```text
MarketPulse -> MedusaPerception -> RegimeAnomalyHydra
      |                |
      |                v
      |        latest RegimeHypothesis
      v                |
FirstBreathRuntime ----+
  -> dynamic threat threshold
  -> Shark route only on reflex interrupt
  -> paper account
  -> SQLite heartbeat journal + selective situation memory
```

Medusa receives pulse updates on a background worker. The Toro heartbeat reads
the latest valid hypothesis and submits the newest pulse afterward, so the
decision path never waits for cognition. The first `situation_memory` table is
kept intentionally small: `id`, `signature`, `action_taken`, `outcome`, and
`regime`.

## Replay Engine

`replay.py` reads versioned BTCUSDT JSONL scenarios from `replay/btcusdt`.
Replay swaps the live worker for a synchronous one-pulse-lag Hydra perception
so repeated stimuli keep deterministic route order while preserving Toro's
latest-valid-hypothesis rule.

```text
ReplayScenario -> ReplayRunner -> FirstBreathRuntime -> SQLite
                         |
                         +-> ReplayReport
                               heartbeats
                               routes and actions
                               regimes and memory writes
                               HydraSnapshot sequence
```

The bundled `calm_drift`, `spread_shock`, and `liquidity_hunt` scenarios are
synthetic behavioral fixtures. They train repeatability and regression
visibility before any live exchange feed is introduced.
