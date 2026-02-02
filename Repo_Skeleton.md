# Repository Skeleton

This document defines the recommended repository layout and initial file templates for the **AREDN SIP Directory Bridge**.

Goal: a small, testable Python service with clear module boundaries aligned with `AREDN_SIP_LDAP_Design_Spec.md` and `agents.md`.

---

## Directory Tree

```
aredn-sip-ldap-bridge/
  AREDN_SIP_LDAP_Design_Spec.md
  agents.md
  README.md
  LICENSE
  pyproject.toml
  .gitignore
  .editorconfig

  config/
    config.example.yaml

  src/
    aredn_ldap_bridge/
      __init__.py
      __main__.py
      cli.py
      config.py
      logging_setup.py

      cache.py
      upstream.py
      model.py
      matcher.py

      ldap_server.py
      ldap_protocol.py

      util.py

  tests/
    __init__.py
    test_config.py
    test_uid.py
    test_cache.py
    test_matcher.py
    test_filter_parse.py
    test_upstream_failover.py
    test_ldap_integration_smoke.py

  scripts/
    run_dev.sh
    ldapsearch_smoke.sh

  deploy/
    systemd/
      aredn-ldap-bridge.service

  docs/
    ops.md
    phone-config-spa514g.md
    development.md
```

---

## File Roles (What Goes Where)

### Root
- `AREDN_SIP_LDAP_Design_Spec.md`: authoritative system spec
- `agents.md`: agent rules / constraints
- `README.md`: install, run, configure, troubleshoot
- `pyproject.toml`: packaging, dependencies, tooling

### `config/`
- Example configs; do not store secrets

### `src/aredn_ldap_bridge/`
- **All application code** (packaged module)

Suggested module responsibilities:
- `config.py`: load + validate config
- `logging_setup.py`: consistent logging configuration
- `model.py`: dataclasses for service + ldap entries
- `upstream.py`: fetch AREDN sysinfo; ordered node list; parse JSON
- `cache.py`: lazy TTL cache + single-flight refresh + last-known-good
- `matcher.py`: token extraction + matching logic over cached entries
- `ldap_protocol.py`: filter parsing helpers / protocol constants / minimal encoder helpers (depending on chosen LDAP library)
- `ldap_server.py`: bind/search handlers; wiring between cache+matcher and LDAP library
- `cli.py`: CLI args, config path, run modes
- `__main__.py`: `python -m aredn_ldap_bridge` entrypoint

### `tests/`
- Unit + integration tests
- Integration tests MUST use mocked upstream

### `scripts/`
- Convenience scripts for local dev and smoke tests

### `deploy/systemd/`
- Systemd unit file template

### `docs/`
- Ops guide, phone setup notes, developer notes

---

## Minimal Starter Templates

### `README.md` (starter outline)
- What it is
- Supported phones (SPA-514G reference)
- Quickstart
- Configuration
- Troubleshooting
- Development

### `config/config.example.yaml`
Include:
- `listen_address`, `listen_port`
- `base_dn`, `ou_dn`
- `upstream_nodes` (ordered)
- `upstream_timeout_seconds`
- `cache_ttl_seconds`
- `max_results`
- `protocol_filter: sip`

### `deploy/systemd/aredn-ldap-bridge.service`
- ExecStart: `python -m aredn_ldap_bridge --config /etc/aredn-ldap-bridge/config.yaml`
- Restart: on-failure
- User: dedicated service user

---

## Implementation Notes for Developers

1. **LDAP library choice**
   - Prefer a lightweight Python LDAP server library that supports v3 bind/search.
   - If a library can parse filters and build responses for you, keep protocol handling minimal.

2. **Module boundaries are intentional**
   - LDAP handlers should be thin: parse request → ensure cache fresh → match → format response.

3. **Do not introduce background refresh**
   - All cache refresh must be triggered by search requests.

---

## Next Step

After creating this skeleton in the repo, proceed to:
- Add the Definition-of-Done checklists per milestone
- Add a CODEX task prompt to build Milestone 1 and 2 incrementally

