from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from src.services import fli_search
from src.services.fli_search import FlightQuery, ScrapeResult, scrape_prices
from src.utils.filters import CabinClass, MaxStops, SearchFilters, resolve_filters

DEPARTURE = datetime(2025, 12, 1, 9, 0, tzinfo=UTC)
ARRIVAL = datetime(2025, 12, 1, 12, 0, tzinfo=UTC)


def _result(fare, number='UO123'):
    return SimpleNamespace(
        price=fare,
        currency='HKD',
        legs=[
            SimpleNamespace(
                flight_number=number,
                departure_datetime=DEPARTURE,
                arrival_datetime=ARRIVAL,
            )
        ],
    )


class _FakeSearchFlights:
    calls: list[dict] = []

    def __init__(self):
        pass

    def search(self, filters, currency=None):
        self.calls.append({'filters': filters, 'currency': currency})
        return self.results


@pytest.fixture
def fake_search(monkeypatch):
    _FakeSearchFlights.calls = []
    _FakeSearchFlights.results = []
    monkeypatch.setattr(fli_search, 'SearchFlights', _FakeSearchFlights)
    return _FakeSearchFlights


@pytest.fixture
def query():
    return FlightQuery('HKG', 'NRT', date.today() + timedelta(days=30))


def test_returns_top_three_cheapest_and_drops_null_prices(app, fake_search, query):
    fake_search.results = [
        _result(500, 'A'),
        _result(None, 'NULL'),
        _result(100, 'B'),
        _result(300, 'C'),
        _result(200, 'D'),
    ]
    with app.app_context():
        result = scrape_prices([query], currency_code='HKD')

    assert len(result) == 1
    assert result[0].success is True
    assert [f.flight_number for f in result[0].results] == ['B', 'D', 'C']
    assert fake_search.calls[0]['currency'] == 'HKD'


def test_empty_search_returns_empty_results(app, fake_search, query):
    fake_search.results = None
    with app.app_context():
        result = scrape_prices([query])

    assert result[0] == ScrapeResult(success=True, results=[])


def test_unknown_airport_returns_typed_error(app, fake_search, query):
    unknown = FlightQuery('ZZZ', 'NRT', date(2025, 12, 1))
    with app.app_context():
        result = scrape_prices([unknown])

    assert result[0].success is False
    assert 'Unknown airport code' in result[0].error_message
    assert fake_search.calls == []


def test_unknown_airline_returns_typed_error(app, fake_search, query):
    filters = SearchFilters(CabinClass.ECONOMY, MaxStops.ANY, ('ZZZZ',))
    with app.app_context():
        result = scrape_prices([query], filters=filters)

    assert result[0].success is False
    assert 'Unknown airline code' in result[0].error_message
    assert fake_search.calls == []


def test_filters_are_mapped_to_fli_models(app, fake_search, query):
    filters = resolve_filters('BUSINESS', 'ONE_STOP', ['CX'])
    with app.app_context():
        scrape_prices([query], filters=filters)

    sent = fake_search.calls[0]['filters']
    assert sent.seat_type.name == 'BUSINESS'
    assert sent.stops.name == 'ONE_STOP_OR_FEWER'
    assert [airline.name for airline in sent.airlines] == ['CX']


def test_digit_leading_airline_code_resolves(app, fake_search, query):
    # fli stores digit-leading IATA codes underscore-prefixed (e.g. 7C Jeju Air as "_7C")
    filters = resolve_filters(None, None, ['7C'])
    with app.app_context():
        scrape_prices([query], filters=filters)

    sent = fake_search.calls[0]['filters']
    assert [airline.name for airline in sent.airlines] == ['_7C']
