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


@given(cabin=CABINS, stops=STOPS, default_cabin=CABINS, default_stops=STOPS)
def test_per_itinerary_value_overrides_default(cabin, stops, default_cabin, default_stops):
    filters = resolve_filters(
        cabin.value,
        stops.value,
        default_cabin_class=default_cabin.value,
        default_max_stops=default_stops.value,
    )
    assert filters.cabin_class is cabin
    assert filters.max_stops is stops


@given(cabin=CABINS, stops=STOPS)
def test_missing_values_fall_back_to_defaults(cabin, stops):
    filters = resolve_filters(
        None,
        '',
        default_cabin_class=cabin.value,
        default_max_stops=stops.value,
    )
    assert filters.cabin_class is cabin
    assert filters.max_stops is stops


@given(default=CODES)
def test_omitted_airlines_fall_back_to_default(default):
    filters = resolve_filters(None, None, default_airlines=default)
    assert filters.airlines == parse_airlines(default)


def test_empty_airlines_is_explicit_no_restriction():
    filters = resolve_filters(None, None, [], default_airlines=['CX', 'JL'])
    assert filters.airlines == ()


def test_empty_airlines_everywhere_means_no_restriction():
    filters = resolve_filters(None, None, [], default_airlines='')
    assert filters.airlines == ()
    assert isinstance(filters, SearchFilters)


@given(codes=st.lists(st.text(min_size=1, max_size=3), max_size=6))
def test_airline_codes_are_normalized_and_deduplicated(codes):
    parsed = parse_airlines(codes)
    assert all(code == code.upper() and code.strip() for code in parsed)
    assert len(parsed) == len(set(parsed))
