import logging
import threading
import uuid
from datetime import UTC, date, datetime, timedelta

from flask import render_template
from sqlalchemy import func, select

from src.extensions.database import FareSnapshot, Flight, Itinerary, db
from src.services import setting
from src.services.fli_search import FlightQuery, filters_for_itinerary, scrape_prices
from src.services.fx_rates import FXRatesError, convert_amount, get_configured_base_currency
from src.utils.email import get_smtp_config, send_html_email
from src.utils.rule37 import Phase, compute_37_best

logger = logging.getLogger(__name__)

AUTO_ARCHIVE_AFTER_DAYS = 30  # ponytail: fixed threshold, hoist to settings when the user asks


def scrape_fares():
    """Daily job to scrape flight prices and send notifications if buy signal triggered."""
    # Get the app context from current_app through the scheduler
    from src.extensions.scheduler import scheduler

    with scheduler.app.app_context():
        try:
            logger.info('Daily scrape job started')
            today = date.today()
            base_currency = get_configured_base_currency()
            itineraries = (
                db.session.query(Itinerary)
                .filter(Itinerary.is_active, Itinerary.archived_at.is_(None))
                .all()
            )
            logger.debug('Processing %d active itineraries', len(itineraries))

            scraped_count = 0
            for itinerary in itineraries:
                if not (active_legs := [f for f in itinerary.flights if f.flight_date >= today]):
                    continue

                scraped_count += 1
                results = scrape_prices(
                    [FlightQuery(f.origin, f.destination, f.flight_date) for f in active_legs],
                    currency_code=base_currency,
                    filters=filters_for_itinerary(itinerary),
                )
                for flight, res in zip(active_legs, results, strict=False):
                    if not res.success:
                        db.session.add(
                            FareSnapshot(
                                id=str(uuid.uuid4()),
                                flight_id=flight.id,
                                fare=None,
                                currency=base_currency,
                                scrape_status='error',
                                error_message=res.error_message or 'Scrape failed',
                            )
                        )
                        continue
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
                                scrape_status='success',
                            )
                        )
            db.session.commit()
            logger.info('Scraped prices for %d itineraries', scraped_count)

            smtp_cfg = get_smtp_config()
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
                fare_by_date: dict[date, float] = {}
                for snapshot in flight.fare_snapshots:
                    if snapshot.scrape_status != 'success' or snapshot.fare is None:
                        continue
                    src_currency = (snapshot.currency or base_currency).upper()
                    try:
                        fare = convert_amount(float(snapshot.fare), src_currency, base_currency)
                    except FXRatesError:
                        logger.warning('Failed to convert fare for rule37: flight_id=%s', flight.id)
                        continue
                    day = snapshot.created_at.date()
                    fare_by_date[day] = min(fare_by_date.get(day, fare), fare)

                r37 = compute_37_best(
                    flight.itinerary.created_at.date(),
                    today,
                    flight.itinerary.deadline,
                    fare_by_date,
                )
                if not r37 or r37.phase != Phase.BUY_SIGNAL:
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


def disable_departured_itineraries():
    """Daily job to pause itineraries whose first flight has departed and archive those whose
    last flight is older than AUTO_ARCHIVE_AFTER_DAYS."""
    from src.extensions.scheduler import scheduler

    if not setting.get_bool('itinerary', 'disable_departured_itineraries', False):
        logger.debug('Skipping disable_departured_itineraries job since it is disabled in settings')
        return

    with scheduler.app.app_context():
        try:
            today = date.today()

            past_itinerary_ids = (
                select(Flight.itinerary_id)
                .group_by(Flight.itinerary_id)
                .having(func.min(Flight.flight_date) < today)
            )

            updated_count = (
                db.session.query(Itinerary)
                .filter(Itinerary.is_active)
                .filter(Itinerary.id.in_(past_itinerary_ids))
                .update({Itinerary.is_active: False}, synchronize_session=False)
            )

            db.session.commit()
            logger.info('Disabled %d itineraries with past departure dates', updated_count)

            cutoff = today - timedelta(days=AUTO_ARCHIVE_AFTER_DAYS)
            stale_itinerary_ids = (
                select(Flight.itinerary_id)
                .group_by(Flight.itinerary_id)
                .having(func.max(Flight.flight_date) < cutoff)
            )
            archived_count = (
                db.session.query(Itinerary)
                .filter(Itinerary.archived_at.is_(None))
                .filter(Itinerary.id.in_(stale_itinerary_ids))
                .update({Itinerary.archived_at: datetime.now(UTC)}, synchronize_session=False)
            )
            db.session.commit()
            logger.info(
                'Archived %d itineraries with all flights older than %d days',
                archived_count,
                AUTO_ARCHIVE_AFTER_DAYS,
            )
        except Exception:
            logger.exception('Failed to disable or archive past itineraries')
            db.session.rollback()
        finally:
            db.session.remove()
