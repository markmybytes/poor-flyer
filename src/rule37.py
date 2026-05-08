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


def compute_37_best(
    start: date, today: date, end: date, values: dict[date, int | float]
) -> Optional[DeadlineRule37]:
    if not (past := [d for d in values if d <= today]):
        return None

    split = start + timedelta(days=int((end - start).days * 0.37))
    latest = float(values[max(past)])

    m = min(
        [float(fare) for d, fare in values.items() if start <= d < split],
        default=float("inf"),
    )

    return DeadlineRule37(
        cutoff_date=split,
        phase=(
            Phase.OBSERVING
            if today < split
            else (Phase.BUY_SIGNAL if latest < m else Phase.WAITING)
        ),
        history_best_val=None if today < split or m == float("inf") else m,
        latest_val=latest,
    )
