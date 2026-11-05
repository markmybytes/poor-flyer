"""Itinerary creation domain logic shared by Inertia pages and the JSON API."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from src.extensions.database import Flight, Itinerary, db
from src.utils.filters import CabinClass, MaxStops, parse_airlines


def _enum_value(enum_type: type[StrEnum], value: Any, label: str) -> str:
    try:
        return enum_type(str(value).strip().upper()).value
    except ValueError:
        raise ValueError(f'Invalid {label}') from None


def create_itinerary(data: Mapping[str, Any]) -> Itinerary:
    """Build an itinerary and its flights from a raw payload.

    Raises ValueError, KeyError, or TypeError on malformed input; the caller
    owns the commit and rollback.
    """
    deadline_str = data.get('deadline')
    deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None

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
        created_at=datetime.now(UTC),
    )

    db.session.add(itinerary)

    flights_data = data.get('flights', [])
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
