"""Domain contracts for the El Toro V3 Shark layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


def clamp_unit(value: float) -> float:
    """Keep normalized signal inputs inside the expected 0..1 interval."""
    return max(0.0, min(1.0, value))


class ReflexAction(StrEnum):
    HOLD = "HOLD"
    PREPARE_ORDER = "PREPARE_ORDER"
    EXECUTE_PARTIAL = "EXECUTE_PARTIAL"
    MAX_REFLEX = "MAX_REFLEX"
    REDUCE_SIZE = "REDUCE_SIZE"
    CANCEL_ORDER = "CANCEL_ORDER"
    SWITCH_PASSIVE = "SWITCH_PASSIVE"
    EMERGENCY_EXIT = "EMERGENCY_EXIT"


class ReflexPosture(StrEnum):
    OBSERVE = "OBSERVE"
    PREPARE = "PREPARE"
    PARTIAL = "PARTIAL"
    ATTACK = "ATTACK"


class TrapPattern(StrEnum):
    FAKE_BREAKOUT = "FAKE_BREAKOUT"
    STOP_HUNT = "STOP_HUNT"
    INSTITUTIONAL_ABSORPTION = "INSTITUTIONAL_ABSORPTION"
    GHOST_LIQUIDITY = "GHOST_LIQUIDITY"
    POST_SPIKE_REVERSAL = "POST_SPIKE_REVERSAL"


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    symbol: str
    volatility_spike: float
    volume_anomaly: float
    spread_change: float
    orderflow_imbalance: float
    regime_shift: float
    entropy: float
    acceleration_against: float = 0.0
    spread_widens_fast: bool = False
    liquidity_vanishes: bool = False

    def normalized(self) -> "MarketSnapshot":
        return MarketSnapshot(
            symbol=self.symbol,
            volatility_spike=clamp_unit(self.volatility_spike),
            volume_anomaly=clamp_unit(self.volume_anomaly),
            spread_change=clamp_unit(self.spread_change),
            orderflow_imbalance=clamp_unit(self.orderflow_imbalance),
            regime_shift=clamp_unit(self.regime_shift),
            entropy=clamp_unit(self.entropy),
            acceleration_against=clamp_unit(self.acceleration_against),
            spread_widens_fast=self.spread_widens_fast,
            liquidity_vanishes=self.liquidity_vanishes,
        )


@dataclass(frozen=True, slots=True)
class PositionState:
    symbol: str
    side: str
    size: float

    @property
    def is_open(self) -> bool:
        return self.size > 0.0


@dataclass(frozen=True, slots=True)
class TrapEvent:
    pattern: TrapPattern
    symbol: str
    severity: float
    evidence: tuple[str, ...]
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class ReflexDecision:
    symbol: str
    attention: float
    score: float
    posture: ReflexPosture
    action: ReflexAction
    reasons: tuple[str, ...]
    memory_hits: tuple[TrapPattern, ...] = ()


@dataclass(frozen=True, slots=True)
class SharkRouteInput:
    market: MarketSnapshot
    confidence: float
    urgency: float
    trace: tuple[str, ...] = ()
