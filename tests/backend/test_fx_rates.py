from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.services.fx_rates import (
    FXRatesError,
    _cache_age_seconds,
    _is_cache_fresh,
    _normalize_currency,
    convert_amount,
)

_MOCK_RATES_HKD = {
    'base': 'HKD',
    'rates': {
        'HKD': 1.0,
        'USD': 0.1282,
        'EUR': 0.1176,
        'JPY': 19.23,
        'GBP': 0.1010,
        'CNY': 0.9259,
    },
    'last_updated': '2024-06-15T00:00:00Z',
}


def test_normalize_currency_uppercase():
    assert _normalize_currency('usd') == 'USD'


def test_normalize_currency_strips_whitespace():
    assert _normalize_currency('  EUR  ') == 'EUR'


def test_normalize_currency_none_uses_fallback():
    assert _normalize_currency(None) == 'HKD'


def test_normalize_currency_empty_string_uses_fallback():
    assert _normalize_currency('') == 'HKD'


def test_normalize_currency_custom_fallback():
    assert _normalize_currency(None, 'USD') == 'USD'


def test_cache_age_seconds_utc_aware():
    now_iso = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    age = _cache_age_seconds(now_iso)
    assert 0 <= age < 5


def test_cache_age_seconds_naive_treated_as_utc():
    naive_iso = '2020-01-01T00:00:00'
    age = _cache_age_seconds(naive_iso)
    assert age > 0


def test_is_cache_fresh_matching_base_within_ttl():
    ts = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    data = {'base': 'HKD', 'rates': {'USD': 0.13}, 'last_updated': ts}
    assert _is_cache_fresh(data, 86400, 'HKD') is True


def test_is_cache_fresh_wrong_base_returns_false():
    ts = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    data = {'base': 'USD', 'rates': {'HKD': 7.8}, 'last_updated': ts}
    assert _is_cache_fresh(data, 86400, 'HKD') is False


def test_is_cache_fresh_expired_returns_false():
    old_ts = '2020-01-01T00:00:00Z'
    data = {'base': 'HKD', 'rates': {'USD': 0.13}, 'last_updated': old_ts}
    assert _is_cache_fresh(data, 3600, 'HKD') is False


def test_is_cache_fresh_missing_last_updated():
    data = {'base': 'HKD', 'rates': {}}
    assert _is_cache_fresh(data, 86400, 'HKD') is False


def test_convert_amount_same_currency_returns_rounded(app):
    with app.app_context():
        with patch('src.services.fx_rates.get_rates', return_value=_MOCK_RATES_HKD):
            assert convert_amount(100.0, 'HKD', 'HKD') == 100.0


def test_convert_amount_hkd_to_usd(app):
    with app.app_context():
        with patch('src.services.fx_rates.get_rates', return_value=_MOCK_RATES_HKD):
            result = convert_amount(780.0, 'USD', 'HKD')
            assert isinstance(result, float)
            assert result == round(780.0 / 0.1282, 2)


def test_convert_amount_unknown_src_raises_fx_error(app):
    with app.app_context():
        with patch('src.services.fx_rates.get_rates', return_value=_MOCK_RATES_HKD):
            with pytest.raises(FXRatesError, match='No FX rate found'):
                convert_amount(100.0, 'XYZ', 'HKD')


def test_convert_amount_zero_rate_raises_fx_error(app):
    rates_with_zero = {**_MOCK_RATES_HKD, 'rates': {**_MOCK_RATES_HKD['rates'], 'USD': 0.0}}
    with app.app_context():
        with patch('src.services.fx_rates.get_rates', return_value=rates_with_zero):
            with pytest.raises(FXRatesError, match='FX rate for source currency is zero'):
                convert_amount(100.0, 'USD', 'HKD')


def test_convert_amount_case_insensitive_currency(app):
    with app.app_context():
        with patch('src.services.fx_rates.get_rates', return_value=_MOCK_RATES_HKD):
            result = convert_amount(100.0, 'usd', 'hkd')
            assert isinstance(result, float)


@given(
    amount=st.one_of(
        st.floats(allow_nan=True, allow_infinity=True),
        st.integers(min_value=-(10**15), max_value=10**15),
    ),
    src=st.one_of(
        st.sampled_from(['HKD', 'USD', 'EUR', 'JPY', 'GBP', 'XYZ', '', '!!!', '123']),
        st.text(min_size=0, max_size=8),
    ),
    tgt=st.sampled_from(['HKD', 'USD', 'EUR']),
)
@settings(max_examples=300)
def test_fuzz_convert_amount_only_raises_fx_rates_error(app, amount, src, tgt):
    with app.app_context():
        with patch('src.services.fx_rates.get_rates', return_value=_MOCK_RATES_HKD):
            try:
                result = convert_amount(amount, src, tgt)
                assert isinstance(result, float)
            except FXRatesError:
                pass
