import unittest

from el_toro_v3.attention import SharkAttention
from el_toro_v3.domain import MarketSnapshot


class SharkAttentionTests(unittest.TestCase):
    def test_attention_uses_weighted_microstructure_signals(self) -> None:
        market = MarketSnapshot(
            "BTC-USD",
            volatility_spike=1.0,
            volume_anomaly=0.8,
            spread_change=0.5,
            orderflow_imbalance=0.25,
            regime_shift=0.1,
            entropy=0.4,
        )

        self.assertEqual(SharkAttention().score(market), 0.61)

    def test_attention_clamps_out_of_range_input(self) -> None:
        market = MarketSnapshot(
            "BTC-USD",
            volatility_spike=3.0,
            volume_anomaly=-1.0,
            spread_change=0.0,
            orderflow_imbalance=0.0,
            regime_shift=0.0,
            entropy=0.4,
        )

        self.assertEqual(SharkAttention().score(market), 0.25)


if __name__ == "__main__":
    unittest.main()

