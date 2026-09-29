#!/usr/bin/env bash
# GitHub Actions disposable Ubuntu VM only; installs an isolated fake SDK.
set -euo pipefail
python_exe="$(command -v python)"
sdk=/opt/rr-ha-ci-sdk
install=/opt/royalrender-ha-bridge
service=royalrender-ha-bridge
cleanup() {
  sudo systemctl stop "$service" || true
  sudo rm -f "/etc/systemd/system/$service.service"
  sudo systemctl daemon-reload
}
trap cleanup EXIT
sudo "$python_exe" tests/linux_service_smoke.py "$sdk"
sudo "$python_exe" scripts/install-linux.py --rr-root "$sdk" --rr-host unused.invalid
sudo systemd-analyze verify "/etc/systemd/system/$service.service"
test "$(sudo stat -c '%a' "$install/config.json")" = 640
if sudo "$python_exe" scripts/install-linux.py --rr-root "$sdk" --rr-host unused.invalid; then
  echo 'Installer incorrectly accepted an existing installation'
  exit 1
fi
sudo systemctl start "$service"
sudo "$python_exe" - <<'PY'
import json, time, urllib.request
from urllib.error import URLError
from pathlib import Path
config = json.loads(Path('/opt/royalrender-ha-bridge/config.json').read_text())
for attempt in range(30):
    try:
        req = urllib.request.Request('http://127.0.0.1:8787/api/v1/snapshot',
            headers={'Authorization': 'Bearer ' + config['api_key']})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.load(response)
        assert data['jobs'] == [] and data['machines'] == []
        assert data['commands_enabled'] is False
        print('systemd + authenticated HTTP passed with fake SDK')
        break
    except URLError:
        time.sleep(1)
else:
    raise SystemExit('Service did not become ready')
PY
sudo systemctl restart "$service"
sudo systemctl is-active --quiet "$service"
sudo systemctl stop "$service"
if sudo systemctl is-active --quiet "$service"; then exit 1; fi
