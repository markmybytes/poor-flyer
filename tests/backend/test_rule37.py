from datetime import date, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from src.utils.rule37 import DeadlineRule37, Phase, PriceStats, compute_37_best, compute_price_stats

_DATE_MIN = date(2020, 1, 1)
_DATE_MAX = date(2035, 12, 31)


def test_compute_price_stats_empty_returns_none():
    assert compute_price_stats({}) is None


def test_compute_price_stats_single_entry():
    result = compute_price_stats({date(2024, 1, 1): 500.0})
    assert result.latest_val == 500.0
    assert result.all_time_high == 500.0
    assert result.all_time_low == 500.0


def test_compute_price_stats_multiple_entries():
    values = {
        date(2024, 1, 1): 800.0,
        date(2024, 2, 1): 500.0,
        date(2024, 3, 1): 650.0,
    }
    result = compute_price_stats(values)
    assert result.latest_val == 650.0
    assert result.all_time_high == 800.0
    assert result.all_time_low == 500.0


def test_compute_price_stats_returns_price_stats_type():
    result = compute_price_stats({date(2024, 6, 1): 300})
    assert isinstance(result, PriceStats)


def test_compute_37_best_empty_returns_none():
    assert compute_37_best(date(2024, 1, 1), date(2024, 3, 1), date(2024, 12, 31), {}) is None


def test_compute_37_best_before_cutoff_is_observing():
    start = date(2024, 1, 1)
    end = date(2024, 12, 31)
    today = date(2024, 2, 1)
    values = {date(2024, 1, 15): 600.0}

    result = compute_37_best(start, today, end, values)
    assert result.phase == Phase.OBSERVING


def test_compute_37_best_cutoff_date_is_37_percent_of_range():
    start = date(2024, 1, 1)
    end = date(2024, 12, 31)
    result = compute_37_best(start, date(2024, 6, 1), end, {date(2024, 2, 1): 500.0})
    expected_cutoff = start + timedelta(days=int((end - start).days * 0.37))
    assert result.cutoff_date == expected_cutoff


def test_compute_37_best_buy_signal_when_latest_below_history_min():
    start = date(2024, 1, 1)
    end = date(2024, 12, 31)
    cutoff = start + timedelta(days=int((end - start).days * 0.37))
    today = cutoff + timedelta(days=10)
    values = {
        cutoff - timedelta(days=5): 800.0,
        today: 600.0,
    }
    result = compute_37_best(start, today, end, values)
    assert result.phase == Phase.BUY_SIGNAL
    assert result.history_best_val == 800.0


def test_compute_37_best_waiting_when_latest_above_history_min():
    start = date(2024, 1, 1)
    end = date(2024, 12, 31)
    cutoff = start + timedelta(days=int((end - start).days * 0.37))
    today = cutoff + timedelta(days=10)
    values = {
        cutoff - timedelta(days=5): 500.0,
        today: 700.0,
    }
    result = compute_37_best(start, today, end, values)
    assert result.phase == Phase.WAITING
    assert result.history_best_val == 500.0


def test_compute_37_best_no_pre_cutoff_data_is_waiting_after_cutoff():
    start = date(2024, 1, 1)
    end = date(2024, 12, 31)
    cutoff = start + timedelta(days=int((end - start).days * 0.37))
    today = cutoff + timedelta(days=5)
    values = {today: 700.0}
    result = compute_37_best(start, today, end, values)
    assert result.phase == Phase.WAITING
    assert result.history_best_val is None


def test_compute_37_best_returns_deadline_rule37_type():
    start = date(2024, 1, 1)
    end = date(2024, 12, 31)
    result = compute_37_best(start, date(2024, 6, 1), end, {date(2024, 2, 1): 400.0})
    assert isinstance(result, DeadlineRule37)


@given(
    values=st.dictionaries(
        keys=st.dates(min_value=_DATE_MIN, max_value=_DATE_MAX),
        values=st.floats(
            min_value=0.01, max_value=1_000_000, allow_nan=False, allow_infinity=False
        ),
        max_size=30,
    )
)
@settings(max_examples=200)
def test_fuzz_compute_price_stats_never_crashes(values):
    result = compute_price_stats(values)
    assert result is None or isinstance(result, PriceStats)


@given(
    start=st.dates(min_value=_DATE_MIN, max_value=date(2030, 1, 1)),
    days_to_end=st.integers(min_value=1, max_value=730),
    days_offset_today=st.integers(min_value=-180, max_value=910),
    values=st.dictionaries(
        keys=st.dates(min_value=_DATE_MIN, max_value=_DATE_MAX),
        values=st.floats(
            min_value=0.01, max_value=1_000_000, allow_nan=False, allow_infinity=False
        ),
        max_size=30,
    ),
)
@settings(max_examples=300)
def test_fuzz_compute_37_best_never_crashes(start, days_to_end, days_offset_today, values):
    end = start + timedelta(days=days_to_end)
    today = start + timedelta(days=days_offset_today)
    result = compute_37_best(start, today, end, values)
    assert result is None or isinstance(result, DeadlineRule37)


@given(
    values=st.dictionaries(
        keys=st.dates(min_value=_DATE_MIN, max_value=_DATE_MAX),
        values=st.floats(allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=50,
    )
)
@settings(max_examples=200)
def test_fuzz_compute_price_stats_latest_val_is_from_values(values):
    result = compute_price_stats(values)
    assert result is not None
    latest_key = max(values.keys())
    assert result.latest_val == float(values[latest_key])
