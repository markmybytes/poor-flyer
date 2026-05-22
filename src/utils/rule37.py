import logging
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class Phase(Enum):
    OBSERVING = 'OBSERVING'
    BUY_SIGNAL = 'BUY_SIGNAL'
    WAITING = 'WAITING'


@dataclass
class PriceStats:
    latest_val: float | None
    all_time_high: float | None
    all_time_low: float | None


@dataclass
class DeadlineRule37:
    cutoff_date: date
    phase: Phase
    history_best_val: float | None


def compute_price_stats(values: dict[date, int | float]) -> PriceStats | None:
    if not values:
        return None
    valid_vals = [float(v) for v in values.values()]
    latest_date = max(values.keys())
    return PriceStats(
        latest_val=float(values[latest_date]),
        all_time_high=max(valid_vals),
        all_time_low=min(valid_vals),
    )


def compute_37_best(
    start: date, today: date, end: date, values: dict[date, int | float]
) -> DeadlineRule37 | None:
    if not values:
        return None

    cutoff_date = start + timedelta(days=int((end - start).days * 0.37))
    past = [d for d in values if start <= d <= min(today, end)]

    if not past:
        return DeadlineRule37(
            cutoff_date=cutoff_date,
            phase=Phase.OBSERVING if today < cutoff_date else Phase.WAITING,
            history_best_val=None,
        )

    m = min([float(values[d]) for d in past if d < cutoff_date], default=float('inf'))
    latest_val = float(values[max(past)])

    if today < cutoff_date:
        phase = Phase.OBSERVING
    elif m != float('inf') and latest_val < m:
        phase = Phase.BUY_SIGNAL
    else:
        phase = Phase.WAITING

    return DeadlineRule37(
        cutoff_date=cutoff_date,
        phase=phase,
        history_best_val=m if (m != float('inf') and today >= cutoff_date) else None,
    )
