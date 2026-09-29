#!/usr/bin/env python3
"""Experimental Linux/systemd installer. Does not start the service."""
import argparse
import getpass
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import subprocess
import sys
import uuid

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
from rr_ha_bridge.config import Config

SERVICE = "royalrender-ha-bridge"
UNIT_PATH = Path("/etc/systemd/system") / f"{SERVICE}.service"


def safe_path(text):
    """Restrict paths embedded in systemd directives to literal Linux paths."""
    path = str(Path(text).resolve())
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", path):
        raise ValueError("Use absolute paths without spaces or special characters")
    return path


def unit_text(directory, rr_root):
    directory, rr_root = safe_path(directory), safe_path(rr_root)
    return f"""[Unit]
Description=Royal Render Home Assistant Bridge (experimental Linux support)
Wants=network-online.target
After=network-online.target
RequiresMountsFor={rr_root}

[Service]
Type=simple
User={SERVICE}
Group={SERVICE}
StateDirectory={SERVICE}
StateDirectoryMode=0750
WorkingDirectory=/var/lib/{SERVICE}
Environment=RR_ROOT={rr_root}
Environment=LD_LIBRARY_PATH={rr_root}/bin/lx64/lib:{rr_root}/bin/lx64
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=PYTHONUNBUFFERED=1
ExecStart={directory}/venv/bin/python -m rr_ha_bridge.server --config {directory}/config.json
Restart=on-failure
RestartSec=10
TimeoutStopSec=30
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""


def write_private_config(path, config, gid):
    # Exclusive creation prevents overwriting existing credentials or identity.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        os.fchmod(handle.fileno(), 0o640)
        os.fchown(handle.fileno(), 0, gid)
        json.dump(config, handle, indent=2)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rr-root", required=True)
    parser.add_argument("--rr-host", required=True)
    parser.add_argument("--rr-port", type=int, default=7773)
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=8787)
    parser.add_argument("--install-dir", default="/opt/royalrender-ha-bridge")
    parser.add_argument("--rr-user", default="", help="Prompt for its password; never passed on command line")
    parser.add_argument("--enable-commands", action="store_true")
    parser.add_argument("--tls-cert", default="")
    parser.add_argument("--tls-key", default="")
    args = parser.parse_args()
    if sys.platform != "linux" or os.geteuid() != 0:
        parser.error("Run this installer on Linux as root (sudo)")
    if platform.machine().lower() not in ("x86_64", "amd64"):
        parser.error("Only x86-64 RR SDK installations are supported by this preview")
    if not shutil.which("systemctl") or not Path("/run/systemd/system").is_dir():
        parser.error("A running systemd system is required")
    directory = Path(safe_path(args.install_dir))
    root = Path(safe_path(args.rr_root))
    if directory.exists() or directory.is_symlink() or UNIT_PATH.exists() or UNIT_PATH.is_symlink():
        parser.error("Existing installation found; use the documented upgrade procedure")
    sdk_module = root / "bin/lx64/lib" / f"libpyRR{sys.version_info.major}{sys.version_info.minor}.so"
    if not sdk_module.is_file() or not (root / "SDK/External/Python/rr_python_utils/load_rrlib.py").is_file():
        parser.error(f"SDK missing or Python version incompatible: expected {sdk_module}")
    config = dict(
        bridge_id=str(uuid.uuid4()), api_key=secrets.token_urlsafe(48),
        rr_root=str(root), rr_host=args.rr_host, rr_port=args.rr_port,
        rr_user=args.rr_user, rr_password=getpass.getpass("RR password: ") if args.rr_user else "",
        listen_host=args.listen_host, listen_port=args.listen_port,
        allow_commands=args.enable_commands, tls_cert=args.tls_cert, tls_key=args.tls_key,
    )
    import grp
    import pwd
    try:
        account = pwd.getpwnam(SERVICE)
    except KeyError:
        subprocess.run(["useradd", "--system", "--user-group", "--no-create-home",
                        "--home-dir", f"/var/lib/{SERVICE}", "--shell", "/usr/sbin/nologin", SERVICE], check=True)
        account = pwd.getpwnam(SERVICE)
    gid = grp.getgrnam(SERVICE).gr_gid
    if account.pw_uid == 0 or gid == 0:
        raise ValueError("Service account must not be root")
    directory.mkdir(parents=True, mode=0o750)
    os.chown(directory, 0, gid)
    os.chmod(directory, 0o750)
    config_path = directory / "config.json"
    write_private_config(config_path, config, gid)
    Config.load(config_path)
    subprocess.run([sys.executable, "-m", "venv", str(directory / "venv")], check=True)
    python = directory / "venv/bin/python"
    subprocess.run([str(python), "-m", "pip", "install", str(SOURCE)], check=True)
    # The root-owned code must be readable/executable by the unprivileged service.
    subprocess.run(["chmod", "-R", "a+rX", str(directory / "venv")], check=True)
    with UNIT_PATH.open("x", encoding="utf-8") as handle:
        handle.write(unit_text(directory, root))
    UNIT_PATH.chmod(0o644)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    print(f"Installed, NOT started or enabled. Configuration and API key: {config_path}")
    print(f"Check SDK/mount and TLS file access for {SERVICE}, then:")
    print(f"  sudo systemctl enable --now {SERVICE}")


if __name__ == "__main__":
    main()
