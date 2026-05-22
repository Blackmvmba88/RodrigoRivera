"""Immediate reflex actions for risk-first execution guarding."""

from __future__ import annotations

from .domain import MarketSnapshot, PositionState, ReflexAction, ReflexPosture


class ReflexEngine:
    """Select fast guard actions before slower strategic posture is used."""

    def action(
        self,
        market: MarketSnapshot,
        position: PositionState | None,
        posture: ReflexPosture,
    ) -> tuple[ReflexAction, tuple[str, ...]]:
        market = market.normalized()

        if market.spread_widens_fast or market.spread_change > 0.75:
            return ReflexAction.CANCEL_ORDER, ("spread widened too fast",)

        if market.entropy > 0.85:
            return ReflexAction.REDUCE_SIZE, ("entropy exceeded reflex limit",)

        if market.liquidity_vanishes:
            return ReflexAction.SWITCH_PASSIVE, ("visible liquidity vanished",)

        if position and position.is_open and market.acceleration_against > 0.70:
            return ReflexAction.EMERGENCY_EXIT, ("price accelerated against position",)

        posture_action = {
            ReflexPosture.OBSERVE: ReflexAction.HOLD,
            ReflexPosture.PREPARE: ReflexAction.PREPARE_ORDER,
            ReflexPosture.PARTIAL: ReflexAction.EXECUTE_PARTIAL,
            ReflexPosture.ATTACK: ReflexAction.MAX_REFLEX,
        }
        return posture_action[posture], (f"score posture is {posture.value.lower()}",)

