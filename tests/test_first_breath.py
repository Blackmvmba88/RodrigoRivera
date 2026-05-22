import tempfile
import unittest
from pathlib import Path

from el_toro_v3.first_breath import (
    FirstBreathRuntime,
    FirstBreathStore,
    MarketPulse,
    MedusaPerception,
    RegimeAnomalyHydra,
    RegimeHypothesis,
)


class StaticMedusa:
    def __init__(self, hypothesis: RegimeHypothesis) -> None:
        self.latest = hypothesis
        self.submitted: list[MarketPulse] = []

    def submit(self, pulse: MarketPulse) -> None:
        self.submitted.append(pulse)

    def close(self) -> None:
        return None


class RegimeAnomalyHydraTests(unittest.TestCase):
    def test_hydra_marks_large_range_and_volume_delta_as_storm_anomaly(self) -> None:
        hydra = RegimeAnomalyHydra()
        calm = (
            MarketPulse("BTC/USDT", 100.0, 100.2, 99.9, 100.1, 1000, 0.03, 10),
            MarketPulse("BTC/USDT", 100.1, 100.3, 100.0, 100.2, 1010, 0.03, 12),
            MarketPulse("BTC/USDT", 100.2, 100.4, 100.1, 100.3, 1020, 0.03, 8),
        )
        for pulse in calm:
            hydra.observe(pulse)

        hypothesis = hydra.observe(
            MarketPulse("BTC/USDT", 100.3, 104.0, 97.0, 98.5, 3800, 0.55, -420)
        )

        self.assertEqual(hypothesis.regime, "storm")
        self.assertGreaterEqual(hypothesis.anomaly_score, 0.65)
        self.assertIn("wide_spread", hypothesis.signature)


class FirstBreathRuntimeTests(unittest.TestCase):
    def test_toro_uses_latest_hypothesis_and_journals_heartbeat(self) -> None:
        hypothesis = RegimeHypothesis(
            "BTC/USDT",
            "storm",
            anomaly_score=0.95,
            atr_percentile=0.98,
            spread_pressure=0.90,
            volume_delta_zscore=-3.4,
            sequence=9,
        )

        with tempfile.TemporaryDirectory() as directory:
            store = FirstBreathStore(Path(directory) / "breath.sqlite3")
            runtime = FirstBreathRuntime(store, medusa=StaticMedusa(hypothesis))
            heartbeat = runtime.tick(
                MarketPulse("BTC/USDT", 100.0, 103.0, 97.0, 98.0, 4000, 0.60, -450)
            )

            self.assertEqual(heartbeat.route, "REFLEX_INTERRUPT")
            self.assertNotEqual(heartbeat.action, "TORO_HOLD")
            self.assertEqual(heartbeat.perception_sequence, 9)
            self.assertEqual(store.heartbeat_count(), 1)
            runtime.close()

    def test_live_medusa_worker_can_be_closed_without_blocking(self) -> None:
        medusa = MedusaPerception()
        medusa.submit(MarketPulse("BTC/USDT", 100.0, 100.2, 99.9, 100.1, 1000, 0.03, 10))
        medusa.close()


if __name__ == "__main__":
    unittest.main()
