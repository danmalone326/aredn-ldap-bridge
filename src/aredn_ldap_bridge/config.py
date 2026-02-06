from __future__ import annotations

from dataclasses import dataclass
import os
from typing import List

import configparser


@dataclass
class Config:
    listen_address: str = "0.0.0.0"
    listen_port: int = 389
    base_dn: str = "dc=local,dc=mesh"
    upstream_nodes: List[str] = None
    upstream_timeout_seconds: int = 3
    cache_ttl_seconds: int = 60
    max_results: int = 20
    protocol_filter: str = "phone"
    allow_anonymous_bind: bool = True
    allow_simple_bind_any_creds: bool = True
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        # Avoid a shared mutable default list across instances.
        # A fresh list per instance keeps Config safe to mutate.
        if self.upstream_nodes is None:
            self.upstream_nodes = ["localnode.local.mesh"]


def load_config(path: str | None) -> Config:
    parser = configparser.ConfigParser()
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            parser.read_file(handle)

    section = "aredn_ldap_bridge"
    config_section = parser[section] if parser.has_section(section) else parser["DEFAULT"]

    def _get_list(key: str) -> List[str]:
        raw = config_section.get(key, fallback="")
        if not raw:
            return []
        tokens: List[str] = []
        for part in raw.replace("\n", ",").split(","):
            item = part.strip()
            if item:
                tokens.append(item)
        return tokens

    config = Config()

    def _has_option(key: str) -> bool:
        if parser.has_section(section):
            return parser.has_option(section, key)
        return parser.has_option("DEFAULT", key)

    if _has_option("listen_address"):
        config.listen_address = config_section.get("listen_address")
    if _has_option("listen_port"):
        config.listen_port = config_section.getint("listen_port")
    if _has_option("base_dn"):
        config.base_dn = config_section.get("base_dn")
    if _has_option("upstream_nodes"):
        config.upstream_nodes = _get_list("upstream_nodes")
    if _has_option("upstream_timeout_seconds"):
        config.upstream_timeout_seconds = config_section.getint("upstream_timeout_seconds")
    if _has_option("cache_ttl_seconds"):
        config.cache_ttl_seconds = config_section.getint("cache_ttl_seconds")
    if _has_option("max_results"):
        config.max_results = config_section.getint("max_results")
    if _has_option("protocol_filter"):
        config.protocol_filter = config_section.get("protocol_filter")
    if _has_option("allow_anonymous_bind"):
        config.allow_anonymous_bind = config_section.getboolean("allow_anonymous_bind")
    if _has_option("allow_simple_bind_any_creds"):
        config.allow_simple_bind_any_creds = config_section.getboolean("allow_simple_bind_any_creds")
    if _has_option("log_level"):
        config.log_level = config_section.get("log_level")

    return config
