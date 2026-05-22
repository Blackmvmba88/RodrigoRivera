"""Paper-first heartbeat runtime for the first Medusa-Hydra breath."""

from __future__ import annotations

import argparse
import json
import queue
import sqlite3
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

from .domain import ReflexAction, ReflexDecision, clamp_unit
from .router import SharkIntelligence
from .upstream import (
    NashContext,
    TelemetryFrame,
    ThermodynamicPIDState,
    UpstreamContextAdapter,
)


@dataclass(frozen=True, slots=True)
class MarketPulse:
    """Minimal paper telemetry for one heartbeat."""

    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    spread: float
    volume_delta: float


@dataclass(frozen=True, slots=True)
class RegimeHypothesis:
    """Latest non-blocking perception emitted by one Hydra."""

    symbol: str
    regime: str
    anomaly_score: float
    atr_percentile: float
    spread_pressure: float
    volume_delta_zscore: float
    sequence: int

    @classmethod
    def neutral(cls, symbol: str) -> "RegimeHypothesis":
        return cls(symbol, "normal", 0.0, 0.5, 0.0, 0.0, 0)

    @property
    def volatility_adaptation(self) -> float:
        return 0.55 if self.regime == "storm" else 0.20 if self.regime == "normal" else 0.0

    @property
    def signature(self) -> str:
        anomaly_band = "anomaly" if self.anomaly_score >= 0.65 else "quiet"
        spread_band = "wide_spread" if self.spread_pressure >= 0.60 else "stable_spread"
        return f"{self.regime}+{anomaly_band}+{spread_band}"


class RegimeAnomalyHydra:
    """Small regime Hydra using OHLCV, spread, and volume delta only."""

    def __init__(self, window: int = 24) -> None:
        self._ranges: deque[float] = deque(maxlen=window)
        self._volume_deltas: deque[float] = deque(maxlen=window)
        self._spreads: deque[float] = deque(maxlen=window)
        self._sequence = 0

    def observe(self, pulse: MarketPulse) -> RegimeHypothesis:
        price_range = max(pulse.high - pulse.low, 0.0)
        relative_range = price_range / max(abs(pulse.close), 0.01)
        relative_spread = max(pulse.spread, 0.0) / max(abs(pulse.close), 0.01)

        atr_percentile = _rank_percentile(relative_range, self._ranges)
        volume_zscore = _zscore(pulse.volume_delta, self._volume_deltas)
        spread_pressure = _pressure(relative_spread, self._spreads)
        volatility_pressure = max(atr_percentile, 0.15)
        anomaly_score = clamp_unit((abs(volume_zscore) / 3.0) * volatility_pressure)

        self._ranges.append(relative_range)
        self._volume_deltas.append(pulse.volume_delta)
        self._spreads.append(relative_spread)
        self._sequence += 1

        if atr_percentile > 0.70:
            regime = "storm"
        elif atr_percentile < 0.40:
            regime = "calm"
        else:
            regime = "normal"

        return RegimeHypothesis(
            symbol=pulse.symbol,
            regime=regime,
            anomaly_score=round(anomaly_score, 4),
            atr_percentile=round(atr_percentile, 4),
            spread_pressure=round(spread_pressure, 4),
            volume_delta_zscore=round(volume_zscore, 4),
            sequence=self._sequence,
        )


class MedusaPerception:
    """Keep one Hydra moving without blocking the Toro heartbeat."""

    def __init__(self, hydra: RegimeAnomalyHydra | None = None) -> None:
        self._hydra = hydra or RegimeAnomalyHydra()
        self._inputs: queue.Queue[MarketPulse | None] = queue.Queue(maxsize=1)
        self._lock = threading.Lock()
        self._latest: RegimeHypothesis | None = None
        self._thread = threading.Thread(target=self._run, name="medusa-regime-hydra", daemon=True)
        self._thread.start()

    @property
    def latest(self) -> RegimeHypothesis | None:
        with self._lock:
            return self._latest

    def submit(self, pulse: MarketPulse) -> None:
        try:
            self._inputs.put_nowait(pulse)
        except queue.Full:
            try:
                self._inputs.get_nowait()
            except queue.Empty:
                pass
            self._inputs.put_nowait(pulse)

    def close(self) -> None:
        try:
            self._inputs.put_nowait(None)
        except queue.Full:
            try:
                self._inputs.get_nowait()
            except queue.Empty:
                pass
            self._inputs.put_nowait(None)
        self._thread.join(timeout=0.25)

    def _run(self) -> None:
        while True:
            pulse = self._inputs.get()
            if pulse is None:
                return
            hypothesis = self._hydra.observe(pulse)
            with self._lock:
                self._latest = hypothesis


class FirstBreathStore:
    """SQLite heartbeat journal plus small situation memory."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS heartbeats (
                observed_at TEXT NOT NULL,
                symbol TEXT NOT NULL,
                route TEXT NOT NULL,
                regime TEXT NOT NULL,
                action TEXT NOT NULL,
                threat REAL NOT NULL,
                outcome REAL NOT NULL
            )
            """
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS situation_memory (
                id TEXT PRIMARY KEY,
                signature TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                outcome REAL NOT NULL,
                regime TEXT NOT NULL
            )
            """
        )
        self._db.commit()

    def record_heartbeat(
        self,
        pulse: MarketPulse,
        route: str,
        hypothesis: RegimeHypothesis,
        action: str,
        threat: float,
        outcome: float,
    ) -> None:
        self._db.execute(
            """
            INSERT INTO heartbeats (
                observed_at, symbol, route, regime, action, threat, outcome
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _utc_now(),
                pulse.symbol,
                route,
                hypothesis.regime,
                action,
                threat,
                outcome,
            ),
        )
        self._db.commit()

    def remember_if_relevant(
        self,
        hypothesis: RegimeHypothesis,
        action: str,
        outcome: float,
        route: str,
    ) -> None:
        if route != "REFLEX_INTERRUPT" and abs(outcome) < 0.002:
            return

        event_id = f"evt_{time.time_ns()}"
        self._db.execute(
            """
            INSERT INTO situation_memory (
                id, signature, action_taken, outcome, regime
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                event_id,
                hypothesis.signature,
                action,
                outcome,
                json.dumps(
                    {
                        "regime": hypothesis.regime,
                        "atr_percentile": hypothesis.atr_percentile,
                        "spread_pressure": hypothesis.spread_pressure,
                    },
                    sort_keys=True,
                ),
            ),
        )
        self._db.commit()

    def painful_pattern(self, hypothesis: RegimeHypothesis) -> bool:
        row = self._db.execute(
            """
            SELECT outcome
            FROM situation_memory
            WHERE signature = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (hypothesis.signature,),
        ).fetchone()
        return bool(row and row[0] < -0.001)

    def heartbeat_count(self) -> int:
        row = self._db.execute("SELECT COUNT(*) FROM heartbeats").fetchone()
        return int(row[0]) if row else 0

    def situation_count(self) -> int:
        row = self._db.execute("SELECT COUNT(*) FROM situation_memory").fetchone()
        return int(row[0]) if row else 0

    def close(self) -> None:
        self._db.close()


@dataclass(frozen=True, slots=True)
class Heartbeat:
    symbol: str
    route: str
    action: str
    regime: str
    threat: float
    threshold: float
    outcome: float
    perception_sequence: int
    trace: tuple[str, ...]


class PaperAccount:
    """Paper-only mark-to-market account with simple exposure guards."""

    def __init__(self) -> None:
        self.exposure = 1.0
        self._last_mark: float | None = None

    def apply(self, pulse: MarketPulse, decision: ReflexDecision | None) -> tuple[str, float]:
        outcome = 0.0
        if self._last_mark:
            outcome = self.exposure * ((pulse.close - self._last_mark) / self._last_mark)
        self._last_mark = pulse.close

        action = "TORO_HOLD"
        if decision:
            action = decision.action.value
            if decision.action in {ReflexAction.REDUCE_SIZE, ReflexAction.EXECUTE_PARTIAL}:
                self.exposure = min(self.exposure, 0.50)
            elif decision.action in {ReflexAction.CANCEL_ORDER, ReflexAction.SWITCH_PASSIVE}:
                self.exposure = min(self.exposure, 0.25)
            elif decision.action is ReflexAction.EMERGENCY_EXIT:
                self.exposure = 0.0

        return action, round(outcome, 6)


class FirstBreathRuntime:
    """One-second paper heartbeat using last valid Medusa perception."""

    def __init__(
        self,
        store: FirstBreathStore,
        medusa: MedusaPerception | None = None,
        baseline_threat: float = 0.65,
    ) -> None:
        self.store = store
        self.medusa = medusa or MedusaPerception()
        self.baseline_threat = baseline_threat
        self.shark = SharkIntelligence()
        self.adapter = UpstreamContextAdapter()
        self.paper = PaperAccount()

    def tick(self, pulse: MarketPulse) -> Heartbeat:
        hypothesis = self.medusa.latest or RegimeHypothesis.neutral(pulse.symbol)
        memory_warning = self.store.painful_pattern(hypothesis)
        threat = round(
            clamp_unit(
                (hypothesis.anomaly_score * 0.70)
                + (hypothesis.spread_pressure * 0.30)
            ),
            4,
        )
        threshold = round(
            min(self.baseline_threat * (1.0 + hypothesis.volatility_adaptation), 0.90),
            4,
        )

        decision = None
        route = "TORO_NORMAL"
        route_trace: tuple[str, ...] = ()
        if threat >= threshold or memory_warning:
            route = "REFLEX_INTERRUPT"
            route_input = self.adapter.adapt(
                _telemetry_from(pulse, hypothesis),
                _pid_from(hypothesis),
                _nash_from(hypothesis, memory_warning),
            )
            decision = self.shark.route_input(route_input)
            route_trace = route_input.trace + decision.reasons

        action, outcome = self.paper.apply(pulse, decision)
        self.store.record_heartbeat(pulse, route, hypothesis, action, threat, outcome)
        self.store.remember_if_relevant(hypothesis, action, outcome, route)
        self.medusa.submit(pulse)

        memory_trace = ("memory warning=similar painful structure",) if memory_warning else ()
        return Heartbeat(
            symbol=pulse.symbol,
            route=route,
            action=action,
            regime=hypothesis.regime,
            threat=threat,
            threshold=threshold,
            outcome=outcome,
            perception_sequence=hypothesis.sequence,
            trace=(
                f"hypothesis={hypothesis.signature} sequence={hypothesis.sequence}",
                f"threat={threat:.4f} threshold={threshold:.4f}",
            )
            + memory_trace
            + route_trace,
        )

    def close(self) -> None:
        self.medusa.close()
        self.store.close()


def sample_pulses() -> tuple[MarketPulse, ...]:
    """Deterministic BTC/USDT paper feed for the first runtime smoke test."""
    return (
        MarketPulse("BTC/USDT", 100.0, 100.3, 99.8, 100.1, 1200, 0.03, 14),
        MarketPulse("BTC/USDT", 100.1, 100.4, 100.0, 100.2, 1220, 0.03, 18),
        MarketPulse("BTC/USDT", 100.2, 100.5, 100.0, 100.3, 1180, 0.04, -12),
        MarketPulse("BTC/USDT", 100.3, 100.7, 100.1, 100.5, 1280, 0.04, 24),
        MarketPulse("BTC/USDT", 100.5, 103.5, 98.7, 99.1, 3900, 0.48, -380),
        MarketPulse("BTC/USDT", 99.1, 101.9, 97.8, 98.0, 4100, 0.56, -420),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the first paper heartbeat.")
    parser.add_argument("--db", default=".runtime/first_breath.sqlite3")
    parser.add_argument("--heartbeat", type=float, default=0.0)
    args = parser.parse_args()

    runtime = FirstBreathRuntime(FirstBreathStore(args.db))
    try:
        print("El Toro V3 + Medusa-Hydra First Breath")
        for pulse in sample_pulses():
            heartbeat = runtime.tick(pulse)
            print(
                f"{heartbeat.symbol} route={heartbeat.route} action={heartbeat.action} "
                f"regime={heartbeat.regime} threat={heartbeat.threat:.2f}/"
                f"{heartbeat.threshold:.2f} outcome={heartbeat.outcome:+.4f}"
            )
            print("  " + " | ".join(heartbeat.trace))
            if args.heartbeat > 0.0:
                time.sleep(args.heartbeat)
        print(f"heartbeats={runtime.store.heartbeat_count()} db={runtime.store.path}")
    finally:
        runtime.close()


def _telemetry_from(pulse: MarketPulse, hypothesis: RegimeHypothesis) -> TelemetryFrame:
    return TelemetryFrame(
        symbol=pulse.symbol,
        volatility_spike=hypothesis.atr_percentile,
        volume_anomaly=min(abs(hypothesis.volume_delta_zscore) / 3.0, 1.0),
        spread_change=hypothesis.spread_pressure,
        orderflow_imbalance=min(abs(pulse.volume_delta) / max(pulse.volume, 1.0), 1.0),
        regime_shift=hypothesis.anomaly_score,
        entropy=clamp_unit(1.0 - hypothesis.anomaly_score + (hypothesis.spread_pressure * 0.20)),
        spread_widens_fast=hypothesis.spread_pressure >= 0.70,
        liquidity_vanishes=hypothesis.spread_pressure >= 0.85,
    )


def _pid_from(hypothesis: RegimeHypothesis) -> ThermodynamicPIDState:
    return ThermodynamicPIDState(
        thermal_pressure=hypothesis.atr_percentile,
        control_error=hypothesis.anomaly_score,
        impulse=min(abs(hypothesis.volume_delta_zscore) / 3.0, 1.0),
    )


def _nash_from(hypothesis: RegimeHypothesis, memory_warning: bool) -> NashContext:
    conflict = min(hypothesis.spread_pressure + (0.20 if memory_warning else 0.0), 1.0)
    return NashContext(
        edge_confidence=max(1.0 - (hypothesis.anomaly_score * 0.30), 0.20),
        conflict=conflict,
        opponent_pressure=max(hypothesis.anomaly_score, hypothesis.spread_pressure),
    )


def _rank_percentile(value: float, history: deque[float]) -> float:
    if not history:
        return 0.5
    rank = sum(previous <= value for previous in history)
    return rank / len(history)


def _zscore(value: float, history: deque[float]) -> float:
    if len(history) < 2:
        return 0.0
    deviation = pstdev(history)
    if deviation == 0.0:
        return 3.0 if value != mean(history) else 0.0
    return (value - mean(history)) / deviation


def _pressure(value: float, history: deque[float]) -> float:
    if len(history) < 2:
        return 0.0
    if value <= mean(history) * 1.50:
        return 0.0
    return clamp_unit(abs(_zscore(value, history)) / 3.0)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
