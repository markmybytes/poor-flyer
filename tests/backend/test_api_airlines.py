from fli.models.airline import AIRLINE_NAMES


def test_list_airlines(client):
    resp = client.get('/api/airlines')

    assert resp.status_code == 200
    body = resp.get_json()
    assert body['message'] is None
    assert {'code': 'CX', 'name': 'Cathay Pacific'} in body['data']
    assert len(body['data']) == len(AIRLINE_NAMES)


def test_airline_codes_are_not_underscore_prefixed(client):
    codes = {airline['code'] for airline in client.get('/api/airlines').get_json()['data']}

    assert '7C' in codes
    assert '_7C' not in codes


def test_airlines_are_sorted_by_code(client):
    codes = [airline['code'] for airline in client.get('/api/airlines').get_json()['data']]

    assert codes == sorted(codes)
