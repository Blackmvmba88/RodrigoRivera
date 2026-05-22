"""Shark attention scoring."""

from __future__ import annotations

from .domain import MarketSnapshot


class SharkAttention:
    """Focus attention on abnormal microstructure movement."""

    WEIGHTS = {
        "volatility_spike": 0.25,
        "volume_anomaly": 0.25,
        "spread_change": 0.20,
        "orderflow_imbalance": 0.20,
        "regime_shift": 0.10,
    }

    def score(self, market: MarketSnapshot) -> float:
        market = market.normalized()
        score = sum(
            getattr(market, signal) * weight
            for signal, weight in self.WEIGHTS.items()
        )
        return round(score, 4)

