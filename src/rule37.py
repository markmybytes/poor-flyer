from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from math import floor
from typing import Optional


class Phase(Enum):
    OBSERVING = "OBSERVING"
    BUY_SIGNAL = "BUY_SIGNAL"
    WAITING = "WAITING"


@dataclass
class DeadlineRule37:
    """37% rule anchored to a user-supplied deadline date."""
    key_date: date
    phase: Phase
    min_observed: Optional[float]
    latest_fare: Optional[float]


@dataclass
class DynamicRule37:
    """37% rule calculated fresh from all collected snapshots."""
    observation_count: int
    total_snapshots: int
    phase: Phase
    min_observed: Optional[float]
    latest_fare: Optional[float]


def compute_deadline_rule37(entry, snapshots, today: date) -> Optional[DeadlineRule37]:
    if not entry.deadline:
        return None

    created = entry.created_at.date() if hasattr(entry.created_at, "date") else entry.created_at
    span = (entry.deadline - created).days
    key_date = created + timedelta(days=floor(span * 0.37))

    successful = [s for s in snapshots if s.scrape_status == "success"]
    latest_fare = None
    if successful:
        latest = max(successful, key=lambda s: s.scraped_at)
        latest_fare = float(latest.fare) if latest.fare else None

    if today < key_date:
        return DeadlineRule37(
            key_date=key_date,
            phase=Phase.OBSERVING,
            min_observed=None,
            latest_fare=latest_fare,
        )

    key_datetime = datetime.combine(key_date, datetime.min.time())
    obs_snapshots = [s for s in successful if s.scraped_at < key_datetime]
    min_fares = [float(s.fare) for s in obs_snapshots if s.fare]
    min_observed = float(min(min_fares)) if min_fares else None

    if latest_fare is not None and min_observed is not None and latest_fare < min_observed:
        phase = Phase.BUY_SIGNAL
    else:
        phase = Phase.WAITING

    return DeadlineRule37(
        key_date=key_date,
        phase=phase,
        min_observed=min_observed,
        latest_fare=latest_fare,
    )


def compute_dynamic_rule37(snapshots) -> DynamicRule37:
    """Observation window = first 37% of all successful snapshots collected so far."""
    successful = sorted(
        [s for s in snapshots if s.scrape_status == "success"],
        key=lambda s: s.scraped_at,
    )
    total = len(successful)
    obs_count = floor(total * 0.37)

    latest_fare = float(successful[-1].fare) if successful and successful[-1].fare else None

    # Need obs_count >= 1 to have a meaningful observation window
    if obs_count == 0:
        return DynamicRule37(
            observation_count=obs_count,
            total_snapshots=total,
            phase=Phase.OBSERVING,
            min_observed=None,
            latest_fare=latest_fare,
        )

    obs_snapshots = successful[:obs_count]
    min_fares = [float(s.fare) for s in obs_snapshots if s.fare]
    min_observed = float(min(min_fares)) if min_fares else None

    if latest_fare is not None and min_observed is not None and latest_fare < min_observed:
        phase = Phase.BUY_SIGNAL
    else:
        phase = Phase.WAITING

    return DynamicRule37(
        observation_count=obs_count,
        total_snapshots=total,
        phase=phase,
        min_observed=min_observed,
        latest_fare=latest_fare,
    )
