"""Pydantic models for itinerary write payloads.

Schemas validate shape, types, and pure cross-field rules only. Domain rules that
need database state or the viewer's timezone (deadline bounds, first departure)
stay in `src.services.itinerary`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator


def _deadline(value: Any) -> date | None:
    """Parse a page deadline; an empty value clears it."""
    if value in (None, ''):
        return None
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        raise ValueError('Deadline must be a valid date') from None


def _flag(label: str):
    """Bool tokens exactly as `utils.filters.parse_bool` accepts them, with the old copy."""

    def parse(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        token = str(value).strip().lower()
        if token in ('true', '1'):
            return True
        if token in ('false', '0'):
            return False
        raise ValueError(f'Invalid {label}')

    return parse


Deadline = Annotated[date | None, BeforeValidator(_deadline)]
IsActive = Annotated[bool, BeforeValidator(_flag('is_active'))]
NotifyPerLeg = Annotated[bool, BeforeValidator(_flag('notify_per_leg'))]
OptionalIsActive = Annotated[bool | None, BeforeValidator(_flag('is_active'))]
OptionalArchived = Annotated[bool | None, BeforeValidator(_flag('archived'))]


class FlightPayload(BaseModel):
    model_config = ConfigDict(extra='ignore')

    origin: str = ''
    destination: str = ''
    flight_date: date

    @field_validator('origin', 'destination')
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.strip().upper()


class ItineraryCreate(BaseModel):
    model_config = ConfigDict(extra='ignore')

    trip_type: str = 'SINGLE'
    deadline: Deadline = None
    is_active: IsActive = True
    notify_per_leg: NotifyPerLeg = False
    cabin_class: str | None = None
    max_stops: str | None = None
    airlines: list[str] | str | None = None
    flights: list[FlightPayload] = Field(min_length=1)

    @field_validator('cabin_class', 'max_stops', mode='before')
    @classmethod
    def _enum_token(cls, value: Any) -> str | None:
        """`''`/null/omitted all mean "no filter"; membership stays in the service."""
        return str(value).strip().upper() if value else None


class ItinerarySettings(BaseModel):
    """PATCH payload: an absent key means unchanged, `''` clears the deadline."""

    model_config = ConfigDict(extra='ignore')

    deadline: Deadline = None
    notify_per_leg: Annotated[bool | None, BeforeValidator(_flag('notify_per_leg'))] = None


class ItineraryStatus(BaseModel):
    model_config = ConfigDict(extra='forbid')

    is_active: OptionalIsActive = None
    archived: OptionalArchived = None

    @model_validator(mode='before')
    @classmethod
    def _reject_unknown(cls, data: Any) -> Any:
        if isinstance(data, dict):
            unsupported = sorted(set(data) - set(cls.model_fields))
            if unsupported:
                raise ValueError(f'Unsupported field: {", ".join(unsupported)}')
        return data
