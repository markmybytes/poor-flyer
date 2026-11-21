"""Pydantic models for itinerary write payloads.

Schemas validate shape, types, and pure cross-field rules only. Rules that compare
against database state or the viewer's timezone (deadline bounds, first departure)
live in `src.schemas.validators` and are called by the view or the service.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from src.schemas.validators import iso_date, regex_match, reject_none

_IataCode = Annotated[
    str,
    BeforeValidator(
        regex_match(re.compile(r'^[A-Z]{3}$'), 'IATA 代碼無效', prepare=lambda s: s.strip().upper())
    ),
]


class FlightPayload(BaseModel):
    model_config = ConfigDict(extra='forbid')

    origin: _IataCode
    destination: _IataCode
    flight_date: Annotated[date, BeforeValidator(iso_date('航班日期無效'))]


class ItineraryCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    trip_type: Literal['SINGLE', 'ROUND_TRIP', 'MULTI_CITY'] = 'SINGLE'
    deadline: Annotated[
        date | None, BeforeValidator(iso_date('購票限期日期無效', allow_empty=True))
    ] = None
    is_active: Annotated[bool, BeforeValidator(reject_none('追蹤狀態無效'))] = True
    notify_per_leg: Annotated[bool, BeforeValidator(reject_none('逐航段通知設定無效'))] = False
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

    deadline: Annotated[
        date | None, BeforeValidator(iso_date('購票限期日期無效', allow_empty=True))
    ] = None
    notify_per_leg: Annotated[bool | None, BeforeValidator(reject_none('逐航段通知設定無效'))] = (
        None
    )


class ItineraryStatus(BaseModel):
    model_config = ConfigDict(extra='forbid')

    is_active: Annotated[bool | None, BeforeValidator(reject_none('追蹤狀態無效'))] = None
    archived: Annotated[bool | None, BeforeValidator(reject_none('封存狀態無效'))] = None
