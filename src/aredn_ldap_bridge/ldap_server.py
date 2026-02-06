from __future__ import annotations

import logging
import socketserver
from typing import Iterable, List, Tuple

from pyasn1.error import SubstrateUnderrunError

from .config import Config
from .ldap_protocol import (
    build_bind_response,
    build_search_result_done,
    build_search_result_entry,
    decode_ldap_message,
    encode_ldap_message,
)
from .cache import LazyCache
from .matcher import filter_entries


def create_server(config: Config, cache: LazyCache) -> socketserver.ThreadingTCPServer:
    logger = logging.getLogger("aredn_ldap_bridge.ldap_server")

    handler_class = _make_handler(config, cache)

    class ThreadingLDAPServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    server = ThreadingLDAPServer((config.listen_address, config.listen_port), handler_class)
    logger.info(
        "LDAP server listening on %s:%s base_dn=%s",
        config.listen_address,
        config.listen_port,
        config.base_dn,
    )
    return server


def run_server(config: Config, cache: LazyCache) -> None:
    server = create_server(config, cache)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def _make_handler(config: Config, cache: LazyCache):
    def _to_text(value) -> str:
        try:
            raw = bytes(value)
        except Exception:
            return str(value)
        text = raw.decode("utf-8", errors="replace")
        return text.replace("\r", " ").replace("\n", " ")

    class LDAPRequestHandler(socketserver.BaseRequestHandler):
        _MAX_MESSAGE_BYTES = 64 * 1024

        def handle(self) -> None:
            logger = logging.getLogger("aredn_ldap_bridge.ldap_server")
            buffer = b""

            while True:
                data = self.request.recv(4096)
                if not data:
                    return
                buffer += data
                if len(buffer) > self._MAX_MESSAGE_BYTES:
                    logger.warning("Closing connection: LDAP message exceeds %s bytes", self._MAX_MESSAGE_BYTES)
                    return

                while buffer:
                    try:
                        message, rest = decode_ldap_message(buffer)
                    except SubstrateUnderrunError:
                        break
                    except Exception:
                        logger.exception("Failed to decode LDAP message")
                        return

                    buffer = rest
                    self._handle_message(message)

        def _handle_message(self, message) -> None:
            logger = logging.getLogger("aredn_ldap_bridge.ldap_server")
            message_id = int(message.getComponentByName("messageID"))
            protocol_op = message.getComponentByName("protocolOp")
            op_name = protocol_op.getName()

            if op_name == "bindRequest":
                bind_request = protocol_op.getComponent()
                bind_dn = _to_text(bind_request.getComponentByName("name"))
                logger.info("Bind request from %s dn=%s", self.client_address[0], bind_dn)

                response = build_bind_response(message_id, result_code=0)
                self.request.sendall(encode_ldap_message(response))
                return

            if op_name == "searchRequest":
                search_request = protocol_op.getComponent()
                base_dn = _to_text(search_request.getComponentByName("baseObject"))
                filter_value = search_request.getComponentByName("filter")
                try:
                    filter_bytes = bytes(filter_value.asOctets())
                except Exception:
                    filter_bytes = bytes(filter_value)

                logger.info(
                    "Search request from %s base_dn=%s filter_len=%s",
                    self.client_address[0],
                    base_dn,
                    len(filter_bytes),
                )

                entries = cache.get_entries()
                max_results = max(1, int(config.max_results))
                matched = filter_entries(entries, filter_bytes, max_results)
                logger.info("Search results count=%s", len(matched))
                for entry in matched:
                    attributes = [
                        ("uid", [entry.uid]),
                        ("cn", [entry.cn]),
                        ("telephoneNumber", [entry.telephone_number]),
                        ("objectClass", list(entry.object_classes)),
                    ]
                    entry_msg = build_search_result_entry(
                        message_id=message_id,
                        dn=entry.dn,
                        attributes=attributes,
                    )
                    self.request.sendall(encode_ldap_message(entry_msg))

                done_msg = build_search_result_done(message_id=message_id, result_code=0)
                self.request.sendall(encode_ldap_message(done_msg))
                return

            logger.info("Ignoring unsupported protocol op=%s", op_name)

    return LDAPRequestHandler
