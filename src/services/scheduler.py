import logging
import uuid
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler

from src.database import Flight, FlightFareSnapshot, SessionLocal
from src.services.scraper import scrape_prices

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def daily_scrape_job():
    db = SessionLocal()
    try:
        today = date.today()
        entries = (
            db.query(Flight)
            .filter(
                Flight.is_active,
                Flight.flight_date >= today,
            )
            .all()
        )

        for entry in entries:
            results = scrape_prices(
                origin=entry.origin,
                destination=entry.destination,
                flight_date=entry.flight_date,
            )

            for result in results.results:
                snapshot = FlightFareSnapshot(
                    id=str(uuid.uuid4()),
                    flight_id=entry.id,
                    fare=result.fare,
                    flight_number=result.flight_number,
                    departure_at=result.departure_at,
                    arrival_at=result.arrival_at,
                    scrape_status="success" if results.success else "error",
                    error_message=results.error_message,
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
        scheduler.add_job(
            daily_scrape_job,
            "cron",
            hour=9,
            minute=0,
            jitter=1800,
        )
        scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
