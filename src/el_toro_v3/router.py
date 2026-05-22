"""Single decision entrypoint for Shark Reflex Intelligence."""

from __future__ import annotations

from .attention import SharkAttention
from .domain import MarketSnapshot, PositionState, ReflexDecision
from .memory import PredatorMemory
from .reflex import ReflexEngine
from .scoring import SharkReflexScorer


class SharkIntelligence:
    """Route market snapshots through attention, memory, score, and reflex."""

    def __init__(
        self,
        memory: PredatorMemory | None = None,
        attention: SharkAttention | None = None,
        scorer: SharkReflexScorer | None = None,
        reflex: ReflexEngine | None = None,
    ) -> None:
        self.memory = memory or PredatorMemory()
        self.attention = attention or SharkAttention()
        self.scorer = scorer or SharkReflexScorer()
        self.reflex = reflex or ReflexEngine()

    def route(
        self,
        market: MarketSnapshot,
        confidence: float,
        urgency: float,
        position: PositionState | None = None,
    ) -> ReflexDecision:
        market = market.normalized()
        attention_score = self.attention.score(market)
        score = self.scorer.score(attention_score, confidence, urgency, market.entropy)
        posture = self.scorer.posture(score)
        remembered = self.memory.remember_snapshot(market)
        action, reasons = self.reflex.action(market, position, posture)

        memory_hits = tuple(event.pattern for event in remembered)
        if memory_hits:
            reasons = reasons + (
                "memory recorded " + ", ".join(pattern.value for pattern in memory_hits),
            )

        return ReflexDecision(
            symbol=market.symbol,
            attention=attention_score,
            score=score,
            posture=posture,
            action=action,
            reasons=reasons,
            memory_hits=memory_hits,
        )

