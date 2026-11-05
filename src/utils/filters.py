"""Pure search-filter enums and per-itinerary/default merge logic."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class CabinClass(StrEnum):
    ECONOMY = 'ECONOMY'
    PREMIUM_ECONOMY = 'PREMIUM_ECONOMY'
    BUSINESS = 'BUSINESS'
    FIRST = 'FIRST'


class MaxStops(StrEnum):
    ANY = 'ANY'
    NON_STOP = 'NON_STOP'
    ONE_STOP = 'ONE_STOP'
    TWO_PLUS_STOPS = 'TWO_PLUS_STOPS'


@dataclass(frozen=True)
class SearchFilters:
    cabin_class: CabinClass
    max_stops: MaxStops
    airlines: tuple[str, ...] = ()


def parse_airlines(value: Sequence[str] | str | None) -> tuple[str, ...]:
    """Normalize an airline include-list from a JSON list or comma-separated string."""
    if value is None:
        return ()
    items = value.replace(';', ',').split(',') if isinstance(value, str) else value
    codes: list[str] = []
    for item in items:
        code = str(item).strip().upper()
        if code and code not in codes:
            codes.append(code)
    return tuple(codes)


def resolve_filters(
    cabin_class: str | None = None,
    max_stops: str | None = None,
    airlines: Sequence[str] | str | None = None,
) -> SearchFilters:
    """Apply per-itinerary values over hard-coded fallbacks.

    Omitted values (None) fall back to the constants below — there are no
    user-facing global defaults (they were removed as UX cruft). An empty
    airlines list is an explicit no-include-list restriction. Invalid
    non-empty enum values raise ValueError.
    """
    return SearchFilters(
        cabin_class=CabinClass((cabin_class or CabinClass.ECONOMY).upper()),
        max_stops=MaxStops((max_stops or MaxStops.ANY).upper()),
        airlines=parse_airlines(airlines),
    )
