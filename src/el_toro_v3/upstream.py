"""Upstream adapters for the Shark layer."""

from __future__ import annotations

from dataclasses import dataclass

from .domain import MarketSnapshot, SharkRouteInput, clamp_unit


@dataclass(frozen=True, slots=True)
class TelemetryFrame:
    """Normalized microstructure observations before Shark routing."""

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

    def snapshot(self) -> MarketSnapshot:
        return MarketSnapshot(
            symbol=self.symbol,
            volatility_spike=self.volatility_spike,
            volume_anomaly=self.volume_anomaly,
            spread_change=self.spread_change,
            orderflow_imbalance=self.orderflow_imbalance,
            regime_shift=self.regime_shift,
            entropy=self.entropy,
            acceleration_against=self.acceleration_against,
            spread_widens_fast=self.spread_widens_fast,
            liquidity_vanishes=self.liquidity_vanishes,
        ).normalized()


@dataclass(frozen=True, slots=True)
class ThermodynamicPIDState:
    """Control stress emitted by the thermodynamic PID layer."""

    thermal_pressure: float
    control_error: float
    impulse: float


@dataclass(frozen=True, slots=True)
class NashContext:
    """Strategic context emitted by a Nash analysis surface."""

    edge_confidence: float
    conflict: float
    opponent_pressure: float


class UpstreamContextAdapter:
    """Translate upstream context into visible Shark route inputs."""

    def adapt(
        self,
        telemetry: TelemetryFrame,
        pid: ThermodynamicPIDState,
        nash: NashContext,
    ) -> SharkRouteInput:
        market = telemetry.snapshot()
        thermal_pressure = clamp_unit(pid.thermal_pressure)
        control_error = clamp_unit(pid.control_error)
        impulse = clamp_unit(pid.impulse)
        edge_confidence = clamp_unit(nash.edge_confidence)
        conflict = clamp_unit(nash.conflict)
        opponent_pressure = clamp_unit(nash.opponent_pressure)

        confidence = round(edge_confidence * (1.0 - (conflict * 0.25)), 4)
        urgency = round(
            clamp_unit(
                (thermal_pressure * 0.40)
                + (control_error * 0.35)
                + (impulse * 0.15)
                + (opponent_pressure * 0.10)
            ),
            4,
        )

        return SharkRouteInput(
            market=market,
            confidence=confidence,
            urgency=urgency,
            trace=(
                f"nash confidence={confidence:.4f} from edge={edge_confidence:.4f} conflict={conflict:.4f}",
                "pid urgency="
                f"{urgency:.4f} from pressure={thermal_pressure:.4f} "
                f"error={control_error:.4f} impulse={impulse:.4f} "
                f"opponent={opponent_pressure:.4f}",
            ),
        )
