from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Optional


class Phase(Enum):
    OBSERVING = "OBSERVING"
    BUY_SIGNAL = "BUY_SIGNAL"
    WAITING = "WAITING"


@dataclass
class DeadlineRule37:
    cutoff_date: date
    phase: Phase
    history_best_val: Optional[float]
    latest_val: Optional[float]
    all_time_high: Optional[float] = None
    all_time_low: Optional[float] = None


def compute_37_best(
    start: date, today: date, end: date, values: dict[date, int | float]
) -> DeadlineRule37:
    cutoff_date = start + timedelta(days=int((end - start).days * 0.37))
    # ensure dates are within the specificied window
    past = [d for d in values if start <= d <= min(today, end)]

    if not past:
        return DeadlineRule37(
            cutoff_date=cutoff_date,
            phase=Phase.OBSERVING if today < cutoff_date else Phase.WAITING,
            history_best_val=None,
            latest_val=None,
        )

    latest_val = float(values[max(past)])
    valid_vals = [float(values[d]) for d in past]
    m = min([float(values[d]) for d in past if d < cutoff_date], default=float("inf"))

    if today < cutoff_date:
        phase = Phase.OBSERVING
    elif m != float("inf") and latest_val < m:
        phase = Phase.BUY_SIGNAL
    else:
        phase = Phase.WAITING

    return DeadlineRule37(
        cutoff_date=cutoff_date,
        phase=phase,
        history_best_val=m if (m != float("inf") and today >= cutoff_date) else None,
        latest_val=latest_val,
        all_time_high=max(valid_vals),
        all_time_low=min(valid_vals),
    )
