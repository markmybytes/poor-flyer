"""Pydantic models for settings write payloads.

Flags use pydantic's native bool vocabulary and reject an explicit null; legacy stored
values are only normalized store-side, by `utils.transform.to_bool`. Numeric copies match
the service's checks so the page's error bag keeps its current wording.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict

from src.schemas.validators import integer, reject_none


class SettingsPayload(BaseModel):
    """One flat partial write; `model_fields_set` keeps an absent field absent."""

    model_config = ConfigDict(extra='forbid')

    base_currency: str | None = None
    fxrates_api_key: str | None = None
    cache_ttl: (
        Annotated[int, BeforeValidator(integer('快取有效時間必須是大於 0 的整數', minimum=1))]
        | None
    ) = None
    recipients: str | None = None
    disable_departured_itineraries: Annotated[
        bool | None, BeforeValidator(reject_none('格式不正確'))
    ] = None
    host: str | None = None
    port: Annotated[int, BeforeValidator(integer('SMTP 連接埠必須是整數'))] | None = None
    user: str | None = None
    sender_email: str | None = None
    require_auth: Annotated[bool | None, BeforeValidator(reject_none('格式不正確'))] = None
    protocol: str | None = None
    password: str | None = None


class FxRefresh(BaseModel):
    model_config = ConfigDict(extra='forbid')

    base_currency: str | None = None


class TestEmail(BaseModel):
    model_config = ConfigDict(extra='forbid')

    recipient: str = ''
