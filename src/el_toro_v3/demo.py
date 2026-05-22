"""Synthetic demo for the El Toro V3 Shark layer."""

from __future__ import annotations

from .domain import MarketSnapshot, PositionState
from .router import SharkIntelligence
from .upstream import (
    NashContext,
    TelemetryFrame,
    ThermodynamicPIDState,
    UpstreamContextAdapter,
)


def main() -> None:
    shark = SharkIntelligence()
    scenarios = (
        (
            "quiet scan",
            MarketSnapshot("BTC-USD", 0.12, 0.18, 0.08, 0.20, 0.10, 0.45),
            0.50,
            0.35,
            None,
        ),
        (
            "wounded prey",
            MarketSnapshot("ETH-USD", 0.82, 0.78, 0.28, 0.88, 0.60, 0.32),
            0.92,
            0.96,
            None,
        ),
        (
            "spread trap",
            MarketSnapshot(
                "SOL-USD",
                0.62,
                0.67,
                0.90,
                0.66,
                0.42,
                0.48,
                spread_widens_fast=True,
                liquidity_vanishes=True,
            ),
            0.80,
            0.90,
            None,
        ),
        (
            "position under attack",
            MarketSnapshot(
                "AAPL",
                0.72,
                0.58,
                0.22,
                0.77,
                0.52,
                0.54,
                acceleration_against=0.84,
            ),
            0.86,
            0.88,
            PositionState("AAPL", "LONG", 4.0),
        ),
    )

    print("El Toro V3 - Predator Intelligence Edition")
    for label, market, confidence, urgency, position in scenarios:
        decision = shark.route(market, confidence, urgency, position)
        print()
        print(f"[{label}] {decision.symbol}")
        print(f"attention={decision.attention:.2f} score={decision.score:.2f}")
        print(f"posture={decision.posture.value} action={decision.action.value}")
        print("why=" + "; ".join(decision.reasons))

    print()
    print("predator_memory=" + ", ".join(pattern.value for pattern in shark.memory.recent_patterns("SOL-USD")))

    route_input = UpstreamContextAdapter().adapt(
        TelemetryFrame("NVDA", 0.68, 0.72, 0.25, 0.81, 0.58, 0.46),
        ThermodynamicPIDState(thermal_pressure=0.76, control_error=0.82, impulse=0.64),
        NashContext(edge_confidence=0.88, conflict=0.18, opponent_pressure=0.70),
    )
    decision = shark.route_input(route_input)

    print()
    print(f"[upstream adapter] {decision.symbol}")
    print(f"confidence={route_input.confidence:.2f} urgency={route_input.urgency:.2f}")
    print("trace=" + "; ".join(route_input.trace))
    print(f"posture={decision.posture.value} action={decision.action.value}")


if __name__ == "__main__":
    main()
