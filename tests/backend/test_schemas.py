"""Schema-level pins: token vocabulary, pinned copy, and PATCH presence semantics."""

import pytest
from pydantic import ValidationError

from src.schemas import settings as settings_schemas
from src.schemas.itinerary import ItineraryCreate, ItinerarySettings, ItineraryStatus

LEG = {'origin': 'hkg', 'destination': 'nrt', 'flight_date': '2026-12-01'}


def _create(**overrides):
    return ItineraryCreate.model_validate({'flights': [LEG], **overrides})


@pytest.mark.parametrize(
    ('token', 'expected'),
    [(True, True), ('true', True), ('1', True), (False, False), ('false', False), ('0', False)],
)
def test_create_bool_tokens(token, expected):
    model = _create(is_active=token, notify_per_leg=token)
    assert model.is_active is expected
    assert model.notify_per_leg is expected


@pytest.mark.parametrize(
    ('field', 'copy'),
    [('is_active', 'Invalid is_active'), ('notify_per_leg', 'Invalid notify_per_leg')],
)
def test_create_bool_copy_is_pinned(field, copy):
    with pytest.raises(ValidationError) as caught:
        _create(**{field: 'maybe'})
    assert caught.value.errors()[0]['ctx']['error'].args[0] == copy


@pytest.mark.parametrize('token', ['on', 'off', 'yes', 'no', 't', 'f', 'enable'])
def test_create_bool_tokens_stay_strict(token):
    # pydantic's lax bool would accept these; parse_bool's vocabulary must not
    with pytest.raises(ValidationError):
        _create(is_active=token)


@pytest.mark.parametrize('code', ['hkg', 'HKG', ' Hkg '])
def test_leg_codes_normalize_to_iata(code):
    model = ItineraryCreate.model_validate(
        {'flights': [{'origin': code, 'destination': code, 'flight_date': '2026-12-01'}]}
    )
    assert model.flights[0].origin == 'HKG'
    assert model.flights[0].destination == 'HKG'


@pytest.mark.parametrize('code', ['', 'HK', 'HKG1', 'hk g', None])
def test_malformed_iata_is_rejected(code):
    with pytest.raises(ValidationError):
        ItineraryCreate.model_validate(
            {'flights': [{'origin': code, 'destination': 'NRT', 'flight_date': '2026-12-01'}]}
        )


@pytest.mark.parametrize('field', ['origin', 'destination'])
def test_absent_leg_code_is_rejected(field):
    leg = {'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2026-12-01'}
    leg.pop(field)
    with pytest.raises(ValidationError):
        ItineraryCreate.model_validate({'flights': [leg]})


@pytest.mark.parametrize('value', ['SINGLE', 'ROUND_TRIP', 'MULTI_CITY'])
def test_trip_type_membership(value):
    assert _create(trip_type=value).trip_type == value


def test_trip_type_is_normalized_before_membership():
    assert _create(trip_type=' round_trip ').trip_type == 'ROUND_TRIP'


@pytest.mark.parametrize('value', ['BIZARRE', '', None])
def test_unknown_trip_type_is_rejected(value):
    with pytest.raises(ValidationError):
        _create(trip_type=value)


@pytest.mark.parametrize(
    ('value', 'expected'), [('2026-12-01', '2026-12-01'), ('2026-1-5', '2026-01-05')]
)
def test_flight_date_accepts_lenient_calendar_dates(value, expected):
    model = ItineraryCreate.model_validate(
        {'flights': [{'origin': 'HKG', 'destination': 'NRT', 'flight_date': value}]}
    )
    assert model.flights[0].flight_date.isoformat() == expected


@pytest.mark.parametrize('value', ['2026-13-45', 'nope', '2026/12/01', None, ''])
def test_flight_date_rejects_garbage(value):
    with pytest.raises(ValidationError) as caught:
        ItineraryCreate.model_validate(
            {'flights': [{'origin': 'HKG', 'destination': 'NRT', 'flight_date': value}]}
        )
    assert caught.value.errors()[0]['ctx']['error'].args[0] == 'Invalid flight_date'


def test_deadline_accepts_lenient_calendar_dates():
    assert _create(deadline='2026-1-5').deadline.isoformat() == '2026-01-05'


def test_create_uppercases_leg_codes_and_filters():
    model = _create(cabin_class=' business ', max_stops='non_stop')
    assert model.flights[0].origin == 'HKG'
    assert model.flights[0].destination == 'NRT'
    assert model.cabin_class == 'BUSINESS'
    assert model.max_stops == 'NON_STOP'


@pytest.mark.parametrize('value', ['', None])
def test_create_empty_filters_mean_no_filter(value):
    model = _create(cabin_class=value, max_stops=value)
    assert model.cabin_class is None
    assert model.max_stops is None


@pytest.mark.parametrize('value', ['', None])
def test_create_empty_deadline_clears(value):
    assert _create(deadline=value).deadline is None


def test_create_invalid_deadline_copy_is_pinned():
    with pytest.raises(ValidationError) as caught:
        _create(deadline='2026-13-45')
    assert caught.value.errors()[0]['ctx']['error'].args[0] == 'Deadline must be a valid date'


@pytest.mark.parametrize('payload', [{'trip_type': 'SINGLE'}, {'flights': []}])
def test_create_requires_at_least_one_flight(payload):
    with pytest.raises(ValidationError):
        ItineraryCreate.model_validate(payload)


def test_settings_patch_absent_key_is_not_set():
    model = ItinerarySettings.model_validate({})
    assert model.model_fields_set == set()
    assert model.model_dump(exclude_unset=True) == {}


def test_settings_patch_empty_deadline_is_present_and_none():
    model = ItinerarySettings.model_validate({'deadline': ''})
    assert 'deadline' in model.model_fields_set
    assert model.deadline is None


def test_settings_patch_notify_token_and_copy():
    assert ItinerarySettings.model_validate({'notify_per_leg': '0'}).notify_per_leg is False
    with pytest.raises(ValidationError) as caught:
        ItinerarySettings.model_validate({'notify_per_leg': 'none'})
    assert caught.value.errors()[0]['ctx']['error'].args[0] == 'Invalid notify_per_leg'


def test_status_absent_keys_when_empty():
    assert ItineraryStatus.model_validate({}).model_fields_set == set()


def test_status_unsupported_fields_copy_is_sorted():
    with pytest.raises(ValidationError) as caught:
        ItineraryStatus.model_validate({'zeta': 1, 'alpha': 2, 'is_active': False})
    assert caught.value.errors()[0]['ctx']['error'].args[0] == 'Unsupported field: alpha, zeta'


@pytest.mark.parametrize(
    ('token', 'expected'),
    [(True, True), ('true', True), ('1', True), (False, False), ('false', False), ('0', False)],
)
def test_status_bool_tokens(token, expected):
    model = ItineraryStatus.model_validate({'archived': token, 'is_active': token})
    assert model.archived is expected
    assert model.is_active is expected


def test_status_invalid_bool_copy_is_pinned():
    with pytest.raises(ValidationError) as caught:
        ItineraryStatus.model_validate({'is_active': 'maybe'})
    assert caught.value.errors()[0]['ctx']['error'].args[0] == 'Invalid is_active'


@pytest.mark.parametrize(
    ('token', 'expected'),
    [('true', True), ('1', True), ('enable', True), ('yes', True), ('false', False), ('0', False)],
)
def test_settings_flags_use_the_lenient_store_vocabulary(token, expected):
    model = settings_schemas.SettingsPayload.model_validate(
        {'itinerary': {'disable_departured_itineraries': token}, 'smtp': {'require_auth': token}}
    )
    assert model.itinerary.disable_departured_itineraries is expected
    assert model.smtp.require_auth is expected


def test_settings_payload_dump_keeps_only_submitted_keys():
    payload = settings_schemas.SettingsPayload.model_validate(
        {'currency': {'base_currency': 'USD'}}
    )
    assert payload.model_dump(exclude_unset=True) == {'currency': {'base_currency': 'USD'}}


@pytest.mark.parametrize(
    ('section', 'field', 'value', 'copy'),
    [
        ('currency', 'cache_ttl', 'abc', 'Cache TTL must be an integer greater than 0'),
        ('currency', 'cache_ttl', 0, 'Cache TTL must be an integer greater than 0'),
        ('smtp', 'port', 'abc', 'SMTP port must be an integer'),
    ],
)
def test_settings_numeric_copy_is_pinned(section, field, value, copy):
    with pytest.raises(ValidationError) as caught:
        settings_schemas.SettingsPayload.model_validate({section: {field: value}})
    assert caught.value.errors()[0]['ctx']['error'].args[0] == copy


def test_api_models_default_when_absent():
    assert settings_schemas.FxRefresh.model_validate({}).base_currency is None
    assert settings_schemas.TestEmail.model_validate({}).recipient == ''
