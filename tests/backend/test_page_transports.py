INERTIA_HEADERS = {'X-Inertia': 'true', 'X-Inertia-Version': ''}


def _render_props(client):
    return client.get('/itineraries/create', headers=INERTIA_HEADERS).get_json()['props']


def test_flash_share_returns_level_keyed_notices(client):
    with client.session_transaction() as sess:
        sess['_flashes'] = [('success', '已更新設定'), ('legacy', 'still a notice')]

    assert _render_props(client)['flash'] == {
        'success': '已更新設定',
        'legacy': 'still a notice',
    }
    assert _render_props(client)['flash'] == {}


def test_errors_bag_is_popped_on_read_and_camelized(client):
    with client.session_transaction() as sess:
        sess['errors'] = {'notify_per_leg': '逐航段通知設定無效'}

    assert _render_props(client)['errors'] == {'notifyPerLeg': '逐航段通知設定無效'}
    assert _render_props(client)['errors'] == {}


def test_both_channels_populate_and_drain_in_one_render(client):
    with client.session_transaction() as sess:
        sess['_flashes'] = [('success', 'done')]
        sess['errors'] = {'deadline': '購票限期日期無效'}

    props = _render_props(client)
    assert props['flash'] == {'success': 'done'}
    assert props['errors'] == {'deadline': '購票限期日期無效'}

    drained = _render_props(client)
    assert drained['flash'] == {}
    assert drained['errors'] == {}
