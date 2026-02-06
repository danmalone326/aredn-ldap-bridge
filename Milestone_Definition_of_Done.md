# Milestone Definition of Done (DoD)

This document provides **agent-friendly** checklists and acceptance criteria for each milestone in the AREDN LDAP Directory Bridge project.

Each milestone section includes:
- Deliverables
- Acceptance criteria
- Validation steps / commands
- Notes / pitfalls

---

## M0 — Discovery / Alignment

### Deliverables
- Captured evidence of Cisco SPA-514G LDAP behavior (bind + search)
- Verified reachable AREDN sysinfo endpoint(s)
- Documented upstream node list for development/testing

### Acceptance Criteria
- Evidence exists (pcap or text log) showing SPA-514G bind and search requests
- At least one upstream node successfully returns `sysinfo?services=1`

### Validation Steps
- `curl -s 'http://<node>.local.mesh/a/sysinfo?services=1' | head`
- `tcpdump -i <iface> -s0 -w spa514g_ldap.pcap 'tcp port 389'`

---

## M1 — LDAP Skeleton (Static Directory)

### Deliverables
- Running LDAP service listening on TCP 389
- Bind handler accepting anonymous and simple bind
- Search handler returning static, in-memory directory entries

### Acceptance Criteria
- Anonymous bind succeeds
- Simple bind with arbitrary DN/password succeeds
- Search returns at least one entry with required attributes

### Validation Steps
- `ldapsearch -x -H ldap://127.0.0.1:389 -b 'dc=local,dc=mesh' '(cn=*)'`

---

## M2 — AREDN Integration + Lazy Cache

### Deliverables
- Upstream fetch module querying ordered node list
- phone service filtering
- Lazy, TTL-based in-memory cache
- Last-known-good cache fallback

### Acceptance Criteria
- First search triggers upstream fetch
- Searches within TTL do not refresh cache
- Cache refresh only occurs on search
- Service continues responding if upstream unavailable

### Validation Steps
- Run search twice within TTL and confirm single fetch
- Block upstream and confirm cached results still returned

---

## M3 — Filter Parsing + Robust Matching

### Deliverables
- LDAP filter parser supporting equality, substring, AND, OR, presence
- Attribute-name-agnostic matching engine
- Enforced max-results limit

### Acceptance Criteria
- Substring and equality filters return expected matches
- AND/OR semantics honored
- Presence filter returns all entries (bounded)

### Validation Steps
- `ldapsearch -x -H ldap://127.0.0.1:389 '(cn=*foo*)'`
- `ldapsearch -x -H ldap://127.0.0.1:389 '(|(cn=*a*)(cn=*b*))'`

---

## M4 — SPA-514G Device Acceptance

### Deliverables
- Documented SPA-514G Corporate Directory configuration
- Verified end-to-end directory search from phone UI

### Acceptance Criteria
- Phone successfully binds to LDAP service
- Directory search returns phone entries
- Selecting entry dials IP from `telephoneNumber`

### Validation Steps
- Manual validation via SPA-514G UI

---

## M5 — Hardening + Packaging + Ops

### Deliverables
- Systemd unit file
- Clean shutdown handling
- Robust error handling
- Deployment and ops documentation

### Acceptance Criteria
- Service restarts cleanly under systemd
- Does not crash on malformed LDAP requests
- Documentation sufficient for new operator deployment

### Validation Steps
- `systemctl start aredn-ldap-bridge`
- `pytest`

