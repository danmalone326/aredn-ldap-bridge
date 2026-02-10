from __future__ import annotations

import logging
import socketserver

from pyasn1.codec.ber import decoder
from pyasn1.error import SubstrateUnderrunError

from .config import Config
from .ldap_protocol import (
    BindRequestMessage,
    SearchRequestLooseMessage,
    build_bind_response,
    build_extended_response,
    build_ldap_result_response,
    build_search_result_done,
    build_search_result_entry,
    decode_ldap_message,
    encode_ldap_message,
    peek_ldap_op_tag,
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
                        message_id, op_bytes, rest = decode_ldap_message(buffer)
                    except SubstrateUnderrunError:
                        break
                    except Exception as exc:
                        op_tag = peek_ldap_op_tag(buffer)
                        logger.warning("Failed to decode LDAP message op_tag=%s err=%s", op_tag, exc)
                        return

                    buffer = rest
                    self._handle_message(message_id, op_bytes)

        def _handle_message(self, message_id: int, op_bytes: bytes) -> None:
            logger = logging.getLogger("aredn_ldap_bridge.ldap_server")
            op_tag = peek_ldap_op_tag(op_bytes)

            if op_tag == "1:1:0":
                try:
                    bind_request, _ = decoder.decode(op_bytes, asn1Spec=BindRequestMessage())
                except Exception as exc:
                    logger.warning("Failed to decode bind request err=%s", exc)
                    return
                bind_dn = _to_text(bind_request.getComponentByName("name"))
                logger.info("Bind request from %s dn=%s", self.client_address[0], bind_dn)

                response = build_bind_response(message_id, result_code=0)
                self.request.sendall(encode_ldap_message(response))
                return

            if op_tag == "1:1:3":
                try:
                    search_request, _ = decoder.decode(op_bytes, asn1Spec=SearchRequestLooseMessage())
                except Exception as exc:
                    logger.warning("Failed to decode search request err=%s", exc)
                    return
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

            if op_tag == "1:0:2":
                logger.info("Unbind request from %s", self.client_address[0])
                return

            if op_tag == "1:1:23":
                logger.info("Extended request from %s (responding not authorized)", self.client_address[0])
                response = build_extended_response(message_id, result_code=50)
                self.request.sendall(encode_ldap_message(response))
                return

            if op_tag in {"1:1:6", "1:1:8", "1:0:10", "1:1:12", "1:1:14"}:
                response_name = {
                    "1:1:6": "modifyResponse",
                    "1:1:8": "addResponse",
                    "1:0:10": "delResponse",
                    "1:1:12": "modifyDNResponse",
                    "1:1:14": "compareResponse",
                }[op_tag]
                logger.info("Request op_tag=%s from %s (responding not authorized)", op_tag, self.client_address[0])
                response = build_ldap_result_response(message_id, response_name, result_code=50)
                self.request.sendall(encode_ldap_message(response))
                return

            if op_tag == "1:0:16":
                logger.info("Abandon request from %s (ignored)", self.client_address[0])
                return

            logger.info("Ignoring unsupported protocol op_tag=%s", op_tag)

    return LDAPRequestHandler
