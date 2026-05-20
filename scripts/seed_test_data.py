#!/usr/bin/env python3
"""Generate test data for the airline price scraper using the new 3-table schema."""

import random
import sys
from datetime import UTC, datetime, timedelta

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
            utc = UTC
            now = datetime.now(utc)
            today = now.date()

            def add_snap(flight, dt, fare, currency='HKD', status='success'):
                """Helper to generate structurally accurate snapshots for a flight."""
                base_dt = dt + timedelta(days=30)
                session.add(
                    FareSnapshot(
                        flight_id=flight.id,
                        created_at=dt,
                        fare=float(fare) if fare and status == 'success' else None,
                        currency=currency if status == 'success' else None,
                        flight_number=f'CX{random.randint(100, 999)}'
                        if status == 'success'
                        else None,
                        departure_at=base_dt.replace(hour=10, minute=30)
                        if status == 'success'
                        else None,
                        arrival_at=base_dt.replace(hour=14, minute=45)
                        if status == 'success'
                        else None,
                        scrape_status=status,
                    )
                )

            print('Generating daily test scenarios for new 3-table schema...')

            # ---------------------------------------------------------
            # Scenario 1: ROUND_TRIP
            # ---------------------------------------------------------
            # Created 30 days ago, Deadline is 10 days from now.
            itinerary1 = Itinerary(
                trip_type='ROUND_TRIP',
                deadline=today + timedelta(days=10),
                is_active=True,
                created_at=now - timedelta(days=30),
            )
            session.add(itinerary1)
            session.flush()

            # Flight leg 1: Outbound
            flight1_out = Flight(
                itinerary_id=itinerary1.id,
                sequence=1,
                origin='HKG',
                destination='LHR',
                flight_date=today + timedelta(days=30),
            )
            session.add(flight1_out)

            # Flight leg 2: Inbound
            flight1_in = Flight(
                itinerary_id=itinerary1.id,
                sequence=2,
                origin='LHR',
                destination='HKG',
                flight_date=today + timedelta(days=40),
            )
            session.add(flight1_in)
            session.flush()

            # Add data for EVERY DAY over the last 30 days for both flights
            for i in range(30, -1, -1):
                dt = now - timedelta(days=i)
                if i == 20:
                    fare = 4500
                elif i == 10:
                    fare = 6500
                elif i == 8:
                    fare = 4000
                elif i == 2:
                    add_snap(flight1_out, dt, None, status='error')
                    add_snap(flight1_in, dt, None, status='error')
                    continue
                else:
                    fare = 5000 + random.randint(-100, 100)

                # Snapshot for both legs
                add_snap(flight1_out, dt, fare)
                add_snap(flight1_in, dt, fare + 500)  # Inbound slightly more expensive

            # ---------------------------------------------------------
            # Scenario 2: SINGLE
            # ---------------------------------------------------------
            # Created 10 days ago, deadline far in the future.
            itinerary2 = Itinerary(
                trip_type='SINGLE',
                deadline=today + timedelta(days=40),
                is_active=True,
                created_at=now - timedelta(days=10),
            )
            session.add(itinerary2)
            session.flush()

            flight2 = Flight(
                itinerary_id=itinerary2.id,
                sequence=1,
                origin='HKG',
                destination='NRT',
                flight_date=today + timedelta(days=60),
            )
            session.add(flight2)
            session.flush()

            # Add data for EVERY DAY over the last 10 days
            for i in range(10, -1, -1):
                add_snap(flight2, now - timedelta(days=i), 3500 + random.randint(-50, 50), currency='JPY')

            # ---------------------------------------------------------
            # Scenario 3: MULTI_CITY
            # ---------------------------------------------------------
            itinerary3 = Itinerary(
                trip_type='MULTI_CITY',
                deadline=today + timedelta(days=15),
                is_active=True,
                created_at=now - timedelta(days=30),
            )
            session.add(itinerary3)
            session.flush()

            # Leg 1: HKG to BKK
            flight3_1 = Flight(
                itinerary_id=itinerary3.id,
                sequence=1,
                origin='HKG',
                destination='BKK',
                flight_date=today + timedelta(days=20),
            )
            # Leg 2: BKK to SIN
            flight3_2 = Flight(
                itinerary_id=itinerary3.id,
                sequence=2,
                origin='BKK',
                destination='SIN',
                flight_date=today + timedelta(days=25),
            )
            # Leg 3: SIN to HKG
            flight3_3 = Flight(
                itinerary_id=itinerary3.id,
                sequence=3,
                origin='SIN',
                destination='HKG',
                flight_date=today + timedelta(days=30),
            )
            session.add_all([flight3_1, flight3_2, flight3_3])
            session.flush()

            for i in range(30, -1, -1):
                dt = now - timedelta(days=i)
                f1_fare = 1500 + random.randint(-50, 50)
                f2_fare = 800 + random.randint(-20, 20)
                f3_fare = 2000 + random.randint(-100, 100)

                add_snap(flight3_1, dt, f1_fare)
                add_snap(flight3_2, dt, f2_fare)
                add_snap(flight3_3, dt, f3_fare)

            # ---------------------------------------------------------
            # Scenario 4: Expired SINGLE
            # ---------------------------------------------------------
            itinerary4 = Itinerary(
                trip_type='SINGLE',
                deadline=today - timedelta(days=10),
                is_active=False,
                created_at=now - timedelta(days=40),
            )
            session.add(itinerary4)
            session.flush()

            flight4 = Flight(
                itinerary_id=itinerary4.id,
                sequence=1,
                origin='HKG',
                destination='TPE',
                flight_date=today - timedelta(days=5),
            )
            session.add(flight4)
            session.flush()

            for i in range(40, 4, -1):
                add_snap(flight4, now - timedelta(days=i), 1200 + random.randint(-50, 50), currency='TWD')

            session.commit()

            print('\nSuccess! UI Test Data Generated (New Schema):')
            print('  ✅ Itinerary 1: ROUND_TRIP (HKG->LHR->HKG)')
            print('  ✅ Itinerary 2: SINGLE (HKG->NRT)')
            print('  ✅ Itinerary 3: MULTI_CITY (HKG->BKK->SIN->HKG)')
            print('  ✅ Itinerary 4: SINGLE Expired (HKG->TPE)')

        except Exception as e:
            session.rollback()
            print(f'ERROR: {e}', file=sys.stderr)
            raise


if __name__ == '__main__':
    add_test_data()
