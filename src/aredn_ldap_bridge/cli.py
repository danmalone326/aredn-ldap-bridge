from __future__ import annotations

import argparse
import logging
import signal

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

    config = load_config(args.config)
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

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    try:
        server.serve_forever()
    finally:
        server.server_close()
