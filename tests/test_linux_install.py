import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location(
    "linux_install", Path(__file__).parents[1] / "scripts/install-linux.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


@pytest.mark.skipif(__import__('sys').platform != 'linux', reason='Linux path semantics')
def test_unit_has_native_loader_paths_and_unprivileged_service():
    unit = installer.unit_text('/opt/rr-bridge', '/mnt/rr')
    assert 'User=royalrender-ha-bridge' in unit
    assert 'RequiresMountsFor=/mnt/rr' in unit
    assert 'LD_LIBRARY_PATH=/mnt/rr/bin/lx64/lib:/mnt/rr/bin/lx64' in unit
    assert 'ExecStart=/opt/rr-bridge/venv/bin/python -m rr_ha_bridge.server' in unit
    assert 'api_key' not in unit
    assert 'rr_password' not in unit


@pytest.mark.parametrize('path', ['/opt/bridge name', '/opt/bridge%h', '/opt/bridge\nUser=root'])
def test_systemd_directive_injection_rejected(path):
    with pytest.raises(ValueError):
        installer.safe_path(path)
