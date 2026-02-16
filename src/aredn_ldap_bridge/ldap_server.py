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
        _OP_TAG_NAMES = {
            "1:1:0": "bindRequest",
            "1:1:3": "searchRequest",
            "1:0:2": "unbindRequest",
            "1:1:6": "modifyRequest",
            "1:1:8": "addRequest",
            "1:0:10": "delRequest",
            "1:1:12": "modifyDNRequest",
            "1:1:14": "compareRequest",
            "1:0:16": "abandonRequest",
            "1:1:23": "extendedRequest",
        }

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
            op_name = self._OP_TAG_NAMES.get(op_tag, "unknown")

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
                    "Search request from %s base_dn=%s filter=%s filter_hex=%s filter_len=%s",
                    self.client_address[0],
                    base_dn,
                    _render_filter_expression(filter_bytes),
                    filter_bytes.hex(),
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
                logger.info(
                    "Request op=%s op_tag=%s from %s (responding not authorized)",
                    op_name,
                    op_tag,
                    self.client_address[0],
                )
                response = build_ldap_result_response(message_id, response_name, result_code=50)
                self.request.sendall(encode_ldap_message(response))
                return

            if op_tag == "1:0:16":
                logger.info("Abandon request from %s (ignored)", self.client_address[0])
                return

            logger.info("Ignoring unsupported protocol op=%s op_tag=%s", op_name, op_tag)

    return LDAPRequestHandler


def _render_filter_expression(filter_bytes: bytes) -> str:
    try:
        text, next_offset = _parse_filter_at(filter_bytes, 0)
        if next_offset != len(filter_bytes):
            return f"{text} <trailing={filter_bytes[next_offset:].hex()}>"
        return text
    except Exception:
        return "<unparsed>"


def _parse_filter_at(data: bytes, offset: int) -> tuple[str, int]:
    tag_class, _, tag_number, length, header_len = _read_tlv_header(data, offset)
    value_start = offset + header_len
    value_end = value_start + length
    value = data[value_start:value_end]

    if tag_class != 0x80:
        return "(unknown=*)", value_end

    if tag_number == 0:
        return "(&" + "".join(_parse_filter_list(value)) + ")", value_end
    if tag_number == 1:
        return "(|" + "".join(_parse_filter_list(value)) + ")", value_end
    if tag_number == 2:
        child, _ = _parse_filter_at(value, 0)
        return "(!" + child + ")", value_end
    if tag_number == 3:
        return _parse_ava_content(value, "="), value_end
    if tag_number == 4:
        return _parse_substrings_content(value), value_end
    if tag_number == 5:
        return _parse_ava_content(value, ">="), value_end
    if tag_number == 6:
        return _parse_ava_content(value, "<="), value_end
    if tag_number == 7:
        return f"({_decode_bytes(value)}=*)", value_end
    if tag_number == 8:
        return _parse_ava_content(value, "~="), value_end
    if tag_number == 9:
        return "(extensibleMatch=*)", value_end
    return f"(unknown:{tag_number})", value_end


def _parse_filter_list(data: bytes) -> list[str]:
    items: list[str] = []
    offset = 0
    while offset < len(data):
        text, next_offset = _parse_filter_at(data, offset)
        if next_offset <= offset:
            break
        items.append(text)
        offset = next_offset
    return items


def _parse_ava_content(data: bytes, operator: str) -> str:
    parts: list[bytes] = []
    offset = 0
    while offset < len(data) and len(parts) < 2:
        tag_class, _, tag_number, length, header_len = _read_tlv_header(data, offset)
        if tag_class != 0x00 or tag_number != 4:
            break
        value_start = offset + header_len
        value_end = value_start + length
        parts.append(data[value_start:value_end])
        offset = value_end

    attr = _decode_bytes(parts[0]) if parts else "attr"
    token = _decode_bytes(parts[1]) if len(parts) > 1 else ""
    return f"({_escape_filter_value(attr)}{operator}{_escape_filter_value(token)})"


def _parse_substrings_content(data: bytes) -> str:
    attr_class, _, attr_tag, attr_len, attr_hdr = _read_tlv_header(data, 0)
    if attr_class != 0x00 or attr_tag != 4:
        return "(unknown=*)"
    attr_start = attr_hdr
    attr_end = attr_start + attr_len
    attr = _decode_bytes(data[attr_start:attr_end])

    seq_class, _, seq_tag, seq_len, seq_hdr = _read_tlv_header(data, attr_end)
    if seq_class != 0x00 or seq_tag != 16:
        return f"({_escape_filter_value(attr)}=*)"

    offset = attr_end + seq_hdr
    seq_end = offset + seq_len
    initial = ""
    any_tokens: list[str] = []
    final = ""
    while offset < seq_end:
        piece_class, _, piece_tag, piece_len, piece_hdr = _read_tlv_header(data, offset)
        piece_start = offset + piece_hdr
        piece_end = piece_start + piece_len
        token = _escape_filter_value(_decode_bytes(data[piece_start:piece_end]))
        if piece_class == 0x80 and piece_tag == 0:
            initial = token
        elif piece_class == 0x80 and piece_tag == 1:
            any_tokens.append(token)
        elif piece_class == 0x80 and piece_tag == 2:
            final = token
        offset = piece_end

    pattern_parts: list[str] = []
    if initial:
        pattern_parts.append(initial)
    pattern_parts.append("*")
    for token in any_tokens:
        pattern_parts.append(token)
        pattern_parts.append("*")
    if final:
        pattern_parts.append(final)
    return f"({_escape_filter_value(attr)}={''.join(pattern_parts)})"


def _read_tlv_header(data: bytes, offset: int) -> tuple[int, bool, int, int, int]:
    if offset >= len(data):
        raise ValueError("offset out of range")
    first = data[offset]
    tag_class = first & 0xC0
    constructed = bool(first & 0x20)
    tag_number = first & 0x1F

    if offset + 1 >= len(data):
        raise ValueError("missing length")
    length_byte = data[offset + 1]
    if length_byte & 0x80 == 0:
        return tag_class, constructed, tag_number, length_byte, 2

    length_octets = length_byte & 0x7F
    if length_octets == 0:
        raise ValueError("indefinite length not supported")
    if offset + 2 + length_octets > len(data):
        raise ValueError("invalid length")
    length = 0
    for b in data[offset + 2 : offset + 2 + length_octets]:
        length = (length << 8) | b
    return tag_class, constructed, tag_number, length, 2 + length_octets


def _decode_bytes(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def _escape_filter_value(value: str) -> str:
    return (
        value.replace("\\", "\\5c")
        .replace("*", "\\2a")
        .replace("(", "\\28")
        .replace(")", "\\29")
        .replace("\x00", "\\00")
    )
