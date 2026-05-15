#!/usr/bin/env python3
"""Generate test data for the airline price scraper to cover all UI states."""

import random
import sys
from datetime import UTC, datetime, timedelta

sys.path.insert(0, str(__file__).rsplit("\\", 2)[0])

from src.database import Base, Flight, FlightFareSnapshot, SessionLocal, engine


def add_test_data():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        utc = UTC
        now = datetime.now(utc)
        today = now.date()

        def add_snap(entry, dt, fare, status="success"):
            """Helper to generate structurally accurate snapshots"""
            base_dt = dt + timedelta(
                days=30
            )  # Future flight times relative to snapshot
            db.add(
                FlightFareSnapshot(
                    flight_id=entry.id,
                    created_at=dt,
                    fare=float(fare) if fare and status == "success" else None,
                    flight_number=f"CX{random.randint(100, 999)}"
                    if status == "success"
                    else None,
                    departure_at=base_dt.replace(hour=10, minute=30)
                    if status == "success"
                    else None,
                    arrival_at=base_dt.replace(hour=14, minute=45)
                    if status == "success"
                    else None,
                    scrape_status=status,
                    error_message="Connection timeout" if status == "error" else None,
                )
            )

        print("Generating daily test scenarios...")

        # ---------------------------------------------------------
        # Scenario 1: Rule 37 BUY_SIGNAL & All Table Row Colors
        # ---------------------------------------------------------
        # Created 30 days ago, Deadline is 10 days from now.
        # Total window = 40 days. 37% Cutoff = ~15 days ago.
        e1 = Flight(
            origin="HKG",
            destination="LHR",
            flight_date=today + timedelta(days=30),
            deadline=today + timedelta(days=10),
            is_active=True,
            created_at=now - timedelta(days=30),
        )
        db.add(e1)
        db.flush()

        # Add data for EVERY DAY over the last 30 days
        for i in range(30, -1, -1):
            dt = now - timedelta(days=i)

            # Inject specific scenarios on specific days to trigger UI colors
            if i == 20:
                fare = 4500  # history_best_val (Observing phase)
            elif i == 10:
                fare = 6500  # All-Time High -> triggers bg-red-50
            elif i == 8:
                fare = 4000  # All-Time Low -> triggers bg-green-50
            elif i == 5:
                fare = (
                    4500  # Matches history_best_val, but not ATL -> triggers bg-blue-50
                )
            elif i == 2:
                add_snap(e1, dt, None, status="error")  # Error -> triggers bg-gray-50
                continue
            elif i == 0:
                fare = 4200  # Current <= 4500 -> Triggers BUY_SIGNAL Green UI header
            else:
                # Normal background noise prices
                fare = 5000 + random.randint(-100, 100)

            add_snap(e1, dt, fare)

        # ---------------------------------------------------------
        # Scenario 2: Rule 37 OBSERVING
        # ---------------------------------------------------------
        # Created 10 days ago, deadline far in the future.
        e2 = Flight(
            origin="HKG",
            destination="NRT",
            flight_date=today + timedelta(days=60),
            deadline=today + timedelta(days=40),
            is_active=True,
            created_at=now - timedelta(days=10),
        )
        db.add(e2)
        db.flush()

        # Add data for EVERY DAY over the last 10 days
        for i in range(10, -1, -1):
            add_snap(e2, now - timedelta(days=i), 3500 + random.randint(-50, 50))
        # Current day is still in observing window -> Triggers Yellow "觀察中" UI

        # ---------------------------------------------------------
        # Scenario 3: Rule 37 WAITING
        # ---------------------------------------------------------
        # Cutoff has passed. Best price during observing was $5500. Current is $5800.
        e3 = Flight(
            origin="HKG",
            destination="JFK",
            flight_date=today + timedelta(days=40),
            deadline=today + timedelta(days=15),
            is_active=True,
            created_at=now - timedelta(days=30),
        )
        db.add(e3)
        db.flush()

        # Add data for EVERY DAY over the last 30 days
        for i in range(30, -1, -1):
            dt = now - timedelta(days=i)
            if i == 25:
                fare = 5500  # Sets history_best_val
            elif i > 15:  # Observing phase background noise
                fare = 6000 + random.randint(-100, 100)
            else:  # Post cutoff background noise
                fare = 5800 + random.randint(0, 200)  # Always higher than 5500

            add_snap(
                e3, dt, fare
            )  # Ends higher than history best -> Triggers Gray "等待中" UI

        # ---------------------------------------------------------
        # Scenario 4: Expired & Inactive
        # ---------------------------------------------------------
        # Flight departed 5 days ago. Created 40 days ago.
        e4 = Flight(
            origin="HKG",
            destination="TPE",
            flight_date=today - timedelta(days=5),
            deadline=today - timedelta(days=10),
            is_active=False,
            created_at=now - timedelta(days=40),
        )
        db.add(e4)
        db.flush()

        # Add data for EVERY DAY from creation up to the flight date
        for i in range(40, 4, -1):
            add_snap(e4, now - timedelta(days=i), 1200 + random.randint(-50, 50))
        # Triggers "已過期" badge

        # ---------------------------------------------------------
        # Scenario 5: No Deadline Set
        # ---------------------------------------------------------
        e5 = Flight(
            origin="HKG",
            destination="SIN",
            flight_date=today + timedelta(days=20),
            deadline=None,
            is_active=True,
            created_at=now - timedelta(days=10),
        )
        db.add(e5)
        db.flush()

        # Add data for EVERY DAY over the last 10 days
        for i in range(10, -1, -1):
            add_snap(e5, now - timedelta(days=i), 1500 + random.randint(-50, 50))
        # Triggers Amber Rule 37 warning box

        # ---------------------------------------------------------
        # Scenario 6: Completely Empty
        # ---------------------------------------------------------
        e6 = Flight(
            origin="HKG",
            destination="BKK",
            flight_date=today + timedelta(days=10),
            deadline=today + timedelta(days=5),
            is_active=True,
            created_at=now - timedelta(days=1),
        )
        db.add(e6)
        db.flush()
        # No snapshots added -> Triggers empty list/chart fallback UI

        db.commit()

        print("\nSuccess! UI Test Data Generated:")
        print(
            "  ✓ Entry 1 (HKG->LHR): Rule 37 BUY_SIGNAL (31 daily points + all table row colors)"
        )
        print("  ✓ Entry 2 (HKG->NRT): Rule 37 OBSERVING state (11 daily points)")
        print("  ✓ Entry 3 (HKG->JFK): Rule 37 WAITING state (31 daily points)")
        print("  ✓ Entry 4 (HKG->TPE): Expired Flight / Inactive UI (36 daily points)")
        print("  ✓ Entry 5 (HKG->SIN): Missing Deadline fallback (11 daily points)")
        print("  ✓ Entry 6 (HKG->BKK): Completely Empty fallback (0 points)")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_test_data()
