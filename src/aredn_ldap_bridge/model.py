from __future__ import annotations

import csv
from dataclasses import dataclass
import re
from pathlib import Path
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


def _display_name(name: str) -> str:
    # Strip one trailing bracketed marker like "[phone]" from service names.
    return re.sub(r"\s*\[[^\]]+\]\s*$", "", name).strip()


def entries_from_services(services: Iterable[dict], base_dn: str) -> List[DirectoryEntry]:
    results: List[DirectoryEntry] = []
    for service in services:
        name = str(service.get("name", "")).strip()
        ip = str(service.get("ip", "")).strip()
        telephone_number = str(service.get("telephone_number", "") or "").strip()
        link = str(service.get("link", "") or "").strip()
        if not name:
            continue
        if not telephone_number and not ip:
            continue
        uid_source = telephone_number or ip
        uid = stable_uid(uid_source, name)
        results.append(
            DirectoryEntry(
                uid=uid,
                cn=_display_name(name),
                telephone_number=telephone_number or ip,
                dn=f"uid={uid},{base_dn}",
                link=link,
            )
        )
    return results


def entries_from_test_cases(csv_path: str, base_dn: str) -> List[DirectoryEntry]:
    path = Path(csv_path)
    if not path.exists():
        return []

    rows: list[list[str]] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            rows.append(row)

    if not rows:
        return []

    first = [cell.strip().lower() for cell in rows[0]]
    has_header = len(first) >= 2 and first[0] == "cn" and first[1] in {"telephonenumer", "telephonenumber"}
    data_rows = rows[1:] if has_header else rows

    results: List[DirectoryEntry] = []
    for row in data_rows:
        if len(row) < 2:
            continue
        cn = row[0]
        telephone_number = row[1]
        if not cn or not telephone_number:
            continue
        uid = stable_uid(telephone_number, cn)
        results.append(
            DirectoryEntry(
                uid=uid,
                cn=cn,
                telephone_number=telephone_number,
                dn=f"uid={uid},{base_dn}",
                link="",
            )
        )
    return results
