import unittest

from el_toro_v3.domain import PositionState, ReflexAction
from el_toro_v3.router import SharkIntelligence
from el_toro_v3.upstream import (
    NashContext,
    TelemetryFrame,
    ThermodynamicPIDState,
    UpstreamContextAdapter,
)


class UpstreamContextAdapterTests(unittest.TestCase):
    def test_adapter_clamps_context_and_emits_visible_route_input(self) -> None:
        route_input = UpstreamContextAdapter().adapt(
            TelemetryFrame("ETH-USD", 1.4, 0.7, 0.2, 0.8, -1.0, 0.42),
            ThermodynamicPIDState(thermal_pressure=1.2, control_error=0.8, impulse=0.6),
            NashContext(edge_confidence=0.9, conflict=0.4, opponent_pressure=1.5),
        )

        self.assertEqual(route_input.market.volatility_spike, 1.0)
        self.assertEqual(route_input.market.regime_shift, 0.0)
        self.assertEqual(route_input.confidence, 0.81)
        self.assertEqual(route_input.urgency, 0.87)
        self.assertEqual(len(route_input.trace), 2)
        self.assertIn("nash confidence", route_input.trace[0])

    def test_adapted_input_routes_through_existing_reflex_guard(self) -> None:
        route_input = UpstreamContextAdapter().adapt(
            TelemetryFrame(
                "AAPL",
                0.72,
                0.58,
                0.22,
                0.77,
                0.52,
                0.54,
                acceleration_against=0.84,
            ),
            ThermodynamicPIDState(thermal_pressure=0.8, control_error=0.9, impulse=0.7),
            NashContext(edge_confidence=0.86, conflict=0.08, opponent_pressure=0.75),
        )

        decision = SharkIntelligence().route_input(
            route_input,
            PositionState("AAPL", "LONG", 4.0),
        )

        self.assertEqual(decision.action, ReflexAction.EMERGENCY_EXIT)
        self.assertEqual(decision.symbol, "AAPL")


if __name__ == "__main__":
    unittest.main()
