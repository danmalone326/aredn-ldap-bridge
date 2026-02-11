from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Tuple, List, Iterable

from .util import stable_uid


@dataclass(frozen=True)
class DirectoryEntry:
    uid: str
    cn: str
    telephone_number: str
    dn: str
    link: str = ""
    object_classes: Tuple[str, ...] = ("top", "inetOrgPerson")


def build_static_entries(base_dn: str) -> List[DirectoryEntry]:
    entries = [
        DirectoryEntry(
            uid="static-001",
            cn="AREDN Echo Test",
            telephone_number="sip:10.0.0.10",
            dn=f"uid=static-001,{base_dn}",
            link="",
        ),
        DirectoryEntry(
            uid="static-002",
            cn="AREDN Radio Room",
            telephone_number="sip:10.0.0.20",
            dn=f"uid=static-002,{base_dn}",
            link="",
        ),
    ]
    return entries


def _telephone_number(ip: str, link: str) -> str:
    if link.lower().startswith("sip:"):
        suffix = link[4:].replace("/", "")
        return f"sip:{suffix}" if suffix else f"sip:{ip}"
    return f"sip:{ip}"


def _display_name(name: str) -> str:
    # Strip one trailing bracketed marker like "[phone]" from service names.
    return re.sub(r"\s*\[[^\]]+\]\s*$", "", name).strip()


def entries_from_services(services: Iterable[dict], base_dn: str) -> List[DirectoryEntry]:
    results: List[DirectoryEntry] = []
    for service in services:
        name = str(service.get("name", "")).strip()
        ip = str(service.get("ip", "")).strip()
        link = str(service.get("link", "") or "").strip()
        if not name or not ip:
            continue
        uid = stable_uid(ip, name)
        results.append(
            DirectoryEntry(
                uid=uid,
                cn=_display_name(name),
                telephone_number=_telephone_number(ip, link),
                dn=f"uid={uid},{base_dn}",
                link=link,
            )
        )
    return results
