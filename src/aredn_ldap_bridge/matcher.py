from __future__ import annotations

from typing import Iterable, List

from .model import DirectoryEntry


def filter_entries(
    entries: Iterable[DirectoryEntry],
    filter_bytes: bytes,
    max_results: int,
) -> List[DirectoryEntry]:
    filter_node = parse_filter_bytes(filter_bytes)
    matched: List[DirectoryEntry] = []
    for entry in entries:
        if _match_filter(entry, filter_node):
            matched.append(entry)
            if len(matched) >= max_results:
                break
    return matched


class FilterNode:
    def __init__(self, op: str, tokens: List[str] | None = None, children: List["FilterNode"] | None = None):
        self.op = op
        self.tokens = tokens or []
        self.children = children or []

_MAX_FILTER_DEPTH = 20
_MAX_FILTER_NODES = 200


def _match_filter(entry: DirectoryEntry, node: FilterNode) -> bool:
    if node.op == "and":
        return all(_match_filter(entry, child) for child in node.children)
    if node.op == "or":
        return any(_match_filter(entry, child) for child in node.children)
    if node.op == "not":
        return not _match_filter(entry, node.children[0]) if node.children else True
    if node.op == "present":
        return True
    if node.op == "tokens":
        return all(_token_matches(entry, token) for token in node.tokens)
    return True


def _token_matches(entry: DirectoryEntry, token: str) -> bool:
    token = token.strip().lower()
    if not token:
        return True
    blob = _search_blob(entry)
    return token in blob


def _search_blob(entry: DirectoryEntry) -> str:
    return f"{entry.cn} {entry.telephone_number} {entry.link}".lower()


def parse_filter_bytes(data: bytes) -> FilterNode:
    try:
        state = {"depth": 0, "nodes": 0}
        node, _ = _parse_filter_at(data, 0, state)
        return node
    except Exception:
        return FilterNode("present")


def _parse_filter_at(data: bytes, offset: int, state: dict) -> tuple[FilterNode, int]:
    state["nodes"] += 1
    if state["nodes"] > _MAX_FILTER_NODES:
        raise ValueError("filter node limit exceeded")
    state["depth"] += 1
    if state["depth"] > _MAX_FILTER_DEPTH:
        raise ValueError("filter depth limit exceeded")

    tag_class, constructed, tag_number, length, header_len = _read_tlv_header(data, offset)
    value_start = offset + header_len
    value_end = value_start + length
    value = data[value_start:value_end]

    if tag_class == 0x00 and tag_number == 16:
        tokens = _parse_substrings(data[offset:value_end])
        if tokens:
            state["depth"] -= 1
            return FilterNode("tokens", tokens=tokens), value_end
        token = _parse_ava_assertion(data[offset:value_end])
        if token:
            state["depth"] -= 1
            return FilterNode("tokens", tokens=[token]), value_end

    if tag_class == 0x80:  # context-specific
        if tag_number == 0:  # and
            node = FilterNode("and", children=_parse_filter_list(value, state))
            state["depth"] -= 1
            return node, value_end
        if tag_number == 1:  # or
            node = FilterNode("or", children=_parse_filter_list(value, state))
            state["depth"] -= 1
            return node, value_end
        if tag_number == 2:  # not
            child, _ = _parse_filter_at(value, 0, state)
            node = FilterNode("not", children=[child])
            state["depth"] -= 1
            return node, value_end
        if tag_number == 3:  # equalityMatch
            token = _parse_ava_assertion_content(value)
            state["depth"] -= 1
            return FilterNode("tokens", tokens=[token] if token else []), value_end
        if tag_number == 4:  # substrings
            tokens = _parse_substrings_content(value)
            state["depth"] -= 1
            return FilterNode("tokens", tokens=tokens), value_end
        if tag_number == 7:  # present
            state["depth"] -= 1
            return FilterNode("present"), value_end

    # Unknown or unsupported filter: fail open
    state["depth"] -= 1
    return FilterNode("present"), value_end


def _parse_filter_list(data: bytes, state: dict) -> List[FilterNode]:
    children: List[FilterNode] = []
    offset = 0
    while offset < len(data):
        child, next_offset = _parse_filter_at(data, offset, state)
        if next_offset <= offset:
            break
        offset = next_offset
        children.append(child)
    return children


def _parse_ava_assertion(data: bytes) -> str:
    _, _, tag_number, length, header_len = _read_tlv_header(data, 0)
    if tag_number != 16:
        return ""
    value_start = header_len
    value_end = value_start + length
    seq = data[value_start:value_end]
    offset = 0
    token = ""
    part_index = 0
    while offset < len(seq):
        _, _, inner_tag, inner_len, inner_hdr = _read_tlv_header(seq, offset)
        inner_value = seq[offset + inner_hdr : offset + inner_hdr + inner_len]
        if inner_tag == 4 and part_index == 1:
            token = _decode_bytes(inner_value)
            break
        part_index += 1
        offset = offset + inner_hdr + inner_len
    return token


def _parse_ava_assertion_content(data: bytes) -> str:
    offset = 0
    part_index = 0
    token = ""
    while offset < len(data):
        _, _, inner_tag, inner_len, inner_hdr = _read_tlv_header(data, offset)
        inner_value = data[offset + inner_hdr : offset + inner_hdr + inner_len]
        if inner_tag == 4 and part_index == 1:
            token = _decode_bytes(inner_value)
            break
        part_index += 1
        offset = offset + inner_hdr + inner_len
    return token


def _parse_substrings(data: bytes) -> List[str]:
    tokens: List[str] = []
    _, _, tag_number, length, header_len = _read_tlv_header(data, 0)
    if tag_number != 16:
        return tokens
    value_start = header_len
    value_end = value_start + length
    seq = data[value_start:value_end]
    offset = 0
    parts: List[bytes] = []
    part_index = 0
    substrings_bytes: bytes | None = None
    while offset < len(seq):
        _, _, inner_tag, inner_len, inner_hdr = _read_tlv_header(seq, offset)
        inner_value = seq[offset + inner_hdr : offset + inner_hdr + inner_len]
        if inner_tag == 16 and part_index == 1:
            substrings_bytes = inner_value
            break
        part_index += 1
        offset = offset + inner_hdr + inner_len

    if substrings_bytes is None:
        return tokens

    offset = 0
    while offset < len(substrings_bytes):
        tag_class, _, _, inner_len, inner_hdr = _read_tlv_header(substrings_bytes, offset)
        inner_value = substrings_bytes[offset + inner_hdr : offset + inner_hdr + inner_len]
        if tag_class == 0x80:
            token = _decode_bytes(inner_value)
            if token:
                tokens.append(token)
        offset = offset + inner_hdr + inner_len
    return tokens


def _parse_substrings_content(data: bytes) -> List[str]:
    tokens: List[str] = []
    offset = 0
    part_index = 0
    substrings_bytes: bytes | None = None
    while offset < len(data):
        _, _, inner_tag, inner_len, inner_hdr = _read_tlv_header(data, offset)
        inner_value = data[offset + inner_hdr : offset + inner_hdr + inner_len]
        if inner_tag == 16 and part_index == 1:
            substrings_bytes = inner_value
            break
        part_index += 1
        offset = offset + inner_hdr + inner_len

    if substrings_bytes is None:
        return tokens

    offset = 0
    while offset < len(substrings_bytes):
        tag_class, _, _, inner_len, inner_hdr = _read_tlv_header(substrings_bytes, offset)
        inner_value = substrings_bytes[offset + inner_hdr : offset + inner_hdr + inner_len]
        if tag_class == 0x80:
            token = _decode_bytes(inner_value)
            if token:
                tokens.append(token)
        offset = offset + inner_hdr + inner_len
    return tokens


def _read_tlv_header(data: bytes, offset: int) -> tuple[int, bool, int, int, int]:
    if offset + 1 >= len(data):
        raise ValueError("truncated TLV header")
    first = data[offset]
    tag_class = first & 0xC0
    constructed = bool(first & 0x20)
    tag_number = first & 0x1F
    length_byte = data[offset + 1]
    if length_byte & 0x80 == 0:
        length = length_byte
        header_len = 2
    else:
        num_len_bytes = length_byte & 0x7F
        if num_len_bytes == 0:
            raise ValueError("indefinite length not supported")
        if offset + 2 + num_len_bytes > len(data):
            raise ValueError("truncated TLV length")
        length = int.from_bytes(data[offset + 2 : offset + 2 + num_len_bytes], "big")
        header_len = 2 + num_len_bytes
    if offset + header_len + length > len(data):
        raise ValueError("TLV length exceeds buffer")
    return tag_class, constructed, tag_number, length, header_len


def _decode_bytes(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")
