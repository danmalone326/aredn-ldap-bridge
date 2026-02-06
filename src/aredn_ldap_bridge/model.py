from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, List, Optional, Iterable

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
            telephone_number="10.0.0.10",
            dn=f"uid=static-001,{base_dn}",
            link="",
        ),
        DirectoryEntry(
            uid="static-002",
            cn="AREDN Radio Room",
            telephone_number="10.0.0.20",
            dn=f"uid=static-002,{base_dn}",
            link="",
        ),
    ]
    return entries


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
                cn=name,
                telephone_number=ip,
                dn=f"uid={uid},{base_dn}",
                link=link,
            )
        )
    return results
