import unittest

from el_toro_v3.domain import MarketSnapshot, PositionState, ReflexAction, ReflexPosture
from el_toro_v3.memory import PredatorMemory
from el_toro_v3.reflex import ReflexEngine
from el_toro_v3.router import SharkIntelligence
from el_toro_v3.scoring import SharkReflexScorer


class SharkReflexScorerTests(unittest.TestCase):
    def test_score_maps_to_posture_bands(self) -> None:
        scorer = SharkReflexScorer()

        self.assertEqual(scorer.posture(12.0), ReflexPosture.OBSERVE)
        self.assertEqual(scorer.posture(30.0), ReflexPosture.PREPARE)
        self.assertEqual(scorer.posture(60.0), ReflexPosture.PARTIAL)
        self.assertEqual(scorer.posture(80.0), ReflexPosture.ATTACK)

    def test_score_caps_entropy_amplification_at_one_hundred(self) -> None:
        scorer = SharkReflexScorer()

        self.assertEqual(scorer.score(1.0, 1.0, 1.0, 0.0), 100.0)


class ReflexEngineTests(unittest.TestCase):
    def test_spread_guard_beats_attack_posture(self) -> None:
        market = MarketSnapshot(
            "SOL-USD",
            0.8,
            0.7,
            0.9,
            0.8,
            0.5,
            0.4,
            spread_widens_fast=True,
        )

        action, reasons = ReflexEngine().action(market, None, ReflexPosture.ATTACK)

        self.assertEqual(action, ReflexAction.CANCEL_ORDER)
        self.assertIn("spread", reasons[0])

    def test_acceleration_against_open_position_exits(self) -> None:
        market = MarketSnapshot("AAPL", 0.4, 0.3, 0.2, 0.2, 0.1, 0.5, 0.9)
        position = PositionState("AAPL", "LONG", 2.0)

        action, _ = ReflexEngine().action(market, position, ReflexPosture.PREPARE)

        self.assertEqual(action, ReflexAction.EMERGENCY_EXIT)


class PredatorMemoryTests(unittest.TestCase):
    def test_memory_records_ghost_liquidity_and_absorption(self) -> None:
        memory = PredatorMemory()
        market = MarketSnapshot(
            "ETH-USD",
            volatility_spike=0.5,
            volume_anomaly=0.9,
            spread_change=0.8,
            orderflow_imbalance=0.95,
            regime_shift=0.4,
            entropy=0.5,
            liquidity_vanishes=True,
        )

        events = memory.remember_snapshot(market)

        self.assertEqual(len(events), 2)
        self.assertEqual(len(memory.recent_patterns("ETH-USD")), 2)


class SharkIntelligenceTests(unittest.TestCase):
    def test_router_exposes_guarded_decision_and_memory_hits(self) -> None:
        shark = SharkIntelligence()
        market = MarketSnapshot(
            "SOL-USD",
            volatility_spike=0.7,
            volume_anomaly=0.8,
            spread_change=0.88,
            orderflow_imbalance=0.72,
            regime_shift=0.5,
            entropy=0.42,
            liquidity_vanishes=True,
        )

        decision = shark.route(market, confidence=0.9, urgency=0.95)

        self.assertEqual(decision.action, ReflexAction.CANCEL_ORDER)
        self.assertEqual(decision.symbol, "SOL-USD")
        self.assertGreaterEqual(decision.score, 60.0)
        self.assertTrue(decision.memory_hits)
        self.assertTrue(any("memory recorded" in reason for reason in decision.reasons))


if __name__ == "__main__":
    unittest.main()

