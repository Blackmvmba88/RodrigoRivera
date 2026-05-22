"""Deterministic scenario replay for the paper heartbeat runtime."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from time import sleep
from typing import Iterator

from .first_breath import (
    FirstBreathRuntime,
    FirstBreathStore,
    Heartbeat,
    MarketPulse,
    RegimeAnomalyHydra,
    RegimeHypothesis,
)


@dataclass(frozen=True, slots=True)
class ReplayRecord:
    timestamp: float
    pulse: MarketPulse


@dataclass(frozen=True, slots=True)
class HydraSnapshot:
    heartbeat: int
    threat_threshold: float
    threat: float
    attention_target: str
    regime: str
    memory_pressure: float
    interrupt_rate: float
    perception_sequence: int


@dataclass(frozen=True, slots=True)
class ReplayReport:
    scenario: str
    heartbeats: int
    interrupts: int
    interrupt_rate: float
    actions: dict[str, int]
    regimes: dict[str, int]
    relevant_memories: int
    sqlite_journal: str
    hydra_snapshots: tuple[HydraSnapshot, ...]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


class ReplayScenario:
    """JSONL pulse source using the MarketPulse contract."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @property
    def name(self) -> str:
        return self.path.stem

    def records(self) -> Iterator[ReplayRecord]:
        with self.path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                payload = json.loads(line)
                try:
                    yield ReplayRecord(
                        timestamp=float(payload["timestamp"]),
                        pulse=MarketPulse(
                            symbol=str(payload["symbol"]),
                            open=float(payload["open"]),
                            high=float(payload["high"]),
                            low=float(payload["low"]),
                            close=float(payload["close"]),
                            volume=float(payload["volume"]),
                            spread=float(payload["spread"]),
                            volume_delta=float(payload["volume_delta"]),
                        ),
                    )
                except KeyError as error:
                    raise ValueError(
                        f"{self.path}:{line_number} missing replay field {error.args[0]}"
                    ) from error


class ReplayPerception:
    """Synchronous one-pulse-lag Hydra perception for repeatable replays."""

    def __init__(self, hydra: RegimeAnomalyHydra | None = None) -> None:
        self._hydra = hydra or RegimeAnomalyHydra()
        self.latest: RegimeHypothesis | None = None

    def submit(self, pulse: MarketPulse) -> None:
        self.latest = self._hydra.observe(pulse)

    def close(self) -> None:
        return None


class ReplayRunner:
    """Feed a replay scenario into First Breath and report behavior."""

    def __init__(
        self,
        scenario: ReplayScenario,
        db_path: str | Path,
        snapshot_every: int = 4,
        speed: float = 0.0,
    ) -> None:
        self.scenario = scenario
        self.db_path = Path(db_path)
        self.snapshot_every = snapshot_every
        self.speed = speed

    def run(self) -> ReplayReport:
        store = FirstBreathStore(self.db_path)
        runtime = FirstBreathRuntime(store, medusa=ReplayPerception())
        heartbeats: list[Heartbeat] = []
        snapshots: list[HydraSnapshot] = []
        previous_timestamp: float | None = None

        try:
            for index, record in enumerate(self.scenario.records(), start=1):
                self._pace(previous_timestamp, record.timestamp)
                heartbeat = runtime.tick(record.pulse)
                heartbeats.append(heartbeat)
                if self.snapshot_every > 0 and index % self.snapshot_every == 0:
                    snapshots.append(_snapshot(index, heartbeat, heartbeats, store))
                previous_timestamp = record.timestamp

            if heartbeats and (
                not snapshots or snapshots[-1].heartbeat != len(heartbeats)
            ):
                snapshots.append(_snapshot(len(heartbeats), heartbeats[-1], heartbeats, store))

            interrupts = sum(beat.route == "REFLEX_INTERRUPT" for beat in heartbeats)
            return ReplayReport(
                scenario=self.scenario.name,
                heartbeats=len(heartbeats),
                interrupts=interrupts,
                interrupt_rate=_rate(interrupts, len(heartbeats)),
                actions=dict(sorted(Counter(beat.action for beat in heartbeats).items())),
                regimes=dict(sorted(Counter(beat.regime for beat in heartbeats).items())),
                relevant_memories=store.situation_count(),
                sqlite_journal=str(store.path),
                hydra_snapshots=tuple(snapshots),
            )
        finally:
            runtime.close()

    def _pace(self, previous: float | None, current: float) -> None:
        if previous is None or self.speed <= 0.0:
            return
        delay = max(current - previous, 0.0) / self.speed
        if delay > 0.0:
            sleep(delay)


def scenario_path(name_or_path: str) -> Path:
    candidate = Path(name_or_path)
    if candidate.exists():
        return candidate
    bundled = Path(__file__).resolve().parents[2] / "replay" / "btcusdt" / f"{name_or_path}.jsonl"
    if bundled.exists():
        return bundled
    raise FileNotFoundError(f"replay scenario not found: {name_or_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay paper heartbeat scenarios.")
    parser.add_argument("--scenario", default="spread_shock")
    parser.add_argument("--db", default=".runtime/replay.sqlite3")
    parser.add_argument("--snapshot-every", type=int, default=4)
    parser.add_argument(
        "--speed",
        type=_speed,
        default=0.0,
        help="0 steps without sleeping; positive values or 20x replay virtual seconds faster.",
    )
    args = parser.parse_args()

    report = ReplayRunner(
        ReplayScenario(scenario_path(args.scenario)),
        db_path=args.db,
        snapshot_every=args.snapshot_every,
        speed=args.speed,
    ).run()
    print(report.to_json())


def _snapshot(
    index: int,
    heartbeat: Heartbeat,
    heartbeats: list[Heartbeat],
    store: FirstBreathStore,
) -> HydraSnapshot:
    interrupts = sum(beat.route == "REFLEX_INTERRUPT" for beat in heartbeats)
    return HydraSnapshot(
        heartbeat=index,
        threat_threshold=heartbeat.threshold,
        threat=heartbeat.threat,
        attention_target=heartbeat.symbol,
        regime=heartbeat.regime,
        memory_pressure=_rate(store.situation_count(), index),
        interrupt_rate=_rate(interrupts, index),
        perception_sequence=heartbeat.perception_sequence,
    )


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _speed(value: str) -> float:
    return float(value.removesuffix("x"))


if __name__ == "__main__":
    main()
