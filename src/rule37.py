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


def compute_deadline_rule37(entry, snapshots, today: date) -> Optional[DeadlineRule37]:
    """Compute deadline-based 37% rule. Returns None if no deadline is set."""
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
