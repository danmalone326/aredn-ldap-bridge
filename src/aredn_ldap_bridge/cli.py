from __future__ import annotations

import argparse
import logging
import signal
from typing import Optional

from .config import load_config
from .cache import LazyCache
from .ldap_server import create_server
from .logging_setup import configure_logging
from .upstream import UpstreamClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AREDN LDAP Bridge")
    parser.add_argument(
        "--config",
        required=False,
        help="Path to INI config file (optional)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config_path: Optional[str] = args.config
    config = load_config(config_path)
    configure_logging(config.log_level)

    upstream = UpstreamClient(
        nodes=config.upstream_nodes,
        timeout_seconds=config.upstream_timeout_seconds,
        protocol_filter=config.protocol_filter,
    )
    cache = LazyCache(
        upstream=upstream,
        base_dn=config.base_dn,
        ttl_seconds=config.cache_ttl_seconds,
    )
    logger = logging.getLogger("aredn_ldap_bridge.cli")
    logger.info(
        "Startup config listen=%s:%s base_dn=%s upstream_nodes=%s ttl=%s max_results=%s protocol_filter=%s",
        config.listen_address,
        config.listen_port,
        config.base_dn,
        ",".join(config.upstream_nodes),
        config.cache_ttl_seconds,
        config.max_results,
        config.protocol_filter,
    )

    server = create_server(config, cache)

    def _handle_signal(signum, frame) -> None:
        logger.info("Received signal %s; shutting down", signum)
        server.shutdown()

    def _handle_reload(signum, frame) -> None:
        logger.info("Received signal %s; reloading config", signum)
        new_config = load_config(config_path)
        if new_config.listen_address != config.listen_address:
            logger.warning("Listen address changed; restart required to apply")
        if new_config.listen_port != config.listen_port:
            logger.warning("Listen port changed; restart required to apply")
        new_upstream = UpstreamClient(
            nodes=new_config.upstream_nodes,
            timeout_seconds=new_config.upstream_timeout_seconds,
            protocol_filter=new_config.protocol_filter,
        )
        cache.reload_settings(new_upstream, new_config.base_dn, new_config.cache_ttl_seconds)
        if new_config.max_results != config.max_results:
            logger.info("Applied max_results=%s", new_config.max_results)
        if new_config.protocol_filter != config.protocol_filter:
            logger.info("Applied protocol_filter=%s", new_config.protocol_filter)
        if new_config.allow_anonymous_bind != config.allow_anonymous_bind:
            logger.info("Applied allow_anonymous_bind=%s", new_config.allow_anonymous_bind)
        if new_config.allow_simple_bind_any_creds != config.allow_simple_bind_any_creds:
            logger.info("Applied allow_simple_bind_any_creds=%s", new_config.allow_simple_bind_any_creds)
        if new_config.log_level != config.log_level:
            logging.getLogger().setLevel(new_config.log_level)
            logger.info("Applied log_level=%s", new_config.log_level)
        config.listen_address = new_config.listen_address
        config.listen_port = new_config.listen_port
        config.base_dn = new_config.base_dn
        config.upstream_nodes = list(new_config.upstream_nodes)
        config.upstream_timeout_seconds = new_config.upstream_timeout_seconds
        config.cache_ttl_seconds = new_config.cache_ttl_seconds
        config.max_results = new_config.max_results
        config.protocol_filter = new_config.protocol_filter
        config.allow_anonymous_bind = new_config.allow_anonymous_bind
        config.allow_simple_bind_any_creds = new_config.allow_simple_bind_any_creds
        config.log_level = new_config.log_level
        logger.info(
            "Reloaded config base_dn=%s upstream_nodes=%s ttl=%s max_results=%s protocol_filter=%s",
            new_config.base_dn,
            ",".join(new_config.upstream_nodes),
            new_config.cache_ttl_seconds,
            new_config.max_results,
            new_config.protocol_filter,
        )

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGHUP, _handle_reload)

    try:
        server.serve_forever()
    finally:
        server.server_close()
