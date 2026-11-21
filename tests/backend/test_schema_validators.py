"""Direct pins for the shared before-validator factories in `src.schemas.validators`."""

from datetime import date

import pytest

from src.schemas.validators import iso_date, reject_none


@pytest.mark.parametrize(
    ('value', 'expected'), [('2026-12-01', '2026-12-01'), ('2026-1-5', '2026-01-05')]
)
def test_iso_date_accepts_lenient_calendar_dates(value, expected):
    assert iso_date('無效')(value).isoformat() == expected


@pytest.mark.parametrize('value', ['2026-13-45', 'nope', '2026/12/01', None, ''])
def test_iso_date_rejects_garbage_with_pinned_copy(value):
    with pytest.raises(ValueError) as caught:
        iso_date('日期無效')(value)
    assert caught.value.args[0] == '日期無效'


@pytest.mark.parametrize('value', [None, ''])
def test_iso_date_allow_empty_clears(value):
    assert iso_date('無效', allow_empty=True)(value) is None


@pytest.mark.parametrize('value', [None, ''])
def test_iso_date_without_allow_empty_does_not_clear(value):
    with pytest.raises(ValueError):
        iso_date('無效')(value)


def test_iso_date_returns_date():
    assert iso_date('無效')('2026-12-01') == date(2026, 12, 1)


def test_reject_none_raises_pinned_copy():
    with pytest.raises(ValueError) as caught:
        reject_none('狀態無效')(None)
    assert caught.value.args[0] == '狀態無效'


@pytest.mark.parametrize('value', [True, False, '0', 0, 'yes', []])
def test_reject_none_passes_everything_else_through(value):
    assert reject_none('狀態無效')(value) is value
