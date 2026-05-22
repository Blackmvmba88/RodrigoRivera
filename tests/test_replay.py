import tempfile
import unittest
from pathlib import Path

from el_toro_v3.replay import ReplayRunner, ReplayScenario, scenario_path


class ReplayRunnerTests(unittest.TestCase):
    def test_spread_shock_replay_is_repeatable_and_reports_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report_a = ReplayRunner(
                ReplayScenario(scenario_path("spread_shock")),
                Path(directory) / "spread-a.sqlite3",
                snapshot_every=3,
            ).run()
            report_b = ReplayRunner(
                ReplayScenario(scenario_path("spread_shock")),
                Path(directory) / "spread-b.sqlite3",
                snapshot_every=3,
            ).run()

        self.assertEqual(report_a.heartbeats, 7)
        self.assertGreaterEqual(report_a.interrupts, 1)
        self.assertIn("CANCEL_ORDER", report_a.actions)
        self.assertEqual(report_a.actions, report_b.actions)
        self.assertEqual(report_a.regimes, report_b.regimes)
        self.assertEqual(report_a.hydra_snapshots, report_b.hydra_snapshots)

    def test_calm_drift_has_lower_interrupt_pressure_than_spread_shock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            calm = ReplayRunner(
                ReplayScenario(scenario_path("calm_drift")),
                Path(directory) / "calm.sqlite3",
            ).run()
            shock = ReplayRunner(
                ReplayScenario(scenario_path("spread_shock")),
                Path(directory) / "shock.sqlite3",
            ).run()

        self.assertEqual(calm.interrupts, 0)
        self.assertGreater(shock.interrupt_rate, calm.interrupt_rate)
        self.assertEqual(calm.heartbeats, 6)


if __name__ == "__main__":
    unittest.main()
