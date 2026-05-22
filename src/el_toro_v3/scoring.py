"""Shark Reflex Score calculation and posture bands."""

from __future__ import annotations

from .domain import ReflexPosture, clamp_unit


class SharkReflexScorer:
    """Convert normalized focus and urgency into a 0..100 reflex score."""

    def score(
        self,
        attention: float,
        confidence: float,
        urgency: float,
        entropy: float,
    ) -> float:
        numerator = (
            clamp_unit(attention)
            * clamp_unit(confidence)
            * clamp_unit(urgency)
        )
        entropy_floor = max(clamp_unit(entropy), 0.01)
        return round(min((numerator / entropy_floor) * 100.0, 100.0), 2)

    def posture(self, score: float) -> ReflexPosture:
        if score < 30.0:
            return ReflexPosture.OBSERVE
        if score < 60.0:
            return ReflexPosture.PREPARE
        if score < 80.0:
            return ReflexPosture.PARTIAL
        return ReflexPosture.ATTACK

