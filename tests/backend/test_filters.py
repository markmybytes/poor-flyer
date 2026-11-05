from hypothesis import given
from hypothesis import strategies as st

from src.utils.filters import (
    CabinClass,
    MaxStops,
    SearchFilters,
    parse_airlines,
    resolve_filters,
)

CABINS = st.sampled_from(list(CabinClass))
STOPS = st.sampled_from(list(MaxStops))
CODES = st.lists(
    st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', min_size=2, max_size=3),
    max_size=5,
)


@given(cabin=CABINS, stops=STOPS)
def test_resolve_filters_keeps_per_itinerary_values(cabin, stops):
    filters = resolve_filters(cabin.value, stops.value, ['CX'])
    assert filters.cabin_class is cabin
    assert filters.max_stops is stops


@given(codes=CODES)
def test_resolve_filters_uses_hardcoded_fallbacks_and_codes(codes):
    filters = resolve_filters(None, None, codes)
    assert filters.cabin_class is CabinClass.ECONOMY
    assert filters.max_stops is MaxStops.ANY
    assert filters.airlines == parse_airlines(codes)


def test_empty_airlines_is_explicit_no_restriction():
    filters = resolve_filters(None, None, [])
    assert filters.airlines == ()
    assert isinstance(filters, SearchFilters)


@given(codes=st.lists(st.text(min_size=1, max_size=3), max_size=6))
def test_airline_codes_are_normalized_and_deduplicated(codes):
    parsed = parse_airlines(codes)
    assert all(code == code.upper() and code.strip() for code in parsed)
    assert len(parsed) == len(set(parsed))
