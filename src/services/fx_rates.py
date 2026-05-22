from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from flask import current_app

from src.services.config import get_int, get_str

FX_RATES_BASE_URL = 'https://api.fxratesapi.com'
SUPPORTED_CURRENCIES = [
    'HKD',
    'USD',
    'EUR',
    'GBP',
    'JPY',
    'AUD',
    'CAD',
    'SGD',
    'CNY',
    'KRW',
    'TWD',
    'NZD',
    'CHF',
    'THB',
    'MYR',
    'IDR',
    'PHP',
    'INR',
    'AED',
    'SAR',
    'ZAR',
    'MXN',
    'BRL',
    'TRY',
]
logger = logging.getLogger(__name__)


class FXRatesError(Exception):
    pass


def _normalize_currency(currency: str | None, fallback: str = 'HKD') -> str:
    return (currency or fallback).strip().upper() or fallback


def _resolve_cache_path() -> Path:
    p = Path(current_app.instance_path) / 'fx_cache.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _cache_age_seconds(iso: str) -> float:
    return (
        datetime.now(UTC) - datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(UTC)
    ).total_seconds()


def _read_cache() -> dict[str, Any] | None:
    p = _resolve_cache_path()
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding='utf-8'))
        if isinstance(d, dict) and isinstance(d.get('rates'), dict):
            return d
    except (json.JSONDecodeError, OSError) as e:
        logger.warning('Unable to read FX cache file: %s', e)
    return None


def _write_cache(data: dict[str, Any]) -> None:
    _resolve_cache_path().write_text(
        json.dumps(data, ensure_ascii=True, indent=2), encoding='utf-8'
    )


def _is_cache_fresh(data: dict[str, Any], ttl: int, base: str) -> bool:
    if data.get('base') != base or not isinstance(data.get('last_updated'), str):
        return False
    try:
        return _cache_age_seconds(data['last_updated']) <= ttl
    except ValueError:
        return False


def _fetch_live_rates(base: str, api_key: str | None) -> dict[str, Any]:
    params = {'base': base}
    if api_key:
        params['api_key'] = api_key
    with httpx.Client(timeout=15) as c:
        r = c.get(f'{FX_RATES_BASE_URL}/latest', params=params)
        r.raise_for_status()
        data = r.json()
    rates = data.get('rates')
    if not isinstance(rates, dict) or not rates:
        raise FXRatesError('FX API response does not include valid rates data')
    nb = _normalize_currency(str(data.get('base', base)), base)
    rates[nb] = 1.0
    res = {
        'base': nb,
        'rates': {k.upper(): float(v) for k, v in rates.items()},
        'last_updated': data.get('date') or datetime.now(UTC).isoformat(),
        'source': 'Live API',
    }
    _write_cache(res)
    return res


def get_rates(base_currency: str, force_refresh: bool = False) -> dict[str, Any]:
    nb = _normalize_currency(base_currency)
    c_data = _read_cache()
    if (
        not force_refresh
        and c_data
        and _is_cache_fresh(c_data, get_int('currency', 'cache_ttl', 86400) or 86400, nb)
    ):
        return {**c_data, 'source': 'Local Cache'}
    try:
        return _fetch_live_rates(nb, get_str('currency', 'fxrates_api_key'))
    except (httpx.HTTPError, FXRatesError, ValueError) as e:
        if c_data and c_data.get('base') == nb:
            logger.warning('Falling back to stale FX cache due to refresh failure: %s', e)
            return {**c_data, 'source': 'Local Cache'}
        raise FXRatesError(
            'Unable to load FX rates from API and no local cache is available'
        ) from e


def convert_amount(amount: float | int, src: str, tgt: str) -> float:
    s, t = _normalize_currency(src), _normalize_currency(tgt)
    if s == t:
        return float(round(amount, 2))
    rates = get_rates(t).get('rates', {})
    if not isinstance(rates, dict) or s not in rates:
        raise FXRatesError(f'No FX rate found for source currency: {s}')
    r = float(rates[s])
    if r == 0:
        raise FXRatesError(f'FX rate for source currency is zero: {s}')
    return round(float(amount) / r, 2)


def get_configured_base_currency() -> str:
    b = _normalize_currency(get_str('currency', 'base_currency', 'HKD'), 'HKD')
    return b if b in SUPPORTED_CURRENCIES else 'HKD'
