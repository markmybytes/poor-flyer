#!/usr/bin/env python3
"""Generate test data for the airline price scraper."""

import random
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

sys.path.insert(0, str(__file__).rsplit("\\", 2)[0])

from src.database import PriceSnapshot, SessionLocal, TrackingEntry, init_db


def generate_fares(base_price, num_samples, volatility=50):
    """Generate realistic fare variations."""
    fares = []
    for i in range(num_samples):
        variation = random.uniform(-volatility, volatility)
        fare = max(base_price + variation, base_price * 0.7)
        fares.append(round(fare, 2))
    return fares


def add_test_data():
    init_db()
    db = SessionLocal()

    try:
        db.query(TrackingEntry).delete()
        db.commit()

        today = date.today()

        # Entry 1: Completed (past flight) - created 1/1/2026, deadline 5/1/2026, departed 1/3/2026
        entry1 = TrackingEntry(
            origin="HKG",
            destination="BKK",
            flight_date=date(2026, 1, 3),
            adult_count=2,
            child_count=0,
            infant_count=0,
            deadline=date(2026, 5, 1),
            is_active=False,
            created_at=datetime(2026, 1, 1, 10, 0, 0),
        )
        db.add(entry1)
        db.flush()

        start_date = datetime(2026, 1, 1, 6, 0, 0)
        for i in range(20):
            snap_time = start_date + timedelta(hours=6 * i)
            db.add(
                PriceSnapshot(
                    entry_id=entry1.id,
                    created_at=snap_time,
                    fare=Decimal(str(1200 - 30 * i)) if i < 15 else None,
                    flight_number="CX 601"
                    if i % 3 == 0
                    else ("TG 601" if i % 3 == 1 else "FD 601"),
                    departure_time="08:00" if i % 2 == 0 else "14:30",
                    arrival_time="12:00" if i % 2 == 0 else "18:30",
                    scrape_status="success" if i < 15 else "error",
                    error_message=None if i < 15 else "Timeout",
                )
            )
        db.commit()
        print("[OK] Entry 1 (completed): HKG->BKK on 2026-01-03 (20 snapshots)")

        # Entry 2: Active, future flight
        entry2 = TrackingEntry(
            origin="HKG",
            destination="NRT",
            flight_date=date(2026, 5, 20),
            adult_count=1,
            child_count=1,
            infant_count=0,
            deadline=date(2026, 5, 10),
            is_active=True,
            created_at=datetime(2026, 4, 1, 9, 30, 0),
        )
        db.add(entry2)
        db.flush()

        start_date = datetime(2026, 4, 1, 8, 0, 0)
        for i in range(30):
            snap_time = start_date + timedelta(hours=4 * i)
            fare = 3500 - (i * 25) + random.randint(-100, 100)
            db.add(
                PriceSnapshot(
                    entry_id=entry2.id,
                    created_at=snap_time,
                    fare=Decimal(str(max(fare, 2800))),
                    flight_number=random.choice(["NH 601", "JL 602", "ANA 603"]),
                    departure_time="09:00" if i % 2 == 0 else "21:30",
                    arrival_time="16:00" if i % 2 == 0 else "05:00+1",
                    scrape_status="success",
                    error_message=None,
                )
            )
        db.commit()
        print("[OK] Entry 2 (active): HKG->NRT on 2026-05-20 (30 snapshots)")

        # Entry 3: Paused, past flight
        entry3 = TrackingEntry(
            origin="HKG",
            destination="SIN",
            flight_date=date(2026, 3, 15),
            adult_count=1,
            child_count=0,
            infant_count=0,
            deadline=date(2026, 5, 10),
            is_active=False,
            created_at=datetime(2026, 2, 20, 14, 0, 0),
        )
        db.add(entry3)
        db.flush()

        start_date = datetime(2026, 2, 20, 10, 0, 0)
        for i in range(25):
            snap_time = start_date + timedelta(hours=5 * i)
            db.add(
                PriceSnapshot(
                    entry_id=entry3.id,
                    created_at=snap_time,
                    fare=Decimal(str(850 + (i % 3) * 50 - (i // 3) * 20)),
                    flight_number="SQ " + str(600 + (i % 3)),
                    departure_time="11:00" if i % 2 == 0 else "17:45",
                    arrival_time="13:00" if i % 2 == 0 else "19:45",
                    scrape_status="success",
                    error_message=None,
                )
            )
        db.commit()
        print("[OK] Entry 3 (paused): HKG->SIN on 2026-03-15 (25 snapshots)")

        # Entry 4: Active, near-future flight
        entry4 = TrackingEntry(
            origin="HKG",
            destination="LAX",
            flight_date=date(2026, 6, 10),
            adult_count=2,
            child_count=1,
            infant_count=0,
            deadline=date(2026, 5, 25),
            is_active=True,
            created_at=datetime(2026, 4, 15, 11, 0, 0),
        )
        db.add(entry4)
        db.flush()

        start_date = datetime(2026, 4, 15, 7, 0, 0)
        for i in range(35):
            snap_time = start_date + timedelta(hours=3 * i)
            fare = 5200 - (i * 40) + random.randint(-200, 150)
            db.add(
                PriceSnapshot(
                    entry_id=entry4.id,
                    created_at=snap_time,
                    fare=Decimal(str(max(fare, 3800))),
                    flight_number=random.choice(["AA 128", "UA 850", "DL 280"]),
                    departure_time=random.choice(["10:30", "14:00", "22:15"]),
                    arrival_time=random.choice(["14:30", "18:00", "02:15+1"]),
                    scrape_status="success" if i < 32 else "error",
                    error_message=None if i < 32 else "Connection error",
                )
            )
        db.commit()
        print("[OK] Entry 4 (active): HKG->LAX on 2026-06-10 (35 snapshots)")

        print("\nSuccess! Test data generated.")
        print("   - 4 entries with varying states (completed, active, paused)")
        print("   - 110 total price snapshots")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_test_data()
