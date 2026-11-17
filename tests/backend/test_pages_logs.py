INERTIA_HEADERS = {'X-Inertia': 'true', 'X-Inertia-Version': ''}


def test_logs_index_renders_correct_component(client, app, tmp_path):
    with app.app_context():
        app.config['LOG_FILE'] = str(tmp_path / 'empty.log')
        resp = client.get('/logs/', headers=INERTIA_HEADERS)
    assert resp.status_code == 200
    assert resp.get_json()['component'] == 'Logs/Index'


def test_logs_index_props_structure(client, app, tmp_path):
    with app.app_context():
        app.config['LOG_FILE'] = str(tmp_path / 'empty.log')
        resp = client.get('/logs/', headers=INERTIA_HEADERS)
    data = resp.get_json()
    assert 'logs' in data['props']
    assert 'pagination' in data['props']
    assert 'filters' in data['props']


def test_logs_index_empty_file_returns_empty_list(client, app, tmp_path):
    log_file = tmp_path / 'empty.log'
    log_file.write_text('')
    with app.app_context():
        app.config['LOG_FILE'] = str(log_file)
        resp = client.get('/logs/', headers=INERTIA_HEADERS)
    assert resp.get_json()['props']['logs'] == []


def test_logs_index_parses_log_entries(client, app, tmp_path):
    log_file = tmp_path / 'app.log'
    log_file.write_text(
        '2024-06-15 10:00:00,000 - INFO - src.routes - Request received\n'
        '2024-06-15 10:01:00,000 - ERROR - src.services - Something failed\n'
    )
    with app.app_context():
        app.config['LOG_FILE'] = str(log_file)
        resp = client.get('/logs/', headers=INERTIA_HEADERS)
    data = resp.get_json()
    assert len(data['props']['logs']) == 2


def test_logs_index_level_filter_applied(client, app, tmp_path):
    log_file = tmp_path / 'app.log'
    log_file.write_text(
        '2024-06-15 10:00:00,000 - INFO - src - Info message\n'
        '2024-06-15 10:01:00,000 - ERROR - src - Error message\n'
    )
    with app.app_context():
        app.config['LOG_FILE'] = str(log_file)
        resp = client.get('/logs/?levels=ERROR', headers=INERTIA_HEADERS)
    data = resp.get_json()
    assert len(data['props']['logs']) == 1
    assert data['props']['logs'][0]['level'] == 'ERROR'


def test_logs_index_parses_correlation_prefix(client, app, tmp_path):
    log_file = tmp_path / 'app.log'
    log_file.write_text(
        '2024-06-15 10:00:00,000 - INFO - src.routes - [cid:1a2b3c4d] Request received\n'
        '2024-06-15 10:01:00,000 - INFO - src.routes - Plain message\n'
    )
    with app.app_context():
        app.config['LOG_FILE'] = str(log_file)
        resp = client.get('/logs/', headers=INERTIA_HEADERS)
    entries = {entry['message']: entry for entry in resp.get_json()['props']['logs']}
    assert entries['Request received']['correlation'] == '1a2b3c4d'
    assert entries['Plain message']['correlation'] is None


def test_logs_index_pagination_total_reflects_all_entries(client, app, tmp_path):
    log_file = tmp_path / 'app.log'
    lines = '\n'.join(
        f'2024-06-{str(d).zfill(2)} 10:00:00,000 - INFO - src - msg {d}' for d in range(1, 26)
    )
    log_file.write_text(lines + '\n')
    with app.app_context():
        app.config['LOG_FILE'] = str(log_file)
        resp = client.get('/logs/', headers=INERTIA_HEADERS)
    data = resp.get_json()
    assert data['props']['pagination']['total'] == 25


def test_logs_index_invalid_level_falls_back_to_all(client, app, tmp_path):
    log_file = tmp_path / 'app.log'
    log_file.write_text('2024-06-15 10:00:00,000 - INFO - src - msg\n')
    with app.app_context():
        app.config['LOG_FILE'] = str(log_file)
        resp = client.get('/logs/?levels=INVALID', headers=INERTIA_HEADERS)
    data = resp.get_json()
    assert len(data['props']['logs']) == 1


def test_logs_clear_redirects_and_empties_file(client, app, tmp_path):
    log_file = tmp_path / 'app.log'
    log_file.write_text('2024-01-01 00:00:00,000 - INFO - src - test message\n')
    with app.app_context():
        app.config['LOG_FILE'] = str(log_file)
        resp = client.delete('/logs')
    assert resp.status_code in (302, 303)
    assert resp.headers['Location'] == '/logs/'
    assert log_file.read_text() == ''


def test_logs_clear_missing_file_still_redirects(client, app, tmp_path):
    with app.app_context():
        app.config['LOG_FILE'] = str(tmp_path / 'nonexistent.log')
        resp = client.delete('/logs')
    assert resp.status_code in (302, 303)
    assert resp.headers['Location'] == '/logs/'


def test_logs_clear_failure_rerenders_index_with_error(client, app, tmp_path, mocker):
    log_file = tmp_path / 'app.log'
    log_file.write_text('2024-01-01 00:00:00,000 - INFO - src - kept message\n')
    mocker.patch('src.routes.pages.logs.log_svc.clear_logs', side_effect=OSError('boom'))
    with app.app_context():
        app.config['LOG_FILE'] = str(log_file)
        resp = client.delete('/logs', headers=INERTIA_HEADERS)
    data = resp.get_json()
    assert resp.status_code == 422
    assert data['component'] == 'Logs/Index'
    assert data['props']['errors']['logs']
    assert 'kept message' in log_file.read_text()
