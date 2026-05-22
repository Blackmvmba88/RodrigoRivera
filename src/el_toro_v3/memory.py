"""Predator memory for trap-pattern evidence."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from .domain import MarketSnapshot, TrapEvent, TrapPattern, clamp_unit


class PredatorMemory:
    """Bounded trap memory that stays explicit about why it recorded a pattern."""

    def __init__(self, limit: int = 256) -> None:
        self._events: deque[TrapEvent] = deque(maxlen=limit)

    @property
    def events(self) -> tuple[TrapEvent, ...]:
        return tuple(self._events)

    def record(
        self,
        pattern: TrapPattern,
        symbol: str,
        severity: float,
        evidence: Iterable[str],
    ) -> TrapEvent:
        event = TrapEvent(
            pattern=pattern,
            symbol=symbol,
            severity=clamp_unit(severity),
            evidence=tuple(evidence),
        )
        self._events.append(event)
        return event

    def remember_snapshot(self, market: MarketSnapshot) -> tuple[TrapEvent, ...]:
        market = market.normalized()
        events: list[TrapEvent] = []

        if market.spread_change > 0.70 and market.liquidity_vanishes:
            events.append(
                self.record(
                    TrapPattern.GHOST_LIQUIDITY,
                    market.symbol,
                    market.spread_change,
                    ("spread expansion", "liquidity vanished"),
                )
            )

        if market.volatility_spike > 0.80 and market.regime_shift < 0.35:
            events.append(
                self.record(
                    TrapPattern.POST_SPIKE_REVERSAL,
                    market.symbol,
                    market.volatility_spike,
                    ("large volatility spike", "regime did not confirm shift"),
                )
            )

        if market.orderflow_imbalance > 0.82 and market.volume_anomaly > 0.65:
            events.append(
                self.record(
                    TrapPattern.INSTITUTIONAL_ABSORPTION,
                    market.symbol,
                    (market.orderflow_imbalance + market.volume_anomaly) / 2.0,
                    ("orderflow imbalance", "volume anomaly"),
                )
            )

        return tuple(events)

    def recent_patterns(self, symbol: str, limit: int = 5) -> tuple[TrapPattern, ...]:
        recent = [
            event.pattern
            for event in reversed(self._events)
            if event.symbol == symbol
        ]
        return tuple(recent[:limit])

