"""Pydantic models for settings write payloads.

Flags use `utils.transform.to_bool` (the lenient store vocabulary: real booleans and
legacy string tokens). Numeric copies match the service's checks so the page's error
bag keeps its current wording.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict

from src.utils.transform import to_bool

Flag = Annotated[bool | None, BeforeValidator(to_bool)]


def _cache_ttl(value: Any) -> int:
    try:
        ttl = int(value)
    except TypeError, ValueError:
        raise ValueError('Cache TTL must be an integer greater than 0') from None
    if ttl <= 0:
        raise ValueError('Cache TTL must be an integer greater than 0')
    return ttl


def _port(value: Any) -> int:
    try:
        return int(value)
    except TypeError, ValueError:
        raise ValueError('SMTP port must be an integer') from None


class CurrencySection(BaseModel):
    model_config = ConfigDict(extra='ignore')

    base_currency: str | None = None
    fxrates_api_key: str | None = None
    cache_ttl: Annotated[int, BeforeValidator(_cache_ttl)] | None = None


class EmailSection(BaseModel):
    model_config = ConfigDict(extra='ignore')

    recipients: str | None = None


class ItinerarySection(BaseModel):
    model_config = ConfigDict(extra='ignore')

    disable_departured_itineraries: Flag = None


class SmtpSection(BaseModel):
    model_config = ConfigDict(extra='ignore')

    host: str | None = None
    port: Annotated[int, BeforeValidator(_port)] | None = None
    user: str | None = None
    sender_email: str | None = None
    require_auth: Flag = None
    protocol: str | None = None
    password: str | None = None


class SettingsPayload(BaseModel):
    """One partial write: each section may be absent."""

    model_config = ConfigDict(extra='ignore')

    currency: CurrencySection | None = None
    email: EmailSection | None = None
    itinerary: ItinerarySection | None = None
    smtp: SmtpSection | None = None


class FxRefresh(BaseModel):
    model_config = ConfigDict(extra='ignore')

    base_currency: str | None = None


class TestEmail(BaseModel):
    model_config = ConfigDict(extra='ignore')

    recipient: str = ''
