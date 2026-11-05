"""Google Flights adapter (via fli) behind the existing ScrapeResult contract."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from flask import current_app
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
from src.services.setting import get, get_int
from src.utils.filters import MaxStops, SearchFilters, resolve_filters

logger = logging.getLogger(__name__)

DEFAULT_CACHE_TTL = 12 * 60 * 60
_CACHE_VERSION = 1
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
    """Merge per-itinerary filters over the configured global defaults."""
    return resolve_filters(
        itinerary.cabin_class,
        itinerary.max_stops,
        itinerary.airlines,
        default_cabin_class=get('search', 'default_cabin_class', 'ECONOMY'),
        default_max_stops=get('search', 'default_max_stops', 'ANY'),
        default_airlines=get('search', 'default_airlines', ''),
    )


def _cache_enabled() -> bool:
    # cache exists to protect the rate limit while developing/testing — a
    # production scheduler must always fetch live fare data
    return bool(current_app.debug or current_app.config.get('TESTING'))


def _resolve_cache_path() -> Path:
    p = Path(current_app.instance_path) / 'fli_cache.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def cache_key(query: FlightQuery, filters: SearchFilters, currency_code: str) -> str:
    payload = {
        'origin': query.origin.upper(),
        'destination': query.destination.upper(),
        'date': query.flight_date.isoformat(),
        'currency': currency_code.upper(),
        'cabin_class': filters.cabin_class.value,
        'max_stops': filters.max_stops.value,
        'airlines': sorted(filters.airlines),
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    ).hexdigest()
    return f'fetch:fare:{digest}:v{_CACHE_VERSION}'


def _cache_ttl() -> int:
    return get_int('search', 'cache_ttl', DEFAULT_CACHE_TTL) or DEFAULT_CACHE_TTL


def _read_cache() -> dict[str, Any]:
    p = _resolve_cache_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        logger.warning('Failed to parse flight fare cache file')
        return {}
    except OSError as exc:
        logger.warning('Unable to read flight fare cache: error=%s', type(exc).__name__)
        return {}
    return data if isinstance(data, dict) else {}


def _write_cache(entries: dict[str, Any]) -> None:
    try:
        _resolve_cache_path().write_text(
            json.dumps(entries, ensure_ascii=True, indent=2), encoding='utf-8'
        )
    except OSError as exc:
        logger.warning('Failed to write flight fare cache: error=%s', type(exc).__name__)


def is_cache_fresh(entry: dict[str, Any], ttl: int, now: datetime | None = None) -> bool:
    cached_at = entry.get('cached_at')
    if not isinstance(cached_at, str):
        return False
    try:
        cached = datetime.fromisoformat(cached_at)
    except ValueError:
        return False
    if cached.tzinfo is None:
        cached = cached.replace(tzinfo=UTC)
    return ((now or datetime.now(UTC)) - cached).total_seconds() <= ttl


def _serialize(results: list[Flight]) -> list[dict[str, Any]]:
    return [
        {
            'flight_number': r.flight_number,
            'departure_at': r.departure_at.isoformat() if r.departure_at else None,
            'arrival_at': r.arrival_at.isoformat() if r.arrival_at else None,
            'fare': r.fare,
            'currency': r.currency,
        }
        for r in results
    ]


def _deserialize(rows: list[dict[str, Any]]) -> list[Flight]:
    return [
        Flight(
            flight_number=r.get('flight_number') or '',
            departure_at=datetime.fromisoformat(r['departure_at'])
            if r.get('departure_at')
            else None,
            arrival_at=datetime.fromisoformat(r['arrival_at']) if r.get('arrival_at') else None,
            fare=float(r['fare']),
            currency=r.get('currency') or 'HKD',
        )
        for r in rows
    ]


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
        flights.append(
            Flight(
                flight_number=leg.flight_number,
                departure_at=leg.departure_datetime,
                arrival_at=leg.arrival_datetime,
                fare=float(result.price),
                currency=result.currency or currency_code,
            )
        )
    return sorted(flights, key=lambda f: f.fare)[:3]


def _scrape_leg(
    query: FlightQuery, currency_code: str, filters: SearchFilters, force_refresh: bool
) -> ScrapeResult:
    key = cache_key(query, filters, currency_code)
    if _cache_enabled():
        entries = _read_cache()
        entry = entries.get(key)
        if not force_refresh and isinstance(entry, dict) and is_cache_fresh(entry, _cache_ttl()):
            rows = _deserialize(entry.get('results', []))
            logger.info('Fare cache hit: key=%s rows=%d', key, len(rows))
            return ScrapeResult(success=True, results=rows)

    # cache only exists to protect the rate limit while developing/testing;
    # production always fetches live
    logger.info('Fare cache miss: key=%s', key)
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

    # an empty result is never cached: a Google blockage/consent wall must not
    # persist as a "no flights" fact for the TTL window
    if _cache_enabled() and flights:
        entries = _read_cache()
        entries[key] = {'cached_at': datetime.now(UTC).isoformat(), 'results': _serialize(flights)}
        _write_cache(entries)
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
    force_refresh: bool = False,
) -> list[ScrapeResult]:
    """Price each leg independently via fli; one fetch per leg, cached on disk."""
    filters = filters or resolve_filters()
    logger.info(
        'Starting flight scrape: legs=%d currency=%s cabin=%s stops=%s airlines=%s',
        len(queries),
        currency_code,
        filters.cabin_class,
        filters.max_stops,
        ','.join(filters.airlines) or 'all',
    )
    return [_scrape_leg(q, currency_code, filters, force_refresh) for q in queries]
