# CODEX Task Prompt — AREDN LDAP Bridge

This prompt is intended to be given verbatim to a CODEX (or similar) autonomous coding agent.

The agent MUST follow `agents.md` and `AREDN_LDAP_Design_Spec.md` as authoritative constraints.

---

## Role
You are an AI software engineer working on the **AREDN LDAP Directory Bridge** project.

Your task is to implement the project incrementally, milestone by milestone, without deviating from the design specification or introducing unnecessary complexity.

---

## Authoritative Documents (Read First)

You MUST read and adhere to the following files before writing code:

1. `agents.md`
2. `AREDN_LDAP_Design_Spec.md`
3. `Milestone_Definition_of_Done.md`

If there is any conflict:
- `AREDN_LDAP_Design_Spec.md` wins
- then `agents.md`
- then this prompt

---

## Global Constraints (Non-Negotiable)

- DO NOT implement TLS, StartTLS, or LDAPS
- DO NOT require authentication; accept all binds
- DO NOT introduce background polling or timers
- DO NOT use OpenLDAP or slapd
- DO NOT persist data to disk or a database
- DO NOT invent directory entries

Fail open when client behavior is ambiguous.

---

## Implementation Strategy

You MUST work strictly in milestone order:

- M1 → M2 → M3 → M4 → M5

You MUST NOT skip milestones or combine them.

After completing each milestone:
- Verify against the **Definition of Done** for that milestone
- Stop and report completion before proceeding

---

## Milestone 1 — LDAP Skeleton (START HERE)

### Objective
Create a minimal LDAP v3 server that accepts binds and returns static directory entries from memory.

### Scope (M1 ONLY)
- Implement LDAP listener on TCP 389
- Implement anonymous bind → success
- Implement simple bind with any DN/password → success
- Implement search returning static in-memory entries
- Implement basic logging

### Out of Scope (Explicitly Forbidden in M1)
- No AREDN upstream fetch
- No caching logic
- No filter parsing beyond presence `(attr=*)`

### Required Behavior
- Service starts via:
  ```
  python -m aredn_ldap_bridge --config config/config.example.ini
  ```
- Search returns entries with:
  - `uid`
  - `cn`
  - `telephoneNumber`
  - `objectClass`

### Acceptance Check
- `ldapsearch` with anonymous bind returns at least one entry
- `ldapsearch` with arbitrary credentials returns at least one entry

When M1 acceptance criteria are met:
STOP. Do not proceed until explicitly instructed.

---

## Milestone 2 — AREDN Integration + Lazy Cache

### Objective
Replace static data with live phone services fetched from AREDN, using a lazy TTL cache.

### Scope
- Implement upstream fetch from ordered node list
- Filter services to `protocol == "phone"`
- Implement in-memory TTL cache (default 60s)
- Refresh cache ONLY on LDAP search
- Implement last-known-good fallback

### Forbidden
- Background refresh threads
- Timers or schedulers

### Acceptance Check
- First search triggers upstream fetch
- Searches within TTL do not refresh
- Cache refresh occurs only after TTL expiry AND a search

STOP after acceptance.

---

## Milestone 3 — Filter Parsing + Matching

### Objective
Implement robust LDAP filter handling and attribute-agnostic matching.

### Scope
- Parse equality, substring, AND, OR, presence filters
- Extract asserted value tokens
- Perform case-insensitive substring matching
- Enforce `max_results`
- Deterministic UID hashing

### Acceptance Check
- `(cn=*foo*)`, `(sn=*foo*)`, `(telephoneNumber=*10*)` all work
- AND/OR semantics honored
- Presence filter returns all entries (bounded)

STOP after acceptance.

---

## Milestone 4 — SPA-514G Acceptance

### Objective
Ensure Cisco SPA-514G Corporate Directory works end-to-end.

### Scope
- Validate bind + search from phone UI
- Validate displayed name and dialing behavior
- Document SPA configuration

### Acceptance Check
- Phone search returns phone entries
- Selecting entry dials IP from `telephoneNumber`

STOP after acceptance.

---

## Milestone 5 — Hardening + Ops

### Objective
Prepare service for real deployment.

### Scope
- Systemd unit
- Clean shutdown handling
- Robust error handling
- Logging improvements
- Documentation

### Acceptance Check
- Service runs reliably under systemd
- Does not crash on malformed LDAP input

---

## Coding Style Requirements

- Python 3.x
- Small, readable modules
- Explicit logic preferred over abstraction
- Logging at INFO level by default
- No unused features

---

## Output Expectations

For each milestone:
- Describe what was implemented
- List files changed
- Explain how acceptance criteria were met

Do NOT proceed beyond the current milestone without instruction.

---

## Final Reminder

This project values:
- correctness over cleverness
- tolerance over strictness
- debuggability over performance

If unsure, choose the simplest implementation that satisfies the spec.
