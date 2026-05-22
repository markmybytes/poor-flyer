#!/usr/bin/env python3
"""Generate test data for the airline price scraper covering all UI states."""

import random
import sys
from datetime import UTC, datetime, timedelta, timezone

sys.path.insert(0, str(__file__).rsplit('\\', 2)[0])
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

from src import create_app
from src.extensions.database import Base, FareSnapshot, Flight, Itinerary, db


def add_test_data():
    app = create_app()
    with app.app_context():
        # Clear database and recreate tables
        Base.metadata.drop_all(bind=db.engine)
        Base.metadata.create_all(bind=db.engine)
        session = db.session

        try:
            now = datetime.now(UTC)
            today = now.date()

            # Helper to generate robust daily snapshots with optional multi-scraping
            def add_daily_snaps(
                flight, dt, base_fare, currency='HKD', status='success', snaps_per_day=1
            ):
                for m in range(snaps_per_day):
                    snap_time = dt + timedelta(hours=m * 4)  # Spread out during the day

                    # Randomize error occurrences for mixed-state days
                    is_err = status == 'error' or (status == 'mixed' and random.random() > 0.7)
                    actual_status = 'error' if is_err else 'success'

                    # Add variance to intra-day pricing to test min/max UI highlighting
                    actual_fare = None if is_err else float(base_fare + random.randint(-150, 150))

                    # Generate fake timezones to test fmtTz
                    dep_tz = timezone(timedelta(hours=8))
                    arr_tz = timezone(timedelta(hours=9))

                    # Fake flight times based on flight date
                    flight_dt = datetime.combine(flight.flight_date, datetime.min.time())
                    dep_at = (flight_dt + timedelta(hours=random.randint(6, 12))).replace(
                        tzinfo=dep_tz
                    )
                    arr_at = dep_at + timedelta(
                        hours=random.randint(2, 5), minutes=random.randint(0, 59)
                    )
                    arr_at = arr_at.replace(tzinfo=arr_tz)

                    session.add(
                        FareSnapshot(
                            flight_id=flight.id,
                            created_at=snap_time,
                            fare=actual_fare,
                            currency=currency if actual_status == 'success' else None,
                            flight_number=f'UO{random.randint(100, 999)}'
                            if actual_status == 'success'
                            else None,
                            departure_at=dep_at if actual_status == 'success' else None,
                            arrival_at=arr_at if actual_status == 'success' else None,
                            scrape_status=actual_status,
                        )
                    )

            print('Generating Exhaustive UI State Scenarios...')

            # ---------------------------------------------------------
            # Scenario 1: ROUND_TRIP | Phase: BUY_SIGNAL
            # ---------------------------------------------------------
            # Drops the price massively today to trigger the Buy Signal.
            itinerary1 = Itinerary(
                trip_type='ROUND_TRIP',
                deadline=today + timedelta(days=10),
                is_active=True,
                created_at=now - timedelta(days=30),
            )
            session.add(itinerary1)
            session.flush()

            flight1_out = Flight(
                itinerary_id=itinerary1.id,
                sequence=1,
                origin='HKG',
                destination='NRT',
                flight_date=today + timedelta(days=30),
            )
            flight1_in = Flight(
                itinerary_id=itinerary1.id,
                sequence=2,
                origin='NRT',
                destination='HKG',
                flight_date=today + timedelta(days=37),
            )
            session.add_all([flight1_out, flight1_in])
            session.flush()

            for i in range(30, -1, -1):
                dt = now - timedelta(days=i)
                fare = 1200 if i == 0 else 2000  # Drop price today
                add_daily_snaps(flight1_out, dt, fare, snaps_per_day=3)
                add_daily_snaps(flight1_in, dt, fare + 300, snaps_per_day=3)

            # ---------------------------------------------------------
            # Scenario 2: SINGLE | Phase: OBSERVING (Foreign Currency & Mixed Errors)
            # ---------------------------------------------------------
            itinerary2 = Itinerary(
                trip_type='SINGLE',
                deadline=today + timedelta(days=40),
                is_active=True,
                created_at=now - timedelta(days=2),
            )
            session.add(itinerary2)
            session.flush()

            flight2 = Flight(
                itinerary_id=itinerary2.id,
                sequence=1,
                origin='PKX',
                destination='HKG',
                flight_date=today + timedelta(days=60),
            )
            session.add(flight2)
            session.flush()

            for i in range(2, -1, -1):
                status = 'error' if i == 1 else 'mixed'
                add_daily_snaps(
                    flight2,
                    now - timedelta(days=i),
                    490,
                    currency='CNY',
                    status=status,
                    snaps_per_day=4,
                )

            # ---------------------------------------------------------
            # Scenario 3: MULTI_CITY | Phase: WAITING (Prices Increasing)
            # ---------------------------------------------------------
            itinerary3 = Itinerary(
                trip_type='MULTI_CITY',
                deadline=today + timedelta(days=5),
                is_active=True,
                created_at=now - timedelta(days=40),
            )
            session.add(itinerary3)
            session.flush()

            flight3_1 = Flight(
                itinerary_id=itinerary3.id,
                sequence=1,
                origin='HKG',
                destination='BKK',
                flight_date=today + timedelta(days=20),
            )
            flight3_2 = Flight(
                itinerary_id=itinerary3.id,
                sequence=2,
                origin='BKK',
                destination='SIN',
                flight_date=today + timedelta(days=25),
            )
            flight3_3 = Flight(
                itinerary_id=itinerary3.id,
                sequence=3,
                origin='SIN',
                destination='HKG',
                flight_date=today + timedelta(days=30),
            )
            session.add_all([flight3_1, flight3_2, flight3_3])
            session.flush()

            for i in range(40, -1, -1):
                dt = now - timedelta(days=i)
                fare_base = 500 if i == 20 else 1200 + (40 - i) * 10
                add_daily_snaps(flight3_1, dt, fare_base, snaps_per_day=2)
                add_daily_snaps(flight3_2, dt, fare_base * 0.8, snaps_per_day=2)
                add_daily_snaps(flight3_3, dt, fare_base * 1.5, snaps_per_day=2)

            # ---------------------------------------------------------
            # Scenario 4: SINGLE | Paused (No Deadline = No Rule37)
            # ---------------------------------------------------------
            itinerary4 = Itinerary(
                trip_type='SINGLE',
                deadline=None,
                is_active=False,
                created_at=now - timedelta(days=10),
            )
            session.add(itinerary4)
            session.flush()

            flight4 = Flight(
                itinerary_id=itinerary4.id,
                sequence=1,
                origin='LHR',
                destination='HKG',
                flight_date=today + timedelta(days=50),
            )
            session.add(flight4)
            session.flush()

            for i in [10, 8, 2]:
                add_daily_snaps(flight4, now - timedelta(days=i), 6500, snaps_per_day=1)

            # ---------------------------------------------------------
            # Scenario 5: ROUND_TRIP | Insufficient Data Warning
            # ---------------------------------------------------------
            # Tests the `<p>數據不足，尚無法分析最佳購買時機。</p>` fallback.
            # Generated when itinerary has a deadline, but ALL scrapes failed.
            itinerary5 = Itinerary(
                trip_type='ROUND_TRIP',
                deadline=today + timedelta(days=20),
                is_active=True,
                created_at=now - timedelta(days=5),
            )
            session.add(itinerary5)
            session.flush()

            flight5_out = Flight(
                itinerary_id=itinerary5.id,
                sequence=1,
                origin='TPE',
                destination='KIX',
                flight_date=today + timedelta(days=40),
            )
            flight5_in = Flight(
                itinerary_id=itinerary5.id,
                sequence=2,
                origin='KIX',
                destination='TPE',
                flight_date=today + timedelta(days=45),
            )
            session.add_all([flight5_out, flight5_in])
            session.flush()

            for i in range(5, -1, -1):
                add_daily_snaps(flight5_out, now - timedelta(days=i), 0, status='error')
                add_daily_snaps(flight5_in, now - timedelta(days=i), 0, status='error')

            # ---------------------------------------------------------
            # Scenario 6: SINGLE | Cutoff Date Highlight
            # ---------------------------------------------------------
            # Tests the `▴ 購買時機分析 · 決策期 ▴` banner in the table list.
            # 100 day window (created 37 days ago, deadline 63 days away).
            # 37% of 100 days = 37. So the Cutoff Date is EXACTLY TODAY.
            itinerary6 = Itinerary(
                trip_type='SINGLE',
                deadline=today + timedelta(days=63),
                is_active=True,
                created_at=now - timedelta(days=37),
            )
            session.add(itinerary6)
            session.flush()

            flight6 = Flight(
                itinerary_id=itinerary6.id,
                sequence=1,
                origin='HKG',
                destination='ICN',
                flight_date=today + timedelta(days=80),
            )
            session.add(flight6)
            session.flush()

            for i in range(37, -1, -1):
                add_daily_snaps(flight6, now - timedelta(days=i), 1500)

            # ---------------------------------------------------------
            # Scenario 7: MULTI_CITY | Absolute Zero Data (Empty States)
            # ---------------------------------------------------------
            # Tests the `暫無趨勢數據` and `暫無價格數據` UI hero blocks.
            # Itinerary and flights exist, but no `FareSnapshot` rows exist yet.
            itinerary7 = Itinerary(
                trip_type='MULTI_CITY',
                deadline=today + timedelta(days=30),
                is_active=True,
                created_at=now,
            )
            session.add(itinerary7)
            session.flush()

            flight7_1 = Flight(
                itinerary_id=itinerary7.id,
                sequence=1,
                origin='HKG',
                destination='SFO',
                flight_date=today + timedelta(days=50),
            )
            flight7_2 = Flight(
                itinerary_id=itinerary7.id,
                sequence=2,
                origin='SFO',
                destination='HKG',
                flight_date=today + timedelta(days=60),
            )
            session.add_all([flight7_1, flight7_2])
            session.flush()
            # NO SNAPSHOTS ADDED.

            session.commit()

            print('\nSuccess! Comprehensive UI Test Data Generated:')
            print('  🟢 1: BUY_SIGNAL | Round Trip | High Volatility')
            print('  ⚪ 2: OBSERVING  | Single | CNY | Scraping Errors')
            print('  🔵 3: WAITING    | Multi-City | Prices Increasing')
            print('  ⏸️ 4: NO R37     | Paused | No Deadline')
            print('  ⚠️ 5: DATA ERROR | Insufficient Data Warning (All Failed)')
            print('  📅 6: CUTOFF DAY | Tests Cutoff UI Banner Highlight')
            print('  👻 7: ZERO DATA  | Tests Empty UI Hero Blocks')

        except Exception as e:
            session.rollback()
            print(f'ERROR: {e}', file=sys.stderr)
            raise


if __name__ == '__main__':
    add_test_data()
