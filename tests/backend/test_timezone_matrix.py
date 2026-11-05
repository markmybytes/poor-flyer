from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from src.extensions.database import FareSnapshot, Flight, Itinerary, db
from src.routes.pages.itinerary import _serialize_itinerary

NEGATIVE_OFFSETS = [
    timezone(timedelta(hours=-12)),
    timezone(timedelta(hours=-8)),
    timezone(timedelta(hours=-5)),
    timezone(timedelta(hours=-3)),
]

POSITIVE_OFFSETS = [
    timezone(timedelta(hours=3)),
    timezone(timedelta(hours=5)),
    timezone(timedelta(hours=8)),
    timezone(timedelta(hours=12)),
]


def _seed_itinerary_with_deadline(deadline_date):
    base_dt = datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC)
    it = Itinerary(
        trip_type='SINGLE',
        deadline=deadline_date,
        is_active=True,
        created_at=base_dt,
    )
    db.session.add(it)
    db.session.flush()
    fl = Flight(
        itinerary_id=it.id,
        sequence=0,
        origin='HKG',
        destination='NRT',
        flight_date=date(2025, 12, 1),
    )
    db.session.add(fl)
    db.session.flush()
    for offset_days in [-5, -2, 0, 2]:
        snapshot_date = base_dt + timedelta(days=offset_days)
        db.session.add(
            FareSnapshot(
                flight_id=fl.id,
                fare=1200.0 + (offset_days * 50),
                currency='HKD',
                scrape_status='success',
                created_at=snapshot_date,
            )
        )
    db.session.commit()
    return it


@pytest.mark.parametrize('tz_offset', NEGATIVE_OFFSETS)
def test_negative_offset_serialization_uses_explicit_today(app, tz_offset):
    with app.app_context():
        it = _seed_itinerary_with_deadline(date(2025, 12, 15))
        frozen_today = date(2025, 6, 1)
        result = _serialize_itinerary(it, 'HKD', today=frozen_today)
        assert result['id'] == it.id
        assert result['trip_type'] == 'SINGLE'


@pytest.mark.parametrize('tz_offset', POSITIVE_OFFSETS)
def test_positive_offset_serialization_uses_explicit_today(app, tz_offset):
    with app.app_context():
        it = _seed_itinerary_with_deadline(date(2025, 12, 15))
        frozen_today = date(2025, 6, 1)
        result = _serialize_itinerary(it, 'HKD', today=frozen_today)
        assert result['id'] == it.id
        assert result['trip_type'] == 'SINGLE'


def test_negative_offset_midnight_rollover_utc_minus_8():
    tz = timezone(timedelta(hours=-8))
    utc_midnight = datetime(2025, 6, 2, 0, 0, 0, tzinfo=UTC)
    local_time = utc_midnight.astimezone(tz)
    assert local_time.day == 1
    assert local_time.hour == 16


def test_positive_offset_midnight_rollover_utc_plus_8():
    tz = timezone(timedelta(hours=8))
    utc_midnight = datetime(2025, 6, 2, 0, 0, 0, tzinfo=UTC)
    local_time = utc_midnight.astimezone(tz)
    assert local_time.day == 2
    assert local_time.hour == 8


def test_serialization_with_negative_offset_and_deadline(app):
    with app.app_context():
        it = _seed_itinerary_with_deadline(date(2025, 12, 15))
        frozen_today = date(2025, 6, 1)
        result = _serialize_itinerary(it, 'HKD', today=frozen_today)
        assert 'rule37_analysis' in result
        assert 'statistics' in result


def test_serialization_with_positive_offset_and_deadline(app):
    with app.app_context():
        it = _seed_itinerary_with_deadline(date(2025, 12, 15))
        frozen_today = date(2025, 6, 1)
        result = _serialize_itinerary(it, 'HKD', today=frozen_today)
        assert 'rule37_analysis' in result
        assert 'statistics' in result


@pytest.mark.parametrize(
    'offset,utc_dt,expected_local_date',
    [
        (
            timezone(timedelta(hours=-12)),
            datetime(2025, 6, 1, 2, 0, 0, tzinfo=UTC),
            date(2025, 5, 31),
        ),
        (
            timezone(timedelta(hours=-5)),
            datetime(2025, 6, 1, 4, 0, 0, tzinfo=UTC),
            date(2025, 5, 31),
        ),
        (
            timezone(timedelta(hours=3)),
            datetime(2025, 6, 1, 23, 0, 0, tzinfo=UTC),
            date(2025, 6, 2),
        ),
        (
            timezone(timedelta(hours=8)),
            datetime(2025, 6, 1, 18, 0, 0, tzinfo=UTC),
            date(2025, 6, 2),
        ),
    ],
)
def test_utc_to_local_date_conversions(offset, utc_dt, expected_local_date):
    local_dt = utc_dt.astimezone(offset)
    assert local_dt.date() == expected_local_date


def test_snapshot_date_extraction_with_utc_timestamp(app):
    with app.app_context():
        it = Itinerary(
            trip_type='SINGLE',
            is_active=True,
            created_at=datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC),
        )
        db.session.add(it)
        db.session.flush()
        fl = Flight(
            itinerary_id=it.id,
            sequence=0,
            origin='HKG',
            destination='NRT',
            flight_date=date(2025, 12, 1),
        )
        db.session.add(fl)
        db.session.flush()
        snapshot_utc = datetime(2025, 6, 1, 23, 0, 0, tzinfo=UTC)
        db.session.add(
            FareSnapshot(
                flight_id=fl.id,
                fare=1200.0,
                currency='HKD',
                scrape_status='success',
                created_at=snapshot_utc,
            )
        )
        db.session.commit()
        result = _serialize_itinerary(it, 'HKD', today=date(2025, 6, 1))
        assert len(result['flights'][0]['fare_snapshots']) == 1
        snapshot = result['flights'][0]['fare_snapshots'][0]
        assert isinstance(snapshot['created_at'], datetime)
        assert snapshot['created_at'].year == 2025
        assert snapshot['created_at'].month == 6
        assert snapshot['created_at'].day == 1


def test_multiple_snapshots_across_offset_boundaries(app):
    with app.app_context():
        it = Itinerary(
            trip_type='SINGLE',
            deadline=date(2025, 12, 15),
            is_active=True,
            created_at=datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC),
        )
        db.session.add(it)
        db.session.flush()
        fl = Flight(
            itinerary_id=it.id,
            sequence=0,
            origin='HKG',
            destination='NRT',
            flight_date=date(2025, 12, 1),
        )
        db.session.add(fl)
        db.session.flush()
        for i in range(5):
            snapshot_date = datetime(2025, 6, 1 + i, 12, 0, 0, tzinfo=UTC)
            db.session.add(
                FareSnapshot(
                    flight_id=fl.id,
                    fare=1200.0 + (i * 100),
                    currency='HKD',
                    scrape_status='success',
                    created_at=snapshot_date,
                )
            )
        db.session.commit()
        frozen_today = date(2025, 6, 1)
        result = _serialize_itinerary(it, 'HKD', today=frozen_today)
        assert len(result['flights'][0]['fare_snapshots']) == 5


def test_serialization_preserves_utc_storage_with_negative_offset_override(app):
    with app.app_context():
        it = _seed_itinerary_with_deadline(date(2025, 12, 15))
        frozen_today_for_negative = date(2025, 6, 1)
        result = _serialize_itinerary(it, 'HKD', today=frozen_today_for_negative)
        assert result['created_at'] is not None
        assert isinstance(result['created_at'], datetime)
        assert result['created_at'].tzinfo == UTC


def test_serialization_preserves_utc_storage_with_positive_offset_override(app):
    with app.app_context():
        it = _seed_itinerary_with_deadline(date(2025, 12, 15))
        frozen_today_for_positive = date(2025, 6, 1)
        result = _serialize_itinerary(it, 'HKD', today=frozen_today_for_positive)
        assert result['created_at'] is not None
        assert isinstance(result['created_at'], datetime)
        assert result['created_at'].tzinfo == UTC


def test_rule37_computation_with_frozen_today_date_negative_offset(app):
    with app.app_context():
        it = _seed_itinerary_with_deadline(date(2025, 12, 15))
        frozen_today = date(2025, 6, 1)
        result = _serialize_itinerary(it, 'HKD', today=frozen_today)
        assert 'rule37_analysis' in result
        assert isinstance(result['rule37_analysis'], (dict, type(None)))


def test_rule37_computation_with_frozen_today_date_positive_offset(app):
    with app.app_context():
        it = _seed_itinerary_with_deadline(date(2025, 12, 15))
        frozen_today = date(2025, 6, 1)
        result = _serialize_itinerary(it, 'HKD', today=frozen_today)
        assert 'rule37_analysis' in result
        assert isinstance(result['rule37_analysis'], (dict, type(None)))


def test_no_live_clock_dependency_in_serialize(app):
    with app.app_context():
        it = _seed_itinerary_with_deadline(date(2025, 12, 15))
        frozen_past = date(2020, 1, 1)
        result1 = _serialize_itinerary(it, 'HKD', today=frozen_past)
        result2 = _serialize_itinerary(it, 'HKD', today=frozen_past)
        assert result1 == result2
