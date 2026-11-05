import json
from datetime import UTC, date, datetime, timedelta

import pytest

from src.extensions.database import FareSnapshot, Flight, Itinerary, db
from src.routes.api import itinerary as api_itinerary
from src.services import scheduler as scheduler_module
from src.services.fli_search import ScrapeResult


def _seed_itinerary(flight_date=None, created_at=None, deadline=None):
    itinerary = Itinerary(
        trip_type='SINGLE',
        deadline=deadline,
        is_active=True,
        created_at=created_at or datetime.now(UTC),
    )
    db.session.add(itinerary)
    db.session.flush()
    flight = Flight(
        itinerary_id=itinerary.id,
        sequence=0,
        origin='HKG',
        destination='NRT',
        flight_date=flight_date or (date.today() + timedelta(days=10)),
    )
    db.session.add(flight)
    db.session.commit()
    return itinerary, flight


def test_scheduler_failed_leg_writes_one_sentinel(app, monkeypatch):
    with app.app_context():
        itinerary, flight = _seed_itinerary()
        monkeypatch.setattr(
            scheduler_module,
            'scrape_prices',
            lambda *args, **kwargs: [ScrapeResult(False, 'blocked')],
        )

        scheduler_module.scrape_fares()

        snapshots = db.session.query(FareSnapshot).filter_by(flight_id=flight.id).all()
        assert len(snapshots) == 1
        assert snapshots[0].fare is None
        assert snapshots[0].scrape_status == 'error'
        assert snapshots[0].error_message == 'blocked'


def test_scheduler_rule37_uses_min_fare_per_date(app, monkeypatch):
    with app.app_context():
        day_one = datetime(2025, 6, 1, 10, 0, tzinfo=UTC)
        day_two = datetime(2025, 6, 2, 10, 0, tzinfo=UTC)
        itinerary, flight = _seed_itinerary(created_at=day_one, deadline=date(2025, 12, 15))
        for created_at, fare in [(day_one, 1000.0), (day_one, 900.0), (day_two, 800.0)]:
            db.session.add(
                FareSnapshot(
                    flight_id=flight.id,
                    fare=fare,
                    currency='HKD',
                    scrape_status='success',
                    created_at=created_at,
                )
            )
        db.session.commit()

        captured = {}

        def fake_compute(start, today, end, values):
            captured['values'] = values
            return None

        monkeypatch.setattr(scheduler_module, 'scrape_prices', lambda *a, **k: [])
        monkeypatch.setattr(scheduler_module, 'compute_37_best', fake_compute)

        scheduler_module.scrape_fares()

        assert captured['values'] == {day_one.date(): 900.0, day_two.date(): 800.0}


def test_on_demand_scrape_failed_leg_writes_sentinel(client, app, monkeypatch):
    with app.app_context():
        itinerary, flight = _seed_itinerary()
        iid, fid = itinerary.id, flight.id

    calls = {}

    def fake_scrape(queries, **kwargs):
        calls.update(kwargs)
        return [ScrapeResult(False, 'blocked')]

    monkeypatch.setattr(api_itinerary, 'scrape_prices', fake_scrape)
    resp = client.post(f'/api/itineraries/{iid}/scrape')

    assert resp.status_code == 200
    with app.app_context():
        snapshots = db.session.query(FareSnapshot).filter_by(flight_id=fid).all()
        assert len(snapshots) == 1
        assert snapshots[0].fare is None
        assert snapshots[0].scrape_status == 'error'


@pytest.mark.parametrize(
    'payload',
    [
        {'cabin_class': 'FIRST'},
        {'max_stops': 'ONE_STOP'},
        {'airlines': ['JL']},
        {'airlines': []},
        {'cabin_class': None, 'max_stops': None, 'airlines': None},
    ],
)
def test_patch_itinerary_rejects_filter_edits(client, app, payload):
    with app.app_context():
        itinerary, _ = _seed_itinerary()
        itinerary.cabin_class = 'BUSINESS'
        itinerary.max_stops = 'NON_STOP'
        itinerary.airlines = ['CX']
        db.session.commit()
        iid = itinerary.id

    resp = client.patch(
        f'/api/itineraries/{iid}',
        data=json.dumps(payload),
        content_type='application/json',
    )

    assert resp.status_code == 400
    assert resp.get_json()['message'] == '搜尋條件於建立後不可修改'
    with app.app_context():
        unchanged = db.session.get(Itinerary, iid)
        assert unchanged.cabin_class == 'BUSINESS'
        assert unchanged.max_stops == 'NON_STOP'
        assert unchanged.airlines == ['CX']


def test_patch_itinerary_deadline_only_still_updates(client, app):
    with app.app_context():
        itinerary, _ = _seed_itinerary()
        iid = itinerary.id

    resp = client.patch(
        f'/api/itineraries/{iid}',
        data=json.dumps({'deadline': '2025-12-31'}),
        content_type='application/json',
    )

    assert resp.status_code == 200
    with app.app_context():
        assert db.session.get(Itinerary, iid).deadline == date(2025, 12, 31)


def test_patch_itinerary_absent_filters_are_unchanged(client, app):
    with app.app_context():
        itinerary, _ = _seed_itinerary()
        itinerary.cabin_class = 'BUSINESS'
        itinerary.max_stops = 'NON_STOP'
        itinerary.airlines = ['CX']
        db.session.commit()
        iid = itinerary.id

    resp = client.patch(
        f'/api/itineraries/{iid}',
        data=json.dumps({'is_active': True}),
        content_type='application/json',
    )

    assert resp.status_code == 200
    with app.app_context():
        updated = db.session.get(Itinerary, iid)
        assert updated.cabin_class == 'BUSINESS'
        assert updated.max_stops == 'NON_STOP'
        assert updated.airlines == ['CX']


def test_create_itinerary_accepts_search_filters(client, app):
    resp = client.post(
        '/api/itineraries',
        data=json.dumps(
            {
                'trip_type': 'SINGLE',
                'cabin_class': 'PREMIUM_ECONOMY',
                'max_stops': 'NON_STOP',
                'airlines': ['UO'],
                'flights': [{'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2025-12-01'}],
            }
        ),
        content_type='application/json',
    )

    assert resp.status_code == 200
    with app.app_context():
        created = db.session.get(Itinerary, resp.get_json()['data'])
        assert created.cabin_class == 'PREMIUM_ECONOMY'
        assert created.max_stops == 'NON_STOP'
        assert created.airlines == ['UO']
