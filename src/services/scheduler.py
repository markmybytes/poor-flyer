import logging
import threading
import uuid
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app, render_template

from src.database import Flight, FlightFareSnapshot, SessionLocal
from src.services.config import ConfigManager
from src.services.email import get_smtp_config, send_html_email
from src.services.rule37 import Phase, compute_37_best
from src.services.scraper import scrape_prices

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def daily_scrape_job():
    db = SessionLocal()
    try:
        today = date.today()
        flights = db.query(Flight).filter(Flight.is_active, Flight.flight_date >= today).all()
        for flight in flights:
            res = scrape_prices(flight.origin, flight.destination, flight.flight_date)
            for r in res.results:
                db.add(
                    FlightFareSnapshot(
                        id=str(uuid.uuid4()),
                        flight_id=flight.id,
                        fare=r.fare,
                        flight_number=r.flight_number,
                        departure_at=r.departure_at,
                        arrival_at=r.arrival_at,
                        scrape_status='success' if res.success else 'error',
                        error_message=res.error_message,
                    )
                )
        db.commit()

        smtp_cfg = get_smtp_config()
        recipients = [
            r.strip()
            for r in ConfigManager.get_str('email', 'recipients', '').split(',')
            if r.strip()
        ]

        for flight in (f for f in flights if f.notification_enabled and f.deadline):
            r37 = compute_37_best(
                flight.created_at.date(),
                today,
                flight.deadline,
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

            with current_app.app_context():
                date = flight.flight_date.strftime('%Y-%m-%d')
                subj = f'✈️ 購買信號 | {flight.origin} → {flight.destination} ({date})'
                body = render_template(
                    'email/buy_signal.html',
                    flight_origin=flight.origin,
                    flight_destination=flight.destination,
                    flight_date=date,
                    current_fare=float(snap.fare),
                    lowest_fare=float(r37.history_best_val or snap.fare),
                )

            for email in recipients:
                threading.Thread(
                    target=send_html_email, args=(smtp_cfg, email, subj, body), daemon=True
                ).start()

    except Exception as flight:
        logger.error(f'Job failed: {flight}')
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            daily_scrape_job,
            'cron',
            hour=9,
            minute=0,
            jitter=1800,
        )
        scheduler.start()
        logger.info('Scheduler started')


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info('Scheduler stopped')
