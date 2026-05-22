import logging
import threading
import uuid
from datetime import date

from flask import render_template

from src.extensions.database import FareSnapshot, Itinerary, db
from src.services import setting
from src.services.fx_rates import FXRatesError, convert_amount, get_configured_base_currency
from src.services.scraper import FlightQuery, scrape_prices
from src.utils.email import get_smtp_config, send_html_email
from src.utils.rule37 import Phase, compute_37_best

logger = logging.getLogger(__name__)


def scrape_fares():
    """Daily job to scrape flight prices and send notifications if buy signal triggered."""
    # Get the app context from current_app through the scheduler
    from src.extensions.scheduler import scheduler

    with scheduler.app.app_context():
        try:
            logger.info('Daily scrape job started')
            today = date.today()
            itineraries = db.session.query(Itinerary).filter(Itinerary.is_active).all()
            logger.debug('Processing %d active itineraries', len(itineraries))

            scraped_count = 0
            for itinerary in itineraries:
                if not (active_legs := [f for f in itinerary.flights if f.flight_date >= today]):
                    continue

                scraped_count += 1
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
            logger.info('Scraped prices for %d itineraries', scraped_count)

            smtp_cfg = get_smtp_config()
            base_currency = get_configured_base_currency()
            recipients = [
                r.strip() for r in setting.get('email', 'recipients', '').split(',') if r.strip()
            ]
            logger.debug('Email recipients count=%d', len(recipients))

            all_active_legs = [
                f
                for itinerary in itineraries
                if itinerary.deadline
                for f in itinerary.flights
                if f.flight_date >= today
            ]

            buy_signals_sent = 0
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

                buy_signals_sent += 1
                snap = max(
                    (s for s in flight.fare_snapshots if s.scrape_status == 'success'),
                    key=lambda s: s.created_at,
                    default=None,
                )
                if not snap or not recipients:
                    continue

                src_currency = (snap.currency or base_currency).upper()
                current_fare = float(snap.fare)
                lowest_fare = float(r37.history_best_val or snap.fare)
                try:
                    current_fare = convert_amount(current_fare, src_currency, base_currency)
                    lowest_fare = convert_amount(lowest_fare, src_currency, base_currency)
                except FXRatesError:
                    logger.warning(
                        'Failed to convert fare for buy signal email: flight_id=%s',
                        flight.id,
                    )

                flight_date_str = flight.flight_date.strftime('%Y-%m-%d')
                subj = f'✈️ 購買信號 | {flight.origin} → {flight.destination} ({flight_date_str})'
                body = render_template(
                    'email/buy_signal.html',
                    flight_origin=flight.origin,
                    flight_destination=flight.destination,
                    flight_date=flight_date_str,
                    current_fare=current_fare,
                    lowest_fare=lowest_fare,
                    display_currency=base_currency,
                )

                for email in recipients:
                    threading.Thread(
                        target=send_html_email,
                        args=(smtp_cfg, email, subj, body),
                        daemon=True,
                    ).start()

            logger.info('Daily scrape job completed: buy_signals_sent=%d', buy_signals_sent)

        except Exception:
            logger.exception('Daily scrape job failed')
            db.session.rollback()
        finally:
            db.session.remove()
