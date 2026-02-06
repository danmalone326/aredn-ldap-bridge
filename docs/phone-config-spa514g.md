# Cisco SPA-514G Corporate Directory Configuration

This document captures a working baseline configuration for the SPA-514G Corporate Directory
to use the AREDN LDAP Bridge.

## Prerequisites
- LDAP service running and reachable from the phone network
- Firewall allows TCP to the LDAP port (default dev port: 8389)

## Directory Settings (SPA-514G Web UI)
Navigate: **Admin Login** → **Advanced** → **Voice** → **Phone** → **LDAP Corporate Directory Search**

Set the following:
- **LDAP Dir Enable**: Yes
- **LDAP Corp Dir Name**: AREDN
- **LDAP Server**: `dev.malone.org:8389`
- **LDAP Auth Method**: None
- **LDAP Search Base**: `dc=local,dc=mesh`
- **LDAP First Name Filter**: `cn`
- **LDAP Display Attrs**: `a=cn;a=telephoneNumber,n=Phone,t=p;`
- **All other settings in this section**: *(blank)*

Save and reboot the phone if prompted.

## Notes
- The LDAP server accepts anonymous bind and simple bind with any credentials.
- The filter is attribute-agnostic; the value token drives matching.
- The phone uses the **LDAP First Name Filter** field for the search token.

## Validation
- On the phone, open Corporate Directory and search for a known name fragment.
- Results should display the service name (`cn`) and dialing should use `telephoneNumber`.
