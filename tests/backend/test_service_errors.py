"""Service rules collect every failing field into InvalidFieldsError, copy unchanged."""

from datetime import date

import pytest

from src.extensions.database import Config, Itinerary, db
from src.schemas.validators import date_cmp
from src.services import setting
from src.services.errors import FieldIssue, InvalidFieldsError
from src.services.itinerary import create_itinerary

LEG = {'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2026-06-01'}
TODAY = date(2026, 1, 1)


def _failures(exc: InvalidFieldsError) -> set[tuple[str, str]]:
    return {(error.field, error.message) for error in exc.errors}


@pytest.mark.parametrize(
    ('payload', 'field', 'message'),
    [
        ({'cabin_class': 'SUITE', 'flights': [LEG]}, 'cabin_class', '艙等無效'),
        ({'max_stops': 'FIVE_STOPS', 'flights': [LEG]}, 'max_stops', '轉機次數無效'),
        (
            {'deadline': '2025-12-01', 'flights': [LEG]},
            'deadline',
            '購票限期不能早於今天',
        ),
        (
            {'deadline': '2027-12-01', 'flights': [LEG]},
            'deadline',
            '購票限期不能晚於首程出發日期',
        ),
    ],
)
def test_itinerary_rules_carry_their_field(payload, field, message):
    with pytest.raises(InvalidFieldsError) as caught:
        create_itinerary(payload, today=TODAY)

    assert caught.value.errors == [FieldIssue(field, message)]


def test_itinerary_reports_every_failing_field(app):
    payload = {
        'deadline': '2025-12-01',
        'cabin_class': 'SUITE',
        'max_stops': 'FIVE_STOPS',
        'flights': [LEG],
    }

    with app.app_context():
        with pytest.raises(InvalidFieldsError) as caught:
            create_itinerary(payload, today=TODAY)

        assert _failures(caught.value) == {
            ('deadline', '購票限期不能早於今天'),
            ('cabin_class', '艙等無效'),
            ('max_stops', '轉機次數無效'),
        }
        assert not db.session.new
        assert db.session.query(Itinerary).count() == 0


def test_deadline_rule_is_still_a_value_error():
    with pytest.raises(ValueError) as caught:
        date_cmp(date(2025, 12, 1), TODAY, op='ge', copy='購票限期不能早於今天')
    assert str(caught.value) == '購票限期不能早於今天'


@pytest.mark.parametrize(
    ('payload', 'field', 'message'),
    [
        (
            {'currency': {'base_currency': 'XXX'}},
            'base_currency',
            '不支援的基準貨幣',
        ),
        (
            {'currency': {'cache_ttl': 'abc'}},
            'cache_ttl',
            '快取有效時間必須是大於 0 的整數',
        ),
        (
            {'currency': {'cache_ttl': 0}},
            'cache_ttl',
            '快取有效時間必須是大於 0 的整數',
        ),
        ({'smtp': {'port': 'abc'}}, 'port', 'SMTP 連接埠必須是整數'),
    ],
)
def test_setting_rules_carry_their_field(payload, field, message):
    with pytest.raises(InvalidFieldsError) as caught:
        setting.update(payload)

    assert caught.value.errors == [FieldIssue(field, message)]


def test_setting_reports_every_failing_field(app):
    setting.set_many('currency', {'base_currency': 'HKD', 'cache_ttl': '3600'})

    with app.app_context():
        with pytest.raises(InvalidFieldsError) as caught:
            setting.update(
                {
                    'currency': {'base_currency': 'XXX', 'cache_ttl': 0},
                    'smtp': {'host': 'mail.example.com', 'port': 'abc'},
                }
            )

        assert _failures(caught.value) == {
            ('base_currency', '不支援的基準貨幣'),
            ('cache_ttl', '快取有效時間必須是大於 0 的整數'),
            ('port', 'SMTP 連接埠必須是整數'),
        }
        rows = {(c.namespace, c.key): c.value for c in db.session.query(Config)}
        assert rows == {
            ('currency', 'base_currency'): 'HKD',
            ('currency', 'cache_ttl'): '3600',
        }
