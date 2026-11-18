"""Pydantic models for itinerary write payloads.

Schemas validate shape, types, and pure cross-field rules only. Domain rules that
need database state or the viewer's timezone (deadline bounds, first departure)
stay in `src.services.itinerary`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

IATA_PATTERN = re.compile(r'^[A-Z]{3}$')


class TripType(StrEnum):
    """The create form's three trip types (`Pages/Itineraries/Create.vue`)."""

    SINGLE = 'SINGLE'
    ROUND_TRIP = 'ROUND_TRIP'
    MULTI_CITY = 'MULTI_CITY'


def _iso_date(value: Any, copy: str) -> date:
    """Lenient calendar-date parse shared by deadline and flight dates."""
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(copy) from None


def _deadline(value: Any) -> date | None:
    """Parse a page deadline; an empty value clears it."""
    if value in (None, ''):
        return None
    return _iso_date(value, '購票限期日期無效')


def _flight_date(value: Any) -> date:
    return _iso_date(value, '航班日期無效')


def _reject_none(copy: str) -> Callable[[Any], Any]:
    """Reject an explicit null with this field's copy; absent keys never reach it."""

    def validate(value: Any) -> Any:
        if value is None:
            raise ValueError(copy)
        return value

    return validate


class FlightPayload(BaseModel):
    model_config = ConfigDict(extra='forbid')

    origin: str
    destination: str
    flight_date: Annotated[date, BeforeValidator(_flight_date)]

    @field_validator('origin', 'destination', mode='before')
    @classmethod
    def _iata(cls, value: Any) -> str:
        code = str(value or '').strip().upper()
        if not IATA_PATTERN.fullmatch(code):
            raise ValueError('IATA 代碼無效')
        return code


class ItineraryCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    trip_type: TripType = TripType.SINGLE
    deadline: Annotated[date | None, BeforeValidator(_deadline)] = None
    is_active: Annotated[bool, BeforeValidator(_reject_none('追蹤狀態無效'))] = True
    notify_per_leg: Annotated[bool, BeforeValidator(_reject_none('逐航段通知設定無效'))] = False
    cabin_class: str | None = None
    max_stops: str | None = None
    airlines: list[str] | str | None = None
    flights: list[FlightPayload] = Field(min_length=1)

    @field_validator('trip_type', mode='before')
    @classmethod
    def _trip_type(cls, value: Any) -> str:
        return str(value).strip().upper()

    @field_validator('cabin_class', 'max_stops', mode='before')
    @classmethod
    def _enum_token(cls, value: Any) -> str | None:
        """`''`/null/omitted all mean "no filter"; membership stays in the service."""
        return str(value).strip().upper() if value else None


class ItinerarySettings(BaseModel):
    """PATCH payload: an absent key means unchanged, `''` clears the deadline."""

    model_config = ConfigDict(extra='forbid')

    deadline: Annotated[date | None, BeforeValidator(_deadline)] = None
    notify_per_leg: Annotated[bool | None, BeforeValidator(_reject_none('逐航段通知設定無效'))] = (
        None
    )


class ItineraryStatus(BaseModel):
    model_config = ConfigDict(extra='forbid')

    is_active: Annotated[bool | None, BeforeValidator(_reject_none('追蹤狀態無效'))] = None
    archived: Annotated[bool | None, BeforeValidator(_reject_none('封存狀態無效'))] = None

    @model_validator(mode='before')
    @classmethod
    def _reject_unknown(cls, data: Any) -> Any:
        if isinstance(data, dict) and (unsupported := sorted(set(data) - set(cls.model_fields))):
            # model-level error carries no loc; the bridge splits `fields` into one key each
            raise PydanticCustomError(
                'unsupported_field',
                '不允許的欄位：{fields}',
                {'fields': ', '.join(unsupported)},
            )
        return data
