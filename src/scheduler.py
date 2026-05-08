import logging
import uuid
from datetime import date, datetime

from apscheduler.schedulers.background import BackgroundScheduler

from src.database import PriceSnapshot, SessionLocal, TrackingEntry
from src.scraper import scrape_prices

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def daily_scrape_job():
    db = SessionLocal()
    try:
        today = date.today()
        entries = (
            db.query(TrackingEntry)
            .filter(
                TrackingEntry.is_active,
                TrackingEntry.flight_date >= today,
            )
            .all()
        )

        for entry in entries:
            result = scrape_prices(
                origin=entry.origin,
                destination=entry.destination,
                flight_date=entry.flight_date,
                adult_count=entry.adult_count,
                child_count=entry.child_count,
                infant_count=entry.infant_count,
            )

            snapshot = PriceSnapshot(
                id=str(uuid.uuid4()),
                entry_id=entry.id,
                created_at=datetime.utcnow(),
                fare=result.fare,
                flight_number=result.flight_number,
                departure_time=result.departure_time,
                arrival_time=result.arrival_time,
                scrape_status="success" if result.success else "error",
                error_message=result.error_message,
            )

            db.add(snapshot)

        db.commit()
        logger.info(f"Daily scrape job completed for {len(entries)} active entries")
    except Exception as e:
        logger.error(f"Daily scrape job failed: {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(daily_scrape_job, "cron", hour=9, minute=0, timezone="UTC")
        scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
