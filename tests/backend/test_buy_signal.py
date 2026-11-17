import logging
from datetime import UTC, date, datetime, timedelta

from src.extensions.database import FareSnapshot, Flight, Itinerary, db
from src.services import scheduler as scheduler_module
from src.services import setting

RECIPIENT = 'ops@example.com'

# 37% cutoff lands ~59 days after creation: day_early is before it, day_late after.
CREATED_AT = datetime.now(UTC) - timedelta(days=100)
DAY_EARLY = CREATED_AT + timedelta(days=5)
DAY_LATE = datetime.now(UTC) - timedelta(days=5)


class _ImmediateThread:
    """Runs the send inline so assertions do not race the daemon threads."""

    def __init__(self, target=None, args=(), daemon=None):
        self._target = target
        self._args = args

    def start(self):
        self._target(*self._args)


def _seed_itinerary(legs, *, notify_per_leg=None):
    """legs: list of (origin, destination, flight_date, [(created_at, fare), ...])."""
    itinerary = Itinerary(
        trip_type='SINGLE',
        deadline=date.today() + timedelta(days=60),
        is_active=True,
        created_at=CREATED_AT,
    )
    if notify_per_leg is not None:
        itinerary.notify_per_leg = notify_per_leg
    db.session.add(itinerary)
    db.session.flush()

    for sequence, (origin, destination, flight_date, fares) in enumerate(legs):
        flight = Flight(
            itinerary_id=itinerary.id,
            sequence=sequence,
            origin=origin,
            destination=destination,
            flight_date=flight_date,
        )
        db.session.add(flight)
        db.session.flush()
        for created_at, fare in fares:
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
    return itinerary


def _setup(monkeypatch, sent, recipients=RECIPIENT):
    if recipients:
        setting.set('email', 'recipients', recipients)
    monkeypatch.setattr(scheduler_module, 'scrape_prices', lambda *a, **k: [])
    monkeypatch.setattr(scheduler_module.threading, 'Thread', _ImmediateThread)
    monkeypatch.setattr(
        scheduler_module,
        'send_html_email',
        lambda cfg, rec, subj, body: sent.append((rec, subj, body)) is None,
    )


def test_leg_signal_does_not_fire_combined_email(app, monkeypatch):
    sent = []
    with app.app_context():
        _seed_itinerary(
            [
                (
                    'HKG',
                    'NRT',
                    date.today() + timedelta(days=10),
                    [(DAY_EARLY, 500.0), (DAY_LATE, 500.0), (DAY_LATE, 450.0)],
                ),
                (
                    'NRT',
                    'HKG',
                    date.today() + timedelta(days=17),
                    [(DAY_EARLY, 500.0), (DAY_LATE, 700.0)],
                ),
            ],
            notify_per_leg=True,
        )
        _setup(monkeypatch, sent)

        scheduler_module.scrape_fares()

        assert len(sent) == 1
        _, subject, body = sent[0]
        assert 'HKG → NRT' in subject
        assert '450.00' in body  # day-min, not the newer 500.00 row
        assert '1150.00' not in body


def test_per_leg_email_is_opt_in(app, monkeypatch):
    sent = []
    with app.app_context():
        _seed_itinerary(
            [
                (
                    'HKG',
                    'NRT',
                    date.today() + timedelta(days=10),
                    [(DAY_EARLY, 500.0), (DAY_LATE, 450.0)],
                ),
                (
                    'NRT',
                    'HKG',
                    date.today() + timedelta(days=17),
                    [(DAY_EARLY, 500.0), (DAY_LATE, 700.0)],
                ),
            ]
        )
        _setup(monkeypatch, sent)

        scheduler_module.scrape_fares()

        assert sent == []


def test_combined_total_signal_sends_one_itinerary_email(app, monkeypatch):
    sent = []
    with app.app_context():
        _seed_itinerary(
            [
                (
                    'HKG',
                    'NRT',
                    date.today() + timedelta(days=10),
                    [(DAY_EARLY, 400.0), (DAY_LATE, 300.0)],
                ),
                (
                    'NRT',
                    'HKG',
                    date.today() + timedelta(days=17),
                    [(DAY_EARLY, 400.0), (DAY_LATE, 350.0)],
                ),
            ]
        )
        _setup(monkeypatch, sent)

        scheduler_module.scrape_fares()

        assert len(sent) == 1
        _, subject, body = sent[0]
        assert '全程總價' in subject
        assert '650.00' in body
        assert '800.00' in body
        assert '150.00' in body
        assert 'HKG → NRT' in body
        assert 'NRT → HKG' in body


def test_counter_counts_only_attempted_sends(app, monkeypatch, caplog):
    sent = []
    with app.app_context():
        _seed_itinerary(
            [
                (
                    'HKG',
                    'NRT',
                    date.today() + timedelta(days=10),
                    [(DAY_EARLY, 400.0), (DAY_LATE, 300.0)],
                ),
                (
                    'NRT',
                    'HKG',
                    date.today() + timedelta(days=17),
                    [(DAY_EARLY, 400.0), (DAY_LATE, 350.0)],
                ),
            ]
        )
        _setup(monkeypatch, sent, recipients='')

        with caplog.at_level(logging.INFO, logger='src.services.scheduler'):
            scheduler_module.scrape_fares()

        assert sent == []
        assert 'buy_signals_sent=0' in caplog.text


def test_combined_series_requires_every_leg(app, monkeypatch):
    """A day missing one leg's fare is not a combined total."""
    sent = []
    with app.app_context():
        _seed_itinerary(
            [
                (
                    'HKG',
                    'NRT',
                    date.today() + timedelta(days=10),
                    [(DAY_EARLY, 400.0), (DAY_LATE, 300.0)],
                ),
                ('NRT', 'HKG', date.today() + timedelta(days=17), [(DAY_EARLY, 400.0)]),
            ]
        )
        _setup(monkeypatch, sent)

        scheduler_module.scrape_fares()

        assert sent == []


def test_itinerary_without_deadline_is_skipped(app, monkeypatch):
    sent = []
    with app.app_context():
        itinerary = _seed_itinerary(
            [('HKG', 'NRT', date.today() + timedelta(days=5), [(DAY_LATE, 10.0)])]
        )
        itinerary.deadline = None
        db.session.commit()
        _setup(monkeypatch, sent)

        scheduler_module.scrape_fares()

        assert sent == []
