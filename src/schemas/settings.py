"""Pydantic models for settings write payloads.

Flags use pydantic's native bool vocabulary and reject an explicit null; legacy stored
values are only normalized store-side, by `utils.transform.to_bool`. Numeric copies match
the service's checks so the page's error bag keeps its current wording.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict


def _reject_none(value: Any) -> Any:
    """Reject an explicit null; absent keys never reach the validator."""
    if value is None:
        raise ValueError('格式不正確')
    return value


Flag = Annotated[bool | None, BeforeValidator(_reject_none)]


def _cache_ttl(value: Any) -> int:
    try:
        ttl = int(value)
    except TypeError, ValueError:
        raise ValueError('快取有效時間必須是大於 0 的整數') from None
    if ttl <= 0:
        raise ValueError('快取有效時間必須是大於 0 的整數')
    return ttl


def _port(value: Any) -> int:
    try:
        return int(value)
    except TypeError, ValueError:
        raise ValueError('SMTP 連接埠必須是整數') from None


class CurrencySection(BaseModel):
    model_config = ConfigDict(extra='forbid')

    base_currency: str | None = None
    fxrates_api_key: str | None = None
    cache_ttl: Annotated[int, BeforeValidator(_cache_ttl)] | None = None


class EmailSection(BaseModel):
    model_config = ConfigDict(extra='forbid')

    recipients: str | None = None


class ItinerarySection(BaseModel):
    model_config = ConfigDict(extra='forbid')

    disable_departured_itineraries: Flag = None


class SmtpSection(BaseModel):
    model_config = ConfigDict(extra='forbid')

    host: str | None = None
    port: Annotated[int, BeforeValidator(_port)] | None = None
    user: str | None = None
    sender_email: str | None = None
    require_auth: Flag = None
    protocol: str | None = None
    password: str | None = None


class SettingsPayload(BaseModel):
    """One partial write: each section may be absent."""

    model_config = ConfigDict(extra='forbid')

    currency: CurrencySection | None = None
    email: EmailSection | None = None
    itinerary: ItinerarySection | None = None
    smtp: SmtpSection | None = None


class FxRefresh(BaseModel):
    model_config = ConfigDict(extra='forbid')

    base_currency: str | None = None


class TestEmail(BaseModel):
    model_config = ConfigDict(extra='forbid')

    recipient: str = ''
