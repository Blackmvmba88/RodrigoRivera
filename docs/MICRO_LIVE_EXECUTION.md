# Micro Live Execution Roadmap

El Toro V3 is paper-first and micro-live-capable.

The goal is not aggressive automated trading. The goal is to test whether the runtime can behave responsibly with extremely small capital while preserving operator control, auditability, and survival.

This document defines the safe path from deterministic replay to minimal live execution.

## Philosophy

Live execution is allowed only as a controlled experiment.

The system must earn the right to touch capital.

Micro-live mode exists for:

- validating real exchange latency and slippage,
- testing order lifecycle handling,
- observing whether reflex decisions survive real market noise,
- building operator confidence,
- improving solvency carefully without pretending that profit is guaranteed.

It is not designed for leverage, revenge trading, oversized positions, or autonomous capital deployment.

## Execution Ladder

```text
Deterministic Replay
        ↓
Paper Heartbeat
        ↓
Shadow Live Feed
        ↓
Dry-Run Broker Adapter
        ↓
Micro Live Execution
        ↓
Audited Expansion Only If Stable
```

No stage should be skipped.

## Micro-Live Definition

Micro-live means:

- tiny position size,
- no leverage by default,
- one active position at a time,
- strict daily loss cap,
- strict max order size,
- full journal logging,
- manual operator kill switch,
- live mode disabled by default.

Example initial constraints:

```text
MAX_POSITION_USD=10
MAX_DAILY_LOSS_USD=3
MAX_OPEN_POSITIONS=1
ALLOW_LEVERAGE=false
LIVE_MODE=false
KILL_SWITCH=armed
```

These values are intentionally small. The first goal is not income. The first goal is proving that the execution path does not behave recklessly.

## Required Gates Before Any Real Order

A real order can only pass if every gate accepts it:

```text
signal/reflex decision
        ↓
position size gate
        ↓
daily loss gate
        ↓
spread/slippage gate
        ↓
volatility stress gate
        ↓
cooldown gate
        ↓
kill-switch gate
        ↓
operator-live-mode gate
        ↓
broker adapter
```

If any gate fails, the order must be rejected and logged.

## Environment Variables

Live mode should require explicit environment flags.

```bash
export EL_TORO_LIVE_MODE=0
export EL_TORO_MAX_POSITION_USD=10
export EL_TORO_MAX_DAILY_LOSS_USD=3
export EL_TORO_MAX_OPEN_POSITIONS=1
export EL_TORO_ALLOW_LEVERAGE=0
export EL_TORO_KILL_SWITCH=armed
```

To enter micro-live mode, the operator must intentionally change:

```bash
export EL_TORO_LIVE_MODE=1
```

The code should refuse live execution if required limits are missing.

## Hard Safety Rules

The runtime must never:

- place an order without explicit live mode,
- trade without max position and daily loss limits,
- trade with missing journal logging,
- increase size after a loss automatically,
- use leverage by default,
- ignore the kill switch,
- hide rejected decisions,
- silently retry failed orders,
- assume paper performance equals live performance.

## Journal Requirements

Every live decision must write an immutable record:

```json
{
  "timestamp": "2026-05-28T00:00:00Z",
  "mode": "micro_live",
  "symbol": "BTCUSDT",
  "decision": "reduce_size",
  "allowed": false,
  "rejection_reason": "daily_loss_gate",
  "position_usd": 0,
  "max_position_usd": 10,
  "daily_pnl_usd": -3.04,
  "max_daily_loss_usd": 3,
  "reflex_score": 0.82,
  "stress": 0.77,
  "entropy": 0.69
}
```

The journal is part of the safety system, not an optional report.

## First Implementation Target

The first broker-facing implementation should not place real orders.

Target:

```text
BrokerAdapter.dry_run_order()
```

It should validate:

- credentials are loaded only from environment variables,
- symbol formatting is correct,
- order payloads are valid,
- journal output is complete,
- rejected orders are visible,
- live mode remains off by default.

Only after dry-run stability should real order placement be added.

## Minimal Live Order Policy

When real orders are introduced, the first live policy should be conservative:

```text
order_type = market or limit-only depending on adapter maturity
position_size = smallest practical notional
symbol = one high-liquidity pair only
max_open_positions = 1
cooldown_after_trade = required
cooldown_after_loss = longer
manual stop allowed at all times
```

No multi-symbol scanning during the first micro-live phase.

No pyramiding.

No autonomous size escalation.

## Expansion Rule

Capital limits can only increase if all conditions are true:

- positive or controlled paper/replay behavior,
- no journal gaps,
- no safety gate bypasses,
- live orders match intended payloads,
- slippage is understood,
- drawdown stays inside limits,
- operator approves the increase manually.

Expansion is earned, not assumed.

## Short README Phrase

Recommended project positioning:

```text
Paper-first. Micro-live-capable. Safety-gated.
Built to observe market stress, survive traps, and execute only under controlled risk.
```

## Boundary

This document does not claim profitability, financial advice, or live execution safety.

It defines the minimum safety architecture required before El Toro V3 is allowed to test tiny real orders under operator control.
