"""RSS headline fetch via stdlib only (urllib + xml.etree).

Never required for core ADS-B operation: any failure (offline, DNS,
malformed feed) is caught and logged at debug level, leaving callers to
keep showing the last known-good headlines (or nothing).
"""
from __future__ import annotations

import logging
import time
import urllib.request
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_S = 5.0
MAX_HEADLINES = 5


class NewsReader:
    def __init__(self, feed_url: str, refresh_minutes: float) -> None:
        self._feed_url = feed_url
        self._refresh_interval = max(refresh_minutes, 1.0) * 60.0
        self._cached: list[str] = []
        self._next_fetch = 0.0

    def read(self, now: float | None = None) -> list[str]:
        now = now if now is not None else time.monotonic()
        if now < self._next_fetch:
            return self._cached

        self._next_fetch = now + self._refresh_interval
        fetched = self._fetch()
        if fetched:
            self._cached = fetched
        return self._cached

    def _fetch(self) -> list[str]:
        try:
            req = urllib.request.Request(self._feed_url, headers={"User-Agent": "FlightScanner/1.0"})
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as response:
                root = ET.fromstring(response.read())
        except Exception:
            logger.debug("News fetch failed", exc_info=True)
            return []

        titles: list[str] = []
        for item in root.iter("item"):
            title = item.findtext("title")
            if title:
                titles.append(title.strip())
            if len(titles) >= MAX_HEADLINES:
                break

        return titles
