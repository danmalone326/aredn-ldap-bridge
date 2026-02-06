# Operations Guide

This guide describes deployment and operational basics for the AREDN LDAP Bridge.

## Install Layout (Recommended)
- `/opt/aredn-ldap-bridge` (repo checkout + venv)
- `/etc/aredn-ldap-bridge/config.ini` (runtime configuration)

## Create Service User
```
sudo useradd --system --home /opt/aredn-ldap-bridge --shell /usr/sbin/nologin aredn-ldap-bridge
```

## Install Steps
```
sudo mkdir -p /opt
cd /opt
sudo git clone https://github.com/danmalone326/aredn-ldap-bridge.git
sudo chown -R aredn-ldap-bridge:aredn-ldap-bridge /opt/aredn-ldap-bridge
cd /opt/aredn-ldap-bridge
```

### Python Version and Virtualenv
This project assumes Python 3.x with a local virtualenv named `venv`.
```
sudo -u aredn-ldap-bridge -- python3 -m venv /opt/aredn-ldap-bridge/venv
sudo -u aredn-ldap-bridge -H -- /opt/aredn-ldap-bridge/venv/bin/pip install -r requirements.txt
```

## Systemd Unit
Copy the unit file:
```
sudo mkdir -p /etc/systemd/system
sudo cp deploy/systemd/aredn-ldap-bridge.service /etc/systemd/system/aredn-ldap-bridge.service
sudo systemctl daemon-reload
```

Enable and start:
```
sudo systemctl enable --now aredn-ldap-bridge
```

Check status and logs:
```
sudo systemctl status aredn-ldap-bridge
sudo journalctl -u aredn-ldap-bridge -f
```

Note: The service uses `PYTHONPATH=/opt/aredn-ldap-bridge/src` to load the module without a package install.
The unit grants `CAP_NET_BIND_SERVICE` so the non-root service can bind to port 389.

## Firewall
Allow inbound TCP to the configured LDAP port (default 389; dev 8389):
```
sudo ufw allow 389/tcp
```

## Config
If you need overrides, copy the example config and edit:
```
sudo mkdir -p /etc/aredn-ldap-bridge
sudo cp config/config.example.ini /etc/aredn-ldap-bridge/config.ini
```

Update:
- `listen_address`, `listen_port`
- `upstream_nodes`
- `cache_ttl_seconds`
- `max_results`

Then update the systemd unit to pass the config:
```
sudo systemctl edit aredn-ldap-bridge
```
Add:
```
[Service]
ExecStart=
ExecStart=/opt/aredn-ldap-bridge/venv/bin/python -m aredn_ldap_bridge --config /etc/aredn-ldap-bridge/config.ini
```
Reload and restart:
```
sudo systemctl daemon-reload
sudo systemctl restart aredn-ldap-bridge
```

## Shutdown
The service handles SIGTERM and will stop cleanly under systemd.
