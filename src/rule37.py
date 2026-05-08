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


def compute_37_best(
    start: date, today: date, end: date, values: dict[date, int | float]
) -> Optional[DeadlineRule37]:
    if not (past := [d for d in values if d <= today]):
        return None

    cutoff_date = start + timedelta(days=int((end - start).days * 0.37))
    latest_val = float(values[max(past)])
    m = min(
        [float(fare) for d, fare in values.items() if start <= d < cutoff_date],
        default=float("inf"),
    )

    return DeadlineRule37(
        cutoff_date=cutoff_date,
        phase=(
            Phase.OBSERVING
            if today < cutoff_date
            else (Phase.BUY_SIGNAL if latest_val < m else Phase.WAITING)
        ),
        history_best_val=None if today < cutoff_date or m == float("inf") else m,
        latest_val=latest_val,
        all_time_high=max(map(float, values.values()), default=None),
        all_time_low=min(map(float, values.values()), default=None),
    )
