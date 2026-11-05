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


def _resolve_enum(enum_type, value, default, fallback: str):
    return enum_type(str(value).strip().upper() if value else default or fallback)


def resolve_filters(
    cabin_class: str | None = None,
    max_stops: str | None = None,
    airlines: Sequence[str] | str | None = None,
    *,
    default_cabin_class: str | None = None,
    default_max_stops: str | None = None,
    default_airlines: Sequence[str] | str | None = None,
) -> SearchFilters:
    """Apply per-itinerary values over global defaults.

    Omitted values (None) fall back to defaults. An empty airlines list is an
    explicit no-include-list restriction and does not fall back. Invalid
    non-empty enum values raise ValueError.
    """
    return SearchFilters(
        cabin_class=_resolve_enum(CabinClass, cabin_class, default_cabin_class, CabinClass.ECONOMY),
        max_stops=_resolve_enum(MaxStops, max_stops, default_max_stops, MaxStops.ANY),
        airlines=parse_airlines(airlines)
        if airlines is not None
        else parse_airlines(default_airlines),
    )
