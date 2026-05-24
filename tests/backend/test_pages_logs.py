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
