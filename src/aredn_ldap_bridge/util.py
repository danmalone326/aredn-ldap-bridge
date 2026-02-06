from __future__ import annotations

import hashlib


def stable_uid(ip: str, name: str) -> str:
    payload = f"{ip}|{name}".encode("utf-8")
    digest = hashlib.sha1(payload).hexdigest()
    return digest[:12]
