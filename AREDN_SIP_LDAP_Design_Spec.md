# AREDN SIP Directory Bridge (LDAP Facade)

## Purpose
Provide a lightweight LDAP v3 directory service for SIP IP phones on an AREDN mesh. The service translates LDAP Corporate Directory searches into lookups against AREDN advertised services and returns dialable entries whose telephone number is the service IP address.

This document is written to be machine-readable and suitable for use by AI coding agents (e.g., CODEX) as an authoritative design specification.

---

## High-Level Summary
- Acts as an LDAP **facade** over AREDN `sysinfo?services=1`
- Filters services to `protocol == "sip"`
- Accepts **anonymous bind** and **simple bind with any credentials**
- Ignores most LDAP semantics (base DN, schema strictness)
- Returns `cn` (display) + `telephoneNumber` (IP address)
- Uses **lazy, on-demand caching** (TTL = 60s)
- Designed for small hardware (Raspberry Pi)

---

## Scope
### In Scope
- LDAP v3 bind + search
- SIP-only directory entries derived from AREDN advertised services
- Cisco SPA-series SIP phones (SPA-514G as reference)
- Stateless operation with in-memory cache

### Out of Scope
- TLS / StartTLS / LDAPS
- LDAP modify/add/delete
- Authentication or authorization
- Persistent database storage
- Non-SIP services

---

## Terminology
- **AREDN Service**: A service advertised by an AREDN node and returned via `sysinfo?services=1`
- **Directory Entry**: One LDAP entry synthesized from one SIP AREDN service
- **Upstream Node**: An AREDN node queried for mesh-wide service data

---

## Functional Requirements

### Upstream Data Acquisition
- Fetch services from one of an **ordered list** of upstream nodes
- Endpoint: `GET http://<node>.local.mesh/a/sysinfo?services=1`
- Parse JSON and extract `services[]`
- Required service fields:
  - `name` (string)
  - `ip` (string)
  - `protocol` (string)
  - `link` (string, optional)
- Filter strictly to `protocol == "sip"` (case-insensitive)

---

## LDAP Server Requirements

### Network
- Listen on TCP port **389**
- Support LDAP v3

### Bind Behavior
- Anonymous bind: MUST succeed
- Simple bind (any DN/password): MUST succeed
- Credentials are ignored
- Search without bind SHOULD be tolerated

### Search Behavior
- Base DN is ignored (treated as informational only)
- Scope may be ignored (treat as subtree)
- Directory searched is always the in-memory SIP service cache
- Maximum results per search enforced (default: 50)

### Supported Filter Types
- Equality: `(attr=value)`
- Substring: `(attr=*value*)`, `(attr=value*)`, `(attr=*value)`
- AND / OR (recursive)
- Presence: `(attr=*)`

Attribute names in filters are **ignored for semantics**; only asserted values matter.

---

## Matching Strategy

### Token Extraction
- Extract asserted values from the LDAP filter AST
- Ignore attribute names

### Matching Logic
- Precompute a searchable blob per entry:
  ```
  search_blob = lower(name + " " + ip + " " + link)
  ```
- Matching is case-insensitive substring search
- AND: all tokens must match
- OR: any token may match
- Presence-only filter: match all entries (subject to size limit)

---

## Directory Entry Model

### Identifier Strategy
- Each entry has a hash-based identifier
- Compute:
  ```
  uid = truncate(hash(ip + "|" + name), 12)
  ```
- Hash algorithm: SHA-1 or SHA-256 (choose one and standardize)

### Distinguished Name (DN)
```
uid=<uid>,ou=sip,dc=local,dc=mesh
```

Renaming a service produces a new DN (acceptable by design).

### Object Classes
- `top`
- `inetOrgPerson`

### Required Attributes
- `uid`
- `cn` (service name)
- `telephoneNumber` (service IP address)

### Optional Attributes
- `displayName` (same as cn)
- `description` (e.g., protocol + link)
- `labeledURI` (e.g., `sip:<ip>` or provided link)

---

## Caching & Refresh Model

### Cache Characteristics
- In-memory only
- TTL: 60 seconds (configurable)
- No background refresh thread

### Lazy Refresh Logic
- On LDAP search:
  - If cache is missing or expired → refresh before responding
  - Otherwise → serve from cache

### Refresh Behavior
- Try upstream nodes **in order**
- First successful response wins
- If all upstreams fail:
  - Serve last-known-good cache if available
  - Otherwise return zero results

### Concurrency
- Only one refresh operation may run at a time
- Concurrent searches wait or use last-known-good cache

---

## Configuration

### Required Config Parameters
```yaml
listen_address: 0.0.0.0
listen_port: 389
base_dn: dc=local,dc=mesh
ou_dn: ou=sip,dc=local,dc=mesh
upstream_nodes:
  - node1.local.mesh
  - node2.local.mesh
upstream_timeout_seconds: 3
cache_ttl_seconds: 60
max_results: 50
protocol_filter: sip
allow_anonymous_bind: true
allow_simple_bind_any_creds: true
log_level: INFO
```

---

## Logging & Observability

### Required Logs
- Startup configuration summary
- Upstream refresh attempts and success/failure
- Cache refresh events and age
- LDAP bind attempts
- LDAP search requests:
  - filter tokens
  - result count
  - processing time

### Optional Metrics
- Refresh success/failure counters
- Cache age
- Search count
- Average refresh and search latency

---

## Deployment

### Target Platform
- Raspberry Pi or small Linux host on AREDN LAN
- Python runtime

### Service Management
- Run as systemd service
- Restart on failure
- Log to journald or stdout

---

## Testing Requirements

### Unit Tests
- Filter parsing
- Token extraction
- Matching semantics
- Hash determinism
- Cache TTL logic

### Integration Tests
- Mock AREDN sysinfo endpoint
- Ordered upstream failover
- LDAP bind + search via `ldapsearch`

### Device Acceptance
- Cisco SPA-514G Corporate Directory
- Verify:
  - successful bind
  - search results displayed
  - dialing uses `telephoneNumber`

---

## Development Milestones

### M0 – Discovery
- Capture SPA-514G LDAP traffic
- Confirm upstream API access

### M1 – LDAP Skeleton
- Bind + search with static data

### M2 – AREDN Integration
- Upstream fetch + cache + failover

### M3 – Filter Parsing
- AND/OR/substrings/presence

### M4 – Device Acceptance
- SPA-514G validation and fixes

### M5 – Hardening
- Logging, packaging, deployment docs

---

## Open Decisions
- Hash algorithm (SHA-1 vs SHA-256)
- NOT filter support (initially optional)
- Attribute request strictness
- Optional rate limiting / IP allowlist

---

## Design Principles (Non-Negotiable)
- Fail open for LDAP quirks
- Prefer usability over LDAP purity
- No background polling
- Small, readable, auditable codebase
- Treat AREDN as the sole source of truth

