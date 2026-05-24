def test_clear_logs_success(client, app, tmp_path):
    log_file = tmp_path / 'test.log'
    log_file.write_text('2024-01-01 00:00:00,000 - INFO - src - test message\n')

    with app.app_context():
        app.config['LOG_FILE'] = str(log_file)
        resp = client.delete('/api/logs')

    assert resp.status_code == 200
    assert resp.get_json()['success'] is True
    assert not log_file.exists() or log_file.read_text() == ''


def test_clear_logs_missing_file_still_succeeds(client, app, tmp_path):
    with app.app_context():
        app.config['LOG_FILE'] = str(tmp_path / 'nonexistent.log')
        resp = client.delete('/api/logs')

    assert resp.status_code == 200
    assert resp.get_json()['success'] is True
