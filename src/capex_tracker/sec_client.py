"""HTTP access to SEC EDGAR: User-Agent, rate limiting, retries and a raw JSON cache."""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from capex_tracker.config import Company, Config

logger = logging.getLogger(__name__)

USER_AGENT_ENV = "SEC_USER_AGENT"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"


class MissingUserAgentError(RuntimeError):
    """SEC_USER_AGENT is not set."""


class SecRequestError(RuntimeError):
    """A request to SEC failed after all retries."""


class CacheMissError(RuntimeError):
    """A raw response is needed but has not been fetched yet."""


def get_user_agent() -> str:
    """Return the declared User-Agent, or raise with instructions for setting it."""
    value = os.environ.get(USER_AGENT_ENV, "").strip()
    if not value:
        raise MissingUserAgentError(
            f"{USER_AGENT_ENV} is not set. SEC requires a declared User-Agent that identifies "
            "you and includes a way to contact you. Set it before running, for example:\n"
            f'    export {USER_AGENT_ENV}="Your Name <your email address>"\n'
            "In GitHub Actions, add it as a repository secret with the same name."
        )
    return value


def cik_from_tickers(tickers_json: dict[str, Any], ticker: str) -> str:
    """Return the 10-digit zero-padded CIK for ``ticker``."""
    for entry in tickers_json.values():
        if str(entry["ticker"]).upper() == ticker.upper():
            return f"{int(entry['cik_str']):010d}"
    raise KeyError(f"ticker {ticker!r} not found in SEC company_tickers.json")


def _parse_cache_timestamp(path: Path) -> datetime | None:
    try:
        stamp = path.stem.rsplit("_", 1)[1]
        return datetime.strptime(stamp, TIMESTAMP_FORMAT).replace(tzinfo=UTC)
    except (IndexError, ValueError):
        return None


class RawCache:
    """Timestamped raw JSON files such as ``companyfacts_MSFT_20261109T010203Z.json``."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _entries(self, key: str) -> list[tuple[datetime, Path]]:
        entries = []
        for path in self.directory.glob(f"{key}_*.json"):
            stamp = _parse_cache_timestamp(path)
            if stamp is not None and path.stem == f"{key}_{stamp.strftime(TIMESTAMP_FORMAT)}":
                entries.append((stamp, path))
        return sorted(entries)

    def latest(self, key: str) -> tuple[datetime, Path] | None:
        entries = self._entries(key)
        return entries[-1] if entries else None

    def read(self, key: str) -> dict[str, Any]:
        entry = self.latest(key)
        if entry is None:
            raise CacheMissError(
                f"No cached response for {key} in {self.directory}. "
                "Run `python -m capex_tracker fetch` first."
            )
        return json.loads(entry[1].read_text(encoding="utf-8"))

    def write(self, key: str, payload: dict[str, Any], now: datetime) -> Path:
        """Store ``payload`` and delete older copies, keeping only the newest response."""
        self.directory.mkdir(parents=True, exist_ok=True)
        stale = [path for _, path in self._entries(key)]
        path = self.directory / f"{key}_{now.strftime(TIMESTAMP_FORMAT)}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        for old in stale:
            if old != path:
                old.unlink()
        return path


class SecClient:
    """Polite SEC client. Waits between requests and retries 429 and 5xx with backoff."""

    def __init__(
        self,
        config: Config,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.settings = config.sec
        self.cache = RawCache(config.paths.raw_dir)
        self.session = session or requests.Session()
        self.session.headers.update(
            {"User-Agent": get_user_agent(), "Accept-Encoding": "gzip, deflate"}
        )
        self._sleep = sleep
        self._clock = clock
        self._now = now
        self._last_request: float | None = None

    def _throttle(self) -> None:
        if self._last_request is not None:
            remaining = self.settings.request_delay_seconds - (self._clock() - self._last_request)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request = self._clock()

    def _backoff(self, attempt: int, retry_after: str | None) -> float:
        delay = self.settings.backoff_seconds * (2**attempt)
        if retry_after and retry_after.isdigit():
            delay = max(delay, float(retry_after))
        return delay

    def get_json(self, url: str) -> dict[str, Any]:
        """GET ``url`` and decode JSON, retrying transient failures."""
        last_error = "no attempt made"
        for attempt in range(self.settings.max_retries + 1):
            self._throttle()
            retry_after = None
            try:
                response = self.session.get(url, timeout=self.settings.timeout_seconds)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code == 200:
                    return response.json()
                last_error = f"HTTP {response.status_code}"
                if response.status_code not in RETRYABLE_STATUS:
                    raise SecRequestError(f"{url} returned {last_error}, which is not retryable")
                retry_after = response.headers.get("Retry-After")
            if attempt < self.settings.max_retries:
                delay = self._backoff(attempt, retry_after)
                logger.warning("%s failed (%s); retrying in %.1fs", url, last_error, delay)
                self._sleep(delay)
        raise SecRequestError(
            f"{url} failed after {self.settings.max_retries + 1} attempts: {last_error}"
        )

    def _fetch_cached(self, key: str, url: str, refresh: bool) -> dict[str, Any]:
        entry = self.cache.latest(key)
        max_age = timedelta(hours=self.settings.cache_ttl_hours)
        if not refresh and entry is not None and self._now() - entry[0] < max_age:
            logger.info("Using cached %s from %s", key, entry[0].strftime(TIMESTAMP_FORMAT))
            return json.loads(entry[1].read_text(encoding="utf-8"))
        logger.info("Fetching %s", url)
        payload = self.get_json(url)
        self.cache.write(key, payload, self._now())
        return payload

    def fetch_all(self, companies: list[Company], refresh: bool = False) -> None:
        """Populate the cache with the ticker map and each company's facts."""
        tickers = self._fetch_cached("company_tickers", self.settings.tickers_url, refresh)
        for company in companies:
            cik = cik_from_tickers(tickers, company.ticker)
            url = self.settings.companyfacts_url.format(cik=cik)
            self._fetch_cached(cache_key(company.ticker), url, refresh)


def cache_key(ticker: str) -> str:
    """Cache key for one company's companyfacts response."""
    return f"companyfacts_{ticker.upper()}"
