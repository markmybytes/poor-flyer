from datetime import date, timedelta

from src.extensions.cache import cache
from src.extensions.database import Flight, Itinerary, db
from src.services import setting
from src.services.scheduler import disable_departured_itineraries


def _days_from_today(offset: int) -> date:
    return date.today() + timedelta(days=offset)


def _seed_itinerary(flight_offsets: list[int], is_active: bool = True) -> Itinerary:
    it = Itinerary(trip_type='SINGLE', is_active=is_active)
    db.session.add(it)
    db.session.flush()
    for i, offset in enumerate(flight_offsets):
        db.session.add(
            Flight(
                itinerary_id=it.id,
                sequence=i,
                origin='HKG',
                destination='NRT',
                flight_date=_days_from_today(offset),
            )
        )
    db.session.commit()
    return it


def _is_active(it_id: str) -> bool:
    db.session.expire_all()
    return db.session.get(Itinerary, it_id).is_active


def _archived_at(it_id: str):
    db.session.expire_all()
    return db.session.get(Itinerary, it_id).archived_at


def _enable_job() -> None:
    setting.set('itinerary', 'disable_departured_itineraries', 'true')
    cache.clear()


def test_disables_when_first_flight_departed(app):
    with app.app_context():
        it = _seed_itinerary([-1, 10])
        _enable_job()
        disable_departured_itineraries()
        assert _is_active(it.id) is False


def test_keeps_active_when_first_flight_is_today(app):
    with app.app_context():
        it = _seed_itinerary([0, 10])
        _enable_job()
        disable_departured_itineraries()
        assert _is_active(it.id) is True


def test_keeps_active_when_all_flights_in_future(app):
    with app.app_context():
        it = _seed_itinerary([5, 10])
        _enable_job()
        disable_departured_itineraries()
        assert _is_active(it.id) is True


def test_does_nothing_when_setting_disabled(app):
    with app.app_context():
        it = _seed_itinerary([-1])
        setting.set('itinerary', 'disable_departured_itineraries', 'false')
        cache.clear()
        disable_departured_itineraries()
        assert _is_active(it.id) is True


def test_defaults_to_disabled_when_setting_missing(app):
    with app.app_context():
        it = _seed_itinerary([-1])
        disable_departured_itineraries()
        assert _is_active(it.id) is True


def test_keeps_already_inactive_itinerary_inactive(app):
    with app.app_context():
        it = _seed_itinerary([-1], is_active=False)
        _enable_job()
        disable_departured_itineraries()
        assert _is_active(it.id) is False


def test_auto_archives_itinerary_when_all_flights_older_than_threshold(app):
    with app.app_context():
        it = _seed_itinerary([-40, -35])
        _enable_job()
        disable_departured_itineraries()
        assert _archived_at(it.id) is not None


def test_does_not_archive_when_latest_flight_within_threshold(app):
    with app.app_context():
        it = _seed_itinerary([-40, -5])
        _enable_job()
        disable_departured_itineraries()
        assert _archived_at(it.id) is None


def test_does_not_archive_itinerary_with_future_flight(app):
    with app.app_context():
        it = _seed_itinerary([-40, 20])
        _enable_job()
        disable_departured_itineraries()
        assert _archived_at(it.id) is None


def test_does_not_auto_archive_when_setting_disabled(app):
    with app.app_context():
        it = _seed_itinerary([-40])
        setting.set('itinerary', 'disable_departured_itineraries', 'false')
        cache.clear()
        disable_departured_itineraries()
        assert _archived_at(it.id) is None
