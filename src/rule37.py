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

    cutoff_date: date
    phase: Phase
    history_best_val: Optional[float]
    latest_val: Optional[float]
    all_time_high: Optional[float] = None
    all_time_low: Optional[float] = None
    observation_high: Optional[float] = None
    observation_low: Optional[float] = None


def compute_37_best(
    start: date, today: date, end: date, values: dict[date, int | float]
) -> Optional[DeadlineRule37]:
    if not (past := [d for d in values if d <= today]):
        return None

    split = start + timedelta(days=int((end - start).days * 0.37))
    latest = float(values[max(past)])

    all_fares = [float(f) for f in values.values()]
    all_time_high = max(all_fares) if all_fares else None
    all_time_low = min(all_fares) if all_fares else None

    m = min(
        [float(fare) for d, fare in values.items() if start <= d < split],
        default=float("inf"),
    )

    obs_high = obs_low = None
    if today >= split:
        obs_vals = [float(f) for d, f in values.items() if d >= split]
        if obs_vals:
            obs_high = max(obs_vals)
            obs_low = min(obs_vals)

    return DeadlineRule37(
        cutoff_date=split,
        phase=(
            Phase.OBSERVING
            if today < split
            else (Phase.BUY_SIGNAL if latest < m else Phase.WAITING)
        ),
        history_best_val=None if today < split or m == float("inf") else m,
        latest_val=latest,
        all_time_high=all_time_high,
        all_time_low=all_time_low,
        observation_high=obs_high,
        observation_low=obs_low,
    )
