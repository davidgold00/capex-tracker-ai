from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import requests

from capex_tracker.config import Config
from capex_tracker.sec_client import (
    MissingUserAgentError,
    RawCache,
    SecClient,
    SecRequestError,
    cik_from_tickers,
    get_user_agent,
)


class FakeResponse:
    def __init__(self, status: int, payload: Any = None, headers: dict | None = None) -> None:
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}

    def json(self) -> Any:
        return self._payload


class FakeSession:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.headers: dict[str, str] = {}
        self.calls = 0

    def get(self, url: str, timeout: float) -> Any:
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def client_config(config: Config, tmp_path: Path) -> Config:
    paths = config.paths.model_copy(update={"raw_dir": tmp_path})
    return config.model_copy(update={"paths": paths})


def make_client(config: Config, responses: list[Any], monkeypatch, sleeps: list[float]):
    monkeypatch.setenv("SEC_USER_AGENT", "test-agent")
    session = FakeSession(responses)
    client = SecClient(config, session=session, sleep=sleeps.append)
    return client, session


def test_missing_user_agent_explains_how_to_set_it(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    with pytest.raises(MissingUserAgentError, match="export SEC_USER_AGENT"):
        get_user_agent()


def test_blank_user_agent_is_treated_as_missing(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "   ")
    with pytest.raises(MissingUserAgentError):
        get_user_agent()


def test_user_agent_is_sent(client_config, monkeypatch):
    client, session = make_client(client_config, [], monkeypatch, [])
    assert session.headers["User-Agent"] == "test-agent"
    assert client is not None


def test_cik_is_zero_padded_to_ten_digits():
    tickers = {"0": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft"}}
    assert cik_from_tickers(tickers, "msft") == "0000789019"


def test_unknown_ticker_raises():
    with pytest.raises(KeyError):
        cik_from_tickers({}, "NOPE")


def test_retries_429_and_5xx_with_exponential_backoff(client_config, monkeypatch):
    sleeps: list[float] = []
    client, session = make_client(
        client_config,
        [FakeResponse(429), FakeResponse(503), FakeResponse(200, {"ok": True})],
        monkeypatch,
        sleeps,
    )
    assert client.get_json("https://example.test") == {"ok": True}
    assert session.calls == 3
    backoff = client_config.sec.backoff_seconds
    assert backoff in sleeps
    assert backoff * 2 in sleeps


def test_retry_after_header_extends_the_wait(client_config, monkeypatch):
    sleeps: list[float] = []
    client, _ = make_client(
        client_config,
        [FakeResponse(429, headers={"Retry-After": "30"}), FakeResponse(200, {})],
        monkeypatch,
        sleeps,
    )
    client.get_json("https://example.test")
    assert 30.0 in sleeps


def test_connection_errors_are_retried(client_config, monkeypatch):
    client, session = make_client(
        client_config, [requests.ConnectionError("boom"), FakeResponse(200, {})], monkeypatch, []
    )
    client.get_json("https://example.test")
    assert session.calls == 2


def test_gives_up_after_max_retries(client_config, monkeypatch):
    attempts = client_config.sec.max_retries + 1
    client, session = make_client(
        client_config, [FakeResponse(500) for _ in range(attempts)], monkeypatch, []
    )
    with pytest.raises(SecRequestError, match="HTTP 500"):
        client.get_json("https://example.test")
    assert session.calls == attempts


def test_non_retryable_status_fails_immediately(client_config, monkeypatch):
    client, session = make_client(client_config, [FakeResponse(403)], monkeypatch, [])
    with pytest.raises(SecRequestError, match="403"):
        client.get_json("https://example.test")
    assert session.calls == 1


def test_requests_are_spaced_by_the_configured_delay(client_config, monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setenv("SEC_USER_AGENT", "test-agent")
    session = FakeSession([FakeResponse(200, {}), FakeResponse(200, {})])
    client = SecClient(client_config, session=session, sleep=sleeps.append, clock=lambda: 100.0)
    client.get_json("https://example.test/a")
    client.get_json("https://example.test/b")
    assert sleeps == [client_config.sec.request_delay_seconds]


def test_cache_write_replaces_older_copies(tmp_path: Path):
    cache = RawCache(tmp_path)
    first = datetime(2026, 1, 1, tzinfo=UTC)
    cache.write("key", {"v": 1}, first)
    cache.write("key", {"v": 2}, first + timedelta(hours=1))
    assert cache.read("key") == {"v": 2}
    assert len(list(tmp_path.glob("key_*.json"))) == 1


def test_cache_keys_do_not_match_prefixes(tmp_path: Path):
    cache = RawCache(tmp_path)
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    cache.write("companyfacts_META", {"v": "meta"}, moment)
    assert cache.latest("companyfacts") is None


def test_fresh_cache_is_used_and_refresh_bypasses_it(client_config, monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    monkeypatch.setenv("SEC_USER_AGENT", "test-agent")
    session = FakeSession([FakeResponse(200, {"v": 1}), FakeResponse(200, {"v": 2})])
    client = SecClient(client_config, session=session, sleep=lambda _: None, now=lambda: now)

    assert client._fetch_cached("key", "https://example.test", refresh=False) == {"v": 1}
    assert client._fetch_cached("key", "https://example.test", refresh=False) == {"v": 1}
    assert session.calls == 1
    assert client._fetch_cached("key", "https://example.test", refresh=True) == {"v": 2}
    assert session.calls == 2
