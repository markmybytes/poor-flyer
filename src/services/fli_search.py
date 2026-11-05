"""Google Flights adapter (via fli) behind the existing ScrapeResult contract."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime

from fli.models import (
    Airline,
    Airport,
    FlightSearchFilters,
    FlightSegment,
    PassengerInfo,
    SeatType,
    TripType,
)
from fli.models import MaxStops as FliMaxStops
from fli.search import SearchClientError, SearchFlights

from src.extensions.database import Itinerary
from src.utils.filters import MaxStops, SearchFilters, resolve_filters

logger = logging.getLogger(__name__)

_SEAT_TYPES = {
    'ECONOMY': SeatType.ECONOMY,
    'PREMIUM_ECONOMY': SeatType.PREMIUM_ECONOMY,
    'BUSINESS': SeatType.BUSINESS,
    'FIRST': SeatType.FIRST,
}
_STOPS = {
    MaxStops.ANY: FliMaxStops.ANY,
    MaxStops.NON_STOP: FliMaxStops.NON_STOP,
    MaxStops.ONE_STOP: FliMaxStops.ONE_STOP_OR_FEWER,
    MaxStops.TWO_PLUS_STOPS: FliMaxStops.TWO_OR_FEWER_STOPS,
}


@dataclass
class Flight:
    flight_number: str
    departure_at: datetime | None
    arrival_at: datetime | None
    fare: float
    currency: str


@dataclass
class FlightQuery:
    origin: str
    destination: str
    flight_date: date


@dataclass
class ScrapeResult:
    success: bool
    error_message: str | None = None
    results: list[Flight] = field(default_factory=list)


def filters_for_itinerary(itinerary: Itinerary) -> SearchFilters:
    """Merge per-itinerary filters over the hard-coded fallbacks."""
    return resolve_filters(itinerary.cabin_class, itinerary.max_stops, itinerary.airlines)


def _lookup_airline(code: str) -> Airline:
    members = Airline.__members__
    # digit-leading IATA codes (e.g. 7C Jeju Air) are stored underscore-prefixed, like "_7C"
    member = members.get(code) or members.get('_' + code)
    if member is None:
        raise ValueError(f'Unknown airline code: {code}') from None
    return member


def _search_leg(query: FlightQuery, currency_code: str, filters: SearchFilters) -> list[Flight]:
    try:
        departure = Airport.__members__[query.origin.upper()]
        arrival = Airport.__members__[query.destination.upper()]
        airlines = [_lookup_airline(code) for code in filters.airlines]
    except KeyError as exc:
        raise ValueError(f'Unknown airport code: {exc.args[0]}') from None

    search_filters = FlightSearchFilters(
        trip_type=TripType.ONE_WAY,
        passenger_info=PassengerInfo(adults=1),
        flight_segments=[
            FlightSegment(
                departure_airport=[[departure, 0]],
                arrival_airport=[[arrival, 0]],
                travel_date=query.flight_date.isoformat(),
            )
        ],
        seat_type=_SEAT_TYPES[filters.cabin_class],
        stops=_STOPS[filters.max_stops],
        airlines=airlines or None,
    )

    raw = SearchFlights().search(search_filters, currency=currency_code)
    flights: list[Flight] = []
    for result in raw or []:
        if result.price is None:
            continue
        leg = result.legs[0]
        airline_code = leg.airline.name.removeprefix('_') if leg.airline else ''
        flights.append(
            Flight(
                flight_number=f'{airline_code}{leg.flight_number}',
                departure_at=leg.departure_datetime,
                arrival_at=leg.arrival_datetime,
                fare=float(result.price),
                currency=result.currency or currency_code,
            )
        )
    return sorted(flights, key=lambda f: f.fare)


def _scrape_leg(query: FlightQuery, currency_code: str, filters: SearchFilters) -> ScrapeResult:
    try:
        flights = _search_leg(query, currency_code, filters)
    except (SearchClientError, ValueError) as exc:
        logger.warning(
            'Flight search failed: route=%s-%s error=%s',
            query.origin,
            query.destination,
            exc,
        )
        return ScrapeResult(success=False, error_message=str(exc))

    logger.info(
        'Flight search completed: route=%s-%s rows=%d',
        query.origin,
        query.destination,
        len(flights),
    )
    return ScrapeResult(success=True, results=flights)


def scrape_prices(
    queries: list[FlightQuery],
    currency_code: str = 'HKD',
    filters: SearchFilters | None = None,
) -> list[ScrapeResult]:
    """Price each leg independently via fli; one live fetch per leg (no disk cache)."""
    filters = filters or resolve_filters()
    logger.info(
        'Starting flight scrape: legs=%d currency=%s cabin=%s stops=%s airlines=%s',
        len(queries),
        currency_code,
        filters.cabin_class,
        filters.max_stops,
        ','.join(filters.airlines) or 'all',
    )
    return [_scrape_leg(q, currency_code, filters) for q in queries]
