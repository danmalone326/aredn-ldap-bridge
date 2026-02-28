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
                hosts = list(payload.get("hosts", []) or [])
                host_ip_map = _build_host_ip_map(hosts)
                filtered = []
                for svc in services:
                    protocol = str(svc.get("protocol", "")).lower()
                    name = str(svc.get("name", "")).lower()
                    phone_tag = f"[{self._protocol_filter}]"
                    is_phone_service = protocol == self._protocol_filter or phone_tag in name
                    if not is_phone_service:
                        continue

                    link = str(svc.get("link", "") or "").strip()
                    sip_target = _parse_sip_target(link)
                    if sip_target is None:
                        continue

                    host, port = sip_target
                    host_ip = host_ip_map.get(host.lower())
                    if not host_ip:
                        self._logger.debug("Skipping service with unresolved sip host host=%s link=%s", host, link)
                        continue

                    telephone_number = host_ip if port is None else f"{host_ip}:{port}"
                    normalized = dict(svc)
                    normalized["telephone_number"] = telephone_number
                    filtered.append(normalized)
                self._logger.info(
                    "Upstream %s returned %s services (%s matched phone-service+sip-link)",
                    node,
                    len(services),
                    len(filtered),
                )
                return filtered
            except (HTTPError, URLError, ValueError) as exc:
                last_error = exc
                self._logger.warning("Upstream %s failed: %s", node, exc)
                continue

        if last_error is not None:
            raise last_error
        return []


def _build_host_ip_map(hosts: List[dict]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for host in hosts:
        name = str(host.get("name", "") or "").strip()
        ip = str(host.get("ip", "") or "").strip()
        if not name or not ip:
            continue
        lower_name = name.lower()
        mapping[lower_name] = ip
        if lower_name.endswith(".local.mesh"):
            mapping[lower_name[: -len(".local.mesh")]] = ip
    return mapping


def _parse_sip_target(link: str) -> tuple[str, int | None] | None:
    if not link.lower().startswith("sip:"):
        return None

    target = link[4:].strip()
    while target.startswith("/"):
        target = target[1:]
    if not target:
        return None

    for marker in (";", "?", "/"):
        marker_index = target.find(marker)
        if marker_index >= 0:
            target = target[:marker_index]
    if not target:
        return None

    if "@" in target:
        target = target.rsplit("@", 1)[1]
    if not target:
        return None

    if target.startswith("["):
        closing = target.find("]")
        if closing < 0:
            return None
        host = target[1:closing].strip()
        remainder = target[closing + 1 :]
        if remainder.startswith(":"):
            port_text = remainder[1:]
            if not port_text.isdigit():
                return None
            return host, int(port_text)
        return host, None

    if ":" in target:
        host, port_text = target.rsplit(":", 1)
        host = host.strip()
        port_text = port_text.strip()
        if not host or not port_text.isdigit():
            return None
        return host, int(port_text)

    return target.strip(), None
