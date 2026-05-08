from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional


class Phase(Enum):
    OBSERVING = "OBSERVING"
    BUY_SIGNAL = "BUY_SIGNAL"
    WAITING = "WAITING"


@dataclass
class Rule37Status:
    phase: Phase
    min_observed: Optional[float]
    observation_threshold: int
    current_count: int
    latest_fare: Optional[float]


def compute_rule37(
    entry,
    snapshots,
    today: date,
) -> Rule37Status:
    if entry.rule_mode == "fixed_window":
        return _compute_fixed_window(entry, snapshots, today)
    else:
        return _compute_per_data_points(entry, snapshots)


def _compute_fixed_window(entry, snapshots, today: date) -> Rule37Status:
    monitor_start = entry.monitor_start
    monitor_end = entry.monitor_end

    observation_cutoff = monitor_start + (monitor_end - monitor_start) * 0.37
    observation_threshold = int((monitor_end - monitor_start).days)
    current_count = (today - monitor_start).days

    successful_snapshots = [s for s in snapshots if s.scrape_status == "success"]
    latest_fare = None
    if successful_snapshots:
        latest = max(successful_snapshots, key=lambda s: s.scraped_at)
        latest_fare = float(latest.fare) if latest.fare else None

    if today < observation_cutoff:
        return Rule37Status(
            phase=Phase.OBSERVING,
            min_observed=None,
            observation_threshold=observation_threshold,
            current_count=current_count,
            latest_fare=latest_fare,
        )

    cutoff_datetime = datetime.combine(observation_cutoff, datetime.min.time())
    observation_snapshots = [
        s
        for s in snapshots
        if s.scraped_at < cutoff_datetime and s.scrape_status == "success"
    ]

    if not observation_snapshots:
        min_observed = None
    else:
        min_observed = float(
            min(float(s.fare) for s in observation_snapshots if s.fare)
        )

    if (
        latest_fare is not None
        and min_observed is not None
        and latest_fare < min_observed
    ):
        phase = Phase.BUY_SIGNAL
    else:
        phase = Phase.WAITING

    return Rule37Status(
        phase=phase,
        min_observed=min_observed,
        observation_threshold=observation_threshold,
        current_count=current_count,
        latest_fare=latest_fare,
    )


def _compute_per_data_points(entry, snapshots) -> Rule37Status:
    sample_size = entry.rule_sample_size
    observation_count = int(sample_size * 0.37)

    successful_snapshots = sorted(
        [s for s in snapshots if s.scrape_status == "success"],
        key=lambda s: s.scraped_at,
    )

    latest_fare = None
    if successful_snapshots:
        latest = successful_snapshots[-1]
        latest_fare = float(latest.fare) if latest.fare else None

    if len(successful_snapshots) <= observation_count:
        return Rule37Status(
            phase=Phase.OBSERVING,
            min_observed=None,
            observation_threshold=observation_count,
            current_count=len(successful_snapshots),
            latest_fare=latest_fare,
        )

    observation_snapshots = successful_snapshots[:observation_count]
    min_observed = float(min(float(s.fare) for s in observation_snapshots if s.fare))

    if latest_fare is not None and latest_fare < min_observed:
        phase = Phase.BUY_SIGNAL
    else:
        phase = Phase.WAITING

    return Rule37Status(
        phase=phase,
        min_observed=min_observed,
        observation_threshold=observation_count,
        current_count=len(successful_snapshots),
        latest_fare=latest_fare,
    )
