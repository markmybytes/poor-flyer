"""Itinerary creation domain logic shared by Inertia pages and the JSON API."""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from collections.abc import Mapping
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from src.extensions.database import Flight, Itinerary, db
from src.services.fx_rates import FXRatesError, convert_amount
from src.utils.filters import CabinClass, MaxStops, parse_airlines

logger = logging.getLogger(__name__)


def _enum_value(enum_type: type[StrEnum], value: Any, label: str) -> str:
    try:
        return enum_type(str(value).strip().upper()).value
    except ValueError:
        raise ValueError(f'Invalid {label}') from None


def validate_deadline(deadline: date | None, first_departure: date | None) -> None:
    """Reject a deadline outside today..first departure; both bounds are inclusive."""
    if deadline is None:
        return
    if deadline < date.today():
        raise ValueError('Deadline must not be in the past')
    if first_departure is not None and deadline > first_departure:
        raise ValueError('Deadline must not be after the first departure')


def _notify_per_leg(value: Any) -> bool:
    """Coerce the opt-in flag from a JSON boolean or a form-encoded string."""
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    if token not in ('true', 'false', '1', '0', 'none', ''):
        raise ValueError('Invalid notify_per_leg')
    return token not in ('false', '0', 'none', '')


def create_itinerary(data: Mapping[str, Any]) -> Itinerary:
    """Build an itinerary and its flights from a raw payload.

    Raises ValueError, KeyError, or TypeError on malformed input; the caller
    owns the commit and rollback.
    """
    deadline_str = data.get('deadline')
    deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None
    flights_data = data.get('flights', [])
    if deadline is not None:
        first_date = flights_data[0].get('flight_date') if flights_data else None
        validate_deadline(
            deadline, datetime.strptime(first_date, '%Y-%m-%d').date() if first_date else None
        )

    itinerary = Itinerary(
        id=str(uuid.uuid4()),
        trip_type=data.get('trip_type', 'SINGLE'),
        deadline=deadline,
        is_active=bool(data.get('is_active', True)),
        cabin_class=_enum_value(CabinClass, data['cabin_class'], 'cabin_class')
        if data.get('cabin_class')
        else None,
        max_stops=_enum_value(MaxStops, data['max_stops'], 'max_stops')
        if data.get('max_stops')
        else None,
        airlines=list(parse_airlines(data['airlines']))
        if data.get('airlines') is not None
        else None,
        notify_per_leg=_notify_per_leg(data.get('notify_per_leg', False)),
        created_at=datetime.now(UTC),
    )

    db.session.add(itinerary)

    for i, flight_data in enumerate(flights_data):
        flight = Flight(
            id=str(uuid.uuid4()),
            itinerary_id=itinerary.id,
            sequence=i,
            origin=flight_data.get('origin', '').upper(),
            destination=flight_data.get('destination', '').upper(),
            flight_date=datetime.strptime(flight_data.get('flight_date'), '%Y-%m-%d').date(),
        )
        db.session.add(flight)

    return itinerary


def get_combined_totals(itinerary: Itinerary, currency: str) -> dict[date, float]:
    """Computes daily combined price minimums across all legs of an itinerary."""
    date_fares = defaultdict(dict)
    for flight in itinerary.flights:
        for s in flight.fare_snapshots:
            if s.scrape_status == 'success' and s.fare is not None:
                src_currency = (s.currency or currency).upper()
                try:
                    fare_value = convert_amount(s.fare, src_currency, currency)
                except FXRatesError:
                    logger.warning('convert itinerary fare snapshot failed: snapshot_id=%s', s.id)
                    continue

                s_date = (
                    s.created_at.date()
                    if isinstance(s.created_at, datetime)
                    else getattr(s.created_at, 'date', lambda s=s: s.created_at)()
                )
                if (
                    flight.id not in date_fares[s_date]
                    or fare_value < date_fares[s_date][flight.id]
                ):
                    date_fares[s_date][flight.id] = fare_value

    combined_totals = {}
    num_flights = len(itinerary.flights)
    if num_flights == 0:
        return {}

    for d, f_fares in date_fares.items():
        if len(f_fares) == num_flights:
            combined_totals[d] = float(sum(f_fares.values()))

    return combined_totals
