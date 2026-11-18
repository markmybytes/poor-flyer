"""Direct pins for the shared before-validator factories in `src.schemas.validators`."""

import re
from datetime import date

import pytest

from src.schemas.validators import (
    date_cmp,
    integer,
    iso_date,
    regex_match,
    reject_none,
)


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


LOWER, UPPER = date(2026, 6, 1), date(2026, 6, 30)


@pytest.mark.parametrize(
    ('op', 'value', 'message'),
    [
        ('ge', date(2026, 5, 31), '不能早於下限'),
        ('le', date(2026, 7, 1), '不能晚於上限'),
        ('eq', date(2026, 7, 1), '必須是這一天'),
    ],
)
def test_date_cmp_rejects_with_its_copy(op, value, message):
    with pytest.raises(ValueError) as caught:
        date_cmp(value, LOWER, op=op, copy=message)
    assert str(caught.value) == message


@pytest.mark.parametrize('op', ['ge', 'le', 'eq'])
def test_date_cmp_accepts_a_passing_comparison(op):
    assert date_cmp(LOWER, LOWER, op=op, copy='不要') is None


IATA = re.compile(r'^[A-Z]{3}$')
IATA_MATCH = regex_match(IATA, '代碼無效', prepare=lambda s: s.strip().upper())


@pytest.mark.parametrize(('value', 'expected'), [('tpe', 'TPE'), (' tpe ', 'TPE')])
def test_regex_match_returns_prepared_text(value, expected):
    assert IATA_MATCH(value) == expected


@pytest.mark.parametrize('value', ['tpe1', '', None])
def test_regex_match_rejects_mismatch_with_pinned_copy(value):
    with pytest.raises(ValueError) as caught:
        IATA_MATCH(value)
    assert caught.value.args[0] == '代碼無效'


@pytest.mark.parametrize(('value', 'expected'), [('7', 7), (7, 7), (' 7 ', 7)])
def test_integer_parses(value, expected):
    assert integer('數值無效')(value) == expected


@pytest.mark.parametrize('value', ['abc', '', None])
def test_integer_rejects_bad_value_with_copy(value):
    with pytest.raises(ValueError) as caught:
        integer('數值無效')(value)
    assert caught.value.args[0] == '數值無效'


@pytest.mark.parametrize('value', ['0', 0, -1])
def test_integer_rejects_below_minimum_with_same_copy(value):
    with pytest.raises(ValueError) as caught:
        integer('數值無效', minimum=1)(value)
    assert caught.value.args[0] == '數值無效'


@pytest.mark.parametrize('value', ['1', 1])
def test_integer_minimum_boundary_is_accepted(value):
    assert integer('數值無效', minimum=1)(value) == 1
