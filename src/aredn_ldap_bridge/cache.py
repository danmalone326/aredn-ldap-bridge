from __future__ import annotations

import logging
import threading
import time
from typing import Callable, List

from .model import DirectoryEntry, entries_from_services
from .upstream import UpstreamClient


class LazyCache:
    def __init__(
        self,
        upstream: UpstreamClient,
        base_dn: str,
        ttl_seconds: int,
    ) -> None:
        self._upstream = upstream
        self._base_dn = base_dn
        self._ttl_seconds = max(1, int(ttl_seconds))
        self._entries: List[DirectoryEntry] = []
        self._last_refresh: float | None = None
        self._lock = threading.Lock()
        self._refreshing = False
        self._refresh_done = threading.Condition(self._lock)
        self._logger = logging.getLogger("aredn_ldap_bridge.cache")

    def get_entries(self) -> List[DirectoryEntry]:
        with self._lock:
            if self._is_fresh_locked():
                return list(self._entries)

            if self._refreshing:
                self._logger.info("Cache refresh in-flight; waiting")
                self._refresh_done.wait(timeout=self._ttl_seconds)
                return list(self._entries)

            self._refreshing = True

        try:
            refreshed = self._refresh()
        finally:
            with self._lock:
                self._refreshing = False
                self._refresh_done.notify_all()

        return list(refreshed)

    def reload_settings(self, upstream: UpstreamClient, base_dn: str, ttl_seconds: int) -> None:
        with self._lock:
            self._upstream = upstream
            self._base_dn = base_dn
            self._ttl_seconds = max(1, int(ttl_seconds))
            self._last_refresh = None

    def _is_fresh_locked(self) -> bool:
        if self._last_refresh is None:
            return False
        age = time.monotonic() - self._last_refresh
        return age < self._ttl_seconds

    def _refresh(self) -> List[DirectoryEntry]:
        self._logger.info("Refreshing cache from upstream")
        try:
            services = self._upstream.fetch_services()
            entries = entries_from_services(services, self._base_dn)
            with self._lock:
                self._entries = entries
                self._last_refresh = time.monotonic()
            self._logger.info("Cache refresh succeeded with %s entries", len(entries))
            return entries
        except Exception as exc:
            self._logger.warning("Cache refresh failed: %s", exc)
            with self._lock:
                if self._entries:
                    self._logger.info("Serving last-known-good cache (%s entries)", len(self._entries))
                    return list(self._entries)
            return []
