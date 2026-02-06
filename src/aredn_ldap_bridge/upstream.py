from __future__ import annotations

import json
import logging
from typing import List
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


class UpstreamClient:
    def __init__(self, nodes: List[str], timeout_seconds: int, protocol_filter: str) -> None:
        self._nodes = nodes
        self._timeout_seconds = timeout_seconds
        self._protocol_filter = protocol_filter.lower()
        self._logger = logging.getLogger("aredn_ldap_bridge.upstream")

    def fetch_services(self) -> List[dict]:
        last_error: Exception | None = None
        for node in self._nodes:
            url = f"http://{node}/a/sysinfo?services=1"
            self._logger.info("Fetching upstream services from %s", url)
            try:
                request = Request(url)
                with urlopen(request, timeout=self._timeout_seconds) as response:
                    raw = response.read()
                payload = json.loads(raw.decode("utf-8"))
                services = list(payload.get("services", []) or [])
                filtered = []
                for svc in services:
                    protocol = str(svc.get("protocol", "")).lower()
                    name = str(svc.get("name", "")).lower()
                    tag = f"[{self._protocol_filter}]"
                    if protocol == self._protocol_filter or tag in name:
                        filtered.append(svc)
                self._logger.info(
                    "Upstream %s returned %s services (%s matched protocol=%s)",
                    node,
                    len(services),
                    len(filtered),
                    self._protocol_filter,
                )
                return filtered
            except (HTTPError, URLError, ValueError) as exc:
                last_error = exc
                self._logger.warning("Upstream %s failed: %s", node, exc)
                continue

        if last_error is not None:
            raise last_error
        return []
