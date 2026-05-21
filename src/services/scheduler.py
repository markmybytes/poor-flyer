import logging
import threading
import uuid
from datetime import date

from flask import render_template

from src.extensions.database import FareSnapshot, Itinerary, db
from src.services import config
from src.services.email import get_smtp_config, send_html_email
from src.services.rule37 import Phase, compute_37_best
from src.services.scraper import FlightQuery, scrape_prices

logger = logging.getLogger(__name__)


def daily_scrape_job():
    """Daily job to scrape flight prices and send notifications if buy signal triggered."""
    # Get the app context from current_app through the scheduler
    from src.extensions.scheduler import scheduler

    with scheduler.app.app_context():
        try:
            today = date.today()
            itineraries = db.session.query(Itinerary).filter(Itinerary.is_active).all()
            for itinerary in itineraries:
                if not (active_legs := [f for f in itinerary.flights if f.flight_date >= today]):
                    continue

                results = scrape_prices(
                    [FlightQuery(f.origin, f.destination, f.flight_date) for f in active_legs]
                )
                for flight, res in zip(active_legs, results, strict=False):
                    for r in res.results:
                        db.session.add(
                            FareSnapshot(
                                id=str(uuid.uuid4()),
                                flight_id=flight.id,
                                fare=r.fare,
                                currency=r.currency,
                                flight_number=r.flight_number,
                                departure_at=r.departure_at,
                                arrival_at=r.arrival_at,
                                scrape_status='success' if res.success else 'error',
                                error_message=res.error_message,
                            )
                        )
            db.session.commit()

            smtp_cfg = get_smtp_config()
            recipients = [
                r.strip() for r in config.get_str('email', 'recipients', '').split(',') if r.strip()
            ]

            all_active_legs = [
                f
                for itinerary in itineraries
                if itinerary.deadline
                for f in itinerary.flights
                if f.flight_date >= today
            ]
            for flight in all_active_legs:
                r37 = compute_37_best(
                    flight.itinerary.created_at.date(),
                    today,
                    flight.itinerary.deadline,
                    {
                        s.created_at.date(): float(s.fare)
                        for s in flight.fare_snapshots
                        if s.scrape_status == 'success'
                    },
                )
                if r37.phase != Phase.BUY_SIGNAL:
                    continue

                snap = max(
                    (s for s in flight.fare_snapshots if s.scrape_status == 'success'),
                    key=lambda s: s.created_at,
                    default=None,
                )
                if not snap or not recipients:
                    continue

                flight_date_str = flight.flight_date.strftime('%Y-%m-%d')
                subj = f'✈️ 購買信號 | {flight.origin} → {flight.destination} ({flight_date_str})'
                body = render_template(
                    'email/buy_signal.html',
                    flight_origin=flight.origin,
                    flight_destination=flight.destination,
                    flight_date=flight_date_str,
                    current_fare=float(snap.fare),
                    lowest_fare=float(r37.history_best_val or snap.fare),
                )

                for email in recipients:
                    threading.Thread(
                        target=send_html_email,
                        args=(smtp_cfg, email, subj, body),
                        daemon=True,
                    ).start()

        except Exception as exc:
            logger.error(f'Scheduler job failed: {exc}', exc_info=True)
            db.session.rollback()
        finally:
            db.session.remove()
