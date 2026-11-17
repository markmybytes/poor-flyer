import json
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from src.extensions.database import Itinerary, db


def _make_itinerary(trip_type='SINGLE', deadline=None):
    it = Itinerary(
        trip_type=trip_type,
        deadline=deadline,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.session.add(it)
    db.session.flush()
    return it


def test_patch_itinerary_is_active(client, app):
    with app.app_context():
        it = _make_itinerary()
        db.session.commit()
        iid = it.id

    resp = client.patch(
        f'/api/itineraries/{iid}',
        data=json.dumps({'is_active': False}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    assert resp.get_json() == {'message': 'Entry updated', 'data': iid}
    with app.app_context():
        assert db.session.get(Itinerary, iid).is_active is False


def test_patch_itinerary_not_found(client, app):
    with app.app_context():
        resp = client.patch(
            f'/api/itineraries/{uuid.uuid4()}',
            data=json.dumps({'is_active': False}),
            content_type='application/json',
        )
    assert resp.status_code == 404
    body = resp.get_json()
    assert body['message'] == 'Entry not found'
    assert body['data'] is None


def test_patch_itinerary_archive_and_unarchive(client, app):
    with app.app_context():
        it = _make_itinerary()
        db.session.commit()
        iid = it.id

    resp = client.patch(
        f'/api/itineraries/{iid}',
        data=json.dumps({'archived': True}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    with app.app_context():
        assert db.session.get(Itinerary, iid).archived_at is not None

    resp = client.patch(
        f'/api/itineraries/{iid}',
        data=json.dumps({'archived': False}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    with app.app_context():
        assert db.session.get(Itinerary, iid).archived_at is None


def test_patch_itinerary_form_encoded_archived_false_restores(client, app):
    with app.app_context():
        it = _make_itinerary()
        db.session.commit()
        iid = it.id

    resp = client.patch(
        f'/api/itineraries/{iid}',
        data=json.dumps({'archived': True}),
        content_type='application/json',
    )
    assert resp.status_code == 200

    resp = client.patch(
        f'/api/itineraries/{iid}',
        data={'archived': 'false', 'is_active': 'false'},
    )
    assert resp.status_code == 200
    with app.app_context():
        entry = db.session.get(Itinerary, iid)
        assert entry.archived_at is None
        assert entry.is_active is False


def test_patch_itinerary_archive_twice_keeps_first_archived_at(client, app):
    with app.app_context():
        it = _make_itinerary()
        it.archived_at = datetime(2020, 1, 1, tzinfo=UTC)
        db.session.commit()
        iid = it.id

    resp = client.patch(
        f'/api/itineraries/{iid}',
        data=json.dumps({'archived': True}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    with app.app_context():
        assert db.session.get(Itinerary, iid).archived_at.year == 2020


def test_patch_itinerary_invalid_is_active_token_returns_400(client, app):
    with app.app_context():
        it = _make_itinerary()
        db.session.commit()
        iid = it.id

    resp = client.patch(
        f'/api/itineraries/{iid}',
        data=json.dumps({'is_active': 'maybe'}),
        content_type='application/json',
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body['message'] == 'Invalid is_active'
    assert body['data'] is None
    with app.app_context():
        assert db.session.get(Itinerary, iid).is_active is True


@pytest.mark.parametrize(
    'payload',
    [
        {'deadline': '2030-01-01'},
        {'notify_per_leg': True},
        {'cabin_class': 'FIRST'},
        {'max_stops': 'ONE_STOP'},
        {'airlines': ['JL']},
        {'unexpected': 'value'},
        {'is_active': False, 'deadline': '2030-01-01'},
    ],
)
def test_patch_itinerary_rejects_non_toggle_fields(client, app, payload):
    with app.app_context():
        it = _make_itinerary()
        it.cabin_class = 'BUSINESS'
        it.max_stops = 'NON_STOP'
        it.airlines = ['CX']
        it.notify_per_leg = True
        db.session.commit()
        iid = it.id

    resp = client.patch(
        f'/api/itineraries/{iid}',
        data=json.dumps(payload),
        content_type='application/json',
    )

    assert resp.status_code == 400
    body = resp.get_json()
    assert body['message'].startswith('Unsupported field: ')
    assert body['data'] is None
    with app.app_context():
        unchanged = db.session.get(Itinerary, iid)
        assert unchanged.is_active is True
        assert unchanged.deadline is None
        assert unchanged.notify_per_leg is True
        assert unchanged.cabin_class == 'BUSINESS'
        assert unchanged.max_stops == 'NON_STOP'
        assert unchanged.airlines == ['CX']


def test_patch_itinerary_archive_keeps_existing_deadline(client, app):
    deadline = date.today() + timedelta(days=30)
    with app.app_context():
        it = _make_itinerary(deadline=deadline)
        db.session.commit()
        iid = it.id

    resp = client.patch(
        f'/api/itineraries/{iid}',
        data=json.dumps({'archived': True}),
        content_type='application/json',
    )

    assert resp.status_code == 200
    with app.app_context():
        entry = db.session.get(Itinerary, iid)
        assert entry.archived_at is not None
        assert entry.deadline == deadline
