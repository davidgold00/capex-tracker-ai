import json

import pytest

from capex_tracker.guidance import provider


@pytest.mark.parametrize(
    "details",
    [
        {"details": {"parameter_size": "7.6B"}},
        {"remote_model": "remote", "details": {"parameter_size": "3.2B"}},
    ],
)
def test_live_record_rejects_large_and_remote_models(tmp_path, monkeypatch, details):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return details

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            assert url == "http://127.0.0.1:11434/api/show"
            return Response()

    monkeypatch.setattr(provider.requests, "Session", Session)
    with pytest.raises(ValueError, match="local model"):
        provider.call("extract_v1", "test", {}, directory=tmp_path, record=True)
    record = next((tmp_path / "failures").glob("*.json"))
    assert json.loads(record.read_text())["error"] == "ValueError"
    with pytest.raises(RuntimeError, match="Recorded transport failure"):
        provider.call("extract_v1", "test", {}, directory=tmp_path)
