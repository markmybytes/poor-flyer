import logging
from datetime import UTC, date, datetime

from src.extensions.database import FareSnapshot, Flight, Itinerary, db, floating_datetime
from src.utils.transform import CamelCaseJSONProvider, camelize, model_to_dict, to_camel


def test_to_camel_single_word():
    assert to_camel('hello') == 'hello'


def test_to_camel_two_words():
    assert to_camel('hello_world') == 'helloWorld'


def test_to_camel_multiple_words():
    assert to_camel('scrape_status_code') == 'scrapeStatusCode'


def test_to_camel_already_camel():
    assert to_camel('helloWorld') == 'helloWorld'


def test_to_camel_leading_underscore():
    assert to_camel('_private') == 'Private'


def test_camelize_flat_dict():
    assert camelize({'snake_case': 1, 'another_key': 2}) == {'snakeCase': 1, 'anotherKey': 2}


def test_camelize_nested_dict():
    assert camelize({'outer_key': {'inner_key': 'val'}}) == {'outerKey': {'innerKey': 'val'}}


def test_camelize_list_of_dicts():
    assert camelize([{'foo_bar': 1}, {'baz_qux': 2}]) == [{'fooBar': 1}, {'bazQux': 2}]


def test_camelize_tuple():
    assert camelize(({'key_one': 1},)) == [{'keyOne': 1}]


def test_camelize_scalar_passthrough():
    assert camelize(42) == 42
    assert camelize('hello') == 'hello'
    assert camelize(None) is None


def test_model_to_dict_returns_columns(app):
    with app.app_context():
        it = Itinerary(
            trip_type='SINGLE',
            deadline=None,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        db.session.add(it)
        db.session.commit()

        result = model_to_dict(it)
        assert 'id' in result
        assert result['trip_type'] == 'SINGLE'
        assert result['is_active'] is True


def test_model_to_dict_non_model_passthrough():
    assert model_to_dict({'a': 1}) == {'a': 1}
    assert model_to_dict(42) == 42


def test_camelize_sqlalchemy_model(app):
    with app.app_context():
        it = Itinerary(
            trip_type='ROUND_TRIP',
            is_active=False,
            created_at=datetime.now(UTC),
        )
        db.session.add(it)
        db.session.commit()

        result = camelize(it)
        assert 'tripType' in result
        assert result['isActive'] is False


def test_camelcase_json_provider_utc_datetime(app):
    with app.app_context():
        provider = CamelCaseJSONProvider(app)
        dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        assert provider.default(dt) == '2024-06-15T12:00:00Z'


def test_camelcase_json_provider_floating_datetime_no_warning(app, caplog):
    with app.app_context():
        provider = CamelCaseJSONProvider(app)
        fd = floating_datetime(2024, 6, 15, 10, 30, 0)
        with caplog.at_level(logging.WARNING, logger='src.utils.transform'):
            result = provider.default(fd)
        assert result == '2024-06-15T10:30:00'
        assert 'Serialization alert' not in caplog.text


def test_camelcase_json_provider_naive_datetime_logs_warning(app, caplog):
    with app.app_context():
        provider = CamelCaseJSONProvider(app)
        naive_dt = datetime(2024, 6, 15, 8, 0, 0)
        with caplog.at_level(logging.WARNING, logger='src.utils.transform'):
            result = provider.default(naive_dt)
        assert 'Serialization alert' in caplog.text
        assert result.endswith('Z')


def test_camelcase_json_provider_date(app):
    with app.app_context():
        provider = CamelCaseJSONProvider(app)
        assert provider.default(date(2024, 1, 1)) == '2024-01-01'


def test_camelcase_json_provider_dumps_camelizes_keys(app):
    with app.app_context():
        provider = CamelCaseJSONProvider(app)
        serialized = provider.dumps({'trip_type': 'SINGLE', 'is_active': True})
        assert 'tripType' in serialized
        assert 'isActive' in serialized


def test_utcdatetime_round_trip(app):
    with app.app_context():
        it = Itinerary(
            trip_type='SINGLE',
            is_active=True,
            created_at=datetime(2024, 3, 10, 9, 0, 0, tzinfo=UTC),
        )
        db.session.add(it)
        db.session.commit()
        db.session.expire(it)

        fetched = db.session.get(Itinerary, it.id)
        assert fetched.created_at.tzinfo is not None
        assert fetched.created_at.utcoffset().total_seconds() == 0


def test_floating_datetime_round_trip(app):
    with app.app_context():
        it = Itinerary(
            trip_type='SINGLE',
            is_active=True,
            created_at=datetime.now(UTC),
        )
        db.session.add(it)
        db.session.flush()

        flight = Flight(
            itinerary_id=it.id,
            sequence=0,
            origin='HKG',
            destination='NRT',
            flight_date=date(2025, 6, 15),
        )
        db.session.add(flight)
        db.session.flush()

        snapshot = FareSnapshot(
            flight_id=flight.id,
            departure_at=datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC),
            arrival_at=datetime(2025, 6, 15, 14, 0, 0, tzinfo=UTC),
            fare=1200.0,
            currency='HKD',
            scrape_status='success',
        )
        db.session.add(snapshot)
        db.session.commit()
        db.session.expire(snapshot)

        fetched = db.session.get(FareSnapshot, snapshot.id)
        assert isinstance(fetched.arrival_at, datetime)
        assert isinstance(fetched.departure_at, datetime)
