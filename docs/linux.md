# Linux bridge — experimental preview 0.2.0b1

The bridge can run alongside the native Linux edition of Royal Render and serves
the same API as the Windows bridge. Home Assistant configuration is unchanged.
**Real RR Linux SDK loading and farm communication have not been validated.**
Linux CI tests the installer, systemd and HTTP using an explicitly fake SDK.
The proprietary RR SDK is not distributed with this project.

## Requirements

- Linux x86-64 with a running **systemd** system (initial CI target: Ubuntu).
- An installed/mounted Royal Render tree containing `SDK/External/Python` and
  `bin/lx64/lib`. The service user must be able to traverse/read these paths.
- Python **3.11 or later**, venv and pip, with an exactly matching RR native module.
  The inspected RR 9.1.28 distribution has `libpyRR311.so` and `libpyRR313.so`;
  Python 3.12 support must not be assumed. Choose Python 3.13 if that is what
  your vendor installation provides. HA's Python version is independent.
- Distribution/glibc and native libraries compatible with the RR Linux package.
  ARM and non-systemd systems are not covered by this installer.
- Same local timezone as rrServer (RR submission datetimes are interpreted locally).

Install the selected Python and its venv package through your distribution's
supported method. Check the exact executable and architecture:

```sh
python3.13 -c 'import sys, platform; print(sys.executable); print(platform.machine())'
ls /opt/royalrender/bin/lx64/lib/libpyRR313.so
```

All paths and hosts below are examples. Use a local RR path or an existing mounted
RR installation; provisioning SMB/NFS mounts is outside the installer.

## Install

Download and extract the `v0.2.0b1` release archive, then from its directory:

```sh
sudo /usr/bin/python3.13 scripts/install-linux.py \
  --rr-root /opt/royalrender \
  --rr-host rr-server.example.local \
  --listen-host 0.0.0.0 \
  --listen-port 8787
```

The script creates:

- a dedicated non-login system account `royalrender-ha-bridge`;
- root-owned code/venv in `/opt/royalrender-ha-bridge` (override with `--install-dir`);
- `config.json` in that directory: root-owned, service-group readable, mode 0640;
- a random API key and persistent bridge UUID;
- `/etc/systemd/system/royalrender-ha-bridge.service`.

It does **not** start/enable the service or modify the firewall. Default listen
address is loopback; explicitly select `0.0.0.0` or a LAN address for HA access.
It refuses an existing installation or service unit and preserves their contents.
Paths embedded in systemd must not contain spaces or special characters.

Optional arguments:

- `--enable-commands`: enable machine/job actions (otherwise monitoring only).
- `--rr-user USER`: prompt for the RR password, never place it on the command line.
- `--rr-port PORT`: RR TCP port (default 7773).
- `--tls-cert PATH --tls-key PATH`: enable HTTPS; both files must be readable by
  the service account and the certificate trusted by HA.

Keep `config.json` and its backups private. The installer does not print the key.
If installation fails midway, inspect the error and partial installation before
retrying; do not delete an existing configuration blindly.

## Check native SDK access before startup

The RR module lives in `bin/lx64/lib`. Linux's native library search path must be
set **before Python starts**, which the generated unit does automatically.
To test the SDK import without connecting or sending a farm command:

```sh
sudo -u royalrender-ha-bridge env \
  RR_ROOT=/opt/royalrender \
  LD_LIBRARY_PATH=/opt/royalrender/bin/lx64/lib:/opt/royalrender/bin/lx64 \
  PYTHONPATH=/opt/royalrender/SDK/External/Python:/opt/royalrender/bin/lx64/lib \
  /opt/royalrender-ha-bridge/venv/bin/python -B -c \
  'from rr_python_utils.load_rrlib import rrLib; print(rrLib.getRRModuleVersion())'
```

Adapt **all** paths if your installation differs. Use `ldd` on the trusted vendor
`.so` to identify missing system libraries. Do not substitute arbitrary system
libraries or assume Windows DLLs can be used on Linux.

## Start and connect HA

```sh
sudo systemctl enable --now royalrender-ha-bridge
sudo systemctl status royalrender-ha-bridge --no-pager
sudo journalctl -u royalrender-ha-bridge -n 50 --no-pager
```

The service runs without root, logs to journald and restarts on process failure.
Its working directory is `/var/lib/royalrender-ha-bridge`; temporary files use a
private temporary directory. `RequiresMountsFor` waits for the RR path's mounts.
Network failures are handled by bridge polling, never by replaying commands.

Test authenticated HTTP locally without printing the key:

```sh
sudo /opt/royalrender-ha-bridge/venv/bin/python - <<'PY'
import json
from pathlib import Path
from urllib.request import Request, urlopen
config = json.loads(Path('/opt/royalrender-ha-bridge/config.json').read_text())
request = Request('http://127.0.0.1:8787/api/v1/snapshot',
                  headers={'Authorization': 'Bearer ' + config['api_key']})
with urlopen(request, timeout=20) as response:
    print(json.load(response)['summary'])
PY
```

Adapt the URL if you changed port, bind address or enabled HTTPS. Authorize the
chosen TCP port from the HA machine using your distribution's firewall. In HA,
enter the bridge's network URL and the key from your local config in separate
fields. HTTP is intended for a trusted LAN; use TLS for other networks.

## Reconfiguration and upgrade

Stop the service before editing configuration with `sudoedit`:

```sh
sudo systemctl stop royalrender-ha-bridge
sudo cp -p /opt/royalrender-ha-bridge/config.json /opt/royalrender-ha-bridge/config.json.bak
sudoedit /opt/royalrender-ha-bridge/config.json
sudo systemctl start royalrender-ha-bridge
```

Preserve `bridge_id` and `api_key`. Change `allow_commands` to `true` to enable
buttons, or `false` to return to monitoring. Native Disable may interrupt work;
use Disable after frame for an after-frame stop request.

For a source upgrade, stop the service and install from the new extracted release:

```sh
sudo /opt/royalrender-ha-bridge/venv/bin/python -m pip install --upgrade /path/to/new-source
sudo systemctl start royalrender-ha-bridge
```

The installer is for first installation, not upgrades. If the RR mount/root path
changes, update `config.json` **and** the unit's `RR_ROOT`, `LD_LIBRARY_PATH` and
`RequiresMountsFor` values, then run `sudo systemctl daemon-reload` and restart.

## Remove the service

```sh
sudo systemctl disable --now royalrender-ha-bridge
sudo rm /etc/systemd/system/royalrender-ha-bridge.service
sudo systemctl daemon-reload
```

Configuration, venv, state directory, journals and service account are retained.
Remove these separately only if no longer needed. They may contain private data.

## Validation boundaries

Automated coverage: unit generation, native library search paths, rejection of
unsafe systemd paths, actual installation/start/restart/stop on a disposable
Linux CI VM, secret-file permissions, refusal to overwrite an existing install,
and authenticated HTTP with a fake SDK.

Still requiring a volunteer RR Linux installation: native module ABI/dependencies,
real SDK/rrServer connection, mount permissions, server reboot, Working Hours,
after-frame commands and job assignments. Include distribution, Python and RR
versions in reports; redact keys, passwords, internal names and addresses.
