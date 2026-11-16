import contextvars
import logging
import threading
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from flask import render_template
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.extensions.database import FareSnapshot, Flight, Itinerary, db
from src.logging_config import bind_correlation_id, reset_correlation_id
from src.services import setting
from src.services.fli_search import FlightQuery, filters_for_itinerary, scrape_prices
from src.services.fx_rates import FXRatesError, convert_amount, get_configured_base_currency
from src.services.itinerary import get_combined_totals
from src.utils.email import SMTPConfig, get_smtp_config, send_html_email
from src.utils.rule37 import Phase, compute_37_best

logger = logging.getLogger(__name__)

AUTO_ARCHIVE_AFTER_DAYS = 30  # ponytail: fixed threshold, hoist to settings when the user asks


def _daily_min_fares(flight: Flight, base_currency: str) -> dict[date, float]:
    """Day-min base-currency fares for one leg."""
    fares: dict[date, float] = {}
    for snapshot in flight.fare_snapshots:
        if snapshot.scrape_status != 'success' or snapshot.fare is None:
            continue
        src_currency = (snapshot.currency or base_currency).upper()
        try:
            fare = convert_amount(float(snapshot.fare), src_currency, base_currency)
        except FXRatesError:
            logger.warning('failed to convert fare for rule37: flight_id=%s', flight.id)
            continue
        day = snapshot.created_at.date()
        fares[day] = min(fares.get(day, fare), fare)
    return fares


def _value_on_or_before(values: dict[date, float], day: date) -> float:
    """Latest entry at or before day: the value the 37% comparison judged."""
    return values[max(d for d in values if d <= day)]


def _notify(smtp_cfg: SMTPConfig, recipients: Sequence[str], subject: str, body: str) -> None:
    """Queue one email per recipient; sends are fire-and-forget daemon threads."""
    for email in recipients:
        threading.Thread(
            # a new thread starts with an empty context, so carry the cid over
            target=contextvars.copy_context().run,
            args=(send_html_email, smtp_cfg, email, subject, body),
            daemon=True,
        ).start()


def scrape_fares():  # noqa: C901, PLR0915 - split into scrape + notify steps next time it grows
    """Daily job to scrape flight prices and send notifications if buy signal triggered."""
    bind_correlation_id()
    # Get the app context from current_app through the scheduler
    from src.extensions.scheduler import scheduler

    with scheduler.app.app_context():
        try:
            logger.info('daily scrape job started')
            today = date.today()
            base_currency = get_configured_base_currency()
            itineraries = (
                db.session.execute(
                    select(Itinerary)
                    .options(selectinload(Itinerary.flights).selectinload(Flight.fare_snapshots))
                    .where(Itinerary.is_active, Itinerary.archived_at.is_(None))
                )
                .scalars()
                .all()
            )
            logger.debug('processing %d active itineraries', len(itineraries))

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
            logger.info('scraped prices for %d itineraries', scraped_count)

            # the scrape commit expires every instance, so reload the notify inputs in
            # one eager query instead of letting the loop lazy-load per itinerary
            notify_inputs = (
                db.session.execute(
                    select(Itinerary)
                    .options(selectinload(Itinerary.flights).selectinload(Flight.fare_snapshots))
                    .where(Itinerary.is_active, Itinerary.archived_at.is_(None))
                )
                .scalars()
                .all()
            )

            smtp_cfg = get_smtp_config()
            recipients = [
                r.strip() for r in setting.get('email', 'recipients', '').split(',') if r.strip()
            ]
            logger.debug('email recipients count=%d', len(recipients))

            buy_signals_sent = 0
            for itinerary in (i for i in notify_inputs if i.deadline):
                legs = [f for f in itinerary.flights if f.flight_date >= today]
                if not legs:
                    continue

                created_on = itinerary.created_at.date()
                leg_fares = {f.id: _daily_min_fares(f, base_currency) for f in legs}
                combined = get_combined_totals(itinerary, base_currency)
                comparison_day = min(today, itinerary.deadline)

                r37 = compute_37_best(created_on, today, itinerary.deadline, combined)
                if r37 and r37.phase is Phase.BUY_SIGNAL and recipients:
                    current_total = _value_on_or_before(combined, comparison_day)
                    history_low = r37.history_best_val or current_total
                    savings = history_low - current_total
                    body = render_template(
                        'email/buy_signal_itinerary.html',
                        legs=[
                            {
                                'origin': f.origin,
                                'destination': f.destination,
                                'flight_date': f.flight_date.strftime('%Y-%m-%d'),
                                'fare': _value_on_or_before(leg_fares[f.id], comparison_day),
                            }
                            for f in legs
                        ],
                        current_total=current_total,
                        history_low=history_low,
                        savings=savings,
                        savings_pct=(savings / history_low * 100) if history_low else 0.0,
                        display_currency=base_currency,
                    )
                    subj = f'✈️ 購買信號 | {legs[0].origin} → {legs[-1].destination} 全程總價'
                    _notify(smtp_cfg, recipients, subj, body)
                    # count the attempt: the daemon send thread never reports its result back
                    buy_signals_sent += 1

                if not itinerary.notify_per_leg:
                    continue

                for flight in legs:
                    leg_r37 = compute_37_best(
                        created_on, today, itinerary.deadline, leg_fares[flight.id]
                    )
                    if not leg_r37 or leg_r37.phase is not Phase.BUY_SIGNAL or not recipients:
                        continue

                    current_fare = _value_on_or_before(leg_fares[flight.id], comparison_day)
                    lowest_fare = leg_r37.history_best_val or current_fare
                    savings = lowest_fare - current_fare
                    flight_date_str = flight.flight_date.strftime('%Y-%m-%d')
                    subj = (
                        f'✈️ 購買信號 | {flight.origin} → {flight.destination} ({flight_date_str})'
                    )
                    body = render_template(
                        'email/buy_signal.html',
                        flight_origin=flight.origin,
                        flight_destination=flight.destination,
                        flight_date=flight_date_str,
                        current_fare=current_fare,
                        lowest_fare=lowest_fare,
                        savings=savings,
                        savings_pct=(savings / lowest_fare * 100) if lowest_fare else 0.0,
                        display_currency=base_currency,
                    )
                    _notify(smtp_cfg, recipients, subj, body)
                    # count the attempt: the daemon send thread never reports its result back
                    buy_signals_sent += 1

            logger.info('daily scrape job completed: buy_signals_sent=%d', buy_signals_sent)

        except Exception:
            logger.exception('daily scrape job failed')
            db.session.rollback()
        finally:
            db.session.remove()
            reset_correlation_id()


def disable_departured_itineraries():
    """Daily job to pause itineraries whose first flight has departed and archive those whose
    last flight is older than AUTO_ARCHIVE_AFTER_DAYS."""
    from src.extensions.scheduler import scheduler

    bind_correlation_id()
    try:
        if not setting.get_bool('itinerary', 'disable_departured_itineraries', False):
            logger.debug(
                'skipping disable_departured_itineraries job since it is disabled in settings'
            )
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
                logger.info('disabled %d itineraries with past departure dates', updated_count)

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
                    'archived %d itineraries with all flights older than %d days',
                    archived_count,
                    AUTO_ARCHIVE_AFTER_DAYS,
                )
            except Exception:
                logger.exception('failed to disable or archive past itineraries')
                db.session.rollback()
            finally:
                db.session.remove()
    finally:
        reset_correlation_id()
