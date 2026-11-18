from src import _secret_key


def test_secret_key_prefers_env(monkeypatch, tmp_path):
    monkeypatch.setenv('PF_SECRET_KEY', 'from-env')

    assert _secret_key(tmp_path) == 'from-env'
    assert not (tmp_path / 'secret_key').exists()


def test_secret_key_file_is_generated_once(monkeypatch, tmp_path):
    monkeypatch.delenv('PF_SECRET_KEY', raising=False)

    key = _secret_key(tmp_path)

    assert len(key) == 64
    assert (tmp_path / 'secret_key').stat().st_size == 64
    assert _secret_key(tmp_path) == key
